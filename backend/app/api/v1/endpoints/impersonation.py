"""Audited impersonation and admin notification management (M45.S01.T023). Prefix /api/v1/impersonation."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.identity import ImpersonationSession, NotificationPolicy
from app.services import impersonation_service as imp
from app.services import notification_policy_service as nps
from app.services import pat_service as pats

router = APIRouter()


class StartIn(BaseModel):
    user_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=500)
    minutes: int = Field(30, ge=1, le=imp.MAX_MINUTES)


@router.post("/start")
async def start(body: StartIn, response: Response, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        s = await imp.start(db, current_user, body.user_id, body.reason, body.minutes)
    except imp.ImpersonationError as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    response.set_cookie(imp.COOKIE, imp.token_for(s), max_age=body.minutes * 60, httponly=True,
                        secure=settings.AUTH_COOKIE_SECURE, samesite=settings.AUTH_COOKIE_SAMESITE, path="/")
    return {"session_id": str(s.id), "expires_at": s.expires_at.isoformat()}


@router.post("/end")
async def end(request: Request, response: Response, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    info = getattr(current_user, "impersonated_by", None)
    if info:
        await imp.end(db, uuid.UUID(info["session_id"]))
        pats.audit(db, current_user, "IMPERSONATION_ENDED", "user", str(current_user.id), {"session": info["session_id"]})
        await db.commit()
    response.delete_cookie(imp.COOKIE, path="/", httponly=True, secure=settings.AUTH_COOKIE_SECURE, samesite=settings.AUTH_COOKIE_SAMESITE)
    return {"ended": bool(info)}


@router.get("/status")
async def status(current_user=Depends(get_current_user)):
    info = getattr(current_user, "impersonated_by", None)
    return {"active": bool(info), **(info or {})}


@router.get("/sessions")
async def sessions(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, ("users.impersonate", "audit.view"))):
        raise HTTPException(403, "Not allowed.")
    from app.models.user import User
    names = dict((await db.execute(select(User.id, User.username))).all())
    return [{"id": str(s.id), "actor": names.get(s.actor_id), "target": names.get(s.target_id), "reason": s.reason,
             "started_at": s.started_at.isoformat(), "expires_at": s.expires_at.isoformat(),
             "ended_at": s.ended_at.isoformat() if s.ended_at else None, "ended_reason": s.ended_reason}
            for s in (await db.execute(select(ImpersonationSession).order_by(ImpersonationSession.started_at.desc()).limit(200))).scalars()]


# ── admin notification management ────────────────────────────────────────────

@router.get("/notification-policies")
async def policies(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await nps.matrix(db)


class PolicyIn(BaseModel):
    notification_type: str = Field(max_length=30)
    channel: str = Field(max_length=20)
    default_enabled: bool
    mandatory: bool = False


@router.put("/notification-policies")
async def set_policy(body: PolicyIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, ("notifications.admin", "notifications.configure"))):
        raise HTTPException(403, "Only notification administrators change company defaults.")
    try:
        await nps.set_policy(db, body.notification_type, body.channel, body.default_enabled, body.mandatory, current_user.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    pats.audit(db, current_user, "NOTIFICATION_POLICY_CHANGED", "notification_policy", f"{body.notification_type}:{body.channel}", body.model_dump())
    await db.commit()
    return await nps.matrix(db)
