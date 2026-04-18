"""
Master Production Scheduling (MPS) — Database Models

Sits between MRP output and shop floor execution.
Resolves capacity constraints, groups into campaigns,
supports what-if simulation and AI optimization.
"""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum as SAEnum, DateTime, Date,
    UniqueConstraint, Index, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enumerations ───────────────────────────────────────────────────────────────

class MPSPlanningMode(str, enum.Enum):
    MANUAL   = "MANUAL"    # Planner creates/edits every line manually
    ASSISTED = "ASSISTED"  # System suggests, planner confirms
    AUTO     = "AUTO"      # System auto-generates, planner can override
    AI       = "AI"        # AI drives sequencing + batch sizes


class MPSCapacityMode(str, enum.Enum):
    FINITE   = "FINITE"    # Respect work center capacity limits
    INFINITE = "INFINITE"  # Ignore capacity, plan demand only


class MPSStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    APPROVED = "APPROVED"
    RELEASED = "RELEASED"   # Production orders created
    CLOSED   = "CLOSED"


class MPSFeasibilityStatus(str, enum.Enum):
    PENDING        = "PENDING"
    FEASIBLE       = "FEASIBLE"
    OVERLOADED     = "OVERLOADED"     # Capacity exceeded
    MATERIAL_SHORT = "MATERIAL_SHORT" # Net MRP shortage
    INFEASIBLE     = "INFEASIBLE"     # Multiple blocking issues
    ON_HOLD        = "ON_HOLD"        # Planner hold


class MPSAgentType(str, enum.Enum):
    OPTIMIZER       = "OPTIMIZER"       # Sequence / batch optimization
    RISK_PREDICTOR  = "RISK_PREDICTOR"  # Late / stockout / overload risk


class MPSRecType(str, enum.Enum):
    SEQUENCE   = "SEQUENCE"
    CAMPAIGN   = "CAMPAIGN"
    BATCH_SIZE = "BATCH_SIZE"
    RISK_ALERT = "RISK_ALERT"
    CAPACITY   = "CAPACITY"
    SPLIT      = "SPLIT"
    MERGE      = "MERGE"


class MPSRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class WhatIfStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    COMPUTED = "COMPUTED"


class MPSChangeType(str, enum.Enum):
    DELAY         = "DELAY"
    BATCH_SIZE    = "BATCH_SIZE"
    LINE_CHANGE   = "LINE_CHANGE"
    SPLIT         = "SPLIT"
    MERGE         = "MERGE"
    SHIFT_ADD     = "SHIFT_ADD"
    QTY_ADJUST    = "QTY_ADJUST"


# ── Plan Header ───────────────────────────────────────────────────────────────

class MPSPlan(Base, TimestampMixin):
    """Master Production Schedule — one per planning cycle."""
    __tablename__ = "mps_plans"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_no              = Column(String(50), nullable=False, unique=True, index=True)
    plan_name            = Column(String(255), nullable=False)
    plant_code           = Column(String(50), nullable=True)
    planning_horizon_days = Column(Integer, nullable=False, default=90)
    start_date           = Column(Date, nullable=False)
    end_date             = Column(Date, nullable=False)
    planning_mode        = Column(SAEnum(MPSPlanningMode), nullable=False, default=MPSPlanningMode.ASSISTED)
    capacity_mode        = Column(SAEnum(MPSCapacityMode), nullable=False, default=MPSCapacityMode.FINITE)
    status               = Column(SAEnum(MPSStatus), nullable=False, default=MPSStatus.DRAFT, index=True)

    # Source linkage
    mrp_run_id  = Column(UUID(as_uuid=True), ForeignKey("mrp_runs.id", ondelete="SET NULL"), nullable=True)

    # Counters (updated by scheduler)
    total_lines      = Column(Integer, nullable=False, default=0)
    overloaded_lines = Column(Integer, nullable=False, default=0)
    feasible_lines   = Column(Integer, nullable=False, default=0)
    locked_lines     = Column(Integer, nullable=False, default=0)

    approved_at      = Column(DateTime(timezone=True), nullable=True)
    released_at      = Column(DateTime(timezone=True), nullable=True)

    created_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    mrp_run       = relationship("MRPRun")
    created_by    = relationship("User", foreign_keys=[created_by_id])
    approved_by   = relationship("User", foreign_keys=[approved_by_id])
    lines         = relationship("MPSLine", back_populates="mps_plan", cascade="all, delete-orphan")
    campaigns     = relationship("MPSCampaign", back_populates="mps_plan", cascade="all, delete-orphan")
    capacity_slots = relationship("MPSCapacitySlot", back_populates="mps_plan", cascade="all, delete-orphan")
    whatif_scenarios = relationship("MPSWhatIfScenario", back_populates="mps_plan", cascade="all, delete-orphan")
    ai_recommendations = relationship("MPSAIRecommendation", back_populates="mps_plan", cascade="all, delete-orphan")


# ── Plan Lines ─────────────────────────────────────────────────────────────────

class MPSLine(Base, TimestampMixin):
    """One planned production entry per product per period."""
    __tablename__ = "mps_lines"
    __table_args__ = (
        Index("ix_mps_lines_plan_product", "mps_id", "product_id"),
        Index("ix_mps_lines_period", "period_start", "period_end"),
    )

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_no  = Column(String(50), nullable=False, unique=True, index=True)
    mps_id   = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Source linkage
    mrp_result_id = Column(UUID(as_uuid=True), ForeignKey("mrp_results.id", ondelete="SET NULL"), nullable=True)

    # Period
    period_label = Column(String(20), nullable=True)   # "2024-W01" or "2024-01"
    period_start = Column(Date, nullable=False)
    period_end   = Column(Date, nullable=False)

    # Demand decomposition
    confirmed_demand_qty   = Column(Numeric(16, 3), nullable=False, default=0)
    forecast_qty           = Column(Numeric(16, 3), nullable=False, default=0)
    safety_stock_qty       = Column(Numeric(16, 3), nullable=False, default=0)
    net_requirement_qty    = Column(Numeric(16, 3), nullable=False, default=0)

    # Planned production (may differ from net req due to batching)
    planned_production_qty = Column(Numeric(16, 3), nullable=False, default=0)
    batch_size_qty         = Column(Numeric(16, 3), nullable=True)
    num_batches            = Column(Integer, nullable=True)

    # Scheduling
    work_center_id     = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date   = Column(Date, nullable=True)
    required_hours     = Column(Numeric(10, 3), nullable=True)

    # Campaign
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("mps_campaigns.id", ondelete="SET NULL"), nullable=True)

    # Priority + Feasibility
    priority_score      = Column(Numeric(7, 3), nullable=False, default=50.0)
    feasibility_status  = Column(SAEnum(MPSFeasibilityStatus), nullable=False, default=MPSFeasibilityStatus.PENDING)
    overload_hours      = Column(Numeric(10, 3), nullable=True)

    # Manual override flag — locked lines are not touched by engine
    is_locked = Column(Boolean, nullable=False, default=False)
    remarks   = Column(Text, nullable=True)

    # Released production order linkage
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    mps_plan         = relationship("MPSPlan", back_populates="lines")
    product          = relationship("Product")
    mrp_result       = relationship("MRPResult")
    work_center      = relationship("WorkCenter")
    campaign         = relationship("MPSCampaign", back_populates="lines")
    production_order = relationship("ProductionOrder")


# ── Campaign ───────────────────────────────────────────────────────────────────

class MPSCampaign(Base, TimestampMixin):
    """
    A campaign groups similar SKUs on one work center to minimize changeovers.
    FMCG-critical: same base formula, different packaging run together.
    """
    __tablename__ = "mps_campaigns"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_code = Column(String(50), nullable=False, unique=True, index=True)
    campaign_name = Column(String(255), nullable=False)
    mps_id        = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)

    campaign_start         = Column(Date, nullable=True)
    campaign_end           = Column(Date, nullable=True)
    total_production_hrs   = Column(Numeric(10, 3), nullable=False, default=0)
    total_changeover_hrs   = Column(Numeric(10, 3), nullable=False, default=0)
    sequence_order         = Column(Integer, nullable=False, default=0)
    sku_count              = Column(Integer, nullable=False, default=0)

    notes = Column(Text, nullable=True)

    mps_plan    = relationship("MPSPlan", back_populates="campaigns")
    work_center = relationship("WorkCenter")
    lines       = relationship("MPSLine", back_populates="campaign")


# ── Capacity Slots ─────────────────────────────────────────────────────────────

class MPSCapacitySlot(Base, TimestampMixin):
    """Daily capacity utilization per work center for one MPS plan."""
    __tablename__ = "mps_capacity_slots"
    __table_args__ = (
        UniqueConstraint("mps_id", "work_center_id", "slot_date", name="uq_mps_capacity_slot"),
        Index("ix_mps_capacity_slots_plan", "mps_id", "slot_date"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mps_id         = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    work_center_id = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_date      = Column(Date, nullable=False)

    available_hours = Column(Numeric(8, 3), nullable=False, default=8.0)
    allocated_hours = Column(Numeric(8, 3), nullable=False, default=0.0)
    downtime_hours  = Column(Numeric(8, 3), nullable=False, default=0.0)
    overload_hours  = Column(Numeric(8, 3), nullable=False, default=0.0)
    utilization_pct = Column(Numeric(6, 2), nullable=False, default=0.0)
    is_overloaded   = Column(Boolean, nullable=False, default=False)

    mps_plan    = relationship("MPSPlan", back_populates="capacity_slots")
    work_center = relationship("WorkCenter")


# ── What-If Scenarios ──────────────────────────────────────────────────────────

class MPSWhatIfScenario(Base, TimestampMixin):
    """
    A what-if simulation: planner proposes changes (delay, batch resize, etc.)
    and the system computes the impact before committing anything.
    """
    __tablename__ = "mps_whatif_scenarios"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_no   = Column(String(50), nullable=False, unique=True, index=True)
    scenario_name = Column(String(255), nullable=False)
    mps_id        = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    description   = Column(Text, nullable=True)

    # The proposed changes as JSON list of {line_id, change_type, new_value}
    changes = Column(JSON, nullable=False, default=list)

    # Computed impact
    impact_service_level_pct = Column(Numeric(6, 2), nullable=True)
    impact_delay_count       = Column(Integer, nullable=True)
    impact_cost_delta        = Column(Numeric(16, 4), nullable=True)
    impact_summary           = Column(Text, nullable=True)
    status                   = Column(SAEnum(WhatIfStatus), nullable=False, default=WhatIfStatus.DRAFT)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    mps_plan   = relationship("MPSPlan", back_populates="whatif_scenarios")
    created_by = relationship("User")


# ── AI Recommendations ─────────────────────────────────────────────────────────

class MPSAIRecommendation(Base, TimestampMixin):
    """
    AI agent output — optimizer or risk predictor.
    Never applied automatically; planner reviews and accepts/rejects.
    """
    __tablename__ = "mps_ai_recommendations"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mps_id  = Column(UUID(as_uuid=True), ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_type = Column(SAEnum(MPSAgentType), nullable=False)
    rec_type   = Column(SAEnum(MPSRecType), nullable=False)

    affected_line_ids = Column(JSON, nullable=False, default=list)
    recommendation    = Column(Text, nullable=False)
    impact_summary    = Column(Text, nullable=True)
    confidence_score  = Column(Numeric(5, 2), nullable=False, default=0)

    status        = Column(SAEnum(MPSRecStatus), nullable=False, default=MPSRecStatus.PENDING)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)

    mps_plan    = relationship("MPSPlan", back_populates="ai_recommendations")
    reviewed_by = relationship("User")
