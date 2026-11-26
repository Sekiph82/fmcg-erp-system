"""M48.S01.T013 (remediates M37.S03.T002): the mobile admin endpoints refuse everyone except administrators.

GET /mobile/kpis, GET /mobile/devices/stats and POST /mobile/push/send need users.edit, company.edit or
integrations.edit (or their `_all` grant). Every seeded role from ROLE_DEFINITIONS is built in a disposable
PostgreSQL and called through the real app with a real session cookie: roles holding one of those rights get 200,
every other role gets 403, and no cookie gets 401. The endpoints count devices/approvals system-wide and have no
company scope (MobilePushToken has no company column), so there is no per-company isolation to test.
Needs M48_DB=1 and DATABASE_URL pointing at a disposable database.
"""
import os
import random
import uuid

import httpx
import pytest
from sqlalchemy import select

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
ADMIN_RIGHTS = ("users.edit", "company.edit", "integrations.edit")
CALLS = (("GET", "/api/v1/mobile/kpis", None), ("GET", "/api/v1/mobile/devices/stats", None),
         ("POST", "/api/v1/mobile/push/send", {"user_ids": [], "title": "POVU stock alert", "body": "POVU AllClean 1 L low"}))


@pytest.fixture(autouse=True)
async def _dispose_engine(monkeypatch):
    from app.core import token_blocklist
    monkeypatch.setattr(token_blocklist, "_get_redis", lambda: None)     # in-memory blocklist: never the dev Redis
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client(cookies=None):
    from app.main import app
    ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 50000)), base_url="http://erp.test",
                             cookies=cookies)


def _expected_allowed(codes: set[str]) -> bool:
    return any(c in codes or f"{c}_all" in codes for c in ADMIN_RIGHTS)


async def _role_users(db, tag):
    """One active user per seeded role (2FA enrolled so privileged roles pass the login policy)."""
    from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS
    from app.models.role import Permission, Role
    from app.models.two_factor import TwoFAMethod, User2FASettings
    from app.models.user import User

    every = sorted({f"{p[0]}.{p[1]}" for p in PERMISSIONS})
    wanted = set(every) | {c for d in ROLE_DEFINITIONS.values() if d["permissions"] != "*" for c in d["permissions"]}
    have = {p.code: p for p in (await db.execute(select(Permission).where(Permission.code.in_(wanted)))).scalars()}
    for code in wanted - set(have):
        mod, act = code.split(".", 1)
        have[code] = Permission(code=code, name=code, module=mod, action=act, is_active=True)
        db.add(have[code])
    await db.flush()
    out = []
    for name, d in ROLE_DEFINITIONS.items():
        codes = set(every) if d["permissions"] == "*" else set(d["permissions"])
        role = Role(name=f"{name}-{tag}", is_active=True, permissions=[have[c] for c in sorted(codes)])
        u = User(username=f"m48mob-{name}-{tag}", email=f"m48mob-{name}-{tag}@povu-demo.test", full_name=f"POVU {name}",
                 hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False, roles=[role])
        db.add(u)
        await db.flush()
        db.add(User2FASettings(user_id=u.id, is_enabled=True, method=TwoFAMethod.TOTP, secret_key="JBSWY3DPEHPK3PXP"))
        out.append((name, u, _expected_allowed(codes)))
    return out


async def _call(c, method, path, body):
    return await (c.post(path, json=body) if method == "POST" else c.get(path))


@DB
@pytest.mark.asyncio
async def test_mobile_admin_endpoints_by_role():
    from app.core.config import settings
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionLocal, engine

    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.port != 5432, "never the dev database"
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        people = await _role_users(db, tag)
        await db.commit()
        tokens = {name: create_access_token(str(u.id), session_version=u.auth_session_version or 0) for name, u, _ in people}
    allowed = sorted(n for n, _, ok in people if ok)
    denied = sorted(n for n, _, ok in people if not ok)
    assert "owner" in allowed and "admin" in allowed and len(denied) >= 30, (allowed, denied)

    async with _client() as anon:                                         # no session at all
        for method, path, body in CALLS:
            assert (await _call(anon, method, path, body)).status_code == 401, path

    seen = {}
    for name, _, ok in people:
        async with _client({settings.AUTH_COOKIE_NAME: tokens[name]}) as c:
            for method, path, body in CALLS:
                r = await _call(c, method, path, body)
                seen[(name, path)] = r.status_code
                assert r.status_code == (200 if ok else 403), (name, path, r.status_code, r.text[:200])
                if ok and path.endswith("/push/send"):
                    assert r.json()["sent"] == 0                          # no recipients → nothing sent, no egress
                if ok and path.endswith("/devices/stats"):
                    assert {"total_active_devices", "total_registered_ever", "by_platform"} <= set(r.json())
    assert len(seen) == 3 * len(people)
