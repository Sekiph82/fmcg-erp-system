"""Social listening and moderation across networks (M49.S01.T010). Extends the Meta webhook inbox of M44.S01.T008.

What each network lets us do is in social_formats.MODERATION (unsupported operations are refused with the reason, and the UI
shows them disabled). No scraping and no platform-wide search: only comments on our own published posts (LinkedIn, YouTube,
Facebook, Instagram) and mentions of our own account (X), read through the official API with the channel's token, and only
for channels the owner opted in (listen_enabled). TikTok exposes no comments to this integration (metrics only).
Official contracts:
- LinkedIn Comments API https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api (202611)
- YouTube commentThreads.list / comments.insert / setModerationStatus / delete https://developers.google.com/youtube/v3/docs/commentThreads
- X GET /2/users/{id}/mentions, PUT /2/tweets/{id}/hidden https://docs.x.com/x-api (UNVERIFIED in the M48 matrix)
- Facebook /{comment}/comments, is_hidden, DELETE; Instagram /{comment}/replies, hide, DELETE (Graph v27.0).
A reply is a draft, approved by a second person, then sent; REPLIED is recorded only when the provider returns the reply id.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.crm import SocialChannel, SocialItem, SocialPost
from app.models.m49_social import SocialOptOut, SocialWebhookEvent
from app.services import social_flows as fl
from app.services import social_formats as sf
from app.services import social_service as ss

SocialError = ss.SocialError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def author_hash(network: str, author: Optional[str]) -> str:
    return hashlib.sha256(f"{network}:{(author or '').strip().lower()}".encode()).hexdigest()


def retention_days() -> int:
    return int(sf.cfg("SOCIAL_ITEM_RETENTION_DAYS", 365))


async def is_opted_out(db: AsyncSession, network: str, author: Optional[str]) -> bool:
    if not author:
        return False
    return (await db.execute(select(SocialOptOut.id).where(SocialOptOut.network == network,
                                                           SocialOptOut.author_hash == author_hash(network, author)))).first() is not None


def _blank(i: SocialItem, status: str = "DELETED") -> None:
    i.text, i.author, i.evidence, i.status, i.reply_draft, i.url = None, None, {}, status, None, None


async def opt_out(db: AsyncSession, network: str, author: str, reason: Optional[str], user: str) -> int:
    """The author asked not to be stored: remember only a hash, erase what we hold, drop future items."""
    await db.execute(insert(SocialOptOut).values(network=network, author_hash=author_hash(network, author), reason=(reason or "")[:200] or None,
                                                 created_by=user).on_conflict_do_nothing(constraint="uq_m49_social_optout"))
    n = 0
    for i in (await db.execute(select(SocialItem).where(SocialItem.network == network))).scalars():
        if i.author and i.author.strip().lower() == author.strip().lower():
            _blank(i)
            n += 1
    return n


async def retention_sweep(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Items past their retention date lose their personal content (the row stays so a replay is not re-ingested)."""
    now = now or _now()
    rows = (await db.execute(select(SocialItem).where(SocialItem.retention_until < now, SocialItem.status != "DELETED")
                             .limit(500).with_for_update(skip_locked=True))).scalars().all()
    for i in rows:
        _blank(i)
    if rows:
        await db.commit()
    return len(rows)


async def first_delivery(db: AsyncSession, source: str, raw: bytes) -> bool:
    """Webhook replay ledger: True the first time this exact body is seen."""
    res = await db.execute(insert(SocialWebhookEvent).values(source=source, event_hash=hashlib.sha256(raw).hexdigest())
                           .on_conflict_do_nothing(constraint="uq_m49_social_webhook_event"))
    return bool(res.rowcount)


# ── polling (LinkedIn, YouTube, X, Facebook, Instagram) ─────────────────

def _ms(v) -> Optional[datetime]:
    return datetime.fromtimestamp(int(v) / 1000, timezone.utc) if str(v or "").isdigit() else None


def _iso(v) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


async def _own_posts(db, ch) -> list[SocialPost]:
    return list((await db.execute(select(SocialPost).where(SocialPost.channel_id == ch.id, SocialPost.status == "PUBLISHED",
                                                           SocialPost.external_post_id.isnot(None)).order_by(SocialPost.published_at.desc()).limit(25))).scalars())


async def poll_channel(db: AsyncSession, ch: SocialChannel) -> dict:
    """Read new comments/mentions for one opted-in channel. Returns counts; TikTok and unsupported networks say why not."""
    if not ch.listen_enabled:
        return {"stored": 0, "reason": "Listening is not enabled for this channel (opt-in)."}
    ok, why, _ = sf.MODERATION[ch.network]["read"]
    if not ok:
        return {"stored": 0, "reason": why}
    if ss.publish_route(ch.network) != "API":
        return {"stored": 0, "reason": f"The {ch.network} token or SOCIAL_PUBLISHING_ENABLED is not set."}
    stored = 0
    opts = dict(ch.options or {})
    if ch.network == "x":
        cur = (opts.get("cursors") or {}).get("mentions")
        params = {"max_results": 50, "tweet.fields": "created_at,author_id", "expansions": "author_id", "user.fields": "username",
                  **({"since_id": cur} if cur else {})}
        d = await ss._read(lambda c: fl._x_get(c, f"users/{ch.external_id}/mentions", params))
        users = {u["id"]: u.get("username") for u in (d.get("includes") or {}).get("users", [])}
        for t in d.get("data", []):
            stored += await ss._store(db, ch, "x", "MENTION", t["id"], author=users.get(t.get("author_id")) or t.get("author_id"),
                                      text=t.get("text"), at=_iso(t.get("created_at")), source="POLL")
        if (d.get("meta") or {}).get("newest_id"):
            opts["cursors"] = {**(opts.get("cursors") or {}), "mentions": d["meta"]["newest_id"]}
    else:
        for p in await _own_posts(db, ch):
            pid = p.external_post_id
            if ch.network == "linkedin":
                d = await ss._read(lambda c: fl._get(c, fl._li(f"socialActions/{quote(pid, safe='')}/comments"), None, fl._li_h(), "linkedin"))
                for e in d.get("elements", []):
                    stored += await ss._store(db, ch, "linkedin", "COMMENT", e.get("commentUrn") or str(e.get("id")), parent=pid,
                                              author=e.get("actor"), text=(e.get("message") or {}).get("text"), at=_ms((e.get("created") or {}).get("time")), source="POLL")
            elif ch.network == "youtube":
                d = await ss._read(lambda c: fl._yt_get(c, "commentThreads", {"part": "snippet", "videoId": pid, "maxResults": 50}))
                for e in d.get("items", []):
                    sn = (e.get("snippet") or {}).get("topLevelComment", {}).get("snippet", {})
                    stored += await ss._store(db, ch, "youtube", "COMMENT", e["snippet"]["topLevelComment"]["id"], parent=pid,
                                              author=sn.get("authorDisplayName"), text=sn.get("textOriginal") or sn.get("textDisplay"), at=_iso(sn.get("publishedAt")), source="POLL")
            elif ch.network in ("facebook", "instagram"):
                f = "id,message,from,created_time" if ch.network == "facebook" else "id,text,username,timestamp"
                d = await ss._read(lambda c: fl._get(c, ss._graph(f"{pid}/comments"), {"fields": f}, ss._meta_h(), ch.network))
                for e in d.get("data", []):
                    stored += await ss._store(db, ch, ch.network, "COMMENT", e["id"], parent=pid, author=(e.get("from") or {}).get("name") or e.get("username"),
                                              text=e.get("message") or e.get("text"), at=_iso(e.get("created_time") or e.get("timestamp")), source="POLL")
    opts["last_polled_at"] = _now().isoformat()
    ch.options = opts
    return {"stored": stored}


async def poll_due(db: AsyncSession) -> int:
    """Worker tick: poll opted-in channels not polled for SOCIAL_LISTEN_POLL_MINUTES."""
    gap = timedelta(minutes=int(sf.cfg("SOCIAL_LISTEN_POLL_MINUTES", 15)))
    n = 0
    for ch in (await db.execute(select(SocialChannel).where(SocialChannel.listen_enabled.is_(True)))).scalars().all():
        last = _iso((ch.options or {}).get("last_polled_at") or "")
        if last and _now() - last < gap:
            continue
        try:
            await poll_channel(db, ch)
            n += 1
        except (SocialError, httpx.HTTPError, EgressBlocked):
            pass
        await db.commit()
    return n


# ── reply (draft -> second person approves -> send) ─────────────────────

def _check(network: str, op: str) -> None:
    ok, why, _ = sf.MODERATION[network][op]
    if not ok:
        raise SocialError(f"{network} does not allow this: {why}", "unsupported")


async def _send_reply(db, item: SocialItem, ch: Optional[SocialChannel], text: str) -> str:
    n, ext, parent = item.network, item.external_id, item.parent_id
    async with provider_client() as c:
        if n == "facebook":
            return ss._ok(await c.post(ss._graph(f"{ext}/comments"), data={"message": text}, headers=ss._meta_h()), n)["id"]
        if n == "instagram":
            return ss._ok(await c.post(ss._graph(f"{ext}/replies"), data={"message": text}, headers=ss._meta_h()), n)["id"]
        if n == "linkedin":
            r = await c.post(fl._li(f"socialActions/{quote(parent or '', safe='')}/comments"), headers=fl._li_h(), json={
                "actor": f"urn:li:organization:{ch.external_id}", "object": parent, "message": {"text": text}, "parentComment": ext})
            if r.status_code >= 400:
                ss._ok(r, n)
            return r.headers.get("x-restli-id") or str((r.json() if r.content else {}).get("id") or "")
        if n == "youtube":
            return fl._yt_ok(await c.post(fl._yt("comments"), params={"part": "snippet"}, headers=fl._yt_h(),
                                          json={"snippet": {"parentId": ext, "textOriginal": text}}))["id"]
        if n == "x":
            if item.kind != "MENTION":
                raise SocialError("x: on self-serve tiers a reply is allowed only to a post that mentioned our account.", "reply_not_permitted")
            return fl.x_ok(await c.post(fl._x("tweets"), json={"text": text, "reply": {"in_reply_to_tweet_id": ext}}, headers=fl._x_h()))["data"]["id"]
    raise SocialError(f"{n}: replies are not available", "unsupported")


async def send_reply(db: AsyncSession, item: SocialItem) -> SocialItem:
    """Send the approved reply. Claim first; REPLIED only with the provider's reply id; a lost answer is UNKNOWN, never resent."""
    _check(item.network, "reply")
    if item.reply_status != "APPROVED" or not item.reply_draft:
        raise SocialError("The reply must be approved by a second person first.", "not_approved")
    if ss.publish_route(item.network) != "API":
        raise SocialError(f"Sending needs SOCIAL_PUBLISHING_ENABLED and the {item.network} token.", "not_enabled")
    ch = await db.get(SocialChannel, item.channel_id) if item.channel_id else None
    item.reply_status, item.reply_error = "SENDING", None
    await db.commit()
    try:
        rid = await _send_reply(db, item, ch, item.reply_draft)
        item.reply_status, item.reply_external_id, item.status = "SENT", rid or None, "REPLIED"
        if not rid:
            item.reply_error = "The provider accepted the reply but gave no reply id."
    except (SocialError, EgressBlocked) as e:
        item.reply_error = str(e)[:500]
        item.reply_status = "UNKNOWN" if getattr(e, "retryable", False) else "FAILED"
    except httpx.HTTPError as e:
        item.reply_status, item.reply_error = "UNKNOWN", f"No answer ({type(e).__name__}); check the network before sending again."
    await db.commit()
    return item


# ── hide / delete ───────────────────────────────────────────────────────

async def moderate(db: AsyncSession, item: SocialItem, op: str) -> SocialItem:
    """hide or delete on the network where its API allows; local state changes only after the provider confirms."""
    _check(item.network, op)
    if ss.publish_route(item.network) != "API":
        raise SocialError(f"Moderation needs SOCIAL_PUBLISHING_ENABLED and the {item.network} token.", "not_enabled")
    n, ext, parent = item.network, item.external_id, item.parent_id
    ch = await db.get(SocialChannel, item.channel_id) if item.channel_id else None
    async with provider_client() as c:
        if n in ("facebook", "instagram"):
            if op == "hide":
                ss._ok(await c.post(ss._graph(ext), data={"is_hidden": "true"} if n == "facebook" else {"hide": "true"}, headers=ss._meta_h()), n)
            else:
                ss._ok(await c.delete(ss._graph(ext), headers=ss._meta_h()), n)
        elif n == "youtube":
            if op == "hide":
                r = await c.post(fl._yt("comments/setModerationStatus"), params={"id": ext, "moderationStatus": "rejected"}, headers=fl._yt_h())
            else:
                r = await c.delete(fl._yt("comments"), params={"id": ext}, headers=fl._yt_h())
            if r.status_code not in (200, 204):
                fl._yt_ok(r)
        elif n == "x":
            fl.x_ok(await c.put(fl._x(f"tweets/{ext}/hidden"), json={"hidden": True}, headers=fl._x_h()))
        elif n == "linkedin" and op == "delete":
            r = await c.delete(fl._li(f"socialActions/{quote(parent or '', safe='')}/comments/{quote(ext, safe='')}"),
                               params={"actor": f"urn:li:organization:{ch.external_id}"}, headers=fl._li_h())
            if r.status_code not in (200, 204):
                ss._ok(r, n)
    if op == "hide":
        item.provider_state, item.status = "HIDDEN", "HIDDEN"
    else:
        item.provider_state = "DELETED"
        _blank(item)
    return item
