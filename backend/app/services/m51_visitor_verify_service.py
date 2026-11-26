"""M51.S01.T009 secure e-mail verification for anonymous, consenting website visitors.

Flow: the visitor ticks consent and types an address → request() → (if eligible) a one-time link AND 6-digit code are
delivered to the LOCAL outbox (or Mailpit on loopback) → confirm() with the browser's visitor + session ids and the
token (or the code plus the address) → the existing web_identities row gets verified_at, which is what form shortening
(crm_lead_capture_service) and CMS personalization (cms_personalize) already require.

Controls:
- token (32 random bytes) and code are stored only as keyed hashes; 15 minute expiry; single use through one atomic
  UPDATE ... WHERE consumed_at IS NULL; at most 5 wrong attempts per challenge.
- bound to the browser: the confirm call must carry the same visitor id and session id (as keyed hashes) AND, for the
  code path, the same address. A link opened in another browser verifies nothing.
- anti-enumeration: request() always returns the same body whether the address is known, rate-limited, unsendable or
  fine; confirm() returns the same {"verified": false} for every failure. Only the per-IP limit answers 429 (it does not
  depend on the address).
- rate limits: per IP hash, per address hash, per visitor hash per hour (settings below), counted from stored rows.
- explicit consent: marketing consent is recorded from the visitor's explicit ``consent`` flag (analytics choice is kept).
- no cross-account merge: only the visitor↔e-mail row in web_identities is written; CRM contacts, portal users and
  other visitors are never merged. Revocation clears it again (visitor or staff).
- no real e-mail: M51_VERIFY_MAIL_MODE = outbox (default, DB table) | mailpit (SMTP to M51_MAILPIT_HOST, loopback only
  or *.localhost/*.test) | off. Failure to deliver leaves the visitor unverified (full forms stay, safe fallback).

Settings (getattr): M51_VERIFY_MAIL_MODE (str "outbox"), M51_MAILPIT_HOST ("127.0.0.1"), M51_MAILPIT_PORT (1025),
M51_VERIFY_TTL_MIN (15), M51_VERIFY_IP_PER_HOUR (10), M51_VERIFY_EMAIL_PER_HOUR (3), M51_VERIFY_VISITOR_PER_HOUR (5).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import _is_local_host
from app.models.crm import WebIdentity
from app.models.m51_seo import M51VisitorMailOutbox, M51VisitorVerification
from app.services import web_analytics_service as wa

GENERIC = {"status": "SENT_IF_ELIGIBLE", "message": "If this address can be verified, a message with a link and a code "
           "is on its way. It works for 15 minutes in this browser."}
FAIL = {"verified": False}
SUBJECT = {"en": "Confirm your e-mail address", "sw": "Thibitisha barua pepe yako", "tr": "E-posta adresinizi doğrulayın"}
BODY = {"en": "Open this link in the same browser: {link}\nOr enter this code: {code}\nIt works for {ttl} minutes. If you did not ask for it, ignore this message.",
        "sw": "Fungua kiungo hiki katika kivinjari kilekile: {link}\nAu weka msimbo huu: {code}\nUnatumika kwa dakika {ttl}. Kama hukuuomba, puuza ujumbe huu.",
        "tr": "Bu bağlantıyı aynı tarayıcıda açın: {link}\nVeya bu kodu girin: {code}\n{ttl} dakika geçerlidir. Siz istemediyseniz bu iletiyi yok sayın."}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _h(kind: str, raw: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"m51verify:{kind}:{raw}".encode(), hashlib.sha256).hexdigest()


def norm_email(e: str) -> str:
    return (e or "").strip().lower()[:254]


async def _count(db: AsyncSession, col, val: str) -> int:
    return int((await db.execute(select(func.count()).select_from(M51VisitorVerification).where(
        col == val, M51VisitorVerification.created_at > _now() - timedelta(hours=1)))).scalar_one())


class RateLimited(Exception):
    pass


async def request(db: AsyncSession, visitor: str, session: str, email: str, consent: bool, ip: str, locale: str = "en") -> dict:
    email = norm_email(email)
    ip_h, em_h, vh = _h("ip", ip or "?"), _h("em", email), wa.hashed("v", visitor)
    if await _count(db, M51VisitorVerification.ip_hash, ip_h) >= int(getattr(settings, "M51_VERIFY_IP_PER_HOUR", 10)):
        raise RateLimited()
    if not consent:
        return dict(GENERIC)                                        # no consent: nothing is stored or sent, same answer
    if await _count(db, M51VisitorVerification.email_hash, em_h) >= int(getattr(settings, "M51_VERIFY_EMAIL_PER_HOUR", 3)) \
            or await _count(db, M51VisitorVerification.visitor_hash, vh) >= int(getattr(settings, "M51_VERIFY_VISITOR_PER_HOUR", 5)):
        return dict(GENERIC)
    mode = getattr(settings, "M51_VERIFY_MAIL_MODE", "outbox")
    if mode not in ("outbox", "mailpit"):
        return dict(GENERIC)
    latest = (await wa._latest_consent(db, vh))
    await wa.record_consent(db, visitor, bool(latest.analytics) if latest else False, True)
    ttl = int(getattr(settings, "M51_VERIFY_TTL_MIN", 15))
    token, code, vid = secrets.token_urlsafe(32), f"{secrets.randbelow(10**6):06d}", uuid.uuid4()
    row = M51VisitorVerification(id=vid, visitor_hash=vh, session_hash=wa.hashed("s", session), email_hash=em_h, email=email,
                                 ip_hash=ip_h, token_hash=_h("tok", token), code_hash=_h("code", f"{vid}:{code}"),
                                 expires_at=_now() + timedelta(minutes=ttl))
    db.add(row)
    await db.flush()
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/verify-email#t={token}"
    loc = locale if locale in SUBJECT else "en"
    subject, body = SUBJECT[loc], BODY[loc].format(link=link, code=code, ttl=ttl)
    ok = await _deliver(db, row, email, subject, body, mode)
    if not ok:                                                       # safe fallback: nothing pending, visitor unverified
        row.revoked_at, row.email = _now(), None
    return dict(GENERIC)


async def _deliver(db: AsyncSession, row, to: str, subject: str, body: str, mode: str) -> bool:
    if mode == "outbox":
        db.add(M51VisitorMailOutbox(verification_id=row.id, to_email=to, subject=subject, body=body, channel="OUTBOX"))
        await db.flush()
        return True
    host = getattr(settings, "M51_MAILPIT_HOST", "127.0.0.1")
    if not _is_local_host(host):                                     # never a real mail server
        return False
    import smtplib
    from email.message import EmailMessage

    def send():
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = "no-reply@povu-demo.test", to, subject
        m.set_content(body)
        with smtplib.SMTP(host, int(getattr(settings, "M51_MAILPIT_PORT", 1025)), timeout=5) as s:
            s.send_message(m)
    try:
        await asyncio.to_thread(send)
    except OSError:
        return False
    db.add(M51VisitorMailOutbox(verification_id=row.id, to_email=to, subject=subject, body=body, channel="MAILPIT"))
    await db.flush()
    return True


async def confirm(db: AsyncSession, visitor: str, session: str, token: Optional[str], code: Optional[str],
                  email: Optional[str]) -> dict:
    vh, sh = wa.hashed("v", visitor), wa.hashed("s", session)
    now = _now()
    row = None
    if token:
        row = (await db.execute(select(M51VisitorVerification).where(
            M51VisitorVerification.token_hash == _h("tok", token)).with_for_update())).scalar_one_or_none()
    elif code and email:
        row = (await db.execute(select(M51VisitorVerification).where(
            M51VisitorVerification.email_hash == _h("em", norm_email(email)), M51VisitorVerification.visitor_hash == vh,
            M51VisitorVerification.consumed_at.is_(None), M51VisitorVerification.revoked_at.is_(None))
            .order_by(M51VisitorVerification.created_at.desc()).limit(1).with_for_update())).scalar_one_or_none()
    if row is None or row.consumed_at or row.revoked_at or row.expires_at <= now or row.attempts >= 5:
        return dict(FAIL)
    bound = hmac.compare_digest(row.visitor_hash, vh) and hmac.compare_digest(row.session_hash, sh)
    if token:
        good = bound
    else:
        good = bound and hmac.compare_digest(row.code_hash, _h("code", f"{row.id}:{code}"))
    if not good:
        row.attempts += 1
        if row.attempts >= 5:
            row.revoked_at, row.email = now, None
            await db.execute(delete(M51VisitorMailOutbox).where(M51VisitorMailOutbox.verification_id == row.id))
        await db.flush()
        return dict(FAIL)
    won = (await db.execute(update(M51VisitorVerification).where(
        M51VisitorVerification.id == row.id, M51VisitorVerification.consumed_at.is_(None))
        .values(consumed_at=now).returning(M51VisitorVerification.email))).first()
    if won is None:
        return dict(FAIL)
    address = won[0]
    row.email = None
    await db.execute(delete(M51VisitorMailOutbox).where(M51VisitorMailOutbox.verification_id == row.id))
    linked = await wa.identify(db, visitor, address, verified=True)   # needs marketing consent: recorded at request time
    if not linked:
        return dict(FAIL)
    await wa.collect(db, visitor, session, [{"event_id": uuid.uuid4().hex, "kind": "CUSTOM", "name": "visitor_email_verified",
                                              "path": "/"}], "")      # counted only with analytics consent
    return {"verified": True}


async def status(db: AsyncSession, visitor: str) -> dict:
    return {"verified": (await wa.verified_email(db, visitor)) is not None}


async def revoke_visitor(db: AsyncSession, visitor: str) -> None:
    vh = wa.hashed("v", visitor)
    await db.execute(update(WebIdentity).where(WebIdentity.visitor_hash == vh).values(verified_at=None))
    await _revoke_pending(db, M51VisitorVerification.visitor_hash == vh)


async def revoke_address(db: AsyncSession, email: str) -> int:
    e = norm_email(email)
    n = (await db.execute(update(WebIdentity).where(WebIdentity.email == e).values(verified_at=None))).rowcount or 0
    await _revoke_pending(db, M51VisitorVerification.email_hash == _h("em", e))
    return n


async def _revoke_pending(db: AsyncSession, cond) -> None:
    ids = (await db.execute(select(M51VisitorVerification.id).where(cond, M51VisitorVerification.consumed_at.is_(None),
                                                                    M51VisitorVerification.revoked_at.is_(None)))).scalars().all()
    if ids:
        await db.execute(update(M51VisitorVerification).where(M51VisitorVerification.id.in_(ids))
                         .values(revoked_at=_now(), email=None))
        await db.execute(delete(M51VisitorMailOutbox).where(M51VisitorMailOutbox.verification_id.in_(ids)))


async def purge_expired(db: AsyncSession) -> int:
    cut = _now() - timedelta(days=7)
    await db.execute(delete(M51VisitorMailOutbox).where(M51VisitorMailOutbox.created_at < _now() - timedelta(hours=1)))
    return (await db.execute(delete(M51VisitorVerification).where(M51VisitorVerification.created_at < cut))).rowcount or 0
