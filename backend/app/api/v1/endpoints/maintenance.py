from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.models.user import User
from app.models.maintenance import (
    AssetStatus, PMStatus, BreakdownStatus, BreakdownSeverity,
    MaintenancePredictionRisk, MaintenancePredictionStatus,
)
import app.crud.maintenance as crud
import app.services.maintenance_service as svc
from app.schemas.maintenance import (
    AssetCreate, AssetUpdate, AssetRead,
    PMPlanCreate, PMPlanUpdate, PMPlanRead,
    PMWorkOrderCreate, PMWorkOrderUpdate, PMWorkOrderRead,
    BreakdownCreate, BreakdownUpdate, BreakdownRead,
    SparePartCreate, SparePartUpdate, SparePartRead,
    SparePartUsageCreate, SparePartUsageRead,
    MaintenancePredictionRead, MaintenancePredictionReview,
    MtbfMttrRow, DowntimeByMachineRow, OverduePMRow,
)

router = APIRouter()


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
    asset = await crud.create_asset(db, body.model_dump())
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
    asset = await crud.update_asset(db, asset, body.model_dump(exclude_none=True))
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
    wo = await crud.create_work_order(db, data, svc.next_wo_no(count))
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

@router.get("/breakdowns/", response_model=List[BreakdownRead])
async def list_breakdowns(
    asset_id: Optional[uuid.UUID] = None,
    status: Optional[BreakdownStatus] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("maintenance", "view")),
):
    bds = await crud.list_breakdowns(db, asset_id=asset_id, status=status)
    return [_bd_read(bd) for bd in bds]


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
    bd = await crud.resolve_breakdown(db, bd, body.model_dump(exclude_none=True), current_user.id)
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
    for k, v in body.model_dump(exclude_none=True).items():
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
    sp = await crud.update_spare_part(db, sp, body.model_dump(exclude_none=True))
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
    usage = await crud.record_spare_usage(db, data, current_user.id)
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
    _=Depends(require_permission("maintenance", "review_prediction")),
):
    pred = await svc.get_maintenance_prediction(db, prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    await svc.review_maintenance_prediction(
        db,
        pred,
        status_value=body.status,
        reviewed_by=body.reviewed_by,
        notes=body.review_notes,
    )
    await db.commit()
    pred = await svc.get_maintenance_prediction(db, prediction_id)
    return _prediction_read(pred)


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
