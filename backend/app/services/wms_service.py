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

from app.core.access_control import can_modify_scope, can_view_scope, has_permission
from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.models.master import Product, Material, Warehouse
from app.models.wms import (
    WarehouseZone, StorageLocation, StockCount, StockCountLine,
    StockCountStatus, PutawayRule, PutawayRuleType, PutawayTask,
    PutawayExecution, PutawayTaskStatus,
    HandlingUnit, HandlingUnitItem, HandlingUnitStatus,
    PickWave, PickWaveStatus, PickingTaskStatus,
    PackingStatus, ReplenishmentStatus,
)
from app.models.production import MaterialConsumption, FinishedGoodsReceipt
from app.crud import wms as crud
from app.schemas.wms import (
    PutawayRequest, QuarantineRequest, ReleaseQuarantineRequest,
    FEFOSuggestion, NearExpiryRow, LowStockRow, StockAgingRow,
    LotTraceRow, LotTraceResult, RecordCountRequest,
    PutawayTaskCreate, PutawayExecuteRequest, SuggestLocationResult,
    HandlingUnitCreate, HandlingUnitUpdate, PickWaveCreate, PickWaveUpdate,
    WMSAccessHint,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def build_wms_access_hint(user, warehouse_id: uuid.UUID | str) -> WMSAccessHint:
    """Return per-warehouse UI hints without replacing backend authorization."""
    return WMSAccessHint(
        can_view=(
            has_permission(user, "inventory.view")
            or has_permission(user, "inventory.view_all")
            or has_permission(user, "warehouses.view_all")
            or can_view_scope(user, "inventory", "warehouse", warehouse_id)
            or can_view_scope(user, "warehouses", "warehouse", warehouse_id)
        ),
        can_edit=can_modify_scope(user, "inventory", "edit", "warehouse", warehouse_id),
        can_putaway=can_modify_scope(user, "inventory", "receive", "warehouse", warehouse_id),
        can_pick=can_modify_scope(user, "inventory", "dispatch", "warehouse", warehouse_id),
        can_pack=can_modify_scope(user, "inventory", "dispatch", "warehouse", warehouse_id),
        can_replenish=(
            can_modify_scope(user, "inventory", "transfer", "warehouse", warehouse_id)
            or can_modify_scope(user, "inventory", "edit", "warehouse", warehouse_id)
        ),
        can_quarantine=can_modify_scope(user, "inventory", "adjust", "warehouse", warehouse_id),
        can_release=can_modify_scope(user, "inventory", "adjust", "warehouse", warehouse_id),
        can_approve=can_modify_scope(user, "cycle_count", "perform", "warehouse", warehouse_id),
        can_export=can_modify_scope(user, "inventory", "export", "warehouse", warehouse_id),
    )


def ensure_wms_action_allowed(user, warehouse_id: uuid.UUID | str, action: str) -> WMSAccessHint:
    hint = build_wms_access_hint(user, warehouse_id)
    action_field = {
        "view": "can_view",
        "edit": "can_edit",
        "putaway": "can_putaway",
        "pick": "can_pick",
        "pack": "can_pack",
        "replenish": "can_replenish",
        "quarantine": "can_quarantine",
        "release": "can_release",
        "approve": "can_approve",
        "export": "can_export",
    }.get(action)
    if action_field is None or not getattr(hint, action_field):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "You can view this record but cannot modify it in this warehouse scope.",
            },
        )
    return hint


def can_change_wms_status(record_type: str, current_status, next_status=None) -> bool:
    current = str(getattr(current_status, "value", current_status)).upper()
    target = str(getattr(next_status, "value", next_status)).upper() if next_status is not None else None
    if record_type == "handling_unit":
        return current in {HandlingUnitStatus.OPEN.value, HandlingUnitStatus.ON_HOLD.value}
    if record_type == "pick_wave":
        if current in {PickWaveStatus.CANCELLED.value, PickWaveStatus.CLOSED.value}:
            return False
        if current == PickWaveStatus.PICKED.value and target not in {PickWaveStatus.CLOSED.value, PickWaveStatus.CANCELLED.value, None}:
            return False
        return True
    if record_type == "picking_task":
        return current not in {PickingTaskStatus.PACKED.value, PickingTaskStatus.CANCELLED.value}
    if record_type == "packing_record":
        return current != PackingStatus.CLOSED.value
    if record_type == "replenishment_task":
        return current not in {ReplenishmentStatus.COMPLETED.value, ReplenishmentStatus.CANCELLED.value}
    if record_type == "putaway_task":
        return current not in {PutawayTaskStatus.COMPLETED.value, PutawayTaskStatus.CANCELLED.value}
    return True


async def _require_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(404, "Warehouse not found")
    return warehouse


async def _require_location_in_warehouse(
    db: AsyncSession,
    location_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> StorageLocation:
    result = await db.execute(
        select(StorageLocation)
        .join(WarehouseZone, StorageLocation.zone_id == WarehouseZone.id)
        .where(StorageLocation.id == location_id, WarehouseZone.warehouse_id == warehouse_id)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(422, "Location does not belong to the selected warehouse")
    if location.is_blocked:
        raise HTTPException(422, "Location is blocked")
    return location


def _validate_hu_item(item) -> None:
    if item.quantity <= 0:
        raise HTTPException(422, "Handling unit item quantity must be greater than zero")
    has_product = item.product_id is not None
    has_material = item.material_id is not None
    if item.stock_type == "PRODUCT" and not (has_product and not has_material):
        raise HTTPException(422, "PRODUCT handling unit items require product_id only")
    if item.stock_type == "MATERIAL" and not (has_material and not has_product):
        raise HTTPException(422, "MATERIAL handling unit items require material_id only")


async def create_handling_unit(
    db: AsyncSession,
    data: HandlingUnitCreate,
    user_id: uuid.UUID,
) -> HandlingUnit:
    await _require_warehouse(db, data.warehouse_id)
    if data.location_id:
        await _require_location_in_warehouse(db, data.location_id, data.warehouse_id)

    if data.parent_hu_id:
        parent_result = await db.execute(
            select(HandlingUnit).where(
                HandlingUnit.id == data.parent_hu_id,
                HandlingUnit.warehouse_id == data.warehouse_id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(422, "Parent handling unit must belong to the same warehouse")

    payload = data.model_dump(exclude={"items"})
    handling_unit = HandlingUnit(**payload, created_by_id=user_id)
    db.add(handling_unit)
    await db.flush()

    for item_data in data.items:
        _validate_hu_item(item_data)
        db.add(HandlingUnitItem(handling_unit_id=handling_unit.id, **item_data.model_dump()))

    await db.flush()
    await db.refresh(handling_unit)
    return handling_unit


async def update_handling_unit(
    db: AsyncSession,
    handling_unit: HandlingUnit,
    data: HandlingUnitUpdate,
) -> HandlingUnit:
    if not can_change_wms_status("handling_unit", handling_unit.status, data.status):
        raise HTTPException(422, "Closed, shipped, consumed, or void handling units are locked")
    if data.location_id:
        await _require_location_in_warehouse(db, data.location_id, handling_unit.warehouse_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(handling_unit, field, value)
    await db.flush()
    await db.refresh(handling_unit)
    return handling_unit


async def create_pick_wave(
    db: AsyncSession,
    data: PickWaveCreate,
    user_id: uuid.UUID,
) -> PickWave:
    await _require_warehouse(db, data.warehouse_id)
    wave = PickWave(**data.model_dump())
    db.add(wave)
    await db.flush()
    await db.refresh(wave)
    return wave


async def update_pick_wave(
    db: AsyncSession,
    wave: PickWave,
    data: PickWaveUpdate,
    user_id: uuid.UUID,
) -> PickWave:
    if data.status and not can_change_wms_status("pick_wave", wave.status, data.status):
        raise HTTPException(422, "Pick wave status transition is locked")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(wave, field, value)
    if data.status == PickWaveStatus.RELEASED and not wave.released_at:
        wave.released_at = _now()
        wave.released_by_id = user_id
    if data.status == PickWaveStatus.CLOSED and not wave.closed_at:
        wave.closed_at = _now()
    await db.flush()
    await db.refresh(wave)
    return wave


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


# ── Putaway Rule Engine ───────────────────────────────────────────────────────

async def _available_locations_in_zone(
    db: AsyncSession,
    zone_id: uuid.UUID,
    weight_kg: Optional[Decimal],
    volume_m3: Optional[Decimal],
) -> List[StorageLocation]:
    q = select(StorageLocation).where(
        StorageLocation.zone_id == zone_id,
        StorageLocation.is_active == True,  # noqa: E712
        StorageLocation.is_blocked == False,  # noqa: E712
    )
    result = await db.execute(q)
    locs = list(result.scalars().all())

    valid = []
    for loc in locs:
        if weight_kg and loc.max_weight_kg and weight_kg > loc.max_weight_kg:
            continue
        if volume_m3 and loc.max_volume_m3 and volume_m3 > loc.max_volume_m3:
            continue
        valid.append(loc)
    return valid


async def suggest_putaway_location(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    product_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
    weight_kg: Optional[Decimal] = None,
    volume_m3: Optional[Decimal] = None,
) -> SuggestLocationResult:
    """Evaluate putaway rules by priority and return best location suggestion."""
    rules_q = await db.execute(
        select(PutawayRule)
        .where(
            PutawayRule.warehouse_id == warehouse_id,
            PutawayRule.is_active == True,  # noqa: E712
        )
        .order_by(PutawayRule.priority.asc())
    )
    rules = list(rules_q.scalars().all())

    for rule in rules:
        if rule.rule_type == PutawayRuleType.FIXED:
            if product_id and rule.product_id and rule.product_id != product_id:
                continue
            if rule.location_id:
                loc_r = await db.execute(
                    select(StorageLocation)
                    .where(
                        StorageLocation.id == rule.location_id,
                        StorageLocation.is_active == True,  # noqa: E712
                        StorageLocation.is_blocked == False,  # noqa: E712
                    )
                )
                loc = loc_r.scalar_one_or_none()
                if loc:
                    await db.execute(
                        select(WarehouseZone).where(WarehouseZone.id == loc.zone_id)
                    )
                    zone_r = await db.execute(select(WarehouseZone).where(WarehouseZone.id == loc.zone_id))
                    zone = zone_r.scalar_one_or_none()
                    return SuggestLocationResult(
                        location_id=loc.id,
                        location_code=loc.code,
                        zone_name=zone.name if zone else None,
                        rule_applied=rule.rule_code,
                        confidence="FIXED",
                    )

        elif rule.rule_type in (PutawayRuleType.ZONE, PutawayRuleType.CATEGORY):
            if rule.rule_type == PutawayRuleType.CATEGORY:
                if not category or rule.category != category:
                    continue
            if rule.zone_id:
                candidates = await _available_locations_in_zone(db, rule.zone_id, weight_kg, volume_m3)
                if candidates:
                    loc = candidates[0]
                    zone_r = await db.execute(select(WarehouseZone).where(WarehouseZone.id == loc.zone_id))
                    zone = zone_r.scalar_one_or_none()
                    return SuggestLocationResult(
                        location_id=loc.id,
                        location_code=loc.code,
                        zone_name=zone.name if zone else None,
                        rule_applied=rule.rule_code,
                        confidence="ZONE",
                    )

        elif rule.rule_type in (PutawayRuleType.RANDOM, PutawayRuleType.NEAREST):
            zone_filter = PutawayRule.zone_id == rule.zone_id if rule.zone_id else None
            target_zone_id = rule.zone_id
            if target_zone_id:
                candidates = await _available_locations_in_zone(db, target_zone_id, weight_kg, volume_m3)
            else:
                all_zones_q = await db.execute(
                    select(WarehouseZone.id).where(WarehouseZone.warehouse_id == warehouse_id)
                )
                zone_ids = [r for (r,) in all_zones_q.all()]
                candidates = []
                for zid in zone_ids:
                    candidates += await _available_locations_in_zone(db, zid, weight_kg, volume_m3)
            if candidates:
                import random
                if rule.rule_type == PutawayRuleType.RANDOM:
                    loc = random.choice(candidates)
                else:
                    loc = candidates[0]
                zone_r = await db.execute(select(WarehouseZone).where(WarehouseZone.id == loc.zone_id))
                zone = zone_r.scalar_one_or_none()
                return SuggestLocationResult(
                    location_id=loc.id,
                    location_code=loc.code,
                    zone_name=zone.name if zone else None,
                    rule_applied=rule.rule_code,
                    confidence=rule.rule_type.value,
                )

    # Fallback: any available location in warehouse
    all_zones_q = await db.execute(
        select(WarehouseZone.id).where(WarehouseZone.warehouse_id == warehouse_id)
    )
    zone_ids = [r for (r,) in all_zones_q.all()]
    for zid in zone_ids:
        candidates = await _available_locations_in_zone(db, zid, weight_kg, volume_m3)
        if candidates:
            loc = candidates[0]
            zone_r = await db.execute(select(WarehouseZone).where(WarehouseZone.id == loc.zone_id))
            zone = zone_r.scalar_one_or_none()
            return SuggestLocationResult(
                location_id=loc.id,
                location_code=loc.code,
                zone_name=zone.name if zone else None,
                rule_applied="FALLBACK",
                confidence="LOW",
            )

    return SuggestLocationResult(confidence="NONE")


async def create_putaway_task_from_receipt(
    db: AsyncSession,
    data: PutawayTaskCreate,
    user_id: uuid.UUID,
) -> PutawayTask:
    from app.crud import wms as crud

    suggestion = await suggest_putaway_location(
        db,
        warehouse_id=data.warehouse_id,
        product_id=data.product_id,
        material_id=data.material_id,
        weight_kg=data.weight_kg,
        volume_m3=data.volume_m3,
    )

    from datetime import date as d_date
    task_no = f"PUT-{_now().strftime('%Y%m%d%H%M%S')}"
    task = await crud.create_putaway_task(
        db, data, task_no, suggested_location_id=suggestion.location_id
    )
    await db.flush()
    await db.refresh(task)
    return task


async def execute_putaway_task(
    db: AsyncSession,
    task: PutawayTask,
    req: PutawayExecuteRequest,
    user_id: uuid.UUID,
) -> PutawayExecution:
    if task.status == PutawayTaskStatus.COMPLETED:
        raise HTTPException(422, "Task already completed")
    if task.status == PutawayTaskStatus.CANCELLED:
        raise HTTPException(422, "Task is cancelled")

    loc_r = await db.execute(
        select(StorageLocation).where(
            StorageLocation.id == req.actual_location_id,
            StorageLocation.is_blocked == False,  # noqa: E712
        )
    )
    loc = loc_r.scalar_one_or_none()
    if not loc:
        raise HTTPException(404, "Target location not found or blocked")

    is_variance = (
        task.suggested_location_id is not None
        and task.suggested_location_id != req.actual_location_id
    )

    if is_variance and not req.override_reason:
        raise HTTPException(422, "override_reason required when location differs from suggestion")

    execution = PutawayExecution(
        task_id=task.id,
        actual_location_id=req.actual_location_id,
        executed_by=user_id,
        executed_at=_now(),
        is_variance=is_variance,
        notes=req.notes,
    )
    db.add(execution)

    task.status = PutawayTaskStatus.COMPLETED
    if req.override_reason:
        task.override_reason = req.override_reason

    # Move stock to actual location
    stock_filters = [
        Stock.warehouse_id == task.warehouse_id,
        Stock.location_id.is_(None),
    ]
    if task.product_id:
        stock_filters += [Stock.product_id == task.product_id, Stock.stock_type == StockType.PRODUCT]
    elif task.material_id:
        stock_filters += [Stock.material_id == task.material_id, Stock.stock_type == StockType.MATERIAL]

    if task.lot_number:
        lot_r = await db.execute(select(Lot).where(Lot.lot_number == task.lot_number))
        lot = lot_r.scalar_one_or_none()
        if lot:
            stock_filters.append(Stock.lot_id == lot.id)

    stock_r = await db.execute(select(Stock).where(and_(*stock_filters)).with_for_update())
    stock = stock_r.scalar_one_or_none()
    if stock:
        stock.location_id = req.actual_location_id

    await db.flush()
    await db.refresh(execution)
    return execution


# ── AI: Space Optimizer ───────────────────────────────────────────────────────

async def ai_space_optimizer(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
) -> dict:
    """Analyze location utilization and suggest improvements."""
    # Count locations per zone and occupied (stock assigned)
    zones_q = await db.execute(
        select(WarehouseZone).where(WarehouseZone.warehouse_id == warehouse_id)
    )
    zones = list(zones_q.scalars().all())

    zone_stats = []
    total_locs = 0
    occupied_locs = 0

    for zone in zones:
        locs_q = await db.execute(
            select(StorageLocation).where(StorageLocation.zone_id == zone.id)
        )
        locs = list(locs_q.scalars().all())
        loc_ids = [l.id for l in locs]

        occupied = 0
        if loc_ids:
            occ_q = await db.execute(
                select(func.count(Stock.id.distinct())).where(
                    Stock.location_id.in_(loc_ids),
                    Stock.quantity_on_hand > 0,
                )
            )
            occupied = occ_q.scalar() or 0

        total_locs += len(locs)
        occupied_locs += occupied
        utilization_pct = round(occupied / len(locs) * 100, 1) if locs else 0
        zone_stats.append({
            "zone_code": zone.code,
            "zone_name": zone.name,
            "zone_type": zone.zone_type.value,
            "total_locations": len(locs),
            "occupied_locations": occupied,
            "utilization_pct": utilization_pct,
            "available_locations": len(locs) - occupied,
        })

    overall_pct = round(occupied_locs / total_locs * 100, 1) if total_locs else 0
    insights = []
    for z in zone_stats:
        if z["utilization_pct"] > 90:
            insights.append(f"Zone '{z['zone_name']}' near capacity ({z['utilization_pct']}%) — consider expansion or overflow zone.")
        elif z["utilization_pct"] < 20 and z["total_locations"] > 5:
            insights.append(f"Zone '{z['zone_name']}' underutilized ({z['utilization_pct']}%) — consolidate stock or repurpose space.")

    return {
        "warehouse_id": str(warehouse_id),
        "overall_utilization_pct": overall_pct,
        "total_locations": total_locs,
        "occupied_locations": occupied_locs,
        "available_locations": total_locs - occupied_locs,
        "zone_breakdown": zone_stats,
        "ai_insights": insights if insights else ["Warehouse space utilization is within normal range."],
        "generated_at": _now().isoformat(),
    }


async def ai_putaway_efficiency(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
) -> dict:
    """Detect override patterns and inefficient placements."""
    tasks_q = await db.execute(
        select(PutawayTask)
        .where(
            PutawayTask.warehouse_id == warehouse_id,
            PutawayTask.status == PutawayTaskStatus.COMPLETED,
        )
        .options(selectinload(PutawayTask.execution))
    )
    tasks = list(tasks_q.scalars().all())

    total = len(tasks)
    overrides = sum(1 for t in tasks if t.execution and t.execution.is_variance)
    override_pct = round(overrides / total * 100, 1) if total else 0

    pending_q = await db.execute(
        select(func.count(PutawayTask.id)).where(
            PutawayTask.warehouse_id == warehouse_id,
            PutawayTask.status == PutawayTaskStatus.PENDING,
        )
    )
    pending = pending_q.scalar() or 0

    insights = []
    if override_pct > 30:
        insights.append(f"High override rate ({override_pct}%) — putaway rules may not match actual workflow. Review rule priorities.")
    if pending > 20:
        insights.append(f"{pending} putaway tasks pending — potential congestion. Assign more warehouse staff.")
    if total == 0:
        insights.append("No completed putaway tasks yet. Generate tasks from goods receipts to begin tracking.")

    return {
        "warehouse_id": str(warehouse_id),
        "total_completed_tasks": total,
        "override_count": overrides,
        "override_rate_pct": override_pct,
        "pending_tasks": pending,
        "ai_insights": insights if insights else ["Putaway efficiency is within acceptable range."],
        "generated_at": _now().isoformat(),
    }

