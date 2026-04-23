from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.machine_operator import (
    MachineStatus, MachineFamily, SkillLevel, CertStatus,
    AssignmentType, RuntimeActivity, DowntimeClass, LaborActivity,
    ReviewType, MOAIAgentType, MOAIRecStatus,
)


# ── Machine ───────────────────────────────────────────────────────────────────

class MachineCreate(BaseModel):
    machine_code: str
    machine_name: str
    machine_type: Optional[str] = None
    machine_family: MachineFamily = MachineFamily.OTHER
    plant_id: Optional[str] = None
    section_id: Optional[str] = None
    line_id: Optional[str] = None
    work_center_id: Optional[UUID] = None
    manufacturer: Optional[str] = None
    model_no: Optional[str] = None
    serial_no: Optional[str] = None
    commission_date: Optional[date] = None
    status: MachineStatus = MachineStatus.ACTIVE
    rated_capacity_per_hour: Optional[Decimal] = None
    capacity_uom: Optional[str] = None
    standard_speed: Optional[Decimal] = None
    minimum_speed: Optional[Decimal] = None
    maximum_speed: Optional[Decimal] = None
    setup_time_standard_min: Optional[int] = 0
    cleanup_time_standard_min: Optional[int] = 0
    changeover_time_standard_min: Optional[int] = 0
    hourly_cost_rate: Optional[Decimal] = None
    energy_cost_per_hour: Optional[Decimal] = None
    maintenance_cost_factor: Optional[Decimal] = None
    depreciation_cost_factor: Optional[Decimal] = None
    labor_requirement_standard: Optional[Decimal] = None
    oee_tracking_enabled: bool = True
    active_flag: bool = True
    preferred_product_families: Optional[str] = None
    notes: Optional[str] = None


class MachineUpdate(BaseModel):
    machine_name: Optional[str] = None
    status: Optional[MachineStatus] = None
    hourly_cost_rate: Optional[Decimal] = None
    energy_cost_per_hour: Optional[Decimal] = None
    rated_capacity_per_hour: Optional[Decimal] = None
    standard_speed: Optional[Decimal] = None
    setup_time_standard_min: Optional[int] = None
    cleanup_time_standard_min: Optional[int] = None
    active_flag: Optional[bool] = None
    notes: Optional[str] = None


class MachineOut(MachineCreate):
    id: UUID
    work_center_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Operator Profile ──────────────────────────────────────────────────────────

class OperatorProfileCreate(BaseModel):
    operator_code: str
    employee_id: Optional[UUID] = None
    full_name: str
    department: Optional[str] = None
    skill_level: SkillLevel = SkillLevel.BASIC
    primary_work_center_id: Optional[UUID] = None
    primary_machine_id: Optional[UUID] = None
    primary_line_id: Optional[str] = None
    labor_rate_per_hour: Optional[Decimal] = None
    active_flag: bool = True
    notes: Optional[str] = None


class OperatorProfileOut(OperatorProfileCreate):
    id: UUID
    cert_count: Optional[int] = None
    expiring_cert_count: Optional[int] = None

    class Config:
        from_attributes = True


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    team_code: str
    team_name: str
    supervisor_id: Optional[UUID] = None
    default_shift_id: Optional[UUID] = None
    active_flag: bool = True
    notes: Optional[str] = None


class TeamMemberAdd(BaseModel):
    operator_id: UUID
    role_in_team: Optional[str] = None


class TeamOut(TeamCreate):
    id: UUID
    member_count: Optional[int] = None

    class Config:
        from_attributes = True


class TeamMemberOut(BaseModel):
    id: UUID
    team_id: UUID
    operator_id: UUID
    operator_name: Optional[str] = None
    role_in_team: Optional[str] = None
    active_flag: bool

    class Config:
        from_attributes = True


# ── Skill / Cert ──────────────────────────────────────────────────────────────

class SkillCertCreate(BaseModel):
    operator_id: UUID
    machine_id: Optional[UUID] = None
    work_center_id: Optional[UUID] = None
    operation_code: Optional[str] = None
    skill_level: SkillLevel = SkillLevel.BASIC
    certification_required: bool = False
    certification_expiry: Optional[date] = None
    approved_flag: bool = True
    notes: Optional[str] = None


class SkillCertOut(SkillCertCreate):
    id: UUID
    cert_status: CertStatus
    operator_name: Optional[str] = None
    machine_name: Optional[str] = None

    class Config:
        from_attributes = True


class AssignmentValidateRequest(BaseModel):
    work_order_id: UUID
    machine_id: Optional[UUID] = None
    operator_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None


class AssignmentValidateResult(BaseModel):
    valid: bool
    warnings: List[str] = []
    blocks: List[str] = []
    operator_certified: bool = True
    machine_available: bool = True


# ── Work Order Assignment ─────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    work_order_id: UUID
    production_order_id: Optional[UUID] = None
    machine_id: Optional[UUID] = None
    operator_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None
    cert_override_flag: bool = False
    cert_override_reason: Optional[str] = None
    notes: Optional[str] = None


class AssignmentOut(AssignmentCreate):
    id: UUID
    assigned_at: datetime
    cert_validation_passed: bool
    machine_name: Optional[str] = None
    operator_name: Optional[str] = None
    team_name: Optional[str] = None

    class Config:
        from_attributes = True


class AssignmentHistoryOut(BaseModel):
    id: UUID
    work_order_id: UUID
    assignment_type: AssignmentType
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True


# ── Runtime Log ───────────────────────────────────────────────────────────────

class RuntimeLogCreate(BaseModel):
    machine_id: UUID
    work_order_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    activity_type: RuntimeActivity
    start_time: datetime
    end_time: Optional[datetime] = None
    operator_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    reason_code: Optional[str] = None
    notes: Optional[str] = None


class RuntimeLogOut(RuntimeLogCreate):
    id: UUID
    duration_minutes: Optional[Decimal] = None
    machine_name: Optional[str] = None
    operator_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Labor Time Log ────────────────────────────────────────────────────────────

class LaborTimeCreate(BaseModel):
    operator_id: UUID
    team_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    activity_type: LaborActivity = LaborActivity.RUN
    start_time: datetime
    end_time: Optional[datetime] = None
    overtime_flag: bool = False
    notes: Optional[str] = None


class LaborTimeOut(LaborTimeCreate):
    id: UUID
    duration_minutes: Optional[Decimal] = None
    cost_rate_at_time: Optional[Decimal] = None
    overtime_minutes: Optional[Decimal] = None
    approved_flag: bool
    operator_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Performance Snapshot ──────────────────────────────────────────────────────

class PerformanceSnapshotOut(BaseModel):
    id: UUID
    machine_id: UUID
    machine_code: Optional[str] = None
    machine_name: Optional[str] = None
    snapshot_date: date
    planned_time_min: int
    setup_time_min: Decimal
    run_time_min: Decimal
    downtime_min: Decimal
    cleanup_time_min: Decimal
    changeover_time_min: Decimal
    idle_time_min: Decimal
    units_produced: Decimal
    good_units: Decimal
    scrap_units: Decimal
    actual_speed: Optional[Decimal] = None
    rated_speed: Optional[Decimal] = None
    availability: Optional[Decimal] = None
    performance: Optional[Decimal] = None
    quality_rate: Optional[Decimal] = None
    oee: Optional[Decimal] = None
    utilization_pct: Optional[Decimal] = None
    machine_cost_actual: Optional[Decimal] = None
    labor_cost_actual: Optional[Decimal] = None
    anomaly_flag: bool
    low_oee_flag: bool
    high_downtime_flag: bool

    class Config:
        from_attributes = True


# ── Downtime Intelligence ─────────────────────────────────────────────────────

class DowntimeIntelCreate(BaseModel):
    machine_id: UUID
    work_order_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    downtime_class: DowntimeClass
    downtime_subclass: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    reported_by_id: Optional[UUID] = None
    root_cause: Optional[str] = None
    units_lost: Optional[Decimal] = None
    notes: Optional[str] = None


class DowntimeIntelOut(DowntimeIntelCreate):
    id: UUID
    duration_minutes: Optional[Decimal] = None
    repeat_occurrence: bool
    maintenance_escalated: bool
    cost_impact: Optional[Decimal] = None
    machine_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Supervisor Review ─────────────────────────────────────────────────────────

class SupervisorReviewCreate(BaseModel):
    entity_type: str
    entity_id: UUID
    review_type: ReviewType
    action_taken: Optional[str] = None
    comments: Optional[str] = None
    production_order_id: Optional[UUID] = None


class SupervisorReviewOut(SupervisorReviewCreate):
    id: UUID
    reviewed_at: datetime
    reviewed_by: Optional[UUID] = None

    class Config:
        from_attributes = True


# ── AI Recommendations ────────────────────────────────────────────────────────

class MOAIRecOut(BaseModel):
    id: UUID
    agent_type: MOAIAgentType
    status: MOAIRecStatus
    machine_id: Optional[UUID] = None
    operator_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    title: str
    description: str
    severity: str
    confidence_score: Optional[Decimal] = None
    estimated_impact: Optional[str] = None
    actioned_at: Optional[datetime] = None
    action_notes: Optional[str] = None

    class Config:
        from_attributes = True


class MOAIRecAction(BaseModel):
    status: MOAIRecStatus
    notes: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class MODashboard(BaseModel):
    total_machines: int = 0
    machines_active: int = 0
    machines_maintenance: int = 0
    total_operators: int = 0
    total_teams: int = 0
    expiring_certs: int = 0
    avg_oee_today: Optional[Decimal] = None
    total_downtime_today_min: Decimal = Decimal("0")
    pending_ai_recs: int = 0
    recent_downtime: List[DowntimeIntelOut] = []
    ai_recommendations: List[MOAIRecOut] = []


# ── Cost Contribution ─────────────────────────────────────────────────────────

class CostContribution(BaseModel):
    production_order_id: UUID
    machine_runtime_hours: Decimal = Decimal("0")
    machine_setup_hours: Decimal = Decimal("0")
    machine_cost_runtime: Decimal = Decimal("0")
    machine_cost_setup: Decimal = Decimal("0")
    machine_cost_energy: Decimal = Decimal("0")
    machine_cost_total: Decimal = Decimal("0")
    labor_direct_hours: Decimal = Decimal("0")
    labor_overtime_hours: Decimal = Decimal("0")
    labor_cost_direct: Decimal = Decimal("0")
    labor_cost_overtime: Decimal = Decimal("0")
    labor_cost_total: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    std_machine_cost: Optional[Decimal] = None
    std_labor_cost: Optional[Decimal] = None
    variance_pct: Optional[Decimal] = None
