"""
Subcontracting Service
──────────────────────
Manages the full subcontract flow:
  create order → issue materials → track production → receive goods → reconcile yield
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Stock, StockMovement, StockType, MovementType, Lot
from app.models.master import Material, Supplier, Warehouse
from app.models.subcontracting import (
    SCAIAgentType, SCAIRecommendation,
    SCIssueStatus, SCOrderStatus, SCReceiptStatus,
    SCYieldStatus, ScrapReasonCode,
    SubcontractMaterialIssue, SubcontractMaterialIssueLine,
    SubcontractOrder, SubcontractOrderLine,
    SubcontractReceipt, SubcontractReceiptLine,
    SubcontractYieldRecord, SCPerformanceRecord,
    SubcontractorLocation,
)
from app.schemas.subcontracting import (
    SCDashboard, SCIssueCreate, SCOrderCreate, SCReceiptCreate,
    SubcontractorLocationCreate, SubcontractorStockRow,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    if v is None: return Decimal("0")
    return Decimal(str(v))

def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal("0." + "0" * dp), rounding=ROUND_HALF_UP)

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)

def _today() -> date:
    return date.today()

def _order_no() -> str:
    d = _today().strftime("%Y%m%d")
    return f"SCO-{d}-{str(uuid.uuid4())[:6].upper()}"

def _issue_no() -> str:
    d = _today().strftime("%Y%m%d")
    return f"SCI-{d}-{str(uuid.uuid4())[:6].upper()}"

def _receipt_no() -> str:
    d = _today().strftime("%Y%m%d")
    return f"SCR-{d}-{str(uuid.uuid4())[:6].upper()}"


# ── Subcontractor Location ────────────────────────────────────────────────────

async def create_location(db: AsyncSession, payload: SubcontractorLocationCreate) -> SubcontractorLocation:
    loc = SubcontractorLocation(
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        notes=payload.notes,
    )
    db.add(loc)
    await db.flush()
    return loc


async def get_location_for_supplier(db: AsyncSession, supplier_id: UUID) -> Optional[SubcontractorLocation]:
    q = select(SubcontractorLocation).where(SubcontractorLocation.supplier_id == supplier_id)
    return (await db.execute(q)).scalar_one_or_none()


async def list_locations(db: AsyncSession) -> List[SubcontractorLocation]:
    q = (
        select(SubcontractorLocation)
        .options(
            selectinload(SubcontractorLocation.supplier),
            selectinload(SubcontractorLocation.warehouse),
        )
    )
    return list((await db.execute(q)).scalars().all())


# ── Order CRUD ────────────────────────────────────────────────────────────────

async def create_order(db: AsyncSession, payload: SCOrderCreate, user_id: Optional[UUID]) -> SubcontractOrder:
    # Resolve subcontractor location
    loc = await get_location_for_supplier(db, payload.supplier_id)

    order = SubcontractOrder(
        order_no=_order_no(),
        supplier_id=payload.supplier_id,
        order_date=payload.order_date,
        expected_completion_date=payload.expected_completion_date,
        status=SCOrderStatus.DRAFT,
        warehouse_id=payload.warehouse_id,
        linked_po_id=payload.linked_po_id,
        subcontractor_location_id=loc.id if loc else None,
        currency=payload.currency,
        remarks=payload.remarks,
        created_by_id=user_id,
    )
    db.add(order)
    await db.flush()

    for l in payload.lines:
        line = SubcontractOrderLine(
            order_id=order.id,
            line_no=l.line_no,
            product_id=l.product_id,
            material_id=l.material_id,
            description=l.description,
            quantity_ordered=l.quantity_ordered,
            uom=l.uom,
            bom_id=l.bom_id,
            service_unit_cost=l.service_unit_cost,
            estimated_yield_pct=l.estimated_yield_pct,
            notes=l.notes,
        )
        db.add(line)

    await db.flush()
    return order


async def approve_order(db: AsyncSession, order_id: UUID, user_id: Optional[UUID]) -> SubcontractOrder:
    order = await db.get(SubcontractOrder, order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != SCOrderStatus.DRAFT:
        raise ValueError(f"Only DRAFT orders can be approved (current: {order.status})")
    order.status = SCOrderStatus.APPROVED
    order.approved_by_id = user_id
    order.approved_at = _now()
    await db.flush()
    return order


async def list_orders(
    db: AsyncSession,
    status: Optional[SCOrderStatus] = None,
    supplier_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[SubcontractOrder]:
    q = (
        select(SubcontractOrder)
        .options(
            selectinload(SubcontractOrder.supplier),
            selectinload(SubcontractOrder.warehouse),
            selectinload(SubcontractOrder.lines).selectinload(SubcontractOrderLine.product),
            selectinload(SubcontractOrder.lines).selectinload(SubcontractOrderLine.material),
        )
        .order_by(SubcontractOrder.created_at.desc())
    )
    if status:
        q = q.where(SubcontractOrder.status == status)
    if supplier_id:
        q = q.where(SubcontractOrder.supplier_id == supplier_id)
    q = q.offset(skip).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def get_order(db: AsyncSession, order_id: UUID) -> Optional[SubcontractOrder]:
    q = (
        select(SubcontractOrder)
        .options(
            selectinload(SubcontractOrder.supplier),
            selectinload(SubcontractOrder.warehouse),
            selectinload(SubcontractOrder.lines).selectinload(SubcontractOrderLine.product),
            selectinload(SubcontractOrder.lines).selectinload(SubcontractOrderLine.material),
            selectinload(SubcontractOrder.material_issues).selectinload(
                SubcontractMaterialIssue.lines).selectinload(SubcontractMaterialIssueLine.material),
            selectinload(SubcontractOrder.receipts).selectinload(
                SubcontractReceipt.lines),
            selectinload(SubcontractOrder.yield_records),
        )
        .where(SubcontractOrder.id == order_id)
    )
    return (await db.execute(q)).scalar_one_or_none()


# ── Material Issue ────────────────────────────────────────────────────────────

async def issue_materials(
    db: AsyncSession,
    payload: SCIssueCreate,
    user_id: Optional[UUID],
) -> SubcontractMaterialIssue:
    order = await db.get(SubcontractOrder, payload.order_id)
    if not order:
        raise ValueError(f"Order {payload.order_id} not found")
    if order.status not in (SCOrderStatus.APPROVED, SCOrderStatus.ISSUED,
                             SCOrderStatus.IN_PROGRESS, SCOrderStatus.PARTIALLY_RECEIVED):
        raise ValueError(f"Cannot issue materials for order in status {order.status}")

    # Resolve target subcontractor warehouse
    loc = await get_location_for_supplier(db, order.supplier_id)
    dest_wh_id = loc.warehouse_id if loc else None

    issue = SubcontractMaterialIssue(
        issue_no=_issue_no(),
        order_id=payload.order_id,
        issue_date=payload.issue_date,
        status=SCIssueStatus.ISSUED,
        issued_by_id=user_id,
        notes=payload.notes,
    )
    db.add(issue)
    await db.flush()

    for l in payload.lines:
        # Create stock movement: source warehouse → subcontractor location
        mv = None
        if order.warehouse_id and dest_wh_id:
            mv = StockMovement(
                reference_number=issue.issue_no,
                movement_type=MovementType.TRANSFER,
                stock_type=StockType.MATERIAL,
                movement_date=payload.issue_date,
                material_id=l.material_id,
                lot_id=l.lot_id,
                source_warehouse_id=order.warehouse_id,
                destination_warehouse_id=dest_wh_id,
                quantity=l.quantity_issued,
                unit_cost=l.unit_cost,
                total_cost=_R(_D(l.quantity_issued) * _D(l.unit_cost), 4) if l.unit_cost else None,
                notes=f"SC issue: {issue.issue_no}",
                created_by_id=user_id,
            )
            db.add(mv)
            await db.flush()

            # Update source stock: deduct
            await _adjust_stock(db, order.warehouse_id, l.material_id, l.lot_id,
                                  -_D(l.quantity_issued))
            # Update dest stock: add
            if dest_wh_id:
                await _adjust_stock(db, dest_wh_id, l.material_id, l.lot_id,
                                     _D(l.quantity_issued))

        line = SubcontractMaterialIssueLine(
            issue_id=issue.id,
            line_no=l.line_no,
            material_id=l.material_id,
            lot_id=l.lot_id,
            quantity_issued=l.quantity_issued,
            uom=l.uom,
            unit_cost=l.unit_cost,
            stock_movement_id=mv.id if mv else None,
            notes=l.notes,
        )
        db.add(line)

    # Advance order status
    if order.status == SCOrderStatus.APPROVED:
        order.status = SCOrderStatus.ISSUED

    await db.flush()
    return issue


async def _adjust_stock(
    db: AsyncSession,
    warehouse_id: UUID,
    material_id: UUID,
    lot_id: Optional[UUID],
    delta: Decimal,
) -> None:
    """Upsert stock record for material+warehouse, adjusting by delta."""
    q = select(Stock).where(
        Stock.warehouse_id == warehouse_id,
        Stock.material_id == material_id,
        Stock.stock_type == StockType.MATERIAL,
        Stock.lot_id == lot_id,
    )
    stock = (await db.execute(q)).scalar_one_or_none()

    if stock:
        stock.quantity_on_hand    = _R(_D(stock.quantity_on_hand) + delta)
        stock.quantity_available  = _R(max(_D(stock.quantity_available) + delta, Decimal("0")))
    else:
        if delta > 0:
            stock = Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                lot_id=lot_id,
                quantity_on_hand=delta,
                quantity_reserved=Decimal("0"),
                quantity_available=delta,
            )
            db.add(stock)

    await db.flush()


# ── Receipt ───────────────────────────────────────────────────────────────────

async def receive_goods(
    db: AsyncSession,
    payload: SCReceiptCreate,
    user_id: Optional[UUID],
) -> SubcontractReceipt:
    order = await db.get(SubcontractOrder, payload.order_id)
    if not order:
        raise ValueError(f"Order {payload.order_id} not found")
    if order.status not in (SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS,
                             SCOrderStatus.PARTIALLY_RECEIVED):
        raise ValueError(f"Cannot receive for order in status {order.status}")

    receipt = SubcontractReceipt(
        receipt_no=_receipt_no(),
        order_id=payload.order_id,
        receipt_date=payload.receipt_date,
        status=SCReceiptStatus.DRAFT,
        received_by_id=user_id,
        qc_inspection_id=payload.qc_inspection_id,
        notes=payload.notes,
    )
    db.add(receipt)
    await db.flush()

    # Target warehouse for incoming FG
    dest_wh_id = order.warehouse_id

    for l in payload.lines:
        accepted = l.quantity_accepted if l.quantity_accepted is not None else (
            _D(l.quantity_received) - _D(l.quantity_rejected)
        )

        # Stock movement: subcontractor location → main warehouse (for accepted qty)
        mv = None
        loc = await get_location_for_supplier(db, order.supplier_id)
        sc_wh_id = loc.warehouse_id if loc else None

        if dest_wh_id and accepted > 0:
            mv = StockMovement(
                reference_number=receipt.receipt_no,
                movement_type=MovementType.RECEIPT,
                stock_type=StockType.MATERIAL if l.material_id else StockType.PRODUCT,
                movement_date=payload.receipt_date,
                product_id=l.product_id,
                material_id=l.material_id,
                source_warehouse_id=sc_wh_id,
                destination_warehouse_id=dest_wh_id,
                quantity=accepted,
                unit_cost=l.unit_service_cost,
                notes=f"SC receipt: {receipt.receipt_no}",
                created_by_id=user_id,
            )
            db.add(mv)
            await db.flush()

            # Add to factory stock
            item_id = l.product_id or l.material_id
            if l.material_id:
                await _adjust_stock(db, dest_wh_id, l.material_id, None, accepted)
            if sc_wh_id and l.material_id:
                await _adjust_stock(db, sc_wh_id, l.material_id, None, -accepted)

        rl = SubcontractReceiptLine(
            receipt_id=receipt.id,
            order_line_id=l.order_line_id,
            line_no=l.line_no,
            product_id=l.product_id,
            material_id=l.material_id,
            quantity_received=l.quantity_received,
            quantity_accepted=accepted,
            quantity_rejected=l.quantity_rejected,
            uom=l.uom,
            lot_number=l.lot_number,
            expiry_date=l.expiry_date,
            unit_service_cost=l.unit_service_cost,
            stock_movement_id=mv.id if mv else None,
            notes=l.notes,
        )
        db.add(rl)

        # Update order line received qty
        if l.order_line_id:
            ol = await db.get(SubcontractOrderLine, l.order_line_id)
            if ol:
                ol.quantity_received = _R(_D(ol.quantity_received) + accepted)

    # Advance order status
    order.status = SCOrderStatus.IN_PROGRESS
    receipt.status = SCReceiptStatus.POSTED
    await db.flush()

    # Recalculate yield
    await _recalculate_yield(db, order)
    await db.flush()

    return receipt


async def _recalculate_yield(db: AsyncSession, order: SubcontractOrder) -> None:
    """Recompute yield records for all order lines."""
    # Total materials issued per order
    issues_q = (
        select(
            SubcontractMaterialIssueLine.issue_id,
            func.sum(SubcontractMaterialIssueLine.quantity_issued).label("total_issued"),
            func.sum(SubcontractMaterialIssueLine.quantity_returned).label("total_returned"),
            func.sum(SubcontractMaterialIssueLine.quantity_scrapped).label("total_scrapped"),
        )
        .join(SubcontractMaterialIssue, SubcontractMaterialIssueLine.issue_id == SubcontractMaterialIssue.id)
        .where(SubcontractMaterialIssue.order_id == order.id)
        .group_by(SubcontractMaterialIssueLine.issue_id)
    )

    total_issued_overall = Decimal("0")
    total_scrapped_overall = Decimal("0")

    rows = (await db.execute(issues_q)).all()
    for row in rows:
        total_issued_overall   += _D(row.total_issued)
        total_scrapped_overall += _D(row.total_scrapped)

    for ol in order.lines if hasattr(order, "lines") and order.lines else []:
        existing = (await db.execute(
            select(SubcontractYieldRecord).where(
                SubcontractYieldRecord.order_id == order.id,
                SubcontractYieldRecord.order_line_id == ol.id,
            )
        )).scalar_one_or_none()

        actual_yield = (
            _R(_D(ol.quantity_received) / _D(ol.quantity_ordered) * Decimal("100"), 3)
            if _D(ol.quantity_ordered) > 0 else Decimal("0")
        )
        expected = _D(ol.estimated_yield_pct) if ol.estimated_yield_pct else Decimal("100")
        variance = _R(actual_yield - expected, 3)

        status = SCYieldStatus.NORMAL
        if actual_yield < expected * Decimal("0.90"):
            status = SCYieldStatus.LOW_YIELD
        elif total_scrapped_overall > total_issued_overall * Decimal("0.10"):
            status = SCYieldStatus.HIGH_SCRAP

        if existing:
            existing.total_material_issued  = total_issued_overall
            existing.quantity_received      = _D(ol.quantity_received)
            existing.actual_yield_pct       = actual_yield
            existing.expected_yield_pct     = expected
            existing.yield_variance_pct     = variance
            existing.yield_status           = status
            existing.total_scrapped         = total_scrapped_overall
            existing.is_abnormal            = status != SCYieldStatus.NORMAL
        else:
            yr = SubcontractYieldRecord(
                order_id=order.id,
                order_line_id=ol.id,
                total_material_issued=total_issued_overall,
                quantity_ordered=_D(ol.quantity_ordered),
                quantity_received=_D(ol.quantity_received),
                expected_yield_pct=expected,
                actual_yield_pct=actual_yield,
                yield_variance_pct=variance,
                yield_status=status,
                total_scrapped=total_scrapped_overall,
                is_abnormal=status != SCYieldStatus.NORMAL,
            )
            db.add(yr)

    await db.flush()


# ── Complete / Close order ────────────────────────────────────────────────────

async def complete_order(db: AsyncSession, order_id: UUID) -> SubcontractOrder:
    order = await db.get(SubcontractOrder, order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")

    order.status = SCOrderStatus.COMPLETED
    order.actual_completion_date = _today()

    # Compute service cost from receipt lines
    receipts_q = (
        select(SubcontractReceiptLine)
        .join(SubcontractReceipt, SubcontractReceiptLine.receipt_id == SubcontractReceipt.id)
        .where(SubcontractReceipt.order_id == order_id)
    )
    receipt_lines = list((await db.execute(receipts_q)).scalars().all())
    svc_cost = sum(
        _D(rl.unit_service_cost) * _D(rl.quantity_accepted)
        for rl in receipt_lines if rl.unit_service_cost
    )

    # Compute material cost from issue lines
    issues_q = (
        select(SubcontractMaterialIssueLine)
        .join(SubcontractMaterialIssue,
              SubcontractMaterialIssueLine.issue_id == SubcontractMaterialIssue.id)
        .where(SubcontractMaterialIssue.order_id == order_id)
    )
    issue_lines = list((await db.execute(issues_q)).scalars().all())
    mat_cost = sum(
        _D(il.unit_cost) * _D(il.quantity_consumed)
        for il in issue_lines if il.unit_cost
    )
    scrap_cost = sum(
        _D(il.unit_cost) * _D(il.quantity_scrapped)
        for il in issue_lines if il.unit_cost
    )

    order.total_service_cost    = _R(svc_cost, 4)
    order.total_material_cost   = _R(mat_cost, 4)
    order.total_wastage_cost    = _R(scrap_cost, 4)

    # Create/update performance record
    await _upsert_performance(db, order)
    await db.flush()
    return order


async def _upsert_performance(db: AsyncSession, order: SubcontractOrder) -> None:
    existing = (await db.execute(
        select(SCPerformanceRecord).where(SCPerformanceRecord.order_id == order.id)
    )).scalar_one_or_none()

    planned = order.expected_completion_date
    actual  = order.actual_completion_date or _today()
    delay   = (actual - planned).days if planned else None
    on_time = delay is not None and delay <= 0

    # Totals from receipts
    receipt_q = (
        select(
            func.sum(SubcontractReceiptLine.quantity_received).label("rcv"),
            func.sum(SubcontractReceiptLine.quantity_accepted).label("acc"),
            func.sum(SubcontractReceiptLine.quantity_rejected).label("rej"),
        )
        .join(SubcontractReceipt, SubcontractReceiptLine.receipt_id == SubcontractReceipt.id)
        .where(SubcontractReceipt.order_id == order.id)
    )
    r = (await db.execute(receipt_q)).one()
    total_rcv = _D(r.rcv); total_rej = _D(r.rej)
    rej_rate  = _R(total_rej / total_rcv * Decimal("100"), 3) if total_rcv > 0 else Decimal("0")

    yield_q   = select(func.avg(SubcontractYieldRecord.actual_yield_pct)).where(
        SubcontractYieldRecord.order_id == order.id)
    avg_yield = _D((await db.execute(yield_q)).scalar())

    total_budget = (
        sum(_D(l.quantity_ordered) * _D(l.service_unit_cost)
            for l in order.lines if hasattr(order, "lines") and l.service_unit_cost)
        if hasattr(order, "lines") else Decimal("0")
    )
    actual_cost = (_D(order.total_service_cost) + _D(order.total_material_cost)
                   + _D(order.total_wastage_cost))
    cost_var = (
        _R((actual_cost - total_budget) / total_budget * Decimal("100"), 3)
        if total_budget > 0 else Decimal("0")
    )

    # Simple performance score
    score = Decimal("100")
    if delay and delay > 0:
        score -= min(Decimal(str(delay)) * Decimal("2"), Decimal("30"))
    score -= rej_rate
    if avg_yield and avg_yield < Decimal("95"):
        score -= (Decimal("95") - avg_yield) / Decimal("2")
    score = max(score, Decimal("0"))

    vals = dict(
        supplier_id=order.supplier_id,
        planned_completion=planned,
        actual_completion=actual,
        delay_days=delay,
        on_time=on_time,
        total_qty_ordered=_D(sum(l.quantity_ordered for l in order.lines))
        if hasattr(order, "lines") else Decimal("0"),
        total_qty_received=_D(r.acc) if r.acc else Decimal("0"),
        total_qty_rejected=total_rej,
        rejection_rate_pct=rej_rate,
        avg_yield_pct=avg_yield,
        budgeted_cost=total_budget,
        actual_cost=actual_cost,
        cost_variance_pct=cost_var,
        performance_score=_R(score, 2),
    )

    if existing:
        for k, v in vals.items():
            setattr(existing, k, v)
    else:
        db.add(SCPerformanceRecord(order_id=order.id, **vals))

    await db.flush()


# ── Subcontractor stock ───────────────────────────────────────────────────────

async def get_subcontractor_stock(
    db: AsyncSession,
    supplier_id: Optional[UUID] = None,
) -> List[SubcontractorStockRow]:
    """Aggregate materials currently at subcontractor locations."""
    q = (
        select(
            SubcontractOrder.supplier_id,
            Supplier.name.label("supplier_name"),
            SubcontractMaterialIssueLine.material_id,
            Material.code.label("material_code"),
            Material.name.label("material_name"),
            Material.uom.label("uom"),
            func.sum(SubcontractMaterialIssueLine.quantity_issued).label("qty_issued"),
            func.sum(SubcontractMaterialIssueLine.quantity_returned).label("qty_returned"),
            func.sum(SubcontractMaterialIssueLine.quantity_consumed).label("qty_consumed"),
            func.sum(SubcontractMaterialIssueLine.quantity_scrapped).label("qty_scrapped"),
            func.avg(SubcontractMaterialIssueLine.unit_cost).label("unit_cost"),
        )
        .join(SubcontractMaterialIssue,
              SubcontractMaterialIssueLine.issue_id == SubcontractMaterialIssue.id)
        .join(SubcontractOrder, SubcontractMaterialIssue.order_id == SubcontractOrder.id)
        .join(Supplier, SubcontractOrder.supplier_id == Supplier.id)
        .join(Material, SubcontractMaterialIssueLine.material_id == Material.id)
        .where(SubcontractOrder.status.in_([
            SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS, SCOrderStatus.PARTIALLY_RECEIVED
        ]))
        .group_by(
            SubcontractOrder.supplier_id, Supplier.name,
            SubcontractMaterialIssueLine.material_id,
            Material.code, Material.name, Material.uom,
        )
    )
    if supplier_id:
        q = q.where(SubcontractOrder.supplier_id == supplier_id)

    rows = (await db.execute(q)).all()
    result = []
    for r in rows:
        issued   = _D(r.qty_issued)
        returned = _D(r.qty_returned)
        consumed = _D(r.qty_consumed)
        scrapped = _D(r.qty_scrapped)
        balance  = _R(issued - returned - consumed - scrapped)
        uc       = _D(r.unit_cost) if r.unit_cost else None
        result.append(SubcontractorStockRow(
            supplier_id=r.supplier_id,
            supplier_name=r.supplier_name,
            material_id=r.material_id,
            material_code=r.material_code,
            material_name=r.material_name,
            uom=r.uom.value if hasattr(r.uom, "value") else str(r.uom) if r.uom else None,
            qty_issued=_R(issued),
            qty_returned=_R(returned),
            qty_consumed=_R(consumed),
            qty_scrapped=_R(scrapped),
            qty_balance=balance,
            unit_cost=uc,
            total_value=_R(balance * uc, 4) if uc else None,
        ))
    return result


# ── Performance ───────────────────────────────────────────────────────────────

async def list_performance(
    db: AsyncSession,
    supplier_id: Optional[UUID] = None,
) -> List[SCPerformanceRecord]:
    q = (
        select(SCPerformanceRecord)
        .options(
            selectinload(SCPerformanceRecord.supplier),
            selectinload(SCPerformanceRecord.order),
        )
        .order_by(SCPerformanceRecord.created_at.desc())
    )
    if supplier_id:
        q = q.where(SCPerformanceRecord.supplier_id == supplier_id)
    return list((await db.execute(q)).scalars().all())


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> SCDashboard:
    total   = (await db.execute(select(func.count()).select_from(SubcontractOrder))).scalar() or 0
    draft   = (await db.execute(select(func.count()).select_from(SubcontractOrder).where(
        SubcontractOrder.status == SCOrderStatus.DRAFT))).scalar() or 0
    active  = (await db.execute(select(func.count()).select_from(SubcontractOrder).where(
        SubcontractOrder.status.in_([SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS,
                                      SCOrderStatus.PARTIALLY_RECEIVED])))).scalar() or 0
    done    = (await db.execute(select(func.count()).select_from(SubcontractOrder).where(
        SubcontractOrder.status.in_([SCOrderStatus.COMPLETED, SCOrderStatus.CLOSED])))).scalar() or 0
    today   = _today()
    overdue = (await db.execute(select(func.count()).select_from(SubcontractOrder).where(
        SubcontractOrder.status.in_([SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS]),
        SubcontractOrder.expected_completion_date < today))).scalar() or 0

    mat_val_q = select(func.sum(
        SubcontractMaterialIssueLine.quantity_issued * SubcontractMaterialIssueLine.unit_cost
    )).select_from(SubcontractMaterialIssueLine)
    mat_val = _D((await db.execute(mat_val_q)).scalar())

    avg_yield_q = select(func.avg(SubcontractYieldRecord.actual_yield_pct)).select_from(
        SubcontractYieldRecord)
    avg_yield = (await db.execute(avg_yield_q)).scalar()

    scrap_q = select(func.sum(SubcontractYieldRecord.scrap_cost)).select_from(SubcontractYieldRecord)
    scrap_cost = _D((await db.execute(scrap_q)).scalar())

    ai_cnt = (await db.execute(select(func.count()).select_from(SCAIRecommendation))).scalar() or 0
    sup_cnt = (await db.execute(select(func.count()).select_from(Supplier).where(
        Supplier.is_active == True))).scalar() or 0
    loc_cnt = (await db.execute(select(func.count()).select_from(SubcontractorLocation).where(
        SubcontractorLocation.is_active == True))).scalar() or 0

    return SCDashboard(
        total_orders=total,
        draft_orders=draft,
        active_orders=active,
        completed_orders=done,
        overdue_orders=overdue,
        total_material_issued_value=_R(mat_val, 2),
        avg_yield_pct=_D(avg_yield) if avg_yield else None,
        total_scrap_cost=_R(scrap_cost, 2),
        ai_recs_count=ai_cnt,
        supplier_count=sup_cnt,
        locations_count=loc_cnt,
    )


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession, order_id: Optional[UUID] = None) -> Dict[str, int]:
    counts = {
        "performance_analyzer": await _run_performance_analyzer(db, order_id),
        "cost_optimizer":       await _run_cost_optimizer(db, order_id),
        "risk_detector":        await _run_risk_detector(db, order_id),
    }
    await db.flush()
    return counts


async def _orders_scope(db: AsyncSession, order_id: Optional[UUID]) -> List[SubcontractOrder]:
    q = (
        select(SubcontractOrder)
        .options(
            selectinload(SubcontractOrder.lines),
            selectinload(SubcontractOrder.supplier),
            selectinload(SubcontractOrder.yield_records),
        )
    )
    if order_id:
        q = q.where(SubcontractOrder.id == order_id)
    else:
        q = q.where(SubcontractOrder.status.in_([
            SCOrderStatus.IN_PROGRESS, SCOrderStatus.COMPLETED,
            SCOrderStatus.PARTIALLY_RECEIVED,
        ]))
    return list((await db.execute(q)).scalars().all())


async def _run_performance_analyzer(db: AsyncSession, order_id: Optional[UUID]) -> int:
    orders = await _orders_scope(db, order_id)
    count = 0
    for o in orders:
        for yr in (o.yield_records if hasattr(o, "yield_records") else []):
            if yr.yield_status in (SCYieldStatus.LOW_YIELD, SCYieldStatus.HIGH_SCRAP,
                                    SCYieldStatus.ABNORMAL):
                rec = SCAIRecommendation(
                    order_id=o.id,
                    supplier_id=o.supplier_id,
                    agent_type=SCAIAgentType.PERFORMANCE_ANALYZER,
                    title=f"Low yield detected: {o.order_no}",
                    recommendation=(
                        f"Order {o.order_no} with {o.supplier.name if o.supplier else 'supplier'} "
                        f"shows {yr.yield_status.value}. "
                        f"Actual yield: {yr.actual_yield_pct}% vs expected {yr.expected_yield_pct}%. "
                        f"Scrap: {yr.total_scrapped} units. "
                        f"Investigate process parameters and material quality at subcontractor site."
                    ),
                    rationale="Yield variance exceeds 10% threshold.",
                    risk_level="HIGH" if yr.yield_status == SCYieldStatus.ABNORMAL else "MEDIUM",
                    priority=2 if yr.is_abnormal else 4,
                )
                db.add(rec)
                count += 1

        # Overdue check
        if (o.expected_completion_date and
                o.status in (SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS) and
                o.expected_completion_date < _today()):
            delay = (_today() - o.expected_completion_date).days
            rec = SCAIRecommendation(
                order_id=o.id,
                supplier_id=o.supplier_id,
                agent_type=SCAIAgentType.PERFORMANCE_ANALYZER,
                title=f"Overdue order: {o.order_no} ({delay} days late)",
                recommendation=(
                    f"Subcontracting order {o.order_no} is {delay} days overdue. "
                    f"Contact {o.supplier.name if o.supplier else 'supplier'} immediately. "
                    f"Consider splitting remaining quantity to an alternative subcontractor."
                ),
                rationale="Late delivery impacts production schedules and sales commitments.",
                risk_level="CRITICAL" if delay > 7 else "HIGH",
                priority=1 if delay > 7 else 2,
            )
            db.add(rec)
            count += 1

    return count


async def _run_cost_optimizer(db: AsyncSession, order_id: Optional[UUID]) -> int:
    orders = await _orders_scope(db, order_id)
    count = 0
    for o in orders:
        if not o.total_wastage_cost:
            continue
        wastage = _D(o.total_wastage_cost)
        if wastage > Decimal("10000"):
            rec = SCAIRecommendation(
                order_id=o.id,
                supplier_id=o.supplier_id,
                agent_type=SCAIAgentType.COST_OPTIMIZER,
                title=f"High wastage cost: {o.order_no} (KES {wastage:,.0f})",
                recommendation=(
                    f"Order {o.order_no} has KES {wastage:,.0f} in wastage costs. "
                    f"Review subcontractor process controls. "
                    f"Consider requesting scrap reduction SLA in next contract. "
                    f"Evaluate alternative subcontractors with lower scrap rates."
                ),
                rationale="Wastage cost exceeds KES 10,000 threshold.",
                potential_saving=_R(wastage * Decimal("0.5"), 4),
                risk_level="MEDIUM",
                priority=4,
            )
            db.add(rec)
            count += 1

    return count


async def _run_risk_detector(db: AsyncSession, order_id: Optional[UUID]) -> int:
    count = 0
    # Check orders with no subcontractor location
    q = (
        select(SubcontractOrder)
        .options(selectinload(SubcontractOrder.supplier))
        .where(
            SubcontractOrder.subcontractor_location_id == None,
            SubcontractOrder.status.in_([SCOrderStatus.DRAFT, SCOrderStatus.APPROVED]),
        )
    )
    if order_id:
        q = q.where(SubcontractOrder.id == order_id)

    no_loc_orders = list((await db.execute(q)).scalars().all())
    for o in no_loc_orders:
        rec = SCAIRecommendation(
            order_id=o.id,
            supplier_id=o.supplier_id,
            agent_type=SCAIAgentType.RISK_DETECTOR,
            title=f"No virtual location for: {o.supplier.name if o.supplier else 'supplier'}",
            recommendation=(
                f"Order {o.order_no} has no subcontractor virtual location configured. "
                f"Materials cannot be tracked at the subcontractor site. "
                f"Create a SubcontractorLocation for this supplier before issuing materials."
            ),
            rationale="Without a virtual location, inventory tracking and traceability are broken.",
            risk_level="HIGH",
            priority=2,
        )
        db.add(rec)
        count += 1

    # Check orders nearing deadline
    threshold = _today() + timedelta(days=3)
    q2 = (
        select(SubcontractOrder)
        .options(selectinload(SubcontractOrder.supplier))
        .where(
            SubcontractOrder.status.in_([SCOrderStatus.ISSUED, SCOrderStatus.IN_PROGRESS]),
            SubcontractOrder.expected_completion_date.between(_today(), threshold),
        )
    )
    if order_id:
        q2 = q2.where(SubcontractOrder.id == order_id)

    near_orders = list((await db.execute(q2)).scalars().all())
    for o in near_orders:
        days = (o.expected_completion_date - _today()).days if o.expected_completion_date else 0
        rec = SCAIRecommendation(
            order_id=o.id,
            supplier_id=o.supplier_id,
            agent_type=SCAIAgentType.RISK_DETECTOR,
            title=f"Deadline in {days} day(s): {o.order_no}",
            recommendation=(
                f"Subcontracting order {o.order_no} is due in {days} day(s). "
                f"Confirm production status with {o.supplier.name if o.supplier else 'supplier'}. "
                f"Arrange transport and QC inspector for goods receipt."
            ),
            rationale="Less than 3 days to expected completion — proactive follow-up reduces delay risk.",
            risk_level="HIGH" if days <= 1 else "MEDIUM",
            priority=2 if days <= 1 else 3,
        )
        db.add(rec)
        count += 1

    return count


async def list_ai_recs(
    db: AsyncSession,
    order_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
) -> List[SCAIRecommendation]:
    q = (
        select(SCAIRecommendation)
        .options(
            selectinload(SCAIRecommendation.supplier),
            selectinload(SCAIRecommendation.order),
        )
        .order_by(SCAIRecommendation.priority.asc())
    )
    if order_id:
        q = q.where(SCAIRecommendation.order_id == order_id)
    if supplier_id:
        q = q.where(SCAIRecommendation.supplier_id == supplier_id)
    return list((await db.execute(q)).scalars().all())


async def action_ai_rec(db: AsyncSession, rec_id: UUID, notes: Optional[str]) -> SCAIRecommendation:
    rec = await db.get(SCAIRecommendation, rec_id)
    if not rec:
        raise ValueError(f"AI rec {rec_id} not found")
    rec.is_actioned  = True
    rec.action_notes = notes
    await db.flush()
    return rec


# ── Yield report ──────────────────────────────────────────────────────────────

async def list_yield_records(
    db: AsyncSession,
    order_id: Optional[UUID] = None,
    abnormal_only: bool = False,
) -> List[SubcontractYieldRecord]:
    q = (
        select(SubcontractYieldRecord)
        .options(
            selectinload(SubcontractYieldRecord.order),
            selectinload(SubcontractYieldRecord.order_line),
        )
        .order_by(SubcontractYieldRecord.created_at.desc())
    )
    if order_id:
        q = q.where(SubcontractYieldRecord.order_id == order_id)
    if abnormal_only:
        q = q.where(SubcontractYieldRecord.is_abnormal == True)
    return list((await db.execute(q)).scalars().all())
