"""
Manufacturing Execution Service.

Orchestrates the full production lifecycle:
  release → start → [pause/resume] → complete / cancel

Material consumption issues raw materials from inventory.
Finished goods receipt receives product into inventory.
All inventory mutations reuse the existing stock movement ledger and
stock delta logic so that inventory remains consistent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production import (
    ProductionPlan, ProductionPlanLine, ProductionOrder,
    MaterialConsumption, FinishedGoodsReceipt, DowntimeLog,
    ProductionPlanStatus, ProductionOrderStatus, DowntimeReason,
)
from app.models.recipe import Recipe, RecipeItem
from app.models.inventory import Stock, StockMovement, MovementType, StockType, Lot
from app.models.master import Material, Warehouse
from app.schemas.production import (
    CompleteOrderRequest, DowntimeLogCreate, DowntimeLogClose,
    OEEMetrics, ProductionReportRow, DowntimeSummaryRow, ProductionSummary,
    MaterialConsumptionRead, FinishedGoodsReceiptRead, DowntimeLogRead,
)
from app.crud import production as crud


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def _require_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail=f"Warehouse {warehouse_id} not found")
    return wh


async def _get_material_stock(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    material_id: uuid.UUID,
    lot_id: Optional[uuid.UUID],
) -> Optional[Stock]:
    filters = [
        Stock.warehouse_id == warehouse_id,
        Stock.material_id == material_id,
        Stock.stock_type == StockType.MATERIAL,
    ]
    if lot_id:
        filters.append(Stock.lot_id == lot_id)
    else:
        filters.append(Stock.lot_id.is_(None))
    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    return result.scalar_one_or_none()


async def _issue_material(
    db: AsyncSession,
    order: ProductionOrder,
    material: Material,
    warehouse_id: uuid.UUID,
    quantity: Decimal,
    lot_id: Optional[uuid.UUID],
    reference: str,
    notes: Optional[str],
    user_id: uuid.UUID,
) -> StockMovement:
    stock = await _get_material_stock(db, warehouse_id, material.id, lot_id)
    available = stock.quantity_available if stock else Decimal("0")
    if available < quantity:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INSUFFICIENT_MATERIAL",
                "message": f"Cannot consume {quantity} {material.uom.value} of '{material.name}' "
                           f"from warehouse. Only {available} available.",
                "available": float(available),
                "requested": float(quantity),
                "material": material.name,
            },
        )

    movement = StockMovement(
        reference_number=reference,
        movement_type=MovementType.ISSUE,
        stock_type=StockType.MATERIAL,
        movement_date=_now().date(),
        material_id=material.id,
        lot_id=lot_id,
        source_warehouse_id=warehouse_id,
        quantity=quantity,
        notes=notes or f"Material consumption for {order.order_no}",
        created_by_id=user_id,
    )
    db.add(movement)
    await db.flush()

    # Update stock
    if stock:
        stock.quantity_on_hand -= quantity
        stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
    await db.flush()
    return movement


async def _receipt_finished_goods(
    db: AsyncSession,
    order: ProductionOrder,
    quantity: Decimal,
    warehouse_id: uuid.UUID,
    lot_number: Optional[str],
    batch_no: Optional[str],
    fg_expiry_date: Optional[str],
    user_id: uuid.UUID,
) -> tuple[StockMovement, Optional[uuid.UUID]]:
    lot_id: Optional[uuid.UUID] = None
    if lot_number:
        # Find or create lot
        r = await db.execute(
            select(Lot).where(Lot.product_id == order.product_id, Lot.lot_number == lot_number)
        )
        lot = r.scalar_one_or_none()
        if not lot:
            from datetime import date as _date
            expiry = None
            if fg_expiry_date:
                try:
                    expiry = _date.fromisoformat(fg_expiry_date)
                except ValueError:
                    pass
            lot = Lot(
                product_id=order.product_id,
                lot_number=lot_number,
                batch_number=batch_no or order.batch_no,
                expiry_date=expiry,
                manufacture_date=_now().date(),
            )
            db.add(lot)
            await db.flush()
        lot_id = lot.id

    # Get or create product stock
    filters = [
        Stock.warehouse_id == warehouse_id,
        Stock.product_id == order.product_id,
        Stock.stock_type == StockType.PRODUCT,
    ]
    if lot_id:
        filters.append(Stock.lot_id == lot_id)
    else:
        filters.append(Stock.lot_id.is_(None))

    r2 = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    existing = r2.scalar_one_or_none()

    movement = StockMovement(
        reference_number=order.order_no,
        movement_type=MovementType.RECEIPT,
        stock_type=StockType.PRODUCT,
        movement_date=_now().date(),
        product_id=order.product_id,
        lot_id=lot_id,
        destination_warehouse_id=warehouse_id,
        quantity=quantity,
        notes=f"Finished goods receipt for {order.order_no}",
        created_by_id=user_id,
    )
    db.add(movement)
    await db.flush()

    if existing:
        existing.quantity_on_hand += quantity
        existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved
    else:
        stock = Stock(
            stock_type=StockType.PRODUCT,
            warehouse_id=warehouse_id,
            product_id=order.product_id,
            lot_id=lot_id,
            quantity_on_hand=quantity,
            quantity_reserved=Decimal("0"),
            quantity_available=quantity,
        )
        db.add(stock)

    await db.flush()
    return movement, lot_id


def _compute_oee(order: ProductionOrder) -> OEEMetrics:
    scheduled_minutes = 0.0
    if order.scheduled_start and order.scheduled_end:
        scheduled_minutes = (
            (order.scheduled_end - order.scheduled_start).total_seconds() / 60
        )

    actual_minutes: Optional[float] = None
    if order.actual_start and order.actual_end:
        actual_minutes = (
            (order.actual_end - order.actual_start).total_seconds() / 60
        )

    downtime_minutes = sum(
        (log.duration_minutes or 0) for log in order.downtime_logs
    )

    available_minutes = max(scheduled_minutes - downtime_minutes, 0.0)
    availability = (available_minutes / scheduled_minutes * 100) if scheduled_minutes > 0 else 100.0

    planned = float(order.planned_quantity) if order.planned_quantity else 0.0
    actual = float(order.actual_quantity) if order.actual_quantity else 0.0
    performance = min((actual / planned * 100) if planned > 0 else 0.0, 100.0)

    quality = 100.0  # no reject tracking yet

    oee = (availability / 100) * (performance / 100) * (quality / 100) * 100

    return OEEMetrics(
        order_id=order.id,
        order_no=order.order_no,
        scheduled_minutes=scheduled_minutes,
        actual_minutes=actual_minutes,
        downtime_minutes=downtime_minutes,
        availability=round(availability, 2),
        performance=round(performance, 2),
        quality=round(quality, 2),
        oee=round(oee, 2),
    )


# ── Lifecycle operations ──────────────────────────────────────────────────────

async def release_order(db: AsyncSession, order: ProductionOrder) -> ProductionOrder:
    if order.status != ProductionOrderStatus.PLANNED:
        raise HTTPException(422, detail=f"Order is {order.status.value}. Only PLANNED orders can be released.")

    # Validate recipe is approved
    r = await db.execute(select(Recipe).where(Recipe.id == order.recipe_id))
    recipe = r.scalar_one_or_none()
    if not recipe or recipe.status.value != "APPROVED":
        raise HTTPException(422, detail="Cannot release: Recipe must be in APPROVED status.")

    order.status = ProductionOrderStatus.RELEASED
    await db.flush()
    await db.refresh(order)
    return order


async def start_order(
    db: AsyncSession, order: ProductionOrder, actual_start: Optional[datetime] = None
) -> ProductionOrder:
    if order.status != ProductionOrderStatus.RELEASED:
        raise HTTPException(422, detail=f"Order is {order.status.value}. Only RELEASED orders can be started.")

    order.status = ProductionOrderStatus.IN_PROGRESS
    order.actual_start = actual_start or _now()
    await db.flush()
    await db.refresh(order)
    return order


async def pause_order(
    db: AsyncSession, order: ProductionOrder, req: DowntimeLogCreate
) -> DowntimeLog:
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(422, detail="Order must be IN_PROGRESS to record downtime.")

    active = await crud.get_active_downtime(db, order.id)
    if active:
        raise HTTPException(422, detail="There is already an open downtime log for this order.")

    log = DowntimeLog(
        production_order_id=order.id,
        machine_id=req.machine_id,
        reason=req.reason,
        start_time=req.start_time or _now(),
        notes=req.notes,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def resume_order(
    db: AsyncSession, order: ProductionOrder, req: DowntimeLogClose
) -> DowntimeLog:
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(422, detail="Order must be IN_PROGRESS.")

    log = await crud.get_active_downtime(db, order.id)
    if not log:
        raise HTTPException(404, detail="No open downtime log found for this order.")

    end_time = req.end_time or _now()
    log.end_time = end_time
    log.duration_minutes = int((end_time - log.start_time).total_seconds() / 60)
    if req.notes:
        log.notes = req.notes
    await db.flush()
    await db.refresh(log)
    return log


async def complete_order(
    db: AsyncSession,
    order: ProductionOrder,
    req: CompleteOrderRequest,
    user_id: uuid.UUID,
) -> ProductionOrder:
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(422, detail=f"Order is {order.status.value}. Must be IN_PROGRESS to complete.")

    if req.actual_quantity <= 0:
        raise HTTPException(422, detail="actual_quantity must be positive.")

    # Close any open downtime
    active_dt = await crud.get_active_downtime(db, order.id)
    if active_dt:
        now = _now()
        active_dt.end_time = now
        active_dt.duration_minutes = int((now - active_dt.start_time).total_seconds() / 60)

    source_wh_id = req.source_warehouse_id or order.source_warehouse_id

    # ── Material consumption ──────────────────────────────────────────────────
    if req.consume_materials and source_wh_id:
        # Load recipe items
        ri_result = await db.execute(
            select(RecipeItem)
            .where(RecipeItem.recipe_id == order.recipe_id)
            .options(selectinload(RecipeItem.material))
        )
        items: List[RecipeItem] = list(ri_result.scalars().all())

        if items and float(order.planned_quantity) > 0:
            scale = float(req.actual_quantity) / float(order.planned_quantity)
        else:
            scale = 1.0

        for item in items:
            if item.is_optional:
                continue
            material = item.material
            if not material:
                continue

            loss_factor = 1 + float(item.loss_percentage or 0) / 100
            std_qty = Decimal(str(round(float(item.quantity) * scale, 4)))
            actual_qty_with_loss = Decimal(str(round(float(std_qty) * loss_factor, 4)))

            movement = await _issue_material(
                db=db,
                order=order,
                material=material,
                warehouse_id=source_wh_id,
                quantity=actual_qty_with_loss,
                lot_id=None,
                reference=order.order_no,
                notes=f"Auto-consumption for {order.order_no}",
                user_id=user_id,
            )

            consumption = MaterialConsumption(
                production_order_id=order.id,
                material_id=material.id,
                lot_id=None,
                standard_quantity=std_qty,
                actual_quantity=actual_qty_with_loss,
                variance_quantity=actual_qty_with_loss - std_qty,
                unit=item.unit,
                source_warehouse_id=source_wh_id,
                stock_movement_id=movement.id,
            )
            db.add(consumption)

    # ── Finished goods receipt ────────────────────────────────────────────────
    movement, lot_id = await _receipt_finished_goods(
        db=db,
        order=order,
        quantity=req.actual_quantity,
        warehouse_id=order.target_warehouse_id,
        lot_number=req.fg_lot_number or order.batch_no,
        batch_no=order.batch_no,
        fg_expiry_date=req.fg_expiry_date,
        user_id=user_id,
    )

    fg_receipt = FinishedGoodsReceipt(
        production_order_id=order.id,
        product_id=order.product_id,
        quantity=req.actual_quantity,
        uom=order.uom,
        lot_number=req.fg_lot_number or order.batch_no,
        batch_no=order.batch_no,
        warehouse_id=order.target_warehouse_id,
        stock_movement_id=movement.id,
        notes=req.notes,
    )
    db.add(fg_receipt)

    # ── Finalise order ────────────────────────────────────────────────────────
    order.actual_quantity = req.actual_quantity
    order.actual_end = _now()
    order.status = ProductionOrderStatus.COMPLETED
    if req.notes:
        order.notes = req.notes

    await db.flush()
    await db.refresh(order)
    return order


async def cancel_order(db: AsyncSession, order: ProductionOrder) -> ProductionOrder:
    if order.status in (ProductionOrderStatus.COMPLETED,):
        raise HTTPException(422, detail="Completed orders cannot be cancelled.")
    order.status = ProductionOrderStatus.CANCELLED
    await db.flush()
    await db.refresh(order)
    return order


# ── OEE ───────────────────────────────────────────────────────────────────────

async def get_order_oee(db: AsyncSession, order_id: uuid.UUID) -> OEEMetrics:
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    return _compute_oee(order)


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_production_report(
    db: AsyncSession,
    date_from: datetime,
    date_to: datetime,
    product_id: Optional[uuid.UUID] = None,
) -> ProductionSummary:
    q = (
        select(ProductionOrder)
        .where(
            ProductionOrder.scheduled_start >= date_from,
            ProductionOrder.scheduled_start <= date_to,
        )
        .options(
            selectinload(ProductionOrder.product),
            selectinload(ProductionOrder.downtime_logs),
        )
    )
    if product_id:
        q = q.where(ProductionOrder.product_id == product_id)

    result = await db.execute(q.order_by(ProductionOrder.scheduled_start))
    orders: List[ProductionOrder] = list(result.scalars().all())

    rows: List[ProductionReportRow] = []
    downtime_map: dict = {}
    total_planned = Decimal("0")
    total_actual = Decimal("0")
    total_downtime = 0.0
    oee_values: List[float] = []

    for o in orders:
        dt_minutes = sum(log.duration_minutes or 0 for log in o.downtime_logs)
        total_downtime += dt_minutes

        for log in o.downtime_logs:
            key = (log.reason.value, log.machine_id)
            if key not in downtime_map:
                downtime_map[key] = {"reason": log.reason.value, "count": 0, "total_minutes": 0.0, "machine_id": log.machine_id}
            downtime_map[key]["count"] += 1
            downtime_map[key]["total_minutes"] += log.duration_minutes or 0

        total_planned += o.planned_quantity
        if o.actual_quantity:
            total_actual += o.actual_quantity

        variance = None
        variance_pct = None
        if o.actual_quantity is not None:
            variance = o.actual_quantity - o.planned_quantity
            if float(o.planned_quantity) > 0:
                variance_pct = round(float(variance) / float(o.planned_quantity) * 100, 2)

        if o.status == ProductionOrderStatus.COMPLETED:
            oee = _compute_oee(o)
            oee_values.append(oee.oee)

        rows.append(ProductionReportRow(
            date=o.scheduled_start.strftime("%Y-%m-%d") if o.scheduled_start else "",
            order_no=o.order_no,
            product_name=o.product.name if o.product else "",
            product_sku=o.product.sku if o.product else "",
            planned_quantity=o.planned_quantity,
            actual_quantity=o.actual_quantity,
            variance=variance,
            variance_pct=variance_pct,
            status=o.status,
            batch_no=o.batch_no,
            downtime_minutes=dt_minutes,
        ))

    completed = sum(1 for o in orders if o.status == ProductionOrderStatus.COMPLETED)
    in_progress = sum(1 for o in orders if o.status == ProductionOrderStatus.IN_PROGRESS)

    return ProductionSummary(
        total_orders=len(orders),
        completed_orders=completed,
        in_progress_orders=in_progress,
        planned_quantity_total=total_planned,
        actual_quantity_total=total_actual,
        overall_variance=total_actual - total_planned,
        total_downtime_minutes=total_downtime,
        avg_oee=round(sum(oee_values) / len(oee_values), 2) if oee_values else None,
        orders=rows,
        downtime_summary=[DowntimeSummaryRow(**v) for v in downtime_map.values()],
    )
