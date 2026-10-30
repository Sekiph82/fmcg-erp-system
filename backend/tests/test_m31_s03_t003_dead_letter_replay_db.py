"""M31.S03.T003 replay lineage checks; require a named loopback disposable DB."""
from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal, engine
from app.models.webhook import DeliveryAttempt, DeliveryStatus, EventLog, Subscription
from app.schemas.webhook import ReplayRequest
from app.services.webhook_service import (
    list_dead_letter_deliveries,
    manual_retry_delivery,
    replay_events,
)


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s03_t003_[a-f0-9]{24}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S03_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access without the exact loopback M31.S03.T003 test database.")


def test_database_guard_rejects_other_tasks_and_non_loopback_urls():
    name = "fmcg_m31_s03_t003_0123456789abcdef01234567"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s02_t003_0123456789abcdef01234567")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_lineage_is_unique_and_preserves_the_dead_letter_record():
    _require_task_owned_database()
    suffix = uuid4().hex
    event_code = f"test.m31.s03.t003.{suffix}"
    event_id = None
    subscription_id = None
    delivery_id = None
    try:
        async with AsyncSessionLocal() as db:
            event = EventLog(event_code=event_code, module="testing", payload={})
            subscription = Subscription(
                name=f"Synthetic dead-letter {suffix}",
                endpoint_url="https://example.invalid/m31-s03-t003",
                event_codes=[event_code],
                active_flag=True,
            )
            db.add_all([event, subscription])
            await db.flush()
            delivery = DeliveryAttempt(
                event_log_id=event.id,
                subscription_id=subscription.id,
                attempt_no=6,
                status=DeliveryStatus.DEAD_LETTER,
                error_message="synthetic exhausted delivery",
            )
            db.add(delivery)
            await db.commit()
            event_id = event.id
            subscription_id = subscription.id
            delivery_id = delivery.id

        async with AsyncSessionLocal() as db:
            assert await replay_events(
                db,
                ReplayRequest(
                    event_ids=[event_id],
                    subscription_ids=[subscription_id],
                ),
            ) == 1

        async with AsyncSessionLocal() as db:
            original = await db.get(DeliveryAttempt, delivery_id)
            assert original.status == DeliveryStatus.DEAD_LETTER
            assert await manual_retry_delivery(db, delivery_id) is None
            assert await list_dead_letter_deliveries(db) == []
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(
                    DeliveryAttempt.replay_of_id == delivery_id
                )
            ) == 1

            db.add(DeliveryAttempt(
                event_log_id=event_id,
                subscription_id=subscription_id,
                attempt_no=8,
                replay_of_id=delivery_id,
                status=DeliveryStatus.PENDING,
            ))
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()
    finally:
        if event_code:
            async with AsyncSessionLocal() as db:
                await db.execute(delete(EventLog).where(EventLog.event_code == event_code))
                await db.execute(delete(Subscription).where(Subscription.id == subscription_id))
                await db.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_first_bulk_replays_create_only_one_root_attempt():
    _require_task_owned_database()
    suffix = uuid4().hex
    event_code = f"test.m31.s03.t003.concurrent.{suffix}"
    event_id = None
    subscription_id = None
    try:
        async with AsyncSessionLocal() as db:
            event = EventLog(event_code=event_code, module="testing", payload={})
            subscription = Subscription(
                name=f"Synthetic concurrent replay {suffix}",
                endpoint_url="https://example.invalid/m31-s03-t003-concurrent",
                event_codes=[event_code],
                active_flag=True,
            )
            db.add_all([event, subscription])
            await db.commit()
            event_id = event.id
            subscription_id = subscription.id

        async def replay_once() -> int:
            async with AsyncSessionLocal() as db:
                return await replay_events(
                    db,
                    ReplayRequest(
                        event_ids=[event_id],
                        subscription_ids=[subscription_id],
                    ),
                )

        results = await asyncio.gather(replay_once(), replay_once())
        assert sorted(results) == [0, 1]
        async with AsyncSessionLocal() as db:
            assert await db.scalar(
                select(func.count()).select_from(DeliveryAttempt).where(
                    DeliveryAttempt.event_log_id == event_id,
                    DeliveryAttempt.subscription_id == subscription_id,
                )
            ) == 1
    finally:
        if event_code:
            async with AsyncSessionLocal() as db:
                await db.execute(delete(EventLog).where(EventLog.event_code == event_code))
                await db.execute(delete(Subscription).where(Subscription.id == subscription_id))
                await db.commit()
