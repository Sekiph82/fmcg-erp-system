"""M36 consent register and CRM e-mail outbox (foundation for sequences and campaigns).

- Every CRM e-mail is queued with a dedupe key; the same key is never sent twice.
- SEQUENCE and CAMPAIGN mail needs a SUBSCRIBED consent; UNSUBSCRIBED / BOUNCED / COMPLAINED addresses are
  suppressed for every purpose except MANUAL one-to-one mail to non-suppressed addresses. INVOICE (a payment link
  the customer is owed) is not stopped by a marketing unsubscribe, only by BOUNCED / COMPLAINED (M48.S01.T022 F8).
- M48.S01.T022 double opt-in: web form and chat consent records PENDING and queues a CONSENT confirmation e-mail
  with a signed, expiring link; only the click (POST /public/consent-confirm) sets SUBSCRIBED, with the time and a
  keyed hash of the connection. PENDING never overrides an existing status.
- Suppression is checked when queuing and again right before sending (an unsubscribe in between wins).
- Delivery uses the configured SMTP server only when CRM_OUTBOUND_EMAIL_ENABLED is on; otherwise mail stays
  QUEUED. A message becomes SENT only after the SMTP server accepted it.
- Every marketing message carries a signed unsubscribe link and RFC 8058 one-click List-Unsubscribe headers.
  Links are signed with UNSUBSCRIBE_SECRET (blank = SECRET_KEY) and verified against UNSUBSCRIBE_PREVIOUS_SECRETS
  too, so rotating the key does not break links already delivered.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMContactConsent, CRMOutboundMessage

logger = logging.getLogger(__name__)

PURPOSES = ("MANUAL", "SEQUENCE", "CAMPAIGN", "INVOICE", "CONSENT")  # INVOICE, CONSENT: transactional, no footer
TRANSACTIONAL = ("INVOICE", "CONSENT")
SUPPRESSING = ("UNSUBSCRIBED", "BOUNCED", "COMPLAINED")
MAX_ATTEMPTS = 3
STALE_SENDING = timedelta(minutes=15)


def norm(email: str) -> str:
    return (email or "").strip().lower()


def _one_line(text: str) -> str:
    """Header values never carry line breaks (no header injection through subject or address)."""
    return " ".join((text or "").split())


def _keys() -> list[bytes]:
    """Signing key first, then previous keys accepted for verification only."""
    current = getattr(settings, "UNSUBSCRIBE_SECRET", "") or settings.SECRET_KEY
    previous = [k.strip() for k in (getattr(settings, "UNSUBSCRIBE_PREVIOUS_SECRETS", "") or "").split(",") if k.strip()]
    return [k.encode() for k in [current, *previous]]


def _enc(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sig(key: bytes, msg: bytes) -> str:
    return _enc(hmac.new(key, msg, hashlib.sha256).digest()[:16])


def unsubscribe_token(email: str) -> str:
    raw = norm(email).encode()
    return f"{_enc(raw)}.{_sig(_keys()[0], b'unsub:' + raw)}"


def email_from_token(token: str) -> Optional[str]:
    try:
        part, sig = token.split(".", 1)
        email = _dec(part).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    msg = b"unsub:" + norm(email).encode()
    ok = any(hmac.compare_digest(_sig(k, msg).encode(), sig.encode("utf-8", "replace")) for k in _keys())
    return email if ok and email == norm(email) else None


def confirm_token(email: str, now: Optional[float] = None) -> str:
    """Signed double opt-in link token: e-mail, expiry (unix seconds), signature."""
    raw = norm(email).encode()
    exp = int((now or time.time()) + 3600 * int(getattr(settings, "CRM_CONSENT_CONFIRM_TTL_HOURS", 72)))
    return f"{_enc(raw)}.{exp}.{_sig(_keys()[0], b'confirm:' + raw + b':' + str(exp).encode())}"


def email_from_confirm_token(token: str) -> Optional[str]:
    """The e-mail of a valid, unexpired confirmation token, else None."""
    try:
        part, exp, sig = token.split(".", 2)
        email, exp_i = _dec(part).decode(), int(exp)
    except (ValueError, UnicodeDecodeError):
        return None
    if exp_i < time.time() or email != norm(email):
        return None
    msg = b"confirm:" + email.encode() + b":" + str(exp_i).encode()
    ok = any(hmac.compare_digest(_sig(k, msg).encode(), sig.encode("utf-8", "replace")) for k in _keys())
    return email if ok else None


def erased_email(email: str) -> str:
    """Stand-in stored after erasure: a keyed hash, so a suppression still matches the address but cannot be read."""
    digest = hmac.new(_keys()[0], b"erase:" + norm(email).encode(), hashlib.sha256).hexdigest()[:40]
    return f"erased-{digest}@invalid"


async def consent_for(db: AsyncSession, email: str) -> Optional[CRMContactConsent]:
    rows = (await db.execute(select(CRMContactConsent).where(
        CRMContactConsent.email.in_([norm(email), erased_email(email)])))).scalars().all()
    # an erased row still suppressing the address wins over a newer live row (unsubscribe survives erasure)
    return next((r for r in rows if r.status in SUPPRESSING), None) or next((r for r in rows if r.email == norm(email)),
                                                                           rows[0] if rows else None)


async def record_consent(db: AsyncSession, email: str, status: str, source: str, text: Optional[str] = None,
                         may_lift_unsubscribe: bool = False) -> CRMContactConsent:
    """Latest event wins, except: SUBSCRIBED never lifts BOUNCED/COMPLAINED, and lifts UNSUBSCRIBED only when the
    caller is an authorised person recording proof (may_lift_unsubscribe) — never an anonymous web form, where
    anybody can type anybody's address. PENDING only ever creates a row. Caller commits."""
    from sqlalchemy.dialects.postgresql import insert

    now = datetime.now(timezone.utc)
    # first event for an address: insert-or-skip, so two concurrent requests never collide on the unique email
    inserted = (await db.execute(insert(CRMContactConsent).values(
        id=uuid4(), email=norm(email), status=status, source=source[:100], consent_text=text, updated_at=now,
    ).on_conflict_do_nothing(index_elements=["email"]))).rowcount == 1
    row = await consent_for(db, email)
    blocked = status == "PENDING" or (status == "SUBSCRIBED" and (
        row.status in ("BOUNCED", "COMPLAINED") or (row.status == "UNSUBSCRIBED" and not may_lift_unsubscribe)))
    if not inserted and not blocked:
        row.status, row.source, row.updated_at = status, source[:100], now
        if text:
            row.consent_text = text
    await db.flush()  # sessions run without autoflush: make the event visible to the next check
    return row


async def request_confirmation(db: AsyncSession, email: str, source: str, text: Optional[str]) -> CRMContactConsent:
    """Web form / chat marketing consent: record PENDING and queue the confirmation e-mail (at most one per address
    per day, so a stranger's address cannot be flooded). Nothing is sent to an address that is already subscribed or
    suppressed. Caller commits."""
    row = await record_consent(db, email, "PENDING", source, text)
    if row.status == "PENDING":
        link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/consent-confirm?t={confirm_token(email)}"
        hours = int(getattr(settings, "CRM_CONSENT_CONFIRM_TTL_HOURS", 72))
        await queue(db, to_email=email, purpose="CONSENT",
                    dedupe_key=f"consent-confirm:{norm(email)}:{datetime.now(timezone.utc).date().isoformat()}",
                    subject="Please confirm you want e-mails from POVU", created_by="double-opt-in",
                    body=("Someone (we hope you) asked POVU to send e-mails about our products to this address.\n\n"
                          f"To confirm, open this link and press Confirm (valid for {hours} hours):\n{link}\n\n"
                          "If this was not you, ignore this e-mail: you will not be subscribed."))
    return row


async def confirm(db: AsyncSession, email: str, ip_hash: Optional[str]) -> Optional[CRMContactConsent]:
    """The confirmation click: PENDING becomes SUBSCRIBED with time and connection hash. An address that is
    unsubscribed, bounced or complained stays so (existing protections). None when there is no request. Caller commits."""
    row = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == norm(email))
                            .with_for_update())).scalar_one_or_none()
    current = await consent_for(db, email)          # an erased row may still suppress the address
    if current is not None and current.status in SUPPRESSING:
        return current
    if row is not None and row.status == "PENDING":
        now = datetime.now(timezone.utc)
        row.status, row.updated_at, row.confirmed_at, row.confirm_ip_hash = "SUBSCRIBED", now, now, ip_hash
        row.source = f"{row.source or ''} confirmed"[:100]
        await db.flush()
    return row


async def anonymise_consent(db: AsyncSession, email: str, actor: str) -> int:
    """Erasure request (docs/PRIVACY_RETENTION.md): replace the address on the consent row with a keyed hash and
    drop it from lead submissions. Status, timestamps and the consent text stay, so suppression and proof of what
    was agreed survive. Returns rows changed. Caller commits."""
    from sqlalchemy import delete, update

    from app.models.audit_log import AuditLog
    from app.models.crm import CRMLeadSubmission

    addr, gone = norm(email), erased_email(email)
    rows = {r.email: r for r in (await db.execute(select(CRMContactConsent).where(
        CRMContactConsent.email.in_([addr, gone])))).scalars().all()}
    if addr in rows and gone in rows:   # erased before: keep one row, a suppression first, else the newest
        old_wins = rows[gone].status in SUPPRESSING and rows[addr].status not in SUPPRESSING
        await db.execute(delete(CRMContactConsent).where(CRMContactConsent.email == (addr if old_wins else gone)))
    n = (await db.execute(update(CRMContactConsent).where(CRMContactConsent.email == addr)
                          .values(email=gone, confirm_ip_hash=None))).rowcount or 0
    n += (await db.execute(update(CRMLeadSubmission).where(CRMLeadSubmission.contact_email == addr)
                           .values(contact_email=None))).rowcount or 0
    db.add(AuditLog(actor_email=actor[:255], event_type="CONSENT_ANONYMISED", module="crm",
                    target_type="crm_contact_consent", target_id=gone[:100], details={"rows": n}))
    await db.flush()
    return n


async def _blocked_reason(db: AsyncSession, email: str, purpose: str) -> Optional[str]:
    consent = await consent_for(db, email)
    if consent is not None and consent.status in SUPPRESSING:
        if not (purpose == "INVOICE" and consent.status == "UNSUBSCRIBED"):   # a payment link is not marketing
            return f"address is {consent.status.lower()}"
    if purpose in ("SEQUENCE", "CAMPAIGN") and (consent is None or consent.status != "SUBSCRIBED"):
        return "no marketing consent on record"
    if purpose == "CONSENT":   # transactional, limited by its own dedupe key
        return None
    from app.services.crm_workspace_service import frequency_blocked   # M43.S01.T013 per-contact cap
    return await frequency_blocked(db, norm(email), purpose)


async def queue(db: AsyncSession, *, to_email: str, subject: str, body: str, purpose: str, dedupe_key: str,
                crm_record_id: Optional[UUID] = None, customer_id: Optional[UUID] = None,
                created_by: Optional[str] = None, send_after: Optional[datetime] = None,
                track: bool = False, body_html: Optional[str] = None) -> CRMOutboundMessage:
    """Queue (or return the already queued) message for this dedupe key. Caller commits."""
    if purpose not in PURPOSES:
        raise ValueError(f"purpose must be one of {PURPOSES}")
    from sqlalchemy.dialects.postgresql import insert

    key = dedupe_key[:200]
    existing = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == key))).scalar_one_or_none()
    if existing is not None:
        return existing
    now = datetime.now(timezone.utc)
    reason = await _blocked_reason(db, to_email, purpose)
    # insert-or-skip: a concurrent caller with the same key gets the one stored message, never a 500
    await db.execute(insert(CRMOutboundMessage).values(
        id=uuid4(), dedupe_key=key, purpose=purpose, to_email=_one_line(norm(to_email)), subject=_one_line(subject)[:300],
        body_text=body, crm_record_id=crm_record_id, customer_id=customer_id,
        status="SUPPRESSED" if reason else "QUEUED", status_reason=reason, attempts=0,
        next_attempt_at=send_after or now, created_by=created_by, created_at=now,
        track_engagement=bool(track) and purpose not in TRANSACTIONAL, body_html=body_html,
    ).on_conflict_do_nothing(index_elements=["dedupe_key"]))
    return (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == key))).scalar_one()


def _with_footer(msg: CRMOutboundMessage) -> tuple[str, dict]:
    if msg.purpose in TRANSACTIONAL:  # a document the customer is owed or a confirmation request: no unsubscribe link
        return msg.body_text, {}
    token = unsubscribe_token(msg.to_email)
    page = f"{settings.PUBLIC_APP_URL.rstrip('/')}/unsubscribe?t={token}"
    one_click = f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/unsubscribe?t={token}"
    body = f"{msg.body_text}\n\n--\nTo stop receiving these e-mails: {page}"
    return body, {"List-Unsubscribe": f"<{one_click}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}


async def deliver_due(db: AsyncSession, now: Optional[datetime] = None) -> dict:
    """Send due QUEUED mail. Rows are claimed as SENDING (SKIP LOCKED) and committed before any SMTP I/O, so
    concurrent workers never pick the same message and no lock is held while talking to the server. A send
    interrupted by a crash is never retried automatically (the server may have accepted it): it is marked
    FAILED for a person to check."""
    from app.services.email_sender import send_email

    now = now or datetime.now(timezone.utc)
    stale = (await db.execute(select(CRMOutboundMessage).where(
        CRMOutboundMessage.status == "SENDING", CRMOutboundMessage.next_attempt_at < now - STALE_SENDING)
        .with_for_update(skip_locked=True))).scalars().all()
    for msg in stale:
        msg.status, msg.status_reason = "FAILED", "interrupted while sending; check the recipient before retrying"
    await db.commit()
    if not (settings.CRM_OUTBOUND_EMAIL_ENABLED and settings.SMTP_HOST):
        return {"sent": 0, "failed": 0, "suppressed": 0, "waiting": "outbound e-mail is not enabled"}
    rows = (await db.execute(select(CRMOutboundMessage).where(
        CRMOutboundMessage.status == "QUEUED", CRMOutboundMessage.next_attempt_at <= now)
        .order_by(CRMOutboundMessage.created_at).limit(max(1, settings.CRM_OUTBOUND_MAX_PER_TICK))
        .with_for_update(skip_locked=True))).scalars().all()
    counts = {"sent": 0, "failed": 0, "suppressed": 0}
    claimed = []
    for msg in rows:
        reason = await _blocked_reason(db, msg.to_email, msg.purpose)
        if reason:  # unsubscribed or bounced after queuing
            msg.status, msg.status_reason = "SUPPRESSED", reason
            counts["suppressed"] += 1
        else:
            msg.status, msg.next_attempt_at = "SENDING", now
            msg.attempts += 1
            claimed.append(msg)
            await db.flush()      # the next message's frequency-cap check must see this claim (review M43 #5)
    await db.commit()
    for msg in claimed:  # ponytail: one SMTP connection per message; reuse one if volumes grow
        msg.next_attempt_at = datetime.now(timezone.utc)  # stale-SENDING clock starts when this send starts
        await db.commit()
        body, headers = _with_footer(msg)
        html = None
        from app.services import crm_engagement_service as engagement
        tracked = await engagement.may_track(db, msg)
        if msg.body_html:                             # M44.S01.T001 designed e-mail
            html = engagement.with_unsubscribe(msg, msg.body_html)
            if tracked:
                html, msg.tracked_links = engagement.track_html(msg, html)
                await db.commit()
        elif tracked:                                 # M43.S01.T006 opt-in tracking of plain mail
            html, msg.tracked_links = engagement.render_html(msg, body)
            await db.commit()
        try:
            # html only when tracked: existing callers/fakes keep the 4-argument call
            msg.provider_message_id = await asyncio.to_thread(send_email, msg.to_email, msg.subject, body, headers,
                                                              **({"html": html} if html else {}))
            msg.status, msg.sent_at, msg.status_reason = "SENT", datetime.now(timezone.utc), None
            counts["sent"] += 1
        except Exception as exc:
            # users see the error class and SMTP code only; server banners and auth replies go to the log
            code = getattr(exc, "smtp_code", None)
            msg.status_reason = f"{exc.__class__.__name__}" + (f" (SMTP {code})" if code else "")
            logger.warning("CRM e-mail %s to %s failed: %s", msg.id, msg.to_email, exc)
            if msg.attempts >= MAX_ATTEMPTS:
                msg.status = "FAILED"
                counts["failed"] += 1
            else:
                msg.status, msg.next_attempt_at = "QUEUED", now + timedelta(minutes=5 * msg.attempts)
        await db.commit()
    return counts
