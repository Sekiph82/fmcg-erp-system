"""Carrier adapters and the capability matrix for the contact center (M49.S01.T004).

Twilio Programmable Voice, REST API version 2010-04-01 (official docs, checked 2026-11-26 in
coordination/milestones/M48/CAPABILITY_MATRIX.md):
- Create call   POST {base}/2010-04-01/Accounts/{AccountSid}/Calls.json  (form To, From, Url, StatusCallback,
                StatusCallbackEvent, Timeout; HTTP Basic AccountSid:AuthToken) -> 201 {"sid", "status": "queued", ...}
- Fetch call    GET  .../Calls/{Sid}.json   (eventually consistent; used only to verify a stuck call)
- Update call   POST .../Calls/{Sid}.json   (Twiml= / Url= redirects a live call: used for cold transfer)
  https://www.twilio.com/docs/voice/api/call-resource
- Errors are JSON {"code", "message", "more_info", "status"}; 429 and 5xx are retried with backoff.
- Webhooks: X-Twilio-Signature = base64(HMAC-SHA1(AuthToken, full URL + sorted POST params as key+value)).
  https://www.twilio.com/docs/usage/webhooks/webhooks-security  Twilio sends no timestamp, so replay is handled by a
  per-(CallSid, CallStatus, SequenceNumber) event key. Base64 output is "widely assumed" in our matrix (UNVERIFIED).
- TwiML verbs used: Say, Gather, Dial(+Number), Record, Pause, Redirect, Hangup (https://www.twilio.com/docs/voice/twiml);
  the verb list was not fetched in the matrix session, so it is marked in the capability matrix, not assumed.

Africa's Talking stays in voice_service (its docs were unreachable; mid-call control is UNSUPPORTED/UNVERIFIED).
Every call goes through provider_client(): PROVIDER_EGRESS=local only reaches the local simulator. Nothing here is
ever placed on a real network without the explicit VOICE_TWILIO_* credentials.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from typing import Optional
from xml.sax.saxutils import escape, quoteattr

import httpx

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client

_BACKOFF = 0.5          # seconds, doubled per retry (tests patch it to 0)
MAX_TRIES = 3


class CarrierError(Exception):
    def __init__(self, message: str, status_code: int = 502, retryable: bool = False):
        super().__init__(message)
        self.status_code, self.retryable = status_code, retryable


def _cfg(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or default)


def twilio_configured() -> bool:
    return bool(_cfg("VOICE_TWILIO_ACCOUNT_SID") and _cfg("VOICE_TWILIO_AUTH_TOKEN") and _cfg("VOICE_TWILIO_PHONE_NUMBER"))


def _base() -> str:
    return _cfg("VOICE_TWILIO_BASE_URL", "https://api.twilio.com").rstrip("/") + f"/2010-04-01/Accounts/{_cfg('VOICE_TWILIO_ACCOUNT_SID')}"


# ── capability matrix ─────────────────────────────────────────────────────────

S, U, V = "SUPPORTED", "UNSUPPORTED", "UNVERIFIED"


def matrix(provider: Optional[str]) -> dict:
    """What the active carrier can really do; the UI enables only SUPPORTED and shows the reason otherwise."""
    none = "No voice provider is configured; calls use the phone's dialler."
    if provider == "twilio":
        return {
            "outbound_call": (S, None), "inbound_ivr": (S, None), "queue_hold": (S, None), "recording": (S, None),
            "voicemail": (S, None), "signature_verification": (S, None),
            "cold_transfer": (S, "Inbound calls only: the customer leg is redirected."),
            "warm_transfer": (S, "Announced hand-off (target accepts first); not a 3-way conference."),
        }
    if provider == "africastalking":
        mid = "Africa's Talking exposes no mid-call control API (SDK source: only call, queueStatus, mediaUpload)."
        return {
            "outbound_call": (S, None), "inbound_ivr": (S, None), "recording": (S, None),
            "queue_hold": (V, "Hold-and-redirect polling needs the <Redirect> action, whose docs could not be fetched."),
            "voicemail": (V, "The <Record> action is listed by the SDK-era docs only; not verified against official docs."),
            "cold_transfer": (U, mid), "warm_transfer": (U, mid),
            "signature_verification": (U, "Callbacks carry no signature; a secret token in the URL is the credential."),
        }
    return {k: (U, none) for k in ("outbound_call", "inbound_ivr", "queue_hold", "recording", "voicemail",
                                   "cold_transfer", "warm_transfer", "signature_verification")}


def matrix_out(provider: Optional[str]) -> dict:
    return {k: {"state": v[0], "reason": v[1]} for k, v in matrix(provider).items()}


# ── webhook signature ─────────────────────────────────────────────────────────

def twilio_signature(auth_token: str, url: str, params: dict) -> str:
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    return base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()


def twilio_signature_ok(url: str, params: dict, header: Optional[str]) -> bool:
    token = _cfg("VOICE_TWILIO_AUTH_TOKEN")
    if not token or not header:
        return False                                    # fail closed: no token or no signature -> refused
    return hmac.compare_digest(twilio_signature(token, url, params).encode(), header.strip().encode())


# ── REST ──────────────────────────────────────────────────────────────────────

def _auth() -> tuple[str, str]:
    return _cfg("VOICE_TWILIO_ACCOUNT_SID"), _cfg("VOICE_TWILIO_AUTH_TOKEN")


async def _request(method: str, url: str, data: Optional[dict] = None) -> dict:
    """One Twilio REST call with retry/backoff on 429/5xx. Never retried after a 4xx (other than 429)."""
    last: Optional[CarrierError] = None
    for attempt in range(MAX_TRIES):
        try:
            async with provider_client() as c:
                r = await c.request(method, url, data=data, auth=_auth(), headers={"Accept": "application/json"})
        except EgressBlocked as e:
            raise CarrierError(str(e), 503) from None
        except httpx.TimeoutException:
            # the request may have reached Twilio: the outcome is unknown and must be reconciled, not re-sent
            raise CarrierError("The carrier did not answer in time; the call outcome is unknown.", 504) from None
        except httpx.HTTPError:
            last = CarrierError("The carrier could not be reached.", 503, True)
        else:
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code < 300:
                return body
            msg = f"Twilio {body.get('code', r.status_code)}: {str(body.get('message') or '')[:120]}"
            if r.status_code == 429 or r.status_code >= 500:
                last = CarrierError(msg, 503, True)
            else:
                raise CarrierError(msg, 502 if r.status_code != 401 else 424)
        if attempt < MAX_TRIES - 1:
            await asyncio.sleep(_BACKOFF * (2 ** attempt))
    raise last or CarrierError("The carrier failed.", 503)


def webhook_url(step: str, **q: str) -> str:
    from urllib.parse import urlencode
    return (f"{_cfg('PUBLIC_API_URL', 'http://localhost:8000').rstrip('/')}/api/v1/calls/cc/twilio/webhook?"
            + urlencode({"step": step, **q}))


async def create_call(to: str, call_ref: str) -> dict:
    """Ring ``to`` (the agent's phone); when answered Twilio fetches our TwiML (step=voice)."""
    return await _request("POST", _base() + "/Calls.json", {
        "To": to, "From": _cfg("VOICE_TWILIO_PHONE_NUMBER"), "Url": webhook_url("voice", ref=call_ref), "Method": "POST",
        "StatusCallback": webhook_url("status", ref=call_ref), "StatusCallbackMethod": "POST",
        "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"], "Timeout": "30"})


async def create_consult_call(to: str, url: str) -> dict:
    """Warm transfer: ring the target with an announcement (their keypress accepts or declines)."""
    return await _request("POST", _base() + "/Calls.json", {"To": to, "From": _cfg("VOICE_TWILIO_PHONE_NUMBER"),
                                                           "Url": url, "Method": "POST", "Timeout": "30"})


async def fetch_call(sid: str) -> dict:
    return await _request("GET", _base() + f"/Calls/{sid}.json")


async def update_call(sid: str, twiml: str) -> dict:
    return await _request("POST", _base() + f"/Calls/{sid}.json", {"Twiml": twiml})


# ── TwiML ─────────────────────────────────────────────────────────────────────

def _digits(n: str) -> str:
    return "".join(ch for ch in n if ch.isdigit() or ch == "+")


def twiml(*parts: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(parts) + "</Response>"


def say(text: str) -> str:
    return f"<Say>{escape(text)}</Say>"


def gather(action: str, *prompt: str, timeout: int = 8) -> str:
    return (f'<Gather input="dtmf" numDigits="1" timeout="{timeout}" method="POST" action={quoteattr(action)}>'
            + "".join(prompt) + "</Gather>")


def dial(numbers: list[str], action: str, record: bool, rec_cb: Optional[str] = None, timeout: int = 20) -> str:
    rec = (f' record="record-from-answer-dual" recordingStatusCallback={quoteattr(rec_cb)}' if record and rec_cb
           else ' record="do-not-record"')
    return (f'<Dial timeout="{timeout}" method="POST" action={quoteattr(action)}{rec}>'
            + "".join(f"<Number>{escape(_digits(n))}</Number>" for n in numbers) + "</Dial>")


def record_voicemail(action: str, rec_cb: str) -> str:
    return (f'<Record maxLength="120" playBeep="true" method="POST" action={quoteattr(action)} '
            f'recordingStatusCallback={quoteattr(rec_cb)}/>')


def hold(redirect: str, seconds: int = 10) -> str:
    return f'<Pause length="{seconds}"/><Redirect method="POST">{escape(redirect)}</Redirect>'
