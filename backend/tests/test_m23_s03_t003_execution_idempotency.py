from datetime import timedelta
import asyncio
import os
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.api.v1.endpoints import shop_floor as shop_floor_api
from app.db.session import AsyncSessionLocal, engine
from app.models.shop_floor import SFDowntimeLog, WOActivityLog
from app.models.user import User
from app.services import shop_floor_service


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m23_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def test_database_guard_rejects_non_task_owned_databases():
    name = "fmcg_m23_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m23_s03_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(
    os.environ.get("M23_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the exact task-owned disposable PostgreSQL database",
)
async def test_downtime_retry_persists_one_row_and_rejects_key_reuse():
    expected_name = os.environ.get("M23_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    assert _is_task_owned_database(engine.url, expected_name), (
        "Refusing integration writes unless DATABASE_URL targets the exact loopback M23.S03.T003 database."
    )
    key = f"m23-s03-t003-{uuid4().hex}"
    suffix = uuid4().hex[:20]
    user = User(
        email=f"m23-s03-t003-{suffix}@example.invalid",
        username=f"m23s03t003{suffix}",
        full_name="Synthetic Shop Floor operator",
        hashed_password="test-only",
    )
    data = {
        "created_by_user_id": None,
        "line_id": "SYNTHETIC-LINE-T003",
        "downtime_category": "IT_ISSUE",
        "root_reason": "Synthetic retry acceptance",
        "start_idempotency_key": key,
        "start_idempotency_fingerprint": "a" * 64,
    }
    try:
        async with AsyncSessionLocal() as db:
            db.add(user)
            await db.commit()
            data["created_by_user_id"] = user.id
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_name

        async def start_once():
            async with AsyncSessionLocal() as db:
                return await shop_floor_service.start_downtime(db, data)

        first, replay = await asyncio.gather(start_once(), start_once())
        assert first.id == replay.id
        assert first.created_by_user_id == user.id

        mismatched = {**data, "start_idempotency_fingerprint": "b" * 64}
        async with AsyncSessionLocal() as db:
            with pytest.raises(shop_floor_service.IdempotencyConflictError):
                await shop_floor_service.start_downtime(db, mismatched)
            await db.rollback()

        async with AsyncSessionLocal() as db:
            count = await db.scalar(
                select(func.count()).select_from(SFDowntimeLog).where(
                    SFDowntimeLog.created_by_user_id == user.id,
                    SFDowntimeLog.start_idempotency_key == key,
                    SFDowntimeLog.line_id == "SYNTHETIC-LINE-T003",
                )
            )
            assert count == 1
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                SFDowntimeLog.__table__.delete().where(
                    SFDowntimeLog.created_by_user_id == user.id,
                    SFDowntimeLog.start_idempotency_key == key,
                    SFDowntimeLog.line_id == "SYNTHETIC-LINE-T003",
                )
            )
            await db.execute(User.__table__.delete().where(User.id == user.id))
            await db.commit()


def test_execution_fingerprint_binds_actor_resource_action_and_payload():
    actor_id = uuid4()
    work_order_id = uuid4()
    user = SimpleNamespace(id=actor_id)
    body = SimpleNamespace(model_dump=lambda **_kwargs: {"qty": "2.5", "session_id": "session-1"})

    key, first = shop_floor_api._execution_idempotency_context(
        "retry-1", action="consume", resource_id=f"work-order:{work_order_id}", user=user, body=body,
    )
    same_request = shop_floor_api._execution_idempotency_context(
        "retry-1", action="consume", resource_id=f"work-order:{work_order_id}", user=user, body=body,
    )[1]
    other_action = shop_floor_api._execution_idempotency_context(
        "retry-1", action="scrap", resource_id=f"work-order:{work_order_id}", user=user, body=body,
    )[1]
    other_resource = shop_floor_api._execution_idempotency_context(
        "retry-1", action="consume", resource_id=f"work-order:{uuid4()}", user=user, body=body,
    )[1]

    assert key == "retry-1"
    assert first == same_request
    assert first != other_action
    assert first != other_resource


def test_execution_idempotency_key_rejects_blank_or_oversized_values():
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(model_dump=lambda **_kwargs: {})
    for key in ("", "  ", "x" * 129, "bad key"):
        with pytest.raises(HTTPException) as error:
            shop_floor_api._execution_idempotency_context(
                key, action="note", resource_id="work-order:1", user=user, body=body,
            )
        assert error.value.status_code == 400


class _Result:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class _Session:
    def __init__(self, row):
        self.row = row

    async def execute(self, _statement):
        return _Result(self.row)


@pytest.mark.asyncio
async def test_existing_execution_key_replays_only_matching_fingerprint():
    actor_id, work_order_id = uuid4(), uuid4()
    event = SimpleNamespace(id=uuid4(), idempotency_fingerprint="a" * 64)

    replay = await shop_floor_service._find_idempotent_execution_event(
        _Session(event), work_order_id, actor_id, "retry-1", "a" * 64,
    )
    assert replay is event

    with pytest.raises(shop_floor_service.IdempotencyConflictError):
        await shop_floor_service._find_idempotent_execution_event(
            _Session(event), work_order_id, actor_id, "retry-1", "b" * 64,
        )


def test_activity_and_downtime_models_enforce_idempotency_pairing():
    activity_constraints = {item.name: str(getattr(item, "sqltext", "")) for item in WOActivityLog.__table__.constraints}
    downtime_constraints = {item.name: str(getattr(item, "sqltext", "")) for item in SFDowntimeLog.__table__.constraints}

    assert "ck_sf_activity_logs_idempotency_pair" in activity_constraints
    assert "uq_sf_activity_logs_actor_idempotency" in activity_constraints
    assert "ck_sf_downtime_logs_start_idempotency_pair" in downtime_constraints
    assert "ck_sf_downtime_logs_stop_idempotency_pair" in downtime_constraints
    assert "uq_sf_downtime_logs_creator_start_idempotency" in downtime_constraints


def test_shop_floor_execution_mutations_require_idempotency_header():
    expected_paths = {
        "/work-orders/{wo_id}/start",
        "/work-orders/{wo_id}/pause",
        "/work-orders/{wo_id}/resume",
        "/work-orders/{wo_id}/update-qty",
        "/work-orders/{wo_id}/scrap",
        "/work-orders/{wo_id}/finish",
        "/work-orders/{wo_id}/help",
        "/work-orders/{wo_id}/qc-trigger",
        "/work-orders/{wo_id}/note",
        "/work-orders/{wo_id}/materials/{material_id}/consume",
        "/work-orders/{wo_id}/qc-checkpoints",
        "/downtime",
        "/downtime/{dt_id}/stop",
    }
    routes = {
        route.path: route
        for route in shop_floor_api.router.routes
        if getattr(route, "methods", None) and "POST" in route.methods and route.path in expected_paths
    }

    assert set(routes) == expected_paths
    for route in routes.values():
        assert any(
            parameter.alias == "Idempotency-Key" and parameter.field_info.is_required()
            for parameter in route.dependant.header_params
        )


@pytest.mark.asyncio
async def test_stop_downtime_same_key_returns_original_closed_record(monkeypatch):
    start_time = shop_floor_service._now().replace(microsecond=0)
    end_time = start_time + timedelta(minutes=1)
    record = SimpleNamespace(
        id=uuid4(),
        work_order_id=None,
        start_time=start_time,
        end_time=None,
        duration_minutes=None,
        is_closed=False,
        comments=None,
        closed_by_user_id=None,
        stop_idempotency_key=None,
        stop_idempotency_fingerprint=None,
    )

    class _DowntimeSession:
        commits = 0

        async def execute(self, _statement):
            return _Result(record)

        async def commit(self):
            self.commits += 1

        async def refresh(self, _row):
            return None

    db = _DowntimeSession()
    monkeypatch.setattr(
        shop_floor_service,
        "_now",
        lambda: end_time,
    )

    first = await shop_floor_service.stop_downtime(
        db, record.id, "Stopped", closed_by_user_id=uuid4(),
        idempotency_key="stop-1", request_fingerprint="c" * 64,
    )
    first_end_time = first.end_time
    replay = await shop_floor_service.stop_downtime(
        db, record.id, "Stopped", closed_by_user_id=first.closed_by_user_id,
        idempotency_key="stop-1", request_fingerprint="c" * 64,
    )

    assert replay is first
    assert replay.end_time == first_end_time
    assert db.commits == 1
