from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.machine_operator import RuntimeActivity
from app.services import machine_operator_service as service


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Session:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _statement):
        return _Result(self.rows)


def _machine(code):
    return type("MachineRow", (), {"id": uuid4(), "machine_code": code, "machine_name": f"Machine {code}"})()


def _downtime(machine, start, duration_minutes):
    return type("RuntimeRow", (), {
        "id": uuid4(),
        "machine_id": machine.id,
        "activity_type": RuntimeActivity.DOWNTIME,
        "start_time": start,
        "end_time": start + timedelta(minutes=duration_minutes) if duration_minutes is not None else None,
    })()


@pytest.mark.asyncio
async def test_performance_anomalies_use_machine_baseline_and_exclude_weak_or_ambiguous_evidence():
    target_date = date(2026, 11, 8)
    target_start = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
    machine_a, machine_b, machine_c, machine_d = (_machine(code) for code in ("A", "B", "C", "D"))
    rows = []

    baseline_a = [_downtime(machine_a, target_start - timedelta(days=day), 10) for day in range(1, 6)]
    anomaly_a = _downtime(machine_a, target_start, 45)
    rows.extend((log, machine_a) for log in [*baseline_a, anomaly_a])

    baseline_b = [_downtime(machine_b, target_start - timedelta(days=day), 10) for day in (1, 2)]
    candidate_b = _downtime(machine_b, target_start, 40)
    rows.extend((log, machine_b) for log in [*baseline_b, candidate_b])

    baseline_c = [_downtime(machine_c, target_start - timedelta(days=day), 10) for day in range(1, 6)]
    overlapping_c1 = _downtime(machine_c, target_start, 40)
    overlapping_c2 = _downtime(machine_c, target_start + timedelta(minutes=20), 30)
    rows.extend((log, machine_c) for log in [*baseline_c, overlapping_c1, overlapping_c2])

    open_d = _downtime(machine_d, target_start, None)
    rows.append((open_d, machine_d))

    report = await service.get_performance_anomalies(
        _Session(rows), date_from=target_date, date_to=target_date
    )

    assert report.period_start == target_date
    assert report.baseline_start == target_date - timedelta(days=30)
    assert len(report.anomalies) == 1, report.model_dump_json()
    anomaly = report.anomalies[0]
    assert anomaly.machine_id == machine_a.id
    assert anomaly.runtime_log_id == anomaly_a.id
    assert anomaly.observed_downtime_minutes == 45
    assert anomaly.baseline_median_minutes == 10
    assert anomaly.baseline_mad_minutes == 0
    assert anomaly.alert_threshold_minutes == 10
    assert set(anomaly.source_baseline_runtime_log_ids) == {log.id for log in baseline_a}
    assert report.insufficient_baseline_machine_ids == [machine_b.id]
    assert set(report.overlapping_runtime_log_ids) == {overlapping_c1.id, overlapping_c2.id}
    assert report.unavailable_runtime_log_ids == [open_d.id]
