import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class POSSessionStatus(str, enum.Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"


class POSPaymentMethod(str, enum.Enum):
    CASH   = "CASH"
    MPESA  = "MPESA"
    CARD   = "CARD"
    SPLIT  = "SPLIT"


class POSSaleStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    VOIDED    = "VOIDED"


class POSSession(Base, TimestampMixin):
    """A cashier's shift session at a register."""
    __tablename__ = "pos_sessions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_no     = Column(String(50), unique=True, nullable=False, index=True)
    cashier_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    register_id    = Column(String(50), nullable=False, default="REGISTER-1")
    status         = Column(Enum(POSSessionStatus), nullable=False, default=POSSessionStatus.OPEN, index=True)
    opened_at      = Column(DateTime(timezone=True), nullable=False)
    closed_at      = Column(DateTime(timezone=True), nullable=True)
    opening_float  = Column(Numeric(12, 2), nullable=False, default=0)  # cash in drawer at open
    closing_cash   = Column(Numeric(12, 2), nullable=True)              # actual cash counted at close
    expected_cash  = Column(Numeric(12, 2), nullable=True)              # opening_float + cash sales
    cash_difference = Column(Numeric(12, 2), nullable=True)             # closing_cash - expected_cash
    total_sales    = Column(Numeric(14, 2), nullable=False, default=0)
    total_transactions = Column(Integer, nullable=False, default=0)
    notes          = Column(Text, nullable=True)

    cashier = relationship("User", foreign_keys=[cashier_id])
    sales   = relationship("POSSale", back_populates="session")


class POSSale(Base, TimestampMixin):
    """Single POS sale transaction."""
    __tablename__ = "pos_sales"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_no        = Column(String(50), unique=True, nullable=False, index=True)
    session_id     = Column(UUID(as_uuid=True), ForeignKey("pos_sessions.id", ondelete="RESTRICT"), nullable=False, index=True)
    cashier_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    payment_method = Column(Enum(POSPaymentMethod), nullable=False, default=POSPaymentMethod.CASH)
    status         = Column(Enum(POSSaleStatus), nullable=False, default=POSSaleStatus.COMPLETED, index=True)

    subtotal       = Column(Numeric(14, 2), nullable=False, default=0)
    discount_total = Column(Numeric(14, 2), nullable=False, default=0)
    tax_total      = Column(Numeric(14, 2), nullable=False, default=0)
    sale_total     = Column(Numeric(14, 2), nullable=False, default=0)
    amount_paid    = Column(Numeric(14, 2), nullable=True)
    change_given   = Column(Numeric(14, 2), nullable=True)

    mpesa_ref      = Column(String(100), nullable=True)
    notes          = Column(Text, nullable=True)

    session  = relationship("POSSession", back_populates="sales")
    cashier  = relationship("User", foreign_keys=[cashier_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    lines    = relationship("POSSaleLine", back_populates="sale", cascade="all, delete-orphan",
                            order_by="POSSaleLine.line_no")


class POSSaleLine(Base, TimestampMixin):
    """Line item in a POS sale."""
    __tablename__ = "pos_sale_lines"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id     = Column(UUID(as_uuid=True), ForeignKey("pos_sales.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no     = Column(Integer, nullable=False)
    product_id  = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    qty         = Column(Numeric(14, 3), nullable=False)
    unit_price  = Column(Numeric(14, 4), nullable=False)
    discount_pct = Column(Numeric(6, 4), nullable=False, default=0)
    tax_rate    = Column(Numeric(6, 4), nullable=False, default=16)  # 16% VAT
    line_total  = Column(Numeric(14, 4), nullable=False)

    sale    = relationship("POSSale", back_populates="lines")
    product = relationship("Product", foreign_keys=[product_id])
