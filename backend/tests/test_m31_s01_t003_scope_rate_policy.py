"""M31.S01.T003/T004 checks; gated to an owned disposable PostgreSQL database."""
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

from app.core.config import settings
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
        and re.fullmatch(r"fmcg_m31_s01_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S01_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M31_S01_T003_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M31_S01_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration reads/writes: DATABASE_URL must match the exact loopback M31.S01.T003 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m31_s01_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t003_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user: User, *, permissions: tuple[str, ...] = (), is_superuser: bool = False):
    role_permissions = [SimpleNamespace(is_active=True, code=code) for code in permissions]
    roles = [SimpleNamespace(is_active=True, permissions=role_permissions)] if role_permissions else []
    return SimpleNamespace(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_superuser=is_superuser,
        roles=roles,
        access_scopes=[],
    )


async def _new_user(email: str) -> User:
    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(),
            email=email,
            username=email,
            full_name=email,
            hashed_password="test-only-not-a-real-credential",
            is_active=True,
            is_superuser=False,
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
async def test_scope_and_rate_policy_is_validated_stored_rotated_and_documented():
    _require_task_owned_database()
    owner = await _new_user(f"m31-policy-owner-{uuid4().hex}@example.invalid")
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
                json={"name": "Scope and rate policy fixture", "environment": "sandbox"},
            )
            assert application_response.status_code == 201, application_response.text
            application_id = application_response.json()["client_id"]

            default_response = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Default policy"},
            )
            assert default_response.status_code == 201, default_response.text
            default_key = default_response.json()
            assert default_key["scopes"] == "read"
            assert default_key["rate_limit_per_min"] == 60

            normalized_response = await client.post(
                "/api/v1/developer/keys",
                json={
                    "application_id": application_id,
                    "key_name": "Normalized policy",
                    "scopes": " WRITE, read ",
                    "rate_limit_per_min": 1,
                },
            )
            assert normalized_response.status_code == 201, normalized_response.text
            normalized_key = normalized_response.json()
            assert normalized_key["scopes"] == "read,write"
            assert normalized_key["rate_limit_per_min"] == 1

            max_response = await client.post(
                "/api/v1/developer/keys",
                json={
                    "application_id": application_id,
                    "key_name": "Maximum rate",
                    "scopes": "write",
                    "rate_limit_per_min": 1000,
                },
            )
            assert max_response.status_code == 201, max_response.text
            assert max_response.json()["rate_limit_per_min"] == 1000

            for index, scopes in enumerate(("", "read,read", "read,unknown", "admin,read")):
                invalid_scope = await client.post(
                    "/api/v1/developer/keys",
                    json={"application_id": application_id, "key_name": f"Invalid scope {index}", "scopes": scopes},
                )
                assert invalid_scope.status_code == 422, invalid_scope.text
            for index, rate in enumerate((0, 1001, -1)):
                invalid_rate = await client.post(
                    "/api/v1/developer/keys",
                    json={
                        "application_id": application_id,
                        "key_name": f"Invalid rate {index}",
                        "rate_limit_per_min": rate,
                    },
                )
                assert invalid_rate.status_code == 422, invalid_rate.text

            non_admin_issue = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Non-admin cannot issue admin", "scopes": "admin"},
            )
            assert non_admin_issue.status_code == 403, non_admin_issue.text

            app.dependency_overrides[get_current_user] = lambda: _actor(
                owner, permissions=permissions, is_superuser=True
            )
            admin_issue = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Superuser admin", "scopes": "admin"},
            )
            assert admin_issue.status_code == 201, admin_issue.text
            assert admin_issue.json()["scopes"] == "admin"

            app.dependency_overrides[get_current_user] = lambda: _actor(owner, permissions=permissions)
            denied_admin_rotation = await client.post(
                f"/api/v1/developer/keys/{admin_issue.json()['key_id']}/rotate",
                json={"scopes": "admin"},
            )
            assert denied_admin_rotation.status_code == 403, denied_admin_rotation.text

            changed_policy = await client.post(
                f"/api/v1/developer/keys/{default_key['key_id']}/rotate",
                json={"scopes": "WRITE, read", "rate_limit_per_min": 1000},
            )
            assert changed_policy.status_code == 201, changed_policy.text
            replacement = changed_policy.json()
            assert replacement["scopes"] == "read,write"
            assert replacement["rate_limit_per_min"] == 1000
            assert replacement["replaces_key_id"] == default_key["key_id"]
            async with AsyncSessionLocal() as db:
                previous = await db.get(ApiKey, UUID(default_key["key_id"]))
                current = await db.get(ApiKey, UUID(replacement["key_id"]))
                assert previous is not None and not previous.is_active
                assert current is not None and current.is_active
                assert current.scopes == "read,write"
                assert current.rate_limit_per_min == 1000

            preserve_response = await client.post(f"/api/v1/developer/keys/{replacement['key_id']}/rotate", json={})
            assert preserve_response.status_code == 201, preserve_response.text
            assert preserve_response.json()["scopes"] == "read,write"
            assert preserve_response.json()["rate_limit_per_min"] == 1000

            resources_response = await client.get("/api/v1/developer/resources")
            assert resources_response.status_code == 200
            resources = resources_response.json()
            assert resources["authentication"]["method"] == "HttpOnly session cookie (JWT)"
            assert f"{settings.AUTH_COOKIE_NAME}=<session>" in resources["authentication"]["header"]
            assert "not enabled" in resources["authentication"]["api_key_note"]
            assert resources["rate_limits"]["minimum"] == 1
            assert resources["rate_limits"]["maximum"] == 1000
            assert resources["rate_limits"]["window"] == "60 seconds"
            assert "not enforced" in resources["rate_limits"]["enforcement"]
            assert "GET/HEAD" in resources["api_key_scopes"]["read"]
            assert "POST/PUT/PATCH/DELETE" in resources["api_key_scopes"]["write"]
            assert "not currently enforced" in resources["api_key_scopes"]["admin"]

            dashboard_response = await client.get("/api/v1/developer/dashboard")
            assert dashboard_response.status_code == 200
            dashboard = dashboard_response.json()
            assert dashboard["available_scopes"] == ["read", "write", "admin"]
            assert dashboard["default_rate_limit"] == 60
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await _delete_users(owner.id)
