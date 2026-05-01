from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import esg as crud
from app.services import esg_service as svc
from app.models.esg import SourceType, EmissionScope, ESGMetricType
from app.schemas.esg import (
    ActivityCreate, ActivityRead,
    EmissionFactorCreate, EmissionFactorUpdate, EmissionFactorRead,
    EmissionRecordRead,
    ResourceMetricCreate, ResourceMetricRead,
    ESGTargetCreate, ESGTargetRead,
    EmissionSummaryRow, EmissionBySourceRow, ResourceSummaryRow,
    ESGDashboard, ESGInsight, FleetImportResult,
)

router = APIRouter()


def _activity_read(a) -> ActivityRead:
    r = ActivityRead.model_validate(a)
    if a.location:
        r.location_name = a.location.name
    if a.supplier:
        r.supplier_name = a.supplier.name
    if a.emission_records:
        rec = a.emission_records[0]
        r.calculated_emission_kgco2e = rec.calculated_emission_kgco2e
        r.scope = rec.scope
    return r


def _emission_read(rec) -> EmissionRecordRead:
    r = EmissionRecordRead.model_validate(rec)
    if rec.activity:
        r.source_type = rec.activity.source_type
        r.activity_date = rec.activity.activity_date
        r.quantity = rec.activity.quantity
        r.unit = rec.activity.unit
        if rec.activity.location:
            r.location_name = rec.activity.location.name
    if rec.factor:
        r.factor_code = rec.factor.factor_code
        r.factor_value = rec.factor.factor_value
    return r


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ESGDashboard)
async def esg_dashboard(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_esg_dashboard(db, date_from=date_from, date_to=date_to)


# ── Activity Data ─────────────────────────────────────────────────────────────

@router.get("/activities", response_model=List[ActivityRead])
async def list_activities(
    source_type: Optional[SourceType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    location_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    activities = await crud.list_activities(
        db, source_type=source_type, date_from=date_from,
        date_to=date_to, location_id=location_id, skip=skip, limit=limit,
    )
    return [_activity_read(a) for a in activities]


@router.post("/activities", response_model=ActivityRead, status_code=201)
async def create_activity(
    data: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    activity, _ = await svc.create_activity_with_emission(db, data, current_user.id)
    await db.commit()
    activity = await crud.get_activity(db, activity.id)
    return _activity_read(activity)


@router.get("/activities/{activity_id}", response_model=ActivityRead)
async def get_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    a = await crud.get_activity(db, activity_id)
    if not a:
        raise HTTPException(404, "Activity not found")
    return _activity_read(a)


# ── Emission Factors ──────────────────────────────────────────────────────────

@router.get("/factors", response_model=List[EmissionFactorRead])
async def list_factors(
    source_type: Optional[SourceType] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await crud.list_factors(db, source_type=source_type, is_active=is_active)


@router.post("/factors", response_model=EmissionFactorRead, status_code=201)
async def create_factor(
    data: EmissionFactorCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_factor(db, data)
    await db.commit()
    return EmissionFactorRead.model_validate(obj)


@router.patch("/factors/{factor_id}", response_model=EmissionFactorRead)
async def update_factor(
    factor_id: uuid.UUID,
    data: EmissionFactorUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    factor = await crud.get_factor(db, factor_id)
    if not factor:
        raise HTTPException(404, "Factor not found")
    factor = await crud.update_factor(db, factor, data)
    await db.commit()
    return EmissionFactorRead.model_validate(factor)


@router.post("/factors/seed", status_code=201)
async def seed_factors(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    n = await svc.seed_default_factors(db)
    await db.commit()
    return {"seeded": n, "message": f"Seeded {n} default emission factors."}


# ── Emission Records ──────────────────────────────────────────────────────────

@router.get("/emissions", response_model=List[EmissionRecordRead])
async def list_emissions(
    scope: Optional[EmissionScope] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0, limit: int = 500,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    records = await crud.list_emission_records(
        db, scope=scope, date_from=date_from, date_to=date_to, skip=skip, limit=limit
    )
    return [_emission_read(r) for r in records]


# ── Resource Metrics ──────────────────────────────────────────────────────────

@router.get("/metrics", response_model=List[ResourceMetricRead])
async def list_metrics(
    metric_type: Optional[ESGMetricType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    metrics = await crud.list_metrics(
        db, metric_type=metric_type, date_from=date_from, date_to=date_to, skip=skip, limit=limit
    )
    out = []
    for m in metrics:
        r = ResourceMetricRead.model_validate(m)
        if m.location:
            r.location_name = m.location.name
        out.append(r)
    return out


@router.post("/metrics", response_model=ResourceMetricRead, status_code=201)
async def create_metric(
    data: ResourceMetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = await crud.create_metric(db, data, user_id=current_user.id)
    await db.commit()
    r = ResourceMetricRead.model_validate(obj)
    return r


# ── ESG Targets ───────────────────────────────────────────────────────────────

@router.get("/targets", response_model=List[ESGTargetRead])
async def list_targets(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await crud.list_targets(db, is_active=is_active)


@router.post("/targets", response_model=ESGTargetRead, status_code=201)
async def create_target(
    data: ESGTargetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_target(db, data)
    await db.commit()
    return ESGTargetRead.model_validate(obj)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/emission-summary", response_model=List[EmissionSummaryRow])
async def emission_summary_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_emission_summary(db, date_from=date_from, date_to=date_to)


@router.get("/reports/emission-by-source", response_model=List[EmissionBySourceRow])
async def emission_by_source_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_emission_by_source(db, date_from=date_from, date_to=date_to)


@router.get("/reports/resources", response_model=List[ResourceSummaryRow])
async def resource_summary_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_resource_summary(db, date_from=date_from, date_to=date_to)


@router.get("/reports/targets")
async def target_performance_report(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_target_performance(db)


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/import/fleet", response_model=FleetImportResult)
async def import_fleet_fuel(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await svc.import_from_fleet(db, date_from=date_from, date_to=date_to, user_id=current_user.id)
    await db.commit()
    return result


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/ai/hotspot", response_model=ESGInsight)
async def ai_hotspot(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_emission_hotspot(db, date_from=date_from, date_to=date_to)


@router.get("/ai/reduction-advisor", response_model=ESGInsight)
async def ai_reduction(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_reduction_advisor(db, date_from=date_from, date_to=date_to)


@router.get("/ai/data-quality", response_model=ESGInsight)
async def ai_data_quality(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_data_quality(db, date_from=date_from, date_to=date_to)
