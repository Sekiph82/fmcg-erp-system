from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel

from app.models.dunning import (
    DunningActionType, DunningCaseStatus, DunningActionOutcome,
    PTPStatus, DunningExceptionType, DunningAIAgentType, DunningAIRecStatus,
)


# ── Policy ─────────────────────────────────────────────────────────────────────

class DunningPolicyCreate(BaseModel):
    policy_code: str
    policy_name: str
    applies_to_customer_id: Optional[UUID] = None
    applies_to_channel: Optional[str] = None
    applies_to_region: Optional[str] = None
    applies_to_country: Optional[str] = None
    applies_to_segment: Optional[str] = None
    default_flag: bool = False
    auto_credit_hold_days: Optional[int] = None
    auto_credit_hold_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class DunningPolicyUpdate(BaseModel):
    policy_name: Optional[str] = None
    active_flag: Optional[bool] = None
    default_flag: Optional[bool] = None
    applies_to_channel: Optional[str] = None
    applies_to_region: Optional[str] = None
    applies_to_segment: Optional[str] = None
    auto_credit_hold_days: Optional[int] = None
    auto_credit_hold_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class DunningPolicyOut(BaseModel):
    id: UUID
    policy_code: str
    policy_name: str
    active_flag: bool
    applies_to_customer_id: Optional[UUID]
    applies_to_channel: Optional[str]
    applies_to_region: Optional[str]
    applies_to_country: Optional[str]
    applies_to_segment: Optional[str]
    default_flag: bool
    auto_credit_hold_days: Optional[int]
    auto_credit_hold_amount: Optional[Decimal]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Level ──────────────────────────────────────────────────────────────────────

class DunningLevelCreate(BaseModel):
    level_no: int
    level_name: str
    days_overdue_from: int
    days_overdue_to: Optional[int] = None
    action_type: DunningActionType = DunningActionType.EMAIL
    template_code: Optional[str] = None
    auto_send_flag: bool = True
    requires_approval_flag: bool = False
    apply_credit_hold_flag: bool = False
    escalate_to_role: Optional[str] = None
    notes: Optional[str] = None


class DunningLevelOut(BaseModel):
    id: UUID
    policy_id: UUID
    level_no: int
    level_name: str
    days_overdue_from: int
    days_overdue_to: Optional[int]
    action_type: DunningActionType
    template_code: Optional[str]
    auto_send_flag: bool
    requires_approval_flag: bool
    apply_credit_hold_flag: bool
    escalate_to_role: Optional[str]
    active_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Template ───────────────────────────────────────────────────────────────────

class DunningTemplateCreate(BaseModel):
    template_code: str
    language: str = "en"
    subject: str
    body_text: str
    channel: DunningActionType = DunningActionType.EMAIL
    notes: Optional[str] = None


class DunningTemplateOut(BaseModel):
    id: UUID
    template_code: str
    language: str
    subject: str
    body_text: str
    channel: DunningActionType
    active_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Case ───────────────────────────────────────────────────────────────────────

class DunningCaseOut(BaseModel):
    id: UUID
    case_no: str
    customer_id: UUID
    policy_id: Optional[UUID]
    current_level_no: int
    case_status: DunningCaseStatus
    total_overdue_amount: Decimal
    oldest_due_date: Optional[date]
    latest_action_date: Optional[datetime]
    next_action_date: Optional[date]
    assigned_collector_id: Optional[UUID]
    credit_hold_flag: bool
    credit_hold_reason: Optional[str]
    credit_hold_date: Optional[date]
    priority_score: int
    collector_notes: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DunningCaseNoteUpdate(BaseModel):
    collector_notes: str


class DunningCaseAssign(BaseModel):
    assigned_collector_id: UUID


# ── Case Invoice ───────────────────────────────────────────────────────────────

class DunningCaseInvoiceOut(BaseModel):
    id: UUID
    case_id: UUID
    invoice_id: UUID
    invoice_number: str
    invoice_due_date: date
    invoice_balance_amount: Decimal
    days_overdue: int
    dispute_flag: bool
    dispute_reason: Optional[str]
    promise_to_pay_date: Optional[date]
    excluded_from_dunning: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class DunningDisputeSet(BaseModel):
    invoice_id: UUID
    dispute_flag: bool
    dispute_reason: Optional[str] = None


# ── Action Log ─────────────────────────────────────────────────────────────────

class DunningActionLogOut(BaseModel):
    id: UUID
    case_id: UUID
    invoice_id: Optional[UUID]
    level_no: int
    action_type: DunningActionType
    channel_type: Optional[str]
    action_datetime: datetime
    sent_by_system_flag: bool
    outcome_status: DunningActionOutcome
    rendered_subject: Optional[str]
    rendered_body: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class DunningReminderRequest(BaseModel):
    channel: DunningActionType = DunningActionType.EMAIL
    manual_note: Optional[str] = None
    user_id: Optional[UUID] = None


class DunningManualNote(BaseModel):
    notes: str
    user_id: Optional[UUID] = None


# ── PTP ────────────────────────────────────────────────────────────────────────

class DunningPTPCreate(BaseModel):
    promised_amount: Decimal
    promised_date: date
    recorded_by: str
    notes: Optional[str] = None


class DunningPTPUpdate(BaseModel):
    status: PTPStatus
    notes: Optional[str] = None


class DunningPTPOut(BaseModel):
    id: UUID
    case_id: UUID
    customer_id: UUID
    promised_amount: Decimal
    promised_date: date
    recorded_by: str
    recorded_at: datetime
    status: PTPStatus
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Exception ──────────────────────────────────────────────────────────────────

class DunningExceptionCreate(BaseModel):
    exception_type: DunningExceptionType
    approved_by: str
    start_date: date
    end_date: Optional[date] = None
    reason: str
    notes: Optional[str] = None


class DunningExceptionOut(BaseModel):
    id: UUID
    case_id: UUID
    exception_type: DunningExceptionType
    approved_by: str
    start_date: date
    end_date: Optional[date]
    reason: str
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Credit Hold ────────────────────────────────────────────────────────────────

class CreditHoldApply(BaseModel):
    reason: str
    applied_by: str


class CreditHoldRelease(BaseModel):
    released_by: str
    notes: Optional[str] = None


# ── AI ─────────────────────────────────────────────────────────────────────────

class DunningAIRecAck(BaseModel):
    status: DunningAIRecStatus
    actioned_by: str


class DunningAIRecOut(BaseModel):
    id: UUID
    case_id: Optional[UUID]
    customer_id: Optional[UUID]
    agent_type: DunningAIAgentType
    status: DunningAIRecStatus
    title: str
    body: str
    severity: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Aging ──────────────────────────────────────────────────────────────────────

class AgingBucket(BaseModel):
    label: str
    days_from: int
    days_to: Optional[int]
    total_amount: Decimal
    invoice_count: int


class CustomerAgingRow(BaseModel):
    customer_id: str
    customer_name: str
    customer_code: str
    currency: str
    current: Decimal
    overdue_1_7: Decimal
    overdue_8_14: Decimal
    overdue_15_30: Decimal
    overdue_31_60: Decimal
    overdue_61_90: Decimal
    overdue_90_plus: Decimal
    total_overdue: Decimal
    credit_hold: bool
    case_id: Optional[str]
    priority_score: int
