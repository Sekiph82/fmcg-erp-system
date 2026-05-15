from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.ess import (
    ESSAccountStatus, EmploymentStatus, LeaveStatus, AttendanceStatus,
    ESSRequestType, ESSRequestStatus, NotificationType, ESSDocumentType,
    ESSAIAgentType, ESSAIRecStatus,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class ESSLoginRequest(BaseModel):
    email: str
    password: str


class ESSLoginResponse(BaseModel):
    ess_account_id: UUID
    employee_id: UUID
    hr_employee_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    email: str
    token: str
    status: ESSAccountStatus


class ESSAccountCreate(BaseModel):
    employee_id: UUID
    hr_employee_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    email: str
    password: str


class ESSAccountRead(BaseModel):
    ess_account_id: UUID
    employee_id: UUID
    hr_employee_id: Optional[UUID]
    user_id: Optional[UUID]
    email: str
    status: ESSAccountStatus
    last_login: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class ESSPasswordReset(BaseModel):
    email: str


class ESSPasswordChange(BaseModel):
    token: str
    new_password: str


# ── Profile ───────────────────────────────────────────────────────────────────

class ESSProfileCreate(BaseModel):
    employee_id: UUID
    hr_employee_id: Optional[UUID] = None
    full_name: str
    email: str
    personal_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    manager_id: Optional[UUID] = None
    manager_name: Optional[str] = None
    job_title: Optional[str] = None
    joining_date: Optional[date] = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    grade: Optional[str] = None
    national_id: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class ESSProfileRead(ESSProfileCreate):
    profile_id: UUID
    profile_photo: Optional[str]
    bank_account_no: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ESSProfileUpdate(BaseModel):
    personal_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    profile_photo: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


# ── Leave Types ───────────────────────────────────────────────────────────────

class ESSLeaveTypeCreate(BaseModel):
    type_code: str
    type_name: str
    annual_entitlement_days: int = 21
    carry_forward_max: int = 0
    requires_approval: bool = True
    requires_document: bool = False
    paid_leave: bool = True
    notes: Optional[str] = None


class ESSLeaveTypeRead(ESSLeaveTypeCreate):
    leave_type_id: UUID
    active_flag: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Leave Balance ─────────────────────────────────────────────────────────────

class ESSLeaveBalanceRead(BaseModel):
    balance_id: UUID
    employee_id: UUID
    leave_type_id: UUID
    year: int
    entitled_days: Decimal
    taken_days: Decimal
    pending_days: Decimal
    carried_forward: Decimal
    adjusted_days: Decimal
    available_days: float
    model_config = {"from_attributes": True}


class ESSLeaveBalanceUpsert(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    year: int
    entitled_days: Decimal = Decimal("0")
    carried_forward: Decimal = Decimal("0")
    adjusted_days: Decimal = Decimal("0")


# ── Leave Request ─────────────────────────────────────────────────────────────

class ESSLeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    reason: Optional[str] = None
    attachment_ref: Optional[str] = None


class ESSLeaveRequestRead(BaseModel):
    leave_request_id: UUID
    leave_request_no: str
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    days_requested: Decimal
    reason: Optional[str]
    attachment_ref: Optional[str]
    status: LeaveStatus
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ESSLeaveApproveReject(BaseModel):
    approver_id: UUID
    rejection_reason: Optional[str] = None


# ── Attendance ────────────────────────────────────────────────────────────────

class ESSAttendanceCreate(BaseModel):
    employee_id: UUID
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = None


class ESSAttendanceRead(ESSAttendanceCreate):
    attendance_id: UUID
    hours_worked: Optional[Decimal]
    overtime_hours: Decimal
    late_minutes: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ── ESS Request ───────────────────────────────────────────────────────────────

class ESSRequestCreate(BaseModel):
    employee_id: UUID
    request_type: ESSRequestType
    subject: str
    description: Optional[str] = None
    attachment_ref: Optional[str] = None
    reference_id: Optional[UUID] = None


class ESSRequestRead(BaseModel):
    request_id: UUID
    request_no: str
    employee_id: UUID
    request_type: ESSRequestType
    request_date: date
    subject: str
    description: Optional[str]
    attachment_ref: Optional[str]
    status: ESSRequestStatus
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    hr_notes: Optional[str]
    reference_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ESSRequestReview(BaseModel):
    approver_id: UUID
    status: ESSRequestStatus
    hr_notes: Optional[str] = None


# ── Document ──────────────────────────────────────────────────────────────────

class ESSDocumentCreate(BaseModel):
    employee_id: UUID
    document_type: ESSDocumentType
    document_name: str
    document_ref: Optional[str] = None
    period: Optional[str] = None
    uploaded_by: Optional[UUID] = None


class ESSDocumentRead(ESSDocumentCreate):
    document_id: UUID
    visible_to_employee: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Notification ──────────────────────────────────────────────────────────────

class ESSNotificationRead(BaseModel):
    notification_id: UUID
    employee_id: UUID
    notification_type: NotificationType
    title: str
    body: str
    reference_id: Optional[UUID]
    read_flag: bool
    read_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class ESSDashboardResponse(BaseModel):
    employee_name: str
    job_title: Optional[str]
    department_name: Optional[str]
    days_since_joining: int
    pending_leave_requests: int
    unread_notifications: int
    pending_requests: int
    annual_leave_available: float
    attendance_this_month: int
    documents_count: int


# ── Activity Log ──────────────────────────────────────────────────────────────

class ESSActivityLogRead(BaseModel):
    activity_id: UUID
    employee_id: UUID
    activity_type: str
    description: Optional[str]
    reference_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI ────────────────────────────────────────────────────────────────────────

class ESSAIRecRead(BaseModel):
    rec_id: UUID
    agent_type: ESSAIAgentType
    subject: str
    body: str
    ref_employee_id: Optional[UUID]
    status: ESSAIRecStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class ESSAIRecAck(BaseModel):
    status: ESSAIRecStatus
    notes: Optional[str] = None
