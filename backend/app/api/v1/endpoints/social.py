"""Social publishing, calendar and listening (M44.S01.T006–T008). Prefix /api/v1/social."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import SocialChannel, SocialItem, SocialPost
from app.services import social_service as ss

READ = ("marketing.view", "marketing.edit", "social_media.view", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "social_media.edit", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
EDITABLE = ("DRAFT", "PENDING", "APPROVED", "FAILED")


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _tz(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, f"Unknown time zone {name!r}") from None
    return name


class ChannelIn(BaseModel):
    network: Literal["facebook", "instagram", "linkedin", "tiktok", "x", "youtube"]
    external_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=200)
    time_zone: str = Field("Africa/Nairobi", max_length=64)
    listen_enabled: bool = False


def _ch(c: SocialChannel) -> dict:
    return {"id": str(c.id), "network": c.network, "external_id": c.external_id, "name": c.name, "time_zone": c.time_zone,
            "listen_enabled": c.listen_enabled, "publishing": ss.publish_route(c.network)}


@router.get("/channels")
async def channels(db: AsyncSession = Depends(get_db)):
    return [_ch(c) for c in (await db.execute(select(SocialChannel).order_by(SocialChannel.network, SocialChannel.name))).scalars()]


@router.post("/channels", status_code=201)
async def add_channel(body: ChannelIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    c = SocialChannel(**{**body.model_dump(), "time_zone": _tz(body.time_zone)})
    db.add(c)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(409, "This channel is already added.") from None
    return _ch(c)


@router.patch("/channels/{cid}/listening")
async def set_listening(cid: uuid.UUID, enabled: bool, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    c = await db.get(SocialChannel, cid)
    if c is None:
        raise HTTPException(404, "Channel not found")
    c.listen_enabled = enabled
    await db.commit()
    return _ch(c)


class Media(BaseModel):
    url: str = Field(max_length=1000)
    kind: Literal["image", "video"]


class PostIn(BaseModel):
    channel_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    text: str = Field(min_length=1, max_length=63206)
    media: list[Media] = Field(default_factory=list, max_length=10)
    link: Optional[str] = Field(None, max_length=500, pattern=r"^https?://\S+$")
    campaign_tag: Optional[str] = Field(None, max_length=100)
    scheduled_at: Optional[datetime] = None
    time_zone: str = Field("Africa/Nairobi", max_length=64)


async def _out(db, p: SocialPost) -> dict:
    ch = await db.get(SocialChannel, p.channel_id)
    return {"id": str(p.id), "channel_id": str(p.channel_id), "network": ch.network, "channel": ch.name, "text": p.text,
            "media": p.media, "link": p.link, "campaign_tag": p.campaign_tag,
            "owner_id": str(p.owner_id) if p.owner_id else None,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None, "time_zone": p.time_zone,
            "status": p.status, "version": p.version, "approved": p.approved_version == p.version,
            "approved_by": p.approved_by, "external_post_id": p.external_post_id, "error": p.error,
            "published_at": p.published_at.isoformat() if p.published_at else None, "history": p.history,
            "created_by": p.created_by, "route": ss.publish_route(ch.network),
            "problems": ss.problems(ch.network, p.text, p.media or [], p.link), "conflicts": await ss.conflicts(db, p)}


def _when(body: PostIn) -> Optional[datetime]:
    """A naive time is local time in the post's time zone; stored in UTC."""
    if body.scheduled_at is None:
        return None
    at = body.scheduled_at
    if at.tzinfo is None:
        at = at.replace(tzinfo=ZoneInfo(_tz(body.time_zone)))
    return at.astimezone(timezone.utc)


async def _post(db, pid: uuid.UUID) -> SocialPost:
    p = await db.get(SocialPost, pid)
    if p is None:
        raise HTTPException(404, "Post not found")
    return p


@router.get("/posts")
async def posts(start: Optional[datetime] = None, end: Optional[datetime] = None, campaign_tag: Optional[str] = None,
                db: AsyncSession = Depends(get_db)):
    """Calendar: posts in a window (plus unscheduled drafts when no window is given)."""
    q = select(SocialPost).order_by(SocialPost.scheduled_at.asc().nullsfirst())
    if start and end:
        q = q.where(SocialPost.scheduled_at.between(start, end))
    if campaign_tag:
        q = q.where(SocialPost.campaign_tag == campaign_tag)
    return [await _out(db, p) for p in (await db.execute(q.limit(500))).scalars()]


@router.post("/posts", status_code=201)
async def create_post(body: PostIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    old = (await db.execute(select(SocialPost).where(SocialPost.idempotency_key == body.idempotency_key))).scalar_one_or_none()
    if old:
        return await _out(db, old)
    if await db.get(SocialChannel, body.channel_id) is None:
        raise HTTPException(404, "Channel not found")
    p = SocialPost(channel_id=body.channel_id, idempotency_key=body.idempotency_key, text=body.text,
                   media=[m.model_dump() for m in body.media], link=body.link, campaign_tag=body.campaign_tag,
                   scheduled_at=_when(body), time_zone=_tz(body.time_zone), owner_id=current_user.id,
                   created_by=current_user.username, history=[])
    ss.log(p, "CREATED")
    db.add(p)
    await db.commit()
    return await _out(db, p)


@router.put("/posts/{pid}")
async def edit_post(pid: uuid.UUID, body: PostIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Content change → new version, approval needed again. A time-only change (reschedule) keeps the approval."""
    _w(current_user)
    p = await _post(db, pid)
    if p.status not in EDITABLE:
        raise HTTPException(409, f"A {p.status.lower()} post cannot be changed.")
    content = (body.text, [m.model_dump() for m in body.media], body.link)
    if content != (p.text, p.media, p.link) or body.channel_id != p.channel_id:
        p.text, p.media, p.link, p.channel_id = *content, body.channel_id
        p.version += 1
        p.status, p.approved_by = "DRAFT", None
        ss.log(p, "EDITED", "content changed: approval needed again")
    p.campaign_tag, p.time_zone = body.campaign_tag, _tz(body.time_zone)
    new_at = _when(body)
    if new_at != p.scheduled_at:
        p.scheduled_at = new_at
        ss.log(p, "RESCHEDULED", new_at.isoformat() if new_at else "unscheduled")
    if p.status == "FAILED" and p.approved_version == p.version and not p.external_post_id:
        p.status = "APPROVED"
    await db.commit()
    return await _out(db, p)


@router.post("/posts/{pid}/{action}")
async def post_action(pid: uuid.UUID, action: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    p = await _post(db, pid)
    if action == "request":
        if p.status != "DRAFT":
            raise HTTPException(409, "Only a draft can be sent for approval.")
        p.status = "PENDING"
        ss.log(p, "APPROVAL_REQUESTED", current_user.username)
    elif action in ("approve", "reject"):
        if p.status != "PENDING":
            raise HTTPException(409, "Nothing waiting for approval.")
        asked = next((h["detail"] for h in reversed(p.history or []) if h["event"] == "APPROVAL_REQUESTED"), None)
        if current_user.username in (p.created_by, asked):
            raise HTTPException(403, "A second editor must approve.")
        if action == "approve":
            p.status, p.approved_version, p.approved_by = "APPROVED", p.version, current_user.username
        else:
            p.status = "DRAFT"
        ss.log(p, "APPROVED" if action == "approve" else "REJECTED", current_user.username)
    elif action == "cancel":
        if p.status in ("PUBLISHED", "PUBLISHING"):
            raise HTTPException(409, "Already published; delete it on the network itself.")
        p.status = "CANCELLED"
        ss.log(p, "CANCELLED", current_user.username)
    elif action == "retry":
        if p.status != "FAILED" or p.approved_version != p.version or p.external_post_id:
            raise HTTPException(409, "Only a failed, approved post can be retried.")
        p.status = "APPROVED"
        ss.log(p, "RETRY", current_user.username)
    elif action == "export":
        ch = await db.get(SocialChannel, p.channel_id)
        if p.approved_version != p.version:
            raise HTTPException(409, "Approve the current version before exporting it.")
        p.status = "EXPORTED"
        ss.log(p, "EXPORTED", current_user.username)
        await db.commit()
        return {"network": ch.network, "channel": ch.name, "text": p.text + (f"\n{p.link}" if p.link and ch.network != "facebook" else ""),
                "link": p.link, "media": p.media, "scheduled_local": p.scheduled_at.astimezone(ZoneInfo(p.time_zone)).isoformat() if p.scheduled_at else None,
                "note": "Post this manually on the network, then paste the post link into the post's history if you want it tracked."}
    else:
        raise HTTPException(404, "Unknown action")
    await db.commit()
    return await _out(db, p)


# ── listening ──────────────────────────────────────────────────────────

def _item(i: SocialItem) -> dict:
    return {"id": str(i.id), "network": i.network, "kind": i.kind, "author": i.author, "text": i.text, "url": i.url,
            "occurred_at": i.occurred_at.isoformat(), "source": i.source, "sentiment": i.sentiment, "topics": i.topics,
            "evidence": i.evidence, "status": i.status, "assigned_to": i.assigned_to, "reply_draft": i.reply_draft}


@router.get("/inbox")
async def inbox(status: Optional[str] = Query(None, max_length=9), sentiment: Optional[str] = Query(None, max_length=8),
                db: AsyncSession = Depends(get_db)):
    q = select(SocialItem).order_by(SocialItem.occurred_at.desc()).limit(300)
    if status:
        q = q.where(SocialItem.status == status.upper())
    if sentiment:
        q = q.where(SocialItem.sentiment == sentiment.upper())
    return {"items": [_item(i) for i in (await db.execute(q)).scalars()],
            "note": "Only opted-in channels and imported items — not platform-wide listening. Tags come from keywords; check the evidence."}


class ImportIn(BaseModel):
    csv: str = Field(min_length=1, max_length=2_000_000)


@router.post("/inbox/import")
async def import_items(body: ImportIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    res = await ss.import_csv(db, body.csv)
    await db.commit()
    return res


class ItemPatch(BaseModel):
    status: Optional[Literal["NEW", "ASSIGNED", "REPLIED", "HIDDEN", "DONE"]] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    reply_draft: Optional[str] = Field(None, max_length=8000)


@router.patch("/inbox/{iid}")
async def update_item(iid: uuid.UUID, body: ItemPatch, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    i = await db.get(SocialItem, iid)
    if i is None:
        raise HTTPException(404, "Item not found")
    if i.status == "DELETED":
        raise HTTPException(409, "The author deleted this item.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(i, k, v)
    await db.commit()
    return _item(i)


@router.post("/inbox/{iid}/suggest-reply")
async def suggest(iid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    i = await db.get(SocialItem, iid)
    if i is None:
        raise HTTPException(404, "Item not found")
    return {"reply_draft": ss.suggest_reply(i), "note": "A draft for you to edit. Replies are posted by a person on the network."}
