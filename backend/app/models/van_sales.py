from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class VanStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    INACTIVE  = "INACTIVE"
    ON_ROUTE  = "ON_ROUTE"
    IN_REPAIR = "IN_REPAIR"


class TxnType(str, enum.Enum):
    SALE       = "SALE"
    RETURN     = "RETURN"
    EXCHANGE   = "EXCHANGE"
    CREDIT     = "CREDIT"


class TxnStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    CONFIRMED  = "CONFIRMED"
    INVOICED   = "INVOICED"
    CANCELLED  = "CANCELLED"
    SYNCED     = "SYNCED"
    PENDING_SYNC = "PENDING_SYNC"


class PaymentStatus(str, enum.Enum):
    UNPAID     = "UNPAID"
    PARTIAL    = "PARTIAL"
    PAID       = "PAID"
    REFUNDED   = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    CASH       = "CASH"
    MPESA      = "MPESA"
    CARD       = "CARD"
    CREDIT     = "CREDIT"
    MIXED      = "MIXED"


class VisitStatus(str, enum.Enum):
    PLANNED    = "PLANNED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED  = "COMPLETED"
    MISSED     = "MISSED"
    SKIPPED    = "SKIPPED"


class ReturnReason(str, enum.Enum):
    DAMAGED    = "DAMAGED"
    EXPIRED    = "EXPIRED"
    WRONG_ITEM = "WRONG_ITEM"
    EXCESS     = "EXCESS"
    CUSTOMER_REFUSAL = "CUSTOMER_REFUSAL"
    OTHER      = "OTHER"


class ReconciliationStatus(str, enum.Enum):
    OPEN       = "OPEN"
    SUBMITTED  = "SUBMITTED"
    APPROVED   = "APPROVED"
    DISCREPANCY = "DISCREPANCY"


class VSAIAgentType(str, enum.Enum):
    ROUTE_OPTIMIZER    = "ROUTE_OPTIMIZER"
    SALES_ASSISTANT    = "SALES_ASSISTANT"
    RISK_MONITOR       = "RISK_MONITOR"


class VSAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class Van(Base, TimestampMixin):
    __tablename__ = "vans"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    van_code     = Column(String(50), unique=True, nullable=False, index=True)
    plate_number = Column(String(30), nullable=True)
    driver_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    route_id     = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    capacity_kg  = Column(Numeric(10, 2), nullable=True)
    status       = Column(String(50), nullable=False, default=VanStatus.ACTIVE.value)
    notes        = Column(Text, nullable=True)

    stock        = relationship("VanStock", back_populates="van", cascade="all, delete-orphan")
    transactions = relationship("VanSalesTxn", back_populates="van")
    reconciliations = relationship("VanReconciliation", back_populates="van")


class VanStock(Base, TimestampMixin):
    __tablename__ = "van_stock"
    __table_args__ = (UniqueConstraint("van_id", "item_id", "batch_id", name="uq_van_stock_item_batch"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    van_id       = Column(UUID(as_uuid=True), ForeignKey("vans.id", ondelete="CASCADE"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    batch_id     = Column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True)
    quantity     = Column(Numeric(14, 3), nullable=False, default=0)
    reserved_qty = Column(Numeric(14, 3), nullable=False, default=0)
    unit_cost    = Column(Numeric(14, 4), nullable=True)
    uom          = Column(String(20), nullable=False, default="PCS")

    van  = relationship("Van", back_populates="stock")


class VanStockMovement(Base, TimestampMixin):
    __tablename__ = "van_stock_movements"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    van_id       = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    batch_id     = Column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True)
    movement_type = Column(String(30), nullable=False)   # LOAD / SALE / RETURN / TRANSFER / RECONCILE
    quantity     = Column(Numeric(14, 3), nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True)   # txn_id or reconciliation_id
    reference_no = Column(String(100), nullable=True)
    moved_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes        = Column(Text, nullable=True)


class VanVisit(Base, TimestampMixin):
    __tablename__ = "van_visits"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    van_id          = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=False)
    route_id        = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    route_date      = Column(Date, nullable=False)
    sequence_no     = Column(Integer, nullable=True)
    planned_time    = Column(DateTime, nullable=True)
    check_in_time   = Column(DateTime, nullable=True)
    check_out_time  = Column(DateTime, nullable=True)
    status          = Column(String(50), nullable=False, default=VisitStatus.PLANNED.value)
    gps_lat         = Column(Numeric(10, 7), nullable=True)
    gps_lng         = Column(Numeric(10, 7), nullable=True)
    missed_reason   = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)
    offline_id      = Column(String(100), unique=True, nullable=True)  # client UUID for dedup
    outlet_photo_url = Column(Text, nullable=True)   # retail outlet photo capture

    transactions = relationship("VanSalesTxn", back_populates="visit")


class VanSalesTxn(Base, TimestampMixin):
    __tablename__ = "van_sales_txns"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_no          = Column(String(50), unique=True, nullable=False, index=True)
    van_id          = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=False)
    route_id        = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    visit_id        = Column(UUID(as_uuid=True), ForeignKey("van_visits.id"), nullable=True)
    driver_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    txn_type        = Column(String(30), nullable=False, default=TxnType.SALE.value)
    txn_datetime    = Column(DateTime, nullable=False)
    status          = Column(String(50), nullable=False, default=TxnStatus.DRAFT.value)
    payment_status  = Column(String(50), nullable=False, default=PaymentStatus.UNPAID.value)

    subtotal        = Column(Numeric(14, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(14, 2), nullable=False, default=0)
    tax_amount      = Column(Numeric(14, 2), nullable=False, default=0)
    total_amount    = Column(Numeric(14, 2), nullable=False, default=0)
    paid_amount     = Column(Numeric(14, 2), nullable=False, default=0)
    balance_due     = Column(Numeric(14, 2), nullable=False, default=0)
    currency        = Column(String(3), nullable=False, default="KES")

    linked_so_id    = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    price_list_id   = Column(UUID(as_uuid=True), nullable=True)
    promo_ids       = Column(JSON, nullable=True)   # list of applied promotion IDs

    offline_id      = Column(String(100), unique=True, nullable=True)
    synced_at       = Column(DateTime, nullable=True)
    device_id       = Column(String(100), nullable=True)
    notes           = Column(Text, nullable=True)

    van     = relationship("Van", back_populates="transactions")
    visit   = relationship("VanVisit", back_populates="transactions")
    lines   = relationship("VanSalesTxnLine", back_populates="txn", cascade="all, delete-orphan")
    payments = relationship("VanPayment", back_populates="txn", cascade="all, delete-orphan")


class VanSalesTxnLine(Base, TimestampMixin):
    __tablename__ = "van_sales_txn_lines"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_id       = Column(UUID(as_uuid=True), ForeignKey("van_sales_txns.id", ondelete="CASCADE"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    batch_id     = Column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=True)
    uom          = Column(String(20), nullable=False, default="PCS")
    quantity     = Column(Numeric(14, 3), nullable=False)
    unit_price   = Column(Numeric(14, 4), nullable=False)
    discount_pct = Column(Numeric(5, 2), nullable=False, default=0)
    discount_amt = Column(Numeric(14, 2), nullable=False, default=0)
    tax_pct      = Column(Numeric(5, 2), nullable=False, default=0)
    tax_amt      = Column(Numeric(14, 2), nullable=False, default=0)
    line_total   = Column(Numeric(14, 2), nullable=False)
    return_reason = Column(String(50), nullable=True)   # for RETURN lines
    notes        = Column(Text, nullable=True)

    txn = relationship("VanSalesTxn", back_populates="lines")


class VanPayment(Base, TimestampMixin):
    __tablename__ = "van_payments"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_id       = Column(UUID(as_uuid=True), ForeignKey("van_sales_txns.id", ondelete="CASCADE"), nullable=False)
    method       = Column(String(30), nullable=False)
    amount       = Column(Numeric(14, 2), nullable=False)
    reference_no = Column(String(200), nullable=True)
    collected_at = Column(DateTime, nullable=False)
    collected_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    receipt_no   = Column(String(100), nullable=True)
    notes        = Column(Text, nullable=True)

    txn = relationship("VanSalesTxn", back_populates="payments")


class VanReconciliation(Base, TimestampMixin):
    __tablename__ = "van_reconciliations"
    __table_args__ = (UniqueConstraint("van_id", "route_date", name="uq_van_recon_date"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    van_id           = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=False)
    route_date       = Column(Date, nullable=False)
    status           = Column(String(50), nullable=False, default=ReconciliationStatus.OPEN.value)

    opening_stock    = Column(JSON, nullable=True)   # {item_id: qty}
    closing_stock    = Column(JSON, nullable=True)
    sales_qty        = Column(JSON, nullable=True)
    returns_qty      = Column(JSON, nullable=True)
    discrepancy      = Column(JSON, nullable=True)

    total_sales      = Column(Numeric(14, 2), nullable=True)
    total_cash       = Column(Numeric(14, 2), nullable=True)
    total_mpesa      = Column(Numeric(14, 2), nullable=True)
    total_credit     = Column(Numeric(14, 2), nullable=True)
    total_returns    = Column(Numeric(14, 2), nullable=True)

    submitted_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    notes            = Column(Text, nullable=True)

    van = relationship("Van", back_populates="reconciliations")


class VSAIRecommendation(Base, TimestampMixin):
    __tablename__ = "vs_ai_recommendations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type  = Column(String(50), nullable=False)
    status      = Column(String(50), default=VSAIRecStatus.PENDING.value)
    severity    = Column(String(20), default="INFO")
    title       = Column(String(200), nullable=False)
    body        = Column(Text, nullable=False)
    data        = Column(JSON, nullable=True)
    van_id      = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=True)
    driver_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    route_id    = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)


# ── M-Pesa STK Push ───────────────────────────────────────────────────────────

class MpesaStkStatus(str, enum.Enum):
    PENDING  = "PENDING"
    SUCCESS  = "SUCCESS"
    FAILED   = "FAILED"
    TIMEOUT  = "TIMEOUT"
    CANCELLED = "CANCELLED"


class VanMpesaPayment(Base, TimestampMixin):
    __tablename__ = "van_mpesa_payments"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_id           = Column(UUID(as_uuid=True), ForeignKey("van_sales_txns.id"), nullable=False)
    van_payment_id   = Column(UUID(as_uuid=True), ForeignKey("van_payments.id"), nullable=True)
    phone_number     = Column(String(20), nullable=False)
    amount           = Column(Numeric(14, 2), nullable=False)
    merchant_request_id = Column(String(100), nullable=True, unique=True)
    checkout_request_id = Column(String(100), nullable=True, unique=True)
    mpesa_receipt_no = Column(String(50), nullable=True)
    status           = Column(String(30), nullable=False, default=MpesaStkStatus.PENDING.value)
    result_code      = Column(String(10), nullable=True)
    result_desc      = Column(Text, nullable=True)
    request_time     = Column(DateTime, nullable=False)
    callback_time    = Column(DateTime, nullable=True)
    raw_callback     = Column(JSON, nullable=True)


# ── Fraud Alert ───────────────────────────────────────────────────────────────

class FraudType(str, enum.Enum):
    ABNORMAL_DISCOUNT    = "ABNORMAL_DISCOUNT"
    PRICE_OVERRIDE       = "PRICE_OVERRIDE"
    REPEATED_RETURN      = "REPEATED_RETURN"
    STOCK_MISMATCH       = "STOCK_MISMATCH"
    DUPLICATE_TXN        = "DUPLICATE_TXN"
    PAYMENT_MISMATCH     = "PAYMENT_MISMATCH"
    OFFLINE_MANIPULATION = "OFFLINE_MANIPULATION"
    UNUSUAL_PATTERN      = "UNUSUAL_PATTERN"


class FraudSeverity(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class FraudAlertStatus(str, enum.Enum):
    OPEN       = "OPEN"
    REVIEWED   = "REVIEWED"
    DISMISSED  = "DISMISSED"
    ESCALATED  = "ESCALATED"
    CONFIRMED  = "CONFIRMED"


class VanFraudAlert(Base, TimestampMixin):
    __tablename__ = "van_fraud_alerts"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_id       = Column(UUID(as_uuid=True), ForeignKey("van_sales_txns.id"), nullable=True)
    van_id       = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=True)
    driver_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    fraud_type   = Column(String(50), nullable=False)
    risk_score   = Column(Numeric(5, 2), nullable=False, default=0)  # 0–100
    severity     = Column(String(20), nullable=False, default=FraudSeverity.LOW.value)
    status       = Column(String(30), nullable=False, default=FraudAlertStatus.OPEN.value)
    description  = Column(Text, nullable=True)
    data         = Column(JSON, nullable=True)
    reviewed_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at  = Column(DateTime, nullable=True)
    resolution   = Column(Text, nullable=True)


# ── Rider Performance ─────────────────────────────────────────────────────────

class VanRiderPerformance(Base, TimestampMixin):
    __tablename__ = "van_rider_performance"
    __table_args__ = (UniqueConstraint("driver_id", "perf_date", name="uq_rider_perf_date"),)

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    van_id               = Column(UUID(as_uuid=True), ForeignKey("vans.id"), nullable=True)
    route_id             = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)
    perf_date            = Column(Date, nullable=False)

    total_sales          = Column(Numeric(14, 2), nullable=False, default=0)
    total_orders         = Column(Integer, nullable=False, default=0)
    total_visits         = Column(Integer, nullable=False, default=0)
    completed_visits     = Column(Integer, nullable=False, default=0)
    missed_visits        = Column(Integer, nullable=False, default=0)

    route_completion_pct = Column(Numeric(5, 2), nullable=True)  # completed/total*100
    collection_rate_pct  = Column(Numeric(5, 2), nullable=True)  # paid/invoiced*100

    expected_cash        = Column(Numeric(14, 2), nullable=True)
    actual_cash          = Column(Numeric(14, 2), nullable=True)
    cash_variance        = Column(Numeric(14, 2), nullable=True)

    stock_variance_pct   = Column(Numeric(7, 3), nullable=True)
    fraud_flag_count     = Column(Integer, nullable=False, default=0)

    performance_score    = Column(Numeric(5, 2), nullable=True)  # 0–100 composite
    notes                = Column(Text, nullable=True)


class VanRepDayLog(Base, TimestampMixin):
    """Field rep daily GPS check-in / check-out log. One row per rep per day."""
    __tablename__ = "van_rep_day_logs"
    __table_args__ = (UniqueConstraint("rep_user_id", "log_date", name="uq_rep_day_log"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rep_user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    rep_name        = Column(String(200), nullable=True)
    log_date        = Column(Date, nullable=False)

    # Day start
    start_time      = Column(DateTime, nullable=True)
    start_gps_lat   = Column(Numeric(10, 7), nullable=True)
    start_gps_lng   = Column(Numeric(10, 7), nullable=True)
    start_photo_url = Column(Text, nullable=True)

    # Day end
    end_time        = Column(DateTime, nullable=True)
    end_gps_lat     = Column(Numeric(10, 7), nullable=True)
    end_gps_lng     = Column(Numeric(10, 7), nullable=True)
    end_photo_url   = Column(Text, nullable=True)

    # Summary
    total_visits    = Column(Integer, nullable=True)
    total_km_est    = Column(Numeric(8, 2), nullable=True)
    total_sales     = Column(Numeric(14, 2), nullable=True)
    notes           = Column(Text, nullable=True)

    rep = relationship("User", foreign_keys=[rep_user_id])
