"""Local organic-social simulator (M48.S01.T005): synthetic Facebook Page / Instagram Content Publishing / LinkedIn Posts /
TikTok Content Posting v2 endpoints shaped like the documented contracts, with delayed asynchronous completion.

- TikTok (https://developers.tiktok.com/doc/content-posting-api-get-started): creator_info/query, video/init
  (PULL_FROM_URL with verified-prefix check, FILE_UPLOAD with chunk-rule check and an upload_url taking Content-Range PUTs,
  206 partial / 201 complete), status/fetch (PROCESSING_* for N polls, then PUBLISH_COMPLETE or FAILED + fail_reason),
  cancel (PULL_FROM_URL only, publish_not_cancellable when final). Unaudited apps: SELF_ONLY only.
- Instagram: /{ig}/media container → GET /{container}?fields=status_code (IN_PROGRESS for N polls, then FINISHED) →
  /{ig}/media_publish (once per container).
- Facebook /{page}/feed and /photos, LinkedIn /rest/posts (LinkedIn-Version header, 201 + x-restli-id).
Never a real platform. Run standalone: python -m tests.provider_sim.social_app --port 8766

Control: POST /_control {"processing_polls": n, "next_outcome": {"status": "FAILED", "fail_reason": "spam_risk_text"},
"audited": bool, "privacy_options": [...], "video_size": bytes, "faults": {"tt_init"|"tt_status"|"tt_creator"|"ig_publish"|
"social": ["timeout"|"500"|"429"|"perm"|"auth"]}}. "timeout" performs the action and then loses the answer.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Optional

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

TOKENS = {"meta": "sim-page-token", "linkedin": "sim-li-social", "tiktok": "sim-tt-social"}
LI_VERSION = "202611"
TT_SECRET = "sim-tt-client-secret"
VERIFIED_PREFIX = "https://cdn.povu-demo.test/videos/"
MB = 1024 * 1024


def social_sim_settings(base: str) -> dict:
    base = base.rstrip("/")
    return {"META_ADS_API_URL": f"{base}/meta", "META_PAGE_ACCESS_TOKEN": TOKENS["meta"],
            "LINKEDIN_ADS_API_URL": f"{base}/linkedin", "LINKEDIN_ADS_VERSION": LI_VERSION,
            "LINKEDIN_SOCIAL_ACCESS_TOKEN": TOKENS["linkedin"], "TIKTOK_SOCIAL_API_URL": f"{base}/tiktok-social",
            "TIKTOK_SOCIAL_ACCESS_TOKEN": TOKENS["tiktok"], "SOCIAL_PUBLISHING_ENABLED": True,
            "TIKTOK_CLIENT_SECRET": TT_SECRET, "TIKTOK_VERIFIED_URL_PREFIXES": VERIFIED_PREFIX,
            "TIKTOK_APP_AUDITED": False, "SOCIAL_STATUS_BACKOFF_SECONDS": 0.0}


def apply_sim_settings(monkeypatch, base: str, **extra) -> None:
    """Point the ERP at this simulator. New M48 settings are not Settings fields yet (read with getattr), so they are
    placed on the instance dict; monkeypatch removes them afterwards."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in {**social_sim_settings(base), **extra}.items():
        if k in type(settings).model_fields:
            monkeypatch.setattr(settings, k, v)
        else:
            monkeypatch.setitem(settings.__dict__, k, v)


def tiktok_webhook(event: str, publish_id: str, ts: Optional[int] = None, secret: str = TT_SECRET) -> tuple[bytes, str]:
    """A signed TikTok webhook delivery: (raw body, TikTok-Signature header)."""
    ts = int(ts or time.time())
    raw = json.dumps({"client_key": "sim-client", "event": event, "create_time": ts, "user_openid": "sim-openid",
                      "content": json.dumps({"publish_id": publish_id, "publish_type": "DIRECT_PUBLISH"})}).encode()
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return raw, f"t={ts},s={sig}"


def create_social_app() -> FastAPI:
    app = FastAPI(title="POVU organic social simulator (synthetic, local only)")
    st: dict = {}
    run = secrets.randbelow(10**6)      # ids stay unique across simulator instances (like real provider ids)

    def reset():
        st.clear()
        st.update(faults={}, calls=[], tt={}, ig={}, processing_polls=2, next_outcome=None, audited=False,
                  privacy_options=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"], video_size=MB, n=0)
    reset()

    def fault(k: str) -> Optional[str]:
        q = st["faults"].get(k) or []
        return q.pop(0) if q else None

    def lose_answer():
        raise httpx.ReadTimeout("simulated: the provider acted but the answer was lost")

    @app.post("/_control")
    async def control(request: Request):
        body = await request.json()
        for k, v in (body.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        for k in ("processing_polls", "next_outcome", "audited", "privacy_options", "video_size"):
            if k in body:
                st[k] = body[k]
        return {"ok": True}

    @app.post("/_control/reset")
    async def control_reset():
        reset()
        return {"ok": True}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    # ── TikTok Content Posting v2 ────────────────────────────────────────
    def tt_err(code: str, msg: str, status: int):
        return JSONResponse({"data": {}, "error": {"code": code, "message": msg, "log_id": "sim"}}, status)

    def tt_ok(data: dict):
        return {"data": data, "error": {"code": "ok", "message": "", "log_id": "sim"}}

    def tt_gate(authorization, fk: str):
        f = fault(fk)
        if authorization != f"Bearer {TOKENS['tiktok']}" or f == "auth":
            return tt_err("access_token_invalid", "The access token is invalid or not found in the request.", 401), None
        if f == "429":
            return tt_err("rate_limit_exceeded", "rate limited", 429), None
        if f == "500":
            return JSONResponse({"error": {"code": "internal_error", "message": "simulated"}}, 500), None
        return None, f

    @app.post("/tiktok-social/v2/post/publish/creator_info/query/")
    async def tt_creator(authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_creator")
        if err:
            return err
        return tt_ok({"creator_username": "povu_demo", "creator_nickname": "POVU Demo", "creator_avatar_url": "",
                      "privacy_level_options": st["privacy_options"], "comment_disabled": False,
                      "duet_disabled": False, "stitch_disabled": True, "max_video_post_duration_sec": 300})

    @app.post("/tiktok-social/v2/post/publish/video/init/")
    async def tt_init(request: Request, authorization: Optional[str] = Header(None)):
        err, f = tt_gate(authorization, "tt_init")
        if err:
            return err
        body = await request.json()
        pi, si = body.get("post_info") or {}, body.get("source_info") or {}
        priv = pi.get("privacy_level")
        if priv not in st["privacy_options"]:
            return tt_err("privacy_level_option_mismatch", "privacy_level not in creator options", 403)
        if not st["audited"] and priv != "SELF_ONLY":
            return tt_err("unaudited_client_can_only_post_to_private_accounts", "Unaudited clients can only post privately", 403)
        if len(pi.get("title", "")) > 2200:
            return tt_err("invalid_param", "title too long", 400)
        st["n"] += 1
        rec = {"source": si.get("source"), "privacy": priv, "polls": st["processing_polls"], "cancelled": False,
               "outcome": st["next_outcome"], "uploaded": 0, "size": 0, "post_info": pi}
        st["next_outcome"] = None
        if si.get("source") == "PULL_FROM_URL":
            if not str(si.get("video_url", "")).startswith(VERIFIED_PREFIX):
                return tt_err("url_ownership_unverified", "Video URL domain or prefix is not verified", 403)
            pid, data = f"v_pub_url~v2-{run}-{st['n']}", {}
        elif si.get("source") == "FILE_UPLOAD":
            size, chunk, count = si.get("video_size") or 0, si.get("chunk_size") or 0, si.get("total_chunk_count") or 0
            ok = size > 0 and chunk > 0 and count == size // chunk and 1 <= count <= 1000 and (
                (size < 5 * MB and chunk == size) or (5 * MB <= chunk <= 64 * MB and size - chunk * (count - 1) <= 128 * MB))
            if not ok:
                return tt_err("invalid_param", "chunk_size / total_chunk_count do not follow the media transfer rules", 400)
            pid = f"v_pub_file~v2-{run}-{st['n']}"
            rec.update(size=size)
            data = {"upload_url": f"{str(request.base_url).rstrip('/')}/tiktok-upload/{pid}"}
        else:
            return tt_err("invalid_param", "source_info.source", 400)
        st["tt"][pid] = rec
        st["calls"].append({"provider": "tiktok", "publish_id": pid, "json": body})
        if f == "timeout":
            lose_answer()
        return tt_ok({"publish_id": pid, **data})

    @app.put("/tiktok-upload/{pid}")
    async def tt_upload(pid: str, request: Request, content_range: Optional[str] = Header(None)):
        rec = st["tt"].get(pid)
        if rec is None or rec["source"] != "FILE_UPLOAD":
            return Response(status_code=404)
        m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range or "")
        raw = await request.body()
        if not m or int(m[3]) != rec["size"] or len(raw) != int(m[2]) - int(m[1]) + 1:
            return Response(status_code=400)
        if int(m[1]) != rec["uploaded"]:
            return Response(status_code=416, headers={"Content-Range": f"bytes 0-{rec['uploaded'] - 1}/{rec['size']}"})
        rec["uploaded"] = int(m[2]) + 1
        done = rec["uploaded"] == rec["size"]
        return Response(status_code=201 if done else 206,
                        headers={"Content-Range": f"bytes 0-{rec['uploaded'] - 1}/{rec['size']}"})

    @app.post("/tiktok-social/v2/post/publish/status/fetch/")
    async def tt_status(request: Request, authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_status")
        if err:
            return err
        rec = st["tt"].get((await request.json()).get("publish_id"))
        if rec is None:
            return tt_err("invalid_publish_id", "publish_id not found", 400)
        base = {"uploaded_bytes": rec["uploaded"], "downloaded_bytes": 0}
        if rec["cancelled"]:
            return tt_ok({**base, "status": "FAILED", "fail_reason": "publish_cancelled"})
        if rec["source"] == "FILE_UPLOAD" and rec["uploaded"] < rec["size"]:
            return tt_ok({**base, "status": "PROCESSING_UPLOAD"})
        if rec["polls"] > 0:
            rec["polls"] -= 1
            return tt_ok({**base, "status": "PROCESSING_DOWNLOAD" if rec["source"] == "PULL_FROM_URL" else "PROCESSING_UPLOAD"})
        if rec["outcome"]:
            return tt_ok({**base, **rec["outcome"]})
        ids = [7300000000000000000 + int(re.sub(r"\D", "", rec_id(rec)) or 0)] if rec["privacy"] == "PUBLIC_TO_EVERYONE" else []
        return tt_ok({**base, "status": "PUBLISH_COMPLETE", "publicaly_available_post_id": ids})

    def rec_id(rec) -> str:
        return next(k for k, v in st["tt"].items() if v is rec)

    @app.post("/tiktok-social/v2/post/publish/cancel/")
    async def tt_cancel(request: Request, authorization: Optional[str] = Header(None)):
        err, _ = tt_gate(authorization, "tt_cancel")
        if err:
            return err
        rec = st["tt"].get((await request.json()).get("publish_id"))
        if rec is None:
            return tt_err("invalid_publish_id", "publish_id not found", 400)
        if rec["source"] != "PULL_FROM_URL" or rec["polls"] <= 0:
            return tt_err("publish_not_cancellable", "The publish task is already final or not cancellable", 400)
        rec["cancelled"] = True
        return tt_ok({})

    @app.get("/videos/{name}")
    async def video(name: str):          # the company's own media file (FILE_UPLOAD reads it)
        return Response(b"\0" * st["video_size"], media_type="video/mp4")

    # ── Meta Graph (Page + Instagram) ────────────────────────────────────
    def meta_err(code: int, status: int, msg: str):
        return JSONResponse({"error": {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "sim"}}, status)

    def page_gate(authorization, fk: str = "social"):
        f = fault(fk)
        if authorization != f"Bearer {TOKENS['meta']}" or f == "auth":
            return meta_err(190, 401, "Error validating access token"), None
        if f == "perm":
            return meta_err(200, 403, "(#200) Requires pages_manage_posts permission"), None
        if f == "500":
            return meta_err(2, 500, "An unexpected error has occurred"), None
        return None, f

    @app.post("/meta/{ver}/{node}/feed")
    async def page_feed(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err, f = page_gate(authorization)
        if err:
            return err
        st["calls"].append({"provider": "facebook", "form": dict(await request.form())})
        if f == "timeout":
            lose_answer()
        return {"id": f"{node}_{len(st['calls'])}"}

    @app.post("/meta/{ver}/{node}/photos")
    async def page_photo(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if not str(form.get("url", "")).startswith("https://"):
            return meta_err(100, 400, "Invalid image URL")
        st["calls"].append({"provider": "facebook-photo", "form": form})
        return {"id": "ph1", "post_id": f"{node}_ph1"}

    @app.post("/meta/{ver}/{node}/media")
    async def ig_media(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if len(form.get("caption", "")) > 2200 or not str(form.get("image_url", "")).startswith("https://"):
            return meta_err(100, 400, "Invalid parameter")
        st["n"] += 1
        cid = f"1789{run:06d}{st['n']:04d}"
        st["ig"][cid] = {"polls": st["processing_polls"], "outcome": (st["next_outcome"] or {}).get("status_code"),
                         "published": None}
        st["next_outcome"] = None
        st["calls"].append({"provider": "instagram-container", "form": form, "id": cid})
        return {"id": cid}

    @app.get("/meta/{ver}/{cid}")
    async def ig_container(ver: str, cid: str, fields: str = "", authorization: Optional[str] = Header(None)):
        err, _ = page_gate(authorization, "ig_status")
        if err:
            return err
        c = st["ig"].get(cid)
        if c is None:
            return meta_err(100, 400, "Unsupported get request")
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

    @app.post("/meta/{ver}/{node}/media_publish")
    async def ig_publish(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err, f = page_gate(authorization, "ig_publish")
        if err:
            return err
        cid = dict(await request.form()).get("creation_id")
        c = st["ig"].get(cid)
        if c is None or c["polls"] > 0 or c["outcome"]:
            return meta_err(9007, 400, "Media ID is not available")
        if c["published"]:
            return meta_err(9007, 400, "The media has already been published")
        c["published"] = f"ig-media-{cid}"
        st["calls"].append({"provider": "instagram", "creation_id": cid})
        if f == "timeout":
            lose_answer()
        return {"id": c["published"]}

    # ── LinkedIn Posts API ───────────────────────────────────────────────
    @app.post("/linkedin/rest/posts")
    async def li_post(request: Request, authorization: Optional[str] = Header(None),
                      linkedin_version: Optional[str] = Header(None)):
        if authorization != f"Bearer {TOKENS['linkedin']}":
            return JSONResponse({"status": 401, "message": "Invalid access token"}, 401)
        if linkedin_version != LI_VERSION:
            return JSONResponse({"status": 426, "message": "Requested version is not active"}, 426)
        body = await request.json()
        if not body.get("author", "").startswith("urn:li:organization:") or len(body.get("commentary", "")) > 3000:
            return JSONResponse({"status": 422, "message": "Invalid post"}, 422)
        st["calls"].append({"provider": "linkedin", "json": body})
        return Response(status_code=201, headers={"x-restli-id": f"urn:li:share:{9000 + len(st['calls'])}"})

    app.state.sim = st
    return app


if __name__ == "__main__":
    import argparse

    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    uvicorn.run(create_social_app(), host="127.0.0.1", port=ap.parse_args().port)
