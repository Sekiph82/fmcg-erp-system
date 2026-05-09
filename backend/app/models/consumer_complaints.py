"""Consumer Complaint Management — linked to product batches/lots."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ComplaintSeverity(str, PyEnum):
    SAFETY = "SAFETY"             # Potential health risk — may trigger recall
    QUALITY = "QUALITY"           # Sub-standard quality
    FOREIGN_OBJECT = "FOREIGN_OBJECT"   # Physical contamination
    LABEL_ISSUE = "LABEL_ISSUE"   # Mislabeling, wrong info
    PACKAGING = "PACKAGING"       # Damaged or defective packaging
    OTHER = "OTHER"


class ComplaintChannel(str, PyEnum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    WALK_IN = "WALK_IN"
    RETAILER = "RETAILER"


class ComplaintStatus(str, PyEnum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    COMPENSATED = "COMPENSATED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ConsumerComplaint(Base):
    __tablename__ = "consumer_complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_ref = Column(String(50), unique=True, nullable=False, index=True)

    # Consumer details
    consumer_name = Column(String(300), nullable=True)
    consumer_contact = Column(String(200), nullable=True)  # phone or email
    consumer_location = Column(String(300), nullable=True)
    channel = Column(Enum(ComplaintChannel), nullable=False, default=ComplaintChannel.PHONE)

    # Product & batch linkage
    product_name = Column(String(300), nullable=False)
    lot_number = Column(String(100), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # soft FK to production batch
    purchase_date = Column(String(20), nullable=True)
    purchase_location = Column(String(300), nullable=True)

    # Complaint details
    severity = Column(Enum(ComplaintSeverity), nullable=False, default=ComplaintSeverity.QUALITY)
    description = Column(Text, nullable=False)
    status = Column(Enum(ComplaintStatus), nullable=False, default=ComplaintStatus.NEW, index=True)

    # Investigation
    assigned_to = Column(String(200), nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    regulatory_report_required = Column(Boolean, default=False, nullable=False)

    # Auto-recall flag
    recall_triggered_flag = Column(Boolean, default=False, nullable=False)
    recall_ref = Column(String(100), nullable=True)

    # Response tracking
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    compensation_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
