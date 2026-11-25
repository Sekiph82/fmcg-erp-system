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
        "status": c.status, "provider": c.provider,
        "transcription_status": c.transcription_status, "transcription_error": c.transcription_error,
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
    """Start a call. With a voice provider configured (M43.S01.T008) and your answering phone set, the provider
    rings you first and then connects the customer (recorded only with consent). Otherwise the phone dials the
    returned tel: link and the call is logged as DIALED (update its outcome afterwards)."""
    from app.models.voip import VoiceAgentProfile
    from app.services import voice_service as voice

    await _check_refs(db, body)
    call = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number=body.phone_number,
                   customer_id=body.customer_id, crm_record_id=body.crm_record_id, agent_id=current_user.id,
                   started_at=datetime.utcnow(), outcome="DIALED", follow_up_required=False,
                   recording_consent=bool(body.recording_consent), consent_note=body.consent_note)
    db.add(call)
    await db.flush()
    profile = await db.get(VoiceAgentProfile, current_user.id)
    if voice.provider() and profile is not None:
        try:
            await voice.place_call(db, call, profile.phone_number)
        except voice.VoiceError as e:
            await db.commit()
            raise HTTPException(e.status_code, str(e)) from None
        await db.commit()
        return {"id": str(call.id), "call_ref": call.call_ref, "dial": None, "provider": call.provider,
                "status": call.status, "message": "Your phone will ring; answer it to be connected."}
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



# ── M43.S01.T008 provider voice: capabilities, agent phone, provider callback, IVR, power dialer ───────────

from fastapi import Request  # noqa: E402
from fastapi.responses import Response  # noqa: E402

from app.models.voip import DialerSession, VoiceAgentProfile, VoiceIvrMenu  # noqa: E402
from app.services import transcription_service as transcription  # noqa: E402
from app.services import voice_service as voice  # noqa: E402


@router.get("/capabilities")
async def voice_capabilities(current_user=Depends(get_current_user)):
    return {**voice.capabilities(), "transcription_engine": transcription.adapter() or "NOT_AVAILABLE"}


class AgentPhoneIn(BaseModel):
    phone_number: str = Field(pattern=PHONE)
    available: bool = True


@router.get("/me/phone")
async def my_phone(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    p = await db.get(VoiceAgentProfile, current_user.id)
    return {"phone_number": p.phone_number if p else None, "available": p.available if p else False}


@router.put("/me/phone")
async def set_my_phone(body: AgentPhoneIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    p = await db.get(VoiceAgentProfile, current_user.id) or VoiceAgentProfile(user_id=current_user.id, phone_number="")
    p.phone_number, p.available = body.phone_number, body.available
    db.add(p)
    await db.commit()
    return {"phone_number": p.phone_number, "available": p.available}


@router.post("/provider/callback")
async def provider_callback(request: Request, token: str = Query("", max_length=200), db: AsyncSession = Depends(get_db)):
    """Africa's Talking Voice callback (public; the secret token in the URL is the credential)."""
    if not voice.callback_ok(token):
        raise HTTPException(403, "Invalid callback token.")
    form = {k: str(v)[:500] for k, v in (await request.form()).items()}
    xml = await voice.handle_callback(db, form)
    await db.commit()
    return Response(xml, media_type="application/xml")


class IvrOption(BaseModel):
    digit: str = Field(pattern=r"^[0-9]$")
    label: str = Field(min_length=1, max_length=60)
    user_ids: list[uuid.UUID] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)


class IvrIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone_number: str = Field(pattern=PHONE)
    greeting_text: str = Field(min_length=1, max_length=500)
    options: list[IvrOption] = Field(min_length=1, max_length=9)
    record_calls: bool = False
    consent_text: Optional[str] = Field(None, max_length=300)
    is_active: bool = True


def _ivr_out(m: VoiceIvrMenu) -> dict:
    return {"id": str(m.id), "name": m.name, "phone_number": m.phone_number, "greeting_text": m.greeting_text,
            "options": m.options, "record_calls": m.record_calls, "consent_text": m.consent_text, "is_active": m.is_active}


@router.get("/ivr")
async def list_ivr(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return [_ivr_out(m) for m in (await db.execute(select(VoiceIvrMenu).order_by(VoiceIvrMenu.name))).scalars()]


@router.post("/ivr", status_code=201)
async def save_ivr(body: IvrIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, EDIT_ALL)):
        raise HTTPException(403, "Only CRM managers can change phone menus.")
    if body.record_calls and not body.consent_text:
        raise HTTPException(422, "Recording callers needs a consent announcement.")
    if len({o.digit for o in body.options}) != len(body.options):
        raise HTTPException(422, "Each digit can be used once.")
    phone = "".join(ch for ch in body.phone_number if ch.isdigit() or ch == "+")
    m = (await db.execute(select(VoiceIvrMenu).where(VoiceIvrMenu.phone_number == phone))).scalar_one_or_none() \
        or VoiceIvrMenu(phone_number=phone)
    m.name, m.greeting_text, m.record_calls, m.consent_text, m.is_active = (
        body.name, body.greeting_text, body.record_calls, body.consent_text, body.is_active)
    m.options = [{**o.model_dump(), "user_ids": [str(u) for u in o.user_ids]} for o in body.options]
    db.add(m)
    await db.commit()
    return _ivr_out(m)


class DialerItem(BaseModel):
    phone: str = Field(pattern=PHONE)
    label: Optional[str] = Field(None, max_length=200)
    crm_record_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None


class DialerIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    items: list[DialerItem] = Field(min_length=1, max_length=500)


def _ds_out(ds: DialerSession) -> dict:
    return {"id": str(ds.id), "name": ds.name, "status": ds.status, "items": ds.items, "current_index": ds.current_index}


async def _my_session(db, session_id, user) -> DialerSession:
    ds = await db.get(DialerSession, session_id)
    if ds is None or ds.agent_id != user.id:
        raise HTTPException(404, "Dialer session not found")
    return ds


@router.post("/dialer", status_code=201)
async def create_dialer(body: DialerIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    seen, items = set(), []
    for it in body.items:
        phone = "".join(ch for ch in it.phone if ch.isdigit() or ch == "+")
        if phone in seen:
            continue
        seen.add(phone)
        items.append({"phone": phone, "label": it.label, "state": "PENDING", "call_id": None,
                      "crm_record_id": str(it.crm_record_id) if it.crm_record_id else None,
                      "customer_id": str(it.customer_id) if it.customer_id else None})
    ds = DialerSession(agent_id=current_user.id, name=body.name, status="ACTIVE", items=items)
    db.add(ds)
    await db.commit()
    return _ds_out(ds)


@router.get("/dialer")
async def my_dialers(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(DialerSession).where(DialerSession.agent_id == current_user.id)
                             .order_by(DialerSession.created_at.desc()).limit(50))).scalars()
    return [_ds_out(d) for d in rows]


@router.post("/dialer/{session_id}/next")
async def dialer_next(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Call the next number. The previous call must have an outcome first (one call at a time)."""
    ds = await _my_session(db, session_id, current_user)
    if any(it.get("state") == "CALLING" for it in ds.items or []):
        raise HTTPException(409, "Finish the current call (set its outcome) before the next one.")
    profile = await db.get(VoiceAgentProfile, current_user.id)
    call = await voice.start_next(db, ds, profile.phone_number if profile else None)
    await db.commit()
    if call is None:
        return {**_ds_out(ds), "call": None}
    dial = None if call.provider else "tel:" + call.phone_number
    return {**_ds_out(ds), "call": {"id": str(call.id), "status": call.status, "dial": dial}}


@router.post("/dialer/{session_id}/outcome")
async def dialer_outcome(session_id: uuid.UUID, outcome: Outcome = Query(...), db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    """Without a provider the rep records the result of the tel: call here; it also frees the queue."""
    ds = await _my_session(db, session_id, current_user)
    items = list(ds.items or [])
    cur = next((it for it in items if it.get("state") == "CALLING"), None)
    if cur is None:
        raise HTTPException(409, "No call in progress.")
    call = await db.get(CallLog, uuid.UUID(cur["call_id"]))
    if call is not None and call.status not in voice.FINAL:
        call.outcome, call.status = outcome, {"ANSWERED": "COMPLETED"}.get(outcome, outcome if outcome in voice.FINAL else "COMPLETED")
        call.follow_up_required = outcome in FOLLOW_UP_OUTCOMES
        call.ended_at = datetime.utcnow()
    cur["state"] = "DONE" if outcome == "ANSWERED" else outcome
    ds.items = items
    await db.commit()
    return _ds_out(ds)


@router.post("/dialer/{session_id}/pause")
async def dialer_pause(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    ds = await _my_session(db, session_id, current_user)
    ds.status = "PAUSED" if ds.status == "ACTIVE" else ("ACTIVE" if ds.status == "PAUSED" else ds.status)
    await db.commit()
    return _ds_out(ds)


# ── M43.S01.T009 transcription and coaching ───────────────────────────────────

@router.post("/logs/{call_id}/transcribe")
async def transcribe(call_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    call = await _my_call(db, call_id, current_user)
    try:
        await transcription.request(db, call)
    except transcription.TranscriptionError as e:
        raise HTTPException(e.status_code, str(e)) from None
    await db.commit()
    return {"id": str(call.id), "transcription_status": call.transcription_status}


@router.post("/logs/{call_id}/withdraw-consent")
async def withdraw_consent(call_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """The customer withdrew recording consent: recording, transcript and coaching quotes are deleted now."""
    call = await _my_call(db, call_id, current_user)
    await transcription.withdraw_consent(db, call)
    await db.commit()
    return {"id": str(call.id), "recording_consent": False}


@router.get("/logs/{call_id}/transcript")
async def call_transcript(call_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.crm import CRMConversationInsight
    q = _scope(select(CallLog).where(CallLog.id == call_id), current_user)
    call = (await db.execute(q)).scalar_one_or_none()
    if call is None:
        raise HTTPException(404, "Call log not found")
    if not _recording_ok(call):
        return {"status": call.transcription_status, "segments": [], "recap": None}
    ins = (await db.execute(select(CRMConversationInsight).where(CRMConversationInsight.source_type == "call",
           CRMConversationInsight.source_id == call.id).order_by(CRMConversationInsight.analysed_at.desc()).limit(1))).scalar_one_or_none()
    return {"status": call.transcription_status, "language": call.transcript_language,
            "segments": call.transcript_segments or ([{"start": None, "end": None, "speaker": None, "text": call.transcript}]
                                                     if call.transcript else []),
            "recap": transcription.recap(ins.findings) if ins else None}
