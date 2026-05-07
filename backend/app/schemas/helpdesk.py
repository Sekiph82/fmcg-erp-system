from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.helpdesk import TicketStatus, TicketCategory, TicketPriority, TicketSource


class TicketCommentCreate(BaseModel):
    body: str
    is_internal: bool = False


class TicketCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    ticket_id:     uuid.UUID
    body:          str
    is_internal:   bool
    created_by_id: Optional[uuid.UUID]
    created_by_name: Optional[str] = None
    created_at:    datetime


class TicketCreate(BaseModel):
    customer_id:  Optional[uuid.UUID] = None
    category:     TicketCategory = TicketCategory.OTHER
    priority:     TicketPriority = TicketPriority.MEDIUM
    source:       TicketSource   = TicketSource.MANUAL
    subject:      str
    description:  Optional[str]  = None
    lot_id:       Optional[uuid.UUID] = None
    sla_hours:    Optional[int]  = None  # if None, derived from priority


class TicketUpdate(BaseModel):
    category:     Optional[TicketCategory] = None
    priority:     Optional[TicketPriority] = None
    source:       Optional[TicketSource]   = None
    subject:      Optional[str]            = None
    description:  Optional[str]            = None
    lot_id:       Optional[uuid.UUID]      = None
    sla_hours:    Optional[int]            = None


class TicketAssignRequest(BaseModel):
    user_id: uuid.UUID


class TicketResolveRequest(BaseModel):
    resolution_notes: Optional[str] = None


class TicketCloseRequest(BaseModel):
    customer_satisfaction: Optional[int] = None  # 1–5

    @field_validator("customer_satisfaction")
    @classmethod
    def validate_satisfaction(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in range(1, 6):
            raise ValueError("customer_satisfaction must be 1–5")
        return v


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    ticket_no:      str
    customer_id:    Optional[uuid.UUID]
    customer_name:  Optional[str] = None
    customer_code:  Optional[str] = None
    category:       TicketCategory
    priority:       TicketPriority
    status:         TicketStatus
    source:         TicketSource
    subject:        str
    description:    Optional[str]
    lot_id:         Optional[uuid.UUID]
    lot_number:     Optional[str] = None
    sla_hours:      int
    first_response_at: Optional[datetime]
    resolved_at:    Optional[datetime]
    closed_at:      Optional[datetime]
    resolution_notes: Optional[str]
    customer_satisfaction: Optional[int]
    assigned_to_id: Optional[uuid.UUID]
    assigned_to_name: Optional[str] = None
    created_by_id:  Optional[uuid.UUID]
    created_at:     datetime
    sla_breached:   bool = False
    comments:       List[TicketCommentRead] = []


class HelpdeskDashboard(BaseModel):
    total_tickets:       int
    open_count:          int
    in_progress_count:   int
    escalated_count:     int
    resolved_count:      int
    closed_count:        int
    sla_breached_count:  int
    avg_resolution_hours: Optional[float]
    by_category: dict
    by_priority: dict
