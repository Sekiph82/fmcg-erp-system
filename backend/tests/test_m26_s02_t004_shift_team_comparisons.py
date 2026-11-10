from datetime import date, datetime, timedelta, timezone
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


@pytest.mark.asyncio
async def test_shift_team_comparisons_use_recorded_assignment_and_preserve_unassigned_sources():
    work_order_id = uuid4()
    team_a_id, team_b_id = uuid4(), uuid4()
    shift_a_id, shift_b_id = uuid4(), uuid4()
    operator_a_id, operator_b_id = uuid4(), uuid4()
    machine_id = uuid4()
    labor_a_id, labor_b_id, unapproved_id = uuid4(), uuid4(), uuid4()
    runtime_id, open_runtime_id = uuid4(), uuid4()
    start = datetime(2026, 11, 2, 8, tzinfo=timezone.utc)

    labor_a = SimpleNamespace(
        id=labor_a_id, work_order_id=work_order_id, team_id=team_a_id, operator_id=operator_a_id,
        start_time=start, duration_minutes=Decimal("60"), approved_flag=True,
    )
    labor_b = SimpleNamespace(
        id=labor_b_id, work_order_id=work_order_id, team_id=team_b_id, operator_id=operator_b_id,
        start_time=start + timedelta(hours=1), duration_minutes=Decimal("60"), approved_flag=True,
    )
    unapproved = SimpleNamespace(
        id=unapproved_id, work_order_id=None, team_id=None, operator_id=uuid4(),
        start_time=start + timedelta(hours=2), duration_minutes=Decimal("30"), approved_flag=False,
    )
    runtime = SimpleNamespace(
        id=runtime_id, work_order_id=work_order_id, team_id=team_a_id, operator_id=operator_a_id,
        machine_id=machine_id, activity_type=RuntimeActivity.RUNNING,
        start_time=start, end_time=start + timedelta(hours=1),
    )
    open_runtime = SimpleNamespace(
        id=open_runtime_id, work_order_id=None, team_id=None, operator_id=None, machine_id=uuid4(),
        activity_type=RuntimeActivity.DOWNTIME, start_time=start + timedelta(hours=2), end_time=None,
    )
    assignment_a = SimpleNamespace(
        work_order_id=work_order_id, assigned_at=start - timedelta(hours=1),
        operator_id=operator_a_id, team_id=team_a_id, machine_id=machine_id, shift_id=shift_a_id,
    )
    assignment_b = SimpleNamespace(
        work_order_id=work_order_id, assigned_at=start + timedelta(minutes=30),
        operator_id=operator_b_id, team_id=team_b_id, machine_id=machine_id, shift_id=shift_b_id,
    )
    completed_order = SimpleNamespace(
        id=work_order_id, actual_quantity=Decimal("100"), end_time=start + timedelta(hours=3),
    )

    db = _Session(
        _Result([labor_a, labor_b, unapproved]),
        _Result([runtime, open_runtime]),
        _Result([(completed_order, "case")]),
        _Result([labor_a, labor_b]),
        _Result([assignment_a, assignment_b]),
        _Result([
            SimpleNamespace(id=team_a_id, team_code="TEAM-A", team_name="Team A"),
            SimpleNamespace(id=team_b_id, team_code="TEAM-B", team_name="Team B"),
        ]),
        _Result([
            SimpleNamespace(id=shift_a_id, shift_code="SHIFT-A", name="Shift A"),
            SimpleNamespace(id=shift_b_id, shift_code="SHIFT-B", name="Shift B"),
        ]),
    )

    result = await service.get_shift_team_comparisons(db, date_from=date(2026, 11, 2), date_to=date(2026, 11, 2))

    teams = {group.group_id: group for group in result.teams}
    shifts = {group.group_id: group for group in result.shifts}
    assert teams[team_a_id].approved_labor_minutes == Decimal("60.00")
    assert teams[team_b_id].approved_labor_minutes == Decimal("60.00")
    assert teams[None].unapproved_labor_log_count == 1
    assert teams[team_a_id].recorded_runtime_minutes == Decimal("60.00")
    assert teams[None].unavailable_runtime_log_ids == [open_runtime_id]
    assert shifts[shift_a_id].source_labor_log_ids == [labor_a_id]
    assert shifts[shift_b_id].source_labor_log_ids == [labor_b_id]
    assert shifts[None].source_runtime_log_ids == [open_runtime_id]
    assert teams[team_a_id].output_by_uom[0].allocated_output_quantity == Decimal("50.000")
    assert teams[team_b_id].output_by_uom[0].allocated_output_quantity == Decimal("50.000")
    assert shifts[shift_a_id].output_by_uom[0].allocated_output_quantity == Decimal("50.000")
    assert shifts[shift_b_id].output_by_uom[0].allocated_output_quantity == Decimal("50.000")
    assert set(teams[team_a_id].output_by_uom[0].allocation_labor_log_ids) == {labor_a_id, labor_b_id}
    assert result.unavailable_output_work_order_ids == []
