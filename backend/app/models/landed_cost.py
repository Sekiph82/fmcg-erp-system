import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean,
    ForeignKey, Date, DateTime, JSON, Enum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin
from app.models.finance import OperationalPostingStatus


# ── Enums ─────────────────────────────────────────────────────────────────────

class LCStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    VALIDATED = "VALIDATED"
    POSTED    = "POSTED"
    CANCELLED = "CANCELLED"


class LandedCostType(str, enum.Enum):
    FREIGHT_SEA       = "FREIGHT_SEA"
    FREIGHT_AIR       = "FREIGHT_AIR"
    FREIGHT_LAND      = "FREIGHT_LAND"
    CUSTOMS_DUTY      = "CUSTOMS_DUTY"
    IMPORT_TAX        = "IMPORT_TAX"
    INSURANCE         = "INSURANCE"
    PORT_HANDLING     = "PORT_HANDLING"
    CLEARING_AGENT    = "CLEARING_AGENT"
    INLAND_TRANSPORT  = "INLAND_TRANSPORT"
    STORAGE           = "STORAGE"
    INSPECTION        = "INSPECTION"
    DEMURRAGE         = "DEMURRAGE"
    DETENTION         = "DETENTION"
    OTHER             = "OTHER"


class LCAllocationMethod(str, enum.Enum):
    BY_QUANTITY  = "BY_QUANTITY"
    BY_WEIGHT    = "BY_WEIGHT"
    BY_VOLUME    = "BY_VOLUME"
    BY_VALUE     = "BY_VALUE"
    EQUAL_SPLIT  = "EQUAL_SPLIT"
    CUSTOM       = "CUSTOM"


class LCReferenceType(str, enum.Enum):
    GRN      = "GRN"
    SHIPMENT = "SHIPMENT"
    PO       = "PO"
    MANUAL   = "MANUAL"


class LCAIAgentType(str, enum.Enum):
    COST_ANALYZER    = "COST_ANALYZER"
    ROUTE_OPTIMIZER  = "ROUTE_OPTIMIZER"
    VARIANCE_DETECTOR = "VARIANCE_DETECTOR"


class LCAIRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ── Models ────────────────────────────────────────────────────────────────────

class LandedCostHeader(Base, TimestampMixin):
    """Master record for a landed cost document."""
    __tablename__ = "lc_headers"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_no         = Column(String(50), unique=True, nullable=False)
    reference_type= Column(String(30), nullable=False, default="MANUAL")  # LCReferenceType
    shipment_id   = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id"), nullable=True)
    po_id         = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    vendor_name   = Column(String(200), nullable=True)
    bill_no       = Column(String(100), nullable=True)
    bill_date     = Column(Date, nullable=True)
    currency_code = Column(String(10), nullable=False, default="KES")
    exchange_rate = Column(Numeric(14, 6), nullable=False, default=1)
    exchange_rate_id = Column(
        UUID(as_uuid=True), ForeignKey("exchange_rates.id", name="fk_lc_headers_exchange_rate_id_exchange_rates", ondelete="SET NULL"), nullable=True,
        comment="Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot",
    )
    exchange_rate_date = Column(
        Date, nullable=True,
        comment="Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns",
    )
    exchange_rate_source = Column(
        String(20), nullable=True,
        comment="Added by Alembic revision 20261029_0040; source copied with the rate snapshot",
    )
    total_lc_amount_fc   = Column(Numeric(14, 4), nullable=False, default=0)
    total_lc_amount_base = Column(Numeric(14, 4), nullable=False, default=0)
    allocation_method    = Column(String(30), nullable=False, default="BY_VALUE")  # LCAllocationMethod
    status        = Column(String(20), nullable=False, default="DRAFT")  # LCStatus
    posted_at     = Column(DateTime, nullable=True)
    posted_by     = Column(String(150), nullable=True)
    notes         = Column(Text, nullable=True)

    cost_lines      = relationship("LandedCostLine", back_populates="header", cascade="all, delete-orphan")
    grn_links       = relationship("LandedCostGRNLink", back_populates="header", cascade="all, delete-orphan")
    allocation_lines= relationship("LandedCostAllocationLine", back_populates="header", cascade="all, delete-orphan")
    ai_recs         = relationship("LCAIRecommendation", back_populates="header", cascade="all, delete-orphan")
    exchange_rate_record = relationship("ExchangeRate", foreign_keys=[exchange_rate_id])


class LandedCostLine(Base, TimestampMixin):
    """Individual cost component within a landed cost document."""
    __tablename__ = "lc_lines"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id     = Column(UUID(as_uuid=True), ForeignKey("lc_headers.id"), nullable=False)
    cost_type     = Column(String(30), nullable=False)  # LandedCostType
    description   = Column(String(300), nullable=True)
    vendor_name   = Column(String(200), nullable=True)
    amount_fc     = Column(Numeric(14, 4), nullable=False, default=0)
    estimated_amount_fc = Column(Numeric(14, 4), nullable=True)
    currency_code = Column(String(10), nullable=False, default="KES")
    exchange_rate = Column(Numeric(14, 6), nullable=False, default=1)
    exchange_rate_id = Column(
        UUID(as_uuid=True), ForeignKey("exchange_rates.id", name="fk_lc_lines_exchange_rate_id_exchange_rates", ondelete="SET NULL"), nullable=True,
        comment="Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot",
    )
    exchange_rate_date = Column(
        Date, nullable=True,
        comment="Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns",
    )
    exchange_rate_source = Column(
        String(20), nullable=True,
        comment="Added by Alembic revision 20261029_0040; source copied with the rate snapshot",
    )
    amount_base   = Column(Numeric(14, 4), nullable=False, default=0)
    allocation_method = Column(String(30), nullable=True)  # override per line; NULL = use header default
    is_included_in_valuation = Column(Boolean, nullable=False, default=True)
    account_code  = Column(String(50), nullable=True)
    remarks       = Column(Text, nullable=True)

    header = relationship("LandedCostHeader", back_populates="cost_lines")
    actual_record = relationship(
        "LandedCostLineActual",
        back_populates="line",
        uselist=False,
        cascade="all, delete-orphan",
    )
    exchange_rate_record = relationship("ExchangeRate", foreign_keys=[exchange_rate_id])


class LandedCostLineActual(Base):
    """One immutable actual-cost source entry for a landed-cost line."""
    __tablename__ = "lc_line_actuals"
    __table_args__ = (
        UniqueConstraint("lc_line_id", name="uq_lc_line_actuals_lc_line_id"),
        Index("ix_lc_line_actuals_recorded_at", "recorded_at"),
        {"comment": "added by Alembic revision 20261029_0039"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_line_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lc_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount_fc = Column(Numeric(14, 4), nullable=False)
    source_reference = Column(String(200), nullable=False)
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actual_amount_base = Column(
        Numeric(14, 4), nullable=True,
        comment="Added by Alembic revision 20261029_0041; actual source amount translated at the saved landed-cost line rate",
    )
    variance_amount_base = Column(
        Numeric(14, 4), nullable=True,
        comment="Added by Alembic revision 20261029_0041; actual base amount less the immutable original posted allocation",
    )
    variance_status = Column(
        String(20), nullable=True,
        comment="Added by Alembic revision 20261029_0041; RECORDED, PENDING, POSTED, or NOT_REQUIRED",
    )
    posting_error = Column(
        Text, nullable=True,
        comment="Added by Alembic revision 20261029_0041; bounded reconciliation detail for a failed variance posting",
    )
    posted_at = Column(
        DateTime, nullable=True,
        comment="Added by Alembic revision 20261029_0041; successful actual-variance posting timestamp",
    )

    line = relationship("LandedCostLine", back_populates="actual_record")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
    variance_postings = relationship(
        "LandedCostActualVariancePosting",
        back_populates="actual",
        cascade="all, delete-orphan",
        order_by="LandedCostActualVariancePosting.id",
    )


class LandedCostActualVariancePosting(Base, TimestampMixin):
    """Immutable GL posting link for one allocation in an actual-cost variance."""
    __tablename__ = "lc_actual_variance_postings"
    __table_args__ = (
        UniqueConstraint("actual_id", "allocation_line_id", name="uq_lc_actual_variance_allocation"),
        Index("ix_lc_actual_variance_postings_batch_id", "posting_batch_id"),
        Index("ix_lc_actual_variance_postings_journal_id", "journal_entry_id"),
        Index("ix_lc_actual_variance_postings_status", "accounting_status"),
        {"comment": "Added by Alembic revision 20261029_0041"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actual_id = Column(UUID(as_uuid=True), ForeignKey("lc_line_actuals.id", ondelete="CASCADE"), nullable=False)
    allocation_line_id = Column(UUID(as_uuid=True), ForeignKey("lc_allocation_lines.id", ondelete="RESTRICT"), nullable=False)
    variance_amount_base = Column(Numeric(14, 4), nullable=False)
    posting_batch_id = Column(UUID(as_uuid=True), ForeignKey("accounting_posting_batches.id", ondelete="SET NULL"), nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    accounting_status = Column(Enum(OperationalPostingStatus, name="operational_posting_status"), nullable=True)
    posting_error = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    actual = relationship("LandedCostLineActual", back_populates="variance_postings")
    allocation_line = relationship("LandedCostAllocationLine", foreign_keys=[allocation_line_id])
    posting_batch = relationship("AccountingPostingBatch", foreign_keys=[posting_batch_id])
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])


class LandedCostGRNLink(Base, TimestampMixin):
    """Links a landed cost document to one or more GRNs."""
    __tablename__ = "lc_grn_links"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id = Column(UUID(as_uuid=True), ForeignKey("lc_headers.id"), nullable=False)
    grn_id    = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id"), nullable=False)
    grn_no    = Column(String(50), nullable=True)
    po_no     = Column(String(50), nullable=True)
    grn_value_base    = Column(Numeric(14, 4), nullable=True)   # total GRN value at purchase cost
    grn_total_qty     = Column(Numeric(14, 3), nullable=True)
    grn_total_weight  = Column(Numeric(14, 3), nullable=True)
    grn_total_volume  = Column(Numeric(14, 3), nullable=True)
    allocation_share  = Column(Numeric(7, 4), nullable=True)    # % of total LC allocated to this GRN

    header = relationship("LandedCostHeader", back_populates="grn_links")


class LandedCostAllocationLine(Base, TimestampMixin):
    """Per-GRN-line allocation result after running the allocation engine."""
    __tablename__ = "lc_allocation_lines"
    __table_args__ = (
        Index("ix_lc_allocation_lines_posting_batch_id", "posting_batch_id"),
        Index("ix_lc_allocation_lines_journal_entry_id", "journal_entry_id"),
        Index("ix_lc_allocation_lines_accounting_status", "accounting_status"),
    )

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id     = Column(UUID(as_uuid=True), ForeignKey("lc_headers.id"), nullable=False)
    lc_line_id    = Column(UUID(as_uuid=True), ForeignKey("lc_lines.id"), nullable=False)
    grn_id        = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id"), nullable=True)
    grn_line_id   = Column(UUID(as_uuid=True), ForeignKey("grn_lines.id"), nullable=True)
    material_id   = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    material_name = Column(String(200), nullable=True)
    lot_no        = Column(String(100), nullable=True)
    received_qty  = Column(Numeric(14, 3), nullable=True)
    received_weight = Column(Numeric(14, 3), nullable=True)
    received_volume = Column(Numeric(14, 6), nullable=True)
    purchase_value  = Column(Numeric(14, 4), nullable=True)
    allocation_basis= Column(Numeric(14, 6), nullable=True)  # the basis value used (qty/weight/value)
    allocation_share= Column(Numeric(7, 4), nullable=True)   # % share
    allocated_amount= Column(Numeric(14, 4), nullable=False, default=0)
    per_unit_lc_cost= Column(Numeric(14, 6), nullable=True)
    is_posted       = Column(Boolean, nullable=False, default=False)
    inventory_adj_id= Column(UUID(as_uuid=True), ForeignKey("lc_inventory_adjustments.id"), nullable=True)
    posting_batch_id = Column(UUID(as_uuid=True), ForeignKey("accounting_posting_batches.id", ondelete="SET NULL"),
                              nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    accounting_status = Column(Enum(OperationalPostingStatus, name="operational_posting_status"), nullable=True)
    posting_error = Column(Text, nullable=True)

    header   = relationship("LandedCostHeader", back_populates="allocation_lines")
    inv_adj  = relationship("LCInventoryAdjustment", back_populates="allocation_line", foreign_keys=[inventory_adj_id])
    posting_batch = relationship("AccountingPostingBatch", foreign_keys=[posting_batch_id])
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])


class LCInventoryAdjustment(Base, TimestampMixin):
    """Inventory valuation adjustment record created when posting a landed cost."""
    __tablename__ = "lc_inventory_adjustments"
    __table_args__ = (
        Index("ix_lc_inventory_adjustments_posting_batch_id", "posting_batch_id"),
        Index("ix_lc_inventory_adjustments_journal_entry_id", "journal_entry_id"),
        Index("ix_lc_inventory_adjustments_accounting_status", "accounting_status"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id       = Column(UUID(as_uuid=True), ForeignKey("lc_headers.id"), nullable=False)
    grn_line_id     = Column(UUID(as_uuid=True), ForeignKey("grn_lines.id"), nullable=True)
    material_id     = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    lot_no          = Column(String(100), nullable=True)
    adjustment_amount = Column(Numeric(14, 4), nullable=False, default=0)
    per_unit_amount   = Column(Numeric(14, 6), nullable=True)
    qty_on_hand       = Column(Numeric(14, 3), nullable=True)
    old_avg_cost      = Column(Numeric(14, 6), nullable=True)
    new_avg_cost      = Column(Numeric(14, 6), nullable=True)
    journal_ref       = Column(String(100), nullable=True)
    posting_batch_id  = Column(UUID(as_uuid=True), ForeignKey("accounting_posting_batches.id", ondelete="SET NULL"),
                               nullable=True)
    journal_entry_id  = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    accounting_status = Column(Enum(OperationalPostingStatus, name="operational_posting_status"), nullable=True)
    posting_error     = Column(Text, nullable=True)
    posted_at         = Column(DateTime, nullable=True)

    allocation_line = relationship(
        "LandedCostAllocationLine",
        back_populates="inv_adj",
        foreign_keys="[LandedCostAllocationLine.inventory_adj_id]",
    )
    posting_batch = relationship("AccountingPostingBatch", foreign_keys=[posting_batch_id])
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])


class LCAIRecommendation(Base, TimestampMixin):
    __tablename__ = "lc_ai_recommendations"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id        = Column(UUID(as_uuid=True), ForeignKey("lc_headers.id"), nullable=True)
    agent_type       = Column(String(30), nullable=False)  # LCAIAgentType
    status           = Column(String(20), nullable=False, default="PENDING")  # LCAIRecStatus
    title            = Column(String(300), nullable=False)
    explanation      = Column(Text, nullable=True)
    impact_summary   = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    data_snapshot    = Column(JSON, nullable=True)
    actioned_at      = Column(DateTime, nullable=True)
    actioned_by      = Column(String(150), nullable=True)

    header = relationship("LandedCostHeader", back_populates="ai_recs")
