"""Provider flows for rich organic-social formats (M49.S01.T007-T009). Called by social_service.publish()/refresh().

Official contracts (checked in coordination/milestones/M48/CAPABILITY_MATRIX.md, 2026-11-26):
- Facebook Pages + Instagram: Graph API v27.0. https://developers.facebook.com/docs/pages-api/posts ,
  /docs/video-api/guides/publishing (Resumable Upload API: POST /{app}/uploads -> POST /upload:{id} file_offset -> h; then
  POST graph-video.facebook.com/{page}/videos fbuploader_video_file_chunk), /docs/video-api/guides/reels-publishing
  (video_reels start/upload/finish), /docs/page-stories-api, /docs/instagram-platform/content-publishing/
  (containers, carousel children, status_code, content_publishing_limit, rupload resumable on Facebook Login only).
- LinkedIn Community Management, Linkedin-Version 202611: Posts, Images, Videos (initializeUpload/finalizeUpload), MultiImage.
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api (+ images-api, videos-api,
  multiimage-post-api, organizations/share-statistics).
- TikTok Content Posting API v2: video/init, inbox/video/init, content/init (photo), status/fetch.
  https://developers.tiktok.com/doc/content-posting-api-reference-photo-post
- YouTube Data API v3: resumable videos.insert, videos.list, thumbnails.set, playlistItems.insert.
  https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
- X API v2: /2/media/upload/{initialize,append,finalize}, GET /2/media/upload?command=STATUS, POST /2/tweets.
  https://docs.x.com/x-api/media/quickstart/media-upload-chunked

State: a multi-step flow keeps its checkpoint in SocialPost.flow_state; provider_ref is the id the provider will report on
(video id, container id, asset urn, upload id). A step never reports PUBLISHED before the provider's documented final state;
a mutating call whose answer is lost becomes UNKNOWN and is looked up on the network (never resubmitted).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import provider_client
from app.models.crm import SocialChannel, SocialPost
from app.models.m49_social import SocialPostMetric, SocialQuotaUse
from app.services import social_service as ss
from app.services.social_formats import MB, cfg

SocialError = ss.SocialError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fs(post: SocialPost) -> dict:
    return dict(post.flow_state or {})


def _set(post: SocialPost, **kw) -> None:
    post.flow_state = {**(post.flow_state or {}), **kw}


def _fo(post: SocialPost) -> dict:
    return post.format_options or {}


async def _fetch(c: httpx.AsyncClient, url: str, cap: Optional[int] = None) -> tuple[bytes, str]:
    r = await c.get(url)
    if r.status_code != 200:
        raise SocialError(f"could not read the media file (HTTP {r.status_code})", "file_unreadable")
    if cap and len(r.content) > cap:
        raise SocialError(f"the media file is {len(r.content) // MB} MB; the limit is {cap // MB} MB", "file_too_large")
    return r.content, r.headers.get("content-type", "application/octet-stream").split(";")[0]


def _reject(post: SocialPost, msg: str, code: str) -> None:
    raise SocialError(msg, code)


# ═════════════════ Facebook Page ═════════════════

def _fb_vid(path: str) -> str:
    return f"{cfg('META_VIDEO_API_URL', settings.META_ADS_API_URL).rstrip('/')}/{settings.META_ADS_API_VERSION}/{path}"


def _oauth() -> dict:
    return {"Authorization": f"OAuth {settings.META_PAGE_ACCESS_TOKEN}"}


async def fb_upload_handle(c: httpx.AsyncClient, ch: SocialChannel, blob: bytes, name: str, ctype: str) -> str:
    """Resumable Upload API. After a dropped connection the offset is read back and the upload continues from it."""
    app_id = (ch.options or {}).get("app_id") or cfg("META_APP_ID", "")
    if not app_id:
        raise SocialError("facebook: the Meta app id is not configured (channel option app_id or META_APP_ID)", "no_app_id")
    sess = ss._ok(await c.post(ss._graph(f"{app_id}/uploads"), params={"file_name": name, "file_length": len(blob), "file_type": ctype},
                               headers=ss._meta_h()), "facebook")["id"]
    offset = 0
    for attempt in range(4):
        try:
            b = ss._ok(await c.post(ss._graph(sess), content=blob[offset:], headers={**_oauth(), "file_offset": str(offset)}), "facebook")
            if b.get("h"):
                return b["h"]
            raise SocialError("facebook: the upload finished without a file handle", "no_handle")
        except httpx.TransportError:
            if attempt == 3:
                raise
            offset = int(ss._ok(await c.get(ss._graph(sess), headers=_oauth()), "facebook").get("file_offset", 0))
    raise SocialError("facebook: upload did not complete", "upload_failed", True)


def _fb_after(post: SocialPost, node_id: str, sched: Optional[int], kind: str) -> None:
    if sched:        # scheduled on Facebook: the post exists but is not live until the time
        _set(post, kind=kind)
        ss._submitted(post, node_id, "SUBMITTED")
        post.provider_status = "SCHEDULED"
    else:
        ss._published(post, node_id, f"facebook returned the created post")


async def _fb_reel_like(c, ch, post, edge: str, blob: bytes, sched: Optional[int], state: str) -> None:
    start = ss._ok(await c.post(ss._graph(f"{ch.external_id}/{edge}"), data={"upload_phase": "start"}, headers=ss._meta_h()), "facebook")
    vid = start["video_id"]
    _set(post, kind="fb_video", phase="uploading", video_id=vid)
    ss._submitted(post, vid, "PROCESSING")
    r = await c.post(start.get("upload_url") or f"{cfg('META_RUPLOAD_URL', settings.META_ADS_API_URL).rstrip('/')}/video-upload/{vid}",
                     content=blob, headers={**_oauth(), "offset": "0", "file_size": str(len(blob))})
    ss._ok(r, "facebook")
    fin = {"upload_phase": "finish", "video_id": vid, "video_state": state, "description": post.text, "title": _fo(post).get("title", "")[:100]}
    if sched:
        fin["scheduled_publish_time"] = str(sched)
    ss._ok(await c.post(ss._graph(f"{ch.external_id}/{edge}"), data=fin, headers=ss._meta_h()), "facebook")
    _set(post, phase="published_requested")


async def fb_submit(db: AsyncSession, c: httpx.AsyncClient, ch: SocialChannel, post: SocialPost) -> None:
    fmt, fo, page = post.format, _fo(post), ch.external_id
    sched = int(post.scheduled_at.timestamp()) if fo.get("native_schedule") and post.scheduled_at else None
    sch = {"published": "false", "scheduled_publish_time": str(sched)} if sched else {}
    h = ss._meta_h()
    if fmt in ("text", "link"):
        data = {"message": post.text, **({"link": post.link} if post.link else {}), **sch}
        _fb_after(post, ss._ok(await c.post(ss._graph(f"{page}/feed"), data=data, headers=h), "facebook")["id"], sched, "fb_post")
    elif fmt == "photo":
        m = post.media[0]
        data = {"url": m["url"], "caption": post.text, **({"alt_text_custom": m["alt_text"]} if m.get("alt_text") else {}), **sch}
        b = ss._ok(await c.post(ss._graph(f"{page}/photos"), data=data, headers=h), "facebook")
        _fb_after(post, b.get("post_id") or b["id"], sched, "fb_post")
    elif fmt == "photos":
        ids = _fs(post).get("photo_ids", [])
        for m in post.media[len(ids):]:     # unpublished photos are harmless if a later step fails
            d = {"url": m["url"], "published": "false", **({"alt_text_custom": m["alt_text"]} if m.get("alt_text") else {})}
            ids.append(ss._ok(await c.post(ss._graph(f"{page}/photos"), data=d, headers=h), "facebook")["id"])
            _set(post, photo_ids=ids)
        data = {"message": post.text, **{f"attached_media[{i}]": json.dumps({"media_fbid": x}) for i, x in enumerate(ids)}, **sch}
        _fb_after(post, ss._ok(await c.post(ss._graph(f"{page}/feed"), data=data, headers=h), "facebook")["id"], sched, "fb_post")
    elif fmt == "video":
        blob, ctype = await _fetch(c, post.media[0]["url"])
        handle = await fb_upload_handle(c, ch, blob, "video.mp4", ctype)
        data = {"title": fo.get("title", "")[:100], "description": post.text, "fbuploader_video_file_chunk": handle, **sch}
        vid = ss._ok(await c.post(_fb_vid(f"{page}/videos"), data=data, headers=h), "facebook")["id"]
        _set(post, kind="fb_video", phase="published_requested", video_id=vid)
        ss._submitted(post, vid, "PROCESSING")
        post.provider_status = "SCHEDULED" if sched else post.provider_status
    elif fmt == "reel":
        used = (await db.execute(select(func.count()).select_from(SocialPost).where(
            SocialPost.channel_id == ch.id, SocialPost.format == "reel", SocialPost.id != post.id,
            SocialPost.claimed_at > _now() - timedelta(hours=24), SocialPost.status.notin_(["FAILED", "CANCELLED", "DRAFT"])))).scalar()
        if used >= 30:
            raise SocialError("facebook: 30 API-published Reels per 24 hours already used for this Page", "reel_quota")
        blob, _ = await _fetch(c, post.media[0]["url"])
        await _fb_reel_like(c, ch, post, "video_reels", blob, sched, "SCHEDULED" if sched else "PUBLISHED")
    elif fmt == "story_photo":
        pid = ss._ok(await c.post(ss._graph(f"{page}/photos"), data={"url": post.media[0]["url"], "published": "false"}, headers=h), "facebook")["id"]
        b = ss._ok(await c.post(ss._graph(f"{page}/photo_stories"), data={"photo_id": pid}, headers=h), "facebook")
        ss._published(post, b.get("post_id") or pid, "facebook created the photo story")
    elif fmt == "story_video":
        blob, _ = await _fetch(c, post.media[0]["url"])
        await _fb_reel_like(c, ch, post, "video_stories", blob, None, "PUBLISHED")
    else:
        raise SocialError(f"facebook: unsupported format {fmt}", "unsupported_format")


async def fb_advance(db, ch, post) -> None:
    st = _fs(post)
    if st.get("kind") == "fb_post":
        d = await ss._read(lambda c: _get(c, ss._graph(post.provider_ref), {"fields": "is_published,scheduled_publish_time"}, ss._meta_h(), "facebook"))
        post.provider_status = "PUBLISHED" if d.get("is_published") else "SCHEDULED"
        if d.get("is_published"):
            ss._published(post, post.provider_ref, "facebook reports is_published")
        return
    d = await ss._read(lambda c: _get(c, ss._graph(post.provider_ref), {"fields": "status"}, ss._meta_h(), "facebook"))
    s = d.get("status") or {}
    vs = post.provider_status = str(s.get("video_status") or "")[:40]
    pub = (s.get("publishing_phase") or {}).get("publish_status")
    if vs in ("error", "expired", "upload_failed"):
        ss._failed(post, vs, f"Facebook video {vs}: {json.dumps(s)[:200]}")
    elif pub == "scheduled":
        post.provider_status = "SCHEDULED"
    elif vs == "ready" and pub in (None, "published"):
        ss._published(post, post.provider_ref, "facebook video_status ready and published")
    else:
        post.status = "PROCESSING" if post.status != "UNKNOWN" else post.status


async def _get(c, url, params, headers, net) -> dict:
    return ss._ok(await c.get(url, params=params, headers=headers), net)


# ═════════════════ Instagram ═════════════════

IG_FIELDS = "status_code,status"


async def ig_quota(c, ig: str) -> dict:
    d = ss._ok(await c.get(ss._graph(f"{ig}/content_publishing_limit"), params={"fields": "quota_usage,config"}, headers=ss._meta_h()), "instagram")
    row = (d.get("data") or [{}])[0]
    return {"used": row.get("quota_usage", 0), "total": (row.get("config") or {}).get("quota_total")}


async def _ig_container(c, ig: str, params: dict) -> str:
    return ss._ok(await c.post(ss._graph(f"{ig}/media"), data=params, headers=ss._meta_h()), "instagram")["id"]


def _ig_params(post: SocialPost, m: dict, *, child: bool = False) -> dict:
    p: dict = {}
    if m["kind"] == "video":
        p["video_url"] = m["url"]
        if not child:
            p["media_type"] = "VIDEO"
    else:
        p["image_url"] = m["url"]
        if m.get("alt_text"):
            p["alt_text"] = m["alt_text"]
    if child:
        p["is_carousel_item"] = "true"
        if m["kind"] == "video":
            p["media_type"] = "VIDEO"
    return p


async def ig_submit(db, c, ch, post) -> None:
    fmt, fo, ig = post.format, _fo(post), ch.external_id
    q = await ig_quota(c, ig)
    if q["total"] is not None and q["used"] >= q["total"]:
        raise SocialError(f"instagram: the 24-hour publishing quota is used up ({q['used']}/{q['total']})", "ig_quota")
    caption = {"caption": post.text} if post.text else {}
    if fmt == "carousel":
        kids = _fs(post).get("children", [])
        for m in post.media[len(kids):]:
            kids.append(await _ig_container(c, ig, _ig_params(post, m, child=True)))
            _set(post, children=kids)
        _set(post, kind="ig_carousel", phase="children")
        ss._submitted(post, kids[0], "PROCESSING")
        return
    m = post.media[0]
    p = {**caption}
    if fmt == "image":
        p.update(_ig_params(post, m))
    elif fmt == "video":
        p.update(_ig_params(post, m))
    elif fmt == "reel":
        p.update({"media_type": "REELS", "video_url": m["url"], "share_to_feed": str(bool(fo.get("share_to_feed", True))).lower()})
        if fo.get("cover_url"):
            p["cover_url"] = fo["cover_url"]
        elif fo.get("thumb_offset_ms") is not None:
            p["thumb_offset"] = str(int(fo["thumb_offset_ms"]))
    elif fmt in ("story_image", "story_video"):
        p = {"media_type": "STORIES", **_ig_params(post, m)}
        p.pop("caption", None)
    if fo.get("resumable") and (ch.options or {}).get("ig_login") == "facebook" and m["kind"] == "video":
        p.pop("video_url", None)
        p["upload_type"] = "resumable"
        blob, _ = await _fetch(c, m["url"])
        cid = await _ig_container(c, ig, p)
        _set(post, kind="ig_container")
        ss._submitted(post, cid, "PROCESSING")
        await db.commit()
        ss._ok(await c.post(f"{cfg('META_RUPLOAD_URL', settings.META_ADS_API_URL).rstrip('/')}/ig-api-upload/{settings.META_ADS_API_VERSION}/{cid}",
                            content=blob, headers={**_oauth(), "offset": "0", "file_size": str(len(blob))}), "instagram")
        return
    _set(post, kind="ig_container")
    ss._submitted(post, await _ig_container(c, ig, p), "PROCESSING")


async def ig_advance(db, ch, post) -> bool:
    """Carousel child polling and parent creation. Returns True when the single-container logic should continue."""
    st = _fs(post)
    if st.get("phase") != "children":
        return True
    kids = st["children"]
    codes = []
    for k in kids:
        d = await ss._read(lambda c, k=k: _get(c, ss._graph(k), {"fields": IG_FIELDS}, ss._meta_h(), "instagram"))
        codes.append(str(d.get("status_code") or ""))
    post.provider_status = ",".join(sorted(set(codes)))[:40]
    if any(x in ("ERROR", "EXPIRED") for x in codes):
        ss._failed(post, "carousel_child", f"A carousel item failed at Instagram ({', '.join(codes)})")
        return False
    if all(x == "FINISHED" for x in codes):
        async with provider_client() as c:
            cid = await _ig_container(c, ch.external_id, {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": post.text})
        _set(post, phase="container")
        post.provider_ref = cid
        ss.log(post, "CONTAINER", f"carousel container {cid} from {len(kids)} items")
    return False


# ═════════════════ LinkedIn ═════════════════

def _li(path: str) -> str:
    return f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/{path}"


def _li_h() -> dict:
    return {"Authorization": f"Bearer {settings.LINKEDIN_SOCIAL_ACCESS_TOKEN}", "LinkedIn-Version": settings.LINKEDIN_ADS_VERSION,
            "X-Restli-Protocol-Version": "2.0.0"}


async def li_upload_image(c, owner: str, blob: bytes) -> str:
    v = ss._ok(await c.post(_li("images?action=initializeUpload"), json={"initializeUploadRequest": {"owner": owner}}, headers=_li_h()), "linkedin")["value"]
    r = await c.put(v["uploadUrl"], content=blob, headers={"Authorization": _li_h()["Authorization"], "Content-Type": "application/octet-stream"})
    if r.status_code >= 400:
        raise SocialError(f"linkedin: image upload answered HTTP {r.status_code}", f"upload_{r.status_code}", r.status_code >= 500)
    return v["image"]


async def li_upload_video(c, owner: str, blob: bytes, thumb: Optional[bytes]) -> str:
    body = {"initializeUploadRequest": {"owner": owner, "fileSizeBytes": len(blob), "uploadCaptions": False, "uploadThumbnail": bool(thumb)}}
    v = ss._ok(await c.post(_li("videos?action=initializeUpload"), json=body, headers=_li_h()), "linkedin")["value"]
    etags = []
    for part in v["uploadInstructions"]:
        chunk = blob[part["firstByte"]:part["lastByte"] + 1]

        async def put(cl, chunk=chunk, url=part["uploadUrl"]):
            r = await cl.put(url, content=chunk, headers={"Content-Type": "application/octet-stream"})
            if r.status_code >= 400:
                raise SocialError(f"linkedin: video part upload answered HTTP {r.status_code}", f"upload_{r.status_code}", r.status_code >= 500)
            return r.headers.get("etag", "")
        etags.append(await ss._read(put))          # a part PUT is idempotent: retried with backoff
    if thumb and v.get("thumbnailUploadUrl"):
        await c.put(v["thumbnailUploadUrl"], content=thumb, headers={"Content-Type": "application/octet-stream"})
    ss._ok(await c.post(_li("videos?action=finalizeUpload"), json={"finalizeUploadRequest": {
        "video": v["video"], "uploadToken": v.get("uploadToken", ""), "uploadedPartIds": etags}}, headers=_li_h()), "linkedin")
    return v["video"]


def _li_asset_path(urn: str) -> str:
    return ("images/" if ":image:" in urn else "videos/") + quote(urn, safe="")


def _li_body(post: SocialPost, owner: str, assets: list[dict]) -> dict:
    fmt, fo = post.format, _fo(post)
    body = {"author": owner, "commentary": post.text, "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    media = [a for a in assets if a["role"] == "media"]
    alts = [m.get("alt_text") for m in post.media]
    if fmt == "image":
        body["content"] = {"media": {"id": media[0]["urn"], **({"altText": alts[0]} if alts[0] else {})}}
    elif fmt == "images":
        body["content"] = {"multiImage": {"images": [{"id": a["urn"], **({"altText": alts[i]} if alts[i] else {})} for i, a in enumerate(media)]}}
    elif fmt == "video":
        body["content"] = {"media": {"id": media[0]["urn"], "title": fo.get("video_title", "")[:100] or "POVU video"}}
    elif fmt == "link":
        art = {"source": post.link, "title": fo["article_title"][:200], "description": (fo.get("article_description") or "")[:300]}
        th = next((a for a in assets if a["role"] == "thumb"), None)
        if th:
            art["thumbnail"] = th["urn"]
        body["content"] = {"article": art}
    return body


async def li_submit(db, c, ch, post) -> None:
    owner = f"urn:li:organization:{ch.external_id}"
    fmt = post.format
    assets: list[dict] = []
    if fmt in ("image", "images"):
        for m in post.media:
            blob, _ = await _fetch(c, m["url"], 36 * MB)
            assets.append({"urn": await li_upload_image(c, owner, blob), "role": "media"})
    elif fmt == "video":
        blob, _ = await _fetch(c, post.media[0]["url"], 500 * MB)
        thumb = (await _fetch(c, post.media[0]["thumbnail_url"], 10 * MB))[0] if post.media[0].get("thumbnail_url") else None
        assets.append({"urn": await li_upload_video(c, owner, blob, thumb), "role": "media"})
    elif fmt == "link" and _fo(post).get("article_thumbnail_url"):
        blob, _ = await _fetch(c, _fo(post)["article_thumbnail_url"], 10 * MB)
        assets.append({"urn": await li_upload_image(c, owner, blob), "role": "thumb"})
    _set(post, kind="li", phase="assets" if assets else "create", assets=assets, owner=owner)
    ss._submitted(post, assets[0]["urn"] if assets else f"lookup:{post.idempotency_key[:40]}", "PROCESSING")
    if not assets:
        _set(post, phase="create")


async def _li_find(c, post: SocialPost) -> Optional[str]:
    """After a lost answer: the post is ours if the author's recent posts hold the same commentary created after the claim."""
    d = ss._ok(await c.get(_li("posts"), params={"q": "author", "author": _fs(post)["owner"], "count": 10, "sortBy": "LAST_MODIFIED"},
                           headers={**_li_h(), "X-RestLi-Method": "FINDER"}), "linkedin")
    floor = int((post.claimed_at or _now()).timestamp() * 1000) - 60_000
    for e in d.get("elements", []):
        if e.get("commentary") == post.text and int(e.get("createdAt", 0)) >= floor:
            return e["id"]
    return None


async def li_advance(db, ch, post) -> None:
    st = _fs(post)
    phase = st.get("phase")
    if phase == "assets":
        states = []
        for a in st["assets"]:
            d = await ss._read(lambda c, a=a: _get(c, _li(_li_asset_path(a["urn"])), None, _li_h(), "linkedin"))
            states.append(str(d.get("status") or ""))
            if d.get("status") == "PROCESSING_FAILED":
                ss._failed(post, "asset_failed", f"LinkedIn could not process the media: {d.get('processingFailureReason') or 'no reason given'}")
                return
        post.provider_status = ",".join(sorted(set(states)))[:40]
        if not all(s == "AVAILABLE" for s in states):
            return
        phase = "create"
    if phase == "create":
        _set(post, phase="creating")
        await db.commit()                                      # the claim of the create call is durable
        try:
            async with provider_client() as c:
                r = await c.post(_li("posts"), json=_li_body(post, st["owner"], st.get("assets", [])), headers=_li_h())
            if r.status_code >= 400:
                ss._ok(r, "linkedin")
            urn = r.headers.get("x-restli-id")
            if not urn:
                raise SocialError("linkedin: created without a post id", "no_id", True)
        except (httpx.HTTPError, SocialError) as e:
            if isinstance(e, SocialError) and not e.retryable:
                ss._failed(post, e.code, str(e))
                return
            _set(post, phase="lookup")                         # never post twice: look the post up instead
            post.provider_ref = f"lookup:{post.idempotency_key[:40]}"
            ss._unknown(post, f"No confirmed answer to the LinkedIn post call ({type(e).__name__}); looking it up on the page.")
            return
        _set(post, phase="post")
        post.provider_ref = urn
        ss.log(post, "POST_CREATED", urn)
        phase = "post"
    if phase == "creating":                                    # crashed between the claim and the answer
        phase = "lookup"
    if phase == "lookup":
        found = await ss._read(lambda c: _li_find(c, post))
        if not found:
            ss.log(post, "NOT_FOUND_YET", "the post is not on the page; it is not resubmitted automatically")
            return
        _set(post, phase="post")
        post.provider_ref = found
        ss.log(post, "ADOPTED", f"found {found} on the page")
    d = await ss._read(lambda c: _get(c, _li(f"posts/{quote(post.provider_ref, safe='')}"), {"viewContext": "AUTHOR"}, _li_h(), "linkedin"))
    lc = post.provider_status = str(d.get("lifecycleState") or "")[:40]
    if lc == "PUBLISHED":
        ss._published(post, post.provider_ref, "LinkedIn lifecycleState PUBLISHED")
    elif lc == "PUBLISH_FAILED":
        ss._failed(post, lc, "LinkedIn could not publish the post (PUBLISH_FAILED)")
    elif post.status == "SUBMITTED":
        post.status = "PROCESSING"


# ═════════════════ TikTok: photo and inbox formats ═════════════════

async def tt_submit_ext(db, c, post: SocialPost) -> None:
    fmt, fo = post.format, _fo(post)
    inbox = fmt.endswith("_inbox")
    o = post.publish_options or {}
    if fmt.startswith("photo"):
        info = await ss.tiktok_creator_info(c) if not inbox else None
        pi = {"title": (fo.get("title") or post.text)[:90], "description": (fo.get("description") or "")[:4000],
              "disable_comment": bool(o.get("disable_comment")), "auto_add_music": bool(fo.get("auto_add_music", True))}
        if not inbox:
            if o.get("privacy_level") not in info["privacy_level_options"]:
                raise SocialError(f"tiktok: privacy {o.get('privacy_level')} is not offered for this creator", "privacy_level_option_mismatch")
            pi["privacy_level"] = o["privacy_level"]
            pi["disable_comment"] = pi["disable_comment"] or info["comment_disabled"]
        body = {"media_type": "PHOTO", "post_mode": "MEDIA_UPLOAD" if inbox else "DIRECT_POST", "post_info": pi,
                "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": int(fo.get("photo_cover_index", 0)),
                                "photo_images": [m["url"] for m in post.media]}}
        d = await ss._tt(c, "/v2/post/publish/content/init/", body)
    else:                                                       # video_inbox: no post_info, creator finishes in the app
        url = post.media[0]["url"]
        if o.get("source") == "FILE_UPLOAD":
            blob, _ = await _fetch(c, url)
            chunk, count = ss.chunk_plan(len(blob))
            src = {"source": "FILE_UPLOAD", "video_size": len(blob), "chunk_size": chunk, "total_chunk_count": count}
        else:
            blob, src = None, {"source": "PULL_FROM_URL", "video_url": url}
        d = await ss._tt(c, "/v2/post/publish/inbox/video/init/", {"source_info": src})
        ss._submitted(post, d["publish_id"], "SUBMITTED")
        await db.commit()
        if blob is not None:
            await ss._tt_upload(c, d["upload_url"], blob, chunk, count)
        return
    ss._submitted(post, d["publish_id"], "SUBMITTED")


# ═════════════════ YouTube ═════════════════

def _yt(path: str, upload: bool = False) -> str:
    return f"{cfg('YOUTUBE_API_URL', 'https://www.googleapis.com').rstrip('/')}/{'upload/' if upload else ''}youtube/v3/{path}"


def _yt_h() -> dict:
    return {"Authorization": f"Bearer {cfg('YOUTUBE_SOCIAL_ACCESS_TOKEN', '')}"}


def _yt_ok(r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400:
        err = (body.get("error") or {}) if isinstance(body, dict) else {}
        reason = ((err.get("errors") or [{}])[0]).get("reason") or f"http_{r.status_code}"
        msg = err.get("message") or f"HTTP {r.status_code}"
        if reason in ("quotaExceeded", "dailyLimitExceeded", "uploadLimitExceeded"):
            msg += " (YouTube quota exhausted; it resets at midnight Pacific time)"
        raise SocialError(f"youtube: {msg}", reason, r.status_code >= 500 or r.status_code == 429)
    return body


async def _quota_take(db: AsyncSession, network: str, bucket: str, limit: int) -> None:
    day = _now().date()
    await db.execute(insert(SocialQuotaUse).values(network=network, bucket=bucket, day=day, used=0).on_conflict_do_nothing(constraint="uq_m49_social_quota"))
    used = (await db.execute(select(SocialQuotaUse.used).where(SocialQuotaUse.network == network, SocialQuotaUse.bucket == bucket,
                                                              SocialQuotaUse.day == day).with_for_update())).scalar()
    if used >= limit:
        raise SocialError(f"{network}: our own {bucket} counter is at {used}/{limit} for today; not sent to the provider", "quota_exhausted")
    await db.execute(update(SocialQuotaUse).where(SocialQuotaUse.network == network, SocialQuotaUse.bucket == bucket,
                                                  SocialQuotaUse.day == day).values(used=SocialQuotaUse.used + 1))


def yt_snippet(post: SocialPost, ch: SocialChannel) -> dict:
    from app.services.social_formats import youtube_private_only
    fo = _fo(post)
    priv = "private" if youtube_private_only(ch.options) else fo.get("privacy_status", "private")
    status = {"privacyStatus": priv, "selfDeclaredMadeForKids": bool(fo.get("made_for_kids")), **({"publishAt": fo["publish_at"]} if fo.get("publish_at") else {})}
    return {"snippet": {"title": fo["title"], "description": post.text, "tags": fo.get("tags") or [], "categoryId": str(fo.get("category_id", "22"))},
            "status": status}


async def yt_upload(c, post: SocialPost, blob: bytes) -> None:
    """Send the bytes to the session URI in 256 KiB-multiple chunks; resume from the server's Range after any drop."""
    st = _fs(post)
    total, chunk = len(blob), max(256 * 1024, (int(cfg("YOUTUBE_CHUNK_BYTES", 8 * MB)) // (256 * 1024)) * 256 * 1024)
    off = int(st.get("offset", 0))
    for _ in range(200):
        end = min(off + chunk, total) - 1
        try:
            r = await c.put(st["session"], content=blob[off:end + 1], headers={"Content-Range": f"bytes {off}-{end}/{total}", "Content-Type": "video/mp4"})
        except httpx.TransportError:                                        # ask where the upload stands
            r = await c.put(st["session"], content=b"", headers={"Content-Range": f"bytes */{total}"})
        if r.status_code in (200, 201):
            vid = r.json()["id"]
            _set(post, phase="processing", offset=total, video_id=vid)
            post.provider_ref = vid
            ss.log(post, "UPLOADED", f"{total} bytes; video id {vid}")
            return
        if r.status_code == 308:
            rng = r.headers.get("Range")
            off = int(rng.split("-")[1]) + 1 if rng else 0
            _set(post, offset=off)
            continue
        if r.status_code == 404:
            raise SocialError("youtube: the upload session expired; start a new upload (retry)", "session_expired")
        _yt_ok(r)
        raise SocialError(f"youtube: unexpected upload answer HTTP {r.status_code}", "upload_unexpected", r.status_code >= 500)
    raise SocialError("youtube: upload did not finish", "upload_incomplete", True)


async def yt_submit(db, c, ch, post) -> None:
    await _quota_take(db, "youtube", "videos.insert", int(cfg("YOUTUBE_UPLOAD_QUOTA_PER_DAY", 100)))
    blob, ctype = await _fetch(c, post.media[0]["url"])
    r = await c.post(_yt("videos", True), params={"uploadType": "resumable", "part": "snippet,status"}, json=yt_snippet(post, ch),
                     headers={**_yt_h(), "X-Upload-Content-Length": str(len(blob)), "X-Upload-Content-Type": ctype if ctype.startswith("video/") else "video/mp4"})
    _yt_ok(r)
    session = r.headers.get("location")
    if not session:
        raise SocialError("youtube: no upload session URI returned", "no_session", True)
    _set(post, kind="yt", phase="uploading", session=session, offset=0)
    ss._submitted(post, "upload:" + hashlib.sha1(session.encode()).hexdigest()[:24], "SUBMITTED")
    await db.commit()
    await yt_upload(c, post, blob)
    post.status = "PROCESSING"


async def yt_advance(db, ch, post) -> None:
    st = _fs(post)
    if st.get("phase") == "uploading":                         # a restart interrupted the upload: continue at the server's offset
        async with provider_client() as c:
            blob, _ = await _fetch(c, post.media[0]["url"])
            r = await c.put(st["session"], content=b"", headers={"Content-Range": f"bytes */{len(blob)}"})
            if r.status_code == 308:
                rng = r.headers.get("Range")
                _set(post, offset=int(rng.split("-")[1]) + 1 if rng else 0)
            elif r.status_code in (200, 201):
                vid = r.json()["id"]
                _set(post, phase="processing", video_id=vid)
                post.provider_ref = vid
                return
            else:
                _yt_ok(r)
            await yt_upload(c, post, blob)
        return
    d = await ss._read(lambda c: _yt_get(c, "videos", {"part": "status,processingDetails", "id": post.provider_ref}))
    items = d.get("items") or []
    if not items:
        post.provider_status = "NOT_VISIBLE_YET"
        return
    s, pd = items[0].get("status") or {}, items[0].get("processingDetails") or {}
    up = post.provider_status = str(s.get("uploadStatus") or "")[:40]
    if up in ("failed", "rejected", "deleted"):
        ss._failed(post, s.get("failureReason") or s.get("rejectionReason") or up, f"YouTube {up}: {s.get('failureReason') or s.get('rejectionReason') or 'no reason given'}")
    elif pd.get("processingStatus") in ("failed", "terminated"):
        ss._failed(post, pd.get("processingStatus"), f"YouTube processing {pd.get('processingStatus')}: {pd.get('processingFailureReason') or ''}".strip())
    elif up == "processed":
        priv = s.get("privacyStatus")
        if not st.get("extras_done"):
            _set(post, extras_done=True)
            await _yt_extras(post)
        if s.get("publishAt") and priv == "private":
            post.provider_status = "SCHEDULED"                   # not live until publishAt
        else:
            ss._published(post, post.provider_ref, f"YouTube uploadStatus processed, visibility {priv}"
                          + (" (locked to private by YouTube for an unverified project)" if priv == "private" and _fo(post).get("privacy_status") in ("public", "unlisted") else ""))
    else:
        post.status = "PROCESSING" if post.status != "UNKNOWN" else post.status


async def _yt_get(c, path, params) -> dict:
    return _yt_ok(await c.get(_yt(path), params=params, headers=_yt_h()))


async def _yt_extras(post: SocialPost) -> None:
    """Custom thumbnail and playlist: optional, so a failure is logged and never fails the post."""
    fo = _fo(post)
    try:
        async with provider_client() as c:
            if fo.get("thumbnail_url"):
                img, ctype = await _fetch(c, fo["thumbnail_url"], 2 * MB)
                _yt_ok(await c.post(_yt("thumbnails/set", True), params={"videoId": post.provider_ref}, content=img, headers={**_yt_h(), "Content-Type": ctype}))
                ss.log(post, "THUMBNAIL", "thumbnails.set accepted")
            if fo.get("playlist_id"):
                _yt_ok(await c.post(_yt("playlistItems"), params={"part": "snippet"}, headers=_yt_h(), json={"snippet": {
                    "playlistId": fo["playlist_id"], "resourceId": {"kind": "youtube#video", "videoId": post.provider_ref}}}))
                ss.log(post, "PLAYLIST", fo["playlist_id"])
    except (SocialError, httpx.HTTPError) as e:
        ss.log(post, "EXTRA_FAILED", str(e) or type(e).__name__)


# ═════════════════ X ═════════════════

def _x(path: str) -> str:
    return f"{cfg('X_API_URL', 'https://api.x.com').rstrip('/')}/2/{path}"


def _x_h() -> dict:
    return {"Authorization": f"Bearer {cfg('X_SOCIAL_ACCESS_TOKEN', '')}"}


def x_ok(r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400:
        detail = (body.get("detail") or body.get("title") or f"HTTP {r.status_code}") if isinstance(body, dict) else f"HTTP {r.status_code}"
        reset = r.headers.get("x-rate-limit-reset")
        raise SocialError(f"x: {detail}" + (f" (rate limit resets at {reset})" if r.status_code == 429 and reset else ""),
                          str(body.get("type") or r.status_code)[-60:], r.status_code >= 500 or r.status_code == 429)
    return body


CATEGORY = {"image": "tweet_image", "gif": "tweet_gif", "video": "tweet_video"}


async def x_upload(c, kind: str, blob: bytes, ctype: str) -> dict:
    d = x_ok(await c.post(_x("media/upload/initialize"), json={"media_type": ctype, "total_bytes": len(blob), "media_category": CATEGORY[kind]}, headers=_x_h()))["data"]
    mid, seg = d["id"], 5 * MB
    for i in range(0, max(1, (len(blob) + seg - 1) // seg)):
        part = blob[i * seg:(i + 1) * seg]

        async def append(cl, part=part, i=i):
            x_ok(await cl.post(_x(f"media/upload/{mid}/append"), data={"segment_index": str(i)}, files={"media": ("seg", part)}, headers=_x_h()))
        await ss._read(append)                                  # appending the same segment index again is safe
    f = x_ok(await c.post(_x(f"media/upload/{mid}/finalize"), headers=_x_h()))["data"]
    return {"id": mid, "processing": f.get("processing_info")}


async def x_create(c, post: SocialPost, media_ids: list[str]) -> str:
    body: dict = {"text": post.text + (f" {post.link}" if post.link else "")}
    if media_ids:
        body["media"] = {"media_ids": media_ids}
    return x_ok(await c.post(_x("tweets"), json=body, headers=_x_h()))["data"]["id"]


async def x_submit(db, c, ch, post) -> None:
    fo_cost = "0.20" if post.link else "0.015"
    ss.log(post, "COST_NOTE", f"X pay-per-use estimate ${fo_cost} (activation note: needs funded credits)")
    media = []
    for m in post.media:
        blob, ctype = await _fetch(c, m["url"], 8 * 1024 * MB)
        media.append(await x_upload(c, m["kind"], blob, ctype))
    pending = [m for m in media if m["processing"] and (m["processing"] or {}).get("state") != "succeeded"]
    if pending:
        _set(post, kind="x", phase="media", media_ids=[m["id"] for m in media])
        ss._submitted(post, pending[0]["id"], "PROCESSING")
        return
    _set(post, kind="x", media_ids=[m["id"] for m in media])
    ss._published(post, await x_create(c, post, [m["id"] for m in media]), "X returned the created post")


async def _x_find(c, ch, post) -> Optional[str]:
    d = x_ok(await c.get(_x(f"users/{ch.external_id}/tweets"), params={"max_results": 10, "tweet.fields": "created_at"}, headers=_x_h()))
    floor = (post.claimed_at or _now()) - timedelta(minutes=1)
    for t in d.get("data", []):
        if t["text"].startswith(post.text[:200]) and datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) >= floor:
            return t["id"]
    return None


async def x_advance(db, ch, post) -> None:
    st = _fs(post)
    if st.get("phase") == "lookup":
        found = await ss._read(lambda c: _x_find(c, ch, post))
        if found:
            ss._published(post, found, "X lookup found the post after a lost answer")
        else:
            ss.log(post, "NOT_FOUND_YET", "not on the account; not resubmitted automatically")
        return
    states = []
    for mid in st.get("media_ids", []):
        d = (await ss._read(lambda c, mid=mid: _x_get(c, "media/upload", {"command": "STATUS", "media_id": mid}))).get("data") or {}
        pi = d.get("processing_info") or {}
        states.append(pi.get("state", "succeeded"))
        if pi.get("state") == "failed":
            ss._failed(post, "media_failed", f"X media processing failed: {(pi.get('error') or {}).get('message', 'no reason given')}")
            return
    post.provider_status = ",".join(sorted(set(states)))[:40]
    if not all(s == "succeeded" for s in states):
        return
    _set(post, phase="creating")
    await db.commit()
    try:
        async with provider_client() as c:
            ss._published(post, await x_create(c, post, st["media_ids"]), "X returned the created post")
    except (httpx.HTTPError, SocialError) as e:
        if isinstance(e, SocialError) and not e.retryable:
            ss._failed(post, e.code, str(e))
        else:
            _set(post, phase="lookup")
            post.provider_ref = f"lookup:{post.idempotency_key[:40]}"
            ss._unknown(post, f"No confirmed answer to the X post call ({type(e).__name__}); looking it up on the account.")


async def _x_get(c, path, params) -> dict:
    return x_ok(await c.get(_x(path), params=params, headers=_x_h()))


# ═════════════════ lookup after a lost answer (create calls) ═════════════════

def mark_lookup(post: SocialPost, network: str) -> bool:
    """An X create call lost its answer: reconcile by looking the post up on the account instead of guessing or resending."""
    if network != "x" or not post.format:
        return False
    _set(post, phase="lookup")
    post.provider_ref = f"lookup:{post.idempotency_key[:40]}"
    return True


# ═════════════════ dispatch ═════════════════

async def submit(db, c, ch, post) -> None:
    n = ch.network
    if n == "facebook":
        await fb_submit(db, c, ch, post)
    elif n == "instagram":
        await ig_submit(db, c, ch, post)
    elif n == "linkedin":
        await li_submit(db, c, ch, post)
    elif n == "tiktok":
        await tt_submit_ext(db, c, post)
    elif n == "youtube":
        await yt_submit(db, c, ch, post)
    elif n == "x":
        await x_submit(db, c, ch, post)


async def advance(db, ch, post) -> bool:
    """One reconcile step for a post that has a format. Returns True when the legacy Instagram/TikTok logic should run next."""
    n = ch.network
    if n == "facebook":
        await fb_advance(db, ch, post)
    elif n == "linkedin":
        await li_advance(db, ch, post)
    elif n == "youtube":
        await yt_advance(db, ch, post)
    elif n == "x":
        await x_advance(db, ch, post)
    elif n == "instagram":
        return await ig_advance(db, ch, post)
    else:
        return True
    return False


# ═════════════════ insights ═════════════════

def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


async def fetch_insights(ch: SocialChannel, post: SocialPost) -> list[tuple[str, float, str]]:
    """Metrics exactly as returned by the provider: (metric, value, source). Nothing is estimated."""
    pid, n, out = post.external_post_id, ch.network, []
    if not pid:
        raise SocialError("The post is not published yet: there are no metrics to read.", "not_published")
    if n == "facebook":
        d = await ss._read(lambda c: _get(c, ss._graph(f"{pid}/insights"), {"metric": "post_clicks,post_reactions_by_type_total"}, ss._meta_h(), "facebook"))
        src = f"GET /{pid}/insights"
        for row in d.get("data", []):
            v = ((row.get("values") or [{}])[0]).get("value")
            if isinstance(v, dict):
                out += [(f"{row['name']}.{k}", _num(x), src) for k, x in v.items() if _num(x) is not None]
            elif _num(v) is not None:
                out.append((row["name"], _num(v), src))
    elif n == "instagram":
        d = await ss._read(lambda c: _get(c, ss._graph(f"{pid}/insights"), {"metric": "reach,views,likes,comments"}, ss._meta_h(), "instagram"))
        out = [(r["name"], _num(((r.get("values") or [{}])[0]).get("value")), f"GET /{pid}/insights") for r in d.get("data", [])]
    elif n == "linkedin":
        key = "ugcPosts" if "ugcPost" in pid else "shares"
        d = await ss._read(lambda c: _get(c, _li("organizationalEntityShareStatistics"), {
            "q": "organizationalEntity", "organizationalEntity": f"urn:li:organization:{ch.external_id}", key: f"List({pid})"}, _li_h(), "linkedin"))
        tot = ((d.get("elements") or [{}])[0]).get("totalShareStatistics") or {}
        out = [(k, _num(v), "GET /rest/organizationalEntityShareStatistics") for k, v in tot.items()]
    elif n == "youtube":
        d = await ss._read(lambda c: _yt_get(c, "videos", {"part": "statistics", "id": pid}))
        st = ((d.get("items") or [{}])[0]).get("statistics") or {}
        out = [(k, _num(int(v)) if str(v).isdigit() else None, "videos.list statistics") for k, v in st.items()]
    elif n == "x":
        d = await ss._read(lambda c: _x_get(c, f"tweets/{pid}", {"tweet.fields": "public_metrics"}))
        out = [(k, _num(v), "GET /2/tweets public_metrics") for k, v in ((d.get("data") or {}).get("public_metrics") or {}).items()]
    elif n == "tiktok":
        d = await ss._read(lambda c: ss._tt(c, "/v2/video/query/?fields=id,like_count,comment_count,share_count,view_count", {"filters": {"video_ids": [pid]}}))
        v = (d.get("videos") or [{}])[0]
        out = [(k, _num(x), "POST /v2/video/query/") for k, x in v.items() if k.endswith("_count")]
    return [(m, v, s) for m, v, s in out if v is not None]


async def store_insights(db: AsyncSession, post: SocialPost, network: str, rows) -> int:
    for m, v, s in rows:
        stmt = insert(SocialPostMetric).values(post_id=post.id, network=network, metric=m[:80], value=v, source=s[:160], fetched_at=_now())
        await db.execute(stmt.on_conflict_do_update(constraint="uq_m49_social_post_metric", set_={"value": v, "source": s[:160], "fetched_at": _now()}))
    return len(rows)
