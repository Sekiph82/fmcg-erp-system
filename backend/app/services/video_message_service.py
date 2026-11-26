"""M47.S01.T009 1-to-1 video messages.

A rep uploads (or records in the browser) a short video. It is stored through cms_media_service.store as staff-only
media (not public, no access list: the CMS public media routes refuse it to everyone). One expiring, revocable link is
made for one contact; only the SHA-256 digest of its 256-bit token is stored and the link serves only its own video.
Each view is recorded once per viewer per 30 minutes (keyed hash, no IP stored) and shows on the customer timeline.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cms import CmsMedia
from app.models.m47_sales_depth import SalesVideoMessage, SalesVideoView


def _now() -> datetime:
    return datetime.now(timezone.utc)


def digest(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()


async def create(db: AsyncSession, upload, *, title: str, contact_email: str, contact_name: Optional[str], customer_id,
                 crm_record_id, days: int, user) -> tuple[SalesVideoMessage, str]:
    from app.services import cms_media_service as media
    key, mime, size, sha = await media.store(upload)
    if media.KINDS[mime] != "VIDEO":
        media.root().joinpath(key).unlink(missing_ok=True)
        raise HTTPException(422, "Upload a video (MP4 or WebM).")
    m = CmsMedia(kind="VIDEO", title=f"Video message: {title}"[:200], mime=mime, size=size, sha256=sha, storage_path=key,
                 captions={}, public=False, access_list_id=None, created_by=user.username)
    db.add(m)
    await db.flush()
    token = secrets.token_urlsafe(32)
    vm = SalesVideoMessage(media_id=m.id, title=title[:200], contact_email=contact_email.strip().lower()[:255],
                           contact_name=(contact_name or "").strip()[:200] or None, customer_id=customer_id,
                           crm_record_id=crm_record_id, token_hash=digest(token), expires_at=_now() + timedelta(days=days),
                           created_by_id=user.id)
    db.add(vm)
    await db.flush()
    return vm, token


def url(token: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/v/{token}"


async def resolve(db: AsyncSession, token: str) -> tuple[SalesVideoMessage, CmsMedia]:
    vm = (await db.execute(select(SalesVideoMessage).where(SalesVideoMessage.token_hash == digest(token)))).scalar_one_or_none()
    if vm is None:
        raise HTTPException(404, "This link does not exist.")
    if vm.revoked_at is not None or vm.expires_at <= _now():
        raise HTTPException(410, "This video link has expired or was withdrawn.")
    m = await db.get(CmsMedia, vm.media_id)
    if m is None:
        raise HTTPException(410, "This video is no longer available.")
    return vm, m


def viewer(vm: SalesVideoMessage, request) -> str:
    raw = f"video:{vm.id}:{request.client.host if request.client else ''}:{request.headers.get('user-agent', '')}"
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()


async def record_view(db: AsyncSession, vm: SalesVideoMessage, request, seconds: int) -> bool:
    vh = viewer(vm, request)
    secs = max(0, min(int(seconds or 0), 86400))
    recent = (await db.execute(select(SalesVideoView).where(SalesVideoView.video_id == vm.id, SalesVideoView.viewer_hash == vh,
                                                            SalesVideoView.at >= _now() - timedelta(minutes=30)))).scalars().first()
    if recent:
        recent.seconds = max(recent.seconds, secs)
        return False
    db.add(SalesVideoView(video_id=vm.id, viewer_hash=vh, seconds=secs, at=_now()))
    return True


async def listing(db: AsyncSession, user, everyone: bool) -> list[dict]:
    q = select(SalesVideoMessage).order_by(SalesVideoMessage.created_at.desc()).limit(200)
    if not everyone:
        q = q.where(SalesVideoMessage.created_by_id == user.id)
    rows = (await db.execute(q)).scalars().all()
    views = dict((await db.execute(select(SalesVideoView.video_id, func.count()).where(
        SalesVideoView.video_id.in_([r.id for r in rows])).group_by(SalesVideoView.video_id))).all()) if rows else {}
    return [{"id": str(r.id), "title": r.title, "contact_email": r.contact_email, "contact_name": r.contact_name,
             "customer_id": str(r.customer_id) if r.customer_id else None, "expires_at": r.expires_at.isoformat(),
             "revoked": r.revoked_at is not None, "views": views.get(r.id, 0)} for r in rows]
