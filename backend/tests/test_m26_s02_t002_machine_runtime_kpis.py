from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.machine_operator import RuntimeActivity
from app.models.machine_operator import MachinePerformanceSnapshot
from app.services import machine_operator_service as service


class _Result:
    def __init__(self, rows=None, scalar=None, one=None):
        self.rows = rows or []
        self.scalar = scalar
        self.one_value = one

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def one(self):
        return self.one_value


class _Session:
    def __init__(self, *results):
        self.results = list(results)
        self.added = []

    async def execute(self, _statement):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        snapshot = self.added[-1]
        for name, value in {
            "setup_time_min": Decimal("0"),
            "run_time_min": Decimal("0"),
            "downtime_min": Decimal("0"),
            "cleanup_time_min": Decimal("0"),
            "changeover_time_min": Decimal("0"),
            "idle_time_min": Decimal("0"),
            "units_produced": Decimal("0"),
            "good_units": Decimal("0"),
            "low_oee_flag": False,
            "high_downtime_flag": False,
            "anomaly_flag": False,
        }.items():
            setattr(snapshot, name, value)

    async def commit(self):
        return None

    async def refresh(self, _value):
        return None


@pytest.mark.asyncio
async def test_runtime_kpis_clip_cross_midnight_logs_and_preserve_source_ids(monkeypatch):
    machine_id = uuid4()
    run_id = uuid4()
    downtime_id = uuid4()
    open_id = uuid4()
    machine = SimpleNamespace(id=machine_id, machine_code="M-01", machine_name="Mixer 1")
    logs = [
        SimpleNamespace(
            id=run_id,
            activity_type=RuntimeActivity.RUNNING,
            start_time=datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 0, 30, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            id=downtime_id,
            activity_type=RuntimeActivity.DOWNTIME,
            start_time=datetime(2026, 11, 1, 0, 15, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 0, 45, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            id=open_id,
            activity_type=RuntimeActivity.IDLE,
            start_time=datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
            end_time=None,
        ),
    ]
    db = _Session(_Result(scalar=machine), _Result(rows=logs))

    result = await service.get_machine_runtime_kpis(
        db, machine_id, date_from=date(2026, 11, 1), date_to=date(2026, 11, 1)
    )

    assert result is not None
    assert result.recorded_activity_log_minutes == Decimal("60.00")
    assert [(row.activity_type, row.duration_minutes) for row in result.activities] == [
        (RuntimeActivity.DOWNTIME, Decimal("30.00")),
        (RuntimeActivity.RUNNING, Decimal("30.00")),
    ]
    assert result.activities[0].source_runtime_log_ids == [downtime_id]
    assert result.activities[1].source_runtime_log_ids == [run_id]
    assert result.unavailable_runtime_log_ids == [open_id]


@pytest.mark.asyncio
async def test_performance_snapshot_does_not_assume_planned_shift_minutes(monkeypatch):
    machine_id = uuid4()
    snapshot_date = date(2026, 11, 1)
    run_start = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc)
    run_end = datetime(2026, 11, 1, 0, 30, tzinfo=timezone.utc)
    downtime_start = datetime(2026, 11, 1, 0, 15, tzinfo=timezone.utc)
    downtime_end = datetime(2026, 11, 1, 0, 45, tzinfo=timezone.utc)
    runtime_rows = [
        (RuntimeActivity.RUNNING, run_start, run_end),
        (RuntimeActivity.DOWNTIME, downtime_start, downtime_end),
    ]
    db = _Session(_Result(scalar=None), _Result(rows=runtime_rows))

    async def get_machine(_db, _machine_id):
        return SimpleNamespace(rated_capacity_per_hour=None, hourly_cost_rate=None, energy_cost_per_hour=None)

    monkeypatch.setattr(service, "get_machine", get_machine)
    result = await service.compute_performance_snapshot(db, machine_id, snapshot_date)

    assert isinstance(result, MachinePerformanceSnapshot)
    assert result.planned_time_min == 0
    assert result.run_time_min == Decimal("30.00")
    assert result.downtime_min == Decimal("30.00")
    assert result.availability is None
    assert result.utilization_pct is None
    assert result.oee is None
    assert result.machine_cost_actual is None
    assert result.labor_cost_actual is None
    assert result.energy_cost_actual is None

