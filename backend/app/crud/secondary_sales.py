from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.secondary_sales import (
    RetailerMaster, SecondarySalesHeader, SecondarySalesLine,
    DistributorInventorySnapshot, SecondarySalesStatus,
)
from app.schemas.secondary_sales import RetailerCreate, InventorySnapshotCreate


# ── Retailers ─────────────────────────────────────────────────────────────────

async def list_retailers(
    db: AsyncSession,
    distributor_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[RetailerMaster]:
    q = (
        select(RetailerMaster)
        .options(selectinload(RetailerMaster.distributor))
        .order_by(RetailerMaster.name)
    )
    if distributor_id:
        q = q.where(RetailerMaster.distributor_id == distributor_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_retailer(db: AsyncSession, retailer_id: uuid.UUID) -> Optional[RetailerMaster]:
    result = await db.execute(
        select(RetailerMaster)
        .where(RetailerMaster.id == retailer_id)
        .options(selectinload(RetailerMaster.distributor))
    )
    return result.scalar_one_or_none()


async def create_retailer(db: AsyncSession, data: RetailerCreate) -> RetailerMaster:
    obj = RetailerMaster(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_or_create_retailer_by_name(
    db: AsyncSession,
    name: str,
    distributor_id: Optional[uuid.UUID],
) -> Optional[RetailerMaster]:
    q = select(RetailerMaster).where(RetailerMaster.name == name)
    if distributor_id:
        q = q.where(RetailerMaster.distributor_id == distributor_id)
    result = await db.execute(q)
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    obj = RetailerMaster(name=name, distributor_id=distributor_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Secondary Sales Headers ───────────────────────────────────────────────────

async def list_headers(
    db: AsyncSession,
    distributor_id: Optional[uuid.UUID] = None,
    status: Optional[SecondarySalesStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[SecondarySalesHeader]:
    q = (
        select(SecondarySalesHeader)
        .options(selectinload(SecondarySalesHeader.distributor))
        .order_by(SecondarySalesHeader.created_at.desc())
    )
    if distributor_id:
        q = q.where(SecondarySalesHeader.distributor_id == distributor_id)
    if status:
        q = q.where(SecondarySalesHeader.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_header(db: AsyncSession, header_id: uuid.UUID) -> Optional[SecondarySalesHeader]:
    result = await db.execute(
        select(SecondarySalesHeader)
        .where(SecondarySalesHeader.id == header_id)
        .options(
            selectinload(SecondarySalesHeader.distributor),
            selectinload(SecondarySalesHeader.lines).selectinload(SecondarySalesLine.product),
            selectinload(SecondarySalesHeader.lines).selectinload(SecondarySalesLine.retailer),
        )
    )
    return result.scalar_one_or_none()


async def create_header(
    db: AsyncSession,
    header: SecondarySalesHeader,
) -> SecondarySalesHeader:
    db.add(header)
    await db.flush()
    await db.refresh(header)
    return header


# ── Inventory Snapshots ───────────────────────────────────────────────────────

async def list_snapshots(
    db: AsyncSession,
    distributor_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[DistributorInventorySnapshot]:
    q = (
        select(DistributorInventorySnapshot)
        .options(
            selectinload(DistributorInventorySnapshot.distributor),
            selectinload(DistributorInventorySnapshot.product),
        )
        .order_by(DistributorInventorySnapshot.snapshot_date.desc())
    )
    if distributor_id:
        q = q.where(DistributorInventorySnapshot.distributor_id == distributor_id)
    if product_id:
        q = q.where(DistributorInventorySnapshot.product_id == product_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_snapshot(
    db: AsyncSession, data: InventorySnapshotCreate
) -> DistributorInventorySnapshot:
    # Upsert by unique constraint
    existing_q = await db.execute(
        select(DistributorInventorySnapshot).where(
            DistributorInventorySnapshot.distributor_id == data.distributor_id,
            DistributorInventorySnapshot.product_id == data.product_id,
            DistributorInventorySnapshot.snapshot_date == data.snapshot_date,
        ).with_for_update()
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        existing.stock_qty = data.stock_qty
        if data.notes:
            existing.notes = data.notes
        await db.flush()
        await db.refresh(existing)
        return existing

    obj = DistributorInventorySnapshot(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj
