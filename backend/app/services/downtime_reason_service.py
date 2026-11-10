"""Queries and input validation for the shared downtime reason taxonomy."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance import DowntimeReasonCode


async def list_downtime_reason_codes(db: AsyncSession) -> list[DowntimeReasonCode]:
    result = await db.execute(
        select(DowntimeReasonCode)
        .where(DowntimeReasonCode.is_active.is_(True))
        .order_by(DowntimeReasonCode.sort_order, DowntimeReasonCode.code)
    )
    return list(result.scalars().all())


async def validate_downtime_reason_code(
    db: AsyncSession,
    code: Optional[str],
) -> Optional[str]:
    if code is None:
        return None
    normalized = code.strip().upper()
    if not normalized:
        return None
    result = await db.execute(
        select(DowntimeReasonCode).where(
            DowntimeReasonCode.code == normalized,
            DowntimeReasonCode.is_active.is_(True),
            DowntimeReasonCode.is_selectable.is_(True),
            DowntimeReasonCode.parent_code.is_not(None),
            DowntimeReasonCode.parent.has(DowntimeReasonCode.is_active.is_(True)),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=422, detail="Select an active leaf downtime reason code.")
    return normalized
