"""Shared and delegated mailboxes (M49.S01.T003). Prefix /api/v1/shared-mailboxes.

Registering a mailbox, granting / revoking members and closing it needs integrations.edit. Reading, replying and
syncing need membership of that mailbox (re-checked on every request, so revocation is immediate); the mailbox's mail
lives in its own account and never appears in anyone's personal inbox (/email/*)."""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.email_integration import EmailThread
from app.models.m49_calendar_mail import SharedMailbox, SharedMailboxMember
from app.schemas.email_integration import EmailThreadRead
from app.services import shared_mailbox_service as svc

router = APIRouter()
MANAGE = ("integrations.edit",)


class RegisterIn(BaseModel):
    provider: Literal["google", "microsoft"]
    address: EmailStr
    display_name: Optional[str] = Field(None, max_length=255)
    kind: Literal["shared", "delegated"] = "shared"

    @field_validator("display_name")
    @classmethod
    def _one_line(cls, v):
        if v is not None and any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class MemberIn(BaseModel):
    user_id: uuid.UUID
    can_send: bool = False
    send_mode: Literal["send_as", "on_behalf"] = "send_as"


class SendIn(BaseModel):
    to_emails: List[EmailStr] = Field(min_length=1, max_length=50)
    cc_emails: List[EmailStr] = Field(default_factory=list, max_length=50)
    subject: str = Field(min_length=1, max_length=900)
    body_text: str = Field(max_length=200_000)
    reply_to_thread_id: Optional[uuid.UUID] = None

    @field_validator("subject")
    @classmethod
    def _one_line(cls, v):
        if any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


def _manage(user) -> None:
    if not has_any_permission(user, MANAGE):
        raise HTTPException(403, "Required permission is missing.")


def _fail(e: svc.SharedMailboxError) -> HTTPException:
    return HTTPException(e.status, str(e))


async def _admin_mailbox(db: AsyncSession, mailbox_id: uuid.UUID, user) -> SharedMailbox:
    _manage(user)
    mb = await db.get(SharedMailbox, mailbox_id)
    if mb is None:
        raise HTTPException(404, "Mailbox not found")
    return mb


@router.get("")
async def list_mailboxes(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Mailboxes you are a member of (the mailbox selector). Managers also see the ones they administer, without access."""
    members = {m.mailbox_id: m for m in (await db.execute(select(SharedMailboxMember).where(
        SharedMailboxMember.user_id == current_user.id, SharedMailboxMember.revoked_at.is_(None)))).scalars()}
    q = select(SharedMailbox).order_by(SharedMailbox.address)
    if not has_any_permission(current_user, MANAGE):
        q = q.where(SharedMailbox.id.in_(list(members) or [uuid.uuid4()]), SharedMailbox.status != "REVOKED")
    return [{**svc.view(mb, members.get(mb.id)), "member": mb.id in members}
            for mb in (await db.execute(q)).scalars().all()]


@router.post("", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _manage(current_user)
    try:
        mb = await svc.register(db, current_user, provider=body.provider, address=str(body.address),
                                display_name=body.display_name, kind=body.kind)
    except svc.SharedMailboxError as e:
        raise _fail(e)
    await db.commit()
    return svc.view(mb)


@router.get("/{mailbox_id}/members")
async def members(mailbox_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _admin_mailbox(db, mailbox_id, current_user)
    from app.models.user import User
    rows = (await db.execute(select(SharedMailboxMember, User).join(User, User.id == SharedMailboxMember.user_id).where(
        SharedMailboxMember.mailbox_id == mailbox_id).order_by(User.email))).all()
    return [{"user_id": str(m.user_id), "email": u.email, "name": u.full_name, "can_send": m.can_send, "send_mode": m.send_mode,
             "active": m.revoked_at is None, "granted_at": m.granted_at.isoformat() if m.granted_at else None,
             "revoked_at": m.revoked_at.isoformat() if m.revoked_at else None} for m, u in rows]


@router.put("/{mailbox_id}/members")
async def grant(mailbox_id: uuid.UUID, body: MemberIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    mb = await _admin_mailbox(db, mailbox_id, current_user)
    try:
        row = await svc.grant(db, current_user, mb, body.user_id, can_send=body.can_send, send_mode=body.send_mode)
    except svc.SharedMailboxError as e:
        raise _fail(e)
    await db.commit()
    return {"user_id": str(row.user_id), "can_send": row.can_send, "send_mode": row.send_mode}


@router.delete("/{mailbox_id}/members/{user_id}", status_code=204)
async def revoke_member(mailbox_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    mb = await _admin_mailbox(db, mailbox_id, current_user)
    try:
        await svc.revoke_member(db, current_user, mb, user_id)
    except svc.SharedMailboxError as e:
        raise _fail(e)
    await db.commit()


@router.post("/{mailbox_id}/revoke")
async def revoke_mailbox(mailbox_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    mb = await _admin_mailbox(db, mailbox_id, current_user)
    await svc.revoke_mailbox(db, current_user, mb)
    await db.commit()
    return svc.view(mb)


@router.post("/{mailbox_id}/sync")
async def sync(mailbox_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        mb, _ = await svc.require_access(db, current_user, mailbox_id)
        res = await svc.sync(db, mb, current_user)
    except svc.SharedMailboxError as e:
        await db.commit()                                  # keep ACCESS_LOST / last_error
        raise _fail(e)
    await db.commit()
    return res


@router.get("/{mailbox_id}/threads", response_model=List[EmailThreadRead])
async def threads(mailbox_id: uuid.UUID, q: Optional[str] = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200),
                  db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        mb, _ = await svc.require_access(db, current_user, mailbox_id)
    except svc.SharedMailboxError as e:
        raise _fail(e)
    stmt = select(EmailThread).options(selectinload(EmailThread.messages)).where(EmailThread.account_id == mb.account_id)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(EmailThread.subject.ilike(like), EmailThread.snippet.ilike(like)))
    rows = (await db.execute(stmt.order_by(EmailThread.last_message_at.desc().nullslast()).limit(limit))).scalars().all()
    return rows


@router.get("/{mailbox_id}/threads/{thread_id}", response_model=EmailThreadRead)
async def thread(mailbox_id: uuid.UUID, thread_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    try:
        mb, _ = await svc.require_access(db, current_user, mailbox_id)
    except svc.SharedMailboxError as e:
        raise _fail(e)
    t = (await db.execute(select(EmailThread).options(selectinload(EmailThread.messages)).where(
        EmailThread.id == thread_id, EmailThread.account_id == mb.account_id))).scalar_one_or_none()
    if t is None:
        raise HTTPException(404, "Thread not found")
    return t


@router.post("/{mailbox_id}/send", status_code=201, response_model=EmailThreadRead)
async def send(mailbox_id: uuid.UUID, body: SendIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Send (or reply, with reply_to_thread_id) as the shared mailbox, with your own provider sign-in."""
    try:
        t = await svc.send(db, current_user, mailbox_id, to=[str(x) for x in body.to_emails], cc=[str(x) for x in body.cc_emails],
                           subject=body.subject, body=body.body_text, thread_id=body.reply_to_thread_id)
    except svc.SharedMailboxError as e:
        await db.rollback()
        raise _fail(e)
    await db.commit()
    t = (await db.execute(select(EmailThread).options(selectinload(EmailThread.messages)).where(EmailThread.id == t.id))).scalar_one()
    return t
