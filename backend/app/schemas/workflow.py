from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.workflow import ApprovalModule, ApprovalStatus


class ApprovalRuleCreate(BaseModel):
    module:        ApprovalModule
    level:         int = 1
    required_role: str
    amount_min:    Decimal = Decimal("0")
    amount_max:    Optional[Decimal] = None
    sla_hours:     int = 24
    description:   Optional[str] = None


class ApprovalRuleUpdate(BaseModel):
    required_role: Optional[str]    = None
    amount_min:    Optional[Decimal] = None
    amount_max:    Optional[Decimal] = None
    sla_hours:     Optional[int]    = None
    is_active:     Optional[bool]   = None
    description:   Optional[str]    = None


class ApprovalRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    module:        ApprovalModule
    level:         int
    required_role: str
    amount_min:    Decimal
    amount_max:    Optional[Decimal]
    sla_hours:     int
    is_active:     bool
    description:   Optional[str]
    created_at:    datetime


class ApprovalStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    request_id:       uuid.UUID
    level:            int
    required_role:    str
    status:           ApprovalStatus
    sla_deadline:     Optional[datetime]
    action_at:        Optional[datetime]
    action_by_id:     Optional[uuid.UUID]
    action_by_name:   Optional[str] = None
    notes:            Optional[str]
    rejection_reason: Optional[str]
    created_at:       datetime


class ApprovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    module:           ApprovalModule
    object_id:        uuid.UUID
    object_ref:       str
    amount:           Optional[Decimal]
    currency:         str
    status:           ApprovalStatus
    current_level:    int
    max_level:        int
    description:      Optional[str]
    requested_by_id:  Optional[uuid.UUID]
    requested_by_name: Optional[str] = None
    final_action_at:  Optional[datetime]
    created_at:       datetime
    steps:            List[ApprovalStepRead] = []


class ApprovalSubmit(BaseModel):
    module:      ApprovalModule
    object_id:   uuid.UUID
    object_ref:  str
    amount:      Optional[Decimal] = None
    currency:    str = "KES"
    description: Optional[str] = None


class ApprovalAction(BaseModel):
    notes: Optional[str] = None


class ApprovalReject(BaseModel):
    reason: str
