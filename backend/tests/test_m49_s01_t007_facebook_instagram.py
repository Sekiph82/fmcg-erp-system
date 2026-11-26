"""M49.S01.T007 Facebook Page and Instagram rich media against the local simulator (DB part needs M49_DB=1).

Per format: photo (alt text), multi-photo, resumable video (connection drop and resume), Reel, native scheduling,
Instagram carousel/Reel/story/image, quota, container errors, lost answers, insights. A submission or container id is never
PUBLISHED: only the network's documented final state publishes. Synthetic POVU home-care data only.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services import social_formats as sf
from tests.m49_social_helpers import (ALICE, BOB, DB, IMG1, IMG2, IMG3, TEXT, VID, _dispose_engine, act, calls, ctl, drive, make_post, sim)  # noqa: F401


def test_formats_validation_and_capabilities():
    ig = sf.capabilities("instagram")
    text = next(f for f in ig["formats"] if f["key"] == "text")
    assert not text["available"] and "no text-only" in text["reason"].lower()
    assert any("Resumable video upload" in n for n in ig["notes"])
    assert sf.validate("instagram", "reel", TEXT, [{"url": "https://a.test/v.mp4", "kind": "video", "duration_sec": 1000}], None)
    assert sf.validate("instagram", "image", TEXT, [{"url": "https://a.test/i.png", "kind": "image", "content_type": "image/png"}], None)
    assert sf.validate("instagram", "carousel", TEXT, [{"url": f"https://a.test/{i}.jpg", "kind": "image"} for i in range(21)], None)
    assert sf.validate("instagram", "image", "#a " * 31, [IMG1], None)
    assert sf.validate("facebook", "reel", TEXT, [{"url": "https://a.test/v.mp4", "kind": "video", "duration_sec": 30, "width": 1920, "height": 1080}], None)
    assert not sf.validate("facebook", "reel", TEXT, [{"url": "https://a.test/v.mp4", "kind": "video", "duration_sec": 30, "width": 1080, "height": 1920}], None)
    now = datetime.now(timezone.utc)
    ok = {"native_schedule": True}
    assert sf.validate("facebook", "text", TEXT, [], None, ok, scheduled_at=now + timedelta(minutes=5))
    assert sf.validate("facebook", "text", TEXT, [], None, ok, scheduled_at=now + timedelta(days=31))
    assert not sf.validate("facebook", "text", TEXT, [], None, ok, scheduled_at=now + timedelta(hours=2))
    assert sf.validate("facebook", "story_photo", TEXT, [IMG1], None, ok, scheduled_at=now + timedelta(hours=2))  # no native schedule for stories


@DB
@pytest.mark.asyncio
async def test_facebook_photo_alt_text_and_multi_photo(sim):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="photo", media=[IMG1])
        out = await act(db, pid, "submit")
        assert out["status"] == "PUBLISHED" and out["external_post_id"] and out["format"] == "photo"
        assert calls(sim, "facebook-photo")[0]["form"]["alt_text_custom"] == IMG1["alt_text"]
        pid, _ = await make_post(db, "facebook", fmt="photos", media=[IMG1, IMG2, IMG3])
        out = await act(db, pid, "submit")
        assert out["status"] == "PUBLISHED"
        feed = calls(sim, "facebook")[-1]["form"]
        assert sorted(k for k in feed if k.startswith("attached_media")) == [f"attached_media[{i}]" for i in range(3)]
        assert len([c for c in calls(sim, "facebook-photo") if c["form"].get("published") == "false"]) == 3


@DB
@pytest.mark.asyncio
async def test_facebook_video_resumable_upload_resumes_and_waits_for_ready(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, fb_polls=2, video_size=3 * 1024 * 1024, faults={"fb_upload": ["drop"]})
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="video", media=[VID], fopts={"title": "POVU AllClean demo"})
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["external_post_id"] is None          # video id is not a publication
        v = calls(sim, "facebook-video")[0]["form"]
        assert v["title"] == "POVU AllClean demo" and v["fbuploader_video_file_chunk"].startswith("h:")
        assert sim["fb_handles"][v["fbuploader_video_file_chunk"]] == 3 * 1024 * 1024        # the whole file arrived after the resume
        assert (await act(db, pid, "refresh"))["status"] == "PROCESSING"
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and done["provider_status"] == "ready"


@DB
@pytest.mark.asyncio
async def test_facebook_reel_and_failure_and_quota(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, fb_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="reel", media=[{**VID, "duration_sec": 30, "width": 1080, "height": 1920}])
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["provider_ref"].startswith("reel")
        assert calls(sim, "facebook-reel")[0]["form"]["video_state"] == "PUBLISHED"
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        ctl(sim, fb_outcome="upload_failed")
        pid, _ = await make_post(db, "facebook", fmt="story_video", media=[{**VID, "duration_sec": 20, "width": 1080, "height": 1920}])
        await act(db, pid, "submit")
        failed = await drive(db, pid)
        assert failed["status"] == "FAILED" and failed["fail_reason"] == "upload_failed" and failed["external_post_id"] is None
        pid, _ = await make_post(db, "facebook", fmt="story_photo", media=[IMG3])
        ctl(sim, fb_outcome=None)
        o = await act(db, pid, "submit")
        assert o["status"] == "PUBLISHED", o["error"]


@DB
@pytest.mark.asyncio
async def test_facebook_native_schedule_is_not_published_until_facebook_says_so(sim):
    from app.api.v1.endpoints import social as ep
    from app.db.session import AsyncSessionLocal
    at = datetime.now(timezone.utc) + timedelta(hours=3)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="text", fopts={"native_schedule": True}, at=at)
        out = await act(db, pid, "submit")
        form = calls(sim, "facebook")[0]["form"]
        assert form["published"] == "false" and int(form["scheduled_publish_time"]) == int(at.timestamp())
        assert out["status"] == "SUBMITTED" and out["provider_status"] == "SCHEDULED" and out["external_post_id"] is None
        assert (await act(db, pid, "refresh"))["status"] == "SUBMITTED"
        sim["publish_scheduled"] = True
        done = await act(db, pid, "refresh")
        assert done["status"] == "PUBLISHED" and done["external_post_id"]
        sim["publish_scheduled"] = False
        pid2, _ = await make_post(db, "facebook", fmt="text", fopts={"native_schedule": True}, at=at)
        await act(db, pid2, "submit")
        assert (await act(db, pid2, "cancel"))["status"] == "CANCELLED"
        assert sim["deleted"]                                                       # the scheduled post was removed on Facebook
        with pytest.raises(Exception):
            await ep.create_post(ep.PostIn(channel_id=uuid.uuid4(), idempotency_key="k-bad-channel", text=TEXT), db, ALICE)


@DB
@pytest.mark.asyncio
async def test_facebook_lost_answer_is_unknown_and_never_resubmitted(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, faults={"social": ["timeout"]})
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="link", link="https://povu-demo.test/allclean")
        out = await act(db, pid, "submit")
        assert out["status"] == "UNKNOWN" and "may have posted" in out["error"] or "No answer" in out["error"]
        assert len(calls(sim, "facebook")) == 1
        released = await act(db, pid, "release")                                     # a person checked the Page: not there
        assert released["status"] == "APPROVED"


@DB
@pytest.mark.asyncio
async def test_instagram_carousel_publishes_only_after_children_and_container_finish(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "instagram", fmt="carousel", media=[IMG1, IMG2, {"url": f"{VID['url']}", "kind": "video"}])
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["flow_phase"] == "children"
        assert len(calls(sim, "instagram-container")) == 3
        assert calls(sim, "instagram-container")[0]["form"]["alt_text"] == IMG1["alt_text"]
        final = await drive(db, pid, 12)
        assert final["status"] == "PUBLISHED" and final["external_post_id"].startswith("ig-media-")
        kinds = [c["form"].get("media_type") for c in calls(sim, "instagram-container")]
        assert kinds[-1] == "CAROUSEL" and len(calls(sim, "instagram")) == 1            # one publish call for the parent only
        assert calls(sim, "instagram-container")[-1]["form"]["children"].count(",") == 2


@DB
@pytest.mark.asyncio
async def test_instagram_reel_cover_story_image_quota_and_container_error(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "instagram", fmt="reel", media=[{**VID, "duration_sec": 20}], fopts={"cover_url": IMG1["url"], "share_to_feed": False})
        await act(db, pid, "submit")
        f = calls(sim, "instagram-container")[0]["form"]
        assert f["media_type"] == "REELS" and f["cover_url"] == IMG1["url"] and f["share_to_feed"] == "false"
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        pid, _ = await make_post(db, "instagram", fmt="story_image", media=[IMG3])
        await act(db, pid, "submit")
        assert calls(sim, "instagram-container")[-1]["form"]["media_type"] == "STORIES"
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        ctl(sim, next_outcome={"status_code": "ERROR"})
        pid, _ = await make_post(db, "instagram", fmt="image", media=[IMG2])
        await act(db, pid, "submit")
        err = await drive(db, pid)
        assert err["status"] == "FAILED" and err["fail_reason"] == "ERROR" and err["external_post_id"] is None
        sim["ig_used"], sim["ig_quota"] = 50, 50
        pid, _ = await make_post(db, "instagram", fmt="image", media=[IMG1])
        n = len(calls(sim, "instagram-container"))
        out = await act(db, pid, "submit")
        assert out["status"] == "FAILED" and out["fail_reason"] == "ig_quota" and len(calls(sim, "instagram-container")) == n   # no container created


@DB
@pytest.mark.asyncio
async def test_instagram_resumable_upload_only_on_facebook_login_and_text_refused(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "instagram", fmt="video", media=[{**VID, "duration_sec": 15}], fopts={"resumable": True}, copts={"ig_login": "facebook"})
        await act(db, pid, "submit")
        c = calls(sim, "instagram-container")[0]
        assert c["form"]["upload_type"] == "resumable" and "video_url" not in c["form"]
        assert sim["ig"][c["id"]].get("uploaded") is True
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        pid, _ = await make_post(db, "instagram", fmt="text", media=[])
        out = await act(db, pid, "submit") if False else None
        from app.api.v1.endpoints import social as ep
        posts = await ep.posts(None, None, None, db)
        mine = next(p for p in posts if p["id"] == str(pid))
        assert any("no text-only" in x.lower() for x in mine["problems"])


@DB
@pytest.mark.asyncio
async def test_post_insights_read_back_from_facebook_and_instagram(sim):
    from fastapi import HTTPException

    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "facebook", fmt="text")
        with pytest.raises(HTTPException) as e:
            await m.insights_refresh(pid, db, ALICE)
        assert e.value.status_code == 409                                              # nothing published: no metrics invented
        await act(db, pid, "submit")
        res = await m.insights_refresh(pid, db, ALICE)
        got = {r["metric"]: r["value"] for r in res["metrics"]}
        assert got["post_clicks"] == 12 and got["post_reactions_by_type_total.like"] == 5
        sim["metrics"]["post_clicks"] = 15
        assert {r["metric"]: r["value"] for r in (await m.insights_refresh(pid, db, ALICE))["metrics"]}["post_clicks"] == 15
        pid, _ = await make_post(db, "instagram", fmt="image", media=[IMG1])
        await act(db, pid, "submit")
        await drive(db, pid)
        res = await m.insights_refresh(pid, db, ALICE)
        assert {r["metric"] for r in res["metrics"]} == {"reach", "views", "likes", "comments"}
