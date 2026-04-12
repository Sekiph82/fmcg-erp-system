import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean,
    ForeignKey, Enum, Date, DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ReturnReason(str, enum.Enum):
    DAMAGED = "DAMAGED"
    EXPIRED = "EXPIRED"
    WRONG_ITEM = "WRONG_ITEM"
    OVERSTOCKED = "OVERSTOCKED"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"
    OTHER = "OTHER"


class ReturnCondition(str, enum.Enum):
    RESALEABLE = "RESALEABLE"    # can go back to stock
    DAMAGED = "DAMAGED"          # write-off
    EXPIRED = "EXPIRED"          # write-off


class ReturnStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"     # stock reversed / credit note issued


class ReturnOrder(Base, TimestampMixin):
    __tablename__ = "return_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_no = Column(String(50), unique=True, nullable=False, index=True)
    original_so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    return_date = Column(Date, nullable=False)
    reason = Column(Enum(ReturnReason), nullable=False, default=ReturnReason.OTHER)
    status = Column(Enum(ReturnStatus), nullable=False, default=ReturnStatus.DRAFT)
    notes = Column(Text, nullable=True)
    credit_note_no = Column(String(100), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    original_so = relationship("SalesOrder")
    customer = relationship("Customer")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    lines = relationship("ReturnLine", back_populates="return_order",
                          cascade="all, delete-orphan")


class ReturnLine(Base, TimestampMixin):
    __tablename__ = "return_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id = Column(UUID(as_uuid=True), ForeignKey("return_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    return_reason = Column(Enum(ReturnReason), nullable=True)
    condition = Column(Enum(ReturnCondition), nullable=False, default=ReturnCondition.RESALEABLE)
    notes = Column(Text, nullable=True)

    return_order = relationship("ReturnOrder", back_populates="lines")
    product = relationship("Product")
    lot = relationship("Lot")
