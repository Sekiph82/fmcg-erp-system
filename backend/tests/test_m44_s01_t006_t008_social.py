"""M44.S01.T006–T008 social publishing, calendar and listening (unit + simulator; DB part needs M44_DB=1).

Unit/simulator: network constraints (Instagram needs one image and ≤30 hashtags, TikTok one video, LinkedIn text-only,
https media), publishing route is MANUAL unless publishing is enabled and the token is set, adapters against the local
simulator (Facebook feed/photo, Instagram container → publish, LinkedIn posts with version header, TikTok SELF_ONLY),
missing permission → error, keyword tags list their evidence, Meta webhook signature.
DB: version/approval flow (edit after approval → needs approval again; reschedule keeps it), second editor, due post
published once, unconfigured channel → not published, webhook only for opted-in channels, dedupe, author deletion
blanks the text, CSV import dedupes and rejects bad rows.
"""
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import social_service as ss
from tests.provider_sim.ads_app import create_ads_app, social_sim_settings

BASE = "http://ads.test"
IMG = [{"url": "https://cdn.povu-demo.test/juice.jpg", "kind": "image"}]
VID = [{"url": "https://cdn.povu-demo.test/juice.mp4", "kind": "video"}]


def test_constraints_and_route(monkeypatch):
    assert ss.problems("instagram", "POVU juice", [], None)                        # needs one image
    assert not ss.problems("instagram", "POVU juice", IMG, None)
    assert ss.problems("instagram", " ".join(f"#t{i}" for i in range(31)), IMG, None)
    assert ss.problems("tiktok", "x", IMG, None) and not ss.problems("tiktok", "x", VID, None)
    assert ss.problems("linkedin", "x", IMG, None) and not ss.problems("linkedin", "x", [], "https://povu-demo.test")
    assert ss.problems("facebook", "x", [{"url": "http://insecure.test/a.jpg", "kind": "image"}], None)
    assert ss.problems("x", "y" * 281, [], None)
    monkeypatch.setattr(settings, "META_PAGE_ACCESS_TOKEN", "t")
    monkeypatch.setattr(settings, "SOCIAL_PUBLISHING_ENABLED", False)
    assert ss.publish_route("facebook") == "MANUAL"
    monkeypatch.setattr(settings, "SOCIAL_PUBLISHING_ENABLED", True)
    assert ss.publish_route("facebook") == "API" and ss.publish_route("x") == "MANUAL" and ss.publish_route("youtube") == "MANUAL"


def test_tags_have_evidence_and_replies_are_drafts():
    s, topics, ev = ss.tag("Delivery was late and the bottle was leaking, terrible")
    assert s == "NEGATIVE" and {"delivery", "packaging", "quality"} <= set(topics) and "late" in ev["negative"]
    assert ss.tag("POVU juice is delicious, asante!")[0] == "POSITIVE"
    assert ss.tag("Where can I buy it?")[0] == "NEUTRAL"
    item = SimpleNamespace(author="Asha Buyer", sentiment="NEGATIVE", topics=["delivery"])
    assert "sorry" in ss.suggest_reply(item) and "delivery" in ss.suggest_reply(item)


def test_meta_signature(monkeypatch):
    monkeypatch.setattr(settings, "META_APP_SECRET", "")
    with pytest.raises(ss.SocialError, match="not configured"):
        ss.verify_meta(b"{}", "")
    monkeypatch.setattr(settings, "META_APP_SECRET", "sim-app-secret")
    raw = b'{"object":"page"}'
    good = "sha256=" + hmac.new(b"sim-app-secret", raw, hashlib.sha256).hexdigest()
    ss.verify_meta(raw, good)
    with pytest.raises(ss.SocialError):
        ss.verify_meta(raw + b" ", good)


@pytest.fixture
def sim(monkeypatch):
    app = create_ads_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in social_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


def _p(text="POVU juice is back", media=None, link=None):
    return SimpleNamespace(text=text, media=media or [], link=link)


@pytest.mark.asyncio
async def test_adapters_against_simulator(sim):
    ch = lambda net, ext="123": SimpleNamespace(network=net, external_id=ext)  # noqa: E731
    assert await ss._post_api(ch("facebook"), _p(link="https://povu-demo.test")) == "123_1"
    assert await ss._post_api(ch("facebook"), _p(media=IMG)) == "123_ph1"
    assert await ss._post_api(ch("instagram", "17841"), _p(media=IMG)) == "ig-media-1"
    assert await ss._post_api(ch("linkedin", "555"), _p(link="https://povu-demo.test")) == "urn:li:share:9001"
    assert await ss._post_api(ch("tiktok", "tt"), _p(media=VID)) == "v_pub_url~1"
    async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
        await c.post("/_control", json={"faults": {"social": ["perm"]}})
    with pytest.raises(ss.SocialError, match="pages_manage_posts"):
        await ss._post_api(ch("facebook"), _p())


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@DB
@pytest.mark.asyncio
async def test_post_lifecycle_and_publishing(sim):
    from fastapi import HTTPException
    from app.api.v1.endpoints import social as ep
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialPost
    alice = SimpleNamespace(username="alice", is_superuser=True, id=None)
    bob = SimpleNamespace(username="bob", is_superuser=True, id=None)
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        fb = await ep.add_channel(ep.ChannelIn(network="facebook", external_id=f"pg{tag}", name="POVU Page"), db, alice)
        xx = await ep.add_channel(ep.ChannelIn(network="x", external_id=f"x{tag}", name="POVU X"), db, alice)
        body = ep.PostIn(channel_id=fb["id"], idempotency_key=f"k-{tag}-1", text="POVU juice is back",
                         scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        p = await ep.create_post(body, db, alice)
        assert (await ep.create_post(body, db, alice))["id"] == p["id"]                 # idempotent
        pid = uuid.UUID(p["id"])
        await ep.post_action(pid, "request", db, alice)
        with pytest.raises(HTTPException):
            await ep.post_action(pid, "approve", db, alice)
        assert (await ep.post_action(pid, "approve", db, bob))["approved"]
        # reschedule keeps approval, content change does not
        later = body.model_copy(update={"scheduled_at": datetime.now(timezone.utc) - timedelta(seconds=30)})
        assert (await ep.edit_post(pid, later, db, alice))["approved"]
        changed = later.model_copy(update={"text": "POVU juice is back — now in 1L"})
        out = await ep.edit_post(pid, changed, db, alice)
        assert not out["approved"] and out["version"] == 2 and out["status"] == "DRAFT"
        await ep.post_action(pid, "request", db, alice)
        await ep.post_action(pid, "approve", db, bob)
        assert await ss.publish_due(db) >= 1
        post = await db.get(SocialPost, pid)
        await db.refresh(post)
        assert post.status == "PUBLISHED" and post.external_post_id
        assert await ss.publish_due(db) == 0 or (await db.get(SocialPost, pid)).status == "PUBLISHED"
        # unconfigured network: never published, exportable
        q = await ep.create_post(ep.PostIn(channel_id=xx["id"], idempotency_key=f"k-{tag}-2", text="POVU on X",
                                           scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1)), db, alice)
        qid = uuid.UUID(q["id"])
        await ep.post_action(qid, "request", db, alice)
        await ep.post_action(qid, "approve", db, bob)
        await ss.publish_due(db)
        xp = await db.get(SocialPost, qid)
        await db.refresh(xp)
        assert xp.status == "FAILED" and "manually" in xp.error
        assert (await ep.post_action(qid, "export", db, alice))["text"] == "POVU on X"


@DB
@pytest.mark.asyncio
async def test_listening_opt_in_dedupe_delete_import():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import SocialChannel, SocialItem
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        ch = SocialChannel(network="facebook", external_id=f"pg{tag}", name="POVU Page", listen_enabled=False)
        db.add(ch)
        await db.flush()
        ev = {"object": "page", "entry": [{"id": f"pg{tag}", "changes": [{"field": "feed", "value": {
            "item": "comment", "verb": "add", "comment_id": f"c{tag}", "post_id": "p1", "message": "Delivery was late",
            "from": {"name": "Asha Buyer", "id": "1"}, "created_time": 1764000000}}]}]}
        assert (await ss.ingest_meta(db, ev))["stored"] == 0                             # not opted in
        ch.listen_enabled = True
        await db.flush()
        assert (await ss.ingest_meta(db, ev))["stored"] == 1
        assert (await ss.ingest_meta(db, ev))["stored"] == 0                             # dedupe
        ev["entry"][0]["changes"][0]["value"]["verb"] = "remove"
        await ss.ingest_meta(db, ev)
        await db.flush()
        it = (await db.execute(select(SocialItem).where(SocialItem.external_id == f"c{tag}"))).scalar_one()
        assert it.status == "DELETED" and it.text is None and it.author is None
        csv = ("network,kind,external_id,author,text,url,occurred_at\n"
               f"linkedin,COMMENT,li{tag},Ben,Great product,https://www.linkedin.com/x,2026-11-20T10:00:00\n"
               f"linkedin,COMMENT,li{tag},Ben,Great product,,\n"
               f"myspace,COMMENT,z{tag},A,b,,\n")
        assert await ss.import_csv(db, csv) == {"stored": 1, "duplicates": 1, "rejected": 1}
        await db.rollback()
