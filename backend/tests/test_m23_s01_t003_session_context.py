"""Unit coverage for snapshotting virtual operator-session context on actions."""
from uuid import uuid4

import pytest

from app.models.shop_floor import SFSession
from app.services import shop_floor_service
from app.services.shop_floor_service import _log_event, start_downtime


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _SessionDB:
    def __init__(self, session):
        self.session = session
        self.entries = []

    async def execute(self, _statement):
        return _Result(self.session)

    def add(self, entry):
        self.entries.append(entry)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, _entry):
        return None


@pytest.mark.asyncio
async def test_activity_event_snapshots_context_from_operator_session():
    session = SFSession(
        id=uuid4(),
        session_code="SES-SYNTHETIC-001",
        status="ACTIVE",
        operator_id=uuid4(),
        operator_name="Virtual operator A",
        team_id=uuid4(),
        machine_id=uuid4(),
        line_id="VIRTUAL-LINE-1",
        shift_id=uuid4(),
    )
    db = _SessionDB(session)

    entry = await _log_event(
        db,
        work_order_id=uuid4(),
        production_order_id=uuid4(),
        event_type="START",
        session_id=session.id,
        operator_name="Mismatched client operator",
        line_id="MISMATCHED-LINE",
    )

    assert db.entries == [entry]
    assert entry.operator_id == session.operator_id
    assert entry.operator_name == session.operator_name
    assert entry.team_id == session.team_id
    assert entry.machine_id == session.machine_id
    assert entry.line_id == session.line_id
    assert entry.shift_id == session.shift_id


@pytest.mark.asyncio
async def test_new_activity_rejects_a_logged_out_operator_session():
    session = SFSession(
        id=uuid4(),
        session_code="SES-SYNTHETIC-LOGGED-OUT",
        status="LOGGED_OUT",
        operator_name="Virtual operator C",
    )
    db = _SessionDB(session)

    with pytest.raises(ValueError, match="Operator session is not active"):
        await _log_event(
            db,
            work_order_id=uuid4(),
            production_order_id=uuid4(),
            event_type="START",
            session_id=session.id,
        )

    assert db.entries == []


@pytest.mark.asyncio
async def test_downtime_record_and_activity_use_the_same_session_context(monkeypatch):
    session = SFSession(
        id=uuid4(),
        session_code="SES-SYNTHETIC-002",
        status="ACTIVE",
        operator_id=uuid4(),
        operator_name="Virtual operator B",
        team_id=uuid4(),
        machine_id=uuid4(),
        line_id="VIRTUAL-LINE-2",
        shift_id=uuid4(),
    )
    db = _SessionDB(session)
    parent = type("Parent", (), {"id": uuid4(), "status": "IN_PROGRESS"})()
    work_order = type("WorkOrder", (), {
        "id": uuid4(), "production_order_id": parent.id,
        "line_id": session.line_id, "status": "IN_PROGRESS",
    })()

    async def lock_context(_db, requested_work_order_id):
        assert requested_work_order_id == work_order.id
        return parent, work_order

    monkeypatch.setattr(shop_floor_service, "_lock_wo_context", lock_context)

    downtime = await start_downtime(db, {
        "work_order_id": work_order.id,
        "production_order_id": parent.id,
        "session_id": session.id,
        "operator_id": uuid4(),
        "operator_name": "Mismatched client operator",
        "team_id": uuid4(),
        "machine_id": uuid4(),
        "line_id": session.line_id,
        "shift_id": uuid4(),
        "downtime_category": "MACHINE_BREAKDOWN",
        "impact_level": "MEDIUM",
    })
    activity = db.entries[1]

    for record in (downtime, activity):
        assert record.session_id == session.id
        assert record.operator_id == session.operator_id
        assert record.operator_name == session.operator_name
        assert record.team_id == session.team_id
        assert record.machine_id == session.machine_id
        assert record.line_id == session.line_id
        assert record.shift_id == session.shift_id
