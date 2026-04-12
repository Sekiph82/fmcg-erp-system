from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.production import (
    ProductionPlan, ProductionPlanLine,
    ProductionOrder, MaterialConsumption, FinishedGoodsReceipt, DowntimeLog,
    ProductionPlanStatus, ProductionOrderStatus,
)
from app.schemas.production import (
    ProductionPlanCreate, ProductionPlanUpdate,
    PlanLineCreate, ProductionOrderCreate,
)


# ── Production Plan ───────────────────────────────────────────────────────────

async def get_plan(db: AsyncSession, plan_id: uuid.UUID) -> Optional[ProductionPlan]:
    result = await db.execute(
        select(ProductionPlan)
        .where(ProductionPlan.id == plan_id)
        .options(
            selectinload(ProductionPlan.lines).selectinload(ProductionPlanLine.product),
            selectinload(ProductionPlan.lines).selectinload(ProductionPlanLine.recipe),
            selectinload(ProductionPlan.lines).selectinload(ProductionPlanLine.target_warehouse),
        )
    )
    return result.scalar_one_or_none()


async def list_plans(
    db: AsyncSession,
    status: Optional[ProductionPlanStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[ProductionPlan]:
    q = select(ProductionPlan)
    if status:
        q = q.where(ProductionPlan.status == status)
    q = q.order_by(ProductionPlan.planned_date.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_plan(
    db: AsyncSession, data: ProductionPlanCreate, user_id: uuid.UUID
) -> ProductionPlan:
    obj = ProductionPlan(**data.model_dump(), created_by=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_plan(
    db: AsyncSession, obj: ProductionPlan, data: ProductionPlanUpdate
) -> ProductionPlan:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def add_plan_line(
    db: AsyncSession, plan_id: uuid.UUID, data: PlanLineCreate
) -> ProductionPlanLine:
    obj = ProductionPlanLine(plan_id=plan_id, **data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_plan_line(db: AsyncSession, line: ProductionPlanLine) -> None:
    await db.delete(line)
    await db.flush()


async def get_plan_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[ProductionPlanLine]:
    result = await db.execute(select(ProductionPlanLine).where(ProductionPlanLine.id == line_id))
    return result.scalar_one_or_none()


# ── Production Order ──────────────────────────────────────────────────────────

async def get_order(db: AsyncSession, order_id: uuid.UUID) -> Optional[ProductionOrder]:
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .options(
            selectinload(ProductionOrder.product),
            selectinload(ProductionOrder.recipe),
            selectinload(ProductionOrder.target_warehouse),
            selectinload(ProductionOrder.source_warehouse),
            selectinload(ProductionOrder.consumptions).selectinload(MaterialConsumption.material),
            selectinload(ProductionOrder.consumptions).selectinload(MaterialConsumption.lot),
            selectinload(ProductionOrder.consumptions).selectinload(MaterialConsumption.source_warehouse),
            selectinload(ProductionOrder.fg_receipts).selectinload(FinishedGoodsReceipt.warehouse),
            selectinload(ProductionOrder.downtime_logs),
        )
    )
    return result.scalar_one_or_none()


async def list_orders(
    db: AsyncSession,
    status: Optional[ProductionOrderStatus] = None,
    product_id: Optional[uuid.UUID] = None,
    plan_line_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[ProductionOrder]:
    q = (
        select(ProductionOrder)
        .options(
            selectinload(ProductionOrder.product),
            selectinload(ProductionOrder.recipe),
            selectinload(ProductionOrder.target_warehouse),
        )
    )
    if status:
        q = q.where(ProductionOrder.status == status)
    if product_id:
        q = q.where(ProductionOrder.product_id == product_id)
    if plan_line_id:
        q = q.where(ProductionOrder.plan_line_id == plan_line_id)
    q = q.order_by(ProductionOrder.scheduled_start.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_order(
    db: AsyncSession, data: ProductionOrderCreate, user_id: uuid.UUID
) -> ProductionOrder:
    obj = ProductionOrder(**data.model_dump(), created_by=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Downtime ──────────────────────────────────────────────────────────────────

async def get_active_downtime(db: AsyncSession, order_id: uuid.UUID) -> Optional[DowntimeLog]:
    result = await db.execute(
        select(DowntimeLog)
        .where(DowntimeLog.production_order_id == order_id, DowntimeLog.end_time.is_(None))
    )
    return result.scalar_one_or_none()


async def get_downtime_log(db: AsyncSession, log_id: uuid.UUID) -> Optional[DowntimeLog]:
    result = await db.execute(select(DowntimeLog).where(DowntimeLog.id == log_id))
    return result.scalar_one_or_none()


async def list_downtime_logs(
    db: AsyncSession, order_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100
) -> List[DowntimeLog]:
    q = select(DowntimeLog)
    if order_id:
        q = q.where(DowntimeLog.production_order_id == order_id)
    q = q.order_by(DowntimeLog.start_time.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
