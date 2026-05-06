"""
Team Messaging / Channel Chat API
───────────────────────────────────
Prefix: /api/v1/messaging

Routes:
  GET  /channels/           – channels user belongs to
  POST /channels/           – create team channel
  POST /channels/dm         – get or create DM with a user
  POST /channels/{id}/join  – join a channel
  GET  /channels/{id}/messages  – paginated messages (poll for "real-time")
  POST /channels/{id}/messages  – post message
  GET  /channels/{id}/messages/{msg_id}/thread – thread replies
  PATCH /messages/{msg_id}  – edit message
  DELETE /messages/{msg_id} – soft-delete message
  GET  /search              – full-text search across messages
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.messaging import (
    ChannelType, MemberRole,
    ChatChannel, ChannelMember, ChannelMessage,
)
from app.models.user import User
from app.schemas.messaging import (
    ChannelCreate, ChannelRead,
    MessageCreate, MessageRead, MessagePage,
    DMCreate,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _build_msg(m: ChannelMessage, reply_count: int = 0) -> MessageRead:
    r = MessageRead.model_validate(m)
    if m.sender:
        r.sender_name = m.sender.full_name or m.sender.username
        initials = "".join(p[0].upper() for p in (m.sender.full_name or m.sender.username).split()[:2])
        r.sender_initials = initials or "?"
    r.reply_count = reply_count
    return r


async def _ensure_member(db: AsyncSession, channel_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    q = select(ChannelMember).where(
        ChannelMember.channel_id == channel_id,
        ChannelMember.user_id == user_id,
    )
    return (await db.execute(q)).scalar_one_or_none() is not None


async def _notify_mentions(db: AsyncSession, message: ChannelMessage, channel: ChatChannel) -> None:
    if not message.mentions:
        return
    from app.models.notifications import Notification, NotificationType, NotificationPriority, NotificationChannel, NotificationStatus
    for uid_str in message.mentions:
        try:
            uid = uuid.UUID(uid_str)
        except ValueError:
            continue
        notif = Notification(
            user_id=uid_str,
            user_name="",
            title=f"@mention in #{channel.name}",
            message=message.body[:200],
            notification_type=NotificationType.NOTIFICATION_EVENT,
            priority=NotificationPriority.NORMAL,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.PENDING,
            reference_type="channel_message",
            reference_id=str(message.id),
            module="messaging",
        )
        db.add(notif)


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels/", response_model=List[ChannelRead])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return channels the current user is a member of."""
    member_q = select(ChannelMember.channel_id).where(
        ChannelMember.user_id == current_user.id
    )
    channel_ids = list((await db.execute(member_q)).scalars().all())

    if not channel_ids:
        return []

    q = (
        select(ChatChannel)
        .options(selectinload(ChatChannel.members))
        .where(ChatChannel.id.in_(channel_ids), ChatChannel.is_archived.is_(False))
        .order_by(ChatChannel.name)
    )
    channels = list((await db.execute(q)).scalars().all())

    result = []
    for ch in channels:
        row = ChannelRead.model_validate(ch)
        row.member_count = len(ch.members)
        # Unread count: messages after last_read_at
        member = next((m for m in ch.members if m.user_id == current_user.id), None)
        if member and member.last_read_at:
            unread_q = select(func.count(ChannelMessage.id)).where(
                ChannelMessage.channel_id == ch.id,
                ChannelMessage.created_at > member.last_read_at,
                ChannelMessage.is_deleted.is_(False),
            )
            row.unread_count = (await db.execute(unread_q)).scalar() or 0
        result.append(row)
    return result


@router.post("/channels/", response_model=ChannelRead, status_code=201)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_slug = _slug(body.name)
    slug = base_slug
    # ensure slug unique
    existing = (await db.execute(select(ChatChannel).where(ChatChannel.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"

    channel = ChatChannel(
        name=body.name,
        slug=slug,
        channel_type=ChannelType.TEAM,
        description=body.description,
        module_context=body.module_context,
        created_by_id=current_user.id,
    )
    db.add(channel)
    await db.flush()

    # Add creator as admin
    member_ids = set(body.member_ids) | {current_user.id}
    for uid in member_ids:
        role = MemberRole.ADMIN if uid == current_user.id else MemberRole.MEMBER
        db.add(ChannelMember(channel_id=channel.id, user_id=uid, role=role,
                             joined_at=datetime.now(tz=timezone.utc)))

    await db.commit()
    await db.refresh(channel)
    row = ChannelRead.model_validate(channel)
    row.member_count = len(member_ids)
    return row


@router.post("/channels/dm", response_model=ChannelRead, status_code=201)
async def get_or_create_dm(
    body: DMCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get existing DM channel with a user, or create one."""
    # Find DM channel where both users are members
    my_channels_q = select(ChannelMember.channel_id).where(ChannelMember.user_id == current_user.id)
    their_channels_q = select(ChannelMember.channel_id).where(ChannelMember.user_id == body.target_user_id)

    dm_q = select(ChatChannel).where(
        ChatChannel.channel_type == ChannelType.DIRECT,
        ChatChannel.id.in_(select(ChannelMember.channel_id).where(ChannelMember.user_id == current_user.id)),
        ChatChannel.id.in_(select(ChannelMember.channel_id).where(ChannelMember.user_id == body.target_user_id)),
    )
    existing_dm = (await db.execute(dm_q)).scalar_one_or_none()
    if existing_dm:
        row = ChannelRead.model_validate(existing_dm)
        row.member_count = 2
        return row

    target = await db.get(User, body.target_user_id)
    if not target:
        raise HTTPException(404, "User not found")

    slug = f"dm-{min(str(current_user.id), str(body.target_user_id))[:8]}-{max(str(current_user.id), str(body.target_user_id))[:8]}"
    channel = ChatChannel(
        name=f"DM: {current_user.full_name or current_user.username} & {target.full_name or target.username}",
        slug=slug,
        channel_type=ChannelType.DIRECT,
        created_by_id=current_user.id,
    )
    db.add(channel)
    await db.flush()
    for uid in [current_user.id, body.target_user_id]:
        db.add(ChannelMember(channel_id=channel.id, user_id=uid, role=MemberRole.MEMBER,
                             joined_at=datetime.now(tz=timezone.utc)))
    await db.commit()
    await db.refresh(channel)
    row = ChannelRead.model_validate(channel)
    row.member_count = 2
    return row


@router.post("/channels/{channel_id}/join", response_model=ChannelRead)
async def join_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = await db.get(ChatChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")
    if channel.channel_type == ChannelType.DIRECT:
        raise HTTPException(422, "Cannot join a DM channel")

    already = await _ensure_member(db, channel_id, current_user.id)
    if not already:
        db.add(ChannelMember(channel_id=channel_id, user_id=current_user.id,
                             role=MemberRole.MEMBER, joined_at=datetime.now(tz=timezone.utc)))
        await db.commit()
        await db.refresh(channel)

    row = ChannelRead.model_validate(channel)
    return row


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/channels/{channel_id}/messages", response_model=MessagePage)
async def get_messages(
    channel_id: uuid.UUID,
    before: Optional[datetime] = None,
    since: Optional[datetime] = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await _ensure_member(db, channel_id, current_user.id):
        raise HTTPException(403, "Not a member of this channel")

    q = (
        select(ChannelMessage)
        .options(selectinload(ChannelMessage.sender))
        .where(
            ChannelMessage.channel_id == channel_id,
            ChannelMessage.parent_id.is_(None),
            ChannelMessage.is_deleted.is_(False),
        )
    )
    if before:
        q = q.where(ChannelMessage.created_at < before)
    if since:
        q = q.where(ChannelMessage.created_at > since)

    q = q.order_by(ChannelMessage.created_at.desc()).limit(limit + 1)
    rows = list((await db.execute(q)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    # Get reply counts
    msg_ids = [m.id for m in rows]
    reply_counts: dict[uuid.UUID, int] = {}
    if msg_ids:
        rc_q = (
            select(ChannelMessage.parent_id, func.count(ChannelMessage.id).label("cnt"))
            .where(ChannelMessage.parent_id.in_(msg_ids), ChannelMessage.is_deleted.is_(False))
            .group_by(ChannelMessage.parent_id)
        )
        for parent_id, cnt in (await db.execute(rc_q)).all():
            reply_counts[parent_id] = cnt

    messages = [_build_msg(m, reply_counts.get(m.id, 0)) for m in reversed(rows)]

    # Mark as read
    member = (await db.execute(
        select(ChannelMember).where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if member:
        member.last_read_at = datetime.now(tz=timezone.utc)
        await db.commit()

    return MessagePage(
        messages=messages,
        has_more=has_more,
        oldest_at=messages[0].created_at if messages else None,
    )


@router.post("/channels/{channel_id}/messages", response_model=MessageRead, status_code=201)
async def post_message(
    channel_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await _ensure_member(db, channel_id, current_user.id):
        raise HTTPException(403, "Not a member of this channel")

    channel = await db.get(ChatChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")

    msg = ChannelMessage(
        channel_id=channel_id,
        sender_id=current_user.id,
        body=body.body,
        parent_id=body.parent_id,
        link_module=body.link_module,
        link_type=body.link_type,
        link_id=body.link_id,
        link_ref=body.link_ref,
        mentions=body.mentions or [],
    )
    db.add(msg)
    await db.flush()
    await _notify_mentions(db, msg, channel)
    await db.commit()

    result = await db.execute(
        select(ChannelMessage).options(selectinload(ChannelMessage.sender)).where(ChannelMessage.id == msg.id)
    )
    return _build_msg(result.scalar_one())


@router.get("/channels/{channel_id}/messages/{msg_id}/thread", response_model=List[MessageRead])
async def get_thread(
    channel_id: uuid.UUID,
    msg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await _ensure_member(db, channel_id, current_user.id):
        raise HTTPException(403, "Not a member")

    q = (
        select(ChannelMessage)
        .options(selectinload(ChannelMessage.sender))
        .where(
            ChannelMessage.parent_id == msg_id,
            ChannelMessage.is_deleted.is_(False),
        )
        .order_by(ChannelMessage.created_at.asc())
    )
    replies = list((await db.execute(q)).scalars().all())
    return [_build_msg(r) for r in replies]


@router.patch("/messages/{msg_id}", response_model=MessageRead)
async def edit_message(
    msg_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelMessage).options(selectinload(ChannelMessage.sender)).where(ChannelMessage.id == msg_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(403, "Cannot edit another user's message")

    msg.body = body.body
    msg.is_edited = True
    msg.edited_at = datetime.now(tz=timezone.utc)
    msg.mentions = body.mentions or []
    await db.commit()
    await db.refresh(msg)
    return _build_msg(msg)


@router.delete("/messages/{msg_id}", status_code=204)
async def delete_message(
    msg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = await db.get(ChannelMessage, msg_id)
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(403, "Cannot delete another user's message")
    msg.is_deleted = True
    msg.body = "[deleted]"
    await db.commit()


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=List[MessageRead])
async def search_messages(
    q: str = Query(..., min_length=2),
    channel_id: Optional[uuid.UUID] = None,
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Restrict to channels the user belongs to
    member_channels = list((await db.execute(
        select(ChannelMember.channel_id).where(ChannelMember.user_id == current_user.id)
    )).scalars().all())

    sq = (
        select(ChannelMessage)
        .options(selectinload(ChannelMessage.sender))
        .where(
            ChannelMessage.channel_id.in_(member_channels),
            ChannelMessage.is_deleted.is_(False),
            ChannelMessage.body.ilike(f"%{q}%"),
        )
    )
    if channel_id:
        sq = sq.where(ChannelMessage.channel_id == channel_id)

    sq = sq.order_by(ChannelMessage.created_at.desc()).limit(limit)
    msgs = list((await db.execute(sq)).scalars().all())
    return [_build_msg(m) for m in msgs]
