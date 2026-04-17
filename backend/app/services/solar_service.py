"""
Solar Energy Service
────────────────────────────────────────────────────────────────────────────────
Aggregation queries for the SOLAR utility type.

Data sources:
  1. utility_transactions (utility_type = SOLAR) — generation volume & cost
  2. solar_records — irradiance, DC/AC, self-consumption, grid export, PR ratio

No writes happen here — creation / mutation goes through
utility_transaction_service.create_transaction() and crud.solar.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, cast, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import SolarRecord, UtilityTransaction, UtilityType
from app.schemas.solar import (
    SolarBreakdown,
    SolarBreakdownRow,
    SolarKPIs,
    SolarTrendPoint,
)

logger = logging.getLogger(__name__)

_SOLAR = UtilityType.SOLAR


# ── Internal helpers ──────────────────────────────────────────────────────────


def _solar_tx_clauses(
    *,
    date_from:     Optional[date],
    date_to:       Optional[date],
    department:    Optional[str],
    building_area: Optional[str],
    line_id:       Optional[str],
    machine_id:    Optional[str],
    shift_id:      Optional[str],
) -> list:
    c = [UtilityTransaction.utility_type == _SOLAR]
    if date_from:
        c.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        c.append(UtilityTransaction.transaction_date <= date_to)
    if department:
        c.append(UtilityTransaction.department == department)
    if building_area:
        c.append(UtilityTransaction.building_area == building_area)
    if line_id:
        c.append(UtilityTransaction.production_line == line_id)
    if machine_id:
        c.append(UtilityTransaction.machine_ref == machine_id)
    if shift_id:
        c.append(UtilityTransaction.shift_ref == shift_id)
    return c


def _solar_rec_clauses(
    *,
    asset_id:  Optional[UUID],
    date_from: Optional[date],
    date_to:   Optional[date],
) -> list:
    from datetime import datetime as dt
    c = []
    if asset_id:
        c.append(SolarRecord.asset_id == asset_id)
    if date_from:
        c.append(SolarRecord.record_datetime >= dt.combine(date_from, dt.min.time()))
    if date_to:
        c.append(SolarRecord.record_datetime <= dt.combine(date_to, dt.max.time()))
    return c


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


# ── Public API ────────────────────────────────────────────────────────────────


async def get_kpis(
    db: AsyncSession,
    *,
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
    asset_id:      Optional[UUID] = None,
) -> SolarKPIs:
    tx_where = _solar_tx_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )

    # ── Transaction aggregate (generation volume & cost) ────────────────────
    agg = (await db.execute(
        select(
            func.sum(UtilityTransaction.quantity).label("total_generated"),
            func.max(UtilityTransaction.quantity).label("peak_generated"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
            func.min(UtilityTransaction.transaction_date).label("actual_from"),
            func.max(UtilityTransaction.transaction_date).label("actual_to"),
        ).where(and_(*tx_where))
    )).one()

    total_generated = _dec(agg.total_generated)
    peak_kwh        = _dec(agg.peak_generated) if agg.peak_generated else None
    total_cost      = _dec(agg.total_cost) if agg.total_cost else None
    tx_count        = int(agg.tx_count or 0)
    anomaly_count   = int(agg.anomaly_count or 0)

    df = date_from or agg.actual_from
    dt = date_to   or agg.actual_to
    days = max(1, (dt - df).days + 1) if df and dt else 1

    avg_gen_day  = (total_generated / days) if total_generated else None
    avg_cost_kwh = (total_cost / total_generated) if (total_cost and total_generated) else None

    # ── SolarRecord aggregate (self-consumption, export, performance) ────────
    rec_where = _solar_rec_clauses(asset_id=asset_id, date_from=date_from, date_to=date_to)
    rec_agg = (await db.execute(
        select(
            func.sum(SolarRecord.self_consumption_kwh).label("self_consumed"),
            func.sum(SolarRecord.grid_export_kwh).label("grid_export"),
            func.avg(SolarRecord.pr_ratio).label("avg_pr"),
            func.avg(SolarRecord.inverter_efficiency_pct).label("avg_eff"),
            func.avg(SolarRecord.capacity_factor_pct).label("avg_cf"),
            func.count().label("rec_count"),
        ).where(and_(*rec_where) if rec_where else True)
    )).one()

    self_consumed = _dec(rec_agg.self_consumed) if rec_agg.self_consumed else None
    grid_export   = _dec(rec_agg.grid_export) if rec_agg.grid_export else None
    avg_pr        = _dec(rec_agg.avg_pr) if rec_agg.avg_pr else None
    avg_eff       = _dec(rec_agg.avg_eff) if rec_agg.avg_eff else None
    avg_cf        = _dec(rec_agg.avg_cf) if rec_agg.avg_cf else None
    rec_count     = int(rec_agg.rec_count or 0)

    self_ratio = None
    if self_consumed and total_generated and total_generated > 0:
        self_ratio = Decimal(str(round(float(self_consumed) / float(total_generated) * 100, 2)))

    solar_contribution_pct = None
    if avg_cf:
        solar_contribution_pct = avg_cf

    return SolarKPIs(
        date_from=date_from,
        date_to=date_to,
        total_generated_kwh=total_generated,
        avg_generated_kwh_per_day=avg_gen_day,
        peak_generation_kwh=peak_kwh,
        total_self_consumption_kwh=self_consumed,
        total_grid_export_kwh=grid_export,
        self_consumption_ratio=self_ratio,
        solar_contribution_pct=solar_contribution_pct,
        avg_pr_ratio=avg_pr,
        avg_inverter_efficiency_pct=avg_eff,
        avg_capacity_factor_pct=avg_cf,
        total_cost_offset=total_cost,
        avg_cost_per_kwh=avg_cost_kwh,
        tx_count=tx_count,
        record_count=rec_count,
        anomaly_count=anomaly_count,
    )


async def get_daily_trend(
    db: AsyncSession,
    *,
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
    asset_id:      Optional[UUID] = None,
) -> List[SolarTrendPoint]:
    tx_where = _solar_tx_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )
    tx_rows = list((await db.execute(
        select(
            UtilityTransaction.transaction_date.label("tx_date"),
            func.sum(UtilityTransaction.quantity).label("total_generated"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*tx_where))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all())

    # Pull daily solar-record aggregates for self-consumption, export, pr
    from datetime import datetime as dt
    rec_where = _solar_rec_clauses(asset_id=asset_id, date_from=date_from, date_to=date_to)
    rec_rows = list((await db.execute(
        select(
            func.date(SolarRecord.record_datetime).label("rec_date"),
            func.sum(SolarRecord.self_consumption_kwh).label("self_consumed"),
            func.sum(SolarRecord.grid_export_kwh).label("grid_export"),
            func.avg(SolarRecord.pr_ratio).label("avg_pr"),
        )
        .where(and_(*rec_where) if rec_where else True)
        .group_by(func.date(SolarRecord.record_datetime))
        .order_by(func.date(SolarRecord.record_datetime))
    )).all())

    rec_map = {r.rec_date: r for r in rec_rows}

    result = []
    for r in tx_rows:
        rec = rec_map.get(r.tx_date)
        result.append(SolarTrendPoint(
            date=r.tx_date,
            total_generated_kwh=_dec(r.total_generated),
            grid_export_kwh=_dec(rec.grid_export) if rec and rec.grid_export else None,
            self_consumption_kwh=_dec(rec.self_consumed) if rec and rec.self_consumed else None,
            avg_pr_ratio=_dec(rec.avg_pr) if rec and rec.avg_pr else None,
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            anomaly_count=int(r.anomaly_count or 0),
            tx_count=int(r.tx_count or 0),
        ))
    return result


async def get_breakdown(
    db: AsyncSession,
    *,
    dimension: str,
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
) -> SolarBreakdown:
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

    tx_where = _solar_tx_clauses(
        date_from=date_from, date_to=date_to,
        department=None if dimension == "department" else department,
        building_area=None if dimension == "building_area" else building_area,
        line_id=None if dimension == "line" else line_id,
        machine_id=None if dimension == "machine" else machine_id,
        shift_id=None if dimension == "shift" else shift_id,
    )
    rows = list((await db.execute(
        select(
            dim_col.label("group_key"),
            func.sum(UtilityTransaction.quantity).label("total_generated"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*tx_where))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
    )).all())

    grand = sum(_dec(r.total_generated) for r in rows) or Decimal("1")
    result_rows = [
        SolarBreakdownRow(
            dimension=dimension,
            group_key=r.group_key,
            label=r.group_key or f"(no {dimension})",
            total_generated_kwh=_dec(r.total_generated),
            pct_of_total=Decimal(str(round(_dec(r.total_generated) / grand * 100, 2))),
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            tx_count=int(r.tx_count or 0),
            anomaly_count=int(r.anomaly_count or 0),
        )
        for r in rows
    ]
    return SolarBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total_generated_kwh=grand,
    )
