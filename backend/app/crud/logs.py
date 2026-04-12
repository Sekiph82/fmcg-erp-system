from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List, Tuple
from datetime import datetime
import uuid

from app.models.operational_log import OperationalLog, MpesaStatusHistory
from app.schemas.logs import OperationalLogCreate


async def create_operational_log(db: AsyncSession, data: OperationalLogCreate) -> OperationalLog:
    entry = OperationalLog(**data.model_dump())
    db.add(entry)
    await db.flush()
    return entry


async def log_operation(
    db: AsyncSession,
    *,
    module_name: str,
    entity_type: str,
    action_type: str,
    entity_id: Optional[str] = None,
    status: str = "SUCCESS",
    error_message: Optional[str] = None,
    request_payload: Optional[dict] = None,
    response_payload: Optional[dict] = None,
    created_by_id: Optional[uuid.UUID] = None,
    created_by_email: Optional[str] = None,
) -> OperationalLog:
    entry = OperationalLog(
        module_name=module_name,
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action_type,
        status=status,
        error_message=error_message,
        request_payload=request_payload,
        response_payload=response_payload,
        created_by_id=created_by_id,
        created_by_email=created_by_email,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_operational_logs(
    db: AsyncSession,
    *,
    module_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    created_by_id: Optional[uuid.UUID] = None,
    error_only: bool = False,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[OperationalLog], int]:
    base_q = select(OperationalLog)
    if module_name:
        base_q = base_q.where(OperationalLog.module_name == module_name)
    if entity_type:
        base_q = base_q.where(OperationalLog.entity_type == entity_type)
    if entity_id:
        base_q = base_q.where(OperationalLog.entity_id == entity_id)
    if action_type:
        base_q = base_q.where(OperationalLog.action_type == action_type)
    if status:
        base_q = base_q.where(OperationalLog.status == status)
    if created_by_id:
        base_q = base_q.where(OperationalLog.created_by_id == created_by_id)
    if error_only:
        base_q = base_q.where(OperationalLog.status == "FAILED")
    if date_from:
        base_q = base_q.where(OperationalLog.created_at >= date_from)
    if date_to:
        base_q = base_q.where(OperationalLog.created_at <= date_to)

    count_q = select(func.count()).select_from(base_q.subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar_one()

    data_q = base_q.order_by(desc(OperationalLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(data_q)
    return list(result.scalars().all()), total


async def add_mpesa_status_history(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    old_status: Optional[str],
    new_status: str,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> MpesaStatusHistory:
    entry = MpesaStatusHistory(
        transaction_id=transaction_id,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_mpesa_status_history(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> List[MpesaStatusHistory]:
    q = (
        select(MpesaStatusHistory)
        .where(MpesaStatusHistory.transaction_id == transaction_id)
        .order_by(MpesaStatusHistory.created_at)
    )
    result = await db.execute(q)
    return list(result.scalars().all())
