"""
MPS Service — core orchestration.

Responsibilities:
- Plan CRUD
- Generate MPS lines from MRP results
- Approve / Release plans
- Dashboard aggregation
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSCampaign, MPSCapacitySlot,
    MPSStatus, MPSFeasibilityStatus, MPSPlanningMode,
)
from app.models.mrp import MRPRun, MRPResult, MRPRunStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import Recipe
from app.models.master import Product, Warehouse
from app.schemas.mps import (
    MPSPlanCreate, MPSLineUpdate, GenerateFromMRPRequest,
    MPSDashboard, MPSPlanSummary,
)


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


def _seq(prefix: str, n: int) -> str:
    return f"{prefix}-{n:06d}"


async def _next_seq(db: AsyncSession, prefix: str, col) -> str:
    result = await db.execute(
        select(func.count()).select_from(MPSPlan if "MPS-" in prefix else MPSLine)
    )
    count = (result.scalar() or 0) + 1
    return _seq(prefix, count)


# ── Plan CRUD ─────────────────────────────────────────────────────────────────

async def create_mps_plan(
    db: AsyncSession,
    data: MPSPlanCreate,
    user_id: uuid.UUID,
) -> MPSPlan:
    count_result = await db.execute(select(func.count()).select_from(MPSPlan))
    n = (count_result.scalar() or 0) + 1
    plan = MPSPlan(
        plan_no=f"MPS-{n:06d}",
        plan_name=data.plan_name,
        plant_code=data.plant_code,
        planning_horizon_days=data.planning_horizon_days,
        start_date=data.start_date,
        end_date=data.end_date,
        planning_mode=data.planning_mode,
        capacity_mode=data.capacity_mode,
        mrp_run_id=data.mrp_run_id,
        created_by_id=user_id,
        notes=data.notes,
    )
    db.add(plan)
    await db.flush()
    return plan


async def get_mps_plan(db: AsyncSession, mps_id: uuid.UUID) -> Optional[MPSPlan]:
    result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    return result.scalar_one_or_none()


async def list_mps_plans(db: AsyncSession, limit: int = 50, offset: int = 0):
    result = await db.execute(
        select(MPSPlan)
        .order_by(MPSPlan.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_mps_lines(db: AsyncSession, mps_id: uuid.UUID):
    result = await db.execute(
        select(MPSLine)
        .where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.priority_score.desc(), MPSLine.period_start)
    )
    lines = result.scalars().all()
    # Enrich with product names
    for line in lines:
        if line.product:
            line.product_name = line.product.name
            line.product_code = getattr(line.product, "code", None) or getattr(line.product, "sku", None) or ""
        if line.work_center:
            line.work_center_name = line.work_center.name
    return lines


async def update_mps_line(
    db: AsyncSession,
    line_id: uuid.UUID,
    data: MPSLineUpdate,
) -> Optional[MPSLine]:
    result = await db.execute(select(MPSLine).where(MPSLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return None
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(line, k, v)
    line.is_locked = True  # any manual update locks the line
    await db.flush()
    return line


# ── Generate from MRP ─────────────────────────────────────────────────────────

async def generate_mps_from_mrp(
    db: AsyncSession,
    mps_id: uuid.UUID,
    req: GenerateFromMRPRequest,
) -> int:
    """Pull MRP results and create MPS lines grouped by period."""
    plan_result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Can only generate lines for DRAFT plans")

    # Load MRP results for this run
    mrp_q = await db.execute(
        select(MRPResult)
        .where(
            MRPResult.mrp_run_id == req.mrp_run_id,
            MRPResult.net_requirement_qty > 0,
        )
        .order_by(MRPResult.product_id)
    )
    mrp_results = mrp_q.scalars().all()

    if not mrp_results:
        return 0

    # Delete existing non-locked lines
    existing_q = await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked == False)
    )
    for old in existing_q.scalars().all():
        await db.delete(old)
    await db.flush()

    line_count_q = await db.execute(select(func.count()).select_from(MPSLine))
    seq = (line_count_q.scalar() or 0) + 1

    period_days = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}.get(req.period_type, 7)
    created = 0

    for mrp in mrp_results:
        # Divide horizon into periods
        cursor = plan.start_date
        while cursor < plan.end_date:
            p_end = min(cursor + timedelta(days=period_days - 1), plan.end_date)

            # Pro-rate net_requirement across periods
            horizon = max((plan.end_date - plan.start_date).days, 1)
            period_fraction = Decimal(str(period_days)) / Decimal(str(horizon))
            net_req = _R(_D(mrp.net_requirement_qty) * period_fraction)

            if net_req <= 0:
                cursor = p_end + timedelta(days=1)
                continue

            # Snap to batch size
            planned_qty = net_req
            num_batches = 1
            if req.respect_batch_sizes and req.default_batch_qty and req.default_batch_qty > 0:
                import math
                num_batches = max(1, math.ceil(float(net_req) / float(req.default_batch_qty)))
                planned_qty = _R(Decimal(str(num_batches)) * _D(req.default_batch_qty))

            if req.period_type == "WEEKLY":
                period_label = f"{cursor.year}-W{cursor.isocalendar()[1]:02d}"
            elif req.period_type == "MONTHLY":
                period_label = f"{cursor.year}-{cursor.month:02d}"
            else:
                period_label = cursor.isoformat()

            line = MPSLine(
                line_no=f"MPSL-{seq:07d}",
                mps_id=mps_id,
                product_id=mrp.product_id,
                mrp_result_id=mrp.id,
                period_label=period_label,
                period_start=cursor,
                period_end=p_end,
                confirmed_demand_qty=_D(mrp.so_demand_qty) * period_fraction,
                forecast_qty=_D(mrp.forecast_demand_qty) * period_fraction,
                safety_stock_qty=_D(mrp.safety_stock_qty),
                net_requirement_qty=net_req,
                planned_production_qty=planned_qty,
                batch_size_qty=req.default_batch_qty,
                num_batches=num_batches,
                planned_start_date=cursor,
                planned_end_date=p_end,
                feasibility_status=MPSFeasibilityStatus.PENDING,
                priority_score=_D("50"),
            )
            db.add(line)
            seq += 1
            created += 1
            cursor = p_end + timedelta(days=1)

    await db.flush()

    # Update plan counters
    await _refresh_plan_counters(db, mps_id)
    plan.mrp_run_id = req.mrp_run_id
    await db.flush()

    return created


# ── Approve / Release ─────────────────────────────────────────────────────────

async def approve_mps_plan(
    db: AsyncSession,
    mps_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MPSPlan:
    result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Only DRAFT plans can be approved")
    plan.status = MPSStatus.APPROVED
    plan.approved_by_id = user_id
    plan.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return plan


async def release_mps_plan(
    db: AsyncSession,
    mps_id: uuid.UUID,
    user_id: uuid.UUID,
    target_warehouse_id: uuid.UUID,
) -> dict:
    """Release: create ProductionOrders for all FEASIBLE non-released lines."""
    plan_result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status not in (MPSStatus.APPROVED, MPSStatus.DRAFT):
        raise ValueError("Plan must be APPROVED before release")

    lines_result = await db.execute(
        select(MPSLine).where(
            MPSLine.mps_id == mps_id,
            MPSLine.production_order_id == None,
            MPSLine.planned_production_qty > 0,
        )
    )
    lines = lines_result.scalars().all()

    po_count_q = await db.execute(select(func.count()).select_from(ProductionOrder))
    po_seq = (po_count_q.scalar() or 0) + 1
    created = 0

    for line in lines:
        # Need a recipe — get active recipe for product
        recipe_q = await db.execute(
            select(Recipe).where(
                Recipe.product_id == line.product_id,
                Recipe.is_active == True,
            ).limit(1)
        )
        recipe = recipe_q.scalar_one_or_none()
        if not recipe:
            line.remarks = (line.remarks or "") + " [no active recipe — skipped]"
            continue

        start_dt = datetime.combine(
            line.planned_start_date or plan.start_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(
            line.planned_end_date or plan.end_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        po = ProductionOrder(
            order_no=f"PO-MPS-{po_seq:06d}",
            product_id=line.product_id,
            recipe_id=recipe.id,
            planned_quantity=line.planned_production_qty,
            uom="KG",
            status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=target_warehouse_id,
            scheduled_start=start_dt,
            scheduled_end=end_dt,
            created_by=user_id,
            notes=f"Released from MPS {plan.plan_no} line {line.line_no}",
        )
        db.add(po)
        await db.flush()

        line.production_order_id = po.id
        po_seq += 1
        created += 1

    plan.status = MPSStatus.RELEASED
    plan.released_at = datetime.now(timezone.utc)
    await db.flush()
    return {"released_orders": created, "skipped": len(lines) - created}


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_mps_dashboard(db: AsyncSession) -> MPSDashboard:
    active_q = await db.execute(
        select(func.count()).select_from(MPSPlan).where(
            MPSPlan.status.in_([MPSStatus.DRAFT, MPSStatus.APPROVED])
        )
    )
    active_plans = active_q.scalar() or 0

    lines_q = await db.execute(
        select(
            func.count().label("total"),
            func.sum(
                func.cast(MPSLine.feasibility_status == MPSFeasibilityStatus.OVERLOADED, type_=None)
            ).label("over"),
            func.sum(
                func.cast(MPSLine.feasibility_status == MPSFeasibilityStatus.FEASIBLE, type_=None)
            ).label("feas"),
        ).select_from(MPSLine)
    )
    row = lines_q.first()
    total_lines = row.total or 0
    overloaded_lines = int(row.over or 0)
    feasible_lines = int(row.feas or 0)

    from app.models.mps import MPSAIRecommendation, MPSRecStatus
    ai_q = await db.execute(
        select(func.count()).select_from(MPSAIRecommendation).where(
            MPSAIRecommendation.status == MPSRecStatus.PENDING
        )
    )
    pending_ai = ai_q.scalar() or 0

    approval_q = await db.execute(
        select(func.count()).select_from(MPSPlan).where(MPSPlan.status == MPSStatus.DRAFT)
    )
    pending_approvals = approval_q.scalar() or 0

    # Overload alerts — top 10 overloaded lines
    overload_q = await db.execute(
        select(MPSLine)
        .where(MPSLine.feasibility_status == MPSFeasibilityStatus.OVERLOADED)
        .order_by(MPSLine.overload_hours.desc())
        .limit(10)
    )
    overload_lines = overload_q.scalars().all()
    overload_alerts = [
        {
            "line_id": str(l.id),
            "line_no": l.line_no,
            "product_id": str(l.product_id),
            "overload_hours": float(l.overload_hours or 0),
            "period_start": str(l.period_start),
        }
        for l in overload_lines
    ]

    plans_q = await db.execute(
        select(MPSPlan).order_by(MPSPlan.created_at.desc()).limit(5)
    )
    recent_plans = plans_q.scalars().all()

    return MPSDashboard(
        active_plans=active_plans,
        total_lines=total_lines,
        overloaded_lines=overloaded_lines,
        feasible_lines=feasible_lines,
        pending_ai_recs=pending_ai,
        pending_approvals=pending_approvals,
        overload_alerts=overload_alerts,
        recent_plans=recent_plans,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _refresh_plan_counters(db: AsyncSession, mps_id: uuid.UUID) -> None:
    q = await db.execute(
        select(
            func.count().label("total"),
            func.sum(
                func.cast(MPSLine.feasibility_status == MPSFeasibilityStatus.OVERLOADED, type_=None)
            ).label("over"),
            func.sum(
                func.cast(MPSLine.feasibility_status == MPSFeasibilityStatus.FEASIBLE, type_=None)
            ).label("feas"),
            func.sum(
                func.cast(MPSLine.is_locked == True, type_=None)
            ).label("locked"),
        ).select_from(MPSLine).where(MPSLine.mps_id == mps_id)
    )
    row = q.first()
    plan_q = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_q.scalar_one_or_none()
    if plan:
        plan.total_lines = row.total or 0
        plan.overloaded_lines = int(row.over or 0)
        plan.feasible_lines = int(row.feas or 0)
        plan.locked_lines = int(row.locked or 0)
