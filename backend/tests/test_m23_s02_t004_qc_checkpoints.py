from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints import shop_floor as shop_floor_api
from app.schemas.shop_floor import SFQCCheckpointRequest
from app.services import production_execution_service, shop_floor_service


def test_qc_checkpoint_schema_accepts_only_explicit_outcomes():
    session_id = uuid4()
    assert SFQCCheckpointRequest(
        session_id=session_id,
        checkpoint_name="Fill weight",
        result="PASS",
    ).result == "PASS"
    with pytest.raises(ValidationError):
        SFQCCheckpointRequest(
            session_id=session_id,
            checkpoint_name="Fill weight",
            result="UNKNOWN",
        )


@pytest.mark.asyncio
async def test_checkpoint_results_remain_per_checkpoint_and_retest_clears_only_matching_failure(monkeypatch):
    parent_id, wo_id, session_id = uuid4(), uuid4(), uuid4()
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=wo_id,
        production_order_id=parent_id,
        status="IN_PROGRESS",
        qc_required_flag=True,
        qc_passed=None,
    )
    session = SimpleNamespace(current_work_order_id=wo_id)
    events = [
        SimpleNamespace(
            id=uuid4(), created_at=None, timestamp_start=None,
            extra_data={"checkpoint_name": "Fill weight", "result": "FAIL", "checkpoint_sequence": 1},
        ),
        SimpleNamespace(
            id=uuid4(), created_at=None, timestamp_start=None,
            extra_data={"checkpoint_name": "Appearance", "result": "PASS", "checkpoint_sequence": 2},
        ),
    ]
    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", _lock_context(parent, work_order))
    monkeypatch.setattr(shop_floor_service, "_get_session_context", _session_context(session))
    monkeypatch.setattr(shop_floor_service, "get_qc_checkpoints", lambda *_args: _async_value(events))

    async def log_event(*_args, **kwargs):
        entry = SimpleNamespace(
            id=uuid4(), created_at=None, timestamp_start=None,
            extra_data=kwargs["extra_data"], remarks=kwargs["remarks"],
        )
        events.append(entry)
        return entry

    monkeypatch.setattr(shop_floor_service, "_log_event", log_event)
    db = _DB()

    await shop_floor_service.record_qc_checkpoint(
        db, wo_id, session_id=session_id, checkpoint_name="Appearance", result="PASS",
    )
    assert work_order.qc_passed is False

    await shop_floor_service.record_qc_checkpoint(
        db, wo_id, session_id=session_id, checkpoint_name=" fill   weight ", result="PASS",
        measured_value="498", unit="g", notes="Recheck passed",
    )
    assert work_order.qc_passed is True
    assert events[-1].extra_data["checkpoint_name"] == "fill   weight"
    assert events[-1].extra_data["checkpoint_sequence"] == 4
    assert db.commits == 2


@pytest.mark.asyncio
async def test_shop_floor_finish_cannot_bypass_required_qc_checkpoint(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=uuid4(), production_order_id=parent.id, status="IN_PROGRESS",
        qc_required_flag=True, qc_passed=False,
    )
    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", _lock_context(parent, work_order))

    with pytest.raises(ValueError, match="Required in-process QC checkpoints"):
        await shop_floor_service.finish_work_order(
            _DB(), work_order.id, Decimal("1"), Decimal("0"), Decimal("0"), None,
            uuid4(), "Virtual operator", None,
        )

    assert work_order.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_production_execution_finish_does_not_trust_request_qc_boolean(monkeypatch):
    parent_id, wo_id = uuid4(), uuid4()
    parent = SimpleNamespace(id=parent_id, status="IN_PROGRESS")
    work_order = SimpleNamespace(
        id=wo_id, production_order_id=parent_id, status="IN_PROGRESS",
        qc_required_flag=True, qc_passed=None,
    )
    monkeypatch.setattr(production_execution_service, "_load_order", _load_order(parent))

    with pytest.raises(ValueError, match="Required in-process QC checkpoints"):
        await production_execution_service.complete_work_order(
            _DBSequence(parent_id, work_order), wo_id, uuid4(), Decimal("1"), Decimal("0"),
            Decimal("0"), None, None, None, None, None, True, None,
        )

    assert work_order.status == "IN_PROGRESS"
    assert work_order.qc_passed is None


@pytest.mark.asyncio
async def test_qc_checkpoint_edit_requires_quality_scope(monkeypatch):
    user_id, wo_id, session_id = uuid4(), uuid4(), uuid4()
    session = SimpleNamespace(
        id=session_id, status="ACTIVE", authenticated_user_id=user_id,
        current_work_order_id=wo_id, line_id="LINE-1",
    )
    monkeypatch.setattr(shop_floor_api, "_get_session", _return(session))
    monkeypatch.setattr(shop_floor_api, "_require_line_edit", lambda *_args: None)
    monkeypatch.setattr(shop_floor_api, "has_any_permission", lambda *_args: False)
    monkeypatch.setattr(shop_floor_api, "has_permission", lambda *_args: False)
    monkeypatch.setattr(shop_floor_api, "can_modify_scope", lambda *_args: False)
    monkeypatch.setattr(shop_floor_api, "can_view_scope", lambda *_args: False)

    with pytest.raises(HTTPException) as error:
        await shop_floor_api._require_qc_session_and_scope(
            _DBContext(("LINE-1", "FOOD")),
            SimpleNamespace(id=user_id), session_id, wo_id, action="edit",
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_qc_checkpoint_edit_all_also_requires_quality_view_permission(monkeypatch):
    user_id, wo_id, session_id = uuid4(), uuid4(), uuid4()
    session = SimpleNamespace(
        id=session_id, status="ACTIVE", authenticated_user_id=user_id,
        current_work_order_id=wo_id, line_id="LINE-1",
    )
    monkeypatch.setattr(shop_floor_api, "_get_session", _return(session))
    monkeypatch.setattr(shop_floor_api, "_require_line_edit", lambda *_args: None)
    monkeypatch.setattr(shop_floor_api, "has_any_permission", lambda *_args: False)
    monkeypatch.setattr(shop_floor_api, "has_permission", lambda *_args: True)
    monkeypatch.setattr(shop_floor_api, "can_view_scope", lambda *_args: False)

    with pytest.raises(HTTPException) as error:
        await shop_floor_api._require_qc_session_and_scope(
            _DBContext(("LINE-1", "FOOD")),
            SimpleNamespace(id=user_id), session_id, wo_id, action="edit",
        )

    assert error.value.status_code == 403


def _lock_context(parent, work_order):
    async def lock(_db, requested_wo_id):
        assert requested_wo_id == work_order.id
        return parent, work_order

    return lock


def _session_context(session):
    async def get_session(_db, _session_id, **_kwargs):
        return session

    return get_session


def _return(value):
    async def get(*_args, **_kwargs):
        return value

    return get


def _load_order(order):
    async def load(*_args, **_kwargs):
        return order

    return load


async def _async_value(value):
    return value


class _Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class _DB:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _value):
        return None


class _DBSequence(_DB):
    def __init__(self, *results):
        super().__init__()
        self.results = iter(results)

    async def execute(self, _statement):
        return _Result(next(self.results))


class _DBContext(_DB):
    def __init__(self, context):
        super().__init__()
        self.context = context

    async def execute(self, _statement):
        return _Result(self.context)
