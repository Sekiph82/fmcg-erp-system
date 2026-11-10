"""Focused security regressions for authenticated shop-floor role gating."""
from types import SimpleNamespace
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import shop_floor
from app.core.deps import get_current_user
from app.db.session import get_auth_db, get_db
from app.services import shop_floor_service as shop_floor_service


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(shop_floor.router, prefix="/shop-floor")

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db
    app.dependency_overrides[get_auth_db] = empty_db
    return app


def _user(permission_codes=(), scopes=()):
    permissions = [SimpleNamespace(code=code, is_active=True) for code in permission_codes]
    role = SimpleNamespace(is_active=True, permissions=permissions, access_scopes=list(scopes))
    return SimpleNamespace(
        id=uuid4(), is_superuser=False, roles=[role], access_scopes=[], full_name="Virtual ERP User"
    )


def _line_scope(line_id: str):
    return SimpleNamespace(
        scope_type="production_line",
        scope_id=line_id,
        is_active=True,
        can_view=True,
        can_edit=True,
        can_update=True,
    )


def test_shop_floor_api_requires_authentication_for_reads_and_mutations():
    app = _app()
    with TestClient(app) as client:
        responses = [
            client.get("/shop-floor/dashboard"),
            client.get("/shop-floor/live-queue?line_id=LINE-A"),
            client.post("/shop-floor/sessions", json={"operator_name": "Virtual Operator", "line_id": "LINE-A"}),
            client.post(
                f"/shop-floor/work-orders/{uuid4()}/start",
                json={"session_id": str(uuid4())},
            ),
            client.post(f"/shop-floor/handovers/{uuid4()}/approve", json={}),
            client.post("/shop-floor/overrides", json={"override_type": "MANUAL"}),
            client.post("/shop-floor/ai/run"),
        ]
    assert [response.status_code for response in responses] == [401] * len(responses)


def test_authenticated_user_without_permission_cannot_open_aggregate_or_start_session():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user()
    with TestClient(app) as client:
        dashboard = client.get("/shop-floor/dashboard")
        session = client.post(
            "/shop-floor/sessions",
            json={"operator_name": "Virtual Operator", "line_id": "LINE-A"},
        )
        approval = client.post(f"/shop-floor/handovers/{uuid4()}/approve", json={})
    assert [dashboard.status_code, session.status_code, approval.status_code] == [403, 403, 403]


def test_operator_scoped_view_and_execution_permissions_are_line_bound():
    user = _user(
        ("shop_floor.view_own_scope", "production_execution.update_own_line"),
        (_line_scope("LINE-A"),),
    )

    shop_floor._require_line_view(user, "LINE-A")
    shop_floor._require_line_edit(user, "LINE-A")

    with pytest.raises(HTTPException) as view_denied:
        shop_floor._require_line_view(user, "LINE-B")
    assert view_denied.value.status_code == 403

    with pytest.raises(HTTPException) as edit_denied:
        shop_floor._require_line_edit(user, "LINE-B")
    assert edit_denied.value.status_code == 403

    with pytest.raises(HTTPException) as approval_denied:
        shop_floor._require_production_approval(user)
    assert approval_denied.value.status_code == 403


def test_supervisor_decisions_require_explicit_approval_permission():
    supervisor = _user(("production.approve",))
    shop_floor._require_production_approval(supervisor)

    operator = _user(("production_execution.update_own_line",))
    with pytest.raises(HTTPException) as denied:
        shop_floor._require_production_approval(operator)
    assert denied.value.status_code == 403


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _SequentialDB:
    def __init__(self, *values):
        self.values = iter(values)

    async def execute(self, _statement):
        return _Result(next(self.values))


@pytest.mark.asyncio
async def test_operator_execution_requires_owned_active_session_and_matching_work_order_line():
    user = _user(
        ("production_execution.update_own_line",),
        (_line_scope("LINE-A"),),
    )
    session = SimpleNamespace(
        id=uuid4(), status="ACTIVE", authenticated_user_id=user.id, line_id="LINE-A"
    )
    wo_id = uuid4()
    work_order = SimpleNamespace(id=wo_id, line_id="LINE-A")
    result = await shop_floor._require_execution_session(
        _SequentialDB(session, work_order), user, session.id, work_order_id=wo_id
    )
    assert result is session

    mismatched = SimpleNamespace(id=wo_id, line_id="LINE-B")
    with pytest.raises(HTTPException) as denied:
        await shop_floor._require_execution_session(
            _SequentialDB(session, mismatched), user, session.id, work_order_id=wo_id
        )
    assert denied.value.status_code == 403

    foreign_session = SimpleNamespace(
        id=uuid4(), status="ACTIVE", authenticated_user_id=uuid4(), line_id="LINE-A"
    )
    with pytest.raises(HTTPException) as foreign_denied:
        await shop_floor._require_execution_session(
            _SequentialDB(foreign_session), user, foreign_session.id
        )
    assert foreign_denied.value.status_code == 403

    inactive_session = SimpleNamespace(
        id=uuid4(), status="LOGGED_OUT", authenticated_user_id=user.id, line_id="LINE-A"
    )
    with pytest.raises(HTTPException) as inactive_denied:
        await shop_floor._require_execution_session(
            _SequentialDB(inactive_session), user, inactive_session.id
        )
    assert inactive_denied.value.status_code == 403


class _EventDB:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_activity_log_uses_authenticated_session_actor_and_preserves_duration(monkeypatch):
    actor_id = uuid4()
    session = SimpleNamespace(
        authenticated_user_id=actor_id,
        operator_id=uuid4(),
        operator_name="Virtual Operator",
        team_id=None,
        machine_id=None,
        line_id="LINE-A",
        shift_id=None,
    )

    async def get_context(_db, _session_id, *, allow_inactive=False):
        assert allow_inactive is False
        return session

    monkeypatch.setattr(shop_floor_service, "_get_session_context", get_context)
    entry = await shop_floor_service._log_event(
        _EventDB(), uuid4(), None, "DOWNTIME_STOP", session_id=uuid4(), duration_minutes=Decimal("12.5")
    )
    assert entry.actor_user_id == actor_id
    assert entry.operator_name == "Virtual Operator"
    assert entry.duration_minutes == Decimal("12.5")
