from __future__ import annotations
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.returns_mgmt import ReturnOrder, ReturnLine, ReturnStatus
from app.schemas.returns_mgmt import ReturnOrderCreate, ReturnOrderUpdate


async def list_returns(
    db: AsyncSession,
    *,
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[ReturnStatus] = None,
    limit: int = 50,
) -> List[ReturnOrder]:
    q = select(ReturnOrder).options(
        selectinload(ReturnOrder.customer),
        selectinload(ReturnOrder.lines).selectinload(ReturnLine.product),
    )
    if customer_id:
        q = q.where(ReturnOrder.customer_id == customer_id)
    if status:
        q = q.where(ReturnOrder.status == status)
    result = await db.execute(q.order_by(ReturnOrder.return_date.desc()).limit(limit))
    return list(result.scalars().all())


async def get_return(db: AsyncSession, return_id: uuid.UUID) -> Optional[ReturnOrder]:
    result = await db.execute(
        select(ReturnOrder)
        .options(
            selectinload(ReturnOrder.customer),
            selectinload(ReturnOrder.lines).selectinload(ReturnLine.product),
            selectinload(ReturnOrder.created_by),
            selectinload(ReturnOrder.approved_by),
        )
        .where(ReturnOrder.id == return_id)
    )
    return result.scalar_one_or_none()


async def create_return(
    db: AsyncSession,
    data: ReturnOrderCreate,
    created_by_id: uuid.UUID,
) -> ReturnOrder:
    lines_data = data.lines
    ret = ReturnOrder(**data.model_dump(exclude={"lines"}), created_by_id=created_by_id)
    db.add(ret)
    await db.flush()
    for ld in lines_data:
        db.add(ReturnLine(return_id=ret.id, **ld.model_dump()))
    await db.flush()
    await db.refresh(ret)
    return ret


async def update_return(db: AsyncSession, ret: ReturnOrder, data: ReturnOrderUpdate) -> ReturnOrder:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(ret, k, v)
    await db.flush()
    await db.refresh(ret)
    return ret
