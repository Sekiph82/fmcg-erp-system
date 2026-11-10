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

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production import (
    ProductionOrder,
    MaterialConsumption, FinishedGoodsReceipt, DowntimeLog,
    ProductionOrderStatus,
)
from app.models.production_advanced import WorkOrder, WorkOrderStatus
from app.models.production_advanced import RoutingStep
from app.models.recipe import Recipe, RecipeItem
from app.models.inventory import Stock, StockMovement, MovementType, StockType, Lot
from app.models.master import Material, Warehouse
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.models.traceability import (
    GenealogyRelType,
    LotGenealogyLink,
    TraceEvent,
    TraceEventLine,
    TraceEventType,
    TraceItemStage,
)
from app.services.oee_calculation import calculate_oee_components
from app.models.quality import QCType
from app.schemas.production import (
    CompleteOrderRequest, DowntimeLogCreate, DowntimeLogClose,
    OEEMetrics, ProductionReportRow, DowntimeSummaryRow, ProductionSummary,
)
from app.crud import production as crud
from app.services.inventory_locking import lot_identity, lock_inventory_identity, stock_identity
from app.services import quality_service
from app.services.utilities_service import convert_uom
from app.services.production_transition_history import PRODUCTION_ORDER, record_transition


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


async def _require_release_material_readiness(
    db: AsyncSession, order: ProductionOrder, recipe: Recipe
) -> None:
    """Fail release when required recipe inputs are not currently usable.

    This is a point-in-time readiness gate, not a stock reservation. Material
    issue remains authoritative and rechecks availability when consumption is
    posted. The existing configured QMS release gate remains authoritative for
    production QC; blocked/quarantined/expired material stock is excluded here.
    """
    required_items = [item for item in recipe.items if not item.is_optional]
    if not required_items:
        return
    if order.source_warehouse_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PRODUCTION_SOURCE_WAREHOUSE_REQUIRED",
                "message": "Cannot release: assign a source warehouse to verify required recipe materials.",
                "production_order_id": str(order.id),
            },
        )

    warehouse_result = await db.execute(
        select(Warehouse).where(Warehouse.id == order.source_warehouse_id)
    )
    source_warehouse = warehouse_result.scalar_one_or_none()
    if source_warehouse is None or not source_warehouse.is_active:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PRODUCTION_SOURCE_WAREHOUSE_UNAVAILABLE",
                "message": "Cannot release: the production source warehouse is missing or inactive.",
                "production_order_id": str(order.id),
            },
        )

    def _uom_code(value) -> str:
        return str(getattr(value, "value", value) or "").strip().upper()

    required_by_material: dict[uuid.UUID, tuple[Material, Decimal]] = {}
    for item in required_items:
        material = item.material
        if material is None or not material.is_active:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "PRODUCTION_RECIPE_MATERIAL_UNAVAILABLE",
                    "message": "Cannot release: a required recipe material is missing or inactive.",
                    "recipe_item_id": str(item.id),
                    "material_id": str(item.material_id),
                },
            )
        quantity = Decimal(item.quantity)
        loss_percentage = Decimal(item.loss_percentage or 0)
        if quantity < 0 or loss_percentage < 0 or loss_percentage >= 100:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "PRODUCTION_RECIPE_MATERIAL_INVALID",
                    "message": "Cannot release: a required recipe material has invalid quantity or loss percentage.",
                    "recipe_item_id": str(item.id),
                    "material_id": str(material.id),
                },
            )
        try:
            material_uom_quantity = await convert_uom(
                db,
                quantity * (Decimal(1) + loss_percentage / Decimal(100)),
                _uom_code(item.unit),
                _uom_code(material.uom),
            )
        except (HTTPException, MultipleResultsFound) as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "PRODUCTION_MATERIAL_UOM_UNRESOLVED",
                    "message": f"Cannot release: recipe material '{material.name}' has no unique conversion to its inventory unit.",
                    "recipe_item_id": str(item.id),
                    "material_id": str(material.id),
                    "from_uom": _uom_code(item.unit),
                    "to_uom": _uom_code(material.uom),
                },
            ) from exc
        required_quantity = material_uom_quantity.quantize(
            Decimal("0.001"), rounding=ROUND_CEILING
        )
        previous = required_by_material.get(material.id)
        required_by_material[material.id] = (
            material,
            required_quantity + (previous[1] if previous else Decimal(0)),
        )

    material_use_date = order.scheduled_start.date()
    for material_id, (material, required_quantity) in required_by_material.items():
        stock_result = await db.execute(
            select(Stock)
            .options(selectinload(Stock.lot))
            .where(
                Stock.stock_type == StockType.MATERIAL,
                Stock.warehouse_id == order.source_warehouse_id,
                Stock.material_id == material_id,
                Stock.is_blocked.is_(False),
            )
            .order_by(Stock.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        usable_quantity = Decimal(0)
        stocks = list(stock_result.scalars().all())
        lot_ids = sorted({stock.lot_id for stock in stocks if stock.lot_id is not None})
        quality_statuses: dict[uuid.UUID, LotQualityStatus] = {}
        if lot_ids:
            quality_result = await db.execute(
                select(LotQualityStatus)
                .where(LotQualityStatus.lot_id.in_(lot_ids))
                .order_by(LotQualityStatus.lot_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            quality_statuses = {
                status.lot_id: status for status in quality_result.scalars().all()
            }
        for stock in stocks:
            if stock.lot_id is not None:
                lot = stock.lot
                quality_status = quality_statuses.get(stock.lot_id)
                if (
                    lot is None
                    or lot.material_id != material_id
                    or lot.is_quarantine
                    or (lot.expiry_date is not None and lot.expiry_date < material_use_date)
                    or (
                        quality_status is not None
                        and (
                            quality_status.hold_flag
                            or quality_status.quarantine_flag
                            or quality_status.release_status != ReleaseStatus.RELEASED
                        )
                    )
                ):
                    continue
            usable_quantity += max(Decimal(0), Decimal(stock.quantity_available))
        if usable_quantity < required_quantity:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "PRODUCTION_MATERIAL_SHORTAGE",
                    "message": f"Cannot release: insufficient released stock for required material '{material.name}'.",
                    "production_order_id": str(order.id),
                    "material_id": str(material_id),
                    "required_quantity": str(required_quantity),
                    "available_quantity": str(usable_quantity),
                    "uom": _uom_code(material.uom),
                },
            )


PRODUCTION_ORDER_TRANSITIONS = {
    ProductionOrderStatus.PLANNED: {
        ProductionOrderStatus.RELEASED,
        ProductionOrderStatus.CANCELLED,
    },
    ProductionOrderStatus.RELEASED: {
        ProductionOrderStatus.IN_PROGRESS,
        ProductionOrderStatus.CANCELLED,
    },
    ProductionOrderStatus.IN_PROGRESS: {
        ProductionOrderStatus.COMPLETED,
    },
    ProductionOrderStatus.COMPLETED: set(),
    ProductionOrderStatus.CANCELLED: set(),
}


def _require_order_transition(order: ProductionOrder, target: ProductionOrderStatus) -> None:
    allowed = PRODUCTION_ORDER_TRANSITIONS.get(order.status, set())
    if target not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition production order from {order.status.value} to {target.value}.",
        )


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

    components = calculate_oee_components(
        planned_time_min=Decimal(str(scheduled_minutes)),
        downtime_min=Decimal(str(downtime_minutes)),
        actual_run_time_min=(
            Decimal(str(actual_minutes)) - Decimal(str(downtime_minutes))
            if actual_minutes is not None
            else None
        ),
        ideal_cycle_time_sec=None,
        total_units=None,
        good_units=None,
    )

    return OEEMetrics(
        order_id=order.id,
        order_no=order.order_no,
        scheduled_minutes=scheduled_minutes,
        actual_minutes=actual_minutes,
        downtime_minutes=downtime_minutes,
        availability=float(components["availability"]) if components["availability"] is not None else None,
        performance=float(components["performance"]) if components["performance"] is not None else None,
        quality=float(components["quality"]) if components["quality"] is not None else None,
        oee=float(components["oee"]) if components["oee"] is not None else None,
    )


# ── Lifecycle operations ──────────────────────────────────────────────────────

async def approve_order(
    db: AsyncSession, order: ProductionOrder, user_id: uuid.UUID
) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
    if order.status != ProductionOrderStatus.PLANNED:
        raise HTTPException(422, detail="Only a planned production order can be approved.")
    if order.approved_by is not None or order.approved_at is not None:
        raise HTTPException(422, detail="Production order approval has already been recorded.")
    if order.created_by is None:
        raise HTTPException(422, detail="The order creator must be recorded before approval.")
    if order.created_by == user_id:
        raise HTTPException(422, detail="The order creator cannot approve the same production order.")

    order.approved_by = user_id
    order.approved_at = _now()
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="APPROVED",
        actor_id=user_id,
        from_status=order.status,
        to_status=order.status,
    )
    await db.flush()
    await db.refresh(order)
    return order

async def release_order(
    db: AsyncSession, order: ProductionOrder, user_id: uuid.UUID
) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
    _require_order_transition(order, ProductionOrderStatus.RELEASED)
    if order.approved_by is None or order.approved_at is None:
        raise HTTPException(422, detail="Cannot release: production order approval is required first.")

    # Validate recipe is approved
    r = await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.items).selectinload(RecipeItem.material))
        .where(Recipe.id == order.recipe_id)
    )
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
            db, order, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, date.today(), actor_id=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await _require_release_material_readiness(db, order, recipe)

    previous_status = order.status
    order.status = ProductionOrderStatus.RELEASED
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="RELEASED",
        actor_id=user_id,
        from_status=previous_status,
        to_status=order.status,
    )
    await db.flush()
    await db.refresh(order)
    return order


async def start_order(
    db: AsyncSession,
    order: ProductionOrder,
    actual_start: Optional[datetime],
    user_id: uuid.UUID,
) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
    _require_order_transition(order, ProductionOrderStatus.IN_PROGRESS)

    previous_status = order.status
    order.status = ProductionOrderStatus.IN_PROGRESS
    order.actual_start = actual_start or _now()
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="STARTED",
        actor_id=user_id,
        from_status=previous_status,
        to_status=order.status,
    )
    await db.flush()
    await db.refresh(order)
    return order


async def pause_order(
    db: AsyncSession, order: ProductionOrder, req: DowntimeLogCreate, user_id: uuid.UUID
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
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="DOWNTIME_OPENED",
        actor_id=user_id,
        from_status=order.status,
        to_status=order.status,
    )
    await db.flush()
    await db.refresh(log)
    return log


async def resume_order(
    db: AsyncSession, order: ProductionOrder, req: DowntimeLogClose, user_id: uuid.UUID
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
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="DOWNTIME_CLOSED",
        actor_id=user_id,
        from_status=order.status,
        to_status=order.status,
    )
    await db.flush()
    await db.refresh(log)
    return log


async def _completed_work_order_output_quantity(
    db: AsyncSession, order: ProductionOrder
) -> Optional[Decimal]:
    all_count_result = await db.execute(
        select(func.count(WorkOrder.id)).where(WorkOrder.production_order_id == order.id)
    )
    all_count = all_count_result.scalar_one()
    rows_result = await db.execute(
        select(
            WorkOrder,
            RoutingStep.routing_id,
            RoutingStep.step_number,
        )
        .outerjoin(RoutingStep, WorkOrder.routing_step_id == RoutingStep.id)
        .where(
            WorkOrder.production_order_id == order.id,
            WorkOrder.status != WorkOrderStatus.CANCELLED,
        )
        .order_by(WorkOrder.created_at, WorkOrder.id)
    )
    rows = list(rows_result.all())
    if not rows:
        if all_count:
            raise HTTPException(
                422,
                detail="Production order has only cancelled work orders; add an active operation before completion.",
            )
        return None

    if any(work_order.status != WorkOrderStatus.COMPLETED for work_order, _, _ in rows):
        raise HTTPException(422, detail="Every active work order must be completed before order closure.")
    if any(work_order.actual_quantity is None for work_order, _, _ in rows):
        raise HTTPException(422, detail="Completed work orders must record their actual quantity.")

    routed_rows = [row for row in rows if row[0].routing_step_id is not None]
    manual_rows = [row for row in rows if row[0].routing_step_id is None]
    if routed_rows and manual_rows:
        raise HTTPException(422, detail="Routed and manual work orders cannot be reconciled on the same production order.")

    if routed_rows:
        routing_ids = {routing_id for _, routing_id, _ in routed_rows}
        if len(routing_ids) != 1 or None in routing_ids:
            raise HTTPException(422, detail="Production order work orders must use one valid routing.")
        routing_id = next(iter(routing_ids))
        final_step_result = await db.execute(
            select(func.max(RoutingStep.step_number)).where(RoutingStep.routing_id == routing_id)
        )
        final_step_number = final_step_result.scalar_one_or_none()
        if final_step_number is None:
            raise HTTPException(422, detail="Production routing has no final operation to reconcile.")
        final_rows = [row[0] for row in routed_rows if row[2] == final_step_number]
        if not final_rows:
            raise HTTPException(422, detail="Final routing operation has no linked work orders.")
    else:
        manual_groups = {(work_order.work_center_id, work_order.operation.strip()) for work_order, _, _ in manual_rows}
        if len(manual_groups) != 1:
            raise HTTPException(
                422,
                detail="Multiple manual operations have no authoritative sequence; link them to a routing before closure.",
            )
        final_rows = [work_order for work_order, _, _ in manual_rows]

    return sum(
        (
            Decimal(work_order.actual_quantity) - Decimal(work_order.rework_quantity or 0)
            for work_order in final_rows
        ),
        Decimal("0"),
    )


async def _create_partial_backorder(
    db: AsyncSession,
    source: ProductionOrder,
    quantity: Decimal,
    actor_id: uuid.UUID,
) -> ProductionOrder:
    if quantity <= 0 or quantity != quantity.quantize(Decimal("0.001")):
        raise HTTPException(422, detail="Backorder quantity must be positive and use no more than three decimal places.")
    existing_result = await db.execute(
        select(ProductionOrder.id)
        .where(ProductionOrder.backorder_of_id == source.id)
        .limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(422, detail="This production order already has a backorder; refusing to create a duplicate.")

    duration = source.scheduled_end - source.scheduled_start
    if duration <= timedelta(0):
        raise HTTPException(422, detail="A valid source schedule window is required to plan the backorder.")
    now = _now()
    scheduled_start = max(source.scheduled_end, now)
    scheduled_end = scheduled_start + duration

    sequence = 1
    while True:
        order_no = f"{source.order_no}-BO-{sequence:02d}"
        if len(order_no) > 50:
            order_no = f"BO-{source.id.hex[:16]}-{sequence:02d}"
        collision = await db.execute(
            select(ProductionOrder.id).where(ProductionOrder.order_no == order_no).limit(1)
        )
        if collision.scalar_one_or_none() is None:
            break
        sequence += 1
        if sequence > 999_999:
            raise HTTPException(422, detail="Unable to allocate a unique backorder number.")

    backorder = ProductionOrder(
        order_no=order_no,
        plan_line_id=source.plan_line_id,
        product_id=source.product_id,
        recipe_id=source.recipe_id,
        planned_quantity=quantity,
        actual_quantity=None,
        backorder_of_id=source.id,
        backordered_quantity=Decimal("0"),
        batch_no=source.batch_no,
        uom=source.uom,
        status=ProductionOrderStatus.PLANNED,
        target_warehouse_id=source.target_warehouse_id,
        source_warehouse_id=source.source_warehouse_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        created_by=actor_id,
        notes=(
            f"Backorder from {source.order_no}; remaining quantity {quantity} {source.uom}."
            + (f" Source notes: {source.notes}" if source.notes else "")
        ),
    )
    db.add(backorder)
    source.backordered_quantity = quantity
    await db.flush()
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=backorder.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=source.id,
        action="BACKORDER_CREATED",
        actor_id=actor_id,
        to_status=backorder.status,
    )
    return backorder


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
    _require_order_transition(order, ProductionOrderStatus.COMPLETED)

    requested_quantity = Decimal(req.actual_quantity)
    if not requested_quantity.is_finite() or requested_quantity <= 0:
        raise HTTPException(422, detail="actual_quantity must be a positive finite quantity.")
    if requested_quantity != requested_quantity.quantize(Decimal("0.001")):
        raise HTTPException(422, detail="actual_quantity must use no more than three decimal places.")
    if requested_quantity > Decimal(order.planned_quantity):
        raise HTTPException(422, detail="actual_quantity cannot exceed the production-order planned quantity.")

    final_operation_quantity = await _completed_work_order_output_quantity(db, order)
    if final_operation_quantity is not None and requested_quantity != final_operation_quantity:
        raise HTTPException(
            422,
            detail=(
                "Production-order actual quantity must equal the completed output of the final work-order operation "
                f"({final_operation_quantity} {order.uom})."
            ),
        )

    unfinished_work_order = await db.execute(
        select(WorkOrder.id)
        .where(
            WorkOrder.production_order_id == order.id,
            WorkOrder.status.notin_({WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}),
        )
        .limit(1)
    )
    if unfinished_work_order.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=422,
            detail="All work orders must be completed before the production order can be completed.",
        )

    from app.services.qms_service import (
        PRODUCTION_GATE_TARGET_MODULE,
        PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
        ensure_production_quality_gates_pass,
        lock_quality_gate_scope,
    )

    await lock_quality_gate_scope(db, PRODUCTION_GATE_TARGET_MODULE, PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT)
    try:
        await ensure_production_quality_gates_pass(
            db, order, PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, date.today(), actor_id=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
    from app.models.material_flow import (
        FlowStatus,
        FlowType,
        MaterialFlowLine,
        MaterialFlowTransaction,
        ProductionConsumption,
    )

    reserved_issue_result = await db.execute(
        select(MaterialFlowLine, MaterialFlowTransaction.flow_type)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(
            MaterialFlowTransaction.production_order_id == order.id,
            MaterialFlowTransaction.flow_type.in_((FlowType.RAW_ISSUE, FlowType.PKG_ISSUE)),
            MaterialFlowTransaction.status == FlowStatus.POSTED,
            MaterialFlowTransaction.source_document_type == "MATERIAL_RESERVATION",
            MaterialFlowLine.issue_flag.is_(True),
            MaterialFlowLine.item_type == "material",
            MaterialFlowLine.reservation_line_id.is_not(None),
        )
        .order_by(MaterialFlowTransaction.transaction_datetime, MaterialFlowLine.line_no)
        .with_for_update()
    )
    reserved_issue_rows = reserved_issue_result.all()
    reserved_issue_lines = {
        line.id: (line, flow_type) for line, flow_type in reserved_issue_rows
    }
    reserved_issue_material_ids = {
        line.material_id for line, _ in reserved_issue_rows if line.material_id is not None
    }
    material_consumptions: list[ProductionConsumption] = []
    reserved_issue_line_ids = list(reserved_issue_lines)
    if reserved_issue_line_ids:
        material_consumption_result = await db.execute(
            select(ProductionConsumption)
            .where(
                ProductionConsumption.production_order_id == order.id,
                ProductionConsumption.flow_line_id.in_(reserved_issue_line_ids),
                ProductionConsumption.quantity_consumed > 0,
            )
            .order_by(ProductionConsumption.consumed_at, ProductionConsumption.id)
            .with_for_update()
        )
        material_consumptions = list(material_consumption_result.scalars().all())

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
            scale = float(requested_quantity) / float(order.planned_quantity)
        else:
            scale = 1.0

        for item in items:
            if item.is_optional:
                continue
            material = item.material
            if not material:
                continue
            if material.id in reserved_issue_material_ids:
                # Reservation-based issue already reduced stock; its actual
                # consumption event is the authority for genealogy at close.
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
    from app.services.material_flow_service import (
        cancel_reservations_for_order,
        receive_wip_finished_goods,
    )

    # If this order used the M24 WIP ledger, consume its exact available stage and
    # location balances in the same transaction as the canonical stock receipt.
    # Orders without recorded WIP retain the established production completion path.
    await receive_wip_finished_goods(
        db,
        order.id,
        quantity=requested_quantity,
        destination_warehouse_id=order.target_warehouse_id,
        created_by=user_id,
    )
    # Release unused reservation balances in the same unit of work as stock,
    # WIP, finished-goods, genealogy, and order completion changes.
    await cancel_reservations_for_order(db, order.id)

    movement, lot_id = await _receipt_finished_goods(
        db=db,
        order=order,
        quantity=requested_quantity,
        warehouse_id=order.target_warehouse_id,
        lot_number=finished_lot_number,
        batch_no=order.batch_no,
        fg_expiry_date=req.fg_expiry_date,
        user_id=user_id,
    )

    fg_receipt = FinishedGoodsReceipt(
        production_order_id=order.id,
        product_id=order.product_id,
        quantity=requested_quantity,
        uom=order.uom,
        lot_number=finished_lot_number,
        batch_no=order.batch_no,
        warehouse_id=order.target_warehouse_id,
        stock_movement_id=movement.id,
        notes=req.notes,
    )
    db.add(fg_receipt)

    if lot_id is not None and (genealogy_inputs or material_consumptions):
        trace_event = TraceEvent(
            trace_event_type=TraceEventType.transformation,
            event_datetime=_now(),
            reference_number=order.order_no,
            source_document_type="production_order",
            source_document_id=order.id,
            production_order_id=order.id,
            warehouse_id=order.target_warehouse_id,
            performed_by_id=user_id,
            notes="Production transformation with raw-material and packaging consumption linked to the finished-goods lot.",
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
        for consumption in material_consumptions:
            if consumption.material_id is None:
                continue
            issue_line, flow_type = reserved_issue_lines[consumption.flow_line_id]
            is_packaging = flow_type == FlowType.PKG_ISSUE
            source_stage = TraceItemStage.packaging if is_packaging else TraceItemStage.raw_stock
            relationship_type = (
                GenealogyRelType.packed_from if is_packaging else GenealogyRelType.intermediate_from
            )
            db.add(TraceEventLine(
                event_id=trace_event.id,
                product_id=order.product_id,
                material_id=consumption.material_id,
                source_lot_id=consumption.lot_id,
                child_lot_id=lot_id,
                quantity=consumption.quantity_consumed,
                uom=consumption.uom,
                source_stage=source_stage,
                dest_stage=TraceItemStage.finished_good,
                source_location_id=issue_line.source_location_id,
                quality_status=issue_line.quality_status.value if hasattr(issue_line.quality_status, "value") else issue_line.quality_status,
                movement_reason="packaging consumption" if is_packaging else "raw material consumption",
                notes=(
                    f"Reserved issue line {consumption.flow_line_id}; "
                    f"actual consumption event {consumption.id}; order {order.order_no}."
                ),
            ))
            if consumption.lot_id is not None:
                db.add(LotGenealogyLink(
                    parent_lot_id=consumption.lot_id,
                    child_lot_id=lot_id,
                    relationship_type=relationship_type,
                    source_document_type="production_order",
                    source_document_id=order.id,
                    production_order_id=order.id,
                    quantity_linked=consumption.quantity_consumed,
                    uom=consumption.uom,
                    parent_stage=source_stage,
                    child_stage=TraceItemStage.finished_good,
                    notes=f"{'Packaging' if is_packaging else 'Raw material'} consumed by {order.order_no}; event {consumption.id}.",
                ))

    # ── Finalise order ────────────────────────────────────────────────────────
    previous_status = order.status
    order.actual_quantity = requested_quantity
    order.actual_end = _now()
    order.status = ProductionOrderStatus.COMPLETED
    remaining_quantity = Decimal(order.planned_quantity) - requested_quantity
    backorder = None
    if remaining_quantity > 0:
        backorder = await _create_partial_backorder(db, order, remaining_quantity, user_id)
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="COMPLETED_WITH_BACKORDER" if backorder is not None else "COMPLETED",
        actor_id=user_id,
        from_status=previous_status,
        to_status=order.status,
    )
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


async def cancel_order(
    db: AsyncSession, order: ProductionOrder, user_id: uuid.UUID
) -> ProductionOrder:
    order = await _lock_order_for_transition(db, order.id)
    _require_order_transition(order, ProductionOrderStatus.CANCELLED)
    from app.services.material_flow_service import cancel_reservations_for_order

    await cancel_reservations_for_order(db, order.id)
    previous_status = order.status
    order.status = ProductionOrderStatus.CANCELLED
    record_transition(
        db,
        entity_type=PRODUCTION_ORDER,
        entity_id=order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=order.id,
        action="CANCELLED",
        actor_id=user_id,
        from_status=previous_status,
        to_status=order.status,
    )
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

        backordered_quantity = Decimal(o.backordered_quantity or 0)
        effective_planned_quantity = Decimal(o.planned_quantity) - backordered_quantity
        total_planned += effective_planned_quantity
        if o.actual_quantity:
            total_actual += o.actual_quantity

        variance = None
        variance_pct = None
        if o.actual_quantity is not None:
            variance = o.actual_quantity - effective_planned_quantity
            if effective_planned_quantity > 0:
                variance_pct = round(float(variance) / float(effective_planned_quantity) * 100, 2)

        if o.status == ProductionOrderStatus.COMPLETED:
            oee = _compute_oee(o)
            if oee.oee is not None:
                oee_values.append(oee.oee)

        rows.append(ProductionReportRow(
            date=o.scheduled_start.strftime("%Y-%m-%d") if o.scheduled_start else "",
            order_no=o.order_no,
            product_name=o.product.name if o.product else "",
            product_sku=o.product.sku if o.product else "",
            planned_quantity=effective_planned_quantity,
            backordered_quantity=backordered_quantity,
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
        avg_oee=round(sum(oee_values) / len(oee_values), 4) if oee_values else None,
        orders=rows,
        downtime_summary=[DowntimeSummaryRow(**v) for v in downtime_map.values()],
    )
