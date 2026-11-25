"""E-mail complaint feedback and deliverability (M44.S01.T011).

Signed provider event webhooks (public, documented contracts):
- Mailgun: event-data + signature {timestamp, token, signature}; HMAC-SHA256(signing key, timestamp+token), hex.
- SendGrid Event Webhook: ECDSA P-256 over (timestamp header + raw body), public key from the account settings,
  headers X-Twilio-Email-Event-Webhook-Signature / -Timestamp.
- generic: HMAC-SHA256(secret, raw body) hex in X-POVU-Signature, for any other relay.
Unconfigured providers refuse events (503). Timestamps older than 10 minutes are refused (replay).

An event only changes anything when it names a CRM e-mail we really sent (provider_message_id match) to the same
recipient — forged or mismatched events are stored as ignored. Permanent bounces → BOUNCED, complaints → COMPLAINED,
provider unsubscribes → UNSUBSCRIBED (all suppress future mail). Each event id is processed once (providers retry).
DNS diagnostics build the SPF / DKIM / DMARC records to publish and check pasted TXT values offline — no DNS lookup.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMOutboundMessage, MailFeedbackEvent

MAX_AGE = 600
KIND = {"bounced": "BOUNCED", "failed": "BOUNCED", "bounce": "BOUNCED", "dropped": "BOUNCED",
        "complained": "COMPLAINED", "spamreport": "COMPLAINED", "complaint": "COMPLAINED",
        "unsubscribed": "UNSUBSCRIBED", "unsubscribe": "UNSUBSCRIBED", "group_unsubscribe": "UNSUBSCRIBED",
        "delivered": "DELIVERED", "delivery": "DELIVERED"}


class FeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


def _fresh(ts: str) -> None:
    try:
        if abs(time.time() - int(ts)) > MAX_AGE:
            raise FeedbackError("Event timestamp outside the allowed window.")
    except ValueError:
        raise FeedbackError("Bad timestamp.") from None


def verify_mailgun(payload: dict) -> list[dict]:
    key = settings.MAIL_EVENTS_MAILGUN_SIGNING_KEY
    if not key:
        raise FeedbackError("Mailgun events are not configured.", 503)
    sig = payload.get("signature") or {}
    _fresh(str(sig.get("timestamp", "")))
    expect = hmac.new(key.encode(), f"{sig.get('timestamp', '')}{sig.get('token', '')}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect.encode(), str(sig.get("signature", "")).encode()):
        raise FeedbackError("Invalid Mailgun signature.")
    ev = payload.get("event-data") or {}
    severity = ev.get("severity")
    kind = KIND.get(ev.get("event", ""), "OTHER")
    if kind == "BOUNCED" and severity == "temporary":
        kind = "SOFT_BOUNCE"
    mid = ((ev.get("message") or {}).get("headers") or {}).get("message-id")
    return [{"event_id": str(ev.get("id") or sig.get("token")), "kind": kind, "email": ev.get("recipient"),
             "message_id": mid}]


def verify_sendgrid(raw: bytes, signature: str, timestamp: str) -> list[dict]:
    key = settings.MAIL_EVENTS_SENDGRID_PUBLIC_KEY
    if not key:
        raise FeedbackError("SendGrid events are not configured.", 503)
    _fresh(timestamp)
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    try:
        pub = serialization.load_der_public_key(base64.b64decode(key))
        pub.verify(base64.b64decode(signature), timestamp.encode() + raw, ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError):
        raise FeedbackError("Invalid SendGrid signature.") from None
    out = []
    for ev in json.loads(raw or b"[]"):
        kind = KIND.get(ev.get("event", ""), "OTHER")
        if kind == "BOUNCED" and ev.get("type") == "blocked":
            kind = "SOFT_BOUNCE"
        out.append({"event_id": str(ev.get("sg_event_id") or ""), "kind": kind, "email": ev.get("email"),
                    "message_id": ev.get("smtp-id")})
    return out


def verify_generic(raw: bytes, signature: str) -> list[dict]:
    secret = settings.MAIL_EVENTS_GENERIC_SECRET
    if not secret:
        raise FeedbackError("Generic mail events are not configured.", 503)
    expect = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect.encode(), (signature or "").encode()):
        raise FeedbackError("Invalid signature.")
    body = json.loads(raw or b"{}")
    _fresh(str(body.get("timestamp", "")))
    return [{"event_id": str(e.get("id") or ""), "kind": KIND.get(str(e.get("type", "")).lower(), "OTHER"),
             "email": e.get("recipient"), "message_id": e.get("message_id")} for e in body.get("events", [])]


def _norm_mid(mid: Optional[str]) -> str:
    return (mid or "").strip().strip("<>")


async def apply(db: AsyncSession, provider: str, events: list[dict]) -> dict:
    """Store and apply verified events once each. Caller commits."""
    from app.services.crm_outbound_service import norm, record_consent
    counts = {"applied": 0, "ignored": 0, "duplicate": 0}
    for e in events[:1000]:
        eid = (e.get("event_id") or "")[:200]
        if not eid:
            counts["ignored"] += 1
            continue
        if (await db.execute(select(MailFeedbackEvent.id).where(MailFeedbackEvent.provider == provider,
                                                               MailFeedbackEvent.event_id == eid))).first():
            counts["duplicate"] += 1
            continue
        email, mid = norm(e.get("email") or ""), _norm_mid(e.get("message_id"))
        sent = None
        if email and mid:
            sent = (await db.execute(select(CRMOutboundMessage).where(
                func.trim(CRMOutboundMessage.provider_message_id, "<> ") == mid,
                CRMOutboundMessage.to_email == email))).scalars().first()
        applied = False
        if sent is not None and e["kind"] in ("BOUNCED", "COMPLAINED", "UNSUBSCRIBED"):
            await record_consent(db, email, e["kind"], f"{provider} feedback")
            sent.status_reason = f"{e['kind'].lower()} reported by {provider}"[:300]
            applied = True
        db.add(MailFeedbackEvent(provider=provider, event_id=eid, kind=e["kind"], email=email[:254] or None,
                                 message_id=mid[:300] or None, outbound_id=sent.id if sent else None, applied=applied,
                                 received_at=datetime.now(timezone.utc)))
        await db.flush()
        counts["applied" if applied else "ignored"] += 1
    return counts


# ── DNS diagnostics (offline) ─────────────────────────────────────────────────

DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$")


def dns_plan(domain: str, relay_include: str = "", selector: str = "povu") -> dict:
    domain = domain.strip().lower()
    if not DOMAIN.match(domain):
        raise FeedbackError("Enter a domain like mail.example.com", 422)
    spf = "v=spf1 " + (f"include:{relay_include.strip()} " if relay_include.strip() else "") + "~all"
    return {"domain": domain, "records": [
        {"type": "TXT", "host": domain, "value": spf, "purpose": "SPF: which servers may send for the domain"},
        {"type": "TXT", "host": f"{selector}._domainkey.{domain}", "value": "v=DKIM1; k=rsa; p=<public key from your mail relay>",
         "purpose": "DKIM: signature key (the relay generates it)"},
        {"type": "TXT", "host": f"_dmarc.{domain}", "value": f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain}; fo=1",
         "purpose": "DMARC: policy and aggregate reports"}],
        "note": "Publish these at your DNS host; nothing here queries DNS or claims the domain is set up."}


def check_records(spf: str = "", dkim: str = "", dmarc: str = "", relay_include: str = "") -> list[dict]:
    out = []
    s = spf.strip()
    out.append({"record": "SPF", "ok": s.startswith("v=spf1") and s.count("v=spf1") == 1
                and (not relay_include or f"include:{relay_include}" in s) and not s.endswith("+all"),
                "detail": "Must start with v=spf1, include the relay and never end in +all."})
    k = dkim.replace(" ", "")
    key = re.search(r"p=([A-Za-z0-9+/=]+)", k)
    bits = len(base64.b64decode(key.group(1) + "===")) * 8 if key else 0
    out.append({"record": "DKIM", "ok": k.startswith("v=DKIM1") and bits >= 1000,
                "detail": f"Public key {'≈' + str(bits) + ' bits' if bits else 'missing'}; 1024 bits minimum, 2048 recommended."})
    d = {p.split("=", 1)[0].strip(): p.split("=", 1)[1].strip() for p in dmarc.split(";") if "=" in p}
    out.append({"record": "DMARC", "ok": d.get("v") == "DMARC1" and d.get("p") in ("quarantine", "reject", "none"),
                "detail": f"Policy {d.get('p', 'missing')}" + ("; p=none only monitors" if d.get("p") == "none" else "")})
    return out
