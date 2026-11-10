from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import machine_operator as endpoint
from app.services import machine_operator_service as service


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, *results):
        self.results = list(results)

    async def execute(self, _statement):
        return _Result(self.results.pop(0))


@pytest.mark.asyncio
async def test_operator_productivity_uses_approved_labor_and_keeps_units_separate(monkeypatch):
    operator_id = uuid4()
    other_operator_id = uuid4()
    work_order_kg_id = uuid4()
    work_order_l_id = uuid4()
    approved_period_log = SimpleNamespace(
        id=uuid4(), approved_flag=True, duration_minutes=Decimal("120"),
        start_time=datetime(2026, 11, 2, 8, tzinfo=timezone.utc), work_order_id=work_order_kg_id,
    )
    unapproved_period_log = SimpleNamespace(
        id=uuid4(), approved_flag=False, duration_minutes=Decimal("60"),
        start_time=datetime(2026, 11, 2, 10, tzinfo=timezone.utc), work_order_id=None,
    )
    kg_order = SimpleNamespace(id=work_order_kg_id, actual_quantity=Decimal("100"))
    liter_order = SimpleNamespace(id=work_order_l_id, actual_quantity=Decimal("40"))
    shared_log_id = uuid4()
    work_order_logs = [
        SimpleNamespace(
            id=approved_period_log.id, work_order_id=work_order_kg_id, operator_id=operator_id,
            duration_minutes=Decimal("120"), start_time=approved_period_log.start_time,
        ),
        SimpleNamespace(
            id=shared_log_id, work_order_id=work_order_kg_id, operator_id=other_operator_id,
            duration_minutes=Decimal("120"), start_time=approved_period_log.start_time,
        ),
        SimpleNamespace(
            id=uuid4(), work_order_id=work_order_l_id, operator_id=operator_id,
            duration_minutes=Decimal("60"), start_time=approved_period_log.start_time,
        ),
    ]

    async def get_operator(_db, _operator_id):
        return SimpleNamespace(id=operator_id)

    monkeypatch.setattr(service, "get_operator", get_operator)
    db = _Session(
        [approved_period_log, unapproved_period_log],
        [(kg_order, "KG"), (liter_order, "L")],
        work_order_logs,
    )

    result = await service.get_operator_productivity(
        db, operator_id, date_from=date(2026, 11, 1), date_to=date(2026, 11, 30)
    )

    assert result.approved_labor_log_count == 1
    assert result.unapproved_labor_log_count == 1
    assert result.approved_labor_minutes == Decimal("120.00")
    assert result.approved_labor_hours == Decimal("2.000")
    assert [row.uom for row in result.output_by_uom] == ["KG", "L"]
    assert result.output_by_uom[0].allocated_output_quantity == Decimal("50.000")
    assert result.output_by_uom[0].output_quantity_per_operator_labor_hour == Decimal("25.000")
    assert result.output_by_uom[1].allocated_output_quantity == Decimal("40.000")
    assert result.output_by_uom[1].output_quantity_per_operator_labor_hour == Decimal("40.000")
    assert result.output_by_uom[0].source_work_order_ids == [work_order_kg_id]
    assert result.output_by_uom[0].source_labor_log_ids == [approved_period_log.id]
    assert set(result.output_by_uom[0].allocation_labor_log_ids) == {approved_period_log.id, shared_log_id}
    assert result.period_labor_log_ids == [approved_period_log.id, unapproved_period_log.id]


@pytest.mark.asyncio
async def test_operator_productivity_rejects_scoped_only_view_permission(monkeypatch):
    monkeypatch.setattr(endpoint, "has_any_permission", lambda *_args: False)
    monkeypatch.setattr(endpoint, "can_view_scope", lambda *_args: True)
    request = SimpleNamespace(
        url=SimpleNamespace(path="/machine-ops/operators/00000000-0000-0000-0000-000000000001/productivity"),
        method="GET",
    )

    with pytest.raises(HTTPException) as error:
        await endpoint._require_machine_operator_permission(
            request,
            db=SimpleNamespace(),
            current_user=SimpleNamespace(),
        )

    assert error.value.status_code == 403
