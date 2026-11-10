from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints import shop_floor as shop_floor_api
from app.schemas.shop_floor import SFDowntimeCreate
from app.services import shop_floor_service


@pytest.mark.parametrize(
    "quantity",
    [Decimal("0"), Decimal("-0.1"), Decimal("NaN"), Decimal("Infinity")],
)
@pytest.mark.asyncio
async def test_scrap_rejects_non_positive_or_non_finite_quantity_before_db_access(quantity):
    with pytest.raises(ValueError, match="finite and greater than zero"):
        await shop_floor_service.log_scrap(
            db=None,
            wo_id=uuid4(),
            qty_scrap=quantity,
            reason_code=None,
            remarks=None,
            session_id=None,
            operator_name=None,
        )


@pytest.mark.asyncio
async def test_scrap_capture_updates_operation_totals_and_activity_classification(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=uuid4(),
        production_order_id=parent.id,
        status="IN_PROGRESS",
        scrap_qty=Decimal("2"),
        scrap_category=None,
        scrap_reason=None,
    )
    captured = {}

    async def lock_context(_db, _work_order_id):
        return parent, work_order

    async def log_event(*args, **kwargs):
        captured["event"] = (args, kwargs)

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)
    monkeypatch.setattr(shop_floor_service, "_log_event", log_event)

    await shop_floor_service.log_scrap(
        _DB(),
        work_order.id,
        qty_scrap=Decimal("0.5"),
        reason_code=None,
        remarks=None,
        session_id=None,
        operator_name=None,
        scrap_category="abnormal",
        scrap_reason="Packaging spill",
    )

    assert work_order.scrap_qty == Decimal("2.5")
    assert work_order.scrap_category == "abnormal"
    assert work_order.scrap_reason == "Packaging spill"
    assert captured["event"][1]["reason_code"] == "abnormal"
    assert captured["event"][1]["remarks"] == "Packaging spill"


@pytest.mark.parametrize(
    "quantities",
    [
        (Decimal("NaN"), Decimal("0"), Decimal("0")),
        (Decimal("1"), Decimal("Infinity"), Decimal("0")),
        (Decimal("1"), Decimal("0"), Decimal("-0.1")),
    ],
)
@pytest.mark.asyncio
async def test_quantity_update_rejects_non_finite_or_negative_values_before_db_access(quantities):
    with pytest.raises(ValueError, match="finite and non-negative"):
        await shop_floor_service.update_quantity(
            db=None,
            wo_id=uuid4(),
            qty_good=quantities[0],
            qty_scrap=quantities[1],
            qty_rework=quantities[2],
            session_id=None,
            operator_name=None,
            remarks=None,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"downtime_category": "NOT_A_CATEGORY"},
        {"downtime_category": "MACHINE_BREAKDOWN", "impact_level": "URGENT"},
    ],
)
def test_downtime_schema_rejects_unknown_category_or_impact(payload):
    with pytest.raises(ValidationError):
        SFDowntimeCreate(**payload)


@pytest.mark.asyncio
async def test_line_level_downtime_without_operator_session_uses_authenticated_line_edit(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    captured = {}

    def require_line_edit(current_user, line_id):
        assert current_user is user
        assert line_id == "LINE-1"
        captured["authorized"] = True

    async def start_downtime(_db, data):
        captured["data"] = data
        return data

    monkeypatch.setattr(shop_floor_api, "_require_line_edit", require_line_edit)
    monkeypatch.setattr(shop_floor_api.svc, "start_downtime", start_downtime)

    await shop_floor_api.start_downtime(
        SFDowntimeCreate(line_id="LINE-1", downtime_category="MACHINE_BREAKDOWN"),
        db=None,
        current_user=user,
        idempotency_key="line-downtime-test-1",
    )

    assert captured["authorized"] is True
    assert captured["data"]["created_by_user_id"] == user.id


@pytest.mark.asyncio
async def test_work_order_downtime_without_operator_session_is_rejected():
    with pytest.raises(HTTPException) as error:
        await shop_floor_api.start_downtime(
            SFDowntimeCreate(
                work_order_id=uuid4(),
                line_id="LINE-1",
                downtime_category="MACHINE_BREAKDOWN",
            ),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_order_link_without_operation_is_rejected():
    with pytest.raises(HTTPException) as error:
        await shop_floor_api.start_downtime(
            SFDowntimeCreate(
                production_order_id=uuid4(),
                downtime_category="MACHINE_BREAKDOWN",
            ),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert error.value.status_code == 403


class _DB:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, _value):
        return None


@pytest.mark.asyncio
async def test_operation_downtime_derives_parent_and_line_from_locked_work_order(monkeypatch):
    parent_id = uuid4()
    work_order_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=work_order_id,
        production_order_id=parent_id,
        line_id="LINE-1",
        status="IN_PROGRESS",
    )
    session = SimpleNamespace(
        authenticated_user_id=user_id,
        operator_id=None,
        operator_name="Virtual operator",
        team_id=None,
        machine_id=None,
        line_id="LINE-1",
        shift_id=None,
    )
    events = []

    async def lock_context(_db, requested_work_order_id):
        assert requested_work_order_id == work_order_id
        return parent, work_order

    async def get_session(_db, requested_session_id):
        assert requested_session_id == session_id
        return session

    async def log_event(*args, **kwargs):
        events.append((args, kwargs))

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)
    monkeypatch.setattr(shop_floor_service, "_get_session_context", get_session)
    monkeypatch.setattr(shop_floor_service, "_log_event", log_event)

    db = _DB()
    downtime = await shop_floor_service.start_downtime(
        db,
        {
            "work_order_id": work_order_id,
            "session_id": session_id,
            "created_by_user_id": uuid4(),
            "downtime_category": "MACHINE_BREAKDOWN",
        },
    )

    assert downtime.production_order_id == parent_id
    assert downtime.line_id == "LINE-1"
    assert downtime.created_by_user_id == user_id
    assert events[0][0][2] == parent_id
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_operation_downtime_rejects_a_mismatched_parent_link(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=uuid4(),
        production_order_id=parent.id,
        line_id="LINE-1",
        status="IN_PROGRESS",
    )

    async def lock_context(_db, _work_order_id):
        return parent, work_order

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)

    with pytest.raises(ValueError, match="does not match"):
        await shop_floor_service.start_downtime(
            _DB(),
            {
                "work_order_id": work_order.id,
                "production_order_id": uuid4(),
                "downtime_category": "MACHINE_BREAKDOWN",
            },
        )
