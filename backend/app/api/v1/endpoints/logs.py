from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
import uuid
import csv
import io

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import logs as crud
from app.schemas.logs import OperationalLogRead, MpesaStatusHistoryRead, LogsPageResponse
from app.models.operational_log import OperationalLog
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogRead

router = APIRouter()


@router.get(
    "/operational",
    response_model=LogsPageResponse,
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def list_operational_logs(
    module_name: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_by_id: Optional[uuid.UUID] = Query(None),
    error_only: bool = Query(False),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud.list_operational_logs(
        db,
        module_name=module_name,
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action_type,
        status=status,
        created_by_id=created_by_id,
        error_only=error_only,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return LogsPageResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/mpesa",
    response_model=LogsPageResponse,
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def list_mpesa_logs(
    status: Optional[str] = Query(None),
    error_only: bool = Query(False),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Operational logs filtered to M-Pesa module only."""
    items, total = await crud.list_operational_logs(
        db,
        module_name="mpesa",
        status=status,
        error_only=error_only,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return LogsPageResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/mpesa/transaction/{transaction_id}/history",
    response_model=List[MpesaStatusHistoryRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def mpesa_transaction_history(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_mpesa_status_history(db, transaction_id)


@router.get(
    "/security",
    response_model=List[AuditLogRead],
    dependencies=[Depends(require_permission("audit", "view"))],
)
async def list_security_logs(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
    target_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(desc(AuditLog.created_at))
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


@router.get(
    "/operational/export",
    dependencies=[Depends(require_permission("audit", "export"))],
)
async def export_operational_logs(
    module_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    error_only: bool = Query(False),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export operational logs as CSV (max 5000 rows)."""
    items, _ = await crud.list_operational_logs(
        db,
        module_name=module_name,
        status=status,
        error_only=error_only,
        date_from=date_from,
        date_to=date_to,
        skip=0,
        limit=5000,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "module_name", "entity_type", "entity_id",
        "action_type", "status", "created_by_email", "error_message",
    ])
    for row in items:
        writer.writerow([
            str(row.id), row.created_at.isoformat(), row.module_name,
            row.entity_type, row.entity_id or "", row.action_type,
            row.status, row.created_by_email or "", row.error_message or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=operational_logs.csv"},
    )
