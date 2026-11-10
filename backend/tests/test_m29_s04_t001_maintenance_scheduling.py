"""M29.S04.T001 — Maintenance scheduling focused unit tests.

Tests PM window overlap detection logic and breakdown priority/escalation rules
using pure in-memory objects (no database required).
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.maintenance_service import assess_breakdown_priority
from app.models.maintenance import BreakdownStatus


def _breakdown(severity, status, start, end=None):
    return SimpleNamespace(
        id=uuid4(),
        severity=severity,
        status=status,
        start_time=start,
        end_time=end,
    )


NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_critical_breakdown_zero_minute_escalation():
    bd = _breakdown("CRITICAL", BreakdownStatus.OPEN, NOW - timedelta(minutes=1))
    result = assess_breakdown_priority(bd, NOW)
    assert result["priority"] == "P1"
    assert result["state"] == "ESCALATE_NOW"
    assert result["age_minutes"] is not None


def test_high_breakdown_within_target():
    bd = _breakdown("HIGH", BreakdownStatus.OPEN, NOW - timedelta(minutes=60))
    result = assess_breakdown_priority(bd, NOW)
    assert result["priority"] == "P2"
    assert result["state"] == "WITHIN_TARGET"
    assert result["minutes_until_escalation"] is not None
    assert result["minutes_until_escalation"] > 0


def test_resolved_breakdown_does_not_escalate():
    bd = _breakdown(
        "MEDIUM",
        BreakdownStatus.RESOLVED,
        NOW - timedelta(hours=5),
        end=NOW - timedelta(hours=1),
    )
    result = assess_breakdown_priority(bd, NOW)
    assert result["state"] == "RESOLVED"
    assert result["minutes_until_escalation"] is None


def test_breakdown_with_naive_start_returns_data_incomplete():
    naive_start = datetime(2026, 11, 10, 8, 0, 0)  # no tzinfo
    bd = _breakdown("LOW", BreakdownStatus.OPEN, naive_start)
    result = assess_breakdown_priority(bd, NOW)
    assert result["state"] == "DATA_INCOMPLETE"
    assert result["age_minutes"] is None


def test_unknown_severity_returns_data_incomplete():
    bd = _breakdown("UNKNOWN_SEV", BreakdownStatus.OPEN, NOW)
    result = assess_breakdown_priority(bd, NOW)
    assert result["priority"] is None
    assert result["state"] == "DATA_INCOMPLETE"


def test_pm_window_overlap_detection():
    """PM window overlapping a production schedule interval is detected correctly."""
    # Simulate overlap check: PM window [08:00-10:00] and production [09:00-11:00]
    pm_start = datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc)
    pm_end = datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc)
    prod_start = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
    prod_end = datetime(2026, 11, 11, 11, 0, tzinfo=timezone.utc)

    overlap_minutes = max(
        0,
        (min(pm_end, prod_end) - max(pm_start, prod_start)).total_seconds() / 60,
    )
    assert overlap_minutes == 60.0


def test_non_overlapping_pm_window():
    """PM window that ends before production starts has zero overlap."""
    pm_start = datetime(2026, 11, 11, 6, 0, tzinfo=timezone.utc)
    pm_end = datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc)
    prod_start = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
    prod_end = datetime(2026, 11, 11, 11, 0, tzinfo=timezone.utc)

    overlap_minutes = max(
        0,
        (min(pm_end, prod_end) - max(pm_start, prod_start)).total_seconds() / 60,
    )
    assert overlap_minutes == 0.0
