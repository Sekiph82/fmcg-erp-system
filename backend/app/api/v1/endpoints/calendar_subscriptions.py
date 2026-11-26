"""Calendar change notifications, staff side (M49.S01.T002). Prefix /api/v1/calendar-subscriptions.

A signed-in user manages only the subscriptions of their own connected calendars. Enable = create a Google channel /
Graph subscription and run the initial sync; renew = replace/extend it; disconnect = stop it at the provider.
Provider callbacks are in calendar_hooks_public.py."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.m49_calendar_mail import CalendarSubscription
from app.models.oauth_connection import OAuthConnection
from app.services import calendar_sync_service as cal
from app.services import calendar_webhook_service as hooks
from app.services import oauth_service as oauth

router = APIRouter()


async def _mine(db: AsyncSession, sub_id: uuid.UUID, user) -> CalendarSubscription:
    sub = await db.get(CalendarSubscription, sub_id)
    conn = await db.get(OAuthConnection, sub.connection_id) if sub else None
    if sub is None or conn is None or conn.user_id != user.id:
        raise HTTPException(404, "Subscription not found")
    return sub


@router.get("")
async def list_subscriptions(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Your calendars with the state of their change notifications (webhook, or polling when none is live)."""
    conns = (await db.execute(select(OAuthConnection).where(OAuthConnection.user_id == current_user.id,
                                                            OAuthConnection.purpose == "calendar",
                                                            OAuthConnection.status == "CONNECTED"))).scalars().all()
    out = []
    for c in conns:
        subs = (await db.execute(select(CalendarSubscription).where(CalendarSubscription.connection_id == c.id)
                                 .order_by(CalendarSubscription.created_at.desc()).limit(5))).scalars().all()
        live = next((s for s in subs if hooks.view(s)["mode"] == "webhook"), None)
        out.append({"connection_id": str(c.id), "provider": c.provider, "account_email": c.account_email,
                    "mode": "webhook" if live else "polling", "subscription": hooks.view(live or subs[0]) if (live or subs) else None,
                    "history": [hooks.view(s) for s in subs]})
    return out


@router.post("", status_code=201)
async def enable(connection_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    conn = await db.get(OAuthConnection, connection_id)
    if conn is None or conn.user_id != current_user.id:
        raise HTTPException(404, "Calendar connection not found")
    try:
        sub = await hooks.subscribe(db, conn, current_user)
    except hooks.WebhookError as e:
        await db.commit()                                 # keep the connection's last_error / audit trail
        raise HTTPException(409 if str(e).startswith("NOT_CONFIGURED") else 502, str(e))
    await db.commit()
    return hooks.view(sub)


@router.post("/{sub_id}/renew")
async def renew(sub_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    sub = await _mine(db, sub_id, current_user)
    if sub.status == "STOPPED":
        raise HTTPException(409, "This subscription was stopped; enable notifications again.")
    try:
        new = await hooks.renew(db, sub, current_user)
    except hooks.WebhookError as e:
        await db.rollback()
        raise HTTPException(502, str(e))
    await db.commit()
    return hooks.view(new)


@router.post("/{sub_id}/sync")
async def sync_now(sub_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Run the delta sync now (the same one a notification triggers)."""
    sub = await _mine(db, sub_id, current_user)
    conn = await db.get(OAuthConnection, sub.connection_id)
    try:
        res = await cal.sync_connection(db, conn)
    except (oauth.OAuthError, cal.CalendarApiError) as e:
        raise HTTPException(502, str(e))
    from app.core import clock
    sub.last_sync_at = clock.utcnow()
    await db.commit()
    return res


@router.post("/{sub_id}/disconnect")
async def disconnect(sub_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    sub = await _mine(db, sub_id, current_user)
    await hooks.stop(db, sub, current_user)
    await db.commit()
    return hooks.view(sub)
