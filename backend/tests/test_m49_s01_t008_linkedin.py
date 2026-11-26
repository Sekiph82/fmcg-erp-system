"""M49.S01.T008 LinkedIn organization posts: Images/Videos API upload -> status -> post -> lifecycle (DB part needs M49_DB=1).

Image, multi-image (2-20), video (multipart + ETags + finalize), article link, text; Linkedin-Version header; asset
processing; post lifecycle PUBLISH_REQUESTED; auth/permission failure; upload part failure and retry; lost post answer is
looked up (never posted twice); insights. Organic carousel is refused with the documented reason."""
import pytest

from app.services import social_formats as sf
from tests.m49_social_helpers import (CDN, DB, IMG1, IMG2, IMG3, MB, TEXT, VID, _dispose_engine, act, calls, ctl, drive, make_post, sim)  # noqa: F401


def test_linkedin_format_rules():
    cap = {f["key"]: f for f in sf.capabilities("linkedin")["formats"]}
    assert not cap["carousel"]["available"] and "not supported" in cap["carousel"]["reason"]
    assert not cap["document"]["available"]
    assert "no native scheduling" in sf.capabilities("linkedin")["scheduling"].lower()
    assert sf.validate("linkedin", "images", TEXT, [IMG1], None)                                         # needs 2-20
    assert not sf.validate("linkedin", "images", TEXT, [{"url": f"{CDN}/images/{i}.jpg", "kind": "image"} for i in range(20)], None)
    assert sf.validate("linkedin", "images", TEXT, [{"url": f"{CDN}/images/{i}.jpg", "kind": "image"} for i in range(21)], None)
    assert sf.validate("linkedin", "link", TEXT, [], "https://povu-demo.test/allclean")                  # article title missing
    assert sf.validate("linkedin", "video", TEXT, [{**VID, "duration_sec": 2}], None)
    assert sf.validate("linkedin", "text", "x" * 3001, [], None)


@DB
@pytest.mark.asyncio
async def test_image_waits_for_asset_then_creates_post_and_confirms_lifecycle(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, li_asset_polls=2, li_post_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="image", media=[IMG1])
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["flow_phase"] == "assets" and not calls(sim, "linkedin")   # no post before AVAILABLE
        assert out["provider_ref"].startswith("urn:li:image:")
        seen = []
        for _ in range(6):
            out = await act(db, pid, "refresh")
            seen.append((out["status"], out["flow_phase"]))
            if out["status"] == "PUBLISHED":
                break
        assert out["status"] == "PUBLISHED" and out["external_post_id"].startswith("urn:li:share:")
        assert ("PROCESSING", "post") in seen or any(p == "post" for _, p in seen)       # PUBLISH_REQUESTED was observed, not assumed live
        body = calls(sim, "linkedin")[0]["json"]
        assert body["content"]["media"]["altText"] == IMG1["alt_text"] and body["author"].startswith("urn:li:organization:")
        assert len(calls(sim, "linkedin")) == 1


@DB
@pytest.mark.asyncio
async def test_multi_image_and_article_with_thumbnail(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, li_asset_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="images", media=[IMG1, IMG2, IMG3])
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        imgs = calls(sim, "linkedin")[-1]["json"]["content"]["multiImage"]["images"]
        assert len(imgs) == 3 and imgs[0]["altText"] and "altText" not in imgs[2]
        pid, _ = await make_post(db, "linkedin", fmt="link", link="https://povu-demo.test/hand-wash",
                                 fopts={"article_title": "POVU Hand Wash Powder", "article_description": "1 kg pouch", "article_thumbnail_url": IMG1["url"]})
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        art = calls(sim, "linkedin")[-1]["json"]["content"]["article"]
        assert art["title"] == "POVU Hand Wash Powder" and art["thumbnail"].startswith("urn:li:image:") and art["source"].startswith("https://povu-demo")
        pid, _ = await make_post(db, "linkedin", fmt="text")
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"


@DB
@pytest.mark.asyncio
async def test_video_multipart_upload_etags_finalize_processing(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, video_size=9 * MB, li_asset_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="video", media=[{**VID, "duration_sec": 30}], fopts={"video_title": "POVU AllClean 1 L"},
                                 )
        ctl(sim, faults={"li_part": ["500"]})                       # the first part PUT fails once and is retried
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["provider_ref"].startswith("urn:li:video:")
        asset = next(iter(sim["li_assets"].values()))
        assert asset["parts"] == 3 and asset["finalized"] and len(asset["etags"]) == 3
        final = await drive(db, pid)
        assert final["status"] == "PUBLISHED"
        assert calls(sim, "linkedin")[0]["json"]["content"]["media"]["title"] == "POVU AllClean 1 L"


@DB
@pytest.mark.asyncio
async def test_asset_processing_failure_never_creates_a_post(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, li_outcome="FAILED", li_asset_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="image", media=[IMG3])
        await act(db, pid, "submit")
        out = await drive(db, pid)
        assert out["status"] == "FAILED" and out["fail_reason"] == "asset_failed" and "UNSUPPORTED_FORMAT" in out["error"]
        assert not calls(sim, "linkedin") and out["external_post_id"] is None


@DB
@pytest.mark.asyncio
async def test_permission_error_and_wrong_version_fail_visibly_then_retry_works(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    ctl(sim, li_asset_polls=0, faults={"li_post": ["perm"]})
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="text")
        await act(db, pid, "submit")
        out = await drive(db, pid)
        assert out["status"] == "FAILED" and "w_organization_social" in out["error"]
        retried = await act(db, pid, "retry")
        assert retried["status"] == "APPROVED"
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        monkeypatch.setattr(settings, "LINKEDIN_ADS_VERSION", "202601")
        pid, _ = await make_post(db, "linkedin", fmt="text")
        await act(db, pid, "submit")
        bad = await drive(db, pid)
        assert bad["status"] == "FAILED" and "version" in bad["error"].lower()


@DB
@pytest.mark.asyncio
async def test_lost_post_answer_is_looked_up_not_reposted(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, faults={"li_post": ["timeout"]})
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="text", text="POVU Dish Gel 500 ml restock notice")
        await act(db, pid, "submit")
        out = await drive(db, pid)
        assert out["status"] == "PUBLISHED" and out["external_post_id"].startswith("urn:li:share:")   # adopted the post that did get created
        assert len(calls(sim, "linkedin")) == 1 and len(sim["li_posts"]) == 1
        assert any(h["event"] == "ADOPTED" for h in out["history"])


@DB
@pytest.mark.asyncio
async def test_linkedin_insights_and_scheduling_by_our_scheduler(sim):
    from datetime import datetime, timedelta, timezone

    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    from app.services import social_service as ss
    ctl(sim, li_asset_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "linkedin", fmt="text", at=datetime.now(timezone.utc) + timedelta(minutes=1))
        assert await ss.publish_due(db, datetime.now(timezone.utc)) == 0 and not calls(sim, "linkedin")     # not due: nothing sent
        await ss.publish_due(db, datetime.now(timezone.utc) + timedelta(minutes=2))
        out = await drive(db, pid)
        assert out["status"] == "PUBLISHED"
        res = await m.insights_refresh(pid, db, __import__("tests.m49_social_helpers", fromlist=["ALICE"]).ALICE)
        got = {r["metric"]: r["value"] for r in res["metrics"]}
        assert got["impressionCount"] == 900 and got["shareCount"] == 2
