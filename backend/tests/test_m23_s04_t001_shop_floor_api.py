"""HTTP-level Shop Floor mutation contract tests for M23 acceptance."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import shop_floor
from app.core.deps import get_current_user
from app.db.session import get_db


def _user():
    return SimpleNamespace(id=uuid4(), is_superuser=False, roles=[], access_scopes=[])


def _app(user, db):
    app = FastAPI()
    app.include_router(shop_floor.router, prefix="/shop-floor")

    async def provide_db():
        yield db

    app.dependency_overrides[get_db] = provide_db
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _activity(work_order_id, actor_id):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(), work_order_id=work_order_id, production_order_id=uuid4(),
        session_id=None, actor_user_id=actor_id, operator_id=None,
        operator_name="Synthetic operator", team_id=None, machine_id=None,
        shift_id=None, line_id="SYNTHETIC-LINE", event_type="START",
        timestamp_start=now, timestamp_end=None, duration_minutes=None,
        qty_good=None, qty_scrap=None, qty_rework=None, reason_code=None,
        remarks=None, extra_data=None, created_at=now,
    )


def test_start_route_requires_key_and_returns_the_same_persisted_event_on_retry(monkeypatch):
    user = _user()
    work_order_id = uuid4()
    session_id = uuid4()
    event = _activity(work_order_id, user.id)
    calls = []

    async def allow_session(*_args, **_kwargs):
        return SimpleNamespace(id=session_id)

    async def start(_db, _work_order_id, **kwargs):
        calls.append(kwargs)

    async def find_event(_db, requested_wo_id, actor_id, key):
        assert requested_wo_id == work_order_id
        assert actor_id == user.id
        assert key == "start-retry-1"
        return event

    monkeypatch.setattr(shop_floor, "_require_execution_session", allow_session)
    monkeypatch.setattr(shop_floor.svc, "start_work_order", start)
    monkeypatch.setattr(shop_floor.svc, "get_execution_idempotency_event", find_event)

    body = {"session_id": str(session_id), "operator_name": "Synthetic operator", "line_id": "SYNTHETIC-LINE"}
    with TestClient(_app(user, object())) as client:
        missing_key = client.post(f"/shop-floor/work-orders/{work_order_id}/start", json=body)
        first = client.post(
            f"/shop-floor/work-orders/{work_order_id}/start",
            json=body,
            headers={"Idempotency-Key": "start-retry-1"},
        )
        retry = client.post(
            f"/shop-floor/work-orders/{work_order_id}/start",
            json=body,
            headers={"Idempotency-Key": "start-retry-1"},
        )

    assert missing_key.status_code == 422
    assert first.status_code == retry.status_code == 200
    assert first.json()["id"] == retry.json()["id"] == str(event.id)
    assert len(calls) == 2
    assert calls[0]["actor_user_id"] == user.id
    assert calls[0]["idempotency_key"] == "start-retry-1"
    assert calls[0]["request_fingerprint"] == calls[1]["request_fingerprint"]


def test_start_route_maps_reused_key_with_different_payload_to_conflict(monkeypatch):
    user = _user()
    work_order_id = uuid4()

    async def allow_session(*_args, **_kwargs):
        return SimpleNamespace(id=uuid4())

    async def reject_reuse(*_args, **_kwargs):
        raise shop_floor.svc.IdempotencyConflictError("key belongs to another payload")

    monkeypatch.setattr(shop_floor, "_require_execution_session", allow_session)
    monkeypatch.setattr(shop_floor.svc, "start_work_order", reject_reuse)

    with TestClient(_app(user, object())) as client:
        response = client.post(
            f"/shop-floor/work-orders/{work_order_id}/start",
            json={"operator_name": "Synthetic operator"},
            headers={"Idempotency-Key": "start-retry-2"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "key belongs to another payload"


def test_downtime_start_uses_authenticated_actor_and_stable_retry_fields(monkeypatch):
    user = _user()
    captured = []
    now = datetime.now(timezone.utc)
    downtime_id = uuid4()

    def allow_line_edit(current_user, line_id):
        assert current_user is user
        assert line_id == "SYNTHETIC-LINE"

    async def start(_db, data):
        captured.append(data)
        return SimpleNamespace(
            id=downtime_id, work_order_id=None, production_order_id=None,
            session_id=None, created_by_user_id=user.id, closed_by_user_id=None,
            machine_id=None, machine_name=None, line_id="SYNTHETIC-LINE",
            operator_id=None, operator_name=None, team_id=None, shift_id=None,
            start_time=now, end_time=None, duration_minutes=None,
            is_closed=False, downtime_category="IT_ISSUE", root_reason="Synthetic test",
            impact_level="LOW", comments=None, created_at=now,
        )

    monkeypatch.setattr(shop_floor, "_require_line_edit", allow_line_edit)
    monkeypatch.setattr(shop_floor.svc, "start_downtime", start)
    body = {
        "line_id": "SYNTHETIC-LINE",
        "downtime_category": "IT_ISSUE",
        "root_reason": "Synthetic test",
        "impact_level": "LOW",
    }

    with TestClient(_app(user, object())) as client:
        missing_key = client.post("/shop-floor/downtime", json=body)
        first = client.post(
            "/shop-floor/downtime", json=body,
            headers={"Idempotency-Key": "downtime-retry-1"},
        )
        retry = client.post(
            "/shop-floor/downtime", json=body,
            headers={"Idempotency-Key": "downtime-retry-1"},
        )

    assert missing_key.status_code == 422
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"] == str(downtime_id)
    assert len(captured) == 2
    assert captured[0]["created_by_user_id"] == user.id
    assert captured[0]["start_idempotency_key"] == "downtime-retry-1"
    assert captured[0]["start_idempotency_fingerprint"] == captured[1]["start_idempotency_fingerprint"]


def test_downtime_stop_maps_key_conflict_to_http_409(monkeypatch):
    user = _user()
    downtime = SimpleNamespace(id=uuid4(), created_by_user_id=user.id, line_id="SYNTHETIC-LINE")

    class _DB:
        async def get(self, _model, downtime_id):
            assert downtime_id == downtime.id
            return downtime

    def allow_line_edit(current_user, line_id):
        assert current_user is user
        assert line_id == "SYNTHETIC-LINE"

    async def reject_reuse(*_args, **_kwargs):
        raise shop_floor.svc.IdempotencyConflictError("stop key belongs to another payload")

    monkeypatch.setattr(shop_floor, "_require_line_edit", allow_line_edit)
    monkeypatch.setattr(shop_floor.svc, "stop_downtime", reject_reuse)

    with TestClient(_app(user, _DB())) as client:
        response = client.post(
            f"/shop-floor/downtime/{downtime.id}/stop",
            json={"comments": "Synthetic stop"},
            headers={"Idempotency-Key": "downtime-stop-retry-1"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "stop key belongs to another payload"
