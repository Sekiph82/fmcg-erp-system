"""
CRUD for Advanced Production Module.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_advanced import (
    WorkCenter, Routing, RoutingStep, WorkOrder,
    Shift, ProductionSchedule, TimeTracking, DowntimeEvent,
    AdvQCInspection, AdvQCResult, WasteRecord, BatchLot, LaborLog, OEERecord,
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
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def add_routing_step(db: AsyncSession, routing_id: UUID, data: RoutingStepCreate) -> RoutingStep:
    step = RoutingStep(routing_id=routing_id, **data.model_dump())
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return step

async def delete_routing_step(db: AsyncSession, step: RoutingStep) -> None:
    await db.delete(step)
    await db.flush()

async def delete_routing(db: AsyncSession, obj: Routing) -> None:
    await db.delete(obj)
    await db.flush()


# ── Work Orders ────────────────────────────────────────────────────────────────

async def list_work_orders(
    db: AsyncSession, skip=0, limit=100,
    production_order_id: Optional[UUID] = None,
    work_center_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    q = select(WorkOrder).options(
        selectinload(WorkOrder.work_center),
    )
    if production_order_id:
        q = q.where(WorkOrder.production_order_id == production_order_id)
    if work_center_id:
        q = q.where(WorkOrder.work_center_id == work_center_id)
    if status:
        q = q.where(WorkOrder.status == status)
    q = q.offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())

async def get_work_order(db: AsyncSession, pk: UUID) -> Optional[WorkOrder]:
    r = await db.execute(
        select(WorkOrder)
        .options(
            selectinload(WorkOrder.work_center),
            selectinload(WorkOrder.time_entries),
            selectinload(WorkOrder.labor_logs),
        )
        .where(WorkOrder.id == pk)
    )
    return r.scalar_one_or_none()

async def create_work_order(db: AsyncSession, data: WorkOrderCreate) -> WorkOrder:
    obj = WorkOrder(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_work_order(db: AsyncSession, obj: WorkOrder, data: WorkOrderUpdate) -> WorkOrder:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_work_order(db: AsyncSession, obj: WorkOrder) -> None:
    await db.delete(obj)
    await db.flush()


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

async def create_waste_record(db: AsyncSession, data: WasteRecordCreate) -> WasteRecord:
    d = data.model_dump()
    obj = WasteRecord(**d)
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
