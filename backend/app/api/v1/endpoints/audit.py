from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import uuid
import io
import csv
import hashlib
from datetime import datetime

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import audit as crud
from app.schemas.audit import AuditLogRead
from app.models.audit_log import AuditLog, AuditRetentionPolicy

router = APIRouter()


@router.get(
    "/",
    response_model=List[AuditLogRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def list_audit_logs(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_audit_logs(
        db,
        event_type=event_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/user/{user_id}",
    response_model=List[AuditLogRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def user_login_history(
    user_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Returns all audit events where the actor is the specified user."""
    return await crud.list_audit_logs(
        db,
        actor_id=user_id,
        skip=skip,
        limit=limit,
    )


# ── Stats / Summary ───────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(require_permission("audit", "view"))])
async def audit_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate audit event counts for compliance dashboard."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    total_r = await db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= cutoff)
    )
    total = total_r.scalar() or 0

    by_type_r = await db.execute(
        select(AuditLog.event_type, func.count().label("cnt"))
        .where(AuditLog.created_at >= cutoff)
        .group_by(AuditLog.event_type)
        .order_by(desc("cnt"))
        .limit(20)
    )
    by_type = {r.event_type: r.cnt for r in by_type_r.all()}

    by_module_r = await db.execute(
        select(AuditLog.module, func.count().label("cnt"))
        .where(AuditLog.created_at >= cutoff, AuditLog.module.isnot(None))
        .group_by(AuditLog.module)
        .order_by(desc("cnt"))
    )
    by_module = {r.module: r.cnt for r in by_module_r.all()}

    top_actors_r = await db.execute(
        select(AuditLog.actor_email, func.count().label("cnt"))
        .where(AuditLog.created_at >= cutoff, AuditLog.actor_email.isnot(None))
        .group_by(AuditLog.actor_email)
        .order_by(desc("cnt"))
        .limit(10)
    )
    top_actors = [{"email": r.actor_email, "count": r.cnt} for r in top_actors_r.all()]

    security_events = [
        "LOGIN_FAILED", "ACCOUNT_LOCKED", "PERMISSION_DENIED",
        "SUSPICIOUS_ACTIVITY", "AI_INJECTION_DETECTED",
    ]
    sec_r = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= cutoff,
            AuditLog.event_type.in_(security_events),
        )
    )
    security_alerts = sec_r.scalar() or 0

    return {
        "period_days": days,
        "total_events": total,
        "security_alerts": security_alerts,
        "by_event_type": by_type,
        "by_module": by_module,
        "top_actors": top_actors,
    }


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export", dependencies=[Depends(require_permission("audit", "view"))])
async def export_audit_logs(
    event_type: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    limit: int = Query(5000, le=50000),
    db: AsyncSession = Depends(get_db),
):
    """Export audit logs as CSV for compliance reporting."""
    q = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if module:
        q = q.where(AuditLog.module == module)

    result = await db.execute(q)
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "event_type", "module",
        "actor_email", "actor_name", "session_id", "ip_address",
        "target_type", "target_id", "target_name",
        "before_value", "after_value", "row_hash",
    ])
    for lg in logs:
        writer.writerow([
            str(lg.id),
            lg.created_at.isoformat() if lg.created_at else "",
            lg.event_type,
            lg.module or "",
            lg.actor_email or "",
            getattr(lg, "actor_name", "") or "",
            getattr(lg, "session_id", "") or "",
            lg.ip_address or "",
            lg.target_type or "",
            lg.target_id or "",
            lg.target_name or "",
            str(getattr(lg, "before_value", "") or ""),
            str(getattr(lg, "after_value", "") or ""),
            getattr(lg, "row_hash", "") or "",
        ])

    output.seek(0)
    filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.StringIO(output.read()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Integrity Check ───────────────────────────────────────────────────────────

@router.get("/integrity-check", dependencies=[Depends(require_permission("audit", "view"))])
async def integrity_check(
    limit: int = Query(1000, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify row_hash for recent audit log entries.
    Flags any rows where the stored hash doesn't match recomputed hash.
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.row_hash.isnot(None))
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    logs = result.scalars().all()

    tampered = []
    verified = 0
    no_hash = 0

    for lg in logs:
        if not lg.row_hash:
            no_hash += 1
            continue
        payload = (
            str(lg.id) +
            (lg.event_type or "") +
            (lg.actor_email or "") +
            (lg.created_at.isoformat() if lg.created_at else "") +
            str(lg.before_value or "") +
            str(lg.after_value or "")
        )
        expected = hashlib.sha256(payload.encode()).hexdigest()
        if expected != lg.row_hash:
            tampered.append({
                "id": str(lg.id),
                "event_type": lg.event_type,
                "created_at": lg.created_at.isoformat() if lg.created_at else "",
                "actor_email": lg.actor_email,
            })
        else:
            verified += 1

    return {
        "checked": len(logs),
        "verified": verified,
        "tampered_count": len(tampered),
        "no_hash_count": no_hash,
        "tampered_rows": tampered[:50],
        "status": "CLEAN" if not tampered else "INTEGRITY_VIOLATION",
    }


# ── Retention Policies ────────────────────────────────────────────────────────

from pydantic import BaseModel as _BM

class RetentionPolicyIn(_BM):
    module: str
    retain_days: int


@router.get("/retention", dependencies=[Depends(require_permission("audit", "view"))])
async def list_retention_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditRetentionPolicy).order_by(AuditRetentionPolicy.module)
    )
    policies = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "module": p.module,
            "retain_days": p.retain_days,
            "active_flag": p.active_flag,
        }
        for p in policies
    ]


@router.post("/retention", status_code=201, dependencies=[Depends(require_permission("audit", "export"))])
async def create_retention_policy(
    payload: RetentionPolicyIn,
    db: AsyncSession = Depends(get_db),
):
    # Upsert: update if module already exists
    existing_r = await db.execute(
        select(AuditRetentionPolicy).where(AuditRetentionPolicy.module == payload.module)
    )
    existing = existing_r.scalar_one_or_none()
    if existing:
        existing.retain_days = payload.retain_days
        existing.active_flag = True
        existing.updated_at = datetime.utcnow()
        await db.commit()
        return {"id": str(existing.id), "module": existing.module, "retain_days": existing.retain_days, "active_flag": True}

    policy = AuditRetentionPolicy(
        module=payload.module,
        retain_days=payload.retain_days,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return {"id": str(policy.id), "module": policy.module, "retain_days": policy.retain_days, "active_flag": True}
