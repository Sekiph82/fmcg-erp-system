"""Shared helpers for the M51.S01.T006/T007/T010 tests (DB part needs M51_DB=1)."""
import uuid
from types import SimpleNamespace

import httpx


async def ensure_tables():
    from app.db.base import Base
    from app.db.session import engine
    from app.models import m51_media as m
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


def client_for(user) -> httpx.AsyncClient:
    from fastapi import FastAPI
    from app.api.v1.endpoints.m51_media import router
    from app.api.v1.endpoints.m51_media_public import router as public
    from app.core.deps import get_current_user
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/media-studio")
    app.include_router(public, prefix="/api/v1/public/media-files")
    app.dependency_overrides[get_current_user] = lambda: user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


def anon_client() -> httpx.AsyncClient:
    from fastapi import FastAPI
    from app.api.v1.endpoints.m51_media_public import router as public
    app = FastAPI()
    app.include_router(public, prefix="/api/v1/public/media-files")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


def setv(monkeypatch, name, value):
    from app.core.config import settings
    if name in type(settings).model_fields:
        monkeypatch.setattr(settings, name, value)
    else:
        monkeypatch.setattr(type(settings), name, value, raising=False)


def use_image_sim(monkeypatch):
    from app.core import provider_http
    from tests.provider_sim.image_m51_app import create_app
    sim = create_app()
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(provider_http, "_test_transport", httpx.ASGITransport(app=sim))
    return sim


async def sim_calls():
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        return (await c.get("http://127.0.0.1:8765/_control/calls")).json()


async def sim_control(body: dict):
    from app.core.provider_http import provider_client
    async with provider_client() as c:
        await c.post("http://127.0.0.1:8765/_control", json=body)


def clean_scan(monkeypatch):
    """No ClamAV in the test environment: every scan answers CLEAN (the real fail-closed path is tested separately)."""
    from app.services import document_storage_service as d

    async def fake(path):
        return d.ScanResult("CLEAN", "test")
    monkeypatch.setattr(d, "scan_document", fake)
