import uuid
import enum
from datetime import date
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class PSRunStatus(str, enum.Enum):
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"


class PSSuggestionStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    REVIEWED  = "REVIEWED"
    APPROVED  = "APPROVED"
    CONVERTED = "CONVERTED"
    REJECTED  = "REJECTED"


class PSUrgencyLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class PSGroupStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    SENT      = "SENT"
    CONVERTED = "CONVERTED"


class PSAIAgentType(str, enum.Enum):
    SUPPLIER_OPTIMIZER     = "SUPPLIER_OPTIMIZER"
    DEMAND_RISK_PREDICTOR  = "DEMAND_RISK_PREDICTOR"
    COST_OPTIMIZER         = "COST_OPTIMIZER"


class SupplierItemPriority(str, enum.Enum):
    PRIMARY   = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY  = "TERTIARY"
    FALLBACK  = "FALLBACK"


# ── Supplier–Item price / MOQ / lead-time mapping (many-to-many) ──────────────

class SupplierItemPrice(Base, TimestampMixin):
    __tablename__ = "supplier_item_prices"
    __table_args__ = (
        UniqueConstraint("supplier_id", "material_id", name="uq_sip_supplier_material"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id",  ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="CASCADE"), nullable=False, index=True)

    unit_price       = Column(Numeric(14, 4), nullable=False)
    currency         = Column(String(10), nullable=False, default="KES")
    moq              = Column(Numeric(14, 3), nullable=False, default=1)
    pack_size        = Column(Numeric(14, 3), nullable=True)      # must order in multiples
    lead_time_days   = Column(Integer, nullable=False, default=0)
    buffer_days      = Column(Integer, nullable=False, default=0)
    customs_days     = Column(Integer, nullable=False, default=0) # import buffer
    priority         = Column(Enum(SupplierItemPriority), nullable=False, default=SupplierItemPriority.PRIMARY)
    reliability_score = Column(Numeric(5, 2), nullable=True)      # 0-100
    contract_no      = Column(String(100), nullable=True)
    is_active        = Column(Boolean, default=True, nullable=False)
    valid_from       = Column(Date, nullable=True)
    valid_to         = Column(Date, nullable=True)
    notes            = Column(Text, nullable=True)

    supplier = relationship("Supplier")
    material = relationship("Material")


# ── Procurement Suggestion Run (header) ────────────────────────────────────────

class ProcurementSuggestionRun(Base, TimestampMixin):
    __tablename__ = "procurement_suggestion_runs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_no                = Column(String(50), unique=True, nullable=False, index=True)
    suggestion_date       = Column(Date, nullable=False)
    warehouse_id          = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    mrp_run_id            = Column(UUID(as_uuid=True), ForeignKey("mrp_runs.id",   ondelete="SET NULL"), nullable=True)
    status                = Column(Enum(PSRunStatus), nullable=False, default=PSRunStatus.QUEUED)
    planning_horizon_days = Column(Integer, nullable=False, default=90)
    include_safety_stock  = Column(Boolean, default=True, nullable=False)
    include_reorder_point = Column(Boolean, default=True, nullable=False)
    suggestion_count      = Column(Integer, nullable=True)
    total_estimated_cost  = Column(Numeric(16, 4), nullable=True)
    currency              = Column(String(10), nullable=False, default="KES")
    error_message         = Column(Text, nullable=True)
    started_at            = Column(DateTime(timezone=True), nullable=True)
    completed_at          = Column(DateTime(timezone=True), nullable=True)
    created_by            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes                 = Column(Text, nullable=True)

    warehouse        = relationship("Warehouse")
    mrp_run          = relationship("MRPRun")
    creator          = relationship("User")
    lines            = relationship("ProcurementSuggestionLine", back_populates="run", cascade="all, delete-orphan")
    groups           = relationship("ProcurementSuggestionGroup", back_populates="run", cascade="all, delete-orphan")
    ai_recommendations = relationship("PSAIRecommendation", back_populates="run", cascade="all, delete-orphan")


# ── Procurement Suggestion Line (one per item) ─────────────────────────────────

class ProcurementSuggestionLine(Base, TimestampMixin):
    __tablename__ = "procurement_suggestion_lines"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id      = Column(UUID(as_uuid=True), ForeignKey("procurement_suggestion_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    uom         = Column(String(20), nullable=True)

    # Quantities
    required_qty       = Column(Numeric(14, 3), nullable=False, default=0)
    available_qty      = Column(Numeric(14, 3), nullable=False, default=0)
    shortage_qty       = Column(Numeric(14, 3), nullable=False, default=0)
    safety_stock_qty   = Column(Numeric(14, 3), nullable=False, default=0)
    reorder_point_qty  = Column(Numeric(14, 3), nullable=False, default=0)
    incoming_po_qty    = Column(Numeric(14, 3), nullable=False, default=0)

    # Supplier selection
    supplier_id              = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    alternative_supplier_ids = Column(JSON, nullable=True)  # list of UUID strings
    supplier_price           = Column(Numeric(14, 4), nullable=True)
    currency                 = Column(String(10), nullable=False, default="KES")

    # Order quantity
    moq                  = Column(Numeric(14, 3), nullable=True)
    pack_size            = Column(Numeric(14, 3), nullable=True)
    adjusted_order_qty   = Column(Numeric(14, 3), nullable=False, default=0)
    estimated_total_cost = Column(Numeric(16, 4), nullable=True)

    # Timing
    lead_time_days      = Column(Integer, nullable=True)
    buffer_days         = Column(Integer, nullable=False, default=0)
    required_date       = Column(Date, nullable=True)
    suggested_order_date = Column(Date, nullable=True)

    # Classification
    urgency_level        = Column(Enum(PSUrgencyLevel), nullable=False, default=PSUrgencyLevel.MEDIUM)
    risk_flag            = Column(Boolean, default=False, nullable=False)
    risk_notes           = Column(Text, nullable=True)
    recommendation_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    status               = Column(Enum(PSSuggestionStatus), nullable=False, default=PSSuggestionStatus.DRAFT)

    # Links
    mrp_suggestion_id = Column(UUID(as_uuid=True), ForeignKey("mrp_suggestions.id",       ondelete="SET NULL"), nullable=True)
    group_id          = Column(UUID(as_uuid=True), ForeignKey("procurement_suggestion_groups.id", ondelete="SET NULL"), nullable=True)
    converted_pr_id   = Column(UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="SET NULL"), nullable=True)
    notes             = Column(Text, nullable=True)

    run            = relationship("ProcurementSuggestionRun", back_populates="lines")
    material       = relationship("Material")
    supplier       = relationship("Supplier")
    mrp_suggestion = relationship("MRPSuggestion")
    group          = relationship("ProcurementSuggestionGroup", back_populates="lines")
    converted_pr   = relationship("PurchaseRequisition")


# ── Grouped / Consolidated Orders (by supplier) ───────────────────────────────

class ProcurementSuggestionGroup(Base, TimestampMixin):
    __tablename__ = "procurement_suggestion_groups"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id               = Column(UUID(as_uuid=True), ForeignKey("procurement_suggestion_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id          = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    group_no             = Column(String(50), nullable=True)
    target_delivery_date = Column(Date, nullable=True)
    line_count           = Column(Integer, nullable=False, default=0)
    total_estimated_cost = Column(Numeric(16, 4), nullable=True)
    currency             = Column(String(10), nullable=False, default="KES")
    status               = Column(Enum(PSGroupStatus), nullable=False, default=PSGroupStatus.DRAFT)
    converted_pr_id      = Column(UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="SET NULL"), nullable=True)
    notes                = Column(Text, nullable=True)

    run          = relationship("ProcurementSuggestionRun", back_populates="groups")
    supplier     = relationship("Supplier")
    lines        = relationship("ProcurementSuggestionLine", back_populates="group")
    converted_pr = relationship("PurchaseRequisition")


# ── AI Recommendations ─────────────────────────────────────────────────────────

class PSAIRecommendation(Base, TimestampMixin):
    __tablename__ = "ps_ai_recommendations"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id            = Column(UUID(as_uuid=True), ForeignKey("procurement_suggestion_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_type        = Column(Enum(PSAIAgentType), nullable=False)
    material_id       = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="SET NULL"), nullable=True)
    supplier_id       = Column(UUID(as_uuid=True), ForeignKey("suppliers.id",  ondelete="SET NULL"), nullable=True)
    title             = Column(String(255), nullable=False)
    recommendation    = Column(Text, nullable=False)
    rationale         = Column(Text, nullable=True)
    potential_saving  = Column(Numeric(14, 4), nullable=True)
    priority          = Column(Integer, nullable=False, default=5)  # 1=highest
    is_actioned       = Column(Boolean, default=False, nullable=False)
    action_notes      = Column(Text, nullable=True)

    run      = relationship("ProcurementSuggestionRun", back_populates="ai_recommendations")
    material = relationship("Material")
    supplier = relationship("Supplier")
