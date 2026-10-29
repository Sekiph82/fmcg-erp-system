"""M31.S01.T001 API client registry integration checks."""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.api_portal import ApiClientApplication, ApiKey
from app.models.user import User


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s01_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S01_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M31_S01_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M31_S01_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration reads/writes: DATABASE_URL must match the exact loopback M31.S01.T001 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m31_s01_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m31_s01_t001_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user: User, *, permissions: tuple[str, ...] = ()):
    role_permissions = [SimpleNamespace(is_active=True, code=code) for code in permissions]
    roles = [SimpleNamespace(is_active=True, permissions=role_permissions)] if role_permissions else []
    return SimpleNamespace(id=user.id, is_superuser=False, roles=roles, access_scopes=[])


async def _new_user(email: str, *, superuser: bool = True) -> User:
    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(),
            email=email,
            username=email,
            full_name=email,
            hashed_password="test-only-not-a-real-credential",
            is_active=True,
            is_superuser=superuser,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _delete_users(*user_ids) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(ApiClientApplication).where(ApiClientApplication.owner_user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_registry_crud_is_owner_scoped_and_does_not_create_credentials():
    _require_task_owned_database()
    owner = await _new_user(f"m31-owner-{uuid4().hex}@example.invalid", superuser=False)
    other = await _new_user(f"m31-other-{uuid4().hex}@example.invalid", superuser=False)
    viewer = await _new_user(f"m31-viewer-{uuid4().hex}@example.invalid", superuser=False)
    async with AsyncSessionLocal() as db:
        existing_key_count = await db.scalar(select(func.count()).select_from(ApiKey))

    async def override_db():
        async with AsyncSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(
        owner, permissions=("integrations.view", "integrations.edit")
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created_response = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Synthetic planning client", "description": "Test registry entry", "environment": "sandbox"},
            )
            assert created_response.status_code == 201, created_response.text
            created = created_response.json()
            assert created["name"] == "Synthetic planning client"
            assert created["environment"] == "sandbox"
            assert created["is_active"] is True
            assert "owner_user_id" not in created
            assert "raw_key" not in created
            client_id = created["client_id"]

            duplicate = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Synthetic planning client", "environment": "sandbox"},
            )
            assert duplicate.status_code == 409

            invalid_environment = await client.post(
                "/api/v1/developer/applications",
                json={"name": "Invalid", "environment": "live"},
            )
            assert invalid_environment.status_code == 422

            updated_response = await client.patch(
                f"/api/v1/developer/applications/{client_id}",
                json={"name": "Updated planning client", "environment": "development", "description": None},
            )
            assert updated_response.status_code == 200, updated_response.text
            assert updated_response.json()["name"] == "Updated planning client"
            assert updated_response.json()["environment"] == "development"
            assert updated_response.json()["description"] is None

            deactivated = await client.patch(
                f"/api/v1/developer/applications/{client_id}", json={"is_active": False}
            )
            assert deactivated.status_code == 200
            assert deactivated.json()["is_active"] is False
            assert (await client.get("/api/v1/developer/applications")).json() == []
            assert len((await client.get("/api/v1/developer/applications?include_inactive=true")).json()) == 1

            app.dependency_overrides[get_current_user] = lambda: _actor(
                other, permissions=("integrations.view", "integrations.edit")
            )
            assert (await client.get("/api/v1/developer/applications?include_inactive=true")).json() == []
            concealed = await client.patch(
                f"/api/v1/developer/applications/{client_id}", json={"name": "Cross-owner"}
            )
            assert concealed.status_code == 404

            app.dependency_overrides[get_current_user] = lambda: _actor(
                viewer, permissions=("integrations.view",)
            )
            view_allowed = await client.get("/api/v1/developer/applications")
            assert view_allowed.status_code == 200
            assert view_allowed.json() == []
            denied_create = await client.post(
                "/api/v1/developer/applications", json={"name": "Not allowed"}
            )
            assert denied_create.status_code == 403

        backend_directory = Path(__file__).resolve().parents[1]
        downgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "20261029_0041"],
            cwd=backend_directory,
            capture_output=True,
            text=True,
            check=False,
        )
        downgrade_output = f"{downgrade.stdout}\n{downgrade.stderr}"
        assert downgrade.returncode != 0
        assert "application record(s) would be lost" in downgrade_output
        async with AsyncSessionLocal() as db:
            remaining = await db.scalar(select(func.count()).select_from(ApiClientApplication))
            assert remaining == 1

        async with AsyncSessionLocal() as db:
            assert await db.scalar(select(func.count()).select_from(ApiKey)) == existing_key_count
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await _delete_users(owner.id, other.id, viewer.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_registry_migration_creates_owner_foreign_key_and_unique_environment_key():
    _require_task_owned_database()
    async with engine.connect() as connection:
        table_names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
        assert "api_client_applications" in table_names
        foreign_keys = await connection.run_sync(
            lambda sync: inspect(sync).get_foreign_keys("api_client_applications")
        )
        assert any(
            item["constrained_columns"] == ["owner_user_id"]
            and item["referred_table"] == "users"
            and (item.get("options") or {}).get("ondelete", "").upper() == "CASCADE"
            for item in foreign_keys
        )
        constraints = await connection.run_sync(
            lambda sync: inspect(sync).get_unique_constraints("api_client_applications")
        )
        assert any(
            item.get("name") == "uq_api_client_applications_owner_name_environment"
            and item.get("column_names") == ["owner_user_id", "name", "environment"]
            for item in constraints
        )
        check_constraints = await connection.run_sync(
            lambda sync: inspect(sync).get_check_constraints("api_client_applications")
        )
        assert any(
            item.get("name") == "ck_api_client_applications_environment"
            for item in check_constraints
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_exclusive_registry_lock_blocks_registration_until_downgrade_decision_finishes():
    _require_task_owned_database()
    owner = await _new_user(f"m31-lock-{uuid4().hex}@example.invalid")
    lock_connection = await engine.connect()
    transaction = await lock_connection.begin()
    writer_task = None
    try:
        await lock_connection.execute(text("LOCK TABLE api_client_applications IN ACCESS EXCLUSIVE MODE"))
        started = asyncio.Event()

        async def register_application():
            async with AsyncSessionLocal() as db:
                db.add(ApiClientApplication(
                    owner_user_id=owner.id,
                    name="Lock serialization probe",
                    environment="development",
                ))
                started.set()
                await db.flush()
                await db.commit()

        writer_task = asyncio.create_task(register_application())
        await asyncio.wait_for(started.wait(), timeout=3)
        await asyncio.sleep(0.1)
        assert not writer_task.done(), "Registration should wait while downgrade holds ACCESS EXCLUSIVE."
        await transaction.rollback()
        await asyncio.wait_for(writer_task, timeout=5)
        writer_task = None
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await lock_connection.close()
        if writer_task is not None:
            writer_task.cancel()
            await asyncio.gather(writer_task, return_exceptions=True)
        await _delete_users(owner.id)
