from __future__ import annotations

from datetime import date, time
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, EmailStr, model_validator

from app.models.hr import (
    ApprovalStatus, AttendanceStatus, EmployeeStatus,
    LeaveType, PaymentMethod, PayrollStatus,
)


# ── Employee ──────────────────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    employee_code: str
    full_name: str
    department: str
    role: str
    phone: Optional[str] = None
    email: Optional[str] = None
    hire_date: date
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    user_id: Optional[uuid.UUID] = None
    payment_method: Optional[PaymentMethod] = None
    mpesa_number: Optional[str] = None
    bank_account: Optional[str] = None
    salary_grade: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[EmployeeStatus] = None
    user_id: Optional[uuid.UUID] = None
    payment_method: Optional[PaymentMethod] = None
    mpesa_number: Optional[str] = None
    bank_account: Optional[str] = None
    salary_grade: Optional[str] = None


class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class EmployeeShort(BaseModel):
    id: uuid.UUID
    employee_code: str
    full_name: str
    department: str
    role: str
    status: EmployeeStatus

    model_config = {"from_attributes": True}


# ── Shift Template ────────────────────────────────────────────────────────────

class ShiftTemplateBase(BaseModel):
    name: str
    start_time: time
    end_time: time
    department: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ShiftTemplateCreate(ShiftTemplateBase):
    pass


class ShiftTemplateUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    department: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ShiftTemplateRead(ShiftTemplateBase):
    id: uuid.UUID
    created_at: Any

    model_config = {"from_attributes": True}


# ── Shift Assignment ──────────────────────────────────────────────────────────

class ShiftAssignmentCreate(BaseModel):
    employee_id: uuid.UUID
    shift_template_id: uuid.UUID
    effective_from: date
    effective_to: Optional[date] = None
    supervisor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ShiftAssignmentUpdate(BaseModel):
    effective_to: Optional[date] = None
    supervisor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ShiftAssignmentRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    shift_template_id: uuid.UUID
    effective_from: date
    effective_to: Optional[date]
    supervisor_id: Optional[uuid.UUID]
    notes: Optional[str]
    shift_template: Optional[ShiftTemplateRead] = None
    employee: Optional[EmployeeShort] = None

    model_config = {"from_attributes": True}


# ── Attendance ────────────────────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    employee_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus
    clock_in: Optional[time] = None
    clock_out: Optional[time] = None
    notes: Optional[str] = None


class AttendanceBulkCreate(BaseModel):
    records: List[AttendanceCreate]


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    clock_in: Optional[time] = None
    clock_out: Optional[time] = None
    notes: Optional[str] = None


class AttendanceRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus
    clock_in: Optional[time]
    clock_out: Optional[time]
    notes: Optional[str]
    recorded_by_id: Optional[uuid.UUID]
    employee: Optional[EmployeeShort] = None

    model_config = {"from_attributes": True}


# ── Leave ─────────────────────────────────────────────────────────────────────

class LeaveRequestCreate(BaseModel):
    employee_id: uuid.UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @model_validator(mode="after")
    def compute_days(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class LeaveReview(BaseModel):
    approval_status: ApprovalStatus
    review_note: Optional[str] = None


class LeaveRequestRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_requested: int
    reason: Optional[str]
    approval_status: ApprovalStatus
    reviewed_by_id: Optional[uuid.UUID]
    review_note: Optional[str]
    employee: Optional[EmployeeShort] = None

    model_config = {"from_attributes": True}


class LeaveBalanceRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type: LeaveType
    year: int
    entitled_days: int
    used_days: int
    remaining: int

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_remaining(cls, obj: Any) -> "LeaveBalanceRead":
        return cls(
            id=obj.id,
            employee_id=obj.employee_id,
            leave_type=obj.leave_type,
            year=obj.year,
            entitled_days=obj.entitled_days,
            used_days=obj.used_days,
            remaining=obj.entitled_days - obj.used_days,
        )


# ── Payroll ───────────────────────────────────────────────────────────────────

class PayrollPeriodCreate(BaseModel):
    period_month: int
    period_year: int
    notes: Optional[str] = None


class PayrollPeriodRead(BaseModel):
    id: uuid.UUID
    period_month: int
    period_year: int
    status: PayrollStatus
    notes: Optional[str]
    approved_by_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class PayrollLineCreate(BaseModel):
    employee_id: uuid.UUID
    salary_components: Optional[Dict[str, Any]] = None
    gross_pay: int = 0
    net_pay: int = 0
    payment_method: Optional[PaymentMethod] = None


class PayrollLineUpdate(BaseModel):
    salary_components: Optional[Dict[str, Any]] = None
    gross_pay: Optional[int] = None
    net_pay: Optional[int] = None
    payment_method: Optional[PaymentMethod] = None
    payment_reference: Optional[str] = None
    is_paid: Optional[bool] = None


class PayrollLineRead(BaseModel):
    id: uuid.UUID
    period_id: uuid.UUID
    employee_id: uuid.UUID
    salary_components: Optional[Dict[str, Any]]
    gross_pay: int
    net_pay: int
    payment_method: Optional[PaymentMethod]
    payment_reference: Optional[str]
    is_paid: bool
    paid_by_id: Optional[uuid.UUID]
    employee: Optional[EmployeeShort] = None

    model_config = {"from_attributes": True}


class PayrollPeriodDetailRead(PayrollPeriodRead):
    lines: List[PayrollLineRead] = []

    model_config = {"from_attributes": True}
