"""
WMS Service — warehouse zones, locations, stock counts, FEFO/FIFO, inventory reports.

Extends the existing inventory engine without modifying its core logic.
Quarantine sets is_blocked=True and zeroes quantity_available so the
existing issue/transfer guards naturally block blocked stock.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.models.master import Product, Material, Warehouse
from app.models.wms import (
    WarehouseZone, StorageLocation, StockCount, StockCountLine,
    StockCountStatus,
)
from app.models.production import MaterialConsumption, FinishedGoodsReceipt
from app.crud import wms as crud
from app.schemas.wms import (
    PutawayRequest, QuarantineRequest, ReleaseQuarantineRequest,
    FEFOSuggestion, NearExpiryRow, LowStockRow, StockAgingRow,
    LotTraceRow, LotTraceResult, RecordCountRequest,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Putaway ───────────────────────────────────────────────────────────────────

async def putaway(
    db: AsyncSession, req: PutawayRequest, user_id: uuid.UUID
) -> Stock:
    """Assign existing stock row to a storage location."""
    loc = await crud.get_location(db, req.location_id)
    if not loc:
        raise HTTPException(404, "Storage location not found")
    if loc.is_blocked:
        raise HTTPException(422, "Location is blocked")

    # Find the stock row to assign
    filters = [
        Stock.warehouse_id == req.warehouse_id,
        Stock.location_id.is_(None),
    ]
    if req.product_id:
        filters += [Stock.product_id == req.product_id, Stock.stock_type == StockType.PRODUCT]
    elif req.material_id:
        filters += [Stock.material_id == req.material_id, Stock.stock_type == StockType.MATERIAL]
    else:
        raise HTTPException(422, "product_id or material_id required")

    if req.lot_number:
        r = await db.execute(select(Lot).where(Lot.lot_number == req.lot_number))
        lot = r.scalar_one_or_none()
        if lot:
            filters.append(Stock.lot_id == lot.id)

    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(404, "No unassigned stock found for this item in the warehouse")

    stock.location_id = req.location_id
    await db.flush()
    await db.refresh(stock)
    return stock


# ── Quarantine / Release ──────────────────────────────────────────────────────

async def quarantine_stock(
    db: AsyncSession, req: QuarantineRequest, user_id: uuid.UUID
) -> List[Stock]:
    filters = [Stock.warehouse_id == req.warehouse_id, Stock.is_blocked == False]  # noqa: E712

    if req.product_id:
        filters += [Stock.product_id == req.product_id, Stock.stock_type == StockType.PRODUCT]
    elif req.material_id:
        filters += [Stock.material_id == req.material_id, Stock.stock_type == StockType.MATERIAL]

    if req.lot_number:
        r = await db.execute(select(Lot).where(Lot.lot_number == req.lot_number))
        lot = r.scalar_one_or_none()
        if lot:
            filters.append(Stock.lot_id == lot.id)

    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    rows = list(result.scalars().all())
    if not rows:
        raise HTTPException(404, "No available (unblocked) stock found matching criteria")

    for s in rows:
        s.is_blocked = True
        s.quantity_reserved = s.quantity_on_hand
        s.quantity_available = Decimal("0")

    # Write ADJUSTMENT movement as audit trail
    item_id = req.product_id or req.material_id
    stock_type = StockType.PRODUCT if req.product_id else StockType.MATERIAL
    mv = StockMovement(
        reference_number=f"QUAR-{_now().strftime('%Y%m%d%H%M%S')}",
        movement_type=MovementType.ADJUSTMENT,
        stock_type=stock_type,
        movement_date=_now().date(),
        product_id=req.product_id,
        material_id=req.material_id,
        source_warehouse_id=req.warehouse_id,
        quantity=Decimal("0"),
        notes=f"QUARANTINE: {req.reason}. {req.notes or ''}".strip(),
        created_by_id=user_id,
    )
    db.add(mv)
    await db.flush()
    return rows


async def release_quarantine(
    db: AsyncSession, req: ReleaseQuarantineRequest, user_id: uuid.UUID
) -> List[Stock]:
    filters = [Stock.warehouse_id == req.warehouse_id, Stock.is_blocked == True]  # noqa: E712

    if req.product_id:
        filters += [Stock.product_id == req.product_id, Stock.stock_type == StockType.PRODUCT]
    elif req.material_id:
        filters += [Stock.material_id == req.material_id, Stock.stock_type == StockType.MATERIAL]

    if req.lot_number:
        r = await db.execute(select(Lot).where(Lot.lot_number == req.lot_number))
        lot = r.scalar_one_or_none()
        if lot:
            filters.append(Stock.lot_id == lot.id)

    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    rows = list(result.scalars().all())
    if not rows:
        raise HTTPException(404, "No blocked stock found matching criteria")

    for s in rows:
        s.is_blocked = False
        s.quantity_reserved = Decimal("0")
        s.quantity_available = s.quantity_on_hand

    mv = StockMovement(
        reference_number=f"QREL-{_now().strftime('%Y%m%d%H%M%S')}",
        movement_type=MovementType.ADJUSTMENT,
        stock_type=StockType.PRODUCT if req.product_id else StockType.MATERIAL,
        movement_date=_now().date(),
        product_id=req.product_id,
        material_id=req.material_id,
        destination_warehouse_id=req.warehouse_id,
        quantity=Decimal("0"),
        notes=f"QUARANTINE RELEASE. {req.notes or ''}".strip(),
        created_by_id=user_id,
    )
    db.add(mv)
    await db.flush()
    return rows


# ── FEFO / FIFO Suggestion ────────────────────────────────────────────────────

async def get_fefo_suggestions(
    db: AsyncSession,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity_needed: Decimal,
) -> List[FEFOSuggestion]:
    """Return lot suggestions ordered by expiry date (FEFO), falling back to FIFO."""
    q = (
        select(Stock, Lot, StorageLocation)
        .outerjoin(Lot, Stock.lot_id == Lot.id)
        .outerjoin(StorageLocation, Stock.location_id == StorageLocation.id)
        .where(
            Stock.product_id == product_id,
            Stock.warehouse_id == warehouse_id,
            Stock.stock_type == StockType.PRODUCT,
            Stock.is_blocked == False,  # noqa: E712
            Stock.quantity_available > 0,
        )
        .order_by(
            Lot.expiry_date.asc().nulls_last(),
            Stock.created_at.asc(),
        )
    )
    result = await db.execute(q)
    rows = result.all()

    suggestions = []
    remaining = quantity_needed
    today = date.today()

    for stock, lot, loc in rows:
        if remaining <= 0:
            break
        avail = min(stock.quantity_available, remaining)
        days_to_expiry = None
        if lot and lot.expiry_date:
            days_to_expiry = (lot.expiry_date - today).days

        suggestions.append(FEFOSuggestion(
            lot_id=lot.id if lot else stock.id,
            lot_number=lot.lot_number if lot else "NO-LOT",
            expiry_date=lot.expiry_date if lot else None,
            manufacture_date=lot.manufacture_date if lot else None,
            available_quantity=stock.quantity_available,
            location_code=loc.code if loc else None,
            days_to_expiry=days_to_expiry,
        ))
        remaining -= avail

    return suggestions


# ── Stock Count Lifecycle ─────────────────────────────────────────────────────

async def generate_count_lines(db: AsyncSession, count: StockCount) -> int:
    """Snapshot current stock into count lines."""
    q = select(Stock).where(
        Stock.warehouse_id == count.warehouse_id,
        Stock.quantity_on_hand > 0,
    ).options(selectinload(Stock.lot))

    if count.zone_id:
        loc_ids = await db.execute(
            select(StorageLocation.id).where(StorageLocation.zone_id == count.zone_id)
        )
        loc_id_list = [r for (r,) in loc_ids]
        if loc_id_list:
            q = q.where(Stock.location_id.in_(loc_id_list))

    result = await db.execute(q)
    stocks = list(result.scalars().all())

    for s in stocks:
        # Determine unit from product/material
        unit = "KG"
        line = StockCountLine(
            count_id=count.id,
            product_id=s.product_id,
            material_id=s.material_id,
            lot_id=s.lot_id,
            location_id=s.location_id,
            system_quantity=s.quantity_on_hand,
            unit=unit,
        )
        db.add(line)

    await db.flush()
    return len(stocks)


async def start_count(db: AsyncSession, count: StockCount) -> StockCount:
    if count.status != StockCountStatus.DRAFT:
        raise HTTPException(422, "Only DRAFT counts can be started")
    count.status = StockCountStatus.IN_PROGRESS
    await generate_count_lines(db, count)
    await db.flush()
    await db.refresh(count)
    return count


async def record_count_line(
    db: AsyncSession, line: StockCountLine, req: RecordCountRequest
) -> StockCountLine:
    line.counted_quantity = req.counted_quantity
    line.variance = req.counted_quantity - line.system_quantity
    line.is_counted = True
    if req.notes:
        line.notes = req.notes
    await db.flush()
    await db.refresh(line)
    return line


async def submit_count(db: AsyncSession, count: StockCount) -> StockCount:
    if count.status != StockCountStatus.IN_PROGRESS:
        raise HTTPException(422, "Only IN_PROGRESS counts can be submitted")
    uncounted = sum(1 for l in count.lines if not l.is_counted)
    if uncounted > 0:
        raise HTTPException(422, f"{uncounted} lines not yet counted")
    count.status = StockCountStatus.PENDING_APPROVAL
    count.completed_date = _now()
    await db.flush()
    await db.refresh(count)
    return count


async def approve_count(
    db: AsyncSession, count: StockCount, approver_id: uuid.UUID
) -> StockCount:
    if count.status != StockCountStatus.PENDING_APPROVAL:
        raise HTTPException(422, "Count must be PENDING_APPROVAL to approve")

    # Apply ADJUSTMENT movements for lines with variance
    for line in count.lines:
        if line.variance is None or line.variance == 0:
            continue

        stock_type = StockType.PRODUCT if line.product_id else StockType.MATERIAL
        variance = line.variance

        mv = StockMovement(
            reference_number=f"SC-{count.count_no}",
            movement_type=MovementType.ADJUSTMENT,
            stock_type=stock_type,
            movement_date=_now().date(),
            product_id=line.product_id,
            material_id=line.material_id,
            lot_id=line.lot_id,
            destination_warehouse_id=count.warehouse_id if variance > 0 else None,
            source_warehouse_id=count.warehouse_id if variance < 0 else None,
            quantity=abs(variance),
            notes=f"Stock count adjustment {count.count_no}",
            created_by_id=approver_id,
        )
        db.add(mv)
        await db.flush()

        # Update stock directly
        filters = [Stock.warehouse_id == count.warehouse_id]
        if line.product_id:
            filters += [Stock.product_id == line.product_id, Stock.stock_type == StockType.PRODUCT]
        else:
            filters += [Stock.material_id == line.material_id, Stock.stock_type == StockType.MATERIAL]
        if line.lot_id:
            filters.append(Stock.lot_id == line.lot_id)

        r = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
        stock = r.scalar_one_or_none()
        if stock:
            stock.quantity_on_hand += variance
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved

    count.status = StockCountStatus.APPROVED
    count.approved_by = approver_id
    await db.flush()
    await db.refresh(count)
    return count


async def cancel_count(db: AsyncSession, count: StockCount) -> StockCount:
    if count.status == StockCountStatus.APPROVED:
        raise HTTPException(422, "Approved counts cannot be cancelled")
    count.status = StockCountStatus.CANCELLED
    await db.flush()
    await db.refresh(count)
    return count


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_near_expiry_report(
    db: AsyncSession,
    days_ahead: int = 30,
    warehouse_id: Optional[uuid.UUID] = None,
) -> List[NearExpiryRow]:
    today = date.today()
    threshold = today + timedelta(days=days_ahead)

    q = (
        select(Stock, Lot, Product, Warehouse)
        .join(Lot, Stock.lot_id == Lot.id)
        .outerjoin(Product, Stock.product_id == Product.id)
        .join(Warehouse, Stock.warehouse_id == Warehouse.id)
        .where(
            Lot.expiry_date.isnot(None),
            Lot.expiry_date <= threshold,
            Stock.quantity_available > 0,
        )
        .order_by(Lot.expiry_date.asc())
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)

    result = await db.execute(q)
    rows = result.all()
    out = []
    for stock, lot, product, warehouse in rows:
        days_to = (lot.expiry_date - today).days
        out.append(NearExpiryRow(
            lot_number=lot.lot_number,
            product_id=stock.product_id,
            product_name=product.name if product else None,
            product_sku=product.sku if product else None,
            expiry_date=lot.expiry_date,
            days_to_expiry=days_to,
            warehouse_name=warehouse.name,
            quantity_available=stock.quantity_available,
            is_expired=days_to < 0,
        ))
    return out


async def get_low_stock_report(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
) -> List[LowStockRow]:
    q = (
        select(Stock, Product, Warehouse)
        .join(Product, Stock.product_id == Product.id)
        .join(Warehouse, Stock.warehouse_id == Warehouse.id)
        .where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.quantity_available < Product.reorder_point,
        )
        .order_by(Stock.quantity_available.asc())
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)

    result = await db.execute(q)
    rows = result.all()
    return [
        LowStockRow(
            product_id=s.product_id,
            product_sku=p.sku,
            product_name=p.name,
            warehouse_name=w.name,
            quantity_available=s.quantity_available,
            reorder_point=p.reorder_point,
            shortage=p.reorder_point - s.quantity_available,
        )
        for s, p, w in rows
    ]


async def get_stock_aging_report(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
) -> List[StockAgingRow]:
    q = (
        select(Stock, Product, Lot, Warehouse)
        .outerjoin(Product, Stock.product_id == Product.id)
        .outerjoin(Lot, Stock.lot_id == Lot.id)
        .join(Warehouse, Stock.warehouse_id == Warehouse.id)
        .where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.quantity_on_hand > 0,
        )
        .order_by(Stock.created_at.asc())
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)

    result = await db.execute(q)
    rows = result.all()
    today = date.today()
    out = []
    for stock, product, lot, warehouse in rows:
        # Use stock row created_at as first-received proxy
        received = stock.created_at.date() if stock.created_at else None
        age_days = (today - received).days if received else None

        if age_days is None:
            bucket = "Unknown"
        elif age_days <= 30:
            bucket = "0–30 days"
        elif age_days <= 60:
            bucket = "31–60 days"
        elif age_days <= 90:
            bucket = "61–90 days"
        else:
            bucket = "90+ days"

        out.append(StockAgingRow(
            product_sku=product.sku if product else None,
            product_name=product.name if product else None,
            lot_number=lot.lot_number if lot else None,
            warehouse_name=warehouse.name,
            quantity_on_hand=stock.quantity_on_hand,
            first_received_date=str(received) if received else None,
            age_days=age_days,
            age_bucket=bucket,
            is_blocked=stock.is_blocked,
        ))
    return out


async def get_lot_trace(db: AsyncSession, lot_number: str) -> LotTraceResult:
    # Find lot
    r = await db.execute(
        select(Lot)
        .where(Lot.lot_number == lot_number)
        .options(selectinload(Lot.movements))
    )
    lot = r.scalar_one_or_none()
    if not lot:
        raise HTTPException(404, f"Lot '{lot_number}' not found")

    product = None
    if lot.product_id:
        pr = await db.execute(select(Product).where(Product.id == lot.product_id))
        product = pr.scalar_one_or_none()

    material = None
    if lot.material_id:
        mr = await db.execute(select(Material).where(Material.id == lot.material_id))
        material = mr.scalar_one_or_none()

    events: List[LotTraceRow] = []

    # Stock movements
    mv_result = await db.execute(
        select(StockMovement, Warehouse)
        .outerjoin(Warehouse, StockMovement.source_warehouse_id == Warehouse.id)
        .where(StockMovement.lot_id == lot.id)
        .order_by(StockMovement.movement_date.asc(), StockMovement.created_at.asc())
    )
    for mv, wh in mv_result.all():
        events.append(LotTraceRow(
            event_type="MOVEMENT",
            event_date=str(mv.movement_date),
            reference=mv.reference_number,
            description=f"{mv.movement_type.value} — {mv.notes or ''}".strip(" —"),
            quantity=mv.quantity,
            warehouse_name=wh.name if wh else None,
        ))

    # Material consumptions
    mc_result = await db.execute(
        select(MaterialConsumption)
        .where(MaterialConsumption.lot_id == lot.id)
        .options(selectinload(MaterialConsumption.production_order))
    )
    for mc in mc_result.scalars():
        events.append(LotTraceRow(
            event_type="CONSUMPTION",
            event_date=str(mc.created_at.date()) if mc.created_at else "",
            reference=mc.production_order.order_no if mc.production_order else "—",
            description=f"Material consumed in production",
            quantity=mc.actual_quantity,
            order_no=mc.production_order.order_no if mc.production_order else None,
        ))

    events.sort(key=lambda e: e.event_date)

    return LotTraceResult(
        lot_number=lot_number,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        material_name=material.name if material else None,
        expiry_date=lot.expiry_date,
        manufacture_date=lot.manufacture_date,
        events=events,
    )


async def get_movement_ledger(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    movement_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[dict]:
    q = (
        select(StockMovement)
        .options(
            selectinload(StockMovement.source_warehouse),
            selectinload(StockMovement.destination_warehouse),
            selectinload(StockMovement.created_by),
            selectinload(StockMovement.lot),
        )
        .order_by(StockMovement.movement_date.desc(), StockMovement.created_at.desc())
    )
    if warehouse_id:
        q = q.where(
            (StockMovement.source_warehouse_id == warehouse_id) |
            (StockMovement.destination_warehouse_id == warehouse_id)
        )
    if date_from:
        q = q.where(StockMovement.movement_date >= date_from)
    if date_to:
        q = q.where(StockMovement.movement_date <= date_to)
    if movement_type:
        q = q.where(StockMovement.movement_type == movement_type)

    result = await db.execute(q.offset(skip).limit(limit))
    movements = list(result.scalars().all())

    # Bulk product lookup
    product_ids = {m.product_id for m in movements if m.product_id}
    products: dict = {}
    if product_ids:
        pr = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for p in pr.scalars():
            products[p.id] = p

    out = []
    for m in movements:
        p = products.get(m.product_id) if m.product_id else None
        out.append({
            "id": str(m.id),
            "reference_number": m.reference_number,
            "movement_type": m.movement_type.value,
            "stock_type": m.stock_type.value,
            "movement_date": str(m.movement_date),
            "product_sku": p.sku if p else None,
            "product_name": p.name if p else None,
            "lot_number": m.lot.lot_number if m.lot else None,
            "source_warehouse": m.source_warehouse.name if m.source_warehouse else None,
            "destination_warehouse": m.destination_warehouse.name if m.destination_warehouse else None,
            "quantity": float(m.quantity),
            "unit_cost": float(m.unit_cost) if m.unit_cost else None,
            "total_cost": float(m.total_cost) if m.total_cost else None,
            "notes": m.notes,
            "created_by": m.created_by.username if m.created_by else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return out
