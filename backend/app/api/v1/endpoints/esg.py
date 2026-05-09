from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as _BM
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import esg as crud
from app.services import esg_service as svc
from app.models.esg import SourceType, EmissionScope, ESGMetricType, SupplierSustainabilityRisk
from app.schemas.esg import (
    ActivityCreate, ActivityRead,
    EmissionFactorCreate, EmissionFactorUpdate, EmissionFactorRead,
    EmissionRecordRead,
    ResourceMetricCreate, ResourceMetricRead,
    ESGTargetCreate, ESGTargetRead,
    EmissionSummaryRow, EmissionBySourceRow, ResourceSummaryRow,
    ESGDashboard, ESGInsight, FleetImportResult,
    SupplierSustainabilityScoreCreate, SupplierSustainabilityScoreUpdate,
    SupplierSustainabilityScoreRead, EnergyIntensityRow,
    WastewaterComplianceSnapshot, ESGIntelligenceDashboard,
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

@router.get("/intelligence/dashboard", response_model=ESGIntelligenceDashboard)
async def intelligence_dashboard(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_esg_intelligence_dashboard(db, date_from=date_from, date_to=date_to)


@router.get("/intelligence/energy-intensity", response_model=List[EnergyIntensityRow])
async def energy_intensity_by_sku(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_energy_intensity_by_sku(db, date_from=date_from, date_to=date_to, limit=limit)


@router.get("/intelligence/wastewater-compliance", response_model=WastewaterComplianceSnapshot)
async def wastewater_compliance_snapshot(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_wastewater_compliance_snapshot(db, date_from=date_from, date_to=date_to)


@router.get("/supplier-scores", response_model=List[SupplierSustainabilityScoreRead])
async def list_supplier_scores(
    supplier_id: Optional[uuid.UUID] = None,
    risk_level: Optional[SupplierSustainabilityRisk] = None,
    limit: int = Query(100, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.list_supplier_sustainability_scores(db, supplier_id=supplier_id, risk_level=risk_level, limit=limit)


@router.post("/supplier-scores", response_model=SupplierSustainabilityScoreRead, status_code=201)
async def create_supplier_score(
    data: SupplierSustainabilityScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = await svc.create_supplier_sustainability_score(db, data, user_id=current_user.id)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/supplier-scores/{score_id}", response_model=SupplierSustainabilityScoreRead)
async def update_supplier_score(
    score_id: uuid.UUID,
    data: SupplierSustainabilityScoreUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await svc.update_supplier_sustainability_score(db, score_id, data)
    await db.commit()
    return obj


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


# ── Gap 64: Carbon Footprint Per Product ─────────────────────────────────────

class CarbonFootprintIn(_BM):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    production_batch_id: Optional[str] = None
    batch_ref: Optional[str] = None
    calculation_date: date
    units_produced: float
    uom: str = "KG"
    electricity_kwh: Optional[float] = None
    electricity_emission_factor: float = 0.4971  # Kenya grid factor kg CO2e/kWh (KPLC 2023)
    fuel_liters: Optional[float] = None
    packaging_kg_co2e: Optional[float] = None
    raw_material_kg_co2e: Optional[float] = None
    transport_kg_co2e: Optional[float] = None
    methodology: str = "GHG Protocol"
    notes: Optional[str] = None


@router.post("/carbon-footprints", status_code=201,
             dependencies=[Depends(get_current_user)])
async def create_carbon_footprint(payload: CarbonFootprintIn, db: AsyncSession = Depends(get_db)):
    """Calculate and store carbon footprint for a production batch."""
    from app.models.esg import ProductCarbonFootprint

    # Scope 2: electricity
    scope2 = 0.0
    if payload.electricity_kwh:
        scope2 = payload.electricity_kwh * payload.electricity_emission_factor

    # Scope 1: fuel combustion (diesel: ~2.68 kg CO2e/litre)
    scope1 = 0.0
    if payload.fuel_liters:
        scope1 = payload.fuel_liters * 2.68

    # Scope 3: materials + packaging + transport
    scope3 = (
        (payload.raw_material_kg_co2e or 0)
        + (payload.packaging_kg_co2e or 0)
        + (payload.transport_kg_co2e or 0)
    )

    total = scope1 + scope2 + scope3
    per_unit = total / payload.units_produced if payload.units_produced > 0 else None

    fp = ProductCarbonFootprint(
        product_id=uuid.UUID(payload.product_id) if payload.product_id else None,
        product_name=payload.product_name,
        production_batch_id=payload.production_batch_id,
        batch_ref=payload.batch_ref,
        calculation_date=payload.calculation_date,
        units_produced=payload.units_produced,
        uom=payload.uom,
        scope1_kg_co2e=scope1,
        scope2_kg_co2e=scope2,
        scope3_kg_co2e=scope3,
        total_kg_co2e=total,
        co2e_per_unit=per_unit,
        electricity_kwh=payload.electricity_kwh,
        electricity_emission_factor=payload.electricity_emission_factor,
        fuel_liters=payload.fuel_liters,
        packaging_kg_co2e=payload.packaging_kg_co2e,
        raw_material_kg_co2e=payload.raw_material_kg_co2e,
        transport_kg_co2e=payload.transport_kg_co2e,
        methodology=payload.methodology,
        notes=payload.notes,
    )
    db.add(fp)
    await db.commit()
    await db.refresh(fp)
    return {
        "id": str(fp.id),
        "product_name": fp.product_name,
        "batch_ref": fp.batch_ref,
        "scope1_kg_co2e": float(fp.scope1_kg_co2e or 0),
        "scope2_kg_co2e": float(fp.scope2_kg_co2e or 0),
        "scope3_kg_co2e": float(fp.scope3_kg_co2e or 0),
        "total_kg_co2e": float(fp.total_kg_co2e),
        "co2e_per_unit": float(fp.co2e_per_unit) if fp.co2e_per_unit else None,
        "units_produced": float(fp.units_produced),
        "uom": fp.uom,
    }


@router.get("/carbon-footprints",
            dependencies=[Depends(get_current_user)])
async def list_carbon_footprints(
    product_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.esg import ProductCarbonFootprint
    q = select(ProductCarbonFootprint)
    if product_id:
        q = q.where(ProductCarbonFootprint.product_id == uuid.UUID(product_id))
    q = q.order_by(desc(ProductCarbonFootprint.calculation_date)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "product_name": r.product_name, "batch_ref": r.batch_ref,
         "calculation_date": str(r.calculation_date),
         "total_kg_co2e": float(r.total_kg_co2e),
         "co2e_per_unit": float(r.co2e_per_unit) if r.co2e_per_unit else None,
         "units_produced": float(r.units_produced), "uom": r.uom,
         "scope1": float(r.scope1_kg_co2e or 0), "scope2": float(r.scope2_kg_co2e or 0),
         "scope3": float(r.scope3_kg_co2e or 0), "methodology": r.methodology}
        for r in rows
    ]


@router.get("/carbon-footprints/summary",
            dependencies=[Depends(get_current_user)])
async def carbon_summary(db: AsyncSession = Depends(get_db)):
    """Average CO2e per unit by product across all batches."""
    from app.models.esg import ProductCarbonFootprint
    r = await db.execute(
        select(
            ProductCarbonFootprint.product_name,
            func.avg(ProductCarbonFootprint.co2e_per_unit).label("avg_co2e_per_unit"),
            func.sum(ProductCarbonFootprint.total_kg_co2e).label("total_co2e"),
            func.count().label("batches"),
        )
        .where(ProductCarbonFootprint.co2e_per_unit.isnot(None))
        .group_by(ProductCarbonFootprint.product_name)
        .order_by(desc("avg_co2e_per_unit"))
    )
    return [
        {"product_name": row.product_name,
         "avg_co2e_per_unit": round(float(row.avg_co2e_per_unit), 6),
         "total_co2e": round(float(row.total_co2e), 3),
         "batches": row.batches}
        for row in r.all()
    ]
