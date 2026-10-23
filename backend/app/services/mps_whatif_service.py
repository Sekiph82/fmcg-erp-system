"""
MPS What-If Simulation Service

A what-if scenario proposes a set of changes (delay, batch resize, line change, etc.)
and computes the impact WITHOUT touching the live MPS plan.

Impact metrics:
- impact_service_level_pct: % lines that remain on-time after changes
- impact_delay_count: number of lines pushed beyond period_end
- impact_cost_delta: estimated change in production cost (hours × rate)
"""
from __future__ import annotations

import uuid
import json
import logging
import re
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSWhatIfScenario, MPSCapacityMode,
    WhatIfStatus, MPSChangeType,
)
from app.models.master import Product
from app.models.planning import ResourceCalendar
from app.models.planning import ChangeoverMatrix
from app.models.production_advanced import WorkCenter
from app.models.production_advanced import DowntimeEvent
from app.schemas.mps import MPSWhatIfCreate, MPSWhatIfOut

logger = logging.getLogger(__name__)


async def _next_scenario_no(db: AsyncSession, mps_id: uuid.UUID) -> str:
    """Allocate a globally unique scenario suffix without relying on row counts."""
    if db.get_bind().dialect.name == "postgresql":
        result = await db.execute(
            text("SELECT nextval(CAST(:sequence_name AS regclass))"),
            {"sequence_name": "mps_whatif_scenario_no_seq"},
        )
        number = result.scalar_one()
    else:
        result = await db.execute(select(MPSWhatIfScenario.scenario_no))
        largest = 0
        for value in result.scalars().all():
            match = re.fullmatch(r"WI-[0-9A-Fa-f]{6}-([0-9]+)", value) if isinstance(value, str) else None
            if match:
                largest = max(largest, int(match.group(1)))
        number = largest + 1
    return f"WI-{mps_id.hex[:6].upper()}-{number:04d}"


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


def _capacity_rate_per_hour(work_center: WorkCenter, product: Product) -> Decimal | None:
    if not work_center.capacity or _D(work_center.capacity) <= 0:
        return None
    capacity_uom = str(work_center.capacity_uom or "").strip().upper().replace(" ", "")
    product_uom = str(getattr(product.uom, "value", product.uom) or "").upper()
    valid = {f"{product_uom}/HR", f"{product_uom}/HOUR"}
    if product_uom in {"PCS", "EA", "UNIT", "UNITS"}:
        valid.add("UNITS/HR")
    return _D(work_center.capacity) if capacity_uom in valid else None


def _scenario_capacity_loads(
    lines: list[dict], wcs: dict[uuid.UUID, WorkCenter], products: dict[uuid.UUID, Product],
    calendars: dict[tuple[uuid.UUID, date], ResourceCalendar], downtimes: list[DowntimeEvent],
    capacity_mode: MPSCapacityMode,
    shift_additions: dict[tuple[uuid.UUID, date], Decimal] | None = None,
) -> dict:
    """Pure candidate schedule load using the same calendar and rate inputs as finite MPS capacity."""
    if capacity_mode == MPSCapacityMode.INFINITE:
        return {"overload_hours": 0.0, "status": "INFINITE", "unknown_reasons": [], "slot_count": 0}
    loads: dict[tuple[uuid.UUID, date], Decimal] = {}
    unknown: set[str] = set()
    for line in lines:
        if _D(line.get("planned_production_qty")) <= 0:
            continue
        try:
            wc_id = uuid.UUID(str(line.get("work_center_id")))
            product_id = uuid.UUID(str(line.get("product_id")))
            start = date.fromisoformat(str(line.get("planned_start_date") or line["period_start"]))
            end = date.fromisoformat(str(line.get("planned_end_date") or line["period_end"]))
        except (KeyError, TypeError, ValueError):
            unknown.add("LINE_SCHEDULE_OR_SCOPE_MISSING")
            continue
        if end < start:
            unknown.add("LINE_SCHEDULE_INVALID")
            continue
        wc, product = wcs.get(wc_id), products.get(product_id)
        if wc is None or product is None:
            unknown.add("WORK_CENTER_OR_PRODUCT_MISSING")
            continue
        if str(getattr(wc.status, "value", wc.status) or "").lower() != "active":
            unknown.add("WORK_CENTER_INACTIVE")
            continue
        rate = _capacity_rate_per_hour(wc, product)
        if rate is None:
            unknown.add("CAPACITY_RATE_OR_UOM_NOT_CONFIGURED")
            continue
        days = []
        cursor = start
        while cursor <= end:
            days.append(cursor)
            cursor += timedelta(days=1)
        configured = [day for day in days if (wc_id, day) in calendars]
        if not configured:
            unknown.add("CAPACITY_CALENDAR_NOT_CONFIGURED")
            continue
        if len(configured) != len(days):
            unknown.add("CAPACITY_CALENDAR_GAP")
        required = _D(line["planned_production_qty"]) / rate
        per_day = required / Decimal(len(configured))
        for day in configured:
            key = (wc_id, day)
            loads[key] = loads.get(key, Decimal(0)) + per_day

    overload_total = Decimal(0)
    shift_additions = shift_additions or {}
    for (wc_id, day), required in loads.items():
        calendar = calendars.get((wc_id, day))
        if calendar is None:
            unknown.add("CAPACITY_CALENDAR_NOT_CONFIGURED")
            available = Decimal(0)
        else:
            available = Decimal(0) if calendar.is_holiday or calendar.is_maintenance else _D(calendar.available_hours)
        # Downtime reduces the configured shift capacity first. Added scenario
        # hours are extra calendar time and must not silently erase downtime.
        downtime_hours = Decimal(0)
        unbounded = False
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        for event in downtimes:
            if event.work_center_id != wc_id or event.start_time >= end:
                continue
            if event.end_time is None and not event.duration_min:
                if event.start_time.date() <= day:
                    unbounded = True
                continue
            event_end = event.end_time or event.start_time + timedelta(minutes=int(event.duration_min or 0))
            left, right = max(start, event.start_time), min(end, event_end)
            if right > left:
                downtime_hours += Decimal(str((right - left).total_seconds())) / Decimal(3600)
        if unbounded:
            unknown.add("OPEN_DOWNTIME_UNBOUNDED")
            downtime_hours = available
        net_available = max(Decimal(0), available - min(downtime_hours, available))
        net_available += shift_additions.get((wc_id, day), Decimal(0))
        overload_total += max(Decimal(0), required - net_available)
    return {
        "overload_hours": None if unknown else float(_R(overload_total)),
        "known_overload_hours": float(_R(overload_total)),
        "status": "COMPLETE" if not unknown else "PARTIAL_INPUTS",
        "unknown_reasons": sorted(unknown),
        "slot_count": len(loads),
    }


def _validate_shift_additions(
    additions: dict[tuple[uuid.UUID, date], Decimal],
    calendars: dict[tuple[uuid.UUID, date], ResourceCalendar],
    downtimes: list[DowntimeEvent] | None = None,
) -> tuple[dict[tuple[uuid.UUID, date], Decimal], set[str]]:
    """Validate aggregate extra hours against a configured 24-hour day.

    ResourceCalendar.available_hours is the work-center's configured shift
    total. The scenario API has no start/end time for an added shift, so it can
    only safely allocate the unoccupied remainder of that calendar day. A
    missing calendar or inconsistent calendar is reported as unknown and its
    added hours are not credited to capacity.
    """
    unknown: set[str] = set()
    valid: dict[tuple[uuid.UUID, date], Decimal] = {}
    for key, hours in additions.items():
        wc_id, shift_day = key
        day_start = datetime.combine(shift_day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        has_downtime = False
        for event in downtimes or []:
            if event.work_center_id != wc_id or event.start_time >= day_end:
                continue
            if event.end_time is None and not event.duration_min:
                has_downtime = True
                break
            event_end = event.end_time or event.start_time + timedelta(minutes=int(event.duration_min or 0))
            if event_end > day_start:
                has_downtime = True
                break
        if has_downtime:
            # No added-shift interval is supplied, so overlap with this day's
            # downtime cannot be ruled out and the hours must remain uncredited.
            unknown.add("SHIFT_ADD_DOWNTIME_OVERLAP_UNRESOLVED")
            continue
        calendar = calendars.get(key)
        if calendar is None:
            unknown.add("SHIFT_ADD_CALENDAR_NOT_CONFIGURED")
            continue
        configured_hours = _D(calendar.available_hours)
        if not configured_hours.is_finite() or configured_hours < 0 or configured_hours > Decimal(24):
            unknown.add("SHIFT_ADD_CALENDAR_HOURS_INVALID")
            continue
        windows = []
        malformed_window = False
        for index in range(1, 4):
            raw_start = getattr(calendar, f"shift_{index}_start", None)
            raw_end = getattr(calendar, f"shift_{index}_end", None)
            if not raw_start and not raw_end:
                continue
            try:
                start_time = time.fromisoformat(str(raw_start))
                end_time = time.fromisoformat(str(raw_end))
            except (TypeError, ValueError):
                malformed_window = True
                break
            start_min = start_time.hour * 60 + start_time.minute
            end_min = end_time.hour * 60 + end_time.minute
            if start_min == end_min:
                malformed_window = True
                break
            if end_min > start_min:
                windows.append((start_min, end_min))
            else:
                windows.extend(((start_min, 1440), (0, end_min)))
        if malformed_window:
            unknown.add("SHIFT_ADD_CALENDAR_SHIFT_WINDOW_INVALID")
            continue
        if not windows:
            unknown.add("SHIFT_ADD_CALENDAR_SHIFT_WINDOWS_NOT_CONFIGURED")
            continue
        ordered_windows = sorted(windows)
        if any(left[1] > right[0] for left, right in zip(ordered_windows, ordered_windows[1:])):
            unknown.add("SHIFT_ADD_CALENDAR_SHIFTS_OVERLAP")
            continue
        window_hours = Decimal(sum(end - start for start, end in windows)) / Decimal(60)
        if window_hours != configured_hours:
            unknown.add("SHIFT_ADD_CALENDAR_HOURS_MISMATCH")
            continue
        if calendar.is_holiday or calendar.is_maintenance:
            raise ValueError("SHIFT_ADD cannot target a holiday or maintenance calendar")
        if hours > Decimal(24) - configured_hours:
            raise ValueError("Aggregate SHIFT_ADD hours exceed remaining work-center calendar hours for the day")
        valid[key] = hours
    return valid, unknown


def _scenario_changeover_hours(
    lines: list[dict], products: dict[uuid.UUID, Product], changeover_rows: list[ChangeoverMatrix],
) -> dict:
    """Recalculate family-transition setup time using configured matrix rows."""
    matrix = {
        (row.work_center_id, str(row.from_family).upper(), str(row.to_family).upper()): int(row.changeover_minutes)
        for row in changeover_rows if row.is_active
    }
    ordered = []
    unknown: set[str] = set()
    for line in lines:
        if line.get("_merged_into") or ("planned_production_qty" in line and _D(line.get("planned_production_qty")) <= 0):
            continue
        try:
            wc_id = uuid.UUID(str(line.get("work_center_id")))
            product_id = uuid.UUID(str(line.get("product_id")))
            start = date.fromisoformat(str(line.get("planned_start_date") or line["period_start"]))
        except (KeyError, TypeError, ValueError):
            unknown.add("LINE_SCHEDULE_OR_SCOPE_MISSING")
            continue
        product = products.get(product_id)
        if product is None:
            unknown.add("PRODUCT_FAMILY_MISSING")
            continue
        family = str(getattr(product.category, "value", product.category) or "").upper()
        if not family:
            unknown.add("PRODUCT_FAMILY_MISSING")
            continue
        ordered.append((wc_id, start, str(line.get("id", "")), family))

    previous: dict[uuid.UUID, str] = {}
    total_minutes = Decimal(0)
    transition_count = 0
    for wc_id, _start, _line_id, family in sorted(ordered):
        prior = previous.get(wc_id)
        if prior and prior != family:
            minutes = matrix.get((wc_id, prior, family))
            if minutes is None:
                unknown.add(f"CHANGEOVER_NOT_CONFIGURED:{prior}->{family}")
            else:
                total_minutes += Decimal(minutes)
                transition_count += 1
        previous[wc_id] = family
    return {
        "hours": float(_R(total_minutes / Decimal(60))),
        "status": "COMPLETE" if not unknown else "PARTIAL_INPUTS",
        "unknown_reasons": sorted(unknown),
        "transition_count": transition_count,
    }


class _ScenarioSimulationRollback(Exception):
    def __init__(self, result: dict):
        super().__init__("rollback temporary MPS scenario simulation")
        self.result = result


async def _simulate_scenario_materials(db: AsyncSession, mps_id: uuid.UUID, snapshots: dict[str, dict]) -> dict:
    """Run the production material feasibility service inside a rolled-back savepoint.

    The existing service loads the plan's warehouse, approved/effective BOM or
    recipe, nested components, warehouse stock, and dated purchase receipts.
    Temporarily applying a snapshot inside a savepoint gives what-if plans the
    same calculation without persisting line, diagnostic, or counter changes.
    """
    try:
        async def run_once(snapshot_set: dict[str, dict]) -> dict:
            try:
                async with db.begin_nested():
                    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))).scalar_one()
                    lines = (await db.execute(select(MPSLine).where(MPSLine.mps_id == mps_id))).scalars().all()
                    for line in lines:
                        candidate = snapshot_set.get(str(line.id))
                        if candidate is None:
                            continue
                        line.planned_production_qty = Decimal(str(candidate["planned_production_qty"]))
                        for key in ("planned_start_date", "planned_end_date"):
                            if candidate.get(key):
                                setattr(line, key, date.fromisoformat(str(candidate[key])))
                    from app.services.mps_advanced_service import evaluate_material_feasibility
                    result = await evaluate_material_feasibility(db, mps_id)
                    shortage_quantity_by_uom: dict[str, Decimal] = {}
                    if result.get("diagnostic_run_id"):
                        diagnostics = (await db.execute(text(
                            "SELECT diagnostics FROM mps_line_diagnostics WHERE mps_id = :mps_id AND run_id = :run_id"
                        ), {"mps_id": mps_id, "run_id": uuid.UUID(result["diagnostic_run_id"])})).scalars().all()
                        for diagnostic in diagnostics:
                            for issue in diagnostic.get("issues", []):
                                if issue.get("reason_code") == "MATERIAL_SHORT":
                                    uom = str(issue.get("uom") or "").upper()
                                    shortage_quantity_by_uom[uom] = shortage_quantity_by_uom.get(uom, Decimal(0)) + Decimal(str(issue["shortage_qty"]))
                    raise _ScenarioSimulationRollback({
                        **result,
                        "shortage_quantity_by_uom": {uom: str(value) for uom, value in shortage_quantity_by_uom.items()},
                    })
            except _ScenarioSimulationRollback as rollback:
                return rollback.result

        # Baseline and candidate are independent evaluations against identical
        # stock/receipt state. Each savepoint rollback discards temporary writes.
        baseline_lines = (await db.execute(select(MPSLine).where(MPSLine.mps_id == mps_id))).scalars().all()
        baseline = {
            str(line.id): {
                "planned_production_qty": str(line.planned_production_qty),
                "planned_start_date": line.planned_start_date.isoformat() if line.planned_start_date else None,
                "planned_end_date": line.planned_end_date.isoformat() if line.planned_end_date else None,
            } for line in baseline_lines
        }
        baseline_result = await run_once(baseline)
        candidate_result = await run_once(snapshots)
        if baseline_result is None or candidate_result is None:
            raise ValueError("MPS material feasibility result was not returned")
        complete = baseline_result["infeasible_lines"] == 0 and candidate_result["infeasible_lines"] == 0
        return {
            "status": "COMPLETE" if complete else "PARTIAL_INPUTS",
            "baseline_shortage_count": int(baseline_result["material_short_lines"]),
            "candidate_shortage_count": int(candidate_result["material_short_lines"]),
            "shortage_count_delta": int(candidate_result["material_short_lines"]) - int(baseline_result["material_short_lines"]) if complete else None,
            "unknown_reasons": [] if complete else ["one or more lines lack complete approved material feasibility inputs"],
            "baseline_infeasible_lines": int(baseline_result["infeasible_lines"]),
            "candidate_infeasible_lines": int(candidate_result["infeasible_lines"]),
            "baseline_shortage_quantity_by_uom": baseline_result["shortage_quantity_by_uom"],
            "candidate_shortage_quantity_by_uom": candidate_result["shortage_quantity_by_uom"],
        }
    except Exception as exc:
        logger.exception("MPS material scenario simulation failed")
        return {
            "status": "PARTIAL_INPUTS", "baseline_shortage_count": None,
            "candidate_shortage_count": None, "shortage_count_delta": None,
            "unknown_reasons": [f"material simulation unavailable: {type(exc).__name__}"],
        }
def _batch_count_for_quantity(
    line_snapshot: dict, quantity: Decimal, *, validate_existing: bool = True,
) -> int | None:
    """Return a consistent whole batch count, or reject ambiguous batch data."""
    raw_size = line_snapshot.get("batch_size_qty")
    raw_count = line_snapshot.get("num_batches")
    if raw_size is None:
        if raw_count is not None:
            raise ValueError("Structural scenario changes require a configured batch size when num_batches is set")
        return None
    try:
        batch_size = Decimal(str(raw_size))
    except Exception as exc:
        raise ValueError("Structural scenario changes require a positive finite batch size") from exc
    if not batch_size.is_finite() or batch_size <= 0:
        raise ValueError("Structural scenario changes require a positive finite batch size")
    count = quantity / batch_size
    if not count.is_finite() or count <= 0 or count != count.to_integral_value():
        raise ValueError("Structural scenario quantity must be an exact multiple of batch_size_qty")
    whole_count = int(count)
    if validate_existing and raw_count is not None and int(raw_count) != whole_count:
        raise ValueError("Existing num_batches does not match planned quantity and batch_size_qty")
    return whole_count


def _apply_change(line_snapshot: dict, change: dict) -> dict:
    """Apply one change dict to a line snapshot copy."""
    ct = change["change_type"]
    val = change["new_value"]

    if ct == MPSChangeType.DELAY:
        # val = number of days to delay
        delay_value = Decimal(str(val))
        if not delay_value.is_finite() or delay_value < 0 or delay_value != delay_value.to_integral_value():
            raise ValueError("DELAY must be a non-negative whole number of days")
        delay_days = int(delay_value)
        for df in ("planned_start_date", "planned_end_date", "period_start", "period_end"):
            if line_snapshot.get(df):
                d = date.fromisoformat(str(line_snapshot[df]))
                line_snapshot[df] = (d + timedelta(days=delay_days)).isoformat()

    elif ct == MPSChangeType.BATCH_SIZE:
        new_batch = Decimal(str(val))
        if not new_batch.is_finite() or new_batch <= 0:
            raise ValueError("BATCH_SIZE must be a positive finite quantity")
        old_qty = _D(line_snapshot.get("planned_production_qty", 0))
        if new_batch > 0 and old_qty > 0:
            import math
            n_batches = max(1, math.ceil(float(old_qty) / float(new_batch)))
            line_snapshot["planned_production_qty"] = str(_R(new_batch * n_batches))
            line_snapshot["batch_size_qty"] = str(new_batch)
            line_snapshot["num_batches"] = n_batches

    elif ct == MPSChangeType.QTY_ADJUST:
        new_qty = Decimal(str(val))
        if not new_qty.is_finite() or new_qty <= 0:
            raise ValueError("QTY_ADJUST must be a positive finite quantity")
        line_snapshot["planned_production_qty"] = str(new_qty)

    elif ct == MPSChangeType.LINE_CHANGE:
        line_snapshot["work_center_id"] = str(val)

    elif ct == MPSChangeType.SPLIT:
        raw_parts = val.get("quantities") if isinstance(val, dict) else val
        if not isinstance(raw_parts, (list, tuple)) or len(raw_parts) != 2:
            raise ValueError("SPLIT requires exactly two quantities in new_value.quantities")
        try:
            parts = [Decimal(str(part)) for part in raw_parts]
        except Exception as exc:
            raise ValueError("SPLIT quantities must be positive finite numbers") from exc
        if any(not part.is_finite() or part <= 0 or part != _R(part) for part in parts):
            raise ValueError("SPLIT quantities must be positive finite quantities with at most 3 decimals")
        original_qty = _D(line_snapshot.get("planned_production_qty", 0))
        if sum(parts, Decimal(0)) != original_qty:
            raise ValueError("SPLIT quantities must sum exactly to the original planned quantity")
        line_snapshot["_split_batch_counts"] = [
            _batch_count_for_quantity(line_snapshot, part, validate_existing=False) for part in parts
        ]
        line_snapshot["_split_quantities"] = [str(part) for part in parts]

    elif ct == MPSChangeType.MERGE:
        line_snapshot["_merge_with_line_id"] = str(val)

    elif ct == MPSChangeType.SHIFT_ADD:
        # SHIFT_ADD capacity is collected and applied at scenario level. Keep
        # the explicit assumption with the target line for durable replay.
        if not isinstance(val, dict):
            raise ValueError("SHIFT_ADD requires an object with date and hours")
        line_snapshot.setdefault("_added_shifts", []).append({
            "date": str(val.get("date", "")), "hours": str(val.get("hours", "")),
        })

    return line_snapshot


def _compute_impact(
    original_lines: List[dict],
    modified_lines: Dict[str, dict],
    wcs: Dict[uuid.UUID, WorkCenter],
) -> tuple:
    """
    Returns service level and delay count. Monetary impact is unknown unless a
    currency and validated cost basis are available; neither is stored here.
    """
    total = len(original_lines)
    if total == 0:
        return 100.0, 0, None

    delay_count = 0

    for orig in original_lines:
        line_id = str(orig["id"])
        modified = modified_lines.get(line_id, orig)

        orig_end = orig.get("planned_end_date") or orig.get("period_end")
        mod_end = modified.get("planned_end_date") or modified.get("period_end")
        period_end = orig.get("period_end")

        if orig_end and mod_end and period_end:
            orig_end_d = date.fromisoformat(str(orig_end))
            mod_end_d = date.fromisoformat(str(mod_end))
            period_d = date.fromisoformat(str(period_end))
            if mod_end_d > period_d:
                delay_count += 1


    on_time = total - delay_count
    svc_level = round(on_time / total * 100, 2)
    return svc_level, delay_count, None


def _expand_candidate_lines(lines: list[dict]) -> list[dict]:
    """Expand exact split assumptions into separate candidate capacity runs."""
    expanded: list[dict] = []
    for line in lines:
        if line.get("_merged_into") or ("planned_production_qty" in line and _D(line.get("planned_production_qty")) <= 0):
            continue
        parts = line.get("_split_quantities")
        if not parts:
            expanded.append(line)
            continue
        for index, quantity in enumerate(parts, start=1):
            split_line = deepcopy(line)
            split_line["id"] = f"{line['id']}:split:{index}"
            split_line["planned_production_qty"] = quantity
            # The scenario's capacity engine recomputes hours from quantity
            # and configured rate; do not repeat the source line's stale value.
            split_line["required_hours"] = None
            batch_counts = line.get("_split_batch_counts")
            if batch_counts is not None:
                split_line["num_batches"] = batch_counts[index - 1]
            split_line["_split_part"] = index
            expanded.append(split_line)
    return expanded


async def create_whatif_scenario(
    db: AsyncSession,
    mps_id: uuid.UUID,
    data: MPSWhatIfCreate,
    user_id: uuid.UUID,
) -> MPSWhatIfScenario:
    if not data.changes:
        raise ValueError("What-if scenario must include at least one proposed change")
    # Snapshot scenarios against a stable line set. MPS writers take this
    # parent lock before mutating plan lines, so the snapshot cannot interleave.
    plan_q = await db.execute(
        select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update()
    )
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")

    scenario_no = await _next_scenario_no(db, mps_id)

    # MERGE carries its second line ID in new_value; include it in the same
    # scoped lookup and require every referenced line to belong to this plan.
    line_ids = [c.line_id for c in data.changes]
    for change in data.changes:
        if change.change_type == MPSChangeType.MERGE:
            try:
                line_ids.append(uuid.UUID(str(change.new_value)))
            except (TypeError, ValueError) as exc:
                raise ValueError("MERGE requires the second MPS line id as new_value") from exc
    lines_q = await db.execute(
        select(MPSLine).where(
            MPSLine.id.in_(line_ids),
            MPSLine.mps_id == mps_id,
        )
    )
    affected_lines = {l.id: l for l in lines_q.scalars().all()}
    if len(affected_lines) != len(set(line_ids)):
        raise ValueError("All what-if changes must target lines in this MPS plan")

    # Load all plan lines for service level calc
    all_lines_q = await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
    )
    all_lines = all_lines_q.scalars().all()

    # Load work centers
    wc_q = await db.execute(select(WorkCenter))
    wcs: Dict[uuid.UUID, WorkCenter] = {wc.id: wc for wc in wc_q.scalars().all()}

    # Build snapshots
    def _snap(line: MPSLine) -> dict:
        return {
            "id": str(line.id),
            "product_id": str(line.product_id),
            "mrp_result_id": str(line.mrp_result_id) if line.mrp_result_id else None,
            "planned_production_qty": str(line.planned_production_qty),
            "planned_start_date": str(line.planned_start_date) if line.planned_start_date else None,
            "planned_end_date": str(line.planned_end_date) if line.planned_end_date else None,
            "period_start": str(line.period_start),
            "period_end": str(line.period_end),
            "work_center_id": str(line.work_center_id) if line.work_center_id else None,
            "batch_size_qty": str(line.batch_size_qty) if line.batch_size_qty else None,
            "num_batches": line.num_batches,
            "campaign_id": str(line.campaign_id) if line.campaign_id else None,
            "priority_score": str(line.priority_score),
            "feasibility_status": str(getattr(line.feasibility_status, "value", line.feasibility_status)),
            "required_hours": str(line.required_hours) if line.required_hours is not None else None,
            "confirmed_demand_qty": str(line.confirmed_demand_qty),
            "forecast_qty": str(line.forecast_qty),
            "safety_stock_qty": str(line.safety_stock_qty),
            "net_requirement_qty": str(line.net_requirement_qty),
        }

    original_snaps = [_snap(l) for l in all_lines]
    modified_map: Dict[str, dict] = {s["id"]: deepcopy(s) for s in original_snaps}

    # Apply changes
    changes_json = []
    structural_lines: set[uuid.UUID] = set()
    non_shift_lines: set[uuid.UUID] = set()
    shift_lines: set[uuid.UUID] = set()
    shift_additions: dict[tuple[uuid.UUID, date], Decimal] = {}
    for change in data.changes:
        lid = str(change.line_id)
        line = affected_lines[change.line_id]
        if line.is_locked:
            raise ValueError("What-if changes cannot target a locked MPS line")
        if change.change_type == MPSChangeType.MERGE:
            if change.line_id in structural_lines or change.line_id in non_shift_lines or change.line_id in shift_lines:
                raise ValueError("MERGE/SPLIT lines cannot have conflicting scenario changes")
        elif change.change_type == MPSChangeType.SPLIT:
            if change.line_id in structural_lines or change.line_id in non_shift_lines or change.line_id in shift_lines:
                raise ValueError("MERGE/SPLIT lines cannot have conflicting scenario changes")
        elif change.change_type == MPSChangeType.SHIFT_ADD:
            if change.line_id in structural_lines:
                raise ValueError("SHIFT_ADD cannot target a line consumed by MERGE or SPLIT")
        elif change.line_id in structural_lines:
            raise ValueError("MERGE/SPLIT lines cannot have conflicting scenario changes")
        if change.change_type != MPSChangeType.SHIFT_ADD:
            non_shift_lines.add(change.line_id)
        if change.change_type == MPSChangeType.MERGE:
            try:
                merge_id = uuid.UUID(str(change.new_value))
            except (TypeError, ValueError) as exc:
                raise ValueError("MERGE requires the second MPS line id as new_value") from exc
            other = affected_lines.get(merge_id)
            if other is None or merge_id == change.line_id:
                raise ValueError("MERGE requires two distinct lines in this MPS plan")
            if other.is_locked:
                raise ValueError("What-if MERGE cannot target a locked MPS line")
            if merge_id in structural_lines or merge_id in non_shift_lines or merge_id in shift_lines:
                raise ValueError("MERGE/SPLIT lines cannot have conflicting scenario changes")
            target, source = modified_map[str(change.line_id)], modified_map[str(merge_id)]
            match_fields = (
                "product_id", "mrp_result_id", "period_start", "period_end",
                "planned_start_date", "planned_end_date", "work_center_id",
                "campaign_id", "feasibility_status",
            )
            numeric_match_fields = ("batch_size_qty", "priority_score")
            numeric_mismatch = any(
                (target.get(field) is None) != (source.get(field) is None)
                or (
                    target.get(field) is not None
                    and _D(target[field]) != _D(source[field])
                )
                for field in numeric_match_fields
            )
            if numeric_mismatch or any(target.get(field) != source.get(field) for field in match_fields):
                raise ValueError("MERGE requires matching source allocation, product, batch, campaign, period, schedule, work center, and feasibility")
            target_qty, source_qty = _D(target["planned_production_qty"]), _D(source["planned_production_qty"])
            if not target_qty.is_finite() or not source_qty.is_finite() or target_qty <= 0 or source_qty <= 0:
                raise ValueError("MERGE requires two positive finite planned quantities")
            target_batches = _batch_count_for_quantity(target, target_qty)
            source_batches = _batch_count_for_quantity(source, source_qty)
            if (target_batches is None) != (source_batches is None):
                raise ValueError("MERGE requires compatible configured batch sizing")
            if target_batches is not None:
                target["num_batches"] = target_batches + source_batches
            target["planned_production_qty"] = str(_R(target_qty + source_qty))
            target["required_hours"] = None
            source["required_hours"] = None
            for field in ("confirmed_demand_qty", "forecast_qty", "safety_stock_qty", "net_requirement_qty"):
                target[field] = str(_R(_D(target.get(field)) + _D(source.get(field))))
            source["planned_production_qty"] = "0"
            source["_merged_into"] = str(change.line_id)
            structural_lines.update((change.line_id, merge_id))
        elif change.change_type == MPSChangeType.SPLIT:
            _apply_change(modified_map[lid], {"change_type": change.change_type, "new_value": change.new_value})
            structural_lines.add(change.line_id)
        elif change.change_type == MPSChangeType.SHIFT_ADD:
            if plan.capacity_mode != MPSCapacityMode.FINITE:
                raise ValueError("SHIFT_ADD requires a plan in FINITE capacity mode")
            value = change.new_value
            if not isinstance(value, dict):
                raise ValueError("SHIFT_ADD requires an object with date and hours")
            try:
                shift_day = date.fromisoformat(str(value["date"]))
                hours = Decimal(str(value["hours"]))
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise ValueError("SHIFT_ADD requires an ISO date and positive finite hours") from exc
            if not hours.is_finite() or hours <= 0 or hours > 24:
                raise ValueError("SHIFT_ADD hours must be greater than 0 and no more than 24")
            try:
                line_start = date.fromisoformat(str(modified_map[lid].get("planned_start_date") or modified_map[lid]["period_start"]))
                line_end = date.fromisoformat(str(modified_map[lid].get("planned_end_date") or modified_map[lid]["period_end"]))
                wc_id = uuid.UUID(str(modified_map[lid]["work_center_id"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("SHIFT_ADD target requires a scheduled line with a work center") from exc
            if shift_day < line_start or shift_day > line_end:
                raise ValueError("SHIFT_ADD date must fall within the target line schedule")
            shift_additions[(wc_id, shift_day)] = shift_additions.get((wc_id, shift_day), Decimal(0)) + hours
            shift_lines.add(change.line_id)
            _apply_change(modified_map[lid], {"change_type": change.change_type, "new_value": value})
        if change.change_type == MPSChangeType.LINE_CHANGE:
            try:
                target_wc_id = uuid.UUID(str(change.new_value))
            except (TypeError, ValueError) as exc:
                raise ValueError("LINE_CHANGE requires a valid work center id") from exc
            target_wc = wcs.get(target_wc_id)
            if target_wc is None or str(getattr(target_wc.status, "value", target_wc.status)).lower() != "active":
                raise ValueError("LINE_CHANGE requires an active work center")
        if change.change_type == MPSChangeType.DELAY:
            try:
                delay = Decimal(str(change.new_value))
            except Exception as exc:
                raise ValueError("DELAY must be a non-negative whole number of days") from exc
            if not delay.is_finite() or delay < 0 or delay != delay.to_integral_value():
                raise ValueError("DELAY must be a non-negative whole number of days")
        if change.change_type in (MPSChangeType.BATCH_SIZE, MPSChangeType.QTY_ADJUST):
            try:
                quantity = _D(change.new_value)
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise ValueError(f"{change.change_type.value} quantity must be positive and finite") from exc
            if not quantity.is_finite() or quantity <= 0:
                raise ValueError(f"{change.change_type.value} quantity must be positive and finite")
        if lid in modified_map and change.change_type not in (MPSChangeType.MERGE, MPSChangeType.SPLIT, MPSChangeType.SHIFT_ADD):
            modified_map[lid] = _apply_change(modified_map[lid], {
                "change_type": change.change_type,
                "new_value": change.new_value,
            })
        changes_json.append({
            "line_id": lid,
            "change_type": change.change_type,
            "new_value": (
                str(change.new_value) if change.change_type == MPSChangeType.MERGE else
                {"quantities": [str(q) for q in (change.new_value.get("quantities") if isinstance(change.new_value, dict) else change.new_value)]}
                if change.change_type == MPSChangeType.SPLIT else
                {"date": str(change.new_value.get("date")), "hours": str(change.new_value.get("hours"))}
                if change.change_type == MPSChangeType.SHIFT_ADD else
                change.new_value
            ),
        })

    # Compute impact
    svc, delays, cost_delta = _compute_impact(original_snaps, modified_map, wcs)
    product_ids = {uuid.UUID(s["product_id"]) for s in original_snaps}
    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()} if product_ids else {}
    scenario_wc_ids = {uuid.UUID(s["work_center_id"]) for s in modified_map.values() if s.get("work_center_id")}
    scenario_dates = []
    for snap in modified_map.values():
        try:
            scenario_dates.extend((
                date.fromisoformat(str(snap.get("planned_start_date") or snap["period_start"])),
                date.fromisoformat(str(snap.get("planned_end_date") or snap["period_end"])),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    calendar_rows = []
    downtime_rows = []
    if scenario_wc_ids and scenario_dates and plan.capacity_mode == MPSCapacityMode.FINITE:
        first_day, last_day = min(scenario_dates), max(scenario_dates)
        calendar_rows = (await db.execute(select(ResourceCalendar).where(
            ResourceCalendar.work_center_id.in_(scenario_wc_ids),
            ResourceCalendar.calendar_date >= first_day,
            ResourceCalendar.calendar_date <= last_day,
        ))).scalars().all()
        downtime_rows = (await db.execute(select(DowntimeEvent).where(
            DowntimeEvent.work_center_id.in_(scenario_wc_ids),
            DowntimeEvent.start_time < datetime.combine(last_day + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
            (DowntimeEvent.end_time.is_(None)) | (DowntimeEvent.end_time >= datetime.combine(first_day, datetime.min.time(), tzinfo=timezone.utc)),
        ))).scalars().all()
    calendar_map = {(row.work_center_id, row.calendar_date): row for row in calendar_rows}
    valid_shift_additions, shift_unknowns = _validate_shift_additions(shift_additions, calendar_map, downtime_rows)
    candidate_lines = _expand_candidate_lines(list(modified_map.values()))
    capacity_metrics = _scenario_capacity_loads(
        candidate_lines, wcs, products,
        calendar_map,
        downtime_rows, plan.capacity_mode, valid_shift_additions,
    )
    if shift_unknowns:
        capacity_metrics["status"] = "PARTIAL_INPUTS"
        capacity_metrics["overload_hours"] = None
        capacity_metrics["unknown_reasons"] = sorted(set(capacity_metrics["unknown_reasons"]) | shift_unknowns)

    changeover_rows = []
    if scenario_wc_ids:
        changeover_rows = (await db.execute(select(ChangeoverMatrix).where(
            ChangeoverMatrix.work_center_id.in_(scenario_wc_ids),
        ))).scalars().all()
    baseline_changeover = _scenario_changeover_hours(original_snaps, products, changeover_rows)
    candidate_changeover = _scenario_changeover_hours(candidate_lines, products, changeover_rows)
    material_metrics = await _simulate_scenario_materials(db, mps_id, modified_map)

    summary_parts = []
    if delays > 0:
        summary_parts.append(f"{delays} line(s) will be delayed")
    summary_parts.append("cost impact unknown: no approved currency and cost basis are configured")
    if capacity_metrics["status"] == "COMPLETE":
        summary_parts.append(f"projected capacity overload: {capacity_metrics['overload_hours']:.3f} hours")
    elif capacity_metrics["status"] == "INFINITE":
        summary_parts.append("finite capacity overload not applicable in INFINITE mode")
    else:
        summary_parts.append("capacity overload incomplete: " + ", ".join(capacity_metrics["unknown_reasons"]))
    if candidate_changeover["status"] == "COMPLETE":
        summary_parts.append(f"projected configured changeover: {candidate_changeover['hours']:.3f} hours")
    else:
        summary_parts.append("changeover resimulation incomplete: " + ", ".join(candidate_changeover["unknown_reasons"]))
    if material_metrics["status"] == "COMPLETE":
        summary_parts.append(
            f"projected material-short line count: {material_metrics['candidate_shortage_count']} "
            f"(delta {material_metrics['shortage_count_delta']:+d} vs baseline)"
        )
    else:
        summary_parts.append("material resimulation incomplete: " + ", ".join(material_metrics["unknown_reasons"]))
    if delays == 0:
        summary_parts.append("no modeled schedule delay detected")
    if any(c.change_type == MPSChangeType.SPLIT for c in data.changes):
        summary_parts.append("SPLIT uses exact quantity-conserving parts with candidate capacity and changeover re-simulation")
    if valid_shift_additions:
        added_hours = sum(valid_shift_additions.values(), Decimal(0))
        summary_parts.append(f"explicit scenario shifts add {added_hours} capacity hours")
    if shift_unknowns:
        summary_parts.append("scenario shift capacity is incomplete: " + ", ".join(sorted(shift_unknowns)))
    if any(c.change_type == MPSChangeType.MERGE for c in data.changes):
        summary_parts.append("MERGE combines only schedule-equivalent lines and preserves total quantity")
    impact_summary = "; ".join(summary_parts) + f". Projected service level: {svc:.1f}% (estimated)."

    scenario = MPSWhatIfScenario(
        scenario_no=scenario_no,
        scenario_name=data.scenario_name,
        mps_id=mps_id,
        description=data.description,
        changes=changes_json,
        impact_service_level_pct=Decimal(str(svc)),
        impact_delay_count=delays,
        impact_cost_delta=None,
        impact_summary=impact_summary,
        status=WhatIfStatus.COMPUTED,
        created_by_id=user_id,
    )
    db.add(scenario)
    await db.flush()
    snapshot_assumptions = {
        "engine": "mps-whatif.v1",
        "plan_id": str(mps_id),
        "changes": changes_json,
        "line_count": len(original_snaps),
        "cost_basis": None,
        "shift_additions": [
            {"work_center_id": str(wc_id), "date": day.isoformat(), "hours": str(hours)}
            for (wc_id, day), hours in sorted(valid_shift_additions.items(), key=lambda item: (str(item[0][0]), item[0][1]))
        ],
        "uncredited_shift_additions": [
            {"work_center_id": str(wc_id), "date": day.isoformat(), "hours": str(hours)}
            for (wc_id, day), hours in sorted(shift_additions.items(), key=lambda item: (str(item[0][0]), item[0][1]))
            if (wc_id, day) not in valid_shift_additions
        ],
    }
    snapshot_results = {
        "service_level_pct": svc,
        "delay_count": delays,
        "cost_delta": None,
        "cost_delta_status": "UNKNOWN_NO_APPROVED_CURRENCY_BASIS",
        "baseline_material_shortage_count": material_metrics["baseline_shortage_count"],
        "material_shortage_count": material_metrics["candidate_shortage_count"],
        "material_shortage_count_delta": material_metrics["shortage_count_delta"],
        "baseline_material_shortage_quantity_by_uom": material_metrics.get("baseline_shortage_quantity_by_uom"),
        "material_shortage_quantity_by_uom": material_metrics.get("candidate_shortage_quantity_by_uom"),
        "material_status": material_metrics["status"],
        "material_unknown_reasons": material_metrics["unknown_reasons"],
        "capacity_overload_hours": capacity_metrics["overload_hours"],
        "capacity_overload_known_hours": capacity_metrics["known_overload_hours"],
        "capacity_status": capacity_metrics["status"],
        "capacity_unknown_reasons": capacity_metrics["unknown_reasons"],
        "capacity_slot_count": capacity_metrics["slot_count"],
        "capacity_unit": "hours",
        "shift_additions": snapshot_assumptions["shift_additions"],
        "baseline_changeover_hours": baseline_changeover["hours"],
        "baseline_changeover_status": baseline_changeover["status"],
        "changeover_hours": candidate_changeover["hours"] if candidate_changeover["status"] == "COMPLETE" else None,
        "changeover_status": candidate_changeover["status"],
        "changeover_unknown_reasons": candidate_changeover["unknown_reasons"],
        "unknowns": material_metrics["unknown_reasons"] + ["CIP duration source is not configured", "cost currency/basis is not configured"] + candidate_changeover["unknown_reasons"],
        "modified_lines": candidate_lines,
    }
    await db.execute(text("""
        INSERT INTO mps_scenario_snapshots
          (id, scenario_id, snapshot_version, assumptions, results, created_by_id)
        VALUES (:id, :scenario_id, :version, CAST(:assumptions AS jsonb), CAST(:results AS jsonb), :user_id)
    """), {
        "id": uuid.uuid4(), "scenario_id": scenario.id, "version": "mps-whatif.v1",
        "assumptions": json.dumps(snapshot_assumptions), "results": json.dumps(snapshot_results),
        "user_id": user_id,
    })
    return scenario


async def list_whatif_scenarios(db: AsyncSession, mps_id: uuid.UUID):
    q = await db.execute(
        select(MPSWhatIfScenario)
        .where(MPSWhatIfScenario.mps_id == mps_id)
        .order_by(MPSWhatIfScenario.created_at.desc())
    )
    return q.scalars().all()


async def get_whatif_scenario(db: AsyncSession, scenario_id: uuid.UUID):
    q = await db.execute(
        select(MPSWhatIfScenario).where(MPSWhatIfScenario.id == scenario_id)
    )
    return q.scalar_one_or_none()


async def compare_whatif_scenarios(
    db: AsyncSession, mps_id: uuid.UUID, baseline_id: uuid.UUID, candidate_id: uuid.UUID,
) -> dict:
    """Compare immutable saved scenario snapshots without rerunning either case."""
    rows = (await db.execute(text("""
        SELECT scenario_id, snapshot_version, assumptions, results, created_at
        FROM mps_scenario_snapshots
        WHERE scenario_id IN (:baseline_id, :candidate_id)
        ORDER BY created_at DESC
    """), {"baseline_id": baseline_id, "candidate_id": candidate_id})).mappings().all()
    snapshots = {}
    for row in rows:
        snapshots.setdefault(row["scenario_id"], row)
    if baseline_id not in snapshots or candidate_id not in snapshots:
        raise ValueError("Both scenarios must have persisted snapshots")
    baseline, candidate = snapshots[baseline_id], snapshots[candidate_id]
    if baseline["assumptions"].get("plan_id") != str(mps_id) or candidate["assumptions"].get("plan_id") != str(mps_id):
        raise ValueError("Both scenarios must belong to the requested MPS plan")
    bres, cres = baseline["results"], candidate["results"]
    material_complete = (
        cres.get("material_status") == "COMPLETE"
        and bres.get("material_status") == "COMPLETE"
        and cres.get("material_shortage_count") is not None
        and bres.get("material_shortage_count") is not None
    )
    material_quantity_delta = None
    if material_complete:
        baseline_quantities = bres.get("baseline_material_shortage_quantity_by_uom") or {}
        candidate_quantities = cres.get("material_shortage_quantity_by_uom") or {}
        if isinstance(baseline_quantities, dict) and isinstance(candidate_quantities, dict):
            quantity_delta: dict[str, str] = {}
            for uom in sorted(set(baseline_quantities) | set(candidate_quantities)):
                try:
                    baseline_quantity = Decimal(str(baseline_quantities.get(uom, "0")))
                    candidate_quantity = Decimal(str(candidate_quantities.get(uom, "0")))
                except (ArithmeticError, TypeError, ValueError):
                    material_complete = False
                    quantity_delta = {}
                    break
                if not baseline_quantity.is_finite() or not candidate_quantity.is_finite():
                    material_complete = False
                    quantity_delta = {}
                    break
                quantity_delta[str(uom)] = format(candidate_quantity - baseline_quantity, "f")
            if material_complete:
                material_quantity_delta = quantity_delta

    capacity_complete = (
        cres.get("capacity_status") in ("COMPLETE", "INFINITE")
        and bres.get("capacity_status") in ("COMPLETE", "INFINITE")
        and cres.get("capacity_overload_hours") is not None
        and bres.get("capacity_overload_hours") is not None
    )
    changeover_complete = (
        cres.get("changeover_status") == "COMPLETE"
        and bres.get("changeover_status") == "COMPLETE"
        and cres.get("changeover_hours") is not None
        and bres.get("changeover_hours") is not None
    )
    unknowns = []
    for values in (
        cres.get("material_unknown_reasons", []) if not material_complete else [],
        bres.get("material_unknown_reasons", []) if not material_complete else [],
        cres.get("capacity_unknown_reasons", []) if not capacity_complete else [],
        bres.get("capacity_unknown_reasons", []) if not capacity_complete else [],
        cres.get("changeover_unknown_reasons", []) if not changeover_complete else [],
        bres.get("changeover_unknown_reasons", []) if not changeover_complete else [],
    ):
        unknowns.extend(values or [])
    unknowns.extend(("CIP duration source is not configured", "cost currency/basis is not configured"))
    unknowns = list(dict.fromkeys(unknowns))
    return {
        "mps_id": str(mps_id),
        "baseline_scenario_id": str(baseline_id),
        "candidate_scenario_id": str(candidate_id),
        "service_level_pct_delta": round(float(cres["service_level_pct"]) - float(bres["service_level_pct"]), 2),
        "service_level_unit": "percentage_points",
        "delay_count_delta": int(cres["delay_count"]) - int(bres["delay_count"]),
        "delay_count_unit": "lines",
        "cost_delta": None,
        "cost_delta_status": "UNKNOWN_NO_APPROVED_CURRENCY_BASIS",
        "material_status": "COMPLETE" if material_complete else "PARTIAL_INPUTS",
        "material_shortage_count_delta": (
            int(cres["material_shortage_count"]) - int(bres["material_shortage_count"])
            if material_complete else None
        ),
        "material_shortage_quantity_by_uom_delta": material_quantity_delta,
        "capacity_overload_hours_delta": (
            round(float(cres["capacity_overload_hours"]) - float(bres["capacity_overload_hours"]), 3)
            if capacity_complete else None
        ),
        "capacity_status": "COMPLETE" if capacity_complete else "PARTIAL_INPUTS",
        "capacity_unit": "hours",
        "changeover_hours_delta": (
            round(float(cres["changeover_hours"]) - float(bres["changeover_hours"]), 3)
            if changeover_complete else None
        ),
        "changeover_status": "COMPLETE" if changeover_complete else "PARTIAL_INPUTS",
        "changeover_unit": "hours",
        "confidence_status": "PARTIAL_INPUTS" if unknowns else "COMPLETE_INPUTS",
        "unknowns": unknowns,
        "metric_sources": {
            "service_level": "persisted scenario estimate: lines scheduled by period end / all plan lines",
            "delivery_delay": "persisted scenario estimate: lines ending after their plan period",
            "material_shortages": "persisted scenario material-feasibility diagnostics; quantities grouped by source UOM",
            "capacity_overload": "persisted scenario estimate using configured work-center rates, calendars, and downtime",
            "changeover": "persisted scenario estimate using active configured changeover matrix rows",
            "cost": "unknown until an approved currency and cost basis are configured",
        },
        "baseline_version": baseline["snapshot_version"],
        "candidate_version": candidate["snapshot_version"],
    }
