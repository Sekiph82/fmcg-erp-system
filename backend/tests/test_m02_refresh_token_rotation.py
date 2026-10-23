"""Refresh-session rotation, replay revocation, and logout integration tests."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
import pyotp
from sqlalchemy import delete, select, update
from sqlalchemy.engine import URL

from app.api.v1.endpoints.auth import router as auth_router
from app.core.config import settings
from app.core.deps import get_auth_db, get_current_user, get_db
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog, AuditEvent
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.user import User
from app.models.two_factor import TwoFAMethod, User2FASettings
from app.services.auth_refresh_tokens import issue_auth_token_pair, touch_refresh_family_activity
from app.api.v1.endpoints.two_factor import router as two_factor_router


def _is_task_owned_disposable_m02_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m02_t00[123]_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_disposable_postgres() -> None:
    if os.environ.get("M02_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M02_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    expected_name = os.environ.get("M02_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_disposable_m02_database(engine.url, expected_name):
        pytest.fail(
            "Refusing M02 integration writes: DATABASE_URL must target the exact loopback PostgreSQL database "
            "named by M02_DISPOSABLE_TEST_DATABASE_NAME (fmcg_m02_t001_, t002_, or t003_ followed by 20-32 hex chars)."
        )


def test_disposable_database_guard_requires_exact_unique_loopback_target():
    name = "fmcg_m02_t001_0123456789abcdef0123"
    t003_name = "fmcg_m02_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="test", host="127.0.0.1", database=name)
    assert _is_task_owned_disposable_m02_database(safe, name)
    t003_safe = URL.create("postgresql+asyncpg", username="test", host="127.0.0.1", database=t003_name)
    assert _is_task_owned_disposable_m02_database(t003_safe, t003_name)
    assert not _is_task_owned_disposable_m02_database(safe, "fmcg_m02_t001_0123456789abcdef0124")
    assert not _is_task_owned_disposable_m02_database(safe, "fmcg_m02_t001_short")
    assert not _is_task_owned_disposable_m02_database(
        URL.create("postgresql+asyncpg", host="db.example.com", database=name), name
    )
    assert not _is_task_owned_disposable_m02_database(
        URL.create("sqlite+aiosqlite", database=name), name
    )


async def _override_db():
    async with AsyncSessionLocal() as session:
        yield session


async def _override_auth_db():
    async with AsyncSessionLocal() as session:
        yield session


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(two_factor_router, prefix="/api/v1/auth/2fa")
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_auth_db] = _override_auth_db

    @app.get("/protected")
    async def protected(current_user=Depends(get_current_user)):
        return {"user_id": str(current_user.id)}

    @app.get("/protected-staged-write")
    async def protected_staged_write(
        db=Depends(get_db),
        current_user=Depends(get_current_user),
    ):
        staged_email = f"m02-staged-{uuid4().hex}@example.invalid"
        db.add(User(
            email=staged_email,
            username=f"m02-staged-{uuid4().hex}",
            full_name="Must remain uncommitted",
            hashed_password="test-only",
            is_active=True,
        ))
        await db.flush()
        raise HTTPException(status_code=409, detail=staged_email)

    return app


async def _create_user() -> User:
    suffix = uuid4().hex
    user = User(
        email=f"m02-refresh-{suffix}@example.invalid",
        username=f"m02-refresh-{suffix}",
        full_name="M02 refresh-token test",
        hashed_password=hash_password("M02-Refresh-Test-Password9!"),
        is_active=True,
        is_superuser=True,
    )
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def _delete_user(user_id) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _set_family_activity(family_id, timestamp: datetime) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(AuthRefreshToken)
            .where(AuthRefreshToken.family_id == family_id)
            .values(last_activity_at=timestamp)
        )
        await db.commit()


@pytest.mark.asyncio
async def test_login_rotation_and_replay_revoke_the_session_family():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                data={"username": user.username, "password": "M02-Refresh-Test-Password9!"},
            )
            assert login.status_code == 200, login.text
            assert login.json()["access_token"] is None
            first_refresh = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
            first_access = client.cookies.get(settings.AUTH_COOKIE_NAME)
            assert first_refresh and first_access
            assert f"{settings.REFRESH_TOKEN_COOKIE_NAME}=" in login.headers.get("set-cookie", "")
            assert "httponly" in login.headers.get("set-cookie", "").lower()

            async with AsyncSessionLocal() as db:
                first_row = await db.scalar(select(AuthRefreshToken).where(
                    AuthRefreshToken.user_id == user.id,
                ))
                assert first_row is not None
                assert first_row.token_hash != first_refresh
                assert len(first_row.token_hash) == 64
                family_id = first_row.family_id

            protected = await client.get("/protected")
            assert protected.status_code == 200, protected.text

            rotated = await client.post("/api/v1/auth/refresh")
            assert rotated.status_code == 200, rotated.text
            second_refresh = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
            second_access = client.cookies.get(settings.AUTH_COOKIE_NAME)
            assert second_refresh and second_refresh != first_refresh
            assert second_access and second_access != first_access
            assert rotated.json()["access_token"] is None

            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies={settings.REFRESH_TOKEN_COOKIE_NAME: first_refresh},
            ) as replay_client:
                old_token_reuse = await replay_client.post("/api/v1/auth/refresh")
            assert old_token_reuse.status_code == 401

            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies={settings.AUTH_COOKIE_NAME: second_access},
            ) as family_client:
                family_access = await family_client.get("/protected")
            assert family_access.status_code == 401

        async with AsyncSessionLocal() as db:
            family_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == family_id,
            ))).all()
            assert len(family_rows) == 2
            assert family_rows[0].expires_at == family_rows[1].expires_at
            assert all(row.revoked_at is not None for row in family_rows)
            assert any(row.consumed_at is not None and row.replaced_by_id is not None for row in family_rows)
            replay_event = await db.scalar(select(AuditLog.id).where(
                AuditLog.event_type == AuditEvent.REFRESH_TOKEN_REUSE_DETECTED,
                AuditLog.target_id == str(family_id),
            ))
            assert replay_event is not None
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected_and_clears_auth_cookies():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()
        row = await db.scalar(select(AuthRefreshToken).where(
            AuthRefreshToken.family_id == pair.family_id,
        ))
        row.expires_at = row.expires_at - timedelta(days=8)
        await db.commit()

    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.REFRESH_TOKEN_COOKIE_NAME: pair.refresh_token},
        ) as client:
            response = await client.post("/api/v1/auth/refresh")
            assert response.status_code == 401
            set_cookie = response.headers.get("set-cookie", "").lower()
            assert settings.AUTH_COOKIE_NAME.lower() in set_cookie
            assert settings.REFRESH_TOKEN_COOKIE_NAME.lower() in set_cookie
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_two_factor_login_issues_refresh_only_after_successful_verification():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    secret = pyotp.random_base32()
    async with AsyncSessionLocal() as db:
        db.add(User2FASettings(
            user_id=user.id,
            is_enabled=True,
            method=TwoFAMethod.TOTP,
            secret_key=secret,
        ))
        await db.commit()

    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
        ) as client:
            challenge = await client.post(
                "/api/v1/auth/login",
                data={"username": user.username, "password": "M02-Refresh-Test-Password9!"},
            )
            assert challenge.status_code == 200, challenge.text
            assert challenge.json()["two_fa_required"] is True
            assert client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME) is None

            completed = await client.post(
                "/api/v1/auth/2fa/login-verify",
                json={
                    "session_token": challenge.json()["session_token"],
                    "code": pyotp.TOTP(secret).now(),
                },
            )
            assert completed.status_code == 200, completed.text
            assert client.cookies.get(settings.AUTH_COOKIE_NAME)
            assert client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

            async with AsyncSessionLocal() as db:
                refresh_row = await db.scalar(select(AuthRefreshToken).where(
                    AuthRefreshToken.user_id == user.id,
                ))
                assert refresh_row is not None
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_refresh_replay_revokes_the_winning_successor():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    client_app = _app()
    refresh_cookie = {settings.REFRESH_TOKEN_COOKIE_NAME: pair.refresh_token}
    try:
        async def refresh_once():
            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies=refresh_cookie,
            ) as client:
                return await client.post("/api/v1/auth/refresh")

        first, second = await asyncio.gather(refresh_once(), refresh_once())
        assert sorted((first.status_code, second.status_code)) == [200, 401]

        success = first if first.status_code == 200 else second
        winner_access = success.cookies.get(settings.AUTH_COOKIE_NAME)
        assert winner_access
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: winner_access},
        ) as client:
            rejected = await client.get("/protected")
            assert rejected.status_code == 401

        async with AsyncSessionLocal() as db:
            family_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert len(family_rows) == 2
            assert all(row.revoked_at is not None for row in family_rows)
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_replayed_predecessor_serializes_with_successor_rotation():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.REFRESH_TOKEN_COOKIE_NAME: pair.refresh_token},
        ) as initial_client:
            first_rotation = await initial_client.post("/api/v1/auth/refresh")
        assert first_rotation.status_code == 200, first_rotation.text
        successor = first_rotation.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        assert successor

        async def refresh_with(token: str):
            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies={settings.REFRESH_TOKEN_COOKIE_NAME: token},
            ) as client:
                return await client.post("/api/v1/auth/refresh")

        replay_response, successor_response = await asyncio.gather(
            refresh_with(pair.refresh_token),
            refresh_with(successor),
        )
        assert replay_response.status_code == 401, replay_response.text
        assert successor_response.status_code in {200, 401}, successor_response.text

        async with AsyncSessionLocal() as db:
            family_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert len(family_rows) in {2, 3}
            assert all(row.revoked_at is not None for row in family_rows)
            replay_event = await db.scalar(select(AuditLog.id).where(
                AuditLog.event_type == AuditEvent.REFRESH_TOKEN_REUSE_DETECTED,
                AuditLog.target_id == str(pair.family_id),
            ))
            assert replay_event is not None
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_authenticated_request_refreshes_session_activity():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    previous_activity = datetime.now(timezone.utc) - timedelta(minutes=60)
    await _set_family_activity(pair.family_id, previous_activity)
    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: pair.access_token},
        ) as client:
            response = await client.get("/protected")
            assert response.status_code == 200, response.text

        async with AsyncSessionLocal() as db:
            rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert rows
            assert all(row.last_activity_at > previous_activity for row in rows)
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_activity_touch_waiting_on_newer_commit_never_moves_activity_backward():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    newer_activity = datetime.now(timezone.utc) + timedelta(minutes=2)
    try:
        async with AsyncSessionLocal() as lock_db:
            locked_row = await lock_db.scalar(
                select(AuthRefreshToken)
                .where(AuthRefreshToken.family_id == pair.family_id)
                .with_for_update()
            )
            assert locked_row is not None
            touch_started = asyncio.Event()

            async def delayed_touch() -> bool:
                async with AsyncSessionLocal() as activity_db:
                    touch_started.set()
                    return await touch_refresh_family_activity(activity_db, pair.family_id)

            touch_task = asyncio.create_task(delayed_touch())
            await touch_started.wait()
            await asyncio.sleep(0.05)
            assert not touch_task.done(), "activity update should wait behind the locked family row"
            locked_row.last_activity_at = newer_activity
            await lock_db.commit()

        assert await asyncio.wait_for(touch_task, timeout=5)

        async with AsyncSessionLocal() as db:
            rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert rows
            assert all(row.last_activity_at == newer_activity for row in rows)
    finally:
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_activity_commit_does_not_commit_endpoint_business_writes():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: pair.access_token},
        ) as client:
            response = await client.get("/protected-staged-write")
            assert response.status_code == 409
            staged_email = response.json()["detail"]

        async with AsyncSessionLocal() as db:
            assert await db.scalar(select(User.id).where(User.email == staged_email)) is None
            family_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert family_rows and all(row.last_activity_at is not None for row in family_rows)
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_inactive_access_session_is_rejected_revoked_and_audited():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    idle_since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.SESSION_INACTIVITY_TIMEOUT_MINUTES + 1,
    )
    await _set_family_activity(pair.family_id, idle_since)
    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: pair.access_token},
        ) as client:
            response = await client.get("/protected")
            assert response.status_code == 401

        async with AsyncSessionLocal() as db:
            rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert rows and all(row.revoked_at is not None for row in rows)
            event = await db.scalar(select(AuditLog.id).where(
                AuditLog.event_type == AuditEvent.AUTH_SESSION_EXPIRED,
                AuditLog.target_id == str(pair.family_id),
            ))
            assert event is not None
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_inactive_refresh_session_is_rejected_and_revoked():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    idle_since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.SESSION_INACTIVITY_TIMEOUT_MINUTES + 1,
    )
    await _set_family_activity(pair.family_id, idle_since)
    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.REFRESH_TOKEN_COOKIE_NAME: pair.refresh_token},
        ) as client:
            response = await client.post("/api/v1/auth/refresh")
            assert response.status_code == 401

        async with AsyncSessionLocal() as db:
            rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert rows and all(row.revoked_at is not None for row in rows)
            event = await db.scalar(select(AuditLog.id).where(
                AuditLog.event_type == AuditEvent.AUTH_SESSION_EXPIRED,
                AuditLog.target_id == str(pair.family_id),
            ))
            assert event is not None
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_revokes_refresh_family_and_clears_both_cookies(monkeypatch):
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    async with AsyncSessionLocal() as db:
        pair = await issue_auth_token_pair(db, user.id)
        await db.commit()

    from app.core import token_blocklist

    async def no_op_blocklist(_token: str, _expire_at: float) -> None:
        return None

    monkeypatch.setattr(token_blocklist, "add", no_op_blocklist)
    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={
                settings.AUTH_COOKIE_NAME: pair.access_token,
                settings.REFRESH_TOKEN_COOKIE_NAME: pair.refresh_token,
            },
        ) as client:
            response = await client.post("/api/v1/auth/logout")
            assert response.status_code == 200, response.text
            set_cookie = response.headers.get("set-cookie", "").lower()
            assert settings.AUTH_COOKIE_NAME.lower() in set_cookie
            assert settings.REFRESH_TOKEN_COOKIE_NAME.lower() in set_cookie

        async with AsyncSessionLocal() as db:
            family_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.family_id == pair.family_id,
            ))).all()
            assert family_rows and all(row.revoked_at is not None for row in family_rows)
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_all_revokes_every_session_and_allows_a_new_login():
    _require_task_owned_disposable_postgres()
    await engine.dispose()
    user = await _create_user()
    other_user = await _create_user()
    async with AsyncSessionLocal() as db:
        first = await issue_auth_token_pair(db, user.id)
        await db.commit()
    async with AsyncSessionLocal() as db:
        second = await issue_auth_token_pair(db, user.id)
        await db.commit()
    async with AsyncSessionLocal() as db:
        other_session = await issue_auth_token_pair(db, other_user.id)
        await db.commit()
    legacy_access = create_access_token(str(user.id))

    client_app = _app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: legacy_access},
        ) as legacy_client:
            assert (await legacy_client.get("/protected")).status_code == 200

        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={
                settings.AUTH_COOKIE_NAME: first.access_token,
                settings.REFRESH_TOKEN_COOKIE_NAME: first.refresh_token,
            },
        ) as owner_client:
            response = await owner_client.post("/api/v1/auth/logout-all")
        assert response.status_code == 200, response.text
        assert response.json()["refresh_tokens_revoked"] == 2
        cleared_cookies = response.headers.get("set-cookie", "").lower()
        assert settings.AUTH_COOKIE_NAME.lower() in cleared_cookies
        assert settings.REFRESH_TOKEN_COOKIE_NAME.lower() in cleared_cookies

        for access_token in (first.access_token, second.access_token, legacy_access):
            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies={settings.AUTH_COOKIE_NAME: access_token},
            ) as client:
                assert (await client.get("/protected")).status_code == 401

        for refresh_token in (first.refresh_token, second.refresh_token):
            async with AsyncClient(
                transport=ASGITransport(app=client_app),
                base_url="http://m02-auth.test",
                cookies={settings.REFRESH_TOKEN_COOKIE_NAME: refresh_token},
            ) as client:
                assert (await client.post("/api/v1/auth/refresh")).status_code == 401

        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: other_session.access_token},
        ) as other_access_client:
            assert (await other_access_client.get("/protected")).status_code == 200
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.REFRESH_TOKEN_COOKIE_NAME: other_session.refresh_token},
        ) as other_refresh_client:
            assert (await other_refresh_client.post("/api/v1/auth/refresh")).status_code == 200

        async with AsyncSessionLocal() as db:
            stored_user = await db.get(User, user.id)
            assert stored_user is not None and stored_user.auth_session_version == 1
            revoked_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.user_id == user.id,
            ))).all()
            assert len(revoked_rows) == 2
            assert all(row.revoked_at is not None for row in revoked_rows)
            event = await db.scalar(select(AuditLog.id).where(
                AuditLog.event_type == AuditEvent.AUTH_SESSIONS_REVOKED,
                AuditLog.target_id == str(user.id),
            ))
            assert event is not None
            other_rows = (await db.scalars(select(AuthRefreshToken).where(
                AuthRefreshToken.user_id == other_user.id,
            ))).all()
            assert len(other_rows) == 2
            assert all(row.revoked_at is None for row in other_rows)

        async with AsyncSessionLocal() as db:
            new_session = await issue_auth_token_pair(db, user.id)
            await db.commit()
        async with AsyncClient(
            transport=ASGITransport(app=client_app),
            base_url="http://m02-auth.test",
            cookies={settings.AUTH_COOKIE_NAME: new_session.access_token},
        ) as new_session_client:
            assert (await new_session_client.get("/protected")).status_code == 200
    finally:
        client_app.dependency_overrides.clear()
        await _delete_user(user.id)
        await _delete_user(other_user.id)
        await engine.dispose()
