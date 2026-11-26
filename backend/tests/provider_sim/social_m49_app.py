"""M49.S01.T007-T010 routes of the organic-social simulator (mounted by social_app.create_social_app).

Contracts followed (the M48 capability matrix, 2026-11-26): Facebook Graph v27.0 (scheduled_publish_time 10 min-30 days,
attached_media, Resumable Upload API, video_reels/video_stories phases, video status), Instagram containers (carousel
children, quota, status_code, rupload), LinkedIn 202611 (Images/Videos initializeUpload + finalizeUpload, asset status,
post lifecycle, MultiImage 2-20, share statistics, comments), TikTok photo/inbox, YouTube v3 (resumable upload with 308
resume, videos.list status, quota, unverified-project private lock, comments), X v2 (chunked media upload + STATUS,
/2/tweets, mentions, rate limit 429). Delays and failures are controlled through POST /_control (CONTROL_KEYS).
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

import httpx
from fastapi import Header, Request
from fastapi.responses import JSONResponse, Response

MB = 1024 * 1024
VERIFIED = "https://cdn.povu-demo.test/videos/"
CONTROL_KEYS = ("li_post_polls", "li_asset_polls", "li_outcome", "fb_polls", "fb_outcome", "publish_scheduled", "ig_quota", "ig_used",
                "yt_unverified", "yt_quota", "yt_polls", "yt_outcome", "x_media_polls", "x_media_outcome", "x_rate", "comments",
                "x_mentions", "metrics", "yt_publish_scheduled")


def reset(st: dict) -> None:
    st.update(fb_photos={}, fb={}, fbup={}, fbvid={}, fb_handles={}, ig_used=0, ig_quota=50, fb_polls=1, fb_outcome=None,
              publish_scheduled=False, li_assets={}, li_posts={}, li_post_polls=0, li_asset_polls=1, li_outcome=None,
              yt_sess={}, yt_videos={}, yt_unverified=False, yt_quota=100, yt_inserts=0, yt_polls=1, yt_outcome=None,
              yt_publish_scheduled=False, x_media={}, x_media_polls=1, x_media_outcome=None, x_tweets=[], x_rate=100,
              x_mentions=[], x_hidden=[], comments={}, deleted=[], hidden=[], replies=[],
              metrics={"post_clicks": 12, "post_reactions_by_type_total": {"like": 5, "love": 2}, "reach": 340, "views": 512,
                       "likes": 40, "comments": 6, "impressionCount": 900, "clickCount": 31, "likeCount": 20, "commentCount": 4,
                       "shareCount": 2, "viewCount": "321", "like_count": 9, "retweet_count": 1, "reply_count": 2,
                       "impression_count": 700})


# ── Facebook helpers used by the M48 routes ────────────────────────────

def fb_feed_check(st: dict, form: dict) -> Optional[str]:
    if form.get("published") == "false" and form.get("scheduled_publish_time"):
        ts = int(form["scheduled_publish_time"])
        now = time.time()
        if not now + 590 <= ts <= now + 30 * 86400 + 60:
            return "(#100) scheduled_publish_time must be between 10 minutes and 30 days from now"
    for k, v in form.items():
        if k.startswith("attached_media["):
            if json.loads(v).get("media_fbid") not in st["fb_photos"]:
                return "(#100) attached_media: unknown media_fbid"
    return None


def fb_register_post(st: dict, pid: str, form: dict) -> None:
    sched = int(form["scheduled_publish_time"]) if form.get("published") == "false" and form.get("scheduled_publish_time") else None
    st["fb"][pid] = {"sched": sched, "form": form}


def ig_media_check(st: dict, form: dict) -> Optional[str]:
    mt = form.get("media_type")
    if mt == "CAROUSEL":
        kids = [k for k in (form.get("children") or "").split(",") if k]
        if not 2 <= len(kids) <= 20:
            return "Carousels need 2 to 20 children"
        for k in kids:
            c = st["ig"].get(k)
            if c is None or not c["child"]:
                return "Unknown carousel child"
            if c["polls"] > 0 or c["outcome"]:
                return "A carousel child is not ready (status_code must be FINISHED)"
        return None
    if form.get("upload_type") == "resumable":
        return None
    if not (form.get("image_url") or form.get("video_url")):
        return "image_url or video_url is required"
    for k in ("image_url", "video_url"):
        if form.get(k) and not form[k].startswith("https://"):
            return "Media URL must be public https"
    if len(form.get("alt_text", "")) > 1000:
        return "alt_text is longer than 1000 characters"
    if mt in ("VIDEO", "REELS") and not form.get("video_url"):
        return f"{mt} needs video_url"
    if mt == "REELS" and form.get("is_carousel_item") == "true":
        return "Reels cannot be carousel items"
    return None


def register(app, st: dict, ctx: dict) -> None:
    fault, lose, meta_err, page_gate = ctx["fault"], ctx["lose_answer"], ctx["meta_err"], ctx["page_gate"]
    tt_err, tt_ok, tt_gate, run = ctx["tt_err"], ctx["tt_ok"], ctx["tt_gate"], ctx["run"]
    TOK = {"li": "sim-li-social", "yt": "sim-yt-social", "x": "sim-x-social", "meta": "sim-page-token"}

    def base(request: Request) -> str:
        return str(request.base_url).rstrip("/")

    def nxt() -> int:
        st["n"] += 1
        return st["n"]

    # ── media files the company hosts ──
    @app.get("/images/{name}")
    async def image(name: str):
        return Response(b"\xff\xd8\xff" + b"\0" * 2048, media_type="image/jpeg")

    # ═══════════ Meta: Facebook Page + Instagram ═══════════
    def oauth_ok(authorization) -> bool:
        return authorization == f"OAuth {TOK['meta']}"

    @app.post("/meta/{ver}/{app_id}/uploads")
    async def fb_upload_session(ver: str, app_id: str, request: Request, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        q = request.query_params
        if not q.get("file_length", "").isdigit():
            return meta_err(100, 400, "file_length is required")
        sid = f"upload:{run}-{nxt()}"
        st["fbup"][sid] = {"size": int(q["file_length"]), "offset": 0, "name": q.get("file_name")}
        return {"id": sid}

    @app.post("/meta/{ver}/{node}")
    async def meta_node_post(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None),
                             file_offset: Optional[str] = Header(None, convert_underscores=False)):
        if node.startswith("upload:"):                      # Resumable Upload API step 2
            if not oauth_ok(authorization):
                return meta_err(190, 401, "Error validating access token")
            s = st["fbup"].get(node)
            if s is None or file_offset is None or int(file_offset) != s["offset"]:
                return meta_err(100, 400, "file_offset does not match the session")
            body = await request.body()
            if fault("fb_upload") == "drop":                # half arrives, the connection drops
                s["offset"] += len(body) // 2
                raise httpx.ReadTimeout("simulated connection drop mid-upload")
            s["offset"] += len(body)
            if s["offset"] < s["size"]:
                return meta_err(100, 400, "incomplete upload")
            h = f"h:{run}-{nxt()}"
            st["fb_handles"][h] = s["size"]
            return {"h": h}
        err, _ = page_gate(authorization)                   # hide a comment
        if err:
            return err
        form = dict(await request.form())
        if form.get("is_hidden") == "true" or form.get("hide") == "true":
            st["hidden"].append(node)
            return {"success": True}
        return meta_err(100, 400, "Unsupported post request")

    @app.delete("/meta/{ver}/{node}")
    async def meta_delete(ver: str, node: str, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        if node in st["fb"]:
            del st["fb"][node]
        st["deleted"].append(node)
        return {"success": True}

    @app.get("/meta/{ver}/{cid}")
    async def meta_get(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None)):
        if cid.startswith("upload:"):
            if not oauth_ok(authorization):
                return meta_err(190, 401, "Error validating access token")
            return {"id": cid, "file_offset": (st["fbup"].get(cid) or {}).get("offset", 0)}
        err, _ = page_gate(authorization, "ig_status")
        if err:
            return err
        if cid in st["ig"]:
            c = st["ig"][cid]
            if c["published"]:
                code = "PUBLISHED"
            elif c["polls"] > 0:
                c["polls"] -= 1
                code = "IN_PROGRESS"
            else:
                code = c["outcome"] or "FINISHED"
            out = {"id": cid, "status_code": code}
            if code == "ERROR":
                out["status"] = "Error: 2207026 (simulated unsupported media)"
            return out
        if cid in st["fbvid"]:
            v = st["fbvid"][cid]
            if not v["uploaded"]:
                ph = {"video_status": "uploading", "uploading_phase": {"status": "in_progress"}}
            elif v["polls"] > 0:
                v["polls"] -= 1
                ph = {"video_status": "processing", "processing_phase": {"status": "in_progress"}}
            elif v["outcome"]:
                ph = {"video_status": v["outcome"]}
            elif v["sched"] and not st["publish_scheduled"]:
                ph = {"video_status": "ready", "publishing_phase": {"status": "not_started", "publish_status": "scheduled"}}
            else:
                ph = {"video_status": "ready", "publishing_phase": {"status": "complete", "publish_status": "published", "publish_time": "2026-11-26T10:00:00+0000"}}
            return {"id": cid, "status": ph}
        if cid in st["fb"]:
            p = st["fb"][cid]
            pub = p["sched"] is None or st["publish_scheduled"]
            return {"id": cid, "is_published": pub, "scheduled_publish_time": p["sched"]}
        return meta_err(100, 400, "Unsupported get request")

    @app.post("/meta/{ver}/{page}/videos")
    async def fb_videos(ver: str, page: str, request: Request, authorization: Optional[str] = Header(None)):
        err, f = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if form.get("fbuploader_video_file_chunk") not in st["fb_handles"]:
            return meta_err(100, 400, "Unknown upload handle")
        bad = fb_feed_check(st, form)
        if bad:
            return meta_err(100, 400, bad)
        vid = f"vid{run}{nxt()}"
        sched = int(form["scheduled_publish_time"]) if form.get("published") == "false" and form.get("scheduled_publish_time") else None
        st["fbvid"][vid] = {"uploaded": True, "polls": st["fb_polls"], "outcome": st["fb_outcome"], "sched": sched, "form": form}
        st["calls"].append({"provider": "facebook-video", "form": form, "id": vid})
        return {"id": vid}

    async def reel_like(page: str, request: Request, authorization, kind: str):
        err, _ = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        ph = form.get("upload_phase")
        if ph == "start":
            vid = f"{kind}{run}{nxt()}"
            st["fbvid"][vid] = {"uploaded": False, "polls": st["fb_polls"], "outcome": st["fb_outcome"], "sched": None, "kind": kind}
            return {"video_id": vid, "upload_url": f"{base(request)}/meta-rupload/video-upload/{vid}"}
        v = st["fbvid"].get(form.get("video_id"))
        if ph != "finish" or v is None or not v["uploaded"]:
            return meta_err(100, 400, "finish needs an uploaded video")
        if form.get("video_state") not in ("DRAFT", "SCHEDULED", "PUBLISHED"):
            return meta_err(100, 400, "video_state")
        if form["video_state"] == "SCHEDULED":
            v["sched"] = int(form.get("scheduled_publish_time", "0"))
        st["calls"].append({"provider": f"facebook-{kind}", "form": form})
        return {"success": True}

    @app.post("/meta/{ver}/{page}/video_reels")
    async def reels(ver: str, page: str, request: Request, authorization: Optional[str] = Header(None)):
        return await reel_like(page, request, authorization, "reel")

    @app.post("/meta/{ver}/{page}/video_stories")
    async def vstories(ver: str, page: str, request: Request, authorization: Optional[str] = Header(None)):
        return await reel_like(page, request, authorization, "vstory")

    @app.post("/meta-rupload/video-upload/{vid}")
    async def rupload_fb(vid: str, request: Request, authorization: Optional[str] = Header(None), file_size: Optional[str] = Header(None, convert_underscores=False)):
        v = st["fbvid"].get(vid)
        if v is None or not oauth_ok(authorization):
            return Response(status_code=401)
        body = await request.body()
        if file_size is None or int(file_size) != len(body):
            return meta_err(100, 400, "file_size does not match the body")
        v["uploaded"] = True
        return {"success": True}

    @app.post("/meta-rupload/ig-api-upload/{ver}/{cid}")
    async def rupload_ig(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None), file_size: Optional[str] = Header(None, convert_underscores=False)):
        c = st["ig"].get(cid)
        if c is None or not oauth_ok(authorization) or file_size is None or int(file_size) != len(await request.body()):
            return meta_err(100, 400, "bad resumable upload")
        c["uploaded"] = True
        return {"success": True, "message": "Upload successful"}

    @app.post("/meta/{ver}/{page}/photo_stories")
    async def photo_stories(ver: str, page: str, request: Request, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        pid = dict(await request.form()).get("photo_id")
        if pid not in st["fb_photos"]:
            return meta_err(100, 400, "unknown photo_id")
        return {"success": True, "post_id": f"{page}_story_{pid}"}

    @app.get("/meta/{ver}/{ig}/content_publishing_limit")
    async def ig_limit(ver: str, ig: str, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        return {"data": [{"quota_usage": st["ig_used"], "config": {"quota_total": st["ig_quota"], "quota_duration": 86400}}]}

    @app.get("/meta/{ver}/{node}/insights")
    async def meta_insights(ver: str, node: str, metric: str = "", authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        out = []
        for m in metric.split(","):
            if m not in st["metrics"]:
                return meta_err(100, 400, f"(#100) metric {m} is not valid")
            out.append({"name": m, "period": "lifetime", "values": [{"value": st["metrics"][m]}]})
        return {"data": out}

    @app.get("/meta/{ver}/{node}/comments")
    async def meta_comments(ver: str, node: str, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        return err or {"data": st["comments"].get(node, [])}

    async def meta_reply(node: str, request: Request, authorization):
        err, _ = page_gate(authorization)
        if err:
            return err
        text = dict(await request.form()).get("message")
        if not text:
            return meta_err(100, 400, "message is required")
        rid = f"reply{run}{nxt()}"
        st["replies"].append({"to": node, "text": text, "id": rid, "provider": "meta"})
        return {"id": rid}

    @app.post("/meta/{ver}/{node}/comments")
    async def fb_reply(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        return await meta_reply(node, request, authorization)

    @app.post("/meta/{ver}/{node}/replies")
    async def ig_reply(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        return await meta_reply(node, request, authorization)

    # ═══════════ LinkedIn ═══════════
    def li_gate(authorization, version):
        if authorization != f"Bearer {TOK['li']}":
            return JSONResponse({"status": 401, "message": "Invalid access token"}, 401)
        if version != "202611":
            return JSONResponse({"status": 426, "message": "Requested version is not active"}, 426)
        return None

    @app.post("/linkedin/rest/images")
    async def li_image_init(request: Request, action: str = "", authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        owner = ((await request.json()).get("initializeUploadRequest") or {}).get("owner", "")
        if action != "initializeUpload" or not owner.startswith("urn:li:organization:"):
            return JSONResponse({"status": 400, "message": "Invalid initializeUpload request"}, 400)
        key = f"I{run}{nxt()}"
        urn = f"urn:li:image:{key}"
        st["li_assets"][urn] = {"kind": "image", "uploaded": False, "polls": st["li_asset_polls"], "outcome": st["li_outcome"]}
        return {"value": {"uploadUrl": f"{base(request)}/li-upload/{key}", "image": urn, "uploadUrlExpiresAt": 1893456000000}}

    @app.post("/linkedin/rest/videos")
    async def li_video(request: Request, action: str = "", authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        body = await request.json()
        if action == "initializeUpload":
            r = body.get("initializeUploadRequest") or {}
            size = r.get("fileSizeBytes") or 0
            if not r.get("owner", "").startswith("urn:li:organization:") or not 75 * 1024 <= size <= 500 * MB:
                return JSONResponse({"status": 400, "message": "owner or fileSizeBytes invalid (75 KB to 500 MB)"}, 400)
            key = f"V{run}{nxt()}"
            urn = f"urn:li:video:{key}"
            parts, step = [], 4 * MB
            for i, first in enumerate(range(0, size, step)):
                parts.append({"uploadUrl": f"{base(request)}/li-upload/{key}/{i}", "firstByte": first, "lastByte": min(first + step, size) - 1})
            st["li_assets"][urn] = {"kind": "video", "uploaded": False, "finalized": False, "parts": len(parts), "etags": {}, "size": size,
                                    "polls": st["li_asset_polls"], "outcome": st["li_outcome"]}
            out = {"video": urn, "uploadToken": "", "uploadInstructions": parts, "uploadUrlsExpireAt": 1893456000000}
            if r.get("uploadThumbnail"):
                out["thumbnailUploadUrl"] = f"{base(request)}/li-upload/{key}/thumb"
            return {"value": out}
        if action == "finalizeUpload":
            r = body.get("finalizeUploadRequest") or {}
            a = st["li_assets"].get(r.get("video"))
            if a is None or r.get("uploadedPartIds") != [a["etags"].get(i) for i in range(a["parts"])]:
                return JSONResponse({"status": 400, "message": "uploadedPartIds do not match the uploaded parts"}, 400)
            a["finalized"] = a["uploaded"] = True
            return Response(status_code=200)
        return JSONResponse({"status": 400, "message": "unknown action"}, 400)

    @app.put("/li-upload/{key}")
    async def li_put_image(key: str, request: Request):
        a = st["li_assets"].get(f"urn:li:image:{key}")
        if a is None or not (await request.body()):
            return Response(status_code=400)
        a["uploaded"] = True
        return Response(status_code=201)

    @app.put("/li-upload/{key}/{part}")
    async def li_put_part(key: str, part: str, request: Request):
        a = st["li_assets"].get(f"urn:li:video:{key}")
        body = await request.body()
        if a is None or not body:
            return Response(status_code=400)
        if part == "thumb":
            return Response(status_code=201)
        if fault("li_part") == "500":
            return Response(status_code=500)
        a["etags"][int(part)] = f"etag-{key}-{part}-{len(body)}"
        return Response(status_code=200, headers={"ETag": a["etags"][int(part)]})

    def asset_status(urn: str):
        a = st["li_assets"].get(urn)
        if a is None:
            return JSONResponse({"status": 404, "message": "not found"}, 404)
        ready = a["uploaded"] if a["kind"] == "image" else a["finalized"]
        if not ready:
            return {"id": urn, "status": "WAITING_UPLOAD"}
        if a["polls"] > 0:
            a["polls"] -= 1
            return {"id": urn, "status": "PROCESSING"}
        if a["outcome"] == "FAILED":
            return {"id": urn, "status": "PROCESSING_FAILED", "processingFailureReason": "UNSUPPORTED_FORMAT"}
        return {"id": urn, "status": "AVAILABLE"}

    @app.get("/linkedin/rest/images/{urn:path}")
    async def li_image_get(urn: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        return li_gate(authorization, linkedin_version) or asset_status(urn)

    @app.get("/linkedin/rest/videos/{urn:path}")
    async def li_video_get(urn: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        return li_gate(authorization, linkedin_version) or asset_status(urn)

    @app.post("/linkedin/rest/posts")
    async def li_post(request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        f = fault("li_post")
        if err or f == "auth":
            return err or JSONResponse({"status": 401, "message": "Invalid access token"}, 401)
        if f == "500":
            return JSONResponse({"status": 500, "message": "Internal Server Error"}, 500)
        if f == "perm":
            return JSONResponse({"status": 403, "message": "Not enough permissions to access: w_organization_social"}, 403)
        body = await request.json()
        if not body.get("author", "").startswith("urn:li:organization:") or len(body.get("commentary", "")) > 3000:
            return JSONResponse({"status": 422, "message": "Invalid post"}, 422)
        content = body.get("content") or {}
        ids = []
        if "media" in content:
            ids = [content["media"].get("id")]
        elif "multiImage" in content:
            imgs = content["multiImage"].get("images") or []
            if not 2 <= len(imgs) <= 20:
                return JSONResponse({"status": 422, "message": "multiImage needs 2 to 20 images"}, 422)
            ids = [i.get("id") for i in imgs]
        elif "article" in content:
            if not content["article"].get("title") or not content["article"].get("source"):
                return JSONResponse({"status": 422, "message": "article needs source and title"}, 422)
            ids = [content["article"]["thumbnail"]] if content["article"].get("thumbnail") else []
        for i in ids:
            a = st["li_assets"].get(i)
            if a is None or asset_status(i).get("status") != "AVAILABLE" if a else True:
                return JSONResponse({"status": 422, "message": f"Media {i} is not AVAILABLE"}, 422)
        st["calls"].append({"provider": "linkedin", "json": body})
        urn = f"urn:li:share:{9000 + len(st['calls'])}"
        st["li_posts"][urn] = {"commentary": body.get("commentary"), "author": body["author"], "created": int(time.time() * 1000),
                               "polls": st["li_post_polls"], "outcome": None}
        if f == "timeout":
            lose()
        return Response(status_code=201, headers={"x-restli-id": urn})

    @app.get("/linkedin/rest/posts/{urn:path}")
    async def li_post_get(urn: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        p = st["li_posts"].get(urn)
        if err or p is None:
            return err or JSONResponse({"status": 404, "message": "not found"}, 404)
        if p["polls"] > 0:
            p["polls"] -= 1
            return {"id": urn, "lifecycleState": "PUBLISH_REQUESTED", "commentary": p["commentary"]}
        return {"id": urn, "lifecycleState": p["outcome"] or "PUBLISHED", "commentary": p["commentary"]}

    @app.get("/linkedin/rest/posts")
    async def li_posts_find(q: str = "", author: str = "", authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        rows = [{"id": u, **p} for u, p in st["li_posts"].items() if p["author"] == author]
        return {"elements": [{"id": r["id"], "commentary": r["commentary"], "createdAt": r["created"]} for r in sorted(rows, key=lambda r: -r["created"])]}

    @app.get("/linkedin/rest/organizationalEntityShareStatistics")
    async def li_stats(request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        m = st["metrics"]
        return {"elements": [{"totalShareStatistics": {k: m[k] for k in ("impressionCount", "clickCount", "likeCount", "commentCount", "shareCount")}}]}

    @app.get("/linkedin/rest/socialActions/{urn}/comments")
    async def li_comments(urn: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        return li_gate(authorization, linkedin_version) or {"elements": st["comments"].get(urn, [])}

    @app.post("/linkedin/rest/socialActions/{urn}/comments")
    async def li_reply(urn: str, request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        body = await request.json()
        if not (body.get("message") or {}).get("text"):
            return JSONResponse({"status": 422, "message": "message.text required"}, 422)
        rid = f"urn:li:comment:({urn},{nxt()})"
        st["replies"].append({"to": body.get("parentComment"), "text": body["message"]["text"], "id": rid, "provider": "linkedin"})
        return Response(status_code=201, headers={"x-restli-id": rid})

    @app.delete("/linkedin/rest/socialActions/{urn}/comments/{cid}")
    async def li_delete_comment(urn: str, cid: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        st["deleted"].append(cid)
        return Response(status_code=204)

    # ═══════════ TikTok: photo posts, inbox uploads, Display API metrics ═══════════
    @app.post("/tiktok-social/v2/post/publish/content/init/")
    async def tt_photo(request: Request, authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_init")
        if err:
            return err
        body = await request.json()
        pi, si = body.get("post_info") or {}, body.get("source_info") or {}
        imgs = si.get("photo_images") or []
        inbox = body.get("post_mode") == "MEDIA_UPLOAD"
        if body.get("media_type") != "PHOTO" or body.get("post_mode") not in ("DIRECT_POST", "MEDIA_UPLOAD") or si.get("source") != "PULL_FROM_URL":
            return tt_err("invalid_param", "photo posts take media_type PHOTO and PULL_FROM_URL only", 400)
        if not 1 <= len(imgs) <= 35 or not 0 <= si.get("photo_cover_index", 0) < len(imgs):
            return tt_err("invalid_param", "photo_images needs 1 to 35 urls and a valid cover index", 400)
        if any(not u.startswith(VERIFIED) for u in imgs):
            return tt_err("url_ownership_unverified", "Photo URL domain or prefix is not verified", 403)
        if len(pi.get("title", "")) > 90 or len(pi.get("description", "")) > 4000:
            return tt_err("invalid_param", "title (90) or description (4000) too long", 400)
        priv = pi.get("privacy_level")
        if not inbox:
            if priv not in st["privacy_options"]:
                return tt_err("privacy_level_option_mismatch", "privacy_level not in creator options", 403)
            if not st["audited"] and priv != "SELF_ONLY":
                return tt_err("unaudited_client_can_only_post_to_private_accounts", "Unaudited clients can only post privately", 403)
        pid = f"p_pub_url~v2-{run}-{nxt()}"
        st["tt"][pid] = {"source": "PHOTO", "privacy": priv, "polls": st["processing_polls"], "cancelled": False, "outcome": st["next_outcome"],
                         "uploaded": 0, "size": 0, "post_info": pi, "inbox": inbox, "images": imgs}
        st["next_outcome"] = None
        st["calls"].append({"provider": "tiktok-photo", "publish_id": pid, "json": body})
        return tt_ok({"publish_id": pid})

    @app.post("/tiktok-social/v2/post/publish/inbox/video/init/")
    async def tt_inbox(request: Request, authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_init")
        if err:
            return err
        body = await request.json()
        si = body.get("source_info") or {}
        pending = sum(1 for r in st["tt"].values() if r.get("inbox"))
        if pending >= 5:
            return tt_err("spam_risk_too_many_pending_share", "At most 5 pending shares within 24 hours", 429)
        pid = f"v_inbox_{'url' if si.get('source') == 'PULL_FROM_URL' else 'file'}~v2-{run}-{nxt()}"
        rec = {"source": si.get("source"), "privacy": None, "polls": st["processing_polls"], "cancelled": False, "outcome": None,
               "uploaded": 0, "size": si.get("video_size", 0), "post_info": {}, "inbox": True}
        data = {}
        if si.get("source") == "PULL_FROM_URL":
            if not str(si.get("video_url", "")).startswith(VERIFIED):
                return tt_err("url_ownership_unverified", "Video URL domain or prefix is not verified", 403)
        elif si.get("source") == "FILE_UPLOAD":
            data = {"upload_url": f"{base(request)}/tiktok-upload/{pid}"}
        else:
            return tt_err("invalid_param", "source_info.source", 400)
        st["tt"][pid] = rec
        st["calls"].append({"provider": "tiktok-inbox", "publish_id": pid, "json": body})
        return tt_ok({"publish_id": pid, **data})

    @app.post("/tiktok-social/v2/video/query/")
    async def tt_query(request: Request, authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_query")
        if err:
            return err
        ids = ((await request.json()).get("filters") or {}).get("video_ids") or []
        m = st["metrics"]
        return tt_ok({"videos": [{"id": i, "like_count": m["like_count"], "comment_count": m["comments"], "share_count": m["shareCount"],
                                  "view_count": m["views"]} for i in ids]})

    # ═══════════ YouTube Data API v3 ═══════════
    def yt_err(status: int, reason: str, msg: str):
        return JSONResponse({"error": {"code": status, "message": msg, "errors": [{"reason": reason, "domain": "youtube.quota" if "uota" in reason else "global"}]}}, status)

    def yt_auth(authorization):
        return None if authorization == f"Bearer {TOK['yt']}" else yt_err(401, "authError", "Invalid Credentials")

    @app.post("/yt/upload/youtube/v3/videos")
    async def yt_init(request: Request, uploadType: str = "", part: str = "", authorization: Optional[str] = Header(None),
                      x_upload_content_length: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err:
            return err
        body = await request.json()
        sn, stt = body.get("snippet") or {}, body.get("status") or {}
        if uploadType != "resumable" or not (x_upload_content_length or "").isdigit():
            return yt_err(400, "invalidRequest", "resumable upload needs X-Upload-Content-Length")
        if not sn.get("title") or stt.get("privacyStatus") not in ("private", "unlisted", "public") or "selfDeclaredMadeForKids" not in stt:
            return yt_err(400, "invalidRequest", "title, privacyStatus and selfDeclaredMadeForKids are required")
        if stt.get("publishAt") and stt["privacyStatus"] != "private":
            return yt_err(400, "invalidRequest", "publishAt requires privacyStatus private")
        if st["yt_inserts"] >= st["yt_quota"]:
            return yt_err(403, "quotaExceeded", "The request cannot be completed because you have exceeded your quota.")
        st["yt_inserts"] += 1
        sid = f"yt{run}{nxt()}"
        st["yt_sess"][sid] = {"size": int(x_upload_content_length), "got": 0, "body": body, "video": None}
        st["calls"].append({"provider": "youtube-init", "json": body, "session": sid})
        return Response(status_code=200, headers={"Location": f"{base(request)}/yt-session/{sid}"})

    @app.put("/yt-session/{sid}")
    async def yt_put(sid: str, request: Request, content_range: Optional[str] = Header(None)):
        s = st["yt_sess"].get(sid)
        if s is None or fault("yt_chunk") == "expire":
            return Response(status_code=404)
        body = await request.body()
        m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)|bytes \*/(\d+)", content_range or "")
        if not m:
            return Response(status_code=400)

        def done():
            return JSONResponse({"kind": "youtube#video", "id": s["video"]}, 201)

        def incomplete():
            return Response(status_code=308, headers={"Range": f"bytes=0-{s['got'] - 1}"} if s["got"] else {})
        if m[4]:
            return done() if s["video"] else incomplete()
        a, b, total = int(m[1]), int(m[2]), int(m[3])
        if total != s["size"] or a != s["got"] or len(body) != b - a + 1:
            return Response(status_code=400)
        if (b + 1 - a) % (256 * 1024) and b + 1 != total:
            return yt_err(400, "invalidRequest", "chunks must be multiples of 256 KiB")
        s["got"] = b + 1
        if fault("yt_chunk") == "drop":
            raise httpx.ReadTimeout("simulated connection drop mid-upload")
        if s["got"] < total:
            return incomplete()
        s["video"] = f"ytv{run}{nxt()}"
        stt = s["body"]["status"]
        st["yt_videos"][s["video"]] = {"body": s["body"], "polls": st["yt_polls"], "outcome": st["yt_outcome"],
                                       "privacy": "private" if st["yt_unverified"] else stt["privacyStatus"], "publishAt": stt.get("publishAt")}
        return done()

    @app.get("/yt/youtube/v3/videos")
    async def yt_list(part: str = "", id: str = "", authorization: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err:
            return err
        v = st["yt_videos"].get(id)
        if v is None:
            return {"items": []}
        if st["yt_publish_scheduled"] and v["publishAt"]:
            v["privacy"], v["publishAt"] = "public", None
        item: dict = {"id": id}
        if "status" in part:
            if v["polls"] > 0:
                v["polls"] -= 1
                up, pd = "uploaded", {"processingStatus": "processing"}
            elif v["outcome"] == "failed":
                up, pd = "failed", {"processingStatus": "failed"}
            elif v["outcome"] == "rejected":
                up, pd = "rejected", {"processingStatus": "succeeded"}
            else:
                up, pd = "processed", {"processingStatus": "succeeded"}
            item["status"] = {"uploadStatus": up, "privacyStatus": v["privacy"], **({"publishAt": v["publishAt"]} if v["publishAt"] else {}),
                              **({"failureReason": "codec"} if up == "failed" else {}), **({"rejectionReason": "duplicate"} if up == "rejected" else {})}
            item["processingDetails"] = pd
        if "statistics" in part:
            m = st["metrics"]
            item["statistics"] = {"viewCount": m["viewCount"], "likeCount": "9", "commentCount": "2"}
        return {"items": [item]}

    @app.post("/yt/upload/youtube/v3/thumbnails/set")
    async def yt_thumb(videoId: str = "", authorization: Optional[str] = Header(None), request: Request = None):
        err = yt_auth(authorization)
        if err or videoId not in st["yt_videos"] or not (await request.body()):
            return err or yt_err(404, "videoNotFound", "video not found")
        st["calls"].append({"provider": "youtube-thumbnail", "video": videoId})
        return {"items": [{"default": {"url": "https://i.ytimg.test/x.jpg"}}]}

    @app.post("/yt/youtube/v3/playlistItems")
    async def yt_playlist(request: Request, authorization: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err:
            return err
        st["calls"].append({"provider": "youtube-playlist", "json": await request.json()})
        return {"id": f"pli{nxt()}"}

    @app.get("/yt/youtube/v3/commentThreads")
    async def yt_threads(videoId: str = "", authorization: Optional[str] = Header(None)):
        return yt_auth(authorization) or {"items": st["comments"].get(videoId, [])}

    @app.post("/yt/youtube/v3/comments")
    async def yt_reply(request: Request, authorization: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err:
            return err
        sn = (await request.json()).get("snippet") or {}
        if not sn.get("parentId") or not sn.get("textOriginal"):
            return yt_err(400, "invalidRequest", "parentId and textOriginal are required")
        rid = f"ytc{run}{nxt()}"
        st["replies"].append({"to": sn["parentId"], "text": sn["textOriginal"], "id": rid, "provider": "youtube"})
        return {"id": rid}

    @app.post("/yt/youtube/v3/comments/setModerationStatus")
    async def yt_moderate(id: str = "", moderationStatus: str = "", authorization: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err or moderationStatus not in ("heldForReview", "published", "rejected"):
            return err or yt_err(400, "invalidRequest", "moderationStatus")
        st["hidden"].append(id)
        return Response(status_code=204)

    @app.delete("/yt/youtube/v3/comments")
    async def yt_delete(id: str = "", authorization: Optional[str] = Header(None)):
        err = yt_auth(authorization)
        if err:
            return err
        st["deleted"].append(id)
        return Response(status_code=204)

    # ═══════════ X API v2 ═══════════
    def x_auth(authorization):
        return None if authorization == f"Bearer {TOK['x']}" else JSONResponse({"title": "Unauthorized", "type": "about:blank", "status": 401, "detail": "Unauthorized"}, 401)

    CAT = {"tweet_image": 5 * MB, "tweet_gif": 15 * MB, "tweet_video": 8 * 1024 * MB}

    @app.post("/x/2/media/upload/initialize")
    async def x_init(request: Request, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        if err:
            return err
        b = await request.json()
        if b.get("media_category") not in CAT or not isinstance(b.get("total_bytes"), int) or b["total_bytes"] > CAT[b["media_category"]]:
            return JSONResponse({"title": "Invalid Request", "detail": "media_category or total_bytes is invalid", "type": "invalid-request", "status": 400}, 400)
        mid = f"{run}{nxt()}"
        st["x_media"][mid] = {"total": b["total_bytes"], "got": 0, "seg": [], "cat": b["media_category"], "final": False,
                              "polls": st["x_media_polls"] if b["media_category"] == "tweet_video" else 0, "outcome": st["x_media_outcome"]}
        return {"data": {"id": mid, "media_key": f"7_{mid}", "expires_after_secs": 86400}}

    @app.post("/x/2/media/upload/{mid}/append")
    async def x_append(mid: str, request: Request, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        m = st["x_media"].get(mid)
        if err or m is None:
            return err or JSONResponse({"title": "Not Found", "detail": "media id", "status": 404}, 404)
        form = await request.form()
        idx, data = int(form["segment_index"]), await form["media"].read()
        if len(data) > 5 * MB:
            return JSONResponse({"title": "Payload Too Large", "detail": "segments are at most 5 MB", "status": 413}, 413)
        if idx not in m["seg"]:
            m["seg"].append(idx)
            m["got"] += len(data)
        return Response(status_code=204)

    @app.post("/x/2/media/upload/{mid}/finalize")
    async def x_finalize(mid: str, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        m = st["x_media"].get(mid)
        if err or m is None:
            return err or JSONResponse({"title": "Not Found", "status": 404, "detail": "media id"}, 404)
        if m["got"] != m["total"]:
            return JSONResponse({"title": "Invalid Request", "detail": "uploaded bytes do not match total_bytes", "status": 400}, 400)
        m["final"] = True
        out = {"id": mid}
        if m["polls"] > 0 or m["outcome"]:
            out["processing_info"] = {"state": "pending", "check_after_secs": 1}
        return {"data": out}

    @app.get("/x/2/media/upload")
    async def x_status(command: str = "", media_id: str = "", authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        m = st["x_media"].get(media_id)
        if err or command != "STATUS" or m is None:
            return err or JSONResponse({"title": "Invalid Request", "status": 400, "detail": "command=STATUS and media_id"}, 400)
        if m["polls"] > 0:
            m["polls"] -= 1
            return {"data": {"id": media_id, "processing_info": {"state": "in_progress", "check_after_secs": 1}}}
        if m["outcome"] == "failed":
            return {"data": {"id": media_id, "processing_info": {"state": "failed", "error": {"code": 1, "message": "InvalidMedia"}}}}
        m["done"] = True
        return {"data": {"id": media_id, "processing_info": {"state": "succeeded"}}}

    @app.post("/x/2/tweets")
    async def x_tweet(request: Request, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        f = fault("x_tweet")
        if err:
            return err
        if f == "500":
            return JSONResponse({"title": "Internal Server Error", "status": 500, "detail": "simulated"}, 500)
        if len(st["x_tweets"]) >= st["x_rate"] or f == "429":
            return JSONResponse({"title": "Too Many Requests", "detail": "Too Many Requests", "status": 429}, 429, headers={"x-rate-limit-reset": "1893456000"})
        b = await request.json()
        text = b.get("text", "")
        if len(text) > 280 or (not text and not b.get("media")):
            return JSONResponse({"title": "Invalid Request", "detail": "text is empty or longer than 280", "status": 400}, 400)
        ids = (b.get("media") or {}).get("media_ids") or []
        cats = [st["x_media"].get(i, {}).get("cat") for i in ids]
        if None in cats or len(ids) > 4 or ("tweet_video" in cats or "tweet_gif" in cats) and len(ids) > 1:
            return JSONResponse({"title": "Invalid Request", "detail": "media_ids: up to 4 photos, or 1 gif, or 1 video", "status": 400}, 400)
        for i in ids:
            m = st["x_media"][i]
            if not m["final"] or m["polls"] > 0 or m["outcome"]:
                return JSONResponse({"title": "Invalid Request", "detail": f"media {i} is not ready", "status": 400}, 400)
        tid = f"18{run}{nxt()}"
        st["x_tweets"].append({"id": tid, "text": text, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()), "reply": b.get("reply")})
        st["calls"].append({"provider": "x", "json": b, "id": tid})
        if f == "timeout":
            lose()
        return JSONResponse({"data": {"id": tid, "text": text}}, 201)

    @app.get("/x/2/users/{uid}/tweets")
    async def x_user_tweets(uid: str, authorization: Optional[str] = Header(None)):
        return x_auth(authorization) or {"data": list(reversed(st["x_tweets"]))[:10]}

    @app.get("/x/2/users/{uid}/mentions")
    async def x_mentions(uid: str, since_id: str = "", authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        if err:
            return err
        rows = [t for t in st["x_mentions"] if not since_id or int(t["id"]) > int(since_id)]
        out = {"data": rows, "includes": {"users": [{"id": t["author_id"], "username": t.get("username", "user")} for t in rows]}}
        if rows:
            out["meta"] = {"newest_id": str(max(int(t["id"]) for t in rows)), "result_count": len(rows)}
        return out

    @app.get("/x/2/tweets/{tid}")
    async def x_get_tweet(tid: str, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        if err:
            return err
        m = st["metrics"]
        return {"data": {"id": tid, "text": "", "public_metrics": {"like_count": m["like_count"], "retweet_count": m["retweet_count"],
                                                                      "reply_count": m["reply_count"], "impression_count": m["impression_count"]}}}

    @app.put("/x/2/tweets/{tid}/hidden")
    async def x_hide(tid: str, request: Request, authorization: Optional[str] = Header(None)):
        err = x_auth(authorization)
        if err or (await request.json()).get("hidden") is not True:
            return err or JSONResponse({"title": "Invalid Request", "status": 400, "detail": "hidden"}, 400)
        st["hidden"].append(tid)
        return {"data": {"hidden": True}}
