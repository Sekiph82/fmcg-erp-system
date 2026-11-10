from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints import shop_floor as shop_floor_api
from app.schemas.shop_floor import SFMaterialConsumptionRequest, SFOperationMaterialOut
from app.services import shop_floor_service


@pytest.mark.parametrize("qty", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
@pytest.mark.asyncio
async def test_material_consumption_rejects_non_positive_or_non_finite_qty_before_db(qty):
    with pytest.raises(ValueError, match="finite and greater than zero"):
        await shop_floor_service.consume_work_order_material(
            None, uuid4(), uuid4(), qty, session_id=uuid4(),
        )


def test_material_consumption_request_requires_operator_session():
    with pytest.raises(ValidationError):
        SFMaterialConsumptionRequest(qty=Decimal("1"))


def test_scoped_shop_floor_material_response_excludes_cost_fields():
    row = SimpleNamespace(
        id=uuid4(), production_order_id=uuid4(), work_order_id=uuid4(),
        item_type="MATERIAL", item_id=uuid4(), item_name="Raw material", item_code="RM-1",
        required_qty=Decimal("10"), reserved_qty=Decimal("10"), issued_qty=Decimal("5"),
        consumed_qty=Decimal("1"), returned_qty=Decimal("0"), scrapped_qty=Decimal("0"),
        uom="KG", status="ISSUED", lot_numbers=["LOT-1"],
        unit_cost=Decimal("999"), extended_cost=Decimal("4995"),
    )

    response = SFOperationMaterialOut.model_validate(row)

    assert "unit_cost" not in response.model_dump()
    assert "extended_cost" not in response.model_dump()


@pytest.mark.asyncio
async def test_consume_tracks_operation_material_actor_and_single_issued_lot(monkeypatch):
    parent_id, wo_id, material_id, session_id, actor_id = (uuid4() for _ in range(5))
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(id=wo_id, production_order_id=parent_id, status="PAUSED")
    material = SimpleNamespace(
        id=material_id,
        production_order_id=parent_id,
        work_order_id=wo_id,
        item_id=uuid4(),
        item_code="RM-1",
        item_name="Raw material",
        issued_qty=Decimal("10"),
        consumed_qty=Decimal("2"),
        returned_qty=Decimal("3"),
        status="ISSUED",
        lot_numbers=["LOT-1", "LOT-1"],
        uom="KG",
    )
    session = SimpleNamespace(id=session_id, authenticated_user_id=actor_id, current_work_order_id=wo_id)
    captured = {}

    async def lock_context(_db, requested_wo_id):
        assert requested_wo_id == wo_id
        return parent, work_order

    async def get_session(_db, requested_session_id, **_kwargs):
        assert requested_session_id == session_id
        return session

    async def log_event(*args, **kwargs):
        captured["event"] = (args, kwargs)

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)
    monkeypatch.setattr(shop_floor_service, "_get_session_context", get_session)
    monkeypatch.setattr(shop_floor_service, "_log_event", log_event)

    db = _DB(material)
    result = await shop_floor_service.consume_work_order_material(
        db, wo_id, material_id, Decimal("5"), session_id=session_id,
    )

    assert result is material
    assert material.consumed_qty == Decimal("7")
    assert material.status == "CONSUMED"
    assert db.commits == 1
    event_args, event_kwargs = captured["event"]
    assert event_args[1:4] == (wo_id, parent_id, "MATERIAL_CONSUMPTION")
    assert event_kwargs["session_id"] == session_id
    assert event_kwargs["extra_data"] == {
        "material_id": str(material_id),
        "item_id": str(material.item_id),
        "item_code": "RM-1",
        "item_name": "Raw material",
        "qty": "5",
        "uom": "KG",
        "lot_no": "LOT-1",
    }


@pytest.mark.parametrize(
    ("qty", "lot_no", "error"),
    [
        (Decimal("5.0001"), None, "cannot exceed"),
        (Decimal("1"), "FOREIGN-LOT", "not recorded"),
        (Decimal("1"), None, "Select one"),
    ],
)
@pytest.mark.asyncio
async def test_consume_rejects_quantity_over_issue_or_unrecorded_ambiguous_lot(monkeypatch, qty, lot_no, error):
    parent_id, wo_id, material_id, session_id = (uuid4() for _ in range(4))
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(id=wo_id, production_order_id=parent_id, status="IN_PROGRESS")
    material = SimpleNamespace(
        id=material_id,
        production_order_id=parent_id,
        work_order_id=wo_id,
        item_id=None,
        item_code=None,
        item_name=None,
        issued_qty=Decimal("10"),
        consumed_qty=Decimal("2"),
        returned_qty=Decimal("3"),
        status="ISSUED",
        lot_numbers=["LOT-1", "LOT-2"],
        uom="KG",
    )
    session = SimpleNamespace(current_work_order_id=wo_id)
    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", _lock_context(parent, work_order))
    monkeypatch.setattr(shop_floor_service, "_get_session_context", _session_context(session))
    monkeypatch.setattr(shop_floor_service, "_log_event", _unused_log_event)

    with pytest.raises(ValueError, match=error):
        await shop_floor_service.consume_work_order_material(
            _DB(material), wo_id, material_id, qty, session_id=session_id, lot_no=lot_no,
        )


@pytest.mark.asyncio
async def test_consume_rejects_material_from_another_operation_before_mutation(monkeypatch):
    parent_id, wo_id, material_id, session_id = (uuid4() for _ in range(4))
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(id=wo_id, production_order_id=parent_id, status="IN_PROGRESS")
    session = SimpleNamespace(current_work_order_id=wo_id)
    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", _lock_context(parent, work_order))
    monkeypatch.setattr(shop_floor_service, "_get_session_context", _session_context(session))
    monkeypatch.setattr(shop_floor_service, "_log_event", _unused_log_event)

    with pytest.raises(ValueError, match="not assigned to this work order"):
        await shop_floor_service.consume_work_order_material(
            _DB(None), wo_id, material_id, Decimal("1"), session_id=session_id,
        )


@pytest.mark.asyncio
async def test_consume_api_requires_active_session_work_order_binding(monkeypatch):
    wo_id, material_id, session_id = uuid4(), uuid4(), uuid4()
    session = SimpleNamespace(current_work_order_id=uuid4())

    async def require_session(*_args, **_kwargs):
        return session

    monkeypatch.setattr(shop_floor_api, "_require_execution_session", require_session)
    with pytest.raises(HTTPException) as error:
        await shop_floor_api.consume_work_order_material(
            wo_id,
            material_id,
            SFMaterialConsumptionRequest(qty=Decimal("1"), session_id=session_id),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert error.value.status_code == 403


def _lock_context(parent, work_order):
    async def lock(_db, requested_wo_id):
        assert requested_wo_id == work_order.id
        return parent, work_order

    return lock


def _session_context(session):
    async def get_session(_db, requested_session_id, **_kwargs):
        return session

    return get_session


async def _unused_log_event(*_args, **_kwargs):
    raise AssertionError("No event should be written for rejected consumption")


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _DB:
    def __init__(self, material):
        self.material = material
        self.commits = 0

    async def execute(self, _statement):
        return _Result(self.material)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _material):
        return None
