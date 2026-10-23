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
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSCampaign, MPSCapacitySlot,
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


def _validated_calendar_hours(calendar) -> tuple[Decimal | None, str | None]:
    """Validate declared daily hours against any configured shift windows."""
    available = _D(calendar.available_hours)
    if not available.is_finite() or available < 0 or available > 24:
        return None, "available_hours must be finite and between 0 and 24"

    shifts = []
    for number in range(1, 4):
        start_value = getattr(calendar, f"shift_{number}_start", None)
        end_value = getattr(calendar, f"shift_{number}_end", None)
        start_text = str(start_value).strip() if start_value is not None else ""
        end_text = str(end_value).strip() if end_value is not None else ""
        if not start_text and not end_text:
            continue
        if not start_text or not end_text:
            return None, f"shift {number} has an incomplete start/end pair"
        start_match = re.fullmatch(r"([0-2][0-9]):([0-5][0-9])", start_text)
        end_match = re.fullmatch(r"([0-2][0-9]):([0-5][0-9])", end_text)
        if not start_match or not end_match:
            return None, f"shift {number} must use HH:MM times"
        start_hour, start_minute = map(int, start_match.groups())
        end_hour, end_minute = map(int, end_match.groups())
        if start_hour > 23 or end_hour > 23:
            return None, f"shift {number} time is outside the 00:00-23:59 range"
        start_minute_of_day = start_hour * 60 + start_minute
        end_minute_of_day = end_hour * 60 + end_minute
        if start_minute_of_day == end_minute_of_day:
            return None, f"shift {number} has an ambiguous zero/full-day duration"
        end_absolute = end_minute_of_day if end_minute_of_day > start_minute_of_day else end_minute_of_day + 1440
        segments = [(start_minute_of_day, min(end_absolute, 1440))]
        if end_absolute > 1440:
            segments.append((0, end_absolute - 1440))
        shifts.append((number, segments, end_absolute - start_minute_of_day))

    for index, (left_number, left_segments, _) in enumerate(shifts):
        for right_number, right_segments, _ in shifts[index + 1:]:
            if any(max(left_start, right_start) < min(left_end, right_end)
                   for left_start, left_end in left_segments
                   for right_start, right_end in right_segments):
                return None, f"shifts {left_number} and {right_number} overlap"
    if shifts:
        scheduled_hours = Decimal(sum(shift[2] for shift in shifts)) / Decimal(60)
        if abs(available - scheduled_hours) > Decimal("0.01"):
            return None, "available_hours does not equal the configured shift duration"
    return available, None


def _calendar_shift_windows(calendar, day: date) -> list[tuple[datetime, datetime]]:
    """Build UTC intervals for shifts that start on the calendar's date."""
    windows = []
    for number in range(1, 4):
        start_value = getattr(calendar, f"shift_{number}_start", None)
        end_value = getattr(calendar, f"shift_{number}_end", None)
        if start_value is None or end_value is None:
            continue
        start_hour, start_minute = map(int, str(start_value).strip().split(":"))
        end_hour, end_minute = map(int, str(end_value).strip().split(":"))
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(
            hour=start_hour, minute=start_minute,
        )
        end_day = day + timedelta(days=1) if (end_hour, end_minute) <= (start_hour, start_minute) else day
        end = datetime.combine(end_day, datetime.min.time(), tzinfo=timezone.utc).replace(
            hour=end_hour, minute=end_minute,
        )
        windows.append((start, end))
    if windows:
        return windows
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    return [(day_start, day_start + timedelta(days=1))]


def _cross_calendar_shift_errors(calendars) -> dict[tuple[uuid.UUID, date], str]:
    """Reject explicit shifts that overlap in real time across calendar dates."""
    grouped: dict[uuid.UUID, list[tuple[datetime, datetime, tuple[uuid.UUID, date]]]] = defaultdict(list)
    for calendar in calendars:
        if calendar.is_holiday or calendar.is_maintenance:
            continue
        key = (calendar.work_center_id, calendar.calendar_date)
        _, error = _validated_calendar_hours(calendar)
        if error:
            continue
        has_explicit_shift = any(
            getattr(calendar, f"shift_{number}_{edge}", None) is not None
            for number in range(1, 4) for edge in ("start", "end")
        )
        if not has_explicit_shift:
            continue
        grouped[calendar.work_center_id].extend(
            (left, right, key) for left, right in _calendar_shift_windows(calendar, calendar.calendar_date)
        )

    errors: dict[tuple[uuid.UUID, date], str] = {}
    for windows in grouped.values():
        active: list[tuple[datetime, tuple[uuid.UUID, date]]] = []
        for start, end, key in sorted(windows, key=lambda item: (item[0], item[1])):
            active = [(active_end, active_key) for active_end, active_key in active if active_end > start]
            for _, active_key in active:
                if active_key != key:
                    errors[key] = f"configured shift overlaps another calendar shift on {active_key[1].isoformat()}"
                    errors[active_key] = f"configured shift overlaps another calendar shift on {key[1].isoformat()}"
            active.append((end, key))
    return errors


# ── Main Scheduler ─────────────────────────────────────────────────────────────

async def run_capacity_scheduling(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """
    Full capacity pass for one MPS plan.
    Returns summary stats.
    """
    plan_q = await db.execute(
        select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update()
    )
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Capacity scheduling is only allowed for DRAFT MPS plans")

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
    from app.models.master import Product
    from app.models.planning import ChangeoverMatrix, ResourceCalendar
    from app.models.production_advanced import DowntimeEvent
    from app.services.mps_advanced_service import _write_diagnostics
    from app.services.mps_engine import capacity_result
    from app.services.utilities_service import convert_uom

    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())).scalar_one_or_none()
    if plan is None:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Capacity scheduling is only allowed for DRAFT MPS plans")
    lines = list((await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.is_locked.desc(), MPSLine.priority_score.desc(), MPSLine.period_start, MPSLine.line_no)
    )).scalars().all())
    if plan.capacity_mode == MPSCapacityMode.INFINITE:
        # Infinite mode bypasses load limits; it is not evidence of feasibility.
        await db.execute(delete(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == mps_id))
        await db.flush()
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
    calendar_start = start - timedelta(days=1)
    calendar_end = end + timedelta(days=1)
    calendars = (await db.execute(
        select(ResourceCalendar).where(ResourceCalendar.work_center_id.in_(wc_ids),
                                       ResourceCalendar.calendar_date >= calendar_start,
                                       ResourceCalendar.calendar_date <= calendar_end)
    )).scalars().all() if wc_ids else []
    calendar_map = {(item.work_center_id, item.calendar_date): item for item in calendars}
    downtimes = (await db.execute(
        select(DowntimeEvent).where(DowntimeEvent.work_center_id.in_(wc_ids),
                                    DowntimeEvent.start_time < datetime.combine(calendar_end + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc),
                                    (DowntimeEvent.end_time.is_(None)) | (DowntimeEvent.end_time >= datetime.combine(calendar_start, datetime.min.time(), tzinfo=timezone.utc)))
    )).scalars().all() if wc_ids else []

    def working_days(a: date, b: date) -> list[date]:
        cursor, result = a, []
        while cursor <= b:
            result.append(cursor)
            cursor += timedelta(days=1)
        return result

    async def rate_per_hour(wc, product) -> Decimal | None:
        capacity = _D(wc.capacity)
        if not capacity.is_finite() or capacity <= 0:
            return None
        cap_uom = str(wc.capacity_uom or "").strip().upper().replace(" ", "")
        product_uom = str(getattr(product.uom, "value", product.uom) or "").upper()
        rate_match = re.fullmatch(r"(.+?)/(?:HR|HOUR)", cap_uom)
        if rate_match is None:
            return None
        source_uom = rate_match.group(1)
        count_units = {"PCS", "EA", "UNIT", "UNITS"}
        if source_uom in {"UNITS", "UNIT", "EA"} and product_uom in count_units:
            return capacity
        try:
            converted = _D(await convert_uom(db, capacity, source_uom, product_uom))
        except (HTTPException, MultipleResultsFound, InvalidOperation):
            return None
        return converted if converted.is_finite() and converted > 0 else None

    def day_downtime(wc_id: uuid.UUID, day: date, calendar) -> tuple[Decimal, bool, bool]:
        intervals: list[tuple[datetime, datetime]] = []
        unbounded = False
        invalid = False
        windows = _calendar_shift_windows(calendar, day)
        for event in downtimes:
            if event.work_center_id != wc_id:
                continue
            if event.start_time.tzinfo is None or (event.end_time is not None and event.end_time.tzinfo is None):
                naive_windows = [(left.replace(tzinfo=None), right.replace(tzinfo=None)) for left, right in windows]
                naive_start = event.start_time.replace(tzinfo=None)
                naive_end = event.end_time.replace(tzinfo=None) if event.end_time is not None else None
                invalid = invalid or any(
                    min(naive_start, naive_end) < right and max(naive_start, naive_end) > left
                    if naive_end is not None else naive_start < right
                    for left, right in naive_windows
                )
                continue
            if event.end_time is not None and event.end_time < event.start_time:
                invalid = invalid or any(
                    event.end_time < right and event.start_time > left
                    for left, right in windows
                )
                continue
            if event.end_time is None and not event.duration_min:
                if any(event.start_time < right for _, right in windows):
                    unbounded = True
                continue
            if event.end_time is None and int(event.duration_min or 0) < 0:
                event_end = event.start_time + timedelta(minutes=int(event.duration_min or 0))
                invalid = invalid or any(
                    event_end < right and event.start_time > left
                    for left, right in windows
                )
                continue
            event_end = event.end_time or event.start_time + timedelta(minutes=int(event.duration_min or 0))
            for window_start, window_end in windows:
                left, right = max(window_start, event.start_time), min(window_end, event_end)
                if right > left:
                    intervals.append((left, right))
        intervals.sort(key=lambda interval: interval[0])
        merged: list[list[datetime]] = []
        for left, right in intervals:
            if merged and left <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], right)
            else:
                merged.append([left, right])
        total = sum(
            (Decimal(str((right - left).total_seconds())) / Decimal(3600) for left, right in merged),
            Decimal(0),
        )
        return total, unbounded, invalid

    calendar_metrics: dict[tuple[uuid.UUID, date], dict] = {}
    cross_calendar_errors = _cross_calendar_shift_errors(calendars)
    for calendar in calendars:
        key = (calendar.work_center_id, calendar.calendar_date)
        declared_hours, calendar_error = _validated_calendar_hours(calendar)
        calendar_error = calendar_error or cross_calendar_errors.get(key)
        if calendar_error:
            available = Decimal(0)
            calendar_metrics[key] = {
                "available": available, "downtime": Decimal(0), "net_available": Decimal(0),
                "calendar_error": calendar_error, "unbounded": False, "downtime_error": False,
            }
            continue
        available = Decimal(0) if calendar.is_holiday or calendar.is_maintenance else declared_hours
        downtime, unbounded, downtime_error = day_downtime(
            calendar.work_center_id, calendar.calendar_date, calendar,
        )
        if unbounded or downtime_error:
            downtime = available
        else:
            downtime = min(downtime, available)
        calendar_metrics[key] = {
            "available": available, "downtime": downtime,
            "net_available": max(Decimal(0), available - downtime),
            "calendar_error": None, "unbounded": unbounded, "downtime_error": downtime_error,
        }

    slot_allocations: dict[tuple[uuid.UUID, date], Decimal] = defaultdict(Decimal)
    line_allocations: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(dict)
    line_issues: dict[uuid.UUID, list[dict]] = defaultdict(list)
    required_by_line: dict[uuid.UUID, Decimal] = {}

    # Locked commitments are allocated first and consume the same aggregate
    # work-center capacity as concurrent unlocked lines.
    for line in lines:
        line_start = line.planned_start_date or line.period_start
        line_end = line.planned_end_date or line.period_end
        if line_end < line_start:
            line_issues[line.id].append({
                "reason_code": "CAPACITY_DATE_RANGE_INVALID", "from_date": line_start.isoformat(),
                "to_date": line_end.isoformat(), "priority": "CRITICAL",
            })
            continue
        quantity = _D(line.planned_production_qty)
        if not quantity.is_finite() or quantity < 0:
            line_issues[line.id].append({
                "reason_code": "CAPACITY_QUANTITY_INVALID", "planned_quantity": str(line.planned_production_qty),
                "priority": "CRITICAL",
            })
            continue
        if not line.work_center_id or line.work_center_id not in wcs:
            line_issues[line.id].append({"reason_code": "WORK_CENTER_MISSING", "priority": "CRITICAL"})
            continue
        wc = wcs[line.work_center_id]
        product = products.get(line.product_id)
        if product is None or not product.is_active:
            line_issues[line.id].append({"reason_code": "PRODUCT_MASTER_INVALID", "product_id": str(line.product_id), "priority": "CRITICAL"})
            continue
        if str(getattr(wc.status, "value", wc.status) or "").upper() != "ACTIVE":
            line_issues[line.id].append({"reason_code": "WORK_CENTER_INACTIVE", "work_center_id": str(wc.id), "priority": "CRITICAL"})
            continue
        tph = await rate_per_hour(wc, product)
        if tph is None:
            line_issues[line.id].append({"reason_code": "CAPACITY_RATE_NOT_CONFIGURED", "work_center_id": str(wc.id), "capacity_uom": wc.capacity_uom, "product_uom": str(getattr(product.uom, "value", product.uom)), "priority": "CRITICAL"})
            continue
        required = _R(quantity / tph)
        required_by_line[line.id] = required
        line_days = working_days(line_start, line_end)
        configured_days = [day for day in line_days if (wc.id, day) in calendar_map]
        if not configured_days:
            line_issues[line.id].append({"reason_code": "CAPACITY_CALENDAR_NOT_CONFIGURED", "work_center_id": str(wc.id), "from_date": line_start.isoformat(), "to_date": line_end.isoformat(), "priority": "CRITICAL"})
            continue
        missing = sorted(set(line_days) - set(configured_days))
        if missing:
            line_issues[line.id].append({"reason_code": "CAPACITY_CALENDAR_GAP", "dates": [d.isoformat() for d in missing], "priority": "HIGH"})
        valid_capacity_days = []
        for day in configured_days:
            metrics = calendar_metrics[(wc.id, day)]
            if metrics["calendar_error"]:
                line_issues[line.id].append({
                    "reason_code": "CAPACITY_CALENDAR_INVALID", "work_center_id": str(wc.id),
                    "date": day.isoformat(), "message": metrics["calendar_error"], "priority": "CRITICAL",
                })
            if metrics["unbounded"]:
                line_issues[line.id].append({"reason_code": "OPEN_DOWNTIME_UNBOUNDED", "work_center_id": str(wc.id), "date": day.isoformat(), "priority": "CRITICAL"})
            if metrics["downtime_error"]:
                line_issues[line.id].append({"reason_code": "DOWNTIME_DATA_INVALID", "work_center_id": str(wc.id), "date": day.isoformat(), "priority": "CRITICAL"})
            valid_capacity_days.append(day)

        remaining = required
        for day in valid_capacity_days:
            metrics = calendar_metrics[(wc.id, day)]
            capacity_left = max(Decimal(0), metrics["net_available"] - slot_allocations[(wc.id, day)])
            allocated = min(remaining, capacity_left)
            if allocated > 0:
                slot_allocations[(wc.id, day)] += allocated
                line_allocations[line.id][day] = allocated
                remaining -= allocated
            if remaining <= 0:
                break
        if remaining > 0:
            # Keep the full requirement visible as overload instead of silently
            # dropping hours when all configured dates are at capacity.
            overflow_day = valid_capacity_days[-1]
            slot_allocations[(wc.id, overflow_day)] += remaining
            line_allocations[line.id][overflow_day] = line_allocations[line.id].get(overflow_day, Decimal(0)) + remaining

    # Re-evaluate campaign transitions against the current active matrix. The
    # campaign's stored changeover total is a grouping-time snapshot, so using
    # it here could apply stale setup after master data changes. CIP duration
    # has no authoritative MPS source and is therefore carried as unknown.
    campaign_rows = (await db.execute(
        select(MPSCampaign).where(MPSCampaign.mps_id == mps_id)
    )).scalars().all()
    members_by_campaign: dict[uuid.UUID, list[MPSLine]] = defaultdict(list)
    for line in lines:
        if line.campaign_id:
            members_by_campaign[line.campaign_id].append(line)

    campaign_work_centers = {
        campaign.work_center_id for campaign in campaign_rows if campaign.work_center_id
    }
    matrix_rows = (await db.execute(
        select(ChangeoverMatrix).where(
            ChangeoverMatrix.work_center_id.in_(campaign_work_centers),
            ChangeoverMatrix.is_active.is_(True),
        )
    )).scalars().all() if campaign_work_centers else []
    matrix_values: dict[tuple[uuid.UUID, str, str], list[int]] = defaultdict(list)
    for row in matrix_rows:
        key = (
            row.work_center_id,
            str(row.from_family or "").strip().upper(),
            str(row.to_family or "").strip().upper(),
        )
        matrix_values[key].append(row.changeover_minutes)

    campaigns_by_work_center: dict[uuid.UUID, list[tuple[MPSCampaign, list[MPSLine], str]]] = defaultdict(list)
    invalid_campaign_work_centers: set[uuid.UUID] = set()
    for campaign in campaign_rows:
        members = members_by_campaign.get(campaign.id, [])
        if not members:
            continue
        # CIP applicability/duration is not inferable from the available MPS
        # master data. Keep the missing input visible in this capacity run.
        for member in members:
            line_issues[member.id].append({
                "reason_code": "CIP_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                "duration_minutes": None,
                "provenance": "No authoritative MPS CIP duration source exists; no cleaning time was applied.",
                "priority": "LOW",
            })

        member_work_centers = {member.work_center_id for member in members}
        families = {
            str(getattr(products[member.product_id].category, "value", products[member.product_id].category) or "")
            .strip().upper()
            for member in members if member.product_id in products
        }
        if (
            not campaign.work_center_id
            or member_work_centers != {campaign.work_center_id}
            or len(families) != 1
            or not next(iter(families), "")
            or campaign.sequence_order <= 0
            or campaign.campaign_start is None
            or campaign.campaign_end is None
            or campaign.campaign_end < campaign.campaign_start
        ):
            invalid_campaign_work_centers.update(
                center_id for center_id in member_work_centers if center_id is not None
            )
            if campaign.work_center_id is not None:
                invalid_campaign_work_centers.add(campaign.work_center_id)
            issue = {
                "reason_code": "CHANGEOVER_SEQUENCE_INVALID", "state": "SEQUENCE_NOT_ESTABLISHED",
                "campaign_id": str(campaign.id),
                "work_center_ids": sorted(
                    str(center_id) for center_id in member_work_centers | {campaign.work_center_id}
                    if center_id is not None
                ),
                "provenance": "Campaign work center, family, sequence, or date window is incomplete or inconsistent; setup was not applied.",
                "priority": "HIGH",
            }
            for member in members:
                line_issues[member.id].append(issue)
            continue
        campaigns_by_work_center[campaign.work_center_id].append(
            (campaign, members, next(iter(families)))
        )

    for work_center_id, sequenced_campaigns in campaigns_by_work_center.items():
        if work_center_id in invalid_campaign_work_centers:
            for _campaign, members, _family in sequenced_campaigns:
                issue = {
                    "reason_code": "CHANGEOVER_SEQUENCE_INVALID", "state": "SEQUENCE_NOT_ESTABLISHED",
                    "work_center_id": str(work_center_id),
                    "provenance": "Another campaign assigned to this work center has inconsistent member data; transitions were not inferred across it.",
                    "priority": "HIGH",
                }
                for member in members:
                    line_issues[member.id].append(issue)
            continue
        if (
            work_center_id not in wcs
            or str(getattr(wcs[work_center_id].status, "value", wcs[work_center_id].status) or "").upper() != "ACTIVE"
        ):
            # The line validation above already records WORK_CENTER_INACTIVE
            # (or WORK_CENTER_MISSING); never add setup load to an unusable WC.
            continue
        sequenced_campaigns.sort(key=lambda item: (item[0].sequence_order, item[0].id.hex))
        sequence_numbers = [item[0].sequence_order for item in sequenced_campaigns]
        if len(sequence_numbers) != len(set(sequence_numbers)):
            for campaign, members, _family in sequenced_campaigns:
                issue = {
                    "reason_code": "CHANGEOVER_SEQUENCE_INVALID", "state": "SEQUENCE_NOT_ESTABLISHED",
                    "work_center_id": str(work_center_id),
                    "provenance": "Campaign sequence numbers are duplicated for this work center; transitions were not guessed.",
                    "priority": "HIGH",
                }
                for member in members:
                    line_issues[member.id].append(issue)
            continue

        for (previous, _previous_members, previous_family), (campaign, members, family) in zip(
            sequenced_campaigns, sequenced_campaigns[1:]
        ):
            if previous.campaign_end >= campaign.campaign_start:
                issue = {
                    "reason_code": "CHANGEOVER_SEQUENCE_INVALID", "state": "SEQUENCE_NOT_ESTABLISHED",
                    "work_center_id": str(work_center_id),
                    "from_campaign_id": str(previous.id), "to_campaign_id": str(campaign.id),
                    "provenance": "Campaign windows overlap or touch; transition setup was not applied.",
                    "priority": "HIGH",
                }
                for member in members:
                    line_issues[member.id].append(issue)
                continue

            matrix_key = (work_center_id, previous_family, family)
            values = matrix_values.get(matrix_key, [])
            if not values:
                for member in members:
                    line_issues[member.id].append({
                        "reason_code": "CHANGEOVER_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                        "work_center_id": str(work_center_id),
                        "from_family": previous_family, "to_family": family,
                        "duration_minutes": None,
                        "provenance": "No matching active changeover_matrix row exists; no default duration was applied.",
                        "priority": "LOW",
                    })
                continue
            if len(values) != 1 or values[0] < 0:
                issue = {
                    "reason_code": "CHANGEOVER_CONFIGURATION_INVALID", "state": "INVALID_CONFIGURATION",
                    "work_center_id": str(work_center_id),
                    "from_family": previous_family, "to_family": family,
                    "duration_minutes": None,
                    "provenance": "Matching active changeover rows are negative or ambiguous after family normalization; setup was not applied.",
                    "priority": "CRITICAL",
                }
                for member in members:
                    line_issues[member.id].append(issue)
                continue

            duration_minutes = values[0]
            setup_hours = _R(Decimal(duration_minutes) / Decimal(60))
            recipient = min(
                members,
                key=lambda member: (
                    member.planned_start_date or member.period_start,
                    member.line_no,
                    member.id.hex,
                ),
            )
            setup_day = recipient.planned_start_date or recipient.period_start
            setup_key = (work_center_id, setup_day)
            if setup_key not in calendar_map:
                issue = {
                    "reason_code": "CHANGEOVER_CAPACITY_CALENDAR_NOT_CONFIGURED",
                    "state": "NOT_CONFIGURED", "work_center_id": str(work_center_id),
                    "date": setup_day.isoformat(), "duration_minutes": duration_minutes,
                    "priority": "CRITICAL",
                    "provenance": "Configured setup duration could not be placed because its first campaign day has no resource calendar.",
                }
                for member in members:
                    line_issues[member.id].append(issue)
                continue

            slot_allocations[setup_key] += setup_hours
            line_allocations[recipient.id][setup_day] = (
                line_allocations[recipient.id].get(setup_day, Decimal(0)) + setup_hours
            )
            for member in members:
                line_issues[member.id].append({
                    "reason_code": "CHANGEOVER_CAPACITY_APPLIED", "state": "CONFIGURED",
                    "work_center_id": str(work_center_id),
                    "from_family": previous_family, "to_family": family,
                    "duration_minutes": duration_minutes, "changeover_hours": str(setup_hours),
                    "capacity_date": setup_day.isoformat(),
                    "provenance": "Current unique active changeover_matrix row; setup load is allocated once on the successor campaign's first scheduled day.",
                    "priority": "LOW",
                })

    await db.execute(delete(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == mps_id))
    diagnostics = []
    overloaded_lines: set[uuid.UUID] = set()
    for (wc_id, day), allocated in sorted(slot_allocations.items(), key=lambda item: (str(item[0][0]), item[0][1])):
        day_metrics = calendar_metrics[(wc_id, day)]
        metrics = capacity_result(allocated, day_metrics["available"], day_metrics["downtime"])
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
            # Keep the same order used when allocating the daily load. If
            # locked commitments are re-sorted by priority here, an unlocked
            # line can be falsely shown as feasible after a locked overflow.
            contributors = [
                line for line in lines
                if line.work_center_id == wc_id and day in line_allocations[line.id]
            ]
            for line in contributors:
                cumulative += line_allocations[line.id][day]
                cumulative_overload = max(Decimal(0), cumulative - metrics["net_available_hours"])
                line_overload = cumulative_overload - prior_overload
                prior_overload = cumulative_overload
                if line_overload > 0:
                    if not line.is_locked:
                        overloaded_lines.add(line.id)
                    line_issues[line.id].append({
                        "reason_code": "CAPACITY_OVERLOAD", "work_center_id": str(wc_id),
                        "date": day.isoformat(), "required_hours": str(line_allocations[line.id][day]),
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
            informational_unknowns = {"CHANGEOVER_NOT_CONFIGURED", "CIP_NOT_CONFIGURED"}
            non_blocking = {"CAPACITY_OVERLOAD", "CHANGEOVER_CAPACITY_APPLIED", *informational_unknowns}
            if issue_codes - non_blocking:
                line.feasibility_status = MPSFeasibilityStatus.INFEASIBLE
                line.overload_hours = None
            elif line.id in overloaded_lines:
                line.feasibility_status = MPSFeasibilityStatus.OVERLOADED
                line.overload_hours = sum((Decimal(str(i.get("overload_hours", 0))) for i in issues), Decimal(0))
            elif issue_codes & informational_unknowns:
                line.feasibility_status = MPSFeasibilityStatus.PENDING
                line.overload_hours = Decimal(0)
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
