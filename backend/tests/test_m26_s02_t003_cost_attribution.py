from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.machine_operator import RuntimeActivity
from app.services import machine_operator_service as service


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


class _Session:
    def __init__(self, *results):
        self.results = list(results)

    async def execute(self, _statement):
        return self.results.pop(0)


def _runtime(machine_id, activity, hours, start_hour=8):
    start = datetime(2026, 11, 2, start_hour, tzinfo=timezone.utc)
    from datetime import timedelta

    return SimpleNamespace(
        id=uuid4(),
        machine_id=machine_id,
        activity_type=activity,
        start_time=start,
        end_time=start + timedelta(hours=hours),
    )


@pytest.mark.asyncio
async def test_cost_contribution_uses_each_machine_rate_and_each_approved_labor_rate():
    production_order_id = uuid4()
    machine_a_id, machine_b_id = uuid4(), uuid4()
    machine_a = SimpleNamespace(
        id=machine_a_id, machine_code="M-A", hourly_cost_rate=Decimal("100"), energy_cost_per_hour=Decimal("20")
    )
    machine_b = SimpleNamespace(
        id=machine_b_id, machine_code="M-B", hourly_cost_rate=Decimal("200"), energy_cost_per_hour=Decimal("40")
    )
    runtime_rows = [
        (_runtime(machine_a_id, RuntimeActivity.RUNNING, 2), machine_a),
        (_runtime(machine_a_id, RuntimeActivity.SETUP, 1, start_hour=10), machine_a),
        (_runtime(machine_b_id, RuntimeActivity.RUNNING, 1), machine_b),
    ]
    labor_log = SimpleNamespace(
        id=uuid4(), operator_id=uuid4(), approved_flag=True,
        duration_minutes=Decimal("240"), overtime_minutes=Decimal("60"),
        cost_rate_at_time=Decimal("50"),
        start_time=datetime(2026, 11, 2, 8, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
    )
    db = _Session(_Result(runtime_rows), _Result([labor_log]))

    result = await service.get_cost_contribution(db, production_order_id)

    assert result.machine_cost_runtime == Decimal("400.00")
    assert result.machine_cost_setup == Decimal("100.00")
    assert result.machine_cost_energy == Decimal("80.00")
    assert result.machine_cost_total == Decimal("580.00")
    assert result.labor_direct_hours == Decimal("3.000")
    assert result.labor_overtime_hours == Decimal("1.000")
    assert result.labor_cost_direct == Decimal("150.00")
    assert result.labor_cost_overtime == Decimal("75.00")
    assert result.labor_cost_total == Decimal("225.00")
    assert result.total_cost == Decimal("805.00")
    assert result.attribution_complete is True
    assert {line.machine_code for line in result.machine_attributions} == {"M-A", "M-B"}
    assert result.labor_attributions[0].labor_log_id == labor_log.id
    assert "do not store a currency code" in result.cost_unit_note


@pytest.mark.asyncio
async def test_cost_contribution_withholds_total_when_sources_are_unapproved_or_unpriced():
    production_order_id = uuid4()
    machine_id = uuid4()
    machine = SimpleNamespace(
        id=machine_id, machine_code="M-OPEN", hourly_cost_rate=Decimal("100"), energy_cost_per_hour=Decimal("20")
    )
    open_runtime = SimpleNamespace(
        id=uuid4(), machine_id=machine_id, activity_type=RuntimeActivity.RUNNING,
        start_time=datetime(2026, 11, 2, 8, tzinfo=timezone.utc), end_time=None,
    )
    overlap_a = SimpleNamespace(
        id=uuid4(), machine_id=machine_id, activity_type=RuntimeActivity.RUNNING,
        start_time=datetime(2026, 11, 2, 9, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 10, tzinfo=timezone.utc),
    )
    overlap_b = SimpleNamespace(
        id=uuid4(), machine_id=machine_id, activity_type=RuntimeActivity.DOWNTIME,
        start_time=datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc),
    )
    unapproved = SimpleNamespace(
        id=uuid4(), operator_id=uuid4(), approved_flag=False,
        duration_minutes=Decimal("60"), overtime_minutes=Decimal("0"), cost_rate_at_time=Decimal("75"),
    )
    approved_unpriced = SimpleNamespace(
        id=uuid4(), operator_id=uuid4(), approved_flag=True,
        duration_minutes=Decimal("60"), overtime_minutes=Decimal("0"), cost_rate_at_time=None,
    )
    approved_overlap_a = SimpleNamespace(
        id=uuid4(), operator_id=uuid4(), approved_flag=True,
        duration_minutes=Decimal("60"), overtime_minutes=Decimal("0"), cost_rate_at_time=Decimal("75"),
        start_time=datetime(2026, 11, 2, 9, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 10, tzinfo=timezone.utc),
    )
    approved_overlap_b = SimpleNamespace(
        id=uuid4(), operator_id=approved_overlap_a.operator_id, approved_flag=True,
        duration_minutes=Decimal("60"), overtime_minutes=Decimal("0"), cost_rate_at_time=Decimal("75"),
        start_time=datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc),
    )
    db = _Session(
        _Result([(open_runtime, machine), (overlap_a, machine), (overlap_b, machine)]),
        _Result([unapproved, approved_unpriced, approved_overlap_a, approved_overlap_b]),
    )

    result = await service.get_cost_contribution(db, production_order_id)

    assert result.attribution_complete is False
    assert result.machine_cost_total is None
    assert result.labor_cost_total is None
    assert result.total_cost is None
    assert result.unavailable_runtime_log_ids == [open_runtime.id]
    assert set(result.overlapping_runtime_log_ids) == {overlap_a.id, overlap_b.id}
    assert result.unapproved_labor_log_ids == [unapproved.id]
    assert result.unpriced_labor_log_ids == [approved_unpriced.id]
    assert set(result.overlapping_labor_log_ids) == {approved_overlap_a.id, approved_overlap_b.id}
    assert all(line.included is False for line in result.labor_attributions)


@pytest.mark.asyncio
async def test_machine_specific_costing_does_not_allocate_order_labor_to_machine():
    production_order_id = uuid4()
    machine_id = uuid4()
    machine = SimpleNamespace(
        id=machine_id, machine_code="M-ONLY", hourly_cost_rate=Decimal("120"), energy_cost_per_hour=Decimal("30")
    )
    db = _Session(_Result([(_runtime(machine_id, RuntimeActivity.RUNNING, 2), machine)]))

    result = await service.get_cost_contribution(db, production_order_id, machine_id=machine_id)

    assert result.machine_cost_total == Decimal("300.00")
    assert result.labor_attributions == []
    assert result.labor_cost_total is None
    assert result.total_cost is None
    assert result.attribution_complete is False
    assert any("does not allocate production-order labor" in note for note in result.data_notes)

