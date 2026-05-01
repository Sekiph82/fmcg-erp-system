from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.calendar import (
    EventType, EventStatus, ParticipantRole, ResponseStatus,
    ResourceType, ResourceStatus, BookingStatus,
    RecurrenceFrequency, CAIAgentType, CAIRecStatus,
)


class ResourceOut(BaseModel):
    resource_id: str
    resource_type: ResourceType
    name: str
    capacity: int
    location: Optional[str] = None
    description: Optional[str] = None
    availability_rules: dict = {}
    status: ResourceStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class ResourceCreate(BaseModel):
    resource_type: ResourceType
    name: str
    capacity: int = 1
    location: Optional[str] = None
    description: Optional[str] = None
    availability_rules: dict = {}
    status: ResourceStatus = ResourceStatus.ACTIVE


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    availability_rules: Optional[dict] = None
    status: Optional[ResourceStatus] = None


class ParticipantIn(BaseModel):
    user_id: Optional[str] = None
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    role: ParticipantRole = ParticipantRole.ATTENDEE


class ParticipantOut(BaseModel):
    participant_id: str
    event_id: str
    user_id: Optional[str] = None
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    role: ParticipantRole
    response_status: ResponseStatus
    model_config = {"from_attributes": True}


class RecurrenceIn(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = 1
    end_date: Optional[datetime] = None
    max_occurrences: Optional[int] = None
    days_of_week: List[int] = []
    exceptions: List[str] = []


class RecurrenceOut(BaseModel):
    recurrence_id: str
    frequency: RecurrenceFrequency
    interval: int
    end_date: Optional[datetime] = None
    max_occurrences: Optional[int] = None
    days_of_week: List[int] = []
    exceptions: List[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class BookingOut(BaseModel):
    booking_id: str
    event_id: Optional[str] = None
    resource_id: str
    start_datetime: datetime
    end_datetime: datetime
    status: BookingStatus
    notes: Optional[str] = None
    booked_by: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    resource_id: str
    start_datetime: datetime
    end_datetime: datetime
    notes: Optional[str] = None
    booked_by: Optional[str] = None


class EventCreate(BaseModel):
    event_title: str
    event_type: EventType = EventType.MEETING
    start_datetime: datetime
    end_datetime: datetime
    all_day_flag: bool = False
    created_by: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    source_module: Optional[str] = None
    source_ref_id: Optional[str] = None
    participants: List[ParticipantIn] = []
    resource_ids: List[str] = []
    recurrence: Optional[RecurrenceIn] = None


class EventUpdate(BaseModel):
    event_title: Optional[str] = None
    event_type: Optional[EventType] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    all_day_flag: Optional[bool] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[EventStatus] = None


class EventOut(BaseModel):
    event_id: str
    event_title: str
    event_type: EventType
    start_datetime: datetime
    end_datetime: datetime
    all_day_flag: bool
    created_by: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: EventStatus
    source_module: Optional[str] = None
    source_ref_id: Optional[str] = None
    recurrence_id: Optional[str] = None
    created_at: datetime
    participants: List[ParticipantOut] = []
    bookings: List[BookingOut] = []
    model_config = {"from_attributes": True}


class AvailabilityCheck(BaseModel):
    resource_id: str
    start_datetime: datetime
    end_datetime: datetime
    exclude_booking_id: Optional[str] = None


class SlotRequest(BaseModel):
    resource_ids: List[str]
    duration_minutes: int
    date: str
    max_slots: int = 5


class CAIRecOut(BaseModel):
    rec_id: str
    agent_type: CAIAgentType
    title: str
    body: str
    score: Optional[float] = None
    status: CAIRecStatus
    rec_metadata: dict = {}
    created_at: datetime
    model_config = {"from_attributes": True}


class CAIRecAck(BaseModel):
    status: CAIRecStatus


EventOut.model_rebuild()
