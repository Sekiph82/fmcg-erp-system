from __future__ import annotations

from typing import List, Optional
from datetime import date, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import (
    Asset, PMPlan, PMWorkOrder, BreakdownRecord, PMStatus, BreakdownStatus,
)
from app.models.production import DowntimeLog
from app.schemas.maintenance import MtbfMttrRow, DowntimeByMachineRow, OverduePMRow


async def compute_mtbf_mttr(db: AsyncSession) -> List[MtbfMttrRow]:
    """MTBF/MTTR per asset from BreakdownRecord table."""
    # Load all resolved breakdowns grouped by asset
    q = (
        select(
            BreakdownRecord.asset_id,
            func.count(BreakdownRecord.id).label("cnt"),
            func.sum(BreakdownRecord.downtime_minutes).label("total_dt"),
        )
        .where(BreakdownRecord.downtime_minutes.isnot(None))
        .group_by(BreakdownRecord.asset_id)
    )
    rows = (await db.execute(q)).all()

    # Get first/last breakdown dates per asset for MTBF calculation
    date_q = (
        select(
            BreakdownRecord.asset_id,
            func.min(BreakdownRecord.start_time).label("first_bd"),
            func.max(BreakdownRecord.start_time).label("last_bd"),
        )
        .group_by(BreakdownRecord.asset_id)
    )
    date_rows = {r.asset_id: r for r in (await db.execute(date_q)).all()}

    # Load asset details
    asset_ids = [r.asset_id for r in rows]
    assets = {}
    if asset_ids:
        asset_q = select(Asset).where(Asset.id.in_(asset_ids))
        assets = {a.id: a for a in (await db.execute(asset_q)).scalars().all()}

    result = []
    for row in rows:
        asset = assets.get(row.asset_id)
        if not asset:
            continue
        cnt = row.cnt or 0
        total_dt = int(row.total_dt or 0)
        mttr = total_dt / cnt if cnt > 0 else 0.0

        mtbf = None
        dr = date_rows.get(row.asset_id)
        if dr and dr.first_bd and dr.last_bd and cnt > 1:
            span_days = (dr.last_bd - dr.first_bd).days
            mtbf = round(span_days / (cnt - 1), 2)

        result.append(MtbfMttrRow(
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            line=asset.line,
            breakdown_count=cnt,
            total_downtime_minutes=total_dt,
            avg_downtime_minutes=round(mttr, 2),
            mtbf_days=mtbf,
        ))

    result.sort(key=lambda r: r.total_downtime_minutes, reverse=True)
    return result


async def compute_downtime_by_machine(db: AsyncSession) -> List[DowntimeByMachineRow]:
    """Aggregated downtime per machine, including open breakdowns."""
    q = (
        select(
            BreakdownRecord.asset_id,
            func.count(BreakdownRecord.id).label("cnt"),
            func.coalesce(func.sum(BreakdownRecord.downtime_minutes), 0).label("total_dt"),
            func.sum(
                func.cast(
                    BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR]),
                    type_=None,
                )
            ).label("open_cnt"),
        )
        .group_by(BreakdownRecord.asset_id)
    )
    rows = (await db.execute(q)).all()

    # Also pull in MES DowntimeLogs that have machine_id matching asset.asset_no
    mes_q = (
        select(
            DowntimeLog.machine_id,
            func.count(DowntimeLog.id).label("mes_cnt"),
            func.coalesce(func.sum(DowntimeLog.duration_minutes), 0).label("mes_dt"),
        )
        .where(DowntimeLog.machine_id.isnot(None))
        .group_by(DowntimeLog.machine_id)
    )
    mes_rows = {r.machine_id: r for r in (await db.execute(mes_q)).all()}

    asset_ids = [r.asset_id for r in rows]
    assets = {}
    if asset_ids:
        asset_q = select(Asset).where(Asset.id.in_(asset_ids))
        assets = {a.id: a for a in (await db.execute(asset_q)).scalars().all()}

    result = []
    for row in rows:
        asset = assets.get(row.asset_id)
        if not asset:
            continue
        # Add MES downtime if asset_no matches a machine_id in DowntimeLogs
        mes = mes_rows.get(asset.asset_no)
        extra_dt = int(mes.mes_dt) if mes else 0

        result.append(DowntimeByMachineRow(
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            line=asset.line,
            breakdown_count=int(row.cnt) + (int(mes.mes_cnt) if mes else 0),
            total_downtime_minutes=int(row.total_dt) + extra_dt,
            open_breakdowns=int(row.open_cnt or 0),
        ))

    result.sort(key=lambda r: r.total_downtime_minutes, reverse=True)
    return result


async def overdue_pm_list(db: AsyncSession) -> List[OverduePMRow]:
    """Plans where next_due_date < today and status is not completed."""
    today = date.today()
    q = (
        select(PMPlan)
        .options(selectinload(PMPlan.asset))
        .where(
            PMPlan.is_active == True,  # noqa: E712
            PMPlan.next_due_date < today,
        )
        .order_by(PMPlan.next_due_date)
    )
    plans = list((await db.execute(q)).scalars().all())

    result = []
    for p in plans:
        if not p.asset:
            continue
        days_overdue = (today - p.next_due_date).days if p.next_due_date else 0
        result.append(OverduePMRow(
            plan_id=str(p.id),
            asset_id=str(p.asset_id),
            asset_no=p.asset.asset_no,
            asset_name=p.asset.name,
            plan_name=p.name,
            frequency=p.frequency,
            next_due_date=p.next_due_date,
            days_overdue=days_overdue,
        ))

    return result


def next_wo_no(existing_count: int) -> str:
    return f"WO-{existing_count + 1:06d}"


def next_bd_no(existing_count: int) -> str:
    return f"BD-{existing_count + 1:06d}"
