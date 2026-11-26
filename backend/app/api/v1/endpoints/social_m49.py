"""M49.S01.T007-T010 routes mounted under /api/v1/social by social.py: capability matrix, insights, polling, moderation.

RBAC is inherited from the parent router (READ); every mutation needs a marketing editor and writes an audit log row."""
from __future__ import annotations

import uuid
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.models.audit_log import AuditLog
from app.models.crm import SocialChannel, SocialItem, SocialPost
from app.models.m49_social import SocialPostMetric
from app.services import social_flows as fl
from app.services import social_formats as sf
from app.services import social_listening as sl
from app.services import social_service as ss

WRITE = ("marketing.edit", "social_media.edit", "crm.edit_all")
router = APIRouter()


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _audit(db, u, event: str, target: str, tid, details: dict) -> None:
    db.add(AuditLog(actor_id=getattr(u, "id", None), actor_email=getattr(u, "email", None), actor_name=getattr(u, "full_name", None),
                    event_type=f"SOCIAL_{event.upper()}", module="marketing", target_type=target, target_id=str(tid), details=details))


async def _item(db, iid: uuid.UUID, lock: bool = True) -> SocialItem:
    i = await db.get(SocialItem, iid, with_for_update=lock)
    if i is None:
        raise HTTPException(404, "Item not found")
    if i.status == "DELETED":
        raise HTTPException(409, "This item was deleted (by the author, the network, retention or opt-out).")
    return i


def _view(i: SocialItem) -> dict:
    from app.api.v1.endpoints.social import _item as v
    return v(i)


# ── capabilities ───────────────────────────────────────────────────────

@router.get("/capabilities")
async def capabilities(channel_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    """What each network's API allows, with the exact reason for everything disabled. A channel adds its own access tier."""
    ch = await db.get(SocialChannel, channel_id) if channel_id else None
    opts = {c.network: c.options for c in (await db.execute(select(SocialChannel))).scalars()} if ch is None else {ch.network: ch.options}
    nets = [ch.network] if ch else list(sf.NETWORKS)
    return {"networks": {n: {**sf.capabilities(n, opts.get(n)), "publishing": ss.publish_route(n), "mode": ss.publish_mode()} for n in nets},
            "source": "coordination/milestones/M48/CAPABILITY_MATRIX.md (checked 2026-11-26)"}


class ChannelOptions(BaseModel):
    x_tier: Optional[Literal["pay_per_use", "basic", "pro", "enterprise"]] = None
    ig_login: Optional[Literal["instagram", "facebook"]] = None
    app_id: Optional[str] = Field(None, max_length=64, pattern=r"^[0-9]+$")
    youtube_project_verified: Optional[bool] = None


@router.patch("/channels/{cid}/options")
async def set_options(cid: uuid.UUID, body: ChannelOptions, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    c = await db.get(SocialChannel, cid)
    if c is None:
        raise HTTPException(404, "Channel not found")
    c.options = {**(c.options or {}), **body.model_dump(exclude_none=True)}
    _audit(db, current_user, "channel_options", "social_channel", cid, body.model_dump(exclude_none=True))
    await db.commit()
    return {"id": str(c.id), "options": c.options}


# ── insights ───────────────────────────────────────────────────────────

@router.get("/posts/{pid}/insights")
async def insights(pid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    p = await db.get(SocialPost, pid)
    if p is None:
        raise HTTPException(404, "Post not found")
    rows = (await db.execute(select(SocialPostMetric).where(SocialPostMetric.post_id == pid).order_by(SocialPostMetric.metric))).scalars().all()
    ch = await db.get(SocialChannel, p.channel_id)
    return {"network": ch.network, "mode": p.publish_mode, "capability": sf.capabilities(ch.network)["insights"],
            "metrics": [{"metric": r.metric, "value": float(r.value), "source": r.source, "fetched_at": r.fetched_at.isoformat()} for r in rows],
            "note": "Values exactly as the network returned them; nothing is estimated."}


@router.post("/posts/{pid}/insights/refresh")
async def insights_refresh(pid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    p = await db.get(SocialPost, pid)
    if p is None:
        raise HTTPException(404, "Post not found")
    ch = await db.get(SocialChannel, p.channel_id)
    if p.status != "PUBLISHED" or not p.external_post_id:
        raise HTTPException(409, "Only a post confirmed as published (with a network post id) has metrics.")
    if ss.publish_route(ch.network) != "API":
        raise HTTPException(409, f"Reading metrics needs SOCIAL_PUBLISHING_ENABLED and the {ch.network} token.")
    try:
        n = await fl.store_insights(db, p, ch.network, await fl.fetch_insights(ch, p))
    except (ss.SocialError, EgressBlocked) as e:
        raise HTTPException(502, f"{ch.network} metrics unavailable: {e}") from None
    except httpx.HTTPError as e:
        raise HTTPException(504, f"No answer from {ch.network} ({type(e).__name__})") from None
    _audit(db, current_user, "insights_refresh", "social_post", pid, {"metrics": n})
    await db.commit()
    return await insights(pid, db)


# ── listening ──────────────────────────────────────────────────────────

@router.post("/channels/{cid}/poll")
async def poll(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Read new comments/mentions through the network's official API (opted-in channels only). No scraping."""
    _w(current_user)
    c = await db.get(SocialChannel, cid)
    if c is None:
        raise HTTPException(404, "Channel not found")
    try:
        res = await sl.poll_channel(db, c)
    except (ss.SocialError, EgressBlocked) as e:
        raise HTTPException(502, f"{c.network} polling failed: {e}") from None
    except httpx.HTTPError as e:
        raise HTTPException(504, f"No answer from {c.network} ({type(e).__name__})") from None
    _audit(db, current_user, "poll", "social_channel", cid, res)
    await db.commit()
    return res


@router.post("/inbox/{iid}/reply/{action}")
async def reply_action(iid: uuid.UUID, action: Literal["request", "approve", "reject", "send"], db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    """Draft -> approval requested -> approved by a second person -> sent. REPLIED only with the network's reply id."""
    _w(current_user)
    i = await _item(db, iid)
    try:
        sl._check(i.network, "reply")
    except ss.SocialError as e:
        raise HTTPException(409, str(e)) from None
    me = current_user.username
    if action == "request":
        if not (i.reply_draft or "").strip() or i.reply_status not in ("DRAFT", "FAILED", None):
            raise HTTPException(409, "Write a reply draft first (or the reply is already in review).")
        i.reply_status, i.reply_requested_by, i.reply_approved_by = "PENDING", me, None
    elif action in ("approve", "reject"):
        if i.reply_status != "PENDING":
            raise HTTPException(409, "No reply is waiting for approval.")
        if me == i.reply_requested_by:
            raise HTTPException(403, "A second person must approve the reply.")
        i.reply_status, i.reply_approved_by = ("APPROVED", me) if action == "approve" else ("DRAFT", None)
    else:
        try:
            await sl.send_reply(db, i)
        except ss.SocialError as e:
            raise HTTPException(409, str(e)) from None
        _audit(db, current_user, "reply_send", "social_item", iid, {"reply_status": i.reply_status, "reply_id": i.reply_external_id})
        await db.commit()
        return _view(i)
    _audit(db, current_user, f"reply_{action}", "social_item", iid, {"reply_status": i.reply_status})
    await db.commit()
    return _view(i)


class ModerateIn(BaseModel):
    confirm: bool
    reason: str = Field(min_length=3, max_length=200)


@router.post("/inbox/{iid}/moderate/{op}")
async def moderate(iid: uuid.UUID, op: Literal["hide", "delete"], body: ModerateIn, db: AsyncSession = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """Hide or delete on the network itself, only where its API allows. Local state changes only after the network confirms."""
    _w(current_user)
    if not body.confirm:
        raise HTTPException(422, "Confirm the action: deleting a comment on the network cannot be undone.")
    i = await _item(db, iid)
    net = i.network
    try:
        await sl.moderate(db, i, op)
    except ss.SocialError as e:
        raise HTTPException(409 if e.code in ("unsupported", "not_enabled") else 502, str(e)) from None
    except (EgressBlocked, httpx.HTTPError) as e:
        raise HTTPException(502, f"{net} did not confirm: {e or type(e).__name__}") from None
    _audit(db, current_user, f"comment_{op}", "social_item", iid, {"network": net, "reason": body.reason})
    await db.commit()
    return _view(i)


class OptOutIn(BaseModel):
    network: Literal["facebook", "instagram", "linkedin", "tiktok", "x", "youtube"]
    author: str = Field(min_length=1, max_length=200)
    reason: Optional[str] = Field(None, max_length=200)


@router.post("/inbox/optout")
async def optout(body: OptOutIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """An author asks not to be stored: existing items are erased, future ones dropped (only a hash of the handle is kept)."""
    _w(current_user)
    n = await sl.opt_out(db, body.network, body.author, body.reason, current_user.username)
    _audit(db, current_user, "optout", "social_author", sl.author_hash(body.network, body.author)[:16], {"network": body.network, "erased": n})
    await db.commit()
    return {"erased": n, "note": "Future items from this author on this network are not stored."}


@router.post("/inbox/retention-sweep")
async def retention(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    n = await sl.retention_sweep(db)
    _audit(db, current_user, "retention_sweep", "social_item", "all", {"erased": n, "retention_days": sl.retention_days()})
    await db.commit()
    return {"erased": n, "retention_days": sl.retention_days()}
