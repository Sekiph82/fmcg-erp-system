"""
CRUD for Advanced Production Module.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import Base
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import RecipeItem
from app.models.master import Material

from app.models.production_advanced import (
    WorkCenter, Routing, RoutingStep, WorkOrder, WorkOrderStatus,
    Shift, ProductionSchedule, TimeTracking, DowntimeEvent,
    AdvQCInspection, AdvQCResult, WasteRecord, BatchLot, LaborLog, OEERecord,
)
from app.models.production_work_order_genealogy import ProductionWorkOrderGenealogy
from app.services.production_transition_history import (
    PRODUCTION_ORDER,
    WORK_ORDER,
    record_transition,
)
from app.schemas.production_advanced import (
    WorkCenterCreate, WorkCenterUpdate,
    RoutingCreate, RoutingUpdate, RoutingStepCreate,
    WorkOrderCreate, WorkOrderUpdate,
    ShiftCreate, ShiftUpdate,
    ProductionScheduleCreate, ProductionScheduleUpdate,
    TimeTrackingCreate, TimeTrackingUpdate,
    DowntimeEventCreate, DowntimeEventUpdate,
    AdvQCInspectionCreate, AdvQCInspectionUpdate, AdvQCResultCreate,
    WasteRecordCreate, WasteRecordUpdate,
    BatchLotCreate, BatchLotUpdate,
    LaborLogCreate, LaborLogUpdate,
    OEERecordCreate, OEERecordUpdate,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get(db: AsyncSession, model, pk: UUID):
    r = await db.execute(select(model).where(model.id == pk))
    return r.scalar_one_or_none()


async def _list(db: AsyncSession, model, skip=0, limit=100):
    r = await db.execute(select(model).offset(skip).limit(limit))
    return list(r.scalars().all())


# ── Work Centers ───────────────────────────────────────────────────────────────

async def list_work_centers(db: AsyncSession, skip=0, limit=100, status: Optional[str] = None):
    q = select(WorkCenter)
    if status:
        q = q.where(WorkCenter.status == status)
    q = q.offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_work_center(db: AsyncSession, pk: UUID) -> Optional[WorkCenter]:
    return await _get(db, WorkCenter, pk)

async def get_work_center_by_code(db: AsyncSession, code: str) -> Optional[WorkCenter]:
    r = await db.execute(select(WorkCenter).where(WorkCenter.work_center_id == code))
    return r.scalar_one_or_none()

async def create_work_center(db: AsyncSession, data: WorkCenterCreate) -> WorkCenter:
    obj = WorkCenter(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_work_center(db: AsyncSession, obj: WorkCenter, data: WorkCenterUpdate) -> WorkCenter:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_work_center(db: AsyncSession, obj: WorkCenter) -> None:
    await db.delete(obj)
    await db.flush()


# ── Routing ────────────────────────────────────────────────────────────────────

async def list_routings(db: AsyncSession, skip=0, limit=100, product_id: Optional[UUID] = None):
    q = select(Routing).options(
        selectinload(Routing.steps).selectinload(RoutingStep.work_center)
    )
    if product_id:
        q = q.where(Routing.product_id == product_id)
    q = q.offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_routing(db: AsyncSession, pk: UUID) -> Optional[Routing]:
    r = await db.execute(
        select(Routing)
        .options(selectinload(Routing.steps).selectinload(RoutingStep.work_center))
        .where(Routing.id == pk)
    )
    return r.scalar_one_or_none()

async def create_routing(db: AsyncSession, data: RoutingCreate) -> Routing:
    obj = Routing(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_routing(db: AsyncSession, obj: Routing, data: RoutingUpdate) -> Routing:
    locked = await db.execute(select(Routing).where(Routing.id == obj.id).with_for_update())
    obj = locked.scalar_one_or_none()
    if obj is None:
        raise ValueError("Routing not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def add_routing_step(db: AsyncSession, routing_id: UUID, data: RoutingStepCreate) -> RoutingStep:
    routing_result = await db.execute(
        select(Routing).where(Routing.id == routing_id).with_for_update()
    )
    routing = routing_result.scalar_one_or_none()
    if routing is None:
        raise ValueError("Routing not found")
    assigned_step = await db.execute(
        select(WorkOrder.id)
        .join(RoutingStep, WorkOrder.routing_step_id == RoutingStep.id)
        .where(RoutingStep.routing_id == routing_id)
        .limit(1)
    )
    if assigned_step.scalar_one_or_none() is not None:
        raise ValueError("Routing is already assigned to production orders; create a new routing version to change its steps")
    center = await db.get(WorkCenter, data.work_center_id)
    if center is None:
        raise ValueError("Work center not found")
    if center.status != "active":
        raise ValueError("Routing steps require an active work center")
    step = RoutingStep(routing_id=routing_id, **data.model_dump())
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return step

async def delete_routing_step(db: AsyncSession, step: RoutingStep) -> None:
    await db.execute(select(Routing.id).where(Routing.id == step.routing_id).with_for_update())
    referenced = await db.execute(
        select(WorkOrder.id).where(WorkOrder.routing_step_id == step.id).limit(1)
    )
    if referenced.scalar_one_or_none() is not None:
        raise ValueError("Routing step is used by a production work order and cannot be deleted")
    await db.delete(step)
    await db.flush()

async def delete_routing(db: AsyncSession, obj: Routing) -> None:
    locked = await db.execute(select(Routing).where(Routing.id == obj.id).with_for_update())
    obj = locked.scalar_one_or_none()
    if obj is None:
        raise ValueError("Routing not found")
    referenced = await db.execute(
        select(WorkOrder.id)
        .join(RoutingStep, WorkOrder.routing_step_id == RoutingStep.id)
        .where(RoutingStep.routing_id == obj.id)
        .limit(1)
    )
    if referenced.scalar_one_or_none() is not None:
        raise ValueError("Routing is used by production work orders and cannot be deleted")
    await db.delete(obj)
    await db.flush()


# ── Work Orders ────────────────────────────────────────────────────────────────

async def _lock_work_order_parent(
    db: AsyncSession, production_order_id: UUID
) -> ProductionOrder:
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == production_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    parent = result.scalar_one_or_none()
    if parent is None:
        raise ValueError("Production order not found")
    return parent


async def _lock_work_order_context(
    db: AsyncSession, work_order_id: UUID
) -> tuple[ProductionOrder, WorkOrder]:
    parent_id_result = await db.execute(
        select(WorkOrder.production_order_id).where(WorkOrder.id == work_order_id)
    )
    parent_id = parent_id_result.scalar_one_or_none()
    if parent_id is None:
        raise ValueError("Work order not found")

    # All mutations acquire locks in parent-then-child order so parent state
    # transitions serialize against operation edits and lifecycle changes.
    parent = await _lock_work_order_parent(db, parent_id)
    work_order_result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == work_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    work_order = work_order_result.scalar_one_or_none()
    if work_order is None:
        raise ValueError("Work order not found")
    if work_order.production_order_id != parent.id:
        raise ValueError("Work order changed production order during transition")
    return parent, work_order


def _require_parent_status(
    parent: ProductionOrder,
    allowed: set[ProductionOrderStatus],
    action: str,
    *,
    require_unapproved: bool = False,
) -> None:
    if parent.status not in allowed:
        raise ValueError(
            f"Cannot {action} work orders while production order is {parent.status.value}"
        )
    if require_unapproved and (parent.approved_by is not None or parent.approved_at is not None):
        raise ValueError(f"Cannot {action} work orders after production-order approval")

async def list_work_orders(
    db: AsyncSession, skip=0, limit=100,
    production_order_id: Optional[UUID] = None,
    work_center_id: Optional[UUID] = None,
    status: Optional[str] = None,
    work_order_ids: Optional[list[UUID]] = None,
):
    q = select(WorkOrder).outerjoin(WorkOrder.routing_step).options(
        selectinload(WorkOrder.work_center),
        selectinload(WorkOrder.routing_step).selectinload(RoutingStep.routing),
    )
    if production_order_id:
        q = q.where(WorkOrder.production_order_id == production_order_id)
    if work_center_id:
        q = q.where(WorkOrder.work_center_id == work_center_id)
    if status:
        q = q.where(WorkOrder.status == status)
    if work_order_ids is not None:
        if not work_order_ids:
            return []
        q = q.where(WorkOrder.id.in_(work_order_ids))
    q = q.order_by(
        WorkOrder.production_order_id,
        RoutingStep.step_number.asc().nulls_last(),
        WorkOrder.created_at,
        WorkOrder.id,
    ).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_work_order(db: AsyncSession, pk: UUID) -> Optional[WorkOrder]:
    r = await db.execute(
        select(WorkOrder)
        .options(
            selectinload(WorkOrder.work_center),
            selectinload(WorkOrder.routing_step).selectinload(RoutingStep.routing),
            selectinload(WorkOrder.time_entries),
            selectinload(WorkOrder.labor_logs),
        )
        .where(WorkOrder.id == pk)
    )
    return r.scalar_one_or_none()

async def create_work_order(
    db: AsyncSession, data: WorkOrderCreate, actor_id: UUID
) -> WorkOrder:
    parent = await _lock_work_order_parent(db, data.production_order_id)
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "create", require_unapproved=True)

    existing_result = await db.execute(
        select(WorkOrder)
        .options(selectinload(WorkOrder.routing_step).selectinload(RoutingStep.routing))
        .where(WorkOrder.production_order_id == parent.id)
        .with_for_update()
    )
    existing = list(existing_result.scalars().all())
    routing_step = None
    work_center = await db.get(WorkCenter, data.work_center_id)
    if work_center is None:
        raise ValueError("Work center not found")
    if work_center.status != "active":
        raise ValueError("Work orders require an active work center")
    if data.routing_step_id is not None:
        step_result = await db.execute(
            select(RoutingStep)
            .options(
                selectinload(RoutingStep.routing),
                selectinload(RoutingStep.work_center),
            )
            .where(RoutingStep.id == data.routing_step_id)
        )
        routing_step = step_result.scalar_one_or_none()
        if routing_step is None:
            raise ValueError("Routing step not found")
        locked_routing_result = await db.execute(
            select(Routing)
            .where(Routing.id == routing_step.routing_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        locked_routing = locked_routing_result.scalar_one_or_none()
        if locked_routing is None:
            raise ValueError("Routing not found")
        refreshed_step_result = await db.execute(
            select(RoutingStep)
            .options(selectinload(RoutingStep.work_center))
            .where(RoutingStep.id == data.routing_step_id)
            .execution_options(populate_existing=True)
        )
        routing_step = refreshed_step_result.scalar_one_or_none()
        if routing_step is None:
            raise ValueError("Routing step not found")
        routing_step.routing = locked_routing
        if not locked_routing.is_active:
            raise ValueError("Work orders can only use steps from an active routing")
        if locked_routing.product_id != parent.product_id:
            raise ValueError("Routing product does not match the production order")
        if routing_step.work_center_id != data.work_center_id:
            raise ValueError("Work center must match the selected routing step")
        if routing_step.operation.strip() != data.operation.strip():
            raise ValueError("Operation must match the selected routing step")
        if routing_step.work_center.status != "active":
            raise ValueError("Routing step work center is not active")
        if any(
            row.routing_step_id == routing_step.id
            for row in existing
        ):
            raise ValueError("This routing step already has a work order for the production order")
        existing_routing_ids = {
            row.routing_step.routing_id
            for row in existing
            if row.routing_step is not None
        }
        if existing_routing_ids and existing_routing_ids != {locked_routing.id}:
            raise ValueError("A production order cannot mix operations from different routings")
    elif any(row.routing_step_id is not None for row in existing):
        raise ValueError("A routed production order requires every operation to reference its routing step")

    obj = WorkOrder(
        **data.model_dump(),
        status=WorkOrderStatus.PLANNED,
    )
    if routing_step is not None:
        obj.routing_step = routing_step
    db.add(obj)
    await db.flush()
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=obj.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="CREATED",
        actor_id=actor_id,
        to_status=obj.status,
    )
    await db.refresh(obj)
    return obj


async def generate_work_orders_from_routing(
    db: AsyncSession,
    production_order_id: UUID,
    routing_id: UUID,
    actor_id: UUID,
) -> list[WorkOrder]:
    parent = await _lock_work_order_parent(db, production_order_id)
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "generate", require_unapproved=True)

    routing_result = await db.execute(
        select(Routing)
        .options(
            selectinload(Routing.steps).selectinload(RoutingStep.work_center),
        )
        .where(Routing.id == routing_id)
        .with_for_update()
    )
    routing = routing_result.scalar_one_or_none()
    if routing is None:
        raise ValueError("Routing not found")
    if not routing.is_active:
        raise ValueError("Only an active routing can be assigned to a production order")
    if routing.product_id != parent.product_id:
        raise ValueError("Routing product does not match the production order")
    steps = sorted(routing.steps or [], key=lambda step: step.step_number)
    if not steps:
        raise ValueError("Routing has no operation steps")
    if any(step.work_center is None or step.work_center.status != "active" for step in steps):
        raise ValueError("Every routing step must use an active work center")

    existing_result = await db.execute(
        select(WorkOrder)
        .options(selectinload(WorkOrder.routing_step).selectinload(RoutingStep.routing))
        .where(WorkOrder.production_order_id == parent.id)
        .with_for_update()
    )
    existing = list(existing_result.scalars().all())
    expected_step_ids = {step.id for step in steps}
    existing_step_ids = {
        row.routing_step_id
        for row in existing
        if row.routing_step_id is not None
    }
    if existing:
        if (
            len(existing) == len(steps)
            and existing_step_ids == expected_step_ids
            and all(row.routing_step_id is not None for row in existing)
            and all(row.routing_step.routing_id == routing.id for row in existing)
        ):
            return sorted(existing, key=lambda row: row.routing_step.step_number)
        raise ValueError("Production order already has work orders; routing generation would replace or mix them")

    work_orders: list[WorkOrder] = []
    for step in steps:
        readable_code = f"{parent.order_no}-OP-{step.step_number:03d}"
        if len(readable_code) > 50:
            readable_code = f"WO-{uuid4().hex}"
        work_order = WorkOrder(
            work_order_id=readable_code,
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=step.work_center_id,
            operation=step.operation,
            status=WorkOrderStatus.PLANNED,
            planned_quantity=parent.planned_quantity,
        )
        db.add(work_order)
        await db.flush()
        record_transition(
            db,
            entity_type=WORK_ORDER,
            entity_id=work_order.id,
            parent_entity_type=PRODUCTION_ORDER,
            parent_entity_id=parent.id,
            action="CREATED",
            actor_id=actor_id,
            to_status=work_order.status,
        )
        work_order.routing_step = step
        step.routing = routing
        work_order.work_center = step.work_center
        work_orders.append(work_order)

    await db.flush()
    return work_orders


def _require_milliquantity(value: Decimal, label: str) -> Decimal:
    normalized = Decimal(value)
    if not normalized.is_finite() or normalized <= 0:
        raise ValueError(f"{label} must be a positive finite quantity")
    if normalized != normalized.quantize(Decimal("0.001")):
        raise ValueError(f"{label} must use no more than three decimal places")
    return normalized


async def _reject_work_order_dependents(db: AsyncSession, work_order_ids: list[UUID]) -> None:
    """Refuse transformations while another module has attached operational data."""
    for table in Base.metadata.tables.values():
        if table.name == ProductionWorkOrderGenealogy.__tablename__:
            continue
        for column in table.columns:
            if not any(fk.target_fullname == "work_orders.id" for fk in column.foreign_keys):
                continue
            referenced = await db.execute(
                select(column).select_from(table).where(column.in_(work_order_ids)).limit(1)
            )
            if referenced.scalar_one_or_none() is not None:
                raise ValueError(
                    "Work orders with schedules, assignments, execution records, or other linked data cannot be split or merged"
                )


async def _reject_parent_work_center_schedule(
    db: AsyncSession, parent_id: UUID, work_center_ids: set[UUID]
) -> None:
    scheduled = await db.execute(
        select(ProductionSchedule.id)
        .where(
            ProductionSchedule.production_order_id == parent_id,
            ProductionSchedule.work_center_id.in_(work_center_ids),
        )
        .limit(1)
    )
    if scheduled.scalar_one_or_none() is not None:
        raise ValueError("Scheduled work orders cannot be split or merged; remove the schedule before retrying")


def _require_unstarted_work_order(work_order: WorkOrder) -> None:
    if work_order.status != WorkOrderStatus.PLANNED:
        raise ValueError("Only planned work orders can be split or merged")
    if (
        work_order.actual_quantity not in (None, Decimal("0"))
        or work_order.start_time is not None
        or work_order.end_time is not None
    ):
        raise ValueError("A work order with actual production activity cannot be split or merged")
    if work_order.planned_quantity is None:
        raise ValueError("A work order without a planned quantity cannot be split or merged")
    _require_milliquantity(work_order.planned_quantity, "Work-order planned quantity")


async def _require_current_routing_context(
    db: AsyncSession, parent: ProductionOrder, work_order: WorkOrder
) -> None:
    if work_order.routing_step_id is None:
        center_result = await db.execute(
            select(WorkCenter).where(WorkCenter.id == work_order.work_center_id).with_for_update()
        )
        center = center_result.scalar_one_or_none()
        if center is None or center.status != "active":
            raise ValueError("Work order must use an active work center")
        return
    routing_id_result = await db.execute(
        select(RoutingStep.routing_id).where(RoutingStep.id == work_order.routing_step_id)
    )
    routing_id = routing_id_result.scalar_one_or_none()
    if routing_id is None:
        raise ValueError("Work order routing step not found")
    routing_result = await db.execute(
        select(Routing).where(Routing.id == routing_id).with_for_update()
    )
    routing = routing_result.scalar_one_or_none()
    step_result = await db.execute(
        select(RoutingStep)
        .where(RoutingStep.id == work_order.routing_step_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    step = step_result.scalar_one_or_none()
    if step is None or step.routing_id != routing_id:
        raise ValueError("Work order routing step changed during split/merge; retry from the refreshed order")
    if routing is None or not routing.is_active or routing.product_id != parent.product_id:
        raise ValueError("Work order must reference an active routing for its production-order product")
    center_result = await db.execute(
        select(WorkCenter).where(WorkCenter.id == work_order.work_center_id).with_for_update()
    )
    center = center_result.scalar_one_or_none()
    if (
        center is None
        or center.status != "active"
        or step.work_center_id != work_order.work_center_id
        or step.operation.strip() != work_order.operation.strip()
    ):
        raise ValueError("Work order no longer matches an active routing-step work center and operation")


async def split_work_order(
    db: AsyncSession,
    work_order_id: UUID,
    quantities: list[Decimal],
    actor_id: UUID,
) -> list[WorkOrder]:
    if not 2 <= len(quantities) <= 20:
        raise ValueError("A split must create between 2 and 20 work orders")
    parent, source = await _lock_work_order_context(db, work_order_id)
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "split", require_unapproved=True)
    _require_unstarted_work_order(source)
    await _require_current_routing_context(db, parent, source)
    if Decimal(source.planned_quantity) > Decimal(parent.planned_quantity):
        raise ValueError("A work order cannot exceed its production-order planned quantity")
    normalized = [_require_milliquantity(value, "Split quantity") for value in quantities]
    if sum(normalized, Decimal("0")) != Decimal(source.planned_quantity):
        raise ValueError("Split quantities must exactly equal the source planned quantity")
    await _reject_work_order_dependents(db, [source.id])
    await _reject_parent_work_center_schedule(db, parent.id, {source.work_center_id})

    results: list[WorkOrder] = []
    operation_id = uuid4()
    previous_status = source.status
    source.status = WorkOrderStatus.CANCELLED
    await db.flush()
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=source.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="SPLIT_SOURCE_CANCELLED",
        actor_id=actor_id,
        from_status=previous_status,
        to_status=source.status,
    )

    for quantity in normalized:
        result = WorkOrder(
            work_order_id=f"WO-{uuid4().hex}",
            production_order_id=parent.id,
            routing_step_id=source.routing_step_id,
            work_center_id=source.work_center_id,
            operation=source.operation,
            operator=source.operator,
            status=WorkOrderStatus.PLANNED,
            planned_quantity=quantity,
            planned_start=source.planned_start,
            planned_end=source.planned_end,
            notes=source.notes,
        )
        db.add(result)
        await db.flush()
        record_transition(
            db,
            entity_type=WORK_ORDER,
            entity_id=result.id,
            parent_entity_type=PRODUCTION_ORDER,
            parent_entity_id=parent.id,
            action="SPLIT_RESULT_CREATED",
            actor_id=actor_id,
            to_status=result.status,
        )
        db.add(
            ProductionWorkOrderGenealogy(
                operation_id=operation_id,
                action="SPLIT",
                source_work_order_id=source.id,
                result_work_order_id=result.id,
                transferred_quantity=quantity,
                actor_id=actor_id,
            )
        )
        results.append(result)
    await db.flush()
    return results


async def merge_work_orders(
    db: AsyncSession,
    work_order_ids: list[UUID],
    actor_id: UUID,
) -> WorkOrder:
    if not 2 <= len(work_order_ids) <= 20 or len(set(work_order_ids)) != len(work_order_ids):
        raise ValueError("A merge must contain 2 to 20 distinct work orders")
    parent_ids_result = await db.execute(
        select(WorkOrder.production_order_id)
        .where(WorkOrder.id.in_(work_order_ids))
        .order_by(WorkOrder.production_order_id)
    )
    parent_ids = list(parent_ids_result.scalars().all())
    if len(parent_ids) != len(work_order_ids):
        raise ValueError("One or more work orders were not found")
    if len(set(parent_ids)) != 1:
        raise ValueError("Work orders from different production orders cannot be merged")

    parent = await _lock_work_order_parent(db, parent_ids[0])
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "merge", require_unapproved=True)
    locked_result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id.in_(work_order_ids))
        .order_by(WorkOrder.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    sources = list(locked_result.scalars().all())
    if len(sources) != len(work_order_ids) or any(source.production_order_id != parent.id for source in sources):
        raise ValueError("Work orders changed during merge; refresh and retry")
    for source in sources:
        _require_unstarted_work_order(source)
        await _require_current_routing_context(db, parent, source)

    first = sources[0]
    if any(
        source.routing_step_id != first.routing_step_id
        or source.work_center_id != first.work_center_id
        or source.operation != first.operation
        or source.operator != first.operator
        or source.planned_start != first.planned_start
        or source.planned_end != first.planned_end
        for source in sources[1:]
    ):
        raise ValueError(
            "Merged work orders must share the same routing step, work center, operation, operator, and planned window"
        )

    await _reject_work_order_dependents(db, [source.id for source in sources])
    await _reject_parent_work_center_schedule(
        db, parent.id, {source.work_center_id for source in sources}
    )

    total_quantity = sum((Decimal(source.planned_quantity) for source in sources), Decimal("0"))
    _require_milliquantity(total_quantity, "Merged planned quantity")
    if total_quantity > Decimal(parent.planned_quantity):
        raise ValueError("Merged quantity cannot exceed the production-order planned quantity")
    source_notes = [
        f"{source.work_order_id}: {source.notes}"
        for source in sources
        if source.notes and source.notes.strip()
    ]
    result = WorkOrder(
        work_order_id=f"WO-{uuid4().hex}",
        production_order_id=parent.id,
        routing_step_id=first.routing_step_id,
        work_center_id=first.work_center_id,
        operation=first.operation,
        operator=first.operator,
        status=WorkOrderStatus.PLANNED,
        planned_quantity=total_quantity,
        planned_start=first.planned_start,
        planned_end=first.planned_end,
        notes="\n\n".join(source_notes) or None,
    )
    operation_id = uuid4()
    for source in sources:
        previous_status = source.status
        source.status = WorkOrderStatus.CANCELLED
        record_transition(
            db,
            entity_type=WORK_ORDER,
            entity_id=source.id,
            parent_entity_type=PRODUCTION_ORDER,
            parent_entity_id=parent.id,
            action="MERGE_SOURCE_CANCELLED",
            actor_id=actor_id,
            from_status=previous_status,
            to_status=source.status,
        )
    db.add(result)
    await db.flush()
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=result.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="MERGE_RESULT_CREATED",
        actor_id=actor_id,
        to_status=result.status,
    )
    for source in sources:
        db.add(
            ProductionWorkOrderGenealogy(
                operation_id=operation_id,
                action="MERGE",
                source_work_order_id=source.id,
                result_work_order_id=result.id,
                transferred_quantity=source.planned_quantity,
                actor_id=actor_id,
            )
        )
    await db.flush()
    return result


async def list_work_order_genealogy(
    db: AsyncSession, work_order_id: UUID
) -> list[ProductionWorkOrderGenealogy]:
    rows = await db.execute(
        select(ProductionWorkOrderGenealogy)
        .options(
            selectinload(ProductionWorkOrderGenealogy.source_work_order),
            selectinload(ProductionWorkOrderGenealogy.result_work_order),
        )
        .where(
            or_(
                ProductionWorkOrderGenealogy.source_work_order_id == work_order_id,
                ProductionWorkOrderGenealogy.result_work_order_id == work_order_id,
            )
        )
        .order_by(ProductionWorkOrderGenealogy.created_at, ProductionWorkOrderGenealogy.id)
    )
    return list(rows.scalars().all())

async def update_work_order(db: AsyncSession, obj: WorkOrder, data: WorkOrderUpdate) -> WorkOrder:
    parent, obj = await _lock_work_order_context(db, obj.id)
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "edit", require_unapproved=True)
    if obj.status != WorkOrderStatus.PLANNED:
        raise ValueError(f"Work order in status {obj.status.value} cannot be edited")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_work_order(db: AsyncSession, obj: WorkOrder, actor_id: UUID) -> None:
    parent, obj = await _lock_work_order_context(db, obj.id)
    _require_parent_status(parent, {ProductionOrderStatus.PLANNED}, "delete", require_unapproved=True)
    if obj.status != WorkOrderStatus.PLANNED:
        raise ValueError(f"Work order in status {obj.status.value} cannot be deleted")
    genealogy = await db.execute(
        select(ProductionWorkOrderGenealogy.id)
        .where(
            or_(
                ProductionWorkOrderGenealogy.source_work_order_id == obj.id,
                ProductionWorkOrderGenealogy.result_work_order_id == obj.id,
            )
        )
        .limit(1)
    )
    if genealogy.scalar_one_or_none() is not None:
        raise ValueError("A work order with split/merge lineage cannot be deleted")
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=obj.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="DELETED",
        actor_id=actor_id,
        from_status=obj.status,
    )
    await db.delete(obj)
    await db.flush()


async def start_work_order(
    db: AsyncSession, work_order_id: UUID, actor_id: UUID
) -> WorkOrder:
    parent, work_order = await _lock_work_order_context(db, work_order_id)
    _require_parent_status(parent, {ProductionOrderStatus.IN_PROGRESS}, "start")
    if work_order.status != WorkOrderStatus.PLANNED:
        raise ValueError(f"Cannot start work order in status '{work_order.status.value}'")
    previous_status = work_order.status
    work_order.status = WorkOrderStatus.IN_PROGRESS
    work_order.start_time = datetime.now(timezone.utc)
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=work_order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="STARTED",
        actor_id=actor_id,
        from_status=previous_status,
        to_status=work_order.status,
    )
    await db.flush()
    await db.refresh(work_order)
    return work_order


async def complete_work_order(
    db: AsyncSession,
    work_order_id: UUID,
    actor_id: UUID,
    actual_quantity: Optional[Decimal] = None,
) -> WorkOrder:
    parent, work_order = await _lock_work_order_context(db, work_order_id)
    _require_parent_status(parent, {ProductionOrderStatus.IN_PROGRESS}, "complete")
    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        raise ValueError(f"Cannot complete work order in status '{work_order.status.value}'")
    if actual_quantity is not None and actual_quantity <= 0:
        raise ValueError("actual_quantity must be positive")

    previous_status = work_order.status
    work_order.status = WorkOrderStatus.COMPLETED
    work_order.end_time = datetime.now(timezone.utc)
    if actual_quantity is not None:
        work_order.actual_quantity = actual_quantity
    record_transition(
        db,
        entity_type=WORK_ORDER,
        entity_id=work_order.id,
        parent_entity_type=PRODUCTION_ORDER,
        parent_entity_id=parent.id,
        action="COMPLETED",
        actor_id=actor_id,
        from_status=previous_status,
        to_status=work_order.status,
    )
    await db.flush()
    await db.refresh(work_order)
    return work_order


# ── Shifts ─────────────────────────────────────────────────────────────────────

async def list_shifts(db: AsyncSession, skip=0, limit=100) -> List[Shift]:
    return await _list(db, Shift, skip, limit)

async def get_shift(db: AsyncSession, pk: UUID) -> Optional[Shift]:
    return await _get(db, Shift, pk)

async def create_shift(db: AsyncSession, data: ShiftCreate) -> Shift:
    obj = Shift(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_shift(db: AsyncSession, obj: Shift, data: ShiftUpdate) -> Shift:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_shift(db: AsyncSession, obj: Shift) -> None:
    await db.delete(obj)
    await db.flush()


# ── Production Schedules ───────────────────────────────────────────────────────

async def list_schedules(
    db: AsyncSession, skip=0, limit=100,
    work_center_id: Optional[UUID] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    q = select(ProductionSchedule).options(
        selectinload(ProductionSchedule.work_center),
        selectinload(ProductionSchedule.shift),
    )
    if work_center_id:
        q = q.where(ProductionSchedule.work_center_id == work_center_id)
    if status:
        q = q.where(ProductionSchedule.status == status)
    if date_from:
        q = q.where(ProductionSchedule.start_time >= date_from)
    if date_to:
        q = q.where(ProductionSchedule.end_time <= date_to)
    q = q.order_by(ProductionSchedule.start_time).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_schedule(db: AsyncSession, pk: UUID) -> Optional[ProductionSchedule]:
    return await _get(db, ProductionSchedule, pk)

async def create_schedule(db: AsyncSession, data: ProductionScheduleCreate) -> ProductionSchedule:
    obj = ProductionSchedule(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_schedule(db: AsyncSession, obj: ProductionSchedule, data: ProductionScheduleUpdate) -> ProductionSchedule:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_schedule(db: AsyncSession, obj: ProductionSchedule) -> None:
    await db.delete(obj)
    await db.flush()

async def detect_schedule_conflicts(db: AsyncSession, work_center_id: UUID, start: datetime, end: datetime, exclude_id: Optional[UUID] = None):
    """Return schedules that overlap the given window for the same work center."""
    q = select(ProductionSchedule).where(
        and_(
            ProductionSchedule.work_center_id == work_center_id,
            ProductionSchedule.start_time < end,
            ProductionSchedule.end_time > start,
        )
    )
    if exclude_id:
        q = q.where(ProductionSchedule.id != exclude_id)
    r = await db.execute(q)
    return list(r.scalars().all())


# ── Time Tracking ──────────────────────────────────────────────────────────────

async def list_time_tracking(
    db: AsyncSession, skip=0, limit=100,
    work_order_id: Optional[UUID] = None,
):
    q = select(TimeTracking)
    if work_order_id:
        q = q.where(TimeTracking.work_order_id == work_order_id)
    q = q.order_by(TimeTracking.actual_start.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_time_tracking(db: AsyncSession, pk: UUID) -> Optional[TimeTracking]:
    return await _get(db, TimeTracking, pk)

async def create_time_tracking(db: AsyncSession, data: TimeTrackingCreate) -> TimeTracking:
    d = data.model_dump()
    obj = TimeTracking(**d)
    if obj.actual_end and obj.actual_start:
        delta = obj.actual_end - obj.actual_start
        obj.duration_actual_min = int(delta.total_seconds() / 60)
        if obj.duration_planned_min:
            obj.efficiency_pct = round(Decimal(obj.duration_planned_min) / Decimal(obj.duration_actual_min) * 100, 2)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_time_tracking(db: AsyncSession, obj: TimeTracking, data: TimeTrackingUpdate) -> TimeTracking:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    if obj.actual_end and obj.actual_start:
        delta = obj.actual_end - obj.actual_start
        obj.duration_actual_min = int(delta.total_seconds() / 60)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_time_tracking(db: AsyncSession, obj: TimeTracking) -> None:
    await db.delete(obj)
    await db.flush()


# ── Downtime Events ────────────────────────────────────────────────────────────

async def list_downtime_events(
    db: AsyncSession, skip=0, limit=100,
    work_center_id: Optional[UUID] = None,
    category: Optional[str] = None,
):
    q = select(DowntimeEvent).options(selectinload(DowntimeEvent.work_center))
    if work_center_id:
        q = q.where(DowntimeEvent.work_center_id == work_center_id)
    if category:
        q = q.where(DowntimeEvent.category == category)
    q = q.order_by(DowntimeEvent.start_time.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_downtime_event(db: AsyncSession, pk: UUID) -> Optional[DowntimeEvent]:
    return await _get(db, DowntimeEvent, pk)

async def create_downtime_event(db: AsyncSession, data: DowntimeEventCreate) -> DowntimeEvent:
    d = data.model_dump()
    obj = DowntimeEvent(**d)
    if obj.end_time and obj.start_time:
        delta = obj.end_time - obj.start_time
        obj.duration_min = max(0, int(delta.total_seconds() / 60))
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_downtime_event(db: AsyncSession, obj: DowntimeEvent, data: DowntimeEventUpdate) -> DowntimeEvent:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    if obj.end_time and obj.start_time:
        delta = obj.end_time - obj.start_time
        obj.duration_min = max(0, int(delta.total_seconds() / 60))
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_downtime_event(db: AsyncSession, obj: DowntimeEvent) -> None:
    await db.delete(obj)
    await db.flush()


# ── QC Inspections ─────────────────────────────────────────────────────────────

async def list_qc_inspections(
    db: AsyncSession, skip=0, limit=100,
    production_order_id: Optional[UUID] = None,
    status: Optional[str] = None,
    inspection_type: Optional[str] = None,
):
    q = select(AdvQCInspection).options(selectinload(AdvQCInspection.results))
    if production_order_id:
        q = q.where(AdvQCInspection.production_order_id == production_order_id)
    if status:
        q = q.where(AdvQCInspection.status == status)
    if inspection_type:
        q = q.where(AdvQCInspection.inspection_type == inspection_type)
    q = q.order_by(AdvQCInspection.created_at.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_qc_inspection(db: AsyncSession, pk: UUID) -> Optional[AdvQCInspection]:
    r = await db.execute(
        select(AdvQCInspection).options(selectinload(AdvQCInspection.results)).where(AdvQCInspection.id == pk)
    )
    return r.scalar_one_or_none()

async def create_qc_inspection(db: AsyncSession, data: AdvQCInspectionCreate) -> AdvQCInspection:
    d = data.model_dump(exclude={"results"})
    obj = AdvQCInspection(**d)
    db.add(obj)
    await db.flush()
    for res_data in data.results:
        res = AdvQCResult(inspection_id=obj.id, **res_data.model_dump())
        db.add(res)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_qc_inspection(db: AsyncSession, obj: AdvQCInspection, data: AdvQCInspectionUpdate) -> AdvQCInspection:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_qc_inspection(db: AsyncSession, obj: AdvQCInspection) -> None:
    await db.delete(obj)
    await db.flush()


# ── Waste Records ──────────────────────────────────────────────────────────────

ANOMALY_LOSS_THRESHOLD = Decimal("5.0")   # flag if loss > 5 %

async def list_waste_records(
    db: AsyncSession, skip=0, limit=100,
    production_order_id: Optional[UUID] = None,
    is_anomaly: Optional[bool] = None,
):
    q = select(WasteRecord)
    if production_order_id:
        q = q.where(WasteRecord.production_order_id == production_order_id)
    if is_anomaly is not None:
        q = q.where(WasteRecord.is_anomaly == is_anomaly)
    q = q.order_by(WasteRecord.created_at.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_waste_record(db: AsyncSession, pk: UUID) -> Optional[WasteRecord]:
    return await _get(db, WasteRecord, pk)

def _weighted_recipe_loss_pct(rows) -> Optional[Decimal]:
    pairs = [(Decimal(quantity), Decimal(loss_pct)) for quantity, loss_pct in rows]
    if not pairs or any(not qty.is_finite() or not pct.is_finite() or qty < 0 or pct < 0 for qty, pct in pairs):
        return None
    total_qty = sum((qty for qty, _ in pairs), Decimal("0"))
    if total_qty <= 0:
        return None
    weighted_loss = sum((qty * pct for qty, pct in pairs), Decimal("0"))
    return (weighted_loss / total_qty).quantize(Decimal("0.001"))


async def _recipe_standard_loss_pct(db: AsyncSession, obj: WasteRecord) -> Optional[Decimal]:
    material_id = obj.material_id
    if material_id is None and obj.material_code:
        material = await db.execute(select(Material.id).where(Material.code == obj.material_code.strip()))
        material_id = material.scalar_one_or_none()
        if material_id is not None:
            obj.material_id = material_id
            obj.material_code = obj.material_code.strip()
    if material_id is None or not obj.uom or not obj.production_order_id:
        return None
    order = await db.get(ProductionOrder, obj.production_order_id)
    if order is None or order.recipe_id is None:
        return None
    rows = await db.execute(
        select(RecipeItem.quantity, RecipeItem.loss_percentage).where(
            RecipeItem.recipe_id == order.recipe_id,
            RecipeItem.material_id == material_id,
            func.upper(func.trim(RecipeItem.unit)) == obj.uom.strip().upper(),
        )
    )
    return _weighted_recipe_loss_pct(rows.all())


async def create_waste_record(db: AsyncSession, data: WasteRecordCreate) -> WasteRecord:
    d = data.model_dump()
    obj = WasteRecord(**d)
    obj.standard_loss_pct = await _recipe_standard_loss_pct(db, obj)
    if obj.expected_qty and obj.expected_qty > 0:
        obj.loss_pct = round(obj.loss_qty / obj.expected_qty * 100, 3)
        obj.is_anomaly = obj.loss_pct > ANOMALY_LOSS_THRESHOLD
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_waste_record(db: AsyncSession, obj: WasteRecord, data: WasteRecordUpdate) -> WasteRecord:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    if obj.expected_qty and obj.expected_qty > 0:
        obj.loss_qty = obj.expected_qty - obj.actual_qty
        obj.loss_pct = round(obj.loss_qty / obj.expected_qty * 100, 3)
        obj.is_anomaly = obj.loss_pct > ANOMALY_LOSS_THRESHOLD
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_waste_record(db: AsyncSession, obj: WasteRecord) -> None:
    await db.delete(obj)
    await db.flush()


# ── Batch Lots ─────────────────────────────────────────────────────────────────

async def list_batch_lots(
    db: AsyncSession, skip=0, limit=100,
    production_order_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    q = select(BatchLot)
    if production_order_id:
        q = q.where(BatchLot.production_order_id == production_order_id)
    if status:
        q = q.where(BatchLot.status == status)
    q = q.order_by(BatchLot.created_at.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_batch_lot(db: AsyncSession, pk: UUID) -> Optional[BatchLot]:
    return await _get(db, BatchLot, pk)

async def create_batch_lot(db: AsyncSession, data: BatchLotCreate) -> BatchLot:
    obj = BatchLot(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_batch_lot(db: AsyncSession, obj: BatchLot, data: BatchLotUpdate) -> BatchLot:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_batch_lot(db: AsyncSession, obj: BatchLot) -> None:
    await db.delete(obj)
    await db.flush()


# ── Labor Logs ─────────────────────────────────────────────────────────────────

async def list_labor_logs(
    db: AsyncSession, skip=0, limit=100,
    work_order_id: Optional[UUID] = None,
):
    q = select(LaborLog)
    if work_order_id:
        q = q.where(LaborLog.work_order_id == work_order_id)
    q = q.order_by(LaborLog.created_at.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_labor_log(db: AsyncSession, pk: UUID) -> Optional[LaborLog]:
    return await _get(db, LaborLog, pk)

async def create_labor_log(db: AsyncSession, data: LaborLogCreate) -> LaborLog:
    obj = LaborLog(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_labor_log(db: AsyncSession, obj: LaborLog, data: LaborLogUpdate) -> LaborLog:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_labor_log(db: AsyncSession, obj: LaborLog) -> None:
    await db.delete(obj)
    await db.flush()


# ── OEE Records ────────────────────────────────────────────────────────────────

OEE_LOW_THRESHOLD     = Decimal("0.65")
DOWNTIME_HIGH_RATIO   = Decimal("0.20")

def _compute_oee(
    planned_time: int,
    actual_time: Optional[int],
    downtime: int,
    total_units: int,
    good_units: int,
    ideal_cycle_sec: Optional[Decimal],
) -> dict:
    result: dict = {}
    if not planned_time:
        return result
    net_time = (actual_time or planned_time) - downtime
    availability = Decimal(net_time) / Decimal(planned_time)
    result["availability"] = round(min(availability, Decimal("1.0")), 4)

    if ideal_cycle_sec and net_time > 0:
        ideal_output = Decimal(net_time * 60) / ideal_cycle_sec
        perf = Decimal(total_units) / ideal_output if ideal_output > 0 else Decimal(0)
        result["performance"] = round(min(perf, Decimal("1.0")), 4)
    else:
        result["performance"] = None

    if total_units and total_units > 0:
        quality = Decimal(good_units) / Decimal(total_units)
        result["quality"] = round(min(quality, Decimal("1.0")), 4)
    else:
        result["quality"] = None

    if result.get("performance") and result.get("quality"):
        result["oee_score"] = round(
            result["availability"] * result["performance"] * result["quality"], 4
        )
    else:
        result["oee_score"] = None

    return result


async def list_oee_records(
    db: AsyncSession, skip=0, limit=100,
    work_center_id: Optional[UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    q = select(OEERecord).options(
        selectinload(OEERecord.work_center),
        selectinload(OEERecord.shift),
    )
    if work_center_id:
        q = q.where(OEERecord.work_center_id == work_center_id)
    if date_from:
        q = q.where(OEERecord.record_date >= date_from)
    if date_to:
        q = q.where(OEERecord.record_date <= date_to)
    q = q.order_by(OEERecord.record_date.desc()).offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_oee_record(db: AsyncSession, pk: UUID) -> Optional[OEERecord]:
    r = await db.execute(
        select(OEERecord)
        .options(selectinload(OEERecord.work_center), selectinload(OEERecord.shift))
        .where(OEERecord.id == pk)
    )
    return r.scalar_one_or_none()

async def create_oee_record(db: AsyncSession, data: OEERecordCreate) -> OEERecord:
    d = data.model_dump()
    obj = OEERecord(**d)
    # Auto-compute if not provided
    if obj.availability is None:
        kpis = _compute_oee(
            obj.planned_production_time_min,
            obj.actual_production_time_min,
            obj.downtime_min or 0,
            obj.total_units_produced or 0,
            obj.good_units_produced or 0,
            obj.ideal_cycle_time_sec,
        )
        for k, v in kpis.items():
            setattr(obj, k, v)
    # Anomaly flags
    if obj.oee_score is not None:
        obj.is_low_oee = obj.oee_score < OEE_LOW_THRESHOLD
    if obj.planned_production_time_min and obj.downtime_min:
        ratio = Decimal(obj.downtime_min) / Decimal(obj.planned_production_time_min)
        obj.is_high_downtime = ratio > DOWNTIME_HIGH_RATIO
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_oee_record(db: AsyncSession, obj: OEERecord, data: OEERecordUpdate) -> OEERecord:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    kpis = _compute_oee(
        obj.planned_production_time_min,
        obj.actual_production_time_min,
        obj.downtime_min or 0,
        obj.total_units_produced or 0,
        obj.good_units_produced or 0,
        obj.ideal_cycle_time_sec,
    )
    for k, v in kpis.items():
        setattr(obj, k, v)
    if obj.oee_score is not None:
        obj.is_low_oee = obj.oee_score < OEE_LOW_THRESHOLD
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_oee_record(db: AsyncSession, obj: OEERecord) -> None:
    await db.delete(obj)
    await db.flush()
