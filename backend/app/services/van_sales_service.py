"""Van Sales / Mobile POS service — route sales, stock, payments, offline sync."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.van_sales import (
    Van, VanStock, VanStockMovement, VanVisit, VanSalesTxn,
    VanSalesTxnLine, VanPayment, VanReconciliation, VSAIRecommendation,
    VanStatus, TxnType, TxnStatus, PaymentStatus, VisitStatus,
    ReconciliationStatus, VSAIAgentType, VSAIRecStatus,
)
from app.models.sales import Customer
from app.schemas.van_sales import (
    VanCreate, VanUpdate, StockLoadRequest,
    VisitCreate, VisitCheckIn, TxnCreate, PaymentCreate,
    ReconciliationCreate, SyncPayload, SyncResult, VSAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _gen_txn_no(prefix: str = "VS") -> str:
    import random
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rnd = random.randint(100, 999)
    return f"{prefix}-{ts}-{rnd}"


def _gen_receipt_no() -> str:
    import random
    return f"RCP-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


# ── Van CRUD ──────────────────────────────────────────────────────────────────

async def list_vans(
    db: AsyncSession, status: Optional[str] = None, skip: int = 0, limit: int = 50
) -> List[Van]:
    q = select(Van)
    if status:
        q = q.where(Van.status == status)
    result = await db.execute(q.order_by(Van.van_code).offset(skip).limit(limit))
    return result.scalars().all()


async def get_van(db: AsyncSession, van_id: uuid.UUID) -> Optional[Van]:
    return await db.get(Van, van_id)


async def create_van(db: AsyncSession, payload: VanCreate) -> Van:
    v = Van(**payload.model_dump())
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


async def update_van(db: AsyncSession, van: Van, payload: VanUpdate) -> Van:
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(van, field, value)
    await db.commit()
    await db.refresh(van)
    return van


# ── Van Stock ─────────────────────────────────────────────────────────────────

async def get_van_stock(db: AsyncSession, van_id: uuid.UUID) -> List[VanStock]:
    result = await db.execute(
        select(VanStock).where(VanStock.van_id == van_id).order_by(VanStock.created_at)
    )
    return result.scalars().all()


async def load_stock(
    db: AsyncSession, van: Van, payload: StockLoadRequest, user_id: Optional[uuid.UUID]
) -> List[VanStock]:
    updated: list[VanStock] = []
    for line in payload.lines:
        existing = await db.execute(
            select(VanStock).where(
                VanStock.van_id == van.id,
                VanStock.item_id == line.item_id,
                VanStock.batch_id == line.batch_id,
            )
        )
        vs = existing.scalars().first()
        if vs:
            vs.quantity += line.quantity
        else:
            vs = VanStock(
                van_id=van.id,
                item_id=line.item_id,
                batch_id=line.batch_id,
                quantity=line.quantity,
                uom=line.uom,
                unit_cost=line.unit_cost,
            )
            db.add(vs)

        mov = VanStockMovement(
            van_id=van.id,
            item_id=line.item_id,
            batch_id=line.batch_id,
            movement_type="LOAD",
            quantity=line.quantity,
            reference_no=f"LOAD-{datetime.utcnow().strftime('%Y%m%d')}",
            moved_by=user_id,
            notes=payload.notes,
        )
        db.add(mov)
        updated.append(vs)

    await db.commit()
    return updated


async def _deduct_van_stock(
    db: AsyncSession, van_id: uuid.UUID, item_id: uuid.UUID,
    batch_id: Optional[uuid.UUID], qty: Decimal, txn_no: str
) -> None:
    result = await db.execute(
        select(VanStock).where(
            VanStock.van_id == van_id,
            VanStock.item_id == item_id,
            VanStock.batch_id == batch_id,
        )
    )
    vs = result.scalars().first()
    if vs:
        vs.quantity = max(Decimal("0"), vs.quantity - qty)
    mov = VanStockMovement(
        van_id=van_id, item_id=item_id, batch_id=batch_id,
        movement_type="SALE", quantity=-qty, reference_no=txn_no,
    )
    db.add(mov)


async def _add_van_stock(
    db: AsyncSession, van_id: uuid.UUID, item_id: uuid.UUID,
    batch_id: Optional[uuid.UUID], qty: Decimal, txn_no: str, uom: str
) -> None:
    result = await db.execute(
        select(VanStock).where(
            VanStock.van_id == van_id,
            VanStock.item_id == item_id,
            VanStock.batch_id == batch_id,
        )
    )
    vs = result.scalars().first()
    if vs:
        vs.quantity += qty
    else:
        vs = VanStock(van_id=van_id, item_id=item_id, batch_id=batch_id, quantity=qty, uom=uom)
        db.add(vs)
    mov = VanStockMovement(
        van_id=van_id, item_id=item_id, batch_id=batch_id,
        movement_type="RETURN", quantity=qty, reference_no=txn_no,
    )
    db.add(mov)


# ── Visits ────────────────────────────────────────────────────────────────────

async def list_visits(
    db: AsyncSession, van_id: uuid.UUID, route_date: Optional[date] = None
) -> List[VanVisit]:
    q = select(VanVisit).where(VanVisit.van_id == van_id)
    if route_date:
        q = q.where(VanVisit.route_date == route_date)
    result = await db.execute(q.order_by(VanVisit.sequence_no.nullslast(), VanVisit.planned_time))
    return result.scalars().all()


async def create_visit(
    db: AsyncSession, van: Van, payload: VisitCreate
) -> VanVisit:
    if payload.offline_id:
        existing = await db.execute(
            select(VanVisit).where(VanVisit.offline_id == payload.offline_id)
        )
        if existing.scalars().first():
            raise ValueError(f"Visit with offline_id {payload.offline_id} already exists")

    visit = VanVisit(
        van_id=van.id,
        route_id=van.route_id,
        customer_id=payload.customer_id,
        route_date=payload.route_date,
        sequence_no=payload.sequence_no,
        planned_time=payload.planned_time,
        offline_id=payload.offline_id,
        notes=payload.notes,
        status=VisitStatus.PLANNED.value,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


async def check_in_visit(
    db: AsyncSession, visit: VanVisit, payload: VisitCheckIn
) -> VanVisit:
    visit.status = VisitStatus.CHECKED_IN.value
    visit.check_in_time = datetime.utcnow()
    if payload.gps_lat:
        visit.gps_lat = payload.gps_lat
    if payload.gps_lng:
        visit.gps_lng = payload.gps_lng
    await db.commit()
    await db.refresh(visit)
    return visit


async def check_out_visit(
    db: AsyncSession, visit: VanVisit, notes: Optional[str] = None
) -> VanVisit:
    visit.status = VisitStatus.COMPLETED.value
    visit.check_out_time = datetime.utcnow()
    if notes:
        visit.notes = notes
    await db.commit()
    await db.refresh(visit)
    return visit


async def mark_missed_visit(
    db: AsyncSession, visit: VanVisit, reason: Optional[str]
) -> VanVisit:
    visit.status = VisitStatus.MISSED.value
    visit.missed_reason = reason
    await db.commit()
    await db.refresh(visit)
    return visit


# ── Transactions ──────────────────────────────────────────────────────────────

def _calc_lines(lines_data: list) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    subtotal = discount_total = tax_total = grand_total = Decimal("0")
    for l in lines_data:
        qty = _D(l.quantity)
        price = _D(l.unit_price)
        disc_pct = _D(l.discount_pct)
        tax_pct = _D(l.tax_pct)

        gross = qty * price
        disc_amt = gross * disc_pct / 100
        taxable = gross - disc_amt
        tax_amt = taxable * tax_pct / 100
        line_total = taxable + tax_amt

        subtotal += gross
        discount_total += disc_amt
        tax_total += tax_amt
        grand_total += line_total

    return subtotal, discount_total, tax_total, grand_total


async def create_transaction(
    db: AsyncSession, van: Van, payload: TxnCreate, user_id: Optional[uuid.UUID]
) -> VanSalesTxn:
    # Dedup by offline_id
    if payload.offline_id:
        existing = await db.execute(
            select(VanSalesTxn).where(VanSalesTxn.offline_id == payload.offline_id)
        )
        if existing.scalars().first():
            raise ValueError(f"Transaction with offline_id {payload.offline_id} already synced")

    subtotal, discount_total, tax_total, grand_total = _calc_lines(payload.lines)

    txn = VanSalesTxn(
        txn_no=_gen_txn_no("VS" if payload.txn_type == "SALE" else "VR"),
        van_id=van.id,
        route_id=van.route_id,
        customer_id=payload.customer_id,
        visit_id=payload.visit_id,
        driver_id=user_id,
        txn_type=payload.txn_type,
        txn_datetime=payload.txn_datetime,
        status=TxnStatus.CONFIRMED.value,
        payment_status=PaymentStatus.UNPAID.value,
        subtotal=subtotal,
        discount_amount=discount_total,
        tax_amount=tax_total,
        total_amount=grand_total,
        paid_amount=Decimal("0"),
        balance_due=grand_total,
        price_list_id=payload.price_list_id,
        offline_id=payload.offline_id,
        device_id=payload.device_id,
        notes=payload.notes,
    )
    db.add(txn)
    await db.flush()

    for lp in payload.lines:
        qty = _D(lp.quantity)
        price = _D(lp.unit_price)
        disc_pct = _D(lp.discount_pct)
        tax_pct = _D(lp.tax_pct)
        gross = qty * price
        disc_amt = gross * disc_pct / 100
        taxable = gross - disc_amt
        tax_amt = taxable * tax_pct / 100
        line_total = taxable + tax_amt

        line = VanSalesTxnLine(
            txn_id=txn.id,
            item_id=lp.item_id,
            batch_id=lp.batch_id,
            uom=lp.uom,
            quantity=qty,
            unit_price=price,
            discount_pct=disc_pct,
            discount_amt=disc_amt,
            tax_pct=tax_pct,
            tax_amt=tax_amt,
            line_total=line_total,
            return_reason=lp.return_reason,
            notes=lp.notes,
        )
        db.add(line)

        # Adjust van stock
        if payload.txn_type == TxnType.SALE.value:
            await _deduct_van_stock(db, van.id, lp.item_id, lp.batch_id, qty, txn.txn_no)
        elif payload.txn_type == TxnType.RETURN.value:
            await _add_van_stock(db, van.id, lp.item_id, lp.batch_id, qty, txn.txn_no, lp.uom)

    await db.commit()
    await db.refresh(txn)
    return txn


async def list_transactions(
    db: AsyncSession, van_id: uuid.UUID, route_date: Optional[date] = None,
    skip: int = 0, limit: int = 100
) -> List[VanSalesTxn]:
    q = select(VanSalesTxn).options(
        selectinload(VanSalesTxn.lines),
        selectinload(VanSalesTxn.payments),
    ).where(VanSalesTxn.van_id == van_id)
    if route_date:
        q = q.where(func.date(VanSalesTxn.txn_datetime) == route_date)
    result = await db.execute(q.order_by(VanSalesTxn.txn_datetime.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def get_transaction(db: AsyncSession, txn_id: uuid.UUID) -> Optional[VanSalesTxn]:
    result = await db.execute(
        select(VanSalesTxn).options(
            selectinload(VanSalesTxn.lines),
            selectinload(VanSalesTxn.payments),
        ).where(VanSalesTxn.id == txn_id)
    )
    return result.scalars().first()


# ── Payments ──────────────────────────────────────────────────────────────────

async def add_payment(
    db: AsyncSession, txn: VanSalesTxn, payload: PaymentCreate, user_id: Optional[uuid.UUID]
) -> VanPayment:
    payment = VanPayment(
        txn_id=txn.id,
        method=payload.method,
        amount=payload.amount,
        reference_no=payload.reference_no,
        collected_at=payload.collected_at,
        collected_by=user_id,
        receipt_no=_gen_receipt_no(),
        notes=payload.notes,
    )
    db.add(payment)

    txn.paid_amount = (txn.paid_amount or Decimal("0")) + payload.amount
    txn.balance_due = max(Decimal("0"), (txn.total_amount or Decimal("0")) - txn.paid_amount)
    if txn.balance_due == 0:
        txn.payment_status = PaymentStatus.PAID.value
    elif txn.paid_amount > 0:
        txn.payment_status = PaymentStatus.PARTIAL.value

    await db.commit()
    await db.refresh(payment)
    return payment


# ── Reconciliation ────────────────────────────────────────────────────────────

async def create_reconciliation(
    db: AsyncSession, van: Van, payload: ReconciliationCreate, user_id: Optional[uuid.UUID]
) -> VanReconciliation:
    route_date = payload.route_date

    # Aggregate sales
    txns_result = await db.execute(
        select(VanSalesTxn).options(selectinload(VanSalesTxn.lines), selectinload(VanSalesTxn.payments)).where(
            VanSalesTxn.van_id == van.id,
            func.date(VanSalesTxn.txn_datetime) == route_date,
            VanSalesTxn.status != TxnStatus.CANCELLED.value,
        )
    )
    txns = txns_result.scalars().all()

    total_sales = sum(_D(t.total_amount) for t in txns if t.txn_type == TxnType.SALE.value)
    total_returns = sum(_D(t.total_amount) for t in txns if t.txn_type == TxnType.RETURN.value)

    all_payments = [p for t in txns for p in t.payments]
    total_cash = sum(_D(p.amount) for p in all_payments if p.method == "CASH")
    total_mpesa = sum(_D(p.amount) for p in all_payments if p.method == "MPESA")
    total_credit = sum(_D(p.amount) for p in all_payments if p.method == "CREDIT")

    # Build sales_qty / returns_qty by item
    sales_qty: dict[str, float] = {}
    returns_qty: dict[str, float] = {}
    for t in txns:
        for l in t.lines:
            key = str(l.item_id)
            if t.txn_type == TxnType.SALE.value:
                sales_qty[key] = sales_qty.get(key, 0) + float(l.quantity)
            elif t.txn_type == TxnType.RETURN.value:
                returns_qty[key] = returns_qty.get(key, 0) + float(l.quantity)

    # Current van stock as closing stock
    stock_result = await db.execute(select(VanStock).where(VanStock.van_id == van.id))
    closing_stock = {str(s.item_id): float(s.quantity) for s in stock_result.scalars().all()}

    recon = VanReconciliation(
        van_id=van.id,
        route_date=route_date,
        status=ReconciliationStatus.SUBMITTED.value,
        closing_stock=payload.closing_stock or closing_stock,
        sales_qty=sales_qty,
        returns_qty=returns_qty,
        total_sales=total_sales,
        total_cash=total_cash,
        total_mpesa=total_mpesa,
        total_credit=total_credit,
        total_returns=total_returns,
        submitted_by=user_id,
        notes=payload.notes,
    )
    db.add(recon)
    await db.commit()
    await db.refresh(recon)
    return recon


async def approve_reconciliation(
    db: AsyncSession, recon: VanReconciliation, user_id: Optional[uuid.UUID]
) -> VanReconciliation:
    recon.status = ReconciliationStatus.APPROVED.value
    recon.approved_by = user_id
    recon.approved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(recon)
    return recon


async def list_reconciliations(
    db: AsyncSession, van_id: uuid.UUID, skip: int = 0, limit: int = 30
) -> List[VanReconciliation]:
    result = await db.execute(
        select(VanReconciliation)
        .where(VanReconciliation.van_id == van_id)
        .order_by(VanReconciliation.route_date.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


# ── Offline Sync ──────────────────────────────────────────────────────────────

async def process_sync(
    db: AsyncSession, van: Van, payload: SyncPayload, user_id: Optional[uuid.UUID]
) -> SyncResult:
    result = SyncResult()

    # Sync visits
    for vp in payload.visits:
        try:
            await create_visit(db, van, vp)
            result.visits_created += 1
        except ValueError:
            result.duplicates_skipped += 1
        except Exception as e:
            result.errors.append(f"visit: {e}")

    # Sync transactions
    txn_id_map: dict[str, uuid.UUID] = {}
    for tp in payload.transactions:
        tp.device_id = payload.device_id or tp.device_id
        try:
            txn = await create_transaction(db, van, tp, user_id)
            if tp.offline_id:
                txn_id_map[tp.offline_id] = txn.id
            result.txns_created += 1
        except ValueError:
            result.duplicates_skipped += 1
        except Exception as e:
            result.errors.append(f"txn: {e}")

    # Sync payments
    for pp in payload.payments:
        try:
            offline_txn_id = pp.get("offline_txn_id")
            server_txn_id = txn_id_map.get(offline_txn_id) if offline_txn_id else None
            if not server_txn_id and pp.get("txn_id"):
                server_txn_id = uuid.UUID(pp["txn_id"])
            if not server_txn_id:
                result.errors.append(f"payment: could not resolve txn for offline_txn_id={offline_txn_id}")
                continue
            txn = await get_transaction(db, server_txn_id)
            if not txn:
                result.errors.append(f"payment: txn {server_txn_id} not found")
                continue
            pc = PaymentCreate(
                method=pp["method"],
                amount=Decimal(str(pp["amount"])),
                reference_no=pp.get("reference_no"),
                collected_at=datetime.fromisoformat(pp["collected_at"]) if isinstance(pp["collected_at"], str) else pp["collected_at"],
                notes=pp.get("notes"),
            )
            await add_payment(db, txn, pc, user_id)
            result.payments_created += 1
        except Exception as e:
            result.errors.append(f"payment: {e}")

    return result


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_van_summary(db: AsyncSession, van_id: uuid.UUID, days: int = 30) -> Dict:
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            func.count().label("txn_count"),
            func.sum(VanSalesTxn.total_amount).label("total_sales"),
            func.sum(VanSalesTxn.paid_amount).label("total_collected"),
        ).where(
            VanSalesTxn.van_id == van_id,
            VanSalesTxn.txn_type == TxnType.SALE.value,
            VanSalesTxn.status != TxnStatus.CANCELLED.value,
            func.date(VanSalesTxn.txn_datetime) >= cutoff,
        )
    )
    row = result.first()
    return {
        "txn_count": row.txn_count or 0,
        "total_sales": float(row.total_sales or 0),
        "total_collected": float(row.total_collected or 0),
        "days": days,
    }


async def report_route_performance(db: AsyncSession, days: int = 30) -> List[Dict]:
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            VanSalesTxn.route_id,
            func.count().label("txn_count"),
            func.sum(VanSalesTxn.total_amount).label("total_sales"),
        ).where(
            VanSalesTxn.txn_type == TxnType.SALE.value,
            VanSalesTxn.status != TxnStatus.CANCELLED.value,
            func.date(VanSalesTxn.txn_datetime) >= cutoff,
        ).group_by(VanSalesTxn.route_id)
    )
    return [{"route_id": str(r.route_id), "txn_count": r.txn_count, "total_sales": float(r.total_sales or 0)} for r in result.all()]


async def report_driver_performance(db: AsyncSession, days: int = 30) -> List[Dict]:
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            VanSalesTxn.driver_id,
            func.count().label("txn_count"),
            func.sum(VanSalesTxn.total_amount).label("total_sales"),
        ).where(
            VanSalesTxn.txn_type == TxnType.SALE.value,
            VanSalesTxn.status != TxnStatus.CANCELLED.value,
            func.date(VanSalesTxn.txn_datetime) >= cutoff,
        ).group_by(VanSalesTxn.driver_id)
    )
    return [{"driver_id": str(r.driver_id), "txn_count": r.txn_count, "total_sales": float(r.total_sales or 0)} for r in result.all()]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[VSAIRecommendation]:
    recs: list[VSAIRecommendation] = []
    today = date.today()
    cutoff = today - timedelta(days=14)

    # Agent 1 — Route Optimizer: vans with >20% missed visits
    visit_q = await db.execute(
        select(
            VanVisit.van_id,
            func.count().label("total"),
            func.sum(
                (VanVisit.status == VisitStatus.MISSED.value).cast(Integer) if False
                else func.cast(VanVisit.status == VisitStatus.MISSED.value, Integer)
            ).label("missed"),
        ).where(VanVisit.route_date >= cutoff)
        .group_by(VanVisit.van_id)
    )
    for row in visit_q.all():
        if row.total and row.missed and (row.missed / row.total) > 0.2:
            rec = VSAIRecommendation(
                agent_type=VSAIAgentType.ROUTE_OPTIMIZER.value,
                severity="WARNING",
                title=f"Van has {row.missed}/{row.total} missed visits in 14 days",
                body=(
                    f"This van missed {row.missed} of {row.total} planned visits in the last 14 days "
                    f"({round(row.missed/row.total*100)}%). Review route sequencing, visit windows, "
                    "and driver capacity. Consider rebalancing the route."
                ),
                van_id=row.van_id,
                data={"missed": int(row.missed), "total": int(row.total)},
            )
            db.add(rec)
            recs.append(rec)

    # Agent 2 — Sales Assistant: vans with zero sales in 3 days
    active_vans_q = await db.execute(
        select(Van).where(Van.status == VanStatus.ACTIVE.value)
    )
    active_vans = active_vans_q.scalars().all()
    three_days_ago = today - timedelta(days=3)

    for van in active_vans:
        recent_q = await db.execute(
            select(func.count()).select_from(VanSalesTxn).where(
                VanSalesTxn.van_id == van.id,
                VanSalesTxn.txn_type == TxnType.SALE.value,
                func.date(VanSalesTxn.txn_datetime) >= three_days_ago,
            )
        )
        count = recent_q.scalar_one()
        if count == 0:
            rec = VSAIRecommendation(
                agent_type=VSAIAgentType.SALES_ASSISTANT.value,
                severity="WARNING",
                title=f"Van {van.van_code} has no sales in 3 days",
                body=(
                    f"Van {van.van_code} has had zero sales transactions in the last 3 days. "
                    "Check if the driver is executing the route. Review upcoming customer visits "
                    "and push priority reorder customers to the top of the route."
                ),
                van_id=van.id,
                data={"days_inactive": 3},
            )
            db.add(rec)
            recs.append(rec)

    # Agent 3 — Risk Monitor: large discounts (>15%)
    high_disc_q = await db.execute(
        select(VanSalesTxnLine.txn_id, func.avg(VanSalesTxnLine.discount_pct).label("avg_disc"))
        .join(VanSalesTxn, VanSalesTxn.id == VanSalesTxnLine.txn_id)
        .where(func.date(VanSalesTxn.txn_datetime) >= cutoff)
        .group_by(VanSalesTxnLine.txn_id)
        .having(func.avg(VanSalesTxnLine.discount_pct) > 15)
    )
    flagged = high_disc_q.all()
    if flagged:
        rec = VSAIRecommendation(
            agent_type=VSAIAgentType.RISK_MONITOR.value,
            severity="WARNING",
            title=f"{len(flagged)} transactions with avg discount >15% in 14 days",
            body=(
                f"{len(flagged)} van sales transactions in the last 14 days have average line discounts "
                "exceeding 15%. Review whether these discounts are authorized or indicate pricing abuse. "
                "Consider adding approval workflows for discounts above threshold."
            ),
            data={"flagged_count": len(flagged), "threshold_pct": 15},
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        await db.commit()
    return recs


async def list_ai_recs(
    db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None
) -> List[VSAIRecommendation]:
    q = select(VSAIRecommendation)
    if agent_type:
        q = q.where(VSAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(VSAIRecommendation.status == status)
    result = await db.execute(q.order_by(VSAIRecommendation.created_at.desc()).limit(100))
    return result.scalars().all()


async def ack_ai_rec(
    db: AsyncSession, rec_id: uuid.UUID, payload: VSAIRecAck
) -> Optional[VSAIRecommendation]:
    rec = await db.get(VSAIRecommendation, rec_id)
    if rec:
        rec.status = payload.status
        await db.commit()
        await db.refresh(rec)
    return rec
