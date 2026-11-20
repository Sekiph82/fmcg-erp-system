import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    ForeignKey, Enum, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class TicketStatus(str, enum.Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED   = "ESCALATED"
    RESOLVED    = "RESOLVED"
    CLOSED      = "CLOSED"


class TicketCategory(str, enum.Enum):
    QUALITY  = "QUALITY"
    DELIVERY = "DELIVERY"
    BILLING  = "BILLING"
    PRODUCT  = "PRODUCT"
    OTHER    = "OTHER"


class TicketPriority(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class TicketSource(str, enum.Enum):
    PHONE    = "PHONE"
    EMAIL    = "EMAIL"
    PORTAL   = "PORTAL"
    WHATSAPP = "WHATSAPP"
    MANUAL   = "MANUAL"


# Default SLA hours per priority
SLA_DEFAULTS = {
    TicketPriority.CRITICAL: 1,
    TicketPriority.HIGH:     4,
    TicketPriority.MEDIUM:   24,
    TicketPriority.LOW:      72,
}


class HelpdeskTicket(Base, TimestampMixin):
    """Customer complaint / helpdesk ticket."""
    __tablename__ = "helpdesk_tickets"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_no   = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    category    = Column(Enum(TicketCategory), nullable=False, default=TicketCategory.OTHER)
    priority    = Column(Enum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    status      = Column(Enum(TicketStatus),   nullable=False, default=TicketStatus.OPEN, index=True)
    source      = Column(Enum(TicketSource),   nullable=False, default=TicketSource.MANUAL)

    subject     = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Optional batch/lot link (for quality complaints)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)

    # SLA tracking
    sla_hours         = Column(Integer, nullable=False, default=24)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at       = Column(DateTime(timezone=True), nullable=True)
    closed_at         = Column(DateTime(timezone=True), nullable=True)

    # Resolution
    resolution_notes      = Column(Text, nullable=True)
    customer_satisfaction = Column(Integer, nullable=True)  # 1–5

    # People
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer    = relationship("Customer",  foreign_keys=[customer_id])
    lot         = relationship("Lot",       foreign_keys=[lot_id])
    assigned_to = relationship("User",      foreign_keys=[assigned_to_id])
    created_by  = relationship("User",      foreign_keys=[created_by_id])
    comments    = relationship("TicketComment", back_populates="ticket",
                               cascade="all, delete-orphan", order_by="TicketComment.created_at")


class TicketComment(Base, TimestampMixin):
    """Comment / reply on a helpdesk ticket."""
    __tablename__ = "ticket_comments"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id  = Column(UUID(as_uuid=True), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    body       = Column(Text, nullable=False)
    is_internal = Column(Boolean, nullable=False, default=False)  # internal note vs customer-facing reply
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    ticket     = relationship("HelpdeskTicket", back_populates="comments")
    created_by = relationship("User", foreign_keys=[created_by_id])


class TicketAttachment(Base):
    """M36.S04.T004 a file on a ticket. Customer uploads (portal) are visible to staff once the malware scan
    is CLEAN; staff files reach the customer only after a person ticks 'share with customer'."""
    __tablename__ = "ticket_attachments"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id         = Column(UUID(as_uuid=True), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key       = Column(String(32), nullable=False, unique=True)
    file_name         = Column(String(255), nullable=False)
    file_size_bytes   = Column(Integer, nullable=False)
    mime_type         = Column(String(100), nullable=False)
    sha256            = Column(String(64), nullable=False)
    scan_status       = Column(String(20), nullable=False)      # CLEAN | NOT_SCANNED | ERROR (INFECTED is never stored)
    from_customer     = Column(Boolean, nullable=False, default=False)
    portal_user_id    = Column(UUID(as_uuid=True), ForeignKey("portal_users.id", ondelete="SET NULL"), nullable=True)
    uploaded_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_visible  = Column(Boolean, nullable=False, default=False)
    created_at        = Column(DateTime(timezone=True), nullable=False)
