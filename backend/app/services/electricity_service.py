"""
Electricity Service
────────────────────────────────────────────────────────────────────────────────
Aggregation queries for the ELECTRICITY utility type.

All data is read from the unified `utility_transactions` table
(utility_type = ELECTRICITY).  SOLAR transactions in the same window are
surfaced as solar_offset to support net-consumption reporting.

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
from app.schemas.electricity import (
    ElectricityBreakdown,
    ElectricityBreakdownRow,
    ElectricityKPIs,
    ElectricityShiftPoint,
    ElectricityTrendPoint,
)

logger = logging.getLogger(__name__)

_ELEC  = UtilityType.ELECTRICITY
_SOLAR = UtilityType.SOLAR

# ── Internal helpers ──────────────────────────────────────────────────────────


def _elec_clauses(
    *,
    date_from: Optional[date],
    date_to:   Optional[date],
    department:    Optional[str],
    building_area: Optional[str],
    line_id:       Optional[str],
    machine_id:    Optional[str],
    shift_id:      Optional[str],
    utility_type: UtilityType = _ELEC,
) -> list:
    """Build WHERE clauses scoped to electricity (or another utility type)."""
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


# ── Public API ────────────────────────────────────────────────────────────────


async def get_kpis(
    db: AsyncSession,
    *,
    date_from:    Optional[date] = None,
    date_to:      Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
) -> ElectricityKPIs:
    """
    Return aggregated KPIs for the scoped window.
    Runs 4 async DB queries: main aggregate, idle sub-set, solar offset, daily totals.
    """
    where = _elec_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )

    # ── Main aggregate ──────────────────────────────────────────────────────
    agg = (await db.execute(
        select(
            func.sum(UtilityTransaction.quantity).label("total_kwh"),
            func.max(UtilityTransaction.quantity).label("peak_kwh"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly,  Integer)).label("anomaly_count"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("estimated_count"),
            func.min(UtilityTransaction.transaction_date).label("actual_from"),
            func.max(UtilityTransaction.transaction_date).label("actual_to"),
        ).where(and_(*where))
    )).one()

    total_kwh      = _dec(agg.total_kwh)
    peak_kwh       = _dec(agg.peak_kwh) if agg.peak_kwh else None
    total_cost     = _dec(agg.total_cost) if agg.total_cost else None
    tx_count       = int(agg.tx_count or 0)
    anomaly_count  = int(agg.anomaly_count or 0)
    estimated_count = int(agg.estimated_count or 0)

    # Days in range
    df = date_from or agg.actual_from
    dt = date_to   or agg.actual_to
    days = max(1, (dt - df).days + 1) if df and dt else 1

    avg_kwh_day  = (total_kwh / days) if total_kwh else None
    avg_cost_day = (total_cost / days) if total_cost else None
    avg_cost_kwh = (total_cost / total_kwh) if (total_cost and total_kwh) else None
    estimated_pct = (
        Decimal(str(round(estimated_count / tx_count * 100, 2))) if tx_count else None
    )

    # ── Idle consumption (no production linkage) ────────────────────────────
    idle_where = where + [
        UtilityTransaction.production_line.is_(None),
        UtilityTransaction.machine_ref.is_(None),
        UtilityTransaction.batch_no.is_(None),
        UtilityTransaction.production_order_id.is_(None),
    ]
    idle_val = (await db.execute(
        select(func.sum(UtilityTransaction.quantity)).where(and_(*idle_where))
    )).scalar()
    idle_kwh = _dec(idle_val) if idle_val else None

    # ── Solar offset (SOLAR transactions, same date/dept/building scope) ─────
    solar_where = _elec_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=None, machine_id=None, shift_id=None,
        utility_type=_SOLAR,
    )
    solar_val = (await db.execute(
        select(func.sum(UtilityTransaction.quantity)).where(and_(*solar_where))
    )).scalar()
    solar_kwh = _dec(solar_val) if solar_val else None
    net_kwh   = (total_kwh - solar_kwh) if solar_kwh else None

    # ── Base load (avg of bottom 20th-percentile of daily totals) ────────────
    daily_vals = list((await db.execute(
        select(func.sum(UtilityTransaction.quantity).label("day_kwh"))
        .where(and_(*where))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(func.sum(UtilityTransaction.quantity))
    )).scalars().all())

    base_load_kwh = None
    if daily_vals:
        n = max(1, len(daily_vals) // 5)          # bottom 20 %
        bottom = [_dec(v) for v in daily_vals[:n]]
        base_load_kwh = sum(bottom) / len(bottom)

    return ElectricityKPIs(
        date_from=date_from,
        date_to=date_to,
        total_kwh=total_kwh,
        avg_kwh_per_day=avg_kwh_day,
        peak_demand_kwh=peak_kwh,
        base_load_kwh=base_load_kwh,
        idle_kwh=idle_kwh,
        solar_offset_kwh=solar_kwh,
        net_kwh=net_kwh,
        total_cost=total_cost,
        avg_cost_per_day=avg_cost_day,
        avg_cost_per_kwh=avg_cost_kwh,
        tx_count=tx_count,
        anomaly_count=anomaly_count,
        estimated_count=estimated_count,
        estimated_pct=estimated_pct,
        has_tariff_data=bool(total_cost),
    )


async def get_daily_trend(
    db: AsyncSession,
    *,
    date_from:    Optional[date] = None,
    date_to:      Optional[date] = None,
    department:    Optional[str] = None,
    building_area: Optional[str] = None,
    line_id:       Optional[str] = None,
    machine_id:    Optional[str] = None,
    shift_id:      Optional[str] = None,
) -> List[ElectricityTrendPoint]:
    """Daily GROUP BY aggregation for trend chart."""
    where = _elec_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=building_area,
        line_id=line_id, machine_id=machine_id, shift_id=shift_id,
    )
    rows = list((await db.execute(
        select(
            UtilityTransaction.transaction_date.label("tx_date"),
            func.sum(UtilityTransaction.quantity).label("total_kwh"),
            func.max(UtilityTransaction.quantity).label("peak_kwh"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*where))
        .group_by(UtilityTransaction.transaction_date)
        .order_by(UtilityTransaction.transaction_date)
    )).all())

    return [
        ElectricityTrendPoint(
            date=r.tx_date,
            total_kwh=_dec(r.total_kwh),
            peak_kwh=_dec(r.peak_kwh) if r.peak_kwh else None,
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            anomaly_count=int(r.anomaly_count or 0),
            tx_count=int(r.tx_count or 0),
        )
        for r in rows
    ]


async def get_shift_analysis(
    db: AsyncSession,
    *,
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
    department: Optional[str] = None,
    line_id:    Optional[str] = None,
) -> List[ElectricityShiftPoint]:
    """GROUP BY shift_ref for day/night/shift consumption analysis."""
    where = _elec_clauses(
        date_from=date_from, date_to=date_to,
        department=department, building_area=None,
        line_id=line_id, machine_id=None, shift_id=None,
    )
    rows = list((await db.execute(
        select(
            UtilityTransaction.shift_ref.label("shift_id"),
            func.sum(UtilityTransaction.quantity).label("total_kwh"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*where))
        .group_by(UtilityTransaction.shift_ref)
        .order_by(UtilityTransaction.shift_ref.nulls_last())
    )).all())

    return [
        ElectricityShiftPoint(
            shift_id=r.shift_id,
            label=r.shift_id or "(no shift / non-production)",
            total_kwh=_dec(r.total_kwh),
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            tx_count=int(r.tx_count or 0),
            anomaly_count=int(r.anomaly_count or 0),
        )
        for r in rows
    ]


async def get_breakdown(
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
) -> ElectricityBreakdown:
    """
    GROUP BY a single dimension.
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

    # Clear the dimension we're grouping by so it doesn't filter itself out
    where = _elec_clauses(
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
            func.sum(UtilityTransaction.quantity).label("total_kwh"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.count().label("tx_count"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anomaly_count"),
        )
        .where(and_(*where))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
    )).all())

    grand = sum(_dec(r.total_kwh) for r in rows) or Decimal("1")
    result_rows = [
        ElectricityBreakdownRow(
            dimension=dimension,
            group_key=r.group_key,
            label=r.group_key or f"(no {dimension})",
            total_kwh=_dec(r.total_kwh),
            pct_of_total=Decimal(str(round(_dec(r.total_kwh) / grand * 100, 2))),
            total_cost=_dec(r.total_cost) if r.total_cost else None,
            tx_count=int(r.tx_count or 0),
            anomaly_count=int(r.anomaly_count or 0),
        )
        for r in rows
    ]
    return ElectricityBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total_kwh=grand,
    )
