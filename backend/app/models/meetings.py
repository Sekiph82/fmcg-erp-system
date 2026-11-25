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


class CalendarEventLink(Base):
    """M43.S01.T003/T004: an ERP meeting pushed to the host's Google / Outlook calendar."""
    __tablename__ = "calendar_event_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting_records.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="CASCADE"), nullable=False)
    external_event_id = Column(String(1024), nullable=True)
    etag = Column(String(255), nullable=True)
    pushed_sequence = Column(Integer, nullable=True)     # meeting.sequence last written to the provider
    conflict = Column(String(500), nullable=True)        # last unresolved two-way conflict, shown to the host
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CalendarBusyBlock(Base):
    """Busy time from the host's own calendar (start/end only, no titles or attendees): no double booking."""
    __tablename__ = "calendar_busy_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="CASCADE"), nullable=False)
    external_event_id = Column(String(1024), nullable=False)
    starts_at = Column(DateTime, nullable=False)           # naive UTC like meeting_records.scheduled_at
    ends_at = Column(DateTime, nullable=False)


class BookingPage(Base, TimestampMixin):
    """M43.S01.T005 public self-booking page for one host or a round-robin team."""
    __tablename__ = "booking_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(80), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=30)
    buffer_before = Column(Integer, nullable=False, default=0)
    buffer_after = Column(Integer, nullable=False, default=10)
    min_notice_hours = Column(Integer, nullable=False, default=4)
    max_days_ahead = Column(Integer, nullable=False, default=30)
    time_zone = Column(String(64), nullable=False, default="Africa/Nairobi")
    open_time = Column(String(5), nullable=False, default="08:00")
    close_time = Column(String(5), nullable=False, default="17:00")
    weekdays = Column(JSON, nullable=False, default=lambda: [0, 1, 2, 3, 4])   # Monday = 0
    host_ids = Column(JSON, nullable=False, default=list)
    routing = Column(String(20), nullable=False, default="round_robin")    # round_robin | first_available
    platform = Column(String(30), nullable=False, default="jitsi")
    consent_text = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Booking(Base):
    """A visitor's booking through a BookingPage (the meeting itself is a MeetingRecord)."""
    __tablename__ = "booking_page_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("booking_pages.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting_records.id", ondelete="CASCADE"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visitor_name = Column(String(200), nullable=False)
    visitor_email = Column(String(255), nullable=False)
    consent_text = Column(Text, nullable=True)
    manage_token_hash = Column(String(64), nullable=False, unique=True)
    ip_hash = Column(String(64), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
