"""Contact center: queues, agent presence, callbacks, transfers, consent and the Twilio webhook (M49.S01.T004).

Routing is ERP-side and provider independent: ``decide`` picks an available agent of a queue (presence AVAILABLE, a phone
on file), marks the agent BUSY under a row lock so two simultaneous calls never ring the same person, or reports HOLD
(carrier can poll) / OVERFLOW (voicemail, or a callback request). A missed or overflowed inbound call creates at most ONE
open callback per phone number (partial unique index + savepoint), a repeat only raises ``missed_count``.
Recording needs spoken consent: the IVR asks "press 1 to agree"; any other key means no recording, and a recording URL
that still arrives for that call is ignored. Retention follows CALL_RECORDING_RETENTION_DAYS.
Nothing here pretends a provider did something: transfer states move only from the carrier's documented answers.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m49_voice import (VoiceCallback, VoiceCallDisposition, VoicePresence, VoiceProviderEvent, VoiceQueue,
                                  VoiceQueueEntry, VoiceTransfer, VoiceVoicemail)
from app.models.voip import CallLog, VoiceAgentProfile, VoiceIvrMenu
from app.services import voice_carrier as vc

log = logging.getLogger(__name__)
PRESENCE = ("AVAILABLE", "BUSY", "AWAY", "OFFLINE")
DISPOSITIONS = ("SALE", "QUOTE_REQUESTED", "COMPLAINT", "WRONG_NUMBER", "NO_INTEREST", "CALLBACK_REQUESTED", "ESCALATED")
MAX_CALLBACK_ATTEMPTS = 3
TW_STATUS = {"completed": "COMPLETED", "busy": "BUSY", "no-answer": "NO_ANSWER", "failed": "FAILED", "canceled": "FAILED"}
TW_LIVE = {"queued": "QUEUED", "initiated": "QUEUED", "ringing": "RINGING", "in-progress": "ANSWERED"}
FINAL = ("COMPLETED", "NO_ANSWER", "BUSY", "FAILED")


class CCError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def now() -> datetime:
    return datetime.now(timezone.utc)


def digits(n: str) -> str:
    return "".join(ch for ch in (n or "") if ch.isdigit() or ch == "+")[:50]


# ── presence ──────────────────────────────────────────────────────────────────

async def set_presence(db: AsyncSession, user_id: uuid.UUID, status: str, call_id: Optional[uuid.UUID] = None) -> VoicePresence:
    if status not in PRESENCE:
        raise CCError("Unknown presence status.", 422)
    p = await db.get(VoicePresence, user_id, with_for_update=True)
    if p is None:
        p = VoicePresence(user_id=user_id, status=status, status_since=now())
        db.add(p)
    elif p.status != status:
        p.status, p.status_since = status, now()
    p.current_call_id = call_id if status == "BUSY" else None
    prof = await db.get(VoiceAgentProfile, user_id)
    if prof is not None:                                  # the legacy IVR picks agents by this flag
        prof.available = status == "AVAILABLE"
    await db.flush()
    return p


async def release_agent(db: AsyncSession, call: CallLog) -> None:
    """The call ended: free the agent that was held for it (only if still held for this call)."""
    rows = (await db.execute(select(VoicePresence).where(VoicePresence.current_call_id == call.id)
                             .with_for_update())).scalars().all()
    for p in rows:
        await set_presence(db, p.user_id, "AVAILABLE")


# ── routing ───────────────────────────────────────────────────────────────────

@dataclass
class Decision:
    kind: str                                   # DIAL | HOLD | VOICEMAIL | CALLBACK
    numbers: list[str] = field(default_factory=list)


async def _pick(db: AsyncSession, queue: VoiceQueue, call: CallLog) -> list[tuple[uuid.UUID, str]]:
    members = [uuid.UUID(str(u)) for u in queue.member_user_ids or []]
    if not members:
        return []
    rows = (await db.execute(
        select(VoicePresence, VoiceAgentProfile).join(VoiceAgentProfile, VoiceAgentProfile.user_id == VoicePresence.user_id)
        .where(VoicePresence.user_id.in_(members), VoicePresence.status == "AVAILABLE", VoiceAgentProfile.phone_number != "")
        .order_by(VoicePresence.status_since).with_for_update(of=VoicePresence, skip_locked=True))).all()
    if not rows:
        return []
    chosen = rows if queue.strategy == "RING_ALL" else rows[:1]
    for p, _ in chosen:
        if queue.strategy != "RING_ALL":
            await set_presence(db, p.user_id, "BUSY", call.id)
    return [(p.user_id, prof.phone_number) for p, prof in chosen]


async def decide(db: AsyncSession, call: CallLog, queue: VoiceQueue, *, can_hold: bool, can_voicemail: bool) -> Decision:
    entry = (await db.execute(select(VoiceQueueEntry).where(VoiceQueueEntry.call_id == call.id,
             VoiceQueueEntry.queue_id == queue.id).order_by(VoiceQueueEntry.enqueued_at.desc()).limit(1))).scalar_one_or_none()
    if entry is None:
        entry = VoiceQueueEntry(queue_id=queue.id, call_id=call.id, phone_number=call.phone_number, state="WAITING",
                                enqueued_at=now())
        db.add(entry)
    agents = await _pick(db, queue, call) if entry.state == "WAITING" else []
    if agents:
        entry.state, entry.assigned_user_id, entry.resolved_at = "ASSIGNED", agents[0][0], now()
        call.agent_id = agents[0][0]
        return Decision("DIAL", [p for _, p in agents])
    waited = (now() - entry.enqueued_at).total_seconds() if entry.enqueued_at else 0
    if entry.state == "WAITING" and can_hold and waited < queue.max_wait_seconds:
        return Decision("HOLD")
    entry.state, entry.resolved_at = "OVERFLOW", now()
    if queue.overflow == "VOICEMAIL" and can_voicemail:
        return Decision("VOICEMAIL")
    await request_callback(db, call.phone_number, queue.id, call.id)
    call.follow_up_required = True
    return Decision("CALLBACK")


# ── callbacks ─────────────────────────────────────────────────────────────────

async def request_callback(db: AsyncSession, phone: str, queue_id: Optional[uuid.UUID], call_id: Optional[uuid.UUID]) -> tuple[VoiceCallback, bool]:
    """Idempotent: one open callback per number. Returns (callback, created)."""
    phone = digits(phone)
    if not phone:
        raise CCError("A phone number is required.", 422)

    async def _open() -> Optional[VoiceCallback]:
        return (await db.execute(select(VoiceCallback).where(VoiceCallback.phone_number == phone,
                VoiceCallback.state == "PENDING").with_for_update())).scalar_one_or_none()

    cb = await _open()
    if cb is None:
        try:
            async with db.begin_nested():
                cb = VoiceCallback(phone_number=phone, queue_id=queue_id, source_call_id=call_id, state="PENDING")
                db.add(cb)
                await db.flush()
            return cb, True
        except IntegrityError:                          # a parallel request won the unique index
            cb = await _open()
            if cb is None:
                raise
    if call_id is None or cb.source_call_id != call_id:  # the same missed call re-sent does not count twice
        cb.missed_count += 1                             # ponytail: remembers only the latest call id, so an old replay recounts
        cb.source_call_id = call_id or cb.source_call_id
    return cb, False


async def complete_callback(db: AsyncSession, cb: VoiceCallback, outcome: str, user_id: uuid.UUID) -> VoiceCallback:
    if cb.state != "PENDING":
        raise CCError("This callback is already closed.")
    cb.attempts += 1
    cb.last_outcome, cb.assigned_user_id = outcome, user_id
    if outcome == "ANSWERED":
        cb.state, cb.done_at = "DONE", now()
    elif cb.attempts >= MAX_CALLBACK_ATTEMPTS:
        cb.state, cb.done_at = "EXPIRED", now()
    return cb


# ── consent and retention ─────────────────────────────────────────────────────

def record_consent(call: CallLog, agreed: bool, how: str) -> None:
    call.recording_consent = agreed
    call.consent_note = (how if agreed else f"declined: {how}")[:300]


def keep_recording(call: CallLog, url: str) -> bool:
    """Store a recording link only with consent, https, and a retention date. Returns whether it was stored."""
    if not (call.recording_consent and url.startswith("https://")) or call.recording_url:
        return False
    call.recording_url = url[:500]
    call.recording_expires_at = now() + timedelta(days=settings.CALL_RECORDING_RETENTION_DAYS)
    return True


async def purge_expired(db: AsyncSession) -> dict:
    """Voicemails past retention are deleted; recordings/transcripts are purged by the existing job."""
    res = await db.execute(delete(VoiceVoicemail).where(VoiceVoicemail.expires_at < now()))
    from app.models.m49_voice import TranscriptJob
    tj = await db.execute(update(TranscriptJob).where(TranscriptJob.expires_at < now(), TranscriptJob.status == "DONE")
                          .values(segments=None, status="EXPIRED", quality=None))
    return {"voicemails": res.rowcount or 0, "transcripts": tj.rowcount or 0}


# ── Twilio webhook ────────────────────────────────────────────────────────────

async def _first_seen(db: AsyncSession, key: str) -> bool:
    try:
        async with db.begin_nested():
            db.add(VoiceProviderEvent(provider="twilio", event_key=key[:200], received_at=now()))
            await db.flush()
        return True
    except IntegrityError:
        return False


async def _call_by_sid(db: AsyncSession, sid: str) -> Optional[CallLog]:
    return (await db.execute(select(CallLog).where(CallLog.provider_session_id == sid))).scalar_one_or_none() if sid else None


async def _menu_for(db: AsyncSession, to: str) -> Optional[VoiceIvrMenu]:
    return (await db.execute(select(VoiceIvrMenu).where(VoiceIvrMenu.is_active.is_(True),
            VoiceIvrMenu.phone_number == digits(to)))).scalars().first()


def _menu_prompt(menu: VoiceIvrMenu) -> list[str]:
    options = " ".join(f"Press {o['digit']} for {o['label']}." for o in menu.options or [])
    return [vc.say(menu.greeting_text + " " + options)]


async def _route(db: AsyncSession, call: CallLog, queue_id: Optional[str]) -> str:
    queue = await db.get(VoiceQueue, uuid.UUID(queue_id)) if queue_id else None
    if queue is None or not queue.is_active:
        await request_callback(db, call.phone_number, None, call.id)
        return vc.twiml(vc.say("Nobody can take your call right now. We will call you back."), "<Hangup/>")
    d = await decide(db, call, queue, can_hold=True, can_voicemail=True)
    q = {"ref": call.call_ref, "queue": str(queue.id)}
    if d.kind == "DIAL":
        record = bool(call.recording_consent)
        return vc.twiml(*([vc.say("This call may be recorded.")] if record else []),
                        vc.dial(d.numbers, vc.webhook_url("dial_result", **q), record, vc.webhook_url("recording", **q)))
    if d.kind == "HOLD":
        return vc.twiml(vc.say("All of our agents are busy. Please hold."), vc.hold(vc.webhook_url("queue_poll", **q)))
    if d.kind == "VOICEMAIL":
        call.ivr_step = "voicemail"
        return vc.twiml(vc.say("Please leave a message after the tone."),
                        vc.record_voicemail(vc.webhook_url("voicemail_done", **q), vc.webhook_url("recording", **q)))
    return vc.twiml(vc.say("We could not connect you. We will call you back."), "<Hangup/>")


async def handle_twilio(db: AsyncSession, step: str, form: dict, args: dict) -> str:
    """One verified Twilio webhook -> TwiML. Idempotent per event."""
    sid = (form.get("CallSid") or "")[:64]
    call = await _call_by_sid(db, sid)
    if call is None and args.get("ref"):
        call = (await db.execute(select(CallLog).where(CallLog.call_ref == args["ref"][:100]))).scalar_one_or_none()
        if call is not None and sid and not call.provider_session_id:
            call.provider_session_id = sid
    inbound = (form.get("Direction") or "").startswith("inbound")

    if step == "status":
        if call is None:
            return vc.twiml()
        if not await _first_seen(db, f"{sid}:{form.get('CallStatus')}:{form.get('SequenceNumber', '')}"):
            return vc.twiml()
        st = form.get("CallStatus", "")
        if call.status not in FINAL:
            if st in TW_STATUS:
                call.status = TW_STATUS[st]
                call.outcome = {"COMPLETED": "ANSWERED", "NO_ANSWER": "NO_ANSWER", "BUSY": "BUSY"}.get(call.status, "FAILED")
                dur = form.get("CallDuration") or form.get("Duration")
                call.duration_seconds = int(dur) if dur and dur.isdigit() else call.duration_seconds
                call.ended_at = datetime.utcnow()
                if call.outcome in ("NO_ANSWER", "BUSY", "FAILED"):
                    call.follow_up_required = True
                await release_agent(db, call)
            elif st in TW_LIVE:
                call.status = TW_LIVE[st] if call.status in (None, "QUEUED", "RINGING") else call.status
        return vc.twiml()

    if step == "voice":
        if call is None:
            if not inbound:
                return vc.twiml()
            menu = await _menu_for(db, form.get("To", ""))
            call = CallLog(call_ref=f"CALL-{uuid.uuid4().hex[:10].upper()}", direction="INBOUND", started_at=datetime.utcnow(),
                           phone_number=digits(form.get("From", "")) or "unknown", provider="twilio", provider_session_id=sid,
                           status="ANSWERED", outcome="ANSWERED", ivr_menu_id=menu.id if menu else None, recording_consent=False)
            db.add(call)
            await db.flush()
        if not inbound:                                   # agent answered: bridge the customer
            if call.ivr_step == "dialled":
                return vc.twiml()
            call.ivr_step = "dialled"
            q = {"ref": call.call_ref}
            return vc.twiml(*([vc.say("This call may be recorded.")] if call.recording_consent else []),
                            vc.dial([call.phone_number], vc.webhook_url("dial_result", **q), bool(call.recording_consent),
                                    vc.webhook_url("recording", **q)))
        menu = await db.get(VoiceIvrMenu, call.ivr_menu_id) if call.ivr_menu_id else None
        if menu is None:
            await request_callback(db, call.phone_number, None, call.id)
            return vc.twiml(vc.say("Thank you for calling POVU. Nobody can take your call right now. We will call you back."), "<Hangup/>")
        q = {"ref": call.call_ref}
        if menu.record_calls and call.consent_note is None:
            return vc.twiml(vc.gather(vc.webhook_url("consent", **q), vc.say((menu.consent_text or "This call may be recorded.")
                            + " Press 1 to agree to recording, or 2 to continue without recording.")))
        return vc.twiml(vc.gather(vc.webhook_url("menu", **q), *_menu_prompt(menu)), vc.say("We did not receive a choice. Goodbye."))

    if step == "consult_twiml":                             # the transfer target picked up the announcement leg
        return consult_twiml(args.get("transfer", ""), args.get("ref", "")) if call is not None else vc.twiml()
    if call is None:
        return vc.twiml()

    if step == "consent":
        agreed = form.get("Digits", "")[:1] == "1"
        record_consent(call, agreed, "keypress 1 at call start" if agreed else "keypress at call start")
        menu = await db.get(VoiceIvrMenu, call.ivr_menu_id) if call.ivr_menu_id else None
        if menu is None:
            return vc.twiml()
        return vc.twiml(vc.gather(vc.webhook_url("menu", ref=call.call_ref), *_menu_prompt(menu)), vc.say("We did not receive a choice. Goodbye."))

    if step == "menu":
        menu = await db.get(VoiceIvrMenu, call.ivr_menu_id) if call.ivr_menu_id else None
        digit = (form.get("Digits") or "")[:1]
        opt = next((o for o in (menu.options if menu else []) if str(o.get("digit")) == digit), None)
        if opt is None:
            return vc.twiml(vc.say("That is not a valid choice. Goodbye."), "<Hangup/>")
        call.tags = f"ivr:{opt.get('label', digit)}"[:300]
        if opt.get("queue_id"):
            return await _route(db, call, opt["queue_id"])
        numbers = list(opt.get("phone_numbers") or [])
        if not numbers:
            await request_callback(db, call.phone_number, None, call.id)
            return vc.twiml(vc.say("Everyone in this team is busy. We will call you back."), "<Hangup/>")
        return vc.twiml(vc.dial(numbers, vc.webhook_url("dial_result", ref=call.call_ref), bool(call.recording_consent),
                                vc.webhook_url("recording", ref=call.call_ref)))

    if step == "queue_poll":
        return await _route(db, call, args.get("queue"))

    if step == "dial_result":
        st = form.get("DialCallStatus", "")
        if st in ("no-answer", "busy", "failed", "canceled"):
            await release_agent(db, call)
            if call.direction == "INBOUND":
                await request_callback(db, call.phone_number, uuid.UUID(args["queue"]) if args.get("queue") else None, call.id)
                call.follow_up_required, call.outcome = True, "NO_ANSWER"
                return vc.twiml(vc.say("Nobody could answer. We will call you back."), "<Hangup/>")
        return vc.twiml()

    if step == "voicemail_done":
        return vc.twiml(vc.say("Thank you. Goodbye."), "<Hangup/>")

    if step == "recording":
        rsid, url = (form.get("RecordingSid") or "")[:64], form.get("RecordingUrl") or ""
        if form.get("RecordingStatus", "completed") != "completed" or not rsid or not await _first_seen(db, f"rec:{rsid}"):
            return vc.twiml()
        if call.ivr_step == "voicemail":
            dur = form.get("RecordingDuration", "")
            db.add(VoiceVoicemail(call_id=call.id, queue_id=uuid.UUID(args["queue"]) if args.get("queue") else None,
                                  phone_number=call.phone_number, provider_recording_id=rsid, recording_url=url[:500] if url.startswith("https://") else None,
                                  duration_seconds=int(dur) if dur.isdigit() else None, created_at=now(),
                                  expires_at=now() + timedelta(days=settings.CALL_RECORDING_RETENTION_DAYS)))
            call.follow_up_required = True
        else:
            keep_recording(call, url)                       # ignored unless consent was given
        return vc.twiml()

    if step == "consult_accept":                            # the transfer target answered the announcement leg
        t = await db.get(VoiceTransfer, uuid.UUID(args["transfer"]), with_for_update=True) if args.get("transfer") else None
        if t is None or t.call_id != call.id:
            return vc.twiml()
        if t.state == "CONSULTING":
            t.state = "READY" if form.get("Digits", "")[:1] == "1" else "DECLINED"
        return vc.twiml(vc.say("Thank you. The customer will be connected." if t.state == "READY" else "Understood."), "<Hangup/>")
    return vc.twiml()


# ── transfer ──────────────────────────────────────────────────────────────────

async def start_transfer(db: AsyncSession, call: CallLog, kind: str, user, to_user_id: Optional[uuid.UUID], to_number: Optional[str]) -> VoiceTransfer:
    from app.services import voice_service
    prov = voice_service.provider()
    cap = vc.matrix(prov).get("cold_transfer" if kind == "COLD" else "warm_transfer", (vc.U, ""))
    if cap[0] != vc.S:
        raise CCError(f"{kind.title()} transfer is not available: {cap[1]}", 409)
    if call.provider != "twilio" or not call.provider_session_id or call.status in FINAL:
        raise CCError("Only a live call placed through the carrier can be transferred.", 409)
    if call.direction != "INBOUND":
        raise CCError("Transfer works on inbound calls: the customer's leg is not tracked for outbound bridged calls.", 409)
    number = digits(to_number or "")
    if to_user_id:
        pr = await db.get(VoicePresence, to_user_id)
        prof = await db.get(VoiceAgentProfile, to_user_id)
        if pr is None or pr.status != "AVAILABLE" or prof is None or not prof.phone_number:
            raise CCError("The target agent is not available.", 409)
        number = digits(prof.phone_number)
    if not number:
        raise CCError("A target agent or number is required.", 422)
    open_t = (await db.execute(select(VoiceTransfer).where(VoiceTransfer.call_id == call.id,
              VoiceTransfer.state.in_(("REQUESTED", "CONSULTING", "READY"))))).scalars().first()
    if open_t is not None:
        raise CCError("A transfer is already in progress for this call.", 409)
    t = VoiceTransfer(call_id=call.id, kind=kind, from_user_id=user.id, to_user_id=to_user_id, to_number=number, state="REQUESTED")
    db.add(t)
    await db.flush()
    try:
        if kind == "COLD":
            await vc.update_call(call.provider_session_id, vc.twiml(vc.say("Transferring your call."), vc.dial(
                [number], vc.webhook_url("dial_result", ref=call.call_ref), bool(call.recording_consent), vc.webhook_url("recording", ref=call.call_ref))))
            t.state = "COMPLETED"
        else:                                                # announce first; the target accepts with a keypress
            r = await vc.create_consult_call(number, vc.webhook_url("consult_twiml", transfer=str(t.id), ref=call.call_ref))
            t.provider_ref, t.state = r.get("sid"), "CONSULTING"
    except vc.CarrierError as e:
        t.state, t.error = "FAILED", str(e)[:300]
    return t


def consult_twiml(t_id: str, ref: str) -> str:
    return vc.twiml(vc.gather(vc.webhook_url("consult_accept", transfer=t_id, ref=ref),
                    vc.say("A customer is waiting for a transfer. Press 1 to accept, or 2 to decline.")), vc.say("No answer received."), "<Hangup/>")


async def complete_warm_transfer(db: AsyncSession, call: CallLog, t: VoiceTransfer) -> VoiceTransfer:
    if t.kind != "WARM" or t.state != "READY":
        raise CCError("The target has not accepted the transfer yet.", 409)
    try:
        await vc.update_call(call.provider_session_id, vc.twiml(vc.say("Transferring your call."), vc.dial(
            [t.to_number], vc.webhook_url("dial_result", ref=call.call_ref), bool(call.recording_consent), vc.webhook_url("recording", ref=call.call_ref))))
        t.state = "COMPLETED"
    except vc.CarrierError as e:
        t.state, t.error = "FAILED", str(e)[:300]
    return t


# ── outbound placement and status verification ────────────────────────────────

async def place_twilio(call: CallLog, agent_phone: str) -> CallLog:
    try:
        body = await vc.create_call(digits(agent_phone), call.call_ref)
    except vc.CarrierError as e:
        if e.status_code == 504:                              # unknown outcome: never re-send, a human verifies
            call.provider, call.status = "twilio", "UNKNOWN"
        else:
            call.status, call.outcome = "FAILED", "FAILED"
        raise CCError(str(e), e.status_code) from None
    call.provider, call.provider_session_id, call.status = "twilio", body.get("sid"), "QUEUED"
    return call


async def verify_status(db: AsyncSession, call: CallLog) -> CallLog:
    """Poll the carrier for a call that has no final state (lost webhooks, unknown outcome)."""
    if call.provider != "twilio" or not call.provider_session_id:
        raise CCError("Nothing to verify at a carrier for this call.", 409)
    try:
        body = await vc.fetch_call(call.provider_session_id)
    except vc.CarrierError as e:
        raise CCError(str(e), e.status_code) from None
    st = body.get("status", "")
    if call.status not in FINAL:
        if st in TW_STATUS:
            call.status = TW_STATUS[st]
            call.outcome = {"COMPLETED": "ANSWERED", "NO_ANSWER": "NO_ANSWER", "BUSY": "BUSY"}.get(call.status, "FAILED")
            call.ended_at = datetime.utcnow()
            await release_agent(db, call)
        elif st in TW_LIVE:
            call.status = TW_LIVE[st]
    return call
