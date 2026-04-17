"""
Compressor & Compressed Air Service
────────────────────────────────────────────────────────────────────────────────
Aggregation queries over compressor_records for KPI reporting and trend charts.

KPIs derived from compressor_records (operational detail).
Cost data (air_cost_per_nm3) uses utility_transactions (COMPRESSED_AIR type)
and is fetched by the endpoint before being passed in.

Anomaly thresholds:
  specific_energy_kwh_nm3 > 0.12   → flag_poor_efficiency
  idle_run_ratio > 20 %             → flag_high_idle
  avg_leak_pct > 5 %                → flag_leak_detected
  night_pct > 15 %                  → flag_high_night
  avg_pressure_drop > 0.3 bar       → flag_pressure_drop
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, cast, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    CompressorRecord, CompressorStatus,
    UtilityTransaction, UtilityType,
)
from app.schemas.compressor import (
    AirBreakdown,
    AirBreakdownRow,
    AirKPIs,
    AirShiftPoint,
    AirTrendPoint,
)

logger = logging.getLogger(__name__)

POOR_EFFICIENCY_THRESHOLD = Decimal("0.12")   # kWh/Nm³
HIGH_IDLE_THRESHOLD        = Decimal("20")     # %
LEAK_THRESHOLD             = Decimal("5")      # %
NIGHT_THRESHOLD            = Decimal("15")     # %
PRESSURE_DROP_THRESHOLD    = Decimal("0.3")    # bar


# ── Helpers ───────────────────────────────────────────────────────────────────

def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _d_opt(v) -> Optional[Decimal]:
    return Decimal(str(v)) if v is not None else None


def _rnd(v, dp: int = 2) -> Optional[Decimal]:
    return Decimal(str(round(v, dp))) if v is not None else None


def _clauses(
    *,
    asset_id:    Optional[UUID],
    department:  Optional[str],
    shift_ref:   Optional[str],
    date_from:   Optional[date],
    date_to:     Optional[date],
    prod_line:   Optional[str] = None,
) -> list:
    c = []
    if asset_id:
        c.append(CompressorRecord.asset_id == asset_id)
    if department:
        c.append(CompressorRecord.department == department)
    if shift_ref:
        c.append(CompressorRecord.shift_ref == shift_ref)
    if prod_line:
        c.append(CompressorRecord.production_line == prod_line)
    if date_from:
        c.append(CompressorRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        c.append(CompressorRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))
    return c


# ── Public API ────────────────────────────────────────────────────────────────

async def get_air_kpis(
    db: AsyncSession,
    *,
    asset_id:         Optional[UUID]    = None,
    department:       Optional[str]     = None,
    shift_ref:        Optional[str]     = None,
    date_from:        Optional[date]    = None,
    date_to:          Optional[date]    = None,
    prod_line:        Optional[str]     = None,
    air_cost_total:   Optional[Decimal] = None,
) -> AirKPIs:
    clauses = _clauses(asset_id=asset_id, department=department, shift_ref=shift_ref,
                       date_from=date_from, date_to=date_to, prod_line=prod_line)
    where = and_(*clauses) if clauses else True

    agg = (await db.execute(
        select(
            func.sum(CompressorRecord.air_generated_nm3).label("air_nm3"),
            func.sum(CompressorRecord.electricity_used_kwh).label("elec_kwh"),
            func.sum(CompressorRecord.runtime_hours).label("runtime"),
            func.sum(CompressorRecord.load_time_hours).label("load_hrs"),
            func.sum(CompressorRecord.unload_time_hours).label("unload_hrs"),
            func.sum(CompressorRecord.idle_time_hours).label("idle_hrs"),
            func.avg(CompressorRecord.discharge_pressure_bar).label("avg_disc"),
            func.avg(CompressorRecord.system_pressure_bar).label("avg_sys"),
            func.avg(CompressorRecord.receiver_tank_pressure_bar).label("avg_rcvr"),
            func.avg(CompressorRecord.line_pressure_bar).label("avg_line"),
            func.avg(CompressorRecord.dryer_dew_point_c).label("avg_dryer_dp"),
            func.avg(CompressorRecord.leak_estimation_pct).label("avg_leak"),
            func.sum(CompressorRecord.leak_volume_nm3).label("total_leak_nm3"),
            func.sum(CompressorRecord.night_idle_kwh).label("night_kwh"),
            func.sum(CompressorRecord.night_idle_nm3).label("night_nm3"),
            func.sum(CompressorRecord.start_stop_count).label("starts"),
            func.count().label("cnt"),
            func.sum(cast(CompressorRecord.is_anomaly, Integer)).label("anomaly_cnt"),
            func.sum(cast(CompressorRecord.maintenance_flag, Integer)).label("maint_cnt"),
            func.sum(cast(CompressorRecord.leak_test_done, Integer)).label("leak_tests"),
        ).where(where)
    )).one()

    air_nm3    = _d(agg.air_nm3)
    elec_kwh   = _d(agg.elec_kwh)
    runtime    = _d_opt(agg.runtime)
    load_hrs   = _d_opt(agg.load_hrs)
    unload_hrs = _d_opt(agg.unload_hrs)
    idle_hrs   = _d_opt(agg.idle_hrs)

    # Specific energy
    specific = (elec_kwh / air_nm3) if air_nm3 > 0 else None
    if specific is not None:
        specific = _rnd(specific, 4)

    # Utilisation KPIs
    utilization_pct = None
    idle_run_ratio  = None
    if runtime and runtime > 0:
        if load_hrs:
            utilization_pct = _rnd(load_hrs / runtime * 100, 1)
        if idle_hrs:
            idle_run_ratio = _rnd(idle_hrs / runtime * 100, 1)

    # Pressure drop
    avg_disc = _d_opt(agg.avg_disc)
    avg_line = _d_opt(agg.avg_line)
    pressure_drop = None
    if avg_disc is not None and avg_line is not None:
        pressure_drop = _rnd(avg_disc - avg_line, 3)

    # Leak
    avg_leak      = _rnd(agg.avg_leak, 2)
    total_leak_nm3 = _d_opt(agg.total_leak_nm3)

    # Night consumption
    night_kwh = _d_opt(agg.night_kwh)
    night_pct = None
    if night_kwh and elec_kwh > 0:
        night_pct = _rnd(night_kwh / elec_kwh * 100, 1)

    # Cost
    air_cost_per_nm3 = None
    if air_cost_total and air_nm3 > 0:
        air_cost_per_nm3 = _rnd(air_cost_total / air_nm3, 6)

    # Anomaly flags
    flag_high_idle       = bool(idle_run_ratio is not None and idle_run_ratio > HIGH_IDLE_THRESHOLD)
    flag_leak_detected   = bool(avg_leak is not None and avg_leak > LEAK_THRESHOLD)
    flag_pressure_drop   = bool(pressure_drop is not None and pressure_drop > PRESSURE_DROP_THRESHOLD)
    flag_high_night      = bool(night_pct is not None and night_pct > NIGHT_THRESHOLD)
    flag_poor_efficiency = bool(specific is not None and specific > POOR_EFFICIENCY_THRESHOLD)

    return AirKPIs(
        date_from=date_from,
        date_to=date_to,
        total_air_nm3=air_nm3,
        total_electricity_kwh=elec_kwh,
        specific_energy_kwh_nm3=specific,
        total_runtime_hours=runtime,
        total_load_hours=load_hrs,
        total_unload_hours=unload_hrs,
        total_idle_hours=idle_hrs,
        utilization_pct=utilization_pct,
        idle_run_ratio=idle_run_ratio,
        avg_discharge_pressure_bar=_rnd(agg.avg_disc, 3),
        avg_system_pressure_bar=_rnd(agg.avg_sys, 3),
        avg_receiver_pressure_bar=_rnd(agg.avg_rcvr, 3),
        avg_line_pressure_bar=_rnd(agg.avg_line, 3),
        avg_pressure_drop_bar=pressure_drop,
        avg_dryer_dew_point_c=_rnd(agg.avg_dryer_dp, 1),
        leak_test_count=int(agg.leak_tests or 0),
        avg_leak_pct=avg_leak,
        total_leak_nm3=total_leak_nm3,
        total_night_kwh=night_kwh,
        night_pct=night_pct,
        air_cost_total=air_cost_total,
        air_cost_per_nm3=air_cost_per_nm3,
        record_count=int(agg.cnt or 0),
        anomaly_count=int(agg.anomaly_cnt or 0),
        maintenance_count=int(agg.maint_cnt or 0),
        start_stop_total=int(agg.starts or 0),
        flag_high_idle=flag_high_idle,
        flag_leak_detected=flag_leak_detected,
        flag_pressure_drop=flag_pressure_drop,
        flag_high_night=flag_high_night,
        flag_poor_efficiency=flag_poor_efficiency,
    )


async def get_air_daily_trend(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    department: Optional[str]  = None,
    shift_ref:  Optional[str]  = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
    prod_line:  Optional[str]  = None,
) -> List[AirTrendPoint]:
    """Daily GROUP BY aggregation for trend charts."""
    clauses = _clauses(asset_id=asset_id, department=department, shift_ref=shift_ref,
                       date_from=date_from, date_to=date_to, prod_line=prod_line)
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            func.date(CompressorRecord.record_datetime).label("day"),
            func.sum(CompressorRecord.air_generated_nm3).label("air_nm3"),
            func.sum(CompressorRecord.electricity_used_kwh).label("elec_kwh"),
            func.sum(CompressorRecord.load_time_hours).label("load_hrs"),
            func.sum(CompressorRecord.idle_time_hours).label("idle_hrs"),
            func.sum(CompressorRecord.night_idle_kwh).label("night_kwh"),
            func.avg(CompressorRecord.discharge_pressure_bar).label("avg_disc"),
            func.avg(CompressorRecord.line_pressure_bar).label("avg_line"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("avg_se"),
            func.sum(cast(CompressorRecord.is_anomaly, Integer)).label("anomaly"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(func.date(CompressorRecord.record_datetime))
        .order_by(func.date(CompressorRecord.record_datetime))
    )).all())

    result = []
    for r in rows:
        result.append(AirTrendPoint(
            date=str(r.day),
            air_nm3=_d(r.air_nm3),
            electricity_kwh=_d(r.elec_kwh),
            load_hours=_d(r.load_hrs),
            idle_hours=_d(r.idle_hrs),
            night_kwh=_d(r.night_kwh),
            avg_discharge_bar=_rnd(r.avg_disc, 3),
            avg_line_bar=_rnd(r.avg_line, 3),
            avg_specific_energy=_rnd(r.avg_se, 4),
            anomaly_count=int(r.anomaly or 0),
            record_count=int(r.cnt or 0),
        ))
    return result


async def get_air_shift_analysis(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    department: Optional[str]  = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
) -> List[AirShiftPoint]:
    """Per-shift aggregation."""
    clauses = _clauses(asset_id=asset_id, department=department, shift_ref=None,
                       date_from=date_from, date_to=date_to)
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            CompressorRecord.shift_ref.label("shift_id"),
            func.sum(CompressorRecord.air_generated_nm3).label("air_nm3"),
            func.sum(CompressorRecord.electricity_used_kwh).label("elec_kwh"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("avg_se"),
            func.count().label("cnt"),
            func.sum(cast(CompressorRecord.is_anomaly, Integer)).label("anomaly"),
        )
        .where(where)
        .group_by(CompressorRecord.shift_ref)
        .order_by(CompressorRecord.shift_ref.nulls_last())
    )).all())

    return [
        AirShiftPoint(
            shift_id=r.shift_id,
            label=r.shift_id or "(unassigned)",
            air_nm3=_d(r.air_nm3),
            electricity_kwh=_d(r.elec_kwh),
            avg_specific_energy=_rnd(r.avg_se, 4),
            record_count=int(r.cnt or 0),
            anomaly_count=int(r.anomaly or 0),
        )
        for r in rows
    ]


async def get_air_breakdown(
    db: AsyncSession,
    *,
    dimension: str,
    asset_id:  Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
    department: Optional[str] = None,
) -> AirBreakdown:
    """
    GROUP BY a single dimension from utility_transactions (COMPRESSED_AIR).
    dimension ∈ {department, line, machine, building_area, shift}
    """
    _DIM_MAP = {
        "department":    UtilityTransaction.department,
        "line":          UtilityTransaction.production_line,
        "machine":       UtilityTransaction.machine_ref,
        "building_area": UtilityTransaction.building_area,
        "shift":         UtilityTransaction.shift_ref,
    }
    if dimension not in _DIM_MAP:
        dimension = "department"
    dim_col = _DIM_MAP[dimension]

    clauses = [UtilityTransaction.utility_type == UtilityType.COMPRESSED_AIR]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    if department and dimension != "department":
        clauses.append(UtilityTransaction.department == department)

    rows = list((await db.execute(
        select(
            dim_col.label("group_key"),
            func.sum(UtilityTransaction.quantity).label("total_nm3"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
        )
        .where(and_(*clauses))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
    )).all())

    grand = sum(_d(r.total_nm3) for r in rows) or Decimal("1")
    result_rows = [
        AirBreakdownRow(
            dimension=dimension,
            group_key=r.group_key,
            label=r.group_key or f"(no {dimension})",
            total_nm3=_d(r.total_nm3),
            total_cost=_d_opt(r.total_cost),
            pct_of_total=_rnd(_d(r.total_nm3) / grand * 100, 2),
            tx_count=int(r.tx_count or 0),
        )
        for r in rows
    ]
    return AirBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total_nm3=grand,
    )
