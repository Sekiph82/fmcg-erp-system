"""
Steam & Boiler Service
────────────────────────────────────────────────────────────────────────────────
Aggregation queries over boiler_steam_records for KPI reporting and trend charts.

KPIs are derived from the operational log (BoilerSteamRecord), not from
utility_transactions, because steam volume/efficiency data lives in the
operational records.  Cost data (steam_cost_per_ton) requires a separate
call against utility_transactions (STEAM type) which is handled in the endpoint.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, cast, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import BoilerSteamRecord, BoilerStatus, UtilityTransaction, UtilityType
from app.schemas.steam import (
    SteamBreakdown,
    SteamBreakdownRow,
    SteamKPIs,
    SteamShiftPoint,
    SteamTrendPoint,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _d_opt(v) -> Optional[Decimal]:
    return Decimal(str(v)) if v is not None else None


def _boiler_clauses(
    *,
    asset_id:   Optional[UUID],
    department: Optional[str],
    shift_ref:  Optional[str],
    date_from:  Optional[date],
    date_to:    Optional[date],
) -> list:
    c = []
    if asset_id:
        c.append(BoilerSteamRecord.asset_id == asset_id)
    if department:
        c.append(BoilerSteamRecord.department == department)
    if shift_ref:
        c.append(BoilerSteamRecord.shift_ref == shift_ref)
    if date_from:
        c.append(BoilerSteamRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        c.append(BoilerSteamRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))
    return c


# ── Public API ────────────────────────────────────────────────────────────────


async def get_steam_kpis(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    department: Optional[str]  = None,
    shift_ref:  Optional[str]  = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
    # Cost from utility_transactions (passed in if caller fetches it)
    steam_cost_total: Optional[Decimal] = None,
) -> SteamKPIs:
    clauses = _boiler_clauses(
        asset_id=asset_id, department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to,
    )
    where = and_(*clauses) if clauses else True

    agg = (await db.execute(
        select(
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam_kg"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feedwater_m3"),
            func.sum(BoilerSteamRecord.condensate_returned_m3).label("condensate_m3"),
            func.sum(BoilerSteamRecord.blowdown_volume_litres).label("blowdown_l"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("fuel_total"),
            func.min(BoilerSteamRecord.fuel_unit).label("fuel_unit"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("avg_eff"),
            func.avg(BoilerSteamRecord.boiler_load_pct).label("avg_load"),
            func.avg(BoilerSteamRecord.flue_gas_temp_c).label("avg_flue"),
            func.avg(BoilerSteamRecord.o2_pct).label("avg_o2"),
            func.sum(BoilerSteamRecord.burner_runtime_hours).label("burner_hrs"),
            func.sum(BoilerSteamRecord.downtime_minutes).label("downtime_min"),
            func.sum(BoilerSteamRecord.start_stop_count).label("starts"),
            func.sum(BoilerSteamRecord.chemical_dosing_amount).label("chem_total"),
            func.count().label("record_count"),
            func.sum(cast(BoilerSteamRecord.is_anomaly, Integer)).label("anomaly_count"),
            func.sum(cast(BoilerSteamRecord.maintenance_flag, Integer)).label("maint_count"),
        ).where(where)
    )).one()

    steam_kg   = _d(agg.steam_kg)
    steam_tons = steam_kg / Decimal("1000") if steam_kg else Decimal("0")
    feedwater  = _d(agg.feedwater_m3)
    condensate = _d(agg.condensate_m3)
    blowdown_l = _d(agg.blowdown_l)
    fuel_total = _d(agg.fuel_total)

    # Per-ton intensity
    gas_per_ton   = (fuel_total / steam_tons) if steam_tons > 0 else None
    water_per_ton = (feedwater / steam_tons) if steam_tons > 0 else None

    # Recovery & losses
    condensate_pct = (
        Decimal(str(round(condensate / (steam_kg / Decimal("1000")) * 100, 2)))
        if steam_tons > 0 and condensate else None
    )
    blowdown_denom = feedwater * Decimal("1000") + blowdown_l
    blowdown_loss_pct = (
        Decimal(str(round(blowdown_l / blowdown_denom * 100, 2)))
        if blowdown_denom > 0 else None
    )

    # Efficiency
    avg_eff  = Decimal(str(round(agg.avg_eff, 2)))  if agg.avg_eff  is not None else None
    avg_load = Decimal(str(round(agg.avg_load, 1))) if agg.avg_load is not None else None
    avg_flue = Decimal(str(round(agg.avg_flue, 1))) if agg.avg_flue is not None else None
    avg_o2   = Decimal(str(round(agg.avg_o2, 2)))   if agg.avg_o2   is not None else None

    # Operational
    burner_hrs    = _d_opt(agg.burner_hrs)
    downtime_min  = int(agg.downtime_min or 0)
    downtime_hrs  = Decimal(str(round(downtime_min / 60, 3))) if downtime_min else None
    total_starts  = int(agg.starts or 0)
    chem_total    = _d_opt(agg.chem_total)

    # Availability: (period_hours - downtime_hours) / period_hours × 100
    availability_pct = None
    if burner_hrs and burner_hrs > 0 and downtime_hrs:
        available = burner_hrs - downtime_hrs
        availability_pct = Decimal(str(round(max(Decimal("0"), available) / burner_hrs * 100, 2)))
    elif burner_hrs:
        availability_pct = Decimal("100")

    # Cost KPIs
    steam_cost_per_ton = (
        steam_cost_total / steam_tons
        if (steam_cost_total and steam_tons > 0) else None
    )

    # Anomaly flags
    flag_low_condensate = bool(condensate_pct is not None and condensate_pct < 70)
    flag_high_blowdown  = bool(blowdown_loss_pct is not None and blowdown_loss_pct > 5)
    flag_low_efficiency = bool(avg_eff is not None and avg_eff < 80)

    return SteamKPIs(
        date_from=date_from,
        date_to=date_to,
        total_steam_generated_kg=steam_kg,
        total_steam_generated_tons=steam_tons,
        total_feedwater_m3=feedwater,
        total_condensate_m3=condensate,
        total_blowdown_litres=blowdown_l,
        total_fuel_consumed=fuel_total,
        fuel_unit=agg.fuel_unit,
        gas_per_ton_steam=gas_per_ton,
        water_per_ton_steam=water_per_ton,
        condensate_recovery_pct=condensate_pct,
        blowdown_loss_pct=blowdown_loss_pct,
        avg_efficiency_pct=avg_eff,
        avg_boiler_load_pct=avg_load,
        avg_flue_temp_c=avg_flue,
        avg_o2_pct=avg_o2,
        total_burner_hours=burner_hrs,
        total_downtime_hours=downtime_hrs,
        availability_pct=availability_pct,
        total_start_stops=total_starts,
        steam_cost_total=steam_cost_total,
        steam_cost_per_ton=steam_cost_per_ton,
        total_chemical_dosing=chem_total,
        record_count=int(agg.record_count or 0),
        anomaly_count=int(agg.anomaly_count or 0),
        maintenance_count=int(agg.maint_count or 0),
        flag_low_condensate=flag_low_condensate,
        flag_high_blowdown=flag_high_blowdown,
        flag_low_efficiency=flag_low_efficiency,
    )


async def get_steam_daily_trend(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    department: Optional[str]  = None,
    shift_ref:  Optional[str]  = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
) -> List[SteamTrendPoint]:
    """Daily GROUP BY aggregation for trend charts."""
    clauses = _boiler_clauses(
        asset_id=asset_id, department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to,
    )
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            func.date(BoilerSteamRecord.record_datetime).label("day"),
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam_kg"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("fuel"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feedwater"),
            func.sum(BoilerSteamRecord.condensate_returned_m3).label("condensate"),
            func.sum(BoilerSteamRecord.blowdown_volume_litres).label("blowdown"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("avg_eff"),
            func.avg(BoilerSteamRecord.boiler_load_pct).label("avg_load"),
            func.sum(BoilerSteamRecord.downtime_minutes).label("downtime"),
            func.sum(cast(BoilerSteamRecord.is_anomaly, Integer)).label("anomaly"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(func.date(BoilerSteamRecord.record_datetime))
        .order_by(func.date(BoilerSteamRecord.record_datetime))
    )).all())

    return [
        SteamTrendPoint(
            date=r.day,
            steam_generated_kg=_d(r.steam_kg),
            fuel_consumed=_d(r.fuel),
            feedwater_m3=_d(r.feedwater),
            condensate_m3=_d(r.condensate),
            blowdown_litres=_d(r.blowdown),
            avg_efficiency_pct=Decimal(str(round(r.avg_eff, 2))) if r.avg_eff else None,
            avg_boiler_load_pct=Decimal(str(round(r.avg_load, 1))) if r.avg_load else None,
            downtime_minutes=int(r.downtime or 0),
            anomaly_count=int(r.anomaly or 0),
            record_count=int(r.cnt or 0),
        )
        for r in rows
    ]


async def get_steam_shift_analysis(
    db: AsyncSession,
    *,
    asset_id:   Optional[UUID] = None,
    department: Optional[str]  = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
) -> List[SteamShiftPoint]:
    """Per-shift aggregation."""
    clauses = _boiler_clauses(
        asset_id=asset_id, department=department,
        shift_ref=None, date_from=date_from, date_to=date_to,
    )
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            BoilerSteamRecord.shift_ref.label("shift_id"),
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam_kg"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("fuel"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("avg_eff"),
            func.count().label("cnt"),
            func.sum(cast(BoilerSteamRecord.is_anomaly, Integer)).label("anomaly"),
        )
        .where(where)
        .group_by(BoilerSteamRecord.shift_ref)
        .order_by(BoilerSteamRecord.shift_ref.nulls_last())
    )).all())

    return [
        SteamShiftPoint(
            shift_id=r.shift_id,
            label=r.shift_id or "(unassigned)",
            steam_generated_kg=_d(r.steam_kg),
            fuel_consumed=_d(r.fuel),
            avg_efficiency_pct=Decimal(str(round(r.avg_eff, 2))) if r.avg_eff else None,
            record_count=int(r.cnt or 0),
            anomaly_count=int(r.anomaly or 0),
        )
        for r in rows
    ]


async def get_steam_breakdown(
    db: AsyncSession,
    *,
    dimension: str,
    asset_id:   Optional[UUID] = None,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
    department: Optional[str]  = None,
) -> SteamBreakdown:
    """
    GROUP BY a single dimension from utility_transactions (STEAM type).
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

    clauses = [UtilityTransaction.utility_type == UtilityType.STEAM]
    if date_from:
        clauses.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        clauses.append(UtilityTransaction.transaction_date <= date_to)
    if department and dimension != "department":
        clauses.append(UtilityTransaction.department == department)

    rows = list((await db.execute(
        select(
            dim_col.label("group_key"),
            func.sum(UtilityTransaction.quantity).label("total_kg"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
        )
        .where(and_(*clauses))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
    )).all())

    grand = sum(_d(r.total_kg) for r in rows) or Decimal("1")
    result_rows = [
        SteamBreakdownRow(
            dimension=dimension,
            group_key=r.group_key,
            label=r.group_key or f"(no {dimension})",
            total_kg=_d(r.total_kg),
            total_cost=_d_opt(r.total_cost),
            pct_of_total=Decimal(str(round(_d(r.total_kg) / grand * 100, 2))),
            tx_count=int(r.tx_count or 0),
        )
        for r in rows
    ]
    return SteamBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total_kg=grand,
    )
