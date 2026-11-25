"""Provider-independent voice adapter: click-to-call, power dialer, inbound IVR (M43.S01.T008).

Provider: Africa's Talking Voice (public contract, 2026-11-25):
- Outbound: POST {base}/call (form: username, from, to, clientRequestId) with header apiKey → entries[].sessionId.
  The call first rings the agent's phone; when the agent answers, AT posts the call to our callback and our XML
  answer <Dial> connects the customer (record="true" only with recorded consent).
- Callbacks (form fields isActive, sessionId, direction, callerNumber, destinationNumber, dtmfDigits, recordingUrl,
  durationInSeconds, status, amount, currencyCode) carry no signature, so the callback URL holds a secret token
  (VOICE_CALLBACK_SECRET, compared in constant time) — the same pattern as M-Pesa.
- Actions: Say, GetDigits, Dial, Record, Reject (XML <Response>).
No provider configured → VOICE disabled: click-to-call falls back to the existing tel: link (M36.S04.T002) and
nothing is ever shown as placed by a provider. Capability discovery tells the UI what the active provider can do:
voicemail drop needs mid-call control that AT Voice does not expose, so it is reported unsupported, not faked.
Lifecycle: QUEUED → RINGING → ANSWERED → COMPLETED | NO_ANSWER | BUSY | FAILED; repeated callbacks are idempotent
(a final state is never overwritten).
"""
from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.sax.saxutils import escape, quoteattr

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.voip import CallLog, DialerSession, VoiceAgentProfile, VoiceIvrMenu

log = logging.getLogger(__name__)
FINAL = ("COMPLETED", "NO_ANSWER", "BUSY", "FAILED")
AT_STATUS = {"Success": "COMPLETED", "NoAnswer": "NO_ANSWER", "Busy": "BUSY", "Rejected": "BUSY",
             "Failed": "FAILED", "Aborted": "FAILED", "NotNetworkNotFound": "FAILED", "InsufficientCredit": "FAILED"}


class VoiceError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def provider() -> Optional[str]:
    p = (settings.VOICE_PROVIDER or "").strip().lower()
    if p == "africastalking" and settings.VOICE_AT_USERNAME and settings.VOICE_AT_API_KEY and settings.VOICE_AT_PHONE_NUMBER:
        return p
    return None


def capabilities() -> dict:
    p = provider()
    return {"provider": p, "configured": p is not None, "click_to_call": True, "server_dialing": p is not None,
            "power_dialer": True, "ivr": p is not None, "recording": p is not None, "voicemail_drop": False,
            "voicemail_drop_reason": "The configured provider has no mid-call control API; leave a live voicemail.",
            "transcription": bool(settings.CALL_TRANSCRIPTION_ENABLED)}


def callback_ok(token: str) -> bool:
    secret = settings.VOICE_CALLBACK_SECRET
    return bool(secret) and hmac.compare_digest(token or "", secret)


def _digits(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


async def place_call(db: AsyncSession, call: CallLog, agent_phone: str) -> CallLog:
    """Ask the provider to ring the agent; the customer is dialled from the answer callback. Caller commits."""
    if provider() is None:
        raise VoiceError("No voice provider is configured; use the phone's dialler.", 409)
    data = {"username": settings.VOICE_AT_USERNAME, "from": settings.VOICE_AT_PHONE_NUMBER, "to": _digits(agent_phone),
            "clientRequestId": call.call_ref}
    try:
        async with provider_client() as c:
            r = await c.post(settings.VOICE_AT_BASE_URL.rstrip("/") + "/call", data=data,
                             headers={"apiKey": settings.VOICE_AT_API_KEY, "Accept": "application/json"})
    except EgressBlocked as e:
        raise VoiceError(str(e), 503) from None
    except httpx.HTTPError:
        raise VoiceError("The voice provider could not be reached.", 503) from None
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    entry = (body.get("entries") or [{}])[0]
    if r.status_code >= 400 or entry.get("status") not in ("Queued", "Success"):
        call.status, call.outcome = "FAILED", "FAILED"
        raise VoiceError(f"The provider refused the call: {str(body.get('errorMessage') or r.status_code)[:120]}", 502)
    call.provider, call.provider_session_id, call.status = "africastalking", entry.get("sessionId"), "QUEUED"
    return call


def _xml(*actions: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(actions) + "</Response>"


def _say(text: str) -> str:
    return f"<Say>{escape(text)}</Say>"


def _dial(numbers: list[str], record: bool) -> str:
    return f'<Dial phoneNumbers={quoteattr(",".join(_digits(n) for n in numbers))} record="{"true" if record else "false"}" sequential="true"/>'


async def handle_callback(db: AsyncSession, form: dict) -> str:
    """Apply one provider callback; return the XML instructions. Idempotent per (session, state)."""
    session = (form.get("sessionId") or "")[:100]
    active = form.get("isActive") == "1"
    call = (await db.execute(select(CallLog).where(CallLog.provider_session_id == session))).scalar_one_or_none() \
        if session else None
    if call is None and active and form.get("direction") == "Inbound":
        return await _inbound(db, form, session)
    if call is None:
        log.info("voice callback for unknown session ignored")
        return _xml()
    if active:
        if call.status not in FINAL:
            call.status = "ANSWERED" if call.status in ("QUEUED", "RINGING") else call.status
        if call.direction == "OUTBOUND":
            if form.get("dtmfDigits") is not None or call.ivr_step == "dialled":
                return _xml()
            call.ivr_step = "dialled"
            return _xml(*( [_say("This call may be recorded.")] if call.recording_consent else []),
                        _dial([call.phone_number], record=bool(call.recording_consent)))
        return await _ivr_digits(db, call, form)
    # session ended
    if call.status not in FINAL:
        call.status = AT_STATUS.get(form.get("status", ""), "COMPLETED" if form.get("durationInSeconds") else "FAILED")
        call.outcome = {"COMPLETED": "ANSWERED", "NO_ANSWER": "NO_ANSWER", "BUSY": "BUSY"}.get(call.status, "FAILED")
        dur = form.get("durationInSeconds")
        call.duration_seconds = int(float(dur)) if dur and dur.replace(".", "", 1).isdigit() else call.duration_seconds
        call.ended_at = datetime.utcnow()
        if form.get("amount") and form.get("currencyCode"):
            call.cost_amount, call.cost_currency = form["amount"][:20], form["currencyCode"][:10]
        if call.outcome in ("NO_ANSWER", "BUSY", "FAILED"):
            call.follow_up_required = True
        await _advance_dialer(db, call)
    # the recording may arrive in its own, later notification: keep it only with consent, https, within retention
    if form.get("recordingUrl") and call.recording_consent and form["recordingUrl"].startswith("https://")             and not call.recording_url:
        call.recording_url = form["recordingUrl"][:500]
        call.recording_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.CALL_RECORDING_RETENTION_DAYS)
    return _xml()


async def _inbound(db: AsyncSession, form: dict, session: str) -> str:
    menu = (await db.execute(select(VoiceIvrMenu).where(VoiceIvrMenu.is_active.is_(True),
            VoiceIvrMenu.phone_number == _digits(form.get("destinationNumber", ""))))).scalars().first()
    from uuid import uuid4
    call = CallLog(call_ref=f"CALL-{uuid4().hex[:10].upper()}", direction="INBOUND",
                   phone_number=_digits(form.get("callerNumber", ""))[:50] or "unknown", started_at=datetime.utcnow(),
                   provider="africastalking", provider_session_id=session, status="ANSWERED", outcome="ANSWERED",
                   ivr_menu_id=menu.id if menu else None, follow_up_required=False,
                   recording_consent=bool(menu and menu.record_calls))
    db.add(call)
    await db.flush()
    if menu is None:
        return _xml(_say("Thank you for calling POVU. Nobody can take your call right now. Goodbye."))
    options = " ".join(f"Press {o['digit']} for {o['label']}." for o in menu.options or [])
    cb = f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/calls/provider/callback?token={settings.VOICE_CALLBACK_SECRET}"
    consent = _say(menu.consent_text) if menu.record_calls and menu.consent_text else ""
    return _xml(consent, f'<GetDigits timeout="10" finishOnKey="#" numDigits="1" callbackUrl={quoteattr(cb)}>'
                         f"{_say(menu.greeting_text + ' ' + options)}</GetDigits>",
                _say("We did not receive a choice. Goodbye."))


async def _ivr_digits(db: AsyncSession, call: CallLog, form: dict) -> str:
    menu = await db.get(VoiceIvrMenu, call.ivr_menu_id) if call.ivr_menu_id else None
    digit = (form.get("dtmfDigits") or "")[:1]
    opt = next((o for o in (menu.options if menu else []) if str(o.get("digit")) == digit), None)
    if opt is None:
        return _xml(_say("That is not a valid choice. Goodbye."))
    agents = (await db.execute(select(VoiceAgentProfile).where(
        VoiceAgentProfile.user_id.in_(opt.get("user_ids") or []), VoiceAgentProfile.available.is_(True)))).scalars().all()
    numbers = [a.phone_number for a in agents] + list(opt.get("phone_numbers") or [])
    if not numbers:
        call.follow_up_required, call.notes = True, f"IVR option {digit}: nobody available"
        return _xml(_say("Everyone in this team is busy. We will call you back."))
    call.tags = f"ivr:{opt.get('label', digit)}"[:300]
    call.agent_id = agents[0].user_id if agents else None
    return _xml(_say(f"Connecting you to {opt.get('label', 'our team')}."), _dial(numbers, record=bool(menu.record_calls)))


# ── power dialer ──────────────────────────────────────────────────────────────

async def start_next(db: AsyncSession, ds: DialerSession, agent_phone: Optional[str]) -> Optional[CallLog]:
    """Create (and with a provider, place) the call for the next pending item. Caller commits."""
    from uuid import uuid4
    items = list(ds.items or [])
    idx = next((i for i, it in enumerate(items) if it.get("state") == "PENDING"), None)
    if idx is None or ds.status != "ACTIVE":
        ds.status = "DONE" if idx is None else ds.status
        return None
    it = items[idx]
    call = CallLog(call_ref=f"CALL-{uuid4().hex[:10].upper()}", direction="OUTBOUND", phone_number=it["phone"],
                   crm_record_id=it.get("crm_record_id"), customer_id=it.get("customer_id"), agent_id=ds.agent_id,
                   started_at=datetime.utcnow(), outcome="DIALED", status="QUEUED", follow_up_required=False,
                   dialer_session_id=ds.id)
    db.add(call)
    await db.flush()
    it.update(state="CALLING", call_id=str(call.id))
    if provider() is not None and agent_phone:
        try:
            await place_call(db, call, agent_phone)
        except VoiceError:
            it["state"] = "FAILED"
    ds.items, ds.current_index = items, idx
    return call


async def _advance_dialer(db: AsyncSession, call: CallLog) -> None:
    if not call.dialer_session_id:
        return
    ds = await db.get(DialerSession, call.dialer_session_id)
    if ds is None:
        return
    items = list(ds.items or [])
    for it in items:
        if it.get("call_id") == str(call.id):
            it["state"] = "DONE" if call.outcome == "ANSWERED" else call.outcome or "DONE"
    ds.items = items
