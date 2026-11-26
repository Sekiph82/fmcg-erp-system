"""Shared fixtures for the M49 social tests (T007-T010): simulator wiring, channel + approved-post helpers."""
import os
import uuid
from types import SimpleNamespace

import httpx
import pytest

from app.core import provider_http
from tests.provider_sim.social_app import MB, apply_sim_settings, create_social_app  # noqa: F401

BASE = "http://social.test"
CDN = "https://cdn.povu-demo.test"
VID = {"url": f"{CDN}/videos/povu-allclean-1l.mp4", "kind": "video"}
IMG1 = {"url": f"{CDN}/images/povu-hand-wash-1kg.jpg", "kind": "image", "alt_text": "POVU Hand Wash Powder 1 kg pouch"}
IMG2 = {"url": f"{CDN}/images/povu-allclean-1l.jpg", "kind": "image", "alt_text": "POVU AllClean 1 L bottle"}
IMG3 = {"url": f"{CDN}/images/povu-dish-gel.jpg", "kind": "image"}
TEXT = "POVU AllClean 1 L: one bottle, every surface."
ALICE = SimpleNamespace(username="alice", is_superuser=True, id=None, email=None, full_name=None)
BOB = SimpleNamespace(username="bob", is_superuser=True, id=None, email=None, full_name=None)
VIEWER = SimpleNamespace(username="vera", is_superuser=False, id=None, roles=[SimpleNamespace(
    is_active=True, permissions=[SimpleNamespace(code="marketing.view", is_active=True)])])

DB = pytest.mark.skipif(os.environ.get("M49_DB") != "1", reason="requires the task-owned disposable PostgreSQL (M49_DB=1)")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M49_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.fixture
def sim(monkeypatch):
    app = create_social_app()
    apply_sim_settings(monkeypatch, BASE, m49=True, SOCIAL_STATUS_POLL_SECONDS=0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app.state.sim
    provider_http.set_test_transport(None)


def ctl(sim, **kw):
    for k, v in kw.items():
        if k == "faults":
            for fk, fv in v.items():
                sim["faults"].setdefault(fk, []).extend(fv)
        else:
            sim[k] = v


async def make_post(db, network, *, fmt=None, media=(), text=TEXT, fopts=None, link=None, copts=None, at=None, tiktok=None, ext=None, approve=True):
    from app.api.v1.endpoints import social as ep
    tag = uuid.uuid4().hex[:8]
    ch = await ep.add_channel(ep.ChannelIn(network=network, external_id=ext or f"{network[:2]}{tag}", name=f"POVU {network}",
                                           options=copts or {}), db, ALICE)
    p = await ep.create_post(ep.PostIn(channel_id=ch["id"], idempotency_key=f"k-{tag}", text=text, media=list(media), link=link, format=fmt,
                                       format_options=fopts or {}, scheduled_at=at), db, ALICE)
    pid = uuid.UUID(p["id"])
    if tiktok:
        await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(**tiktok), db, ALICE)
    if approve:
        await ep.post_action(pid, "request", db, ALICE)
        await ep.post_action(pid, "approve", db, BOB)
    return pid, ch


async def act(db, pid, action, user=ALICE):
    from app.api.v1.endpoints import social as ep
    return await ep.post_action(pid, action, db, user)


async def state(db, pid):
    from app.api.v1.endpoints import social as ep
    await db.rollback()
    return await ep._out(db, await ep._post(db, pid))


async def drive(db, pid, n=8):
    """Refresh until the post leaves the in-flight states (max n)."""
    out = await state(db, pid)
    for _ in range(n):
        if out["status"] not in ("SUBMITTED", "PROCESSING", "UNKNOWN") or out.get("provider_status") == "SCHEDULED" or not out["provider_ref"]:
            break
        out = await act(db, pid, "refresh")
    return out


def calls(sim, provider):
    return [c for c in sim["calls"] if c["provider"] == provider]
