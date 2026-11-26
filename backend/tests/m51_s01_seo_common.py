"""Shared helpers for the M51.S01.T003/T004/T005/T009 tests (DB part needs M51_DB=1)."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx

SIM = "http://127.0.0.1:8766"


async def ensure_tables():
    from app.db.base import Base
    from app.db.session import engine
    from app.models import m51_seo as m
    tables = [getattr(m, n).__table__ for n in dir(m) if n.startswith("M51") and hasattr(getattr(m, n), "__table__")]
    async with engine.begin() as c:
        await c.run_sync(lambda s: Base.metadata.create_all(s, tables=tables, checkfirst=True))


async def staff(db, tag: str, perms: tuple, superuser: bool = False):
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test",
             full_name=tag.title(), hashed_password="x", is_active=True)
    db.add(u)
    await db.flush()
    plist = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in perms]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=superuser,
                           access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=plist, access_scopes=[])])


def client_for(user=None, ip: str = "203.0.113.7") -> httpx.AsyncClient:
    """The M51 routers on a tiny app (module_registry wiring is done by the coordinator)."""
    from fastapi import FastAPI
    from app.api.v1.endpoints import m51_seo, m51_visitor_verify, m51_visitor_verify_public
    from app.core.deps import get_current_user
    app = FastAPI()
    app.include_router(m51_seo.router, prefix="/api/v1/seo-pro")
    app.include_router(m51_visitor_verify.router, prefix="/api/v1/visitor-verification")
    app.include_router(m51_visitor_verify_public.router, prefix="/api/v1/public/visitor-verify")
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 1234)), base_url="http://erp.test")


def setv(monkeypatch, name, value):
    from app.core.config import settings
    if name in type(settings).model_fields:
        monkeypatch.setattr(settings, name, value)
    else:
        monkeypatch.setattr(type(settings), name, value, raising=False)


def use_sim(monkeypatch):
    from app.core import provider_http
    from tests.provider_sim.seo_m51_app import create_app, sim_settings
    sim = create_app()
    for k, v in sim_settings(SIM).items():
        setv(monkeypatch, k, v)
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.ASGITransport(app=sim))
    return sim


async def sim_control(body: dict):
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        await c.post(f"{SIM}/_control", json=body)


async def sim_calls():
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        return (await c.get(f"{SIM}/_control/calls")).json()


async def connect_google(db, user_id, purpose="searchconsole"):
    from app.models.oauth_connection import OAuthConnection
    from app.services import oauth_service as o
    scope = "webmasters" if purpose.endswith("_edit") else "webmasters.readonly"
    c = OAuthConnection(user_id=user_id, provider="google", purpose=purpose, status="CONNECTED", account_email="seo@povu-demo.test",
                        scopes=[f"https://www.googleapis.com/auth/{scope}"], access_token_enc=o._enc("sim-access-token-ro"),
                        refresh_token_enc=o._enc("sim-refresh"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    db.add(c)
    await db.flush()
    return c
