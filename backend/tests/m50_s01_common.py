"""Shared helpers for the M50.S01.T001-T004 tests (DB part needs M50_DB=1)."""
import uuid
from types import SimpleNamespace

import httpx


async def ensure_tables():
    from app.db.base import Base
    from app.db.session import engine
    from app.models import m50_prospecting as m
    tables = [getattr(m, n).__table__ for n in dir(m) if n.startswith("M50") and hasattr(getattr(m, n), "__table__")]
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


def client_for(user) -> httpx.AsyncClient:
    """The M50 router on a tiny app (module_registry wiring is done by the coordinator) acting as ``user``."""
    from fastapi import FastAPI
    from app.api.v1.endpoints.m50_prospecting import router
    from app.core.deps import get_current_user
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/prospecting-agent")
    app.dependency_overrides[get_current_user] = lambda: user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


def setv(monkeypatch, name, value):
    """Set a setting that may not be a declared field (adapters read them with getattr)."""
    from app.core.config import settings
    if name in type(settings).model_fields:
        monkeypatch.setattr(settings, name, value)
    else:
        monkeypatch.setattr(type(settings), name, value, raising=False)


def use_sim(monkeypatch):
    """Point every adapter at the in-process simulator (PROVIDER_EGRESS=local) and return it."""
    from app.core import provider_http
    from tests.provider_sim.prospecting_m50_app import create_app, sim_settings
    sim = create_app()
    for k, v in sim_settings().items():
        setv(monkeypatch, k, v)
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(provider_http, "_test_transport", httpx.ASGITransport(app=sim))   # restored on teardown
    return sim


async def sim_calls():
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        return (await c.get("http://127.0.0.1:8765/_control/calls")).json()


async def sim_control(body: dict):
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        await c.post("http://127.0.0.1:8765/_control", json=body)
