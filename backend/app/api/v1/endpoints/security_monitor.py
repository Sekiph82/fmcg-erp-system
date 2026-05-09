"""
Security monitoring endpoint — dashboard for security events, threats, and anomalies.

GET /api/v1/security/dashboard   → threat overview
GET /api/v1/security/failed-logins → recent failed login attempts
GET /api/v1/security/anomalies   → suspicious activity events
GET /api/v1/security/lockouts    → currently locked identifiers
POST /api/v1/security/unlock/{identifier} → manually unlock an account
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.login_limiter import is_locked, get_failure_count, clear_login_failures
from app.core import token_blocklist
from app.models.audit_log import AuditLog, AuditEvent

router = APIRouter()
log = logging.getLogger(__name__)

_SECURITY_EVENTS = {
    AuditEvent.LOGIN_FAILED,
    AuditEvent.ACCOUNT_LOCKED,
    AuditEvent.PERMISSION_DENIED,
    AuditEvent.SUSPICIOUS_ACTIVITY,
    AuditEvent.AI_INJECTION_DETECTED,
    AuditEvent.MARGIN_FLOOR_OVERRIDE,
    AuditEvent.DUPLICATE_PAYMENT_BLOCKED,
    AuditEvent.STOCK_NEGATIVE_FLAGGED,
    AuditEvent.TOKEN_REVOKED,
    AuditEvent.PASSWORD_POLICY_VIOLATION,
    AuditEvent.TWO_FA_FAILED,
}


@router.get("/dashboard/")
async def security_dashboard(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("audit", "view")),
):
    """High-level security posture for the last N hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Failed logins in window
    failed_logins = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.event_type == AuditEvent.LOGIN_FAILED)
        .where(AuditLog.created_at >= since)
    )).scalar() or 0

    # Unique IPs with failed logins
    unique_ips = (await db.execute(
        select(func.count(AuditLog.ip_address.distinct()))
        .where(AuditLog.event_type == AuditEvent.LOGIN_FAILED)
        .where(AuditLog.created_at >= since)
        .where(AuditLog.ip_address.isnot(None))
    )).scalar() or 0

    # Total security events
    security_events = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.event_type.in_(list(_SECURITY_EVENTS)))
        .where(AuditLog.created_at >= since)
    )).scalar() or 0

    # Successful logins
    successful_logins = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.event_type == AuditEvent.LOGIN_SUCCESS)
        .where(AuditLog.created_at >= since)
    )).scalar() or 0

    # AI injection attempts
    injection_attempts = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.event_type == AuditEvent.AI_INJECTION_DETECTED)
        .where(AuditLog.created_at >= since)
    )).scalar() or 0

    # Active blocked tokens
    blocked_tokens = await token_blocklist.store_size()

    # Top 5 IPs with most failures
    top_ips_rows = (await db.execute(
        select(AuditLog.ip_address, func.count(AuditLog.id).label("cnt"))
        .where(AuditLog.event_type == AuditEvent.LOGIN_FAILED)
        .where(AuditLog.created_at >= since)
        .where(AuditLog.ip_address.isnot(None))
        .group_by(AuditLog.ip_address)
        .order_by(desc("cnt"))
        .limit(5)
    )).all()

    top_ips = [{"ip": r.ip_address, "failures": r.cnt} for r in top_ips_rows]

    # Risk level
    risk_level = "low"
    if failed_logins > 50 or injection_attempts > 5:
        risk_level = "critical"
    elif failed_logins > 20 or security_events > 30:
        risk_level = "high"
    elif failed_logins > 5:
        risk_level = "medium"

    return {
        "window_hours": hours,
        "risk_level": risk_level,
        "stats": {
            "failed_logins": failed_logins,
            "successful_logins": successful_logins,
            "unique_attacker_ips": unique_ips,
            "security_events_total": security_events,
            "ai_injection_attempts": injection_attempts,
            "blocked_tokens_in_memory": blocked_tokens,
        },
        "top_attacker_ips": top_ips,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/failed-logins/")
async def recent_failed_logins(
    limit: int = Query(50, le=200),
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("audit", "view")),
):
    """List recent failed login attempts."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.event_type == AuditEvent.LOGIN_FAILED)
        .where(AuditLog.created_at >= since)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )).scalars().all()

    return [
        {
            "id": str(r.id),
            "actor_email": r.actor_email,
            "ip_address": r.ip_address,
            "reason": (r.details or {}).get("reason"),
            "failure_count": (r.details or {}).get("failure_count"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/anomalies/")
async def security_anomalies(
    limit: int = Query(50, le=200),
    hours: int = Query(72, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("audit", "view")),
):
    """List suspicious security events."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    anomaly_events = [
        AuditEvent.SUSPICIOUS_ACTIVITY,
        AuditEvent.AI_INJECTION_DETECTED,
        AuditEvent.MARGIN_FLOOR_OVERRIDE,
        AuditEvent.DUPLICATE_PAYMENT_BLOCKED,
        AuditEvent.STOCK_NEGATIVE_FLAGGED,
        AuditEvent.PASSWORD_POLICY_VIOLATION,
        AuditEvent.ACCOUNT_LOCKED,
        AuditEvent.TWO_FA_FAILED,
    ]
    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.event_type.in_(anomaly_events))
        .where(AuditLog.created_at >= since)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )).scalars().all()

    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "actor_email": r.actor_email,
            "target_name": r.target_name,
            "ip_address": r.ip_address,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/account-status/{username}")
async def account_status(
    username: str,
    _=Depends(require_permission("users", "view")),
):
    """Check lock/failure status for a username."""
    return {
        "username": username,
        "locked": is_locked(username),
        "recent_failures": get_failure_count(username),
    }


@router.post("/unlock/{identifier}")
async def unlock_account(
    identifier: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users", "edit")),
):
    """Manually clear lockout for an identifier (username or IP)."""
    clear_login_failures(identifier)
    await db.execute(
        # Log the manual unlock action
        select(AuditLog)  # dummy select to get db into "used" state
    )
    from app.crud import audit as audit_crud
    from app.models.audit_log import AuditEvent
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_UPDATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="account_lock",
        target_name=identifier,
        details={"action": "manual_unlock"},
    )
    await db.commit()
    return {"detail": f"Account unlocked for: {identifier}"}
