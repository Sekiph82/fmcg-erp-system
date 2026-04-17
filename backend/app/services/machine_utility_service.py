"""
Machine Utility Consumption Mapping — Service Layer
────────────────────────────────────────────────────
KPI aggregation, trend charts, and breakdown analysis over
machine_consumption_records.

KPI thresholds:
  HIGH_VARIANCE_PCT   = 15 %  → flag_high_variance
  STANDBY_WASTE_PCT   = 20 %  → flag_standby_waste
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, cast, distinct, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    MachineConsumptionRecord,
    UtilityType,
)
from app.schemas.machine_utility import (
    MachineUtilityBreakdown,
    MachineUtilityBreakdownRow,
    MachineUtilityKPIs,
    MachineUtilityTrendPoint,
)

logger = logging.getLogger(__name__)

HIGH_VARIANCE_PCT = Decimal("15")
STANDBY_WASTE_PCT = Decimal("20")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _d_opt(v) -> Optional[Decimal]:
    return Decimal(str(v)) if v is not None else None


def _rnd(v, dp: int = 2) -> Optional[Decimal]:
    return Decimal(str(round(float(v), dp))) if v is not None else None


def _clauses(
    *,
    work_center_id:  Optional[UUID],
    machine_ref:     Optional[str],
    utility_type:    Optional[str],
    production_line: Optional[str],
    department:      Optional[str],
    shift_ref:       Optional[str],
    date_from:       Optional[date],
    date_to:         Optional[date],
    batch_no:        Optional[str],
) -> list:
    c = []
    if work_center_id:
        c.append(MachineConsumptionRecord.work_center_id == work_center_id)
    if machine_ref:
        c.append(MachineConsumptionRecord.machine_ref == machine_ref)
    if utility_type:
        try:
            c.append(MachineConsumptionRecord.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if production_line:
        c.append(MachineConsumptionRecord.production_line == production_line)
    if department:
        c.append(MachineConsumptionRecord.department == department)
    if shift_ref:
        c.append(MachineConsumptionRecord.shift_ref == shift_ref)
    if date_from:
        c.append(MachineConsumptionRecord.record_date >= date_from)
    if date_to:
        c.append(MachineConsumptionRecord.record_date <= date_to)
    if batch_no:
        c.append(MachineConsumptionRecord.batch_no == batch_no)
    return c


# ── Public API ────────────────────────────────────────────────────────────────

async def get_machine_utility_kpis(
    db: AsyncSession,
    *,
    work_center_id:  Optional[UUID] = None,
    machine_ref:     Optional[str]  = None,
    utility_type:    Optional[str]  = None,
    production_line: Optional[str]  = None,
    department:      Optional[str]  = None,
    shift_ref:       Optional[str]  = None,
    date_from:       Optional[date] = None,
    date_to:         Optional[date] = None,
    batch_no:        Optional[str]  = None,
) -> MachineUtilityKPIs:
    clauses = _clauses(
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        department=department, shift_ref=shift_ref,
        date_from=date_from, date_to=date_to, batch_no=batch_no,
    )
    where = and_(*clauses) if clauses else True

    agg = (await db.execute(
        select(
            func.sum(MachineConsumptionRecord.actual_consumption).label("total_cons"),
            func.sum(MachineConsumptionRecord.runtime_hours).label("total_runtime"),
            func.sum(MachineConsumptionRecord.total_cost).label("total_cost"),
            func.avg(MachineConsumptionRecord.cost_rate).label("avg_cost_rate"),
            func.avg(MachineConsumptionRecord.variance_pct).label("avg_variance"),
            # Standby consumption
            func.sum(
                MachineConsumptionRecord.actual_consumption
                * cast(MachineConsumptionRecord.is_standby, Integer)
            ).label("standby_cons"),
            # Distinct batch count (non-null)
            func.count(distinct(MachineConsumptionRecord.batch_no)).label("batch_cnt"),
            # Distinct production order count
            func.count(distinct(MachineConsumptionRecord.production_order_id)).label("order_cnt"),
            # Record counts
            func.count().label("cnt"),
            func.sum(cast(MachineConsumptionRecord.is_anomaly, Integer)).label("anomaly_cnt"),
            # Per-utility-type helpers (sub-queries below)
            func.max(MachineConsumptionRecord.actual_unit).label("unit"),
        ).where(where)
    )).one()

    total_cons    = _d(agg.total_cons)
    total_runtime = _d_opt(agg.total_runtime)
    total_cost    = _d_opt(agg.total_cost)
    standby_cons  = _d_opt(agg.standby_cons) or Decimal("0")
    batch_cnt     = int(agg.batch_cnt or 0)
    order_cnt     = int(agg.order_cnt or 0)
    record_cnt    = int(agg.cnt or 0)
    anomaly_cnt   = int(agg.anomaly_cnt or 0)
    avg_variance  = _rnd(agg.avg_variance, 2)

    # KPI 1 — electricity per runtime hour
    electricity_per_h = None
    if utility_type in (None, "ELECTRICITY"):
        elec_clauses = [*clauses, MachineConsumptionRecord.utility_type == UtilityType.ELECTRICITY]
        elec_agg = (await db.execute(
            select(
                func.sum(MachineConsumptionRecord.actual_consumption).label("elec"),
                func.sum(MachineConsumptionRecord.runtime_hours).label("hrs"),
            ).where(and_(*elec_clauses) if elec_clauses else True)
        )).one_or_none()
        if elec_agg and elec_agg.elec and elec_agg.hrs and float(elec_agg.hrs) > 0:
            electricity_per_h = _rnd(_d(elec_agg.elec) / _d(elec_agg.hrs), 4)

    # KPI 2 — water per batch
    water_per_batch = None
    if utility_type in (None, "WATER", "SOFT_WATER") and batch_cnt > 0:
        water_clauses = [
            *clauses,
            MachineConsumptionRecord.utility_type.in_([UtilityType.WATER, UtilityType.SOFT_WATER]),
            MachineConsumptionRecord.batch_no.isnot(None),
        ]
        water_agg = (await db.execute(
            select(
                func.sum(MachineConsumptionRecord.actual_consumption).label("water"),
                func.count(distinct(MachineConsumptionRecord.batch_no)).label("batches"),
            ).where(and_(*water_clauses))
        )).one_or_none()
        if water_agg and water_agg.water and water_agg.batches and int(water_agg.batches) > 0:
            water_per_batch = _rnd(_d(water_agg.water) / Decimal(str(water_agg.batches)), 3)

    # KPI 3 — compressed air per batch
    air_per_batch = None
    if utility_type in (None, "COMPRESSED_AIR") and batch_cnt > 0:
        air_clauses = [
            *clauses,
            MachineConsumptionRecord.utility_type == UtilityType.COMPRESSED_AIR,
            MachineConsumptionRecord.batch_no.isnot(None),
        ]
        air_agg = (await db.execute(
            select(
                func.sum(MachineConsumptionRecord.actual_consumption).label("air"),
                func.count(distinct(MachineConsumptionRecord.batch_no)).label("batches"),
            ).where(and_(*air_clauses))
        )).one_or_none()
        if air_agg and air_agg.air and air_agg.batches and int(air_agg.batches) > 0:
            air_per_batch = _rnd(_d(air_agg.air) / Decimal(str(air_agg.batches)), 3)

    # KPI 4 — standby %
    standby_pct = None
    if total_cons > 0 and standby_cons > 0:
        standby_pct = _rnd(standby_cons / total_cons * 100, 1)

    # KPI 5 — cost per batch
    cost_per_batch = None
    if total_cost and batch_cnt > 0:
        cost_per_batch = _rnd(total_cost / Decimal(str(batch_cnt)), 4)

    # Flags
    flag_high_variance = bool(avg_variance is not None and abs(avg_variance) > HIGH_VARIANCE_PCT)
    flag_standby_waste = bool(standby_pct is not None and standby_pct > STANDBY_WASTE_PCT)

    return MachineUtilityKPIs(
        date_from=date_from,
        date_to=date_to,
        machine_ref=machine_ref,
        utility_type=utility_type,
        total_consumption=total_cons,
        total_runtime_hours=total_runtime,
        total_standby_consumption=standby_cons if standby_cons > 0 else None,
        consumption_unit=agg.unit,
        electricity_per_runtime_h=electricity_per_h,
        water_per_batch=water_per_batch,
        air_per_batch=air_per_batch,
        standby_pct=standby_pct,
        cost_per_batch=cost_per_batch,
        total_cost=total_cost,
        avg_cost_rate=_rnd(agg.avg_cost_rate, 6),
        avg_variance_pct=avg_variance,
        record_count=record_cnt,
        batch_count=batch_cnt,
        order_count=order_cnt,
        anomaly_count=anomaly_cnt,
        flag_high_variance=flag_high_variance,
        flag_standby_waste=flag_standby_waste,
    )


async def get_machine_utility_trend(
    db: AsyncSession,
    *,
    work_center_id:  Optional[UUID] = None,
    machine_ref:     Optional[str]  = None,
    utility_type:    Optional[str]  = None,
    production_line: Optional[str]  = None,
    date_from:       Optional[date] = None,
    date_to:         Optional[date] = None,
) -> List[MachineUtilityTrendPoint]:
    clauses = _clauses(
        work_center_id=work_center_id, machine_ref=machine_ref,
        utility_type=utility_type, production_line=production_line,
        department=None, shift_ref=None,
        date_from=date_from, date_to=date_to, batch_no=None,
    )
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            MachineConsumptionRecord.record_date.label("day"),
            MachineConsumptionRecord.machine_ref.label("machine_ref"),
            MachineConsumptionRecord.utility_type.label("utype"),
            func.sum(MachineConsumptionRecord.actual_consumption).label("total_cons"),
            func.sum(
                MachineConsumptionRecord.actual_consumption
                * cast(MachineConsumptionRecord.is_standby, Integer)
            ).label("standby"),
            func.sum(MachineConsumptionRecord.runtime_hours).label("runtime"),
            func.sum(MachineConsumptionRecord.total_cost).label("cost"),
            func.count(distinct(MachineConsumptionRecord.batch_no)).label("batches"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(
            MachineConsumptionRecord.record_date,
            MachineConsumptionRecord.machine_ref,
            MachineConsumptionRecord.utility_type,
        )
        .order_by(MachineConsumptionRecord.record_date, MachineConsumptionRecord.machine_ref)
    )).all())

    return [
        MachineUtilityTrendPoint(
            date=str(r.day),
            machine_ref=r.machine_ref,
            utility_type=r.utype.value if hasattr(r.utype, "value") else str(r.utype),
            total_consumption=_d(r.total_cons),
            standby=_d(r.standby),
            runtime_hours=_d(r.runtime),
            total_cost=_d_opt(r.cost),
            batch_count=int(r.batches or 0),
            record_count=int(r.cnt or 0),
        )
        for r in rows
    ]


async def get_machine_utility_breakdown(
    db: AsyncSession,
    *,
    dimension: str,
    work_center_id:  Optional[UUID] = None,
    utility_type:    Optional[str]  = None,
    date_from:       Optional[date] = None,
    date_to:         Optional[date] = None,
) -> MachineUtilityBreakdown:
    """
    GROUP BY a dimension:
      machine     → group by machine_ref
      utility     → group by utility_type
      shift       → group by shift_ref
      line        → group by production_line
      department  → group by department
      standby     → split standby vs productive
    """
    _DIM_MAP = {
        "machine":    MachineConsumptionRecord.machine_ref,
        "utility":    MachineConsumptionRecord.utility_type,
        "shift":      MachineConsumptionRecord.shift_ref,
        "line":       MachineConsumptionRecord.production_line,
        "department": MachineConsumptionRecord.department,
    }
    if dimension not in _DIM_MAP:
        dimension = "machine"
    dim_col = _DIM_MAP[dimension]

    clauses = _clauses(
        work_center_id=work_center_id, machine_ref=None,
        utility_type=utility_type, production_line=None,
        department=None, shift_ref=None,
        date_from=date_from, date_to=date_to, batch_no=None,
    )
    if work_center_id:
        clauses.append(MachineConsumptionRecord.work_center_id == work_center_id)
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            dim_col.label("group_key"),
            func.sum(MachineConsumptionRecord.actual_consumption).label("total_cons"),
            func.sum(MachineConsumptionRecord.total_cost).label("total_cost"),
            func.sum(MachineConsumptionRecord.runtime_hours).label("runtime"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(dim_col)
        .order_by(func.sum(MachineConsumptionRecord.actual_consumption).desc())
    )).all())

    grand = sum(_d(r.total_cons) for r in rows) or Decimal("1")
    result_rows = [
        MachineUtilityBreakdownRow(
            group_key=r.group_key.value if hasattr(r.group_key, "value") else str(r.group_key) if r.group_key else None,
            label=(r.group_key.value if hasattr(r.group_key, "value") else str(r.group_key)) if r.group_key else f"(no {dimension})",
            total_consumption=_d(r.total_cons),
            total_cost=_d_opt(r.total_cost),
            pct_of_total=_rnd(_d(r.total_cons) / grand * 100, 2),
            runtime_hours=_d_opt(r.runtime),
            record_count=int(r.cnt or 0),
        )
        for r in rows
    ]
    return MachineUtilityBreakdown(
        dimension=dimension,
        rows=result_rows,
        grand_total=grand,
    )
