from __future__ import annotations
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.machine_operator import (
    Machine, OperatorProfile, ProductionTeam, TeamMember,
    OperatorSkillCert, WorkOrderAssignment, AssignmentHistory,
    MachineRuntimeLog, LaborTimeLog, MachinePerformanceSnapshot,
    DowntimeIntelligence, SupervisorReview, MOAIRecommendation,
    MachineStatus, CertStatus, RuntimeActivity, MOAIAgentType, MOAIRecStatus,
    DowntimeClass,
)
from app.schemas.machine_operator import (
    MachineCreate, MachineUpdate, OperatorProfileCreate,
    TeamCreate, TeamMemberAdd, SkillCertCreate,
    AssignmentCreate, AssignmentValidateRequest, AssignmentValidateResult,
    RuntimeLogCreate, LaborTimeCreate, DowntimeIntelCreate,
    SupervisorReviewCreate, MOAIRecAction, CostContribution,
)

_D = Decimal


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _duration(start: datetime, end: Optional[datetime]) -> Optional[Decimal]:
    if not end:
        return None
    delta = end - start
    return _D(str(delta.total_seconds() / 60)).quantize(_D("0.01"))


# ── Machine CRUD ──────────────────────────────────────────────────────────────

async def create_machine(db: AsyncSession, data: MachineCreate) -> Machine:
    m = Machine(**data.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


async def get_machine(db: AsyncSession, machine_id: UUID) -> Optional[Machine]:
    result = await db.execute(select(Machine).where(Machine.id == machine_id))
    return result.scalar_one_or_none()


async def get_machine_by_code(db: AsyncSession, code: str) -> Optional[Machine]:
    result = await db.execute(select(Machine).where(Machine.machine_code == code))
    return result.scalar_one_or_none()


async def list_machines(
    db: AsyncSession,
    status: Optional[MachineStatus] = None,
    active_only: bool = True,
    limit: int = 200,
) -> List[Machine]:
    q = select(Machine).order_by(Machine.machine_code)
    if active_only:
        q = q.where(Machine.active_flag == True)
    if status:
        q = q.where(Machine.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def update_machine(db: AsyncSession, machine_id: UUID, data: MachineUpdate) -> Machine:
    m = await get_machine(db, machine_id)
    if not m:
        raise ValueError("Machine not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    await db.commit()
    await db.refresh(m)
    return m


# ── Operator Profile CRUD ─────────────────────────────────────────────────────

async def create_operator(db: AsyncSession, data: OperatorProfileCreate) -> OperatorProfile:
    op = OperatorProfile(**data.model_dump())
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def get_operator(db: AsyncSession, op_id: UUID) -> Optional[OperatorProfile]:
    result = await db.execute(
        select(OperatorProfile)
        .options(selectinload(OperatorProfile.skills))
        .where(OperatorProfile.id == op_id)
    )
    return result.scalar_one_or_none()


async def list_operators(db: AsyncSession, active_only: bool = True, limit: int = 200) -> List[OperatorProfile]:
    q = select(OperatorProfile).order_by(OperatorProfile.operator_code)
    if active_only:
        q = q.where(OperatorProfile.active_flag == True)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Team CRUD ─────────────────────────────────────────────────────────────────

async def create_team(db: AsyncSession, data: TeamCreate) -> ProductionTeam:
    t = ProductionTeam(**data.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def get_team(db: AsyncSession, team_id: UUID) -> Optional[ProductionTeam]:
    result = await db.execute(
        select(ProductionTeam)
        .options(selectinload(ProductionTeam.members))
        .where(ProductionTeam.id == team_id)
    )
    return result.scalar_one_or_none()


async def list_teams(db: AsyncSession, active_only: bool = True) -> List[ProductionTeam]:
    q = select(ProductionTeam).order_by(ProductionTeam.team_code)
    if active_only:
        q = q.where(ProductionTeam.active_flag == True)
    result = await db.execute(q)
    return result.scalars().all()


async def add_team_member(db: AsyncSession, team_id: UUID, data: TeamMemberAdd) -> TeamMember:
    member = TeamMember(team_id=team_id, operator_id=data.operator_id, role_in_team=data.role_in_team)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


# ── Skill / Certification ─────────────────────────────────────────────────────

async def create_skill_cert(db: AsyncSession, data: SkillCertCreate) -> OperatorSkillCert:
    cert_status = _compute_cert_status(data.certification_expiry, data.certification_required)
    sc = OperatorSkillCert(**data.model_dump(), cert_status=cert_status)
    db.add(sc)
    await db.commit()
    await db.refresh(sc)
    return sc


def _compute_cert_status(expiry: Optional[date], required: bool) -> CertStatus:
    if not required:
        return CertStatus.VALID
    if not expiry:
        return CertStatus.PENDING
    today = date.today()
    if expiry < today:
        return CertStatus.EXPIRED
    if expiry <= today + timedelta(days=30):
        return CertStatus.EXPIRING_SOON
    return CertStatus.VALID


async def list_skills(
    db: AsyncSession,
    operator_id: Optional[UUID] = None,
    machine_id: Optional[UUID] = None,
    expiring_only: bool = False,
) -> List[OperatorSkillCert]:
    q = select(OperatorSkillCert).order_by(OperatorSkillCert.created_at.desc())
    if operator_id:
        q = q.where(OperatorSkillCert.operator_id == operator_id)
    if machine_id:
        q = q.where(OperatorSkillCert.machine_id == machine_id)
    if expiring_only:
        q = q.where(OperatorSkillCert.cert_status.in_([CertStatus.EXPIRING_SOON, CertStatus.EXPIRED]))
    result = await db.execute(q)
    return result.scalars().all()


async def refresh_cert_statuses(db: AsyncSession) -> int:
    result = await db.execute(select(OperatorSkillCert).where(OperatorSkillCert.certification_required == True))
    certs = result.scalars().all()
    updated = 0
    for c in certs:
        new_status = _compute_cert_status(c.certification_expiry, c.certification_required)
        if new_status != c.cert_status:
            c.cert_status = new_status
            updated += 1
    if updated:
        await db.commit()
    return updated


# ── Assignment Validation ─────────────────────────────────────────────────────

async def validate_assignment(
    db: AsyncSession, req: AssignmentValidateRequest
) -> AssignmentValidateResult:
    warnings: List[str] = []
    blocks: List[str] = []
    operator_certified = True
    machine_available = True

    if req.machine_id:
        m = await get_machine(db, req.machine_id)
        if not m:
            blocks.append("Machine not found")
        elif m.status == MachineStatus.MAINTENANCE:
            warnings.append(f"Machine {m.machine_code} is currently in MAINTENANCE")
        elif m.status in (MachineStatus.INACTIVE, MachineStatus.RETIRED):
            blocks.append(f"Machine {m.machine_code} is {m.status.value}")
            machine_available = False

    if req.operator_id and req.machine_id:
        skills = await list_skills(db, operator_id=req.operator_id, machine_id=req.machine_id)
        if not skills:
            warnings.append("No skill record for this operator-machine pair")
        else:
            for s in skills:
                if s.cert_status == CertStatus.EXPIRED and s.certification_required:
                    blocks.append(f"Certification expired for {s.operation_code or 'this machine'}")
                    operator_certified = False
                elif s.cert_status == CertStatus.EXPIRING_SOON:
                    warnings.append("Certification expiring within 30 days")

    return AssignmentValidateResult(
        valid=len(blocks) == 0,
        warnings=warnings,
        blocks=blocks,
        operator_certified=operator_certified,
        machine_available=machine_available,
    )


# ── Work Order Assignment ─────────────────────────────────────────────────────

async def create_assignment(
    db: AsyncSession, data: AssignmentCreate, created_by: Optional[UUID] = None
) -> WorkOrderAssignment:
    validation = await validate_assignment(db, AssignmentValidateRequest(
        work_order_id=data.work_order_id,
        machine_id=data.machine_id,
        operator_id=data.operator_id,
    ))
    if not validation.valid and not data.cert_override_flag:
        raise ValueError(f"Assignment blocked: {'; '.join(validation.blocks)}")

    assignment = WorkOrderAssignment(
        **data.model_dump(),
        assigned_by=created_by,
        cert_validation_passed=validation.valid,
    )
    db.add(assignment)

    hist = AssignmentHistory(
        work_order_id=data.work_order_id,
        assignment_type=__import__("app.models.machine_operator", fromlist=["AssignmentType"]).AssignmentType.OPERATOR,
        new_value=str(data.operator_id) if data.operator_id else None,
        changed_by=created_by,
        reason="Initial assignment",
    )
    db.add(hist)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def get_assignment(db: AsyncSession, work_order_id: UUID) -> Optional[WorkOrderAssignment]:
    result = await db.execute(
        select(WorkOrderAssignment)
        .where(WorkOrderAssignment.work_order_id == work_order_id)
        .order_by(WorkOrderAssignment.assigned_at.desc())
    )
    return result.scalars().first()


async def list_assignment_history(db: AsyncSession, work_order_id: UUID) -> List[AssignmentHistory]:
    result = await db.execute(
        select(AssignmentHistory)
        .where(AssignmentHistory.work_order_id == work_order_id)
        .order_by(AssignmentHistory.changed_at.desc())
    )
    return result.scalars().all()


# ── Machine Runtime Log ───────────────────────────────────────────────────────

async def log_runtime(db: AsyncSession, data: RuntimeLogCreate) -> MachineRuntimeLog:
    duration = _duration(data.start_time, data.end_time)
    log = MachineRuntimeLog(**data.model_dump(), duration_minutes=duration)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_runtime_logs(
    db: AsyncSession,
    machine_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 200,
) -> List[MachineRuntimeLog]:
    q = select(MachineRuntimeLog).order_by(MachineRuntimeLog.start_time.desc())
    if machine_id:
        q = q.where(MachineRuntimeLog.machine_id == machine_id)
    if work_order_id:
        q = q.where(MachineRuntimeLog.work_order_id == work_order_id)
    if date_from:
        q = q.where(MachineRuntimeLog.start_time >= date_from)
    if date_to:
        q = q.where(MachineRuntimeLog.start_time <= date_to)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Labor Time Log ────────────────────────────────────────────────────────────

async def log_labor_time(db: AsyncSession, data: LaborTimeCreate) -> LaborTimeLog:
    duration = _duration(data.start_time, data.end_time)
    overtime_min = _D("0")
    if data.overtime_flag and data.end_time:
        overtime_min = max(_D("0"), duration - _D("480"))

    op = await get_operator(db, data.operator_id)
    rate = op.labor_rate_per_hour if op else None

    log = LaborTimeLog(
        **data.model_dump(),
        duration_minutes=duration,
        cost_rate_at_time=rate,
        overtime_minutes=overtime_min,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_labor_logs(
    db: AsyncSession,
    operator_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    limit: int = 200,
) -> List[LaborTimeLog]:
    q = select(LaborTimeLog).order_by(LaborTimeLog.start_time.desc())
    if operator_id:
        q = q.where(LaborTimeLog.operator_id == operator_id)
    if work_order_id:
        q = q.where(LaborTimeLog.work_order_id == work_order_id)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def approve_labor_log(
    db: AsyncSession, log_id: UUID, approved_by: Optional[UUID]
) -> LaborTimeLog:
    result = await db.execute(select(LaborTimeLog).where(LaborTimeLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise ValueError("Labor log not found")
    log.approved_flag = True
    log.approved_by = approved_by
    await db.commit()
    await db.refresh(log)
    return log


# ── Performance Snapshot Computation ─────────────────────────────────────────

async def compute_performance_snapshot(
    db: AsyncSession,
    machine_id: UUID,
    snapshot_date: date,
    shift_id: Optional[UUID] = None,
) -> MachinePerformanceSnapshot:
    existing = await db.execute(
        select(MachinePerformanceSnapshot).where(
            MachinePerformanceSnapshot.machine_id == machine_id,
            MachinePerformanceSnapshot.snapshot_date == snapshot_date,
            MachinePerformanceSnapshot.shift_id == shift_id,
        )
    )
    snap = existing.scalar_one_or_none()
    if not snap:
        snap = MachinePerformanceSnapshot(
            machine_id=machine_id,
            snapshot_date=snapshot_date,
            shift_id=shift_id,
            planned_time_min=480,
        )
        db.add(snap)
        await db.flush()

    day_start = datetime.combine(snapshot_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    rt_result = await db.execute(
        select(MachineRuntimeLog.activity_type, func.sum(MachineRuntimeLog.duration_minutes))
        .where(
            MachineRuntimeLog.machine_id == machine_id,
            MachineRuntimeLog.start_time >= day_start,
            MachineRuntimeLog.start_time < day_end,
            MachineRuntimeLog.duration_minutes.isnot(None),
        )
        .group_by(MachineRuntimeLog.activity_type)
    )
    rt_map = {row[0]: _D(str(row[1] or 0)) for row in rt_result.all()}

    snap.setup_time_min = rt_map.get(RuntimeActivity.SETUP, _D("0"))
    snap.run_time_min = rt_map.get(RuntimeActivity.RUNNING, _D("0"))
    snap.downtime_min = rt_map.get(RuntimeActivity.DOWNTIME, _D("0"))
    snap.cleanup_time_min = rt_map.get(RuntimeActivity.CLEANUP, _D("0"))
    snap.changeover_time_min = rt_map.get(RuntimeActivity.CHANGEOVER, _D("0"))
    snap.idle_time_min = rt_map.get(RuntimeActivity.IDLE, _D("0"))

    planned = _D(str(snap.planned_time_min))
    productive = snap.run_time_min
    snap.availability = (
        ((planned - snap.downtime_min) / planned).quantize(_D("0.0001"))
        if planned > 0 else None
    )

    machine = await get_machine(db, machine_id)
    if machine and machine.rated_capacity_per_hour and snap.run_time_min > 0:
        ideal_units = machine.rated_capacity_per_hour * snap.run_time_min / _D("60")
        if ideal_units > 0 and snap.units_produced > 0:
            snap.performance = (snap.units_produced / ideal_units).quantize(_D("0.0001"))
        snap.rated_speed = machine.rated_capacity_per_hour

    if snap.units_produced > 0:
        snap.quality_rate = (snap.good_units / snap.units_produced).quantize(_D("0.0001"))

    if snap.availability and snap.performance and snap.quality_rate:
        snap.oee = (snap.availability * snap.performance * snap.quality_rate).quantize(_D("0.0001"))
        snap.low_oee_flag = snap.oee < _D("0.65")

    if planned > 0:
        snap.utilization_pct = ((snap.run_time_min + snap.setup_time_min) / planned).quantize(_D("0.0001"))

    snap.high_downtime_flag = (snap.downtime_min / max(planned, _D("1"))) > _D("0.20")
    snap.anomaly_flag = snap.low_oee_flag or snap.high_downtime_flag

    if machine and machine.hourly_cost_rate:
        snap.machine_cost_actual = (
            (snap.run_time_min + snap.setup_time_min + snap.cleanup_time_min) / _D("60") * machine.hourly_cost_rate
        ).quantize(_D("0.01"))
    if machine and machine.energy_cost_per_hour:
        snap.energy_cost_actual = (snap.run_time_min / _D("60") * machine.energy_cost_per_hour).quantize(_D("0.01"))

    lt_result = await db.execute(
        select(func.sum(LaborTimeLog.duration_minutes), func.sum(LaborTimeLog.cost_rate_at_time))
        .join(OperatorProfile, LaborTimeLog.operator_id == OperatorProfile.id)
        .where(
            LaborTimeLog.start_time >= day_start,
            LaborTimeLog.start_time < day_end,
        )
    )
    lt_row = lt_result.one()
    if lt_row[0] and lt_row[1]:
        snap.labor_cost_actual = (_D(str(lt_row[0])) / _D("60") * _D(str(lt_row[1]))).quantize(_D("0.01"))

    await db.commit()
    await db.refresh(snap)
    return snap


async def list_performance_snapshots(
    db: AsyncSession,
    machine_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 100,
) -> List[MachinePerformanceSnapshot]:
    q = select(MachinePerformanceSnapshot).order_by(MachinePerformanceSnapshot.snapshot_date.desc())
    if machine_id:
        q = q.where(MachinePerformanceSnapshot.machine_id == machine_id)
    if date_from:
        q = q.where(MachinePerformanceSnapshot.snapshot_date >= date_from)
    if date_to:
        q = q.where(MachinePerformanceSnapshot.snapshot_date <= date_to)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Downtime Intelligence ─────────────────────────────────────────────────────

async def log_downtime(db: AsyncSession, data: DowntimeIntelCreate) -> DowntimeIntelligence:
    duration = _duration(data.start_time, data.end_time)
    machine = await get_machine(db, data.machine_id)
    cost_impact = None
    if duration and machine and machine.hourly_cost_rate:
        cost_impact = (duration / _D("60") * machine.hourly_cost_rate).quantize(_D("0.01"))

    repeat = await _check_repeat_downtime(db, data.machine_id, data.downtime_class)

    dt = DowntimeIntelligence(
        **data.model_dump(),
        duration_minutes=duration,
        cost_impact=cost_impact,
        repeat_occurrence=repeat,
    )
    db.add(dt)
    await db.commit()
    await db.refresh(dt)
    return dt


async def _check_repeat_downtime(
    db: AsyncSession, machine_id: UUID, dc: DowntimeClass, window_days: int = 7
) -> bool:
    cutoff = _now() - timedelta(days=window_days)
    result = await db.execute(
        select(func.count(DowntimeIntelligence.id)).where(
            DowntimeIntelligence.machine_id == machine_id,
            DowntimeIntelligence.downtime_class == dc,
            DowntimeIntelligence.start_time >= cutoff,
        )
    )
    return (result.scalar() or 0) >= 2


async def list_downtime(
    db: AsyncSession,
    machine_id: Optional[UUID] = None,
    downtime_class: Optional[DowntimeClass] = None,
    limit: int = 100,
) -> List[DowntimeIntelligence]:
    q = select(DowntimeIntelligence).order_by(DowntimeIntelligence.start_time.desc())
    if machine_id:
        q = q.where(DowntimeIntelligence.machine_id == machine_id)
    if downtime_class:
        q = q.where(DowntimeIntelligence.downtime_class == downtime_class)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Cost Contribution ─────────────────────────────────────────────────────────

async def get_cost_contribution(
    db: AsyncSession, production_order_id: UUID
) -> CostContribution:
    rt_result = await db.execute(
        select(
            MachineRuntimeLog.activity_type,
            func.sum(MachineRuntimeLog.duration_minutes),
        )
        .where(MachineRuntimeLog.production_order_id == production_order_id)
        .group_by(MachineRuntimeLog.activity_type)
    )
    rt_map = {r[0]: _D(str(r[1] or 0)) for r in rt_result.all()}

    run_min = rt_map.get(RuntimeActivity.RUNNING, _D("0"))
    setup_min = rt_map.get(RuntimeActivity.SETUP, _D("0"))
    run_hrs = run_min / _D("60")
    setup_hrs = setup_min / _D("60")

    machines_result = await db.execute(
        select(Machine.hourly_cost_rate, Machine.energy_cost_per_hour)
        .join(MachineRuntimeLog, MachineRuntimeLog.machine_id == Machine.id)
        .where(MachineRuntimeLog.production_order_id == production_order_id)
        .distinct()
    )
    machine_rows = machines_result.all()
    avg_rate = _D("0")
    avg_energy = _D("0")
    if machine_rows:
        rates = [_D(str(r[0] or 0)) for r in machine_rows if r[0]]
        energies = [_D(str(r[1] or 0)) for r in machine_rows if r[1]]
        avg_rate = sum(rates) / len(rates) if rates else _D("0")
        avg_energy = sum(energies) / len(energies) if energies else _D("0")

    machine_cost_runtime = (run_hrs * avg_rate).quantize(_D("0.01"))
    machine_cost_setup = (setup_hrs * avg_rate).quantize(_D("0.01"))
    machine_cost_energy = (run_hrs * avg_energy).quantize(_D("0.01"))
    machine_cost_total = machine_cost_runtime + machine_cost_setup + machine_cost_energy

    lt_result = await db.execute(
        select(
            func.sum(LaborTimeLog.duration_minutes),
            func.sum(LaborTimeLog.overtime_minutes),
            func.sum(LaborTimeLog.cost_rate_at_time),
        )
        .where(LaborTimeLog.production_order_id == production_order_id)
    )
    lt_row = lt_result.one()
    labor_direct_min = _D(str(lt_row[0] or 0))
    labor_ot_min = _D(str(lt_row[1] or 0))
    labor_rate_sum = _D(str(lt_row[2] or 0))
    labor_direct_hrs = labor_direct_min / _D("60")
    labor_ot_hrs = labor_ot_min / _D("60")
    labor_cost_direct = (labor_direct_hrs * labor_rate_sum).quantize(_D("0.01"))
    labor_cost_overtime = (labor_ot_hrs * labor_rate_sum * _D("1.5")).quantize(_D("0.01"))
    labor_cost_total = labor_cost_direct + labor_cost_overtime

    return CostContribution(
        production_order_id=production_order_id,
        machine_runtime_hours=run_hrs,
        machine_setup_hours=setup_hrs,
        machine_cost_runtime=machine_cost_runtime,
        machine_cost_setup=machine_cost_setup,
        machine_cost_energy=machine_cost_energy,
        machine_cost_total=machine_cost_total,
        labor_direct_hours=labor_direct_hrs,
        labor_overtime_hours=labor_ot_hrs,
        labor_cost_direct=labor_cost_direct,
        labor_cost_overtime=labor_cost_overtime,
        labor_cost_total=labor_cost_total,
        total_cost=machine_cost_total + labor_cost_total,
    )


# ── Supervisor Review ─────────────────────────────────────────────────────────

async def create_review(
    db: AsyncSession, data: SupervisorReviewCreate, reviewed_by: Optional[UUID]
) -> SupervisorReview:
    r = SupervisorReview(**data.model_dump(), reviewed_by=reviewed_by)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def list_reviews(
    db: AsyncSession, entity_type: Optional[str] = None, limit: int = 50
) -> List[SupervisorReview]:
    q = select(SupervisorReview).order_by(SupervisorReview.reviewed_at.desc())
    if entity_type:
        q = q.where(SupervisorReview.entity_type == entity_type)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    today = date.today()

    total_machines = await db.execute(select(func.count(Machine.id)).where(Machine.active_flag == True))
    active_machines = await db.execute(select(func.count(Machine.id)).where(Machine.status == MachineStatus.ACTIVE))
    maintenance_machines = await db.execute(select(func.count(Machine.id)).where(Machine.status == MachineStatus.MAINTENANCE))
    total_operators = await db.execute(select(func.count(OperatorProfile.id)).where(OperatorProfile.active_flag == True))
    total_teams = await db.execute(select(func.count(ProductionTeam.id)).where(ProductionTeam.active_flag == True))
    expiring_certs = await db.execute(
        select(func.count(OperatorSkillCert.id)).where(
            OperatorSkillCert.cert_status.in_([CertStatus.EXPIRING_SOON, CertStatus.EXPIRED])
        )
    )

    avg_oee = await db.execute(
        select(func.avg(MachinePerformanceSnapshot.oee)).where(
            MachinePerformanceSnapshot.snapshot_date == today,
            MachinePerformanceSnapshot.oee.isnot(None),
        )
    )

    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    dt_today = await db.execute(
        select(func.coalesce(func.sum(DowntimeIntelligence.duration_minutes), 0)).where(
            DowntimeIntelligence.start_time >= today_start
        )
    )
    pending_ai = await db.execute(
        select(func.count(MOAIRecommendation.id)).where(MOAIRecommendation.status == MOAIRecStatus.PENDING)
    )

    recent_dt = await db.execute(
        select(DowntimeIntelligence).order_by(DowntimeIntelligence.start_time.desc()).limit(5)
    )
    ai_recs = await db.execute(
        select(MOAIRecommendation).where(MOAIRecommendation.status == MOAIRecStatus.PENDING)
        .order_by(MOAIRecommendation.created_at.desc()).limit(5)
    )

    oee_val = avg_oee.scalar()

    return {
        "total_machines": total_machines.scalar() or 0,
        "machines_active": active_machines.scalar() or 0,
        "machines_maintenance": maintenance_machines.scalar() or 0,
        "total_operators": total_operators.scalar() or 0,
        "total_teams": total_teams.scalar() or 0,
        "expiring_certs": expiring_certs.scalar() or 0,
        "avg_oee_today": _D(str(oee_val)).quantize(_D("0.0001")) if oee_val else None,
        "total_downtime_today_min": _D(str(dt_today.scalar() or 0)),
        "pending_ai_recs": pending_ai.scalar() or 0,
        "recent_downtime": recent_dt.scalars().all(),
        "ai_recommendations": ai_recs.scalars().all(),
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[MOAIRecommendation]:
    recs: List[MOAIRecommendation] = []

    # Agent 1: Performance Anomaly Detector
    today = date.today()
    snaps = await list_performance_snapshots(
        db, date_from=today - timedelta(days=7), date_to=today, limit=200
    )
    low_oee = [s for s in snaps if s.low_oee_flag or s.high_downtime_flag]
    if low_oee:
        for s in low_oee[:3]:
            r = MOAIRecommendation(
                agent_type=MOAIAgentType.PERFORMANCE_ANOMALY,
                status=MOAIRecStatus.PENDING,
                machine_id=s.machine_id,
                title=f"OEE anomaly detected on {s.snapshot_date}",
                description=(
                    f"OEE: {float(s.oee or 0) * 100:.1f}%, Downtime: {s.downtime_min} min. "
                    f"Availability: {float(s.availability or 0) * 100:.1f}%. "
                    "Review downtime root cause and maintenance log."
                ),
                severity="high" if s.low_oee_flag else "medium",
                confidence_score=_D("85"),
                estimated_impact="Production shortfall and cost overrun",
            )
            db.add(r)
            recs.append(r)

    # Agent 2: Productivity Optimizer — check cert expiry backlog
    expiring = await list_skills(db, expiring_only=True)
    if expiring:
        r = MOAIRecommendation(
            agent_type=MOAIAgentType.PRODUCTIVITY_OPTIMIZER,
            status=MOAIRecStatus.PENDING,
            title=f"{len(expiring)} certification(s) expiring or expired",
            description=(
                f"{len(expiring)} operator certifications need renewal. "
                "Expired certs block assignment. Schedule refresher training."
            ),
            severity="high" if any(s.cert_status == CertStatus.EXPIRED for s in expiring) else "medium",
            confidence_score=_D("99"),
            estimated_impact="Assignment blocks and compliance risk",
        )
        db.add(r)
        recs.append(r)

    # Agent 3: Cost Variance — chronic downtime cost
    chronic = await db.execute(
        select(DowntimeIntelligence.machine_id, func.sum(DowntimeIntelligence.cost_impact))
        .where(
            DowntimeIntelligence.start_time >= datetime.combine(today - timedelta(days=30), datetime.min.time()).replace(tzinfo=timezone.utc),
            DowntimeIntelligence.cost_impact.isnot(None),
        )
        .group_by(DowntimeIntelligence.machine_id)
        .having(func.sum(DowntimeIntelligence.cost_impact) > 10000)
        .order_by(func.sum(DowntimeIntelligence.cost_impact).desc())
        .limit(3)
    )
    for row in chronic.all():
        r = MOAIRecommendation(
            agent_type=MOAIAgentType.COST_VARIANCE,
            status=MOAIRecStatus.PENDING,
            machine_id=row[0],
            title="High downtime cost detected",
            description=(
                f"KES {_D(str(row[1])).quantize(_D('0.01')):,} in downtime cost in last 30 days. "
                "Review maintenance strategy and failure modes."
            ),
            severity="high",
            confidence_score=_D("78"),
            estimated_impact=f"KES {_D(str(row[1])).quantize(_D('0.01')):,} cost at risk",
        )
        db.add(r)
        recs.append(r)

    if recs:
        await db.commit()
    return recs


async def action_ai_rec(
    db: AsyncSession, rec_id: UUID, data: MOAIRecAction, actioned_by: Optional[UUID]
) -> MOAIRecommendation:
    result = await db.execute(select(MOAIRecommendation).where(MOAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = data.status
    rec.actioned_by = actioned_by
    rec.actioned_at = _now()
    rec.action_notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_ai_recs(
    db: AsyncSession,
    agent_type: Optional[MOAIAgentType] = None,
    status: Optional[MOAIRecStatus] = None,
    limit: int = 50,
) -> List[MOAIRecommendation]:
    q = select(MOAIRecommendation).order_by(MOAIRecommendation.created_at.desc())
    if agent_type:
        q = q.where(MOAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(MOAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
