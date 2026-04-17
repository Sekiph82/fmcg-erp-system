"""
Water Management Service
────────────────────────────────────────────────────────────────────────────────
Aggregation queries for water utility types:
  WATER         – raw intake transactions
  PROCESS_WATER – process / treated consumption
  WASTEWATER    – drain / effluent

All data is read from utility_transactions.
No writes happen here — creation / mutation goes through
utility_transaction_service.create_transaction().
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Integer, cast, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import UtilityTransaction, UtilityType
from app.schemas.water import (
    WaterBreakdown,
    WaterBreakdownRow,
    WaterKPIs,
    WaterTrendPoint,
)

logger = logging.getLogger(__name__)

_WATER   = UtilityType.WATER
_PROCESS = UtilityType.PROCESS_WATER
_WASTE   = UtilityType.WASTEWATER


def _water_clauses(
    *,
    utility_type: UtilityType,
    date_from:     Optional[date],
    date_to:       Optional[date],
    department:    Optional[str],
    building_area: Optional[str],
    line_id:       Optional[str],
    machine_id:    Optional[str],
    shift_id:      Optional[str],
) -> list:
    c = [UtilityTransaction.utility_type == utility_type]
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


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


async def _agg(
    db: AsyncSession,
    *,
    utility_type: UtilityType,
    date_from:    Optional[date],
    date_to:      Optional[date],
    department:   Optional[str],
    building_area: Optional[str],
    line_id:      Optional[str],
    machine_id:   Optional[str],
    shift_id:     Optional[str],
):
    """Run a single-type aggregate query, returns the raw row."""
    where = _water_clauses(
        utility_type=utility_type,
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )
    return (await db.execute(
        select(
            func.sum(UtilityTransaction.quantity).label("total_m3"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly,  Integer)).label("anomaly_count"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("estimated_count"),
        ).where(and_(*where))
    )).one()


# ── Public API ────────────────────────────────────────────────────────────────


async def get_water_kpis(
    db: AsyncSession,
    *,
    date_from:    Optional[date] = None,
    date_to:      Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
) -> WaterKPIs:
    """Return aggregated water KPIs using 3 async DB queries (one per type)."""
    kw = dict(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )

    r_in   = await _agg(db, utility_type=_WATER,   **kw)
    r_proc = await _agg(db, utility_type=_PROCESS, **kw)
    r_ww   = await _agg(db, utility_type=_WASTE,   **kw)

    water_in   = _dec(r_in.total_m3)
    process_m3 = _dec(r_proc.total_m3)
    waste_m3   = _dec(r_ww.total_m3)

    balance_m3 = water_in - waste_m3 if water_in else None
    loss_m3    = water_in - process_m3 - waste_m3 if water_in else None
    loss_pct   = (
        Decimal(str(round(loss_m3 / water_in * 100, 2)))
        if (loss_m3 is not None and water_in > 0) else None
    )
    recovery_pct = (
        Decimal(str(round(process_m3 / water_in * 100, 2)))
        if water_in > 0 else None
    )

    total_m3 = water_in
    total_cost = _dec(r_in.total_cost) + _dec(r_proc.total_cost) + _dec(r_ww.total_cost)
    total_cost = total_cost or None

    tx_count       = int((r_in.tx_count or 0) + (r_proc.tx_count or 0) + (r_ww.tx_count or 0))
    anomaly_count  = int((r_in.anomaly_count or 0) + (r_proc.anomaly_count or 0) + (r_ww.anomaly_count or 0))
    estimated_count = int((r_in.estimated_count or 0) + (r_proc.estimated_count or 0) + (r_ww.estimated_count or 0))

    # Derive date range from date_from/to params (we don't have actual_from/to in multi-type queries)
    days = 1
    if date_from and date_to:
        days = max(1, (date_to - date_from).days + 1)
    elif date_from or date_to:
        days = 30  # approximate when only one bound given

    avg_m3_day   = (total_m3 / days) if total_m3 else None
    avg_cost_day = (total_cost / days) if total_cost else None
    avg_cost_m3  = (total_cost / total_m3) if (total_cost and total_m3) else None
    estimated_pct = (
        Decimal(str(round(estimated_count / tx_count * 100, 2))) if tx_count else None
    )

    return WaterKPIs(
        date_from=date_from,
        date_to=date_to,
        water_in_m3=water_in,
        process_m3=process_m3,
        wastewater_m3=waste_m3,
        balance_m3=balance_m3,
        loss_m3=loss_m3,
        loss_pct=loss_pct,
        recovery_pct=recovery_pct,
        avg_m3_per_day=avg_m3_day,
        total_cost=total_cost,
        avg_cost_per_day=avg_cost_day,
        avg_cost_per_m3=avg_cost_m3,
        tx_count=tx_count,
        anomaly_count=anomaly_count,
        estimated_count=estimated_count,
        estimated_pct=estimated_pct,
    )


async def get_water_daily_trend(
    db: AsyncSession,
    *,
    date_from:    Optional[date] = None,
    date_to:      Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
) -> List[WaterTrendPoint]:
    """
    Daily aggregation across all 3 water utility types.
    Returns one WaterTrendPoint per date present in the data.
    """
    kw = dict(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )

    def _daily_q(utility_type: UtilityType):
        where = _water_clauses(utility_type=utility_type, **kw)
        return (
            select(
                UtilityTransaction.transaction_date.label("tx_date"),
                func.sum(UtilityTransaction.quantity).label("total_m3"),
                func.sum(UtilityTransaction.total_cost).label("total_cost"),
                func.count().label("tx_count"),
                func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
            )
            .where(and_(*where))
            .group_by(UtilityTransaction.transaction_date)
        )

    rows_in   = list((await db.execute(_daily_q(_WATER))).all())
    rows_proc = list((await db.execute(_daily_q(_PROCESS))).all())
    rows_ww   = list((await db.execute(_daily_q(_WASTE))).all())

    # Merge by date
    by_date: dict = {}
    for r in rows_in:
        by_date.setdefault(r.tx_date, {})["in"]   = r
    for r in rows_proc:
        by_date.setdefault(r.tx_date, {})["proc"] = r
    for r in rows_ww:
        by_date.setdefault(r.tx_date, {})["ww"]   = r

    result = []
    for d in sorted(by_date.keys()):
        m = by_date[d]
        r_in   = m.get("in")
        r_proc = m.get("proc")
        r_ww   = m.get("ww")

        total_cost_day = (
            _dec(r_in.total_cost if r_in else None)
            + _dec(r_proc.total_cost if r_proc else None)
            + _dec(r_ww.total_cost if r_ww else None)
        ) or None

        result.append(WaterTrendPoint(
            date=d,
            water_in_m3=_dec(r_in.total_m3 if r_in else None),
            process_m3= _dec(r_proc.total_m3 if r_proc else None),
            wastewater_m3=_dec(r_ww.total_m3 if r_ww else None),
            total_cost=total_cost_day,
            anomaly_count=int(
                (r_in.anomaly_count or 0 if r_in else 0)
                + (r_proc.anomaly_count or 0 if r_proc else 0)
                + (r_ww.anomaly_count or 0 if r_ww else 0)
            ),
            tx_count=int(
                (r_in.tx_count or 0 if r_in else 0)
                + (r_proc.tx_count or 0 if r_proc else 0)
                + (r_ww.tx_count or 0 if r_ww else 0)
            ),
        ))

    return result


async def get_water_breakdown(
    db: AsyncSession,
    *,
    dimension: str,
    date_from:    Optional[date] = None,
    date_to:      Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
    water_type:    str = "WATER",          # which utility_type to break down
) -> WaterBreakdown:
    """
    GROUP BY a single dimension for a specified water type.
    dimension ∈ {department, line, machine, building_area, shift}
    water_type ∈ {WATER, PROCESS_WATER, WASTEWATER}
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

    try:
        ut = UtilityType(water_type)
    except ValueError:
        ut = _WATER

    where = _water_clauses(
        utility_type=ut,
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
            func.sum(UtilityTransaction.quantity).label("total_m3"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*where))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
    )).all())

    grand = sum(_dec(r.total_m3) for r in rows) or Decimal("1")
    result_rows = [
        WaterBreakdownRow(
            dimension=dimension,
            group_key=r.group_key,
            label=r.group_key or f"(no {dimension})",
            total_m3=_dec(r.total_m3),
            pct_of_total=Decimal(str(round(_dec(r.total_m3) / grand * 100, 2))),
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            tx_count=int(r.tx_count or 0),
            anomaly_count=int(r.anomaly_count or 0),
        )
        for r in rows
    ]
    return WaterBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total_m3=grand,
    )
