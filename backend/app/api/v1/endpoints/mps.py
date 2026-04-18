"""
MPS API — Master Production Scheduling endpoints.

All at /api/v1/mps/...
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
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
    run_capacity_scheduling, get_capacity_heatmap, suggest_reschedule,
)
from app.services.mps_campaign_service import run_campaign_grouping, list_campaigns
from app.services.mps_whatif_service import (
    create_whatif_scenario, list_whatif_scenarios, get_whatif_scenario,
)
from app.services.mps_ai_service import (
    run_all_ai_agents, list_ai_recommendations, review_recommendation,
)


router = APIRouter()

_SYSTEM_USER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _get_current_user_id() -> uuid.UUID:
    return _SYSTEM_USER


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=MPSDashboard, tags=["mps"])
async def mps_dashboard(db: AsyncSession = Depends(get_db)):
    return await get_mps_dashboard(db)


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.post("/plans", response_model=MPSPlanOut, status_code=201, tags=["mps"])
async def create_plan(
    body: MPSPlanCreate,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        plan = await create_mps_plan(db, body, _get_current_user_id())
    return plan


@router.get("/plans", response_model=List[MPSPlanSummary], tags=["mps"])
async def list_plans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        return await list_mps_plans(db, limit, offset)


@router.get("/plans/{mps_id}", response_model=MPSPlanOut, tags=["mps"])
async def get_plan(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        plan = await get_mps_plan(db, mps_id)
    if not plan:
        raise HTTPException(404, "MPS plan not found")
    return plan


@router.post("/plans/{mps_id}/generate-from-mrp", tags=["mps"])
async def generate_from_mrp(
    mps_id: uuid.UUID,
    body: GenerateFromMRPRequest,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        try:
            count = await generate_mps_from_mrp(db, mps_id, body)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return {"lines_created": count}


@router.post("/plans/{mps_id}/run-capacity", tags=["mps"])
async def run_capacity(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            result = await run_capacity_scheduling(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.post("/plans/{mps_id}/run-campaigns", tags=["mps"])
async def run_campaigns(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            result = await run_campaign_grouping(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.post("/plans/{mps_id}/run-ai", tags=["mps"])
async def run_ai(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            result = await run_all_ai_agents(db, mps_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


@router.patch("/plans/{mps_id}/approve", response_model=MPSPlanOut, tags=["mps"])
async def approve_plan(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            plan = await approve_mps_plan(db, mps_id, _get_current_user_id())
        except ValueError as e:
            raise HTTPException(400, str(e))
    return plan


@router.post("/plans/{mps_id}/release", tags=["mps"])
async def release_plan(
    mps_id: uuid.UUID,
    target_warehouse_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        try:
            result = await release_mps_plan(db, mps_id, _get_current_user_id(), target_warehouse_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return result


# ── Lines ─────────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/lines", response_model=List[MPSLineOut], tags=["mps"])
async def list_lines(
    mps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        return await get_mps_lines(db, mps_id)


@router.patch("/plans/{mps_id}/lines/{line_id}", response_model=MPSLineOut, tags=["mps"])
async def update_line(
    mps_id: uuid.UUID,
    line_id: uuid.UUID,
    body: MPSLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        line = await update_mps_line(db, line_id, body)
    if not line:
        raise HTTPException(404, "MPS line not found")
    return line


# ── Capacity ──────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/capacity-heatmap", response_model=CapacityHeatmap, tags=["mps"])
async def capacity_heatmap(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        return await get_capacity_heatmap(db, mps_id)


@router.get("/lines/{line_id}/reschedule-suggestion", tags=["mps"])
async def reschedule_suggestion(
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        try:
            return await suggest_reschedule(db, line_id)
        except ValueError as e:
            raise HTTPException(400, str(e))


# ── Campaigns ─────────────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/campaigns", response_model=List[MPSCampaignOut], tags=["mps"])
async def get_campaigns(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        return await list_campaigns(db, mps_id)


# ── What-If ───────────────────────────────────────────────────────────────────

@router.post("/plans/{mps_id}/whatif", response_model=MPSWhatIfOut, status_code=201, tags=["mps"])
async def create_whatif(
    mps_id: uuid.UUID,
    body: MPSWhatIfCreate,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        try:
            scenario = await create_whatif_scenario(db, mps_id, body, _get_current_user_id())
        except ValueError as e:
            raise HTTPException(400, str(e))
    return scenario


@router.get("/plans/{mps_id}/whatif", response_model=List[MPSWhatIfOut], tags=["mps"])
async def list_whatif(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        return await list_whatif_scenarios(db, mps_id)


@router.get("/whatif/{scenario_id}", response_model=MPSWhatIfOut, tags=["mps"])
async def get_whatif(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        s = await get_whatif_scenario(db, scenario_id)
    if not s:
        raise HTTPException(404, "Scenario not found")
    return s


# ── AI Recommendations ────────────────────────────────────────────────────────

@router.get("/plans/{mps_id}/ai-recommendations", response_model=List[MPSAIRecOut], tags=["mps"])
async def get_ai_recs(mps_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        return await list_ai_recommendations(db, mps_id)


@router.patch("/ai-recommendations/{rec_id}/accept", response_model=MPSAIRecOut, tags=["mps"])
async def accept_rec(rec_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            rec = await review_recommendation(db, rec_id, True, _get_current_user_id())
        except ValueError as e:
            raise HTTPException(404, str(e))
    return rec


@router.patch("/ai-recommendations/{rec_id}/reject", response_model=MPSAIRecOut, tags=["mps"])
async def reject_rec(rec_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        try:
            rec = await review_recommendation(db, rec_id, False, _get_current_user_id())
        except ValueError as e:
            raise HTTPException(404, str(e))
    return rec
