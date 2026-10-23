"""Authentication transaction isolation and negative regression coverage."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Permission, Role


@pytest.mark.asyncio
async def test_auth_isolated_from_endpoint_commit_and_explicit_transaction():
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 auth transaction regression requires PostgreSQL")

    suffix = uuid4().hex[:12]
    email = f"m20-auth-boundary-{suffix}@example.invalid"
    username = f"m20-auth-boundary-{suffix}"
    denied_email = f"m20-auth-denied-{suffix}@example.invalid"
    denied_username = f"m20-auth-denied-{suffix}"
    staged_email = f"m20-auth-staged-{suffix}@example.invalid"

    async with AsyncSessionLocal() as setup:
        user = User(
            email=email,
            username=username,
            full_name="M20 auth boundary",
            hashed_password="test-only",
            is_active=True,
            is_superuser=False,
        )
        denied_user = User(
            email=denied_email,
            username=denied_username,
            full_name="M20 auth denied",
            hashed_password="test-only",
            is_active=True,
        )
        setup.add_all([user, denied_user])
        permissions = []
        for code, module in (("mps.view", "mps"), ("warehouses.view", "warehouses")):
            permission = await setup.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(
                    code=code,
                    name=f"View {module.title()}",
                    module=module,
                    action="view",
                    is_active=True,
                )
            permissions.append(permission)
        user.roles.append(Role(
            name=f"m20-auth-boundary-{suffix}",
            is_active=True,
            permissions=permissions,
        ))
        await setup.commit()
        user_id = user.id
        denied_user_id = denied_user.id

    app = FastAPI()
    from app.api.v1.endpoints.mps import router as mps_router
    from app.api.v1.endpoints.warehouses import router as warehouses_router

    app.include_router(mps_router, prefix="/api/v1/mps")
    app.include_router(warehouses_router, prefix="/api/v1/warehouses")

    async def stage_uncommitted_business_write(db: AsyncSession = Depends(get_db)):
        db.add(User(
            email=staged_email,
            username=f"m20-auth-staged-{suffix}",
            full_name="Must remain uncommitted",
            hashed_password="test-only",
            is_active=True,
        ))
        await db.flush()

    @app.get("/explicit-transaction")
    async def explicit_transaction(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        async with db.begin():
            await db.execute(text("SELECT 1"))
        return {"user_id": str(current_user.id)}

    @app.get("/staged-write")
    async def staged_write(
        _=Depends(stage_uncommitted_business_write),
        current_user: User = Depends(get_current_user),
    ):
        assert current_user.id == user_id
        raise HTTPException(status_code=409, detail="intentional rollback probe")

    token = create_access_token(str(user_id))
    cookie = {settings.AUTH_COOKIE_NAME: token}
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://m20-auth.test",
        cookies=cookie,
    ) as client:
        valid = await client.get("/explicit-transaction")
        assert valid.status_code == 200, valid.text
        assert valid.json() == {"user_id": str(user_id)}

        # These real ERP handlers share one endpoint DB session with auth.
        # MPS explicitly begins its transaction; warehouses exercise the
        # unrelated conventional request-session/query path.
        mps = await client.get("/api/v1/mps/plans")
        assert mps.status_code == 200, mps.text
        warehouses = await client.get("/api/v1/warehouses/")
        assert warehouses.status_code == 200, warehouses.text

        invalid = await client.get(
            "/explicit-transaction",
            cookies={settings.AUTH_COOKIE_NAME: "not-a-valid-token"},
        )
        assert invalid.status_code == 401

        denied = await client.get(
            "/api/v1/mps/plans",
            cookies={settings.AUTH_COOKIE_NAME: create_access_token(str(denied_user_id))},
        )
        assert denied.status_code == 403, denied.text

        staged = await client.get("/staged-write")
        assert staged.status_code == 409, staged.text

    async with AsyncSessionLocal() as verify:
        assert await verify.scalar(select(User.id).where(User.email == staged_email)) is None, (
            "auth must not commit writes staged by an earlier endpoint dependency"
        )
        persisted = await verify.scalar(select(User.id).where(User.email == email))
        assert persisted == user_id
        await verify.delete(await verify.get(User, user_id))
        await verify.delete(await verify.get(User, denied_user_id))
        await verify.commit()
