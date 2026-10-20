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


async def run_capacity_scheduling_validated(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Calculate finite capacity only from explicit calendars, rates, and downtime."""
    from datetime import datetime, timezone
    from app.models.master import Product
    from app.models.planning import ResourceCalendar
    from app.models.production_advanced import DowntimeEvent, WorkCenterStatus
    from app.services.mps_advanced_service import _write_diagnostics
    from app.services.mps_engine import capacity_result

    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())).scalar_one_or_none()
    if plan is None:
        raise ValueError("MPS plan not found")
    lines = list((await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.period_start, MPSLine.priority_score.desc(), MPSLine.line_no)
    )).scalars().all())
    if plan.capacity_mode == MPSCapacityMode.INFINITE:
        # Infinite mode bypasses load limits; it is not evidence of material or
        # master-data feasibility and therefore never promotes PENDING lines.
        return {"mode": "INFINITE", "lines_processed": len(lines), "overloaded_lines": 0, "diagnostic_run_id": None}

    wc_ids = {line.work_center_id for line in lines if line.work_center_id}
    wcs = {wc.id: wc for wc in (await db.execute(select(WorkCenter).where(WorkCenter.id.in_(wc_ids)))).scalars().all()} if wc_ids else {}
    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_({l.product_id for l in lines})))).scalars().all()} if lines else {}
    if not lines:
        await db.execute(delete(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == mps_id))
        await db.flush()
        return {"mode": "FINITE", "lines_processed": 0, "overloaded_lines": 0, "capacity_slots_created": 0, "diagnostic_run_id": None}

    start = min(line.planned_start_date or line.period_start for line in lines)
    end = max(line.planned_end_date or line.period_end for line in lines)
    calendars = (await db.execute(
        select(ResourceCalendar).where(ResourceCalendar.work_center_id.in_(wc_ids),
                                       ResourceCalendar.calendar_date >= start,
                                       ResourceCalendar.calendar_date <= end)
    )).scalars().all() if wc_ids else []
    calendar_map = {(item.work_center_id, item.calendar_date): item for item in calendars}
    downtimes = (await db.execute(
        select(DowntimeEvent).where(DowntimeEvent.work_center_id.in_(wc_ids),
                                    DowntimeEvent.start_time < datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
                                    (DowntimeEvent.end_time.is_(None)) | (DowntimeEvent.end_time >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)))
    )).scalars().all() if wc_ids else []

    def working_days(a: date, b: date) -> list[date]:
        cursor, result = a, []
        while cursor <= b:
            result.append(cursor)
            cursor += timedelta(days=1)
        return result

    def rate_per_hour(wc, product) -> Decimal | None:
        if not wc.capacity or _D(wc.capacity) <= 0:
            return None
        cap_uom = str(wc.capacity_uom or "").strip().upper().replace(" ", "")
        product_uom = str(getattr(product.uom, "value", product.uom) or "").upper()
        compatible = {f"{product_uom}/HR", f"{product_uom}/HOUR", "UNITS/HR" if product_uom in {"PCS", "EA", "UNIT", "UNITS"} else ""}
        if cap_uom not in compatible:
            return None
        return _D(wc.capacity)

    def day_downtime(wc_id: uuid.UUID, day: date) -> tuple[Decimal, bool]:
        total = Decimal(0)
        unbounded = False
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        for event in downtimes:
            if event.work_center_id != wc_id or event.start_time >= day_end:
                continue
            if event.end_time is None and not event.duration_min:
                if event.start_time.date() <= day:
                    unbounded = True
                continue
            event_end = event.end_time or event.start_time + timedelta(minutes=int(event.duration_min or 0))
            left, right = max(day_start, event.start_time), min(day_end, event_end)
            if right > left:
                total += Decimal(str((right - left).total_seconds())) / Decimal(3600)
        return total, unbounded

    slot_allocations: dict[tuple[uuid.UUID, date], Decimal] = defaultdict(Decimal)
    line_allocations: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(dict)
    line_issues: dict[uuid.UUID, list[dict]] = defaultdict(list)
    required_by_line: dict[uuid.UUID, Decimal] = {}

    # Locked commitments consume capacity, but their line state and schedule are immutable here.
    for line in lines:
        if not line.work_center_id or line.work_center_id not in wcs:
            line_issues[line.id].append({"reason_code": "WORK_CENTER_MISSING", "priority": "CRITICAL"})
            continue
        wc = wcs[line.work_center_id]
        product = products.get(line.product_id)
        if str(getattr(wc.status, "value", wc.status) or "").upper() != "ACTIVE":
            line_issues[line.id].append({"reason_code": "WORK_CENTER_INACTIVE", "work_center_id": str(wc.id), "priority": "CRITICAL"})
            continue
        tph = rate_per_hour(wc, product) if product else None
        if tph is None:
            line_issues[line.id].append({"reason_code": "CAPACITY_RATE_NOT_CONFIGURED", "work_center_id": str(wc.id), "capacity_uom": wc.capacity_uom, "product_uom": str(getattr(product.uom, "value", product.uom)) if product else None, "priority": "CRITICAL"})
            continue
        required = _R(_D(line.planned_production_qty) / tph)
        required_by_line[line.id] = required
        line_days = working_days(line.planned_start_date or line.period_start, line.planned_end_date or line.period_end)
        configured_days = [day for day in line_days if (wc.id, day) in calendar_map]
        if not configured_days:
            line_issues[line.id].append({"reason_code": "CAPACITY_CALENDAR_NOT_CONFIGURED", "work_center_id": str(wc.id), "from_date": line_days[0].isoformat(), "to_date": line_days[-1].isoformat(), "priority": "CRITICAL"})
            continue
        per_day = _R(required / Decimal(len(configured_days)))
        for day in configured_days:
            slot_allocations[(wc.id, day)] += per_day
            line_allocations[line.id][day] = per_day
        missing = sorted(set(line_days) - set(configured_days))
        if missing:
            line_issues[line.id].append({"reason_code": "CAPACITY_CALENDAR_GAP", "dates": [d.isoformat() for d in missing], "priority": "HIGH"})

    await db.execute(delete(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == mps_id))
    diagnostics = []
    overloaded_lines: set[uuid.UUID] = set()
    for (wc_id, day), allocated in sorted(slot_allocations.items(), key=lambda item: (str(item[0][0]), item[0][1])):
        calendar = calendar_map[(wc_id, day)]
        available = Decimal(0) if calendar.is_holiday or calendar.is_maintenance else _D(calendar.available_hours)
        downtime, unbounded = day_downtime(wc_id, day)
        if unbounded:
            line_issues_for_slot = [line for line in lines if line.work_center_id == wc_id and day in line_allocations[line.id]]
            for line in line_issues_for_slot:
                line_issues[line.id].append({"reason_code": "OPEN_DOWNTIME_UNBOUNDED", "work_center_id": str(wc_id), "date": day.isoformat(), "priority": "CRITICAL"})
            downtime = available
        metrics = capacity_result(allocated, available, min(downtime, available))
        slot = MPSCapacitySlot(
            mps_id=mps_id, work_center_id=wc_id, slot_date=day,
            available_hours=metrics["available_hours"], allocated_hours=metrics["required_hours"],
            downtime_hours=metrics["downtime_hours"], overload_hours=metrics["overload_hours"],
            utilization_pct=_R(allocated / available * 100, 2) if available else Decimal("0"),
            is_overloaded=metrics["status"] == "OVERLOADED",
        )
        db.add(slot)
        if metrics["status"] == "OVERLOADED":
            cumulative = Decimal(0)
            prior_overload = Decimal(0)
            contributors = sorted(
                (line for line in lines if line.work_center_id == wc_id and day in line_allocations[line.id]),
                key=lambda line: (-_D(line.priority_score or 0), line.line_no, line.id.hex),
            )
            for line in contributors:
                cumulative += line_allocations[line.id][day]
                cumulative_overload = max(Decimal(0), cumulative - metrics["net_available_hours"])
                line_overload = cumulative_overload - prior_overload
                prior_overload = cumulative_overload
                if line_overload > 0 and not line.is_locked:
                    overloaded_lines.add(line.id)
                    line_issues[line.id].append({
                        "reason_code": "CAPACITY_OVERLOAD", "work_center_id": str(wc_id),
                        "date": day.isoformat(), "required_hours": str(metrics["required_hours"]),
                        "available_hours": str(metrics["available_hours"]),
                        "downtime_hours": str(metrics["downtime_hours"]),
                        "overload_hours": str(line_overload), "priority": "HIGH",
                    })

    for line in lines:
        issues = line_issues[line.id]
        if not line.is_locked:
            if line.id in required_by_line:
                line.required_hours = required_by_line[line.id]
            issue_codes = {issue["reason_code"] for issue in issues}
            if issue_codes - {"CAPACITY_OVERLOAD"}:
                line.feasibility_status = MPSFeasibilityStatus.INFEASIBLE
                line.overload_hours = None
            elif line.id in overloaded_lines:
                line.feasibility_status = MPSFeasibilityStatus.OVERLOADED
                line.overload_hours = sum((Decimal(str(i.get("overload_hours", 0))) for i in issues), Decimal(0))
            elif line.feasibility_status not in (MPSFeasibilityStatus.MATERIAL_SHORT, MPSFeasibilityStatus.ON_HOLD):
                line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
                line.overload_hours = Decimal(0)
        diagnostics.append((line.id, {
            "reason_codes": list(dict.fromkeys(i["reason_code"] for i in issues)),
            "issues": issues, "status": str(getattr(line.feasibility_status, "value", line.feasibility_status)),
            "plan_id": str(mps_id), "work_center_id": str(line.work_center_id) if line.work_center_id else None,
            "locked": bool(line.is_locked),
        }))

    diagnostic_run = await _write_diagnostics(db, mps_id, diagnostics)
    await db.flush()
    from app.services.mps_service import _refresh_plan_counters
    await _refresh_plan_counters(db, mps_id)
    return {
        "mode": "FINITE", "lines_processed": len(lines),
        "overloaded_lines": len(overloaded_lines), "capacity_slots_created": len(slot_allocations),
        "infeasible_lines": sum(1 for line in lines if not line.is_locked and line.feasibility_status == MPSFeasibilityStatus.INFEASIBLE),
        "diagnostic_run_id": str(diagnostic_run),
    }
