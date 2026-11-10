from __future__ import annotations
import uuid
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value
from app.core.access_control import can_modify_scope, has_any_permission
from app.core.access_control import has_any_permission

from app.models.machine_operator import (
    Machine, OperatorProfile, ProductionTeam, TeamMember,
    OperatorSkillCert, MachineSkillRequirement, WorkOrderAssignment, AssignmentHistory, AssignmentType,
    MachineRuntimeLog, LaborTimeLog, MachinePerformanceSnapshot,
    DowntimeIntelligence, SupervisorReview, MOAIRecommendation, ReviewType,
    MachineStatus, CertStatus, RuntimeActivity, MOAIAgentType, MOAIRecStatus,
    DowntimeClass,
)
from app.models.production import ProductionOrder
from app.models.production_advanced import (
    AdvQCInspection, AdvQCResult, Shift, WasteRecord, WorkCenter, WorkOrder, WorkOrderStatus,
)
from app.models.training import SkillMaster
from app.services.master_stewardship import record_master_data_change, snapshot_master_data
from app.services.oee_calculation import calculate_oee_components
from app.services.downtime_reason_service import validate_downtime_reason_code
from app.schemas.machine_operator import (
    MachineCreate, MachineUpdate, OperatorProfileCreate,
    TeamCreate, TeamMemberAdd, SkillCertCreate,
    MachineSkillRequirementCreate, MachineSkillRequirementUpdate,
    AssignmentCreate, AssignmentValidateRequest, AssignmentValidateResult,
    MachineRuntimeKpisOut, MachineRuntimeActivityKpi,
    OperatorProductivityByUom, OperatorProductivityOut,
    RuntimeLogCreate, LaborTimeCreate, DowntimeIntelCreate,
    SupervisorReviewCreate, MOAIRecAction, CostContribution,
    MachineCostAttribution, LaborCostAttribution,
    ShiftTeamComparisonsOut, ShiftTeamComparisonGroup,
    ComparisonRuntimeActivity, ComparisonOutputByUom,
    PerformanceAnomalyReportOut, MachinePerformanceAnomaly,
    DowntimeProductionCorrelationReport, DowntimeProductionCorrelation,
    MachineInsightFollowUpHandoff,
    CorrelatedLaborLog, CorrelatedQualityInspection, CorrelatedQualityResult,
    CorrelatedWasteRecord,
)

_D = Decimal
CERTIFICATION_EXPIRING_SOON_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


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

async def create_skill_cert(
    db: AsyncSession,
    data: SkillCertCreate,
    *,
    actor: Any,
) -> OperatorSkillCert:
    if data.skill_id is not None:
        skill_result = await db.execute(
            select(SkillMaster.skill_id).where(
                SkillMaster.skill_id == data.skill_id,
                SkillMaster.active_flag.is_(True),
            )
        )
        if skill_result.scalar_one_or_none() is None:
            raise ValueError("An active canonical training skill is required")
    cert_status = _compute_cert_status(data.certification_expiry, data.certification_required)
    sc = OperatorSkillCert(
        **data.model_dump(),
        cert_status=cert_status,
        approved_by=actor.id if data.approved_flag else None,
    )
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
    if expiry <= today + timedelta(days=CERTIFICATION_EXPIRING_SOON_DAYS):
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
    result = await db.execute(q)
    certs = result.scalars().all()
    expiring_statuses = {CertStatus.EXPIRING_SOON, CertStatus.EXPIRED}
    current_certs: List[OperatorSkillCert] = []
    for cert in certs:
        current_status = _compute_cert_status(cert.certification_expiry, cert.certification_required)
        # Expiry status is date-derived. Refresh the loaded value for API output
        # without dirtying the session or making a GET persist unrelated writes.
        set_committed_value(cert, "cert_status", current_status)
        if not expiring_only or current_status in expiring_statuses:
            current_certs.append(cert)
    return current_certs


async def refresh_cert_statuses(db: AsyncSession) -> int:
    result = await db.execute(select(OperatorSkillCert))
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


async def list_machine_skill_requirements(
    db: AsyncSession,
    *,
    machine_id: Optional[UUID] = None,
    work_center_id: Optional[UUID] = None,
    active_only: bool = True,
) -> List[MachineSkillRequirement]:
    query = select(MachineSkillRequirement).order_by(
        MachineSkillRequirement.created_at.desc(), MachineSkillRequirement.id
    )
    if machine_id is not None:
        query = query.where(MachineSkillRequirement.machine_id == machine_id)
    if work_center_id is not None:
        query = query.where(MachineSkillRequirement.work_center_id == work_center_id)
    if active_only:
        query = query.where(MachineSkillRequirement.active_flag.is_(True))
    result = await db.execute(query)
    return result.scalars().all()


async def _validate_requirement_references(
    db: AsyncSession,
    *,
    machine_id: Optional[UUID],
    work_center_id: Optional[UUID],
    skill_id: UUID,
) -> None:
    if (machine_id is None) == (work_center_id is None):
        raise ValueError("A qualification requirement must target exactly one machine or work center")

    if machine_id is not None:
        result = await db.execute(select(Machine.id).where(Machine.id == machine_id))
        if result.scalar_one_or_none() is None:
            raise ValueError("Machine not found")
    else:
        result = await db.execute(select(WorkCenter.id).where(WorkCenter.id == work_center_id))
        if result.scalar_one_or_none() is None:
            raise ValueError("Work center not found")

    result = await db.execute(
        select(SkillMaster.skill_id).where(
            SkillMaster.skill_id == skill_id,
            SkillMaster.active_flag.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise ValueError("An active canonical training skill is required")


async def create_machine_skill_requirement(
    db: AsyncSession,
    data: MachineSkillRequirementCreate,
    *,
    actor: Any,
) -> MachineSkillRequirement:
    await _validate_requirement_references(
        db,
        machine_id=data.machine_id,
        work_center_id=data.work_center_id,
        skill_id=data.skill_id,
    )
    target_filter = (
        MachineSkillRequirement.machine_id == data.machine_id
        if data.machine_id is not None
        else MachineSkillRequirement.work_center_id == data.work_center_id
    )
    duplicate = await db.execute(
        select(MachineSkillRequirement.id).where(
            target_filter,
            MachineSkillRequirement.skill_id == data.skill_id,
        )
    )
    if duplicate.scalar_one_or_none() is not None:
        raise ValueError("This skill requirement already exists for the selected resource")

    requirement = MachineSkillRequirement(
        **data.model_dump(),
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(requirement)
    await db.flush()
    await record_master_data_change(
        db,
        record=requirement,
        actor=actor,
        action="CREATE",
        permission="production.edit",
        audit_context={"scope": "machine_or_work_center_qualification"},
    )
    await db.commit()
    await db.refresh(requirement)
    return requirement


async def update_machine_skill_requirement(
    db: AsyncSession,
    requirement_id: UUID,
    data: MachineSkillRequirementUpdate,
    *,
    actor: Any,
) -> Optional[MachineSkillRequirement]:
    result = await db.execute(
        select(MachineSkillRequirement)
        .where(MachineSkillRequirement.id == requirement_id)
        .with_for_update()
    )
    requirement = result.scalar_one_or_none()
    if requirement is None:
        return None

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("At least one qualification requirement field must be provided")
    if any(value is None for key, value in changes.items() if key not in {"machine_id", "work_center_id", "notes"}):
        raise ValueError("Qualification requirement values cannot be null")

    machine_id = changes.get("machine_id", requirement.machine_id)
    work_center_id = changes.get("work_center_id", requirement.work_center_id)
    skill_id = changes.get("skill_id", requirement.skill_id)
    await _validate_requirement_references(
        db,
        machine_id=machine_id,
        work_center_id=work_center_id,
        skill_id=skill_id,
    )

    target_filter = (
        MachineSkillRequirement.machine_id == machine_id
        if machine_id is not None
        else MachineSkillRequirement.work_center_id == work_center_id
    )
    duplicate = await db.execute(
        select(MachineSkillRequirement.id).where(
            target_filter,
            MachineSkillRequirement.skill_id == skill_id,
            MachineSkillRequirement.id != requirement_id,
        )
    )
    if duplicate.scalar_one_or_none() is not None:
        raise ValueError("This skill requirement already exists for the selected resource")

    before = snapshot_master_data(requirement)
    for key, value in changes.items():
        setattr(requirement, key, value)
    requirement.updated_by = actor.id
    await record_master_data_change(
        db,
        record=requirement,
        actor=actor,
        action="UPDATE",
        permission="production.edit",
        before=before,
        audit_context={"scope": "machine_or_work_center_qualification"},
    )
    await db.commit()
    await db.refresh(requirement)
    return requirement


_SKILL_LEVEL_RANK = {"trainee": 0, "basic": 1, "intermediate": 2, "advanced": 3, "expert": 4}


async def validate_operator_qualification(
    db: AsyncSession,
    *,
    operator_id: Optional[UUID],
    machine_id: Optional[UUID],
    work_center_id: Optional[UUID],
) -> tuple[List[str], List[str]]:
    """Return qualification blockers and warnings for a configured resource."""
    if machine_id is not None:
        machine_result = await db.execute(select(Machine).where(Machine.id == machine_id))
        machine = machine_result.scalar_one_or_none()
        if machine is not None:
            if work_center_id is None:
                work_center_id = machine.work_center_id
            elif machine.work_center_id is not None and machine.work_center_id != work_center_id:
                return ["Selected machine does not belong to the work order's work center"], []

    resource_filters = []
    if machine_id is not None:
        resource_filters.append(MachineSkillRequirement.machine_id == machine_id)
    if work_center_id is not None:
        resource_filters.append(MachineSkillRequirement.work_center_id == work_center_id)
    if not resource_filters:
        return [], []

    requirements_result = await db.execute(
        select(MachineSkillRequirement).where(
            MachineSkillRequirement.active_flag.is_(True),
            or_(*resource_filters),
        )
    )
    requirements = requirements_result.scalars().all()
    if not requirements:
        return [], []
    if operator_id is None:
        return ["An operator must be assigned before this qualified resource can be used"], []

    operator_result = await db.execute(
        select(OperatorProfile).where(
            OperatorProfile.id == operator_id,
            OperatorProfile.active_flag.is_(True),
        )
    )
    operator = operator_result.scalar_one_or_none()
    if operator is None:
        return ["The assigned operator is missing or inactive"], []

    skill_ids = {requirement.skill_id for requirement in requirements}
    certificates_result = await db.execute(
        select(OperatorSkillCert).where(
            OperatorSkillCert.operator_id == operator_id,
            OperatorSkillCert.skill_id.in_(skill_ids),
            OperatorSkillCert.approved_flag.is_(True),
        )
    )
    certificates = certificates_result.scalars().all()
    blockers: List[str] = []
    warnings: List[str] = []

    for requirement in requirements:
        minimum_rank = _SKILL_LEVEL_RANK[requirement.minimum_skill_level]
        matched = False
        expiring_match = False
        for certificate in certificates:
            if certificate.skill_id != requirement.skill_id:
                continue
            is_global = certificate.machine_id is None and certificate.work_center_id is None
            scope_matches = is_global or (
                (certificate.machine_id is None or certificate.machine_id == machine_id)
                and (certificate.work_center_id is None or certificate.work_center_id == work_center_id)
            )
            certificate_level = getattr(certificate.skill_level, "value", certificate.skill_level)
            if not scope_matches or _SKILL_LEVEL_RANK.get(str(certificate_level).lower(), -1) < minimum_rank:
                continue

            status = _compute_cert_status(
                certificate.certification_expiry,
                certificate.certification_required,
            )
            if requirement.certification_required and (
                not certificate.certification_required
                or status in {CertStatus.PENDING, CertStatus.EXPIRED, CertStatus.BLOCKED}
            ):
                expiring_match = expiring_match or status == CertStatus.EXPIRING_SOON
                continue

            matched = True
            expiring_match = status == CertStatus.EXPIRING_SOON
            break

        if not matched:
            blockers.append(f"Operator lacks an approved {requirement.minimum_skill_level} qualification for skill {requirement.skill_id}")
            if expiring_match:
                warnings.append(f"Required certification for skill {requirement.skill_id} expires within {CERTIFICATION_EXPIRING_SOON_DAYS} days")
        elif expiring_match:
            warnings.append(f"Certification for skill {requirement.skill_id} expires within {CERTIFICATION_EXPIRING_SOON_DAYS} days")

    return blockers, warnings


# ── Assignment Validation ─────────────────────────────────────────────────────

async def validate_assignment(
    db: AsyncSession, req: AssignmentValidateRequest
) -> AssignmentValidateResult:
    warnings: List[str] = []
    blocks: List[str] = []
    operator_certified = True
    machine_available = True
    work_center_id: Optional[UUID] = None

    work_order_result = await db.execute(select(WorkOrder).where(WorkOrder.id == req.work_order_id))
    work_order = work_order_result.scalar_one_or_none()
    if work_order is None:
        blocks.append("Work order not found")
    else:
        work_center_id = work_order.work_center_id

    if req.machine_id:
        m = await get_machine(db, req.machine_id)
        if not m:
            blocks.append("Machine not found")
        elif m.status == MachineStatus.MAINTENANCE:
            warnings.append(f"Machine {m.machine_code} is currently in MAINTENANCE")
        elif m.status in (MachineStatus.INACTIVE, MachineStatus.RETIRED):
            blocks.append(f"Machine {m.machine_code} is {m.status.value}")
            machine_available = False
        elif work_center_id and m.work_center_id and m.work_center_id != work_center_id:
            blocks.append("Selected machine does not belong to the work order's work center")
            machine_available = False

    if req.operator_id and req.machine_id:
        skills = await list_skills(db, operator_id=req.operator_id, machine_id=req.machine_id)
        if not skills:
            warnings.append("No skill record for this operator-machine pair")
        else:
            for s in skills:
                if s.skill_id is None and s.cert_status == CertStatus.EXPIRED and s.certification_required:
                    blocks.append(f"Certification expired for {s.operation_code or 'this machine'}")
                    operator_certified = False
                elif s.skill_id is None and s.cert_status == CertStatus.EXPIRING_SOON:
                    warnings.append("Certification expiring within 30 days")

    qualification_blocks, qualification_warnings = await validate_operator_qualification(
        db,
        operator_id=req.operator_id,
        machine_id=req.machine_id,
        work_center_id=work_center_id,
    )
    if qualification_blocks:
        blocks.extend(qualification_blocks)
        operator_certified = False
    warnings.extend(qualification_warnings)

    return AssignmentValidateResult(
        valid=len(blocks) == 0,
        warnings=warnings,
        blocks=blocks,
        operator_certified=operator_certified,
        machine_available=machine_available,
    )


async def _has_work_order_scope_permission(
    db: AsyncSession,
    actor: Any,
    *,
    action: str,
    work_order_id: UUID,
    machine_id: Optional[UUID],
) -> bool:
    if has_any_permission(actor, (f"production.{action}", f"production.{action}_all")):
        return True
    scoped_permission_codes = (
        f"production.{action}_own_scope",
        f"production.{action}_own_machine",
        f"production.{action}_own_factory",
        f"production.{action}_own_section",
        f"production.{action}_own_production_line",
        f"production.{action}_own_work_center",
    )
    if not has_any_permission(actor, scoped_permission_codes):
        return False

    order_result = await db.execute(select(WorkOrder).where(WorkOrder.id == work_order_id))
    work_order = order_result.scalar_one_or_none()
    if work_order is None:
        return False

    def machine_allowed(machine: Machine) -> bool:
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
            can_modify_scope(actor, "production", action, scope_type, scope_id)
            for scope_type, scope_id in scopes
        )

    if machine_id is not None:
        result = await db.execute(select(Machine).where(Machine.id == machine_id))
        machine = result.scalar_one_or_none()
        return bool(
            machine is not None
            and (work_order.work_center_id is None or machine.work_center_id == work_order.work_center_id)
            and machine_allowed(machine)
        )

    work_center_id = work_order.work_center_id
    if work_center_id is None:
        return False
    if can_modify_scope(actor, "production", action, "work_center", work_center_id):
        return True

    result = await db.execute(select(Machine).where(Machine.work_center_id == work_center_id))
    machines = result.scalars().all()
    return bool(machines) and all(machine_allowed(machine) for machine in machines)


# ── Work Order Assignment ─────────────────────────────────────────────────────

async def create_assignment(
    db: AsyncSession, data: AssignmentCreate, *, actor: Any
) -> WorkOrderAssignment:
    validation = await validate_assignment(db, AssignmentValidateRequest(
        work_order_id=data.work_order_id,
        machine_id=data.machine_id,
        operator_id=data.operator_id,
    ))
    required_action = "approve" if data.cert_override_flag else "edit"
    if not await _has_work_order_scope_permission(
        db,
        actor,
        action=required_action,
        work_order_id=data.work_order_id,
        machine_id=data.machine_id,
    ):
        permission_label = "approval" if data.cert_override_flag else "edit"
        raise ValueError(f"Production {permission_label} permission and work-order scope are required")

    qualification_blocks: List[str] = []
    if data.cert_override_flag:
        reason = (data.cert_override_reason or "").strip()
        if not reason:
            raise ValueError("A non-empty audit reason is required for a qualification override")
        if len(reason) > 500:
            raise ValueError("Qualification override reason must be 500 characters or fewer")
        qualification_blocks = [
            block for block in validation.blocks
            if "qualification" in block.lower() or "certification expired" in block.lower()
        ]
        non_qualification_blocks = [block for block in validation.blocks if block not in qualification_blocks]
        if not qualification_blocks:
            raise ValueError("A qualification override is only valid when a qualification check blocks assignment")
        if non_qualification_blocks:
            raise ValueError(f"Assignment has non-qualification blockers that cannot be overridden: {'; '.join(non_qualification_blocks)}")
        data.cert_override_reason = reason
    elif data.cert_override_reason is not None:
        raise ValueError("An override reason can only be supplied when cert_override_flag is enabled")

    if not validation.valid and not data.cert_override_flag:
        raise ValueError(f"Assignment blocked: {'; '.join(validation.blocks)}")

    assignment = WorkOrderAssignment(
        **data.model_dump(),
        assigned_by=actor.id,
        cert_validation_passed=validation.valid and not data.cert_override_flag,
    )
    db.add(assignment)

    hist = AssignmentHistory(
        work_order_id=data.work_order_id,
        assignment_type=AssignmentType.OPERATOR,
        new_value=str(data.operator_id) if data.operator_id else None,
        changed_by=actor.id,
        reason=(
            f"Supervisor qualification override: {data.cert_override_reason}"
            if data.cert_override_flag
            else "Initial assignment"
        ),
    )
    db.add(hist)
    if data.cert_override_flag:
        await db.flush()
        db.add(
            SupervisorReview(
                entity_type="WORK_ORDER_ASSIGNMENT",
                entity_id=assignment.id,
                review_type=ReviewType.CERT_OVERRIDE,
                reviewed_by=actor.id,
                action_taken="QUALIFICATION_OVERRIDE",
                comments=(
                    f"Reason: {data.cert_override_reason}; "
                    f"qualification blockers: {'; '.join(qualification_blocks)}"
                ),
                production_order_id=data.production_order_id,
            )
        )
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


async def get_machine_runtime_kpis(
    db: AsyncSession,
    machine_id: UUID,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Optional[MachineRuntimeKpisOut]:
    machine_result = await db.execute(select(Machine).where(Machine.id == machine_id))
    machine = machine_result.scalar_one_or_none()
    if machine is None:
        return None

    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=29))
    if period_start > period_end:
        raise ValueError("date_from must be on or before date_to")
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_before = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)

    logs_result = await db.execute(
        select(MachineRuntimeLog)
        .where(
            MachineRuntimeLog.machine_id == machine_id,
            MachineRuntimeLog.start_time < end_before,
            or_(MachineRuntimeLog.end_time.is_(None), MachineRuntimeLog.end_time > start_at),
        )
        .order_by(MachineRuntimeLog.start_time, MachineRuntimeLog.id)
    )
    logs = logs_result.scalars().all()
    by_activity: dict[RuntimeActivity, dict[str, Any]] = {}
    unavailable_ids: list[UUID] = []

    for log in logs:
        if log.end_time is None:
            unavailable_ids.append(log.id)
            continue
        log_start = _as_utc_datetime(log.start_time)
        log_end = _as_utc_datetime(log.end_time)
        if log_end <= log_start:
            unavailable_ids.append(log.id)
            continue
        clipped_start = max(log_start, start_at)
        clipped_end = min(log_end, end_before)
        if clipped_end <= clipped_start:
            continue

        minutes = _D(str((clipped_end - clipped_start).total_seconds() / 60)).quantize(_D("0.01"))
        metric = by_activity.setdefault(
            log.activity_type,
            {"minutes": _D("0"), "ids": []},
        )
        metric["minutes"] += minutes
        metric["ids"].append(log.id)

    activities = [
        MachineRuntimeActivityKpi(
            activity_type=activity,
            duration_minutes=metric["minutes"].quantize(_D("0.01")),
            log_count=len(metric["ids"]),
            source_runtime_log_ids=metric["ids"],
        )
        for activity, metric in sorted(by_activity.items(), key=lambda item: item[0].value)
    ]
    recorded_minutes = sum((item.duration_minutes for item in activities), _D("0"))

    return MachineRuntimeKpisOut(
        machine_id=machine.id,
        machine_code=machine.machine_code,
        machine_name=machine.machine_name,
        period_start=period_start,
        period_end=period_end,
        recorded_activity_log_minutes=recorded_minutes.quantize(_D("0.01")),
        activities=activities,
        unavailable_runtime_log_ids=unavailable_ids,
        data_notes=[
            "Activity minutes are derived from runtime-log start/end timestamps and clipped to the selected UTC calendar dates.",
            "Totals sum recorded activity logs; overlapping logs are counted separately and are not treated as machine availability or utilization.",
            "Open or invalid runtime intervals are listed as unavailable; no runtime, availability, throughput, or OEE values are estimated.",
        ],
    )


def build_machine_insight_follow_up_handoffs(
    correlations: DowntimeProductionCorrelationReport,
    anomalies: PerformanceAnomalyReportOut,
) -> list[MachineInsightFollowUpHandoff]:
    """Create review-only module handoffs from explicitly linked recorded evidence."""
    anomalies_by_runtime_id = {item.runtime_log_id: item for item in anomalies.anomalies}
    handoffs: list[MachineInsightFollowUpHandoff] = []

    def add_handoff(
        event: DowntimeProductionCorrelation,
        *,
        destination: str,
        destination_path: str,
        title: str,
        rationale: str,
        source_ids: list[UUID],
    ) -> None:
        unique_source_ids = list(dict.fromkeys(source_ids))
        handoffs.append(
            MachineInsightFollowUpHandoff(
                handoff_id=f"{destination}:{event.downtime_id}",
                destination=destination,
                destination_path=destination_path,
                title=title,
                rationale=rationale,
                machine_id=event.machine_id,
                machine_code=event.machine_code,
                downtime_id=event.downtime_id,
                work_order_id=event.work_order_id,
                production_order_id=event.production_order_id,
                source_ids=unique_source_ids,
                attribution_note=(
                    "Review suggestion only. No maintenance, training, or production plan record was created or changed; "
                    "correlation does not establish cause or operator responsibility."
                ),
            )
        )

    for event in correlations.events:
        matching_anomalies = [
            anomalies_by_runtime_id[runtime_id]
            for runtime_id in event.runtime_log_ids
            if runtime_id in anomalies_by_runtime_id
        ]
        if matching_anomalies:
            anomaly_sources = [event.downtime_id]
            for item in matching_anomalies:
                anomaly_sources.extend([item.runtime_log_id, *item.source_baseline_runtime_log_ids])
            add_handoff(
                event,
                destination="maintenance",
                destination_path="/dashboard/maintenance?tab=breakdowns",
                title="Review machine downtime anomaly",
                rationale=(
                    "The recorded runtime interval exceeded the existing machine-specific historical rule. "
                    "Review the downtime event and its baseline evidence in maintenance."
                ),
                source_ids=anomaly_sources,
            )

        failed_inspections = [
            inspection
            for inspection in event.quality_inspections
            if inspection.status.strip().lower() == "fail"
            or any(result.result.strip().lower() == "fail" for result in inspection.results)
        ]
        if failed_inspections and (event.work_order_id or event.production_order_id):
            quality_sources = [event.downtime_id]
            for inspection in failed_inspections:
                quality_sources.append(inspection.inspection_id)
                quality_sources.extend(result.result_id for result in inspection.results if result.result.strip().lower() == "fail")
            quality_sources.extend(log.labor_log_id for log in event.labor_logs)
            add_handoff(
                event,
                destination="training",
                destination_path="/dashboard/training/skill-matrix",
                title="Review work-order training and standard-work context",
                rationale=(
                    "A failed recorded quality inspection is linked to this work order or production order. "
                    "Review applicable training and standard-work records; this evidence does not attribute the result to an operator."
                ),
                source_ids=quality_sources,
            )

        flagged_waste = [waste for waste in event.waste_records if waste.is_anomaly]
        if (matching_anomalies or flagged_waste) and (event.work_order_id or event.production_order_id):
            planning_sources = [event.downtime_id]
            for item in matching_anomalies:
                planning_sources.extend([item.runtime_log_id, *item.source_baseline_runtime_log_ids])
            planning_sources.extend(waste.waste_record_id for waste in flagged_waste)
            add_handoff(
                event,
                destination="planning",
                destination_path="/dashboard/production/scheduling",
                title="Review order schedule and capacity context",
                rationale=(
                    "Recorded downtime anomaly or explicitly flagged waste is linked to this order. "
                    "Review schedule and capacity context; no reschedule or production change was made."
                ),
                source_ids=planning_sources,
            )

    return handoffs


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


async def get_operator_productivity(
    db: AsyncSession,
    operator_id: UUID,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Optional[OperatorProductivityOut]:
    operator = await get_operator(db, operator_id)
    if operator is None:
        return None

    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=29))
    if period_start > period_end:
        raise ValueError("date_from must be on or before date_to")
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_before = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)

    period_result = await db.execute(
        select(LaborTimeLog).where(
            LaborTimeLog.operator_id == operator_id,
            LaborTimeLog.start_time >= start_at,
            LaborTimeLog.start_time < end_before,
        ).order_by(LaborTimeLog.start_time, LaborTimeLog.id)
    )
    period_logs = period_result.scalars().all()
    approved_period_logs = [log for log in period_logs if log.approved_flag]
    approved_minutes = sum(
        (
            _D(str(log.duration_minutes))
            for log in approved_period_logs
            if log.duration_minutes is not None and log.duration_minutes > 0
        ),
        _D("0"),
    )

    completed_result = await db.execute(
        select(WorkOrder, ProductionOrder.uom)
        .join(LaborTimeLog, LaborTimeLog.work_order_id == WorkOrder.id)
        .outerjoin(ProductionOrder, ProductionOrder.id == WorkOrder.production_order_id)
        .where(
            LaborTimeLog.operator_id == operator_id,
            LaborTimeLog.approved_flag.is_(True),
            WorkOrder.status == WorkOrderStatus.COMPLETED,
            WorkOrder.end_time.is_not(None),
            WorkOrder.end_time >= start_at,
            WorkOrder.end_time < end_before,
        )
        .distinct()
    )
    completed_rows = completed_result.all()
    completed_orders = [row[0] for row in completed_rows]
    uom_by_order = {
        row[0].id: row[1].strip() if isinstance(row[1], str) and row[1].strip() else None
        for row in completed_rows
    }

    all_logs_by_order: dict[UUID, list[LaborTimeLog]] = {}
    if completed_orders:
        order_ids = [order.id for order in completed_orders]
        all_logs_result = await db.execute(
            select(LaborTimeLog)
            .join(WorkOrder, WorkOrder.id == LaborTimeLog.work_order_id)
            .where(
                LaborTimeLog.work_order_id.in_(order_ids),
                LaborTimeLog.approved_flag.is_(True),
                LaborTimeLog.duration_minutes.is_not(None),
                LaborTimeLog.duration_minutes > 0,
                WorkOrder.end_time.is_not(None),
                LaborTimeLog.start_time <= WorkOrder.end_time,
            ).order_by(LaborTimeLog.work_order_id, LaborTimeLog.start_time, LaborTimeLog.id)
        )
        for log in all_logs_result.scalars().all():
            all_logs_by_order.setdefault(log.work_order_id, []).append(log)

    by_uom: dict[str, dict[str, Any]] = {}
    unavailable_order_ids: list[UUID] = []
    for order in completed_orders:
        uom = uom_by_order.get(order.id)
        work_order_logs = all_logs_by_order.get(order.id, [])
        total_minutes = sum((_D(str(log.duration_minutes)) for log in work_order_logs), _D("0"))
        operator_logs = [log for log in work_order_logs if log.operator_id == operator_id]
        operator_minutes = sum((_D(str(log.duration_minutes)) for log in operator_logs), _D("0"))
        if order.actual_quantity is None or not uom or total_minutes <= 0 or operator_minutes <= 0:
            unavailable_order_ids.append(order.id)
            continue

        metric = by_uom.setdefault(
            uom,
            {"quantity": _D("0"), "minutes": _D("0"), "orders": set(), "logs": set(), "allocation_logs": set()},
        )
        metric["quantity"] += _D(str(order.actual_quantity)) * operator_minutes / total_minutes
        metric["minutes"] += operator_minutes
        metric["orders"].add(order.id)
        metric["logs"].update(log.id for log in operator_logs)
        metric["allocation_logs"].update(log.id for log in work_order_logs)

    output_by_uom = []
    for uom, metric in sorted(by_uom.items()):
        rate = None
        if metric["minutes"] > 0:
            rate = (metric["quantity"] / (metric["minutes"] / _D("60"))).quantize(_D("0.001"))
        output_by_uom.append(
            OperatorProductivityByUom(
                uom=uom,
                allocated_output_quantity=metric["quantity"].quantize(_D("0.001")),
                operator_labor_minutes_for_completed_orders=metric["minutes"].quantize(_D("0.01")),
                output_quantity_per_operator_labor_hour=rate,
                source_work_order_ids=sorted(metric["orders"], key=str),
                source_labor_log_ids=sorted(metric["logs"], key=str),
                allocation_labor_log_ids=sorted(metric["allocation_logs"], key=str),
            )
        )

    return OperatorProductivityOut(
        operator_id=operator_id,
        period_start=period_start,
        period_end=period_end,
        approved_labor_log_count=len(approved_period_logs),
        unapproved_labor_log_count=sum(1 for log in period_logs if not log.approved_flag),
        approved_labor_minutes=approved_minutes.quantize(_D("0.01")),
        approved_labor_hours=(approved_minutes / _D("60")).quantize(_D("0.001")),
        completed_work_order_count=len(completed_orders),
        unavailable_output_work_order_ids=sorted(set(unavailable_order_ids), key=str),
        output_by_uom=output_by_uom,
        period_labor_log_ids=[log.id for log in period_logs],
        data_notes=[
            "Period labor totals include approved logs started within the selected dates.",
            "Output includes completed work orders finished in the selected dates, allocated by each operator's share of all approved lifetime labor minutes on each work order.",
            "Output uses recorded work-order actual_quantity and production-order UOM; it is not a good-unit or standard-efficiency score.",
            "Work orders without quantity, UOM, or approved labor duration are listed as unavailable instead of being estimated.",
        ],
    )


def _effective_shift_for_log(
    log: Any,
    assignments_by_work_order: dict[UUID, list[WorkOrderAssignment]],
) -> Optional[UUID]:
    """Use the latest recorded assignment at the log time; never infer a shift from a roster."""
    work_order_id = getattr(log, "work_order_id", None)
    if work_order_id is None:
        return None

    log_time = _as_utc_datetime(log.start_time)
    eligible = [
        assignment
        for assignment in assignments_by_work_order.get(work_order_id, [])
        if _as_utc_datetime(assignment.assigned_at) <= log_time
    ]
    if not eligible:
        return None

    latest_time = max(_as_utc_datetime(item.assigned_at) for item in eligible)
    latest = [item for item in eligible if _as_utc_datetime(item.assigned_at) == latest_time]
    if len(latest) != 1:
        return None

    assignment = latest[0]
    matched_resource = False
    for field in ("operator_id", "team_id", "machine_id"):
        assigned_id = getattr(assignment, field, None)
        log_id = getattr(log, field, None)
        if assigned_id is None or log_id is None:
            continue
        if assigned_id != log_id:
            return None
        matched_resource = True

    if not matched_resource:
        return None
    return assignment.shift_id


def _comparison_state(
    group_id: Optional[UUID],
    group_lookup: dict[UUID, Any],
    *,
    unassigned_label: str,
) -> dict[str, Any]:
    entity = group_lookup.get(group_id) if group_id is not None else None
    return {
        "id": group_id,
        "code": getattr(entity, "team_code", getattr(entity, "shift_code", "UNASSIGNED"))
        if entity is not None
        else "UNASSIGNED",
        "name": getattr(entity, "team_name", getattr(entity, "name", unassigned_label))
        if entity is not None
        else unassigned_label,
        "labor": [],
        "runtime": [],
        "unavailable_runtime": [],
        "activities": {},
        "outputs": {},
    }


async def get_shift_team_comparisons(
    db: AsyncSession,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ShiftTeamComparisonsOut:
    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=29))
    if period_start > period_end:
        raise ValueError("date_from must be on or before date_to")

    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_before = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)

    labor_result = await db.execute(
        select(LaborTimeLog)
        .where(LaborTimeLog.start_time >= start_at, LaborTimeLog.start_time < end_before)
        .order_by(LaborTimeLog.start_time, LaborTimeLog.id)
    )
    period_labor_logs = labor_result.scalars().all()

    runtime_result = await db.execute(
        select(MachineRuntimeLog)
        .where(
            MachineRuntimeLog.start_time < end_before,
            or_(MachineRuntimeLog.end_time.is_(None), MachineRuntimeLog.end_time > start_at),
        )
        .order_by(MachineRuntimeLog.start_time, MachineRuntimeLog.id)
    )
    period_runtime_logs = runtime_result.scalars().all()

    completed_result = await db.execute(
        select(WorkOrder, ProductionOrder.uom)
        .outerjoin(ProductionOrder, ProductionOrder.id == WorkOrder.production_order_id)
        .where(
            WorkOrder.status == WorkOrderStatus.COMPLETED,
            WorkOrder.end_time.is_not(None),
            WorkOrder.end_time >= start_at,
            WorkOrder.end_time < end_before,
        )
        .order_by(WorkOrder.end_time, WorkOrder.id)
    )
    completed_rows = completed_result.all()
    completed_orders = [row[0] for row in completed_rows]
    uom_by_order = {
        row[0].id: row[1].strip() if isinstance(row[1], str) and row[1].strip() else None
        for row in completed_rows
    }

    output_logs: list[LaborTimeLog] = []
    if completed_orders:
        output_log_result = await db.execute(
            select(LaborTimeLog)
            .join(WorkOrder, WorkOrder.id == LaborTimeLog.work_order_id)
            .where(
                LaborTimeLog.work_order_id.in_([order.id for order in completed_orders]),
                LaborTimeLog.approved_flag.is_(True),
                LaborTimeLog.duration_minutes.is_not(None),
                LaborTimeLog.duration_minutes > 0,
                WorkOrder.end_time.is_not(None),
                LaborTimeLog.start_time <= WorkOrder.end_time,
            )
            .order_by(LaborTimeLog.work_order_id, LaborTimeLog.start_time, LaborTimeLog.id)
        )
        output_logs = output_log_result.scalars().all()

    relevant_work_order_ids = {
        log.work_order_id
        for log in [*period_labor_logs, *period_runtime_logs, *output_logs]
        if getattr(log, "work_order_id", None) is not None
    }
    assignments_by_work_order: dict[UUID, list[WorkOrderAssignment]] = {}
    if relevant_work_order_ids:
        assignment_result = await db.execute(
            select(WorkOrderAssignment)
            .where(WorkOrderAssignment.work_order_id.in_(relevant_work_order_ids))
            .order_by(WorkOrderAssignment.work_order_id, WorkOrderAssignment.assigned_at)
        )
        for assignment in assignment_result.scalars().all():
            assignments_by_work_order.setdefault(assignment.work_order_id, []).append(assignment)

    team_result = await db.execute(select(ProductionTeam).order_by(ProductionTeam.team_code))
    teams_by_id = {team.id: team for team in team_result.scalars().all()}
    shift_ids = {
        assignment.shift_id
        for assignments in assignments_by_work_order.values()
        for assignment in assignments
        if assignment.shift_id is not None
    }
    shifts_by_id: dict[UUID, Shift] = {}
    if shift_ids:
        shift_result = await db.execute(select(Shift).where(Shift.id.in_(shift_ids)).order_by(Shift.shift_code))
        shifts_by_id = {shift.id: shift for shift in shift_result.scalars().all()}

    team_states: dict[Optional[UUID], dict[str, Any]] = {}
    shift_states: dict[Optional[UUID], dict[str, Any]] = {}

    def state_for(
        states: dict[Optional[UUID], dict[str, Any]],
        key: Optional[UUID],
        lookup: dict[UUID, Any],
        label: str,
    ) -> dict[str, Any]:
        if key not in states:
            states[key] = _comparison_state(key, lookup, unassigned_label=label)
        return states[key]

    for log in period_labor_logs:
        state_for(team_states, log.team_id, teams_by_id, "Unassigned / not recorded")["labor"].append(log)
        shift_id = _effective_shift_for_log(log, assignments_by_work_order)
        state_for(shift_states, shift_id, shifts_by_id, "Unassigned / no effective shift assignment")["labor"].append(log)

    for log in period_runtime_logs:
        state_for(team_states, log.team_id, teams_by_id, "Unassigned / not recorded")["runtime"].append(log)
        shift_id = _effective_shift_for_log(log, assignments_by_work_order)
        state_for(shift_states, shift_id, shifts_by_id, "Unassigned / no effective shift assignment")["runtime"].append(log)

    logs_by_order: dict[UUID, list[LaborTimeLog]] = {}
    for log in output_logs:
        if log.work_order_id is not None:
            logs_by_order.setdefault(log.work_order_id, []).append(log)

    unavailable_output_order_ids: list[UUID] = []
    for order in completed_orders:
        order_logs = logs_by_order.get(order.id, [])
        total_minutes = sum((_D(str(log.duration_minutes)) for log in order_logs), _D("0"))
        uom = uom_by_order.get(order.id)
        if order.actual_quantity is None or not uom or total_minutes <= 0:
            unavailable_output_order_ids.append(order.id)
            continue

        by_dimension: list[tuple[dict[Optional[UUID], dict[str, Any]], dict[Optional[UUID], list[LaborTimeLog]]]] = []
        for states, key_for_log in (
            (team_states, lambda item: item.team_id),
            (shift_states, lambda item: _effective_shift_for_log(item, assignments_by_work_order)),
        ):
            grouped: dict[Optional[UUID], list[LaborTimeLog]] = {}
            for log in order_logs:
                grouped.setdefault(key_for_log(log), []).append(log)
            by_dimension.append((states, grouped))

        for states, grouped in by_dimension:
            for group_id, group_logs in grouped.items():
                group_minutes = sum((_D(str(log.duration_minutes)) for log in group_logs), _D("0"))
                if group_minutes <= 0:
                    continue
                metric = state_for(
                    states,
                    group_id,
                    teams_by_id if states is team_states else shifts_by_id,
                    "Unassigned / not recorded" if states is team_states else "Unassigned / no effective shift assignment",
                )["outputs"].setdefault(
                    uom,
                    {"quantity": _D("0"), "minutes": _D("0"), "orders": set(), "logs": set(), "allocation_logs": set()},
                )
                metric["quantity"] += _D(str(order.actual_quantity)) * group_minutes / total_minutes
                metric["minutes"] += group_minutes
                metric["orders"].add(order.id)
                metric["logs"].update(log.id for log in group_logs)
                metric["allocation_logs"].update(log.id for log in order_logs)

    def serialize_groups(
        states: dict[Optional[UUID], dict[str, Any]],
    ) -> list[ShiftTeamComparisonGroup]:
        serialized = []
        for state in states.values():
            labor_logs: list[LaborTimeLog] = state["labor"]
            runtime_logs: list[MachineRuntimeLog] = state["runtime"]
            approved_logs = [log for log in labor_logs if log.approved_flag]
            approved_minutes = sum(
                (_D(str(log.duration_minutes)) for log in approved_logs if log.duration_minutes is not None and log.duration_minutes > 0),
                _D("0"),
            )
            activity_totals: dict[RuntimeActivity, dict[str, Any]] = {}
            unavailable_runtime_ids: list[UUID] = []
            recorded_runtime_minutes = _D("0")
            for log in runtime_logs:
                log_start = _as_utc_datetime(log.start_time)
                log_end = _as_utc_datetime(log.end_time) if log.end_time is not None else None
                if log_end is None or log_end <= log_start:
                    unavailable_runtime_ids.append(log.id)
                    continue
                clipped_start = max(log_start, start_at)
                clipped_end = min(log_end, end_before)
                if clipped_end <= clipped_start:
                    unavailable_runtime_ids.append(log.id)
                    continue
                minutes = _D(str((clipped_end - clipped_start).total_seconds() / 60)).quantize(_D("0.01"))
                activity = activity_totals.setdefault(log.activity_type, {"minutes": _D("0"), "ids": []})
                activity["minutes"] += minutes
                activity["ids"].append(log.id)
                recorded_runtime_minutes += minutes

            runtime_by_activity = [
                ComparisonRuntimeActivity(
                    activity_type=activity_type,
                    duration_minutes=metric["minutes"].quantize(_D("0.01")),
                    source_runtime_log_ids=sorted(metric["ids"], key=str),
                )
                for activity_type, metric in sorted(activity_totals.items(), key=lambda item: item[0].value)
            ]
            output_by_uom = []
            for uom, metric in sorted(state["outputs"].items()):
                per_hour = (
                    (metric["quantity"] / (metric["minutes"] / _D("60"))).quantize(_D("0.001"))
                    if metric["minutes"] > 0
                    else None
                )
                output_by_uom.append(
                    ComparisonOutputByUom(
                        uom=uom,
                        allocated_output_quantity=metric["quantity"].quantize(_D("0.001")),
                        labor_minutes_for_completed_orders=metric["minutes"].quantize(_D("0.01")),
                        output_quantity_per_labor_hour=per_hour,
                        source_work_order_ids=sorted(metric["orders"], key=str),
                        source_labor_log_ids=sorted(metric["logs"], key=str),
                        allocation_labor_log_ids=sorted(metric["allocation_logs"], key=str),
                    )
                )
            serialized.append(
                ShiftTeamComparisonGroup(
                    group_id=state["id"],
                    group_code=state["code"],
                    group_name=state["name"],
                    approved_labor_log_count=len(approved_logs),
                    unapproved_labor_log_count=sum(1 for log in labor_logs if not log.approved_flag),
                    approved_labor_minutes=approved_minutes.quantize(_D("0.01")),
                    approved_labor_hours=(approved_minutes / _D("60")).quantize(_D("0.001")),
                    runtime_log_count=len(runtime_logs),
                    recorded_runtime_minutes=recorded_runtime_minutes.quantize(_D("0.01")),
                    unavailable_runtime_log_ids=sorted(unavailable_runtime_ids, key=str),
                    runtime_by_activity=runtime_by_activity,
                    source_labor_log_ids=sorted((log.id for log in labor_logs), key=str),
                    source_runtime_log_ids=sorted((log.id for log in runtime_logs), key=str),
                    output_by_uom=output_by_uom,
                )
            )
        return sorted(serialized, key=lambda group: (group.group_id is None, group.group_code))

    return ShiftTeamComparisonsOut(
        period_start=period_start,
        period_end=period_end,
        teams=serialize_groups(team_states),
        shifts=serialize_groups(shift_states),
        unavailable_output_work_order_ids=sorted(set(unavailable_output_order_ids), key=str),
        period_labor_log_ids=[log.id for log in period_labor_logs],
        period_runtime_log_ids=[log.id for log in period_runtime_logs],
        data_notes=[
            "Labor period totals include approved logs started within the selected UTC dates; unapproved logs are counted but excluded from hours and output allocation.",
            "Team attribution uses the team_id recorded on each labor/runtime log. Missing team values remain in the unassigned group; current team membership is not used as historical evidence.",
            "Shift attribution uses the latest work-order assignment recorded at or before each log start, only when its recorded operator/team/machine identifiers match. Missing or ambiguous assignment stays unassigned; shift rosters and wall-clock schedules are not inferred.",
            "Completed work-order actual_quantity is allocated by approved lifetime labor minutes on that work order. The denominator includes unassigned logs, so group allocations do not overstate total output; allocation log IDs are returned for traceability.",
            "Runtime uses recorded start/end intervals clipped to UTC date boundaries. Open or invalid intervals are listed as unavailable; overlapping runtime is counted as recorded activity and is not a utilization percentage.",
            "Output lacking actual quantity, UOM, or approved labor basis is listed as unavailable rather than estimated.",
        ],
    )


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
            planned_time_min=0,
        )
        db.add(snap)
        await db.flush()

    day_start = datetime.combine(snapshot_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    rt_result = await db.execute(
        select(MachineRuntimeLog.activity_type, MachineRuntimeLog.start_time, MachineRuntimeLog.end_time)
        .where(
            MachineRuntimeLog.machine_id == machine_id,
            MachineRuntimeLog.start_time < day_end,
            or_(MachineRuntimeLog.end_time.is_(None), MachineRuntimeLog.end_time > day_start),
        )
    )
    rt_map: dict[RuntimeActivity, Decimal] = {}
    for activity_type, start_time, end_time in rt_result.all():
        if end_time is None:
            continue
        clipped_start = max(_as_utc_datetime(start_time), day_start)
        clipped_end = min(_as_utc_datetime(end_time), day_end)
        if clipped_end <= clipped_start:
            continue
        minutes = _D(str((clipped_end - clipped_start).total_seconds() / 60)).quantize(_D("0.01"))
        rt_map[activity_type] = rt_map.get(activity_type, _D("0")) + minutes

    snap.setup_time_min = rt_map.get(RuntimeActivity.SETUP, _D("0"))
    snap.run_time_min = rt_map.get(RuntimeActivity.RUNNING, _D("0"))
    snap.downtime_min = rt_map.get(RuntimeActivity.DOWNTIME, _D("0"))
    snap.cleanup_time_min = rt_map.get(RuntimeActivity.CLEANUP, _D("0"))
    snap.changeover_time_min = rt_map.get(RuntimeActivity.CHANGEOVER, _D("0"))
    snap.idle_time_min = rt_map.get(RuntimeActivity.IDLE, _D("0"))

    # This endpoint has no authoritative machine schedule input. Keep the
    # planned-time sentinel at zero so availability/OEE are not fabricated.
    snap.planned_time_min = 0
    snap.availability = None
    snap.performance = None
    snap.rated_speed = None
    snap.quality_rate = None
    snap.oee = None
    snap.utilization_pct = None
    snap.machine_cost_actual = None
    snap.labor_cost_actual = None
    snap.energy_cost_actual = None

    machine = await get_machine(db, machine_id)
    ideal_cycle_time_sec = None
    if machine and machine.rated_capacity_per_hour and machine.rated_capacity_per_hour > 0:
        ideal_cycle_time_sec = _D("3600") / machine.rated_capacity_per_hour
        snap.rated_speed = machine.rated_capacity_per_hour

    oee_components = calculate_oee_components(
        planned_time_min=snap.planned_time_min,
        downtime_min=snap.downtime_min,
        actual_run_time_min=snap.run_time_min,
        ideal_cycle_time_sec=ideal_cycle_time_sec,
        total_units=snap.units_produced,
        good_units=snap.good_units,
    )
    snap.availability = oee_components["availability"]
    snap.performance = oee_components["performance"]
    snap.quality_rate = oee_components["quality"]
    snap.oee = oee_components["oee"]
    snap.low_oee_flag = snap.oee is not None and snap.oee < _D("0.65")

    snap.utilization_pct = None

    snap.high_downtime_flag = False
    snap.anomaly_flag = snap.low_oee_flag or snap.high_downtime_flag

    # Cost attribution is intentionally left to M26.S02.T003; the former
    # calculation mixed labor from unrelated machines and treated configured
    # rates as actual costs.
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


def _median_decimal(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / _D("2")


async def get_performance_anomalies(
    db: AsyncSession,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PerformanceAnomalyReportOut:
    """Detect unusually long machine downtime against that machine's own recent events."""
    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=6))
    if period_start > period_end:
        raise ValueError("date_from must be on or before date_to")

    baseline_start = period_start - timedelta(days=30)
    baseline_start_at = datetime.combine(baseline_start, time.min, tzinfo=timezone.utc)
    period_start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    period_end_before = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    result = await db.execute(
        select(MachineRuntimeLog, Machine)
        .join(Machine, Machine.id == MachineRuntimeLog.machine_id)
        .where(
            MachineRuntimeLog.activity_type == RuntimeActivity.DOWNTIME,
            MachineRuntimeLog.start_time >= baseline_start_at,
            MachineRuntimeLog.start_time < period_end_before,
        )
        .order_by(MachineRuntimeLog.machine_id, MachineRuntimeLog.start_time, MachineRuntimeLog.id)
    )
    rows = result.all()

    by_machine: dict[UUID, list[tuple[MachineRuntimeLog, Machine, datetime, Optional[datetime]]]] = {}
    unavailable_ids: set[UUID] = set()
    for log, machine in rows:
        start = _as_utc_datetime(log.start_time)
        end = _as_utc_datetime(log.end_time) if log.end_time is not None else None
        if end is None or end <= start:
            if period_start_at <= start < period_end_before:
                unavailable_ids.add(log.id)
            continue
        if period_start_at <= start < period_end_before and end > period_end_before:
            unavailable_ids.add(log.id)
        by_machine.setdefault(log.machine_id, []).append((log, machine, start, end))

    overlapping_ids: set[UUID] = set()
    for machine_rows in by_machine.values():
        machine_rows.sort(key=lambda item: (item[2], str(item[0].id)))
        active: list[tuple[MachineRuntimeLog, Machine, datetime, datetime]] = []
        for current in machine_rows:
            _, _, current_start, current_end = current
            active = [previous for previous in active if previous[3] > current_start]
            for previous in active:
                overlapping_ids.add(previous[0].id)
                overlapping_ids.add(current[0].id)
            active.append((current[0], current[1], current_start, current_end))

    minimum_baseline_events = 5
    anomalies: list[MachinePerformanceAnomaly] = []
    insufficient_baseline: set[UUID] = set()
    for machine_id, machine_rows in by_machine.items():
        valid_baseline = [
            item for item in machine_rows
            if baseline_start_at <= item[2] < period_start_at
            and item[3] < period_start_at
            and item[0].id not in overlapping_ids
        ]
        candidate_events = [
            item for item in machine_rows
            if period_start_at <= item[2] < period_end_before
            and item[3] <= period_end_before
            and item[0].id not in overlapping_ids
        ]
        if candidate_events and len(valid_baseline) < minimum_baseline_events:
            insufficient_baseline.add(machine_id)
            continue
        if not candidate_events:
            continue

        durations = [
            _D(str((item[3] - item[2]).total_seconds() / 60)).quantize(_D("0.01"))
            for item in valid_baseline
        ]
        baseline_median = _median_decimal(durations)
        deviations = [abs(value - baseline_median) for value in durations]
        baseline_mad = _median_decimal(deviations)
        threshold = baseline_median + _D("3") * baseline_mad
        source_ids = sorted((item[0].id for item in valid_baseline), key=str)

        for log, machine, event_start, event_end in candidate_events:
            observed = _D(str((event_end - event_start).total_seconds() / 60)).quantize(_D("0.01"))
            if observed <= threshold:
                continue
            anomalies.append(
                MachinePerformanceAnomaly(
                    machine_id=machine_id,
                    machine_code=machine.machine_code,
                    machine_name=machine.machine_name,
                    runtime_log_id=log.id,
                    event_start=event_start,
                    event_end=event_end,
                    observed_downtime_minutes=observed,
                    baseline_event_count=len(valid_baseline),
                    baseline_median_minutes=baseline_median.quantize(_D("0.01")),
                    baseline_mad_minutes=baseline_mad.quantize(_D("0.01")),
                    alert_threshold_minutes=threshold.quantize(_D("0.01")),
                    source_baseline_runtime_log_ids=source_ids,
                )
            )

    return PerformanceAnomalyReportOut(
        period_start=period_start,
        period_end=period_end,
        baseline_start=baseline_start,
        anomalies=sorted(anomalies, key=lambda item: (item.event_start, item.machine_code, str(item.runtime_log_id))),
        insufficient_baseline_machine_ids=sorted(insufficient_baseline, key=str),
        unavailable_runtime_log_ids=sorted(unavailable_ids, key=str),
        overlapping_runtime_log_ids=sorted(overlapping_ids, key=str),
        data_notes=[
            "Rule: a closed machine downtime interval is flagged when its duration exceeds that machine's prior-30-day median plus three median absolute deviations; at least five valid, non-overlapping prior downtime intervals are required.",
            "Only recorded machine runtime downtime intervals are used. This is a deterministic historical signal, not a prediction, live IoT alert, OEE score, schedule variance, or causal diagnosis.",
            "Open/invalid target intervals and intervals overlapping another downtime record for the same machine are excluded and returned by source ID. Baseline windows exclude all overlapping intervals.",
            "No anomaly is inferred when there is insufficient machine-specific history. The response includes the exact baseline source IDs and calculation values for review.",
        ],
    )


# ── Downtime-to-production evidence correlations ──────────────────────────────

async def get_downtime_production_correlations(
    db: AsyncSession,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> DowntimeProductionCorrelationReport:
    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=29))
    if period_start > period_end:
        raise ValueError("date_from must be on or before date_to")
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_before = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)

    downtime_result = await db.execute(
        select(DowntimeIntelligence, Machine)
        .join(Machine, Machine.id == DowntimeIntelligence.machine_id)
        .where(DowntimeIntelligence.start_time >= start_at, DowntimeIntelligence.start_time < end_before)
        .order_by(DowntimeIntelligence.start_time, DowntimeIntelligence.id)
    )
    downtime_rows = downtime_result.all()
    if not downtime_rows:
        return DowntimeProductionCorrelationReport(
            period_start=period_start,
            period_end=period_end,
            data_notes=["No downtime intelligence events were recorded in this period."],
        )

    machine_ids = {event.machine_id for event, _machine in downtime_rows}
    runtime_result = await db.execute(
        select(MachineRuntimeLog)
        .where(
            MachineRuntimeLog.machine_id.in_(machine_ids),
            MachineRuntimeLog.start_time < end_before,
            or_(MachineRuntimeLog.end_time.is_(None), MachineRuntimeLog.end_time > start_at),
        )
        .order_by(MachineRuntimeLog.machine_id, MachineRuntimeLog.start_time, MachineRuntimeLog.id)
    )
    runtime_by_machine: dict[UUID, list[MachineRuntimeLog]] = {}
    for log in runtime_result.scalars().all():
        runtime_by_machine.setdefault(log.machine_id, []).append(log)

    runtime_by_event: dict[UUID, list[MachineRuntimeLog]] = {}
    work_order_ids: set[UUID] = set()
    production_order_ids: set[UUID] = set()
    for event, _machine in downtime_rows:
        if event.work_order_id is not None:
            work_order_ids.add(event.work_order_id)
        if event.production_order_id is not None:
            production_order_ids.add(event.production_order_id)
        event_start = _as_utc_datetime(event.start_time)
        event_end = _as_utc_datetime(event.end_time) if event.end_time is not None else None
        if event_end is not None and event_end <= event_start:
            event_end = None
        matched = []
        for log in runtime_by_machine.get(event.machine_id, []):
            log_start = _as_utc_datetime(log.start_time)
            log_end = _as_utc_datetime(log.end_time) if log.end_time is not None else None
            if event_end is None:
                overlaps = log_start <= event_start and (log_end is None or log_end > event_start)
            elif log_end is None:
                overlaps = event_start <= log_start < event_end
            else:
                overlaps = log_start < event_end and log_end > event_start
            if not overlaps:
                continue
            if event.work_order_id is not None and log.work_order_id is not None and event.work_order_id != log.work_order_id:
                continue
            if event.production_order_id is not None and log.production_order_id is not None and event.production_order_id != log.production_order_id:
                continue
            matched.append(log)
            if log.work_order_id is not None:
                work_order_ids.add(log.work_order_id)
            if log.production_order_id is not None:
                production_order_ids.add(log.production_order_id)
        runtime_by_event[event.id] = matched

    labor_by_work_order: dict[UUID, list[LaborTimeLog]] = {}
    if work_order_ids:
        labor_result = await db.execute(
            select(LaborTimeLog)
            .where(
                LaborTimeLog.work_order_id.in_(work_order_ids),
                LaborTimeLog.start_time < end_before,
                or_(LaborTimeLog.end_time.is_(None), LaborTimeLog.end_time > start_at),
            )
            .order_by(LaborTimeLog.work_order_id, LaborTimeLog.start_time, LaborTimeLog.id)
        )
        for log in labor_result.scalars().all():
            if log.work_order_id is not None:
                labor_by_work_order.setdefault(log.work_order_id, []).append(log)

    quality_by_id: dict[UUID, dict[str, Any]] = {}
    quality_by_work_order: dict[UUID, list[UUID]] = {}
    quality_by_production_order: dict[UUID, list[UUID]] = {}
    if work_order_ids or production_order_ids:
        quality_predicates = []
        if work_order_ids:
            quality_predicates.append(AdvQCInspection.work_order_id.in_(work_order_ids))
        if production_order_ids:
            quality_predicates.append(AdvQCInspection.production_order_id.in_(production_order_ids))
        quality_result = await db.execute(
            select(AdvQCInspection, AdvQCResult)
            .outerjoin(AdvQCResult, AdvQCResult.inspection_id == AdvQCInspection.id)
            .where(or_(*quality_predicates))
            .order_by(AdvQCInspection.inspected_at, AdvQCInspection.id, AdvQCResult.id)
        )
        for inspection, result in quality_result.all():
            entry = quality_by_id.setdefault(inspection.id, {"inspection": inspection, "results": {}})
            if result is not None:
                entry["results"][result.id] = result
            if inspection.work_order_id is not None:
                quality_by_work_order.setdefault(inspection.work_order_id, []).append(inspection.id)
            if inspection.production_order_id is not None:
                quality_by_production_order.setdefault(inspection.production_order_id, []).append(inspection.id)

    waste_by_id: dict[UUID, WasteRecord] = {}
    waste_by_work_order: dict[UUID, list[UUID]] = {}
    waste_by_production_order: dict[UUID, list[UUID]] = {}
    if work_order_ids or production_order_ids:
        waste_predicates = []
        if work_order_ids:
            waste_predicates.append(WasteRecord.work_order_id.in_(work_order_ids))
        if production_order_ids:
            waste_predicates.append(WasteRecord.production_order_id.in_(production_order_ids))
        waste_result = await db.execute(
            select(WasteRecord).where(or_(*waste_predicates)).order_by(WasteRecord.created_at, WasteRecord.id)
        )
        for waste in waste_result.scalars().all():
            waste_by_id[waste.id] = waste
            if waste.work_order_id is not None:
                waste_by_work_order.setdefault(waste.work_order_id, []).append(waste.id)
            waste_by_production_order.setdefault(waste.production_order_id, []).append(waste.id)

    output_events: list[DowntimeProductionCorrelation] = []
    for event, machine in downtime_rows:
        event_start = _as_utc_datetime(event.start_time)
        event_end = _as_utc_datetime(event.end_time) if event.end_time is not None else None
        if event_end is not None and event_end <= event_start:
            event_end = None
        matched_runtime = runtime_by_event.get(event.id, [])
        contextual_work_orders = {event.work_order_id} if event.work_order_id is not None else set()
        contextual_production_orders = {event.production_order_id} if event.production_order_id is not None else set()
        contextual_work_orders.update(log.work_order_id for log in matched_runtime if log.work_order_id is not None)
        contextual_production_orders.update(log.production_order_id for log in matched_runtime if log.production_order_id is not None)

        matched_labor: dict[UUID, LaborTimeLog] = {}
        for work_order_id in contextual_work_orders:
            for log in labor_by_work_order.get(work_order_id, []):
                log_start = _as_utc_datetime(log.start_time)
                log_end = _as_utc_datetime(log.end_time) if log.end_time is not None else None
                if event_end is None:
                    overlaps = log_start <= event_start and (log_end is None or log_end > event_start)
                elif log_end is None:
                    overlaps = event_start <= log_start < event_end
                else:
                    overlaps = log_start < event_end and log_end > event_start
                if overlaps:
                    matched_labor[log.id] = log

        quality_ids = set()
        for work_order_id in contextual_work_orders:
            quality_ids.update(quality_by_work_order.get(work_order_id, []))
        for production_order_id in contextual_production_orders:
            quality_ids.update(quality_by_production_order.get(production_order_id, []))
        quality_inspections = []
        for inspection_id in quality_ids:
            entry = quality_by_id[inspection_id]
            inspection = entry["inspection"]
            quality_inspections.append(
                CorrelatedQualityInspection(
                    inspection_id=inspection.id,
                    qc_id=inspection.qc_id,
                    status=inspection.status.value,
                    inspection_type=inspection.inspection_type.value,
                    inspected_at=_as_utc_datetime(inspection.inspected_at) if inspection.inspected_at is not None else None,
                    work_order_id=inspection.work_order_id,
                    production_order_id=inspection.production_order_id,
                    results=[
                        CorrelatedQualityResult(
                            result_id=result.id,
                            test_type=result.test_type,
                            result=result.result.value,
                            actual_value=result.actual_value,
                            unit=result.unit,
                        )
                        for result in sorted(entry["results"].values(), key=lambda item: str(item.id))
                    ],
                )
            )

        waste_ids = set()
        for work_order_id in contextual_work_orders:
            waste_ids.update(waste_by_work_order.get(work_order_id, []))
        for production_order_id in contextual_production_orders:
            waste_ids.update(waste_by_production_order.get(production_order_id, []))
        waste_records = [
            CorrelatedWasteRecord(
                waste_record_id=waste.id,
                waste_id=waste.waste_id,
                work_order_id=waste.work_order_id,
                production_order_id=waste.production_order_id,
                waste_type=waste.waste_type.value,
                waste_category=waste.waste_category.value,
                expected_qty=waste.expected_qty,
                actual_qty=waste.actual_qty,
                loss_qty=waste.loss_qty,
                loss_pct=waste.loss_pct,
                uom=waste.uom,
                is_anomaly=waste.is_anomaly,
            )
            for waste in (waste_by_id[item] for item in waste_ids)
        ]

        observed_operator_ids = {log.operator_id for log in matched_runtime if log.operator_id is not None}
        observed_operator_ids.update(log.operator_id for log in matched_labor.values())
        basis = set()
        if matched_runtime:
            basis.add("same_machine_time_overlap")
            if any(event.work_order_id is not None and log.work_order_id == event.work_order_id for log in matched_runtime):
                basis.add("same_work_order_runtime_overlap")
        if matched_labor:
            basis.add("same_work_order_labor_time_overlap")
        if quality_inspections:
            basis.add("same_recorded_work_order_or_production_order_quality_link")
        if waste_records:
            basis.add("same_recorded_work_order_or_production_order_waste_link")

        output_events.append(
            DowntimeProductionCorrelation(
                downtime_id=event.id,
                machine_id=event.machine_id,
                machine_code=machine.machine_code,
                machine_name=machine.machine_name,
                work_order_id=event.work_order_id,
                production_order_id=event.production_order_id,
                downtime_class=event.downtime_class.value,
                start_time=event_start,
                end_time=event_end,
                duration_minutes=event.duration_minutes if event.duration_minutes is not None and event.duration_minutes > 0 else None,
                reported_by_operator_id=event.reported_by_id,
                observed_operator_ids=sorted(observed_operator_ids, key=str),
                runtime_log_ids=sorted((log.id for log in matched_runtime), key=str),
                labor_logs=[
                    CorrelatedLaborLog(
                        labor_log_id=log.id,
                        operator_id=log.operator_id,
                        approved_flag=log.approved_flag,
                        start_time=_as_utc_datetime(log.start_time),
                        end_time=_as_utc_datetime(log.end_time) if log.end_time is not None else None,
                        duration_minutes=log.duration_minutes,
                    )
                    for log in sorted(matched_labor.values(), key=lambda item: (item.start_time, str(item.id)))
                ],
                quality_inspections=sorted(quality_inspections, key=lambda item: (item.inspected_at or event_start, str(item.inspection_id))),
                waste_records=sorted(waste_records, key=lambda item: item.waste_id),
                correlation_basis=sorted(basis),
            )
        )

    return DowntimeProductionCorrelationReport(
        period_start=period_start,
        period_end=period_end,
        events=output_events,
        data_notes=[
            "Quality and waste are linked only by the same explicit work-order or production-order ID. Operator context requires recorded same-machine runtime overlap or same-work-order labor-time overlap.",
            "If a downtime event lacks an order link, an overlapping runtime log can provide order context; returned source IDs show that evidence chain.",
            "These are co-occurrence and traceability correlations, not proof that an operator, machine, downtime, QC result, or waste record caused another event.",
            "Labor approval state and source IDs are preserved. The downtime reporter is distinct from operators observed in runtime/labor records.",
            "Open downtime events are matched only at their recorded start instant; duration and later operator exposure are not inferred.",
        ],
    )


# ── Downtime Intelligence ─────────────────────────────────────────────────────

async def log_downtime(db: AsyncSession, data: DowntimeIntelCreate) -> DowntimeIntelligence:
    selected_reason_code = data.reason_code or data.downtime_class.value
    data.reason_code = await validate_downtime_reason_code(db, selected_reason_code)
    if data.reason_code != data.downtime_class.value:
        raise HTTPException(
            status_code=422,
            detail="Downtime reason code must match the selected downtime class.",
        )
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
    db: AsyncSession,
    production_order_id: UUID,
    *,
    machine_id: Optional[UUID] = None,
) -> CostContribution:
    machine_query = (
        select(MachineRuntimeLog, Machine)
        .join(Machine, Machine.id == MachineRuntimeLog.machine_id)
        .outerjoin(WorkOrder, WorkOrder.id == MachineRuntimeLog.work_order_id)
        .where(
            or_(
                MachineRuntimeLog.production_order_id == production_order_id,
                WorkOrder.production_order_id == production_order_id,
            )
        )
        .order_by(Machine.machine_code, MachineRuntimeLog.start_time, MachineRuntimeLog.id)
    )
    if machine_id is not None:
        machine_query = machine_query.where(MachineRuntimeLog.machine_id == machine_id)
    runtime_result = await db.execute(machine_query)
    runtime_rows = runtime_result.all()

    machine_groups: dict[UUID, dict[str, Any]] = {}
    unavailable_runtime_ids: list[UUID] = []
    for log, machine in runtime_rows:
        group = machine_groups.setdefault(
            machine.id,
            {
                "machine": machine,
                "run_minutes": _D("0"),
                "setup_minutes": _D("0"),
                "runtime_ids": [],
                "unavailable_ids": [],
                "intervals": [],
            },
        )
        group["runtime_ids"].append(log.id)
        if log.end_time is None:
            group["unavailable_ids"].append(log.id)
            unavailable_runtime_ids.append(log.id)
            continue
        start_at = _as_utc_datetime(log.start_time)
        end_at = _as_utc_datetime(log.end_time)
        if end_at <= start_at:
            group["unavailable_ids"].append(log.id)
            unavailable_runtime_ids.append(log.id)
            continue
        group["intervals"].append((start_at, end_at, log.id))
        minutes = _D(str((end_at - start_at).total_seconds() / 60)).quantize(_D("0.01"))
        if log.activity_type == RuntimeActivity.RUNNING:
            group["run_minutes"] += minutes
        elif log.activity_type == RuntimeActivity.SETUP:
            group["setup_minutes"] += minutes

    machine_lines: list[MachineCostAttribution] = []
    for machine_data in machine_groups.values():
        machine = machine_data["machine"]
        run_minutes = machine_data["run_minutes"]
        setup_minutes = machine_data["setup_minutes"]
        rate = _D(str(machine.hourly_cost_rate)) if machine.hourly_cost_rate is not None else None
        energy_rate = _D(str(machine.energy_cost_per_hour)) if machine.energy_cost_per_hour is not None else None
        runtime_cost = (
            (run_minutes / _D("60") * rate).quantize(_D("0.01"))
            if run_minutes == 0 or rate is not None else None
        )
        setup_cost = (
            (setup_minutes / _D("60") * rate).quantize(_D("0.01"))
            if setup_minutes == 0 or rate is not None else None
        )
        energy_cost = (
            (run_minutes / _D("60") * energy_rate).quantize(_D("0.01"))
            if run_minutes == 0 or energy_rate is not None else None
        )
        has_unavailable_time = bool(machine_data["unavailable_ids"])
        active_intervals: list[tuple[datetime, UUID]] = []
        overlapping_ids: set[UUID] = set()
        for start_at, end_at, log_id in sorted(machine_data["intervals"], key=lambda row: (row[0], row[1], str(row[2]))):
            active_intervals = [(active_end, active_id) for active_end, active_id in active_intervals if active_end > start_at]
            if active_intervals:
                overlapping_ids.add(log_id)
                overlapping_ids.update(active_id for _, active_id in active_intervals)
            active_intervals.append((end_at, log_id))
        total = (
            runtime_cost + setup_cost + energy_cost
            if not has_unavailable_time and not overlapping_ids and None not in (runtime_cost, setup_cost, energy_cost)
            else None
        )
        machine_lines.append(
            MachineCostAttribution(
                machine_id=machine.id,
                machine_code=machine.machine_code,
                runtime_hours=(run_minutes / _D("60")).quantize(_D("0.001")),
                setup_hours=(setup_minutes / _D("60")).quantize(_D("0.001")),
                hourly_cost_rate_used=rate,
                energy_cost_per_hour_used=energy_rate,
                runtime_cost=runtime_cost,
                setup_cost=setup_cost,
                energy_cost=energy_cost,
                total_cost=total,
                source_runtime_log_ids=sorted(machine_data["runtime_ids"], key=str),
                unavailable_runtime_log_ids=sorted(machine_data["unavailable_ids"], key=str),
                overlapping_runtime_log_ids=sorted(overlapping_ids, key=str),
            )
        )

    labor_lines: list[LaborCostAttribution] = []
    unapproved_labor_ids: list[UUID] = []
    unpriced_labor_ids: list[UUID] = []
    overlapping_labor_ids: set[UUID] = set()
    if machine_id is None:
        labor_query = (
            select(LaborTimeLog)
            .outerjoin(WorkOrder, WorkOrder.id == LaborTimeLog.work_order_id)
            .where(
                or_(
                    LaborTimeLog.production_order_id == production_order_id,
                    WorkOrder.production_order_id == production_order_id,
                )
            )
            .order_by(LaborTimeLog.start_time, LaborTimeLog.id)
        )
        labor_result = await db.execute(labor_query)
        labor_logs = labor_result.scalars().all()
        labor_intervals_by_operator: dict[UUID, list[tuple[datetime, datetime, UUID]]] = {}
        for log in labor_logs:
            start_time = getattr(log, "start_time", None)
            end_time = getattr(log, "end_time", None)
            if not log.approved_flag or start_time is None or end_time is None:
                continue
            start_at = _as_utc_datetime(start_time)
            end_at = _as_utc_datetime(end_time)
            if end_at > start_at:
                labor_intervals_by_operator.setdefault(log.operator_id, []).append((start_at, end_at, log.id))
        for intervals in labor_intervals_by_operator.values():
            active_labor: list[tuple[datetime, UUID]] = []
            for start_at, end_at, log_id in sorted(intervals, key=lambda row: (row[0], row[1], str(row[2]))):
                active_labor = [(active_end, active_id) for active_end, active_id in active_labor if active_end > start_at]
                if active_labor:
                    overlapping_labor_ids.add(log_id)
                    overlapping_labor_ids.update(active_id for _, active_id in active_labor)
                active_labor.append((end_at, log_id))

        for log in labor_logs:
            if not log.approved_flag:
                unapproved_labor_ids.append(log.id)
                labor_lines.append(
                    LaborCostAttribution(
                        labor_log_id=log.id,
                        operator_id=log.operator_id,
                        approved_flag=False,
                        duration_minutes=log.duration_minutes,
                        overtime_minutes=log.overtime_minutes,
                        included=False,
                        exclusion_reason="Labor log is not approved.",
                    )
                )
                continue
            if log.id in overlapping_labor_ids:
                labor_lines.append(
                    LaborCostAttribution(
                        labor_log_id=log.id,
                        operator_id=log.operator_id,
                        approved_flag=True,
                        duration_minutes=log.duration_minutes,
                        overtime_minutes=log.overtime_minutes,
                        cost_rate_per_hour=log.cost_rate_at_time,
                        included=False,
                        exclusion_reason="Approved labor log overlaps another approved interval for this operator.",
                    )
                )
                continue
            if log.duration_minutes is None or log.duration_minutes <= 0:
                unpriced_labor_ids.append(log.id)
                labor_lines.append(
                    LaborCostAttribution(
                        labor_log_id=log.id,
                        operator_id=log.operator_id,
                        approved_flag=True,
                        duration_minutes=log.duration_minutes,
                        overtime_minutes=log.overtime_minutes,
                        cost_rate_per_hour=log.cost_rate_at_time,
                        included=False,
                        exclusion_reason="Approved labor log has no positive recorded duration.",
                    )
                )
                continue
            if log.cost_rate_at_time is None:
                unpriced_labor_ids.append(log.id)
                labor_lines.append(
                    LaborCostAttribution(
                        labor_log_id=log.id,
                        operator_id=log.operator_id,
                        approved_flag=True,
                        duration_minutes=log.duration_minutes,
                        overtime_minutes=log.overtime_minutes,
                        included=False,
                        exclusion_reason="Approved labor log has no captured cost rate.",
                    )
                )
                continue
            duration_minutes = _D(str(log.duration_minutes))
            overtime_minutes = min(max(_D(str(log.overtime_minutes or 0)), _D("0")), duration_minutes)
            direct_minutes = duration_minutes - overtime_minutes
            rate = _D(str(log.cost_rate_at_time))
            direct_cost = (direct_minutes / _D("60") * rate).quantize(_D("0.01"))
            overtime_cost = (overtime_minutes / _D("60") * rate * _D("1.5")).quantize(_D("0.01"))
            labor_lines.append(
                LaborCostAttribution(
                    labor_log_id=log.id,
                    operator_id=log.operator_id,
                    approved_flag=True,
                    duration_minutes=duration_minutes,
                    overtime_minutes=overtime_minutes,
                    cost_rate_per_hour=rate,
                    direct_cost=direct_cost,
                    overtime_cost=overtime_cost,
                    included=True,
                )
            )

    machine_has_data = bool(machine_lines)
    machine_complete = machine_has_data and all(line.total_cost is not None for line in machine_lines)
    machine_runtime = sum((line.runtime_hours for line in machine_lines), _D("0"))
    machine_setup = sum((line.setup_hours for line in machine_lines), _D("0"))
    machine_cost_runtime = (
        sum((line.runtime_cost for line in machine_lines), _D("0")).quantize(_D("0.01"))
        if machine_complete else None
    )
    machine_cost_setup = (
        sum((line.setup_cost for line in machine_lines), _D("0")).quantize(_D("0.01"))
        if machine_complete else None
    )
    machine_cost_energy = (
        sum((line.energy_cost for line in machine_lines), _D("0")).quantize(_D("0.01"))
        if machine_complete else None
    )
    machine_total = (
        sum((line.total_cost for line in machine_lines), _D("0")).quantize(_D("0.01"))
        if machine_complete else None
    )

    approved_labor_lines = [line for line in labor_lines if line.approved_flag]
    labor_complete = (
        machine_id is None
        and bool(approved_labor_lines)
        and not unapproved_labor_ids
        and not unpriced_labor_ids
        and not overlapping_labor_ids
    )
    labor_direct_hours = sum(
        ((_D(str(line.duration_minutes or 0)) - _D(str(line.overtime_minutes or 0))) / _D("60") for line in labor_lines if line.included),
        _D("0"),
    ).quantize(_D("0.001"))
    labor_overtime_hours = sum(
        (_D(str(line.overtime_minutes or 0)) / _D("60") for line in labor_lines if line.included),
        _D("0"),
    ).quantize(_D("0.001"))
    labor_cost_direct = (
        sum((line.direct_cost for line in labor_lines if line.included), _D("0")).quantize(_D("0.01"))
        if labor_complete else None
    )
    labor_cost_overtime = (
        sum((line.overtime_cost for line in labor_lines if line.included), _D("0")).quantize(_D("0.01"))
        if labor_complete else None
    )
    labor_total = (
        labor_cost_direct + labor_cost_overtime
        if labor_cost_direct is not None and labor_cost_overtime is not None
        else None
    )
    complete = machine_complete and labor_complete
    total = machine_total + labor_total if machine_total is not None and labor_total is not None else None

    notes = [
        "Machine costs are estimates using each machine's current configured rates; historical machine-rate snapshots are not stored.",
        "Labor costs include only approved logs with captured duration and cost_rate_at_time; unapproved or unpriced logs are excluded and listed.",
        "The existing 1.5 overtime premium is applied to recorded overtime_minutes; no payroll posting is created.",
        "Rate records do not contain a currency code, so amounts are reported in configured rate units without asserting a currency.",
    ]
    if machine_id is not None:
        notes.append("A machine-specific request does not allocate production-order labor to that machine because labor logs have no machine-level linkage.")
    if unavailable_runtime_ids:
        notes.append("Open or invalid machine runtime intervals are excluded from duration and cost totals.")
    overlapping_runtime_ids = {log_id for line in machine_lines for log_id in line.overlapping_runtime_log_ids}
    if overlapping_runtime_ids:
        notes.append("Overlapping runtime intervals are listed and prevent a complete machine cost total.")
    if overlapping_labor_ids:
        notes.append("Overlapping approved labor intervals are listed and prevent a complete labor cost total.")
    if not machine_lines:
        notes.append("No linked machine runtime evidence exists for this production order.")
    if not labor_lines and machine_id is None:
        notes.append("No linked labor logs exist for this production order.")

    return CostContribution(
        production_order_id=production_order_id,
        machine_runtime_hours=machine_runtime.quantize(_D("0.001")),
        machine_setup_hours=machine_setup.quantize(_D("0.001")),
        machine_cost_runtime=machine_cost_runtime,
        machine_cost_setup=machine_cost_setup,
        machine_cost_energy=machine_cost_energy,
        machine_cost_total=machine_total,
        labor_direct_hours=labor_direct_hours,
        labor_overtime_hours=labor_overtime_hours,
        labor_cost_direct=labor_cost_direct,
        labor_cost_overtime=labor_cost_overtime,
        labor_cost_total=labor_total,
        total_cost=total,
        attribution_complete=complete,
        machine_attributions=machine_lines,
        labor_attributions=labor_lines,
        unavailable_runtime_log_ids=sorted(unavailable_runtime_ids, key=str),
        overlapping_runtime_log_ids=sorted(overlapping_runtime_ids, key=str),
        unapproved_labor_log_ids=sorted(unapproved_labor_ids, key=str),
        unpriced_labor_log_ids=sorted(unpriced_labor_ids, key=str),
        overlapping_labor_log_ids=sorted(overlapping_labor_ids, key=str),
        data_notes=notes,
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
            OperatorSkillCert.certification_required.is_(True),
            OperatorSkillCert.certification_expiry.is_not(None),
            OperatorSkillCert.certification_expiry <= today + timedelta(days=CERTIFICATION_EXPIRING_SOON_DAYS),
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
