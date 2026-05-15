"""
Quote / Estimation Module
──────────────────────────
Prefix: /api/v1/quotes

Routes:
  GET  /              – list quotes with filters
  POST /              – create quote
  GET  /dashboard     – win/loss stats
  GET  /{id}          – quote detail
  PATCH /{id}         – update lines/fields (DRAFT only)
  POST /{id}/send     – mark as SENT (to customer)
  POST /{id}/accept   – mark ACCEPTED
  POST /{id}/reject   – mark REJECTED with reason
  POST /{id}/expire   – mark EXPIRED
  POST /{id}/revise   – create new version (bumps version, old → locked)
  POST /{id}/convert  – convert ACCEPTED quote → Sales Order
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.quotation import Quotation, QuotationLine, QuoteStatus
from app.models.sales import Customer, SalesOrder, SOLine, SOStatus, PaymentMethod, SOPaymentStatus, OrderSource
from app.models.master import Product
from app.models.user import User
from app.schemas.quotation import (
    QuotationCreate, QuotationUpdate, QuotationRead, QuotationLineRead,
    QuoteRejectRequest, QuoteDashboard,
)
from app.services.commercial_access_service import (
    build_commercial_access_hint,
    can_view_record,
    ensure_commercial_action_allowed,
    inherit_commercial_scope,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_quote_no(existing_count: int) -> str:
    today = date.today().strftime("%Y%m%d")
    seq = str(existing_count + 1).zfill(4)
    return f"QT-{today}-{seq}"


def _calc_line_total(qty: Decimal, price: Decimal, disc: Decimal, tax: Decimal) -> Decimal:
    after_disc = price * qty * (1 - disc / 100)
    return (after_disc * (1 + tax / 100)).quantize(Decimal("0.0001"))


def _compute_totals(lines: List[QuotationLine], overall_disc: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(l.line_total for l in lines)
    disc_amt = subtotal * overall_disc / 100
    after_disc = subtotal - disc_amt
    tax = sum((l.qty * l.unit_price * (1 - l.discount_pct / 100)) * (l.tax_rate / 100) for l in lines)
    grand = after_disc + tax
    return after_disc, tax, grand


async def _build_read(db: AsyncSession, q: Quotation, user: User | None = None) -> QuotationRead:
    row = QuotationRead.model_validate(q)
    if q.customer:
        row.customer_name = q.customer.name
        row.customer_code = q.customer.code
    row.lines = []
    for l in q.lines:
        lr = QuotationLineRead.model_validate(l)
        if l.product:
            lr.product_sku = l.product.sku
            lr.product_name = l.product.name
        row.lines.append(lr)
    if user is not None:
        row.access = build_commercial_access_hint(user, q, "sales")
    return row


async def _get_or_404(db: AsyncSession, quote_id: uuid.UUID) -> Quotation:
    result = await db.execute(
        select(Quotation)
        .options(
            selectinload(Quotation.customer),
            selectinload(Quotation.lines).selectinload(QuotationLine.product),
            selectinload(Quotation.created_by),
        )
        .where(Quotation.id == quote_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Quotation not found")
    return q


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[QuotationRead])
async def list_quotes(
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[QuoteStatus] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Quotation)
        .options(
            selectinload(Quotation.customer),
            selectinload(Quotation.lines).selectinload(QuotationLine.product),
        )
        .order_by(Quotation.created_at.desc())
        .offset(skip).limit(limit)
    )
    if customer_id:
        q = q.where(Quotation.customer_id == customer_id)
    if status:
        q = q.where(Quotation.status == status)
    quotes = list((await db.execute(q)).scalars().all())
    quotes = [qt for qt in quotes if can_view_record(current_user, "sales", qt)]
    return [await _build_read(db, qt, current_user) for qt in quotes]


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=QuoteDashboard)
async def quote_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    counts = {}
    for s in QuoteStatus:
        r = await db.execute(select(func.count(Quotation.id)).where(Quotation.status == s))
        counts[s.value] = r.scalar() or 0

    total = sum(counts.values())
    accepted = counts.get("ACCEPTED", 0) + counts.get("CONVERTED", 0)
    closed = accepted + counts.get("REJECTED", 0)
    win_rate = Decimal(str(round(accepted / closed * 100, 1))) if closed > 0 else None

    pipeline_r = await db.execute(
        select(func.coalesce(func.sum(Quotation.grand_total), 0))
        .where(Quotation.status == QuoteStatus.SENT)
    )
    pipeline = Decimal(str(pipeline_r.scalar() or 0))

    return QuoteDashboard(
        total_quotes=total,
        draft_count=counts.get("DRAFT", 0),
        sent_count=counts.get("SENT", 0),
        accepted_count=accepted,
        rejected_count=counts.get("REJECTED", 0),
        expired_count=counts.get("EXPIRED", 0),
        converted_count=counts.get("CONVERTED", 0),
        win_rate_pct=win_rate,
        total_pipeline=pipeline,
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=QuotationRead, status_code=201)
async def create_quote(
    body: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = await db.get(Customer, body.customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    target = Quotation(**body.model_dump(exclude={"lines"}), quote_no="PENDING", version=1, status=QuoteStatus.DRAFT)
    inherit_commercial_scope(target, customer)
    ensure_commercial_action_allowed(current_user, target, "create", "sales")

    # Generate quote_no
    count_r = await db.execute(select(func.count(Quotation.id)))
    count = count_r.scalar() or 0
    quote_no = _next_quote_no(count)

    quote = Quotation(
        quote_no=quote_no,
        version=1,
        customer_id=body.customer_id,
        crm_record_id=body.crm_record_id,
        status=QuoteStatus.DRAFT,
        company_id=target.company_id,
        branch_id=target.branch_id,
        sales_region_id=target.sales_region_id,
        sales_team_id=target.sales_team_id,
        customer_group_id=target.customer_group_id,
        quote_date=body.quote_date,
        valid_until=body.valid_until,
        currency=body.currency,
        discount_pct=body.discount_pct,
        notes=body.notes,
        internal_notes=body.internal_notes,
        created_by_id=current_user.id,
    )
    db.add(quote)
    await db.flush()

    line_objs = []
    for lc in body.lines:
        lt = _calc_line_total(lc.qty, lc.unit_price, lc.discount_pct, lc.tax_rate)
        line = QuotationLine(
            quote_id=quote.id, line_no=lc.line_no, product_id=lc.product_id,
            description=lc.description, qty=lc.qty, unit=lc.unit,
            unit_price=lc.unit_price, discount_pct=lc.discount_pct,
            tax_rate=lc.tax_rate, line_total=lt,
        )
        db.add(line)
        line_objs.append(line)

    await db.flush()
    subtotal, tax, grand = _compute_totals(line_objs, body.discount_pct)
    quote.total_amount = subtotal
    quote.tax_amount = tax
    quote.grand_total = grand
    await db.commit()

    return await _build_read(db, await _get_or_404(db, quote.id), current_user)


# ── Get ───────────────────────────────────────────────────────────────────────

@router.get("/{quote_id}", response_model=QuotationRead)
async def get_quote(quote_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "view", "sales")
    return await _build_read(db, q, current_user)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{quote_id}", response_model=QuotationRead)
async def update_quote(
    quote_id: uuid.UUID,
    body: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "edit", "sales")
    if q.status not in (QuoteStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT quotes can be updated")

    for k, v in body.model_dump(exclude_none=True, exclude={"lines"}).items():
        setattr(q, k, v)

    if body.lines is not None:
        # Replace lines
        for existing_line in list(q.lines):
            await db.delete(existing_line)
        await db.flush()

        line_objs = []
        for lc in body.lines:
            lt = _calc_line_total(lc.qty, lc.unit_price, lc.discount_pct, lc.tax_rate)
            line = QuotationLine(
                quote_id=q.id, line_no=lc.line_no, product_id=lc.product_id,
                description=lc.description, qty=lc.qty, unit=lc.unit,
                unit_price=lc.unit_price, discount_pct=lc.discount_pct,
                tax_rate=lc.tax_rate, line_total=lt,
            )
            db.add(line)
            line_objs.append(line)

        await db.flush()
        disc = body.discount_pct if body.discount_pct is not None else q.discount_pct
        subtotal, tax, grand = _compute_totals(line_objs, disc)
        q.total_amount = subtotal
        q.tax_amount = tax
        q.grand_total = grand

    await db.commit()
    return await _build_read(db, await _get_or_404(db, quote_id), current_user)


# ── Status Actions ────────────────────────────────────────────────────────────

@router.post("/{quote_id}/send", response_model=QuotationRead)
async def send_quote(quote_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "edit", "sales")
    if q.status not in (QuoteStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT quotes can be sent")
    q.status = QuoteStatus.SENT
    q.sent_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return await _build_read(db, await _get_or_404(db, quote_id), current_user)


@router.post("/{quote_id}/accept", response_model=QuotationRead)
async def accept_quote(quote_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "approve", "sales")
    if q.status not in (QuoteStatus.SENT,):
        raise HTTPException(422, "Only SENT quotes can be accepted")
    q.status = QuoteStatus.ACCEPTED
    q.accepted_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return await _build_read(db, await _get_or_404(db, quote_id), current_user)


@router.post("/{quote_id}/reject", response_model=QuotationRead)
async def reject_quote(
    quote_id: uuid.UUID,
    body: QuoteRejectRequest = QuoteRejectRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "cancel", "sales")
    if q.status not in (QuoteStatus.SENT, QuoteStatus.ACCEPTED):
        raise HTTPException(422, "Cannot reject at current status")
    q.status = QuoteStatus.REJECTED
    q.rejected_at = datetime.now(tz=timezone.utc)
    q.lost_reason = body.lost_reason
    await db.commit()
    return await _build_read(db, await _get_or_404(db, quote_id), current_user)


@router.post("/{quote_id}/expire", response_model=QuotationRead)
async def expire_quote(quote_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "cancel", "sales")
    if q.status not in (QuoteStatus.DRAFT, QuoteStatus.SENT):
        raise HTTPException(422, "Cannot expire at current status")
    q.status = QuoteStatus.EXPIRED
    await db.commit()
    return await _build_read(db, await _get_or_404(db, quote_id), current_user)


# ── Revise (new version) ──────────────────────────────────────────────────────

@router.post("/{quote_id}/revise", response_model=QuotationRead, status_code=201)
async def revise_quote(
    quote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new version of the quote. Old version locked (EXPIRED)."""
    old = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, old, "edit", "sales")
    if old.status in (QuoteStatus.CONVERTED,):
        raise HTTPException(422, "Cannot revise a converted quote")

    old.status = QuoteStatus.EXPIRED
    await db.flush()

    new_q = Quotation(
        quote_no=old.quote_no,
        version=old.version + 1,
        customer_id=old.customer_id,
        crm_record_id=old.crm_record_id,
        status=QuoteStatus.DRAFT,
        company_id=old.company_id,
        branch_id=old.branch_id,
        sales_region_id=old.sales_region_id,
        sales_team_id=old.sales_team_id,
        customer_group_id=old.customer_group_id,
        quote_date=date.today(),
        valid_until=old.valid_until,
        currency=old.currency,
        discount_pct=old.discount_pct,
        notes=old.notes,
        internal_notes=old.internal_notes,
        total_amount=old.total_amount,
        tax_amount=old.tax_amount,
        grand_total=old.grand_total,
        created_by_id=current_user.id,
    )
    db.add(new_q)
    await db.flush()

    for ol in old.lines:
        db.add(QuotationLine(
            quote_id=new_q.id, line_no=ol.line_no, product_id=ol.product_id,
            description=ol.description, qty=ol.qty, unit=ol.unit,
            unit_price=ol.unit_price, discount_pct=ol.discount_pct,
            tax_rate=ol.tax_rate, line_total=ol.line_total,
        ))

    await db.commit()
    return await _build_read(db, await _get_or_404(db, new_q.id), current_user)


# ── Convert to Sales Order ────────────────────────────────────────────────────

@router.post("/{quote_id}/convert", response_model=dict, status_code=201)
async def convert_to_so(
    quote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert an ACCEPTED quotation into a Sales Order."""
    q = await _get_or_404(db, quote_id)
    ensure_commercial_action_allowed(current_user, q, "convert", "sales")
    if q.status != QuoteStatus.ACCEPTED:
        raise HTTPException(422, "Only ACCEPTED quotes can be converted to Sales Orders")

    # Generate SO number
    so_count_r = await db.execute(select(func.count(SalesOrder.id)))
    so_count = so_count_r.scalar() or 0
    today = date.today()
    so_no = f"SO-{today.strftime('%Y%m%d')}-{str(so_count + 1).zfill(4)}"

    so = SalesOrder(
        order_no=so_no,
        customer_id=q.customer_id,
        order_date=today,
        requested_delivery_date=today + timedelta(days=7),
        status=SOStatus.DRAFT,
        currency=q.currency,
        company_id=q.company_id,
        branch_id=q.branch_id,
        sales_region_id=q.sales_region_id,
        sales_team_id=q.sales_team_id,
        customer_group_id=q.customer_group_id,
        notes=f"Converted from Quote {q.quote_no} v{q.version}",
        created_by_id=current_user.id,
        source=OrderSource.MANUAL,
        payment_method=PaymentMethod.CASH,
        payment_status=SOPaymentStatus.PENDING,
    )
    db.add(so)
    await db.flush()

    product_lines = [ql for ql in q.lines if ql.product_id is not None]
    if not product_lines:
        raise HTTPException(422, "Cannot convert: quotation has no product lines")
    for i, ql in enumerate(product_lines, start=1):
        db.add(SOLine(
            so_id=so.id,
            line_no=i,
            product_id=ql.product_id,
            ordered_quantity=ql.qty,
            unit=ql.unit,
            unit_price=ql.unit_price,
            discount_pct=ql.discount_pct,
            tax_rate=ql.tax_rate,
        ))

    q.status = QuoteStatus.CONVERTED
    q.converted_so_id = so.id
    await db.commit()

    return {"so_id": str(so.id), "so_no": so_no, "quote_no": q.quote_no, "version": q.version}
