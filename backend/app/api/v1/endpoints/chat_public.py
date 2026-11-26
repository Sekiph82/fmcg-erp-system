"""Public website chat (no login, M36.S03.T005): /public/chat. Allow-listed in PUBLIC_ROUTES.
The visitor proves ownership of a chat with the token from /sessions, sent in the X-Chat-Token header
(never in the URL, so it does not end up in access logs)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_chat_service as chat

router = APIRouter()


class StartIn(BaseModel):
    name: Optional[str] = Field(None, max_length=120, pattern=r"^[^\r\n<>]*$")
    email: Optional[EmailStr] = None
    consent: bool = False
    page_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)   # honeypot: people never see or fill it


class SayIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    email: Optional[EmailStr] = None
    consent: bool = False


def _fail(e: chat.ChatRefused):
    raise HTTPException(e.status, str(e))


async def _portal_user(request: Request, db: AsyncSession):
    """The signed-in portal user if the portal cookie is valid; anonymous otherwise (M45.S01.T024)."""
    from app.core.external_auth import get_portal_user
    try:
        return await get_portal_user(request, db)
    except HTTPException:
        return None


@router.post("/sessions", status_code=201)
async def start_chat(body: StartIn, request: Request, db: AsyncSession = Depends(get_db)):
    portal_user = await _portal_user(request, db)
    try:
        sess, token = await chat.start(db, ip=request.client.host if request.client else None, name=body.name,
                                       email=str(body.email) if body.email else None, consent=body.consent,
                                       page_url=body.page_url, honeypot=body.website, portal_user=portal_user)
    except chat.ChatRefused as e:
        _fail(e)
    await db.commit()
    return {"session_id": str(sess.id), "token": token, "identified": portal_user is not None,
            "messages": await chat.messages(db, sess)}


@router.post("/sessions/{session_id}/messages", status_code=201)
async def say(session_id: uuid.UUID, body: SayIn, x_chat_token: str = Header(..., max_length=100),
              db: AsyncSession = Depends(get_db)):
    try:
        sess = await chat.by_token(db, session_id, x_chat_token, lock=True)
        out = await chat.visitor_says(db, sess, body.body.strip(), email=str(body.email) if body.email else None,
                                      consent=body.consent)
    except chat.ChatRefused as e:
        _fail(e)
    pending = await _pending(db, sess)
    await db.commit()
    return {"status": sess.status, "pending_action": pending,
            "messages": [{"id": str(m.id), "from": m.sender.lower(), "body": m.body, "at": m.created_at.isoformat()} for m in out]}


@router.get("/sessions/{session_id}/messages")
async def poll(session_id: uuid.UUID, after: Optional[datetime] = None, x_chat_token: str = Header(..., max_length=100),
               db: AsyncSession = Depends(get_db)):
    try:
        sess = await chat.by_token(db, session_id, x_chat_token)
    except chat.ChatRefused as e:
        _fail(e)
    return {"status": sess.status, "pending_action": await _pending(db, sess), "messages": await chat.messages(db, sess, after)}


async def _pending(db: AsyncSession, sess) -> Optional[dict]:
    """A write the agent proposed and the customer has not decided (M50.S01.T005): shown with Confirm / Cancel buttons."""
    from app.services import service_agent
    a = await service_agent.pending_action(db, sess)
    return None if a is None else {"id": str(a.id), "kind": a.kind, "summary": a.payload.get("subject")}


class DecideIn(BaseModel):
    confirm: bool


@router.post("/sessions/{session_id}/actions/{action_id}", status_code=201)
async def decide_action(session_id: uuid.UUID, action_id: uuid.UUID, body: DecideIn, x_chat_token: str = Header(..., max_length=100),
                        db: AsyncSession = Depends(get_db)):
    """The customer's own decision on a proposed ticket action. Only the signed-in customer the action was proposed for."""
    from datetime import datetime as _dt, timezone as _tz
    from app.models.crm import CRMChatMessage
    from app.services import service_agent
    try:
        sess = await chat.by_token(db, session_id, x_chat_token, lock=True)
    except chat.ChatRefused as e:
        _fail(e)
    reply = await service_agent.decide_action(db, sess, action_id, body.confirm)
    msg = CRMChatMessage(session_id=sess.id, sender="BOT", body=reply.text, created_at=_dt.now(_tz.utc))
    db.add(msg)
    await db.flush()
    pending = await _pending(db, sess)
    await db.commit()
    return {"status": sess.status, "pending_action": pending,
            "messages": [{"id": str(msg.id), "from": "bot", "body": msg.body, "at": msg.created_at.isoformat()}]}


class FeedbackIn(BaseModel):
    csat: Optional[int] = Field(None, ge=1, le=5)
    ces: Optional[int] = Field(None, ge=1, le=7)


@router.post("/sessions/{session_id}/feedback", status_code=202)
async def feedback(session_id: uuid.UUID, body: FeedbackIn, x_chat_token: str = Header(..., max_length=100),
                   db: AsyncSession = Depends(get_db)):
    from app.services import service_qa
    if body.csat is None and body.ces is None:
        raise HTTPException(422, "Give a satisfaction (1-5) or an effort (1-7) score.")
    try:
        sess = await chat.by_token(db, session_id, x_chat_token)
    except chat.ChatRefused as e:
        _fail(e)
    if not await service_qa.record_feedback(db, sess, body.csat, body.ces):
        raise HTTPException(409, "Nothing to rate yet.")
    await db.commit()
    return {"status": "received"}
