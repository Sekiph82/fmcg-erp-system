from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
import uuid

from app.models.audit_log import AuditLog


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    actor_id: Optional[uuid.UUID] = None,
    actor_email: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_name: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        actor_email=actor_email,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    event_type: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[AuditLog]:
    q = select(AuditLog).order_by(desc(AuditLog.created_at))
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if target_id:
        q = q.where(AuditLog.target_id == target_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())
