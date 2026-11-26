"""Public website-analytics collector (M44.S01.T009). Prefix /public/web.

Called by /povu-analytics.js on the company website. Bodies are JSON sent as text/plain (navigator.sendBeacon /
simple fetch), so no CORS preflight is needed and no response is read by the site. Per-connection limits apply.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.business_cards_public import _client, _count
from app.db.session import get_db
from app.services import web_analytics_service as wa

router = APIRouter()
_hits: dict[str, deque] = defaultdict(deque)
ID = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
UTM = Field(None, max_length=100)


class EventIn(BaseModel):
    event_id: str = ID
    kind: str = Field(pattern=r"^(PAGE|FORM|CTA|CUSTOM)$")
    name: Optional[str] = Field(None, max_length=100)
    path: str = Field("/", max_length=2000)
    referrer: Optional[str] = Field(None, max_length=2000)
    utm_source: Optional[str] = UTM
    utm_medium: Optional[str] = UTM
    utm_campaign: Optional[str] = UTM
    properties: Optional[dict[str, Union[bool, int, float, str]]] = None   # M47.S01.T008: kept only for defined events

    @field_validator("properties")
    @classmethod
    def _small(cls, v):
        if v and (len(v) > 20 or any(len(k) > 40 for k in v)):
            raise ValueError("at most 20 properties with short names")
        return v


class CollectIn(BaseModel):
    visitor: str = ID
    session: str = ID
    events: list[EventIn] = Field(max_length=20)


class ConsentIn(BaseModel):
    visitor: str = ID
    analytics: bool
    marketing: bool


class IdentifyIn(BaseModel):
    visitor: str = ID
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ForgetIn(BaseModel):
    visitor: str = ID


async def _body(request: Request, model):
    _count(_hits, _client(request), 120)
    raw = await request.body()
    if len(raw) > 32_000:
        raise HTTPException(413, "Too large")
    try:
        return model.model_validate(json.loads(raw or b"{}"))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Invalid payload") from None


@router.post("/consent", status_code=204)
async def consent(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, ConsentIn)
    await wa.record_consent(db, b.visitor, b.analytics, b.marketing)
    await db.commit()
    return Response(status_code=204)


@router.post("/collect")
async def collect(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, CollectIn)
    out = await wa.collect(db, b.visitor, b.session, [e.model_dump() for e in b.events], request.headers.get("user-agent", ""))
    await db.commit()
    return out


@router.post("/identify")
async def identify(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, IdentifyIn)
    linked = await wa.identify(db, b.visitor, b.email)
    await db.commit()
    return {"linked": linked}


@router.post("/forget")
async def forget(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, ForgetIn)
    n = await wa.forget(db, b.visitor)
    await db.commit()
    return {"deleted_events": n}


@router.get("/tags")
async def public_tags(db: AsyncSession = Depends(get_db)):
    """Event tag rules for the website script (selectors and event names only; no visitor data)."""
    return await wa.event_tags(db, active_only=True)
