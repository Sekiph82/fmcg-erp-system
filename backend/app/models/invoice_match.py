import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Date, DateTime, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class MatchLineStatus(str, enum.Enum):
    FULLY_MATCHED              = "FULLY_MATCHED"
    MATCHED_WITHIN_TOLERANCE   = "MATCHED_WITHIN_TOLERANCE"
    QUANTITY_MISMATCH          = "QUANTITY_MISMATCH"
    PRICE_MISMATCH             = "PRICE_MISMATCH"
    TAX_MISMATCH               = "TAX_MISMATCH"
    MISSING_PO                 = "MISSING_PO"
    MISSING_GRN                = "MISSING_GRN"
    PARTIAL_MATCH              = "PARTIAL_MATCH"
    OVERBILLED                 = "OVERBILLED"
    BLOCKED                    = "BLOCKED"
    APPROVED_EXCEPTION         = "APPROVED_EXCEPTION"
    REJECTED                   = "REJECTED"


class MatchOverallStatus(str, enum.Enum):
    FULLY_MATCHED              = "FULLY_MATCHED"
    MATCHED_WITHIN_TOLERANCE   = "MATCHED_WITHIN_TOLERANCE"
    PARTIAL_MATCH              = "PARTIAL_MATCH"
    QUANTITY_MISMATCH          = "QUANTITY_MISMATCH"
    PRICE_MISMATCH             = "PRICE_MISMATCH"
    MISSING_PO                 = "MISSING_PO"
    MISSING_GRN                = "MISSING_GRN"
    DUPLICATE_SUSPECTED        = "DUPLICATE_SUSPECTED"
    BLOCKED                    = "BLOCKED"
    APPROVED_EXCEPTION         = "APPROVED_EXCEPTION"
    REJECTED                   = "REJECTED"
    PENDING_REVIEW             = "PENDING_REVIEW"


class MatchReviewAction(str, enum.Enum):
    APPROVED_EXCEPTION = "APPROVED_EXCEPTION"
    REJECTED           = "REJECTED"
    ESCALATED          = "ESCALATED"
    INFO_REQUESTED     = "INFO_REQUESTED"


class DuplicateRisk(str, enum.Enum):
    EXACT     = "EXACT"
    SUSPECTED = "SUSPECTED"
    LOW       = "LOW"


class IMAIAgentType(str, enum.Enum):
    ANOMALY_DETECTOR     = "ANOMALY_DETECTOR"
    EXCEPTION_PRIORITIZER = "EXCEPTION_PRIORITIZER"
    TOLERANCE_TUNER      = "TOLERANCE_TUNER"


class IMAIRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ── Tolerance Rules ───────────────────────────────────────────────────────────

class InvoiceMatchTolerance(Base, TimestampMixin):
    """Configurable tolerance rules for 3-way matching."""
    __tablename__ = "im_tolerance_rules"

    id                           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name                    = Column(String(200), nullable=False)
    supplier_id                  = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    # item_category_id would link to a category table; stored as string for flexibility
    item_category                = Column(String(100), nullable=True)
    quantity_tolerance_pct       = Column(Numeric(7, 3), nullable=False, default=1)   # %
    quantity_tolerance_abs       = Column(Numeric(14, 3), nullable=True)              # absolute units
    price_tolerance_pct          = Column(Numeric(7, 3), nullable=False, default=2)   # %
    price_tolerance_abs          = Column(Numeric(14, 4), nullable=True)              # per unit
    tax_tolerance_pct            = Column(Numeric(7, 3), nullable=False, default=0)
    auto_approve_within_tolerance = Column(Boolean, nullable=False, default=True)
    block_payment_beyond_tolerance= Column(Boolean, nullable=False, default=True)
    approval_role_required        = Column(String(100), nullable=True)  # e.g. finance_manager
    is_active                    = Column(Boolean, nullable=False, default=True)
    priority                     = Column(Integer, nullable=False, default=10)  # lower = higher priority
    notes                        = Column(Text, nullable=True)


# ── Match Header ──────────────────────────────────────────────────────────────

class InvoiceMatchHeader(Base, TimestampMixin):
    """Master 3-way match record for a supplier invoice."""
    __tablename__ = "im_headers"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_no              = Column(String(50), unique=True, nullable=False)
    invoice_id            = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id"), nullable=False)
    po_id                 = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    supplier_id           = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    invoice_no            = Column(String(100), nullable=True)  # denormalised for quick filtering
    invoice_date          = Column(Date, nullable=True)
    currency              = Column(String(10), nullable=False, default="USD")
    invoice_total         = Column(Numeric(16, 4), nullable=False, default=0)
    overall_status        = Column(String(40), nullable=False, default="PENDING_REVIEW")
    duplicate_flag        = Column(Boolean, nullable=False, default=False)
    review_required       = Column(Boolean, nullable=False, default=False)
    is_payable            = Column(Boolean, nullable=False, default=False)
    payment_hold_reason   = Column(Text, nullable=True)
    reviewed_by           = Column(String(150), nullable=True)
    reviewed_at           = Column(DateTime, nullable=True)
    approved_by           = Column(String(150), nullable=True)
    approved_at           = Column(DateTime, nullable=True)
    notes                 = Column(Text, nullable=True)
    run_at                = Column(DateTime, nullable=True)

    match_lines  = relationship("InvoiceMatchLine", back_populates="header", cascade="all, delete-orphan")
    reviews      = relationship("InvoiceMatchReview", back_populates="header", cascade="all, delete-orphan")
    ai_recs      = relationship("IMAIRecommendation", back_populates="header", cascade="all, delete-orphan")


# ── Match Line ────────────────────────────────────────────────────────────────

class InvoiceMatchLine(Base, TimestampMixin):
    """Per-line 3-way comparison result."""
    __tablename__ = "im_lines"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id             = Column(UUID(as_uuid=True), ForeignKey("im_headers.id"), nullable=False)
    invoice_line_id       = Column(UUID(as_uuid=True), ForeignKey("purchase_invoice_lines.id"), nullable=True)
    po_line_id            = Column(UUID(as_uuid=True), ForeignKey("po_lines.id"), nullable=True)
    material_id           = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    material_name         = Column(String(200), nullable=True)
    description           = Column(String(300), nullable=True)
    # PO values
    ordered_qty           = Column(Numeric(14, 3), nullable=True)
    ordered_unit_price    = Column(Numeric(14, 4), nullable=True)
    ordered_tax_rate      = Column(Numeric(6, 4), nullable=True)
    # GRN cumulative values
    total_received_qty    = Column(Numeric(14, 3), nullable=True)
    total_accepted_qty    = Column(Numeric(14, 3), nullable=True)
    prev_invoiced_qty     = Column(Numeric(14, 3), nullable=False, default=0)  # already billed before this invoice
    billable_qty          = Column(Numeric(14, 3), nullable=True)              # accepted - already invoiced
    # Invoice values
    invoiced_qty          = Column(Numeric(14, 3), nullable=True)
    invoiced_unit_price   = Column(Numeric(14, 4), nullable=True)
    invoiced_tax_rate     = Column(Numeric(6, 4), nullable=True)
    invoiced_line_total   = Column(Numeric(16, 4), nullable=True)
    # Variances
    qty_variance          = Column(Numeric(14, 3), nullable=True)   # invoiced - accepted
    price_variance        = Column(Numeric(14, 4), nullable=True)   # invoiced_price - po_price
    tax_variance          = Column(Numeric(6, 4), nullable=True)
    qty_variance_pct      = Column(Numeric(7, 3), nullable=True)
    price_variance_pct    = Column(Numeric(7, 3), nullable=True)
    # Outcome
    match_status          = Column(String(40), nullable=False, default="PARTIAL_MATCH")
    tolerance_rule_id     = Column(UUID(as_uuid=True), ForeignKey("im_tolerance_rules.id"), nullable=True)
    action_required       = Column(Boolean, nullable=False, default=False)
    notes                 = Column(Text, nullable=True)

    header        = relationship("InvoiceMatchHeader", back_populates="match_lines")
    grn_links     = relationship("InvoiceMatchGRNLink", back_populates="match_line", cascade="all, delete-orphan")
    tolerance_rule= relationship("InvoiceMatchTolerance")


# ── GRN Link (many GRN lines per match line) ──────────────────────────────────

class InvoiceMatchGRNLink(Base, TimestampMixin):
    """Links a match line to one or more GRN lines (audit trail)."""
    __tablename__ = "im_grn_links"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_line_id   = Column(UUID(as_uuid=True), ForeignKey("im_lines.id"), nullable=False)
    grn_id          = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id"), nullable=True)
    grn_line_id     = Column(UUID(as_uuid=True), ForeignKey("grn_lines.id"), nullable=True)
    grn_no          = Column(String(50), nullable=True)
    received_qty    = Column(Numeric(14, 3), nullable=True)
    accepted_qty    = Column(Numeric(14, 3), nullable=True)
    rejected_qty    = Column(Numeric(14, 3), nullable=True)
    received_date   = Column(Date, nullable=True)

    match_line = relationship("InvoiceMatchLine", back_populates="grn_links")


# ── Duplicate Detection Log ───────────────────────────────────────────────────

class DuplicateInvoiceLog(Base, TimestampMixin):
    """Records suspected or confirmed duplicate invoices."""
    __tablename__ = "im_duplicate_logs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id          = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id"), nullable=False)
    matched_invoice_id  = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id"), nullable=True)
    supplier_id         = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    invoice_no          = Column(String(100), nullable=True)
    matched_invoice_no  = Column(String(100), nullable=True)
    duplicate_risk      = Column(String(20), nullable=False, default="SUSPECTED")  # DuplicateRisk
    match_reasons       = Column(JSON, nullable=True)     # list of matched fields
    similarity_score    = Column(Numeric(5, 2), nullable=True)
    is_resolved         = Column(Boolean, nullable=False, default=False)
    resolved_by         = Column(String(150), nullable=True)
    resolved_at         = Column(DateTime, nullable=True)
    resolution_notes    = Column(Text, nullable=True)


# ── Review / Approval Workflow ────────────────────────────────────────────────

class InvoiceMatchReview(Base, TimestampMixin):
    """Approval / review event log for a match header."""
    __tablename__ = "im_reviews"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id       = Column(UUID(as_uuid=True), ForeignKey("im_headers.id"), nullable=False)
    action          = Column(String(30), nullable=False)   # MatchReviewAction
    reviewer_name   = Column(String(150), nullable=False)
    reviewer_role   = Column(String(100), nullable=True)
    previous_status = Column(String(40), nullable=True)
    new_status      = Column(String(40), nullable=True)
    justification   = Column(Text, nullable=True)
    line_ids        = Column(JSON, nullable=True)   # specific lines if partial action

    header = relationship("InvoiceMatchHeader", back_populates="reviews")


# ── AI Recommendations ────────────────────────────────────────────────────────

class IMAIRecommendation(Base, TimestampMixin):
    __tablename__ = "im_ai_recommendations"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id        = Column(UUID(as_uuid=True), ForeignKey("im_headers.id"), nullable=True)
    agent_type       = Column(String(40), nullable=False)
    status           = Column(String(20), nullable=False, default="PENDING")
    title            = Column(String(300), nullable=False)
    explanation      = Column(Text, nullable=True)
    impact_summary   = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    priority         = Column(String(10), nullable=False, default="MEDIUM")  # LOW/MEDIUM/HIGH/CRITICAL
    confidence_score = Column(Numeric(5, 2), nullable=True)
    data_snapshot    = Column(JSON, nullable=True)
    actioned_at      = Column(DateTime, nullable=True)
    actioned_by      = Column(String(150), nullable=True)

    header = relationship("InvoiceMatchHeader", back_populates="ai_recs")
