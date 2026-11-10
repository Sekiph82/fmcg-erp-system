from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import (
    Asset, PMPlan, PMWorkOrder, BreakdownRecord, SparePart, SparePartUsage,
    PMPlanSparePartRequirement, PMWorkOrderSparePartReservation,
    AssetStatus, PMStatus, BreakdownStatus,
)


class SparePartAvailabilityError(Exception):
    def __init__(self, detail: dict):
        self.detail = detail
        super().__init__(detail.get("message", "Spare-part availability check failed"))


ACTIVE_PM_STATUSES = (PMStatus.PENDING, PMStatus.IN_PROGRESS, PMStatus.OVERDUE)


async def _active_reserved_quantities(
    db: AsyncSession, spare_part_ids: Optional[list[uuid.UUID]] = None
) -> dict[uuid.UUID, Decimal]:
    query = (
        select(
            PMWorkOrderSparePartReservation.spare_part_id,
            func.sum(
                PMWorkOrderSparePartReservation.quantity_reserved
                - PMWorkOrderSparePartReservation.quantity_consumed
            ),
        )
        .join(PMWorkOrder, PMWorkOrder.id == PMWorkOrderSparePartReservation.work_order_id)
        .where(PMWorkOrder.status.in_(ACTIVE_PM_STATUSES))
        .group_by(PMWorkOrderSparePartReservation.spare_part_id)
    )
    if spare_part_ids is not None:
        if not spare_part_ids:
            return {}
        query = query.where(PMWorkOrderSparePartReservation.spare_part_id.in_(spare_part_ids))
    return {
        part_id: Decimal(str(quantity or 0))
        for part_id, quantity in (await db.execute(query)).all()
    }


async def get_plan_spare_part_requirements(
    db: AsyncSession, plan_id: uuid.UUID
) -> list[dict]:
    reserved = (
        select(
            PMWorkOrderSparePartReservation.spare_part_id.label("spare_part_id"),
            func.sum(
                PMWorkOrderSparePartReservation.quantity_reserved
                - PMWorkOrderSparePartReservation.quantity_consumed
            ).label("reserved_quantity"),
        )
        .join(PMWorkOrder, PMWorkOrder.id == PMWorkOrderSparePartReservation.work_order_id)
        .where(PMWorkOrder.status.in_(ACTIVE_PM_STATUSES))
        .group_by(PMWorkOrderSparePartReservation.spare_part_id)
        .subquery()
    )
    result = await db.execute(
        select(
            PMPlanSparePartRequirement,
            SparePart,
            func.coalesce(reserved.c.reserved_quantity, 0),
        )
        .join(SparePart, SparePart.id == PMPlanSparePartRequirement.spare_part_id)
        .outerjoin(reserved, reserved.c.spare_part_id == SparePart.id)
        .where(PMPlanSparePartRequirement.plan_id == plan_id)
        .order_by(SparePart.part_no, SparePart.id)
    )
    rows = []
    for requirement, part, reserved_quantity in result.all():
        reserved_value = Decimal(str(reserved_quantity or 0))
        available = Decimal(str(part.current_stock)) - reserved_value
        required = Decimal(str(requirement.quantity_required))
        rows.append({
            "spare_part_id": str(part.id),
            "part_no": part.part_no,
            "name": part.name,
            "unit": part.unit,
            "is_active": part.is_active,
            "quantity_required": float(required),
            "current_stock": float(part.current_stock),
            "reserved_quantity": float(reserved_value),
            "available_quantity": float(available),
            "is_available": part.is_active and available >= required,
        })
    return rows


async def replace_plan_spare_part_requirements(
    db: AsyncSession, plan_id: uuid.UUID, items: list[dict]
) -> list[dict]:
    plan = await db.execute(select(PMPlan.id).where(PMPlan.id == plan_id).with_for_update())
    if plan.scalar_one_or_none() is None:
        raise LookupError("PM Plan not found")

    normalized_items = [
        {
            "spare_part_id": item["spare_part_id"]
            if isinstance(item["spare_part_id"], uuid.UUID)
            else uuid.UUID(str(item["spare_part_id"])),
            "quantity_required": Decimal(str(item["quantity_required"])),
        }
        for item in items
    ]
    part_ids = sorted({item["spare_part_id"] for item in normalized_items}, key=str)
    parts = {}
    if part_ids:
        parts = {
            part.id: part
            for part in (await db.execute(
                select(SparePart).where(SparePart.id.in_(part_ids)).order_by(SparePart.id).with_for_update()
            )).scalars().all()
        }
    unavailable = [
        str(part_id) for part_id in part_ids
        if part_id not in parts or not parts[part_id].is_active
    ]
    if unavailable:
        raise SparePartAvailabilityError({
            "message": "Requirements must reference existing active spare parts.",
            "unavailable_part_ids": unavailable,
        })

    await db.execute(delete(PMPlanSparePartRequirement).where(PMPlanSparePartRequirement.plan_id == plan_id))
    db.add_all([
        PMPlanSparePartRequirement(
            plan_id=plan_id,
            spare_part_id=item["spare_part_id"],
            quantity_required=item["quantity_required"],
        )
        for item in normalized_items
    ])
    await db.flush()
    return await get_plan_spare_part_requirements(db, plan_id)


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
        if v is not None or k == "work_center_id":
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
    plan_result = await db.execute(
        select(PMPlan).where(PMPlan.id == data["plan_id"]).with_for_update()
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise LookupError("PM Plan not found")

    requirements = list((await db.execute(
        select(PMPlanSparePartRequirement)
        .where(PMPlanSparePartRequirement.plan_id == plan.id)
        .order_by(PMPlanSparePartRequirement.spare_part_id)
    )).scalars().all())
    required_part_ids = [requirement.spare_part_id for requirement in requirements]
    parts = {}
    if required_part_ids:
        parts = {
            part.id: part
            for part in (await db.execute(
                select(SparePart)
                .where(SparePart.id.in_(required_part_ids))
                .order_by(SparePart.id)
                .with_for_update()
            )).scalars().all()
        }
    reserved = await _active_reserved_quantities(db, required_part_ids)
    shortages = []
    for requirement in requirements:
        part = parts.get(requirement.spare_part_id)
        if part is None:
            continue
        available = Decimal(str(part.current_stock)) - reserved.get(part.id, Decimal("0"))
        required = Decimal(str(requirement.quantity_required))
        if not part.is_active or available < required:
            shortages.append({
                "spare_part_id": str(part.id),
                "part_no": part.part_no,
                "name": part.name,
                "unit": part.unit,
                "quantity_required": float(required),
                "available_quantity": float(available),
                "is_active": part.is_active,
            })
    if shortages:
        raise SparePartAvailabilityError({
            "message": "Work order was not scheduled because required spare parts are unavailable.",
            "items": shortages,
        })

    wo = PMWorkOrder(**data, wo_no=wo_no, status=PMStatus.PENDING)
    db.add(wo)
    await db.flush()
    db.add_all([
        PMWorkOrderSparePartReservation(
            work_order_id=wo.id,
            spare_part_id=requirement.spare_part_id,
            quantity_reserved=requirement.quantity_required,
            quantity_consumed=Decimal("0"),
        )
        for requirement in requirements
    ])
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
    locked_result = await db.execute(
        select(SparePart).where(SparePart.id == sp.id).with_for_update()
    )
    sp = locked_result.scalar_one_or_none()
    if sp is None:
        raise LookupError("Spare part not found")
    has_requirement = await db.scalar(
        select(func.count())
        .select_from(PMPlanSparePartRequirement)
        .where(PMPlanSparePartRequirement.spare_part_id == sp.id)
    )
    reserved = (await _active_reserved_quantities(db, [sp.id])).get(sp.id, Decimal("0"))
    if data.get("current_stock") is not None:
        new_stock = Decimal(str(data["current_stock"]))
        if new_stock < reserved:
            raise SparePartAvailabilityError({
                "message": "Stock cannot be reduced below the quantity reserved for active PM work orders.",
                "spare_part_id": str(sp.id),
                "requested_stock": float(new_stock),
                "reserved_quantity": float(reserved),
            })
    if data.get("is_active") is False and (reserved > 0 or has_requirement):
        raise SparePartAvailabilityError({
            "message": "Remove PM plan requirements and release active work-order reservations before deactivating this spare part.",
            "spare_part_id": str(sp.id),
            "reserved_quantity": float(reserved),
        })
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
    quantity = Decimal(str(data["quantity_used"]))
    if quantity <= 0:
        raise SparePartAvailabilityError({"message": "quantity_used must be greater than zero."})

    work_order = None
    own_reservation = None
    if data.get("pm_work_order_id"):
        work_order_result = await db.execute(
            select(PMWorkOrder).where(PMWorkOrder.id == data["pm_work_order_id"]).with_for_update()
        )
        work_order = work_order_result.scalar_one_or_none()
        if work_order is None:
            raise LookupError("PM work order not found")
        if work_order.status not in ACTIVE_PM_STATUSES:
            raise SparePartAvailabilityError({
                "message": "Spare parts can only be recorded against an active PM work order.",
                "work_order_id": str(work_order.id),
                "status": work_order.status.value,
            })
        plan = await db.get(PMPlan, work_order.plan_id)
        if plan is None or plan.asset_id != data["asset_id"]:
            raise SparePartAvailabilityError({
                "message": "The supplied asset does not match the PM work order asset.",
                "work_order_id": str(work_order.id),
            })

    if data.get("breakdown_id"):
        breakdown = await db.get(BreakdownRecord, data["breakdown_id"])
        if breakdown is None:
            raise LookupError("Breakdown not found")
        if breakdown.asset_id != data["asset_id"]:
            raise SparePartAvailabilityError({
                "message": "The supplied asset does not match the breakdown asset.",
                "breakdown_id": str(breakdown.id),
            })

    sp_result = await db.execute(
        select(SparePart).where(SparePart.id == data["spare_part_id"]).with_for_update()
    )
    sp = sp_result.scalar_one_or_none()
    if sp is None:
        raise LookupError("Spare part not found")
    reserved = (await _active_reserved_quantities(db, [sp.id])).get(sp.id, Decimal("0"))
    free_stock = Decimal(str(sp.current_stock)) - reserved

    if work_order is not None:
        reservation_result = await db.execute(
            select(PMWorkOrderSparePartReservation)
            .where(
                PMWorkOrderSparePartReservation.work_order_id == work_order.id,
                PMWorkOrderSparePartReservation.spare_part_id == sp.id,
            )
            .with_for_update()
        )
        own_reservation = reservation_result.scalar_one_or_none()
    own_remaining = (
        Decimal(str(own_reservation.quantity_reserved)) - Decimal(str(own_reservation.quantity_consumed))
        if own_reservation is not None else Decimal("0")
    )
    available_to_consume = max(Decimal("0"), free_stock) + own_remaining
    if quantity > available_to_consume:
        raise SparePartAvailabilityError({
            "message": "Spare-part usage exceeds unreserved stock and the work order's own reservation.",
            "spare_part_id": str(sp.id),
            "available_to_consume": float(available_to_consume),
            "quantity_requested": float(quantity),
        })

    reserved_consumption = min(quantity, own_remaining)
    if own_reservation is not None and reserved_consumption > 0:
        own_reservation.quantity_consumed = Decimal(str(own_reservation.quantity_consumed)) + reserved_consumption

    usage = SparePartUsage(**data, used_by_id=user_id)
    db.add(usage)
    sp.current_stock = Decimal(str(sp.current_stock)) - quantity
    await db.flush()
    await db.refresh(usage)
    return usage
