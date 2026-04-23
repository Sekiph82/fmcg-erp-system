from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.machine_operator import (
    MachineStatus, MOAIAgentType, MOAIRecStatus, DowntimeClass, RuntimeActivity,
)
from app.schemas.machine_operator import (
    MachineCreate, MachineOut, MachineUpdate,
    OperatorProfileCreate, OperatorProfileOut,
    TeamCreate, TeamOut, TeamMemberAdd, TeamMemberOut,
    SkillCertCreate, SkillCertOut,
    AssignmentCreate, AssignmentOut, AssignmentHistoryOut,
    AssignmentValidateRequest, AssignmentValidateResult,
    RuntimeLogCreate, RuntimeLogOut,
    LaborTimeCreate, LaborTimeOut,
    PerformanceSnapshotOut,
    DowntimeIntelCreate, DowntimeIntelOut,
    SupervisorReviewCreate, SupervisorReviewOut,
    MOAIRecOut, MOAIRecAction,
    MODashboard, CostContribution,
)
from app.services import machine_operator_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=MODashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    data = await svc.get_dashboard(db)
    return MODashboard(**data)


# ── Machines ──────────────────────────────────────────────────────────────────

@router.post("/machines", response_model=MachineOut, status_code=201)
async def create_machine(data: MachineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_machine(db, data)


@router.get("/machines", response_model=List[MachineOut])
async def list_machines(
    status: Optional[MachineStatus] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_machines(db, status, active_only)


@router.get("/machines/{machine_id}", response_model=MachineOut)
async def get_machine(machine_id: UUID, db: AsyncSession = Depends(get_db)):
    m = await svc.get_machine(db, machine_id)
    if not m:
        raise HTTPException(404, "Machine not found")
    return m


@router.patch("/machines/{machine_id}", response_model=MachineOut)
async def update_machine(machine_id: UUID, data: MachineUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_machine(db, machine_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/machines/{machine_id}/runtime", response_model=List[RuntimeLogOut])
async def get_machine_runtime(
    machine_id: UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_runtime_logs(db, machine_id=machine_id, date_from=date_from, date_to=date_to, limit=limit)


@router.get("/machines/{machine_id}/performance", response_model=List[PerformanceSnapshotOut])
async def get_machine_performance(
    machine_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_performance_snapshots(db, machine_id=machine_id, date_from=date_from, date_to=date_to, limit=limit)


@router.post("/machines/{machine_id}/performance/compute", response_model=PerformanceSnapshotOut)
async def compute_performance(
    machine_id: UUID,
    snapshot_date: date = date.today(),
    shift_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.compute_performance_snapshot(db, machine_id, snapshot_date, shift_id)


@router.get("/machines/{machine_id}/costing", response_model=CostContribution)
async def get_machine_costing(machine_id: UUID, production_order_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_cost_contribution(db, production_order_id)


# ── Operators ─────────────────────────────────────────────────────────────────

@router.post("/operators", response_model=OperatorProfileOut, status_code=201)
async def create_operator(data: OperatorProfileCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_operator(db, data)


@router.get("/operators", response_model=List[OperatorProfileOut])
async def list_operators(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    return await svc.list_operators(db, active_only)


@router.get("/operators/{op_id}", response_model=OperatorProfileOut)
async def get_operator(op_id: UUID, db: AsyncSession = Depends(get_db)):
    op = await svc.get_operator(db, op_id)
    if not op:
        raise HTTPException(404, "Operator not found")
    return op


@router.get("/operators/{op_id}/performance", response_model=List[LaborTimeOut])
async def get_operator_performance(op_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await svc.list_labor_logs(db, operator_id=op_id, limit=limit)


# ── Teams ─────────────────────────────────────────────────────────────────────

@router.post("/teams", response_model=TeamOut, status_code=201)
async def create_team(data: TeamCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_team(db, data)


@router.get("/teams", response_model=List[TeamOut])
async def list_teams(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    return await svc.list_teams(db, active_only)


@router.get("/teams/{team_id}", response_model=TeamOut)
async def get_team(team_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_team(db, team_id)
    if not t:
        raise HTTPException(404, "Team not found")
    return t


@router.post("/teams/{team_id}/members", response_model=TeamMemberOut, status_code=201)
async def add_team_member(team_id: UUID, data: TeamMemberAdd, db: AsyncSession = Depends(get_db)):
    return await svc.add_team_member(db, team_id, data)


@router.get("/teams/{team_id}/performance", response_model=List[LaborTimeOut])
async def get_team_performance(team_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await svc.list_labor_logs(db, limit=limit)


# ── Skills / Certs ────────────────────────────────────────────────────────────

@router.post("/operators/skills", response_model=SkillCertOut, status_code=201)
async def create_skill(data: SkillCertCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_skill_cert(db, data)


@router.get("/operators/skills", response_model=List[SkillCertOut])
async def list_skills(
    operator_id: Optional[UUID] = None,
    machine_id: Optional[UUID] = None,
    expiring_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_skills(db, operator_id, machine_id, expiring_only)


@router.post("/operators/skills/refresh-statuses")
async def refresh_cert_statuses(db: AsyncSession = Depends(get_db)):
    count = await svc.refresh_cert_statuses(db)
    return {"updated": count}


# ── Assignment Validation ─────────────────────────────────────────────────────

@router.post("/assignments/validate", response_model=AssignmentValidateResult)
async def validate_assignment(data: AssignmentValidateRequest, db: AsyncSession = Depends(get_db)):
    return await svc.validate_assignment(db, data)


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(data: AssignmentCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.create_assignment(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/assignments/{work_order_id}", response_model=AssignmentOut)
async def get_assignment(work_order_id: UUID, db: AsyncSession = Depends(get_db)):
    a = await svc.get_assignment(db, work_order_id)
    if not a:
        raise HTTPException(404, "Assignment not found")
    return a


@router.get("/assignments/{work_order_id}/history", response_model=List[AssignmentHistoryOut])
async def get_assignment_history(work_order_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_assignment_history(db, work_order_id)


# ── Runtime Logs ──────────────────────────────────────────────────────────────

@router.post("/runtime", response_model=RuntimeLogOut, status_code=201)
async def log_runtime(data: RuntimeLogCreate, db: AsyncSession = Depends(get_db)):
    return await svc.log_runtime(db, data)


@router.get("/runtime", response_model=List[RuntimeLogOut])
async def list_runtime(
    machine_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_runtime_logs(db, machine_id=machine_id, work_order_id=work_order_id, limit=limit)


# ── Labor Time ────────────────────────────────────────────────────────────────

@router.post("/labor", response_model=LaborTimeOut, status_code=201)
async def log_labor(data: LaborTimeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.log_labor_time(db, data)


@router.get("/labor", response_model=List[LaborTimeOut])
async def list_labor(
    operator_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_labor_logs(db, operator_id=operator_id, work_order_id=work_order_id, limit=limit)


@router.post("/labor/{log_id}/approve", response_model=LaborTimeOut)
async def approve_labor(log_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.approve_labor_log(db, log_id, None)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Downtime Intelligence ─────────────────────────────────────────────────────

@router.post("/downtime", response_model=DowntimeIntelOut, status_code=201)
async def log_downtime(data: DowntimeIntelCreate, db: AsyncSession = Depends(get_db)):
    return await svc.log_downtime(db, data)


@router.get("/downtime", response_model=List[DowntimeIntelOut])
async def list_downtime(
    machine_id: Optional[UUID] = None,
    downtime_class: Optional[DowntimeClass] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_downtime(db, machine_id=machine_id, downtime_class=downtime_class, limit=limit)


@router.get("/downtime/intelligence", response_model=List[DowntimeIntelOut])
async def get_downtime_intelligence(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await svc.list_downtime(db, limit=limit)


# ── Performance Snapshots ─────────────────────────────────────────────────────

@router.get("/performance", response_model=List[PerformanceSnapshotOut])
async def list_performance(
    machine_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_performance_snapshots(db, machine_id=machine_id, date_from=date_from, date_to=date_to, limit=limit)


# ── Cost Contribution ─────────────────────────────────────────────────────────

@router.get("/costing/{production_order_id}", response_model=CostContribution)
async def get_costing(production_order_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_cost_contribution(db, production_order_id)


# ── Changeover Analysis ───────────────────────────────────────────────────────

@router.get("/changeovers/analysis", response_model=List[PerformanceSnapshotOut])
async def changeover_analysis(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    snaps = await svc.list_performance_snapshots(db, date_from=date_from, date_to=date_to, limit=200)
    return [s for s in snaps if s.changeover_time_min and s.changeover_time_min > 0]


# ── Supervisor Reviews ────────────────────────────────────────────────────────

@router.post("/supervisor/reviews", response_model=SupervisorReviewOut, status_code=201)
async def create_review(data: SupervisorReviewCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_review(db, data, None)


@router.get("/supervisor/reviews", response_model=List[SupervisorReviewOut])
async def list_reviews(entity_type: Optional[str] = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await svc.list_reviews(db, entity_type, limit)


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[MOAIRecOut])
async def run_ai(db: AsyncSession = Depends(get_db)):
    return await svc.run_ai_agents(db)


@router.get("/ai/recommendations", response_model=List[MOAIRecOut])
async def list_ai_recs(
    agent_type: Optional[MOAIAgentType] = None,
    status: Optional[MOAIRecStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type, status, limit)


@router.post("/ai/recommendations/{rec_id}/action", response_model=MOAIRecOut)
async def action_ai_rec(rec_id: UUID, data: MOAIRecAction, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.action_ai_rec(db, rec_id, data, None)
    except ValueError as e:
        raise HTTPException(404, str(e))
