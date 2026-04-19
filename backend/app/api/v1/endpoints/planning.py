"""Advanced Production Planning Suite — REST endpoints."""
from __future__ import annotations
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.planning import (
    PlanningScenario, ResourceCalendar, OperationQueue, CapacityLoadSnapshot,
    ChangeoverMatrix, PlanningBottleneck, PlanningAIRec, PlanningSimulation,
    ScenarioStatus, PlanningRecStatus,
)
from app.schemas.planning import (
    ScenarioCreate, ScenarioUpdate, ScenarioOut, ScenarioSummary,
    CalendarCreate, CalendarOut,
    OpQueueOut,
    ChangeoverCreate, ChangeoverOut,
    BottleneckOut,
    AIRecOut, AIRecAction,
    SimulationCreate, SimulationOut,
    PlanningDashboard,
)
from app.services import (
    planning_scenario_service as svc,
    planning_capacity_service as cap_svc,
    planning_bottleneck_service as bn_svc,
    planning_simulation_service as sim_svc,
    planning_ai_service as ai_svc,
)

router = APIRouter()


def _user_id() -> UUID:
    return uuid.uuid4()  # auth integration point


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=PlanningDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    data = await svc.get_dashboard_data(db)
    return PlanningDashboard(**data)


# ── Scenarios ──────────────────────────────────────────────────────────────────

@router.post("/scenarios", response_model=ScenarioOut, status_code=201)
async def create_scenario(body: ScenarioCreate, db: AsyncSession = Depends(get_db)):
    scenario = await svc.create_scenario(db, body, _user_id())
    await db.commit()
    await db.refresh(scenario)
    return scenario


@router.get("/scenarios", response_model=List[ScenarioSummary])
async def list_scenarios(
    status: Optional[ScenarioStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_scenarios(db, status)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    scenario = await svc.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return scenario


@router.patch("/scenarios/{scenario_id}", response_model=ScenarioOut)
async def update_scenario(
    scenario_id: UUID, body: ScenarioUpdate, db: AsyncSession = Depends(get_db)
):
    scenario = await svc.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    updated = await svc.update_scenario(db, scenario, body)
    await db.commit()
    await db.refresh(updated)
    return updated


@router.post("/scenarios/{scenario_id}/activate", response_model=ScenarioOut)
async def activate_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    scenario = await svc.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    updated = await svc.activate_scenario(db, scenario)
    await db.commit()
    await db.refresh(updated)
    return updated


@router.post("/scenarios/{scenario_id}/lock", response_model=ScenarioOut)
async def lock_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    scenario = await svc.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    updated = await svc.lock_scenario(db, scenario)
    await db.commit()
    await db.refresh(updated)
    return updated


# ── Calculate (run full scheduling engine) ────────────────────────────────────

@router.post("/scenarios/{scenario_id}/calculate")
async def calculate_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    scenario = await svc.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    result = await cap_svc.run_capacity_scheduling(db, scenario_id)
    await bn_svc.detect_bottlenecks(db, scenario_id)
    await db.commit()
    return result


# ── Operations ─────────────────────────────────────────────────────────────────

@router.get("/scenarios/{scenario_id}/operations", response_model=List[OpQueueOut])
async def list_operations(
    scenario_id: UUID,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(OperationQueue).where(OperationQueue.scenario_id == scenario_id)
    if status:
        q = q.where(OperationQueue.status == status)
    q = q.order_by(OperationQueue.scheduled_start.nulls_last(), OperationQueue.priority.desc())
    result = await db.execute(q)
    return result.scalars().all()


# ── Capacity Board ─────────────────────────────────────────────────────────────

@router.get("/scenarios/{scenario_id}/capacity")
async def get_capacity_board(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    return await cap_svc.get_capacity_board(db, scenario_id)


# ── Bottlenecks ────────────────────────────────────────────────────────────────

@router.get("/scenarios/{scenario_id}/bottlenecks", response_model=List[BottleneckOut])
async def list_bottlenecks(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    return await bn_svc.list_bottlenecks(db, scenario_id)


@router.post("/bottlenecks/{bn_id}/resolve", response_model=BottleneckOut)
async def resolve_bottleneck(bn_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        bn = await bn_svc.resolve_bottleneck(db, bn_id)
        await db.commit()
        await db.refresh(bn)
        return bn
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI Recommendations ─────────────────────────────────────────────────────────

@router.post("/scenarios/{scenario_id}/run-ai")
async def run_ai_agents(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await ai_svc.run_all_agents(db, scenario_id)
    await db.commit()
    return result


@router.get("/scenarios/{scenario_id}/ai-recommendations", response_model=List[AIRecOut])
async def list_ai_recs(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    return await ai_svc.list_recs(db, scenario_id)


@router.post("/ai-recommendations/{rec_id}/action", response_model=AIRecOut)
async def action_ai_rec(
    rec_id: UUID, body: AIRecAction, db: AsyncSession = Depends(get_db)
):
    try:
        rec = await ai_svc.action_rec(db, rec_id, body.status, body.actioned_by_id)
        await db.commit()
        await db.refresh(rec)
        return rec
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Simulations ────────────────────────────────────────────────────────────────

@router.post("/scenarios/{scenario_id}/simulations", response_model=SimulationOut, status_code=201)
async def create_simulation(
    scenario_id: UUID, body: SimulationCreate, db: AsyncSession = Depends(get_db)
):
    sim = await sim_svc.create_simulation(db, scenario_id, body.sim_name, body.description, body.changes)
    await db.commit()
    await db.refresh(sim)
    return sim


@router.post("/simulations/{sim_id}/compute", response_model=SimulationOut)
async def compute_simulation(sim_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        sim = await sim_svc.compute_simulation(db, sim_id)
        await db.commit()
        await db.refresh(sim)
        return sim
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/simulations/{sim_id}/publish", response_model=SimulationOut)
async def publish_simulation(sim_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        sim = await sim_svc.publish_simulation(db, sim_id, _user_id())
        await db.commit()
        await db.refresh(sim)
        return sim
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/scenarios/{scenario_id}/simulations", response_model=List[SimulationOut])
async def list_simulations(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    return await sim_svc.list_simulations(db, scenario_id)


# ── Resource Calendars ─────────────────────────────────────────────────────────

@router.post("/calendars", response_model=CalendarOut, status_code=201)
async def create_calendar(body: CalendarCreate, db: AsyncSession = Depends(get_db)):
    cal = ResourceCalendar(**body.model_dump())
    db.add(cal)
    await db.flush()
    await db.commit()
    await db.refresh(cal)
    return cal


@router.get("/calendars")
async def list_calendars(
    work_center_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ResourceCalendar).order_by(ResourceCalendar.calendar_date.desc())
    if work_center_id:
        q = q.where(ResourceCalendar.work_center_id == work_center_id)
    result = await db.execute(q)
    return result.scalars().all()


# ── Changeover Matrix ──────────────────────────────────────────────────────────

@router.post("/changeover-matrix", response_model=ChangeoverOut, status_code=201)
async def create_changeover(body: ChangeoverCreate, db: AsyncSession = Depends(get_db)):
    row = ChangeoverMatrix(**body.model_dump())
    db.add(row)
    await db.flush()
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/changeover-matrix", response_model=List[ChangeoverOut])
async def list_changeover(
    work_center_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ChangeoverMatrix).where(ChangeoverMatrix.is_active == True)
    if work_center_id:
        q = q.where(ChangeoverMatrix.work_center_id == work_center_id)
    result = await db.execute(q)
    return result.scalars().all()
