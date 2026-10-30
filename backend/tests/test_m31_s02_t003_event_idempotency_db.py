"""M31.S02.T003 persistence/API checks; requires its named loopback disposable PostgreSQL DB."""
from __future__ import annotations

import asyncio
import os
import re
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.webhook import DeliveryAttempt, EventDefinition, EventDefinitionVersion, EventLog, Subscription
from app.services.webhook_service import EventIdempotencyConflictError, publish_event


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s02_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S02_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S02_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access unless DATABASE_URL matches the exact loopback M31.S02.T003 database.")


def test_database_guard_rejects_other_databases():
    name = "fmcg_m31_s02_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s02_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get("M31_S02_T003_DISPOSABLE_TEST_DATABASE") != "1", reason="Run only with the task-owned disposable PostgreSQL database.")
async def test_idempotent_publish_and_conflict_preserve_one_event_and_delivery():
    _require_task_owned_database()
    event_code = f"test.m31.s02.t003.{uuid4().hex}"
    definition_id = None
    subscription_id = None
    try:
        async with AsyncSessionLocal() as db:
            definition = EventDefinition(
                event_code=event_code,
                event_name="Synthetic idempotency test event",
                module="testing",
                payload_schema=None,
            )
            db.add(definition)
            await db.flush()
            definition_id = definition.id
            db.add(EventDefinitionVersion(
                event_def_id=definition.id,
                schema_version=1,
                payload_schema=None,
                change_summary="Synthetic T003 test baseline",
            ))
            subscription = Subscription(
                name="Synthetic T003 delivery",
                endpoint_url="https://example.invalid/webhook",
                event_codes=[event_code],
                active_flag=True,
            )
            db.add(subscription)
            await db.commit()
            subscription_id = subscription.id

        request = {
            "idempotency_key": "invoice-post-17",
            "correlation_id": "workflow-17",
            "causation_id": "event-parent-16",
            "reference_type": "invoice",
            "reference_id": "INV-17",
            "actor_id": "synthetic-user",
            "payload": {"status": "posted", "total": 25},
        }
        async with AsyncSessionLocal() as db:
            original = await publish_event(db, event_code, request["payload"], **{
                key: value for key, value in request.items() if key != "payload"
            })
        async with AsyncSessionLocal() as db:
            repeated = await publish_event(db, event_code, request["payload"], **{
                key: value for key, value in request.items() if key != "payload"
            })
            assert repeated.id == original.id
            assert repeated._idempotency_replayed is True
            assert repeated.payload["correlation_id"] == "workflow-17"
            assert repeated.payload["causation_id"] == "event-parent-16"

            with pytest.raises(EventIdempotencyConflictError):
                await publish_event(db, event_code, {"status": "void", "total": 25}, **{
                    key: value for key, value in request.items() if key != "payload"
                })

            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.event_code == event_code)
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.event_log_id == original.id)
            ) == 1

        actor = {"id": uuid4(), "is_superuser": True}
        original_overrides = dict(app.dependency_overrides)

        async def override_db():
            async with AsyncSessionLocal() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**actor)
        try:
            payload = {
                "event_code": event_code,
                "idempotency_key": "api-retry-1",
                "correlation_id": "api-flow-1",
                "causation_id": "api-parent-1",
                "payload": {"status": "api-posted"},
            }
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                first = await client.post("/api/v1/webhooks/events/publish", json=payload)
                again = await client.post("/api/v1/webhooks/events/publish", json=payload)
                mismatch = await client.post(
                    "/api/v1/webhooks/events/publish",
                    json={**payload, "payload": {"status": "different"}},
                )
            assert first.status_code == 201, first.text
            assert again.status_code == 200, again.text
            assert again.headers["Idempotency-Replayed"] == "true"
            assert first.json()["id"] == again.json()["id"]
            assert again.json()["payload"]["correlation_id"] == "api-flow-1"
            assert again.json()["payload"]["causation_id"] == "api-parent-1"
            assert mismatch.status_code == 409, mismatch.text
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(DeliveryAttempt).where(
                DeliveryAttempt.event_log_id.in_(
                    select(EventLog.id).where(EventLog.event_code == event_code)
                )
            ))
            await cleanup_db.execute(delete(EventLog).where(EventLog.event_code == event_code))
            if subscription_id is not None:
                await cleanup_db.execute(delete(Subscription).where(Subscription.id == subscription_id))
            if definition_id is not None:
                await cleanup_db.execute(
                    delete(EventDefinitionVersion).where(EventDefinitionVersion.event_def_id == definition_id)
                )
                await cleanup_db.execute(delete(EventDefinition).where(EventDefinition.id == definition_id))
            await cleanup_db.commit()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get("M31_S02_T003_DISPOSABLE_TEST_DATABASE") != "1", reason="Run only with the task-owned disposable PostgreSQL database.")
async def test_concurrent_first_uses_of_same_key_converge_on_one_event():
    _require_task_owned_database()
    event_code = f"test.m31.s02.t003.concurrent.{uuid4().hex}"

    async def publish_concurrently():
        async with AsyncSessionLocal() as db:
            return await publish_event(
                db,
                event_code,
                {"status": "posted"},
                idempotency_key="same-concurrent-key",
                correlation_id="flow-concurrent",
            )

    try:
        first, second = await asyncio.gather(publish_concurrently(), publish_concurrently())
        assert first.id == second.id
        async with AsyncSessionLocal() as db:
            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.event_code == event_code)
            ) == 1
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(EventLog).where(EventLog.event_code == event_code))
            await cleanup_db.commit()
