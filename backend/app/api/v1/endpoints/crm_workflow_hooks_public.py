"""Inbound workflow webhook (M47.S01.T008). Prefix /public/crm-workflow-hooks.

A system outside the ERP enrols a CRM record into a published workflow whose trigger is "inbound_webhook":
POST /{workflow_id} with `Authorization: Bearer <token>` and JSON {"event_id", "record_id" | "email"}.
The token is shown once to an approver; only its SHA-256 digest is stored. The event id makes a replay enrol once.
Per-connection and per-workflow limits apply.
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.business_cards_public import _client, _count
from app.db.session import get_db
from app.services import crm_workflow_service as wfs

router = APIRouter()
_hits: dict[str, deque] = defaultdict(deque)


class HookIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    record_id: Optional[uuid.UUID] = None
    email: Optional[str] = Field(None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @model_validator(mode="after")
    def _one(self):
        if (self.record_id is None) == (self.email is None):
            raise ValueError("give exactly one of record_id or email")
        return self


@router.post("/{workflow_id}")
async def enrol(workflow_id: uuid.UUID, request: Request, authorization: str = Header(""),
                db: AsyncSession = Depends(get_db)):
    _count(_hits, f"ip:{_client(request)}", 60)
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if await wfs.hook_token_ok(db, workflow_id, token) is None:
        raise HTTPException(401, "Invalid workflow or token.")
    _count(_hits, f"wf:{workflow_id}", 120)    # counted only for the real token: strangers cannot exhaust it (M47 review)
    raw = await request.body()
    if len(raw) > 8_000:
        raise HTTPException(413, "Too large")
    try:
        body = HookIn.model_validate(json.loads(raw or b"{}"))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Send JSON {event_id, record_id | email}.") from None
    try:
        out = await wfs.hook_enrol(db, workflow_id, token, body.event_id, body.record_id, body.email)
    except wfs.WorkflowError as e:
        await db.rollback()
        raise HTTPException(e.status, e.detail) from None
    await db.commit()
    return out
