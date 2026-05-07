"""
Helpdesk / Customer Complaint Ticketing
────────────────────────────────────────
Prefix: /api/v1/helpdesk

Routes:
  GET  /              – list tickets (filter by status, category, priority, customer)
  POST /              – create ticket
  GET  /dashboard     – KPI stats
  GET  /{id}          – ticket detail with comments
  PATCH /{id}         – update subject/description/category/priority
  POST /{id}/assign   – assign to user
  POST /{id}/escalate – escalate (status → ESCALATED)
  POST /{id}/resolve  – mark RESOLVED + first_response_at if needed
  POST /{id}/close    – mark CLOSED + capture satisfaction score
  POST /{id}/reopen   – reopen CLOSED/RESOLVED → OPEN
  POST /{id}/comments – add comment/internal note
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.helpdesk import (
    HelpdeskTicket, TicketComment,
    TicketStatus, TicketCategory, TicketPriority, SLA_DEFAULTS,
)
from app.models.user import User
from app.schemas.helpdesk import (
    TicketCreate, TicketUpdate, TicketRead, TicketCommentCreate, TicketCommentRead,
    TicketAssignRequest, TicketResolveRequest, TicketCloseRequest, HelpdeskDashboard,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_ticket_no(seq: int) -> str:
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    return f"TKT-{today}-{str(seq + 1).zfill(4)}"


def _is_sla_breached(ticket: HelpdeskTicket) -> bool:
    if ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        end = ticket.resolved_at or ticket.closed_at
    else:
        end = datetime.now(tz=timezone.utc)
    if end is None:
        return False
    deadline = ticket.created_at.replace(tzinfo=timezone.utc) + timedelta(hours=ticket.sla_hours)
    return end > deadline


async def _build_read(ticket: HelpdeskTicket) -> TicketRead:
    row = TicketRead.model_validate(ticket)
    if ticket.customer:
        row.customer_name = ticket.customer.name
        row.customer_code = ticket.customer.code
    if ticket.lot:
        row.lot_number = ticket.lot.lot_number
    if ticket.assigned_to:
        row.assigned_to_name = ticket.assigned_to.full_name if hasattr(ticket.assigned_to, "full_name") else ticket.assigned_to.username
    row.sla_breached = _is_sla_breached(ticket)
    row.comments = []
    for c in ticket.comments:
        cr = TicketCommentRead.model_validate(c)
        if c.created_by:
            cr.created_by_name = getattr(c.created_by, "full_name", None) or c.created_by.username
        row.comments.append(cr)
    return row


async def _get_or_404(db: AsyncSession, ticket_id: uuid.UUID) -> HelpdeskTicket:
    result = await db.execute(
        select(HelpdeskTicket)
        .options(
            selectinload(HelpdeskTicket.customer),
            selectinload(HelpdeskTicket.lot),
            selectinload(HelpdeskTicket.assigned_to),
            selectinload(HelpdeskTicket.created_by),
            selectinload(HelpdeskTicket.comments).selectinload(TicketComment.created_by),
        )
        .where(HelpdeskTicket.id == ticket_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[TicketRead])
async def list_tickets(
    status:      Optional[TicketStatus]   = None,
    category:    Optional[TicketCategory] = None,
    priority:    Optional[TicketPriority] = None,
    customer_id: Optional[uuid.UUID]      = None,
    assigned_to: Optional[uuid.UUID]      = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(HelpdeskTicket)
        .options(
            selectinload(HelpdeskTicket.customer),
            selectinload(HelpdeskTicket.lot),
            selectinload(HelpdeskTicket.assigned_to),
            selectinload(HelpdeskTicket.created_by),
            selectinload(HelpdeskTicket.comments).selectinload(TicketComment.created_by),
        )
        .order_by(HelpdeskTicket.created_at.desc())
        .offset(skip).limit(limit)
    )
    if status:      q = q.where(HelpdeskTicket.status == status)
    if category:    q = q.where(HelpdeskTicket.category == category)
    if priority:    q = q.where(HelpdeskTicket.priority == priority)
    if customer_id: q = q.where(HelpdeskTicket.customer_id == customer_id)
    if assigned_to: q = q.where(HelpdeskTicket.assigned_to_id == assigned_to)
    tickets = list((await db.execute(q)).scalars().all())
    return [await _build_read(t) for t in tickets]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=HelpdeskDashboard)
async def helpdesk_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    counts: dict = {}
    for s in TicketStatus:
        r = await db.execute(select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.status == s))
        counts[s.value] = r.scalar() or 0

    by_cat: dict = {}
    for c in TicketCategory:
        r = await db.execute(select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.category == c))
        by_cat[c.value] = r.scalar() or 0

    by_pri: dict = {}
    for p in TicketPriority:
        r = await db.execute(select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.priority == p))
        by_pri[p.value] = r.scalar() or 0

    # SLA breach count — open/in-progress tickets past deadline
    all_open = (await db.execute(
        select(HelpdeskTicket).where(HelpdeskTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED]))
    )).scalars().all()
    now = datetime.now(tz=timezone.utc)
    breached = sum(
        1 for t in all_open
        if now > t.created_at.replace(tzinfo=timezone.utc) + timedelta(hours=t.sla_hours)
    )

    # Avg resolution hours (resolved + closed)
    resolved = (await db.execute(
        select(HelpdeskTicket).where(
            HelpdeskTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            HelpdeskTicket.resolved_at.isnot(None),
        )
    )).scalars().all()
    avg_res = None
    if resolved:
        diffs = [
            (t.resolved_at.replace(tzinfo=timezone.utc) - t.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            for t in resolved
        ]
        avg_res = round(sum(diffs) / len(diffs), 1)

    return HelpdeskDashboard(
        total_tickets=sum(counts.values()),
        open_count=counts.get("OPEN", 0),
        in_progress_count=counts.get("IN_PROGRESS", 0),
        escalated_count=counts.get("ESCALATED", 0),
        resolved_count=counts.get("RESOLVED", 0),
        closed_count=counts.get("CLOSED", 0),
        sla_breached_count=breached,
        avg_resolution_hours=avg_res,
        by_category=by_cat,
        by_priority=by_pri,
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=TicketRead, status_code=201)
async def create_ticket(
    body: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_r = await db.execute(select(func.count(HelpdeskTicket.id)))
    seq = count_r.scalar() or 0
    sla = body.sla_hours if body.sla_hours is not None else SLA_DEFAULTS[body.priority]

    ticket = HelpdeskTicket(
        ticket_no=_next_ticket_no(seq),
        customer_id=body.customer_id,
        category=body.category,
        priority=body.priority,
        status=TicketStatus.OPEN,
        source=body.source,
        subject=body.subject,
        description=body.description,
        lot_id=body.lot_id,
        sla_hours=sla,
        created_by_id=current_user.id,
    )
    db.add(ticket)
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket.id))


# ── Get ───────────────────────────────────────────────────────────────────────

@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(422, "Cannot update a closed ticket")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Assign ────────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/assign", response_model=TicketRead)
async def assign_ticket(
    ticket_id: uuid.UUID,
    body: TicketAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    t.assigned_to_id = body.user_id
    if t.status == TicketStatus.OPEN:
        t.status = TicketStatus.IN_PROGRESS
    if t.first_response_at is None:
        t.first_response_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Escalate ──────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/escalate", response_model=TicketRead)
async def escalate_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        raise HTTPException(422, "Cannot escalate a resolved/closed ticket")
    t.status = TicketStatus.ESCALATED
    t.priority = TicketPriority.HIGH if t.priority == TicketPriority.MEDIUM else TicketPriority.CRITICAL
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Resolve ───────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/resolve", response_model=TicketRead)
async def resolve_ticket(
    ticket_id: uuid.UUID,
    body: TicketResolveRequest = TicketResolveRequest(),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(422, "Ticket is already closed")
    t.status = TicketStatus.RESOLVED
    t.resolved_at = datetime.now(tz=timezone.utc)
    if body.resolution_notes:
        t.resolution_notes = body.resolution_notes
    if t.first_response_at is None:
        t.first_response_at = t.resolved_at
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Close ─────────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/close", response_model=TicketRead)
async def close_ticket(
    ticket_id: uuid.UUID,
    body: TicketCloseRequest = TicketCloseRequest(),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(422, "Already closed")
    now = datetime.now(tz=timezone.utc)
    t.status = TicketStatus.CLOSED
    t.closed_at = now
    if t.resolved_at is None:
        t.resolved_at = now
    if t.first_response_at is None:
        t.first_response_at = now
    if body.customer_satisfaction is not None:
        t.customer_satisfaction = body.customer_satisfaction
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Reopen ────────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/reopen", response_model=TicketRead)
async def reopen_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        raise HTTPException(422, "Only resolved/closed tickets can be reopened")
    t.status = TicketStatus.OPEN
    t.resolved_at = None
    t.closed_at = None
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))


# ── Add Comment ───────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/comments", response_model=TicketRead, status_code=201)
async def add_comment(
    ticket_id: uuid.UUID,
    body: TicketCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = await _get_or_404(db, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(422, "Cannot comment on a closed ticket")
    if t.first_response_at is None and not body.is_internal:
        t.first_response_at = datetime.now(tz=timezone.utc)
    comment = TicketComment(
        ticket_id=ticket_id,
        body=body.body,
        is_internal=body.is_internal,
        created_by_id=current_user.id,
    )
    db.add(comment)
    await db.commit()
    return await _build_read(await _get_or_404(db, ticket_id))
