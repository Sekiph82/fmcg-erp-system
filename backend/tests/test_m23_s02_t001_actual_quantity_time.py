"""Focused service coverage for shop-floor actual quantity/runtime recording."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import shop_floor_service


class _Result:
    def scalars(self):
        return self

    def all(self):
        return []


class _DB:
    async def execute(self, _statement):
        return _Result()

    async def commit(self):
        return None

    async def refresh(self, _record):
        return None


@pytest.mark.asyncio
async def test_finish_persists_actual_quantities_and_minutes_in_operation_and_activity(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=uuid4(),
        status="IN_PROGRESS",
        production_order_id=uuid4(),
        qc_required_flag=False,
        qc_passed=None,
        completed_qty=Decimal("0"),
        scrap_qty=Decimal("0"),
        rework_qty=Decimal("0"),
        run_time_actual=None,
        completed_at=None,
    )
    activity = {}

    async def lock_context(_db, _work_order_id):
        return parent, work_order

    async def no_transition(*_args, **_kwargs):
        return None

    async def capture_activity(_db, *_args, **kwargs):
        activity.update(kwargs)

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)
    monkeypatch.setattr(shop_floor_service, "record_shop_floor_transition", no_transition)
    monkeypatch.setattr(shop_floor_service, "_log_event", capture_activity)

    result = await shop_floor_service.finish_work_order(
        _DB(),
        uuid4(),
        qty_good=Decimal("120.5"),
        qty_scrap=Decimal("2"),
        qty_rework=Decimal("1.5"),
        run_time_actual=Decimal("18.75"),
        session_id=None,
        operator_name="Virtual operator",
        remarks=None,
    )

    assert result.status == "COMPLETED"
    assert result.completed_qty == Decimal("120.5")
    assert result.scrap_qty == Decimal("2")
    assert result.rework_qty == Decimal("1.5")
    assert result.run_time_actual == Decimal("18.75")
    assert result.completed_at is not None
    assert activity["qty_good"] == Decimal("120.5")
    assert activity["qty_scrap"] == Decimal("2")
    assert activity["qty_rework"] == Decimal("1.5")
    assert activity["duration_minutes"] == Decimal("18.75")
