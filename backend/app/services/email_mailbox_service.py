"""M36.S01.T001 two-way e-mail over IMAP (in) and SMTP (out).

Works with any mailbox that allows IMAP/SMTP login; Gmail and Microsoft 365 with an app password.
M43.S01.T001/T002: a mailbox may instead be connected with Google / Microsoft OAuth (Gmail API, Graph); see
mail_api_adapters. The rest of the pipeline (parse, store, threading, dedupe) is shared.

- Credentials: the password is stored Fernet-encrypted (key derived from SECRET_KEY, its own salt) and
  wiped on disconnect. It is never returned by the API.
- Import: new INBOX messages after the last imported UID; a message whose Message-ID is already in the
  mailbox is skipped, so a replayed or re-delivered mail never doubles. Replies join the thread of the
  message they answer (In-Reply-To / References). Attachments: name, type and size only.
- A sender whose address is a customer's e-mail links the new thread to that customer; a reply whose
  subject starts with "unsubscribe" records the unsubscribe in the CRM consent register.
- Send: real SMTP delivery with Message-ID / In-Reply-To / References, then stored in the thread.
"""
from __future__ import annotations

import asyncio
import hashlib
import imaplib
import logging
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.message import EmailMessage as MimeMessage
from email.utils import getaddresses, make_msgid, parsedate_to_datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_integration import EmailAccount, EmailMessage, EmailProvider, EmailThread
from app.models.sales import Customer

log = logging.getLogger(__name__)

FIRST_SYNC_LIMIT = 200  # first connection imports only the newest messages
BATCH_LIMIT = 200       # later runs import at most this many; the rest follows on the next run
ACCOUNT_SYNC_TIMEOUT = 120  # seconds per mailbox per run (a slow server must not stall everyone)
TIMEOUT = 30
DEFAULTS = {
    EmailProvider.GMAIL: ("imap.gmail.com", 993, "smtp.gmail.com", 465),
    EmailProvider.OUTLOOK: ("outlook.office365.com", 993, "smtp.office365.com", 587),
}


class MailboxError(Exception):
    """Connection, login or delivery failed; the message is safe to show to the mailbox owner."""


class MailboxInputError(MailboxError):
    """Bad recipient, subject or sender name (caller's input)."""


# ── credentials ───────────────────────────────────────────────────────────────

def _cipher():
    import base64

    from cryptography.fernet import Fernet

    from app.core.config import settings
    key = hashlib.sha256(b"fmcg-erp:mailbox-password:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(secret: str) -> str:
    return _cipher().encrypt(secret.encode()).decode()


def decrypt(token: Optional[str]) -> str:
    from cryptography.fernet import InvalidToken

    if not token:
        raise MailboxError("Mailbox is not connected.")
    try:
        return _cipher().decrypt(token.encode()).decode()
    except InvalidToken as e:  # SECRET_KEY changed since the password was stored
        raise MailboxError("The stored password can no longer be read; connect the mailbox again.") from e


def is_connected(acc: EmailAccount) -> bool:
    if acc.oauth_connection_id:   # M43.S01.T001/T002: Gmail API / Microsoft Graph over delegated OAuth
        conn = acc.oauth_connection
        return bool(acc.is_active and conn is not None and conn.status == "CONNECTED")
    return bool(acc.secret_enc and acc.imap_host and acc.smtp_host and acc.is_active)


# ── where we may connect ──────────────────────────────────────────────────────

IMAP_PORTS, SMTP_PORTS = {143, 993}, {25, 465, 587}


def validate_host(host: str, port: int, ports: set[int]) -> None:
    """Mail servers only: standard ports, and (unless MAIL_ALLOW_PRIVATE_HOSTS for a self-hosted server)
    never an address inside our own network, so the mailbox form cannot be used to probe it."""
    import ipaddress
    import socket

    from app.core.config import settings

    if port not in ports:
        raise MailboxError(f"Port {port} is not a mail port ({', '.join(map(str, sorted(ports)))}).")
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError) as e:
        raise MailboxError(f"Mail server {host} was not found.") from e
    if getattr(settings, "MAIL_ALLOW_PRIVATE_HOSTS", False):
        return
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise MailboxError(f"Mail server {host} is not a public address.")


def _public_error(kind: str, e: Exception) -> MailboxError:
    """Log the server's own text; show the user a fixed message (no banners, no network details)."""
    log.info("mailbox %s failed: %s", kind, e)
    if isinstance(e, (imaplib.IMAP4.error, smtplib.SMTPAuthenticationError)):
        return MailboxError(f"{kind}: the mail server refused the login (check the address and app password).")
    return MailboxError(f"{kind}: could not connect to the mail server.")


# ── blocking protocol helpers (run in a worker thread) ────────────────────────

def _imap(host: str, port: int) -> imaplib.IMAP4:
    validate_host(host, port, IMAP_PORTS)  # also re-checked at every connect (DNS may change)
    ctx = ssl.create_default_context()
    if port == 993:
        return imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=TIMEOUT)
    conn = imaplib.IMAP4(host, port, timeout=TIMEOUT)
    conn.starttls(ssl_context=ctx)
    return conn


def _smtp(host: str, port: int) -> smtplib.SMTP:
    validate_host(host, port, SMTP_PORTS)
    ctx = ssl.create_default_context()
    if port == 465:
        return smtplib.SMTP_SSL(host, port, context=ctx, timeout=TIMEOUT)
    conn = smtplib.SMTP(host, port, timeout=TIMEOUT)
    conn.starttls(context=ctx)
    return conn


def check_login(imap_host, imap_port, smtp_host, smtp_port, user, password) -> None:
    try:
        conn = _imap(imap_host, imap_port)
        try:
            conn.login(user, password)
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    except (imaplib.IMAP4.error, OSError) as e:
        raise _public_error("IMAP login failed", e) from e
    try:
        with _smtp(smtp_host, smtp_port) as s:
            s.login(user, password)
    except (smtplib.SMTPException, OSError) as e:
        raise _public_error("SMTP login failed", e) from e


def fetch_new(host, port, user, password, uidvalidity, last_uid) -> tuple[int, list[tuple[int, bytes]]]:
    """Return (uidvalidity, [(uid, raw message)]) for INBOX messages after last_uid (all, if UIDVALIDITY changed)."""
    try:
        conn = _imap(host, port)
        try:
            conn.login(user, password)
            conn.select("INBOX", readonly=True)
            validity = int(conn.response("UIDVALIDITY")[1][0])
            start = (last_uid or 0) + 1 if validity == uidvalidity else 1
            typ, data = conn.uid("SEARCH", None, f"UID {start}:*")
            uids = sorted(u for u in (int(x) for x in (data[0] or b"").split()) if u >= start)
            if not last_uid or validity != uidvalidity:
                uids = uids[-FIRST_SYNC_LIMIT:]
            else:
                uids = uids[:BATCH_LIMIT]  # the rest comes on the next run
            out = []
            for uid in uids:
                typ, msg = conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
                raw = next((part[1] for part in msg if isinstance(part, tuple)), None)
                if raw:
                    out.append((uid, raw))
            return validity, out
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    except (imaplib.IMAP4.error, OSError) as e:
        raise _public_error("IMAP sync failed", e) from e


def smtp_send(host, port, user, password, mime: MimeMessage) -> None:
    try:
        with _smtp(host, port) as s:
            s.login(user, password)
            s.send_message(mime)
    except smtplib.SMTPRecipientsRefused as e:
        log.info("mailbox send refused recipients: %s", e)
        raise MailboxError("Sending failed: the mail server refused a recipient address.") from e
    except (smtplib.SMTPException, OSError) as e:
        raise _public_error("Sending failed", e) from e


# ── parsing ───────────────────────────────────────────────────────────────────

_ID = re.compile(r"<[^<>\s]+>")


def _ids(value: Optional[str]) -> list[str]:
    return _ID.findall(value or "")


@dataclass
class Parsed:
    message_id: str
    in_reply_to: Optional[str]
    references: list[str]
    from_email: str
    from_name: Optional[str]
    to: list[str]
    cc: list[str]
    subject: str
    text: str
    when: datetime
    attachments: list[dict] = field(default_factory=list)
    sender_verified: bool = False   # receiving server reported DMARC/DKIM pass for the From domain
    bounces: list[tuple[str, str]] = field(default_factory=list)  # (failed recipient, status) from a DSN
    bounced_message_id: Optional[str] = None                     # Message-ID of the mail that bounced


def _dsn(msg) -> tuple[list[tuple[str, str]], Optional[str]]:
    """RFC 3464 delivery report: permanently failed recipients and the original Message-ID."""
    if msg.get_content_type() != "multipart/report":
        return [], None
    failed, original = [], None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "message/delivery-status":
            for group in part.get_payload() or []:
                action = str(group.get("Action", "")).strip().lower()
                status = str(group.get("Status", "")).strip()
                rcpt = str(group.get("Final-Recipient", "") or group.get("Original-Recipient", ""))
                addr = rcpt.split(";", 1)[-1].strip().strip("<>").lower()
                if action == "failed" and status.startswith("5") and "@" in addr:
                    failed.append((addr[:254], status[:20]))
        elif ctype in ("message/rfc822", "text/rfc822-headers") and original is None:
            inner = part.get_payload(0) if ctype == "message/rfc822" else message_from_bytes(
                part.get_payload(decode=True) or b"", policy=policy.default)
            original = (_ids(str(inner.get("Message-ID", ""))) or [None])[0]
    return failed, original


def _clean(v: Optional[str]) -> Optional[str]:
    return v.replace("\x00", "") if v else v  # PostgreSQL text cannot hold NUL


_AUTH = re.compile(r"\b(dmarc|dkim)=pass\b([^;]*)", re.I)


def _verified(msg, from_email: str) -> bool:
    """True when the receiving server's Authentication-Results says DMARC passed, or DKIM passed for the
    From domain. Without it the From header is unauthenticated and must not change anyone's consent."""
    domain = from_email.rpartition("@")[2].lower()
    for header in msg.get_all("Authentication-Results", []) or []:
        for kind, rest in _AUTH.findall(str(header)):
            if kind.lower() == "dmarc":
                return True
            d = re.search(r"header\.(?:d|i)=@?([\w.-]+)", rest)
            if d and (d.group(1).lower() == domain or d.group(1).lower().endswith("." + domain)):
                return True
    return False


def _text(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        content = part.get_content()
    except Exception:
        return ""
    if part.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", content))
        content = re.sub(r"[ \t]+", " ", content)
    return _clean(content.strip())


def parse(raw: bytes) -> Parsed:
    msg = message_from_bytes(raw, policy=policy.default)
    sender = getaddresses([str(msg.get("From", ""))])
    name, addr = sender[0] if sender else ("", "")
    try:
        when = parsedate_to_datetime(str(msg.get("Date")))
        when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    except Exception:
        when = datetime.now(timezone.utc)
    mid = (_ids(str(msg.get("Message-ID", ""))) or [""])[0]
    if not mid:  # no Message-ID: derive a stable one so a re-fetch is still recognised
        mid = f"<sha256-{hashlib.sha256(raw).hexdigest()[:40]}@mailbox.local>"
    dsn = _dsn(msg)
    atts = []
    for part in msg.iter_attachments():
        payload = part.get_payload(decode=True) or b""
        atts.append({"name": part.get_filename() or "attachment", "type": part.get_content_type(), "size": len(payload)})
    return Parsed(
        message_id=mid, in_reply_to=(_ids(str(msg.get("In-Reply-To", ""))) or [None])[0],
        references=_ids(str(msg.get("References", ""))),
        from_email=_clean(addr.lower())[:255], from_name=_clean(name or None),
        to=[a.lower() for _, a in getaddresses([str(v) for v in msg.get_all("To", [])]) if a],
        cc=[a.lower() for _, a in getaddresses([str(v) for v in msg.get_all("Cc", [])]) if a],
        subject=_clean(str(msg.get("Subject", "") or "(no subject)"))[:1000], text=_text(msg), when=when,
        attachments=atts, sender_verified=_verified(msg, addr.lower()),
        bounces=dsn[0], bounced_message_id=dsn[1],
    )


# ── import ────────────────────────────────────────────────────────────────────

def _lock_key(account_id) -> int:
    return int(hashlib.sha256(str(account_id).encode()).hexdigest()[:15], 16)


async def _existing(db: AsyncSession, acc: EmailAccount, ids: list[str]) -> Optional[EmailMessage]:
    if not ids:
        return None
    return (await db.execute(select(EmailMessage).join(EmailThread, EmailThread.id == EmailMessage.thread_id)
                             .where(EmailThread.account_id == acc.id, EmailMessage.external_message_id.in_(ids))
                             .order_by(EmailMessage.received_at.desc()).limit(1))).scalar_one_or_none()


async def store(db: AsyncSession, acc: EmailAccount, p: Parsed) -> Optional[EmailMessage]:
    """Store one parsed message in its thread. Returns None when the mailbox already has it."""
    if await _existing(db, acc, [p.message_id]):
        return None
    parent = await _existing(db, acc, [x for x in [p.in_reply_to, *reversed(p.references)] if x])
    outbound = p.from_email == acc.email_address.lower()
    if parent is not None:
        thread = await db.get(EmailThread, parent.thread_id)
    else:
        thread = EmailThread(account_id=acc.id, subject=p.subject, participants=[], message_count=0, is_read=True)
        counterpart = (p.to or [None])[0] if outbound else p.from_email
        if counterpart:
            cust = (await db.execute(select(Customer.id, Customer.name).where(func.lower(Customer.email) == counterpart)
                                     .limit(1))).first()
            if cust:
                thread.linked_module, thread.linked_object_id, thread.linked_object_ref = "customer", cust[0], cust[1][:100]
        db.add(thread)
        await db.flush()
    msg = EmailMessage(thread_id=thread.id, external_message_id=p.message_id, in_reply_to=p.in_reply_to,
                       from_email=p.from_email or "unknown", from_name=p.from_name, to_emails=p.to, cc_emails=p.cc,
                       subject=p.subject, body_text=p.text, received_at=p.when, is_inbound=not outbound,
                       is_read=outbound, has_attachments=bool(p.attachments), attachments=p.attachments or None)
    db.add(msg)
    people = set(thread.participants or []) | {p.from_email, *p.to, *p.cc}
    thread.participants = sorted(x for x in people if x)[:50]
    thread.message_count = (thread.message_count or 0) + 1
    if not thread.last_message_at or p.when >= thread.last_message_at:
        thread.last_message_at, thread.snippet = p.when, (p.text or "")[:200]
    if p.bounces and p.bounced_message_id:
        await _apply_bounces(db, p)
    if not outbound:
        thread.is_read = False
        if re.sub(r"^((re|aw|fw|fwd)\s*:\s*)+", "", p.subject.strip(), flags=re.I).lower().startswith("unsubscribe"):
            if p.sender_verified:
                from app.services.crm_outbound_service import record_consent
                await record_consent(db, p.from_email, "UNSUBSCRIBED", "e-mail reply")
            else:  # forged From headers are trivial; leave it to staff (the message stays in the thread)
                log.info("unverified unsubscribe reply from %s not applied", p.from_email)
    await db.flush()
    return msg


async def _apply_bounces(db: AsyncSession, p: Parsed) -> None:
    """A permanent failure counts only when the report names a CRM e-mail we actually sent (its Message-ID
    and recipient match an outbox row): a forged bounce cannot silence a customer's address."""
    from app.models.crm import CRMOutboundMessage
    from app.services.crm_outbound_service import record_consent

    for rcpt, status in p.bounces:
        sent = (await db.execute(select(CRMOutboundMessage).where(
            CRMOutboundMessage.provider_message_id == p.bounced_message_id,
            func.lower(CRMOutboundMessage.to_email) == rcpt))).scalar_one_or_none()
        if sent is None:
            log.info("bounce for %s ignored: no matching CRM e-mail", rcpt)
            continue
        await record_consent(db, rcpt, "BOUNCED", "bounce report")
        sent.status_reason = f"bounced ({status})"


async def sync_account(db: AsyncSession, acc: EmailAccount) -> dict:
    """Import new mail for one connected mailbox. Caller commits."""
    from sqlalchemy import text

    if acc.oauth_connection_id:
        return await _sync_api_account(db, acc)

    password = decrypt(acc.secret_enc)
    args = (acc.imap_host, acc.imap_port, acc.username, password, acc.imap_uidvalidity, acc.imap_last_uid)
    await db.commit()  # no transaction or DB lock is held during the network I/O
    try:
        validity, raws = await asyncio.to_thread(fetch_new, *args)
    except MailboxError as e:
        await db.refresh(acc)
        acc.sync_error = str(e)[:1000]
        raise
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _lock_key(acc.id)})
    await db.refresh(acc)
    imported = skipped = failed = 0
    last = acc.imap_last_uid if validity == acc.imap_uidvalidity else 0
    for uid, raw in raws:
        try:
            async with db.begin_nested():  # one bad message must not block the mailbox
                stored = await store(db, acc, parse(raw))
        except Exception:
            log.warning("mailbox %s: message UID %s could not be imported", acc.id, uid, exc_info=True)
            failed += 1
            stored = None
        else:
            imported, skipped = (imported + 1, skipped) if stored else (imported, skipped + 1)
        last = max(last or 0, uid)
    acc.imap_uidvalidity, acc.imap_last_uid = validity, last
    acc.last_sync_at, acc.sync_error = datetime.now(timezone.utc), None
    return {"imported": imported, "skipped": skipped, "failed": failed}


async def _sync_api_account(db: AsyncSession, acc: EmailAccount) -> dict:
    """Gmail API / Graph import: raw MIME through the same parse/store; the cursor advances only after storing."""
    from sqlalchemy import text

    from app.services import mail_api_adapters as api
    from app.services import oauth_service as oauth

    conn = acc.oauth_connection
    try:
        raws, cursor = await api.fetch(db, conn)
    except (oauth.OAuthError, api.MailApiError) as e:
        acc.sync_error = str(e)[:1000]
        raise MailboxError(str(e)) from None
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _lock_key(acc.id)})
    imported = skipped = failed = 0
    for raw in raws:
        try:
            async with db.begin_nested():
                stored = await store(db, acc, parse(raw))
        except Exception:
            log.warning("mailbox %s: an API message could not be imported", acc.id, exc_info=True)
            failed, stored = failed + 1, None
        else:
            imported, skipped = (imported + 1, skipped) if stored else (imported, skipped + 1)
    conn.sync_cursor, conn.last_sync_at, conn.last_error = cursor, datetime.now(timezone.utc), None
    acc.last_sync_at, acc.sync_error = conn.last_sync_at, None
    return {"imported": imported, "skipped": skipped, "failed": failed}


# ── send ──────────────────────────────────────────────────────────────────────

async def send(db: AsyncSession, acc: EmailAccount, *, to: list[str], cc: list[str], subject: str, body: str,
               thread: Optional[EmailThread], sent_by: Any, link: dict,
               calendar: Optional[tuple[str, str]] = None) -> EmailThread:
    """Deliver through the mailbox's SMTP server, then store the message. Nothing is stored when delivery fails."""
    if not is_connected(acc):
        raise MailboxError("Connect this mailbox (Google, Microsoft or IMAP/SMTP) before sending; nothing was sent.")
    # same suppression as the CRM outbox: unsubscribed / bounced / complained addresses get no mail of any kind
    from app.models.crm import CRMContactConsent
    from app.services.crm_outbound_service import SUPPRESSING, norm
    addrs = {norm(a) for a in [*to, *cc] if a}
    if addrs:
        hit = (await db.execute(select(CRMContactConsent.email, CRMContactConsent.status).where(
            CRMContactConsent.email.in_(addrs), CRMContactConsent.status.in_(SUPPRESSING))
            .order_by(CRMContactConsent.email).limit(1))).first()
        if hit:
            raise MailboxInputError(f"Not sent: {hit[0]} is {hit[1].lower()} and receives no e-mail from us.")
    mime = MimeMessage()
    try:  # the e-mail policy refuses CR/LF in headers (no header injection); report it as bad input
        mime["From"] = f"{acc.display_name} <{acc.email_address}>" if acc.display_name else acc.email_address
        mime["To"] = ", ".join(to)
        if cc:
            mime["Cc"] = ", ".join(cc)
        mime["Subject"] = subject
    except ValueError as e:
        raise MailboxInputError("Recipient, subject or sender name contains characters that are not allowed.") from e
    mime["Message-ID"] = make_msgid(domain=acc.email_address.rsplit("@", 1)[-1])
    refs: list[str] = []
    if thread is not None:
        prior = (await db.execute(select(EmailMessage.external_message_id).where(
            EmailMessage.thread_id == thread.id, EmailMessage.external_message_id.is_not(None))
            .order_by(EmailMessage.received_at))).scalars().all()
        refs = [r for r in prior if r][-10:]
        if refs:
            mime["In-Reply-To"], mime["References"] = refs[-1], " ".join(refs)
    mime.set_content(body)
    if calendar:  # (METHOD, iCalendar text): Google/Outlook show it as an invitation
        method, ics = calendar
        mime.add_attachment(ics.encode(), maintype="text", subtype="calendar", filename="invite.ics",
                            params={"method": method, "charset": "UTF-8"})
    if acc.oauth_connection_id:
        from app.services import mail_api_adapters as api
        from app.services import oauth_service as oauth
        try:
            await api.send_raw(db, acc.oauth_connection, mime.as_bytes())
        except (oauth.OAuthError, api.MailApiError) as e:
            raise MailboxError(str(e)) from None
    else:
        await asyncio.to_thread(smtp_send, acc.smtp_host, acc.smtp_port, acc.username, decrypt(acc.secret_enc), mime)

    now = datetime.now(timezone.utc)
    if thread is None:
        thread = EmailThread(account_id=acc.id, subject=subject, participants=sorted({acc.email_address.lower(), *to, *cc}),
                             is_read=True, message_count=0, **link)
        db.add(thread)
        await db.flush()
    db.add(EmailMessage(thread_id=thread.id, external_message_id=str(mime["Message-ID"]), in_reply_to=refs[-1] if refs else None,
                        from_email=acc.email_address, from_name=acc.display_name or getattr(sent_by, "full_name", None),
                        to_emails=to, cc_emails=cc, subject=subject, body_text=body, received_at=now,
                        is_inbound=False, is_read=True, sent_by_id=getattr(sent_by, "id", None)))
    thread.message_count = (thread.message_count or 0) + 1
    thread.last_message_at, thread.snippet = now, body[:200]
    await db.flush()
    return thread


# ── background ────────────────────────────────────────────────────────────────

async def sync_all(db: AsyncSession) -> dict:
    from sqlalchemy import and_, or_

    from app.models.oauth_connection import OAuthConnection
    accounts = (await db.execute(select(EmailAccount).outerjoin(
        OAuthConnection, OAuthConnection.id == EmailAccount.oauth_connection_id).where(
        EmailAccount.is_active.is_(True), EmailAccount.sync_enabled.is_(True),
        or_(and_(EmailAccount.secret_enc.is_not(None), EmailAccount.imap_host.is_not(None)),
            OAuthConnection.status == "CONNECTED")))).scalars().all()
    result = {"accounts": len(accounts), "imported": 0, "failed": 0}
    for acc in accounts:
        try:
            r = await asyncio.wait_for(sync_account(db, acc), ACCOUNT_SYNC_TIMEOUT)
            await db.commit()
            result["imported"] += r["imported"]
        except Exception as e:
            await db.rollback()
            result["failed"] += 1
            log.warning("mailbox sync failed for account %s", acc.id, exc_info=True)
            try:  # keep the error visible on the account
                fresh = await db.get(EmailAccount, acc.id)
                fresh.sync_error = (str(e) if isinstance(e, MailboxError) else "Sync failed; check the mailbox settings.")[:1000]
                await db.commit()
            except Exception:
                await db.rollback()
    return result


async def run_mailbox_sync(interval: float = 300.0) -> None:
    """Lifespan task: import new mail for every connected mailbox every 5 minutes."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await sync_all(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("mailbox sync tick failed")
        await asyncio.sleep(interval)
