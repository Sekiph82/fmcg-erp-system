"""
ESG / Environmental Sustainability Service.
Handles activity ingestion, emission calculation, reporting, and AI insights.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta, time
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.esg import (
    ActivityData, EmissionFactor, EmissionRecord, ResourceMetric, ESGTarget,
    SupplierSustainabilityScore,
    SourceType, EmissionScope, ESGMetricType,
    SupplierSustainabilityRisk,
)
from app.models.master import Supplier, Warehouse
from app.models.utility_management import (
    UtilityCostAllocation, UtilityType, WastewaterRecord, ComplianceStatus,
)
from app.crud import esg as crud
from app.schemas.esg import (
    ActivityCreate, EmissionSummaryRow, EmissionBySourceRow,
    EmissionByLocationRow, ResourceSummaryRow, ESGDashboard,
    ESGInsight, FleetImportResult,
    SupplierSustainabilityScoreCreate, SupplierSustainabilityScoreUpdate,
    EnergyIntensityRow, WastewaterComplianceSnapshot, ESGIntelligenceDashboard,
)

_SCOPE_MAP: dict[SourceType, EmissionScope] = {
    SourceType.FUEL_DIESEL: EmissionScope.SCOPE1,
    SourceType.FUEL_PETROL: EmissionScope.SCOPE1,
    SourceType.FUEL_LPG: EmissionScope.SCOPE1,
    SourceType.ELECTRICITY_GRID: EmissionScope.SCOPE2,
    SourceType.ELECTRICITY_SOLAR: EmissionScope.SCOPE2,
    SourceType.TRANSPORT_ROAD: EmissionScope.SCOPE3,
    SourceType.TRANSPORT_AIR: EmissionScope.SCOPE3,
    SourceType.MATERIAL: EmissionScope.SCOPE3,
    SourceType.WATER: EmissionScope.SCOPE3,
    SourceType.WASTE_GENERAL: EmissionScope.SCOPE3,
    SourceType.WASTE_HAZARDOUS: EmissionScope.SCOPE3,
    SourceType.WASTE_RECYCLED: EmissionScope.SCOPE3,
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Calculation Engine ────────────────────────────────────────────────────────

async def calculate_and_record(
    db: AsyncSession,
    activity: ActivityData,
    region: str = "KE",
) -> Optional[EmissionRecord]:
    """Find applicable factor and create emission record for an activity."""
    factor = await crud.get_active_factor(db, activity.source_type, region, activity.activity_date)
    if not factor:
        return None

    emission_kg = activity.quantity * factor.factor_value
    scope = _SCOPE_MAP.get(activity.source_type, EmissionScope.SCOPE3)

    record = EmissionRecord(
        activity_id=activity.id,
        factor_id=factor.id,
        calculated_emission_kgco2e=emission_kg,
        scope=scope,
        calculated_at=_now(),
    )
    return await crud.create_emission_record(db, record)


async def create_activity_with_emission(
    db: AsyncSession,
    data: ActivityCreate,
    user_id: uuid.UUID,
    region: str = "KE",
) -> tuple[ActivityData, Optional[EmissionRecord]]:
    activity = await crud.create_activity(db, data, user_id=user_id)
    emission = await calculate_and_record(db, activity, region)
    await db.flush()
    return activity, emission


# ── Fleet Data Import ─────────────────────────────────────────────────────────

async def import_from_fleet(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user_id: Optional[uuid.UUID] = None,
) -> FleetImportResult:
    """Import fuel logs from Fleet Management as Scope 1 ESG activities."""
    from app.models.fleet import FuelLog

    already_refs: set[str] = set()
    existing_q = await db.execute(
        select(ActivityData.source_reference).where(
            ActivityData.source_type.in_([SourceType.FUEL_DIESEL, SourceType.FUEL_PETROL]),
            ActivityData.is_auto_imported == True,  # noqa: E712
            ActivityData.source_reference.isnot(None),
        )
    )
    already_refs = {r for (r,) in existing_q.all()}

    q = select(FuelLog)
    if date_from:
        q = q.where(FuelLog.fuel_date >= date_from)
    if date_to:
        q = q.where(FuelLog.fuel_date <= date_to)

    fuel_logs_r = await db.execute(q)
    fuel_logs = list(fuel_logs_r.scalars().all())

    imported = 0
    with_emission = 0
    skipped = 0

    for log in fuel_logs:
        ref = f"FLEET-FUEL-{log.id}"
        if ref in already_refs:
            skipped += 1
            continue

        # Default to diesel; in a real system, match vehicle fuel_type
        source_type = SourceType.FUEL_DIESEL
        data = ActivityCreate(
            source_type=source_type,
            source_reference=ref,
            activity_date=log.fuel_date,
            quantity=Decimal(str(log.fuel_quantity_liters)),
            unit="liters",
            notes=f"Auto-imported from fleet fuel log. Station: {log.fuel_station or 'N/A'}",
        )
        activity = await crud.create_activity(db, data, user_id=user_id, is_auto_imported=True)
        emission = await calculate_and_record(db, activity)
        imported += 1
        if emission:
            with_emission += 1

    await db.flush()
    return FleetImportResult(
        imported_activities=imported,
        imported_emissions=with_emission,
        skipped=skipped,
        message=f"Imported {imported} fuel activities ({with_emission} with emission records). Skipped {skipped} already imported.",
    )


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_emission_summary(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[EmissionSummaryRow]:
    q = (
        select(
            EmissionRecord.scope,
            func.sum(EmissionRecord.calculated_emission_kgco2e).label("total_kg"),
            func.count(EmissionRecord.id).label("count"),
        )
        .group_by(EmissionRecord.scope)
        .order_by(EmissionRecord.scope)
    )
    if date_from or date_to:
        q = q.join(ActivityData, EmissionRecord.activity_id == ActivityData.id)
    if date_from:
        q = q.where(ActivityData.activity_date >= date_from)
    if date_to:
        q = q.where(ActivityData.activity_date <= date_to)

    result = await db.execute(q)
    rows = result.all()
    return [
        EmissionSummaryRow(
            scope=row.scope,
            total_kgco2e=Decimal(str(row.total_kg or 0)),
            total_tco2e=(Decimal(str(row.total_kg or 0)) / 1000).quantize(Decimal("0.001")),
            activity_count=row.count or 0,
        )
        for row in rows
    ]


async def get_emission_by_source(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[EmissionBySourceRow]:
    q = (
        select(
            ActivityData.source_type,
            EmissionRecord.scope,
            func.sum(EmissionRecord.calculated_emission_kgco2e).label("total_kg"),
            func.count(EmissionRecord.id).label("count"),
        )
        .join(ActivityData, EmissionRecord.activity_id == ActivityData.id)
        .group_by(ActivityData.source_type, EmissionRecord.scope)
        .order_by(func.sum(EmissionRecord.calculated_emission_kgco2e).desc())
    )
    if date_from:
        q = q.where(ActivityData.activity_date >= date_from)
    if date_to:
        q = q.where(ActivityData.activity_date <= date_to)

    result = await db.execute(q)
    return [
        EmissionBySourceRow(
            source_type=row.source_type,
            scope=row.scope,
            total_kgco2e=Decimal(str(row.total_kg or 0)),
            activity_count=row.count or 0,
        )
        for row in result.all()
    ]


async def get_resource_summary(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[ResourceSummaryRow]:
    q = (
        select(
            ResourceMetric.metric_type,
            ResourceMetric.unit,
            func.sum(ResourceMetric.quantity).label("total"),
            func.min(ResourceMetric.period_from).label("p_from"),
            func.max(ResourceMetric.period_to).label("p_to"),
        )
        .group_by(ResourceMetric.metric_type, ResourceMetric.unit)
    )
    if date_from:
        q = q.where(ResourceMetric.period_from >= date_from)
    if date_to:
        q = q.where(ResourceMetric.period_to <= date_to)

    result = await db.execute(q)
    return [
        ResourceSummaryRow(
            metric_type=row.metric_type,
            total_quantity=Decimal(str(row.total or 0)),
            unit=row.unit,
            period=f"{row.p_from} – {row.p_to}" if row.p_from else "—",
        )
        for row in result.all()
    ]


async def get_esg_dashboard(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ESGDashboard:
    summary = await get_emission_summary(db, date_from, date_to)
    resources = await get_resource_summary(db, date_from, date_to)

    scope_map: dict[EmissionScope, Decimal] = {r.scope: r.total_kgco2e for r in summary}
    total_emission = sum(scope_map.values(), Decimal("0"))

    res_map: dict[str, Decimal] = {}
    for r in resources:
        res_map[r.metric_type.value] = r.total_quantity

    energy = res_map.get("ENERGY", Decimal("0"))
    water = res_map.get("WATER", Decimal("0"))
    waste = res_map.get("WASTE", Decimal("0"))
    recycled = res_map.get("RECYCLING", Decimal("0"))
    recycling_rate = (recycled / (waste + recycled) * 100) if (waste + recycled) > 0 else None

    act_count_r = await db.execute(select(func.count(ActivityData.id)))
    act_count = act_count_r.scalar() or 0

    return ESGDashboard(
        total_emissions_kgco2e=total_emission,
        scope1_kgco2e=scope_map.get(EmissionScope.SCOPE1, Decimal("0")),
        scope2_kgco2e=scope_map.get(EmissionScope.SCOPE2, Decimal("0")),
        scope3_kgco2e=scope_map.get(EmissionScope.SCOPE3, Decimal("0")),
        total_energy_kwh=energy,
        total_water_m3=water,
        total_waste_kg=waste,
        recycling_rate_pct=recycling_rate,
        activity_count=act_count,
        last_updated=_now().isoformat(),
    )


async def get_target_performance(db: AsyncSession) -> list:
    targets = await crud.list_targets(db, is_active=True)
    summary = await get_emission_summary(db)
    resource_summary = await get_resource_summary(db)

    scope_map = {r.scope: r.total_kgco2e for r in summary}
    res_map = {r.metric_type.value: r.total_quantity for r in resource_summary}
    total_emission = sum(scope_map.values(), Decimal("0"))

    out = []
    for t in targets:
        if t.metric_type == ESGMetricType.EMISSIONS:
            scope_val = scope_map.get(t.scope) if t.scope else total_emission
            actual = scope_val or Decimal("0")
        else:
            actual = res_map.get(t.metric_type.value, Decimal("0"))

        reduction_needed = t.baseline_value - t.target_value
        reduction_achieved = t.baseline_value - actual if actual > 0 else Decimal("0")
        progress_pct = (
            (reduction_achieved / reduction_needed * 100).quantize(Decimal("0.1"))
            if reduction_needed > 0 else Decimal("0")
        )
        out.append({
            "id": str(t.id),
            "metric_type": t.metric_type.value,
            "scope": t.scope.value if t.scope else None,
            "baseline_year": t.baseline_year,
            "baseline_value": float(t.baseline_value),
            "target_value": float(t.target_value),
            "actual_value": float(actual),
            "unit": t.unit,
            "target_date": str(t.target_date),
            "progress_pct": float(progress_pct),
            "on_track": float(actual) <= float(t.target_value),
            "notes": t.notes,
        })
    return out


# ── AI Agents ─────────────────────────────────────────────────────────────────

def _date_to_start(dt: Optional[date]) -> Optional[datetime]:
    return datetime.combine(dt, time.min) if dt else None


def _date_to_end(dt: Optional[date]) -> Optional[datetime]:
    return datetime.combine(dt, time.max) if dt else None


def _risk_from_score(score: Decimal) -> SupplierSustainabilityRisk:
    if score >= Decimal("80"):
        return SupplierSustainabilityRisk.LOW
    if score >= Decimal("60"):
        return SupplierSustainabilityRisk.MEDIUM
    if score >= Decimal("40"):
        return SupplierSustainabilityRisk.HIGH
    return SupplierSustainabilityRisk.CRITICAL


async def create_supplier_sustainability_score(
    db: AsyncSession,
    data: SupplierSustainabilityScoreCreate,
    user_id: Optional[uuid.UUID] = None,
) -> SupplierSustainabilityScore:
    if data.assessment_period_end < data.assessment_period_start:
        raise HTTPException(400, "Assessment period end cannot be before start")
    if data.overall_score < 0 or data.overall_score > 100:
        raise HTTPException(400, "Overall score must be between 0 and 100")

    supplier_name = data.supplier_name
    if data.supplier_id:
        supplier = await db.get(Supplier, data.supplier_id)
        if not supplier:
            raise HTTPException(404, "Supplier not found")
        supplier_name = supplier.name

    payload = data.model_dump(exclude={"supplier_name"})
    payload["risk_level"] = payload.get("risk_level") or _risk_from_score(data.overall_score)
    obj = SupplierSustainabilityScore(
        **payload,
        supplier_name=supplier_name,
        assessed_by=user_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def list_supplier_sustainability_scores(
    db: AsyncSession,
    supplier_id: Optional[uuid.UUID] = None,
    risk_level: Optional[SupplierSustainabilityRisk] = None,
    limit: int = 100,
) -> List[SupplierSustainabilityScore]:
    q = (
        select(SupplierSustainabilityScore)
        .options(selectinload(SupplierSustainabilityScore.supplier))
        .order_by(desc(SupplierSustainabilityScore.assessment_period_end), desc(SupplierSustainabilityScore.created_at))
        .limit(limit)
    )
    if supplier_id:
        q = q.where(SupplierSustainabilityScore.supplier_id == supplier_id)
    if risk_level:
        q = q.where(SupplierSustainabilityScore.risk_level == risk_level)
    rows = await db.execute(q)
    return list(rows.scalars().all())


async def update_supplier_sustainability_score(
    db: AsyncSession,
    score_id: uuid.UUID,
    data: SupplierSustainabilityScoreUpdate,
) -> SupplierSustainabilityScore:
    obj = await db.get(SupplierSustainabilityScore, score_id)
    if not obj:
        raise HTTPException(404, "Supplier sustainability score not found")

    patch = data.model_dump(exclude_unset=True)
    start = patch.get("assessment_period_start", obj.assessment_period_start)
    end = patch.get("assessment_period_end", obj.assessment_period_end)
    if end < start:
        raise HTTPException(400, "Assessment period end cannot be before start")
    if "overall_score" in patch and (patch["overall_score"] < 0 or patch["overall_score"] > 100):
        raise HTTPException(400, "Overall score must be between 0 and 100")

    for key, value in patch.items():
        setattr(obj, key, value)
    obj.reviewed_at = _now()
    await db.flush()
    await db.refresh(obj)
    return obj


def _allocation_energy_kwh(row: UtilityCostAllocation) -> tuple[Decimal, bool]:
    qty = Decimal(str(row.allocated_quantity or 0))
    unit = (row.quantity_unit or "").strip().lower()
    if qty <= 0:
        return Decimal("0"), False
    if "kwh" in unit or "kw h" in unit or "kilowatt" in unit:
        return qty, True
    if row.utility_type in (UtilityType.ELECTRICITY, UtilityType.SOLAR) and not unit:
        return qty, True
    return Decimal("0"), False


async def get_energy_intensity_by_sku(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
) -> List[EnergyIntensityRow]:
    q = (
        select(UtilityCostAllocation)
        .options(selectinload(UtilityCostAllocation.product))
        .where(UtilityCostAllocation.product_id.isnot(None))
        .where(UtilityCostAllocation.utility_type.in_([UtilityType.ELECTRICITY, UtilityType.SOLAR]))
        .order_by(desc(UtilityCostAllocation.allocation_date))
        .limit(2000)
    )
    if date_from:
        q = q.where(UtilityCostAllocation.allocation_date >= date_from)
    if date_to:
        q = q.where(UtilityCostAllocation.allocation_date <= date_to)

    rows = list((await db.execute(q)).scalars().all())
    grouped: dict[str, dict] = {}
    for row in rows:
        product = row.product
        key = str(row.product_id)
        if key not in grouped:
            grouped[key] = {
                "product_id": row.product_id,
                "product_sku": product.sku if product else None,
                "product_name": product.name if product else row.target_name or "Unlinked product",
                "batches": set(),
                "allocation_count": 0,
                "total_energy_kwh": Decimal("0"),
                "production_volume_kg": Decimal("0"),
                "total_energy_cost": Decimal("0"),
                "currency_code": row.currency_code,
                "converted": 0,
                "skipped": 0,
            }
        item = grouped[key]
        energy_kwh, converted = _allocation_energy_kwh(row)
        item["allocation_count"] += 1
        item["converted"] += 1 if converted else 0
        item["skipped"] += 0 if converted else 1
        item["total_energy_kwh"] += energy_kwh
        item["production_volume_kg"] += Decimal(str(row.production_volume_kg or 0))
        item["total_energy_cost"] += Decimal(str(row.allocated_cost or row.total_cost or 0))
        if row.batch_no:
            item["batches"].add(row.batch_no)

    out: List[EnergyIntensityRow] = []
    for item in grouped.values():
        volume = item["production_volume_kg"]
        energy = item["total_energy_kwh"]
        kwh_per_kg = (energy / volume).quantize(Decimal("0.0001")) if volume > 0 else None
        kwh_per_ton = (energy / (volume / Decimal("1000"))).quantize(Decimal("0.01")) if volume > 0 else None
        if item["converted"] == 0:
            quality = "NO_KWH_QUANTITY"
        elif volume <= 0:
            quality = "MISSING_PRODUCTION_VOLUME"
        elif item["skipped"] > 0:
            quality = "PARTIAL"
        else:
            quality = "GOOD"
        out.append(EnergyIntensityRow(
            product_id=item["product_id"],
            product_sku=item["product_sku"],
            product_name=item["product_name"],
            batches=len(item["batches"]),
            allocation_count=item["allocation_count"],
            total_energy_kwh=energy.quantize(Decimal("0.001")),
            production_volume_kg=volume.quantize(Decimal("0.001")),
            kwh_per_kg=kwh_per_kg,
            kwh_per_ton=kwh_per_ton,
            total_energy_cost=item["total_energy_cost"].quantize(Decimal("0.01")),
            currency_code=item["currency_code"],
            data_quality=quality,
        ))

    return sorted(out, key=lambda r: r.kwh_per_kg or Decimal("-1"), reverse=True)[:limit]


async def get_wastewater_compliance_snapshot(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> WastewaterComplianceSnapshot:
    filters = []
    start_dt = _date_to_start(date_from)
    end_dt = _date_to_end(date_to)
    if start_dt:
        filters.append(WastewaterRecord.record_datetime >= start_dt)
    if end_dt:
        filters.append(WastewaterRecord.record_datetime <= end_dt)

    status_q = select(WastewaterRecord.compliance_status, func.count(WastewaterRecord.id)).group_by(WastewaterRecord.compliance_status)
    avg_q = select(
        func.avg(WastewaterRecord.effluent_cod_mgl),
        func.avg(WastewaterRecord.effluent_bod_mgl),
        func.avg(WastewaterRecord.effluent_tss_mgl),
        func.avg(WastewaterRecord.effluent_ph),
        func.sum(WastewaterRecord.power_consumed_kwh),
    )
    deviation_q = (
        select(WastewaterRecord)
        .where(or_(
            WastewaterRecord.compliance_status.in_([ComplianceStatus.NON_COMPLIANT, ComplianceStatus.BORDERLINE]),
            WastewaterRecord.is_anomaly == True,  # noqa: E712
        ))
        .order_by(desc(WastewaterRecord.record_datetime))
        .limit(8)
    )
    if filters:
        status_q = status_q.where(and_(*filters))
        avg_q = avg_q.where(and_(*filters))
        deviation_q = deviation_q.where(and_(*filters))

    counts = {status: count for status, count in (await db.execute(status_q)).all()}
    compliant = counts.get(ComplianceStatus.COMPLIANT, 0)
    borderline = counts.get(ComplianceStatus.BORDERLINE, 0)
    non_compliant = counts.get(ComplianceStatus.NON_COMPLIANT, 0)
    not_tested = counts.get(ComplianceStatus.NOT_TESTED, 0)
    total = compliant + borderline + non_compliant + not_tested
    tested = total - not_tested
    compliance_rate = (Decimal(compliant) / Decimal(tested) * 100).quantize(Decimal("0.1")) if tested > 0 else None

    avg_row = (await db.execute(avg_q)).one()
    deviations = list((await db.execute(deviation_q)).scalars().all())

    def dec(value, scale: str = "0.001") -> Optional[Decimal]:
        return Decimal(str(value)).quantize(Decimal(scale)) if value is not None else None

    return WastewaterComplianceSnapshot(
        total_records=total,
        compliant_records=compliant,
        borderline_records=borderline,
        non_compliant_records=non_compliant,
        not_tested_records=not_tested,
        compliance_rate_pct=compliance_rate,
        avg_effluent_cod_mgl=dec(avg_row[0]),
        avg_effluent_bod_mgl=dec(avg_row[1]),
        avg_effluent_tss_mgl=dec(avg_row[2]),
        avg_effluent_ph=dec(avg_row[3], "0.01"),
        total_power_kwh=dec(avg_row[4]) or Decimal("0.000"),
        latest_deviations=[
            {
                "id": str(row.id),
                "record_no": row.record_no,
                "record_datetime": row.record_datetime.isoformat(),
                "status": row.compliance_status.value,
                "effluent_cod_mgl": float(row.effluent_cod_mgl) if row.effluent_cod_mgl is not None else None,
                "effluent_bod_mgl": float(row.effluent_bod_mgl) if row.effluent_bod_mgl is not None else None,
                "effluent_tss_mgl": float(row.effluent_tss_mgl) if row.effluent_tss_mgl is not None else None,
                "effluent_ph": float(row.effluent_ph) if row.effluent_ph is not None else None,
                "deviation_reason": row.deviation_reason,
                "corrective_action": row.corrective_action,
            }
            for row in deviations
        ],
    )


async def get_esg_intelligence_dashboard(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ESGIntelligenceDashboard:
    scores_q = await db.execute(
        select(
            func.count(SupplierSustainabilityScore.id),
            func.avg(SupplierSustainabilityScore.overall_score),
        )
    )
    count, avg_score = scores_q.one()
    high_risk_q = await db.execute(
        select(func.count(SupplierSustainabilityScore.id)).where(
            SupplierSustainabilityScore.risk_level.in_([
                SupplierSustainabilityRisk.HIGH,
                SupplierSustainabilityRisk.CRITICAL,
            ])
        )
    )
    return ESGIntelligenceDashboard(
        supplier_score_count=count or 0,
        average_supplier_score=Decimal(str(avg_score)).quantize(Decimal("0.1")) if avg_score is not None else None,
        high_risk_supplier_count=high_risk_q.scalar() or 0,
        energy_intensity_rows=await get_energy_intensity_by_sku(db, date_from=date_from, date_to=date_to, limit=10),
        wastewater_compliance=await get_wastewater_compliance_snapshot(db, date_from=date_from, date_to=date_to),
    )


async def ai_emission_hotspot(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ESGInsight:
    by_source = await get_emission_by_source(db, date_from, date_to)
    insights = []
    details = []

    if not by_source:
        insights.append("No emission records calculated yet. Add activities and emission factors to begin tracking.")
        return ESGInsight(agent="Emission Hotspot Analyzer", insights=insights, generated_at=_now().isoformat())

    total = sum(r.total_kgco2e for r in by_source)
    for row in by_source[:5]:
        pct = (row.total_kgco2e / total * 100) if total > 0 else Decimal("0")
        insights.append(
            f"HOTSPOT: {row.source_type.value} ({row.scope.value}) = {float(row.total_kgco2e):.1f} kgCO2e ({float(pct):.1f}% of total). "
            f"Priority for reduction."
        )
        details.append({
            "source_type": row.source_type.value,
            "scope": row.scope.value,
            "kgco2e": float(row.total_kgco2e),
            "pct_of_total": float(pct),
        })

    top = by_source[0]
    if top.source_type in (SourceType.FUEL_DIESEL, SourceType.FUEL_PETROL):
        insights.append("RECOMMENDATION: Fleet fuel is the top emission source. Consider route optimization or EV adoption to reduce Scope 1 emissions.")
    elif top.source_type == SourceType.ELECTRICITY_GRID:
        insights.append("RECOMMENDATION: Grid electricity dominates Scope 2. Consider solar expansion or renewable energy certificates.")

    return ESGInsight(agent="Emission Hotspot Analyzer", insights=insights, details=details, generated_at=_now().isoformat())


async def ai_reduction_advisor(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ESGInsight:
    by_source = await get_emission_by_source(db, date_from, date_to)
    dashboard = await get_esg_dashboard(db, date_from, date_to)
    insights = []
    details = []

    if float(dashboard.scope1_kgco2e) > 0:
        potential = float(dashboard.scope1_kgco2e) * 0.15
        insights.append(f"SCOPE 1: Route optimization and load consolidation could reduce fleet emissions by ~15% ({potential:.0f} kgCO2e).")
        details.append({"action": "Route optimization", "scope": "SCOPE1", "potential_saving_kgco2e": round(potential, 1)})

    if float(dashboard.scope2_kgco2e) > 0:
        potential = float(dashboard.scope2_kgco2e) * 0.40
        insights.append(f"SCOPE 2: Expanding solar coverage could displace ~40% of grid electricity ({potential:.0f} kgCO2e).")
        details.append({"action": "Solar expansion", "scope": "SCOPE2", "potential_saving_kgco2e": round(potential, 1)})

    if float(dashboard.scope3_kgco2e) > 0:
        insights.append("SCOPE 3: Engage top suppliers on emission reduction targets. Require GHG disclosures in procurement criteria.")
        details.append({"action": "Supplier engagement", "scope": "SCOPE3", "note": "Supplier data required"})

    if float(dashboard.total_waste_kg) > 0 and float(dashboard.recycling_rate_pct or 0) < 50:
        insights.append(f"WASTE: Recycling rate at {float(dashboard.recycling_rate_pct or 0):.1f}%. Target 70%+ to reduce landfill emissions.")

    if not insights:
        insights.append("Insufficient emission data to generate specific reduction recommendations. Increase activity data coverage.")

    return ESGInsight(agent="Reduction Advisor", insights=insights, details=details, generated_at=_now().isoformat())


async def ai_data_quality(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ESGInsight:
    activities = await crud.list_activities(db, date_from=date_from, date_to=date_to, limit=1000)
    insights = []
    details = []

    total = len(activities)
    without_emission = sum(1 for a in activities if not a.emission_records)
    missing_location = sum(1 for a in activities if a.location_id is None)

    if total == 0:
        insights.append("No activity data recorded yet. Begin logging fuel, electricity, water, and waste to enable ESG reporting.")
        return ESGInsight(agent="Data Quality Monitor", insights=insights, generated_at=_now().isoformat())

    if without_emission > 0:
        pct = without_emission / total * 100
        insights.append(
            f"MISSING FACTORS: {without_emission} activities ({pct:.1f}%) have no emission record — emission factor may be missing for their source type. "
            f"Add factors for {', '.join({a.source_type.value for a in activities if not a.emission_records})}."
        )
        details.append({"issue": "missing_emission_factor", "count": without_emission})

    if missing_location > 0:
        insights.append(f"INCOMPLETE DATA: {missing_location} activities have no location tag — location-based reporting will be incomplete.")
        details.append({"issue": "missing_location", "count": missing_location})

    # Check for gaps (missing months)
    if activities:
        dates = sorted({a.activity_date for a in activities})
        if len(dates) > 1:
            gap = (max(dates) - min(dates)).days
            expected_entries = gap // 7  # rough weekly expectation
            if total < expected_entries * 0.3:
                insights.append(f"DATA GAPS: Only {total} activities over {gap} days — possible under-reporting. Ensure all emission sources are logged consistently.")

    if not insights:
        insights.append("Data quality is acceptable. All activities have emission factors and location tags.")

    return ESGInsight(agent="Data Quality Monitor", insights=insights, details=details, generated_at=_now().isoformat())


# ── Default Factor Seeding ────────────────────────────────────────────────────

DEFAULT_FACTORS = [
    {"factor_code": "KE-DIESEL-S1", "source_type": SourceType.FUEL_DIESEL, "scope": EmissionScope.SCOPE1,
     "factor_value": Decimal("2.68"), "unit": "kgCO2e/liter", "source_reference": "GHG Protocol 2023"},
    {"factor_code": "KE-PETROL-S1", "source_type": SourceType.FUEL_PETROL, "scope": EmissionScope.SCOPE1,
     "factor_value": Decimal("2.31"), "unit": "kgCO2e/liter", "source_reference": "GHG Protocol 2023"},
    {"factor_code": "KE-LPG-S1", "source_type": SourceType.FUEL_LPG, "scope": EmissionScope.SCOPE1,
     "factor_value": Decimal("1.51"), "unit": "kgCO2e/liter", "source_reference": "GHG Protocol 2023"},
    {"factor_code": "KE-GRID-S2", "source_type": SourceType.ELECTRICITY_GRID, "scope": EmissionScope.SCOPE2,
     "factor_value": Decimal("0.24"), "unit": "kgCO2e/kWh", "source_reference": "Kenya KPLC Grid Factor 2023"},
    {"factor_code": "KE-SOLAR-S2", "source_type": SourceType.ELECTRICITY_SOLAR, "scope": EmissionScope.SCOPE2,
     "factor_value": Decimal("0.041"), "unit": "kgCO2e/kWh", "source_reference": "IPCC AR6 lifecycle"},
    {"factor_code": "KE-ROAD-S3", "source_type": SourceType.TRANSPORT_ROAD, "scope": EmissionScope.SCOPE3,
     "factor_value": Decimal("0.096"), "unit": "kgCO2e/tonne-km", "source_reference": "DEFRA 2023"},
    {"factor_code": "KE-WASTE-S3", "source_type": SourceType.WASTE_GENERAL, "scope": EmissionScope.SCOPE3,
     "factor_value": Decimal("0.45"), "unit": "kgCO2e/kg", "source_reference": "IPCC AR6"},
    {"factor_code": "KE-WATER-S3", "source_type": SourceType.WATER, "scope": EmissionScope.SCOPE3,
     "factor_value": Decimal("0.000344"), "unit": "kgCO2e/liter", "source_reference": "DEFRA 2023"},
]


async def seed_default_factors(db: AsyncSession) -> int:
    """Seed default emission factors if not already present."""
    from datetime import date as d
    seeded = 0
    for f in DEFAULT_FACTORS:
        existing = await db.execute(
            select(EmissionFactor).where(EmissionFactor.factor_code == f["factor_code"])
        )
        if existing.scalar_one_or_none():
            continue
        obj = EmissionFactor(
            factor_code=f["factor_code"],
            source_type=f["source_type"],
            scope=f["scope"],
            region="KE",
            valid_from=d(2023, 1, 1),
            factor_value=f["factor_value"],
            unit=f["unit"],
            source_reference=f["source_reference"],
            is_active=True,
        )
        db.add(obj)
        seeded += 1
    if seeded:
        await db.flush()
    return seeded
