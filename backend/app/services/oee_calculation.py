"""Canonical Overall Equipment Effectiveness component calculations.

All metric values use a 0..1 ratio. Missing source facts remain None instead
of being substituted with fabricated perfect scores.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


_FOUR_PLACES = Decimal("0.0001")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_SIXTY = Decimal("60")


def _decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _ratio(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return min(max(value, _ZERO), _ONE).quantize(_FOUR_PLACES)


def calculate_oee_components(
    *,
    planned_time_min: Optional[int],
    downtime_min=0,
    actual_run_time_min=None,
    ideal_cycle_time_sec=None,
    total_units=None,
    good_units=None,
) -> dict[str, Optional[Decimal]]:
    """Calculate OEE from independently recorded time, rate, and count facts.

    Availability requires observed runtime and is bounded by planned time less
    recorded downtime. Performance uses observed runtime and ideal cycle output.
    Quality uses good / total units and remains independent of time data.
    """
    planned = _decimal(planned_time_min)
    downtime = _decimal(downtime_min)
    supplied_runtime = _decimal(actual_run_time_min)
    planned_valid = planned is not None and planned >= _ZERO
    downtime_valid = downtime is not None and downtime >= _ZERO
    runtime_valid = supplied_runtime is not None and supplied_runtime >= _ZERO
    available_run = (
        max(planned - downtime, _ZERO)
        if planned_valid and downtime_valid
        else None
    )

    availability = None
    if (
        planned is not None and planned > _ZERO
        and available_run is not None
        and runtime_valid
    ):
        availability = _ratio(min(supplied_runtime, available_run) / planned)

    ideal_cycle = _decimal(ideal_cycle_time_sec)
    total = _decimal(total_units)
    good = _decimal(good_units)
    performance = None
    performance_run = supplied_runtime if runtime_valid else None
    if planned is not None and planned > _ZERO and available_run is not None and performance_run is not None:
        performance_run = min(performance_run, available_run)
    if (
        ideal_cycle is not None and ideal_cycle > _ZERO
        and total is not None and total >= _ZERO
        and runtime_valid
        and performance_run is not None and performance_run > _ZERO
    ):
        ideal_output = performance_run * _SIXTY / ideal_cycle
        if ideal_output > _ZERO:
            performance = _ratio(total / ideal_output)

    quality = None
    if total is not None and total > _ZERO and good is not None and _ZERO <= good <= total:
        quality = _ratio(good / total)

    oee = None
    if availability is not None and performance is not None and quality is not None:
        oee = _ratio(availability * performance * quality)
    return {
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "oee": oee,
    }
