"""VoIP / Call Center endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.voip import CallLog, CallScript

router = APIRouter()


# M36.S04.T002: validated input; own calls unless broad rights; recording only with consent, kept for
# CALL_RECORDING_RETENTION_DAYS; transcripts only where CALL_TRANSCRIPTION_ENABLED; click-to-call works
# without a telephony provider (the phone dials a tel: link and the call is logged).
from datetime import timedelta, timezone  # noqa: E402
from typing import Literal  # noqa: E402

from pydantic import BaseModel, Field  # noqa: E402

from app.core.access_control import has_any_permission  # noqa: E402
from app.core.config import settings  # noqa: E402

Outcome = Literal["DIALED", "ANSWERED", "NO_ANSWER", "BUSY", "VOICEMAIL", "FAILED"]
VIEW_ALL = ("crm.view_all", "sales.view_all")
EDIT_ALL = ("crm.edit_all", "sales.edit_all")
PHONE = r"^\+?[0-9][0-9 ()-]{5,30}$"
FOLLOW_UP_OUTCOMES = ("NO_ANSWER", "BUSY", "VOICEMAIL", "FAILED")


def _recording_ok(c: CallLog) -> bool:
    exp = c.recording_expires_at
    return bool(c.recording_url and c.recording_consent and (exp is None or exp > datetime.now(timezone.utc)))


def _call_row(c: CallLog) -> dict:
    return {
        "id": str(c.id),
        "call_ref": c.call_ref,
        "direction": c.direction,
        "phone_number": c.phone_number,
        "customer_id": str(c.customer_id) if c.customer_id else None,
        "customer_name": c.customer.name if c.customer else None,
        "agent_id": str(c.agent_id) if c.agent_id else None,
        "agent_name": c.agent.full_name if c.agent else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_seconds": c.duration_seconds,
        "outcome": c.outcome,
        "notes": c.notes,
        # recordings without consent on file, or past retention, are never handed out
        "recording_url": c.recording_url if _recording_ok(c) else None,
        "recording_consent": c.recording_consent,
        "recording_expires_at": c.recording_expires_at.isoformat() if c.recording_expires_at else None,
        "has_transcript": bool(c.transcript),
        "follow_up_required": c.follow_up_required,
        "follow_up_date": c.follow_up_date.isoformat() if c.follow_up_date else None,
        "tags": c.tags,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _scope(q, user):
    if getattr(user, "is_superuser", False) or has_any_permission(user, VIEW_ALL):
        return q
    return q.where(CallLog.agent_id == user.id)


async def _my_call(db: AsyncSession, call_id: uuid.UUID, user) -> CallLog:
    q = _scope(select(CallLog).options(selectinload(CallLog.customer), selectinload(CallLog.agent))
               .where(CallLog.id == call_id), user)
    call = (await db.execute(q)).scalar_one_or_none()
    if call is None:
        raise HTTPException(404, "Call log not found")
    if not (getattr(user, "is_superuser", False) or call.agent_id == user.id or has_any_permission(user, EDIT_ALL)):
        raise HTTPException(403, "Only the caller can change this call.")
    return call


class CallIn(BaseModel):
    phone_number: str = Field(pattern=PHONE)
    direction: Literal["OUTBOUND", "INBOUND"] = "OUTBOUND"
    customer_id: Optional[uuid.UUID] = None
    crm_record_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0, le=24 * 3600)
    outcome: Outcome = "ANSWERED"
    notes: Optional[str] = Field(None, max_length=5000)
    recording_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    recording_consent: bool = False
    consent_note: Optional[str] = Field(None, max_length=300)
    call_script_id: Optional[uuid.UUID] = None
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    tags: Optional[str] = Field(None, max_length=300)


class CallPatch(BaseModel):
    outcome: Optional[Outcome] = None
    notes: Optional[str] = Field(None, max_length=5000)
    duration_seconds: Optional[int] = Field(None, ge=0, le=24 * 3600)
    ended_at: Optional[datetime] = None
    recording_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    recording_consent: Optional[bool] = None
    consent_note: Optional[str] = Field(None, max_length=300)
    transcript: Optional[str] = Field(None, max_length=100000)
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    tags: Optional[str] = Field(None, max_length=300)


def _naive(v: Optional[datetime]) -> Optional[datetime]:
    return v.astimezone(timezone.utc).replace(tzinfo=None) if v and v.tzinfo else v


def _apply_recording(call: CallLog, url: Optional[str], consent: Optional[bool], note: Optional[str]) -> None:
    if consent is not None:
        call.recording_consent = consent
    if note is not None:
        call.consent_note = note
    if url is not None:
        if not call.recording_consent:
            raise HTTPException(422, "A recording can be attached only when the other party agreed to be recorded.")
        if url != call.recording_url:  # re-sending the same link never extends retention
            call.recording_url = url
            call.recording_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.CALL_RECORDING_RETENTION_DAYS)
    if consent is False:  # consent withdrawn: the recording and its transcript go
        call.recording_url, call.recording_expires_at, call.transcript = None, None, None


# ── Call Logs ──────────────────────────────────────────────────

@router.get("/logs", response_model=list)
async def list_calls(
    customer_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = _scope(select(CallLog).options(selectinload(CallLog.customer), selectinload(CallLog.agent)), current_user)
    if customer_id:
        q = q.where(CallLog.customer_id == customer_id)
    if agent_id:
        q = q.where(CallLog.agent_id == agent_id)
    if direction:
        q = q.where(CallLog.direction == direction)
    if outcome:
        q = q.where(CallLog.outcome == outcome)
    r = await db.execute(q.order_by(CallLog.created_at.desc()).limit(limit))
    return [_call_row(c) for c in r.scalars()]


async def _check_refs(db: AsyncSession, body: CallIn) -> None:
    from app.models.sales import Customer
    if body.customer_id and await db.get(Customer, body.customer_id) is None:
        raise HTTPException(422, "Unknown customer.")
    if body.call_script_id and await db.get(CallScript, body.call_script_id) is None:
        raise HTTPException(422, "Unknown call script.")


@router.post("/logs", status_code=201)
async def create_call_log(body: CallIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _check_refs(db, body)
    started = _naive(body.started_at) or datetime.utcnow()
    ended = _naive(body.ended_at)
    call = CallLog(
        call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction=body.direction, phone_number=body.phone_number,
        customer_id=body.customer_id, crm_record_id=body.crm_record_id, agent_id=current_user.id,
        started_at=started, ended_at=ended,
        duration_seconds=body.duration_seconds if body.duration_seconds is not None else (max(0, int((ended - started).total_seconds())) if ended else None),
        outcome=body.outcome, notes=body.notes, call_script_id=body.call_script_id,
        follow_up_required=body.follow_up_required or body.outcome in FOLLOW_UP_OUTCOMES,
        follow_up_date=_naive(body.follow_up_date), tags=body.tags,
    )
    _apply_recording(call, body.recording_url, body.recording_consent, body.consent_note)
    db.add(call)
    await db.commit()
    return {"id": str(call.id), "call_ref": call.call_ref}


@router.post("/click-to-call", status_code=201)
async def click_to_call(body: CallIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Start a call: with no telephony provider connected the phone dials the returned tel: link and the
    call is logged as DIALED (update its outcome afterwards). A provider (e.g. Africa's Talking Voice)
    would place the call server-side instead: live provider gate."""
    await _check_refs(db, body)
    call = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number=body.phone_number,
                   customer_id=body.customer_id, crm_record_id=body.crm_record_id, agent_id=current_user.id,
                   started_at=datetime.utcnow(), outcome="DIALED", follow_up_required=False)
    db.add(call)
    await db.commit()
    dial = "".join(ch for ch in body.phone_number if ch.isdigit() or ch == "+")
    return {"id": str(call.id), "call_ref": call.call_ref, "dial": f"tel:{dial}", "provider": None}


@router.patch("/logs/{call_id}")
async def update_call_log(call_id: uuid.UUID, body: CallPatch, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    call = await _my_call(db, call_id, current_user)
    data = body.model_dump(exclude_unset=True)
    if "transcript" in data and data["transcript"] is not None:
        if not settings.CALL_TRANSCRIPTION_ENABLED:
            raise HTTPException(409, "Call transcription is not enabled for this company.")
        if not call.recording_consent or not _recording_ok(call):
            raise HTTPException(422, "A transcript needs a consented recording that is still within retention.")
        call.transcript = data["transcript"]
    for k in ("outcome", "notes", "duration_seconds", "follow_up_required", "tags"):
        if k in data and data[k] is not None:
            setattr(call, k, data[k])
    if data.get("outcome") in FOLLOW_UP_OUTCOMES:  # failed calls always come back for follow-up
        call.follow_up_required = True
    if "follow_up_date" in data:
        call.follow_up_date = _naive(data["follow_up_date"])
    _apply_recording(call, data.get("recording_url"), data.get("recording_consent"), data.get("consent_note"))
    if data.get("ended_at"):
        call.ended_at = _naive(data["ended_at"])
        if call.started_at:
            call.duration_seconds = max(0, int((call.ended_at - call.started_at).total_seconds()))
    await db.commit()
    return {"id": str(call.id), "outcome": call.outcome}


async def purge_expired_recordings(db: AsyncSession) -> int:
    """Drop recording links and transcripts past their retention date (calls themselves stay). Caller commits."""
    from sqlalchemy import update
    from sqlalchemy import or_
    res = await db.execute(update(CallLog).where(or_(
        CallLog.recording_expires_at < datetime.now(timezone.utc),
        (CallLog.recording_consent.is_(False)) & (CallLog.recording_url.isnot(None)),  # legacy, no consent on file
    )).values(recording_url=None, transcript=None, recording_expires_at=None))
    return res.rowcount or 0


# ── Call Scripts ──────────────────────────────────────────────────────────────

@router.get("/scripts", response_model=list)
async def list_scripts(
    purpose: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CallScript).where(CallScript.is_active == True)
    if purpose:
        q = q.where(CallScript.purpose == purpose)
    r = await db.execute(q.order_by(CallScript.title))
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "purpose": s.purpose,
            "script_text": s.script_text,
            "talking_points": s.talking_points,
            "objection_handlers": s.objection_handlers,
        }
        for s in r.scalars()
    ]


@router.post("/scripts", status_code=201)
async def create_script(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    script = CallScript(
        title=body["title"],
        purpose=body.get("purpose", "sales"),
        script_text=body["script_text"],
        talking_points=body.get("talking_points"),
        objection_handlers=body.get("objection_handlers"),
        created_by_id=current_user.id,
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return {"id": str(script.id), "title": script.title}


# ── Dashboard / Stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def call_stats(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Totals over the calls the user may see (own calls, or all with broad rights)."""
    base = _scope(select(CallLog.id), current_user).subquery()
    mine = CallLog.id.in_(select(base.c.id))
    total = (await db.execute(select(func.count()).select_from(CallLog).where(mine))).scalar_one()
    answered = (await db.execute(select(func.count()).select_from(CallLog).where(mine, CallLog.outcome == "ANSWERED"))).scalar_one()
    followups = (await db.execute(select(func.count()).select_from(CallLog).where(mine, CallLog.follow_up_required.is_(True)))).scalar_one()
    avg = (await db.execute(select(func.avg(CallLog.duration_seconds)).where(mine, CallLog.duration_seconds.isnot(None)))).scalar_one()
    by_outcome = {str(o): n for o, n in (await db.execute(select(CallLog.outcome, func.count()).where(mine).group_by(CallLog.outcome))).all()}
    return {"total_calls": total, "answered_calls": answered, "answer_rate": round(answered / total * 100, 1) if total else 0,
            "follow_ups_pending": followups, "avg_duration_seconds": round(avg or 0), "by_outcome": by_outcome}
