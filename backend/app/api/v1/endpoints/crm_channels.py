"""Messaging channels in the CRM inbox (M44.S01.T013). Prefix /api/v1/crm-channels.
Threads are opened from the unified inbox (visibility = inbox rules); custom channels are managed by CRM admins."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.crm import CustomChannel
from app.services import crm_inbox_service as inbox
from app.services import messaging_service as ms

CRM_EDIT = ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region")
CRM_CONFIG = ("crm.edit_all",)
router = APIRouter()


def _id(v: str) -> uuid.UUID:
    try:
        return uuid.UUID(v)
    except ValueError:
        raise HTTPException(404, "Not found") from None


async def _conv(db: AsyncSession, user, cid: str):
    conv = await inbox.get_visible(db, user, _id(cid))
    if conv is None or conv.channel not in ms.CHANNELS:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/status")
async def status(_=Depends(get_current_user)):
    return {"meta": "CONFIGURED" if settings.META_PAGE_ACCESS_TOKEN and settings.META_APP_SECRET else "NOT_CONFIGURED",
            "slack": "CONFIGURED" if settings.SLACK_WEBHOOK_URL else "NOT_CONFIGURED"}


@router.get("/conversations/{cid}")
async def get_thread(cid: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    conv = await _conv(db, user, cid)
    msgs = await ms.thread(db, conv.channel, conv.source_ref)
    await inbox.mark_read(db, user, conv)
    await db.commit()
    return {"id": str(conv.id), "channel": conv.channel, "subject": conv.subject, "status": conv.status,
            "messages": [{"id": str(m.id), "direction": m.direction, "sender": m.sender, "body": m.body,
                          "status": m.status, "at": m.created_at} for m in msgs]}


class ReplyIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/conversations/{cid}/reply")
async def reply(cid: str, body: ReplyIn, db: AsyncSession = Depends(get_db),
                user=Depends(require_any_permission(CRM_EDIT))):
    conv = await _conv(db, user, cid)
    try:
        m = await ms.reply(db, conv.channel, conv.source_ref, body.text.strip(), user.id)
    except ms.MessagingError as e:
        raise HTTPException(e.status, str(e)) from None
    await db.commit()
    return {"id": str(m.id), "status": m.status}


class CustomIn(BaseModel):
    key: str = Field(..., description="lower-case slug, e.g. partner-app")
    name: str = Field(..., min_length=1, max_length=120)


def _out(c: CustomChannel, token: Optional[str] = None) -> dict:
    d = {"id": str(c.id), "key": c.key, "name": c.name, "active": c.active, "created_by": c.created_by}
    return {**d, "token": token} if token else d


@router.get("/custom-channels")
async def list_custom(db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
    return [_out(c) for c in (await db.execute(select(CustomChannel).order_by(CustomChannel.name))).scalars()]


@router.post("/custom-channels", status_code=201)
async def create_custom(body: CustomIn, db: AsyncSession = Depends(get_db), user=Depends(require_any_permission(CRM_CONFIG))):
    """The token is returned once; keep it in the connecting app."""
    if not ms.KEY_RE.match(body.key):
        raise HTTPException(422, "key: 2–40 lower-case letters, digits or dashes")
    if (await db.execute(select(CustomChannel.id).where(CustomChannel.key == body.key))).first():
        raise HTTPException(409, "A channel with this key exists")
    token, h = ms.new_token()
    c = CustomChannel(key=body.key, name=body.name, token_hash=h, created_by=user.username)
    db.add(c)
    await db.commit()
    return _out(c, token)


@router.post("/custom-channels/{channel_id}/{action}")
async def custom_action(channel_id: str, action: str, db: AsyncSession = Depends(get_db),
                        _=Depends(require_any_permission(CRM_CONFIG))):
    """rotate (new token, old one stops working) | disable | enable."""
    c = await db.get(CustomChannel, _id(channel_id))
    if c is None:
        raise HTTPException(404, "Channel not found")
    token = None
    if action == "rotate":
        token, c.token_hash = ms.new_token()
    elif action in ("disable", "enable"):
        c.active = action == "enable"
    else:
        raise HTTPException(404, "Unknown action")
    await db.commit()
    return _out(c, token)
