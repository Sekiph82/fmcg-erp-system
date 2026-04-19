"""
Advanced Production Planning Suite — Data Models
──────────────────────────────────────────────────
True finite capacity scheduling layer between MPS and shop floor.

Models:
  1. PlanningScenario      — named planning run (DRAFT/ACTIVE/LOCKED/ARCHIVED)
  2. ResourceCalendar      — shift+availability rules per work center
  3. OperationQueue        — scheduled operations with full timing
  4. CapacityLoadSnapshot  — per-resource-per-slot utilization state
  5. ChangeoverMatrix      — product-family transition times
  6. PlanningBottleneck    — detected constraint resources
  7. PlanningAIRec         — AI agent output (optimizer/sequencer/disruptor)
  8. PlanningSimulation    — what-if simulation frame
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer, Float,
    ForeignKey, Enum as SAEnum, DateTime, Date, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class ScenarioStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    LOCKED   = "LOCKED"
    ARCHIVED = "ARCHIVED"

class ScenarioMode(str, enum.Enum):
    FINITE   = "FINITE"
    INFINITE = "INFINITE"

class OpQueueStatus(str, enum.Enum):
    PENDING     = "PENDING"
    SCHEDULED   = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    BLOCKED     = "BLOCKED"
    SKIPPED     = "SKIPPED"

class CapacitySlotType(str, enum.Enum):
    AVAILABLE  = "AVAILABLE"
    ALLOCATED  = "ALLOCATED"
    BLOCKED    = "BLOCKED"   # maintenance, break
    CHANGEOVER = "CHANGEOVER"

class BottleneckSeverity(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

class PlanningAgentType(str, enum.Enum):
    CAPACITY_OPTIMIZER  = "CAPACITY_OPTIMIZER"
    SEQUENCING_OPTIMIZER = "SEQUENCING_OPTIMIZER"
    DISRUPTION_PREDICTOR = "DISRUPTION_PREDICTOR"

class PlanningRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class SimulationStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    COMPUTED  = "COMPUTED"
    PUBLISHED = "PUBLISHED"
    DISCARDED = "DISCARDED"


# ── 1. PlanningScenario ────────────────────────────────────────────────────────

class PlanningScenario(Base, TimestampMixin):
    __tablename__ = "planning_scenarios"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_no  = Column(String(50), nullable=False, unique=True, index=True)
    scenario_name = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    status       = Column(SAEnum(ScenarioStatus), nullable=False, default=ScenarioStatus.DRAFT, index=True)
    mode         = Column(SAEnum(ScenarioMode), nullable=False, default=ScenarioMode.FINITE)

    # date horizon
    horizon_start = Column(Date, nullable=True)
    horizon_end   = Column(Date, nullable=True)

    # links
    mps_plan_id   = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # KPI summary (populated after calculate)
    total_ops          = Column(Integer, nullable=False, default=0)
    scheduled_ops      = Column(Integer, nullable=False, default=0)
    blocked_ops        = Column(Integer, nullable=False, default=0)
    avg_utilization_pct = Column(Numeric(6, 2), nullable=True)
    total_changeover_hrs = Column(Numeric(10, 2), nullable=True)
    bottleneck_count   = Column(Integer, nullable=False, default=0)
    calculated_at      = Column(DateTime(timezone=True), nullable=True)

    # relationships
    operations   = relationship("OperationQueue", back_populates="scenario", cascade="all, delete-orphan")
    load_snapshots = relationship("CapacityLoadSnapshot", back_populates="scenario", cascade="all, delete-orphan")
    bottlenecks  = relationship("PlanningBottleneck", back_populates="scenario", cascade="all, delete-orphan")
    ai_recs      = relationship("PlanningAIRec", back_populates="scenario", cascade="all, delete-orphan")
    simulations  = relationship("PlanningSimulation", back_populates="scenario", cascade="all, delete-orphan")
    created_by   = relationship("User", foreign_keys=[created_by_id])


# ── 2. ResourceCalendar ────────────────────────────────────────────────────────

class ResourceCalendar(Base, TimestampMixin):
    __tablename__ = "resource_calendars"
    __table_args__ = (
        UniqueConstraint("work_center_id", "calendar_date", name="uq_rescal_wc_date"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False)
    calendar_date  = Column(Date, nullable=False, index=True)

    # shift availability (sum of shift hours this day)
    available_hours = Column(Numeric(6, 2), nullable=False, default=8.0)
    shift_1_start   = Column(String(8), nullable=True)  # "HH:MM"
    shift_1_end     = Column(String(8), nullable=True)
    shift_2_start   = Column(String(8), nullable=True)
    shift_2_end     = Column(String(8), nullable=True)
    shift_3_start   = Column(String(8), nullable=True)
    shift_3_end     = Column(String(8), nullable=True)

    is_holiday     = Column(Boolean, nullable=False, default=False)
    is_maintenance = Column(Boolean, nullable=False, default=False)
    notes          = Column(String(255), nullable=True)

    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])


# ── 3. OperationQueue ──────────────────────────────────────────────────────────

class OperationQueue(Base, TimestampMixin):
    __tablename__ = "operation_queue"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    op_no          = Column(String(50), nullable=False, index=True)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False)

    # source links
    mps_line_id       = Column(UUID(as_uuid=True), ForeignKey("mps_lines.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    work_order_id     = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    routing_step_id   = Column(UUID(as_uuid=True), ForeignKey("routing_steps.id", ondelete="SET NULL"), nullable=True)
    work_center_id    = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # cached display
    product_name      = Column(String(255), nullable=True)
    product_code      = Column(String(100), nullable=True)
    work_center_name  = Column(String(255), nullable=True)
    step_name         = Column(String(255), nullable=True)

    # quantities
    planned_qty       = Column(Numeric(14, 3), nullable=False, default=0)
    rate_per_hour     = Column(Numeric(10, 3), nullable=True)    # units/hr from routing step

    # timing (minutes)
    setup_minutes     = Column(Integer, nullable=False, default=0)
    run_minutes       = Column(Integer, nullable=False, default=0)
    cleanup_minutes   = Column(Integer, nullable=False, default=0)
    changeover_minutes = Column(Integer, nullable=False, default=0)
    total_minutes     = Column(Integer, nullable=False, default=0)  # sum of above

    # schedule
    scheduled_start   = Column(DateTime(timezone=True), nullable=True)
    scheduled_end     = Column(DateTime(timezone=True), nullable=True)
    actual_start      = Column(DateTime(timezone=True), nullable=True)
    actual_end        = Column(DateTime(timezone=True), nullable=True)

    # priority & status
    priority          = Column(Integer, nullable=False, default=50)
    status            = Column(SAEnum(OpQueueStatus), nullable=False, default=OpQueueStatus.PENDING, index=True)
    is_critical_path  = Column(Boolean, nullable=False, default=False)
    predecessor_ids   = Column(JSON, nullable=True)   # list of op_queue UUIDs
    block_reason      = Column(String(255), nullable=True)

    # relationships
    scenario    = relationship("PlanningScenario", back_populates="operations")


# ── 4. CapacityLoadSnapshot ────────────────────────────────────────────────────

class CapacityLoadSnapshot(Base, TimestampMixin):
    __tablename__ = "capacity_load_snapshots"
    __table_args__ = (
        UniqueConstraint("scenario_id", "work_center_id", "slot_date", "slot_hour",
                         name="uq_load_snap_wc_slot"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False)
    work_center_name = Column(String(255), nullable=True)

    slot_date      = Column(Date, nullable=False, index=True)
    slot_hour      = Column(Integer, nullable=True)   # 0-23; NULL = day-level

    available_hours  = Column(Numeric(6, 2), nullable=False, default=8.0)
    allocated_hours  = Column(Numeric(8, 2), nullable=False, default=0)
    changeover_hours = Column(Numeric(6, 2), nullable=False, default=0)
    utilization_pct  = Column(Numeric(6, 2), nullable=False, default=0)
    is_overloaded    = Column(Boolean, nullable=False, default=False)
    overload_hours   = Column(Numeric(6, 2), nullable=False, default=0)
    slot_type        = Column(SAEnum(CapacitySlotType), nullable=False, default=CapacitySlotType.AVAILABLE)

    # relationships
    scenario    = relationship("PlanningScenario", back_populates="load_snapshots")
    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])


# ── 5. ChangeoverMatrix ────────────────────────────────────────────────────────

class ChangeoverMatrix(Base, TimestampMixin):
    __tablename__ = "changeover_matrix"
    __table_args__ = (
        UniqueConstraint("work_center_id", "from_family", "to_family", name="uq_changeover_wc_families"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False)
    from_family    = Column(String(50), nullable=False)   # product family/group code
    to_family      = Column(String(50), nullable=False)
    changeover_minutes = Column(Integer, nullable=False, default=0)
    notes          = Column(String(255), nullable=True)
    is_active      = Column(Boolean, nullable=False, default=True)

    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])


# ── 6. PlanningBottleneck ──────────────────────────────────────────────────────

class PlanningBottleneck(Base, TimestampMixin):
    __tablename__ = "planning_bottlenecks"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    work_center_name = Column(String(255), nullable=True)

    severity           = Column(SAEnum(BottleneckSeverity), nullable=False, default=BottleneckSeverity.MEDIUM)
    peak_utilization_pct = Column(Numeric(6, 2), nullable=False, default=0)
    overloaded_days    = Column(Integer, nullable=False, default=0)
    total_overload_hrs = Column(Numeric(8, 2), nullable=False, default=0)
    blocked_op_count   = Column(Integer, nullable=False, default=0)
    recommendation     = Column(Text, nullable=True)
    detected_at        = Column(DateTime(timezone=True), nullable=True)
    is_resolved        = Column(Boolean, nullable=False, default=False)

    scenario    = relationship("PlanningScenario", back_populates="bottlenecks")
    work_center = relationship("WorkCenter", foreign_keys=[work_center_id])


# ── 7. PlanningAIRec ──────────────────────────────────────────────────────────

class PlanningAIRec(Base, TimestampMixin):
    __tablename__ = "planning_ai_recs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False)
    agent_type     = Column(SAEnum(PlanningAgentType), nullable=False)
    status         = Column(SAEnum(PlanningRecStatus), nullable=False, default=PlanningRecStatus.PENDING)

    title          = Column(String(255), nullable=False)
    explanation    = Column(Text, nullable=True)
    impact_summary = Column(Text, nullable=True)
    confidence_score = Column(Numeric(4, 2), nullable=True)   # 0.00–1.00

    affected_op_ids = Column(JSON, nullable=True)   # list of operation_queue UUIDs
    payload        = Column(JSON, nullable=True)    # agent-specific structured data

    actioned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actioned_at    = Column(DateTime(timezone=True), nullable=True)

    scenario    = relationship("PlanningScenario", back_populates="ai_recs")
    actioned_by = relationship("User", foreign_keys=[actioned_by_id])


# ── 8. PlanningSimulation ──────────────────────────────────────────────────────

class PlanningSimulation(Base, TimestampMixin):
    __tablename__ = "planning_simulations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sim_no      = Column(String(50), nullable=False, unique=True, index=True)
    sim_name    = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False)
    status      = Column(SAEnum(SimulationStatus), nullable=False, default=SimulationStatus.DRAFT)

    # changes applied (JSON list of {op_id, field, old_value, new_value})
    changes     = Column(JSON, nullable=True)

    # impact metrics
    ops_rescheduled    = Column(Integer, nullable=True)
    ops_delayed        = Column(Integer, nullable=True)
    utilization_delta  = Column(Numeric(6, 2), nullable=True)   # % change
    changeover_delta_hrs = Column(Numeric(8, 2), nullable=True)
    throughput_delta_pct = Column(Numeric(6, 2), nullable=True)
    impact_summary     = Column(Text, nullable=True)

    computed_at = Column(DateTime(timezone=True), nullable=True)
    published_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    scenario     = relationship("PlanningScenario", back_populates="simulations")
    published_by = relationship("User", foreign_keys=[published_by_id])
