"""
Retail / Shop POS
──────────────────
Prefix: /api/v1/pos

Routes:
  GET  /sessions              – list sessions
  POST /sessions              – open new session
  GET  /sessions/current      – get caller's open session
  GET  /sessions/{id}         – get session detail
  POST /sessions/{id}/close   – close session

  POST /sales                 – create sale (links to caller's open session)
  GET  /sales/{id}            – sale detail
  POST /sales/{id}/void       – void sale

  GET  /dashboard             – today's stats
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.pos import (
    POSSession, POSSale, POSSaleLine,
    POSSessionStatus, POSPaymentMethod, POSSaleStatus,
)
from app.models.user import User
from app.schemas.pos import (
    OpenSessionRequest, CloseSessionRequest, POSSessionRead,
    POSSaleCreate, POSSaleRead, POSSaleLineRead,
    POSDashboard,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_session_no(seq: int) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"SES-{today}-{str(seq + 1).zfill(4)}"


def _next_sale_no(seq: int) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"POS-{today}-{str(seq + 1).zfill(4)}"


def _calc_line_total(qty: Decimal, price: Decimal, disc: Decimal, tax: Decimal) -> Decimal:
    after_disc = price * qty * (1 - disc / 100)
    return (after_disc * (1 + tax / 100)).quantize(Decimal("0.01"))


async def _get_session_or_404(db: AsyncSession, session_id: uuid.UUID) -> POSSession:
    result = await db.execute(
        select(POSSession)
        .options(selectinload(POSSession.cashier), selectinload(POSSession.sales))
        .where(POSSession.id == session_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Session not found")
    return s


def _session_read(s: POSSession) -> POSSessionRead:
    r = POSSessionRead.model_validate(s)
    if s.cashier:
        r.cashier_name = getattr(s.cashier, "full_name", None) or s.cashier.username
    return r


async def _get_sale_or_404(db: AsyncSession, sale_id: uuid.UUID) -> POSSale:
    result = await db.execute(
        select(POSSale)
        .options(
            selectinload(POSSale.cashier),
            selectinload(POSSale.customer),
            selectinload(POSSale.lines).selectinload(POSSaleLine.product),
        )
        .where(POSSale.id == sale_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Sale not found")
    return s


def _sale_read(s: POSSale) -> POSSaleRead:
    r = POSSaleRead.model_validate(s)
    if s.cashier:
        r.cashier_name = getattr(s.cashier, "full_name", None) or s.cashier.username
    if s.customer:
        r.customer_name = s.customer.name
    r.lines = []
    for l in s.lines:
        lr = POSSaleLineRead.model_validate(l)
        if l.product:
            lr.product_name = l.product.name
            lr.product_sku  = l.product.sku
        r.lines.append(lr)
    return r


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[POSSessionRead])
async def list_sessions(
    status: Optional[POSSessionStatus] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(POSSession)
        .options(selectinload(POSSession.cashier))
        .order_by(POSSession.created_at.desc())
        .offset(skip).limit(limit)
    )
    if status:
        q = q.where(POSSession.status == status)
    sessions = list((await db.execute(q)).scalars().all())
    return [_session_read(s) for s in sessions]


@router.get("/sessions/current", response_model=Optional[POSSessionRead])
async def get_current_session(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(POSSession)
        .options(selectinload(POSSession.cashier))
        .where(POSSession.cashier_id == current_user.id, POSSession.status == POSSessionStatus.OPEN)
        .order_by(POSSession.opened_at.desc())
        .limit(1)
    )
    s = result.scalar_one_or_none()
    return _session_read(s) if s else None


@router.post("/sessions", response_model=POSSessionRead, status_code=201)
async def open_session(
    body: OpenSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check no existing open session for this cashier
    existing = await db.execute(
        select(POSSession).where(
            POSSession.cashier_id == current_user.id,
            POSSession.status == POSSessionStatus.OPEN,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(422, "You already have an open session. Close it first.")

    seq_r = await db.execute(select(func.count(POSSession.id)))
    seq = seq_r.scalar() or 0

    session = POSSession(
        session_no=_next_session_no(seq),
        cashier_id=current_user.id,
        register_id=body.register_id,
        status=POSSessionStatus.OPEN,
        opened_at=datetime.now(tz=timezone.utc),
        opening_float=body.opening_float,
    )
    db.add(session)
    await db.commit()
    return _session_read(await _get_session_or_404(db, session.id))


@router.get("/sessions/{session_id}", response_model=POSSessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return _session_read(await _get_session_or_404(db, session_id))


@router.post("/sessions/{session_id}/close", response_model=POSSessionRead)
async def close_session(
    session_id: uuid.UUID,
    body: CloseSessionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    s = await _get_session_or_404(db, session_id)
    if s.status == POSSessionStatus.CLOSED:
        raise HTTPException(422, "Session already closed")

    # Calculate expected cash: opening float + all cash sales
    cash_sales_r = await db.execute(
        select(func.coalesce(func.sum(POSSale.sale_total), 0))
        .where(
            POSSale.session_id == session_id,
            POSSale.payment_method == POSPaymentMethod.CASH,
            POSSale.status == POSSaleStatus.COMPLETED,
        )
    )
    cash_sales = Decimal(str(cash_sales_r.scalar() or 0))

    s.status = POSSessionStatus.CLOSED
    s.closed_at = datetime.now(tz=timezone.utc)
    s.closing_cash = body.closing_cash
    s.expected_cash = s.opening_float + cash_sales
    s.cash_difference = body.closing_cash - s.expected_cash
    s.notes = body.notes
    await db.commit()
    return _session_read(await _get_session_or_404(db, session_id))


# ── Sales ─────────────────────────────────────────────────────────────────────

@router.post("/sales", response_model=POSSaleRead, status_code=201)
async def create_sale(
    body: POSSaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.lines:
        raise HTTPException(422, "Sale must have at least one line")

    # Find caller's open session
    sess_r = await db.execute(
        select(POSSession).where(
            POSSession.cashier_id == current_user.id,
            POSSession.status == POSSessionStatus.OPEN,
        ).limit(1)
    )
    session = sess_r.scalar_one_or_none()
    if not session:
        raise HTTPException(422, "No open session. Please open a register session first.")

    seq_r = await db.execute(select(func.count(POSSale.id)))
    seq = seq_r.scalar() or 0

    # Compute totals
    line_objs = []
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    disc_total = Decimal("0")

    for i, lc in enumerate(body.lines, start=1):
        lt = _calc_line_total(lc.qty, lc.unit_price, lc.discount_pct, lc.tax_rate)
        after_disc_pretax = lc.unit_price * lc.qty * (1 - lc.discount_pct / 100)
        disc_amt = lc.unit_price * lc.qty - after_disc_pretax
        tax_amt = after_disc_pretax * (lc.tax_rate / 100)
        subtotal  += lc.unit_price * lc.qty
        disc_total += disc_amt
        tax_total  += tax_amt
        line_objs.append((i, lc, lt))

    sale_total = subtotal - disc_total + tax_total
    change = (body.amount_paid - sale_total) if body.amount_paid is not None else None

    sale = POSSale(
        sale_no=_next_sale_no(seq),
        session_id=session.id,
        cashier_id=current_user.id,
        customer_id=body.customer_id,
        payment_method=body.payment_method,
        status=POSSaleStatus.COMPLETED,
        subtotal=subtotal.quantize(Decimal("0.01")),
        discount_total=disc_total.quantize(Decimal("0.01")),
        tax_total=tax_total.quantize(Decimal("0.01")),
        sale_total=sale_total.quantize(Decimal("0.01")),
        amount_paid=body.amount_paid,
        change_given=change.quantize(Decimal("0.01")) if change is not None else None,
        mpesa_ref=body.mpesa_ref,
        notes=body.notes,
    )
    db.add(sale)
    await db.flush()

    for i, lc, lt in line_objs:
        db.add(POSSaleLine(
            sale_id=sale.id, line_no=i,
            product_id=lc.product_id, qty=lc.qty,
            unit_price=lc.unit_price, discount_pct=lc.discount_pct,
            tax_rate=lc.tax_rate, line_total=lt,
        ))

    # Update session totals
    session.total_sales = (session.total_sales or Decimal("0")) + sale_total
    session.total_transactions = (session.total_transactions or 0) + 1

    await db.commit()
    return _sale_read(await _get_sale_or_404(db, sale.id))


@router.get("/sales/{sale_id}", response_model=POSSaleRead)
async def get_sale(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return _sale_read(await _get_sale_or_404(db, sale_id))


@router.post("/sales/{sale_id}/void", response_model=POSSaleRead)
async def void_sale(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    s = await _get_sale_or_404(db, sale_id)
    if s.status == POSSaleStatus.VOIDED:
        raise HTTPException(422, "Sale already voided")
    s.status = POSSaleStatus.VOIDED

    # Reverse session totals
    sess = await _get_session_or_404(db, s.session_id)
    sess.total_sales = max(Decimal("0"), (sess.total_sales or Decimal("0")) - s.sale_total)
    sess.total_transactions = max(0, (sess.total_transactions or 1) - 1)

    await db.commit()
    return _sale_read(await _get_sale_or_404(db, sale_id))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=POSDashboard)
async def pos_dashboard(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()

    def today_filter(q):
        return q.where(
            cast(POSSale.created_at, Date) == today,
            POSSale.status == POSSaleStatus.COMPLETED,
        )

    count_r = await db.execute(today_filter(select(func.count(POSSale.id))))
    total_r = await db.execute(today_filter(select(func.coalesce(func.sum(POSSale.sale_total), 0))))
    cash_r  = await db.execute(today_filter(select(func.coalesce(func.sum(POSSale.sale_total), 0))
                                            .where(POSSale.payment_method == POSPaymentMethod.CASH)))
    mpesa_r = await db.execute(today_filter(select(func.coalesce(func.sum(POSSale.sale_total), 0))
                                            .where(POSSale.payment_method == POSPaymentMethod.MPESA)))
    card_r  = await db.execute(today_filter(select(func.coalesce(func.sum(POSSale.sale_total), 0))
                                            .where(POSSale.payment_method == POSPaymentMethod.CARD)))

    cnt     = count_r.scalar() or 0
    total   = Decimal(str(total_r.scalar() or 0))
    cash    = Decimal(str(cash_r.scalar()  or 0))
    mpesa   = Decimal(str(mpesa_r.scalar() or 0))
    card    = Decimal(str(card_r.scalar()  or 0))

    open_r  = await db.execute(select(func.count(POSSession.id)).where(POSSession.status == POSSessionStatus.OPEN))
    open_cnt = open_r.scalar() or 0

    avg = (total / cnt).quantize(Decimal("0.01")) if cnt > 0 else None

    return POSDashboard(
        today_sales_count=cnt,
        today_sales_total=total,
        today_cash_total=cash,
        today_mpesa_total=mpesa,
        today_card_total=card,
        open_sessions=open_cnt,
        avg_basket_value=avg,
    )
