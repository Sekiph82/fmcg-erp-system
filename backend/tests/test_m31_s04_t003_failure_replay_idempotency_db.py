"""M31.S04.T003 end-to-end failure/replay checks for an owned disposable DB."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.webhook import DeliveryAttempt, DeliveryStatus, EventLog, Subscription
from app.schemas.webhook import ReplayRequest
from app.services.webhook_service import (
    EventIdempotencyConflictError,
    process_pending_deliveries,
    process_retry_deliveries,
    publish_event,
    replay_events,
)


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s04_t003_[a-f0-9]{24}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S04_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S04_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access without the exact loopback M31.S04.T003 test database.")


def test_database_guard_rejects_another_task_database_and_remote_hosts():
    name = "fmcg_m31_s04_t003_0123456789abcdef01234567"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(
        URL.create("postgresql+asyncpg", host="127.0.0.1", database=name),
        "fmcg_m31_s03_t003_0123456789abcdef01234567",
    )
    assert not _is_task_owned_database(
        URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name
    )
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get("M31_S04_T003_DISPOSABLE_TEST_DATABASE") != "1", reason="Run only with the task-owned disposable PostgreSQL database.")
async def test_idempotent_publish_failure_retry_dead_letter_and_replay_chain():
    _require_task_owned_database()
    suffix = uuid4().hex
    event_code = f"test.m31.s04.t003.failure.{suffix}"
    subscription_id = None
    try:
        async with AsyncSessionLocal() as db:
            subscription = Subscription(
                name=f"Synthetic failure/replay {suffix}",
                # A closed loopback port makes the synthetic request fail without
                # contacting an external service.
                endpoint_url="http://127.0.0.1:1/m31-s04-t003",
                event_codes=[event_code],
                max_retries=1,
                timeout_seconds=1,
                active_flag=True,
            )
            db.add(subscription)
            await db.commit()
            subscription_id = subscription.id

        request = {
            "idempotency_key": "synthetic-failure-1",
            "correlation_id": "synthetic-workflow-1",
            "payload": {"status": "posted", "amount": 12},
            "module": "testing",
        }
        async with AsyncSessionLocal() as db:
            original = await publish_event(db, event_code, request["payload"], **{
                key: value for key, value in request.items() if key != "payload"
            })

        async with AsyncSessionLocal() as db:
            duplicate = await publish_event(db, event_code, request["payload"], **{
                key: value for key, value in request.items() if key != "payload"
            })
            assert duplicate.id == original.id
            assert duplicate._idempotency_replayed is True
            with pytest.raises(EventIdempotencyConflictError):
                await publish_event(
                    db,
                    event_code,
                    {"status": "void", "amount": 12},
                    **{key: value for key, value in request.items() if key != "payload"},
                )
            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.event_code == event_code)
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(
                    DeliveryAttempt.event_log_id == original.id
                )
            ) == 1

        async with AsyncSessionLocal() as db:
            assert await process_pending_deliveries(db) == 1

        async with AsyncSessionLocal() as db:
            first = await db.scalar(
                select(DeliveryAttempt).where(DeliveryAttempt.event_log_id == original.id)
            )
            assert first.status == DeliveryStatus.RETRYING
            assert first.error_message in {
                "Delivery preparation/request failed (ConnectError)",
                "Delivery preparation/request failed (ConnectTimeout)",
            }
            assert first.next_retry_at is not None
            first.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()

        async with AsyncSessionLocal() as db:
            assert await process_retry_deliveries(db) == 1

        async with AsyncSessionLocal() as db:
            attempts = list((await db.scalars(
                select(DeliveryAttempt)
                .where(DeliveryAttempt.event_log_id == original.id)
                .order_by(DeliveryAttempt.attempt_no)
            )).all())
            assert [attempt.attempt_no for attempt in attempts] == [1, 2]
            assert attempts[0].status == DeliveryStatus.FAILED
            assert attempts[1].status == DeliveryStatus.DEAD_LETTER
            assert attempts[1].replay_of_id == attempts[0].id
            assert attempts[1].next_retry_at is None

        selector = ReplayRequest(
            event_ids=[original.id],
            subscription_ids=[subscription_id],
        )
        async with AsyncSessionLocal() as db:
            assert await replay_events(db, selector) == 1
        async with AsyncSessionLocal() as db:
            assert await replay_events(db, selector) == 0
            attempts = list((await db.scalars(
                select(DeliveryAttempt)
                .where(DeliveryAttempt.event_log_id == original.id)
                .order_by(DeliveryAttempt.attempt_no)
            )).all())
            assert [attempt.attempt_no for attempt in attempts] == [1, 2, 3]
            assert attempts[2].status == DeliveryStatus.PENDING
            assert attempts[2].replay_of_id == attempts[1].id
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(
                    DeliveryAttempt.replay_of_id == attempts[1].id
                )
            ) == 1
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(EventLog).where(EventLog.event_code == event_code))
            if subscription_id is not None:
                await db.execute(delete(Subscription).where(Subscription.id == subscription_id))
            await db.commit()
