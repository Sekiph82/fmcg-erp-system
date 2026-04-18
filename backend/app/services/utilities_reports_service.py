"""
Utilities Reports Service
─────────────────────────
All report query logic for the 21 utility report types.
Endpoints are thin wrappers; all SQL lives here.
"""
from __future__ import annotations

import logging
import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, case, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.utility_management import (
    BoilerSteamRecord,
    CompressorRecord,
    ComplianceStatus,
    SoftWaterRecord,
    SolarRecord,
    TreatmentChemicalRecord,
    UtilityAlarmEvent,
    UtilityAlarmRule,
    UtilityAsset,
    UtilityDevice,
    UtilityCostAllocation,
    UtilityTransaction,
    UtilityType,
    WastewaterRecord,
    AlarmSeverity,
)
from app.schemas.utilities_reports import (
    AbnormalConsumptionReport,
    AbnormalConsumptionRow,
    AlarmDetailRow,
    AlarmTrendReport,
    AlarmTrendRow,
    BaseLoadAnalysis,
    BaseLoadRow,
    BoilerEfficiencyReport,
    BoilerEfficiencyRow,
    ChemicalTreatmentReport,
    ChemicalTreatmentRow,
    CompressorPerformanceReport,
    CompressorPerformanceRow,
    CostAllocationReport,
    CostAllocationRow,
    DailyConsumptionReport,
    DailyConsumptionRow,
    DailySummaryReport,
    DistributionSlice,
    PeakDemandAnalysis,
    PeakDemandRow,
    SoftWaterProductionReport,
    SoftWaterProductionRow,
    SolarGenerationReport,
    SolarGenerationRow,
    SteamGenerationReport,
    SteamGenerationRow,
    SustainabilityMetric,
    SustainabilityReport,
    TrendPoint,
    UtilityTypeSummaryRow,
    WastewaterComplianceReport,
    WastewaterComplianceRow,
)

logger = logging.getLogger(__name__)

_D = lambda v: Decimal(str(v)) if v is not None else Decimal("0")
_DN = lambda v: Decimal(str(v)) if v is not None else None
_R = lambda v, dp=2: Decimal(str(round(float(v), dp))) if v is not None else None
_safe_div = lambda a, b: _R(_D(a) / _D(b)) if b and float(b) != 0.0 else None
_safe_pct = lambda a, b: _R(_D(a) / _D(b) * 100) if b and float(b) != 0.0 else None


def _date_clause(col, d_from: date, d_to: date):
    return and_(col >= d_from, col <= d_to)


def _dtime_clause(col, d_from: date, d_to: date):
    return and_(func.date(col) >= d_from, func.date(col) <= d_to)


# ── 1-2. Daily Consumption + Summary ─────────────────────────────────────────

_UNIT_MAP = {
    "ELECTRICITY": "kWh", "WATER": "m³", "PROCESS_WATER": "m³",
    "SOFT_WATER": "m³", "STEAM": "kg", "COMPRESSED_AIR": "Nm³",
    "SOLAR": "kWh", "NATURAL_GAS": "Nm³", "WASTEWATER": "m³",
    "DIESEL": "L", "CHILLED_WATER": "m³", "OTHER": "units",
}


async def get_daily_consumption_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    utility_type: Optional[str] = None,
    department: Optional[str] = None,
    shift_ref: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> DailyConsumptionReport:
    q = (
        select(
            UtilityTransaction.transaction_date.label("tx_date"),
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.min(UtilityTransaction.currency_code).label("currency"),
            UtilityTransaction.department.label("dept"),
            UtilityTransaction.shift_ref.label("shift"),
            func.count().label("cnt"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(
            UtilityTransaction.transaction_date,
            UtilityTransaction.utility_type,
            UtilityTransaction.department,
            UtilityTransaction.shift_ref,
        )
        .order_by(UtilityTransaction.transaction_date.desc())
    )
    if utility_type:
        q = q.where(UtilityTransaction.utility_type == utility_type)
    if department:
        q = q.where(UtilityTransaction.department == department)
    if shift_ref:
        q = q.where(UtilityTransaction.shift_ref == shift_ref)

    rows_raw = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = [
        DailyConsumptionRow(
            date=str(r.tx_date),
            utility_type=str(r.utype),
            quantity=_DN(r.qty),
            unit=r.uom,
            total_cost=_DN(r.cost),
            currency=r.currency,
            department=r.dept,
            shift_ref=r.shift,
            tx_count=r.cnt,
        )
        for r in rows_raw
    ]

    # Aggregate totals
    agg = (await db.execute(
        select(
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
        ).where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .where(*([] if not utility_type else [UtilityTransaction.utility_type == utility_type]))
        .where(*([] if not department else [UtilityTransaction.department == department]))
    )).one_or_none()

    # Daily trend
    trend_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.quantity).label("v"),
            func.sum(UtilityTransaction.total_cost).label("v2"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .where(*([] if not utility_type else [UtilityTransaction.utility_type == utility_type]))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all()

    trend = [TrendPoint(date=str(r.d), value=_DN(r.v), value2=_DN(r.v2)) for r in trend_raw]

    return DailyConsumptionReport(
        date_from=str(date_from),
        date_to=str(date_to),
        utility_type=utility_type,
        total_quantity=_DN(agg.qty) if agg else None,
        total_cost=_DN(agg.cost) if agg else None,
        unit=_UNIT_MAP.get(utility_type or "", "units") if utility_type else None,
        rows=rows,
        trend=trend,
    )


async def get_daily_summary_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    department: Optional[str] = None,
) -> DailySummaryReport:
    q = (
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.count().label("cnt"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.utility_type)
        .order_by(func.sum(UtilityTransaction.total_cost).desc().nullslast())
    )
    if department:
        q = q.where(UtilityTransaction.department == department)

    rows_raw = (await db.execute(q)).all()
    days = max((date_to - date_from).days, 1)

    rows = [
        UtilityTypeSummaryRow(
            utility_type=str(r.utype),
            quantity=_DN(r.qty),
            unit=r.uom or _UNIT_MAP.get(str(r.utype), "units"),
            total_cost=_DN(r.cost),
            tx_count=r.cnt,
            avg_daily=_R(_D(r.qty) / days) if r.qty else None,
        )
        for r in rows_raw
    ]

    total_cost = sum((_D(r.total_cost) for r in rows if r.total_cost), Decimal("0")) or None

    # Daily trend (all utilities combined)
    trend_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.total_cost).label("v"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all()

    trend = [TrendPoint(date=str(r.d), value=_DN(r.v)) for r in trend_raw]

    return DailySummaryReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_cost=total_cost,
        rows=rows,
        trend=trend,
    )


# ── 3. Boiler Efficiency ──────────────────────────────────────────────────────

async def get_boiler_efficiency_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    shift_ref: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> BoilerEfficiencyReport:
    q = (
        select(BoilerSteamRecord, UtilityAsset.asset_no.label("ano"))
        .outerjoin(UtilityAsset, BoilerSteamRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
        .order_by(BoilerSteamRecord.record_datetime.desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())
    if shift_ref:
        q = q.where(BoilerSteamRecord.shift_ref == shift_ref)
    if department:
        q = q.where(BoilerSteamRecord.department == department)

    records = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = [
        BoilerEfficiencyRow(
            record_no=r.BoilerSteamRecord.record_no,
            asset_no=r.ano,
            record_datetime=str(r.BoilerSteamRecord.record_datetime)[:19],
            shift_ref=r.BoilerSteamRecord.shift_ref,
            department=r.BoilerSteamRecord.department,
            period_hours=_DN(r.BoilerSteamRecord.period_hours),
            steam_generated_kg=_DN(r.BoilerSteamRecord.steam_generated_kg),
            fuel_type=r.BoilerSteamRecord.fuel_type,
            fuel_consumption=_DN(r.BoilerSteamRecord.fuel_consumption),
            fuel_unit=r.BoilerSteamRecord.fuel_unit,
            boiler_efficiency_pct=_DN(r.BoilerSteamRecord.boiler_efficiency_pct),
            boiler_load_pct=_DN(r.BoilerSteamRecord.boiler_load_pct),
            blowdown_pct=_DN(r.BoilerSteamRecord.blowdown_pct),
            feedwater_consumed_m3=_DN(r.BoilerSteamRecord.feedwater_consumed_m3),
            condensate_returned_m3=_DN(r.BoilerSteamRecord.condensate_returned_m3),
            steam_pressure_bar=_DN(r.BoilerSteamRecord.steam_pressure_bar),
            steam_temp_c=_DN(r.BoilerSteamRecord.steam_temp_c),
            status=str(r.BoilerSteamRecord.status) if r.BoilerSteamRecord.status else None,
            is_anomaly=r.BoilerSteamRecord.is_anomaly,
        )
        for r in records
    ]

    # Aggregates
    agg = (await db.execute(
        select(
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("avg_eff"),
            func.sum(BoilerSteamRecord.steam_generated_kg).label("tot_steam"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("tot_fuel"),
            func.avg(BoilerSteamRecord.boiler_load_pct).label("avg_load"),
            func.sum(BoilerSteamRecord.condensate_returned_m3).label("cond"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feed"),
        ).where(_dtime_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    cond_pct = _safe_pct(agg.cond, agg.feed) if agg else None

    # Trend: daily avg efficiency
    trend_raw = (await db.execute(
        select(
            func.date(BoilerSteamRecord.record_datetime).label("d"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("v"),
            func.sum(BoilerSteamRecord.steam_generated_kg).label("v2"),
        )
        .where(_dtime_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
        .group_by(func.date(BoilerSteamRecord.record_datetime))
        .order_by(func.date(BoilerSteamRecord.record_datetime))
    )).all()

    trend = [TrendPoint(date=str(r.d), value=_R(r.v), value2=_DN(r.v2)) for r in trend_raw]

    return BoilerEfficiencyReport(
        date_from=str(date_from),
        date_to=str(date_to),
        avg_efficiency_pct=_R(agg.avg_eff) if agg else None,
        total_steam_kg=_DN(agg.tot_steam) if agg else None,
        total_fuel=_DN(agg.tot_fuel) if agg else None,
        avg_load_pct=_R(agg.avg_load) if agg else None,
        condensate_recovery_pct=cond_pct,
        rows=rows,
        trend=trend,
    )


# ── 4. Steam Generation ───────────────────────────────────────────────────────

async def get_steam_generation_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> SteamGenerationReport:
    q = (
        select(
            func.date(BoilerSteamRecord.record_datetime).label("d"),
            UtilityAsset.asset_no.label("ano"),
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam"),
            func.avg(BoilerSteamRecord.steam_pressure_bar).label("pbar"),
            func.avg(BoilerSteamRecord.steam_temp_c).label("temp"),
            func.avg(BoilerSteamRecord.steam_flow_kgh).label("flow"),
            func.avg(BoilerSteamRecord.steam_quality_pct).label("qual"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feed"),
            func.sum(BoilerSteamRecord.blowdown_volume_litres).label("bldwn"),
        )
        .outerjoin(UtilityAsset, BoilerSteamRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
        .group_by(func.date(BoilerSteamRecord.record_datetime), UtilityAsset.asset_no)
        .order_by(func.date(BoilerSteamRecord.record_datetime).desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())

    rows_raw = (await db.execute(q.offset(skip).limit(limit))).all()
    rows = [
        SteamGenerationRow(
            date=str(r.d),
            asset_no=r.ano,
            steam_generated_kg=_DN(r.steam),
            steam_pressure_bar=_R(r.pbar),
            steam_temp_c=_R(r.temp),
            steam_flow_kgh=_R(r.flow),
            steam_quality_pct=_R(r.qual),
            feedwater_m3=_DN(r.feed),
            blowdown_litres=_DN(r.bldwn),
        )
        for r in rows_raw
    ]

    agg = (await db.execute(
        select(
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam"),
            func.avg(BoilerSteamRecord.steam_pressure_bar).label("pbar"),
            func.avg(BoilerSteamRecord.steam_temp_c).label("temp"),
            func.avg(BoilerSteamRecord.steam_quality_pct).label("qual"),
        ).where(_dtime_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    trend = [TrendPoint(date=r.date, value=r.steam_generated_kg) for r in rows][::-1]

    return SteamGenerationReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_steam_kg=_DN(agg.steam) if agg else None,
        avg_pressure_bar=_R(agg.pbar) if agg else None,
        avg_temp_c=_R(agg.temp) if agg else None,
        avg_quality_pct=_R(agg.qual) if agg else None,
        rows=rows,
        trend=trend,
    )


# ── 5. Compressor Performance & Leak ──────────────────────────────────────────

async def get_compressor_performance_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    shift_ref: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> CompressorPerformanceReport:
    q = (
        select(CompressorRecord, UtilityAsset.asset_no.label("ano"))
        .outerjoin(UtilityAsset, CompressorRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(CompressorRecord.record_datetime, date_from, date_to))
        .order_by(CompressorRecord.record_datetime.desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())
    if shift_ref:
        q = q.where(CompressorRecord.shift_ref == shift_ref)
    if department:
        q = q.where(CompressorRecord.department == department)

    records = (await db.execute(q.offset(skip).limit(limit))).all()
    rows = [
        CompressorPerformanceRow(
            record_no=r.CompressorRecord.record_no,
            asset_no=r.ano,
            record_datetime=str(r.CompressorRecord.record_datetime)[:19],
            shift_ref=r.CompressorRecord.shift_ref,
            department=r.CompressorRecord.department,
            period_hours=_DN(r.CompressorRecord.period_hours),
            air_generated_nm3=_DN(r.CompressorRecord.air_generated_nm3),
            electricity_used_kwh=_DN(r.CompressorRecord.electricity_used_kwh),
            specific_energy_kwh_m3=_DN(r.CompressorRecord.specific_energy_kwh_m3),
            load_pct=_DN(r.CompressorRecord.load_pct),
            discharge_pressure_bar=_DN(r.CompressorRecord.discharge_pressure_bar),
            leak_test_done=r.CompressorRecord.leak_test_done,
            leak_estimation_pct=_DN(r.CompressorRecord.leak_estimation_pct),
            leak_volume_nm3=_DN(r.CompressorRecord.leak_volume_nm3),
            night_idle_kwh=_DN(r.CompressorRecord.night_idle_kwh),
            status=str(r.CompressorRecord.status) if r.CompressorRecord.status else None,
            is_anomaly=r.CompressorRecord.is_anomaly,
        )
        for r in records
    ]

    agg = (await db.execute(
        select(
            func.sum(CompressorRecord.air_generated_nm3).label("air"),
            func.sum(CompressorRecord.electricity_used_kwh).label("kwh"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("spec"),
            func.avg(CompressorRecord.load_pct).label("load"),
            func.avg(CompressorRecord.leak_estimation_pct).label("leak_pct"),
            func.sum(CompressorRecord.leak_volume_nm3).label("leak_vol"),
        ).where(_dtime_clause(CompressorRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    trend_raw = (await db.execute(
        select(
            func.date(CompressorRecord.record_datetime).label("d"),
            func.sum(CompressorRecord.air_generated_nm3).label("v"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("v2"),
        )
        .where(_dtime_clause(CompressorRecord.record_datetime, date_from, date_to))
        .group_by(func.date(CompressorRecord.record_datetime))
        .order_by(func.date(CompressorRecord.record_datetime))
    )).all()

    trend = [TrendPoint(date=str(r.d), value=_DN(r.v), value2=_R(r.v2)) for r in trend_raw]

    return CompressorPerformanceReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_air_nm3=_DN(agg.air) if agg else None,
        total_kwh=_DN(agg.kwh) if agg else None,
        avg_specific_energy=_R(agg.spec) if agg else None,
        avg_load_pct=_R(agg.load) if agg else None,
        avg_leak_pct=_R(agg.leak_pct) if agg else None,
        total_leak_nm3=_DN(agg.leak_vol) if agg else None,
        rows=rows,
        trend=trend,
    )


# ── 6. Soft Water Production & Salt ───────────────────────────────────────────

async def get_soft_water_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    shift_ref: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> SoftWaterProductionReport:
    q = (
        select(SoftWaterRecord, UtilityAsset.asset_no.label("ano"))
        .outerjoin(UtilityAsset, SoftWaterRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(SoftWaterRecord.record_datetime, date_from, date_to))
        .order_by(SoftWaterRecord.record_datetime.desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())
    if shift_ref:
        q = q.where(SoftWaterRecord.shift_ref == shift_ref)
    if department:
        q = q.where(SoftWaterRecord.department == department)

    records = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = []
    for r in records:
        sw = r.SoftWaterRecord
        salt_per_m3 = _safe_div(sw.salt_consumed_kg, sw.volume_treated_m3)
        rows.append(SoftWaterProductionRow(
            record_no=sw.record_no,
            asset_no=r.ano,
            record_datetime=str(sw.record_datetime)[:19],
            shift_ref=sw.shift_ref,
            department=sw.department,
            volume_treated_m3=_DN(sw.volume_treated_m3),
            raw_water_input_m3=_DN(sw.raw_water_input_m3),
            salt_consumed_kg=_DN(sw.salt_consumed_kg),
            salt_per_m3=salt_per_m3,
            efficiency_pct=_DN(sw.efficiency_pct),
            feed_water_hardness_ppm=_DN(sw.feed_water_hardness_ppm),
            product_water_hardness_ppm=_DN(sw.product_water_hardness_ppm),
            regeneration_count=sw.regeneration_count,
            destination_tag=sw.destination_tag,
        ))

    agg = (await db.execute(
        select(
            func.sum(SoftWaterRecord.volume_treated_m3).label("vol"),
            func.sum(SoftWaterRecord.raw_water_input_m3).label("raw"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("salt"),
            func.avg(SoftWaterRecord.efficiency_pct).label("eff"),
        ).where(_dtime_clause(SoftWaterRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    avg_salt = _safe_div(agg.salt, agg.vol) if agg else None
    conv_pct = _safe_pct(agg.vol, agg.raw) if agg else None

    trend_raw = (await db.execute(
        select(
            func.date(SoftWaterRecord.record_datetime).label("d"),
            func.sum(SoftWaterRecord.volume_treated_m3).label("v"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("v2"),
        )
        .where(_dtime_clause(SoftWaterRecord.record_datetime, date_from, date_to))
        .group_by(func.date(SoftWaterRecord.record_datetime))
        .order_by(func.date(SoftWaterRecord.record_datetime))
    )).all()

    return SoftWaterProductionReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_volume_treated_m3=_DN(agg.vol) if agg else None,
        total_raw_water_m3=_DN(agg.raw) if agg else None,
        total_salt_kg=_DN(agg.salt) if agg else None,
        avg_salt_per_m3=avg_salt,
        avg_efficiency_pct=_R(agg.eff) if agg else None,
        conversion_pct=conv_pct,
        rows=rows,
        trend=[TrendPoint(date=str(r.d), value=_DN(r.v), value2=_DN(r.v2)) for r in trend_raw],
    )


# ── 7. Chemical Treatment ─────────────────────────────────────────────────────

async def get_chemical_treatment_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    treatment_type: Optional[str] = None,
    shift_ref: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> ChemicalTreatmentReport:
    q = (
        select(TreatmentChemicalRecord, UtilityAsset.asset_no.label("ano"))
        .outerjoin(UtilityAsset, TreatmentChemicalRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(TreatmentChemicalRecord.record_datetime, date_from, date_to))
        .order_by(TreatmentChemicalRecord.record_datetime.desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())
    if treatment_type:
        q = q.where(TreatmentChemicalRecord.treatment_type == treatment_type)
    if shift_ref:
        q = q.where(TreatmentChemicalRecord.shift_ref == shift_ref)

    records = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = []
    for r in records:
        rec = r.TreatmentChemicalRecord
        cost = _R(_D(rec.unit_cost) * _D(rec.quantity_dosed)) if rec.unit_cost is not None and rec.quantity_dosed is not None else None
        rows.append(ChemicalTreatmentRow(
            record_no=rec.record_no,
            asset_no=r.ano,
            record_datetime=str(rec.record_datetime)[:19],
            treatment_type=str(rec.treatment_type) if rec.treatment_type else None,
            chemical_name=rec.chemical_name,
            chemical_category=str(rec.chemical_category) if rec.chemical_category else None,
            treatment_area=rec.treatment_area,
            quantity_dosed=_DN(rec.quantity_dosed),
            unit=rec.unit,
            target_dose_ppm=_DN(rec.target_dose_ppm),
            actual_dose_ppm=_DN(rec.actual_dose_ppm),
            unit_cost=_DN(rec.unit_cost),
            total_cost=cost,
            overdose_flag=rec.overdose_flag,
            underdose_flag=rec.underdose_flag,
            feed_ph=_DN(rec.feed_ph),
            product_ph=_DN(rec.product_ph),
            residual_chlorine_ppm=_DN(rec.residual_chlorine_ppm),
        ))

    # Aggregates
    agg = (await db.execute(
        select(
            func.sum(TreatmentChemicalRecord.quantity_dosed).label("total_dosed"),
            func.count(
                case((TreatmentChemicalRecord.overdose_flag == True, 1))
            ).label("overdose_cnt"),
            func.count(
                case((TreatmentChemicalRecord.underdose_flag == True, 1))
            ).label("underdose_cnt"),
        ).where(_dtime_clause(TreatmentChemicalRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    # By chemical
    by_chem_raw = (await db.execute(
        select(
            TreatmentChemicalRecord.chemical_name.label("lbl"),
            func.sum(TreatmentChemicalRecord.quantity_dosed).label("val"),
        )
        .where(_dtime_clause(TreatmentChemicalRecord.record_datetime, date_from, date_to))
        .group_by(TreatmentChemicalRecord.chemical_name)
        .order_by(func.sum(TreatmentChemicalRecord.quantity_dosed).desc())
        .limit(10)
    )).all()

    total_dosed = _D(agg.total_dosed) if agg and agg.total_dosed else Decimal("0")
    by_chemical = [
        DistributionSlice(
            label=r.lbl or "Unknown",
            value=_DN(r.val),
            pct=_safe_pct(r.val, total_dosed) if total_dosed else None,
        )
        for r in by_chem_raw
    ]

    # By area
    by_area_raw = (await db.execute(
        select(
            TreatmentChemicalRecord.treatment_area.label("lbl"),
            func.sum(TreatmentChemicalRecord.quantity_dosed).label("val"),
        )
        .where(_dtime_clause(TreatmentChemicalRecord.record_datetime, date_from, date_to))
        .group_by(TreatmentChemicalRecord.treatment_area)
        .order_by(func.sum(TreatmentChemicalRecord.quantity_dosed).desc())
        .limit(10)
    )).all()

    by_area = [
        DistributionSlice(
            label=r.lbl or "Unspecified",
            value=_DN(r.val),
            pct=_safe_pct(r.val, total_dosed) if total_dosed else None,
        )
        for r in by_area_raw
    ]

    # Estimate total cost from unit_cost * quantity_dosed where available
    cost_raw = (await db.execute(
        select(
            func.sum(
                TreatmentChemicalRecord.unit_cost * TreatmentChemicalRecord.quantity_dosed
            ).label("total_cost")
        ).where(
            _dtime_clause(TreatmentChemicalRecord.record_datetime, date_from, date_to),
            TreatmentChemicalRecord.unit_cost.is_not(None),
        )
    )).scalar()

    return ChemicalTreatmentReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_dosed=_DN(agg.total_dosed) if agg else None,
        total_cost=_DN(cost_raw),
        overdose_count=agg.overdose_cnt if agg else None,
        underdose_count=agg.underdose_cnt if agg else None,
        rows=rows,
        by_chemical=by_chemical,
        by_area=by_area,
    )


# ── 8. Solar Generation vs Consumption ───────────────────────────────────────

async def get_solar_generation_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> SolarGenerationReport:
    q = (
        select(
            func.date(SolarRecord.record_datetime).label("d"),
            UtilityAsset.asset_no.label("ano"),
            func.sum(SolarRecord.energy_generated_kwh).label("gen"),
            func.sum(SolarRecord.self_consumption_kwh).label("self_c"),
            func.sum(SolarRecord.grid_export_kwh).label("export"),
            func.avg(SolarRecord.irradiance_wm2).label("irr"),
            func.avg(SolarRecord.pr_ratio).label("pr"),
            func.avg(SolarRecord.inverter_efficiency_pct).label("inv_eff"),
            func.avg(SolarRecord.availability_pct).label("avail"),
            func.avg(SolarRecord.capacity_factor_pct).label("cap_f"),
        )
        .outerjoin(UtilityAsset, SolarRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(SolarRecord.record_datetime, date_from, date_to))
        .group_by(func.date(SolarRecord.record_datetime), UtilityAsset.asset_no)
        .order_by(func.date(SolarRecord.record_datetime).desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())

    rows_raw = (await db.execute(q.offset(skip).limit(limit))).all()

    # Get total electricity consumption per day for contribution calc
    elec_by_day = {}
    elec_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.quantity).label("kwh"),
        )
        .where(
            _date_clause(UtilityTransaction.transaction_date, date_from, date_to),
            UtilityTransaction.utility_type == UtilityType.ELECTRICITY,
        )
        .group_by(UtilityTransaction.transaction_date)
    )).all()
    for r in elec_raw:
        elec_by_day[str(r.d)] = _D(r.kwh)

    rows = []
    for r in rows_raw:
        d_str = str(r.d)
        total_elec = elec_by_day.get(d_str)
        contrib = _safe_pct(r.gen, total_elec) if total_elec and r.gen else None
        rows.append(SolarGenerationRow(
            date=d_str,
            asset_no=r.ano,
            energy_generated_kwh=_DN(r.gen),
            self_consumption_kwh=_DN(r.self_c),
            grid_export_kwh=_DN(r.export),
            irradiance_wm2=_R(r.irr),
            pr_ratio=_R(r.pr, 4),
            inverter_efficiency_pct=_R(r.inv_eff),
            availability_pct=_R(r.avail),
            capacity_factor_pct=_R(r.cap_f),
            total_elec_consumption_kwh=total_elec,
            solar_contribution_pct=contrib,
        ))

    agg = (await db.execute(
        select(
            func.sum(SolarRecord.energy_generated_kwh).label("gen"),
            func.sum(SolarRecord.self_consumption_kwh).label("self_c"),
            func.sum(SolarRecord.grid_export_kwh).label("export"),
            func.avg(SolarRecord.pr_ratio).label("pr"),
        ).where(_dtime_clause(SolarRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    total_elec_period = sum(elec_by_day.values()) or None
    avg_contrib = _safe_pct(agg.gen, total_elec_period) if agg and agg.gen and total_elec_period else None

    trend = sorted(
        [TrendPoint(date=r.date, value=r.energy_generated_kwh, value2=r.total_elec_consumption_kwh) for r in rows],
        key=lambda x: x.date,
    )

    return SolarGenerationReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_generated_kwh=_DN(agg.gen) if agg else None,
        total_self_consumption_kwh=_DN(agg.self_c) if agg else None,
        total_grid_export_kwh=_DN(agg.export) if agg else None,
        avg_pr_ratio=_R(agg.pr, 4) if agg else None,
        avg_contribution_pct=avg_contrib,
        rows=rows,
        trend=trend,
    )


# ── 9. Wastewater Compliance ──────────────────────────────────────────────────

async def get_wastewater_compliance_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    asset_no: Optional[str] = None,
    process_stage: Optional[str] = None,
    shift_ref: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> WastewaterComplianceReport:
    q = (
        select(WastewaterRecord, UtilityAsset.asset_no.label("ano"))
        .outerjoin(UtilityAsset, WastewaterRecord.asset_id == UtilityAsset.id)
        .where(_dtime_clause(WastewaterRecord.record_datetime, date_from, date_to))
        .order_by(WastewaterRecord.record_datetime.desc())
    )
    if asset_no:
        q = q.where(UtilityAsset.asset_no == asset_no.upper())
    if process_stage:
        q = q.where(WastewaterRecord.process_stage == process_stage)
    if shift_ref:
        q = q.where(WastewaterRecord.shift_ref == shift_ref)

    records = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = []
    for r in records:
        ww = r.WastewaterRecord
        cod_rem = _safe_pct(
            _D(ww.influent_cod_mgl) - _D(ww.effluent_cod_mgl),
            ww.influent_cod_mgl,
        ) if ww.influent_cod_mgl and float(ww.influent_cod_mgl) > 0 else None
        rows.append(WastewaterComplianceRow(
            record_no=ww.record_no,
            asset_no=r.ano,
            record_datetime=str(ww.record_datetime)[:19],
            process_stage=str(ww.process_stage) if ww.process_stage else None,
            shift_ref=ww.shift_ref,
            influent_cod_mgl=_DN(ww.influent_cod_mgl),
            effluent_cod_mgl=_DN(ww.effluent_cod_mgl),
            cod_removal_pct=cod_rem,
            influent_bod_mgl=_DN(ww.influent_bod_mgl),
            effluent_bod_mgl=_DN(ww.effluent_bod_mgl),
            influent_tss_mgl=_DN(ww.influent_tss_mgl),
            effluent_tss_mgl=_DN(ww.effluent_tss_mgl),
            effluent_ph=_DN(ww.effluent_ph),
            do_mgl=_DN(ww.do_mgl),
            compliance_status=str(ww.compliance_status) if ww.compliance_status else None,
            permit_limit_ref=ww.permit_limit_ref,
            deviation_reason=ww.deviation_reason,
            power_consumed_kwh=_DN(ww.power_consumed_kwh),
            sludge_produced_kg=_DN(ww.sludge_produced_kg),
        ))

    # Compliance stats
    agg = (await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((WastewaterRecord.compliance_status == ComplianceStatus.COMPLIANT, 1))
            ).label("comp"),
            func.count(
                case((WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, 1))
            ).label("non_comp"),
            func.count(
                case((WastewaterRecord.compliance_status == ComplianceStatus.BORDERLINE, 1))
            ).label("border"),
            func.avg(
                case(
                    (WastewaterRecord.influent_cod_mgl > 0,
                     (WastewaterRecord.influent_cod_mgl - WastewaterRecord.effluent_cod_mgl)
                     / WastewaterRecord.influent_cod_mgl * 100),
                )
            ).label("avg_cod_rem"),
        ).where(_dtime_clause(WastewaterRecord.record_datetime, date_from, date_to))
    )).one_or_none()

    compliance_rate = _safe_pct(agg.comp, agg.total) if agg and agg.total else None

    trend_raw = (await db.execute(
        select(
            func.date(WastewaterRecord.record_datetime).label("d"),
            func.count(
                case((WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, 1))
            ).label("v"),
        )
        .where(_dtime_clause(WastewaterRecord.record_datetime, date_from, date_to))
        .group_by(func.date(WastewaterRecord.record_datetime))
        .order_by(func.date(WastewaterRecord.record_datetime))
    )).all()

    return WastewaterComplianceReport(
        date_from=str(date_from),
        date_to=str(date_to),
        compliant_count=agg.comp if agg else None,
        non_compliant_count=agg.non_comp if agg else None,
        borderline_count=agg.border if agg else None,
        compliance_rate_pct=compliance_rate,
        avg_cod_removal_pct=_R(agg.avg_cod_rem) if agg else None,
        rows=rows,
        trend=[TrendPoint(date=str(r.d), value=Decimal(str(r.v))) for r in trend_raw],
    )


# ── 10. Cost Allocation ───────────────────────────────────────────────────────

async def get_cost_allocation_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    group_by: str = "department",
    utility_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> CostAllocationReport:
    dim_col = {
        "department":     UtilityCostAllocation.department,
        "production_line": UtilityCostAllocation.production_line,
        "machine_ref":    UtilityCostAllocation.machine_ref,
        "batch_no":       UtilityCostAllocation.batch_no,
        "target_id":      UtilityCostAllocation.target_id,
    }.get(group_by, UtilityCostAllocation.department)

    q = (
        select(
            dim_col.label("dim"),
            UtilityCostAllocation.utility_type.label("utype"),
            func.sum(UtilityCostAllocation.allocated_cost).label("cost"),
            func.sum(UtilityCostAllocation.allocated_quantity).label("qty"),
            func.min(UtilityCostAllocation.quantity_unit).label("qunit"),
            func.avg(UtilityCostAllocation.cost_per_unit).label("cpu"),
            func.avg(UtilityCostAllocation.cost_per_ton).label("cpt"),
            func.sum(UtilityCostAllocation.production_volume_kg).label("prod_vol"),
            func.count().label("cnt"),
        )
        .where(_date_clause(UtilityCostAllocation.allocation_date, date_from, date_to))
        .group_by(dim_col, UtilityCostAllocation.utility_type)
        .order_by(func.sum(UtilityCostAllocation.allocated_cost).desc().nullslast())
    )
    if utility_type:
        q = q.where(UtilityCostAllocation.utility_type == utility_type)

    rows_raw = (await db.execute(q.offset(skip).limit(limit))).all()

    total_cost_all = sum(_D(r.cost) for r in rows_raw if r.cost) or Decimal("0")

    rows = [
        CostAllocationRow(
            dimension=r.dim or "Unspecified",
            utility_type=str(r.utype),
            allocated_cost=_DN(r.cost),
            allocated_quantity=_DN(r.qty),
            quantity_unit=r.qunit,
            cost_per_unit=_R(r.cpu),
            cost_per_ton=_R(r.cpt),
            production_volume_kg=_DN(r.prod_vol),
            allocation_count=r.cnt,
            pct_of_total=_safe_pct(r.cost, total_cost_all) if total_cost_all else None,
        )
        for r in rows_raw
    ]

    # By utility type breakdown
    by_ut_raw = (await db.execute(
        select(
            UtilityCostAllocation.utility_type.label("utype"),
            func.sum(UtilityCostAllocation.allocated_cost).label("cost"),
        )
        .where(_date_clause(UtilityCostAllocation.allocation_date, date_from, date_to))
        .group_by(UtilityCostAllocation.utility_type)
        .order_by(func.sum(UtilityCostAllocation.allocated_cost).desc().nullslast())
    )).all()

    total_ut = sum(_D(r.cost) for r in by_ut_raw if r.cost) or Decimal("0")
    by_utility = [
        DistributionSlice(
            label=str(r.utype),
            value=_DN(r.cost),
            pct=_safe_pct(r.cost, total_ut),
        )
        for r in by_ut_raw
    ]

    return CostAllocationReport(
        date_from=str(date_from),
        date_to=str(date_to),
        group_by=group_by,
        utility_type=utility_type,
        total_cost=total_cost_all or None,
        rows=rows,
        by_utility=by_utility,
    )


# ── 11. Base Load Analysis ─────────────────────────────────────────────────────

async def get_base_load_analysis(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    utility_type: Optional[str] = None,
) -> BaseLoadAnalysis:
    ut_filter = [UtilityTransaction.utility_type == utility_type] if utility_type else []

    # Get daily totals per utility type
    daily_raw = (await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
        )
        .where(
            _date_clause(UtilityTransaction.transaction_date, date_from, date_to),
            *ut_filter,
        )
        .group_by(UtilityTransaction.utility_type, UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.utility_type, UtilityTransaction.transaction_date)
    )).all()

    # Group by utility type
    by_ut: dict[str, list] = {}
    for r in daily_raw:
        k = str(r.utype)
        by_ut.setdefault(k, []).append((r.qty, r.uom, r.cost))

    rows = []
    for ut, values in by_ut.items():
        qtys = [float(v[0]) for v in values if v[0] is not None]
        if not qtys:
            continue
        qtys_sorted = sorted(qtys)
        n = len(qtys_sorted)
        p10 = qtys_sorted[max(0, int(n * 0.10) - 1)]
        p25 = qtys_sorted[max(0, int(n * 0.25) - 1)]
        p75 = qtys_sorted[min(n - 1, int(n * 0.75))]
        p90 = qtys_sorted[min(n - 1, int(n * 0.90))]
        base_load = p10
        mean_v = statistics.mean(qtys) if qtys else 0
        base_load_pct = _safe_pct(base_load, mean_v) if mean_v else None
        uom = values[0][1] if values else None

        rows.append(BaseLoadRow(
            utility_type=ut,
            unit=uom,
            min_daily=_R(min(qtys)),
            p10_daily=_R(p10),
            p25_daily=_R(p25),
            median_daily=_R(statistics.median(qtys)),
            mean_daily=_R(mean_v),
            p75_daily=_R(p75),
            p90_daily=_R(p90),
            max_daily=_R(max(qtys)),
            base_load_est=_R(base_load),
            base_load_pct=base_load_pct,
        ))

    # Trend for first utility type (or filtered)
    trend_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.quantity).label("v"),
        )
        .where(
            _date_clause(UtilityTransaction.transaction_date, date_from, date_to),
            *ut_filter,
        )
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all()

    return BaseLoadAnalysis(
        date_from=str(date_from),
        date_to=str(date_to),
        rows=rows,
        trend=[TrendPoint(date=str(r.d), value=_DN(r.v)) for r in trend_raw],
    )


# ── 12. Peak Demand Analysis ───────────────────────────────────────────────────

async def get_peak_demand_analysis(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    utility_type: Optional[str] = None,
    department: Optional[str] = None,
    top_n: int = 20,
) -> PeakDemandAnalysis:
    q = (
        select(
            UtilityTransaction.transaction_date.label("d"),
            UtilityTransaction.utility_type.label("utype"),
            UtilityTransaction.department.label("dept"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.bool_or(UtilityTransaction.is_anomaly).label("anom"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(
            UtilityTransaction.transaction_date,
            UtilityTransaction.utility_type,
            UtilityTransaction.department,
        )
        .order_by(func.sum(UtilityTransaction.quantity).desc().nullslast())
        .limit(top_n)
    )
    if utility_type:
        q = q.where(UtilityTransaction.utility_type == utility_type)
    if department:
        q = q.where(UtilityTransaction.department == department)

    rows_raw = (await db.execute(q)).all()

    top_days = [
        PeakDemandRow(
            date=str(r.d),
            utility_type=str(r.utype),
            department=r.dept,
            quantity=_DN(r.qty),
            unit=r.uom,
            total_cost=_DN(r.cost),
            is_anomaly=r.anom,
        )
        for r in rows_raw
    ]

    peak = top_days[0] if top_days else None

    trend_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.quantity).label("v"),
        )
        .where(
            _date_clause(UtilityTransaction.transaction_date, date_from, date_to),
            *([UtilityTransaction.utility_type == utility_type] if utility_type else []),
        )
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all()

    return PeakDemandAnalysis(
        date_from=str(date_from),
        date_to=str(date_to),
        utility_type=utility_type,
        peak_date=peak.date if peak else None,
        peak_value=peak.quantity if peak else None,
        peak_unit=peak.unit if peak else None,
        top_days=top_days,
        trend=[TrendPoint(date=str(r.d), value=_DN(r.v)) for r in trend_raw],
    )


# ── 13. Alarm Trend Report ─────────────────────────────────────────────────────

async def get_alarm_trend_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    utility_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> AlarmTrendReport:
    ev_q = (
        select(UtilityAlarmEvent)
        .where(_dtime_clause(UtilityAlarmEvent.triggered_at, date_from, date_to))
        .order_by(UtilityAlarmEvent.triggered_at.desc())
    )
    if utility_type:
        ev_q = ev_q.join(UtilityAlarmRule, UtilityAlarmEvent.rule_id == UtilityAlarmRule.id).\
            where(UtilityAlarmRule.utility_type == utility_type)

    # Trend: daily counts by severity
    sev_raw = (await db.execute(
        select(
            func.date(UtilityAlarmEvent.triggered_at).label("d"),
            UtilityAlarmEvent.severity.label("sev"),
            func.count().label("cnt"),
        )
        .where(_dtime_clause(UtilityAlarmEvent.triggered_at, date_from, date_to))
        .group_by(func.date(UtilityAlarmEvent.triggered_at), UtilityAlarmEvent.severity)
        .order_by(func.date(UtilityAlarmEvent.triggered_at))
    )).all()

    # Build daily map
    daily_map: dict[str, dict] = {}
    for r in sev_raw:
        d = str(r.d)
        daily_map.setdefault(d, {"CRITICAL": 0, "ALERT": 0, "WARNING": 0, "INFO": 0})
        daily_map[d][str(r.sev)] = r.cnt

    trend = [
        AlarmTrendRow(
            date=d,
            critical=v.get("CRITICAL", 0),
            alert=v.get("ALERT", 0),
            warning=v.get("WARNING", 0),
            info=v.get("INFO", 0),
            total=sum(v.values()),
        )
        for d, v in sorted(daily_map.items())
    ]

    # Totals
    agg = (await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((UtilityAlarmEvent.severity == AlarmSeverity.CRITICAL, 1))
            ).label("crit"),
            func.count(
                case((UtilityAlarmEvent.resolved_at.is_(None), 1))
            ).label("unresolved"),
        ).where(_dtime_clause(UtilityAlarmEvent.triggered_at, date_from, date_to))
    )).one_or_none()

    # Top rules
    top_rules_raw = (await db.execute(
        select(
            UtilityAlarmRule.rule_code.label("code"),
            UtilityAlarmRule.name.label("nm"),
            func.count(UtilityAlarmEvent.id).label("cnt"),
        )
        .join(UtilityAlarmEvent, UtilityAlarmEvent.rule_id == UtilityAlarmRule.id)
        .where(_dtime_clause(UtilityAlarmEvent.triggered_at, date_from, date_to))
        .group_by(UtilityAlarmRule.rule_code, UtilityAlarmRule.name)
        .order_by(func.count(UtilityAlarmEvent.id).desc())
        .limit(10)
    )).all()

    top_total = sum(r.cnt for r in top_rules_raw) or 1
    top_rules = [
        DistributionSlice(
            label=f"{r.code} — {r.nm}",
            value=Decimal(str(r.cnt)),
            pct=_safe_pct(r.cnt, top_total),
        )
        for r in top_rules_raw
    ]

    # Recent events
    recent_raw = (await db.execute(
        select(
            UtilityAlarmEvent,
            UtilityAlarmRule.rule_code.label("rcode"),
            UtilityAlarmRule.name.label("rname"),
            UtilityAlarmRule.utility_type.label("ut"),
            UtilityAsset.asset_no.label("ano"),
            UtilityDevice.device_code.label("dcode"),
        )
        .outerjoin(UtilityAlarmRule, UtilityAlarmEvent.rule_id == UtilityAlarmRule.id)
        .outerjoin(UtilityAsset, UtilityAlarmEvent.asset_id == UtilityAsset.id)
        .outerjoin(UtilityDevice, UtilityAlarmEvent.device_id == UtilityDevice.id)
        .where(_dtime_clause(UtilityAlarmEvent.triggered_at, date_from, date_to))
        .order_by(UtilityAlarmEvent.triggered_at.desc())
        .limit(limit)
        .offset(skip)
    )).all()

    recent = [
        AlarmDetailRow(
            event_no=r.UtilityAlarmEvent.event_no,
            rule_code=r.rcode,
            rule_name=r.rname,
            utility_type=str(r.ut) if r.ut else None,
            asset_no=r.ano,
            device_code=r.dcode,
            severity=str(r.UtilityAlarmEvent.severity) if r.UtilityAlarmEvent.severity else None,
            triggered_at=str(r.UtilityAlarmEvent.triggered_at)[:19],
            status=str(r.UtilityAlarmEvent.status) if r.UtilityAlarmEvent.status else None,
            triggered_value=_DN(r.UtilityAlarmEvent.triggered_value),
            threshold_value=_DN(r.UtilityAlarmEvent.threshold_value),
            parameter=r.UtilityAlarmEvent.parameter,
        )
        for r in recent_raw
    ]

    return AlarmTrendReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_events=agg.total if agg else None,
        critical_count=agg.crit if agg else None,
        unresolved_count=agg.unresolved if agg else None,
        trend=trend,
        top_rules=top_rules,
        recent=recent,
    )


# ── 14. Abnormal Consumption ───────────────────────────────────────────────────

async def get_abnormal_consumption_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    utility_type: Optional[str] = None,
    department: Optional[str] = None,
    deviation_threshold_pct: float = 30.0,
    skip: int = 0,
    limit: int = 200,
) -> AbnormalConsumptionReport:
    # Calculate mean baseline from the preceding 30 days
    baseline_from = date_from - timedelta(days=30)
    baseline_to = date_from - timedelta(days=1)

    # Per-utility-type daily avg over baseline period
    baseline_raw = (await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("total"),
            func.count(distinct(UtilityTransaction.transaction_date)).label("days"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, baseline_from, baseline_to))
        .group_by(UtilityTransaction.utility_type)
    )).all()

    baselines = {
        str(r.utype): float(_D(r.total) / max(r.days, 1))
        for r in baseline_raw
    }

    q = (
        select(
            UtilityTransaction.transaction_date.label("d"),
            UtilityTransaction.utility_type.label("utype"),
            UtilityTransaction.department.label("dept"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.min(UtilityTransaction.unit_of_measure).label("uom"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.bool_or(UtilityTransaction.is_anomaly).label("anom"),
            func.string_agg(UtilityTransaction.anomaly_note, "; ").label("anom_note"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(
            UtilityTransaction.transaction_date,
            UtilityTransaction.utility_type,
            UtilityTransaction.department,
        )
        .order_by(UtilityTransaction.transaction_date.desc())
    )
    if utility_type:
        q = q.where(UtilityTransaction.utility_type == utility_type)
    if department:
        q = q.where(UtilityTransaction.department == department)

    rows_raw = (await db.execute(q.offset(skip).limit(limit))).all()

    rows = []
    for r in rows_raw:
        baseline = baselines.get(str(r.utype))
        dev_pct = None
        if baseline and baseline > 0 and r.qty:
            dev_pct = _R((float(_D(r.qty)) - baseline) / baseline * 100)
        flagged = r.anom or (dev_pct is not None and abs(float(dev_pct)) > deviation_threshold_pct)
        if flagged or r.anom:
            rows.append(AbnormalConsumptionRow(
                date=str(r.d),
                utility_type=str(r.utype),
                department=r.dept,
                quantity=_DN(r.qty),
                unit=r.uom,
                mean_baseline=_R(baseline) if baseline else None,
                deviation_pct=dev_pct,
                total_cost=_DN(r.cost),
                is_anomaly=r.anom,
                anomaly_note=r.anom_note,
            ))

    high_dev_cnt = sum(
        1 for row in rows
        if row.deviation_pct is not None and abs(float(row.deviation_pct)) > deviation_threshold_pct
    )

    return AbnormalConsumptionReport(
        date_from=str(date_from),
        date_to=str(date_to),
        utility_type=utility_type,
        anomaly_count=sum(1 for r in rows if r.is_anomaly),
        high_deviation_count=high_dev_cnt,
        rows=rows,
    )


# ── 15. Sustainability Summary ─────────────────────────────────────────────────

async def get_sustainability_report(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
) -> SustainabilityReport:
    # Utility transaction aggregates
    tx_agg = (await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.utility_type)
    )).all()

    by_type = {str(r.utype): {"qty": _D(r.qty), "cost": _D(r.cost)} for r in tx_agg}

    elec_kwh = by_type.get("ELECTRICITY", {}).get("qty", Decimal("0"))
    solar_kwh = by_type.get("SOLAR", {}).get("qty", Decimal("0"))
    water_m3 = by_type.get("WATER", {}).get("qty", Decimal("0"))
    proc_water_m3 = by_type.get("PROCESS_WATER", {}).get("qty", Decimal("0"))
    total_cost = sum(v["cost"] for v in by_type.values()) or Decimal("0")

    solar_pct = _safe_pct(solar_kwh, elec_kwh + solar_kwh) if (elec_kwh + solar_kwh) > 0 else None

    # Wastewater compliance rate
    ww_agg = (await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((WastewaterRecord.compliance_status == ComplianceStatus.COMPLIANT, 1))
            ).label("comp"),
        ).where(_dtime_clause(WastewaterRecord.record_datetime, date_from, date_to))
    )).one_or_none()
    ww_compliance = _safe_pct(ww_agg.comp, ww_agg.total) if ww_agg and ww_agg.total else None

    # Wastewater volume treated
    ww_vol = (await db.execute(
        select(func.sum(WastewaterRecord.influent_flow_m3h * WastewaterRecord.aeration_runtime_hours).label("vol"))
        .where(_dtime_clause(WastewaterRecord.record_datetime, date_from, date_to))
    )).scalar()

    # Carbon estimate: grid electricity × 0.7 kgCO2e/kWh (standard UK/Africa grid factor)
    grid_elec = elec_kwh - solar_kwh if elec_kwh >= solar_kwh else elec_kwh
    co2e = _R(grid_elec * Decimal("0.7")) if grid_elec > 0 else None

    # Daily trend: total cost
    trend_raw = (await db.execute(
        select(
            UtilityTransaction.transaction_date.label("d"),
            func.sum(UtilityTransaction.total_cost).label("v"),
        )
        .where(_date_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all()

    metrics = [
        SustainabilityMetric(label="Total Electricity", value=elec_kwh or None, unit="kWh"),
        SustainabilityMetric(label="Solar Generation", value=solar_kwh or None, unit="kWh"),
        SustainabilityMetric(label="Solar Share", value=solar_pct, unit="%"),
        SustainabilityMetric(label="Total Water Consumed", value=water_m3 + proc_water_m3 or None, unit="m³"),
        SustainabilityMetric(label="Wastewater Compliance", value=ww_compliance, unit="%"),
        SustainabilityMetric(label="Est. CO₂e Emissions", value=co2e, unit="kg"),
        SustainabilityMetric(label="Total Utility Cost", value=total_cost or None, unit="$"),
    ]

    return SustainabilityReport(
        date_from=str(date_from),
        date_to=str(date_to),
        total_electricity_kwh=elec_kwh or None,
        solar_kwh=solar_kwh or None,
        solar_pct=solar_pct,
        total_water_m3=water_m3 + proc_water_m3 or None,
        process_water_m3=proc_water_m3 or None,
        wastewater_treated_m3=_DN(ww_vol),
        compliance_rate_pct=ww_compliance,
        total_utility_cost=total_cost or None,
        estimated_co2e_kg=co2e,
        metrics=metrics,
        trend=[TrendPoint(date=str(r.d), value=_DN(r.v)) for r in trend_raw],
    )
