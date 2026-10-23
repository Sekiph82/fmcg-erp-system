"""Deterministic MPS calculations shared by the planning and verification paths.

These helpers deliberately fail closed when the source data cannot establish a
unit, recipe basis, or capacity calendar.  They never substitute a guessed
factory rate, shift, changeover, or currency.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Iterable, Mapping, Sequence


class PlanningInputError(ValueError):
    """Raised when authoritative planning inputs are absent or inconsistent."""


def decimal(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        result = Decimal(str(value))
    except Exception as exc:  # pragma: no cover - Decimal supplies details
        raise PlanningInputError(f"invalid decimal input: {value!r}") from exc
    if not result.is_finite():
        raise PlanningInputError("planning quantities must be finite")
    return result


def round_qty(value: Decimal, places: int = 3) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def period_buckets(start: date, end: date, period_type: str) -> list[tuple[date, date]]:
    """Return inclusive, gap-free buckets clipped to the requested horizon."""
    if end < start:
        raise PlanningInputError("planning horizon end precedes start")
    kind = period_type.upper()
    if kind not in {"DAILY", "WEEKLY", "MONTHLY"}:
        raise PlanningInputError(f"unsupported period type: {period_type}")
    buckets: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        if kind == "DAILY":
            bucket_end = cursor
        elif kind == "WEEKLY":
            bucket_end = min(end, cursor + timedelta(days=6 - cursor.weekday()))
        else:
            bucket_end = min(end, date(cursor.year, cursor.month, monthrange(cursor.year, cursor.month)[1]))
        buckets.append((cursor, bucket_end))
        cursor = bucket_end + timedelta(days=1)
    return buckets


def overlap_days(left_start: date, left_end: date, right_start: date, right_end: date) -> int:
    start = max(left_start, right_start)
    end = min(left_end, right_end)
    return max(0, (end - start).days + 1)


def allocate_period_quantity(
    quantity: object,
    source_start: date,
    source_end: date,
    buckets: Sequence[tuple[date, date]],
) -> list[Decimal]:
    """Allocate an interval quantity by overlapping calendar days, conserving total."""
    qty = decimal(quantity)
    if qty < 0:
        raise PlanningInputError("demand quantities cannot be negative")
    source_days = (source_end - source_start).days + 1
    if source_days <= 0:
        raise PlanningInputError("source demand interval is invalid")
    weights = [Decimal(overlap_days(source_start, source_end, a, b)) for a, b in buckets]
    covered_days = sum(weights, Decimal(0))
    if not buckets:
        return []
    if covered_days <= 0:
        return [Decimal(0)] * len(buckets)
    covered_quantity = round_qty(qty * covered_days / source_days)
    return allocate_weighted_quantity(covered_quantity, weights)


def allocate_weighted_quantity(quantity: object, weights: Sequence[object], places: int = 3) -> list[Decimal]:
    """Allocate a rounded quantity proportionally without negative rounding residues."""
    qty = decimal(quantity)
    if qty < 0:
        raise PlanningInputError("demand quantities cannot be negative")
    normalized_weights = [decimal(weight) for weight in weights]
    if any(weight < 0 for weight in normalized_weights):
        raise PlanningInputError("allocation weights cannot be negative")
    if not normalized_weights:
        if round_qty(qty, places) > 0:
            raise PlanningInputError("a positive quantity requires at least one allocation weight")
        return []
    total_weight = sum(normalized_weights, Decimal(0))
    target = round_qty(qty, places)
    if total_weight <= 0:
        if target == 0:
            return [Decimal(0)] * len(normalized_weights)
        raise PlanningInputError("a positive quantity requires positive allocation weight")

    scale = Decimal(10) ** places
    target_units = int(target * scale)
    raw_units = [Decimal(target_units) * weight / total_weight for weight in normalized_weights]
    allocated_units = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in raw_units]
    remaining_units = target_units - sum(allocated_units)
    # Stable largest-remainder distribution; ties favor later buckets, matching
    # the previous convention of placing rounding residue at the end.
    order = sorted(
        range(len(raw_units)),
        key=lambda index: (raw_units[index] - allocated_units[index], index),
        reverse=True,
    )
    for index in order[:remaining_units]:
        allocated_units[index] += 1
    return [Decimal(units) / scale for units in allocated_units]


def net_finished_goods_requirement(
    *, confirmed: object, forecast: object, safety_stock: object,
    on_hand: object, reserved: object, incoming: object = 0,
    wip: object = 0, other_planned: object = 0,
) -> dict[str, Decimal]:
    """Net stock and dated supply once; confirmed demand consumes forecast first."""
    confirmed_d = decimal(confirmed)
    forecast_d = decimal(forecast)
    safety_d = decimal(safety_stock)
    on_hand_d = decimal(on_hand)
    reserved_d = decimal(reserved)
    incoming_d, wip_d, planned_d = map(decimal, (incoming, wip, other_planned))
    if min(confirmed_d, forecast_d, safety_d, on_hand_d, reserved_d, incoming_d, wip_d, planned_d) < 0:
        raise PlanningInputError("demand and supply inputs cannot be negative")
    available = max(Decimal(0), on_hand_d - reserved_d)
    net_forecast = max(Decimal(0), forecast_d - confirmed_d)
    gross = confirmed_d + net_forecast + safety_d
    total_supply = available + incoming_d + wip_d + planned_d
    return {
        "confirmed": round_qty(confirmed_d),
        "forecast": round_qty(forecast_d),
        "net_forecast": round_qty(net_forecast),
        "safety_stock": round_qty(safety_d),
        "available_on_hand": round_qty(available),
        "incoming": round_qty(incoming_d),
        "wip": round_qty(wip_d),
        "other_planned": round_qty(planned_d),
        "gross_demand": round_qty(gross),
        "total_supply": round_qty(total_supply),
        "net_requirement": round_qty(max(Decimal(0), gross - total_supply)),
    }


def explode_approved_bom(
    *, output_qty: object, output_uom: str, bom: Mapping[str, object],
    lines: Iterable[Mapping[str, object]],
    child_boms: Mapping[str, Mapping[str, object]] | None = None,
    as_of: date | None = None,
    max_depth: int = 16,
) -> list[dict[str, object]]:
    """Recursively scale effective approved BOMs into leaf material needs.

    ``child_boms`` is keyed by stringified BOM id and contains a ``bom`` header
    and its ``lines``. Missing child data, cycles, unsupported components,
    incompatible units and ineffective sub-BOMs all fail closed.
    """
    graph = child_boms or {}

    def explode(current_bom, current_lines, qty, uom, path, depth):
        if depth > max_depth:
            raise PlanningInputError(f"BOM nesting exceeds supported depth {max_depth}")
        bom_id = str(current_bom.get("id") or "<root>")
        if bom_id in path:
            raise PlanningInputError("BOM cycle detected: " + " -> ".join((*path, bom_id)))
        qty_d = decimal(qty)
        base_qty = decimal(current_bom.get("base_qty"))
        base_uom = str(current_bom.get("base_uom") or "").upper()
        output_uom = str(uom or "").upper()
        if qty_d < 0 or base_qty <= 0:
            raise PlanningInputError("BOM output and base quantity must be valid")
        lifecycle = current_bom.get("lifecycle", "")
        if str(getattr(lifecycle, "value", lifecycle)).upper() not in {"APPROVED", "RELEASED"}:
            raise PlanningInputError("no approved/released BOM is available")
        if as_of is not None:
            start, end = current_bom.get("effective_from"), current_bom.get("effective_to")
            if start is not None and start > as_of or end is not None and end < as_of:
                raise PlanningInputError("BOM is not effective on the planned date")
        if base_uom and base_uom != output_uom:
            raise PlanningInputError("BOM base UOM conversion is not configured")
        results = []
        for line in current_lines:
            if bool(line.get("is_optional")):
                continue
            basis_value = line.get("basis_type", "")
            basis = str(getattr(basis_value, "value", basis_value)).upper()
            required = decimal(line.get("required_qty"))
            if required < 0:
                raise PlanningInputError("BOM component quantity cannot be negative")
            if basis == "PER_BATCH":
                amount = required * qty_d / base_qty
            elif basis == "PER_UNIT":
                amount = required * qty_d
            elif basis in {"PER_100KG", "PER_1000L"}:
                token = "KG" if basis == "PER_100KG" else "L"
                if output_uom != token:
                    raise PlanningInputError(f"{basis} requires output UOM {token}; conversion is not configured")
                amount = required * qty_d / (Decimal("100") if basis == "PER_100KG" else Decimal("1000"))
            elif basis == "FIXED":
                amount = required
            else:
                raise PlanningInputError(f"unsupported BOM basis: {basis or 'missing'}")
            losses = decimal(line.get("wastage_pct")) + decimal(line.get("process_loss_pct"))
            if losses < 0 or losses >= 100:
                raise PlanningInputError("BOM loss percentage must be in [0, 100)")
            amount *= Decimal(1) + losses / Decimal(100)
            child_id = line.get("child_bom_id")
            if child_id:
                child = graph.get(str(child_id))
                if child is None:
                    raise PlanningInputError(f"referenced child BOM {child_id} is missing or unavailable")
                child_header = child.get("bom", {})
                required_uom = str(line.get("required_uom") or "").upper()
                if required_uom and required_uom != str(child_header.get("base_uom") or "").upper():
                    raise PlanningInputError("child BOM output UOM does not match its parent component UOM")
                results.extend(explode(child_header, child.get("lines", ()), amount, required_uom, (*path, bom_id), depth + 1))
                continue
            item_type_value = line.get("item_type", "MATERIAL")
            item_type = str(getattr(item_type_value, "value", item_type_value)).upper()
            if not line.get("item_id") or item_type != "MATERIAL":
                raise PlanningInputError("non-material BOM components require an approved child BOM for MPS material feasibility")
            results.append({
                "material_id": line["item_id"], "required_qty": round_qty(amount, 4),
                "uom": str(line.get("required_uom") or "").upper(), "basis_type": basis,
                "substitution_policy": str(line.get("substitution_policy") or "NO_SUB"),
            })
        return results

    return explode(bom, lines, output_qty, output_uom, (), 1)


def capacity_result(required_hours: object, available_hours: object, downtime_hours: object = 0) -> dict[str, Decimal | str]:
    required = decimal(required_hours)
    available = decimal(available_hours)
    downtime = decimal(downtime_hours)
    if min(required, available, downtime) < 0:
        raise PlanningInputError("capacity hours cannot be negative")
    net_available = max(Decimal(0), available - downtime)
    overload = max(Decimal(0), required - net_available)
    return {
        "required_hours": round_qty(required, 3),
        "available_hours": round_qty(available, 3),
        "downtime_hours": round_qty(downtime, 3),
        "net_available_hours": round_qty(net_available, 3),
        "overload_hours": round_qty(overload, 3),
        "status": "OVERLOADED" if overload else "FEASIBLE",
    }


def scenario_kpis(
    *, lines: Sequence[Mapping[str, object]],
    material_shortages: int | None = None,
    capacity_overload_hours: object | None = None,
    changeover_hours: object | None = None,
    cost_delta: object | None = None,
    cost_currency: str | None = None,
) -> dict[str, object]:
    """Transparent scenario KPIs; unknown monetary basis stays unknown."""
    total = len(lines)
    late = sum(1 for line in lines if line.get("late") is True)
    return {
        "schema_version": "mps-scenario-kpis.v1",
        "service_level_pct": round((total - late) * 100 / total, 2) if total else None,
        "line_count": total,
        "late_line_count": late,
        "material_shortage_count": material_shortages,
        "capacity_overload_hours": str(round_qty(decimal(capacity_overload_hours), 3)) if capacity_overload_hours is not None else None,
        "capacity_overload_unit": "hours" if capacity_overload_hours is not None else None,
        "changeover_hours": str(round_qty(decimal(changeover_hours), 3)) if changeover_hours is not None else None,
        "changeover_unit": "hours" if changeover_hours is not None else None,
        "estimated_cost_delta": str(round_qty(decimal(cost_delta), 4)) if cost_delta is not None and cost_currency else None,
        "cost_currency": cost_currency if cost_delta is not None else None,
        "unknowns": ["cost basis or currency is not configured"] if cost_delta is None or not cost_currency else [],
    }
