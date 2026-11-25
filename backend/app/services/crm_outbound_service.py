"""M36 consent register and CRM e-mail outbox (foundation for sequences and campaigns).

- Every CRM e-mail is queued with a dedupe key; the same key is never sent twice.
- SEQUENCE and CAMPAIGN mail needs a SUBSCRIBED consent; UNSUBSCRIBED / BOUNCED / COMPLAINED addresses are
  suppressed for every purpose except MANUAL one-to-one mail to non-suppressed addresses.
- Suppression is checked when queuing and again right before sending (an unsubscribe in between wins).
- Delivery uses the configured SMTP server only when CRM_OUTBOUND_EMAIL_ENABLED is on; otherwise mail stays
  QUEUED. A message becomes SENT only after the SMTP server accepted it.
- Every message carries a signed unsubscribe link and RFC 8058 one-click List-Unsubscribe headers.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMContactConsent, CRMOutboundMessage

logger = logging.getLogger(__name__)

PURPOSES = ("MANUAL", "SEQUENCE", "CAMPAIGN", "INVOICE")  # INVOICE: transactional, no marketing footer
SUPPRESSING = ("UNSUBSCRIBED", "BOUNCED", "COMPLAINED")
MAX_ATTEMPTS = 3
STALE_SENDING = timedelta(minutes=15)


def norm(email: str) -> str:
    return (email or "").strip().lower()


def _one_line(text: str) -> str:
    """Header values never carry line breaks (no header injection through subject or address)."""
    return " ".join((text or "").split())


def unsubscribe_token(email: str) -> str:
    raw = norm(email).encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), b"unsub:" + raw, hashlib.sha256).digest()[:16]
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return f"{enc(raw)}.{enc(sig)}"


def email_from_token(token: str) -> Optional[str]:
    try:
        part, _ = token.split(".", 1)
        email = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    return email if hmac.compare_digest(unsubscribe_token(email).encode(), token.encode("utf-8", "replace")) else None


async def consent_for(db: AsyncSession, email: str) -> Optional[CRMContactConsent]:
    return (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == norm(email)))).scalar_one_or_none()


async def record_consent(db: AsyncSession, email: str, status: str, source: str, text: Optional[str] = None,
                         may_lift_unsubscribe: bool = False) -> CRMContactConsent:
    """Latest event wins, except: SUBSCRIBED never lifts BOUNCED/COMPLAINED, and lifts UNSUBSCRIBED only when the
    caller is an authorised person recording proof (may_lift_unsubscribe) — never an anonymous web form, where
    anybody can type anybody's address. Caller commits."""
    from sqlalchemy.dialects.postgresql import insert

    now = datetime.now(timezone.utc)
    # first event for an address: insert-or-skip, so two concurrent requests never collide on the unique email
    inserted = (await db.execute(insert(CRMContactConsent).values(
        id=uuid4(), email=norm(email), status=status, source=source[:100], consent_text=text, updated_at=now,
    ).on_conflict_do_nothing(index_elements=["email"]))).rowcount == 1
    row = await consent_for(db, email)
    blocked = status == "SUBSCRIBED" and (row.status in ("BOUNCED", "COMPLAINED")
                                          or (row.status == "UNSUBSCRIBED" and not may_lift_unsubscribe))
    if not inserted and not blocked:
        row.status, row.source, row.updated_at = status, source[:100], now
        if text:
            row.consent_text = text
    await db.flush()  # sessions run without autoflush: make the event visible to the next check
    return row


async def _blocked_reason(db: AsyncSession, email: str, purpose: str) -> Optional[str]:
    consent = await consent_for(db, email)
    if consent is not None and consent.status in SUPPRESSING:
        return f"address is {consent.status.lower()}"
    if purpose in ("SEQUENCE", "CAMPAIGN") and (consent is None or consent.status != "SUBSCRIBED"):
        return "no marketing consent on record"
    return None


async def queue(db: AsyncSession, *, to_email: str, subject: str, body: str, purpose: str, dedupe_key: str,
                crm_record_id: Optional[UUID] = None, customer_id: Optional[UUID] = None,
                created_by: Optional[str] = None, send_after: Optional[datetime] = None,
                track: bool = False) -> CRMOutboundMessage:
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
        track_engagement=bool(track) and purpose != "INVOICE",
    ).on_conflict_do_nothing(index_elements=["dedupe_key"]))
    return (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key == key))).scalar_one()


def _with_footer(msg: CRMOutboundMessage) -> tuple[str, dict]:
    if msg.purpose == "INVOICE":  # a document the customer is owed, not marketing: no unsubscribe link
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
    await db.commit()
    for msg in claimed:  # ponytail: one SMTP connection per message; reuse one if volumes grow
        msg.next_attempt_at = datetime.now(timezone.utc)  # stale-SENDING clock starts when this send starts
        await db.commit()
        body, headers = _with_footer(msg)
        html = None
        from app.services import crm_engagement_service as engagement
        if await engagement.may_track(db, msg):      # M43.S01.T006 opt-in tracking
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
