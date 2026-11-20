import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class MeetingRecord(Base, TimestampMixin):
    __tablename__ = "meeting_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    platform = Column(String(30), nullable=False, default="google_meet")  # google_meet | zoom | teams | other
    meeting_url = Column(String(500), nullable=True)
    meeting_id_ext = Column(String(200), nullable=True)   # external meeting ID
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    crm_record_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    status = Column(String(20), nullable=False, default="SCHEDULED")  # SCHEDULED|COMPLETED|CANCELLED|NO_SHOW
    agenda = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    recording_url = Column(String(500), nullable=True)
    attendees = Column(JSON, default=list)    # [{name, email, attended: bool}]
    outcome = Column(String(100), nullable=True)
    follow_up_action = Column(Text, nullable=True)
    time_zone = Column(String(64), nullable=True)          # IANA zone the host booked in; scheduled_at is UTC
    sequence = Column(Integer, nullable=False, default=0, server_default="0")  # iCalendar SEQUENCE, +1 per change

    host = relationship("User", foreign_keys=[host_id])
    customer = relationship("Customer", foreign_keys=[customer_id])


class MeetingCalendarFeed(Base):
    """M36.S01.T005 personal .ics subscription: one revocable token per user (stored as a SHA-256 digest)."""
    __tablename__ = "meeting_calendar_feeds"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
