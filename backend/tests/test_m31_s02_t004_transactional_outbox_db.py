"""M31.S02.T004 outbox atomicity; requires its named loopback disposable PostgreSQL DB."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL

from app.core.deps import get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.webhook import DeliveryAttempt, EventLog, InboundEndpoint, Subscription
from app.services.webhook_service import stage_event


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s02_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S02_T004_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S02_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access unless DATABASE_URL matches the exact loopback M31.S02.T004 database.")


def test_database_guard_rejects_other_databases():
    name = "fmcg_m31_s02_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s02_t003_0123456789abcdef0123")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
async def test_business_state_event_and_delivery_queue_share_commit_or_rollback():
    _require_task_owned_database()
    suffix = uuid4().hex
    endpoint_path = f"t004-{suffix}"
    event_code = f"inbound.t004_{suffix}"
    endpoint_id = None
    subscription_id = None
    try:
        async with AsyncSessionLocal() as db:
            endpoint = InboundEndpoint(
                name="Synthetic T004 transaction",
                endpoint_path=endpoint_path,
                handler_module=f"t004_{suffix}",
            )
            subscription = Subscription(
                name="Synthetic T004 outbox subscriber",
                endpoint_url="https://example.invalid/t004",
                event_codes=[event_code],
                active_flag=True,
            )
            db.add_all([endpoint, subscription])
            await db.commit()
            endpoint_id = endpoint.id
            subscription_id = subscription.id

        original_overrides = dict(app.dependency_overrides)

        async def override_db():
            async with AsyncSessionLocal() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                request = {"status": "received"}
                headers = {
                    "Idempotency-Key": "inbound-retry-1",
                    "X-Correlation-ID": "flow-inbound-1",
                    "X-Causation-ID": "event-parent-1",
                }
                first = await client.post(f"/api/v1/webhooks/inbound/{endpoint_path}", json=request, headers=headers)
                repeated = await client.post(f"/api/v1/webhooks/inbound/{endpoint_path}", json=request, headers=headers)
                conflict = await client.post(
                    f"/api/v1/webhooks/inbound/{endpoint_path}",
                    json={"status": "different"},
                    headers=headers,
                )
            assert first.status_code == 200, first.text
            assert repeated.status_code == 200, repeated.text
            assert conflict.status_code == 409, conflict.text
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

        async with AsyncSessionLocal() as db:
            endpoint = await db.get(InboundEndpoint, endpoint_id)
            assert endpoint.receive_count == 2
            api_event = await db.scalar(
                select(EventLog).where(
                    EventLog.event_code == event_code,
                    EventLog.idempotency_key == "inbound-retry-1",
                )
            )
            assert api_event is not None
            assert api_event.payload["correlation_id"] == "flow-inbound-1"
            assert api_event.payload["causation_id"] == "event-parent-1"
            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.event_code == event_code)
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.event_log_id == api_event.id)
            ) == 1

        async with AsyncSessionLocal() as db:
            endpoint = await db.get(InboundEndpoint, endpoint_id)
            assert endpoint is not None
            endpoint.receive_count = 3
            event = await stage_event(
                db,
                event_code,
                {"receipt": "committed"},
                reference_type="inbound_endpoint",
                reference_id=endpoint_path,
            )
            event_id = event.id
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.event_log_id == event_id)
            ) == 1
            await db.commit()

        async with AsyncSessionLocal() as db:
            assert (await db.get(InboundEndpoint, endpoint_id)).receive_count == 3
            assert await db.scalar(select(func.count()).select_from(EventLog).where(EventLog.id == event_id)) == 1
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.event_log_id == event_id)
            ) == 1

        rollback_event_id = None
        async with AsyncSessionLocal() as db:
            endpoint = await db.get(InboundEndpoint, endpoint_id)
            endpoint.receive_count = 4
            event = await stage_event(
                db,
                event_code,
                {"receipt": "rolled-back"},
                reference_type="inbound_endpoint",
                reference_id=endpoint_path,
            )
            rollback_event_id = event.id
            await db.rollback()

        async with AsyncSessionLocal() as db:
            assert (await db.get(InboundEndpoint, endpoint_id)).receive_count == 3
            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.id == rollback_event_id)
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.event_log_id == rollback_event_id)
            ) == 0
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(DeliveryAttempt).where(
                DeliveryAttempt.event_log_id.in_(select(EventLog.id).where(EventLog.event_code == event_code))
            ))
            await cleanup_db.execute(delete(EventLog).where(EventLog.event_code == event_code))
            if subscription_id is not None:
                await cleanup_db.execute(delete(Subscription).where(Subscription.id == subscription_id))
            if endpoint_id is not None:
                await cleanup_db.execute(delete(InboundEndpoint).where(InboundEndpoint.id == endpoint_id))
            await cleanup_db.commit()
