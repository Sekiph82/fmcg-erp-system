"""Custom channels API (M44.S01.T013). Prefix /public/channels. Authorization: Bearer <channel token>.

POST /{key}/messages  {thread_id, message_id, sender?, text}  → stored once per message_id, threaded in the inbox
GET  /{key}/outbox                                            → our replies, each handed over once
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services import messaging_service as ms

router = APIRouter()


async def _channel(key: str, authorization: str, db: AsyncSession):
    token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    ch = await ms.channel_for_token(db, key, token)
    if ch is None:
        raise HTTPException(401, "Invalid channel or token", headers={"WWW-Authenticate": "Bearer"})
    return ch


class InboundIn(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=120)
    message_id: str = Field(..., min_length=1, max_length=100)
    sender: str | None = Field(None, max_length=200)
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/{key}/messages")
async def inbound(key: str, body: InboundIn, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    ch = await _channel(key, authorization, db)
    stored = await ms._add(db, channel="CUSTOM", account_id=ch.key, thread_id=body.thread_id,
                           external_id=f"in-{body.message_id}", direction="IN", sender=body.sender,
                           body=body.text, status="RECEIVED", created_at=datetime.now(timezone.utc))
    await db.commit()
    return {"stored": stored, "duplicate": not stored}


@router.get("/{key}/outbox")
async def outbox(key: str, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    ch = await _channel(key, authorization, db)
    items = await ms.outbox(db, ch)
    await db.commit()
    return {"items": items}
