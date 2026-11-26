"""M51.S01.T009 PUBLIC visitor e-mail verification endpoints (prefix /public/visitor-verify, no login).

  POST /request   {visitor, session, email, consent, locale}   always the same answer (429 only for the per-IP limit)
  POST /confirm   {visitor, session, token}  or  {visitor, session, email, code}   {"verified": bool}
  POST /status    {visitor}   POST /revoke {visitor}   (no address is ever returned)
JSON bodies up to 32 KB; per-connection limit 60/min; responses never reveal whether an address is known.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.business_cards_public import _client, _count
from app.db.session import get_db
from app.services import m51_visitor_verify_service as vv

router = APIRouter()
_hits: dict[str, deque] = defaultdict(deque)
ID = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
NOINDEX = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}


class RequestIn(BaseModel):
    visitor: str = ID
    session: str = ID
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    consent: bool
    locale: str = Field("en", max_length=2)


class ConfirmIn(BaseModel):
    visitor: str = ID
    session: str = ID
    token: Optional[str] = Field(None, min_length=20, max_length=100)
    code: Optional[str] = Field(None, pattern=r"^\d{6}$")
    email: Optional[str] = Field(None, max_length=254)


class VisitorIn(BaseModel):
    visitor: str = ID


async def _body(request: Request, model):
    _count(_hits, _client(request), 60)
    raw = await request.body()
    if len(raw) > 32_000:
        raise HTTPException(413, "Too large")
    try:
        return model.model_validate(json.loads(raw or b"{}"))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Invalid payload") from None


@router.post("/request")
async def request_(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, RequestIn)
    try:
        out = await vv.request(db, b.visitor, b.session, b.email, b.consent, _client(request), b.locale)
    except vv.RateLimited:
        await db.commit()
        raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": "3600", **NOINDEX}) from None
    await db.commit()
    return out


@router.post("/confirm")
async def confirm(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, ConfirmIn)
    if not (b.token or (b.code and b.email)):
        return dict(vv.FAIL)
    out = await vv.confirm(db, b.visitor, b.session, b.token, b.code, b.email)
    await db.commit()
    return out


@router.post("/status")
async def status(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, VisitorIn)
    return await vv.status(db, b.visitor)


@router.post("/revoke")
async def revoke(request: Request, db: AsyncSession = Depends(get_db)):
    b = await _body(request, VisitorIn)
    await vv.revoke_visitor(db, b.visitor)
    await db.commit()
    return {"revoked": True}


