"""M45.S01.T023 audited impersonation ("log in as another user" for support).

- Only a superuser or a holder of users.impersonate, with a written reason, for at most 60 minutes.
- Never as a superuser, an inactive user or oneself; no nesting.
- The support person keeps their own session; a separate signed cookie (erp_imp) switches the identity while the
  session row is open and unexpired and belongs to that same person.
- While impersonating, secrets of the target cannot be touched: password, 2FA, access tokens and starting another
  impersonation are refused (any method but GET on those paths).
- Every audit-log row written during the session records both people (listener on AuditLog inserts), and the target
  is notified when the session starts.
"""
from __future__ import annotations

import contextvars
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.identity import ImpersonationSession

COOKIE = "erp_imp"
MAX_MINUTES = 60
BLOCKED_PREFIXES = ("/api/v1/auth/2fa", "/api/v1/auth/change-password", "/api/v1/auth/password", "/api/v1/users/me/change-password",
                    "/api/v1/access-tokens", "/api/v1/impersonation/start", "/api/v1/auth/logout-all")
current: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("impersonation", default=None)


class ImpersonationError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def token_for(s: ImpersonationSession) -> str:
    return jwt.encode({"isid": str(s.id), "act": str(s.actor_id), "exp": s.expires_at, "typ": "imp"}, settings.SECRET_KEY, algorithm="HS256")


async def start(db: AsyncSession, actor, target_id: uuid.UUID, reason: str, minutes: int) -> ImpersonationSession:
    from app.core.access_control import has_permission
    from app.models.notifications import (Notification, NotificationChannel, NotificationPriority, NotificationStatus,
                                          NotificationType)
    from app.models.user import User
    from app.services import pat_service as pats
    if current.get():
        raise ImpersonationError(403, "You are already acting as another user.")
    if not (actor.is_superuser or has_permission(actor, "users.impersonate")):
        raise ImpersonationError(403, "You do not have the right to log in as another user.")
    if len((reason or "").strip()) < 10:
        raise ImpersonationError(422, "Give a reason (at least 10 characters), e.g. the support ticket.")
    target = await db.get(User, target_id)
    if target is None or not target.is_active:
        raise ImpersonationError(404, "User not found or inactive.")
    if target.is_superuser:
        raise ImpersonationError(403, "Superusers cannot be impersonated.")
    if target.id == actor.id:
        raise ImpersonationError(422, "You cannot impersonate yourself.")
    if not actor.is_superuser:                                   # privilege ceiling: never gain rights by impersonating
        from sqlalchemy.orm import selectinload as _sl
        from app.core.access_control import get_effective_permission_codes
        from app.models.role import Role
        full = (await db.execute(select(User).options(_sl(User.roles).selectinload(Role.permissions)).where(User.id == target.id))).scalar_one()
        extra = set(get_effective_permission_codes(full)) - set(get_effective_permission_codes(actor))
        if extra:
            raise ImpersonationError(403, f"This user has rights you do not have ({', '.join(sorted(extra)[:5])}); ask an administrator.")
    s = ImpersonationSession(actor_id=actor.id, target_id=target.id, reason=reason.strip()[:500],
                             expires_at=_now() + timedelta(minutes=max(1, min(MAX_MINUTES, minutes))))
    db.add(s)
    await db.flush()
    pats.audit(db, actor, "IMPERSONATION_STARTED", "user", str(target.id),
               {"session": str(s.id), "reason": s.reason, "expires_at": s.expires_at.isoformat()})
    db.add(Notification(user_id=str(target.id), user_name=target.full_name, title="A support person accessed your account",
                        message=f"{actor.full_name or actor.username} signed in as you until {s.expires_at:%H:%M} UTC. Reason: {s.reason}",
                        notification_type=NotificationType.SYSTEM_ALERT, priority=NotificationPriority.HIGH,
                        channel=NotificationChannel.IN_APP, status=NotificationStatus.SENT, sent_at=datetime.utcnow(),
                        reference_type="impersonation", reference_id=str(s.id), module="security"))
    return s


async def end(db: AsyncSession, session_id: uuid.UUID, reason: str = "ENDED") -> Optional[ImpersonationSession]:
    s = await db.get(ImpersonationSession, session_id)
    if s is not None and s.ended_at is None:
        s.ended_at, s.ended_reason = _now(), reason
    return s


async def resolve(db: AsyncSession, request, actor, raw: str):
    """The target user if the impersonation cookie is valid for this actor; otherwise the actor unchanged."""
    from fastapi import HTTPException
    from app.models.role import Role
    from app.models.user import User
    try:
        claims = jwt.decode(raw, settings.SECRET_KEY, algorithms=["HS256"])
        sid = uuid.UUID(claims["isid"])
    except Exception:
        return actor
    if claims.get("typ") != "imp" or claims.get("act") != str(actor.id):
        return actor
    s = await db.get(ImpersonationSession, sid)
    if s is None or s.ended_at is not None or s.actor_id != actor.id:
        return actor
    if s.expires_at <= _now():
        s.ended_at, s.ended_reason = _now(), "EXPIRED"
        await db.commit()
        return actor
    target = (await db.execute(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                               .options(selectinload(User.roles).selectinload(Role.access_scopes))
                               .options(selectinload(User.access_scopes)).options(selectinload(User.two_fa_settings))
                               .where(User.id == s.target_id))).scalar_one_or_none()
    if target is None or not target.is_active or target.is_superuser:
        return actor
    if request.method != "GET" and request.url.path.startswith(BLOCKED_PREFIXES):
        raise HTTPException(403, "Not allowed while acting as another user (passwords, 2FA, tokens and impersonation are the user's own).")
    info = {"session_id": str(s.id), "actor_id": str(actor.id), "actor": actor.username, "target": target.username,
            "expires_at": s.expires_at.isoformat()}
    current.set(info)
    target.impersonated_by = info
    return target


@event.listens_for(Session, "before_flush")
def _stamp_audit(session, flush_context, instances):
    info = current.get()
    if not info:
        return
    from app.models.audit_log import AuditLog
    for obj in session.new:
        if isinstance(obj, AuditLog):
            obj.details = {**(obj.details or {}), "impersonated_by": info["actor"], "impersonator_id": info["actor_id"],
                           "impersonation_id": info["session_id"]}
