"""M31.S01.T002 credential lifecycle checks; gated to an owned disposable PostgreSQL database."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.api_portal import ApiClientApplication, ApiKey, ApiOAuthClientSecret
from app.models.user import User


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s01_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S01_T002_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M31_S01_T002_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M31_S01_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration reads/writes: DATABASE_URL must match the exact loopback M31.S01.T002 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m31_s01_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t001_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t002_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user: User, *, permissions: tuple[str, ...] = ()):
    role_permissions = [SimpleNamespace(is_active=True, code=code) for code in permissions]
    roles = [SimpleNamespace(is_active=True, permissions=role_permissions)] if role_permissions else []
    return SimpleNamespace(id=user.id, is_superuser=False, roles=roles, access_scopes=[])


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
        key_ids = select(ApiKey.key_id).where(ApiKey.user_id.in_([str(user_id) for user_id in user_ids]))
        await db.execute(delete(ApiKey).where(ApiKey.key_id.in_(key_ids)))
        await db.execute(delete(ApiClientApplication).where(ApiClientApplication.owner_user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_api_key_and_oauth_client_secret_lifecycle_is_owner_scoped_and_hash_only():
    _require_task_owned_database()
    owner = await _new_user(f"m31-credential-owner-{uuid4().hex}@example.invalid")
    other = await _new_user(f"m31-credential-other-{uuid4().hex}@example.invalid")
    viewer = await _new_user(f"m31-credential-viewer-{uuid4().hex}@example.invalid")

    async def override_db():
        async with AsyncSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(
        owner, permissions=("integrations.view", "integrations.edit")
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            app_response = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Credential lifecycle fixture", "environment": "sandbox"},
            )
            assert app_response.status_code == 201, app_response.text
            application_id = app_response.json()["client_id"]

            race_app_response = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Concurrent disable fixture", "environment": "development"},
            )
            assert race_app_response.status_code == 201
            race_application_id = UUID(race_app_response.json()["client_id"])
            race_key_response = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": str(race_application_id), "key_name": "Concurrent rotation fixture"},
            )
            assert race_key_response.status_code == 201
            race_key_id = UUID(race_key_response.json()["key_id"])
            async with AsyncSessionLocal() as locked_db:
                race_application = await locked_db.scalar(
                    select(ApiClientApplication)
                    .where(ApiClientApplication.client_id == race_application_id)
                    .with_for_update()
                )
                assert race_application is not None
                pending_rotation = asyncio.create_task(
                    client.post(f"/api/v1/developer/keys/{race_key_id}/rotate", json={})
                )
                await asyncio.sleep(0.2)
                race_application.is_active = False
                race_key = await locked_db.get(ApiKey, race_key_id)
                assert race_key is not None
                race_key.is_active = False
                await locked_db.commit()
                race_rotation_response = await pending_rotation
                assert race_rotation_response.status_code == 409
            async with AsyncSessionLocal() as db:
                assert await db.scalar(
                    select(ApiKey.key_id).where(
                        ApiKey.application_id == race_application_id,
                        ApiKey.is_active.is_(True),
                    )
                ) is None

            key_response = await client.post(
                "/api/v1/developer/keys",
                json={
                    "application_id": application_id,
                    "key_name": "Fixture API key",
                    "scopes": "read",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                },
            )
            assert key_response.status_code == 201, key_response.text
            key_data = key_response.json()
            raw_key = key_data["raw_key"]
            assert key_data["application_id"] == application_id
            assert key_data["key_prefix"] == raw_key[:12]
            assert key_data["expires_at"].endswith("+00:00")
            assert "key_hash" not in key_data
            assert "replaces_key_id" not in key_data

            async with AsyncSessionLocal() as db:
                first_key = await db.get(ApiKey, UUID(key_data["key_id"]))
                assert first_key is not None
                assert first_key.key_hash != raw_key
                assert first_key.key_hash == hashlib.sha256(raw_key.encode()).hexdigest()
                assert raw_key not in first_key.key_hash

            keys_response = await client.get("/api/v1/developer/keys?include_inactive=true")
            assert keys_response.status_code == 200
            assert raw_key not in keys_response.text
            assert "key_hash" not in keys_response.text

            rotated_key_response = await client.post(f"/api/v1/developer/keys/{key_data['key_id']}/rotate", json={})
            assert rotated_key_response.status_code == 201, rotated_key_response.text
            rotated_key = rotated_key_response.json()
            assert rotated_key["raw_key"] != raw_key
            assert rotated_key["replaces_key_id"] == key_data["key_id"]
            assert rotated_key["expires_at"].endswith("+00:00")
            async with AsyncSessionLocal() as db:
                previous = await db.get(ApiKey, UUID(key_data["key_id"]))
                replacement = await db.get(ApiKey, UUID(rotated_key["key_id"]))
                assert previous is not None and previous.is_active is False
                assert replacement is not None and replacement.is_active is True
                assert replacement.application_id == previous.application_id
                assert replacement.scopes == previous.scopes
                assert replacement.key_hash == hashlib.sha256(rotated_key["raw_key"].encode()).hexdigest()

            bad_expiry = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Expired", "expires_at": "2000-01-01T00:00:00Z"},
            )
            assert bad_expiry.status_code == 422

            bad_oauth_expiry = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Expired", "expires_at": "2000-01-01T00:00:00Z"},
            )
            assert bad_oauth_expiry.status_code == 422

            oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Fixture OAuth client secret"},
            )
            assert oauth_response.status_code == 201, oauth_response.text
            oauth = oauth_response.json()
            assert oauth["client_id"] == application_id
            assert oauth["secret_prefix"] == oauth["client_secret"][:16]
            assert "secret_hash" not in oauth
            assert "token" not in oauth
            async with AsyncSessionLocal() as db:
                stored_secret = await db.get(ApiOAuthClientSecret, UUID(oauth["secret_id"]))
                assert stored_secret is not None
                assert stored_secret.secret_hash != oauth["client_secret"]
                assert stored_secret.secret_hash == hashlib.sha256(oauth["client_secret"].encode()).hexdigest()

            oauth_list = await client.get(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets?include_inactive=true"
            )
            assert oauth_list.status_code == 200
            assert oauth["client_secret"] not in oauth_list.text
            assert "secret_hash" not in oauth_list.text

            rotated_oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets/{oauth['secret_id']}/rotate",
                json={},
            )
            assert rotated_oauth_response.status_code == 201, rotated_oauth_response.text
            rotated_oauth = rotated_oauth_response.json()
            assert rotated_oauth["client_secret"] != oauth["client_secret"]
            assert rotated_oauth["replaces_secret_id"] == oauth["secret_id"]
            async with AsyncSessionLocal() as db:
                previous_secret = await db.get(ApiOAuthClientSecret, UUID(oauth["secret_id"]))
                replacement_secret = await db.get(ApiOAuthClientSecret, UUID(rotated_oauth["secret_id"]))
                assert previous_secret is not None and previous_secret.is_active is False
                assert replacement_secret is not None and replacement_secret.is_active is True

            revoked_oauth = await client.delete(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets/{rotated_oauth['secret_id']}"
            )
            assert revoked_oauth.status_code == 204
            async with AsyncSessionLocal() as db:
                revoked_secret = await db.get(ApiOAuthClientSecret, UUID(rotated_oauth["secret_id"]))
                assert revoked_secret is not None and revoked_secret.is_active is False

            third_oauth_response = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Deactivate with application"},
            )
            assert third_oauth_response.status_code == 201

            wrong_owner_secret_list = await client.get(
                f"/api/v1/developer/applications/{uuid4()}/oauth-secrets"
            )
            assert wrong_owner_secret_list.status_code == 404

            app.dependency_overrides[get_current_user] = lambda: _actor(
                other, permissions=("integrations.view", "integrations.edit")
            )
            assert (await client.get("/api/v1/developer/keys?include_inactive=true")).json() == []
            cross_owner_key = await client.post(
                "/api/v1/developer/keys",
                json={"application_id": application_id, "key_name": "Cross owner"},
            )
            assert cross_owner_key.status_code == 404
            assert (await client.delete(f"/api/v1/developer/keys/{rotated_key['key_id']}")).status_code == 404
            assert (await client.get(f"/api/v1/developer/applications/{application_id}/oauth-secrets")).status_code == 404

            app.dependency_overrides[get_current_user] = lambda: _actor(viewer, permissions=("integrations.view",))
            assert (await client.get("/api/v1/developer/keys")).status_code == 200
            assert (await client.post(
                "/api/v1/developer/keys", json={"application_id": application_id, "key_name": "Viewer denied"}
            )).status_code == 403
            assert (await client.delete(f"/api/v1/developer/keys/{rotated_key['key_id']}")).status_code == 403
            assert (await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Viewer denied"},
            )).status_code == 403

            app.dependency_overrides[get_current_user] = lambda: _actor(
                owner, permissions=("integrations.view", "integrations.edit")
            )
            deactivated = await client.patch(
                f"/api/v1/developer/applications/{application_id}", json={"is_active": False}
            )
            assert deactivated.status_code == 200
            inactive_key_rotation = await client.post(
                f"/api/v1/developer/keys/{rotated_key['key_id']}/rotate", json={}
            )
            assert inactive_key_rotation.status_code == 409
            async with AsyncSessionLocal() as db:
                active_keys = await db.scalar(
                    select(ApiKey.key_id).where(ApiKey.application_id == application_id, ApiKey.is_active.is_(True))
                )
                active_secrets = await db.scalar(
                    select(ApiOAuthClientSecret.secret_id).where(
                        ApiOAuthClientSecret.application_id == application_id,
                        ApiOAuthClientSecret.is_active.is_(True),
                    )
                )
                assert active_keys is None
                assert active_secrets is None
            inactive_issue = await client.post(
                f"/api/v1/developer/applications/{application_id}/oauth-secrets",
                json={"secret_name": "Cannot issue"},
            )
            assert inactive_issue.status_code == 409

            downgrade = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20261029_0042"],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            downgrade_output = f"{downgrade.stdout}\n{downgrade.stderr}"
            assert downgrade.returncode != 0
            assert "credential record(s) would be lost" in downgrade_output
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await _delete_users(owner.id, other.id, viewer.id)
