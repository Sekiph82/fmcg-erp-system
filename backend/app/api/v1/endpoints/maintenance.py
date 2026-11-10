from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.models.user import User
from app.models.production_advanced import ProductionSchedule, ScheduleStatus, WorkCenter
from app.models.maintenance import (
    Asset, AssetStatus, PMPlan, PMStatus, PMWorkOrder, BreakdownRecord, BreakdownStatus, BreakdownSeverity,
    MaintenancePredictionRisk, MaintenancePredictionStatus,
)
import app.crud.maintenance as crud
import app.services.maintenance_service as svc
from app.services.downtime_reason_service import list_downtime_reason_codes, validate_downtime_reason_code
from app.schemas.maintenance import (
    DowntimeReasonCodeRead,
    AssetCreate, AssetUpdate, AssetRead,
    PMPlanCreate, PMPlanUpdate, PMPlanRead,
    PMWorkOrderCreate, PMWorkOrderUpdate, PMWorkOrderRead,
    BreakdownCreate, BreakdownUpdate, BreakdownRead,
    SparePartCreate, SparePartUpdate, SparePartRead,
    PMPlanSparePartRequirementsUpdate, PMPlanSparePartRequirementsReport,
    SparePartUsageCreate, SparePartUsageRead,
    MaintenancePredictionRead, MaintenancePredictionReview,
    MtbfMttrRow, DowntimeByMachineRow, OverduePMRow,
    PMWindowScheduleImpact, PMWindowScheduleImpactReport, PMWindowScheduleConflict,
    MaintenanceDowntimeCapacityImpact, MaintenanceDowntimeCapacityReport, MaintenanceScheduleOverlap,
    BreakdownPriorityAssessment, BreakdownPriorityEscalationReport,
)

router = APIRouter()


def _union_minutes(intervals: list[tuple[datetime, datetime]]) -> float:
    merged: list[list[datetime]] = []
    for left, right in sorted(intervals, key=lambda interval: interval[0]):
        if right <= left:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    seconds = sum((right - left).total_seconds() for left, right in merged)
    return round(seconds / 60, 2)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _asset_read(a) -> AssetRead:
    return AssetRead(
        id=str(a.id),
        asset_no=a.asset_no,
        name=a.name,
        description=a.description,
        asset_type=a.asset_type,
        line=a.line,
        serial_no=a.serial_no,
        manufacturer=a.manufacturer,
        model=a.model,
        install_date=a.install_date,
        warranty_expiry=a.warranty_expiry,
        location=a.location,
        work_center_id=str(a.work_center_id) if a.work_center_id else None,
        status=a.status,
        notes=a.notes,
        created_at=a.created_at,
    )


def _plan_read(p) -> PMPlanRead:
    return PMPlanRead(
        id=str(p.id),
        asset_id=str(p.asset_id),
        asset_name=p.asset.name if p.asset else None,
        asset_no=p.asset.asset_no if p.asset else None,
        name=p.name,
        description=p.description,
        frequency=p.frequency,
        interval_days=p.interval_days,
        estimated_duration_minutes=p.estimated_duration_minutes,
        is_active=p.is_active,
        checklist=p.checklist,
        assigned_to=p.assigned_to,
        last_completed_date=p.last_completed_date,
        next_due_date=p.next_due_date,
        created_at=p.created_at,
    )


def _wo_read(wo) -> PMWorkOrderRead:
    plan = wo.plan if hasattr(wo, "plan") and wo.plan else None
    return PMWorkOrderRead(
        id=str(wo.id),
        wo_no=wo.wo_no,
        plan_id=str(wo.plan_id),
        plan_name=plan.name if plan else None,
        asset_id=str(plan.asset_id) if plan else None,
        asset_name=plan.asset.name if plan and plan.asset else None,
        scheduled_date=wo.scheduled_date,
        window_start=wo.window_start,
        window_end=wo.window_end,
        work_center_id=(str(plan.asset.work_center_id) if plan and plan.asset and plan.asset.work_center_id else None),
        status=wo.status,
        started_at=wo.started_at,
        completed_at=wo.completed_at,
        actual_duration_minutes=wo.actual_duration_minutes,
        technician=wo.technician,
        checklist_notes=wo.checklist_notes,
        created_at=wo.created_at,
    )


def _bd_read(bd) -> BreakdownRead:
    return BreakdownRead(
        id=str(bd.id),
        breakdown_no=bd.breakdown_no,
        asset_id=str(bd.asset_id),
        asset_name=bd.asset.name if bd.asset else None,
        asset_no=bd.asset.asset_no if bd.asset else None,
        production_order_id=str(bd.production_order_id) if bd.production_order_id else None,
        start_time=bd.start_time,
        end_time=bd.end_time,
        downtime_minutes=bd.downtime_minutes,
        reason=bd.reason,
        root_cause=bd.root_cause,
        severity=bd.severity,
        status=bd.status,
        corrective_action=bd.corrective_action,
        created_at=bd.created_at,
    )


def _sp_read(sp) -> SparePartRead:
    return SparePartRead(
        id=str(sp.id),
        part_no=sp.part_no,
        name=sp.name,
        description=sp.description,
        unit=sp.unit,
        material_id=str(sp.material_id) if sp.material_id else None,
        current_stock=float(sp.current_stock),
        reorder_level=float(sp.reorder_level) if sp.reorder_level else None,
        unit_cost=float(sp.unit_cost) if sp.unit_cost else None,
        supplier=sp.supplier,
        lead_time_days=sp.lead_time_days,
        is_active=sp.is_active,
        created_at=sp.created_at,
    )


def _usage_read(u) -> SparePartUsageRead:
    return SparePartUsageRead(
        id=str(u.id),
        spare_part_id=str(u.spare_part_id),
        spare_part_name=u.spare_part.name if u.spare_part else None,
        asset_id=str(u.asset_id),
        asset_name=u.asset.name if u.asset else None,
        breakdown_id=str(u.breakdown_id) if u.breakdown_id else None,
        pm_work_order_id=str(u.pm_work_order_id) if u.pm_work_order_id else None,
        quantity_used=float(u.quantity_used),
        unit_cost=float(u.unit_cost) if u.unit_cost else None,
        notes=u.notes,
        created_at=u.created_at,
    )


def _prediction_read(p) -> MaintenancePredictionRead:
    return MaintenancePredictionRead(
        id=str(p.id),
        asset_id=str(p.asset_id) if p.asset_id else None,
        asset_no=p.asset.asset_no if p.asset else None,
        asset_name=p.asset.name if p.asset else None,
        machine_id=p.machine_id,
        machine_name=p.machine_name,
        predicted_failure_date=p.predicted_failure_date,
        confidence=float(p.confidence),
        risk_level=p.risk_level,
        failure_mode=p.failure_mode,
        recommended_action=p.recommended_action,
        evidence_summary=p.evidence_summary,
        source_metrics=p.source_metrics,
        status=p.status,
        generated_at=p.generated_at,
        reviewed_by=p.reviewed_by,
        reviewed_at=p.reviewed_at,
        review_notes=p.review_notes,
        work_order_id=str(p.work_order_id) if p.work_order_id else None,
        work_order_created_by_id=str(p.work_order_created_by_id) if p.work_order_created_by_id else None,
        work_order_created_at=p.work_order_created_at,
        created_at=p.created_at,
    )


# ── Assets ─────────────────────────────────────────────────────────────────────

@router.get("/assets/", response_model=List[AssetRead])
async def list_assets(
    status: Optional[AssetStatus] = None,
    line: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    assets = await crud.list_assets(db, status=status, line=line)
    return [_asset_read(a) for a in assets]


@router.post("/assets/", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "create")),
):
    data = body.model_dump()
    if data.get("work_center_id"):
        try:
            data["work_center_id"] = uuid.UUID(data["work_center_id"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="work_center_id must be a UUID") from exc
        if not await db.get(WorkCenter, data["work_center_id"]):
            raise HTTPException(status_code=404, detail="Work center not found")
    asset = await crud.create_asset(db, data)
    await db.commit()
    return _asset_read(asset)


@router.get("/assets/{asset_id}", response_model=AssetRead)
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    asset = await crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_read(asset)


@router.patch("/assets/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "edit")),
):
    asset = await crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    data = body.model_dump(exclude_unset=True)
    if "work_center_id" in data:
        if data["work_center_id"]:
            try:
                data["work_center_id"] = uuid.UUID(data["work_center_id"])
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="work_center_id must be a UUID") from exc
            if not await db.get(WorkCenter, data["work_center_id"]):
                raise HTTPException(status_code=404, detail="Work center not found")
        else:
            data["work_center_id"] = None
    asset = await crud.update_asset(db, asset, data)
    await db.commit()
    return _asset_read(asset)


# ── PM Plans ───────────────────────────────────────────────────────────────────

@router.get("/pm-plans/", response_model=List[PMPlanRead])
async def list_pm_plans(
    asset_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    plans = await crud.list_pm_plans(db, asset_id=asset_id, active_only=active_only)
    return [_plan_read(p) for p in plans]


@router.post("/pm-plans/", response_model=PMPlanRead, status_code=status.HTTP_201_CREATED)
async def create_pm_plan(
    body: PMPlanCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "create")),
):
    data = body.model_dump()
    data["asset_id"] = uuid.UUID(data["asset_id"])
    plan = await crud.create_pm_plan(db, data)
    await db.commit()
    await db.refresh(plan)
    plan = await crud.get_pm_plan(db, plan.id)
    return _plan_read(plan)


@router.patch("/pm-plans/{plan_id}", response_model=PMPlanRead)
async def update_pm_plan(
    plan_id: uuid.UUID,
    body: PMPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "edit")),
):
    plan = await crud.get_pm_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="PM Plan not found")
    plan = await crud.update_pm_plan(db, plan, body.model_dump(exclude_none=True))
    await db.commit()
    plan = await crud.get_pm_plan(db, plan_id)
    return _plan_read(plan)


@router.get("/pm-plans/{plan_id}/spare-parts", response_model=PMPlanSparePartRequirementsReport)
async def get_pm_plan_spare_parts(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    if await db.get(PMPlan, plan_id) is None:
        raise HTTPException(status_code=404, detail="PM Plan not found")
    requirements = await crud.get_plan_spare_part_requirements(db, plan_id)
    return PMPlanSparePartRequirementsReport(
        plan_id=str(plan_id),
        requirements=requirements,
        data_notes=[
            "Only spare parts explicitly configured for this PM plan are required; no default demand is invented.",
            "Available quantity is current stock minus reservations for active PM work orders.",
            "The report is a live snapshot; scheduling rechecks and reserves stock transactionally.",
        ],
    )


@router.put("/pm-plans/{plan_id}/spare-parts", response_model=PMPlanSparePartRequirementsReport)
async def replace_pm_plan_spare_parts(
    plan_id: uuid.UUID,
    body: PMPlanSparePartRequirementsUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "edit")),
):
    try:
        requirements = await crud.replace_plan_spare_part_requirements(
            db, plan_id, [item.model_dump() for item in body.items]
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.SparePartAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    return PMPlanSparePartRequirementsReport(
        plan_id=str(plan_id),
        requirements=requirements,
        data_notes=[
            "Only spare parts explicitly configured for this PM plan are required; no default demand is invented.",
            "Available quantity is current stock minus reservations for active PM work orders.",
            "Changing plan requirements affects future work orders; existing reservations remain as snapshots.",
        ],
    )


# ── PM Work Orders ─────────────────────────────────────────────────────────────

@router.get("/work-orders/", response_model=List[PMWorkOrderRead])
async def list_work_orders(
    plan_id: Optional[uuid.UUID] = None,
    status: Optional[PMStatus] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    wos = await crud.list_work_orders(db, plan_id=plan_id, status=status)
    return [_wo_read(wo) for wo in wos]


@router.get("/work-orders/schedule-impact", response_model=PMWindowScheduleImpactReport)
async def work_order_schedule_impact(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _maintenance=Depends(require_permission("maintenance", "view")),
    _production=Depends(require_permission("production", "view")),
):
    """Read-only comparison of explicit PM windows with production schedule windows."""
    today = date.today()
    start_date = date_from or (today - timedelta(days=30))
    end_date = date_to or (today + timedelta(days=90))
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from")
    window_start_utc = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    window_end_utc = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    result = await db.execute(
        select(PMWorkOrder, PMPlan, Asset)
        .join(PMPlan, PMWorkOrder.plan_id == PMPlan.id)
        .join(Asset, PMPlan.asset_id == Asset.id)
        .where(
            or_(
                and_(
                    PMWorkOrder.scheduled_date >= start_date,
                    PMWorkOrder.scheduled_date <= end_date,
                ),
                and_(
                    PMWorkOrder.window_start.is_not(None),
                    PMWorkOrder.window_start < window_end_utc,
                    PMWorkOrder.window_end > window_start_utc,
                ),
            ),
            PMWorkOrder.status.in_([PMStatus.PENDING, PMStatus.IN_PROGRESS, PMStatus.OVERDUE]),
        )
        .order_by(PMWorkOrder.scheduled_date, PMWorkOrder.wo_no)
    )
    rows = result.all()
    linked_work_centers = {asset.work_center_id for _, _, asset in rows if asset.work_center_id}
    timed_windows = [
        (work_order.window_start, work_order.window_end)
        for work_order, _, asset in rows
        if asset.work_center_id and work_order.window_start and work_order.window_end
    ]
    schedules_by_center: dict[uuid.UUID, list[ProductionSchedule]] = {}
    if linked_work_centers and timed_windows:
        earliest_window = min(start for start, _ in timed_windows)
        latest_window = max(end for _, end in timed_windows)
        schedules_result = await db.execute(
            select(ProductionSchedule).where(
                ProductionSchedule.work_center_id.in_(linked_work_centers),
                ProductionSchedule.start_time < latest_window,
                ProductionSchedule.end_time > earliest_window,
                ProductionSchedule.status.in_([
                    ScheduleStatus.PLANNED,
                    ScheduleStatus.CONFIRMED,
                    ScheduleStatus.IN_PROGRESS,
                ]),
            )
        )
        for schedule in schedules_result.scalars().all():
            schedules_by_center.setdefault(schedule.work_center_id, []).append(schedule)

    windows = []
    for work_order, plan, asset in rows:
        unavailable_reason = None
        conflicts = []
        if not asset.work_center_id:
            unavailable_reason = "Asset has no linked production work center"
        elif not work_order.window_start or not work_order.window_end:
            unavailable_reason = "PM work order has no explicit time window"
        else:
            for schedule in schedules_by_center.get(asset.work_center_id, []):
                if schedule.start_time < work_order.window_end and schedule.end_time > work_order.window_start:
                    conflicts.append(PMWindowScheduleConflict(
                        schedule_id=str(schedule.id),
                        production_order_id=str(schedule.production_order_id),
                        work_center_id=str(schedule.work_center_id),
                        start_time=schedule.start_time,
                        end_time=schedule.end_time,
                        status=schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
                    ))
        windows.append(PMWindowScheduleImpact(
            pm_work_order_id=str(work_order.id),
            pm_work_order_no=work_order.wo_no,
            pm_status=work_order.status,
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            work_center_id=str(asset.work_center_id) if asset.work_center_id else None,
            window_start=work_order.window_start,
            window_end=work_order.window_end,
            conflicts=conflicts,
            unavailable_reason=unavailable_reason,
        ))
    return PMWindowScheduleImpactReport(
        date_from=start_date,
        date_to=end_date,
        windows=windows,
        data_notes=[
            "Only explicit PM time windows and linked work centers are compared.",
            "The UTC date range includes matching scheduled dates and PM windows intersecting the range.",
            "Reported overlaps are advisory; schedules are not changed or blocked.",
        ],
    )


@router.get("/reports/downtime-capacity-impact", response_model=MaintenanceDowntimeCapacityReport)
async def downtime_capacity_impact(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _maintenance=Depends(require_permission("maintenance", "view")),
    _production=Depends(require_permission("production", "view")),
):
    """Report maintenance intervals that overlap scheduled production time; never reschedules."""
    as_of = datetime.now(timezone.utc)
    today = as_of.date()
    start_date = date_from or (today - timedelta(days=30))
    end_date = date_to or (today + timedelta(days=90))
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from")
    period_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    period_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    pm_result = await db.execute(
        select(PMWorkOrder, PMPlan, Asset)
        .join(PMPlan, PMWorkOrder.plan_id == PMPlan.id)
        .join(Asset, PMPlan.asset_id == Asset.id)
        .where(
            PMWorkOrder.status.in_([PMStatus.PENDING, PMStatus.IN_PROGRESS, PMStatus.OVERDUE]),
            PMWorkOrder.window_start.is_not(None),
            PMWorkOrder.window_end.is_not(None),
            PMWorkOrder.window_start < period_end,
            PMWorkOrder.window_end > period_start,
        )
        .order_by(PMWorkOrder.window_start, PMWorkOrder.wo_no)
    )
    pm_rows = pm_result.all()

    breakdown_result = await db.execute(
        select(BreakdownRecord, Asset)
        .join(Asset, BreakdownRecord.asset_id == Asset.id)
        .where(
            BreakdownRecord.start_time < period_end,
            or_(BreakdownRecord.end_time.is_(None), BreakdownRecord.end_time > period_start),
        )
        .order_by(BreakdownRecord.start_time, BreakdownRecord.breakdown_no)
    )
    breakdown_rows = breakdown_result.all()
    work_center_ids = {asset.work_center_id for _, _, asset in pm_rows if asset.work_center_id}
    work_center_ids.update(asset.work_center_id for _, asset in breakdown_rows if asset.work_center_id)

    schedules_by_center: dict[uuid.UUID, list[ProductionSchedule]] = {}
    if work_center_ids:
        schedule_result = await db.execute(
            select(ProductionSchedule).where(
                ProductionSchedule.work_center_id.in_(work_center_ids),
                ProductionSchedule.start_time < period_end,
                ProductionSchedule.end_time > period_start,
                ProductionSchedule.status.in_([
                    ScheduleStatus.PLANNED,
                    ScheduleStatus.CONFIRMED,
                    ScheduleStatus.IN_PROGRESS,
                ]),
            )
        )
        for schedule in schedule_result.scalars().all():
            schedules_by_center.setdefault(schedule.work_center_id, []).append(schedule)
    invalid_schedule_centers = {
        center_id
        for center_id, schedules in schedules_by_center.items()
        if any(
            schedule.start_time.tzinfo is None
            or schedule.end_time.tzinfo is None
            or schedule.end_time <= schedule.start_time
            for schedule in schedules
        )
    }

    impacts: list[MaintenanceDowntimeCapacityImpact] = []
    all_impacted_intervals: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}

    def build_impact(
        *, source_type: str, source_id: uuid.UUID, source_number: str, status_value: str,
        asset: Asset, started_at: datetime, ended_at: Optional[datetime],
    ) -> None:
        ongoing = ended_at is None and status_value in {BreakdownStatus.OPEN.value, BreakdownStatus.IN_REPAIR.value}
        observed_through = min(as_of, period_end) if ongoing else None
        unavailable_reason = None
        effective_end = observed_through if ongoing else ended_at
        if not asset.work_center_id:
            unavailable_reason = "Asset has no linked production work center"
        elif source_type == "BREAKDOWN" and ended_at is None and not ongoing:
            unavailable_reason = "Resolved breakdown has no recorded end time"
        elif started_at.tzinfo is None or (effective_end is not None and effective_end.tzinfo is None):
            unavailable_reason = "Maintenance interval is missing timezone information"
        elif asset.work_center_id in invalid_schedule_centers:
            unavailable_reason = "Production schedule interval is invalid or missing timezone information"
        elif effective_end is not None and effective_end <= started_at:
            unavailable_reason = "Maintenance interval end is not after its start"

        overlaps: list[MaintenanceScheduleOverlap] = []
        affected_orders: set[str] = set()
        impacted_intervals: list[tuple[datetime, datetime]] = []
        if not unavailable_reason and effective_end is not None:
            for schedule in schedules_by_center.get(asset.work_center_id, []):
                if schedule.start_time.tzinfo is None or schedule.end_time.tzinfo is None:
                    continue
                overlap_start = max(started_at, schedule.start_time, period_start)
                overlap_end = min(effective_end, schedule.end_time, period_end)
                if overlap_end <= overlap_start:
                    continue
                overlap_minutes = round((overlap_end - overlap_start).total_seconds() / 60, 2)
                overlaps.append(MaintenanceScheduleOverlap(
                    schedule_id=str(schedule.id),
                    production_order_id=str(schedule.production_order_id),
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    overlap_minutes=overlap_minutes,
                ))
                affected_orders.add(str(schedule.production_order_id))
                impacted_intervals.append((overlap_start, overlap_end))
            all_impacted_intervals.setdefault(asset.work_center_id, []).extend(impacted_intervals)

        impacts.append(MaintenanceDowntimeCapacityImpact(
            source_type=source_type,
            source_id=str(source_id),
            source_number=source_number,
            status=status_value,
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            work_center_id=str(asset.work_center_id) if asset.work_center_id else None,
            start_time=started_at,
            end_time=ended_at,
            observed_through=observed_through,
            ongoing=ongoing,
            schedule_minutes_at_risk=_union_minutes(impacted_intervals),
            affected_production_order_ids=sorted(affected_orders),
            overlaps=overlaps,
            unavailable_reason=unavailable_reason,
        ))

    for work_order, _plan, asset in pm_rows:
        build_impact(
            source_type="PREVENTIVE_MAINTENANCE",
            source_id=work_order.id,
            source_number=work_order.wo_no,
            status_value=work_order.status.value,
            asset=asset,
            started_at=work_order.window_start,
            ended_at=work_order.window_end,
        )
    for breakdown, asset in breakdown_rows:
        breakdown_status = breakdown.status.value if hasattr(breakdown.status, "value") else str(breakdown.status)
        build_impact(
            source_type="BREAKDOWN",
            source_id=breakdown.id,
            source_number=breakdown.breakdown_no,
            status_value=breakdown_status,
            asset=asset,
            started_at=breakdown.start_time,
            ended_at=breakdown.end_time,
        )

    impacts.sort(key=lambda impact: (
        impact.start_time.replace(tzinfo=timezone.utc)
        if impact.start_time.tzinfo is None
        else impact.start_time.astimezone(timezone.utc),
        impact.source_type,
        impact.source_number,
    ))
    total_at_risk = sum(_union_minutes(intervals) for intervals in all_impacted_intervals.values())
    return MaintenanceDowntimeCapacityReport(
        date_from=start_date,
        date_to=end_date,
        as_of=as_of,
        impacts=impacts,
        total_schedule_minutes_at_risk=round(total_at_risk, 2),
        data_notes=[
            "Capacity impact is measured as scheduled production minutes overlapping maintenance intervals; no lost-unit rate is inferred.",
            "The total deduplicates overlapping maintenance intervals within a work center.",
            "Open breakdowns are observed only through the report timestamp; no future repair duration is assumed.",
            "Only explicit asset/work-center mappings and active production schedules are included.",
            "The report is advisory and does not alter production schedules or ResourceCalendar rows.",
        ],
    )


@router.post("/work-orders/", response_model=PMWorkOrderRead, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    body: PMWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "create")),
):
    count_res = await db.execute(select(func.count()).select_from(__import__("app.models.maintenance", fromlist=["PMWorkOrder"]).PMWorkOrder))
    count = count_res.scalar() or 0
    data = body.model_dump()
    data["plan_id"] = uuid.UUID(data["plan_id"])
    try:
        wo = await crud.create_work_order(db, data, svc.next_wo_no(count))
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.SparePartAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    await db.commit()
    wo = await crud.get_work_order(db, wo.id)
    return _wo_read(wo)


@router.post("/work-orders/{wo_id}/complete", response_model=PMWorkOrderRead)
async def complete_work_order(
    wo_id: uuid.UUID,
    body: PMWorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("maintenance", "edit")),
):
    wo = await crud.get_work_order(db, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    wo = await crud.complete_work_order(db, wo, body.model_dump(exclude_none=True), current_user.id)
    await db.commit()
    wo = await crud.get_work_order(db, wo_id)
    return _wo_read(wo)


# ── Breakdowns ─────────────────────────────────────────────────────────────────

@router.get("/reports/priority-escalation", response_model=BreakdownPriorityEscalationReport)
async def breakdown_priority_escalation(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    as_of = datetime.now(timezone.utc)
    result = await db.execute(
        select(BreakdownRecord)
        .where(BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR]))
        .order_by(BreakdownRecord.start_time, BreakdownRecord.breakdown_no)
    )
    assessments = [
        BreakdownPriorityAssessment(**svc.assess_breakdown_priority(record, as_of))
        for record in result.scalars().all()
    ]
    return BreakdownPriorityEscalationReport(
        as_of=as_of,
        policy_version=svc.BREAKDOWN_ESCALATION_POLICY_VERSION,
        assessments=assessments,
        data_notes=[
            "Virtual demo defaults: CRITICAL/P1 immediate, HIGH/P2 4 hours, MEDIUM/P3 24 hours, LOW/P4 72 hours.",
            "These are transparent software defaults, not owner-approved factory SLAs or real staffing assignments.",
            "The endpoint is read-only and sends no alert, assignment, or external notification.",
            "Escalation age is measured from the recorded breakdown start time; incomplete timestamps are flagged.",
        ],
    )


@router.get("/breakdowns/", response_model=List[BreakdownRead])
async def list_breakdowns(
    asset_id: Optional[uuid.UUID] = None,
    status: Optional[BreakdownStatus] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    bds = await crud.list_breakdowns(db, asset_id=asset_id, status=status)
    return [_bd_read(bd) for bd in bds]


@router.get("/downtime-reason-codes", response_model=List[DowntimeReasonCodeRead])
async def get_downtime_reason_codes(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    """Return active reason categories and selectable leaf codes."""
    return await list_downtime_reason_codes(db)


@router.post("/breakdowns/", response_model=BreakdownRead, status_code=status.HTTP_201_CREATED)
async def create_breakdown(
    body: BreakdownCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("maintenance", "create")),
):
    from app.models.maintenance import BreakdownRecord
    count_res = await db.execute(select(func.count()).select_from(BreakdownRecord))
    count = count_res.scalar() or 0
    data = body.model_dump()
    data["reason_code"] = await validate_downtime_reason_code(db, data.get("reason_code"))
    data["asset_id"] = uuid.UUID(data["asset_id"])
    if data.get("production_order_id"):
        data["production_order_id"] = uuid.UUID(data["production_order_id"])
    bd = await crud.create_breakdown(db, data, current_user.id, svc.next_bd_no(count))
    await db.commit()
    bd = await crud.get_breakdown(db, bd.id)
    return _bd_read(bd)


@router.get("/breakdowns/{bd_id}", response_model=BreakdownRead)
async def get_breakdown(
    bd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    bd = await crud.get_breakdown(db, bd_id)
    if not bd:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return _bd_read(bd)


@router.patch("/breakdowns/{bd_id}/resolve", response_model=BreakdownRead)
async def resolve_breakdown(
    bd_id: uuid.UUID,
    body: BreakdownUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("maintenance", "edit")),
):
    bd = await crud.get_breakdown(db, bd_id)
    if not bd:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    update_data = body.model_dump(exclude_none=True)
    if "reason_code" in update_data:
        update_data["reason_code"] = await validate_downtime_reason_code(db, update_data["reason_code"])
    bd = await crud.resolve_breakdown(db, bd, update_data, current_user.id)
    await db.commit()
    bd = await crud.get_breakdown(db, bd_id)
    return _bd_read(bd)


@router.patch("/breakdowns/{bd_id}", response_model=BreakdownRead)
async def update_breakdown(
    bd_id: uuid.UUID,
    body: BreakdownUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "edit")),
):
    bd = await crud.get_breakdown(db, bd_id)
    if not bd:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    update_data = body.model_dump(exclude_none=True)
    if "reason_code" in update_data:
        update_data["reason_code"] = await validate_downtime_reason_code(db, update_data["reason_code"])
    for k, v in update_data.items():
        setattr(bd, k, v)
    await db.flush()
    await db.commit()
    bd = await crud.get_breakdown(db, bd_id)
    return _bd_read(bd)


# ── Spare Parts ────────────────────────────────────────────────────────────────

@router.get("/spare-parts/", response_model=List[SparePartRead])
async def list_spare_parts(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    parts = await crud.list_spare_parts(db, active_only=active_only)
    return [_sp_read(sp) for sp in parts]


@router.post("/spare-parts/", response_model=SparePartRead, status_code=status.HTTP_201_CREATED)
async def create_spare_part(
    body: SparePartCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "create")),
):
    data = body.model_dump()
    if data.get("material_id"):
        data["material_id"] = uuid.UUID(data["material_id"])
    sp = await crud.create_spare_part(db, data)
    await db.commit()
    return _sp_read(sp)


@router.patch("/spare-parts/{part_id}", response_model=SparePartRead)
async def update_spare_part(
    part_id: uuid.UUID,
    body: SparePartUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "edit")),
):
    sp = await crud.get_spare_part(db, part_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Spare part not found")
    try:
        sp = await crud.update_spare_part(db, sp, body.model_dump(exclude_none=True))
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.SparePartAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    await db.commit()
    return _sp_read(sp)


@router.get("/spare-parts/{part_id}/usages", response_model=List[SparePartUsageRead])
async def list_part_usages(
    part_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    usages = await crud.list_spare_usages(db)
    filtered = [u for u in usages if u.spare_part_id == part_id]
    return [_usage_read(u) for u in filtered]


@router.post("/spare-parts/usage", response_model=SparePartUsageRead, status_code=status.HTTP_201_CREATED)
async def record_spare_usage(
    body: SparePartUsageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("maintenance", "create")),
):
    data = body.model_dump()
    for field in ["spare_part_id", "asset_id"]:
        data[field] = uuid.UUID(data[field])
    for field in ["breakdown_id", "pm_work_order_id"]:
        if data.get(field):
            data[field] = uuid.UUID(data[field])
    try:
        usage = await crud.record_spare_usage(db, data, current_user.id)
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.SparePartAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    await db.commit()
    usage_fresh = await crud.list_spare_usages(db)
    u = next((x for x in usage_fresh if x.id == usage.id), usage)
    return _usage_read(u)


@router.get("/breakdowns/{bd_id}/spare-usages", response_model=List[SparePartUsageRead])
async def list_breakdown_spares(
    bd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    usages = await crud.list_spare_usages(db, breakdown_id=bd_id)
    return [_usage_read(u) for u in usages]


# ── Reports ────────────────────────────────────────────────────────────────────

# Predictive Maintenance

@router.post("/predictions/generate", response_model=List[MaintenancePredictionRead])
async def generate_predictions(
    horizon_days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "predict")),
):
    predictions = await svc.generate_maintenance_predictions(db, horizon_days=horizon_days)
    await db.commit()
    fresh = await svc.list_maintenance_predictions(db, limit=200)
    generated_ids = {p.id for p in predictions}
    if generated_ids:
        fresh = [p for p in fresh if p.id in generated_ids]
    return [_prediction_read(p) for p in fresh]


@router.get("/predictions", response_model=List[MaintenancePredictionRead])
async def list_predictions(
    status_filter: Optional[MaintenancePredictionStatus] = Query(None, alias="status"),
    risk_level: Optional[MaintenancePredictionRisk] = None,
    machine_id: Optional[str] = None,
    limit: int = Query(100, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    predictions = await svc.list_maintenance_predictions(
        db,
        status=status_filter,
        risk_level=risk_level,
        machine_id=machine_id,
        limit=limit,
    )
    return [_prediction_read(p) for p in predictions]


@router.patch("/predictions/{prediction_id}/review", response_model=MaintenancePredictionRead)
async def review_prediction(
    prediction_id: uuid.UUID,
    body: MaintenancePredictionReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("maintenance", "review_prediction")),
):
    pred = await svc.get_maintenance_prediction(db, prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    await svc.review_maintenance_prediction(
        db,
        pred,
        status_value=body.status,
        reviewed_by=str(current_user.id),
        notes=body.review_notes,
    )
    await db.commit()
    pred = await svc.get_maintenance_prediction(db, prediction_id)
    return _prediction_read(pred)


@router.post("/predictions/{prediction_id}/work-order", response_model=MaintenancePredictionRead)
async def create_prediction_work_order(
    prediction_id: uuid.UUID,
    body: PMWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    _review_permission: User = Depends(require_permission("maintenance", "review_prediction")),
    current_user: User = Depends(require_permission("maintenance", "create")),
):
    """Plan a real PM work order from a reviewed prediction and an explicitly selected plan/date."""
    try:
        prediction = await svc.create_work_order_from_prediction(
            db, prediction_id, body, actor_id=current_user.id
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    prediction = await svc.get_maintenance_prediction(db, prediction_id)
    return _prediction_read(prediction)


@router.get("/reports/mtbf-mttr", response_model=List[MtbfMttrRow])
async def report_mtbf_mttr(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "export")),
):
    return await svc.compute_mtbf_mttr(db)


@router.get("/reports/downtime-by-machine", response_model=List[DowntimeByMachineRow])
async def report_downtime_by_machine(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "export")),
):
    return await svc.compute_downtime_by_machine(db)


@router.get("/reports/overdue-pm", response_model=List[OverduePMRow])
async def report_overdue_pm(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    return await svc.overdue_pm_list(db)
