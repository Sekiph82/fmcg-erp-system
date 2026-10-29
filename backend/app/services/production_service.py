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

from datetime import date, datetime, timezone
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
from app.models.traceability import (
    GenealogyRelType,
    LotGenealogyLink,
    TraceEvent,
    TraceEventLine,
    TraceEventType,
    TraceItemStage,
)
from app.models.quality import QCType
from app.schemas.production import (
    CompleteOrderRequest, DowntimeLogCreate, DowntimeLogClose,
    OEEMetrics, ProductionReportRow, DowntimeSummaryRow, ProductionSummary,
    MaterialConsumptionRead, FinishedGoodsReceiptRead, DowntimeLogRead,
)
from app.crud import production as crud
from app.services.inventory_locking import lot_identity, lock_inventory_identity, stock_identity
from app.services import quality_service


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def _require_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail=f"Warehouse {warehouse_id} not found")
    return wh


async def _lock_order_for_transition(db: AsyncSession, order_id: uuid.UUID) -> ProductionOrder:
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    return order


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
        Stock.is_blocked == False,  # noqa: E712
    ]
    if lot_id:
        filters.append(Stock.lot_id == lot_id)
    else:
        filters.append(Stock.lot_id.is_(None))
    result = await db.execute(
        select(Stock)
        .where(and_(*filters))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _resolve_material_lot_id(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    material_id: uuid.UUID,
    requested_lot_id: Optional[uuid.UUID],
) -> Optional[uuid.UUID]:
    if requested_lot_id is not None:
        return requested_lot_id

    result = await db.execute(
        select(Stock.lot_id)
        .where(
            Stock.warehouse_id == warehouse_id,
            Stock.material_id == material_id,
            Stock.stock_type == StockType.MATERIAL,
            Stock.is_blocked == False,  # noqa: E712
            Stock.quantity_available > 0,
        )
        .group_by(Stock.lot_id)
        .order_by(Stock.lot_id)
    )
    candidates = list(result.scalars().all())
    if len(candidates) > 1:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "SOURCE_LOT_SELECTION_REQUIRED",
                "message": f"Select one source lot for material {material_id}; automatic FIFO/FEFO selection is not configured.",
                "material_id": str(material_id),
            },
        )
    return candidates[0] if candidates else None


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
        await lock_inventory_identity(
            db, lot_identity(product_id=order.product_id, lot_number=lot_number)
        )
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

    await lock_inventory_identity(db, stock_identity(
        stock_type=StockType.PRODUCT,
        warehouse_id=warehouse_id,
        product_id=order.product_id,
        lot_id=lot_id,
    ))

    r2 = await db.execute(
        select(Stock)
        .where(and_(*filters))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
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
    order = await _lock_order_for_transition(db, order.id)
    if order.status != ProductionOrderStatus.PLANNED:
        raise HTTPException(422, detail=f"Order is {order.status.value}. Only PLANNED orders can be released.")

    # Validate recipe is approved
    r = await db.execute(select(Recipe).where(Recipe.id == order.recipe_id))
    recipe = r.scalar_one_or_none()
    if not recipe or recipe.status.value != "APPROVED":
        raise HTTPException(422, detail="Cannot release: Recipe must be in APPROVED status.")

    from app.services.qms_service import (
        PRODUCTION_GATE_TARGET_MODULE,
        PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
        ensure_production_quality_gates_pass,
        lock_quality_gate_scope,
    )

    await lock_quality_gate_scope(db, PRODUCTION_GATE_TARGET_MODULE, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT)
    try:
        await ensure_production_quality_gates_pass(
            db, order, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, date.today()
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    order.status = ProductionOrderStatus.RELEASED
    await db.flush()
    await db.refresh(order)
    return order


async def start_order(
    db: AsyncSession, order: ProductionOrder, actual_start: Optional[datetime] = None
) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
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
    order = await _lock_order_for_transition(db, order.id)
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
    order = await _lock_order_for_transition(db, order.id)
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
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(404, detail="Production order not found")

    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(422, detail=f"Order is {order.status.value}. Must be IN_PROGRESS to complete.")

    from app.services.qms_service import (
        PRODUCTION_GATE_TARGET_MODULE,
        PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
        ensure_production_quality_gates_pass,
        lock_quality_gate_scope,
    )

    await lock_quality_gate_scope(db, PRODUCTION_GATE_TARGET_MODULE, PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT)
    try:
        await ensure_production_quality_gates_pass(
            db, order, PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, date.today()
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if req.actual_quantity <= 0:
        raise HTTPException(422, detail="actual_quantity must be positive.")

    finished_lot_number = (req.fg_lot_number or order.batch_no or "").strip()
    if not finished_lot_number:
        raise HTTPException(422, detail="A finished-goods lot number or production batch number is required.")

    # Close any open downtime
    active_dt = await crud.get_active_downtime(db, order.id)
    if active_dt:
        now = _now()
        active_dt.end_time = now
        active_dt.duration_minutes = int((now - active_dt.start_time).total_seconds() / 60)

    source_wh_id = req.source_warehouse_id or order.source_warehouse_id

    # ── Material consumption ──────────────────────────────────────────────────
    genealogy_inputs: list[tuple[uuid.UUID, uuid.UUID, Decimal, str]] = []
    if req.consume_materials and source_wh_id:
        # Load recipe items
        ri_result = await db.execute(
            select(RecipeItem)
            .where(RecipeItem.recipe_id == order.recipe_id)
            .order_by(RecipeItem.material_id, RecipeItem.id)
            .options(selectinload(RecipeItem.material))
        )
        items: List[RecipeItem] = list(ri_result.scalars().all())
        recipe_material_ids = {item.material_id for item in items if not item.is_optional}
        unexpected_lot_ids = set(req.material_lot_ids) - recipe_material_ids
        if unexpected_lot_ids:
            raise HTTPException(
                status_code=422,
                detail="Source lot selections may only reference required materials on this recipe.",
            )

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
            source_lot_id = await _resolve_material_lot_id(
                db,
                warehouse_id=source_wh_id,
                material_id=material.id,
                requested_lot_id=req.material_lot_ids.get(material.id),
            )

            movement = await _issue_material(
                db=db,
                order=order,
                material=material,
                warehouse_id=source_wh_id,
                quantity=actual_qty_with_loss,
                lot_id=source_lot_id,
                reference=order.order_no,
                notes=f"Auto-consumption for {order.order_no}",
                user_id=user_id,
            )

            consumption = MaterialConsumption(
                production_order_id=order.id,
                material_id=material.id,
                lot_id=source_lot_id,
                standard_quantity=std_qty,
                actual_quantity=actual_qty_with_loss,
                variance_quantity=actual_qty_with_loss - std_qty,
                unit=item.unit,
                source_warehouse_id=source_wh_id,
                stock_movement_id=movement.id,
            )
            db.add(consumption)
            if source_lot_id is not None:
                genealogy_inputs.append((material.id, source_lot_id, actual_qty_with_loss, item.unit))

    # ── Finished goods receipt ────────────────────────────────────────────────
    movement, lot_id = await _receipt_finished_goods(
        db=db,
        order=order,
        quantity=req.actual_quantity,
        warehouse_id=order.target_warehouse_id,
        lot_number=finished_lot_number,
        batch_no=order.batch_no,
        fg_expiry_date=req.fg_expiry_date,
        user_id=user_id,
    )

    fg_receipt = FinishedGoodsReceipt(
        production_order_id=order.id,
        product_id=order.product_id,
        quantity=req.actual_quantity,
        uom=order.uom,
        lot_number=finished_lot_number,
        batch_no=order.batch_no,
        warehouse_id=order.target_warehouse_id,
        stock_movement_id=movement.id,
        notes=req.notes,
    )
    db.add(fg_receipt)

    if lot_id is not None and genealogy_inputs:
        trace_event = TraceEvent(
            trace_event_type=TraceEventType.transformation,
            event_datetime=_now(),
            reference_number=order.order_no,
            source_document_type="production_order",
            source_document_id=order.id,
            production_order_id=order.id,
            warehouse_id=order.target_warehouse_id,
            performed_by_id=user_id,
            notes="Production transformation from explicitly issued material lots to finished-goods lot.",
        )
        db.add(trace_event)
        await db.flush()
        for material_id, source_lot_id, linked_quantity, source_uom in genealogy_inputs:
            db.add(TraceEventLine(
                event_id=trace_event.id,
                product_id=order.product_id,
                material_id=material_id,
                source_lot_id=source_lot_id,
                child_lot_id=lot_id,
                quantity=linked_quantity,
                uom=source_uom,
                source_stage=TraceItemStage.raw_stock,
                dest_stage=TraceItemStage.finished_good,
                movement_reason="production consumption",
                notes=f"Production order {order.order_no}",
            ))
            db.add(LotGenealogyLink(
                parent_lot_id=source_lot_id,
                child_lot_id=lot_id,
                relationship_type=GenealogyRelType.intermediate_from,
                source_document_type="production_order",
                source_document_id=order.id,
                production_order_id=order.id,
                quantity_linked=linked_quantity,
                uom=source_uom,
                parent_stage=TraceItemStage.raw_stock,
                child_stage=TraceItemStage.finished_good,
                notes=f"Produced by {order.order_no}",
            ))

    # ── Finalise order ────────────────────────────────────────────────────────
    order.actual_quantity = req.actual_quantity
    order.actual_end = _now()
    order.status = ProductionOrderStatus.COMPLETED
    if req.notes:
        order.notes = req.notes

    await db.flush()
    await quality_service.create_qc_for_order(
        db,
        production_order_id=order.id,
        product_id=order.product_id,
        warehouse_id=order.target_warehouse_id,
        lot_number=finished_lot_number,
        batch_no=order.batch_no,
        inspection_no=f"FG-QC-{order.id.hex}",
        inspector_id=user_id,
        qc_type=QCType.FINISHED_GOODS,
    )
    await db.refresh(order)
    return order


async def cancel_order(db: AsyncSession, order: ProductionOrder) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
    if order.status not in {
        ProductionOrderStatus.PLANNED,
        ProductionOrderStatus.RELEASED,
        ProductionOrderStatus.IN_PROGRESS,
    }:
        raise HTTPException(422, detail=f"Orders in {order.status.value} status cannot be cancelled.")
    active_downtime = (
        await crud.get_active_downtime(db, order.id)
        if order.status == ProductionOrderStatus.IN_PROGRESS
        else None
    )
    if active_downtime:
        end_time = _now()
        active_downtime.end_time = end_time
        active_downtime.duration_minutes = max(
            0, int((end_time - active_downtime.start_time).total_seconds() / 60)
        )
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
