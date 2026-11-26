"""M48.S01.T005 organic social publishing state machine (unit + simulator; DB part needs M48_DB=1).

A TikTok publish_id / Instagram container id is a submission id, never proof of publication. Covered: submit →
processing → published (simulator delays completion), provider FAILED with fail_reason, processing timeout → UNKNOWN →
reconcile, lost init answer → UNKNOWN without resubmission, crash between claim and answer → no duplicate post, restart
recovery, signed webhook (stale / bad signature refused, replay ignored, webhook never sets PUBLISHED by itself), cancel,
unaudited app forced to SELF_ONLY, creator_info options, FILE_UPLOAD chunking, status-read retry, Instagram container
polling, unauthorized user refused. Synthetic POVU home-care data only.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.core import provider_http
from app.services import social_service as ss
from tests.provider_sim.social_app import MB, apply_sim_settings, create_social_app, tiktok_webhook

BASE = "http://social.test"
VID = [{"url": "https://cdn.povu-demo.test/videos/povu-allclean-1l.mp4", "kind": "video"}]
IMG = [{"url": "https://cdn.povu-demo.test/images/povu-hand-wash-1kg.jpg", "kind": "image"}]
ALICE = SimpleNamespace(username="alice", is_superuser=True, id=None, email=None, full_name=None)
BOB = SimpleNamespace(username="bob", is_superuser=True, id=None, email=None, full_name=None)
VIEWER = SimpleNamespace(username="vera", is_superuser=False, id=None, roles=[SimpleNamespace(
    is_active=True, permissions=[SimpleNamespace(code="marketing.view", is_active=True)])])


# ── pure rules ──────────────────────────────────────────────────────────

def test_chunk_rules_and_url_ownership(monkeypatch):
    assert ss.chunk_plan(3 * MB) == (3 * MB, 1)                      # < 5 MB: whole file
    assert ss.chunk_plan(40 * MB) == (40 * MB, 1)                    # one chunk up to 64 MB
    chunk, count = ss.chunk_plan(200 * MB)
    assert (chunk, count) == (64 * MB, 3) and 200 * MB - chunk * (count - 1) <= 128 * MB
    with pytest.raises(ss.SocialError):
        ss.chunk_plan(0)
    with pytest.raises(ss.SocialError):
        ss.chunk_plan(64 * MB * 1001)
    from app.core.config import settings
    monkeypatch.setitem(settings.__dict__, "TIKTOK_VERIFIED_URL_PREFIXES", "https://cdn.povu-demo.test/videos/,media.example.com")
    assert ss.url_verified("https://cdn.povu-demo.test/videos/a.mp4")
    assert not ss.url_verified("https://cdn.povu-demo.test/other/a.mp4")
    assert ss.url_verified("https://eu.media.example.com/x.mp4") and not ss.url_verified("https://example.com/x.mp4")


def test_webhook_signature_window(monkeypatch):
    from app.core.config import settings
    monkeypatch.setitem(settings.__dict__, "TIKTOK_CLIENT_SECRET", "")
    with pytest.raises(ss.SocialError, match="not configured"):
        ss.verify_tiktok(b"{}", "t=1,s=x")
    monkeypatch.setitem(settings.__dict__, "TIKTOK_CLIENT_SECRET", "sim-tt-client-secret")
    raw, header = tiktok_webhook("post.publish.complete", "v_pub_url~v2-1", ts=1_800_000_000)
    assert ss.verify_tiktok(raw, header, now=1_800_000_100)
    with pytest.raises(ss.SocialError, match="stale"):
        ss.verify_tiktok(raw, header, now=1_800_000_000 + 301)
    with pytest.raises(ss.SocialError, match="bad signature"):
        ss.verify_tiktok(raw + b" ", header, now=1_800_000_000)


# ── simulator + DB ──────────────────────────────────────────────────────

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.fixture
def sim(monkeypatch):
    app = create_social_app()
    apply_sim_settings(monkeypatch, BASE, SOCIAL_STATUS_POLL_SECONDS=0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app.state.sim
    provider_http.set_test_transport(None)


def _ctl(sim, **kw):
    for k, v in kw.items():
        if k == "faults":
            for fk, fv in v.items():
                sim["faults"].setdefault(fk, []).extend(fv)
        else:
            sim[k] = v


async def _post(db, network, media, *, opts=None, key=None):
    """A channel + an approved post (second editor), with TikTok options set before approval."""
    from app.api.v1.endpoints import social as ep
    tag = uuid.uuid4().hex[:8]
    ch = await ep.add_channel(ep.ChannelIn(network=network, external_id=f"{network[:2]}{tag}", name=f"POVU {network}"), db, ALICE)
    p = await ep.create_post(ep.PostIn(channel_id=ch["id"], idempotency_key=key or f"k-{tag}", media=media,
                                       text="POVU AllClean 1 L — cleans every surface."), db, ALICE)
    pid = uuid.UUID(p["id"])
    if opts:
        await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(**opts), db, ALICE)
    await ep.post_action(pid, "request", db, ALICE)
    await ep.post_action(pid, "approve", db, BOB)
    return pid, ch


SELF = {"privacy_level": "SELF_ONLY", "consent": True}


async def _act(db, pid, action, user=ALICE):
    from app.api.v1.endpoints import social as ep
    return await ep.post_action(pid, action, db, user)


@DB
@pytest.mark.asyncio
async def test_tiktok_submit_processing_published(sim):
    from app.db.session import AsyncSessionLocal
    _ctl(sim, processing_polls=2)
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        out = await _act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["provider_ref"].startswith("v_pub_url~")
        assert out["external_post_id"] is None and out["publish_mode"] == "SIMULATED"
        init = next(c for c in sim["calls"] if c["provider"] == "tiktok")["json"]
        assert init["post_info"]["privacy_level"] == "SELF_ONLY" and init["source_info"]["source"] == "PULL_FROM_URL"
        assert init["post_info"]["disable_stitch"] is True                 # creator has stitch off
        assert (await _act(db, pid, "refresh"))["status"] == "PROCESSING"
        done = await _act(db, pid, "refresh")
        assert done["status"] == "PUBLISHED" and done["provider_status"] == "PUBLISH_COMPLETE"
        assert done["external_post_id"] is None                             # SELF_ONLY: no public post id
        events = [h["event"] for h in done["history"]]
        assert events.index("CLAIMED") < events.index("SUBMITTED") < events.index("PUBLISHED")


@DB
@pytest.mark.asyncio
async def test_tiktok_failed_and_unaudited_self_only(sim, monkeypatch):
    from fastapi import HTTPException
    from app.api.v1.endpoints import social as ep
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        _ctl(sim, processing_polls=0, next_outcome={"status": "FAILED", "fail_reason": "spam_risk_text"})
        pid, ch = await _post(db, "tiktok", VID, opts=SELF)
        out = await _act(db, pid, "submit")
        assert out["status"] == "FAILED" and out["fail_reason"] == "spam_risk_text" and not out["external_post_id"]
        info = await ep.tiktok_creator_info(uuid.UUID(ch["id"]), db, ALICE)
        assert info["privacy_level_options"] == ["SELF_ONLY"] and not info["audited"]
        assert "PUBLIC_TO_EVERYONE" in info["provider_privacy_level_options"]
        with pytest.raises(HTTPException) as e:                              # unaudited: forced SELF_ONLY
            await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(privacy_level="PUBLIC_TO_EVERYONE", consent=True), db, ALICE)
        assert e.value.status_code == 422
        with pytest.raises(HTTPException):                                   # no consent, no post
            await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(privacy_level="SELF_ONLY", consent=False), db, ALICE)
        # audited app: public allowed, and TikTok's public post id is recorded at PUBLISH_COMPLETE
        monkeypatch.setitem(settings.__dict__, "TIKTOK_APP_AUDITED", True)
        _ctl(sim, audited=True)
        pid2, _ = await _post(db, "tiktok", VID, opts={"privacy_level": "PUBLIC_TO_EVERYONE", "consent": True})
        out = await _act(db, pid2, "submit")
        assert out["status"] == "PUBLISHED" and out["external_post_id"]
        # a post without consent is never sent
        pid3, _ = await _post(db, "tiktok", VID)
        n = len(sim["calls"])
        out = await _act(db, pid3, "submit")
        assert out["status"] == "FAILED" and "consent" in out["error"] and len(sim["calls"]) == n


@DB
@pytest.mark.asyncio
async def test_timeout_unknown_reconcile_and_lost_answer(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialPost
    async with AsyncSessionLocal() as db:
        monkeypatch.setitem(settings.__dict__, "SOCIAL_PUBLISH_TIMEOUT_MINUTES", 0)
        _ctl(sim, processing_polls=2)
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        out = await _act(db, pid, "submit")
        assert out["status"] == "UNKNOWN" and out["provider_ref"]           # not final in time
        for i in range(4):
            await ss.reconcile_due(db, datetime.now(timezone.utc) + timedelta(hours=1 + i))
        p = await db.get(SocialPost, pid)
        await db.refresh(p)
        assert p.status == "PUBLISHED"
        # init accepted but the answer was lost: UNKNOWN without a publish_id, never resubmitted automatically
        monkeypatch.setitem(settings.__dict__, "SOCIAL_PUBLISH_TIMEOUT_MINUTES", 30)
        _ctl(sim, faults={"tt_init": ["timeout"]})
        pid2, _ = await _post(db, "tiktok", VID, opts=SELF)
        out = await _act(db, pid2, "submit")
        assert out["status"] == "UNKNOWN" and out["provider_ref"] is None and "may have posted" in out["error"]
        inits = len([c for c in sim["calls"] if c["provider"] == "tiktok"])
        await ss.publish_due(db, datetime.now(timezone.utc) + timedelta(days=1))
        assert len([c for c in sim["calls"] if c["provider"] == "tiktok"]) == inits
        # a person checked the channel: release puts it back to APPROVED
        assert (await _act(db, pid2, "release"))["status"] == "APPROVED"


@DB
@pytest.mark.asyncio
async def test_crash_between_claim_and_answer_no_duplicate(sim, monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialPost
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        p = await db.get(SocialPost, pid)
        p.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()

    def crash(*a, **k):
        raise RuntimeError("worker killed")
    orig = ss._submitted
    monkeypatch.setattr(ss, "_submitted", crash)                             # dies after TikTok accepted the init
    async with AsyncSessionLocal() as db:
        with pytest.raises(RuntimeError):
            await ss.publish_due(db)
    monkeypatch.setattr(ss, "_submitted", orig)
    assert len([c for c in sim["calls"] if c["provider"] == "tiktok"]) == 1
    async with AsyncSessionLocal() as db:                                    # "restart"
        p = await db.get(SocialPost, pid)
        assert p.status == "SUBMITTING" and p.claimed_at                     # the claim was durable
        await ss.publish_due(db)                                             # not resubmitted
        await ss.reconcile_due(db, datetime.now(timezone.utc) + timedelta(minutes=10))
        await db.refresh(p)
        assert p.status == "UNKNOWN" and "never resubmitted" in p.error
        await ss.publish_due(db, datetime.now(timezone.utc) + timedelta(days=1))
    assert len([c for c in sim["calls"] if c["provider"] == "tiktok"]) == 1


@DB
@pytest.mark.asyncio
async def test_restart_recovery_and_status_retry(sim):
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialPost
    _ctl(sim, processing_polls=3)
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        assert (await _act(db, pid, "submit"))["status"] == "PROCESSING"
    async with AsyncSessionLocal() as db:                                    # new process: the tick resumes it
        _ctl(sim, faults={"tt_status": ["500", "429"]})                      # reads are retried with backoff
        await ss.reconcile_due(db, datetime.now(timezone.utc) + timedelta(hours=1))
        p = await db.get(SocialPost, pid)
        assert p.status == "PROCESSING" and not sim["faults"]["tt_status"]
        for i in range(3):
            await ss.reconcile_due(db, datetime.now(timezone.utc) + timedelta(hours=2 + i))
        await db.refresh(p)
        assert p.status == "PUBLISHED"


@DB
@pytest.mark.asyncio
async def test_webhook_replay_ignored_and_never_publishes_alone(sim):
    from fastapi import FastAPI
    from app.api.v1.endpoints.social_tiktok_webhook_public import router
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialPost
    _ctl(sim, processing_polls=3)
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        ref = (await _act(db, pid, "submit"))["provider_ref"]
    app = FastAPI()
    app.include_router(router, prefix="/public/social/tiktok")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        raw, sig = tiktok_webhook("post.publish.complete", ref)
        h = {"TikTok-Signature": sig, "Content-Type": "application/json"}
        r = await c.post("/public/social/tiktok", content=raw, headers=h)
        assert r.status_code == 200 and r.json() == {"result": "processed", "status": "PROCESSING"}   # status fetch decides
        assert (await c.post("/public/social/tiktok", content=raw, headers=h)).json() == {"result": "replay"}
        assert (await c.post("/public/social/tiktok", content=raw + b" ", headers=h)).status_code == 403
        old_raw, old_sig = tiktok_webhook("post.publish.complete", ref, ts=1_700_000_000)
        assert (await c.post("/public/social/tiktok", content=old_raw, headers={"TikTok-Signature": old_sig})).status_code == 403
        for ts in (1, 2):                                                    # TikTok redelivers: idempotent
            raw, sig = tiktok_webhook("post.publish.complete", ref, ts=int(datetime.now().timestamp()) + ts)
            assert (await c.post("/public/social/tiktok", content=raw, headers={"TikTok-Signature": sig})).status_code == 200
    async with AsyncSessionLocal() as db:
        p = await db.get(SocialPost, pid)
        assert p.status == "PUBLISHED" and [h["event"] for h in p.history].count("PUBLISHED") == 1


@DB
@pytest.mark.asyncio
async def test_cancel_and_file_upload(sim, monkeypatch):
    from fastapi import HTTPException
    from app.db.session import AsyncSessionLocal
    _ctl(sim, processing_polls=5)
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "tiktok", VID, opts=SELF)
        await _act(db, pid, "submit")
        out = await _act(db, pid, "cancel")
        assert out["status"] == "CANCELLED" and out["fail_reason"] == "publish_cancelled"
        # FILE_UPLOAD: 11 MB in two sequential Content-Range chunks (chunk size lowered to the 5 MB minimum)
        monkeypatch.setattr(ss, "CHUNK_MAX", 5 * MB)
        _ctl(sim, video_size=11 * MB, processing_polls=1)
        pid2, _ = await _post(db, "tiktok", VID, opts={**SELF, "source": "FILE_UPLOAD"})
        out = await _act(db, pid2, "submit")
        assert out["provider_ref"].startswith("v_pub_file~") and "UPLOADED" in [h["event"] for h in out["history"]]
        rec = sim["tt"][out["provider_ref"]]
        assert rec["uploaded"] == rec["size"] == 11 * MB
        with pytest.raises(HTTPException) as e:                              # TikTok cancels URL downloads only
            await _act(db, pid2, "cancel")
        assert e.value.status_code == 409
        done = await _act(db, pid2, "refresh")
        assert done["status"] == "PUBLISHED"
        with pytest.raises(HTTPException):
            await _act(db, pid2, "cancel")                                   # published: delete on the network


@DB
@pytest.mark.asyncio
async def test_instagram_container_polled_before_publish(sim):
    from app.db.session import AsyncSessionLocal
    _ctl(sim, processing_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await _post(db, "instagram", IMG)
        out = await _act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and not [c for c in sim["calls"] if c["provider"] == "instagram"]
        _ctl(sim, faults={"ig_publish": ["timeout"]})                         # publish happens, answer lost
        out = await _act(db, pid, "refresh")
        assert out["status"] == "PROCESSING" and out["provider_status"] == "FINISHED"
        out = await _act(db, pid, "refresh")                                  # container now says PUBLISHED
        assert out["status"] == "PUBLISHED"
        assert len([c for c in sim["calls"] if c["provider"] == "instagram"]) == 1   # media_publish once
        _ctl(sim, processing_polls=0, next_outcome={"status_code": "ERROR"})
        pid2, _ = await _post(db, "instagram", IMG)
        out = await _act(db, pid2, "submit")
        assert out["status"] == "FAILED" and out["fail_reason"] == "ERROR"
        _ctl(sim, processing_polls=0)
        pid3, _ = await _post(db, "instagram", IMG)
        out = await _act(db, pid3, "submit")
        assert out["status"] == "PUBLISHED" and out["external_post_id"].startswith("ig-media-")
        # Facebook: the feed id is the created post; an unanswered call is UNKNOWN, not FAILED or PUBLISHED
        _ctl(sim, faults={"social": ["timeout"]})
        pid4, _ = await _post(db, "facebook", [])
        assert (await _act(db, pid4, "submit"))["status"] == "UNKNOWN"


@DB
@pytest.mark.asyncio
async def test_unauthorized_user_refused(sim):
    from fastapi import HTTPException
    from app.api.v1.endpoints import social as ep
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        pid, ch = await _post(db, "tiktok", VID, opts=SELF)
        for call in (lambda: ep.post_action(pid, "submit", db, VIEWER), lambda: ep.post_action(pid, "cancel", db, VIEWER),
                     lambda: ep.set_tiktok_options(pid, ep.TikTokOptionsIn(**SELF), db, VIEWER),
                     lambda: ep.tiktok_creator_info(uuid.UUID(ch["id"]), db, VIEWER)):
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == 403
        assert not [c for c in sim["calls"] if c["provider"] == "tiktok"]
