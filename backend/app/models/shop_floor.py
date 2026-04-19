"""
Shop Floor Execution System models.
Tables: sf_sessions, sf_activity_logs, sf_downtime_logs,
        sf_shift_handovers, sf_supervisor_overrides, sf_ai_recs
"""
import uuid
from enum import Enum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class SFSessionStatus(str, Enum):
    ACTIVE     = "ACTIVE"
    IDLE       = "IDLE"
    LOGGED_OUT = "LOGGED_OUT"
    EXPIRED    = "EXPIRED"

class WOEventType(str, Enum):
    START              = "START"
    PAUSE              = "PAUSE"
    RESUME             = "RESUME"
    FINISH             = "FINISH"
    QTY_UPDATE         = "QTY_UPDATE"
    SCRAP              = "SCRAP"
    DOWNTIME_START     = "DOWNTIME_START"
    DOWNTIME_STOP      = "DOWNTIME_STOP"
    QC_TRIGGER         = "QC_TRIGGER"
    HELP_REQUEST       = "HELP_REQUEST"
    HANDOVER           = "HANDOVER"
    NOTE               = "NOTE"
    SUPERVISOR_OVERRIDE = "SUPERVISOR_OVERRIDE"

class SFDowntimeCat(str, Enum):
    MACHINE_BREAKDOWN  = "MACHINE_BREAKDOWN"
    MATERIAL_SHORTAGE  = "MATERIAL_SHORTAGE"
    PACKAGING_SHORTAGE = "PACKAGING_SHORTAGE"
    QC_WAITING         = "QC_WAITING"
    CHANGEOVER         = "CHANGEOVER"
    CLEANING           = "CLEANING"
    POWER_ISSUE        = "POWER_ISSUE"
    LABOR_SHORTAGE     = "LABOR_SHORTAGE"
    SUPERVISOR_HOLD    = "SUPERVISOR_HOLD"
    MAINTENANCE_STOP   = "MAINTENANCE_STOP"
    LABEL_MISMATCH     = "LABEL_MISMATCH"
    IT_ISSUE           = "IT_ISSUE"
    OTHER              = "OTHER"

class SFImpactLevel(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

class OverrideType(str, Enum):
    APPROVE_OVERPRODUCTION = "APPROVE_OVERPRODUCTION"
    APPROVE_SCRAP          = "APPROVE_SCRAP"
    UNBLOCK                = "UNBLOCK"
    ASSIGN                 = "ASSIGN"
    REASSIGN               = "REASSIGN"
    PAUSE_ORDER            = "PAUSE_ORDER"
    RESUME_ORDER           = "RESUME_ORDER"
    ESCALATE               = "ESCALATE"
    LOCK_TERMINAL          = "LOCK_TERMINAL"

class SFAIAgentType(str, Enum):
    EXECUTION_ANOMALY_DETECTOR = "EXECUTION_ANOMALY_DETECTOR"
    SUPERVISOR_ASSISTANT       = "SUPERVISOR_ASSISTANT"
    OPERATOR_GUIDANCE          = "OPERATOR_GUIDANCE"

class SFAIRecStatus(str, Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class SFLiveStatus(str, Enum):
    WAITING           = "WAITING"
    READY             = "READY"
    ASSIGNED          = "ASSIGNED"
    RUNNING           = "RUNNING"
    PAUSED            = "PAUSED"
    BLOCKED           = "BLOCKED"
    QC_HOLD           = "QC_HOLD"
    SUPERVISOR_REVIEW = "SUPERVISOR_REVIEW"
    COMPLETED         = "COMPLETED"
    CANCELLED         = "CANCELLED"


# ── Models ─────────────────────────────────────────────────────────────────────

class SFSession(Base):
    """Operator terminal session — tracks who is logged into which line/machine."""
    __tablename__ = "sf_sessions"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_code          = Column(String(60), unique=True, nullable=False, index=True)
    operator_id           = Column(UUID(as_uuid=True), nullable=True)
    operator_name         = Column(String(200), nullable=False)
    team_id               = Column(UUID(as_uuid=True), nullable=True)
    machine_id            = Column(UUID(as_uuid=True), nullable=True)
    line_id               = Column(String(50), nullable=True, index=True)
    work_center_id        = Column(UUID(as_uuid=True), nullable=True, index=True)
    shift_id              = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    login_time            = Column(DateTime(timezone=True), server_default=func.now())
    logout_time           = Column(DateTime(timezone=True), nullable=True)
    current_work_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="SET NULL"), nullable=True)
    status                = Column(String(20), default="ACTIVE", index=True)
    notes                 = Column(Text, nullable=True)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    activity_logs = relationship("WOActivityLog", back_populates="session", foreign_keys="WOActivityLog.session_id")


class WOActivityLog(Base):
    """Timestamped event log for every shop floor action on a work order."""
    __tablename__ = "sf_activity_logs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id          = Column(UUID(as_uuid=True), ForeignKey("sf_sessions.id", ondelete="SET NULL"), nullable=True)
    operator_id         = Column(UUID(as_uuid=True), nullable=True)
    operator_name       = Column(String(200), nullable=True)
    team_id             = Column(UUID(as_uuid=True), nullable=True)
    machine_id          = Column(UUID(as_uuid=True), nullable=True)
    line_id             = Column(String(50), nullable=True)

    event_type       = Column(String(30), nullable=False, index=True)
    timestamp_start  = Column(DateTime(timezone=True), server_default=func.now())
    timestamp_end    = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Numeric(8, 2), nullable=True)

    # Quantity capture
    qty_good    = Column(Numeric(14, 4), nullable=True)
    qty_scrap   = Column(Numeric(14, 4), nullable=True)
    qty_rework  = Column(Numeric(14, 4), nullable=True)

    # Context
    reason_code = Column(String(100), nullable=True)
    remarks     = Column(Text, nullable=True)
    extra_data  = Column(JSONB, nullable=True)  # for future extensibility

    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("SFSession", back_populates="activity_logs", foreign_keys="WOActivityLog.session_id")


class SFDowntimeLog(Base):
    """Shop floor downtime record — tracks interruptions with duration and reason."""
    __tablename__ = "sf_downtime_logs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="CASCADE"), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id          = Column(UUID(as_uuid=True), nullable=True)
    machine_name        = Column(String(200), nullable=True)
    line_id             = Column(String(50), nullable=True, index=True)
    operator_id         = Column(UUID(as_uuid=True), nullable=True)
    operator_name       = Column(String(200), nullable=True)
    team_id             = Column(UUID(as_uuid=True), nullable=True)

    start_time        = Column(DateTime(timezone=True), server_default=func.now())
    end_time          = Column(DateTime(timezone=True), nullable=True)
    duration_minutes  = Column(Numeric(8, 2), nullable=True)
    is_closed         = Column(Boolean, default=False)

    downtime_category = Column(String(30), nullable=False)
    root_reason       = Column(Text, nullable=True)
    impact_level      = Column(String(20), default="MEDIUM")

    linked_maintenance_ticket_id = Column(UUID(as_uuid=True), nullable=True)
    comments          = Column(Text, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ShiftHandover(Base):
    """Shift handover record — documents state transfer between shifts."""
    __tablename__ = "sf_shift_handovers"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id                = Column(String(50), nullable=True, index=True)
    work_center_id         = Column(UUID(as_uuid=True), nullable=True)

    shift_from_id          = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    shift_to_id            = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    shift_from_name        = Column(String(100), nullable=True)
    shift_to_name          = Column(String(100), nullable=True)

    outgoing_supervisor_id = Column(UUID(as_uuid=True), nullable=True)
    outgoing_supervisor    = Column(String(200), nullable=True)
    incoming_supervisor_id = Column(UUID(as_uuid=True), nullable=True)
    incoming_supervisor    = Column(String(200), nullable=True)

    outgoing_operators     = Column(JSONB, nullable=True)   # list of names
    incoming_operators     = Column(JSONB, nullable=True)

    # State summary
    open_work_orders       = Column(JSONB, nullable=True)   # list of {order_no, step, status}
    qty_completed          = Column(Numeric(14, 4), nullable=True)
    qty_remaining          = Column(Numeric(14, 4), nullable=True)
    issues_open            = Column(JSONB, nullable=True)   # list of issue strings
    qc_pending_items       = Column(JSONB, nullable=True)
    material_shortages     = Column(JSONB, nullable=True)

    notes                  = Column(Text, nullable=True)
    handover_time          = Column(DateTime(timezone=True), server_default=func.now())
    is_approved            = Column(Boolean, default=False)
    approved_by            = Column(String(200), nullable=True)
    approved_at            = Column(DateTime(timezone=True), nullable=True)

    created_at             = Column(DateTime(timezone=True), server_default=func.now())


class SupervisorOverride(Base):
    """Audit trail for every supervisor intervention on the shop floor."""
    __tablename__ = "sf_supervisor_overrides"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="SET NULL"), nullable=True)
    supervisor_id       = Column(UUID(as_uuid=True), nullable=True)
    supervisor_name     = Column(String(200), nullable=False)
    override_type       = Column(String(40), nullable=False)
    reason              = Column(Text, nullable=True)
    target_operator_id  = Column(UUID(as_uuid=True), nullable=True)
    target_operator_name = Column(String(200), nullable=True)
    approved_at         = Column(DateTime(timezone=True), server_default=func.now())
    notes               = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SFAIRec(Base):
    """AI recommendations for shop floor — per work order or global."""
    __tablename__ = "sf_ai_recs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="CASCADE"), nullable=True, index=True)
    production_order_id = Column(UUID(as_uuid=True), nullable=True)
    agent_type          = Column(String(40), nullable=False)
    status              = Column(String(20), default="PENDING")
    title               = Column(String(300), nullable=False)
    explanation         = Column(Text, nullable=True)
    impact_summary      = Column(Text, nullable=True)
    confidence_score    = Column(Numeric(4, 3), nullable=True)
    actioned_at         = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
