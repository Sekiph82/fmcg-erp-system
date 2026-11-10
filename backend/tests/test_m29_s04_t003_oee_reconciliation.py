"""M29.S04.T003 — OEE reconciliation focused unit tests.

Verifies that OEE components are derived from actual production time/count facts,
that the shared calculator handles edge cases consistently, and that the
production_service integration path matches the calculator contract.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.oee_calculation import calculate_oee_components
from app.services.production_service import _compute_oee


# ── calculate_oee_components boundary tests ───────────────────────────────────

def test_zero_downtime_full_run():
    r = calculate_oee_components(
        planned_time_min=480,
        downtime_min=0,
        actual_run_time_min=480,
        ideal_cycle_time_sec=60,
        total_units=480,
        good_units=480,
    )
    assert r["availability"] == Decimal("1.0000")
    assert r["performance"] == Decimal("1.0000")
    assert r["quality"] == Decimal("1.0000")
    assert r["oee"] == Decimal("1.0000")


def test_oee_with_all_three_losses():
    # 480 planned, 60 downtime, 300 actual run, 60s cycle, 200 total, 180 good
    r = calculate_oee_components(
        planned_time_min=480,
        downtime_min=60,
        actual_run_time_min=300,
        ideal_cycle_time_sec=60,
        total_units=200,
        good_units=180,
    )
    assert r["availability"] is not None
    assert r["performance"] is not None
    assert r["quality"] == Decimal("0.9000")
    assert r["oee"] is not None
    # availability = min(300, 420)/480 = 300/480 = 0.6250
    assert r["availability"] == Decimal("0.6250")


def test_planned_time_zero_produces_no_availability():
    # Availability requires planned_time > 0; performance uses runtime and cycle independently.
    r = calculate_oee_components(
        planned_time_min=0,
        downtime_min=0,
        actual_run_time_min=10,
        ideal_cycle_time_sec=60,
        total_units=10,
        good_units=10,
    )
    assert r["availability"] is None
    # quality still computable
    assert r["quality"] == Decimal("1.0000")
    # oee is None because availability is None
    assert r["oee"] is None


def test_good_units_above_total_suppresses_quality():
    r = calculate_oee_components(
        planned_time_min=100,
        downtime_min=0,
        actual_run_time_min=100,
        ideal_cycle_time_sec=60,
        total_units=50,
        good_units=60,  # impossible
    )
    assert r["quality"] is None


def test_oee_is_none_if_any_component_is_none():
    r = calculate_oee_components(
        planned_time_min=100,
        downtime_min=0,
        actual_run_time_min=None,
        ideal_cycle_time_sec=None,
        total_units=100,
        good_units=90,
    )
    assert r["oee"] is None


# ── _compute_oee integration path ─────────────────────────────────────────────

def _order(scheduled_start, scheduled_end, actual_start=None, actual_end=None, downtime_logs=None):
    return SimpleNamespace(
        id=uuid4(),
        order_no="TEST-01",
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        actual_start=actual_start,
        actual_end=actual_end,
        downtime_logs=downtime_logs or [],
    )


BASE = datetime(2026, 11, 10, 8, 0, 0, tzinfo=timezone.utc)


def test_full_run_no_downtime_availability_one():
    o = _order(BASE, BASE + timedelta(hours=8), BASE, BASE + timedelta(hours=8))
    m = _compute_oee(o)
    assert m.availability == 1.0
    assert m.downtime_minutes == 0


def test_downtime_reduces_availability():
    log = SimpleNamespace(duration_minutes=60)
    o = _order(
        BASE, BASE + timedelta(hours=8),
        BASE, BASE + timedelta(hours=8),
        downtime_logs=[log],
    )
    m = _compute_oee(o)
    # actual run = 480 - 60 = 420; availability = min(420,420)/480 = 0.875
    assert m.availability is not None
    assert abs(m.availability - 0.875) < 0.001


def test_no_actual_end_means_no_oee():
    o = _order(BASE, BASE + timedelta(hours=8), actual_start=BASE, actual_end=None)
    m = _compute_oee(o)
    assert m.availability is None
    assert m.oee is None


def test_scheduled_time_zero_means_no_availability():
    # Identical start/end → 0 planned minutes
    o = _order(BASE, BASE, BASE, BASE)
    m = _compute_oee(o)
    assert m.availability is None
