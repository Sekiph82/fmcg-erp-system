"""
True Finite Capacity Scheduling Engine.

Algorithm:
  1. Load all MPS lines for the scenario's MPS plan (or all POs if no plan)
  2. For each line → look up routing steps via product recipe → create OperationQueue entries
  3. Sort operations by (priority DESC, period_start ASC, product_code ASC) — ATCS rule
  4. For each op, look up ResourceCalendar for the work center; fall back to 8h Mon-Sat
  5. Greedy forward placement: scan calendar days until enough hours accumulate
  6. Build CapacityLoadSnapshot per (wc, date) aggregated hourly slots
  7. Detect overloads; mark ops BLOCKED if no room found in horizon
"""
from __future__ import annotations
import random
import string
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.planning import (
    PlanningScenario, OperationQueue, CapacityLoadSnapshot, ResourceCalendar,
    ChangeoverMatrix, OpQueueStatus, CapacitySlotType,
)
from app.models.mps import MPSLine
from app.models.production_advanced import WorkCenter, Routing, RoutingStep
from app.models.master import Product


_D = lambda v: Decimal(str(v))
_DEFAULT_HOURS = Decimal("8")
_DEFAULT_RATE = Decimal("100")   # units/hr fallback


def _op_no() -> str:
    sfx = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"OP-{sfx}"


def _working_days(start: date, end: date) -> List[date]:
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 6:   # Mon-Sat
            days.append(cur)
        cur += timedelta(days=1)
    return days


async def _calendar_hours(db: AsyncSession, wc_id: UUID, d: date) -> Decimal:
    r = await db.execute(
        select(ResourceCalendar).where(
            ResourceCalendar.work_center_id == wc_id,
            ResourceCalendar.calendar_date == d,
        )
    )
    cal = r.scalar_one_or_none()
    if cal and not cal.is_holiday and not cal.is_maintenance:
        return _D(cal.available_hours)
    if cal and (cal.is_holiday or cal.is_maintenance):
        return Decimal("0")
    # default: Mon-Sat = 8h, Sun = 0h
    return _DEFAULT_HOURS if d.weekday() < 6 else Decimal("0")


async def _get_changeover(
    db: AsyncSession, wc_id: UUID, from_fam: Optional[str], to_fam: Optional[str]
) -> int:
    if not from_fam or not to_fam or from_fam == to_fam:
        return 0
    r = await db.execute(
        select(ChangeoverMatrix).where(
            ChangeoverMatrix.work_center_id == wc_id,
            ChangeoverMatrix.from_family == from_fam,
            ChangeoverMatrix.to_family == to_fam,
            ChangeoverMatrix.is_active == True,
        )
    )
    row = r.scalar_one_or_none()
    return row.changeover_minutes if row else 0


def _product_family(code: Optional[str]) -> str:
    if code and len(code) >= 4:
        return code[:4].upper()
    return "MISC"


def _product_display(product: Optional[Product]) -> tuple[Optional[str], Optional[str]]:
    if not product:
        return None, None
    return product.name, product.sku


def _work_center_rate(work_center: Optional[WorkCenter]) -> Decimal:
    if work_center and work_center.capacity:
        return _D(work_center.capacity)
    return _DEFAULT_RATE


def _operation_minutes(planned_qty: Decimal, step: Optional[RoutingStep], rate: Decimal) -> int:
    if step and step.standard_time_minutes:
        return int(step.standard_time_minutes)
    return int(float(planned_qty or 0) / float(rate) * 60) if rate > 0 else 0


async def run_capacity_scheduling(db: AsyncSession, scenario_id: UUID) -> dict:
    scenario_r = await db.execute(
        select(PlanningScenario).where(PlanningScenario.id == scenario_id)
    )
    scenario: PlanningScenario = scenario_r.scalar_one_or_none()
    if not scenario:
        raise ValueError("Scenario not found")

    # Clear previous ops + snapshots
    await db.execute(delete(OperationQueue).where(OperationQueue.scenario_id == scenario_id))
    await db.execute(delete(CapacityLoadSnapshot).where(CapacityLoadSnapshot.scenario_id == scenario_id))
    await db.flush()

    horizon_start = scenario.horizon_start or date.today()
    horizon_end = scenario.horizon_end or (horizon_start + timedelta(days=30))

    # Load MPS lines if linked
    ops_to_schedule: List[dict] = []

    if scenario.mps_plan_id:
        lines_r = await db.execute(
            select(MPSLine)
            .options(selectinload(MPSLine.product), selectinload(MPSLine.work_center))
            .where(MPSLine.mps_id == scenario.mps_plan_id)
            .order_by(MPSLine.priority_score.desc(), MPSLine.period_start)
        )
        lines = lines_r.scalars().all()

        for line in lines:
            # Find routing for product
            routing_r = await db.execute(
                select(Routing).where(Routing.product_id == line.product_id, Routing.is_active == True)
            )
            routing = routing_r.scalar_one_or_none()

            if routing:
                steps_r = await db.execute(
                    select(RoutingStep)
                    .options(selectinload(RoutingStep.work_center))
                    .where(RoutingStep.routing_id == routing.id)
                    .order_by(RoutingStep.step_number)
                )
                steps = steps_r.scalars().all()
            else:
                steps = []

            if steps:
                for step in steps:
                    wc_id = step.work_center_id
                    product_name, product_code = _product_display(line.product)
                    rate = _work_center_rate(step.work_center)
                    setup_min = step.setup_time_minutes or (step.work_center.setup_time_min if step.work_center else 0) or 0
                    run_min = _operation_minutes(line.planned_production_qty, step, rate)
                    ops_to_schedule.append({
                        "mps_line_id": line.id,
                        "product_id": line.product_id,
                        "product_name": product_name,
                        "product_code": product_code,
                        "work_center_id": wc_id,
                        "routing_step_id": step.id,
                        "step_name": step.operation,
                        "planned_qty": line.planned_production_qty,
                        "rate_per_hour": rate,
                        "setup_minutes": setup_min,
                        "run_minutes": run_min,
                        "cleanup_minutes": 0,
                        "priority": int(line.priority_score or 50),
                        "period_start": line.period_start or horizon_start,
                        "period_end": line.period_end or horizon_end,
                    })
            else:
                # No routing — create one generic op on the line's work center
                wc_id = line.work_center_id
                product_name, product_code = _product_display(line.product)
                rate = _work_center_rate(line.work_center)
                run_min = _operation_minutes(line.planned_production_qty, None, rate)
                ops_to_schedule.append({
                    "mps_line_id": line.id,
                    "product_id": line.product_id,
                    "product_name": product_name,
                    "product_code": product_code,
                    "work_center_id": wc_id,
                    "routing_step_id": None,
                    "step_name": "Production",
                    "planned_qty": line.planned_production_qty,
                    "rate_per_hour": rate,
                    "setup_minutes": 0,
                    "run_minutes": run_min,
                    "cleanup_minutes": 0,
                    "priority": int(line.priority_score or 50),
                    "period_start": line.period_start or horizon_start,
                    "period_end": line.period_end or horizon_end,
                })

    # slot_map: {(wc_id, date): allocated_hours}
    slot_map: Dict[Tuple, Decimal] = {}
    changeover_map: Dict[Tuple, Decimal] = {}  # {(wc_id, date): changeover_hours}
    last_family_on_wc: Dict[UUID, str] = {}

    scheduled = 0
    blocked = 0
    created_ops = []

    for op_data in ops_to_schedule:
        wc_id: Optional[UUID] = op_data["work_center_id"]
        total_run_min = op_data["setup_minutes"] + op_data["run_minutes"] + op_data["cleanup_minutes"]
        total_hrs_needed = Decimal(str(total_run_min)) / Decimal("60")

        # Changeover
        from_fam = last_family_on_wc.get(wc_id)
        to_fam = _product_family(op_data.get("product_code"))
        co_min = await _get_changeover(db, wc_id, from_fam, to_fam) if wc_id else 0
        co_hrs = Decimal(str(co_min)) / Decimal("60")
        total_with_co = total_hrs_needed + co_hrs

        # Find placement date
        period_start = op_data.get("period_start") or horizon_start
        if isinstance(period_start, str):
            period_start = date.fromisoformat(period_start)

        placed = False
        scheduled_start_dt = None
        scheduled_end_dt = None
        block_reason = None

        if not wc_id:
            block_reason = "No work center assigned"
        else:
            accumulated = Decimal("0")
            work_days = _working_days(period_start, horizon_end)
            for wd in work_days:
                avail = await _calendar_hours(db, wc_id, wd)
                if avail <= 0:
                    continue
                already = slot_map.get((wc_id, wd), Decimal("0"))
                free = avail - already
                if free <= 0:
                    continue

                take = min(free, total_with_co - accumulated)
                accumulated += take
                slot_map[(wc_id, wd)] = already + take

                if take >= co_hrs:
                    changeover_map[(wc_id, wd)] = changeover_map.get((wc_id, wd), Decimal("0")) + co_hrs
                    co_hrs = Decimal("0")

                if scheduled_start_dt is None:
                    scheduled_start_dt = datetime(wd.year, wd.month, wd.day, 6, 0, tzinfo=timezone.utc)

                if accumulated >= total_with_co:
                    placed = True
                    scheduled_end_dt = datetime(wd.year, wd.month, wd.day, 6, 0, tzinfo=timezone.utc) + timedelta(hours=float(total_with_co))
                    break

        op_status = OpQueueStatus.SCHEDULED if placed else OpQueueStatus.BLOCKED
        if placed:
            scheduled += 1
            last_family_on_wc[wc_id] = to_fam
        else:
            blocked += 1
            block_reason = block_reason or "No capacity in horizon"

        # Look up WC name
        wc_name = None
        if wc_id:
            wc_r = await db.execute(select(WorkCenter).where(WorkCenter.id == wc_id))
            wc = wc_r.scalar_one_or_none()
            wc_name = wc.name if wc else None

        op = OperationQueue(
            op_no=_op_no(),
            scenario_id=scenario_id,
            mps_line_id=op_data.get("mps_line_id"),
            work_center_id=wc_id,
            product_id=op_data.get("product_id"),
            product_name=op_data.get("product_name"),
            product_code=op_data.get("product_code"),
            work_center_name=wc_name,
            routing_step_id=op_data.get("routing_step_id"),
            step_name=op_data.get("step_name"),
            planned_qty=op_data["planned_qty"],
            rate_per_hour=op_data["rate_per_hour"],
            setup_minutes=op_data["setup_minutes"],
            run_minutes=op_data["run_minutes"],
            cleanup_minutes=op_data["cleanup_minutes"],
            changeover_minutes=co_min,
            total_minutes=total_run_min + co_min,
            scheduled_start=scheduled_start_dt,
            scheduled_end=scheduled_end_dt,
            priority=op_data["priority"],
            status=op_status,
            block_reason=block_reason if not placed else None,
        )
        db.add(op)
        created_ops.append(op)

    await db.flush()

    # Build CapacityLoadSnapshot records
    wc_ids = {k[0] for k in slot_map}
    all_dates = sorted({k[1] for k in slot_map})

    wc_name_map: Dict[UUID, str] = {}
    for wc_id in wc_ids:
        wc_r = await db.execute(select(WorkCenter).where(WorkCenter.id == wc_id))
        wc = wc_r.scalar_one_or_none()
        if wc:
            wc_name_map[wc_id] = wc.name

    for (wc_id, d), alloc in slot_map.items():
        avail = await _calendar_hours(db, wc_id, d) if wc_id else _DEFAULT_HOURS
        co_hrs_slot = changeover_map.get((wc_id, d), Decimal("0"))
        util = (alloc / avail * 100) if avail > 0 else Decimal("0")
        overload = max(Decimal("0"), alloc - avail)
        snap = CapacityLoadSnapshot(
            scenario_id=scenario_id,
            work_center_id=wc_id,
            work_center_name=wc_name_map.get(wc_id),
            slot_date=d,
            available_hours=avail,
            allocated_hours=alloc,
            changeover_hours=co_hrs_slot,
            utilization_pct=round(util, 2),
            is_overloaded=alloc > avail,
            overload_hours=overload,
            slot_type=CapacitySlotType.ALLOCATED,
        )
        db.add(snap)

    await db.flush()

    # Update scenario KPIs
    total_ops = len(created_ops)
    all_util = [float(alloc / await _calendar_hours(db, wc_id, d) * 100) for (wc_id, d), alloc in slot_map.items()]
    avg_util = sum(all_util) / len(all_util) if all_util else 0.0
    total_co_hrs = sum(changeover_map.values())

    scenario.total_ops = total_ops
    scenario.scheduled_ops = scheduled
    scenario.blocked_ops = blocked
    scenario.avg_utilization_pct = round(Decimal(str(avg_util)), 2)
    scenario.total_changeover_hrs = round(total_co_hrs, 2)
    scenario.calculated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(scenario)

    return {
        "total_ops": total_ops,
        "scheduled": scheduled,
        "blocked": blocked,
        "avg_utilization_pct": round(avg_util, 1),
    }


async def get_capacity_board(db: AsyncSession, scenario_id: UUID) -> dict:
    snaps_r = await db.execute(
        select(CapacityLoadSnapshot)
        .where(CapacityLoadSnapshot.scenario_id == scenario_id)
        .order_by(CapacityLoadSnapshot.work_center_id, CapacityLoadSnapshot.slot_date)
    )
    snaps = snaps_r.scalars().all()

    from collections import defaultdict
    by_wc: Dict[UUID, List[CapacityLoadSnapshot]] = defaultdict(list)
    for s in snaps:
        by_wc[s.work_center_id].append(s)

    rows = []
    overload_alerts = []
    total_util = []

    for wc_id, wc_snaps in by_wc.items():
        peak = max((float(s.utilization_pct) for s in wc_snaps), default=0.0)
        overloaded_days = sum(1 for s in wc_snaps if s.is_overloaded)
        total_ol = sum(float(s.overload_hours) for s in wc_snaps)
        wc_name = wc_snaps[0].work_center_name or str(wc_id)[:8]
        total_util.append(peak)

        rows.append({
            "work_center_id": str(wc_id),
            "work_center_name": wc_name,
            "peak_utilization_pct": peak,
            "overloaded_days": overloaded_days,
            "total_overload_hrs": round(total_ol, 2),
            "slots": wc_snaps,
        })

        for s in wc_snaps:
            if s.is_overloaded:
                overload_alerts.append({
                    "work_center": wc_name,
                    "date": str(s.slot_date),
                    "overload_hours": float(s.overload_hours),
                    "utilization_pct": float(s.utilization_pct),
                })

    ops_r = await db.execute(
        select(OperationQueue).where(OperationQueue.scenario_id == scenario_id)
    )
    total_ops = len(ops_r.scalars().all())

    return {
        "rows": rows,
        "overload_alerts": overload_alerts,
        "total_ops": total_ops,
        "avg_utilization_pct": round(sum(total_util) / len(total_util), 1) if total_util else 0.0,
    }
