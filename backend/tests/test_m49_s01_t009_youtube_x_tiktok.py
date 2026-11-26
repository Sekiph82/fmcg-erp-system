"""M49.S01.T009 YouTube Data API v3, X API v2 and the TikTok format audit (DB part needs M49_DB=1).

YouTube: resumable upload with 308 resume, processing status, privacy / publishAt scheduling, unverified-project private lock,
quota (ours and Google's), rejection. X: chunked media upload + STATUS polling, text/link/image/gif/video, rate limit, lost answer
looked up (never posted twice), pay-per-use activation note. TikTok: video, photo (up to 35), inbox uploads, creator duration cap,
unaudited private-only. Nothing is PUBLISHED before the provider's documented final state."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import social_formats as sf
from tests.m49_social_helpers import (ALICE, CDN, DB, IMG1, IMG2, IMG3, MB, TEXT, VID, _dispose_engine, act, calls, ctl, drive, make_post, sim, state)  # noqa: F401

YT = {"title": "POVU AllClean 1 L demo", "made_for_kids": False, "tags": ["povu", "cleaning"]}
PHOTO = lambda i: {"url": f"{CDN}/videos/photo{i}.jpg", "kind": "image"}                     # noqa: E731  (verified TikTok prefix)
SELF = {"privacy_level": "SELF_ONLY", "consent": True}


def test_format_rules_and_capability_notes(monkeypatch):
    from app.core.config import settings
    monkeypatch.setitem(settings.__dict__, "YOUTUBE_UNVERIFIED_PRIVATE_ONLY", True)
    yt = sf.capabilities("youtube")
    assert any("unverified" in n and "private" in n for n in yt["notes"])
    assert not next(f for f in yt["formats"] if f["key"] == "text")["available"]
    assert sf.validate("youtube", "video", TEXT, [VID], None, {**YT, "privacy_status": "public"})            # unverified: private only
    assert not sf.validate("youtube", "video", TEXT, [VID], None, {**YT, "privacy_status": "private"})
    assert sf.validate("youtube", "video", TEXT, [VID], None, {"title": "x"})                                # made_for_kids is required
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert sf.validate("youtube", "video", TEXT, [VID], None, {**YT, "privacy_status": "private", "publish_at": future})   # would stay private
    monkeypatch.setitem(settings.__dict__, "YOUTUBE_UNVERIFIED_PRIVATE_ONLY", False)
    assert not sf.validate("youtube", "video", TEXT, [VID], None, {**YT, "privacy_status": "private", "publish_at": future})
    assert sf.validate("youtube", "video", TEXT, [VID], None, {**YT, "privacy_status": "public", "publish_at": future})
    assert sf.validate("youtube", "short", TEXT, [{**VID, "width": 1920, "height": 1080}], None, YT)
    x = sf.capabilities("x")
    assert any("pay-per-use" in n and "$0.20" in n for n in x["notes"])
    assert sf.validate("x", "image", TEXT, [IMG1, {**IMG2, "kind": "video"}], None)
    assert sf.validate("x", "text", "x" * 281, [], None)
    assert not sf.validate("x", "gif", TEXT, [{"url": f"{CDN}/images/a.gif", "kind": "gif"}], None)
    assert sf.validate("tiktok", "photo", "t" * 91, [PHOTO(1)], None)
    assert sf.validate("tiktok", "photo", "t", [PHOTO(i) for i in range(36)], None)
    assert not next(f for f in sf.capabilities("tiktok")["formats"] if f["key"] == "text")["available"]


@DB
@pytest.mark.asyncio
async def test_youtube_resumable_upload_resumes_then_waits_for_processing(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, yt_polls=2, faults={"yt_chunk": ["drop"]})
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts={**YT, "privacy_status": "unlisted", "thumbnail_url": IMG1["url"], "playlist_id": "PLpovu1"})
        out = await act(db, pid, "submit")
        sess = next(iter(sim["yt_sess"].values()))
        assert sess["got"] == sess["size"] == MB and out["status"] == "PROCESSING" and out["external_post_id"] is None   # 4 chunks, resumed after a drop
        init = calls(sim, "youtube-init")[0]["json"]
        assert init["status"]["privacyStatus"] == "unlisted" and init["status"]["selfDeclaredMadeForKids"] is False and init["snippet"]["tags"] == ["povu", "cleaning"]
        assert out["provider_ref"].startswith("ytv")
        mid = await act(db, pid, "refresh")
        assert mid["status"] == "PROCESSING" and mid["provider_status"] == "uploaded"
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and done["provider_status"] == "processed"
        assert calls(sim, "youtube-thumbnail") and calls(sim, "youtube-playlist")


@DB
@pytest.mark.asyncio
async def test_youtube_unverified_project_is_private_only(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    ctl(sim, yt_polls=0)
    monkeypatch.setitem(settings.__dict__, "YOUTUBE_UNVERIFIED_PRIVATE_ONLY", True)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts={**YT, "privacy_status": "public"}, approve=False)
        from app.api.v1.endpoints import social as ep
        assert any("private" in x for x in (await state(db, pid))["problems"])
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts={**YT, "privacy_status": "private"})
        out = await act(db, pid, "submit")
        assert calls(sim, "youtube-init")[-1]["json"]["status"]["privacyStatus"] == "private"
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        # a verified channel may go public; YouTube itself locking the video private is reported, not hidden
        monkeypatch.setitem(settings.__dict__, "YOUTUBE_UNVERIFIED_PRIVATE_ONLY", False)
        ctl(sim, yt_unverified=True)
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts={**YT, "privacy_status": "public"})
        await act(db, pid, "submit")
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and any("locked to private" in h["detail"] for h in done["history"])


@DB
@pytest.mark.asyncio
async def test_youtube_publish_at_is_scheduled_not_published(sim, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.db.session import AsyncSessionLocal
    from app.services import social_service as ss
    ctl(sim, yt_polls=0)
    at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts={**YT, "privacy_status": "private", "publish_at": at})
        await ss.publish_due(db)                                           # publishAt hands the schedule to YouTube straight away
        out = await state(db, pid)
        assert out["status"] in ("PROCESSING", "SUBMITTED") and calls(sim, "youtube-init")[0]["json"]["status"]["publishAt"] == at
        out = await drive(db, pid)
        assert out["status"] != "PUBLISHED" and out["provider_status"] == "SCHEDULED"
        sim["yt_publish_scheduled"] = True
        assert (await act(db, pid, "refresh"))["status"] == "PUBLISHED"


@DB
@pytest.mark.asyncio
async def test_youtube_quota_rejection_and_failures(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    ctl(sim, yt_polls=0, yt_quota=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts=YT)
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts=YT)
        out = await act(db, pid, "submit")                                  # Google answers quotaExceeded
        assert out["status"] == "FAILED" and out["fail_reason"] == "quotaExceeded" and "midnight Pacific" in out["error"]
        monkeypatch.setitem(settings.__dict__, "YOUTUBE_UPLOAD_QUOTA_PER_DAY", 1)
        sim["yt_quota"] = 100
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts=YT)
        n = len(calls(sim, "youtube-init"))
        out = await act(db, pid, "submit")                                  # our own counter refuses before any provider call
        assert out["status"] == "FAILED" and out["fail_reason"] == "quota_exhausted" and len(calls(sim, "youtube-init")) == n
        monkeypatch.setitem(settings.__dict__, "YOUTUBE_UPLOAD_QUOTA_PER_DAY", 100)
        ctl(sim, yt_outcome="rejected")
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts=YT)
        await act(db, pid, "submit")
        rej = await drive(db, pid)
        assert rej["status"] == "FAILED" and rej["fail_reason"] == "duplicate" and rej["external_post_id"] is None
        ctl(sim, yt_outcome="failed", faults={"yt_chunk": ["expire"]})
        pid, _ = await make_post(db, "youtube", fmt="video", media=[VID], fopts=YT)
        out = await act(db, pid, "submit")
        assert out["status"] in ("FAILED", "PROCESSING", "SUBMITTED", "UNKNOWN") and out["external_post_id"] is None


@DB
@pytest.mark.asyncio
async def test_youtube_statistics_insights(sim):
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    ctl(sim, yt_polls=0)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "youtube", fmt="short", media=[{**VID, "width": 1080, "height": 1920, "duration_sec": 30}], fopts=YT)
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "PUBLISHED"
        res = await m.insights_refresh(pid, db, ALICE)
        assert {r["metric"]: r["value"] for r in res["metrics"]}["viewCount"] == 321


@DB
@pytest.mark.asyncio
async def test_x_text_link_media_and_media_processing(sim):
    from app.db.session import AsyncSessionLocal
    ctl(sim, x_media_polls=2)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "x", text="POVU Hand Wash Powder 1 kg: back in stock.")
        out = await act(db, pid, "submit")
        assert out["status"] == "PUBLISHED" and out["format"] == "text" and out["external_post_id"]
        pid, _ = await make_post(db, "x", text="Shop POVU", link="https://povu-demo.test/shop")
        out = await act(db, pid, "submit")
        assert out["format"] == "link" and any("$0.20" in h["detail"] for h in out["history"])
        plain = [{"url": m["url"], "kind": "image"} for m in (IMG1, IMG2, IMG3)]      # X alt text (media/metadata) is not built
        pid, _ = await make_post(db, "x", fmt="image", media=plain)
        out = await act(db, pid, "submit")
        assert out["status"] == "PUBLISHED" and len(calls(sim, "x")[-1]["json"]["media"]["media_ids"]) == 3
        pid, _ = await make_post(db, "x", fmt="video", media=[VID])
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["external_post_id"] is None and out["flow_phase"] == "media"      # tweet only after STATUS succeeded
        n = len(calls(sim, "x"))
        assert (await act(db, pid, "refresh"))["status"] == "PROCESSING" and len(calls(sim, "x")) == n
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and len(calls(sim, "x")) == n + 1
        ctl(sim, x_media_outcome="failed")
        pid, _ = await make_post(db, "x", fmt="video", media=[VID])
        await act(db, pid, "submit")
        bad = await drive(db, pid)
        assert bad["status"] == "FAILED" and bad["fail_reason"] == "media_failed"


@DB
@pytest.mark.asyncio
async def test_x_rate_limit_and_lost_answer_never_post_twice(sim):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        ctl(sim, faults={"x_tweet": ["429"]})
        pid, _ = await make_post(db, "x", text="POVU AllClean refill pouch is here.", ext=__import__("uuid").uuid4().hex[:10])
        out = await act(db, pid, "submit")
        assert out["status"] == "UNKNOWN" and "rate limit" in out["error"]
        assert (await act(db, pid, "refresh"))["status"] == "UNKNOWN"          # looked up on the account: not there, not resubmitted
        assert not calls(sim, "x")
        assert (await act(db, pid, "release"))["status"] == "APPROVED"
        assert (await act(db, pid, "submit"))["status"] == "PUBLISHED" and len(calls(sim, "x")) == 1
        ctl(sim, faults={"x_tweet": ["timeout"]})
        pid, _ = await make_post(db, "x", text="POVU Dish Gel 500 ml, lemon.", ext=__import__("uuid").uuid4().hex[:10])
        out = await act(db, pid, "submit")
        assert out["status"] == "PUBLISHED" and len(calls(sim, "x")) == 2      # the answer was lost; the lookup adopted the post
        assert [h["event"] for h in out["history"]].count("UNKNOWN") == 1 and "lookup found" in out["history"][-1]["detail"]


@DB
@pytest.mark.asyncio
async def test_x_metrics(sim):
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "x", text="POVU metrics check")
        await act(db, pid, "submit")
        res = await m.insights_refresh(pid, db, ALICE)
        assert {r["metric"]: r["value"] for r in res["metrics"]} == {"like_count": 9, "retweet_count": 1, "reply_count": 2, "impression_count": 700}


@DB
@pytest.mark.asyncio
async def test_tiktok_photo_inbox_and_creator_duration(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=1)
    async with AsyncSessionLocal() as db:
        pid, _ = await make_post(db, "tiktok", fmt="photo", media=[PHOTO(1), PHOTO(2), PHOTO(3)], text="POVU laundry day", tiktok=SELF,
                                 fopts={"description": "Hand wash powder, 1 kg pouch", "photo_cover_index": 1})
        out = await act(db, pid, "submit")
        assert out["status"] == "PROCESSING" and out["provider_ref"].startswith("p_pub_url~")
        body = calls(sim, "tiktok-photo")[0]["json"]
        assert body["media_type"] == "PHOTO" and body["post_mode"] == "DIRECT_POST" and len(body["source_info"]["photo_images"]) == 3
        assert body["source_info"]["photo_cover_index"] == 1 and body["post_info"]["privacy_level"] == "SELF_ONLY" and body["post_info"]["title"] == "POVU laundry day"
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and done["external_post_id"] is None            # private: TikTok gives no public id
        pid, _ = await make_post(db, "tiktok", fmt="video_inbox", media=[VID], tiktok=SELF)
        out = await act(db, pid, "submit")
        inbox = await drive(db, pid)
        assert calls(sim, "tiktok-inbox")[0]["json"].get("post_info") is None
        assert inbox["status"] == "EXPORTED" and inbox["provider_status"] == "SEND_TO_USER_INBOX" and inbox["external_post_id"] is None   # a draft, not a post
        pid, _ = await make_post(db, "tiktok", fmt="photo_inbox", media=[PHOTO(4)], tiktok=SELF)
        await act(db, pid, "submit")
        assert (await drive(db, pid))["status"] == "EXPORTED"
        pid, _ = await make_post(db, "tiktok", fmt="video", media=[{**VID, "duration_sec": 400}], tiktok=SELF)      # creator max is 300 s
        out = await act(db, pid, "submit")
        assert out["status"] == "FAILED" and out["fail_reason"] == "duration_check_failed"
        pid, _ = await make_post(db, "tiktok", fmt="video", media=[VID], tiktok=SELF,
                                 fopts={"video_cover_timestamp_ms": 1500, "brand_content_toggle": False, "is_aigc": False})
        await act(db, pid, "submit")
        pi = calls(sim, "tiktok")[-1]["json"]["post_info"]
        assert pi["video_cover_timestamp_ms"] == 1500 and pi["is_aigc"] is False and pi["privacy_level"] == "SELF_ONLY"


@DB
@pytest.mark.asyncio
async def test_tiktok_unverified_photo_url_refused_and_public_needs_audit(sim, monkeypatch):
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        from fastapi import HTTPException

        from app.api.v1.endpoints import social as ep
        pid, _ = await make_post(db, "tiktok", fmt="photo", media=[{"url": "https://other.example.com/p.jpg", "kind": "image"}], approve=False)
        with pytest.raises(HTTPException) as e:
            await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(**SELF), db, ALICE)
        assert e.value.status_code == 422 and "verified" in e.value.detail
        pid, _ = await make_post(db, "tiktok", fmt="photo", media=[PHOTO(5)], approve=False)
        with pytest.raises(HTTPException) as e:
            await ep.set_tiktok_options(pid, ep.TikTokOptionsIn(privacy_level="PUBLIC_TO_EVERYONE", consent=True), db, ALICE)
        assert e.value.status_code == 422 and "not audited" in e.value.detail
        monkeypatch.setattr(settings, "TIKTOK_APP_AUDITED", True)
        ctl(sim, audited=True, processing_polls=0)
        pid, _ = await make_post(db, "tiktok", fmt="photo", media=[PHOTO(7)], tiktok={"privacy_level": "PUBLIC_TO_EVERYONE", "consent": True})
        await act(db, pid, "submit")
        done = await drive(db, pid)
        assert done["status"] == "PUBLISHED" and done["external_post_id"]
        from app.api.v1.endpoints import social_m49 as m
        res = await m.insights_refresh(pid, db, ALICE)
        assert {r["metric"] for r in res["metrics"]} == {"like_count", "comment_count", "share_count", "view_count"}
