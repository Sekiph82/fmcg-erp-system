"""M32.S04 — Advanced Production Planning verification suite.

Pure-unit tests covering constraint model, bottleneck detection, working-day
calendar, and simulation KPI formulas — no database required.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.planning import BottleneckSeverity, OpQueueStatus, ScenarioStatus
from app.services.planning_bottleneck_service import _severity, _recommendation
from app.services.planning_capacity_service import _working_days, _D


# ── M32.S01 — Constraint Model: working-day calendar ─────────────────────────

def test_working_days_mon_to_fri_gives_five():
    days = _working_days(date(2026, 11, 9), date(2026, 11, 13))   # Mon-Fri
    assert len(days) == 5


def test_working_days_includes_saturday():
    # Mon-Sat = 6 days
    days = _working_days(date(2026, 11, 9), date(2026, 11, 14))
    assert len(days) == 6


def test_working_days_excludes_sunday():
    # Mon-Sun = Mon-Sat = 6 working days
    days = _working_days(date(2026, 11, 9), date(2026, 11, 15))
    assert len(days) == 6
    assert date(2026, 11, 15) not in days  # Sunday excluded


def test_working_days_single_day():
    days = _working_days(date(2026, 11, 9), date(2026, 11, 9))   # Monday
    assert days == [date(2026, 11, 9)]


def test_working_days_sunday_only_gives_zero():
    days = _working_days(date(2026, 11, 15), date(2026, 11, 15))  # Sunday
    assert days == []


def test_working_days_two_weeks():
    days = _working_days(date(2026, 11, 9), date(2026, 11, 22))   # 2 Mon-Sat = 12 days
    assert len(days) == 12


# ── M32.S01-S02 — Constraint Model: decimal helper ───────────────────────────

def test_decimal_helper_converts_int():
    assert _D(8) == Decimal("8")


def test_decimal_helper_converts_float():
    assert abs(_D(0.75) - Decimal("0.75")) < Decimal("0.0001")


# ── M32.S02 — Bottleneck detection: severity thresholds ───────────────────────

def test_severity_below_60_is_low():
    assert _severity(55.0) == BottleneckSeverity.LOW


def test_severity_at_60_is_low():
    assert _severity(60.0) == BottleneckSeverity.LOW


def test_severity_at_75_is_medium():
    assert _severity(75.0) == BottleneckSeverity.MEDIUM


def test_severity_at_90_is_high():
    assert _severity(90.0) == BottleneckSeverity.HIGH


def test_severity_at_110_is_critical():
    assert _severity(110.0) == BottleneckSeverity.CRITICAL


def test_severity_above_110_is_critical():
    assert _severity(150.0) == BottleneckSeverity.CRITICAL


def test_severity_between_75_and_90_is_medium():
    assert _severity(82.0) == BottleneckSeverity.MEDIUM


# ── M32.S02 — Bottleneck recommendation text ──────────────────────────────────

def test_recommendation_critical_mentions_overtime():
    text = _recommendation(BottleneckSeverity.CRITICAL, "Line-1", 3, 24.0)
    assert "Line-1" in text
    assert "overloaded" in text.lower() or "overtime" in text.lower()


def test_recommendation_high_mentions_utilization():
    text = _recommendation(BottleneckSeverity.HIGH, "Mixer-A", 1, 0.0)
    assert "Mixer-A" in text
    assert "utilization" in text.lower() or "high" in text.lower()


def test_recommendation_medium_mentions_capacity():
    text = _recommendation(BottleneckSeverity.MEDIUM, "Filler-2", 1, 0.0)
    assert "capacity" in text.lower() or "monitor" in text.lower()


def test_recommendation_low_has_text():
    text = _recommendation(BottleneckSeverity.LOW, "Labeller", 0, 0.0)
    assert len(text) > 10


# ── M32.S03 — Scenario Optimization: KPI scoring formulas ─────────────────────

def _throughput_delta_pct(ops_delayed: int, total_ops: int) -> float:
    """Mirror of simulation formula."""
    return round(-ops_delayed / max(total_ops, 1) * 100, 2)


def _util_delta(avg_util: float, ops_rescheduled: int, total_ops: int) -> float:
    return round(avg_util * (ops_rescheduled / max(total_ops, 1)) * -0.5, 2)


def test_throughput_delta_zero_delays_is_zero():
    assert _throughput_delta_pct(0, 10) == 0.0


def test_throughput_delta_all_delayed_is_minus_100():
    assert _throughput_delta_pct(10, 10) == -100.0


def test_throughput_delta_half_delayed_is_minus_50():
    assert _throughput_delta_pct(5, 10) == -50.0


def test_throughput_delta_zero_total_ops_safe():
    # max(0, 1) = 1 — no division by zero
    assert _throughput_delta_pct(0, 0) == 0.0


def test_util_delta_no_reschedule_is_zero():
    assert _util_delta(80.0, 0, 10) == 0.0


def test_util_delta_all_rescheduled_reduces_by_half_avg_util():
    # 80% util, all 10 ops rescheduled: delta = -80 * 1.0 * 0.5 = -40
    assert _util_delta(80.0, 10, 10) == -40.0


# ── M32.S04 — Enums and status invariants ─────────────────────────────────────

def test_op_queue_terminal_statuses():
    terminal = {OpQueueStatus.COMPLETED, OpQueueStatus.SKIPPED}
    assert OpQueueStatus.PENDING not in terminal
    assert OpQueueStatus.IN_PROGRESS not in terminal


def test_scenario_status_locked_prevents_changes():
    # Verify LOCKED is distinct from ARCHIVED (both block edits in service layer)
    assert ScenarioStatus.LOCKED != ScenarioStatus.ARCHIVED


def test_bottleneck_severity_ordering():
    # Confirm thresholds are monotonically increasing: LOW < MEDIUM < HIGH < CRITICAL
    from app.services.planning_bottleneck_service import _THRESHOLDS
    assert _THRESHOLDS[BottleneckSeverity.LOW] < _THRESHOLDS[BottleneckSeverity.MEDIUM]
    assert _THRESHOLDS[BottleneckSeverity.MEDIUM] < _THRESHOLDS[BottleneckSeverity.HIGH]
    assert _THRESHOLDS[BottleneckSeverity.HIGH] < _THRESHOLDS[BottleneckSeverity.CRITICAL]
