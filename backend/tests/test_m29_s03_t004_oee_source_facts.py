"""Focused M29 OEE checks against recorded runtime and output facts."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.oee_calculation import calculate_oee_components
from app.services.production_service import _compute_oee


def test_missing_runtime_does_not_become_planned_time_less_downtime():
    values = calculate_oee_components(
        planned_time_min=480,
        downtime_min=30,
        actual_run_time_min=None,
        ideal_cycle_time_sec=60,
        total_units=100,
        good_units=97,
    )

    assert values["availability"] is None
    assert values["performance"] is None
    assert values["quality"] == Decimal("0.9700")
    assert values["oee"] is None


def test_recorded_run_time_is_bounded_by_planned_time_after_downtime():
    values = calculate_oee_components(
        planned_time_min=100,
        downtime_min=20,
        actual_run_time_min=90,
        ideal_cycle_time_sec=60,
        total_units=40,
        good_units=40,
    )

    assert values["availability"] == Decimal("0.8000")
    assert values["performance"] == Decimal("0.5000")
    assert values["quality"] == Decimal("1.0000")
    assert values["oee"] == Decimal("0.4000")


def test_invalid_runtime_does_not_invalidate_independent_quality_fact():
    values = calculate_oee_components(
        planned_time_min=100,
        downtime_min=5,
        actual_run_time_min=-1,
        ideal_cycle_time_sec=60,
        total_units=20,
        good_units=18,
    )

    assert values["availability"] is None
    assert values["performance"] is None
    assert values["quality"] == Decimal("0.9000")
    assert values["oee"] is None


def test_production_order_without_actual_end_has_unknown_availability():
    scheduled_start = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
    order = SimpleNamespace(
        id=uuid4(),
        order_no="PO-1",
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_start + timedelta(hours=8),
        actual_start=scheduled_start,
        actual_end=None,
        downtime_logs=[],
    )

    metrics = _compute_oee(order)

    assert metrics.availability is None
    assert metrics.performance is None
    assert metrics.quality is None
    assert metrics.oee is None


def test_production_order_with_invalid_actual_interval_is_not_reported_as_zero_run():
    actual_end = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
    order = SimpleNamespace(
        id=uuid4(),
        order_no="PO-2",
        scheduled_start=actual_end - timedelta(hours=8),
        scheduled_end=actual_end,
        actual_start=actual_end + timedelta(minutes=5),
        actual_end=actual_end,
        downtime_logs=[],
    )

    metrics = _compute_oee(order)

    assert metrics.availability is None
    assert metrics.performance is None
    assert metrics.oee is None
