from __future__ import annotations
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.distribution import Distributor, DistributorPricingTier
from app.schemas.distribution import DistributorCreate, DistributorUpdate, DistributorPricingTierCreate


async def list_distributors(
    db: AsyncSession,
    *,
    region: Optional[str] = None,
    active_only: bool = False,
) -> List[Distributor]:
    q = select(Distributor)
    if region:
        q = q.where(Distributor.region == region)
    if active_only:
        from app.models.distribution import DistributorStatus
        q = q.where(Distributor.status == DistributorStatus.ACTIVE)
    result = await db.execute(q.order_by(Distributor.name))
    return list(result.scalars().all())


async def get_distributor(db: AsyncSession, distributor_id: uuid.UUID) -> Optional[Distributor]:
    result = await db.execute(
        select(Distributor)
        .options(selectinload(Distributor.pricing_tiers))
        .where(Distributor.id == distributor_id)
    )
    return result.scalar_one_or_none()


async def get_distributor_by_code(db: AsyncSession, code: str) -> Optional[Distributor]:
    result = await db.execute(select(Distributor).where(Distributor.code == code))
    return result.scalar_one_or_none()


async def create_distributor(db: AsyncSession, data: DistributorCreate) -> Distributor:
    d = Distributor(**data.model_dump())
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def update_distributor(db: AsyncSession, dist: Distributor, data: DistributorUpdate) -> Distributor:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(dist, k, v)
    await db.flush()
    await db.refresh(dist)
    return dist


async def add_pricing_tier(
    db: AsyncSession,
    distributor_id: uuid.UUID,
    data: DistributorPricingTierCreate,
) -> DistributorPricingTier:
    tier = DistributorPricingTier(distributor_id=distributor_id, **data.model_dump())
    db.add(tier)
    await db.flush()
    await db.refresh(tier)
    return tier
