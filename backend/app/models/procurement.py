import uuid
import enum
from datetime import date
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin
from app.models.finance import OperationalPostingStatus


class POPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class PRStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CONVERTED = "CONVERTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class POStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ORDERED = "ORDERED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class GRNStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"


class ImportShipmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"
    DELIVERED = "DELIVERED"


class PurchaseRequisition(Base, TimestampMixin):
    __tablename__ = "purchase_requisitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_no = Column(String(50), unique=True, nullable=False, index=True)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    department = Column(String(100), nullable=True)
    required_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(Enum(PRStatus), nullable=False, default=PRStatus.DRAFT)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    requester = relationship("User", foreign_keys=[requester_id])
    approver = relationship("User", foreign_keys=[approved_by_id])
    lines = relationship("PRLine", back_populates="pr", cascade="all, delete-orphan",
                         order_by="PRLine.line_no")


class PRLine(Base, TimestampMixin):
    __tablename__ = "pr_lines"
    __table_args__ = (UniqueConstraint("pr_id", "line_no", name="uq_pr_line"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    description = Column(String(255), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="KG")
    estimated_unit_cost = Column(Numeric(14, 4), nullable=True)
    preferred_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    pr = relationship("PurchaseRequisition", back_populates="lines")
    material = relationship("Material")
    product = relationship("Product")
    preferred_supplier = relationship("Supplier")


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_no = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="SET NULL"), nullable=True)
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    payment_terms = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    exchange_rate = Column(Numeric(10, 6), nullable=False, default=1.0)
    status = Column(Enum(POStatus), nullable=False, default=POStatus.DRAFT)
    notes = Column(Text, nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Payment tracking (optional — only populated when payments are made)
    payment_status = Column(Enum(POPaymentStatus), nullable=False, default=POPaymentStatus.PENDING)
    payment_method = Column(String(20), nullable=True)   # overrides supplier preferred; freeform to stay flexible
    mpesa_reference = Column(String(100), nullable=True)  # last successful M-Pesa reference

    supplier = relationship("Supplier")
    pr = relationship("PurchaseRequisition")
    approver = relationship("User", foreign_keys=[approved_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    lines = relationship("POLine", back_populates="po", cascade="all, delete-orphan",
                         order_by="POLine.line_no")
    goods_receipts = relationship("GoodsReceipt", back_populates="po")
    import_shipment = relationship("ImportShipment", back_populates="po", uselist=False)
    supplier_payments = relationship(
        "SupplierPayment", back_populates="po",
        order_by="SupplierPayment.created_at",
        cascade="all, delete-orphan",
    )


class POLine(Base, TimestampMixin):
    __tablename__ = "po_lines"
    __table_args__ = (UniqueConstraint("po_id", "line_no", name="uq_po_line"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    pr_line_id = Column(UUID(as_uuid=True), ForeignKey("pr_lines.id", ondelete="SET NULL"), nullable=True)
    line_no = Column(Integer, nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    description = Column(String(255), nullable=True)
    ordered_quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="KG")
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    tax_rate = Column(Numeric(6, 4), nullable=False, default=0)
    received_quantity = Column(Numeric(14, 3), nullable=False, default=0)

    po = relationship("PurchaseOrder", back_populates="lines")
    pr_line = relationship("PRLine")
    material = relationship("Material")
    product = relationship("Product")


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grn_no = Column(String(50), unique=True, nullable=False, index=True)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False)
    received_date = Column(Date, nullable=False)
    received_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(Enum(GRNStatus), nullable=False, default=GRNStatus.DRAFT)

    po = relationship("PurchaseOrder", back_populates="goods_receipts")
    received_by = relationship("User")
    warehouse = relationship("Warehouse")
    lines = relationship("GRNLine", back_populates="grn", cascade="all, delete-orphan")


class GRNLine(Base, TimestampMixin):
    __tablename__ = "grn_lines"
    __table_args__ = (
        Index("ix_grn_lines_posting_batch_id", "posting_batch_id"),
        Index("ix_grn_lines_journal_entry_id", "journal_entry_id"),
        Index("ix_grn_lines_accounting_status", "accounting_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grn_id = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False)
    po_line_id = Column(UUID(as_uuid=True), ForeignKey("po_lines.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    received_quantity = Column(Numeric(14, 3), nullable=False)
    accepted_quantity = Column(Numeric(14, 3), nullable=False)
    rejected_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="KG")
    lot_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    stock_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True)
    posting_batch_id = Column(UUID(as_uuid=True), ForeignKey("accounting_posting_batches.id", ondelete="SET NULL"),
                              nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    accounting_status = Column(Enum(OperationalPostingStatus, name="operational_posting_status"), nullable=True)
    posting_error = Column(Text, nullable=True)

    grn = relationship("GoodsReceipt", back_populates="lines")
    po_line = relationship("POLine")
    material = relationship("Material")
    product = relationship("Product")
    posting_batch = relationship("AccountingPostingBatch", foreign_keys=[posting_batch_id])
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])


class ImportShipment(Base, TimestampMixin):
    __tablename__ = "import_shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_no = Column(String(50), unique=True, nullable=False, index=True)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False)
    bl_number = Column(String(100), nullable=True)
    vessel_name = Column(String(255), nullable=True)
    port_of_loading = Column(String(100), nullable=True)
    port_of_discharge = Column(String(100), nullable=True)
    eta = Column(Date, nullable=True)
    ata = Column(Date, nullable=True)
    customs_ref = Column(String(100), nullable=True)
    customs_cleared_at = Column(DateTime(timezone=True), nullable=True)
    landed_cost_freight = Column(Numeric(14, 2), nullable=True)
    landed_cost_insurance = Column(Numeric(14, 2), nullable=True)
    landed_cost_duties = Column(Numeric(14, 2), nullable=True)
    landed_cost_other = Column(Numeric(14, 2), nullable=True)
    status = Column(Enum(ImportShipmentStatus), nullable=False, default=ImportShipmentStatus.PENDING)
    notes = Column(Text, nullable=True)

    po = relationship("PurchaseOrder", back_populates="import_shipment")


class SupplierPayment(Base, TimestampMixin):
    """
    Records a payment made to a supplier against a PO.
    Supports bank, cash and M-Pesa. Partial payments are allowed.
    Intended as the source of truth for future finance module reconciliation.
    """
    __tablename__ = "supplier_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    method = Column(String(20), nullable=False, default="bank")   # bank | cash | mpesa
    reference = Column(String(100), nullable=True)                # M-Pesa receipt / bank ref
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    po = relationship("PurchaseOrder", back_populates="supplier_payments")
    supplier = relationship("Supplier")
    created_by = relationship("User")


class RFQStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    RESPONSES_RECEIVED = "RESPONSES_RECEIVED"
    AWARDED = "AWARDED"
    CANCELLED = "CANCELLED"


class RFQResponseStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    AWARDED = "AWARDED"
    REJECTED = "REJECTED"


class BPAStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RFQRequest(Base, TimestampMixin):
    __tablename__ = "rfq_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_no = Column(String(50), unique=True, nullable=False, index=True)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(500), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="KG")
    required_by = Column(Date, nullable=True)
    response_deadline = Column(Date, nullable=True)
    status = Column(Enum(RFQStatus), nullable=False, default=RFQStatus.DRAFT)
    awarded_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(1000), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    pr = relationship("PurchaseRequisition")
    awarded_supplier = relationship("Supplier", foreign_keys=[awarded_supplier_id])
    responses = relationship("RFQResponse", back_populates="rfq", cascade="all, delete-orphan")


class RFQResponse(Base, TimestampMixin):
    __tablename__ = "rfq_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id = Column(UUID(as_uuid=True), ForeignKey("rfq_requests.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    quoted_unit_price = Column(Numeric(14, 4), nullable=True)
    quoted_currency = Column(String(10), nullable=False, default="KES")
    lead_time_days = Column(Integer, nullable=True)
    valid_until = Column(Date, nullable=True)
    payment_terms = Column(String(100), nullable=True)
    notes = Column(String(1000), nullable=True)
    status = Column(Enum(RFQResponseStatus), nullable=False, default=RFQResponseStatus.PENDING)
    score = Column(Numeric(5, 2), nullable=True)

    rfq = relationship("RFQRequest", back_populates="responses")
    supplier = relationship("Supplier")


class BlanketPurchaseAgreement(Base, TimestampMixin):
    __tablename__ = "blanket_purchase_agreements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bpa_no = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(300), nullable=True)
    agreed_unit_price = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    agreed_quantity = Column(Numeric(14, 3), nullable=True)
    consumed_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="KG")
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    payment_terms = Column(String(100), nullable=True)
    status = Column(Enum(BPAStatus), nullable=False, default=BPAStatus.ACTIVE)
    notes = Column(String(1000), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier = relationship("Supplier")


class AutoReorderPolicy(Base, TimestampMixin):
    __tablename__ = "auto_reorder_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    reorder_point = Column(Numeric(14, 3), nullable=False)
    reorder_quantity = Column(Numeric(14, 3), nullable=False)
    max_stock_level = Column(Numeric(14, 3), nullable=True)
    lead_time_days = Column(Integer, nullable=False, default=7)
    preferred_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    auto_create_pr = Column(Boolean, nullable=False, default=True)
    active_flag = Column(Boolean, nullable=False, default=True)
    notes = Column(String(500), nullable=True)

    preferred_supplier = relationship("Supplier")


class SupplierEvaluation(Base, TimestampMixin):
    __tablename__ = "supplier_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    evaluation_date = Column(Date, nullable=False)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    on_time_delivery_score = Column(Numeric(5, 2), nullable=False)
    quality_score = Column(Numeric(5, 2), nullable=False)
    price_competitiveness_score = Column(Numeric(5, 2), nullable=False)
    responsiveness_score = Column(Numeric(5, 2), nullable=False)
    overall_score = Column(Numeric(5, 2), nullable=False)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    supplier = relationship("Supplier")
    evaluator = relationship("User")
    po = relationship("PurchaseOrder")
