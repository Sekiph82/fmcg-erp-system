"""Contact-center API (M49.S01.T004). Mounted by voip.py under /calls/cc.

Public route: POST /calls/cc/twilio/webhook (Twilio voice webhooks) - X-Twilio-Signature (HMAC-SHA1 over the configured
public URL + sorted form params, constant-time compare) is mandatory; no token configured or a bad signature -> 403.
Everything else needs a signed-in user; queue/IVR configuration needs CRM edit-all rights.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.m49_voice import (VoiceCallback, VoiceCallDisposition, VoicePresence, VoiceQueue, VoiceQueueEntry,
                                  VoiceTransfer, VoiceVoicemail)
from app.models.voip import CallLog, VoiceAgentProfile
from app.services import contact_center_service as cc
from app.services import voice_carrier as vc
from app.services import voice_service as voice

router = APIRouter()
VIEW_ALL = ("crm.view_all", "sales.view_all")
EDIT_ALL = ("crm.edit_all", "sales.edit_all")
PHONE = r"^\+?[0-9][0-9 ()-]{5,30}$"
STEPS = {"voice", "status", "consent", "menu", "queue_poll", "dial_result", "voicemail_done", "recording",
         "consult_twiml", "consult_accept"}


def _manager(u) -> bool:
    return bool(getattr(u, "is_superuser", False)) or has_any_permission(u, EDIT_ALL)


def _viewer(u) -> bool:
    return bool(getattr(u, "is_superuser", False)) or has_any_permission(u, VIEW_ALL)


def _audit(db: AsyncSession, user, event: str, target_type: str, target_id, name: str = "") -> None:
    db.add(AuditLog(actor_id=user.id, event_type=f"VOICE_{event}", module="voip", target_type=target_type,
                    target_id=str(target_id), target_name=name[:200]))


def _fail(e: cc.CCError):
    return HTTPException(e.status_code, str(e))


async def _my_call(db: AsyncSession, call_id: uuid.UUID, user) -> CallLog:
    call = await db.get(CallLog, call_id)
    if call is None or not (_manager(user) or call.agent_id == user.id):
        raise HTTPException(404, "Call log not found")
    return call


# ── public carrier webhook ────────────────────────────────────────────────────

@router.post("/twilio/webhook")
async def twilio_webhook(request: Request, step: str = Query("voice", max_length=20), ref: str = Query("", max_length=100),
                         queue: str = Query("", max_length=40), transfer: str = Query("", max_length=40),
                         db: AsyncSession = Depends(get_db)):
    form = {k: str(v)[:500] for k, v in (await request.form()).items()}
    url = settings.PUBLIC_API_URL.rstrip("/") + request.url.path + (f"?{request.url.query}" if request.url.query else "")
    if not vc.twilio_signature_ok(url, form, request.headers.get("X-Twilio-Signature")):
        raise HTTPException(403, "Invalid signature.")
    if step not in STEPS:
        raise HTTPException(422, "Unknown step.")
    try:
        xml = await cc.handle_twilio(db, step, form, {"ref": ref, "queue": queue, "transfer": transfer})
    except (ValueError, KeyError):
        await db.rollback()
        raise HTTPException(422, "Malformed webhook.") from None
    await db.commit()
    return Response(xml, media_type="application/xml")


# ── capabilities and presence ─────────────────────────────────────────────────

@router.get("/capabilities")
async def capabilities(current_user=Depends(get_current_user)):
    return voice.capabilities()


class PresenceIn(BaseModel):
    status: Literal["AVAILABLE", "AWAY", "OFFLINE"]       # BUSY is set only by a routed call


@router.put("/presence")
async def my_presence(body: PresenceIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    cur = await db.get(VoicePresence, current_user.id)
    if cur is not None and cur.status == "BUSY":
        raise HTTPException(409, "You are on a call; finish it first.")
    if body.status == "AVAILABLE" and (prof := await db.get(VoiceAgentProfile, current_user.id)) is None or \
            body.status == "AVAILABLE" and not prof.phone_number:
        raise HTTPException(409, "Set your answering phone before going available.")
    p = await cc.set_presence(db, current_user.id, body.status)
    _audit(db, current_user, "PRESENCE", "voice_presence", current_user.id, body.status)
    await db.commit()
    return {"status": p.status, "since": p.status_since.isoformat()}


@router.get("/board")
async def board(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Queues with waiting counts and agents' presence. Without view-all rights only the caller's own row."""
    from app.models.user import User
    q = select(VoicePresence, User.full_name).join(User, User.id == VoicePresence.user_id)
    if not _viewer(current_user):
        q = q.where(VoicePresence.user_id == current_user.id)
    agents = [{"user_id": str(p.user_id), "name": n, "status": p.status, "since": p.status_since.isoformat(),
               "call_id": str(p.current_call_id) if p.current_call_id else None} for p, n in (await db.execute(q)).all()]
    queues = []
    for qu in (await db.execute(select(VoiceQueue).order_by(VoiceQueue.name))).scalars():
        waiting = (await db.execute(select(VoiceQueueEntry).where(VoiceQueueEntry.queue_id == qu.id,
                   VoiceQueueEntry.state == "WAITING"))).scalars().all()
        queues.append({**_queue_out(qu), "waiting": len(waiting),
                       "oldest_wait_seconds": int((cc.now() - min(e.enqueued_at for e in waiting)).total_seconds()) if waiting else 0})
    return {"agents": agents, "queues": queues}


# ── queues ────────────────────────────────────────────────────────────────────

class QueueIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    direction: Literal["INBOUND", "OUTBOUND"] = "INBOUND"
    strategy: Literal["LONGEST_IDLE", "RING_ALL"] = "LONGEST_IDLE"
    member_user_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    max_wait_seconds: int = Field(60, ge=0, le=600)
    overflow: Literal["CALLBACK", "VOICEMAIL"] = "CALLBACK"
    is_active: bool = True


def _queue_out(q: VoiceQueue) -> dict:
    return {"id": str(q.id), "name": q.name, "direction": q.direction, "strategy": q.strategy,
            "member_user_ids": q.member_user_ids, "max_wait_seconds": q.max_wait_seconds, "overflow": q.overflow,
            "is_active": q.is_active}


@router.get("/queues")
async def list_queues(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return [_queue_out(q) for q in (await db.execute(select(VoiceQueue).order_by(VoiceQueue.name))).scalars()]


@router.post("/queues", status_code=201)
async def create_queue(body: QueueIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not _manager(current_user):
        raise HTTPException(403, "Only CRM managers can change queues.")
    if body.overflow == "VOICEMAIL" and vc.matrix(voice.provider())["voicemail"][0] != vc.S:
        raise HTTPException(422, "Voicemail overflow is not available on the active carrier: " + str(vc.matrix(voice.provider())["voicemail"][1]))
    if (await db.execute(select(VoiceQueue).where(VoiceQueue.name == body.name))).scalar_one_or_none():
        raise HTTPException(409, "A queue with this name exists.")
    q = VoiceQueue(**{**body.model_dump(), "member_user_ids": [str(u) for u in body.member_user_ids]})
    db.add(q)
    await db.flush()
    _audit(db, current_user, "QUEUE_CREATE", "voice_queue", q.id, q.name)
    await db.commit()
    return _queue_out(q)


@router.put("/queues/{queue_id}")
async def update_queue(queue_id: uuid.UUID, body: QueueIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not _manager(current_user):
        raise HTTPException(403, "Only CRM managers can change queues.")
    q = await db.get(VoiceQueue, queue_id)
    if q is None:
        raise HTTPException(404, "Queue not found")
    for k, v in body.model_dump().items():
        setattr(q, k, [str(u) for u in v] if k == "member_user_ids" else v)
    _audit(db, current_user, "QUEUE_UPDATE", "voice_queue", q.id, q.name)
    await db.commit()
    return _queue_out(q)


class OutboundItems(BaseModel):
    phone_numbers: list[str] = Field(min_length=1, max_length=200)


@router.post("/queues/{queue_id}/entries", status_code=201)
async def add_outbound(queue_id: uuid.UUID, body: OutboundItems, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Managers load numbers into an OUTBOUND queue; agents pull them one by one."""
    import re
    if not _manager(current_user):
        raise HTTPException(403, "Only CRM managers can load outbound queues.")
    q = await db.get(VoiceQueue, queue_id)
    if q is None or q.direction != "OUTBOUND":
        raise HTTPException(404, "Outbound queue not found")
    nums = []
    for n in body.phone_numbers:
        if not re.match(PHONE, n):
            raise HTTPException(422, f"Invalid phone number: {n[:30]}")
        d = cc.digits(n)
        if d not in nums:
            nums.append(d)
    for n in nums:
        db.add(VoiceQueueEntry(queue_id=q.id, phone_number=n, state="WAITING", enqueued_at=cc.now()))
    _audit(db, current_user, "OUTBOUND_LOAD", "voice_queue", q.id, f"{len(nums)} numbers")
    await db.commit()
    return {"added": len(nums)}


@router.post("/queues/{queue_id}/next")
async def next_outbound(queue_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = await db.get(VoiceQueue, queue_id)
    if q is None or q.direction != "OUTBOUND" or str(current_user.id) not in [str(u) for u in q.member_user_ids or []]:
        raise HTTPException(404, "Outbound queue not found")
    e = (await db.execute(select(VoiceQueueEntry).where(VoiceQueueEntry.queue_id == q.id, VoiceQueueEntry.state == "WAITING")
                          .order_by(VoiceQueueEntry.enqueued_at).limit(1).with_for_update(skip_locked=True))).scalar_one_or_none()
    if e is None:
        return {"call": None}
    call = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number=e.phone_number,
                   agent_id=current_user.id, started_at=datetime.utcnow(), outcome="DIALED", status="QUEUED")
    db.add(call)
    await db.flush()
    e.state, e.assigned_user_id, e.call_id, e.resolved_at = "ASSIGNED", current_user.id, call.id, cc.now()
    prof = await db.get(VoiceAgentProfile, current_user.id)
    if voice.provider() is not None and prof and prof.phone_number:
        try:
            await voice.place_call(db, call, prof.phone_number)
        except voice.VoiceError:
            pass                                                # call stays FAILED/UNKNOWN; the agent sees it in the log
    await db.commit()
    return {"call": {"id": str(call.id), "status": call.status, "dial": None if call.provider else "tel:" + call.phone_number}}


# ── callbacks ─────────────────────────────────────────────────────────────────

class CallbackIn(BaseModel):
    phone_number: str = Field(pattern=PHONE)
    queue_id: Optional[uuid.UUID] = None


class CallbackDone(BaseModel):
    outcome: Literal["ANSWERED", "NO_ANSWER", "BUSY"]


def _cb_out(c: VoiceCallback) -> dict:
    return {"id": str(c.id), "phone_number": c.phone_number, "state": c.state, "missed_count": c.missed_count,
            "attempts": c.attempts, "last_outcome": c.last_outcome, "queue_id": str(c.queue_id) if c.queue_id else None,
            "created_at": c.created_at.isoformat() if c.created_at else None}


@router.get("/callbacks")
async def list_callbacks(state: str = Query("PENDING", pattern="^(PENDING|DONE|EXPIRED|CANCELLED)$"),
                         db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(VoiceCallback).where(VoiceCallback.state == state)
                             .order_by(VoiceCallback.created_at).limit(200))).scalars()
    return [_cb_out(c) for c in rows]


@router.post("/callbacks", status_code=201)
async def add_callback(body: CallbackIn, response: Response, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        cb, created = await cc.request_callback(db, body.phone_number, body.queue_id, None)
    except cc.CCError as e:
        raise _fail(e) from None
    _audit(db, current_user, "CALLBACK_REQUEST", "voice_callback", cb.id, cb.phone_number)
    await db.commit()
    if not created:
        response.status_code = 200
    return {**_cb_out(cb), "duplicate": not created}


@router.post("/callbacks/{callback_id}/complete")
async def finish_callback(callback_id: uuid.UUID, body: CallbackDone, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    cb = await db.get(VoiceCallback, callback_id, with_for_update=True)
    if cb is None:
        raise HTTPException(404, "Callback not found")
    try:
        await cc.complete_callback(db, cb, body.outcome, current_user.id)
    except cc.CCError as e:
        raise _fail(e) from None
    _audit(db, current_user, "CALLBACK_" + body.outcome, "voice_callback", cb.id, cb.phone_number)
    await db.commit()
    return _cb_out(cb)


# ── transfer, disposition, verification, voicemail, retention ─────────────────

class TransferIn(BaseModel):
    kind: Literal["COLD", "WARM"]
    to_user_id: Optional[uuid.UUID] = None
    to_number: Optional[str] = Field(None, pattern=PHONE)


def _t_out(t: VoiceTransfer) -> dict:
    return {"id": str(t.id), "call_id": str(t.call_id), "kind": t.kind, "state": t.state, "to_number": t.to_number, "error": t.error}


@router.post("/calls/{call_id}/transfer", status_code=201)
async def transfer(call_id: uuid.UUID, body: TransferIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    call = await _my_call(db, call_id, current_user)
    try:
        t = await cc.start_transfer(db, call, body.kind, current_user, body.to_user_id, body.to_number)
    except cc.CCError as e:
        raise _fail(e) from None
    _audit(db, current_user, f"TRANSFER_{body.kind}", "voice_transfer", t.id, t.state)
    await db.commit()
    return _t_out(t)


@router.post("/transfers/{transfer_id}/complete")
async def complete_transfer(transfer_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    t = await db.get(VoiceTransfer, transfer_id, with_for_update=True)
    if t is None:
        raise HTTPException(404, "Transfer not found")
    call = await _my_call(db, t.call_id, current_user)
    try:
        await cc.complete_warm_transfer(db, call, t)
    except cc.CCError as e:
        raise _fail(e) from None
    _audit(db, current_user, "TRANSFER_COMPLETE", "voice_transfer", t.id, t.state)
    await db.commit()
    return _t_out(t)


@router.get("/calls/{call_id}/transfers")
async def call_transfers(call_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _my_call(db, call_id, current_user)
    return [_t_out(t) for t in (await db.execute(select(VoiceTransfer).where(VoiceTransfer.call_id == call_id)
                                                 .order_by(VoiceTransfer.created_at))).scalars()]


class DispositionIn(BaseModel):
    code: Literal["SALE", "QUOTE_REQUESTED", "COMPLAINT", "WRONG_NUMBER", "NO_INTEREST", "CALLBACK_REQUESTED", "ESCALATED"]
    note: Optional[str] = Field(None, max_length=500)


@router.put("/calls/{call_id}/disposition")
async def set_disposition(call_id: uuid.UUID, body: DispositionIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    call = await _my_call(db, call_id, current_user)
    d = await db.get(VoiceCallDisposition, call.id) or VoiceCallDisposition(call_id=call.id)
    d.code, d.note, d.set_by, d.set_at = body.code, body.note, current_user.id, cc.now()
    db.add(d)
    if body.code == "CALLBACK_REQUESTED":
        await cc.request_callback(db, call.phone_number, None, call.id)
    _audit(db, current_user, "DISPOSITION", "call_log", call.id, body.code)
    await db.commit()
    return {"call_id": str(call.id), "code": d.code, "note": d.note}


@router.post("/calls/{call_id}/verify-status")
async def verify_status(call_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Ask the carrier for the real state of a call whose webhooks never arrived (or whose outcome was unknown)."""
    call = await _my_call(db, call_id, current_user)
    try:
        await cc.verify_status(db, call)
    except cc.CCError as e:
        raise _fail(e) from None
    await db.commit()
    return {"id": str(call.id), "status": call.status, "outcome": call.outcome}


@router.get("/voicemails")
async def voicemails(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not _viewer(current_user):
        raise HTTPException(403, "Managers only.")
    rows = (await db.execute(select(VoiceVoicemail).where(VoiceVoicemail.expires_at > cc.now())
                             .order_by(VoiceVoicemail.created_at.desc()).limit(100))).scalars()
    return [{"id": str(v.id), "phone_number": v.phone_number, "duration_seconds": v.duration_seconds,
             "recording_url": v.recording_url, "created_at": v.created_at.isoformat(), "expires_at": v.expires_at.isoformat()} for v in rows]


@router.post("/retention/purge")
async def purge(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not _manager(current_user):
        raise HTTPException(403, "Only CRM managers can run retention.")
    res = await cc.purge_expired(db)
    _audit(db, current_user, "RETENTION_PURGE", "voice", "retention", str(res))
    await db.commit()
    return res
