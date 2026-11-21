"""Mobile Apps Support Layer endpoints.

Prefix: /api/v1/mobile
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_current_user, get_db

# device management, push sending and company-wide mobile figures: administrators only (M37.S03.T002)
MOBILE_ADMIN = require_any_permission(("users.edit", "company.edit", "integrations.edit"))
from app.models.mobile import MobileAppSession, MobilePlatform, MobilePushToken
from app.models.user import User
from app.services import approval_service as approval_svc

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class DeviceRegisterIn(BaseModel):
    device_id: str
    platform: MobilePlatform
    token: str
    device_name: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None


class DeviceOut(BaseModel):
    push_token_id: str
    device_id: str
    device_name: Optional[str]
    platform: str
    token: str
    active_flag: bool
    app_version: Optional[str]
    created_at: str
    last_seen_at: str

    @classmethod
    def from_orm(cls, t: MobilePushToken) -> "DeviceOut":
        return cls(
            push_token_id=str(t.push_token_id),
            device_id=t.device_id,
            device_name=t.device_name,
            platform=t.platform,
            token=t.token,
            active_flag=t.active_flag,
            app_version=t.app_version,
            created_at=t.created_at.isoformat() if t.created_at else "",
            last_seen_at=t.last_seen_at.isoformat() if t.last_seen_at else "",
        )


class PushSendIn(BaseModel):
    user_ids: List[str]
    title: str
    body: str
    data: Optional[dict] = None


# ── Device / Push Token Registration ────────────────────────────────────────

@router.post("/devices", status_code=201)
async def register_device(
    payload: DeviceRegisterIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register or refresh a mobile push token for the current user."""
    # Deactivate existing token for same device_id + user
    existing_r = await db.execute(
        select(MobilePushToken).where(
            MobilePushToken.user_id == str(current_user.id),
            MobilePushToken.device_id == payload.device_id,
            MobilePushToken.active_flag == True,
        )
    )
    for old in existing_r.scalars().all():
        old.active_flag = False

    token = MobilePushToken(
        user_id=str(current_user.id),
        device_id=payload.device_id,
        platform=payload.platform,
        token=payload.token,
        device_name=payload.device_name,
        app_version=payload.app_version,
    )
    db.add(token)

    # Upsert session record
    sess_r = await db.execute(
        select(MobileAppSession).where(
            MobileAppSession.user_id == str(current_user.id),
            MobileAppSession.device_id == payload.device_id,
        )
    )
    sess = sess_r.scalar_one_or_none()
    if sess:
        sess.last_sync_at = datetime.utcnow()
        sess.is_active = True
        sess.app_version = payload.app_version
    else:
        sess = MobileAppSession(
            user_id=str(current_user.id),
            device_id=payload.device_id,
            device_name=payload.device_name,
            platform=payload.platform,
            os_version=payload.os_version,
            app_version=payload.app_version,
        )
        db.add(sess)

    await db.commit()
    await db.refresh(token)
    return {"push_token_id": str(token.push_token_id), "status": "registered"}


@router.get("/devices", response_model=List[DeviceOut])
async def list_my_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active registered devices for the current user."""
    r = await db.execute(
        select(MobilePushToken).where(
            MobilePushToken.user_id == str(current_user.id),
            MobilePushToken.active_flag == True,
        ).order_by(MobilePushToken.last_seen_at.desc())
    )
    return [DeviceOut.from_orm(t) for t in r.scalars().all()]


@router.delete("/devices/{push_token_id}", status_code=204)
async def deactivate_device(
    push_token_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a push token / unregister a device."""
    r = await db.execute(
        select(MobilePushToken).where(
            MobilePushToken.push_token_id == uuid.UUID(push_token_id),
            MobilePushToken.user_id == str(current_user.id),
        )
    )
    token = r.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Device token not found")
    token.active_flag = False
    await db.commit()


# ── Push Notification (Stub) ─────────────────────────────────────────────────

@router.post("/push/send")
async def send_push_notification(
    payload: PushSendIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(MOBILE_ADMIN),
):
    """Send a Web Push message to the users' installed apps (administrators only). Returns real delivery counts."""
    from app.services.web_push_service import send_to_users
    result = await send_to_users(db, [str(u) for u in payload.user_ids], {"title": payload.title, "body": payload.body,
                                                                         "url": "/dashboard"})
    return {**result, "title": payload.title, "body": payload.body}


# ── Mobile Approvals Inbox ───────────────────────────────────────────────────

@router.get("/approvals")
async def mobile_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compact pending approvals list optimised for mobile view."""
    requests = await approval_svc.get_pending_for_user(db, current_user.id)
    return [
        {
            "request_id": str(req.request_id),
            "reference_type": req.reference_type,
            "reference_id": str(req.reference_id) if req.reference_id else None,
            "title": req.title,
            "amount": float(req.amount) if req.amount else None,
            "currency": req.currency or "KES",
            "requested_by": (
                req.requested_by.full_name or req.requested_by.username
                if req.requested_by else "Unknown"
            ),
            "created_at": req.created_at.isoformat() if req.created_at else "",
        }
        for req in requests
    ]


# ── Mobile Dashboard KPIs ────────────────────────────────────────────────────

@router.get("/kpis")
async def mobile_kpis(
    db: AsyncSession = Depends(get_db),
    _=Depends(MOBILE_ADMIN),
):
    """Key metrics for mobile dashboard screen."""
    from app.models.workflow import ApprovalRequest, ApprovalStatus

    # Pending approvals count
    r = await db.execute(
        select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.status == ApprovalStatus.PENDING
        )
    )
    pending_approvals = r.scalar() or 0

    # Registered mobile devices count
    r2 = await db.execute(
        select(func.count()).select_from(MobilePushToken).where(
            MobilePushToken.active_flag == True
        )
    )
    active_devices = r2.scalar() or 0

    # Active mobile sessions count (seen in last 7 days)
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    r3 = await db.execute(
        select(func.count()).select_from(MobileAppSession).where(
            MobileAppSession.last_sync_at >= cutoff,
            MobileAppSession.is_active == True,
        )
    )
    active_sessions = r3.scalar() or 0

    return {
        "pending_approvals": pending_approvals,
        "active_devices": active_devices,
        "active_sessions_7d": active_sessions,
    }


# ── Device Stats (admin) ─────────────────────────────────────────────────────

@router.get("/devices/stats")
async def device_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(MOBILE_ADMIN),
):
    """Aggregate device stats by platform."""
    r = await db.execute(
        select(MobilePushToken.platform, func.count().label("count"))
        .where(MobilePushToken.active_flag == True)
        .group_by(MobilePushToken.platform)
    )
    rows = r.all()
    by_platform = {row.platform: row.count for row in rows}

    r2 = await db.execute(
        select(func.count()).select_from(MobilePushToken).where(
            MobilePushToken.active_flag == True
        )
    )
    total_active = r2.scalar() or 0

    r3 = await db.execute(
        select(func.count()).select_from(MobilePushToken)
    )
    total_ever = r3.scalar() or 0

    return {
        "total_active_devices": total_active,
        "total_registered_ever": total_ever,
        "by_platform": by_platform,
    }



# ── Web Push subscriptions (M37.S03.T001) ─────────────────────────────────────

class WebPushKeys(BaseModel):
    p256dh: str
    auth: str


class WebPushSubscribeIn(BaseModel):
    endpoint: str
    keys: WebPushKeys


@router.get("/push/public-key")
async def web_push_public_key(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.web_push_service import vapid_keys
    return {"public_key": (await vapid_keys(db))[1]}


@router.post("/push/subscribe", status_code=201)
async def web_push_subscribe(body: WebPushSubscribeIn, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """Register this browser for push. The endpoint must be an https push service; it is re-bound to the
    signed-in user if the device changed hands."""
    from urllib.parse import urlsplit
    from sqlalchemy.dialects.postgresql import insert
    from app.models.mobile import WebPushSubscription
    from app.services.web_push_service import unb64u

    if urlsplit(body.endpoint).scheme != "https" or len(body.endpoint) > 1000:
        raise HTTPException(422, "Push endpoint must be an https URL.")
    try:
        if len(unb64u(body.keys.p256dh)) != 65 or len(unb64u(body.keys.auth)) < 16:
            raise ValueError
    except ValueError:
        raise HTTPException(422, "Invalid subscription keys.")
    ua = (request.headers.get("user-agent") or "")[:300]
    await db.execute(insert(WebPushSubscription).values(
        id=uuid.uuid4(), user_id=current_user.id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth,
        user_agent=ua).on_conflict_do_update(index_elements=["endpoint"], set_={
            "user_id": current_user.id, "p256dh": body.keys.p256dh, "auth": body.keys.auth, "user_agent": ua}))
    await db.commit()
    return {"subscribed": True}


@router.post("/push/unsubscribe")
async def web_push_unsubscribe(body: WebPushSubscribeIn, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    from sqlalchemy import delete
    from app.models.mobile import WebPushSubscription
    await db.execute(delete(WebPushSubscription).where(WebPushSubscription.endpoint == body.endpoint,
                                                       WebPushSubscription.user_id == current_user.id))
    await db.commit()
    return {"subscribed": False}
