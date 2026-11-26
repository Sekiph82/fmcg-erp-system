"""M45.S01.T016 staff OIDC single sign-on against the local OIDC provider (DB part needs M45_DB=1).

Login through the real endpoints (start → IdP authorize → callback → session cookie works); the state cannot be
replayed; a wrong nonce, audience, signing key or expiry is refused; unknown and disabled users are refused; the
groups claim adds mapped roles; enforced SSO blocks password login except for break-glass; refusals are audited.
"""
import os
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim.oidc_app import ISSUER, create_oidc_app

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture
def idp(monkeypatch):
    app = create_oidc_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _erp():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _sign_in(erp, idp_app, email, tamper=None):
    """Drive the browser redirects: ERP start → IdP authorize (as `email`) → ERP callback. Returns the callback response."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=idp_app), base_url=ISSUER) as idp_c:
        if tamper:
            await idp_c.post("/_control", json={"tamper": tamper})
        r = await erp.get("/api/v1/sso/start")
        assert r.status_code == 302 and r.headers["location"].startswith(f"{ISSUER}/authorize")
        auth = await idp_c.get(r.headers["location"] + "&login_hint=" + email)
        q = parse_qs(urlparse(auth.headers["location"]).query)
    return await erp.get("/api/v1/sso/callback", params={"code": q["code"][0], "state": q["state"][0]}), q


@DB
@pytest.mark.asyncio
async def test_oidc_login_and_refusals(idp):
    from sqlalchemy import func, select
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.identity import SSOConfig
    from app.models.role import Role
    from app.models.user import User
    from app.services import sso_service as sso
    pw = uuid.uuid4().hex + "Aa1!"
    async with AsyncSessionLocal() as db:
        role = Role(name=f"SSO sales {uuid.uuid4().hex[:4]}", is_active=True)
        alice = User(username=f"alice-{uuid.uuid4().hex[:6]}", email=f"alice{uuid.uuid4().hex[:4]}@povu-demo.test", full_name="Alice",
                     hashed_password=hash_password(pw), is_active=True)
        off = User(username=f"off-{uuid.uuid4().hex[:6]}", email=f"off{uuid.uuid4().hex[:4]}@povu-demo.test", full_name="Off",
                   hashed_password=hash_password(pw), is_active=False)
        glass = User(username=f"glass-{uuid.uuid4().hex[:6]}", email=f"glass{uuid.uuid4().hex[:4]}@povu-demo.test", full_name="Glass",
                     hashed_password=hash_password(pw), is_active=True)
        for cfg in (await db.execute(select(SSOConfig))).scalars():
            cfg.active = False
        db.add_all([role, alice, off, glass, SSOConfig(name="Local IdP", issuer=ISSUER, client_id="erp-client",
                                                         client_secret=sso.encrypt("sim-secret"), role_mapping={"erp-sales": role.name},
                                                         break_glass=[glass.username], active=True)])
        await db.commit()
        a_email, a_name, off_email, g_name, role_name = alice.email, alice.username, off.email, glass.username, role.name
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=idp), base_url=ISSUER) as c:
        await c.post("/_control", json={"users": {a_email: {"groups": ["erp-sales", "unmapped"]}}})
    async with _erp() as erp:
        r, q = await _sign_in(erp, idp, a_email)
        assert r.status_code == 302 and r.headers["location"].endswith("/dashboard") and "sso_error" not in r.headers["location"]
        me = await erp.get("/api/v1/auth/me")
        assert me.status_code == 200 and me.json()["username"] == a_name
        replay = await erp.get("/api/v1/sso/callback", params={"code": q["code"][0], "state": q["state"][0]})
        assert "sso_error" in replay.headers["location"] and "already" in replay.headers["location"]
    async with _erp() as erp, _erp() as other:
        r = await erp.get("/api/v1/sso/start")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=idp), base_url=ISSUER) as idp_c:
            auth = await idp_c.get(r.headers["location"] + "&login_hint=" + a_email)
        qq = parse_qs(urlparse(auth.headers["location"]).query)
        csrf = await other.get("/api/v1/sso/callback", params={"code": qq["code"][0], "state": qq["state"][0]})
        assert "sso_error" in csrf.headers["location"] and "browser" in csrf.headers["location"]   # login CSRF
    async with _erp() as erp:
        for email, tamper, words in ((f"nobody{uuid.uuid4().hex[:4]}@povu-demo.test", None, "No%20ERP%20account"),
                                     (off_email, None, "disabled"), (a_email, "nonce", "nonce"), (a_email, "aud", "rejected"),
                                     (a_email, "key", "rejected"), (a_email, "expired", "rejected"),
                                     (a_email, "unverified", "confirm"), (a_email, "no_verified_claim", "confirm")):
            r, _ = await _sign_in(erp, idp, email, tamper)
            assert "sso_error" in r.headers["location"] and words in r.headers["location"], (tamper, r.headers["location"])
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.email == a_email))).scalar_one()
        await db.refresh(u, ["roles"])
        assert role_name in {r.name for r in u.roles}
        n = (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "LOGIN_FAILED",
                                                                               AuditLog.details["method"].astext == "oidc"))).scalar_one()
        assert n >= 8
        cfg = (await db.execute(select(SSOConfig).where(SSOConfig.active.is_(True)))).scalar_one()
        cfg.enforced = True
        await db.commit()
    async with _erp() as erp:
        assert (await erp.post("/api/v1/auth/login", data={"username": a_name, "password": pw})).status_code == 403
        assert (await erp.post("/api/v1/auth/login", data={"username": g_name, "password": pw})).status_code == 200
        st = (await erp.get("/api/v1/sso/status")).json()
        assert st["oidc"] == "ACTIVE" and st["enforced"] and st["saml"] == "NOT_AVAILABLE"
    async with AsyncSessionLocal() as db:
        cfg = (await db.execute(select(SSOConfig).where(SSOConfig.active.is_(True)))).scalar_one()
        cfg.enforced, cfg.active = False, False
        await db.commit()
