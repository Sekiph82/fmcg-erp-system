"""
MPS API — Master Production Scheduling endpoints.

All at /api/v1/mps/...
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.access_control import can_modify_scope, can_view_scope
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
    allowed = (can_view_scope(user, "mps", "warehouse", warehouse.id) if view
               else can_modify_scope(user, "mps", action, "warehouse", warehouse.id))
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


@router.get("/plans/{mps_id}/constraints", tags=["mps"])
async def plan_constraints(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "create")),
):
    async with db.begin():
        plan = await create_mps_plan(db, body, current_user.id)
    return plan


@router.get("/plans", response_model=List[MPSPlanSummary], tags=["mps"])
async def list_plans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("mps", "view")),
):
    async with db.begin():
        return await list_mps_plans(db, limit, offset)


@router.get("/plans/{mps_id}", response_model=MPSPlanOut, tags=["mps"])
async def get_plan(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "edit")),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "edit")
        line = await update_mps_line(db, mps_id, line_id, body)
    if not line:
        raise HTTPException(404, "MPS line not found")
    return line


# ── Capacity ──────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/capacity-heatmap", response_model=CapacityHeatmap, tags=["mps"])
async def capacity_heatmap(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "view")),
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
            await _check_plan_scope(db, current_user, mps_id, "simulate")
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
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "view")),
):
    async with db.begin():
        await _check_plan_scope(db, current_user, mps_id, "view", view=True)
        return await list_whatif_scenarios(db, mps_id)


@router.get("/whatif/{scenario_id}", response_model=MPSWhatIfOut, tags=["mps"])
async def get_whatif(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("mps", "view")),
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
    current_user: User = Depends(require_permission("mps", "view")),
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
