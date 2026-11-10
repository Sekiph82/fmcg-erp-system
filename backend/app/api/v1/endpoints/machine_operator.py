from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.access_control import can_modify_scope, can_view_scope, has_any_permission
from app.services.downtime_reason_service import list_downtime_reason_codes
from app.schemas.maintenance import DowntimeReasonCodeRead
from app.models.machine_operator import (
    Machine, MachineSkillRequirement, MachineStatus, MOAIAgentType, MOAIRecStatus, DowntimeClass,
)
from app.models.production_advanced import WorkOrder
from app.schemas.machine_operator import (
    MachineCreate, MachineOut, MachineUpdate,
    OperatorProfileCreate, OperatorProfileOut,
    TeamCreate, TeamOut, TeamMemberAdd, TeamMemberOut,
    SkillCertCreate, SkillCertOut,
    AssignmentCreate, AssignmentOut, AssignmentHistoryOut,
    AssignmentValidateRequest, AssignmentValidateResult,
    MachineSkillRequirementCreate, MachineSkillRequirementOut, MachineSkillRequirementUpdate,
    RuntimeLogCreate, RuntimeLogOut,
    MachineRuntimeKpisOut,
    LaborTimeCreate, LaborTimeOut,
    PerformanceSnapshotOut,
    DowntimeIntelCreate, DowntimeIntelOut,
    SupervisorReviewCreate, SupervisorReviewOut,
    MOAIRecOut, MOAIRecAction,
    MODashboard, CostContribution, OperatorProductivityOut,
    ShiftTeamComparisonsOut,
    PerformanceAnomalyReportOut,
    DowntimeProductionCorrelationReport,
)
from app.services import machine_operator_service as svc

async def _require_machine_operator_permission(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    path = request.url.path.rstrip("/")
    action = "view" if request.method in {"GET", "HEAD", "OPTIONS"} or path.endswith("/assignments/validate") else "edit"
    if action == "view":
        allowed = has_any_permission(current_user, ("production.view", "production.view_all"))
        if allowed:
            return
    elif path.endswith("/assignments") and request.method == "POST":
        if has_any_permission(current_user, ("production.edit", "production.edit_all")):
            allowed = True
        elif has_any_permission(current_user, ("production.approve",)):
            action = "approve"
            allowed = True
        else:
            allowed = False
    elif path.endswith("/labor/approve") or "/labor/" in path and path.endswith("/approve"):
        allowed = has_any_permission(current_user, ("production.approve",))
    elif path.endswith("/supervisor/reviews"):
        allowed = has_any_permission(current_user, ("production.approve",))
    else:
        allowed = has_any_permission(current_user, ("production.edit", "production.edit_all"))
    if allowed:
        return

    async def machine_scope(machine_id: UUID, scope_action: str) -> bool:
        result = await db.execute(select(Machine).where(Machine.id == machine_id))
        machine = result.scalar_one_or_none()
        if machine is None:
            return False
        scopes = [("machine", machine.id)]
        scopes.extend(
            (scope_type, scope_id)
            for scope_type, scope_id in (
                ("factory", machine.plant_id),
                ("section", machine.section_id),
                ("production_line", machine.line_id),
            )
            if scope_id is not None
        )
        return any(
            can_view_scope(current_user, "production", scope_type, scope_id)
            if scope_action == "view"
            else can_modify_scope(current_user, "production", scope_action, scope_type, scope_id)
            for scope_type, scope_id in scopes
        )

    async def work_center_scope(work_center_id: UUID, scope_action: str) -> bool:
        has_center_scope = (
            can_view_scope(current_user, "production", "work_center", work_center_id)
            if scope_action == "view"
            else can_modify_scope(current_user, "production", scope_action, "work_center", work_center_id)
        )
        if has_center_scope:
            return True
        result = await db.execute(select(Machine).where(Machine.work_center_id == work_center_id))
        machines = result.scalars().all()
        # A work-center rule affects every machine assigned to it. A scoped
        # operator must be authorized for all of them before changing/viewing it.
        return bool(machines) and all([await machine_scope(machine.id, scope_action) for machine in machines])

    async def work_order_scope(work_order_id: UUID, scope_action: str, machine_id: UUID | None = None) -> bool:
        result = await db.execute(select(WorkOrder).where(WorkOrder.id == work_order_id))
        work_order = result.scalar_one_or_none()
        if work_order is None:
            return False
        if machine_id is not None:
            if not await machine_scope(machine_id, scope_action):
                return False
            machine_result = await db.execute(select(Machine).where(Machine.id == machine_id))
            machine = machine_result.scalar_one_or_none()
            if machine is None or (
                work_order.work_center_id is not None and machine.work_center_id != work_order.work_center_id
            ):
                return False
            return True
        if work_order.work_center_id is not None:
            return await work_center_scope(work_order.work_center_id, scope_action)
        return False

    scoped_allowed = False
    if path.endswith("/qualification-requirements") and request.method == "GET":
        machine_ids = request.query_params.getlist("machine_id")
        work_center_ids = request.query_params.getlist("work_center_id")
        if machine_ids or work_center_ids:
            try:
                scoped_allowed = all([await machine_scope(UUID(value), action) for value in machine_ids]) and all(
                    [await work_center_scope(UUID(value), action) for value in work_center_ids]
                )
            except ValueError:
                scoped_allowed = False
    elif path.endswith("/qualification-requirements") and request.method == "POST":
        body = await request.json()
        try:
            machine_id = UUID(body["machine_id"]) if body.get("machine_id") else None
            work_center_id = UUID(body["work_center_id"]) if body.get("work_center_id") else None
            scoped_allowed = (
                (machine_id is not None) != (work_center_id is not None)
                and (await machine_scope(machine_id, action) if machine_id else await work_center_scope(work_center_id, action))
            )
        except (KeyError, TypeError, ValueError):
            scoped_allowed = False
    elif "/qualification-requirements/" in path and request.method == "PATCH":
        try:
            requirement_id = UUID(path.rsplit("/", 1)[-1])
            result = await db.execute(
                select(MachineSkillRequirement).where(MachineSkillRequirement.id == requirement_id)
            )
            requirement = result.scalar_one_or_none()
            if requirement is not None:
                body = await request.json()
                old_allowed = (
                    await machine_scope(requirement.machine_id, action)
                    if requirement.machine_id is not None
                    else await work_center_scope(requirement.work_center_id, action)
                )
                target_machine = UUID(body["machine_id"]) if body.get("machine_id") else None
                target_center = UUID(body["work_center_id"]) if body.get("work_center_id") else None
                target_machine = target_machine if "machine_id" in body else requirement.machine_id
                target_center = target_center if "work_center_id" in body else requirement.work_center_id
                target_allowed = (
                    (await machine_scope(target_machine, action) if target_machine else await work_center_scope(target_center, action))
                    if (target_machine is not None) != (target_center is not None)
                    else False
                )
                scoped_allowed = old_allowed and target_allowed
        except (TypeError, ValueError):
            scoped_allowed = False
    elif path.endswith("/assignments/validate") or path.endswith("/assignments") and request.method == "POST":
        try:
            body = await request.json()
            work_order_id = UUID(body["work_order_id"])
            machine_id = UUID(body["machine_id"]) if body.get("machine_id") else None
            if path.endswith("/assignments/validate") or has_any_permission(
                current_user, ("production.edit", "production.edit_all")
            ):
                scoped_allowed = await work_order_scope(work_order_id, action, machine_id)
            else:
                scoped_allowed = await work_order_scope(work_order_id, "edit", machine_id) or await work_order_scope(
                    work_order_id, "approve", machine_id
                )
        except (KeyError, TypeError, ValueError):
            scoped_allowed = False
    elif "/assignments/" in path and request.method == "GET":
        try:
            work_order_id = UUID(path.split("/assignments/", 1)[1].split("/", 1)[0])
            scoped_allowed = await work_order_scope(work_order_id, action)
        except ValueError:
            scoped_allowed = False

    if not scoped_allowed:
        requirement = "broad production view" if action == "view" else "production edit/approval permission and matching resource scope"
        raise HTTPException(403, f"A {requirement} is required for this machine/operator action.")


router = APIRouter(dependencies=[Depends(_require_machine_operator_permission)])


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


@router.get("/machines/{machine_id}/runtime-kpis", response_model=MachineRuntimeKpisOut)
async def get_machine_runtime_kpis(
    machine_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await svc.get_machine_runtime_kpis(db, machine_id, date_from=date_from, date_to=date_to)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if result is None:
        raise HTTPException(404, "Machine not found")
    return result


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
    return await svc.get_cost_contribution(db, production_order_id, machine_id=machine_id)


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


@router.get("/operators/{op_id}/productivity", response_model=OperatorProductivityOut)
async def get_operator_productivity(
    op_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await svc.get_operator_productivity(db, op_id, date_from=date_from, date_to=date_to)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if result is None:
        raise HTTPException(404, "Operator not found")
    return result


@router.get("/performance/shift-team-comparisons", response_model=ShiftTeamComparisonsOut)
async def get_shift_team_comparisons(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.get_shift_team_comparisons(db, date_from=date_from, date_to=date_to)
    except ValueError as error:
        raise HTTPException(400, str(error))


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
async def create_skill(
    data: SkillCertCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.approved_flag and not has_any_permission(current_user, ("production.approve",)):
        raise HTTPException(403, "Production approval permission is required to approve a skill certificate.")
    try:
        return await svc.create_skill_cert(db, data, actor=current_user)
    except ValueError as error:
        raise HTTPException(400, str(error))


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


@router.get("/qualification-requirements", response_model=List[MachineSkillRequirementOut])
async def list_qualification_requirements(
    machine_id: Optional[UUID] = None,
    work_center_id: Optional[UUID] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_machine_skill_requirements(
        db,
        machine_id=machine_id,
        work_center_id=work_center_id,
        active_only=active_only,
    )


@router.post("/qualification-requirements", response_model=MachineSkillRequirementOut, status_code=201)
async def create_qualification_requirement(
    data: MachineSkillRequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await svc.create_machine_skill_requirement(db, data, actor=current_user)
    except ValueError as error:
        raise HTTPException(400, str(error))
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "The qualification requirement conflicts with an existing resource/skill rule") from error


@router.patch("/qualification-requirements/{requirement_id}", response_model=MachineSkillRequirementOut)
async def update_qualification_requirement(
    requirement_id: UUID,
    data: MachineSkillRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        requirement = await svc.update_machine_skill_requirement(
            db,
            requirement_id,
            data,
            actor=current_user,
        )
    except ValueError as error:
        raise HTTPException(400, str(error))
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "The qualification requirement conflicts with an existing resource/skill rule") from error
    if requirement is None:
        raise HTTPException(404, "Qualification requirement not found")
    return requirement


# ── Assignment Validation ─────────────────────────────────────────────────────

@router.post("/assignments/validate", response_model=AssignmentValidateResult)
async def validate_assignment(data: AssignmentValidateRequest, db: AsyncSession = Depends(get_db)):
    return await svc.validate_assignment(db, data)


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await svc.create_assignment(db, data, actor=current_user)
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

@router.get("/downtime/reason-codes", response_model=List[DowntimeReasonCodeRead])
async def get_machine_downtime_reason_codes(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await list_downtime_reason_codes(db)

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


@router.get("/performance/anomalies", response_model=PerformanceAnomalyReportOut)
async def get_performance_anomalies(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.get_performance_anomalies(db, date_from=date_from, date_to=date_to)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get("/performance/downtime-correlations", response_model=DowntimeProductionCorrelationReport)
async def get_downtime_production_correlations(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        report = await svc.get_downtime_production_correlations(db, date_from=date_from, date_to=date_to)
        anomalies = await svc.get_performance_anomalies(db, date_from=date_from, date_to=date_to)
        report.follow_up_handoffs = svc.build_machine_insight_follow_up_handoffs(report, anomalies)
        if report.follow_up_handoffs:
            report.data_notes.append(
                "Follow-up cards are evidence-backed review suggestions only. They do not create or change maintenance, training, or production records."
            )
        return report
    except ValueError as error:
        raise HTTPException(400, str(error))


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
