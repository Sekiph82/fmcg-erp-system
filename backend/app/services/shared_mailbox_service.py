"""M49.S01.T003 shared and delegated mailboxes.

Official contracts (public documentation):
- Microsoft Graph v1.0 (https://learn.microsoft.com/graph/outlook-share-messages-folders): another mailbox is addressed
  as /users/{address}/... (delegated scopes Mail.Read.Shared / Mail.Send.Shared; Exchange must grant the signed-in user
  Full Access / Send As / Send on Behalf; otherwise Graph answers 403 and nothing is read or sent).
  Send as: POST /users/{shared}/sendMail (MIME, base64, text/plain) with the member's own token.
  Send on behalf: POST /me/sendMail with message.from = shared mailbox and message.sender = the signed-in user.
- Gmail API v1 (https://developers.google.com/gmail/api/reference/rest/v1/users.settings.sendAs): a send-as alias is
  listed by users.settings.sendAs.list; only an alias with verificationStatus "accepted" may be used as the From of
  users.messages.send. Gmail has no send-on-behalf through the API, so that mode is refused for Google mailboxes.
  Reading another user's Gmail needs a service account with domain-wide delegation (userId = address); a delegate's
  own OAuth token cannot do it. The ERP asks the provider (profile probe at registration, UNVERIFIED against real
  Workspace) and reports the refusal; send-as through the member's own token is the supported Google path.

Model: a shared mailbox is registered by an administrator who proves provider access with a probe call. ERP members are
rows in shared_mailbox_members; every request re-checks membership, so revocation is immediate. Mail of the mailbox is
stored under its own email_accounts row (created_by NULL, never synced as a personal inbox), so threads, search and the
personal inbox stay separate. Sending uses the member's own provider token, so the provider enforces the member's
rights too. Incremental sync uses its own cursor on shared_mailboxes and is bounded (first run: newest 200, then at most
PAGE_LIMIT pages per run).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import re
from datetime import datetime, timezone
from email import message_from_bytes, policy
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.email_integration import EmailAccount, EmailProvider, EmailThread
from app.models.m49_calendar_mail import SharedMailbox, SharedMailboxMember
from app.models.oauth_connection import OAuthConnection
from app.services import email_mailbox_service as mbx
from app.services import mail_api_adapters as api
from app.services import oauth_service as oauth

log = logging.getLogger(__name__)
_ADDR = re.compile(r"^[a-z0-9._%+'-]{1,64}@[a-z0-9.-]{1,190}\.[a-z]{2,}$")
SEND_MODES = {"google": ("send_as",), "microsoft": ("send_as", "on_behalf")}


class SharedMailboxError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _audit(db: AsyncSession, actor: Any, event: str, mb: SharedMailbox, details: Optional[dict] = None) -> None:
    db.add(AuditLog(actor_id=getattr(actor, "id", None), actor_email=getattr(actor, "email", None), event_type=event,
                    module="email", target_type="shared_mailbox", target_id=str(mb.id), target_name=mb.address[:200],
                    details={"provider": mb.provider, **(details or {})}))


def view(mb: SharedMailbox, member: Optional[SharedMailboxMember] = None) -> dict:
    iso = lambda v: v.isoformat() if v else None  # noqa: E731
    out = {"id": str(mb.id), "provider": mb.provider, "address": mb.address, "display_name": mb.display_name,
           "kind": mb.kind, "status": mb.status, "account_id": str(mb.account_id) if mb.account_id else None,
           "last_sync_at": iso(mb.last_sync_at), "last_error": mb.last_error,
           "send_modes": list(SEND_MODES[mb.provider])}
    if member is not None:
        out["my_access"] = {"can_read": True, "can_send": member.can_send, "send_mode": member.send_mode}
    return out


async def _mail_connection(db: AsyncSession, user_id: UUID, provider: str) -> OAuthConnection:
    conn = (await db.execute(select(OAuthConnection).where(
        OAuthConnection.user_id == user_id, OAuthConnection.provider == provider, OAuthConnection.purpose == "mail",
        OAuthConnection.status == "CONNECTED"))).scalars().first()
    if conn is None:
        raise SharedMailboxError(409, f"Connect your own {'Google' if provider == 'google' else 'Microsoft 365'} "
                                      "mailbox first (Communication > Email); the provider checks your rights with your sign-in.")
    return conn


async def _probe(db: AsyncSession, conn: OAuthConnection, mb_addr: str) -> None:
    """Does the provider let this connection open that mailbox?"""
    try:
        if conn.provider == "google":
            r = await api._call(db, conn, "GET", f"{api._gmail(mb_addr)}/profile")
            ok = r.status_code == 200 and (r.json().get("emailAddress") or "").lower() == mb_addr
        else:
            r = await api._call(db, conn, "GET", f"{api._graph(mb_addr)}/mailFolders/inbox")
            ok = r.status_code == 200
    except (oauth.OAuthError, api.MailApiError) as e:
        raise SharedMailboxError(502, str(e)) from None
    if not ok:
        raise SharedMailboxError(403, f"The provider did not let your account open {mb_addr} "
                                      f"({r.status_code}); ask the mailbox owner / IT to grant access first.")


async def register(db: AsyncSession, actor: Any, *, provider: str, address: str, display_name: Optional[str],
                   kind: str) -> SharedMailbox:
    addr = address.strip().lower()
    if provider not in SEND_MODES or kind not in ("shared", "delegated") or not _ADDR.match(addr):
        raise SharedMailboxError(422, "Provider, kind or address is invalid.")
    if (await db.execute(select(SharedMailbox.id).where(SharedMailbox.provider == provider, SharedMailbox.address == addr,
                                                        SharedMailbox.status != "REVOKED"))).first():
        raise SharedMailboxError(409, "That mailbox is already registered.")
    conn = await _mail_connection(db, actor.id, provider)
    if (conn.account_email or "").lower() == addr:
        raise SharedMailboxError(422, "That is your own personal mailbox; connect it under Email instead.")
    await _probe(db, conn, addr)
    old = (await db.execute(select(SharedMailbox).where(SharedMailbox.provider == provider, SharedMailbox.address == addr))).scalar_one_or_none()
    if old is not None:                                    # re-register a revoked one: fresh membership, fresh cursor
        mb, mb.status, mb.revoked_at, mb.sync_cursor, mb.last_error = old, "ACTIVE", None, None, None
        mb.connection_id, mb.kind, mb.display_name = conn.id, kind, display_name or old.display_name
        acc = await db.get(EmailAccount, mb.account_id) if mb.account_id else None
        if acc is not None:
            acc.is_active = True
    else:
        mb = SharedMailbox(provider=provider, address=addr, display_name=display_name, kind=kind, status="ACTIVE",
                           connection_id=conn.id, created_by_id=actor.id)
        db.add(mb)
        await db.flush()
        acc = None
    if acc is None:
        acc = EmailAccount(provider=EmailProvider.GMAIL if provider == "google" else EmailProvider.OUTLOOK, email_address=addr,
                           display_name=display_name, is_active=True, sync_enabled=False, created_by_id=None)
        db.add(acc)
        await db.flush()
        mb.account_id = acc.id
    _audit(db, actor, "SHARED_MAILBOX_REGISTERED", mb, {"kind": kind, "registered_via": conn.account_email})
    await db.flush()
    return mb


async def member_row(db: AsyncSession, user_id: UUID, mailbox_id: UUID) -> Optional[SharedMailboxMember]:
    return (await db.execute(select(SharedMailboxMember).where(
        SharedMailboxMember.mailbox_id == mailbox_id, SharedMailboxMember.user_id == user_id,
        SharedMailboxMember.revoked_at.is_(None)))).scalar_one_or_none()


async def require_access(db: AsyncSession, user: Any, mailbox_id: UUID, *, send: bool = False) -> tuple[SharedMailbox, SharedMailboxMember]:
    """Membership decides, not the superuser flag: content of a shared mailbox is only for its members. A non-member
    gets 404 (the mailbox is not revealed); a read-only member asking to send gets 403."""
    mb = await db.get(SharedMailbox, mailbox_id)
    member = await member_row(db, user.id, mailbox_id) if mb is not None else None
    if mb is None or member is None or mb.status == "REVOKED":
        raise SharedMailboxError(404, "Mailbox not found")
    if send and not member.can_send:
        raise SharedMailboxError(403, "You may read this mailbox but not send from it.")
    return mb, member


async def grant(db: AsyncSession, actor: Any, mb: SharedMailbox, user_id: UUID, *, can_send: bool, send_mode: str) -> SharedMailboxMember:
    from app.models.user import User
    if mb.status != "ACTIVE":
        raise SharedMailboxError(409, "The mailbox is not active.")
    if send_mode not in SEND_MODES[mb.provider]:
        raise SharedMailboxError(422, f"{'Gmail' if mb.provider == 'google' else 'Microsoft'} does not offer '{send_mode}' "
                                      f"through its API; use {' or '.join(SEND_MODES[mb.provider])}.")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise SharedMailboxError(404, "User not found")
    row = (await db.execute(select(SharedMailboxMember).where(
        SharedMailboxMember.mailbox_id == mb.id, SharedMailboxMember.user_id == user_id))).scalar_one_or_none()
    if row is None:
        row = SharedMailboxMember(mailbox_id=mb.id, user_id=user_id)
        db.add(row)
    row.can_send, row.send_mode, row.revoked_at, row.granted_by_id = can_send, send_mode, None, actor.id
    row.granted_at = datetime.now(timezone.utc)
    _audit(db, actor, "SHARED_MAILBOX_MEMBER_GRANTED", mb, {"user_id": str(user_id), "can_send": can_send, "send_mode": send_mode})
    await db.flush()
    return row


async def revoke_member(db: AsyncSession, actor: Any, mb: SharedMailbox, user_id: UUID) -> None:
    row = await member_row(db, user_id, mb.id)
    if row is None:
        raise SharedMailboxError(404, "That user is not a member.")
    row.revoked_at = datetime.now(timezone.utc)
    _audit(db, actor, "SHARED_MAILBOX_MEMBER_REVOKED", mb, {"user_id": str(user_id)})
    await db.flush()


async def revoke_mailbox(db: AsyncSession, actor: Any, mb: SharedMailbox) -> None:
    """Close the mailbox: nobody reads or sends, the cursor is dropped, stored history stays for the audit trail."""
    now = datetime.now(timezone.utc)
    mb.status, mb.revoked_at, mb.sync_cursor = "REVOKED", now, None
    for m in (await db.execute(select(SharedMailboxMember).where(SharedMailboxMember.mailbox_id == mb.id,
                                                                 SharedMailboxMember.revoked_at.is_(None)))).scalars():
        m.revoked_at = now
    acc = await db.get(EmailAccount, mb.account_id) if mb.account_id else None
    if acc is not None:
        acc.is_active = False
    _audit(db, actor, "SHARED_MAILBOX_REVOKED", mb)
    await db.flush()


# ── incremental sync (bounded) ────────────────────────────────────────────────

async def sync(db: AsyncSession, mb: SharedMailbox, actor: Any = None) -> dict:
    if mb.status != "ACTIVE":
        raise SharedMailboxError(409, "The mailbox is not active.")
    conn = await db.get(OAuthConnection, mb.connection_id) if mb.connection_id else None
    acc = await db.get(EmailAccount, mb.account_id) if mb.account_id else None
    if conn is None or conn.status != "CONNECTED" or acc is None:
        mb.status, mb.last_error = "ACCESS_LOST", "The sign-in used to read this mailbox was disconnected; register it again."
        raise SharedMailboxError(409, mb.last_error)
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                     {"k": int(hashlib.sha256(f"shared-mbx:{mb.id}".encode()).hexdigest()[:15], 16)})
    try:
        raws, cursor = await (api.gmail_fetch if mb.provider == "google" else api.graph_fetch)(
            db, conn, mailbox=mb.address, cursor=mb.sync_cursor or {})
    except (oauth.OAuthError, api.MailApiError) as e:
        msg = str(e)
        mb.last_error = msg[:500]
        if "(403)" in msg or "(404)" in msg:             # provider no longer lets this sign-in open the mailbox
            mb.status = "ACCESS_LOST"
        raise SharedMailboxError(502, msg) from None
    imported = skipped = failed = 0
    for raw in raws:
        try:
            async with db.begin_nested():
                stored = await mbx.store(db, acc, mbx.parse(raw))
        except Exception:
            log.warning("shared mailbox %s: a message could not be imported", mb.id, exc_info=True)
            failed, stored = failed + 1, None
        else:
            imported, skipped = (imported + 1, skipped) if stored else (imported, skipped + 1)
    mb.sync_cursor, mb.last_sync_at, mb.last_error = cursor, datetime.now(timezone.utc), None
    acc.last_sync_at, acc.sync_error = mb.last_sync_at, None
    if actor is not None:
        _audit(db, actor, "SHARED_MAILBOX_SYNCED", mb, {"imported": imported, "skipped": skipped, "failed": failed})
    await db.flush()
    return {"imported": imported, "skipped": skipped, "failed": failed}


async def sync_all(db: AsyncSession) -> dict:
    out = {"mailboxes": 0, "imported": 0, "failed": 0}
    for mb in (await db.execute(select(SharedMailbox).where(SharedMailbox.status == "ACTIVE"))).scalars().all():
        out["mailboxes"] += 1
        try:
            r = await sync(db, mb)
            await db.commit()
            out["imported"] += r["imported"]
        except Exception as e:
            await db.commit() if isinstance(e, SharedMailboxError) else await db.rollback()   # keep ACCESS_LOST / error text
            out["failed"] += 1
    return out


# ── send ──────────────────────────────────────────────────────────────────────

def _graph_json(mime: bytes, shared: str, sender: Optional[str]) -> dict:
    msg = message_from_bytes(mime, policy=policy.default)
    body = msg.get_body(preferencelist=("plain",))
    rcpt = lambda h: [{"emailAddress": {"address": a}} for a in (x.strip() for x in str(msg.get(h, "")).split(",")) if a]  # noqa: E731
    atts = [{"@odata.type": "#microsoft.graph.fileAttachment", "name": p.get_filename() or "attachment",
             "contentType": p.get_content_type(), "contentBytes": base64.b64encode(p.get_payload(decode=True) or b"").decode()}
            for p in msg.iter_attachments()]
    message = {"subject": str(msg.get("Subject", "")), "body": {"contentType": "text", "content": body.get_content() if body else ""},
               "toRecipients": rcpt("To"), "ccRecipients": rcpt("Cc"), "from": {"emailAddress": {"address": shared}},
               "attachments": atts}
    if sender:
        message["sender"] = {"emailAddress": {"address": sender}}
    return {"message": message, "saveToSentItems": True}


async def _verify_google_alias(db: AsyncSession, conn: OAuthConnection, addr: str) -> None:
    try:
        r = await api._call(db, conn, "GET", f"{api._gmail()}/settings/sendAs")
    except (oauth.OAuthError, api.MailApiError) as e:
        raise SharedMailboxError(502, str(e)) from None
    if r.status_code != 200:
        raise SharedMailboxError(502, f"Gmail did not list your send-as addresses ({r.status_code}).")
    alias = next((a for a in r.json().get("sendAs", []) if (a.get("sendAsEmail") or "").lower() == addr), None)
    if alias is None or alias.get("verificationStatus") not in (None, "accepted"):
        raise SharedMailboxError(403, f"Gmail has no verified send-as address {addr} for your account; add and verify it "
                                      "in Gmail settings (Accounts > Send mail as) first. Nothing was sent.")


async def send(db: AsyncSession, user: Any, mailbox_id: UUID, *, to: list[str], cc: list[str], subject: str, body: str,
               thread_id: Optional[UUID] = None) -> EmailThread:
    mb, member = await require_access(db, user, mailbox_id, send=True)
    if mb.status != "ACTIVE":
        raise SharedMailboxError(409, "The mailbox is not active.")
    own = await _mail_connection(db, user.id, mb.provider)
    acc = await db.get(EmailAccount, mb.account_id)
    thread = None
    if thread_id is not None:
        thread = await db.get(EmailThread, thread_id)
        if thread is None or thread.account_id != mb.account_id:
            raise SharedMailboxError(404, "Thread not found in this mailbox")
    mode = member.send_mode if member.send_mode in SEND_MODES[mb.provider] else "send_as"
    if mb.provider == "google":
        await _verify_google_alias(db, own, mb.address)

        async def send_fn(mime: bytes) -> None:
            await api.gmail_send(db, own, mime)
    elif mode == "send_as":
        async def send_fn(mime: bytes) -> None:
            r = await api._call(db, own, "POST", f"{api._graph(mb.address)}/sendMail", content=base64.b64encode(mime),
                                headers={"Content-Type": "text/plain"})
            if r.status_code == 403:
                raise SharedMailboxError(403, "Microsoft says you do not have Send As permission on this mailbox. Nothing was sent.")
            if r.status_code not in (200, 202):
                raise SharedMailboxError(502, f"Microsoft refused the message ({r.status_code}); nothing was sent.")
    else:
        async def send_fn(mime: bytes) -> None:
            r = await api._call(db, own, "POST", f"{api._graph()}/sendMail", json=_graph_json(mime, mb.address, own.account_email))
            if r.status_code == 403:
                raise SharedMailboxError(403, "Microsoft says you do not have Send on Behalf permission on this mailbox. Nothing was sent.")
            if r.status_code not in (200, 202):
                raise SharedMailboxError(502, f"Microsoft refused the message ({r.status_code}); nothing was sent.")
    try:
        thread = await mbx.send(db, acc, to=to, cc=cc, subject=subject, body=body, thread=thread, sent_by=user,
                                link={"linked_module": None, "linked_object_id": None, "linked_object_ref": None},
                                send_fn=send_fn)
    except (oauth.OAuthError, api.MailApiError) as e:
        raise SharedMailboxError(502, str(e)) from None
    except mbx.MailboxError as e:
        raise SharedMailboxError(422, str(e)) from None
    _audit(db, user, "SHARED_MAILBOX_SENT", mb, {"mode": mode, "recipients": len(to) + len(cc), "thread_id": str(thread.id)})
    await db.flush()
    return thread
