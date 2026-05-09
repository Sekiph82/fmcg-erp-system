from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer,
    ForeignKey, Text, Enum as SAEnum, JSON, Float,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class EventType(str, enum.Enum):
    MEETING = "meeting"
    TASK = "task"
    BOOKING = "booking"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class EventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParticipantRole(str, enum.Enum):
    ORGANIZER = "organizer"
    ATTENDEE = "attendee"
    OPTIONAL = "optional"


class ResponseStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ResourceType(str, enum.Enum):
    EMPLOYEE = "employee"
    ROOM = "room"
    VEHICLE = "vehicle"
    MACHINE = "machine"
    EXTERNAL = "external"


class ResourceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class BookingStatus(str, enum.Enum):
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class RecurrenceFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class CAIAgentType(str, enum.Enum):
    SCHEDULE_OPTIMIZER = "schedule_optimizer"
    CONFLICT_RESOLVER = "conflict_resolver"


class CAIRecStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class CalendarResource(Base):
    __tablename__ = "calendar_resources"

    resource_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type = Column(SAEnum(ResourceType), nullable=False)
    name = Column(String(200), nullable=False)
    capacity = Column(Integer, default=1)
    location = Column(String(200))
    description = Column(Text)
    availability_rules = Column(JSON, default=dict)
    status = Column(SAEnum(ResourceStatus), default=ResourceStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = relationship("ResourceBooking", back_populates="resource")


class RecurrenceRule(Base):
    __tablename__ = "cal_recurrence_rules"

    recurrence_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    frequency = Column(SAEnum(RecurrenceFrequency), nullable=False)
    interval = Column(Integer, default=1)
    end_date = Column(DateTime, nullable=True)
    max_occurrences = Column(Integer, nullable=True)
    days_of_week = Column(JSON, default=list)
    exceptions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship(
        "CalendarEvent", back_populates="recurrence",
        foreign_keys="CalendarEvent.recurrence_id",
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_title = Column(String(300), nullable=False)
    event_type = Column(SAEnum(EventType), default=EventType.MEETING)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    all_day_flag = Column(Boolean, default=False)
    created_by = Column(String(100))
    description = Column(Text)
    location = Column(String(200))
    status = Column(SAEnum(EventStatus), default=EventStatus.SCHEDULED)
    source_module = Column(String(50))
    source_ref_id = Column(String(36))
    recurrence_id = Column(
        String(36), ForeignKey("cal_recurrence_rules.recurrence_id"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants = relationship(
        "EventParticipant", back_populates="event", cascade="all, delete-orphan"
    )
    bookings = relationship(
        "ResourceBooking", back_populates="event", cascade="all, delete-orphan"
    )
    recurrence = relationship(
        "RecurrenceRule", back_populates="events", foreign_keys=[recurrence_id]
    )


class EventParticipant(Base):
    __tablename__ = "cal_event_participants"

    participant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(
        String(36), ForeignKey("calendar_events.event_id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String(36), nullable=True)
    participant_name = Column(String(200))
    participant_email = Column(String(200))
    role = Column(SAEnum(ParticipantRole), default=ParticipantRole.ATTENDEE)
    response_status = Column(SAEnum(ResponseStatus), default=ResponseStatus.PENDING)

    event = relationship("CalendarEvent", back_populates="participants")


class ResourceBooking(Base):
    __tablename__ = "cal_resource_bookings"

    booking_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(
        String(36), ForeignKey("calendar_events.event_id", ondelete="SET NULL"), nullable=True
    )
    resource_id = Column(
        String(36), ForeignKey("calendar_resources.resource_id"), nullable=False
    )
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.RESERVED)
    notes = Column(Text)
    booked_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("CalendarEvent", back_populates="bookings")
    resource = relationship("CalendarResource", back_populates="bookings")


class CAIRecommendation(Base):
    __tablename__ = "cal_ai_recommendations"

    rec_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(SAEnum(CAIAgentType), nullable=False)
    title = Column(String(300))
    body = Column(Text)
    score = Column(Float, nullable=True)
    status = Column(SAEnum(CAIRecStatus), default=CAIRecStatus.PENDING)
    rec_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShiftType(str, enum.Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    CUSTOM = "custom"


class ShiftSchedule(Base):
    """Staff shift scheduling — one row per user per date."""
    __tablename__ = "cal_shift_schedules"

    shift_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True, index=True)
    shift_date = Column(String(10), nullable=False, index=True)     # ISO date string
    shift_type = Column(SAEnum(ShiftType), nullable=False, default=ShiftType.MORNING)
    shift_start = Column(String(5), nullable=False)                 # HH:MM
    shift_end = Column(String(5), nullable=False)                   # HH:MM
    location = Column(String(200), nullable=True)
    approved_flag = Column(Boolean, default=False)
    approved_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
