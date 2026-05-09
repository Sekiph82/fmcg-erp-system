"""
Machine + Operator Intelligence Module
───────────────────────────────────────
10 sub-modules:
  1. Machine Master       – enriched machine data linked to WorkCenter
  2. Operator Profile     – employee → production operator linkage
  3. Production Team      – team master + member roster
  4. Skill / Certification – operator certification per machine/operation
  5. Work Order Assignment – structured FK assignments (machine/operator/team)
  6. Assignment History   – full change log
  7. Machine Runtime Log  – setup/run/cleanup/downtime segmented timeline
  8. Labor Time Log       – direct labor time per operator per operation
  9. Performance Snapshot – computed OEE-ready metrics per machine/shift
 10. Supervisor Review    – review log + AI recommendation table
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class MachineStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


class MachineFamily(str, enum.Enum):
    FILLING = "FILLING"
    MIXING = "MIXING"
    PACKAGING = "PACKAGING"
    LABELING = "LABELING"
    PALLETIZING = "PALLETIZING"
    CONVEYOR = "CONVEYOR"
    WEIGHING = "WEIGHING"
    INSPECTION = "INSPECTION"
    UTILITY = "UTILITY"
    OTHER = "OTHER"


class SkillLevel(str, enum.Enum):
    TRAINEE = "TRAINEE"
    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class CertStatus(str, enum.Enum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"


class AssignmentType(str, enum.Enum):
    MACHINE = "MACHINE"
    OPERATOR = "OPERATOR"
    TEAM = "TEAM"
    LINE = "LINE"
    SHIFT = "SHIFT"


class RuntimeActivity(str, enum.Enum):
    SETUP = "SETUP"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    IDLE = "IDLE"
    DOWNTIME = "DOWNTIME"
    CLEANUP = "CLEANUP"
    CHANGEOVER = "CHANGEOVER"
    MAINTENANCE = "MAINTENANCE"
    QC_WAIT = "QC_WAIT"


class DowntimeClass(str, enum.Enum):
    MECHANICAL_BREAKDOWN = "MECHANICAL_BREAKDOWN"
    ELECTRICAL_ISSUE = "ELECTRICAL_ISSUE"
    PNEUMATIC_ISSUE = "PNEUMATIC_ISSUE"
    MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE"
    PACKAGING_SHORTAGE = "PACKAGING_SHORTAGE"
    OPERATOR_UNAVAILABLE = "OPERATOR_UNAVAILABLE"
    QC_WAITING = "QC_WAITING"
    CHANGEOVER_DELAY = "CHANGEOVER_DELAY"
    CLEANING_DELAY = "CLEANING_DELAY"
    MAINTENANCE_INTERVENTION = "MAINTENANCE_INTERVENTION"
    SPEED_LOSS = "SPEED_LOSS"
    MICRO_STOP = "MICRO_STOP"
    PLANNED_STOP = "PLANNED_STOP"
    UNPLANNED_STOP = "UNPLANNED_STOP"
    UTILITY_ISSUE = "UTILITY_ISSUE"
    OTHER = "OTHER"


class LaborActivity(str, enum.Enum):
    SETUP = "SETUP"
    RUN = "RUN"
    CLEANUP = "CLEANUP"
    DOWNTIME_SUPPORT = "DOWNTIME_SUPPORT"
    QC_SUPPORT = "QC_SUPPORT"
    REWORK = "REWORK"
    MAINTENANCE_ASSIST = "MAINTENANCE_ASSIST"
    CHANGEOVER = "CHANGEOVER"


class ReviewType(str, enum.Enum):
    DOWNTIME_REVIEW = "DOWNTIME_REVIEW"
    SCRAP_REVIEW = "SCRAP_REVIEW"
    OVERTIME_APPROVAL = "OVERTIME_APPROVAL"
    ASSIGNMENT_OVERRIDE = "ASSIGNMENT_OVERRIDE"
    CERT_OVERRIDE = "CERT_OVERRIDE"
    PERFORMANCE_COMMENT = "PERFORMANCE_COMMENT"
    COACHING_ACTION = "COACHING_ACTION"
    MAINTENANCE_ESCALATION = "MAINTENANCE_ESCALATION"


class MOAIAgentType(str, enum.Enum):
    PERFORMANCE_ANOMALY = "PERFORMANCE_ANOMALY"
    PRODUCTIVITY_OPTIMIZER = "PRODUCTIVITY_OPTIMIZER"
    COST_VARIANCE = "COST_VARIANCE"


class MOAIRecStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


# ── 1. Machine Master ─────────────────────────────────────────────────────────

class Machine(Base, TimestampMixin):
    """Enriched machine master — supplement to WorkCenter."""
    __tablename__ = "machines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_code = Column(String(50), unique=True, nullable=False, index=True)
    machine_name = Column(String(255), nullable=False)
    machine_type = Column(String(100), nullable=True)
    machine_family = Column(Enum(MachineFamily), nullable=False, default=MachineFamily.OTHER)
    plant_id = Column(String(50), nullable=True)
    section_id = Column(String(50), nullable=True)
    line_id = Column(String(50), nullable=True)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True, index=True)

    manufacturer = Column(String(200), nullable=True)
    model_no = Column(String(100), nullable=True)
    serial_no = Column(String(100), nullable=True)
    commission_date = Column(Date, nullable=True)
    status = Column(Enum(MachineStatus), nullable=False, default=MachineStatus.ACTIVE)

    rated_capacity_per_hour = Column(Numeric(14, 3), nullable=True)
    capacity_uom = Column(String(20), nullable=True)
    standard_speed = Column(Numeric(14, 3), nullable=True)
    minimum_speed = Column(Numeric(14, 3), nullable=True)
    maximum_speed = Column(Numeric(14, 3), nullable=True)

    setup_time_standard_min = Column(Integer, nullable=True, default=0)
    cleanup_time_standard_min = Column(Integer, nullable=True, default=0)
    changeover_time_standard_min = Column(Integer, nullable=True, default=0)

    hourly_cost_rate = Column(Numeric(14, 4), nullable=True)
    energy_cost_per_hour = Column(Numeric(14, 4), nullable=True)
    maintenance_cost_factor = Column(Numeric(5, 4), nullable=True, default=0.05)
    depreciation_cost_factor = Column(Numeric(5, 4), nullable=True, default=0.03)
    labor_requirement_standard = Column(Numeric(5, 2), nullable=True, default=1.0)

    oee_tracking_enabled = Column(Boolean, default=True, nullable=False)
    active_flag = Column(Boolean, default=True, nullable=False)
    preferred_product_families = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])
    runtime_logs = relationship("MachineRuntimeLog", back_populates="machine", cascade="all, delete-orphan")
    performance_snapshots = relationship("MachinePerformanceSnapshot", back_populates="machine", cascade="all, delete-orphan")
    downtime_intel = relationship("DowntimeIntelligence", back_populates="machine", cascade="all, delete-orphan")


# ── 2. Operator Profile ───────────────────────────────────────────────────────

class OperatorProfile(Base, TimestampMixin):
    """Production operator profile — links HR Employee to shop floor."""
    __tablename__ = "operator_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_code = Column(String(50), unique=True, nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    skill_level = Column(Enum(SkillLevel, name="operator_skilllevel"), nullable=False, default=SkillLevel.BASIC)
    primary_work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    primary_machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    primary_line_id = Column(String(50), nullable=True)
    labor_rate_per_hour = Column(Numeric(14, 4), nullable=True)
    active_flag = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id])
    primary_work_center = relationship("WorkCenter", foreign_keys=[primary_work_center_id])
    primary_machine = relationship("Machine", foreign_keys=[primary_machine_id])
    skills = relationship("OperatorSkillCert", back_populates="operator", cascade="all, delete-orphan")
    labor_logs = relationship("LaborTimeLog", back_populates="operator", cascade="all, delete-orphan")


# ── 3. Production Team ────────────────────────────────────────────────────────

class ProductionTeam(Base, TimestampMixin):
    __tablename__ = "production_teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_code = Column(String(50), unique=True, nullable=False, index=True)
    team_name = Column(String(200), nullable=False)
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="SET NULL"), nullable=True)
    default_shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    active_flag = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    supervisor = relationship("OperatorProfile", foreign_keys=[supervisor_id])
    default_shift = relationship("Shift", foreign_keys=[default_shift_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base, TimestampMixin):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "operator_id", name="uq_team_operator"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("production_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="CASCADE"), nullable=False)
    role_in_team = Column(String(100), nullable=True)
    active_flag = Column(Boolean, default=True, nullable=False)

    team = relationship("ProductionTeam", back_populates="members")
    operator = relationship("OperatorProfile", foreign_keys=[operator_id])


# ── 4. Operator Skill / Certification ─────────────────────────────────────────

class OperatorSkillCert(Base, TimestampMixin):
    __tablename__ = "operator_skill_certs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    operation_code = Column(String(100), nullable=True)
    skill_level = Column(Enum(SkillLevel, name="operator_skilllevel"), nullable=False, default=SkillLevel.BASIC)
    cert_status = Column(Enum(CertStatus, name="operator_certstatus"), nullable=False, default=CertStatus.VALID)
    certification_required = Column(Boolean, default=False, nullable=False)
    certification_expiry = Column(Date, nullable=True)
    approved_flag = Column(Boolean, default=True, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    operator = relationship("OperatorProfile", back_populates="skills")
    machine = relationship("Machine", foreign_keys=[machine_id])
    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])
    approver = relationship("User", foreign_keys=[approved_by])


# ── 5. Work Order Assignment ──────────────────────────────────────────────────

class WorkOrderAssignment(Base, TimestampMixin):
    """Structured FK assignment for a work order — replaces free-text operator field."""
    __tablename__ = "work_order_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("production_teams.id", ondelete="SET NULL"), nullable=True)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    cert_validation_passed = Column(Boolean, default=True, nullable=False)
    cert_override_flag = Column(Boolean, default=False, nullable=False)
    cert_override_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])
    machine = relationship("Machine", foreign_keys=[machine_id])
    operator = relationship("OperatorProfile", foreign_keys=[operator_id])
    team = relationship("ProductionTeam", foreign_keys=[team_id])
    shift = relationship("Shift", foreign_keys=[shift_id])
    assigned_user = relationship("User", foreign_keys=[assigned_by])


# ── 6. Assignment History ─────────────────────────────────────────────────────

class AssignmentHistory(Base, TimestampMixin):
    __tablename__ = "assignment_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_type = Column(Enum(AssignmentType), nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    reason = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])
    changer = relationship("User", foreign_keys=[changed_by])


# ── 7. Machine Runtime Log ────────────────────────────────────────────────────

class MachineRuntimeLog(Base, TimestampMixin):
    """Segmented machine activity timeline — setup / running / downtime etc."""
    __tablename__ = "machine_runtime_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(Enum(RuntimeActivity), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Numeric(10, 2), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("production_teams.id", ondelete="SET NULL"), nullable=True)
    reason_code = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    machine = relationship("Machine", back_populates="runtime_logs")
    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])
    operator = relationship("OperatorProfile", foreign_keys=[operator_id])
    team = relationship("ProductionTeam", foreign_keys=[team_id])


# ── 8. Labor Time Log ─────────────────────────────────────────────────────────

class LaborTimeLog(Base, TimestampMixin):
    __tablename__ = "labor_time_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("production_teams.id", ondelete="SET NULL"), nullable=True)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(Enum(LaborActivity), nullable=False, default=LaborActivity.RUN)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Numeric(10, 2), nullable=True)
    cost_rate_at_time = Column(Numeric(14, 4), nullable=True)
    overtime_flag = Column(Boolean, default=False, nullable=False)
    overtime_minutes = Column(Numeric(10, 2), nullable=True, default=0)
    approved_flag = Column(Boolean, default=False, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    operator = relationship("OperatorProfile", back_populates="labor_logs")
    team = relationship("ProductionTeam", foreign_keys=[team_id])
    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])
    approver = relationship("User", foreign_keys=[approved_by])


# ── 9. Machine Performance Snapshot ──────────────────────────────────────────

class MachinePerformanceSnapshot(Base, TimestampMixin):
    """Computed OEE-ready performance metrics per machine per shift/day."""
    __tablename__ = "machine_performance_snapshots"
    __table_args__ = (
        UniqueConstraint("machine_id", "snapshot_date", "shift_id", name="uq_machine_perf_date_shift"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    planned_time_min = Column(Integer, nullable=False, default=0)
    setup_time_min = Column(Numeric(10, 2), nullable=False, default=0)
    run_time_min = Column(Numeric(10, 2), nullable=False, default=0)
    downtime_min = Column(Numeric(10, 2), nullable=False, default=0)
    cleanup_time_min = Column(Numeric(10, 2), nullable=False, default=0)
    changeover_time_min = Column(Numeric(10, 2), nullable=False, default=0)
    idle_time_min = Column(Numeric(10, 2), nullable=False, default=0)

    units_produced = Column(Numeric(14, 3), nullable=False, default=0)
    good_units = Column(Numeric(14, 3), nullable=False, default=0)
    scrap_units = Column(Numeric(14, 3), nullable=False, default=0)
    actual_speed = Column(Numeric(14, 3), nullable=True)
    rated_speed = Column(Numeric(14, 3), nullable=True)

    availability = Column(Numeric(6, 4), nullable=True)
    performance = Column(Numeric(6, 4), nullable=True)
    quality_rate = Column(Numeric(6, 4), nullable=True)
    oee = Column(Numeric(6, 4), nullable=True)
    utilization_pct = Column(Numeric(6, 4), nullable=True)

    machine_cost_actual = Column(Numeric(14, 4), nullable=True)
    labor_cost_actual = Column(Numeric(14, 4), nullable=True)
    energy_cost_actual = Column(Numeric(14, 4), nullable=True)

    anomaly_flag = Column(Boolean, default=False, nullable=False)
    low_oee_flag = Column(Boolean, default=False, nullable=False)
    high_downtime_flag = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    machine = relationship("Machine", back_populates="performance_snapshots")
    shift = relationship("Shift", foreign_keys=[shift_id])


# ── 10a. Downtime Intelligence ────────────────────────────────────────────────

class DowntimeIntelligence(Base, TimestampMixin):
    """Extended downtime classification and MTBF/MTTR readiness."""
    __tablename__ = "downtime_intelligence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    downtime_class = Column(Enum(DowntimeClass), nullable=False)
    downtime_subclass = Column(String(100), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Numeric(10, 2), nullable=True)

    reported_by_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    repeat_occurrence = Column(Boolean, default=False, nullable=False)
    maintenance_escalated = Column(Boolean, default=False, nullable=False)
    units_lost = Column(Numeric(14, 3), nullable=True)
    cost_impact = Column(Numeric(14, 4), nullable=True)
    notes = Column(Text, nullable=True)

    machine = relationship("Machine", back_populates="downtime_intel")
    reported_by = relationship("OperatorProfile", foreign_keys=[reported_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


# ── 10b. Supervisor Review Log ────────────────────────────────────────────────

class SupervisorReview(Base, TimestampMixin):
    __tablename__ = "supervisor_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    review_type = Column(Enum(ReviewType), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    action_taken = Column(String(200), nullable=True)
    comments = Column(Text, nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ── 10c. AI Recommendations ───────────────────────────────────────────────────

class MOAIRecommendation(Base, TimestampMixin):
    __tablename__ = "mo_ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(MOAIAgentType), nullable=False)
    status = Column(Enum(MOAIRecStatus), nullable=False, default=MOAIRecStatus.PENDING)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operator_profiles.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    confidence_score = Column(Numeric(5, 2), nullable=True)
    estimated_impact = Column(Text, nullable=True)
    actioned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actioned_at = Column(DateTime(timezone=True), nullable=True)
    action_notes = Column(Text, nullable=True)

    machine = relationship("Machine", foreign_keys=[machine_id])
    operator = relationship("OperatorProfile", foreign_keys=[operator_id])
    actioned_user = relationship("User", foreign_keys=[actioned_by])
