"""
MPS Capacity Scheduling Service

For each MPS line:
  1. Compute required_hours = planned_qty / work_center_throughput
  2. Distribute hours across working days in the line's date window
  3. Aggregate per (work_center, date) → MPSCapacitySlot
  4. Flag slots and lines where allocated > available
  5. Suggest reschedule when overloaded (shift date or alternate WC)
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSCapacitySlot,
    MPSFeasibilityStatus, MPSCapacityMode, MPSStatus,
)
from app.models.production_advanced import WorkCenter
from app.schemas.mps import CapacityHeatmap, CapacityHeatmapRow, CapacitySlotOut


_DAYS_SHIFT = 8.0          # default available hours per day
_DEFAULT_THROUGHPUT = 100.0 # units per hour when WC has no capacity set


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


def _work_days_in_range(start: date, end: date) -> List[date]:
    """Return all Mon–Sat days between start and end (inclusive)."""
    days = []
    d = start
    while d <= end:
        if d.weekday() < 6:  # Mon=0 … Sat=5
            days.append(d)
        d += timedelta(days=1)
    return days


def _throughput_per_hour(wc: WorkCenter) -> Decimal:
    """Units per hour from WC capacity column (capacity_uom not checked)."""
    if wc.capacity and float(wc.capacity) > 0:
        return _D(wc.capacity)
    return Decimal(str(_DEFAULT_THROUGHPUT))


# ── Main Scheduler ─────────────────────────────────────────────────────────────

async def run_capacity_scheduling(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """
    Full capacity pass for one MPS plan.
    Returns summary stats.
    """
    plan_q = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")

    # Load all non-locked lines
    lines_q = await db.execute(
        select(MPSLine)
        .where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.priority_score.desc(), MPSLine.period_start)
    )
    lines = list(lines_q.scalars().all())

    # Load work centers
    wc_q = await db.execute(select(WorkCenter))
    wcs: Dict[uuid.UUID, WorkCenter] = {wc.id: wc for wc in wc_q.scalars().all()}

    # Infinite capacity mode — mark all as FEASIBLE
    if plan.capacity_mode == MPSCapacityMode.INFINITE:
        for line in lines:
            if not line.is_locked:
                line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
        await db.flush()
        return {"mode": "INFINITE", "lines_processed": len(lines)}

    # ── Finite capacity scheduling ─────────────────────────────────────────────

    # slot_map: (wc_id, day) → allocated_hours
    slot_map: Dict[Tuple[uuid.UUID, date], Decimal] = {}

    # Clear existing capacity slots for this plan
    await db.execute(delete(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == mps_id))
    await db.flush()

    # Assign work centers to lines that don't have one
    # Strategy: find the WC with the most available capacity for the line's period
    default_wc_id = list(wcs.keys())[0] if wcs else None

    for line in lines:
        if line.is_locked:
            continue
        if not line.work_center_id:
            line.work_center_id = default_wc_id
        if not line.work_center_id or line.work_center_id not in wcs:
            line.feasibility_status = MPSFeasibilityStatus.INFEASIBLE
            line.remarks = (line.remarks or "") + " [no work center available]"
            continue

        wc = wcs[line.work_center_id]
        tph = _throughput_per_hour(wc)

        if float(line.planned_production_qty) <= 0:
            line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
            line.required_hours = Decimal("0")
            continue

        # Total required hours for this line
        required_hrs = _R(
            _D(line.planned_production_qty) / tph
        )
        line.required_hours = required_hrs

        # Spread hours across working days in the period
        p_start = line.planned_start_date or line.period_start
        p_end = line.planned_end_date or line.period_end
        work_days = _work_days_in_range(p_start, p_end)

        if not work_days:
            work_days = [p_start]

        hrs_per_day = _R(required_hrs / Decimal(len(work_days)))

        for day in work_days:
            key = (line.work_center_id, day)
            slot_map[key] = slot_map.get(key, Decimal("0")) + hrs_per_day

    # Build MPSCapacitySlot records and detect overloads
    overloaded_lines_ids = set()
    slot_seq_q = await db.execute(select(func.count()).select_from(MPSCapacitySlot))
    slot_seq = slot_seq_q.scalar() or 0

    for (wc_id, day), alloc in slot_map.items():
        available = Decimal(str(_DAYS_SHIFT))
        overload = max(Decimal("0"), alloc - available)
        util_pct = _R(alloc / available * 100, 2)

        slot = MPSCapacitySlot(
            mps_id=mps_id,
            work_center_id=wc_id,
            slot_date=day,
            available_hours=available,
            allocated_hours=_R(alloc),
            overload_hours=_R(overload),
            utilization_pct=util_pct,
            is_overloaded=overload > 0,
        )
        db.add(slot)
        slot_seq += 1

    await db.flush()

    # Re-check each line against built slots to update feasibility
    for line in lines:
        if line.is_locked or not line.work_center_id:
            continue

        p_start = line.planned_start_date or line.period_start
        p_end = line.planned_end_date or line.period_end
        work_days = _work_days_in_range(p_start, p_end)

        line_overload = Decimal("0")
        for day in work_days:
            key = (line.work_center_id, day)
            alloc = slot_map.get(key, Decimal("0"))
            daily_avail = Decimal(str(_DAYS_SHIFT))
            if alloc > daily_avail:
                line_overload += alloc - daily_avail

        if line_overload > 0:
            line.feasibility_status = MPSFeasibilityStatus.OVERLOADED
            line.overload_hours = _R(line_overload)
            overloaded_lines_ids.add(line.id)
        else:
            line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
            line.overload_hours = Decimal("0")

    await db.flush()

    from app.services.mps_service import _refresh_plan_counters
    await _refresh_plan_counters(db, mps_id)

    return {
        "mode": "FINITE",
        "lines_processed": len(lines),
        "overloaded_lines": len(overloaded_lines_ids),
        "capacity_slots_created": len(slot_map),
    }


# ── Capacity Heatmap ──────────────────────────────────────────────────────────

async def get_capacity_heatmap(db: AsyncSession, mps_id: uuid.UUID) -> CapacityHeatmap:
    slots_q = await db.execute(
        select(MPSCapacitySlot)
        .where(MPSCapacitySlot.mps_id == mps_id)
        .order_by(MPSCapacitySlot.work_center_id, MPSCapacitySlot.slot_date)
    )
    slots = slots_q.scalars().all()

    # Group by work center
    wc_map: Dict[uuid.UUID, List[MPSCapacitySlot]] = {}
    for s in slots:
        wc_map.setdefault(s.work_center_id, []).append(s)

    wc_q = await db.execute(select(WorkCenter))
    wcs: Dict[uuid.UUID, WorkCenter] = {wc.id: wc for wc in wc_q.scalars().all()}

    rows = []
    overload_alerts = []

    for wc_id, wc_slots in wc_map.items():
        wc = wcs.get(wc_id)
        wc_name = wc.name if wc else str(wc_id)

        peak = max((float(s.utilization_pct or 0) for s in wc_slots), default=0)
        overloaded_days = sum(1 for s in wc_slots if s.is_overloaded)

        slot_outs = []
        for s in wc_slots:
            so = CapacitySlotOut(
                id=s.id,
                work_center_id=s.work_center_id,
                slot_date=s.slot_date,
                available_hours=s.available_hours,
                allocated_hours=s.allocated_hours,
                downtime_hours=s.downtime_hours,
                overload_hours=s.overload_hours,
                utilization_pct=s.utilization_pct,
                is_overloaded=s.is_overloaded,
                work_center_name=wc_name,
            )
            slot_outs.append(so)
            if s.is_overloaded:
                overload_alerts.append({
                    "work_center": wc_name,
                    "date": str(s.slot_date),
                    "overload_hours": float(s.overload_hours),
                    "utilization_pct": float(s.utilization_pct),
                })

        rows.append(CapacityHeatmapRow(
            work_center_id=wc_id,
            work_center_name=wc_name,
            slots=slot_outs,
            peak_utilization_pct=peak,
            overloaded_days=overloaded_days,
        ))

    return CapacityHeatmap(
        mps_id=mps_id,
        rows=rows,
        overload_alerts=overload_alerts,
    )


# ── Reschedule Suggestion ─────────────────────────────────────────────────────

async def suggest_reschedule(
    db: AsyncSession,
    line_id: uuid.UUID,
) -> dict:
    """
    For an OVERLOADED line, find the earliest future date window
    where enough capacity is available on the same work center.
    """
    line_q = await db.execute(select(MPSLine).where(MPSLine.id == line_id))
    line = line_q.scalar_one_or_none()
    if not line:
        raise ValueError("MPS line not found")
    if not line.work_center_id:
        return {"suggestion": "No work center assigned — cannot reschedule"}

    required_hrs = float(line.required_hours or 0)
    if required_hrs <= 0:
        return {"suggestion": "No required hours — no reschedule needed"}

    # Load existing capacity slots for this work center
    slots_q = await db.execute(
        select(MPSCapacitySlot)
        .where(
            MPSCapacitySlot.mps_id == line.mps_id,
            MPSCapacitySlot.work_center_id == line.work_center_id,
        )
        .order_by(MPSCapacitySlot.slot_date)
    )
    slots = {s.slot_date: s for s in slots_q.scalars().all()}

    # Scan forward from planned_end_date
    cursor = (line.planned_end_date or line.period_end) + timedelta(days=1)
    end_limit = cursor + timedelta(days=30)

    accumulated = 0.0
    start_candidate = None
    while cursor < end_limit:
        if cursor.weekday() < 6:
            slot = slots.get(cursor)
            remaining = float(_DAYS_SHIFT) - float(slot.allocated_hours if slot else 0)
            if remaining > 0:
                if start_candidate is None:
                    start_candidate = cursor
                accumulated += remaining
                if accumulated >= required_hrs:
                    return {
                        "suggestion": f"Shift to {start_candidate.isoformat()} – {cursor.isoformat()}",
                        "new_start": start_candidate.isoformat(),
                        "new_end": cursor.isoformat(),
                        "available_hours": round(accumulated, 2),
                        "required_hours": round(required_hrs, 2),
                    }
            else:
                start_candidate = None
                accumulated = 0.0
        cursor += timedelta(days=1)

    return {
        "suggestion": "No available window found in next 30 days — consider splitting or adding shifts",
        "required_hours": round(required_hrs, 2),
    }
