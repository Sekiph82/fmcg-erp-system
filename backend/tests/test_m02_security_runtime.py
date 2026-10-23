"""Production-like cookie/CORS and company-boundary regression checks."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
from starlette.responses import Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core import token_blocklist
from app.core.auth_cookies import set_auth_cookie
from app.core.config import settings
from app.core.deps import get_auth_db, get_db
from app.db.session import AsyncSessionLocal, engine
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.company import Company, CompanyUserRole, UserCompanyAccess
from app.models.role import Permission, Role
from app.models.user import User
from app.services.auth_refresh_tokens import issue_auth_token_pair


def _require_task_owned_database() -> None:
    expected = os.environ.get("M02_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M02_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M02_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m02_t005_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T005 disposable database.")


@pytest.mark.asyncio
async def test_production_like_cookie_cors_and_company_isolation(monkeypatch):
    _require_task_owned_database()
    suffix = uuid4().hex[:16]
    user_id = None
    role_id = None
    family_id = None
    company_ids: list = []
    created_permission_id = None

    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(token_blocklist, "is_blocked", _not_blocked)

    async with AsyncSessionLocal() as db:
        permission = await db.scalar(select(Permission).where(Permission.code == "company.view"))
        if permission is None:
            permission = Permission(
                code="company.view", name="Company view", module="company", action="view", is_active=True
            )
            db.add(permission)
            await db.flush()
            created_permission_id = permission.id

        role = Role(name=f"m02-runtime-{suffix}", is_active=True, permissions=[permission])
        user = User(
            email=f"m02-runtime-{suffix}@example.invalid",
            username=f"m02-runtime-{suffix}",
            full_name="Synthetic company isolation user",
            hashed_password="test-only-not-used-for-login",
            is_active=True,
            is_superuser=False,
            roles=[role],
        )
        allowed = Company(name=f"Synthetic allowed {suffix}", short_code=f"A{suffix[:10]}")
        denied = Company(name=f"Synthetic denied {suffix}", short_code=f"D{suffix[:10]}")
        db.add_all([user, allowed, denied])
        await db.flush()
        db.add(UserCompanyAccess(user_id=user.id, company_id=allowed.id, role=CompanyUserRole.VIEWER))
        await db.commit()
        user_id, role_id = user.id, role.id
        company_ids = [allowed.id, denied.id]

    try:
        async with AsyncSessionLocal() as auth_db:
            token_pair = await issue_auth_token_pair(auth_db, user_id)
            await auth_db.commit()
            family_id = token_pair.family_id
        await _exercise_production_app(user_id, company_ids, token_pair.access_token)
    finally:
        async with AsyncSessionLocal() as cleanup:
            if family_id is not None:
                await cleanup.execute(
                    delete(AuthRefreshToken).where(AuthRefreshToken.family_id == family_id)
                )
            if user_id is not None:
                await cleanup.execute(delete(UserCompanyAccess).where(UserCompanyAccess.user_id == user_id))
            if company_ids:
                await cleanup.execute(delete(Company).where(Company.id.in_(company_ids)))
            if role_id is not None:
                await cleanup.execute(delete(Role).where(Role.id == role_id))
            if user_id is not None:
                await cleanup.execute(delete(User).where(User.id == user_id))
            if created_permission_id is not None:
                await cleanup.execute(delete(Permission).where(Permission.id == created_permission_id))
            await cleanup.commit()


async def _exercise_production_app(user_id, company_ids, token: str) -> None:
    from app.main import app

    cors = next((item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware"), None)
    assert cors is not None, "Production API must register credentialed CORS middleware"
    allowed_origin = cors.kwargs["allow_origins"][0]
    assert any(item.cls.__name__ == "CSRFOriginMiddleware" for item in app.user_middleware), (
        "Production API must register CSRF origin validation middleware"
    )
    original_overrides = app.dependency_overrides.copy()

    async def get_test_db():
        async with AsyncSessionLocal() as db:
            yield db

    try:
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_auth_db] = get_test_db
        response = Response()
        set_auth_cookie(response, "synthetic-session-token")
        cookie_header = response.headers["set-cookie"].lower()
        assert "httponly" in cookie_header
        assert "secure" in cookie_header
        assert "samesite=lax" in cookie_header

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://127.0.0.1",
            cookies={settings.AUTH_COOKIE_NAME: token},
        ) as client:
            allowed_origin_preflight = await client.options(
                "/api/v1/companies/",
                headers={
                    "Origin": allowed_origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert allowed_origin_preflight.status_code == 200
            assert allowed_origin_preflight.headers["access-control-allow-origin"] == allowed_origin
            assert allowed_origin_preflight.headers["access-control-allow-credentials"] == "true"

            denied_origin_preflight = await client.options(
                "/api/v1/companies/",
                headers={
                    "Origin": "https://attacker.example.invalid",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert denied_origin_preflight.status_code == 400
            assert "access-control-allow-origin" not in denied_origin_preflight.headers

            # A simple cross-site form POST does not require a CORS preflight.
            # Origin validation must reject it before the handler changes state.
            denied_form_post = await client.post(
                f"/api/v1/companies/{company_ids[0]}/set-default",
                headers={"Origin": "https://attacker.example.invalid"},
            )
            assert denied_form_post.status_code == 403, denied_form_post.text
            async with AsyncSessionLocal() as verify:
                access = await verify.scalar(
                    select(UserCompanyAccess).where(
                        UserCompanyAccess.user_id == user_id,
                        UserCompanyAccess.company_id == company_ids[0],
                    )
                )
                assert access is not None and access.is_default is False

            allowed_form_post = await client.post(
                f"/api/v1/companies/{company_ids[0]}/set-default",
                headers={"Origin": allowed_origin},
            )
            assert allowed_form_post.status_code == 200, allowed_form_post.text

            listed = await client.get("/api/v1/companies/", headers={"Origin": allowed_origin})
            assert listed.status_code == 200, listed.text
            assert [row["id"] for row in listed.json()] == [str(company_ids[0])]

            own_company = await client.get(f"/api/v1/companies/{company_ids[0]}")
            assert own_company.status_code == 200, own_company.text
            other_company = await client.get(f"/api/v1/companies/{company_ids[1]}")
            assert other_company.status_code == 403, other_company.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def _not_blocked(_token: str) -> bool:
    return False
