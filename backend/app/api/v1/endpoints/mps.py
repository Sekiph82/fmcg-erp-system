"""
MPS API — Master Production Scheduling endpoints.

All at /api/v1/mps/...
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, require_permission
from app.core.access_control import can_modify_scope, can_view_scope, has_permission
from app.models.user import User
from app.models.mrp import MRPRun
from app.models.master import Warehouse
from app.models.mps import MPSPlan
from sqlalchemy import select
from app.schemas.mps import (
    MPSPlanCreate, MPSPlanOut, MPSPlanSummary,
    MPSLineUpdate, MPSLineOut,
    MPSCampaignOut,
    CapacityHeatmap,
    MPSWhatIfCreate, MPSWhatIfOut,
    MPSAIRecOut,
    MPSDashboard,
    MPSLineConstraintDiagnosticOut,
    GenerateFromMRPRequest,
)
from app.services.mps_service import (
    create_mps_plan, get_mps_plan, list_mps_plans,
    get_mps_lines, update_mps_line,
    generate_mps_from_mrp, approve_mps_plan, release_mps_plan,
    get_mps_dashboard,
)
from app.services.mps_capacity_service import (
    run_capacity_scheduling_validated as run_capacity_scheduling,
    get_capacity_heatmap, suggest_reschedule,
)
from app.services.mps_campaign_service import (
    run_campaign_grouping_validated as run_campaign_grouping,
    list_campaigns,
)
from app.services.mps_whatif_service import (
    create_whatif_scenario, list_whatif_scenarios, get_whatif_scenario,
    compare_whatif_scenarios,
)
from app.services.mps_ai_service import (
    run_all_ai_agents, list_ai_recommendations, review_recommendation,
)
from app.services.mps_advanced_service import (
    project_demand_and_supply, evaluate_material_feasibility,
    list_plan_diagnostics,
)


router = APIRouter()


_MPS_SCOPE_SUFFIXES = {
    "view": ("own_scope", "own_company", "own_branch", "own_warehouse"),
    "create": ("own_scope", "own_company", "own_branch", "own_warehouse"),
    "edit": ("own_scope", "own_company", "own_branch", "own_warehouse"),
}


def _require_mps_scope_action_permission(user: User, action: str) -> bool:
    """Return whether the caller has global access; allow scoped roles for filtering/checks below."""
    if has_permission(user, f"mps.{action}") or has_permission(user, f"mps.{action}_all"):
        return True
    if any(has_permission(user, f"mps.{action}_{suffix}") for suffix in _MPS_SCOPE_SUFFIXES[action]):
        return False
    raise HTTPException(403, f"Permission 'mps.{action}' or a scoped MPS permission is required")


async def require_mps_view_permission(current_user: User = Depends(get_current_user)) -> User:
    _require_mps_scope_action_permission(current_user, "view")
    return current_user


async def require_mps_edit_permission(current_user: User = Depends(get_current_user)) -> User:
    _require_mps_scope_action_permission(current_user, "edit")
    return current_user


def _warehouse_in_user_scope(user: User, warehouse: Warehouse, action: str, *, view: bool = False) -> bool:
    def allowed(scope_type: str, scope_id: uuid.UUID) -> bool:
        if view:
            return can_view_scope(user, "mps", scope_type, scope_id)
        return can_modify_scope(user, "mps", action, scope_type, scope_id)

    if allowed("warehouse", warehouse.id):
        return True
    if warehouse.company_id:
        if allowed("company", warehouse.company_id):
            return True
    if warehouse.branch_id:
        if allowed("branch", warehouse.branch_id):
            return True
    return False


async def _check_source_run_scope(db: AsyncSession, user: User, mrp_run_id: uuid.UUID | None) -> None:
    """Scoped plan creators may only bind a plan to an MRP run in their scope."""
    if has_permission(user, "mps.create") or has_permission(user, "mps.create_all"):
        return
    if mrp_run_id is None:
        raise HTTPException(400, "A scoped MPS creator must select a warehouse-scoped MRP run")
    run = await db.get(MRPRun, mrp_run_id)
    if run is None:
        return  # Let the service return its canonical invalid-source response.
    if run.warehouse_id is None:
        raise HTTPException(400, "A scoped MPS creator cannot use an MRP run without a warehouse")
    warehouse = await db.get(Warehouse, run.warehouse_id)
    if warehouse is None:
        raise HTTPException(400, "The MRP run warehouse is unavailable")
    if not _warehouse_in_user_scope(user, warehouse, "create"):
        raise HTTPException(403, "Access denied for the MPS source warehouse scope")


async def _visible_mps_warehouse_ids(db: AsyncSession, user: User) -> list[uuid.UUID] | None:
    """Return warehouse IDs visible to a scoped planner; None denotes explicit global view."""
    if _require_mps_scope_action_permission(user, "view"):
        return None
    warehouses = (await db.execute(select(Warehouse))).scalars().all()
    return [warehouse.id for warehouse in warehouses if _warehouse_in_user_scope(user, warehouse, "view", view=True)]


async def _check_plan_scope(db: AsyncSession, user: User, mps_id: uuid.UUID, action: str, *, view: bool = False) -> None:
    """Apply warehouse-scope authorization to an MPS plan's source run."""
    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))).scalar_one_or_none()
    if plan is None:
        raise HTTPException(404, "MPS plan not found")
    run = await db.get(MRPRun, plan.mrp_run_id) if plan.mrp_run_id else None
    if run is None or run.warehouse_id is None:
        raise HTTPException(400, "MPS plan has no warehouse-scoped MRP source")
    warehouse = await db.get(Warehouse, run.warehouse_id)
    if warehouse is None:
        raise HTTPException(400, "MPS plan source warehouse is unavailable")
    allowed = _warehouse_in_user_scope(user, warehouse, action, view=view)
    if not allowed:
        raise HTTPException(403, "Access denied for the MPS plan warehouse scope")


@router.post("/plans/{mps_id}/project-demand", tags=["mps"])
async def project_demand(
    mps_id: uuid.UUID,
    period_type: str = Query("WEEKLY", pattern="^(DAILY|WEEKLY|MONTHLY)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "calculate")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "calculate")
            return await project_demand_and_supply(db, mps_id, period_type)
        except ValueError as exc:
            raise HTTPException(400, str(exc))


@router.post("/plans/{mps_id}/material-feasibility", tags=["mps"])
async def material_feasibility(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "calculate")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "calculate")
            return await evaluate_material_feasibility(db, mps_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))


@router.get("/plans/{mps_id}/constraints", response_model=List[MPSLineConstraintDiagnosticOut], tags=["mps"])
async def plan_constraints(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await list_plan_diagnostics(db, mps_id)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=MPSDashboard, tags=["mps"])
async def mps_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("mps", "view")),
):
    return await get_mps_dashboard(db)


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.post("/plans", response_model=MPSPlanOut, status_code=201, tags=["mps"])
async def create_plan(
    body: MPSPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_mps_scope_action_permission(current_user, "create")
    async with db.begin():
        await _check_source_run_scope(db, current_user, body.mrp_run_id)
        plan = await create_mps_plan(db, body, current_user.id)
    return plan


@router.get("/plans", response_model=List[MPSPlanSummary], tags=["mps"])
async def list_plans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_mps_scope_action_permission(current_user, "view")
    async with db.begin():
        warehouse_ids = await _visible_mps_warehouse_ids(db, current_user)
        return await list_mps_plans(db, limit, offset, warehouse_ids=warehouse_ids)


@router.get("/plans/{mps_id}", response_model=MPSPlanOut, tags=["mps"])
async def get_plan(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        plan = await get_mps_plan(db, mps_id)
    if not plan:
        raise HTTPException(404, "MPS plan not found")
    return plan


@router.post("/plans/{mps_id}/generate-from-mrp", tags=["mps"])
async def generate_from_mrp(
    mps_id: uuid.UUID,
    body: GenerateFromMRPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "calculate")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "calculate")
            count = await generate_mps_from_mrp(db, mps_id, body)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return {"lines_created": count}


@router.post("/plans/{mps_id}/run-capacity", tags=["mps"])
async def run_capacity(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "calculate")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "calculate")
            result = await run_capacity_scheduling(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.post("/plans/{mps_id}/run-campaigns", tags=["mps"])
async def run_campaigns(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "calculate")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "calculate")
            result = await run_campaign_grouping(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.post("/plans/{mps_id}/run-ai", tags=["mps"])
async def run_ai(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "ai")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "ai")
            result = await run_all_ai_agents(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.patch("/plans/{mps_id}/approve", response_model=MPSPlanOut, tags=["mps"])
async def approve_plan(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "approve")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "approve")
            plan = await approve_mps_plan(db, mps_id, current_user.id)
            # Load server-managed timestamps before the response serializer
            # reads the ORM object after the transaction has ended.
            await db.refresh(plan)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return plan


@router.post("/plans/{mps_id}/release", tags=["mps"])
async def release_plan(
    mps_id: uuid.UUID,
    target_warehouse_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "release")),
):
    async with db.begin():
        try:
            await _check_plan_scope(db, current_user, mps_id, "release")
            if not can_modify_scope(current_user, "mps", "release", "warehouse", target_warehouse_id):
                raise HTTPException(403, "Access denied for the release target warehouse scope")
            result = await release_mps_plan(db, mps_id, current_user.id, target_warehouse_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


# ── Lines ─────────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/lines", response_model=List[MPSLineOut], tags=["mps"])
async def list_lines(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await get_mps_lines(db, mps_id)


@router.patch("/plans/{mps_id}/lines/{line_id}", response_model=MPSLineOut, tags=["mps"])
async def update_line(
    mps_id: uuid.UUID,
    line_id: uuid.UUID,
    body: MPSLineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_edit_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "edit")
        try:
            line = await update_mps_line(db, mps_id, line_id, body, current_user.id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    if not line:
        raise HTTPException(404, "MPS line not found")
    return line


# ── Capacity ──────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/capacity-heatmap", response_model=CapacityHeatmap, tags=["mps"])
async def capacity_heatmap(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await get_capacity_heatmap(db, mps_id)


@router.get("/lines/{line_id}/reschedule-suggestion", tags=["mps"])
async def reschedule_suggestion(
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("mps", "view")),
):
    async with db.begin():
        try:
            return await suggest_reschedule(db, line_id)
        except ValueError as e:
            raise HTTPException(400, str(e))


# ── Campaigns ─────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/campaigns", response_model=List[MPSCampaignOut], tags=["mps"])
async def get_campaigns(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await list_campaigns(db, mps_id)


# ── What-If ───────────────────────────────────────────────────────────────────

@router.post("/plans/{mps_id}/whatif", response_model=MPSWhatIfOut, status_code=201, tags=["mps"])
async def create_whatif(
    mps_id: uuid.UUID,
    body: MPSWhatIfCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "simulate")),
):
    async with db.begin():
        try:
            # Saving a simulation is allowed only to planners with edit access
            # to the source plan's warehouse; the module-level simulate
            # permission is checked separately by the route dependency.
            await _check_plan_scope(db, current_user, mps_id, "edit")
            scenario = await create_whatif_scenario(db, mps_id, body, current_user.id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return scenario


@router.get("/plans/{mps_id}/scenario-comparison", tags=["mps"])
async def scenario_comparison(
    mps_id: uuid.UUID,
    baseline_id: uuid.UUID = Query(...),
    candidate_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        try:
            return await compare_whatif_scenarios(db, mps_id, baseline_id, candidate_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))


@router.get("/plans/{mps_id}/whatif", response_model=List[MPSWhatIfOut], tags=["mps"])
async def list_whatif(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await list_whatif_scenarios(db, mps_id)


@router.get("/whatif/{scenario_id}", response_model=MPSWhatIfOut, tags=["mps"])
async def get_whatif(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        s = await get_whatif_scenario(db, scenario_id)
        if s:
            await _check_plan_scope(db, current_user, s.mps_id, "view", view=True)
    if not s:
        raise HTTPException(404, "Scenario not found")
    return s


# ── AI Recommendations ────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/ai-recommendations", response_model=List[MPSAIRecOut], tags=["mps"])
async def get_ai_recs(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mps_view_permission),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await list_ai_recommendations(db, mps_id)


@router.patch("/ai-recommendations/{rec_id}/accept", response_model=MPSAIRecOut, tags=["mps"])
async def accept_rec(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "ai")),
):
    async with db.begin():
        try:
            rec = await review_recommendation(db, rec_id, True, current_user.id)
        except ValueError as e:
            raise HTTPException(404, str(e))
    return rec


@router.patch("/ai-recommendations/{rec_id}/reject", response_model=MPSAIRecOut, tags=["mps"])
async def reject_rec(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "ai")),
):
    async with db.begin():
        try:
            rec = await review_recommendation(db, rec_id, False, current_user.id)
        except ValueError as e:
            raise HTTPException(404, str(e))
    return rec
