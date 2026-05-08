import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class CallDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CallOutcome(str, enum.Enum):
    ANSWERED = "ANSWERED"
    NO_ANSWER = "NO_ANSWER"
    BUSY = "BUSY"
    VOICEMAIL = "VOICEMAIL"
    FAILED = "FAILED"


class CallLog(Base, TimestampMixin):
    __tablename__ = "call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_ref = Column(String(100), unique=True, nullable=False, index=True)
    direction = Column(String(20), nullable=False, default="OUTBOUND")
    phone_number = Column(String(50), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    crm_record_id = Column(UUID(as_uuid=True), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    outcome = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    recording_url = Column(String(500), nullable=True)
    call_script_id = Column(UUID(as_uuid=True), ForeignKey("call_scripts.id", ondelete="SET NULL"), nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(DateTime, nullable=True)
    tags = Column(String(300), nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    agent = relationship("User", foreign_keys=[agent_id])
    call_script = relationship("CallScript", foreign_keys=[call_script_id])


class CallScript(Base, TimestampMixin):
    __tablename__ = "call_scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    purpose = Column(String(100), nullable=False, default="sales")
    script_text = Column(Text, nullable=False)
    talking_points = Column(Text, nullable=True)
    objection_handlers = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
