import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class CustomerChannel(str, enum.Enum):
    RETAIL = "RETAIL"
    WHOLESALE = "WHOLESALE"
    DISTRIBUTOR = "DISTRIBUTOR"
    DIRECT = "DIRECT"
    EXPORT = "EXPORT"
    ONLINE = "ONLINE"


class CustomerType(str, enum.Enum):
    RETAIL = "RETAIL"           # small shop / duka
    WHOLESALE = "WHOLESALE"     # bulk buyer
    KIOSK = "KIOSK"             # roadside kiosk
    SUPERMARKET = "SUPERMARKET"
    HOTEL = "HOTEL"
    INSTITUTION = "INSTITUTION"


class OrderSource(str, enum.Enum):
    MANUAL = "MANUAL"               # created in back-office
    FIELD_SALES = "FIELD_SALES"     # created by motorbike rep
    DISTRIBUTOR = "DISTRIBUTOR"     # raised by distributor
    ECOMMERCE = "ECOMMERCE"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    MPESA = "mpesa"
    BANK_TRANSFER = "bank_transfer"
    CREDIT = "credit"


class SOPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    FAILED = "failed"


class MpesaTxStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SOStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    ALLOCATED = "ALLOCATED"
    PICKING = "PICKING"
    SHIPPED = "SHIPPED"
    INVOICED = "INVOICED"
    CANCELLED = "CANCELLED"


class ShipmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PICKING = "PICKING"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    delivery_address = Column(Text, nullable=True)
    delivery_city = Column(String(100), nullable=True)
    delivery_country = Column(String(100), nullable=True)
    channel = Column(Enum(CustomerChannel), nullable=False, default=CustomerChannel.WHOLESALE)
    payment_terms_days = Column(Integer, default=30, nullable=False)
    credit_limit = Column(Numeric(16, 2), nullable=True)
    tax_id = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_prepaid = Column(Boolean, default=False, nullable=False)

    # Distribution extensions
    customer_type = Column(Enum(CustomerType), nullable=True)
    region = Column(String(100), nullable=True)
    segment = Column(String(100), nullable=True)     # custom segmentation tag
    credit_risk_score = Column(Integer, nullable=True)  # 0–100, lower = safer
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="SET NULL"), nullable=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="SET NULL"), nullable=True)
    gps_lat = Column(Numeric(10, 7), nullable=True)
    gps_lng = Column(Numeric(10, 7), nullable=True)

    distributor = relationship("Distributor", back_populates="customers",
                                foreign_keys=[distributor_id],
                                primaryjoin="Customer.distributor_id == Distributor.id")
    route = relationship("SalesRoute")
    orders = relationship("SalesOrder", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    order_date = Column(Date, nullable=False)
    requested_delivery_date = Column(Date, nullable=False)
    status = Column(Enum(SOStatus), nullable=False, default=SOStatus.DRAFT)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.CASH)
    payment_status = Column(Enum(SOPaymentStatus), nullable=False, default=SOPaymentStatus.PENDING)
    mpesa_reference = Column(String(100), nullable=True)
    mpesa_request_id = Column(String(100), nullable=True)

    # Distribution extensions
    source = Column(Enum(OrderSource), nullable=False, default=OrderSource.MANUAL)
    sales_rep_id = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), nullable=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="SET NULL"), nullable=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="SET NULL"), nullable=True)
    offline_id = Column(String(100), unique=True, nullable=True, index=True)  # client UUID for offline sync
    offline_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Marketing extensions — soft FKs (no hard constraint; marketing module is optional)
    campaign_id = Column(UUID(as_uuid=True), nullable=True, index=True)   # → mkt_campaigns.id
    promotion_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # → mkt_promotions.id
    crm_segment_id = Column(UUID(as_uuid=True), nullable=True)            # → mkt_customer_segments.id

    customer = relationship("Customer", back_populates="orders")
    warehouse = relationship("Warehouse")
    created_by = relationship("User", foreign_keys=[created_by_id])
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
    sales_rep = relationship("SalesRep")
    distributor = relationship("Distributor")
    lines = relationship("SOLine", back_populates="so", cascade="all, delete-orphan", order_by="SOLine.line_no")
    shipments = relationship("Shipment", back_populates="so")
    invoices = relationship("Invoice", back_populates="so")
    mpesa_transactions = relationship(
        "MpesaTransaction", back_populates="so",
        order_by="MpesaTransaction.created_at",
        cascade="all, delete-orphan",
    )


class SOLine(Base, TimestampMixin):
    __tablename__ = "so_lines"
    __table_args__ = (UniqueConstraint("so_id", "line_no", name="uq_so_line"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    ordered_quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    discount_pct = Column(Numeric(6, 4), nullable=False, default=0)
    tax_rate = Column(Numeric(6, 4), nullable=False, default=0)
    allocated_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    shipped_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    cost_price = Column(Numeric(14, 4), nullable=True)
    notes = Column(Text, nullable=True)

    so = relationship("SalesOrder", back_populates="lines")
    product = relationship("Product")


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_no = Column(String(50), unique=True, nullable=False, index=True)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(ShipmentStatus), nullable=False, default=ShipmentStatus.PENDING)
    scheduled_date = Column(Date, nullable=False)
    dispatched_date = Column(Date, nullable=True)
    carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dispatched_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    so = relationship("SalesOrder", back_populates="shipments")
    warehouse = relationship("Warehouse")
    created_by = relationship("User", foreign_keys=[created_by_id])
    dispatched_by = relationship("User", foreign_keys=[dispatched_by_id])
    lines = relationship("ShipmentLine", back_populates="shipment", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="shipment", uselist=False)


class ShipmentLine(Base, TimestampMixin):
    __tablename__ = "shipment_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    so_line_id = Column(UUID(as_uuid=True), ForeignKey("so_lines.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")
    stock_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True)
    is_picked = Column(Boolean, default=False, nullable=False)
    picked_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    picked_at = Column(DateTime(timezone=True), nullable=True)

    shipment = relationship("Shipment", back_populates="lines")
    product = relationship("Product")
    lot = relationship("Lot")
    picked_by = relationship("User")


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_no = Column(String(50), unique=True, nullable=False, index=True)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    currency = Column(String(10), nullable=False, default="USD")
    subtotal = Column(Numeric(16, 4), nullable=False, default=0)
    tax_amount = Column(Numeric(16, 4), nullable=False, default=0)
    total_amount = Column(Numeric(16, 4), nullable=False, default=0)
    paid_amount = Column(Numeric(16, 4), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    so = relationship("SalesOrder", back_populates="invoices")
    shipment = relationship("Shipment", back_populates="invoice")
    customer = relationship("Customer", back_populates="invoices")
    created_by = relationship("User")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    so_line_id = Column(UUID(as_uuid=True), ForeignKey("so_lines.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    description = Column(String(255), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    discount_pct = Column(Numeric(6, 4), nullable=False, default=0)
    tax_rate = Column(Numeric(6, 4), nullable=False, default=0)
    line_total = Column(Numeric(16, 4), nullable=False, default=0)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    method = Column(String(20), nullable=False, default="cash")   # cash | bank | mpesa
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    invoice = relationship("Invoice", back_populates="payments")
    created_by = relationship("User")


class MpesaTransaction(Base, TimestampMixin):
    __tablename__ = "mpesa_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False)
    phone_number = Column(String(20), nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    mpesa_request_id = Column(String(100), nullable=True, index=True)   # CheckoutRequestID from Daraja
    mpesa_reference = Column(String(100), nullable=True)                # MpesaReceiptNumber on success
    status = Column(Enum(MpesaTxStatus), nullable=False, default=MpesaTxStatus.PENDING)
    result_code = Column(Integer, nullable=True)
    result_description = Column(Text, nullable=True)
    initiated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    so = relationship("SalesOrder", back_populates="mpesa_transactions")
    initiated_by = relationship("User")
