"""Organic social publishing, content calendar and listening (M44.S01.T006–T008).

Publishing (documented APIs only):
- Facebook Page: Graph POST /{page}/feed (text + link) or /{page}/photos (one image by URL).
- Instagram professional account: Graph POST /{ig}/media (one image + caption) then /{ig}/media_publish.
- LinkedIn organisation: POST /rest/posts (text; link appended). Images need LinkedIn's upload flow → manual.
- TikTok: Content Posting API /v2/post/publish/video/init/ with PULL_FROM_URL, privacy SELF_ONLY (unaudited apps
  may only post privately; public posting needs TikTok's app audit).
- X and YouTube, and any format above that a network does not take this way → manual export.
Nothing is posted unless SOCIAL_PUBLISHING_ENABLED and the network's token are set. A post needs approval by a second
editor for its current version; editing the content after approval starts a new version that needs approval again.

Listening: comments/mentions arrive only from channels with listen_enabled (opt-in) through signed Meta webhooks, or
through manual CSV import for other networks. No scraping. A deleted comment is blanked. Sentiment and topics come from
a small keyword lexicon, and every tag lists the words that caused it; it is an aid, not a verdict.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.crm import SocialChannel, SocialItem, SocialPost

NETWORKS = ("facebook", "instagram", "linkedin", "tiktok", "x", "youtube")
LIMITS = {   # max text, media rule
    "facebook": (63206, "none_or_one_image"), "instagram": (2200, "one_image"), "linkedin": (3000, "none"),
    "tiktok": (2200, "one_video"), "x": (280, "any"), "youtube": (5000, "one_video"),
}
API_PUBLISHABLE = {"facebook", "instagram", "linkedin", "tiktok"}
CONFLICT_MINUTES = 30


class SocialError(Exception):
    pass


# ── validation ───────────────────────────────────────────────────────────

def problems(network: str, text: str, media: list[dict], link: Optional[str]) -> list[str]:
    """Constraint check against the network's documented limits. Empty list = postable by API."""
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
             "linkedin": settings.LINKEDIN_SOCIAL_ACCESS_TOKEN, "tiktok": settings.TIKTOK_SOCIAL_ACCESS_TOKEN}.get(network)
    return "API" if network in API_PUBLISHABLE and token and settings.SOCIAL_PUBLISHING_ENABLED else "MANUAL"


def log(post: SocialPost, event: str, detail: str = "") -> None:
    post.history = [*(post.history or []), {"at": datetime.now(timezone.utc).isoformat(), "event": event,
                                            "version": post.version, "detail": detail[:300]}]


# ── adapters ───────────────────────────────────────────────────────────

def _graph(path: str) -> str:
    return f"{settings.META_ADS_API_URL.rstrip('/')}/{settings.META_ADS_API_VERSION}/{path}"


def _ok(r: httpx.Response, network: str) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    err = body.get("error") if isinstance(body, dict) else None
    if r.status_code >= 400 or (err and not (isinstance(err, dict) and err.get("code") == "ok")):
        msg = (err or {}).get("message") if isinstance(err, dict) else None
        raise SocialError(f"{network}: {msg or body.get('message') or f'HTTP {r.status_code}'}")
    return body


async def _post_api(ch: SocialChannel, post: SocialPost) -> str:
    h = {"Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}"}
    async with provider_client() as c:
        if ch.network == "facebook":
            img = next((m for m in post.media if m["kind"] == "image"), None)
            if img:
                b = _ok(await c.post(_graph(f"{ch.external_id}/photos"), data={"url": img["url"], "caption": post.text}, headers=h), "facebook")
                return b.get("post_id") or b["id"]
            data = {"message": post.text, **({"link": post.link} if post.link else {})}
            return _ok(await c.post(_graph(f"{ch.external_id}/feed"), data=data, headers=h), "facebook")["id"]
        if ch.network == "instagram":
            created = _ok(await c.post(_graph(f"{ch.external_id}/media"),
                                       data={"image_url": post.media[0]["url"], "caption": post.text}, headers=h), "instagram")
            return _ok(await c.post(_graph(f"{ch.external_id}/media_publish"), data={"creation_id": created["id"]},
                                    headers=h), "instagram")["id"]
        if ch.network == "linkedin":
            body = {"author": f"urn:li:organization:{ch.external_id}",
                    "commentary": post.text + (f"\n{post.link}" if post.link else ""), "visibility": "PUBLIC",
                    "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
                    "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
            r = await c.post(f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/posts", json=body,
                             headers={"Authorization": f"Bearer {settings.LINKEDIN_SOCIAL_ACCESS_TOKEN}",
                                      "LinkedIn-Version": settings.LINKEDIN_ADS_VERSION, "X-Restli-Protocol-Version": "2.0.0"})
            if r.status_code >= 400:
                _ok(r, "linkedin")          # raises with LinkedIn's message
            return r.headers.get("x-restli-id") or ""
        if ch.network == "tiktok":
            body = {"post_info": {"title": post.text, "privacy_level": "SELF_ONLY", "disable_comment": False},
                    "source_info": {"source": "PULL_FROM_URL", "video_url": post.media[0]["url"]}}
            b = _ok(await c.post(f"{settings.TIKTOK_SOCIAL_API_URL.rstrip('/')}/v2/post/publish/video/init/", json=body,
                                 headers={"Authorization": f"Bearer {settings.TIKTOK_SOCIAL_ACCESS_TOKEN}"}), "tiktok")
            return b["data"]["publish_id"]
    raise SocialError(f"{ch.network} has no publishing adapter")


async def publish(db: AsyncSession, post: SocialPost) -> SocialPost:
    """Publish one approved, due post. Called by the worker; never twice (status claim + external id)."""
    ch = await db.get(SocialChannel, post.channel_id)
    if post.external_post_id:
        post.status = "PUBLISHED"
        return post
    issues = problems(ch.network, post.text, post.media or [], post.link)
    if publish_route(ch.network) != "API" or issues:
        post.status, post.error = "FAILED", ("; ".join(issues) or
                                             "Publishing is not enabled for this channel. Export the post and publish it manually.")
        log(post, "NOT_PUBLISHED", post.error)
        return post
    post.status = "PUBLISHING"
    await db.flush()
    try:
        post.external_post_id = (await _post_api(ch, post))[:120] or None
        post.status, post.published_at, post.error = "PUBLISHED", datetime.now(timezone.utc), None
        log(post, "PUBLISHED", post.external_post_id or "")
    except (SocialError, EgressBlocked) as e:
        post.status, post.error = "FAILED", str(e)[:500]
        log(post, "FAILED", post.error)
    except httpx.HTTPError as e:
        post.status = "FAILED"
        post.error = f"No answer from {ch.network} ({type(e).__name__}); check the channel before retrying — it may have posted."
        log(post, "FAILED_UNKNOWN", post.error)
    return post


async def publish_due(db: AsyncSession, now: Optional[datetime] = None) -> int:
    now = now or datetime.now(timezone.utc)
    rows = (await db.execute(select(SocialPost).where(SocialPost.status == "APPROVED", SocialPost.scheduled_at <= now,
                                                      SocialPost.approved_version == SocialPost.version)
                             .with_for_update(skip_locked=True).limit(20))).scalars().all()
    for p in rows:
        await publish(db, p)
        await db.commit()
    return len(rows)


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
    s, t, ev = tag(text or "")
    res = await db.execute(insert(SocialItem).values(
        channel_id=ch.id if ch else None, network=network, kind=kind, external_id=str(ext)[:120],
        parent_id=(str(parent)[:120] if parent else None), author=(author or "")[:200] or None, text=(text or "")[:5000] or None,
        url=url, occurred_at=at or datetime.now(timezone.utc), source=source, sentiment=s, topics=t, evidence=ev,
        status="NEW").on_conflict_do_nothing(constraint="uq_social_item_network_ext"))
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
