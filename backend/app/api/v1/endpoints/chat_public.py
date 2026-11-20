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


@router.post("/sessions", status_code=201)
async def start_chat(body: StartIn, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        sess, token = await chat.start(db, ip=request.client.host if request.client else None, name=body.name,
                                       email=str(body.email) if body.email else None, consent=body.consent,
                                       page_url=body.page_url, honeypot=body.website)
    except chat.ChatRefused as e:
        _fail(e)
    await db.commit()
    return {"session_id": str(sess.id), "token": token, "messages": await chat.messages(db, sess)}


@router.post("/sessions/{session_id}/messages", status_code=201)
async def say(session_id: uuid.UUID, body: SayIn, x_chat_token: str = Header(..., max_length=100),
              db: AsyncSession = Depends(get_db)):
    try:
        sess = await chat.by_token(db, session_id, x_chat_token, lock=True)
        out = await chat.visitor_says(db, sess, body.body.strip(), email=str(body.email) if body.email else None,
                                      consent=body.consent)
    except chat.ChatRefused as e:
        _fail(e)
    await db.commit()
    return {"status": sess.status, "messages": [{"id": str(m.id), "from": m.sender.lower(), "body": m.body,
                                                  "at": m.created_at.isoformat()} for m in out]}


@router.get("/sessions/{session_id}/messages")
async def poll(session_id: uuid.UUID, after: Optional[datetime] = None, x_chat_token: str = Header(..., max_length=100),
               db: AsyncSession = Depends(get_db)):
    try:
        sess = await chat.by_token(db, session_id, x_chat_token)
    except chat.ChatRefused as e:
        _fail(e)
    return {"status": sess.status, "messages": await chat.messages(db, sess, after)}
