"""Organic social publishing, content calendar and listening (M44.S01.T006–T008; asynchronous state machine M48.S01.T005).

Publishing (documented APIs only):
- Facebook Page: Graph POST /{page}/feed (text + link) or /{page}/photos (one image by URL). The response id IS the post.
- LinkedIn organisation: POST /rest/posts (text; link appended); 201 + x-restli-id header is the created post.
- Instagram professional account (Content Publishing): POST /{ig}/media creates a container; GET /{container}?fields=
  status_code,status is polled (IN_PROGRESS → FINISHED | ERROR | EXPIRED | PUBLISHED) and POST /{ig}/media_publish is
  called only when the container is FINISHED. PUBLISHED only when media_publish returns an id, or the container itself
  reports PUBLISHED (answer of a timed-out publish call was lost).
  https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-container (Graph version from META_ADS_API_VERSION)
- TikTok Content Posting API v2 (Direct Post), https://developers.tiktok.com/doc/content-posting-api-get-started :
  * POST /v2/post/publish/creator_info/query/ first; the user picks a privacy_level from privacy_level_options
    (…-reference-query-creator-info). Unaudited clients may only post SELF_ONLY (…-reference-direct-post,
    error unaudited_client_can_only_post_to_private_accounts) → TIKTOK_APP_AUDITED=false forces SELF_ONLY.
  * Explicit user consent is stored with the choices; without it nothing is submitted.
  * POST /v2/post/publish/video/init/ with source PULL_FROM_URL (URL must be under a verified domain / URL prefix:
    url_ownership_unverified) or FILE_UPLOAD (chunks 5–64 MB, last ≤128 MB, < 5 MB whole, ≤1000 chunks, sequential PUT
    with Content-Range; 206 partial, 201 done) — …-media-transfer-guide.
  * publish_id is only a submission id. POST /v2/post/publish/status/fetch/ is polled (…-reference-get-video-status):
    PROCESSING_UPLOAD / PROCESSING_DOWNLOAD → PROCESSING; PUBLISH_COMPLETE → PUBLISHED (publicaly_available_post_id
    when TikTok gives one); FAILED → FAILED with fail_reason (publish_cancelled → CANCELLED).
  * POST /v2/post/publish/cancel/ (best effort, PULL_FROM_URL downloads; publish_not_cancellable otherwise).
  * Webhooks post.publish.* signed with TikTok-Signature t=..,s=HMAC-SHA256(client_secret, "t.body")
    (https://developers.tiktok.com/doc/webhooks-verification); a webhook only triggers a status fetch, never PUBLISHED.
- X and YouTube, and any format above that a network does not take this way → manual export.

State machine: APPROVED → SUBMITTING (claim committed BEFORE any provider call) → SUBMITTED → PROCESSING → PUBLISHED |
FAILED | CANCELLED; no answer / 5xx on a mutating call → UNKNOWN (never resubmitted automatically). A SUBMITTING row left
by a crash becomes UNKNOWN; rows with a provider_ref are reconciled by status polling (reads retried with backoff).
A post still not final after SOCIAL_PUBLISH_TIMEOUT_MINUTES becomes UNKNOWN and keeps being reconciled.
publish_mode records SIMULATED (local simulators) or LIVE (PROVIDER_EGRESS=live) for every submission.
Nothing is posted unless SOCIAL_PUBLISHING_ENABLED and the network's token are set. A post needs approval by a second
editor for its current version; editing the content after approval starts a new version that needs approval again.

Listening: comments/mentions arrive only from channels with listen_enabled (opt-in) through signed Meta webhooks, or
through manual CSV import for other networks. No scraping. A deleted comment is blanked. Sentiment and topics come from
a small keyword lexicon, and every tag lists the words that caused it; it is an aid, not a verdict.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import hmac
import io
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, egress_mode, provider_client
from app.models.crm import SocialChannel, SocialItem, SocialPost
from app.models import m49_social as _m49_social  # noqa: F401  (maps the M49 side tables)
from app.services import social_formats as sf

NETWORKS = ("facebook", "instagram", "linkedin", "tiktok", "x", "youtube")
LIMITS = {   # max text, media rule
    "facebook": (63206, "none_or_one_image"), "instagram": (2200, "one_image"), "linkedin": (3000, "none"),
    "tiktok": (2200, "one_video"), "x": (280, "any"), "youtube": (5000, "one_video"),
}
API_PUBLISHABLE = {"facebook", "instagram", "linkedin", "tiktok", "x", "youtube"}
CONFLICT_MINUTES = 30
IN_FLIGHT = ("SUBMITTED", "PROCESSING", "UNKNOWN")
TT_PRIVACY = ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY")
MB = 1024 * 1024
CHUNK_MIN, CHUNK_MAX, MAX_CHUNKS = 5 * MB, 64 * MB, 1000
CLAIM_STALE = timedelta(minutes=5)
WEBHOOK_WINDOW = 300     # seconds; TikTok leaves the tolerance to the receiver


class SocialError(Exception):
    def __init__(self, msg: str, code: Optional[str] = None, retryable: bool = False):
        super().__init__(msg)
        self.code, self.retryable = code, retryable


# ── validation ───────────────────────────────────────────────────────────

def effective_format(network: str, post: SocialPost) -> Optional[str]:
    return post.format or sf.infer_format(network, post.media or [], post.link)


def problems(network: str, text: str, media: list[dict], link: Optional[str], fmt: Optional[str] = None,
             fopts: Optional[dict] = None, scheduled_at: Optional[datetime] = None, channel_opts: Optional[dict] = None) -> list[str]:
    """Constraint check against the network's documented limits. Empty list = postable by API."""
    if fmt is None and network in ("x", "youtube"):
        fmt = sf.infer_format(network, media, link)
        if fmt is None:
            return ["YouTube takes exactly one video." if network == "youtube" else "Choose a post format."]
    if fmt:
        return sf.validate(network, fmt, text, media, link, fopts, scheduled_at=scheduled_at, channel_opts=channel_opts)
    out = []
    max_len, rule = LIMITS[network]
    if len(text) > max_len:
        out.append(f"Text is {len(text)} characters; {network} allows {max_len}.")
    if network == "instagram" and len(re.findall(r"#\w+", text)) > 30:
        out.append("Instagram allows at most 30 hashtags.")
    imgs = [m for m in media if m.get("kind") == "image"]
    vids = [m for m in media if m.get("kind") == "video"]
    for m in media:
        if not str(m.get("url", "")).startswith("https://"):
            out.append("Media must be a public https URL.")
            break
    if rule == "one_image" and (len(imgs) != 1 or vids):
        out.append(f"{network} posts here need exactly one image (carousels and video: post manually).")
    if rule == "one_video" and (len(vids) != 1 or imgs):
        out.append(f"{network} needs exactly one video.")
    if rule == "none_or_one_image" and (len(imgs) > 1 or vids):
        out.append("Facebook posts here take text, a link or one image (video and albums: post manually).")
    if rule == "none" and media:
        out.append("LinkedIn image/video posts need LinkedIn's upload flow: post manually.")
    if network == "linkedin" and link and len(text) + len(link) + 1 > max_len:
        out.append("Text plus link exceeds LinkedIn's 3000 characters.")
    return out


def publish_route(network: str) -> str:
    """API when the network has a documented posting API we use and its token is set, else MANUAL."""
    token = {"facebook": settings.META_PAGE_ACCESS_TOKEN, "instagram": settings.META_PAGE_ACCESS_TOKEN,
             "linkedin": settings.LINKEDIN_SOCIAL_ACCESS_TOKEN, "tiktok": settings.TIKTOK_SOCIAL_ACCESS_TOKEN,
             "youtube": sf.cfg("YOUTUBE_SOCIAL_ACCESS_TOKEN", ""), "x": sf.cfg("X_SOCIAL_ACCESS_TOKEN", "")}.get(network)
    return "API" if network in API_PUBLISHABLE and token and settings.SOCIAL_PUBLISHING_ENABLED else "MANUAL"


def publish_mode() -> str:
    return "LIVE" if egress_mode() == "live" else "SIMULATED"


def tiktok_audited() -> bool:
    return bool(getattr(settings, "TIKTOK_APP_AUDITED", False))


def url_verified(url: str) -> bool:
    """TikTok PULL_FROM_URL ownership: a verified URL prefix (https://host/path/) or a verified domain (and its subdomains)."""
    raw = getattr(settings, "TIKTOK_VERIFIED_URL_PREFIXES", "") or ""
    entries = [e.strip() for e in (raw.split(",") if isinstance(raw, str) else raw) if e and e.strip()]
    host = (urlsplit(url).hostname or "").lower()
    for e in entries:
        if e.startswith("https://"):
            if e.endswith("/") and url.startswith(e):
                return True
        elif host == e.lower() or host.endswith("." + e.lower()):
            return True
    return False


def chunk_plan(size: int) -> tuple[int, int]:
    """(chunk_size, total_chunk_count) per the media transfer guide; the last chunk takes the remainder."""
    if size <= 0:
        raise SocialError("The video is empty.", "invalid_param")
    if size < CHUNK_MIN or size <= CHUNK_MAX:
        return size, 1
    count = size // CHUNK_MAX
    if count > MAX_CHUNKS:
        raise SocialError("The video is too large for TikTok's upload (more than 1000 chunks).", "invalid_param")
    return CHUNK_MAX, count


def tiktok_issues(post: SocialPost) -> list[str]:
    o = post.publish_options or {}
    fmt = post.format or "video"
    inbox, photo = fmt.endswith("_inbox"), fmt.startswith("photo")
    out = []
    if not o.get("consent"):
        out.append("TikTok needs the poster's explicit consent" + ("" if inbox else " and a privacy choice") + " (set TikTok options).")
    elif inbox:
        pass            # MEDIA_UPLOAD sends no post_info: the creator picks privacy in the TikTok app
    elif o.get("privacy_level") not in TT_PRIVACY:
        out.append("Choose a TikTok privacy level.")
    elif not tiktok_audited() and o["privacy_level"] != "SELF_ONLY":
        out.append("This TikTok app is not audited: only SELF_ONLY (private) posts are allowed.")
    if photo and o.get("source", "PULL_FROM_URL") != "PULL_FROM_URL":
        out.append("TikTok photo posts support PULL_FROM_URL only.")
    if (photo or o.get("source", "PULL_FROM_URL") == "PULL_FROM_URL") and any(not url_verified(m["url"]) for m in post.media or []):
        out.append("The media URL is not under a TikTok-verified domain or URL prefix (use FILE_UPLOAD for video, or verify the domain).")
    return out


def log(post: SocialPost, event: str, detail: str = "") -> None:
    post.history = [*(post.history or []), {"at": datetime.now(timezone.utc).isoformat(), "event": event,
                                            "version": post.version, "detail": detail[:300]}]


# ── provider calls ─────────────────────────────────────────────────────

def _graph(path: str) -> str:
    return f"{settings.META_ADS_API_URL.rstrip('/')}/{settings.META_ADS_API_VERSION}/{path}"


def _meta_h() -> dict:
    return {"Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}"}


def _ok(r: httpx.Response, network: str) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    err = body.get("error") if isinstance(body, dict) else None
    if r.status_code >= 400 or (err and not (isinstance(err, dict) and err.get("code") == "ok")):
        msg = (err or {}).get("message") if isinstance(err, dict) else None
        code = str((err or {}).get("code")) if isinstance(err, dict) and err.get("code") is not None else f"http_{r.status_code}"
        raise SocialError(f"{network}: {msg or body.get('message') or f'HTTP {r.status_code}'}", code,
                          r.status_code >= 500 or r.status_code == 429)
    return body


async def _tt(c: httpx.AsyncClient, path: str, body: Optional[dict]) -> dict:
    r = await c.post(f"{settings.TIKTOK_SOCIAL_API_URL.rstrip('/')}{path}", json=body,
                     headers={"Authorization": f"Bearer {settings.TIKTOK_SOCIAL_ACCESS_TOKEN}",
                              "Content-Type": "application/json; charset=UTF-8"})
    return _ok(r, "tiktok").get("data") or {}


async def _read(fn):
    """Status reads only: retried with exponential backoff on 429/5xx/transport errors."""
    backoff = float(getattr(settings, "SOCIAL_STATUS_BACKOFF_SECONDS", 1.0))
    for i in range(3):
        try:
            async with provider_client() as c:
                return await fn(c)
        except (httpx.TransportError, SocialError) as e:
            if i == 2 or (isinstance(e, SocialError) and not e.retryable):
                raise
            await asyncio.sleep(backoff * 2 ** i)


async def tiktok_creator_info(c: Optional[httpx.AsyncClient] = None) -> dict:
    """creator_info, with the privacy options this app may actually use (unaudited → SELF_ONLY only)."""
    if c is None:
        return await _read(tiktok_creator_info)
    d = await _tt(c, "/v2/post/publish/creator_info/query/", None)
    opts = [o for o in d.get("privacy_level_options") or [] if o in TT_PRIVACY]
    return {"creator_username": d.get("creator_username"), "creator_nickname": d.get("creator_nickname"),
            "provider_privacy_level_options": opts, "audited": tiktok_audited(),
            "privacy_level_options": opts if tiktok_audited() else [o for o in opts if o == "SELF_ONLY"],
            "comment_disabled": bool(d.get("comment_disabled")), "duet_disabled": bool(d.get("duet_disabled")),
            "stitch_disabled": bool(d.get("stitch_disabled")),
            "max_video_post_duration_sec": d.get("max_video_post_duration_sec")}


async def _post_direct(c: httpx.AsyncClient, ch: SocialChannel, post: SocialPost) -> str:
    """Facebook and LinkedIn create the post synchronously: the returned id is the live post."""
    if ch.network == "facebook":
        img = next((m for m in post.media if m["kind"] == "image"), None)
        if img:
            b = _ok(await c.post(_graph(f"{ch.external_id}/photos"), data={"url": img["url"], "caption": post.text},
                                 headers=_meta_h()), "facebook")
            return b.get("post_id") or b["id"]
        data = {"message": post.text, **({"link": post.link} if post.link else {})}
        return _ok(await c.post(_graph(f"{ch.external_id}/feed"), data=data, headers=_meta_h()), "facebook")["id"]
    body = {"author": f"urn:li:organization:{ch.external_id}",
            "commentary": post.text + (f"\n{post.link}" if post.link else ""), "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    r = await c.post(f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/posts", json=body,
                     headers={"Authorization": f"Bearer {settings.LINKEDIN_SOCIAL_ACCESS_TOKEN}",
                              "LinkedIn-Version": settings.LINKEDIN_ADS_VERSION, "X-Restli-Protocol-Version": "2.0.0"})
    if r.status_code >= 400:
        _ok(r, "linkedin")          # raises with LinkedIn's message
    if not r.headers.get("x-restli-id"):
        raise SocialError("linkedin: created without a post id", "no_id", retryable=True)
    return r.headers["x-restli-id"]


def _tt_post_info(post: SocialPost, info: dict) -> dict:
    o = post.publish_options or {}
    return {"title": post.text, "privacy_level": o["privacy_level"],
            "disable_comment": bool(o.get("disable_comment")) or info["comment_disabled"],
            "disable_duet": bool(o.get("disable_duet")) or info["duet_disabled"],
            "disable_stitch": bool(o.get("disable_stitch")) or info["stitch_disabled"],
            **{k: post.format_options[k] for k in ("video_cover_timestamp_ms", "brand_content_toggle", "brand_organic_toggle", "is_aigc")
               if (post.format_options or {}).get(k) is not None}}


async def _tt_upload(c: httpx.AsyncClient, url: str, blob: bytes, chunk: int, count: int) -> None:
    total = len(blob)
    for i in range(count):
        first = i * chunk
        last = total - 1 if i == count - 1 else first + chunk - 1
        r = await c.put(url, content=blob[first:last + 1],
                        headers={"Content-Type": "video/mp4", "Content-Range": f"bytes {first}-{last}/{total}"})
        if r.status_code not in (201, 206):
            raise SocialError(f"tiktok: chunk upload answered HTTP {r.status_code}", f"upload_{r.status_code}",
                              r.status_code >= 500)


# ── state machine ──────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _schedule(post: SocialPost) -> None:
    base = int(getattr(settings, "SOCIAL_STATUS_POLL_SECONDS", 15))
    post.next_poll_at = _now() + timedelta(seconds=min(base * 2 ** min(post.poll_count or 0, 6), 900))


def _published(post: SocialPost, post_id: Optional[str], detail: str) -> None:
    post.status, post.published_at, post.error, post.next_poll_at = "PUBLISHED", _now(), None, None
    post.external_post_id = (post_id or "")[:120] or None
    log(post, "PUBLISHED", f"{detail}; post id {post.external_post_id or 'not given by the provider'}")


def _failed(post: SocialPost, reason: Optional[str], msg: str) -> None:
    post.status, post.fail_reason, post.error, post.next_poll_at = "FAILED", (reason or "")[:120] or None, msg[:500], None
    log(post, "FAILED", msg)


def _unknown(post: SocialPost, msg: str) -> None:
    post.status, post.error = "UNKNOWN", msg[:500]
    if post.provider_ref:
        _schedule(post)
    log(post, "UNKNOWN", msg)


def _submitted(post: SocialPost, ref: str, status: str) -> None:
    post.provider_ref, post.status, post.submitted_at = str(ref)[:120], status, _now()
    post.next_poll_at = _now()
    log(post, status, f"provider ref {post.provider_ref} (a submission id, not a publication)")


async def publish(db: AsyncSession, post: SocialPost) -> SocialPost:
    """Submit one approved post. The claim is committed before any provider call, so a crash can never post twice."""
    ch = await db.get(SocialChannel, post.channel_id)
    fmt = effective_format(ch.network, post)
    issues = problems(ch.network, post.text, post.media or [], post.link, fmt, post.format_options, post.scheduled_at, ch.options)
    if ch.network == "tiktok" and not issues:
        issues = tiktok_issues(post)
    if publish_route(ch.network) != "API" or issues:
        post.status, post.error = "FAILED", ("; ".join(issues) or
                                             "Publishing is not enabled for this channel. Export the post and publish it manually.")
        log(post, "NOT_PUBLISHED", post.error)
        return post
    post.status, post.claimed_at, post.publish_mode, post.poll_count = "SUBMITTING", _now(), publish_mode(), 0
    post.provider_ref = post.provider_status = post.fail_reason = post.error = post.submitted_at = None
    post.format, post.flow_state = fmt or post.format, None
    log(post, "CLAIMED", f"idempotency key {post.idempotency_key} v{post.version} ({post.publish_mode})")
    await db.commit()
    try:
        async with provider_client() as c:
            from app.services import social_flows as flows
            if post.format and (ch.network != "tiktok" or post.format in ("photo", "photo_inbox", "video_inbox")):
                await flows.submit(db, c, ch, post)
            elif ch.network in ("facebook", "linkedin"):
                _published(post, await _post_direct(c, ch, post), f"{ch.network} returned the created post")
            elif ch.network == "instagram":
                b = _ok(await c.post(_graph(f"{ch.external_id}/media"), data={"image_url": post.media[0]["url"],
                                                                              "caption": post.text}, headers=_meta_h()), "instagram")
                _submitted(post, b["id"], "PROCESSING")
            else:
                await _submit_tiktok(db, c, post)
    except EgressBlocked as e:                       # refused before a socket was opened: nothing was sent
        if post.provider_ref:
            log(post, "UPLOAD_ERROR", str(e))
        else:
            _failed(post, "egress_blocked", str(e))
    except SocialError as e:
        if post.provider_ref:                        # accepted by the provider; its status decides the outcome
            log(post, "UPLOAD_ERROR", str(e))
        elif e.retryable:
            from app.services import social_flows as flows
            flows.mark_lookup(post, ch.network)
            _unknown(post, f"{e} — the network may have accepted it; check the channel before retrying.")
        else:
            _failed(post, e.code, str(e))
    except httpx.HTTPError as e:
        if post.provider_ref:
            log(post, "UPLOAD_ERROR", type(e).__name__)
        else:
            from app.services import social_flows as flows
            flows.mark_lookup(post, ch.network)
            _unknown(post, f"No answer from {ch.network} ({type(e).__name__}); check the channel before retrying — it may have posted.")
    await db.commit()
    if post.status in IN_FLIGHT and post.provider_ref:
        await refresh(db, post, ch)
        await db.commit()
    return post


async def _submit_tiktok(db: AsyncSession, c: httpx.AsyncClient, post: SocialPost) -> None:
    info = await tiktok_creator_info(c)
    o = post.publish_options or {}
    if o.get("privacy_level") not in info["privacy_level_options"]:
        raise SocialError(f"tiktok: privacy {o.get('privacy_level')} is not offered for this creator "
                          f"({', '.join(info['privacy_level_options']) or 'none'})", "privacy_level_option_mismatch")
    url = post.media[0]["url"]
    cap, dur = info.get("max_video_post_duration_sec"), post.media[0].get("duration_sec")
    if cap and dur and dur > cap:
        raise SocialError(f"tiktok: this creator may post videos up to {cap}s; the video lasts {dur}s", "duration_check_failed")
    if o.get("source") == "FILE_UPLOAD":
        r = await c.get(url)
        if r.status_code != 200:
            raise SocialError(f"tiktok: could not read the video file (HTTP {r.status_code})", "file_unreadable")
        blob = r.content
        chunk, count = chunk_plan(len(blob))
        source = {"source": "FILE_UPLOAD", "video_size": len(blob), "chunk_size": chunk, "total_chunk_count": count}
    else:
        blob, source = None, {"source": "PULL_FROM_URL", "video_url": url}
    d = await _tt(c, "/v2/post/publish/video/init/", {"post_info": _tt_post_info(post, info), "source_info": source})
    _submitted(post, d["publish_id"], "SUBMITTED")
    await db.commit()                                # publish_id is durable before the upload starts
    if blob is not None:
        await _tt_upload(c, d["upload_url"], blob, chunk, count)
        log(post, "UPLOADED", f"{count} chunk(s), {len(blob)} bytes")


async def refresh(db: AsyncSession, post: SocialPost, ch: Optional[SocialChannel] = None) -> SocialPost:
    """Reconcile one in-flight post with the provider's status. Only a documented final state ends it."""
    ch = ch or await db.get(SocialChannel, post.channel_id)
    if post.status not in IN_FLIGHT or not post.provider_ref:
        return post
    post.poll_count = (post.poll_count or 0) + 1
    try:
        handled = False
        if post.format and ch.network != "tiktok":
            from app.services import social_flows as flows
            handled = not await flows.advance(db, ch, post)
        if handled:
            pass
        elif ch.network == "tiktok":
            d = await _read(lambda c: _tt(c, "/v2/post/publish/status/fetch/", {"publish_id": post.provider_ref}))
            s = post.provider_status = str(d.get("status") or "")[:40]
            if s == "PUBLISH_COMPLETE":
                ids = d.get("publicaly_available_post_id") or []      # spelling as documented
                _published(post, str(ids[0]) if ids else None, "TikTok status PUBLISH_COMPLETE")
            elif s == "SEND_TO_USER_INBOX" and (post.format or "").endswith("_inbox"):
                post.status, post.next_poll_at = "EXPORTED", None     # a draft in the creator's inbox: NOT published
                log(post, "DELIVERED_TO_INBOX", "TikTok put it in the creator's inbox; the creator finishes publishing in the TikTok app")
            elif s == "FAILED" and d.get("fail_reason") == "publish_cancelled":
                post.status, post.fail_reason, post.next_poll_at = "CANCELLED", "publish_cancelled", None
                log(post, "CANCELLED", "TikTok confirmed the cancellation")
            elif s == "FAILED":
                _failed(post, d.get("fail_reason"), f"TikTok rejected the post: {d.get('fail_reason') or 'no reason given'}")
            elif post.status != "UNKNOWN":
                post.status = "PROCESSING"
        elif ch.network == "instagram":
            async def container(c):
                return _ok(await c.get(_graph(post.provider_ref), params={"fields": "status_code,status"},
                                       headers=_meta_h()), "instagram")
            d = await _read(container)
            s = post.provider_status = str(d.get("status_code") or "")[:40]
            if s == "FINISHED":                      # ready: publish now (a container publishes at most once)
                async with provider_client() as c:
                    b = _ok(await c.post(_graph(f"{ch.external_id}/media_publish"), data={"creation_id": post.provider_ref},
                                         headers=_meta_h()), "instagram")
                _published(post, b["id"], "Instagram media_publish returned the media id")
            elif s == "PUBLISHED":
                _published(post, None, "Instagram container status PUBLISHED")
            elif s in ("ERROR", "EXPIRED"):
                _failed(post, s, f"Instagram container {s.lower()}: {d.get('status') or ''}".strip())
            elif post.status != "UNKNOWN":
                post.status = "PROCESSING"
        else:
            return post
    except (SocialError, httpx.HTTPError, EgressBlocked) as e:
        code = getattr(e, "code", None)
        if code in ("invalid_publish_id", "token_not_authorized_for_specified_publish_id"):
            _unknown(post, f"Status not readable: {e}")
        else:
            log(post, "PROVIDER_CALL_FAILED", str(e) or type(e).__name__)
    if post.status in IN_FLIGHT:
        limit = timedelta(minutes=int(getattr(settings, "SOCIAL_PUBLISH_TIMEOUT_MINUTES", 30)))
        if post.status != "UNKNOWN" and post.provider_status != "SCHEDULED" and post.submitted_at and _now() - post.submitted_at > limit:
            _unknown(post, f"Not final after {limit}; still reconciling with {ch.network}.")
        _schedule(post)
    return post


async def cancel_at_provider(db: AsyncSession, post: SocialPost) -> str:
    """Cancel an in-flight post where the network allows it. Returns the resulting status."""
    ch = await db.get(SocialChannel, post.channel_id)
    if ch.network == "instagram" and post.status in ("SUBMITTED", "PROCESSING"):
        post.status, post.next_poll_at = "CANCELLED", None    # never publish the container; it expires after 24 h
        log(post, "CANCELLED", "container will not be published")
        return post.status
    if ch.network == "facebook" and post.provider_status == "SCHEDULED" and post.provider_ref and (post.flow_state or {}).get("kind") == "fb_post":
        async with provider_client() as c:       # DELETE /{post}: removes the scheduled (unpublished) post
            _ok(await c.delete(_graph(post.provider_ref), headers=_meta_h()), "facebook")
        post.status, post.next_poll_at = "CANCELLED", None
        log(post, "CANCELLED", "the scheduled Facebook post was deleted")
        return post.status
    if ch.network != "tiktok" or post.status not in ("SUBMITTED", "PROCESSING") or not post.provider_ref:
        raise SocialError(f"A {post.status.lower()} {ch.network} post cannot be cancelled here.", "not_cancellable")
    if (post.publish_options or {}).get("source") == "FILE_UPLOAD":
        raise SocialError("TikTok cancels only PULL_FROM_URL downloads.", "publish_not_cancellable")
    async with provider_client() as c:
        await _tt(c, "/v2/post/publish/cancel/", {"publish_id": post.provider_ref})
    log(post, "CANCEL_REQUESTED", "TikTok accepted the cancel request")
    await refresh(db, post, ch)
    return post.status


async def publish_due(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Worker tick (crm_automation_service): submit due posts, then recover/reconcile in-flight ones."""
    now = now or _now()
    done = 0
    for _ in range(20):   # one post per transaction: the row lock is held until its own commit (M44 review)
        p = (await db.execute(select(SocialPost).where(SocialPost.status == "APPROVED", SocialPost.scheduled_at <= now,
                                                       SocialPost.approved_version == SocialPost.version)
                              .order_by(SocialPost.scheduled_at).with_for_update(skip_locked=True).limit(1))).scalars().first()
        if p is None:
            break
        await publish(db, p)
        await db.commit()
        done += 1
    for p in (await db.execute(select(SocialPost).where(
            SocialPost.status == "APPROVED", SocialPost.format.isnot(None), SocialPost.approved_version == SocialPost.version,
            (SocialPost.scheduled_at.is_(None)) | (SocialPost.scheduled_at <= now + timedelta(days=30)))
            .order_by(SocialPost.scheduled_at).with_for_update(skip_locked=True).limit(20))).scalars().all():
        fo = p.format_options or {}
        if (fo.get("native_schedule") and p.scheduled_at and p.scheduled_at > now) or (fo.get("publish_at") and p.format in ("video", "short")):
            await publish(db, p)         # handed to the network's own scheduler (Facebook scheduled_publish_time / YouTube publishAt)
            await db.commit()
            done += 1
    await reconcile_due(db, now)
    from app.services import social_listening
    await social_listening.retention_sweep(db, now)
    await social_listening.poll_due(db)
    return done


async def reconcile_due(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Restart recovery: a stale claim becomes UNKNOWN (never resubmitted); SUBMITTED/PROCESSING/UNKNOWN are polled."""
    now = now or _now()
    stale = (await db.execute(select(SocialPost).where(SocialPost.status == "SUBMITTING",
                                                       SocialPost.claimed_at < now - CLAIM_STALE)
                              .with_for_update(skip_locked=True))).scalars().all()
    for p in stale:
        _unknown(p, "Interrupted between claim and the provider's answer; it may have posted. "
                    "Check the channel — this post is never resubmitted automatically.")
    await db.commit()
    n = 0
    for _ in range(20):
        p = (await db.execute(select(SocialPost).where(SocialPost.status.in_(IN_FLIGHT), SocialPost.provider_ref.isnot(None),
                                                       (SocialPost.next_poll_at.is_(None)) | (SocialPost.next_poll_at <= now))
                              .order_by(SocialPost.next_poll_at.asc().nullsfirst())
                              .with_for_update(skip_locked=True).limit(1))).scalars().first()
        if p is None:
            break
        await refresh(db, p)
        if p.status in IN_FLIGHT and p.next_poll_at and p.next_poll_at <= now:
            p.next_poll_at = now + timedelta(seconds=1)     # do not spin within one tick
        await db.commit()
        n += 1
    return n


# ── TikTok webhooks ────────────────────────────────────────────────────

def verify_tiktok(raw: bytes, header: str, now: Optional[float] = None) -> str:
    """TikTok-Signature: t=<unix>,s=<hex HMAC-SHA256(client_secret, "<t>.<raw body>")>. Returns the signature."""
    secret = getattr(settings, "TIKTOK_CLIENT_SECRET", "") or ""
    if not secret:
        raise SocialError("not configured")
    parts = dict(p.split("=", 1) for p in (header or "").split(",") if "=" in p)
    t, s = parts.get("t", ""), parts.get("s", "")
    if not t.isdigit():
        raise SocialError("bad signature")
    want = hmac.new(secret.encode(), t.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, s):
        raise SocialError("bad signature")
    if abs((now or time.time()) - int(t)) > WEBHOOK_WINDOW:
        raise SocialError("stale")
    return s


async def ingest_tiktok(db: AsyncSession, payload: dict, signature: str) -> dict:
    """post.publish.* events only trigger a status fetch; a replayed delivery (same signature) is ignored."""
    event = str(payload.get("event") or "")
    if not event.startswith("post.publish."):
        return {"result": "ignored"}
    content = payload.get("content")
    try:
        content = json.loads(content) if isinstance(content, str) else (content or {})
    except ValueError:
        return {"result": "ignored"}
    pid = str(content.get("publish_id") or "")
    post = (await db.execute(select(SocialPost).join(SocialChannel, SocialChannel.id == SocialPost.channel_id)
                             .where(SocialChannel.network == "tiktok", SocialPost.provider_ref == pid)
                             .with_for_update())).scalars().first() if pid else None
    if post is None:
        return {"result": "ignored"}
    digest = hashlib.sha256(signature.encode()).hexdigest()[:32]
    if any(h.get("event") == "WEBHOOK" and h.get("detail", "").endswith(digest) for h in post.history or []):
        return {"result": "replay"}
    log(post, "WEBHOOK", f"{event} {digest}")
    await refresh(db, post)
    return {"result": "processed", "status": post.status}


async def conflicts(db: AsyncSession, post: SocialPost) -> list[str]:
    if not post.scheduled_at:
        return []
    w = timedelta(minutes=CONFLICT_MINUTES)
    rows = (await db.execute(select(SocialPost).where(
        SocialPost.channel_id == post.channel_id, SocialPost.id != post.id,
        SocialPost.status.notin_(["CANCELLED", "FAILED"]),
        SocialPost.scheduled_at.between(post.scheduled_at - w, post.scheduled_at + w)))).scalars().all()
    return [f"Another post on this channel at {p.scheduled_at.isoformat()} (within {CONFLICT_MINUTES} minutes)." for p in rows]


# ── listening ──────────────────────────────────────────────────────────

POS = {"love", "great", "good", "excellent", "tasty", "delicious", "fresh", "thanks", "thank", "amazing", "best", "nice",
       "poa", "safi", "nzuri", "asante"}
NEG = {"bad", "late", "expensive", "broken", "leak", "leaking", "stale", "expired", "worst", "terrible", "rude", "missing",
       "complaint", "refund", "sick", "mbaya", "ghali", "chelewa"}
TOPICS = {"price": {"price", "expensive", "cheap", "cost", "ghali", "bei"}, "delivery": {"delivery", "late", "deliver", "chelewa", "order"},
          "quality": {"quality", "stale", "expired", "fresh", "taste", "tasty", "leak", "leaking"},
          "availability": {"stock", "available", "find", "shelf", "missing"}, "packaging": {"bottle", "pack", "packaging", "cap", "label"}}


def tag(text: str) -> tuple[str, list[str], dict]:
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    p, n = sorted(words & POS), sorted(words & NEG)
    sentiment = "POSITIVE" if len(p) > len(n) else "NEGATIVE" if len(n) > len(p) else "NEUTRAL"
    topics = {t: sorted(words & kw) for t, kw in TOPICS.items() if words & kw}
    return sentiment, sorted(topics), {"positive": p, "negative": n, "topics": topics}


def verify_meta(raw: bytes, header: str) -> None:
    if not settings.META_APP_SECRET:
        raise SocialError("not configured")
    want = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, header or ""):
        raise SocialError("bad signature")


async def _store(db: AsyncSession, ch: Optional[SocialChannel], network: str, kind: str, ext: str, *, parent=None,
                 author=None, text=None, url=None, at: Optional[datetime] = None, source="WEBHOOK") -> bool:
    if not ext:   # without an id the item cannot be deduplicated (M44 review)
        return False
    from app.services import social_listening as sl
    if await sl.is_opted_out(db, network, author):      # the author opted out: nothing is stored
        return False
    s, t, ev = tag(text or "")
    ev["source"] = {"network": network, "external_id": str(ext)[:120], "via": source, "channel": ch.external_id if ch else None}
    res = await db.execute(insert(SocialItem).values(
        channel_id=ch.id if ch else None, network=network, kind=kind, external_id=str(ext)[:120],
        parent_id=(str(parent)[:120] if parent else None), author=(author or "")[:200] or None, text=(text or "")[:5000] or None,
        url=url, occurred_at=at or datetime.now(timezone.utc), source=source, sentiment=s, topics=t, evidence=ev,
        status="NEW", retention_until=datetime.now(timezone.utc) + timedelta(days=sl.retention_days())).on_conflict_do_nothing(constraint="uq_social_item_network_ext"))
    return bool(res.rowcount)


async def _erase(db: AsyncSession, network: str, ext: str) -> None:
    it = (await db.execute(select(SocialItem).where(SocialItem.network == network, SocialItem.external_id == str(ext)))).scalar_one_or_none()
    if it:
        it.text, it.author, it.evidence, it.status, it.reply_draft = None, None, {}, "DELETED", None


async def ingest_meta(db: AsyncSession, payload: dict) -> dict:
    """Facebook Page feed comments and Instagram comments/mentions, only for opted-in channels."""
    stored = ignored = 0
    network = {"page": "facebook", "instagram": "instagram"}.get(payload.get("object"))
    for entry in payload.get("entry", []) if network else []:
        ch = (await db.execute(select(SocialChannel).where(SocialChannel.network == network,
                                                           SocialChannel.external_id == str(entry.get("id"))))).scalar_one_or_none()
        for chg in entry.get("changes", []):
            v = chg.get("value") or {}
            if ch is None or not ch.listen_enabled:
                ignored += 1
                continue
            at = datetime.fromtimestamp(int(v["created_time"]), timezone.utc) if str(v.get("created_time", "")).isdigit() else None
            if network == "facebook" and chg.get("field") == "feed" and v.get("item") == "comment":
                if v.get("verb") == "remove":
                    await _erase(db, network, v.get("comment_id"))
                    continue
                stored += await _store(db, ch, network, "COMMENT", v.get("comment_id"), parent=v.get("post_id"),
                                       author=(v.get("from") or {}).get("name"), text=v.get("message"), at=at)
            elif network == "instagram" and chg.get("field") == "comments":
                stored += await _store(db, ch, network, "COMMENT", v.get("id"), parent=(v.get("media") or {}).get("id"),
                                       author=(v.get("from") or {}).get("username"), text=v.get("text"), at=at)
            elif network == "instagram" and chg.get("field") == "mentions":
                stored += await _store(db, ch, network, "MENTION", v.get("comment_id") or v.get("media_id"),
                                       parent=v.get("media_id"), at=at)
            else:
                ignored += 1
    return {"stored": stored, "ignored": ignored}


async def import_csv(db: AsyncSession, raw: str) -> dict:
    """Manual import (for networks without a webhook we use). Columns: network,kind,external_id,author,text,url,occurred_at."""
    stored = dup = bad = 0
    for row in csv.DictReader(io.StringIO(raw)):
        net, kind = (row.get("network") or "").strip().lower(), (row.get("kind") or "COMMENT").strip().upper()
        if net not in NETWORKS or kind not in ("COMMENT", "MENTION", "MESSAGE") or not row.get("external_id"):
            bad += 1
            continue
        try:
            at = datetime.fromisoformat(row["occurred_at"]) if row.get("occurred_at") else None
            at = at.replace(tzinfo=timezone.utc) if at and at.tzinfo is None else at
        except ValueError:
            bad += 1
            continue
        url = row.get("url") if str(row.get("url", "")).startswith("https://") else None
        if await _store(db, None, net, kind, row["external_id"], author=row.get("author"), text=row.get("text"),
                        url=url, at=at, source="IMPORT"):
            stored += 1
        else:
            dup += 1
    return {"stored": stored, "duplicates": dup, "rejected": bad}


def suggest_reply(item: SocialItem) -> str:
    """A starting point for a human to edit — never sent automatically."""
    name = (item.author or "there").split(" ")[0]
    if item.sentiment == "NEGATIVE":
        topic = (item.topics or ["your experience"])[0]
        return (f"Hi {name}, we're sorry to hear about the {topic}. Please send us a direct message with your order "
                "details so we can put it right.")
    if item.sentiment == "POSITIVE":
        return f"Thank you {name}! We're glad you enjoy POVU."
    return f"Hi {name}, thanks for reaching out — how can we help?"
