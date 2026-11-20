"""M36.S01.T003 unified conversations inbox.

One index row per customer conversation over the channels that already store messages:
e-mail threads (personal mailboxes), WhatsApp numbers (the company's shared number) and helpdesk
tickets. Messages stay in their source tables; `sync()` upserts the index from them (idempotent:
one row per (channel, source_ref), so replayed or duplicate events never add rows).

Who sees a conversation (besides superusers and the assignee):
  EMAIL    - the mailbox owner (mailboxes are personal, as on the customer timeline)
  WHATSAPP - broad CRM viewers (crm.view / crm.view_all)
  TICKET   - quality viewers (the helpdesk screens are gated on quality.view)
and never a conversation of another company's customer unless the user has crm.view_all.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import String, and_, case, cast, delete, false, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.models.crm import CRMConversation, CRMConversationRead
from app.models.email_integration import EmailAccount, EmailMessage, EmailThread
from app.models.helpdesk import HelpdeskTicket, TicketComment, TicketStatus
from app.models.sales import Customer
from app.models.whatsapp import WAMessageDirection, WhatsAppMessage

DEFAULT_REPLY_HOURS = 24  # reply due for an unanswered e-mail / WhatsApp message
CHANNELS = ("EMAIL", "WHATSAPP", "TICKET")
STATUSES = ("OPEN", "PENDING", "CLOSED")
SYNC_LOCK = 3600_1003  # pg advisory lock key for sync()
_CLOSED_TICKET = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def _sla(last_in: Optional[datetime], last_out: Optional[datetime], hours: int) -> Optional[datetime]:
    if last_in is None or (last_out is not None and last_out >= last_in):
        return None
    return last_in + timedelta(hours=hours)


async def _upsert(db: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Insert new conversations; refresh activity fields of existing ones. Inbox-owned state
    (assignee, status) is kept, except a closed e-mail/WhatsApp conversation reopens on a new
    customer message, and ticket status/assignee follow the ticket."""
    for row in rows:
        stmt = pg_insert(CRMConversation).values(**row)
        ex = stmt.excluded
        reopened = and_(CRMConversation.status == "CLOSED", ex.last_inbound_at.is_not(None),
                        or_(CRMConversation.closed_at.is_(None), ex.last_inbound_at > CRMConversation.closed_at))
        is_ticket = literal(row["channel"] == "TICKET")
        update = {
            "subject": ex.subject, "contact": ex.contact, "customer_id": ex.customer_id,
            "company_id": ex.company_id, "mailbox_owner_id": ex.mailbox_owner_id,
            "last_inbound_at": ex.last_inbound_at, "last_outbound_at": ex.last_outbound_at,
            "last_message_at": ex.last_message_at, "sla_due_at": ex.sla_due_at,
            "status": case((is_ticket, ex.status), (reopened, "OPEN"), else_=CRMConversation.status),
            "closed_at": case((is_ticket, ex.closed_at), (reopened, None), else_=CRMConversation.closed_at),
            "assignee_id": case((is_ticket, ex.assignee_id), else_=CRMConversation.assignee_id),
            "updated_at": func.now(),
        }
        await db.execute(stmt.on_conflict_do_update(constraint="uq_crm_conversation_source", set_=update))


async def _customer_company(db: AsyncSession, ids: set) -> dict:
    ids.discard(None)
    if not ids:
        return {}
    return dict((await db.execute(select(Customer.id, Customer.company_id).where(Customer.id.in_(ids)))).all())


async def sync(db: AsyncSession) -> int:
    """Rebuild the index from the source tables. Returns the number of conversations touched.
    ponytail: full rescan on every inbox load; switch to an updated_at watermark when volume grows."""
    rows: list[dict[str, Any]] = []
    await db.execute(select(func.pg_advisory_xact_lock(SYNC_LOCK)))  # one sync at a time; concurrent loads wait

    # E-mail: one conversation per thread.
    last_in = func.max(case((EmailMessage.is_inbound.is_(True), EmailMessage.received_at)))
    last_out = func.max(case((EmailMessage.is_inbound.is_(False), EmailMessage.received_at)))
    q = (select(EmailThread, EmailAccount.created_by_id, last_in, last_out)
         .join(EmailAccount, EmailAccount.id == EmailThread.account_id)
         .outerjoin(EmailMessage, EmailMessage.thread_id == EmailThread.id)
         .group_by(EmailThread.id, EmailAccount.created_by_id))
    emails = (await db.execute(q)).all()
    for t, owner, li, lo in emails:
        cust = t.linked_object_id if t.linked_module == "customer" else None
        rows.append(dict(channel="EMAIL", source_ref=str(t.id), subject=t.subject[:500],
                         contact=", ".join((t.participants or [])[:3])[:255] or None, customer_id=cust,
                         mailbox_owner_id=owner, last_inbound_at=li, last_outbound_at=lo,
                         last_message_at=t.last_message_at or li or lo, sla_due_at=_sla(li, lo, DEFAULT_REPLY_HOURS),
                         status="OPEN", assignee_id=None, closed_at=None))

    # WhatsApp: one conversation per (business number, customer phone).
    inbound = WhatsAppMessage.direction == WAMessageDirection.INBOUND
    q = (select(WhatsAppMessage.config_id, WhatsAppMessage.phone,
                func.max(WhatsAppMessage.contact_name),
                func.max(case((inbound, WhatsAppMessage.created_at))),
                func.max(case((~inbound, WhatsAppMessage.created_at))),
                func.max(case((WhatsAppMessage.linked_module == "customer", cast(WhatsAppMessage.linked_object_id, String)))))
         .group_by(WhatsAppMessage.config_id, WhatsAppMessage.phone))
    for cfg, phone, name, li, lo, cust in (await db.execute(q)).all():
        rows.append(dict(channel="WHATSAPP", source_ref=f"{cfg}:{phone}", subject=f"WhatsApp {name or phone}"[:500],
                         contact=(f"{name} {phone}" if name else phone)[:255], customer_id=UUID(cust) if cust else None,
                         mailbox_owner_id=None, last_inbound_at=li, last_outbound_at=lo,
                         last_message_at=max(x for x in (li, lo) if x), sla_due_at=_sla(li, lo, DEFAULT_REPLY_HOURS),
                         status="OPEN", assignee_id=None, closed_at=None))

    # Helpdesk tickets: status and assignee follow the ticket.
    # Last customer-visible reply per ticket (internal notes and edits such as assignment are not messages).
    # Customer replies (portal: no staff author) are inbound; staff replies are outbound (M36.S04.T004).
    customer_said = TicketComment.created_by_id.is_(None)
    replies = {tid: (cin, cout) for tid, cin, cout in (await db.execute(
        select(TicketComment.ticket_id,
               func.max(case((customer_said, TicketComment.created_at))),
               func.max(case((~customer_said, TicketComment.created_at))))
        .where(TicketComment.is_internal.is_(False)).group_by(TicketComment.ticket_id))).all()}
    for t in (await db.execute(select(HelpdeskTicket))).scalars():
        closed = t.status in _CLOSED_TICKET
        cin, cout = replies.get(t.id, (None, None))
        li = max(x for x in (t.created_at, cin) if x)
        lo = max((x for x in (t.first_response_at, cout) if x), default=None)
        rows.append(dict(channel="TICKET", source_ref=str(t.id), subject=f"{t.ticket_no}: {t.subject}"[:500],
                         contact=None, customer_id=t.customer_id, mailbox_owner_id=None,
                         last_inbound_at=li, last_outbound_at=lo,
                         last_message_at=max(x for x in (li, lo) if x),
                         sla_due_at=None if closed else _sla(li, lo, t.sla_hours or DEFAULT_REPLY_HOURS),
                         status="CLOSED" if closed else "OPEN", assignee_id=t.assigned_to_id,
                         closed_at=(t.closed_at or t.resolved_at) if closed else None))

    # Thread/message links have no foreign key: keep a customer only if it exists (a stale or bogus link
    # must neither break the upsert for everyone nor drop the company filter to "visible to all").
    companies = await _customer_company(db, {r["customer_id"] for r in rows})
    for r in rows:
        if r["customer_id"] not in companies:
            r["customer_id"] = None
        r["company_id"] = companies.get(r["customer_id"])
    rows.sort(key=lambda r: (r["channel"], r["source_ref"]))  # fixed lock order
    await _upsert(db, rows)
    # Remove index rows whose source is gone (deleted thread, ticket or WhatsApp history).
    for ch in CHANNELS:
        refs = [r["source_ref"] for r in rows if r["channel"] == ch]
        await db.execute(delete(CRMConversation).where(CRMConversation.channel == ch,
                                                       CRMConversation.source_ref.not_in(refs) if refs else true()))
    await db.flush()
    return len(rows)


# ── visibility ────────────────────────────────────────────────────────────────

def _any(user: Any, *codes: str) -> bool:
    return any(has_permission(user, c) for c in codes)


def visible_clause(user: Any):
    """SQL filter for the conversations this user may see."""
    if getattr(user, "is_superuser", False):
        return true()
    channel = or_(
        and_(CRMConversation.channel == "EMAIL", CRMConversation.mailbox_owner_id == user.id),
        and_(CRMConversation.channel == "WHATSAPP", true() if _any(user, "crm.view", "crm.view_all") else false()),
        and_(CRMConversation.channel == "TICKET", true() if _any(user, "quality.view", "quality.view_all") else false()),
    )
    clause = or_(CRMConversation.assignee_id == user.id, channel)
    company = getattr(user, "company_id", None)
    if company is not None and not _any(user, "crm.view_all"):
        clause = and_(clause, or_(CRMConversation.company_id.is_(None), CRMConversation.company_id == company))
    return clause


def _unread_expr(user_id: UUID):
    read_at = (select(CRMConversationRead.last_read_at)
               .where(CRMConversationRead.conversation_id == CRMConversation.id,
                      CRMConversationRead.user_id == user_id).scalar_subquery())
    return and_(CRMConversation.last_inbound_at.is_not(None),
                or_(read_at.is_(None), CRMConversation.last_inbound_at > read_at))


def _link(c: CRMConversation) -> str:
    if c.channel == "TICKET":
        return "/dashboard/helpdesk"
    if c.channel == "WHATSAPP":
        return "/dashboard/whatsapp"
    return "/dashboard/communication"


def to_dict(c: CRMConversation, unread: bool, now: datetime) -> dict:
    return {
        "id": str(c.id), "channel": c.channel, "subject": c.subject, "contact": c.contact,
        "customer_id": str(c.customer_id) if c.customer_id else None,
        "assignee_id": str(c.assignee_id) if c.assignee_id else None, "status": c.status,
        "last_message_at": c.last_message_at, "sla_due_at": c.sla_due_at,
        "sla_overdue": bool(c.sla_due_at and c.status != "CLOSED" and c.sla_due_at < now),
        "unread": bool(unread), "link": _link(c),
    }


async def list_conversations(db: AsyncSession, user: Any, *, view: str = "all", channel: Optional[str] = None,
                             status: Optional[str] = None, limit: int = 100) -> dict:
    await sync(db)
    unread = _unread_expr(user.id).label("unread")
    # populate_existing: the upsert above is plain SQL, so rows already in this session must be refreshed
    q = select(CRMConversation, unread).where(visible_clause(user)).execution_options(populate_existing=True)
    if view == "mine":
        q = q.where(CRMConversation.assignee_id == user.id)
    elif view == "unassigned":
        q = q.where(CRMConversation.assignee_id.is_(None))
    elif view == "unread":
        q = q.where(_unread_expr(user.id))
    if channel:
        q = q.where(CRMConversation.channel == channel)
    q = q.where(CRMConversation.status == status) if status else q.where(CRMConversation.status != "CLOSED")
    q = q.order_by(CRMConversation.last_message_at.desc().nulls_last()).limit(limit)
    now = datetime.now(timezone.utc)
    items = [to_dict(c, u, now) for c, u in (await db.execute(q)).all()]
    counts = (await db.execute(select(func.count(), func.count().filter(_unread_expr(user.id)))
                               .select_from(CRMConversation)
                               .where(visible_clause(user), CRMConversation.status != "CLOSED"))).one()
    await db.commit()
    return {"items": items, "open": counts[0], "unread": counts[1]}


async def get_visible(db: AsyncSession, user: Any, conversation_id: UUID) -> Optional[CRMConversation]:
    return (await db.execute(select(CRMConversation).where(
        CRMConversation.id == conversation_id, visible_clause(user)).with_for_update())).scalar_one_or_none()


async def mark_read(db: AsyncSession, user: Any, conv: CRMConversation) -> None:
    now = datetime.now(timezone.utc)
    stmt = pg_insert(CRMConversationRead).values(conversation_id=conv.id, user_id=user.id, last_read_at=now)
    await db.execute(stmt.on_conflict_do_update(constraint="uq_crm_conversation_read", set_={"last_read_at": now}))


async def assign(db: AsyncSession, conv: CRMConversation, assignee_id: Optional[UUID]) -> None:
    conv.assignee_id = assignee_id
    if conv.channel == "TICKET":  # keep the helpdesk ticket in step
        ticket = await db.get(HelpdeskTicket, UUID(conv.source_ref))
        if ticket is not None:
            ticket.assigned_to_id = assignee_id


def set_status(conv: CRMConversation, status: str) -> None:
    if conv.channel == "TICKET":
        raise ValueError("Ticket status is managed in the helpdesk")
    conv.status = status
    conv.closed_at = datetime.now(timezone.utc) if status == "CLOSED" else None
