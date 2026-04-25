import uuid
import enum
from datetime import date
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class SCOrderStatus(str, enum.Enum):
    DRAFT              = "DRAFT"
    APPROVED           = "APPROVED"
    ISSUED             = "ISSUED"
    IN_PROGRESS        = "IN_PROGRESS"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    COMPLETED          = "COMPLETED"
    CLOSED             = "CLOSED"
    CANCELLED          = "CANCELLED"


class SCIssueStatus(str, enum.Enum):
    DRAFT              = "DRAFT"
    ISSUED             = "ISSUED"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    RETURNED           = "RETURNED"


class SCReceiptStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    POSTED   = "POSTED"
    QC_HOLD  = "QC_HOLD"
    REJECTED = "REJECTED"


class SCYieldStatus(str, enum.Enum):
    NORMAL      = "NORMAL"
    LOW_YIELD   = "LOW_YIELD"
    HIGH_SCRAP  = "HIGH_SCRAP"
    ABNORMAL    = "ABNORMAL"


class SCAIAgentType(str, enum.Enum):
    PERFORMANCE_ANALYZER = "PERFORMANCE_ANALYZER"
    COST_OPTIMIZER       = "COST_OPTIMIZER"
    RISK_DETECTOR        = "RISK_DETECTOR"


class ScrapReasonCode(str, enum.Enum):
    PROCESS_LOSS   = "PROCESS_LOSS"
    QUALITY_DEFECT = "QUALITY_DEFECT"
    HANDLING_DAMAGE= "HANDLING_DAMAGE"
    CONTAMINATION  = "CONTAMINATION"
    EXPIRED        = "EXPIRED"
    OTHER          = "OTHER"


# ── Subcontractor Virtual Location ────────────────────────────────────────────

class SubcontractorLocation(Base, TimestampMixin):
    """Virtual warehouse that represents a subcontractor's premises."""
    __tablename__ = "subcontractor_locations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"),
                         nullable=False, unique=True, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"),
                          nullable=False, unique=True)
    is_active    = Column(Boolean, default=True, nullable=False)
    notes        = Column(Text, nullable=True)

    supplier  = relationship("Supplier")
    warehouse = relationship("Warehouse")


# ── Subcontracting Order Header ───────────────────────────────────────────────

class SubcontractOrder(Base, TimestampMixin):
    __tablename__ = "subcontract_orders"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no                 = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id              = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"),
                                      nullable=False, index=True)
    order_date               = Column(Date, nullable=False)
    expected_completion_date = Column(Date, nullable=True)
    actual_completion_date   = Column(Date, nullable=True)
    status                   = Column(Enum(SCOrderStatus), nullable=False, default=SCOrderStatus.DRAFT)
    linked_po_id             = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"),
                                      nullable=True)
    warehouse_id             = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"),
                                      nullable=True)          # source warehouse for material issue
    subcontractor_location_id = Column(UUID(as_uuid=True),
                                       ForeignKey("subcontractor_locations.id", ondelete="SET NULL"),
                                       nullable=True)

    # Cost summary
    total_material_cost    = Column(Numeric(16, 4), nullable=True)
    total_service_cost     = Column(Numeric(16, 4), nullable=True)
    total_wastage_cost     = Column(Numeric(16, 4), nullable=True)
    currency               = Column(String(10), nullable=False, default="KES")

    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at    = Column(DateTime(timezone=True), nullable=True)
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks        = Column(Text, nullable=True)

    supplier                = relationship("Supplier")
    warehouse               = relationship("Warehouse")
    subcontractor_location  = relationship("SubcontractorLocation")
    linked_po               = relationship("PurchaseOrder")
    approved_by             = relationship("User", foreign_keys=[approved_by_id])
    created_by              = relationship("User", foreign_keys=[created_by_id])
    lines                   = relationship("SubcontractOrderLine", back_populates="order",
                                            cascade="all, delete-orphan")
    material_issues         = relationship("SubcontractMaterialIssue", back_populates="order",
                                            cascade="all, delete-orphan")
    receipts                = relationship("SubcontractReceipt", back_populates="order",
                                            cascade="all, delete-orphan")
    yield_records           = relationship("SubcontractYieldRecord", back_populates="order",
                                            cascade="all, delete-orphan")
    ai_recommendations      = relationship("SCAIRecommendation", back_populates="order",
                                            cascade="all, delete-orphan")


# ── Subcontracting Order Line (what to produce) ───────────────────────────────

class SubcontractOrderLine(Base, TimestampMixin):
    __tablename__ = "subcontract_order_lines"
    __table_args__ = (UniqueConstraint("order_id", "line_no", name="uq_sc_order_line"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id            = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    line_no             = Column(Integer, nullable=False)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"),
                                 nullable=True)
    material_id         = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"),
                                 nullable=True)
    description         = Column(String(255), nullable=True)
    quantity_ordered    = Column(Numeric(14, 3), nullable=False)
    quantity_received   = Column(Numeric(14, 3), nullable=False, default=0)
    uom                 = Column(String(20), nullable=False, default="KG")
    bom_id              = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="SET NULL"),
                                 nullable=True)
    service_unit_cost   = Column(Numeric(14, 4), nullable=True)  # cost per unit of output
    estimated_yield_pct = Column(Numeric(7, 3), nullable=True, default=100)
    notes               = Column(Text, nullable=True)

    order    = relationship("SubcontractOrder", back_populates="lines")
    product  = relationship("Product")
    material = relationship("Material")
    bom      = relationship("AdvancedBOM")


# ── Material Issue Header ─────────────────────────────────────────────────────

class SubcontractMaterialIssue(Base, TimestampMixin):
    __tablename__ = "subcontract_material_issues"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_no     = Column(String(50), unique=True, nullable=False, index=True)
    order_id     = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    issue_date   = Column(Date, nullable=False)
    status       = Column(Enum(SCIssueStatus), nullable=False, default=SCIssueStatus.DRAFT)
    issued_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes        = Column(Text, nullable=True)

    order     = relationship("SubcontractOrder", back_populates="material_issues")
    issued_by = relationship("User")
    lines     = relationship("SubcontractMaterialIssueLine", back_populates="issue",
                              cascade="all, delete-orphan")


# ── Material Issue Line ───────────────────────────────────────────────────────

class SubcontractMaterialIssueLine(Base, TimestampMixin):
    __tablename__ = "subcontract_material_issue_lines"
    __table_args__ = (UniqueConstraint("issue_id", "line_no", name="uq_sc_issue_line"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id            = Column(UUID(as_uuid=True), ForeignKey("subcontract_material_issues.id",
                                                                  ondelete="CASCADE"),
                                  nullable=False, index=True)
    line_no             = Column(Integer, nullable=False)
    material_id         = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"),
                                  nullable=False)
    lot_id              = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"),
                                  nullable=True)
    quantity_issued     = Column(Numeric(14, 3), nullable=False)
    quantity_returned   = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_consumed   = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_scrapped   = Column(Numeric(14, 3), nullable=False, default=0)
    uom                 = Column(String(20), nullable=False, default="KG")
    unit_cost           = Column(Numeric(14, 4), nullable=True)
    stock_movement_id   = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"),
                                  nullable=True)
    notes               = Column(Text, nullable=True)

    issue          = relationship("SubcontractMaterialIssue", back_populates="lines")
    material       = relationship("Material")
    lot            = relationship("Lot")
    stock_movement = relationship("StockMovement")


# ── Receipt Header ────────────────────────────────────────────────────────────

class SubcontractReceipt(Base, TimestampMixin):
    __tablename__ = "subcontract_receipts"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_no          = Column(String(50), unique=True, nullable=False, index=True)
    order_id            = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    receipt_date        = Column(Date, nullable=False)
    status              = Column(Enum(SCReceiptStatus), nullable=False, default=SCReceiptStatus.DRAFT)
    received_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    qc_inspection_id    = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="SET NULL"),
                                  nullable=True)
    notes               = Column(Text, nullable=True)

    order          = relationship("SubcontractOrder", back_populates="receipts")
    received_by    = relationship("User")
    qc_inspection  = relationship("QCInspection")
    lines          = relationship("SubcontractReceiptLine", back_populates="receipt",
                                   cascade="all, delete-orphan")


# ── Receipt Line ──────────────────────────────────────────────────────────────

class SubcontractReceiptLine(Base, TimestampMixin):
    __tablename__ = "subcontract_receipt_lines"
    __table_args__ = (UniqueConstraint("receipt_id", "line_no", name="uq_sc_receipt_line"),)

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id           = Column(UUID(as_uuid=True), ForeignKey("subcontract_receipts.id", ondelete="CASCADE"),
                                   nullable=False, index=True)
    order_line_id        = Column(UUID(as_uuid=True), ForeignKey("subcontract_order_lines.id",
                                                                    ondelete="SET NULL"), nullable=True)
    line_no              = Column(Integer, nullable=False)
    product_id           = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"),
                                   nullable=True)
    material_id          = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"),
                                   nullable=True)
    quantity_received    = Column(Numeric(14, 3), nullable=False)
    quantity_accepted    = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_rejected    = Column(Numeric(14, 3), nullable=False, default=0)
    uom                  = Column(String(20), nullable=False, default="KG")
    lot_number           = Column(String(100), nullable=True)
    expiry_date          = Column(Date, nullable=True)
    unit_service_cost    = Column(Numeric(14, 4), nullable=True)
    stock_movement_id    = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"),
                                   nullable=True)
    notes                = Column(Text, nullable=True)

    receipt        = relationship("SubcontractReceipt", back_populates="lines")
    order_line     = relationship("SubcontractOrderLine")
    product        = relationship("Product")
    material       = relationship("Material")
    stock_movement = relationship("StockMovement")


# ── Yield Record (per order line) ─────────────────────────────────────────────

class SubcontractYieldRecord(Base, TimestampMixin):
    __tablename__ = "subcontract_yield_records"
    __table_args__ = (UniqueConstraint("order_id", "order_line_id", name="uq_sc_yield"),)

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id                = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                                      nullable=False, index=True)
    order_line_id           = Column(UUID(as_uuid=True), ForeignKey("subcontract_order_lines.id",
                                                                      ondelete="CASCADE"), nullable=False)

    # Input
    total_material_issued   = Column(Numeric(14, 3), nullable=False, default=0)
    expected_material_input = Column(Numeric(14, 3), nullable=True)  # from BOM

    # Output
    quantity_ordered        = Column(Numeric(14, 3), nullable=False)
    quantity_received       = Column(Numeric(14, 3), nullable=False, default=0)

    # Yield
    expected_yield_pct      = Column(Numeric(7, 3), nullable=True)
    actual_yield_pct        = Column(Numeric(7, 3), nullable=True)
    yield_variance_pct      = Column(Numeric(7, 3), nullable=True)
    yield_status            = Column(Enum(SCYieldStatus), nullable=False, default=SCYieldStatus.NORMAL)

    # Scrap
    total_scrapped          = Column(Numeric(14, 3), nullable=False, default=0)
    scrap_reason            = Column(Enum(ScrapReasonCode), nullable=True)
    scrap_cost              = Column(Numeric(14, 4), nullable=True)

    # Variance
    material_variance_qty   = Column(Numeric(14, 3), nullable=True)  # issued - expected
    material_variance_cost  = Column(Numeric(14, 4), nullable=True)

    is_abnormal             = Column(Boolean, default=False, nullable=False)
    notes                   = Column(Text, nullable=True)

    order      = relationship("SubcontractOrder", back_populates="yield_records")
    order_line = relationship("SubcontractOrderLine")


# ── Performance Record (per order, for KPI tracking) ─────────────────────────

class SCPerformanceRecord(Base, TimestampMixin):
    __tablename__ = "sc_performance_records"
    __table_args__ = (UniqueConstraint("order_id", name="uq_sc_perf_order"),)

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id              = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                                    nullable=False, unique=True, index=True)
    supplier_id           = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"),
                                    nullable=False, index=True)

    # Delivery
    planned_completion    = Column(Date, nullable=True)
    actual_completion     = Column(Date, nullable=True)
    delay_days            = Column(Integer, nullable=True)
    on_time               = Column(Boolean, nullable=True)

    # Quality
    total_qty_ordered     = Column(Numeric(14, 3), nullable=False, default=0)
    total_qty_received    = Column(Numeric(14, 3), nullable=False, default=0)
    total_qty_rejected    = Column(Numeric(14, 3), nullable=False, default=0)
    rejection_rate_pct    = Column(Numeric(7, 3), nullable=True)

    # Yield
    avg_yield_pct         = Column(Numeric(7, 3), nullable=True)

    # Cost
    budgeted_cost         = Column(Numeric(16, 4), nullable=True)
    actual_cost           = Column(Numeric(16, 4), nullable=True)
    cost_variance_pct     = Column(Numeric(7, 3), nullable=True)

    # Overall score (0-100)
    performance_score     = Column(Numeric(5, 2), nullable=True)
    notes                 = Column(Text, nullable=True)

    order    = relationship("SubcontractOrder")
    supplier = relationship("Supplier")


# ── AI Recommendations ────────────────────────────────────────────────────────

class SCAIRecommendation(Base, TimestampMixin):
    __tablename__ = "sc_ai_recommendations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id        = Column(UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
                              nullable=True, index=True)
    supplier_id     = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"),
                              nullable=True, index=True)
    agent_type      = Column(Enum(SCAIAgentType), nullable=False)
    title           = Column(String(255), nullable=False)
    recommendation  = Column(Text, nullable=False)
    rationale       = Column(Text, nullable=True)
    risk_level      = Column(String(20), nullable=True)  # LOW / MEDIUM / HIGH / CRITICAL
    potential_saving = Column(Numeric(14, 4), nullable=True)
    priority        = Column(Integer, nullable=False, default=5)
    is_actioned     = Column(Boolean, default=False, nullable=False)
    action_notes    = Column(Text, nullable=True)

    order    = relationship("SubcontractOrder", back_populates="ai_recommendations")
    supplier = relationship("Supplier")
