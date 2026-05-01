from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.wms import (
    WarehouseZone, StorageLocation, StockCount, StockCountLine,
    StockCountStatus, StockCountType,
    PutawayRule, PutawayTask, PutawayExecution, PutawayTaskStatus,
)
from app.schemas.wms import (
    WarehouseZoneCreate, StorageLocationCreate, StorageLocationUpdate,
    StockCountCreate, RecordCountRequest,
    PutawayRuleCreate, PutawayRuleUpdate, PutawayTaskCreate,
)


# ── Zones ─────────────────────────────────────────────────────────────────────

async def list_zones(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[WarehouseZone]:
    q = (
        select(WarehouseZone)
        .options(selectinload(WarehouseZone.warehouse), selectinload(WarehouseZone.locations))
    )
    if warehouse_id:
        q = q.where(WarehouseZone.warehouse_id == warehouse_id)
    q = q.order_by(WarehouseZone.code).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_zone(db: AsyncSession, zone_id: uuid.UUID) -> Optional[WarehouseZone]:
    result = await db.execute(
        select(WarehouseZone)
        .where(WarehouseZone.id == zone_id)
        .options(selectinload(WarehouseZone.warehouse), selectinload(WarehouseZone.locations).selectinload(StorageLocation.zone))
    )
    return result.scalar_one_or_none()


async def create_zone(db: AsyncSession, data: WarehouseZoneCreate) -> WarehouseZone:
    obj = WarehouseZone(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Locations ─────────────────────────────────────────────────────────────────

async def list_locations(
    db: AsyncSession,
    zone_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[StorageLocation]:
    q = (
        select(StorageLocation)
        .options(
            selectinload(StorageLocation.zone).selectinload(WarehouseZone.warehouse)
        )
    )
    if zone_id:
        q = q.where(StorageLocation.zone_id == zone_id)
    if warehouse_id:
        q = q.join(WarehouseZone).where(WarehouseZone.warehouse_id == warehouse_id)
    q = q.order_by(StorageLocation.code).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_location(db: AsyncSession, location_id: uuid.UUID) -> Optional[StorageLocation]:
    result = await db.execute(
        select(StorageLocation)
        .where(StorageLocation.id == location_id)
        .options(selectinload(StorageLocation.zone).selectinload(WarehouseZone.warehouse))
    )
    return result.scalar_one_or_none()


async def get_location_by_barcode(db: AsyncSession, barcode: str) -> Optional[StorageLocation]:
    result = await db.execute(
        select(StorageLocation)
        .where(StorageLocation.barcode == barcode)
        .options(selectinload(StorageLocation.zone).selectinload(WarehouseZone.warehouse))
    )
    return result.scalar_one_or_none()


async def create_location(db: AsyncSession, data: StorageLocationCreate) -> StorageLocation:
    obj = StorageLocation(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_location(
    db: AsyncSession, obj: StorageLocation, data: StorageLocationUpdate
) -> StorageLocation:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Stock Counts ──────────────────────────────────────────────────────────────

async def list_counts(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    status: Optional[StockCountStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[StockCount]:
    q = select(StockCount).options(
        selectinload(StockCount.warehouse),
        selectinload(StockCount.zone),
        selectinload(StockCount.lines),
    )
    if warehouse_id:
        q = q.where(StockCount.warehouse_id == warehouse_id)
    if status:
        q = q.where(StockCount.status == status)
    q = q.order_by(StockCount.scheduled_date.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_count(db: AsyncSession, count_id: uuid.UUID) -> Optional[StockCount]:
    result = await db.execute(
        select(StockCount)
        .where(StockCount.id == count_id)
        .options(
            selectinload(StockCount.warehouse),
            selectinload(StockCount.zone),
            selectinload(StockCount.lines).selectinload(StockCountLine.product),
            selectinload(StockCount.lines).selectinload(StockCountLine.material),
            selectinload(StockCount.lines).selectinload(StockCountLine.lot),
            selectinload(StockCount.lines).selectinload(StockCountLine.location),
        )
    )
    return result.scalar_one_or_none()


async def create_count(
    db: AsyncSession, data: StockCountCreate, user_id: uuid.UUID
) -> StockCount:
    obj = StockCount(**data.model_dump(), created_by=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_count_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[StockCountLine]:
    result = await db.execute(select(StockCountLine).where(StockCountLine.id == line_id))
    return result.scalar_one_or_none()


# ── Putaway Rules ─────────────────────────────────────────────────────────────

async def list_putaway_rules(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
) -> List[PutawayRule]:
    q = (
        select(PutawayRule)
        .options(
            selectinload(PutawayRule.warehouse),
            selectinload(PutawayRule.zone),
            selectinload(PutawayRule.location),
            selectinload(PutawayRule.product),
        )
        .order_by(PutawayRule.priority.asc())
    )
    if warehouse_id:
        q = q.where(PutawayRule.warehouse_id == warehouse_id)
    if is_active is not None:
        q = q.where(PutawayRule.is_active == is_active)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_putaway_rule(db: AsyncSession, rule_id: uuid.UUID) -> Optional[PutawayRule]:
    result = await db.execute(
        select(PutawayRule)
        .where(PutawayRule.id == rule_id)
        .options(
            selectinload(PutawayRule.warehouse),
            selectinload(PutawayRule.zone),
            selectinload(PutawayRule.location),
            selectinload(PutawayRule.product),
        )
    )
    return result.scalar_one_or_none()


async def create_putaway_rule(db: AsyncSession, data: PutawayRuleCreate) -> PutawayRule:
    obj = PutawayRule(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_putaway_rule(
    db: AsyncSession, obj: PutawayRule, data: PutawayRuleUpdate
) -> PutawayRule:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Putaway Tasks ─────────────────────────────────────────────────────────────

async def list_putaway_tasks(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    status: Optional[PutawayTaskStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[PutawayTask]:
    q = (
        select(PutawayTask)
        .options(
            selectinload(PutawayTask.warehouse),
            selectinload(PutawayTask.product),
            selectinload(PutawayTask.material),
            selectinload(PutawayTask.suggested_location),
            selectinload(PutawayTask.assignee),
            selectinload(PutawayTask.execution),
        )
        .order_by(PutawayTask.created_at.desc())
    )
    if warehouse_id:
        q = q.where(PutawayTask.warehouse_id == warehouse_id)
    if status:
        q = q.where(PutawayTask.status == status)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_putaway_task(db: AsyncSession, task_id: uuid.UUID) -> Optional[PutawayTask]:
    result = await db.execute(
        select(PutawayTask)
        .where(PutawayTask.id == task_id)
        .options(
            selectinload(PutawayTask.warehouse),
            selectinload(PutawayTask.product),
            selectinload(PutawayTask.material),
            selectinload(PutawayTask.suggested_location).selectinload(StorageLocation.zone),
            selectinload(PutawayTask.assignee),
            selectinload(PutawayTask.execution).selectinload(PutawayExecution.actual_location),
        )
    )
    return result.scalar_one_or_none()


async def create_putaway_task(
    db: AsyncSession, data: PutawayTaskCreate, task_no: str,
    suggested_location_id: Optional[uuid.UUID] = None,
) -> PutawayTask:
    obj = PutawayTask(
        task_no=task_no,
        suggested_location_id=suggested_location_id,
        **data.model_dump(),
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj
