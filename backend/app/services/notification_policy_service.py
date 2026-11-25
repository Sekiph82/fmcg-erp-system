"""M45.S01.T023 admin notification management: company-wide defaults and mandatory notifications.

Effective rule for one user, type and channel: mandatory → always delivered; otherwise the user's own preference
(nc_notification_preferences, including a temporary mute); otherwise the company default; otherwise on.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import NotificationPolicy


def _types():
    from app.models.notifications import NotificationChannel, NotificationType
    return [t.value for t in NotificationType], [c.value for c in NotificationChannel]


async def matrix(db: AsyncSession) -> dict:
    types, channels = _types()
    rows = {(p.notification_type, p.channel): p for p in (await db.execute(select(NotificationPolicy))).scalars()}
    return {"types": types, "channels": channels,
            "policies": [{"notification_type": t, "channel": c, "default_enabled": rows[(t, c)].default_enabled if (t, c) in rows else True,
                          "mandatory": rows[(t, c)].mandatory if (t, c) in rows else False} for t in types for c in channels]}


async def set_policy(db: AsyncSession, ntype: str, channel: str, default_enabled: bool, mandatory: bool, user: str) -> None:
    from sqlalchemy.dialects.postgresql import insert
    types, channels = _types()
    if ntype not in types or channel not in channels:
        raise ValueError("Unknown notification type or channel.")
    vals = {"default_enabled": default_enabled or mandatory, "mandatory": mandatory, "updated_by": user, "updated_at": datetime.now(timezone.utc)}
    await db.execute(insert(NotificationPolicy).values(id=uuid.uuid4(), notification_type=ntype, channel=channel, **vals)
                     .on_conflict_do_update(constraint="uq_nc_notification_policy", set_=vals))


async def should_notify(db: AsyncSession, user_id: str, ntype, channel) -> bool:
    from app.models.notifications import NotificationPreference
    t, c = getattr(ntype, "value", ntype), getattr(channel, "value", channel)
    pol = (await db.execute(select(NotificationPolicy).where(NotificationPolicy.notification_type == t,
                                                             NotificationPolicy.channel == c))).scalar_one_or_none()
    if pol is not None and pol.mandatory:
        return True
    pref = (await db.execute(select(NotificationPreference).where(
        NotificationPreference.user_id == str(user_id), NotificationPreference.notification_type == ntype,
        NotificationPreference.channel == channel))).scalars().first()
    if pref is not None:
        if pref.muted_until and pref.muted_until > datetime.utcnow():
            return False
        return bool(pref.enabled_flag)
    return pol.default_enabled if pol is not None else True
