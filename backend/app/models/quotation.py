import uuid
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class QuoteStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    SENT     = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED  = "EXPIRED"
    CONVERTED = "CONVERTED"   # converted to Sales Order


class Quotation(Base, TimestampMixin):
    """
    Sales quotation / commercial offer to a customer.
    Multiple versions can exist for the same quote_no (revision tracking).
    """
    __tablename__ = "quotations"
    __table_args__ = (UniqueConstraint("quote_no", "version", name="uq_quote_version"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_no       = Column(String(50), nullable=False, index=True)   # e.g. QT-20240115-001
    version        = Column(Integer, nullable=False, default=1)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    status         = Column(Enum(QuoteStatus), nullable=False, default=QuoteStatus.DRAFT, index=True)

    # Validity
    quote_date     = Column(Date, nullable=False)
    valid_until    = Column(Date, nullable=True)

    # Pricing
    currency       = Column(String(10), nullable=False, default="KES")
    discount_pct   = Column(Numeric(6, 4), nullable=False, default=0)  # overall discount on top of line discounts
    total_amount   = Column(Numeric(18, 4), nullable=True)             # computed on save
    tax_amount     = Column(Numeric(18, 4), nullable=True)
    grand_total    = Column(Numeric(18, 4), nullable=True)

    # Tracking
    sent_at        = Column(DateTime(timezone=True), nullable=True)
    accepted_at    = Column(DateTime(timezone=True), nullable=True)
    rejected_at    = Column(DateTime(timezone=True), nullable=True)
    lost_reason    = Column(Text, nullable=True)

    # Conversion
    converted_so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)

    # People
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes          = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    customer     = relationship("Customer", foreign_keys=[customer_id])
    created_by   = relationship("User", foreign_keys=[created_by_id])
    converted_so = relationship("SalesOrder", foreign_keys=[converted_so_id])
    lines        = relationship("QuotationLine", back_populates="quote",
                                cascade="all, delete-orphan",
                                order_by="QuotationLine.line_no")


class QuotationLine(Base, TimestampMixin):
    """One line item in a quotation."""
    __tablename__ = "quotation_lines"
    __table_args__ = (UniqueConstraint("quote_id", "line_no", name="uq_quote_line"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id     = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no      = Column(Integer, nullable=False)
    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    description  = Column(String(500), nullable=True)   # free-text for non-product lines
    qty          = Column(Numeric(14, 3), nullable=False)
    unit         = Column(String(20), nullable=False, default="PCS")
    unit_price   = Column(Numeric(14, 4), nullable=False, default=0)
    discount_pct = Column(Numeric(6, 4), nullable=False, default=0)
    tax_rate     = Column(Numeric(6, 4), nullable=False, default=0)
    line_total   = Column(Numeric(18, 4), nullable=False, default=0)   # qty × unit_price × (1-disc) × (1+tax)

    quote   = relationship("Quotation", back_populates="lines")
    product = relationship("Product", foreign_keys=[product_id])
