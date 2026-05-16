from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import (
    Asset, PMPlan, PMWorkOrder, BreakdownRecord, SparePart, SparePartUsage,
    AssetStatus, PMStatus, BreakdownStatus,
)


# ── Assets ─────────────────────────────────────────────────────────────────────

async def list_assets(
    db: AsyncSession,
    status: Optional[AssetStatus] = None,
    line: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Asset]:
    q = select(Asset).order_by(Asset.line, Asset.asset_no)
    if status:
        q = q.where(Asset.status == status)
    if line:
        q = q.where(Asset.line == line)
    return list((await db.execute(q.offset(offset).limit(min(limit, 1000)))).scalars().all())


async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Optional[Asset]:
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalar_one_or_none()


async def create_asset(db: AsyncSession, data: dict) -> Asset:
    asset = Asset(**data)
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def update_asset(db: AsyncSession, asset: Asset, data: dict) -> Asset:
    for k, v in data.items():
        if v is not None:
            setattr(asset, k, v)
    await db.flush()
    await db.refresh(asset)
    return asset


# ── PM Plans ───────────────────────────────────────────────────────────────────

async def list_pm_plans(
    db: AsyncSession,
    asset_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> List[PMPlan]:
    q = (
        select(PMPlan)
        .options(selectinload(PMPlan.asset))
        .order_by(PMPlan.next_due_date)
    )
    if asset_id:
        q = q.where(PMPlan.asset_id == asset_id)
    if active_only:
        q = q.where(PMPlan.is_active == True)  # noqa: E712
    return list((await db.execute(q.offset(offset).limit(min(limit, 1000)))).scalars().all())


async def get_pm_plan(db: AsyncSession, plan_id: uuid.UUID) -> Optional[PMPlan]:
    result = await db.execute(
        select(PMPlan)
        .options(selectinload(PMPlan.asset))
        .where(PMPlan.id == plan_id)
    )
    return result.scalar_one_or_none()


async def create_pm_plan(db: AsyncSession, data: dict) -> PMPlan:
    plan = PMPlan(**data)
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def update_pm_plan(db: AsyncSession, plan: PMPlan, data: dict) -> PMPlan:
    for k, v in data.items():
        if v is not None:
            setattr(plan, k, v)
    await db.flush()
    await db.refresh(plan)
    return plan


# ── PM Work Orders ─────────────────────────────────────────────────────────────

async def list_work_orders(
    db: AsyncSession,
    plan_id: Optional[uuid.UUID] = None,
    status: Optional[PMStatus] = None,
    limit: int = 100,
) -> List[PMWorkOrder]:
    q = (
        select(PMWorkOrder)
        .options(
            selectinload(PMWorkOrder.plan).selectinload(PMPlan.asset),
        )
        .order_by(PMWorkOrder.scheduled_date.desc())
    )
    if plan_id:
        q = q.where(PMWorkOrder.plan_id == plan_id)
    if status:
        q = q.where(PMWorkOrder.status == status)
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_work_order(db: AsyncSession, wo_id: uuid.UUID) -> Optional[PMWorkOrder]:
    result = await db.execute(
        select(PMWorkOrder)
        .options(selectinload(PMWorkOrder.plan).selectinload(PMPlan.asset))
        .where(PMWorkOrder.id == wo_id)
    )
    return result.scalar_one_or_none()


async def create_work_order(db: AsyncSession, data: dict, wo_no: str) -> PMWorkOrder:
    wo = PMWorkOrder(**data, wo_no=wo_no)
    db.add(wo)
    await db.flush()
    await db.refresh(wo)
    return wo


async def complete_work_order(
    db: AsyncSession,
    wo: PMWorkOrder,
    data: dict,
    user_id: uuid.UUID,
) -> PMWorkOrder:
    from datetime import date as date_type
    wo.status = PMStatus.COMPLETED
    wo.completed_by_id = user_id
    for k, v in data.items():
        if v is not None:
            setattr(wo, k, v)
    await db.flush()
    # Update plan's last_completed_date and compute next_due_date
    plan_result = await db.execute(select(PMPlan).where(PMPlan.id == wo.plan_id).with_for_update())
    plan = plan_result.scalar_one_or_none()
    if plan:
        from datetime import timedelta
        today = date_type.today()
        plan.last_completed_date = today
        interval = _plan_interval_days(plan)
        plan.next_due_date = today + timedelta(days=interval)
    await db.flush()
    await db.refresh(wo)
    return wo


def _plan_interval_days(plan: PMPlan) -> int:
    if plan.interval_days:
        return plan.interval_days
    from app.models.maintenance import PMFrequency
    mapping = {
        PMFrequency.DAILY: 1,
        PMFrequency.WEEKLY: 7,
        PMFrequency.MONTHLY: 30,
        PMFrequency.QUARTERLY: 91,
        PMFrequency.BIANNUAL: 183,
        PMFrequency.ANNUAL: 365,
    }
    return mapping.get(plan.frequency, 30)


# ── Breakdowns ─────────────────────────────────────────────────────────────────

async def list_breakdowns(
    db: AsyncSession,
    asset_id: Optional[uuid.UUID] = None,
    status: Optional[BreakdownStatus] = None,
    limit: int = 200,
) -> List[BreakdownRecord]:
    q = (
        select(BreakdownRecord)
        .options(selectinload(BreakdownRecord.asset))
        .order_by(BreakdownRecord.start_time.desc())
    )
    if asset_id:
        q = q.where(BreakdownRecord.asset_id == asset_id)
    if status:
        q = q.where(BreakdownRecord.status == status)
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_breakdown(db: AsyncSession, bd_id: uuid.UUID) -> Optional[BreakdownRecord]:
    result = await db.execute(
        select(BreakdownRecord)
        .options(
            selectinload(BreakdownRecord.asset),
            selectinload(BreakdownRecord.spare_usages).selectinload(SparePartUsage.spare_part),
        )
        .where(BreakdownRecord.id == bd_id)
    )
    return result.scalar_one_or_none()


async def create_breakdown(
    db: AsyncSession, data: dict, user_id: uuid.UUID, bd_no: str
) -> BreakdownRecord:
    bd = BreakdownRecord(**data, breakdown_no=bd_no, reported_by_id=user_id)
    db.add(bd)
    # Mark asset as UNDER_MAINTENANCE
    asset_result = await db.execute(
        select(Asset).where(Asset.id == bd.asset_id).with_for_update()
    )
    asset = asset_result.scalar_one_or_none()
    if asset:
        asset.status = AssetStatus.UNDER_MAINTENANCE
    await db.flush()
    await db.refresh(bd)
    return bd


async def resolve_breakdown(
    db: AsyncSession, bd: BreakdownRecord, data: dict, user_id: uuid.UUID
) -> BreakdownRecord:
    from datetime import datetime, timezone
    bd.status = BreakdownStatus.RESOLVED
    bd.resolved_by_id = user_id
    for k, v in data.items():
        if v is not None:
            setattr(bd, k, v)
    # Auto-calculate downtime if end_time set but not downtime_minutes
    if bd.end_time and bd.start_time and not bd.downtime_minutes:
        delta = bd.end_time - bd.start_time
        bd.downtime_minutes = int(delta.total_seconds() / 60)
    # Restore asset to ACTIVE
    asset_result = await db.execute(
        select(Asset).where(Asset.id == bd.asset_id).with_for_update()
    )
    asset = asset_result.scalar_one_or_none()
    if asset and asset.status == AssetStatus.UNDER_MAINTENANCE:
        asset.status = AssetStatus.ACTIVE
    await db.flush()
    await db.refresh(bd)
    return bd


# ── Spare Parts ────────────────────────────────────────────────────────────────

async def list_spare_parts(
    db: AsyncSession,
    active_only: bool = True,
    low_stock: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> List[SparePart]:
    q = select(SparePart).order_by(SparePart.part_no)
    if active_only:
        q = q.where(SparePart.is_active == True)  # noqa: E712
    return list((await db.execute(q.offset(offset).limit(min(limit, 1000)))).scalars().all())


async def get_spare_part(db: AsyncSession, part_id: uuid.UUID) -> Optional[SparePart]:
    result = await db.execute(select(SparePart).where(SparePart.id == part_id))
    return result.scalar_one_or_none()


async def create_spare_part(db: AsyncSession, data: dict) -> SparePart:
    sp = SparePart(**data)
    db.add(sp)
    await db.flush()
    await db.refresh(sp)
    return sp


async def update_spare_part(db: AsyncSession, sp: SparePart, data: dict) -> SparePart:
    for k, v in data.items():
        if v is not None:
            setattr(sp, k, v)
    await db.flush()
    await db.refresh(sp)
    return sp


# ── Spare Part Usage ───────────────────────────────────────────────────────────

async def list_spare_usages(
    db: AsyncSession,
    asset_id: Optional[uuid.UUID] = None,
    breakdown_id: Optional[uuid.UUID] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[SparePartUsage]:
    q = (
        select(SparePartUsage)
        .options(
            selectinload(SparePartUsage.spare_part),
            selectinload(SparePartUsage.asset),
        )
        .order_by(SparePartUsage.created_at.desc())
    )
    if asset_id:
        q = q.where(SparePartUsage.asset_id == asset_id)
    if breakdown_id:
        q = q.where(SparePartUsage.breakdown_id == breakdown_id)
    return list((await db.execute(q.offset(offset).limit(min(limit, 1000)))).scalars().all())


async def record_spare_usage(
    db: AsyncSession, data: dict, user_id: uuid.UUID
) -> SparePartUsage:
    usage = SparePartUsage(**data, used_by_id=user_id)
    db.add(usage)
    await db.flush()
    # Deduct stock
    sp_result = await db.execute(
        select(SparePart).where(SparePart.id == usage.spare_part_id).with_for_update()
    )
    sp = sp_result.scalar_one_or_none()
    if sp:
        sp.current_stock = max(0, float(sp.current_stock) - float(usage.quantity_used))
    await db.flush()
    await db.refresh(usage)
    return usage
