"""
Email Integration API
──────────────────────
Prefix: /api/v1/email

Routes:
  GET  /accounts         – list email accounts
  POST /accounts         – add email account
  GET  /threads          – list threads (filterable by linked_object_id)
  GET  /threads/{id}     – thread detail with messages
  PUT  /accounts/{id}/connection – connect a mailbox (IMAP/SMTP, login tested)
  POST /send             – send through the mailbox's SMTP server
  POST /sync/{account_id} – import new mail now
  GET  /templates        – list email templates
  POST /templates        – create template
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.email_integration import (
    EmailAccount, EmailThread, EmailMessage, EmailTemplate, EmailProvider,
)
from app.models.user import User
from app.schemas.email_integration import (
    EmailAccountCreate, EmailAccountRead, MailboxSettings,
    EmailThreadRead, EmailMessageRead,
    SendEmailRequest,
    EmailTemplateCreate, EmailTemplateRead,
)

router = APIRouter()


def _read(acc: EmailAccount) -> EmailAccountRead:
    from app.services.email_mailbox_service import is_connected
    row = EmailAccountRead.model_validate(acc)
    row.connected = is_connected(acc)
    return row


async def _apply_mailbox(acc: EmailAccount, body) -> None:
    """Fill provider defaults, test the IMAP and SMTP login, then store the encrypted password."""
    import asyncio
    from app.services import email_mailbox_service as mbx

    d = mbx.DEFAULTS.get(acc.provider, (None, 993, None, 587))
    imap_host, imap_port = body.imap_host or acc.imap_host or d[0], body.imap_port or acc.imap_port or d[1]
    smtp_host, smtp_port = body.smtp_host or acc.smtp_host or d[2], body.smtp_port or acc.smtp_port or d[3]
    username = body.username or acc.username or acc.email_address
    if not (imap_host and smtp_host):
        raise HTTPException(422, "IMAP and SMTP server names are required for this provider.")
    try:
        await asyncio.to_thread(mbx.validate_host, imap_host, imap_port, mbx.IMAP_PORTS)
        await asyncio.to_thread(mbx.validate_host, smtp_host, smtp_port, mbx.SMTP_PORTS)
        await asyncio.to_thread(mbx.check_login, imap_host, imap_port, smtp_host, smtp_port, username, body.password)
    except mbx.MailboxError as e:
        raise HTTPException(422, str(e))
    acc.imap_host, acc.imap_port, acc.smtp_host, acc.smtp_port = imap_host, imap_port, smtp_host, smtp_port
    acc.username, acc.secret_enc, acc.sync_error = username, mbx.encrypt(body.password), None


# Mailboxes are personal: a user reaches only the accounts they connected (superusers: all).
def _owns(account: EmailAccount, user: User) -> bool:
    return bool(getattr(user, "is_superuser", False)) or account.created_by_id == user.id


async def _account_for(db: AsyncSession, account_id: uuid.UUID, user: User) -> EmailAccount:
    account = await db.get(EmailAccount, account_id)
    if not account or not _owns(account, user):
        raise HTTPException(404, "Account not found")
    return account


async def _thread_for(db: AsyncSession, thread_id: uuid.UUID, user: User, with_messages: bool = False) -> EmailThread:
    q = select(EmailThread).where(EmailThread.id == thread_id)
    if with_messages:
        q = q.options(selectinload(EmailThread.messages))
    thread = (await db.execute(q)).scalar_one_or_none()
    account = await db.get(EmailAccount, thread.account_id) if thread else None
    if not thread or account is None or not _owns(account, user):
        raise HTTPException(404, "Thread not found")
    return thread


# ── Accounts ──────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=List[EmailAccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(EmailAccount).where(EmailAccount.is_active.is_(True)).order_by(EmailAccount.created_at)
    if not current_user.is_superuser:
        q = q.where(EmailAccount.created_by_id == current_user.id)
    result = await db.execute(q)
    return [_read(a) for a in result.scalars().all()]


@router.post("/accounts", response_model=EmailAccountRead, status_code=201)
async def add_account(
    body: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a mailbox. With a password it is connected (login tested first, 422 if it fails); without one it
    is only a record and cannot send or sync."""
    account = EmailAccount(provider=body.provider, email_address=body.email_address.strip().lower(),
                           display_name=body.display_name, sync_enabled=body.sync_enabled, created_by_id=current_user.id)
    if body.password:
        await _apply_mailbox(account, body)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _read(account)


@router.put("/accounts/{account_id}/connection", response_model=EmailAccountRead)
async def connect_account(account_id: uuid.UUID, body: MailboxSettings, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Connect or re-connect (e.g. new app password) a mailbox; the login is tested before anything is stored."""
    account = await _account_for(db, account_id, current_user)
    if not account.is_active:
        raise HTTPException(404, "Account not found")
    if not body.password:
        raise HTTPException(422, "password is required")
    await _apply_mailbox(account, body)
    await db.commit()
    await db.refresh(account)
    return _read(account)


@router.delete("/accounts/{account_id}", status_code=204)
async def remove_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Disconnect: stop syncing and sending and erase the stored password. Threads stay as history."""
    account = await _account_for(db, account_id, current_user)
    account.is_active = False
    account.sync_enabled = False
    account.secret_enc = None
    await db.commit()


# ── Threads ───────────────────────────────────────────────────────────────────

@router.get("/threads", response_model=List[EmailThreadRead])
async def list_threads(
    linked_object_id: Optional[uuid.UUID] = None,
    linked_module: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (select(EmailThread).options(noload(EmailThread.messages))  # list view: no messages
         .order_by(EmailThread.last_message_at.desc().nulls_last()).offset(skip).limit(limit))
    if not current_user.is_superuser:
        q = q.where(EmailThread.account_id.in_(
            select(EmailAccount.id).where(EmailAccount.created_by_id == current_user.id)))
    if linked_object_id:
        q = q.where(EmailThread.linked_object_id == linked_object_id)
    if linked_module:
        q = q.where(EmailThread.linked_module == linked_module)
    if account_id:
        q = q.where(EmailThread.account_id == account_id)
    if unread_only:
        q = q.where(EmailThread.is_read.is_(False))

    threads = list((await db.execute(q)).scalars().all())
    result = []
    for t in threads:
        row = EmailThreadRead.model_validate(t)
        row.messages = []  # don't include messages in list view
        result.append(row)
    return result


@router.get("/threads/{thread_id}", response_model=EmailThreadRead)
async def get_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = await _thread_for(db, thread_id, current_user, with_messages=True)

    # Mark as read
    thread.is_read = True
    for m in thread.messages:
        m.is_read = True
    await db.commit()

    row = EmailThreadRead.model_validate(thread)
    row.messages = [EmailMessageRead.model_validate(m) for m in thread.messages]
    return row


@router.patch("/threads/{thread_id}/link", response_model=EmailThreadRead)
async def link_thread(
    thread_id: uuid.UUID,
    linked_module: str,
    linked_object_id: uuid.UUID,
    linked_object_ref: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an email thread to an ERP record."""
    thread = await _thread_for(db, thread_id, current_user)
    if linked_module == "customer":
        from app.models.sales import Customer
        if await db.get(Customer, linked_object_id) is None:
            raise HTTPException(422, "Customer not found")
    thread.linked_module = linked_module
    thread.linked_object_id = linked_object_id
    thread.linked_object_ref = linked_object_ref
    await db.commit()
    await db.refresh(thread, ["messages"])  # serialised below; never lazy-load in async
    row = EmailThreadRead.model_validate(thread)
    return row


# ── Send Email ────────────────────────────────────────────────────────────────

@router.post("/send", response_model=EmailThreadRead, status_code=201)
async def send_email(
    body: SendEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send through the mailbox's own SMTP server and keep the message in the thread. A reply carries
    In-Reply-To / References so it stays in the customer's thread too. Nothing is stored if delivery fails."""
    from app.services import email_mailbox_service as mbx

    account = await _account_for(db, body.account_id, current_user)
    if not account.is_active:
        raise HTTPException(404, "Email account not found or inactive")
    thread = None
    if body.thread_id:
        thread = await _thread_for(db, body.thread_id, current_user)
        if thread.account_id != account.id:
            raise HTTPException(422, "Thread belongs to another mailbox")
    to = [e.strip().lower() for e in body.to_emails if e.strip()]
    if not to:
        raise HTTPException(422, "At least one recipient is required")
    link = {"linked_module": body.linked_module, "linked_object_id": body.linked_object_id,
            "linked_object_ref": body.linked_object_ref}
    try:
        thread = await mbx.send(db, account, to=to, cc=[e.strip().lower() for e in body.cc_emails if e.strip()],
                                subject=body.subject, body=body.body_text, thread=thread, sent_by=current_user, link=link)
    except mbx.MailboxError as e:
        raise HTTPException(422 if isinstance(e, mbx.MailboxInputError) else 409 if not mbx.is_connected(account) else 502, str(e))
    await db.commit()

    result = await db.execute(
        select(EmailThread).options(selectinload(EmailThread.messages)).where(EmailThread.id == thread.id)
    )
    t = result.scalar_one()
    row = EmailThreadRead.model_validate(t)
    row.messages = [EmailMessageRead.model_validate(m) for m in t.messages]
    return row


# ── Sync ──────────────────────────────────────────────────────────

# Local development only: sample POVU mail for a mailbox that is not connected.
_DEMO_THREADS = [
    ("Order for POVU AllClean 1 L — 20 cartons", "orders@mama-duka.example", "Mama Duka Stores",
     "Hello,\n\nPlease deliver 20 cartons of POVU AllClean 1 L (POVU-ALC-1L) to our Kawangware shop on Friday.\n\nThanks", 45),
    ("Broken caps on last delivery", "qc@retail-chain.example", "Retail Chain QC",
     "Hello,\n\n2 cartons of POVU AllClean 1 L arrived with broken caps (lot on the carton label). Please advise.\n\nRegards", 200),
    ("Price list request — baby wipes", "buyer@coastal-dist.example", "Coastal Distributors",
     "Good afternoon,\n\nCould you share your current price list for POVU baby wipes and liquid detergents for Mombasa?\n\nThank you", 360),
]


@router.post("/sync/{account_id}", response_model=dict)
async def sync_mailbox(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import new mail now (connected mailboxes are also synced every 5 minutes). A mailbox that is not
    connected answers 409; only local development fills it with sample POVU mail."""
    from app.services import email_mailbox_service as mbx

    account = await _account_for(db, account_id, current_user)
    if not account.is_active:
        raise HTTPException(404, "Account not found")
    if mbx.is_connected(account):
        try:
            result = await mbx.sync_account(db, account)
        except mbx.MailboxError as e:
            await db.commit()  # keep sync_error on the account
            raise HTTPException(502, str(e))
        await db.commit()
        return {**result, "account": account.email_address}
    if settings.ENVIRONMENT != "development":
        raise HTTPException(409, "Connect this mailbox (IMAP/SMTP) first; nothing was imported.")

    now = datetime.now(tz=timezone.utc)
    created = 0
    for subject, sender, name, body, minutes in _DEMO_THREADS:
        p = mbx.Parsed(message_id=f"<demo-{account.id}-{created}@povu.local>", in_reply_to=None, references=[],
                       from_email=sender, from_name=name, to=[account.email_address.lower()], cc=[], subject=subject,
                       text=body, when=now - timedelta(minutes=minutes))
        if await mbx.store(db, account, p):
            created += 1
    account.last_sync_at = now
    await db.commit()
    return {"imported": created, "skipped": len(_DEMO_THREADS) - created, "account": account.email_address, "demo": True}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[EmailTemplateRead])
async def list_templates(
    module: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(EmailTemplate).where(EmailTemplate.is_active.is_(True)).order_by(EmailTemplate.name)
    if module:
        q = q.where((EmailTemplate.module == module) | (EmailTemplate.module.is_(None)))
    return [EmailTemplateRead.model_validate(t) for t in (await db.execute(q)).scalars().all()]


@router.post("/templates", response_model=EmailTemplateRead, status_code=201)
async def create_template(
    body: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = EmailTemplate(**body.model_dump(), created_by_id=current_user.id)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return EmailTemplateRead.model_validate(tmpl)
