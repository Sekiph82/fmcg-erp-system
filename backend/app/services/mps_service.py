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

from sqlalchemy import select, func, and_, update, cast, Integer, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mps import (
    MPSPlan, MPSLine, MPSCampaign, MPSCapacitySlot,
    MPSStatus, MPSFeasibilityStatus, MPSPlanningMode,
)
from app.models.mrp import MRPRun, MRPResult, MRPRunStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import Recipe, RecipeStatus
from app.services.recipe_governance import recipe_precedence_ordering, recipe_required_date
from app.models.master import Product, UnitOfMeasure, Warehouse
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
    return f"{prefix}{n:07d}" if prefix == "MPSL-" else f"{prefix}{n:06d}"


def _phase_periods(start_date: date, end_date: date, period_days: int) -> list:
    """Partition [start_date, end_date] into consecutive period_days-sized
    windows, returning (period_start, period_end, fraction_of_total) tuples.
    Each fraction is the period's own actual day count over the total
    horizon day count, so fractions sum to exactly 1 and phased quantities
    conserve the source total regardless of a partial final period —
    see M20.S01.T001 F6.
    """
    total_days = max((end_date - start_date).days + 1, 1)
    periods = []
    cursor = start_date
    while cursor <= end_date:
        p_end = min(cursor + timedelta(days=period_days - 1), end_date)
        actual_days = (p_end - cursor).days + 1
        fraction = Decimal(str(actual_days)) / Decimal(str(total_days))
        periods.append((cursor, p_end, fraction))
        cursor = p_end + timedelta(days=1)
    return periods


async def _next_seq(db: AsyncSession, prefix: str, col) -> str:
    sequence_name = {
        "MPS-": "mps_plan_no_seq",
        "MPSL-": "mps_line_no_seq",
    }.get(prefix)
    if sequence_name is None:
        raise ValueError(f"Unsupported MPS sequence prefix: {prefix}")

    if db.get_bind().dialect.name == "postgresql":
        result = await db.execute(
            text("SELECT nextval(CAST(:sequence_name AS regclass))"),
            {"sequence_name": sequence_name},
        )
        number = result.scalar_one()
    else:
        result = await db.execute(select(col))
        largest = 0
        for value in result.scalars().all():
            if isinstance(value, str) and value.startswith(prefix):
                suffix = value[len(prefix):]
                if suffix.isdigit():
                    largest = max(largest, int(suffix))
        number = largest + 1
    return _seq(prefix, number)


# ── Plan CRUD ─────────────────────────────────────────────────────────────────

async def create_mps_plan(
    db: AsyncSession,
    data: MPSPlanCreate,
    user_id: uuid.UUID,
) -> MPSPlan:
    if data.end_date < data.start_date:
        raise ValueError("MPS plan end date must be on or after start date")
    if data.planning_horizon_days < 1:
        raise ValueError("MPS planning horizon must be at least one day")
    if data.mrp_run_id:
        source_run = await db.get(MRPRun, data.mrp_run_id)
        if source_run is None or source_run.status != MRPRunStatus.COMPLETED:
            raise ValueError("MPS source MRP run must exist and be COMPLETED")
    plan = MPSPlan(
        plan_no=await _next_seq(db, "MPS-", MPSPlan.plan_no),
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


async def list_mps_plans(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    *,
    warehouse_ids: list[uuid.UUID] | None = None,
):
    query = select(MPSPlan)
    if warehouse_ids is not None:
        if not warehouse_ids:
            return []
        query = query.join(MRPRun, MPSPlan.mrp_run_id == MRPRun.id).where(
            MRPRun.warehouse_id.in_(warehouse_ids)
        )
    result = await db.execute(
        query
        .order_by(MPSPlan.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_mps_lines(db: AsyncSession, mps_id: uuid.UUID):
    result = await db.execute(
        select(MPSLine)
        .options(selectinload(MPSLine.product), selectinload(MPSLine.work_center))
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
    mps_id: uuid.UUID,
    line_id: uuid.UUID,
    data: MPSLineUpdate,
    user_id: Optional[uuid.UUID] = None,
) -> Optional[MPSLine]:
    # Match regeneration/approval lock order so a manual lock or edit cannot
    # race a regeneration that is replacing the plan's unlocked lines.
    plan_result = await db.execute(
        select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update()
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        return None
    if plan.status not in {MPSStatus.DRAFT, MPSStatus.APPROVED}:
        raise ValueError("Only unreleased DRAFT or APPROVED MPS plans can be edited")
    result = await db.execute(
        select(MPSLine).where(
            MPSLine.id == line_id,
            MPSLine.mps_id == mps_id,
        ).with_for_update()
    )
    line = result.scalar_one_or_none()
    if not line:
        return None
    updates = data.model_dump(exclude_unset=True)
    clear_hold = bool(updates.pop("clear_hold", False))
    if not updates and not clear_hold:
        raise ValueError("At least one editable MPS line field must be provided")
    if line.feasibility_status == MPSFeasibilityStatus.ON_HOLD and not clear_hold:
        raise ValueError("ON_HOLD MPS lines must be explicitly cleared before editing")
    if clear_hold and line.feasibility_status != MPSFeasibilityStatus.ON_HOLD:
        raise ValueError("Only an ON_HOLD MPS line can be explicitly cleared")
    if clear_hold and user_id is None:
        raise ValueError("An authenticated editor is required to clear an MPS line hold")
    if not clear_hold and all(getattr(line, key) == value for key, value in updates.items()):
        return line
    reopened_approval = False
    actor = None
    if plan.status == MPSStatus.APPROVED:
        if plan.released_at is not None:
            raise ValueError("An approved plan with release history cannot be reopened for editing")
        linked_count = await db.scalar(
            select(func.count()).select_from(MPSLine).where(
                MPSLine.mps_id == mps_id,
                MPSLine.production_order_id.is_not(None),
            )
        )
        if linked_count:
            raise ValueError("An approved plan with production-order links cannot be reopened for editing")
        if user_id is None:
            raise ValueError("An authenticated editor is required to reopen an approved MPS plan")

        from app.models.audit_log import AuditLog
        from app.models.user import User

        actor = await db.get(User, user_id)
        if actor is None:
            raise ValueError("Authenticated editor no longer exists")
        previous_approval = {
            "status": MPSStatus.APPROVED.value,
            "approved_by_id": str(plan.approved_by_id) if plan.approved_by_id else None,
            "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        }
        plan.status = MPSStatus.DRAFT
        plan.approved_by_id = None
        plan.approved_at = None
        reopened_approval = True
        db.add(AuditLog(
            actor_id=user_id,
            actor_email=actor.email,
            actor_name=actor.full_name,
            event_type="MPS_PLAN_REOPENED_FOR_EDIT",
            module="mps",
            target_type="mps_plan",
            target_id=str(plan.id),
            target_name=plan.plan_no,
            before_value=previous_approval,
            after_value={"status": MPSStatus.DRAFT.value},
            details={
                "reason": "A planner edit invalidates the prior approval; reapproval is required before release.",
                "line_id": str(line_id),
            },
        ))
    if clear_hold:
        from app.models.audit_log import AuditLog
        from app.models.user import User

        if actor is None:
            actor = await db.get(User, user_id)
        if actor is None:
            raise ValueError("Authenticated editor no longer exists")
        db.add(AuditLog(
            actor_id=user_id,
            actor_email=actor.email,
            actor_name=actor.full_name,
            event_type="MPS_LINE_HOLD_CLEARED",
            module="mps",
            target_type="mps_line",
            target_id=str(line.id),
            target_name=line.line_no,
            before_value={
                "feasibility_status": MPSFeasibilityStatus.ON_HOLD.value,
                "is_locked": bool(line.is_locked),
            },
            after_value={"feasibility_status": MPSFeasibilityStatus.PENDING.value, "is_locked": False},
            details={
                "plan_id": str(plan.id),
                "reason": "Authenticated planner explicitly cleared the hold; feasibility must be recalculated before approval.",
            },
        ))
        line.feasibility_status = MPSFeasibilityStatus.PENDING
        line.is_locked = False
    for k, v in updates.items():
        setattr(line, k, v)
    # A post-approval repair must be recalculated before it can be approved
    # again, so keep that edited line eligible for the engine. Draft edits
    # retain the existing planner-lock behavior.
    if not clear_hold:
        line.is_locked = (
            line.feasibility_status == MPSFeasibilityStatus.ON_HOLD
            if reopened_approval else True
        )
    await db.flush()
    return line


# ── Generate from MRP ─────────────────────────────────────────────────────────

async def generate_mps_from_mrp(
    db: AsyncSession,
    mps_id: uuid.UUID,
    req: GenerateFromMRPRequest,
) -> int:
    """Pull MRP results and create MPS lines grouped by period."""
    # Serialize regeneration with approval/release, which lock the same plan
    # row before inspecting or changing its lines.
    plan_result = await db.execute(
        select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update()
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Can only generate lines for DRAFT plans")
    # A plan already tied to one MRP run must not silently pick up an
    # unrelated run on a later (re)generation call. MPSPlan carries no
    # warehouse/company/branch FK to cross-check against MRPRun.warehouse_id
    # (only a free-text plant_code with no relation to it), so run identity
    # is the strongest context-lineage check the current schema supports —
    # see M20.S01.T001 V02 F-V01-002. Checked before the MRP run lookup
    # since it needs no query.
    if plan.mrp_run_id is not None and plan.mrp_run_id != req.mrp_run_id:
        raise ValueError(
            "Plan is already linked to a different MRP run "
            f"({plan.mrp_run_id}); cannot attach unrelated run {req.mrp_run_id}"
        )

    mrp_run_result = await db.execute(select(MRPRun).where(MRPRun.id == req.mrp_run_id))
    mrp_run = mrp_run_result.scalar_one_or_none()
    if not mrp_run:
        raise ValueError("MRP run not found")
    if mrp_run.status != MRPRunStatus.COMPLETED:
        raise ValueError(f"MRP run must be COMPLETED (current status: {mrp_run.status})")
    # Record the source even for zero-demand runs so the plan cannot later be
    # rebound to a different MRP run after an empty regeneration.
    plan.mrp_run_id = req.mrp_run_id

    # Load MRP results for this run
    mrp_q = await db.execute(
        select(MRPResult)
        .where(
            MRPResult.run_id == req.mrp_run_id,
            MRPResult.net_requirement_qty > 0,
        )
        .order_by(MRPResult.product_id)
    )
    mrp_results = mrp_q.scalars().all()

    # Delete existing non-locked lines
    existing_q = await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked == False)
    )
    for old in existing_q.scalars().all():
        await db.delete(old)
    await db.flush()

    if not mrp_results:
        await _refresh_plan_counters(db, mps_id)
        return 0

    period_days = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}.get(req.period_type, 7)
    created = 0

    periods = _phase_periods(plan.start_date, plan.end_date, period_days)

    for mrp in mrp_results:
        for cursor, p_end, period_fraction in periods:
            net_req = _R(_D(mrp.net_requirement_qty) * period_fraction)

            if net_req <= 0:
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
                line_no=await _next_seq(db, "MPSL-", MPSLine.line_no),
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
            created += 1

    await db.flush()

    # Update plan counters
    await _refresh_plan_counters(db, mps_id)
    await db.flush()

    return created


# ── Approve / Release ─────────────────────────────────────────────────────────

async def approve_mps_plan(
    db: AsyncSession,
    mps_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MPSPlan:
    from app.models.audit_log import AuditLog
    from app.models.user import User

    result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())
    plan = result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Only DRAFT plans can be approved")
    lines = (await db.execute(select(MPSLine).where(MPSLine.mps_id == mps_id))).scalars().all()
    release_lines = [line for line in lines if _D(line.planned_production_qty) > 0]
    if not release_lines:
        raise ValueError("MPS plan must contain at least one positive production line before approval")
    blocked = [line.line_no for line in release_lines if line.feasibility_status != MPSFeasibilityStatus.FEASIBLE]
    if blocked:
        raise ValueError("Every positive production line must be FEASIBLE before approval; blocked lines: " + ", ".join(blocked[:10]))
    if not plan.mrp_run_id:
        raise ValueError("MPS plan must be linked to its source MRP run before approval")
    source_run = await db.get(MRPRun, plan.mrp_run_id)
    if source_run is None or source_run.status != MRPRunStatus.COMPLETED or not source_run.warehouse_id:
        raise ValueError("Approval requires a COMPLETED MRP run with a warehouse scope")
    actor = await db.get(User, user_id)
    if actor is None:
        raise ValueError("Authenticated approver no longer exists")
    before = {"status": str(getattr(plan.status, "value", plan.status)), "approved_by_id": str(plan.approved_by_id) if plan.approved_by_id else None}
    plan.status = MPSStatus.APPROVED
    plan.approved_by_id = user_id
    plan.approved_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        actor_id=user_id, actor_email=actor.email, actor_name=actor.full_name,
        event_type="MPS_PLAN_APPROVED", module="mps", target_type="mps_plan",
        target_id=str(plan.id), target_name=plan.plan_no,
        before_value=before,
        after_value={"status": "APPROVED", "approved_by_id": str(user_id), "approved_at": plan.approved_at.isoformat()},
        details={"line_count": len(lines), "release_line_count": len(release_lines), "warehouse_id": str(source_run.warehouse_id)},
    ))
    await db.flush()
    return plan


async def _select_release_recipe(db: AsyncSession, product_id: uuid.UUID, as_of: date) -> Optional[Recipe]:
    """Deterministic recipe selection for release: the strongest lifecycle
    contract the current Recipe model supports (status == APPROVED, active,
    within its effective date window), not just "any active recipe". Ties
    (more than one currently-effective APPROVED recipe) break on the most
    recently effective, then most recently created — see M20.S01.T001 V02
    F-V01-004. This does not invent a parallel recipe lifecycle; it uses the
    existing status/is_active/valid_from/valid_to fields already on Recipe.
    """
    recipe_q = await db.execute(
        select(Recipe)
        .where(
            Recipe.product_id == product_id,
            Recipe.status == RecipeStatus.APPROVED,
            Recipe.is_active == True,
            (Recipe.valid_from == None) | (Recipe.valid_from <= as_of),
            (Recipe.valid_to == None) | (Recipe.valid_to >= as_of),
        )
        .order_by(*recipe_precedence_ordering())
        .limit(1)
    )
    return recipe_q.scalar_one_or_none()


async def release_mps_plan(
    db: AsyncSession,
    mps_id: uuid.UUID,
    user_id: uuid.UUID,
    target_warehouse_id: uuid.UUID,
) -> dict:
    """Release: create ProductionOrders for all FEASIBLE non-released lines."""
    from app.models.audit_log import AuditLog
    from app.models.user import User

    plan_result = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")
    if plan.status == MPSStatus.RELEASED:
        # A RELEASED header is not sufficient proof that release output still
        # exists.  Validate every positive-quantity line before acknowledging
        # an idempotent retry so deleted orders or partial/dangling releases
        # cannot be reported as complete.
        released = (await db.execute(select(MPSLine).where(
            MPSLine.mps_id == mps_id,
            MPSLine.planned_production_qty > 0,
        ))).scalars().all()
        if not released or any(line.production_order_id is None for line in released):
            raise ValueError("Released MPS plan has missing production-order links; repair release state before retrying")
        production_order_ids = [line.production_order_id for line in released]
        if len(set(production_order_ids)) != len(production_order_ids):
            raise ValueError("Released MPS plan has duplicate production-order links; repair release state before retrying")
        existing_orders = [await db.get(ProductionOrder, line.production_order_id) for line in released]
        if any(order is None for order in existing_orders):
            raise ValueError("Released MPS plan references a missing production order; repair release state before retrying")
        orders = existing_orders
        if len(orders) != len(released):
            raise ValueError("Released MPS plan production orders do not match all required lines")
        if any(order.target_warehouse_id != target_warehouse_id for order in orders):
            raise ValueError("Idempotent release retry must use the original target warehouse")
        return {"released_orders": len(orders), "release_required_lines": len(released), "release_complete": True, "idempotent_retry": True, "production_order_ids": [str(order.id) for order in orders]}
    if plan.status != MPSStatus.APPROVED:
        raise ValueError("Plan must be APPROVED before release")

    if not plan.mrp_run_id:
        raise ValueError("MPS plan has no warehouse-scoped source MRP run")
    source_run = await db.get(MRPRun, plan.mrp_run_id)
    if source_run is None or source_run.status != MRPRunStatus.COMPLETED or not source_run.warehouse_id:
        raise ValueError("Release requires a COMPLETED source MRP run with warehouse scope")
    source_warehouse = await db.get(Warehouse, source_run.warehouse_id)
    if source_warehouse is None:
        raise ValueError("Source MRP warehouse no longer exists")

    warehouse = await db.get(Warehouse, target_warehouse_id)
    if not warehouse:
        raise ValueError(f"Target warehouse {target_warehouse_id} not found")
    if not warehouse.is_active:
        raise ValueError(f"Target warehouse {warehouse.code} is not active")
    if warehouse.company_id != source_warehouse.company_id:
        raise ValueError("Target warehouse must belong to the same company as the source MRP warehouse")

    prelinked_count = await db.scalar(
        select(func.count()).select_from(MPSLine).where(
            MPSLine.mps_id == mps_id,
            MPSLine.planned_production_qty > 0,
            MPSLine.production_order_id.is_not(None),
        )
    )
    if prelinked_count:
        raise ValueError(
            "Approved MPS plan already contains production-order links; reconcile release state before creating orders"
        )

    lines_result = await db.execute(
        select(MPSLine).where(
            MPSLine.mps_id == mps_id,
            MPSLine.production_order_id == None,
            MPSLine.planned_production_qty > 0,
            MPSLine.feasibility_status == MPSFeasibilityStatus.FEASIBLE,
        )
    )
    lines = lines_result.scalars().all()

    ineligible_count_result = await db.execute(
        select(func.count()).select_from(MPSLine).where(
            MPSLine.mps_id == mps_id,
            MPSLine.production_order_id == None,
            MPSLine.planned_production_qty > 0,
            MPSLine.feasibility_status != MPSFeasibilityStatus.FEASIBLE,
        )
    )
    ineligible_count = ineligible_count_result.scalar() or 0

    skipped_no_recipe = 0
    prepared_lines = []
    for line in lines:
        required_start = recipe_required_date(line.planned_start_date, line.period_start)
        recipe = await _select_release_recipe(db, line.product_id, required_start)
        if not recipe:
            reason = "[no approved effective recipe — skipped]"
            if reason not in (line.remarks or ""):
                line.remarks = (line.remarks or "") + f" {reason}"
            skipped_no_recipe += 1
            continue

        product = await db.get(Product, line.product_id)
        if product is None:
            raise ValueError(
                f"Product {line.product_id} is missing; cannot release MPS line {line.line_no}"
            )

        product_uom = product.uom
        uom_value = getattr(product_uom, "value", product_uom)
        valid_uoms = {member.value for member in UnitOfMeasure}
        if not isinstance(uom_value, str) or uom_value not in valid_uoms:
            raise ValueError(
                f"Product {line.product_id} has no valid authoritative UOM; "
                f"cannot release MPS line {line.line_no}"
            )

        start_dt = datetime.combine(
            line.planned_start_date or plan.start_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(
            line.planned_end_date or plan.end_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        prepared_lines.append((line, recipe, uom_value, start_dt, end_dt))

    # Release is deliberately all-or-none.  A mixed eligible/ineligible set or
    # a missing recipe is reported without creating partial ProductionOrders;
    # the plan remains APPROVED and can be repaired and retried safely.
    release_required_count = len(lines) + ineligible_count
    unresolved_count = skipped_no_recipe + ineligible_count
    if unresolved_count:
        await db.flush()
        return {
            "released_orders": 0,
            "skipped_no_recipe": skipped_no_recipe,
            "skipped_ineligible": ineligible_count,
            "unresolved_lines": unresolved_count,
            "release_required_lines": release_required_count,
            "release_complete": False,
        }

    if not prepared_lines:
        return {
            "released_orders": 0, "skipped_no_recipe": skipped_no_recipe,
            "skipped_ineligible": ineligible_count,
            "unresolved_lines": skipped_no_recipe + ineligible_count,
            "release_required_lines": release_required_count,
            "release_complete": False,
        }

    # The migration-backed PostgreSQL sequence is monotonic across concurrent
    # releases and survives deletion of an older ProductionOrder.  It replaces
    # the unsafe count+1 allocator without changing unrelated PO numbering.
    po_seq_result = await db.execute(
        text("SELECT nextval('mps_po_number_seq')")
    )
    po_seq = int(po_seq_result.scalar())
    created = 0
    for line, recipe, uom_value, start_dt, end_dt in prepared_lines:

        po = ProductionOrder(
            order_no=f"PO-MPS-{po_seq:06d}",
            product_id=line.product_id,
            recipe_id=recipe.id,
            planned_quantity=line.planned_production_qty,
            uom=uom_value,
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
        created += 1
        if created < len(prepared_lines):
            po_seq_result = await db.execute(
                text("SELECT nextval('mps_po_number_seq')")
            )
            po_seq = int(po_seq_result.scalar())

    release_complete = (
        release_required_count > 0
        and created == len(lines)
        and skipped_no_recipe == 0
        and ineligible_count == 0
    )
    if release_complete:
        actor = await db.get(User, user_id)
        if actor is None:
            raise ValueError("Authenticated releaser no longer exists")
        before = {"status": str(getattr(plan.status, "value", plan.status)), "released_at": plan.released_at.isoformat() if plan.released_at else None}
        plan.status = MPSStatus.RELEASED
        plan.released_at = datetime.now(timezone.utc)
        db.add(AuditLog(
            actor_id=user_id, actor_email=actor.email, actor_name=actor.full_name,
            event_type="MPS_PLAN_RELEASED", module="mps", target_type="mps_plan",
            target_id=str(plan.id), target_name=plan.plan_no, before_value=before,
            after_value={"status": "RELEASED", "released_at": plan.released_at.isoformat()},
            details={"production_order_ids": [str(line.production_order_id) for line, *_ in prepared_lines], "target_warehouse_id": str(target_warehouse_id)},
        ))
    await db.flush()
    return {
        "released_orders": created,
        "skipped_no_recipe": skipped_no_recipe,
        "skipped_ineligible": ineligible_count,
        "unresolved_lines": skipped_no_recipe + ineligible_count,
        "release_required_lines": release_required_count,
        "release_complete": release_complete,
        "idempotent_retry": False,
        "production_order_ids": [
            str(line.production_order_id) for line, *_ in prepared_lines if line.production_order_id is not None
        ],
    }


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
                cast(MPSLine.feasibility_status == MPSFeasibilityStatus.OVERLOADED, Integer)
            ).label("over"),
            func.sum(
                cast(MPSLine.feasibility_status == MPSFeasibilityStatus.FEASIBLE, Integer)
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
            func.sum(case((MPSLine.feasibility_status == MPSFeasibilityStatus.OVERLOADED, 1), else_=0)).label("over"),
            func.sum(case((MPSLine.feasibility_status == MPSFeasibilityStatus.FEASIBLE, 1), else_=0)).label("feas"),
            func.sum(case((MPSLine.is_locked.is_(True), 1), else_=0)).label("locked"),
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
