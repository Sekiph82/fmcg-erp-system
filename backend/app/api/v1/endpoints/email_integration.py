"""
Email Integration API
──────────────────────
Prefix: /api/v1/email

Routes:
  GET  /accounts         – list email accounts
  POST /accounts         – add email account
  GET  /threads          – list threads (filterable by linked_object_id)
  GET  /threads/{id}     – thread detail with messages
  POST /send             – compose + log outgoing email
  POST /sync/{account_id} – simulate inbox sync
  GET  /templates        – list email templates
  POST /templates        – create template
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import random

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.email_integration import (
    EmailAccount, EmailThread, EmailMessage, EmailTemplate, EmailProvider,
)
from app.models.user import User
from app.schemas.email_integration import (
    EmailAccountCreate, EmailAccountRead,
    EmailThreadRead, EmailMessageRead,
    SendEmailRequest,
    EmailTemplateCreate, EmailTemplateRead,
)

router = APIRouter()


# ── Accounts ──────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=List[EmailAccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailAccount).where(EmailAccount.is_active.is_(True)).order_by(EmailAccount.created_at)
    )
    return [EmailAccountRead.model_validate(a) for a in result.scalars().all()]


@router.post("/accounts", response_model=EmailAccountRead, status_code=201)
async def add_account(
    body: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = EmailAccount(**body.model_dump(), created_by_id=current_user.id)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return EmailAccountRead.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=204)
async def remove_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    account = await db.get(EmailAccount, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    account.is_active = False
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
    _: User = Depends(get_current_user),
):
    q = select(EmailThread).order_by(EmailThread.last_message_at.desc()).offset(skip).limit(limit)
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
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailThread)
        .options(selectinload(EmailThread.messages))
        .where(EmailThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(404, "Thread not found")

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
    _: User = Depends(get_current_user),
):
    """Link an email thread to an ERP record."""
    thread = await db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    thread.linked_module = linked_module
    thread.linked_object_id = linked_object_id
    thread.linked_object_ref = linked_object_ref
    await db.commit()
    await db.refresh(thread)
    row = EmailThreadRead.model_validate(thread)
    return row


# ── Send Email ────────────────────────────────────────────────────────────────

@router.post("/send", response_model=EmailThreadRead, status_code=201)
async def send_email(
    body: SendEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compose and log an outgoing email. Creates or appends to a thread."""
    account = await db.get(EmailAccount, body.account_id)
    if not account or not account.is_active:
        raise HTTPException(404, "Email account not found or inactive")

    now = datetime.now(tz=timezone.utc)

    # Get or create thread
    if body.thread_id:
        thread = await db.get(EmailThread, body.thread_id)
        if not thread:
            raise HTTPException(404, "Thread not found")
    else:
        thread = EmailThread(
            account_id=account.id,
            subject=body.subject,
            snippet=body.body_text[:200] if body.body_text else "",
            participants=list({account.email_address} | set(body.to_emails)),
            is_read=True,
            message_count=0,
            last_message_at=now,
            linked_module=body.linked_module,
            linked_object_id=body.linked_object_id,
            linked_object_ref=body.linked_object_ref,
        )
        db.add(thread)
        await db.flush()

    message = EmailMessage(
        thread_id=thread.id,
        from_email=account.email_address,
        from_name=account.display_name or current_user.full_name,
        to_emails=body.to_emails,
        cc_emails=body.cc_emails,
        subject=body.subject,
        body_text=body.body_text,
        received_at=now,
        is_inbound=False,
        is_read=True,
        sent_by_id=current_user.id,
    )
    db.add(message)
    thread.message_count += 1
    thread.last_message_at = now
    thread.snippet = body.body_text[:200] if body.body_text else ""
    await db.commit()

    result = await db.execute(
        select(EmailThread).options(selectinload(EmailThread.messages)).where(EmailThread.id == thread.id)
    )
    t = result.scalar_one()
    row = EmailThreadRead.model_validate(t)
    row.messages = [EmailMessageRead.model_validate(m) for m in t.messages]
    return row


# ── Simulate Sync ──────────────────────────────────────────────────────────────

@router.post("/sync/{account_id}", response_model=dict)
async def simulate_sync(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Simulate inbox sync — creates realistic demo email threads for demo/testing.
    In production this would call Gmail/Outlook API.
    """
    account = await db.get(EmailAccount, account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    now = datetime.now(tz=timezone.utc)

    demo_threads = [
        {
            "subject": "RE: Purchase Order PO-2024-0042 Confirmation",
            "from_email": "supplier@globalfoods.com",
            "from_name": "Global Foods Supplies",
            "body": "Dear Team,\n\nWe confirm receipt of your PO-2024-0042 for 5,000 kg of Maize Flour. "
                    "Expected delivery: 2024-02-15. Attached is our pro-forma invoice.\n\nBest regards,\nGlobal Foods",
            "linked_module": "procurement",
            "linked_object_ref": "PO-2024-0042",
            "minutes_ago": 45,
        },
        {
            "subject": "Invoice INV-2024-0128 — Payment Confirmation",
            "from_email": "accounts@nairobi-distributors.co.ke",
            "from_name": "Nairobi Distributors Ltd",
            "body": "Hi,\n\nPlease find attached our payment confirmation for Invoice INV-2024-0128 "
                    "(KES 485,000). M-Pesa transaction ref: QHF3G2891K.\n\nThank you.",
            "linked_module": "finance",
            "linked_object_ref": "INV-2024-0128",
            "minutes_ago": 120,
        },
        {
            "subject": "Quality Issue — Batch LOT-2024-0088",
            "from_email": "qc@retailchain.co.ke",
            "from_name": "Retail Chain QC Team",
            "body": "Hello,\n\nWe have identified potential quality issues with batch LOT-2024-0088 "
                    "(Cooking Oil 1L). 3 consumer complaints received regarding off-smell. "
                    "Please advise on next steps.\n\nRegards",
            "linked_module": "quality",
            "linked_object_ref": "LOT-2024-0088",
            "minutes_ago": 200,
        },
        {
            "subject": "New Distributor Inquiry — Mombasa Region",
            "from_email": "john.mwangi@coastal-dist.co.ke",
            "from_name": "John Mwangi",
            "body": "Good afternoon,\n\nI represent Coastal Distributors Ltd operating in the Mombasa "
                    "region. We are interested in becoming an authorized distributor for your product range. "
                    "Could you share your distributor onboarding requirements?\n\nThank you",
            "linked_module": "sales",
            "linked_object_ref": None,
            "minutes_ago": 360,
        },
        {
            "subject": "Certificate of Analysis Request — Export Shipment",
            "from_email": "import@middle-east-partner.ae",
            "from_name": "ME Import Partner",
            "body": "Dear Quality Team,\n\nFor our upcoming import shipment, please provide the Certificate "
                    "of Analysis for products in SO-2024-0156. Our customs requires this document prior to clearance.",
            "linked_module": "sales",
            "linked_object_ref": "SO-2024-0156",
            "minutes_ago": 480,
        },
    ]

    created = 0
    for demo in demo_threads:
        msg_time = now - timedelta(minutes=demo["minutes_ago"])
        thread = EmailThread(
            account_id=account.id,
            subject=demo["subject"],
            snippet=demo["body"][:150],
            participants=[demo["from_email"], account.email_address],
            is_read=False,
            message_count=1,
            last_message_at=msg_time,
            linked_module=demo["linked_module"],
            linked_object_ref=demo["linked_object_ref"],
        )
        db.add(thread)
        await db.flush()

        msg = EmailMessage(
            thread_id=thread.id,
            from_email=demo["from_email"],
            from_name=demo["from_name"],
            to_emails=[account.email_address],
            subject=demo["subject"],
            body_text=demo["body"],
            received_at=msg_time,
            is_inbound=True,
            is_read=False,
        )
        db.add(msg)
        created += 1

    account.last_sync_at = now
    account.sync_error = None
    await db.commit()
    return {"synced": created, "account": account.email_address}


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
