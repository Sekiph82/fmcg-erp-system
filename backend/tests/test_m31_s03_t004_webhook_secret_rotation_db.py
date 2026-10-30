"""M31.S03.T004 secret rotation checks; require this task's named loopback DB."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.webhook import AuthType, InboundEndpoint, Subscription
from app.schemas.webhook import InboundEndpointCreate, SubscriptionCreate
from app.services import webhook_service


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s03_t004_[a-f0-9]{24}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S03_T004_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S03_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access without the exact loopback M31.S03.T004 test database.")


def test_database_guard_rejects_other_tasks_and_non_loopback_urls():
    name = "fmcg_m31_s03_t004_0123456789abcdef01234567"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s03_t003_0123456789abcdef01234567")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get("M31_S03_T004_DISPOSABLE_TEST_DATABASE") != "1", reason="Run only with the task-owned disposable PostgreSQL database.")
async def test_subscription_and_inbound_secrets_rotate_with_encrypted_storage_and_audit():
    _require_task_owned_database()
    suffix = uuid4().hex
    old_secret = f"old-{suffix}-" + "x" * 40
    subscription_id = None
    endpoint_id = None
    try:
        async with AsyncSessionLocal() as db:
            subscription = await webhook_service.create_subscription(
                db,
                SubscriptionCreate(
                    name=f"Synthetic rotation subscription {suffix}",
                    endpoint_url="https://example.invalid/m31-s03-t004",
                    auth_type=AuthType.HMAC,
                    secret_key=old_secret,
                ),
                actor=None,
            )
            endpoint = await webhook_service.create_inbound_endpoint(
                db,
                InboundEndpointCreate(
                    name=f"Synthetic rotation endpoint {suffix}",
                    endpoint_path=f"synthetic-{suffix}",
                    auth_type=AuthType.HMAC,
                    secret_key=old_secret,
                ),
                actor=None,
            )
            subscription_id = subscription.id
            endpoint_id = endpoint.id

        async with AsyncSessionLocal() as db:
            subscription_rotation = await webhook_service.rotate_subscription_secret(
                db, subscription_id, actor=None
            )
        async with AsyncSessionLocal() as db:
            endpoint_rotation = await webhook_service.rotate_inbound_endpoint_secret(
                db, endpoint_id, actor=None
            )

        for result in (subscription_rotation, endpoint_rotation):
            assert result is not None
            assert result["secret_version"] == 2
            assert result["secret_key"] != old_secret
            assert len(result["secret_key"]) >= 32
            assert result["previous_secret_expires_at"] > datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            subscription = await db.get(Subscription, subscription_id)
            endpoint = await db.get(InboundEndpoint, endpoint_id)
            assert subscription.secret_key.startswith(webhook_service.WEBHOOK_SECRET_ENVELOPE_PREFIX)
            assert endpoint.secret_key.startswith(webhook_service.WEBHOOK_SECRET_ENVELOPE_PREFIX)
            assert subscription.previous_secret_key.startswith(webhook_service.WEBHOOK_SECRET_ENVELOPE_PREFIX)
            assert endpoint.previous_secret_key.startswith(webhook_service.WEBHOOK_SECRET_ENVELOPE_PREFIX)
            assert webhook_service._read_webhook_secret(subscription.secret_key) == subscription_rotation["secret_key"]
            assert webhook_service._read_webhook_secret(endpoint.secret_key) == endpoint_rotation["secret_key"]
            assert webhook_service._read_webhook_secret(subscription.previous_secret_key) == old_secret
            assert webhook_service._read_webhook_secret(endpoint.previous_secret_key) == old_secret

            audits = list(
                (
                    await db.scalars(
                        select(AuditLog).where(
                            AuditLog.event_type == "WEBHOOK_SECRET_ROTATED",
                            AuditLog.target_id.in_([str(subscription_id), str(endpoint_id)]),
                        )
                    )
                ).all()
            )
            assert len(audits) == 2
            assert all(old_secret not in str(entry.details) for entry in audits)
            assert all(subscription_rotation["secret_key"] not in str(entry.after_value) for entry in audits)
            assert all(endpoint_rotation["secret_key"] not in str(entry.after_value) for entry in audits)
            assert all(not hasattr(entry, "secret_key") for entry in audits)
    finally:
        async with AsyncSessionLocal() as db:
            if subscription_id or endpoint_id:
                await db.execute(
                    delete(AuditLog).where(
                        AuditLog.target_id.in_([str(subscription_id), str(endpoint_id)])
                    )
                )
            if subscription_id:
                await db.execute(delete(Subscription).where(Subscription.id == subscription_id))
            if endpoint_id:
                await db.execute(delete(InboundEndpoint).where(InboundEndpoint.id == endpoint_id))
            await db.commit()
