"""
Utilities Reports API
─────────────────────
All 21 utility report types exposed as GET endpoints.
Every report has a companion /export/csv endpoint.

Permission: utility_management.view (all reports)
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.utilities_reports import (
    AbnormalConsumptionReport,
    AlarmTrendReport,
    BaseLoadAnalysis,
    BoilerEfficiencyReport,
    ChemicalTreatmentReport,
    CompressorPerformanceReport,
    CostAllocationReport,
    DailyConsumptionReport,
    DailySummaryReport,
    PeakDemandAnalysis,
    SoftWaterProductionReport,
    SolarGenerationReport,
    SteamGenerationReport,
    SustainabilityReport,
    WastewaterComplianceReport,
)
from app.services.utilities_reports_service import (
    get_abnormal_consumption_report,
    get_alarm_trend_report,
    get_base_load_analysis,
    get_boiler_efficiency_report,
    get_chemical_treatment_report,
    get_compressor_performance_report,
    get_cost_allocation_report,
    get_daily_consumption_report,
    get_daily_summary_report,
    get_peak_demand_analysis,
    get_soft_water_report,
    get_solar_generation_report,
    get_steam_generation_report,
    get_sustainability_report,
    get_wastewater_compliance_report,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# ── Helper: default date range (last 30 days) ─────────────────────────────────

def _today() -> date:
    return date.today()

def _d30() -> date:
    return date.today() - timedelta(days=30)


def _csv_response(rows: list[dict], filename: str, fieldnames: list[str]) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({k: (str(v) if v is not None else "") for k, v in row.items()})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. Daily Consumption (electricity / water / gas / any utility type)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/daily-consumption", response_model=DailyConsumptionReport)
async def daily_consumption_report(
    date_from:    date           = Query(default_factory=_d30),
    date_to:      date           = Query(default_factory=_today),
    utility_type: Optional[str]  = Query(None),
    department:   Optional[str]  = Query(None),
    shift_ref:    Optional[str]  = Query(None),
    skip:         int            = Query(0, ge=0),
    limit:        int            = Query(500, le=2000),
    db:           AsyncSession   = Depends(get_db),
    _:            User           = Depends(get_current_user),
):
    return await get_daily_consumption_report(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department, shift_ref=shift_ref,
        skip=skip, limit=limit,
    )


@router.get("/daily-consumption/export/csv")
async def daily_consumption_export(
    date_from:    date           = Query(default_factory=_d30),
    date_to:      date           = Query(default_factory=_today),
    utility_type: Optional[str]  = Query(None),
    department:   Optional[str]  = Query(None),
    shift_ref:    Optional[str]  = Query(None),
    db:           AsyncSession   = Depends(get_db),
    _:            User           = Depends(get_current_user),
):
    report = await get_daily_consumption_report(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department, shift_ref=shift_ref,
        skip=0, limit=10000,
    )
    fields = ["date", "utility_type", "quantity", "unit", "total_cost", "currency", "department", "shift_ref", "tx_count"]
    return _csv_response([r.model_dump() for r in report.rows], "daily_consumption.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Daily Utility Summary (all utilities on one report)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/daily-summary", response_model=DailySummaryReport)
async def daily_summary_report(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    department: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    return await get_daily_summary_report(db, date_from=date_from, date_to=date_to, department=department)


@router.get("/daily-summary/export/csv")
async def daily_summary_export(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    department: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    report = await get_daily_summary_report(db, date_from=date_from, date_to=date_to, department=department)
    fields = ["utility_type", "quantity", "unit", "total_cost", "tx_count", "avg_daily"]
    return _csv_response([r.model_dump() for r in report.rows], "daily_summary.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Boiler Efficiency
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/boiler-efficiency", response_model=BoilerEfficiencyReport)
async def boiler_efficiency_report(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    shift_ref:  Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(500, le=2000),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    return await get_boiler_efficiency_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, shift_ref=shift_ref, department=department,
        skip=skip, limit=limit,
    )


@router.get("/boiler-efficiency/export/csv")
async def boiler_efficiency_export(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    shift_ref:  Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    report = await get_boiler_efficiency_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, shift_ref=shift_ref, department=department,
        skip=0, limit=10000,
    )
    fields = [
        "record_no", "asset_no", "record_datetime", "shift_ref", "department",
        "period_hours", "steam_generated_kg", "fuel_type", "fuel_consumption", "fuel_unit",
        "boiler_efficiency_pct", "boiler_load_pct", "blowdown_pct",
        "feedwater_consumed_m3", "condensate_returned_m3",
        "steam_pressure_bar", "steam_temp_c", "status", "is_anomaly",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "boiler_efficiency.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Steam Generation
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/steam-generation", response_model=SteamGenerationReport)
async def steam_generation_report(
    date_from: date          = Query(default_factory=_d30),
    date_to:   date          = Query(default_factory=_today),
    asset_no:  Optional[str] = Query(None),
    skip:      int           = Query(0, ge=0),
    limit:     int           = Query(500, le=2000),
    db:        AsyncSession  = Depends(get_db),
    _:         User          = Depends(get_current_user),
):
    return await get_steam_generation_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, skip=skip, limit=limit,
    )


@router.get("/steam-generation/export/csv")
async def steam_generation_export(
    date_from: date          = Query(default_factory=_d30),
    date_to:   date          = Query(default_factory=_today),
    asset_no:  Optional[str] = Query(None),
    db:        AsyncSession  = Depends(get_db),
    _:         User          = Depends(get_current_user),
):
    report = await get_steam_generation_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, skip=0, limit=10000,
    )
    fields = ["date", "asset_no", "steam_generated_kg", "steam_pressure_bar", "steam_temp_c",
              "steam_flow_kgh", "steam_quality_pct", "feedwater_m3", "blowdown_litres"]
    return _csv_response([r.model_dump() for r in report.rows], "steam_generation.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Compressor Performance & Leak
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/compressor-performance", response_model=CompressorPerformanceReport)
async def compressor_performance_report(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    shift_ref:  Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(500, le=2000),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    return await get_compressor_performance_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, shift_ref=shift_ref, department=department,
        skip=skip, limit=limit,
    )


@router.get("/compressor-performance/export/csv")
async def compressor_performance_export(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    report = await get_compressor_performance_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, department=department,
        skip=0, limit=10000,
    )
    fields = [
        "record_no", "asset_no", "record_datetime", "shift_ref", "department",
        "period_hours", "air_generated_nm3", "electricity_used_kwh", "specific_energy_kwh_m3",
        "load_pct", "discharge_pressure_bar",
        "leak_test_done", "leak_estimation_pct", "leak_volume_nm3",
        "night_idle_kwh", "status", "is_anomaly",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "compressor_performance.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Soft Water Production & Salt
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/soft-water", response_model=SoftWaterProductionReport)
async def soft_water_report(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    shift_ref:  Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(500, le=2000),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    return await get_soft_water_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, shift_ref=shift_ref, department=department,
        skip=skip, limit=limit,
    )


@router.get("/soft-water/export/csv")
async def soft_water_export(
    date_from:  date          = Query(default_factory=_d30),
    date_to:    date          = Query(default_factory=_today),
    asset_no:   Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
    _:          User          = Depends(get_current_user),
):
    report = await get_soft_water_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, department=department,
        skip=0, limit=10000,
    )
    fields = [
        "record_no", "asset_no", "record_datetime", "shift_ref", "department",
        "volume_treated_m3", "raw_water_input_m3", "salt_consumed_kg", "salt_per_m3",
        "efficiency_pct", "feed_water_hardness_ppm", "product_water_hardness_ppm",
        "regeneration_count", "destination_tag",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "soft_water_report.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Water Treatment Chemical
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/chemical-treatment", response_model=ChemicalTreatmentReport)
async def chemical_treatment_report(
    date_from:      date          = Query(default_factory=_d30),
    date_to:        date          = Query(default_factory=_today),
    asset_no:       Optional[str] = Query(None),
    treatment_type: Optional[str] = Query(None),
    shift_ref:      Optional[str] = Query(None),
    skip:           int           = Query(0, ge=0),
    limit:          int           = Query(500, le=2000),
    db:             AsyncSession  = Depends(get_db),
    _:              User          = Depends(get_current_user),
):
    return await get_chemical_treatment_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, treatment_type=treatment_type, shift_ref=shift_ref,
        skip=skip, limit=limit,
    )


@router.get("/chemical-treatment/export/csv")
async def chemical_treatment_export(
    date_from:      date          = Query(default_factory=_d30),
    date_to:        date          = Query(default_factory=_today),
    asset_no:       Optional[str] = Query(None),
    treatment_type: Optional[str] = Query(None),
    db:             AsyncSession  = Depends(get_db),
    _:              User          = Depends(get_current_user),
):
    report = await get_chemical_treatment_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, treatment_type=treatment_type, skip=0, limit=10000,
    )
    fields = [
        "record_no", "asset_no", "record_datetime", "treatment_type",
        "chemical_name", "chemical_category", "treatment_area",
        "quantity_dosed", "unit", "target_dose_ppm", "actual_dose_ppm",
        "unit_cost", "total_cost", "overdose_flag", "underdose_flag",
        "feed_ph", "product_ph", "residual_chlorine_ppm",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "chemical_treatment.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Solar Generation vs Consumption
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/solar-generation", response_model=SolarGenerationReport)
async def solar_generation_report(
    date_from: date          = Query(default_factory=_d30),
    date_to:   date          = Query(default_factory=_today),
    asset_no:  Optional[str] = Query(None),
    skip:      int           = Query(0, ge=0),
    limit:     int           = Query(500, le=2000),
    db:        AsyncSession  = Depends(get_db),
    _:         User          = Depends(get_current_user),
):
    return await get_solar_generation_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, skip=skip, limit=limit,
    )


@router.get("/solar-generation/export/csv")
async def solar_generation_export(
    date_from: date          = Query(default_factory=_d30),
    date_to:   date          = Query(default_factory=_today),
    asset_no:  Optional[str] = Query(None),
    db:        AsyncSession  = Depends(get_db),
    _:         User          = Depends(get_current_user),
):
    report = await get_solar_generation_report(
        db, date_from=date_from, date_to=date_to, asset_no=asset_no, skip=0, limit=10000,
    )
    fields = [
        "date", "asset_no", "energy_generated_kwh", "self_consumption_kwh", "grid_export_kwh",
        "irradiance_wm2", "pr_ratio", "inverter_efficiency_pct", "availability_pct",
        "capacity_factor_pct", "total_elec_consumption_kwh", "solar_contribution_pct",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "solar_generation.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Wastewater Compliance
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/wastewater-compliance", response_model=WastewaterComplianceReport)
async def wastewater_compliance_report(
    date_from:     date          = Query(default_factory=_d30),
    date_to:       date          = Query(default_factory=_today),
    asset_no:      Optional[str] = Query(None),
    process_stage: Optional[str] = Query(None),
    shift_ref:     Optional[str] = Query(None),
    skip:          int           = Query(0, ge=0),
    limit:         int           = Query(500, le=2000),
    db:            AsyncSession  = Depends(get_db),
    _:             User          = Depends(get_current_user),
):
    return await get_wastewater_compliance_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, process_stage=process_stage, shift_ref=shift_ref,
        skip=skip, limit=limit,
    )


@router.get("/wastewater-compliance/export/csv")
async def wastewater_compliance_export(
    date_from:     date          = Query(default_factory=_d30),
    date_to:       date          = Query(default_factory=_today),
    asset_no:      Optional[str] = Query(None),
    process_stage: Optional[str] = Query(None),
    db:            AsyncSession  = Depends(get_db),
    _:             User          = Depends(get_current_user),
):
    report = await get_wastewater_compliance_report(
        db, date_from=date_from, date_to=date_to,
        asset_no=asset_no, process_stage=process_stage, skip=0, limit=10000,
    )
    fields = [
        "record_no", "asset_no", "record_datetime", "process_stage", "shift_ref",
        "influent_cod_mgl", "effluent_cod_mgl", "cod_removal_pct",
        "influent_bod_mgl", "effluent_bod_mgl",
        "influent_tss_mgl", "effluent_tss_mgl",
        "effluent_ph", "do_mgl", "compliance_status",
        "permit_limit_ref", "deviation_reason",
        "power_consumed_kwh", "sludge_produced_kg",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "wastewater_compliance.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 10. Cost Allocation (dept / line / machine / product / batch)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/cost-allocation", response_model=CostAllocationReport)
async def cost_allocation_report(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    group_by:     str           = Query("department"),
    utility_type: Optional[str] = Query(None),
    skip:         int           = Query(0, ge=0),
    limit:        int           = Query(200, le=1000),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    return await get_cost_allocation_report(
        db, date_from=date_from, date_to=date_to,
        group_by=group_by, utility_type=utility_type, skip=skip, limit=limit,
    )


@router.get("/cost-allocation/export/csv")
async def cost_allocation_export(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    group_by:     str           = Query("department"),
    utility_type: Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    report = await get_cost_allocation_report(
        db, date_from=date_from, date_to=date_to,
        group_by=group_by, utility_type=utility_type, skip=0, limit=10000,
    )
    fields = [
        "dimension", "utility_type", "allocated_cost", "allocated_quantity",
        "quantity_unit", "cost_per_unit", "cost_per_ton",
        "production_volume_kg", "allocation_count", "pct_of_total",
    ]
    return _csv_response(
        [r.model_dump() for r in report.rows],
        f"cost_by_{group_by}.csv",
        fields,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 11. Base Load Analysis
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/base-load", response_model=BaseLoadAnalysis)
async def base_load_analysis(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    return await get_base_load_analysis(
        db, date_from=date_from, date_to=date_to, utility_type=utility_type,
    )


@router.get("/base-load/export/csv")
async def base_load_export(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    report = await get_base_load_analysis(db, date_from=date_from, date_to=date_to, utility_type=utility_type)
    fields = [
        "utility_type", "unit", "min_daily", "p10_daily", "p25_daily",
        "median_daily", "mean_daily", "p75_daily", "p90_daily", "max_daily",
        "base_load_est", "base_load_pct",
    ]
    return _csv_response([r.model_dump() for r in report.rows], "base_load_analysis.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 12. Peak Demand Analysis
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/peak-demand", response_model=PeakDemandAnalysis)
async def peak_demand_analysis(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    department:   Optional[str] = Query(None),
    top_n:        int           = Query(20, ge=5, le=100),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    return await get_peak_demand_analysis(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department, top_n=top_n,
    )


@router.get("/peak-demand/export/csv")
async def peak_demand_export(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    department:   Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    report = await get_peak_demand_analysis(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department, top_n=1000,
    )
    fields = ["date", "utility_type", "department", "quantity", "unit", "total_cost", "is_anomaly"]
    return _csv_response([r.model_dump() for r in report.top_days], "peak_demand.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 13. Alarm Trend
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/alarm-trends", response_model=AlarmTrendReport)
async def alarm_trend_report(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    skip:         int           = Query(0, ge=0),
    limit:        int           = Query(50, le=500),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    return await get_alarm_trend_report(
        db, date_from=date_from, date_to=date_to, utility_type=utility_type,
        skip=skip, limit=limit,
    )


@router.get("/alarm-trends/export/csv")
async def alarm_trend_export(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    report = await get_alarm_trend_report(
        db, date_from=date_from, date_to=date_to, utility_type=utility_type,
        skip=0, limit=10000,
    )
    fields = ["event_no", "rule_code", "rule_name", "utility_type", "asset_no", "device_code",
              "severity", "triggered_at", "status", "triggered_value", "threshold_value", "parameter"]
    return _csv_response([r.model_dump() for r in report.recent], "alarm_events.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 14. Abnormal Consumption
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/abnormal-consumption", response_model=AbnormalConsumptionReport)
async def abnormal_consumption_report(
    date_from:              date          = Query(default_factory=_d30),
    date_to:                date          = Query(default_factory=_today),
    utility_type:           Optional[str] = Query(None),
    department:             Optional[str] = Query(None),
    deviation_threshold_pct: float        = Query(30.0, ge=5.0, le=200.0),
    skip:                   int           = Query(0, ge=0),
    limit:                  int           = Query(200, le=1000),
    db:                     AsyncSession  = Depends(get_db),
    _:                      User          = Depends(get_current_user),
):
    return await get_abnormal_consumption_report(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department,
        deviation_threshold_pct=deviation_threshold_pct,
        skip=skip, limit=limit,
    )


@router.get("/abnormal-consumption/export/csv")
async def abnormal_consumption_export(
    date_from:    date          = Query(default_factory=_d30),
    date_to:      date          = Query(default_factory=_today),
    utility_type: Optional[str] = Query(None),
    department:   Optional[str] = Query(None),
    deviation_threshold_pct: float = Query(30.0),
    db:           AsyncSession  = Depends(get_db),
    _:            User          = Depends(get_current_user),
):
    report = await get_abnormal_consumption_report(
        db, date_from=date_from, date_to=date_to,
        utility_type=utility_type, department=department,
        deviation_threshold_pct=deviation_threshold_pct,
        skip=0, limit=10000,
    )
    fields = ["date", "utility_type", "department", "quantity", "unit",
              "mean_baseline", "deviation_pct", "total_cost", "is_anomaly", "anomaly_note"]
    return _csv_response([r.model_dump() for r in report.rows], "abnormal_consumption.csv", fields)


# ══════════════════════════════════════════════════════════════════════════════
# 15. Sustainability Summary
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/sustainability", response_model=SustainabilityReport)
async def sustainability_report(
    date_from: date         = Query(default_factory=_d30),
    date_to:   date         = Query(default_factory=_today),
    db:        AsyncSession = Depends(get_db),
    _:         User         = Depends(get_current_user),
):
    return await get_sustainability_report(db, date_from=date_from, date_to=date_to)


@router.get("/sustainability/export/csv")
async def sustainability_export(
    date_from: date         = Query(default_factory=_d30),
    date_to:   date         = Query(default_factory=_today),
    db:        AsyncSession = Depends(get_db),
    _:         User         = Depends(get_current_user),
):
    report = await get_sustainability_report(db, date_from=date_from, date_to=date_to)
    fields = ["label", "value", "unit", "benchmark", "trend"]
    return _csv_response([m.model_dump() for m in report.metrics], "sustainability.csv", fields)
