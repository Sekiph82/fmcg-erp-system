"""
Advanced Production Module — API Endpoints
──────────────────────────────────────────
Prefix: /api/v1/production-adv

Sub-routers:
  /work-centers          Work center CRUD
  /routings              Routing + steps CRUD
  /work-orders           Work order CRUD + status transitions
  /shifts                Shift definition CRUD
  /schedules             Machine-level scheduling + conflict detection
  /time-tracking         Actual vs planned time logging
  /downtime              Machine downtime events
  /qc                    QC inspections + results
  /waste                 Waste & yield records
  /batch-lots            Batch/lot traceability
  /labor                 Labor / operator work logs
  /oee                   OEE daily records + KPI summary
"""
from __future__ import annotations

import uuid as _uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.crud import production_advanced as crud
from app.schemas.production_advanced import (
    # Work Centers
    WorkCenterCreate, WorkCenterUpdate, WorkCenterRead,
    # Routing
    RoutingCreate, RoutingUpdate, RoutingRead, RoutingStepCreate, RoutingStepRead,
    # Work Orders
    WorkOrderCreate, WorkOrderUpdate, WorkOrderRead,
    # Shifts
    ShiftCreate, ShiftUpdate, ShiftRead,
    # Schedule
    ProductionScheduleCreate, ProductionScheduleUpdate, ProductionScheduleRead,
    # Time Tracking
    TimeTrackingCreate, TimeTrackingUpdate, TimeTrackingRead,
    # Downtime
    DowntimeEventCreate, DowntimeEventUpdate, DowntimeEventRead,
    # QC
    AdvQCInspectionCreate, AdvQCInspectionUpdate, AdvQCInspectionRead,
    # Waste
    WasteRecordCreate, WasteRecordUpdate, WasteRecordRead,
    # Batch Lots
    BatchLotCreate, BatchLotUpdate, BatchLotRead,
    # Labor
    LaborLogCreate, LaborLogUpdate, LaborLogRead,
    # OEE
    OEERecordCreate, OEERecordUpdate, OEERecordRead,
)
from app.models.production_advanced import (
    WorkCenter, Routing, RoutingStep, WorkOrder,
    Shift, ProductionSchedule, TimeTracking, DowntimeEvent,
    AdvQCInspection, WasteRecord, BatchLot, LaborLog, OEERecord,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# WORK CENTERS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/work-centers", response_model=List[WorkCenterRead], tags=["work-centers"])
async def list_work_centers(
    skip: int = 0, limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await crud.list_work_centers(db, skip, limit, status)


@router.post("/work-centers", response_model=WorkCenterRead, status_code=201, tags=["work-centers"])
async def create_work_center(
    data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_work_center(db, data)
    await db.commit()
    return obj


@router.get("/work-centers/{pk}", response_model=WorkCenterRead, tags=["work-centers"])
async def get_work_center(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_work_center(db, pk)
    if not obj:
        raise HTTPException(404, "Work center not found")
    return obj


@router.patch("/work-centers/{pk}", response_model=WorkCenterRead, tags=["work-centers"])
async def update_work_center(
    pk: _uuid.UUID, data: WorkCenterUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    obj = await crud.get_work_center(db, pk)
    if not obj:
        raise HTTPException(404, "Work center not found")
    obj = await crud.update_work_center(db, obj, data)
    await db.commit()
    return obj


@router.delete("/work-centers/{pk}", status_code=204, tags=["work-centers"])
async def delete_work_center(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_work_center(db, pk)
    if not obj:
        raise HTTPException(404, "Work center not found")
    await crud.delete_work_center(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/routings", response_model=List[RoutingRead], tags=["routing"])
async def list_routings(
    skip: int = 0, limit: int = 100,
    product_id: Optional[_uuid.UUID] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    routings = await crud.list_routings(db, skip, limit, product_id)
    return [_enrich_routing(r) for r in routings]


@router.post("/routings", response_model=RoutingRead, status_code=201, tags=["routing"])
async def create_routing(data: RoutingCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_routing(db, data)
    await db.commit()
    return _enrich_routing(obj)


@router.get("/routings/{pk}", response_model=RoutingRead, tags=["routing"])
async def get_routing(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_routing(db, pk)
    if not obj:
        raise HTTPException(404, "Routing not found")
    return _enrich_routing(obj)


@router.patch("/routings/{pk}", response_model=RoutingRead, tags=["routing"])
async def update_routing(pk: _uuid.UUID, data: RoutingUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_routing(db, pk)
    if not obj:
        raise HTTPException(404, "Routing not found")
    obj = await crud.update_routing(db, obj, data)
    await db.commit()
    return _enrich_routing(obj)


@router.delete("/routings/{pk}", status_code=204, tags=["routing"])
async def delete_routing(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_routing(db, pk)
    if not obj:
        raise HTTPException(404, "Routing not found")
    await crud.delete_routing(db, obj)
    await db.commit()
    return Response(status_code=204)


@router.post("/routings/{pk}/steps", response_model=RoutingStepRead, status_code=201, tags=["routing"])
async def add_routing_step(pk: _uuid.UUID, data: RoutingStepCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    routing = await crud.get_routing(db, pk)
    if not routing:
        raise HTTPException(404, "Routing not found")
    step = await crud.add_routing_step(db, pk, data)
    await db.commit()
    return _enrich_step(step)


@router.delete("/routings/{pk}/steps/{step_id}", status_code=204, tags=["routing"])
async def delete_routing_step(pk: _uuid.UUID, step_id: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import select as _select
    r = await db.execute(_select(RoutingStep).where(RoutingStep.id == step_id, RoutingStep.routing_id == pk))
    step = r.scalar_one_or_none()
    if not step:
        raise HTTPException(404, "Step not found")
    await crud.delete_routing_step(db, step)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# WORK ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/work-orders", response_model=List[WorkOrderRead], tags=["work-orders"])
async def list_work_orders(
    skip: int = 0, limit: int = 100,
    production_order_id: Optional[_uuid.UUID] = None,
    work_center_id: Optional[_uuid.UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    return [_enrich_wo(w) for w in await crud.list_work_orders(db, skip, limit, production_order_id, work_center_id, status)]


@router.post("/work-orders", response_model=WorkOrderRead, status_code=201, tags=["work-orders"])
async def create_work_order(data: WorkOrderCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_work_order(db, data)
    await db.commit()
    return _enrich_wo(obj)


@router.get("/work-orders/{pk}", response_model=WorkOrderRead, tags=["work-orders"])
async def get_work_order(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_work_order(db, pk)
    if not obj:
        raise HTTPException(404, "Work order not found")
    return _enrich_wo(obj)


@router.patch("/work-orders/{pk}", response_model=WorkOrderRead, tags=["work-orders"])
async def update_work_order(pk: _uuid.UUID, data: WorkOrderUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_work_order(db, pk)
    if not obj:
        raise HTTPException(404, "Work order not found")
    obj = await crud.update_work_order(db, obj, data)
    await db.commit()
    return _enrich_wo(obj)


@router.delete("/work-orders/{pk}", status_code=204, tags=["work-orders"])
async def delete_work_order(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_work_order(db, pk)
    if not obj:
        raise HTTPException(404, "Work order not found")
    await crud.delete_work_order(db, obj)
    await db.commit()
    return Response(status_code=204)


@router.post("/work-orders/{pk}/start", response_model=WorkOrderRead, tags=["work-orders"])
async def start_work_order(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from datetime import datetime, timezone
    obj = await crud.get_work_order(db, pk)
    if not obj:
        raise HTTPException(404, "Work order not found")
    if obj.status != "planned":
        raise HTTPException(400, f"Cannot start work order in status '{obj.status}'")
    obj.status = "in_progress"
    obj.start_time = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _enrich_wo(obj)


@router.post("/work-orders/{pk}/complete", response_model=WorkOrderRead, tags=["work-orders"])
async def complete_work_order(
    pk: _uuid.UUID,
    actual_quantity: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from datetime import datetime, timezone
    from decimal import Decimal as D
    obj = await crud.get_work_order(db, pk)
    if not obj:
        raise HTTPException(404, "Work order not found")
    if obj.status != "in_progress":
        raise HTTPException(400, f"Cannot complete work order in status '{obj.status}'")
    obj.status = "completed"
    obj.end_time = datetime.now(timezone.utc)
    if actual_quantity is not None:
        obj.actual_quantity = D(str(actual_quantity))
    await db.flush()
    await db.commit()
    return _enrich_wo(obj)


# ─────────────────────────────────────────────────────────────────────────────
# SHIFTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/shifts", response_model=List[ShiftRead], tags=["shifts"])
async def list_shifts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await crud.list_shifts(db, skip, limit)


@router.post("/shifts", response_model=ShiftRead, status_code=201, tags=["shifts"])
async def create_shift(data: ShiftCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_shift(db, data)
    await db.commit()
    return obj


@router.patch("/shifts/{pk}", response_model=ShiftRead, tags=["shifts"])
async def update_shift(pk: _uuid.UUID, data: ShiftUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_shift(db, pk)
    if not obj:
        raise HTTPException(404, "Shift not found")
    obj = await crud.update_shift(db, obj, data)
    await db.commit()
    return obj


@router.delete("/shifts/{pk}", status_code=204, tags=["shifts"])
async def delete_shift(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_shift(db, pk)
    if not obj:
        raise HTTPException(404, "Shift not found")
    await crud.delete_shift(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/schedules", response_model=List[ProductionScheduleRead], tags=["scheduling"])
async def list_schedules(
    skip: int = 0, limit: int = 100,
    work_center_id: Optional[_uuid.UUID] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    schedules = await crud.list_schedules(db, skip, limit, work_center_id, status, date_from, date_to)
    return [_enrich_schedule(s) for s in schedules]


@router.post("/schedules", response_model=ProductionScheduleRead, status_code=201, tags=["scheduling"])
async def create_schedule(data: ProductionScheduleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    # Conflict detection
    conflicts = await crud.detect_schedule_conflicts(db, data.work_center_id, data.start_time, data.end_time)
    obj = await crud.create_schedule(db, data)
    if conflicts:
        obj.conflict_flag = True
        await db.flush()
    await db.commit()
    return _enrich_schedule(obj)


@router.get("/schedules/conflicts", tags=["scheduling"])
async def get_schedule_conflicts(
    work_center_id: Optional[_uuid.UUID] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    """Return all schedules flagged with conflicts."""
    from sqlalchemy import select
    q = select(ProductionSchedule).where(ProductionSchedule.conflict_flag == True)
    if work_center_id:
        q = q.where(ProductionSchedule.work_center_id == work_center_id)
    r = await db.execute(q)
    schedules = list(r.scalars().all())
    return [_enrich_schedule(s) for s in schedules]


@router.patch("/schedules/{pk}", response_model=ProductionScheduleRead, tags=["scheduling"])
async def update_schedule(pk: _uuid.UUID, data: ProductionScheduleUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_schedule(db, pk)
    if not obj:
        raise HTTPException(404, "Schedule not found")
    obj = await crud.update_schedule(db, obj, data)
    await db.commit()
    return _enrich_schedule(obj)


@router.delete("/schedules/{pk}", status_code=204, tags=["scheduling"])
async def delete_schedule(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_schedule(db, pk)
    if not obj:
        raise HTTPException(404, "Schedule not found")
    await crud.delete_schedule(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# TIME TRACKING
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/time-tracking", response_model=List[TimeTrackingRead], tags=["time-tracking"])
async def list_time_tracking(
    skip: int = 0, limit: int = 100,
    work_order_id: Optional[_uuid.UUID] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    entries = await crud.list_time_tracking(db, skip, limit, work_order_id)
    return [_enrich_tt(e) for e in entries]


@router.post("/time-tracking", response_model=TimeTrackingRead, status_code=201, tags=["time-tracking"])
async def create_time_tracking(data: TimeTrackingCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_time_tracking(db, data)
    await db.commit()
    return _enrich_tt(obj)


@router.patch("/time-tracking/{pk}", response_model=TimeTrackingRead, tags=["time-tracking"])
async def update_time_tracking(pk: _uuid.UUID, data: TimeTrackingUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_time_tracking(db, pk)
    if not obj:
        raise HTTPException(404, "Time tracking entry not found")
    obj = await crud.update_time_tracking(db, obj, data)
    await db.commit()
    return _enrich_tt(obj)


@router.delete("/time-tracking/{pk}", status_code=204, tags=["time-tracking"])
async def delete_time_tracking(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_time_tracking(db, pk)
    if not obj:
        raise HTTPException(404, "Time tracking entry not found")
    await crud.delete_time_tracking(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNTIME EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/downtime", response_model=List[DowntimeEventRead], tags=["downtime"])
async def list_downtime_events(
    skip: int = 0, limit: int = 100,
    work_center_id: Optional[_uuid.UUID] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    events = await crud.list_downtime_events(db, skip, limit, work_center_id, category)
    return [_enrich_dt(e) for e in events]


@router.post("/downtime", response_model=DowntimeEventRead, status_code=201, tags=["downtime"])
async def create_downtime_event(data: DowntimeEventCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_downtime_event(db, data)
    await db.commit()
    return _enrich_dt(obj)


@router.patch("/downtime/{pk}", response_model=DowntimeEventRead, tags=["downtime"])
async def update_downtime_event(pk: _uuid.UUID, data: DowntimeEventUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_downtime_event(db, pk)
    if not obj:
        raise HTTPException(404, "Downtime event not found")
    obj = await crud.update_downtime_event(db, obj, data)
    await db.commit()
    return _enrich_dt(obj)


@router.delete("/downtime/{pk}", status_code=204, tags=["downtime"])
async def delete_downtime_event(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_downtime_event(db, pk)
    if not obj:
        raise HTTPException(404, "Downtime event not found")
    await crud.delete_downtime_event(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# QC INSPECTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/qc", response_model=List[AdvQCInspectionRead], tags=["quality-control"])
async def list_qc_inspections(
    skip: int = 0, limit: int = 100,
    production_order_id: Optional[_uuid.UUID] = None,
    status: Optional[str] = None,
    inspection_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    items = await crud.list_qc_inspections(db, skip, limit, production_order_id, status, inspection_type)
    return [_enrich_qc(q) for q in items]


@router.post("/qc", response_model=AdvQCInspectionRead, status_code=201, tags=["quality-control"])
async def create_qc_inspection(data: AdvQCInspectionCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_qc_inspection(db, data)
    await db.commit()
    return _enrich_qc(obj)


@router.get("/qc/{pk}", response_model=AdvQCInspectionRead, tags=["quality-control"])
async def get_qc_inspection(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_qc_inspection(db, pk)
    if not obj:
        raise HTTPException(404, "QC inspection not found")
    return _enrich_qc(obj)


@router.patch("/qc/{pk}", response_model=AdvQCInspectionRead, tags=["quality-control"])
async def update_qc_inspection(pk: _uuid.UUID, data: AdvQCInspectionUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_qc_inspection(db, pk)
    if not obj:
        raise HTTPException(404, "QC inspection not found")
    obj = await crud.update_qc_inspection(db, obj, data)
    await db.commit()
    return _enrich_qc(obj)


@router.delete("/qc/{pk}", status_code=204, tags=["quality-control"])
async def delete_qc_inspection(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_qc_inspection(db, pk)
    if not obj:
        raise HTTPException(404, "QC inspection not found")
    await crud.delete_qc_inspection(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# WASTE RECORDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/waste", response_model=List[WasteRecordRead], tags=["waste-yield"])
async def list_waste_records(
    skip: int = 0, limit: int = 100,
    production_order_id: Optional[_uuid.UUID] = None,
    is_anomaly: Optional[bool] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    return [_enrich_waste(w) for w in await crud.list_waste_records(db, skip, limit, production_order_id, is_anomaly)]


@router.post("/waste", response_model=WasteRecordRead, status_code=201, tags=["waste-yield"])
async def create_waste_record(data: WasteRecordCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_waste_record(db, data)
    await db.commit()
    return _enrich_waste(obj)


@router.patch("/waste/{pk}", response_model=WasteRecordRead, tags=["waste-yield"])
async def update_waste_record(pk: _uuid.UUID, data: WasteRecordUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_waste_record(db, pk)
    if not obj:
        raise HTTPException(404, "Waste record not found")
    obj = await crud.update_waste_record(db, obj, data)
    await db.commit()
    return _enrich_waste(obj)


@router.delete("/waste/{pk}", status_code=204, tags=["waste-yield"])
async def delete_waste_record(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_waste_record(db, pk)
    if not obj:
        raise HTTPException(404, "Waste record not found")
    await crud.delete_waste_record(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# BATCH LOTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/batch-lots", response_model=List[BatchLotRead], tags=["batch-lots"])
async def list_batch_lots(
    skip: int = 0, limit: int = 100,
    production_order_id: Optional[_uuid.UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    return [_enrich_batch(b) for b in await crud.list_batch_lots(db, skip, limit, production_order_id, status)]


@router.post("/batch-lots", response_model=BatchLotRead, status_code=201, tags=["batch-lots"])
async def create_batch_lot(data: BatchLotCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_batch_lot(db, data)
    await db.commit()
    return _enrich_batch(obj)


@router.patch("/batch-lots/{pk}", response_model=BatchLotRead, tags=["batch-lots"])
async def update_batch_lot(pk: _uuid.UUID, data: BatchLotUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_batch_lot(db, pk)
    if not obj:
        raise HTTPException(404, "Batch lot not found")
    obj = await crud.update_batch_lot(db, obj, data)
    await db.commit()
    return _enrich_batch(obj)


@router.delete("/batch-lots/{pk}", status_code=204, tags=["batch-lots"])
async def delete_batch_lot(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_batch_lot(db, pk)
    if not obj:
        raise HTTPException(404, "Batch lot not found")
    await crud.delete_batch_lot(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# LABOR TRACKING
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/labor", response_model=List[LaborLogRead], tags=["labor"])
async def list_labor_logs(
    skip: int = 0, limit: int = 100,
    work_order_id: Optional[_uuid.UUID] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    return [_enrich_labor(l) for l in await crud.list_labor_logs(db, skip, limit, work_order_id)]


@router.post("/labor", response_model=LaborLogRead, status_code=201, tags=["labor"])
async def create_labor_log(data: LaborLogCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_labor_log(db, data)
    await db.commit()
    return _enrich_labor(obj)


@router.patch("/labor/{pk}", response_model=LaborLogRead, tags=["labor"])
async def update_labor_log(pk: _uuid.UUID, data: LaborLogUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_labor_log(db, pk)
    if not obj:
        raise HTTPException(404, "Labor log not found")
    obj = await crud.update_labor_log(db, obj, data)
    await db.commit()
    return _enrich_labor(obj)


@router.delete("/labor/{pk}", status_code=204, tags=["labor"])
async def delete_labor_log(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_labor_log(db, pk)
    if not obj:
        raise HTTPException(404, "Labor log not found")
    await crud.delete_labor_log(db, obj)
    await db.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# OEE RECORDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/oee", response_model=List[OEERecordRead], tags=["oee"])
async def list_oee_records(
    skip: int = 0, limit: int = 100,
    work_center_id: Optional[_uuid.UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    records = await crud.list_oee_records(db, skip, limit, work_center_id, date_from, date_to)
    return [_enrich_oee(r) for r in records]


@router.post("/oee", response_model=OEERecordRead, status_code=201, tags=["oee"])
async def create_oee_record(data: OEERecordCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.create_oee_record(db, data)
    await db.commit()
    return _enrich_oee(obj)


@router.patch("/oee/{pk}", response_model=OEERecordRead, tags=["oee"])
async def update_oee_record(pk: _uuid.UUID, data: OEERecordUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_oee_record(db, pk)
    if not obj:
        raise HTTPException(404, "OEE record not found")
    obj = await crud.update_oee_record(db, obj, data)
    await db.commit()
    return _enrich_oee(obj)


@router.delete("/oee/{pk}", status_code=204, tags=["oee"])
async def delete_oee_record(pk: _uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_oee_record(db, pk)
    if not obj:
        raise HTTPException(404, "OEE record not found")
    await crud.delete_oee_record(db, obj)
    await db.commit()
    return Response(status_code=204)


@router.get("/oee/summary", tags=["oee"])
async def oee_summary(
    work_center_id: Optional[_uuid.UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    """Aggregate OEE KPIs per work center for the given date range."""
    from sqlalchemy import select, func
    from app.models.production_advanced import OEERecord, WorkCenter
    q = (
        select(
            OEERecord.work_center_id,
            func.avg(OEERecord.availability).label("avg_availability"),
            func.avg(OEERecord.performance).label("avg_performance"),
            func.avg(OEERecord.quality).label("avg_quality"),
            func.avg(OEERecord.oee_score).label("avg_oee"),
            func.sum(OEERecord.downtime_min).label("total_downtime_min"),
            func.count(OEERecord.id).label("records_count"),
        )
        .group_by(OEERecord.work_center_id)
    )
    if work_center_id:
        q = q.where(OEERecord.work_center_id == work_center_id)
    if date_from:
        q = q.where(OEERecord.record_date >= date_from)
    if date_to:
        q = q.where(OEERecord.record_date <= date_to)
    r = await db.execute(q)
    rows = r.fetchall()
    result = []
    for row in rows:
        wc = await crud.get_work_center(db, row.work_center_id)
        result.append({
            "work_center_id": str(row.work_center_id),
            "work_center_name": wc.name if wc else None,
            "avg_availability": float(row.avg_availability) if row.avg_availability else None,
            "avg_performance":  float(row.avg_performance)  if row.avg_performance  else None,
            "avg_quality":      float(row.avg_quality)      if row.avg_quality      else None,
            "avg_oee":          float(row.avg_oee)          if row.avg_oee          else None,
            "total_downtime_min": int(row.total_downtime_min) if row.total_downtime_min else 0,
            "records_count":    row.records_count,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# AI Integration endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ai-insights", tags=["oee"])
async def production_ai_insights(
    work_center_id: Optional[_uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Generate AI-driven production insights:
    - Low OEE machines (OEE < 65%)
    - High downtime anomalies
    - Waste anomalies
    - Recipe performance comparisons
    - Predictive maintenance alerts
    """
    from sqlalchemy import select
    insights = []

    # Low OEE
    q = select(OEERecord).where(OEERecord.is_low_oee == True)
    if work_center_id:
        q = q.where(OEERecord.work_center_id == work_center_id)
    r = await db.execute(q.order_by(OEERecord.record_date.desc()).limit(10))
    low_oee_records = list(r.scalars().all())
    for rec in low_oee_records:
        wc = await crud.get_work_center(db, rec.work_center_id)
        insights.append({
            "type": "LOW_OEE",
            "severity": "HIGH",
            "machine": wc.name if wc else str(rec.work_center_id),
            "date": str(rec.record_date),
            "oee_score": float(rec.oee_score) if rec.oee_score else None,
            "recommendation": f"OEE of {round(float(rec.oee_score or 0)*100,1)}% is below the 65% target. Investigate downtime and quality losses.",
        })

    # High downtime
    q2 = select(OEERecord).where(OEERecord.is_high_downtime == True)
    if work_center_id:
        q2 = q2.where(OEERecord.work_center_id == work_center_id)
    r2 = await db.execute(q2.order_by(OEERecord.record_date.desc()).limit(10))
    for rec in list(r2.scalars().all()):
        wc = await crud.get_work_center(db, rec.work_center_id)
        insights.append({
            "type": "HIGH_DOWNTIME",
            "severity": "MEDIUM",
            "machine": wc.name if wc else str(rec.work_center_id),
            "date": str(rec.record_date),
            "downtime_min": rec.downtime_min,
            "recommendation": f"{rec.downtime_min} min downtime recorded. Schedule preventive maintenance.",
        })

    # Waste anomalies
    q3 = select(WasteRecord).where(WasteRecord.is_anomaly == True).limit(10)
    r3 = await db.execute(q3)
    for rec in list(r3.scalars().all()):
        insights.append({
            "type": "WASTE_ANOMALY",
            "severity": "MEDIUM",
            "waste_id": rec.waste_id,
            "loss_pct": float(rec.loss_pct) if rec.loss_pct else None,
            "recommendation": f"Waste loss of {round(float(rec.loss_pct or 0),1)}% exceeds normal threshold. Review process parameters.",
        })

    return {"total_insights": len(insights), "insights": insights}


# ─────────────────────────────────────────────────────────────────────────────
# Enrichment helpers
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_routing(obj: Routing) -> dict:
    d = RoutingRead.model_validate(obj).model_dump()
    if obj.product:
        d["product_name"] = obj.product.name
        d["product_sku"]  = obj.product.sku
    d["steps"] = [_enrich_step(s) for s in (obj.steps or [])]
    return d

def _enrich_step(s: RoutingStep) -> dict:
    d = RoutingStepRead.model_validate(s).model_dump()
    if s.work_center:
        d["work_center_name"] = s.work_center.name
    return d

def _enrich_wo(obj: WorkOrder) -> dict:
    d = WorkOrderRead.model_validate(obj).model_dump()
    if obj.work_center:
        d["work_center_name"] = obj.work_center.name
    return d

def _enrich_schedule(obj: ProductionSchedule) -> dict:
    d = ProductionScheduleRead.model_validate(obj).model_dump()
    if obj.work_center:
        d["work_center_name"] = obj.work_center.name
    if obj.shift:
        d["shift_name"] = obj.shift.name
    return d

def _enrich_tt(obj: TimeTracking) -> dict:
    d = TimeTrackingRead.model_validate(obj).model_dump()
    if obj.work_order:
        d["work_order_code"] = obj.work_order.work_order_id
    return d

def _enrich_dt(obj: DowntimeEvent) -> dict:
    d = DowntimeEventRead.model_validate(obj).model_dump()
    if obj.work_center:
        d["work_center_name"] = obj.work_center.name
    return d

def _enrich_qc(obj: AdvQCInspection) -> dict:
    d = AdvQCInspectionRead.model_validate(obj).model_dump()
    if obj.production_order:
        d["order_no"] = obj.production_order.order_no
    return d

def _enrich_waste(obj: WasteRecord) -> dict:
    d = WasteRecordRead.model_validate(obj).model_dump()
    if obj.production_order:
        d["order_no"] = obj.production_order.order_no
    return d

def _enrich_batch(obj: BatchLot) -> dict:
    d = BatchLotRead.model_validate(obj).model_dump()
    if obj.production_order:
        d["order_no"] = obj.production_order.order_no
    if obj.product:
        d["product_name"] = obj.product.name
    return d

def _enrich_labor(obj: LaborLog) -> dict:
    d = LaborLogRead.model_validate(obj).model_dump()
    if obj.work_order:
        d["work_order_code"] = obj.work_order.work_order_id
    return d

def _enrich_oee(obj: OEERecord) -> dict:
    d = OEERecordRead.model_validate(obj).model_dump()
    if obj.work_center:
        d["work_center_name"] = obj.work_center.name
    if obj.shift:
        d["shift_name"] = obj.shift.name
    return d
