"""M31.S01.T004 partner audit and usage analytics checks; disposable PostgreSQL only."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.api_portal import ApiClientApplication, ApiKey, ApiKeyUsageLog, ApiOAuthClientSecret
from app.models.audit_log import AuditLog
from app.models.user import User


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s01_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S01_T004_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M31_S01_T004_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M31_S01_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration reads/writes: DATABASE_URL must match the exact loopback M31.S01.T004 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m31_s01_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t003_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t004_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user: User, *, permissions: tuple[str, ...] = ()):
    role_permissions = [SimpleNamespace(is_active=True, code=code) for code in permissions]
    roles = [SimpleNamespace(is_active=True, permissions=role_permissions)] if role_permissions else []
    return SimpleNamespace(
        id=user.id, email=user.email, full_name=user.full_name,
        is_superuser=False, roles=roles, access_scopes=[],
    )


async def _new_user(email: str) -> User:
    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(), email=email, username=email, full_name=email,
            hashed_password="test-only-not-a-real-credential", is_active=True, is_superuser=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _delete_users(*user_ids) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        key_ids = select(ApiKey.key_id).where(ApiKey.user_id.in_([str(user_id) for user_id in user_ids]))
        await db.execute(delete(ApiKeyUsageLog).where(ApiKeyUsageLog.key_id.in_(key_ids)))
        await db.execute(delete(ApiKey).where(ApiKey.key_id.in_(key_ids)))
        application_ids = select(ApiClientApplication.client_id).where(
            ApiClientApplication.owner_user_id.in_(user_ids)
        )
        await db.execute(delete(ApiOAuthClientSecret).where(ApiOAuthClientSecret.application_id.in_(application_ids)))
        await db.execute(delete(ApiClientApplication).where(ApiClientApplication.owner_user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()

@pytest.mark.asyncio(loop_scope="session")
async def test_partner_audit_is_secret_free_actor_scoped_and_usage_analytics_are_record_based():
    _require_task_owned_database()
    owner = await _new_user(f"m31-audit-owner-{uuid4().hex}@example.invalid")
    other = await _new_user(f"m31-audit-other-{uuid4().hex}@example.invalid")
    permissions = ("integrations.view", "integrations.edit")

    async def override_db():
        async with AsyncSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(owner, permissions=permissions)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            application_response = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Audit fixture", "environment": "sandbox"},
            )
            assert application_response.status_code == 201, application_response.text
            application_id = application_response.json()["client_id"]
            key_response = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Audit fixture key"},
            )
            assert key_response.status_code == 201, key_response.text
            key = key_response.json()
            raw_key = key["raw_key"]

            rotated_key_response = await client.post(
                f"/api/v1/developer/keys/{key['key_id']}/rotate", json={}
            )
            assert rotated_key_response.status_code == 201, rotated_key_response.text
            rotated_key = rotated_key_response.json()
            assert (await client.delete(f"/api/v1/developer/keys/{rotated_key['key_id']}")).status_code == 204

            oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Audit fixture OAuth"},
            )
            assert oauth_response.status_code == 201, oauth_response.text
            oauth = oauth_response.json()
            raw_secret = oauth["client_secret"]
            rotated_oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets/{oauth['secret_id']}/rotate",
                json={},
            )
            assert rotated_oauth_response.status_code == 201, rotated_oauth_response.text
            rotated_oauth = rotated_oauth_response.json()
            assert (await client.delete(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets/{rotated_oauth['secret_id']}"
            )).status_code == 204

            active_key_response = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Disabled with application"},
            )
            assert active_key_response.status_code == 201, active_key_response.text
            active_key = active_key_response.json()
            active_oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Disabled with application"},
            )
            assert active_oauth_response.status_code == 201, active_oauth_response.text
            active_oauth = active_oauth_response.json()
            raw_active_key = active_key["raw_key"]
            raw_active_oauth = active_oauth["client_secret"]
            deactivate_response = await client.patch(
                f"/api/v1/developer/applications/{application_id}", json={"is_active": False}
            )
            assert deactivate_response.status_code == 200, deactivate_response.text
            assert deactivate_response.json()["is_active"] is False

            audit_response = await client.get("/api/v1/developer/audit?limit=50")
            assert audit_response.status_code == 200, audit_response.text
            audit = audit_response.json()
            event_types = {event["event_type"] for event in audit}
            assert {
                "PARTNER_APPLICATION_CREATED",
                "PARTNER_APPLICATION_UPDATED",
                "PARTNER_API_KEY_CREATED",
                "PARTNER_API_KEY_ROTATED",
                "PARTNER_API_KEY_REVOKED",
                "PARTNER_OAUTH_SECRET_CREATED",
                "PARTNER_OAUTH_SECRET_ROTATED",
                "PARTNER_OAUTH_SECRET_REVOKED",
            }.issubset(event_types)
            assert raw_key not in audit_response.text
            assert raw_secret not in audit_response.text
            assert raw_active_key not in audit_response.text
            assert raw_active_oauth not in audit_response.text
            assert all("secret_hash" not in event["details"] for event in audit)
            assert all("key_hash" not in event["details"] for event in audit)
            app_update = next(event for event in audit if event["event_type"] == "PARTNER_APPLICATION_UPDATED")
            assert app_update["details"]["deactivated_keys"] == 1
            assert app_update["details"]["deactivated_oauth_secrets"] == 1

            async with AsyncSessionLocal() as db:
                now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                db.add_all(
                    [
                        ApiKeyUsageLog(
                            key_id=UUID(active_key["key_id"]),
                            endpoint="/fixture/ok",
                            method="GET",
                            status_code=200,
                            response_ms=20,
                            ip_address="192.0.2.10",
                            created_at=now_utc_naive - timedelta(hours=1),
                        ),
                        ApiKeyUsageLog(
                            key_id=UUID(active_key["key_id"]),
                            endpoint="/fixture/error",
                            method="POST",
                            status_code=429,
                            response_ms=80,
                            ip_address="192.0.2.11",
                            created_at=now_utc_naive - timedelta(days=1, hours=1),
                        ),
                        ApiKeyUsageLog(
                            key_id=UUID(active_key["key_id"]),
                            endpoint="/fixture/unknown",
                            method="GET",
                            status_code=None,
                            response_ms=None,
                            ip_address="192.0.2.12",
                            created_at=now_utc_naive - timedelta(days=1, hours=2),
                        ),
                        ApiKeyUsageLog(
                            key_id=UUID(active_key["key_id"]),
                            endpoint="/fixture/future",
                            method="GET",
                            status_code=200,
                            response_ms=5,
                            created_at=now_utc_naive + timedelta(days=1),
                        ),
                    ]
                )
                await db.commit()

            analytics_response = await client.get("/api/v1/developer/usage/analytics?days=30")
            assert analytics_response.status_code == 200, analytics_response.text
            analytics = analytics_response.json()
            assert analytics["days"] == 30
            assert analytics["total_calls"] == 3
            assert analytics["success_calls"] == 1
            assert analytics["error_calls"] == 1
            assert analytics["unclassified_calls"] == 1
            assert analytics["average_response_ms"] == 50.0
            assert len(analytics["daily_usage"]) == 2
            assert analytics["collection_enabled"] is False
            assert "Automatic request capture is disabled" in analytics["collection_note"]
            assert "192.0.2." not in analytics_response.text
            assert (await client.get("/api/v1/developer/usage/analytics?days=91")).status_code == 422
            per_key_usage = await client.get(f"/api/v1/developer/keys/{active_key['key_id']}/usage")
            assert per_key_usage.status_code == 200
            assert len(per_key_usage.json()) == 3
            assert "192.0.2." not in per_key_usage.text

            app.dependency_overrides[get_current_user] = lambda: _actor(other, permissions=permissions)
            other_audit = await client.get("/api/v1/developer/audit")
            assert other_audit.status_code == 200
            assert other_audit.json() == []
            other_analytics = await client.get("/api/v1/developer/usage/analytics")
            assert other_analytics.status_code == 200
            assert other_analytics.json()["total_calls"] == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await _delete_users(owner.id, other.id)
