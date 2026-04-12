"""HR module – Employee Master, Shifts, Attendance, Leave, Payroll scaffold."""
from __future__ import annotations

import uuid
import enum
from datetime import date, time

from sqlalchemy import (
    Column, String, Boolean, Date, Time, Text, Integer,
    ForeignKey, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enumerations ──────────────────────────────────────────────────────────────

class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    LEAVE = "LEAVE"
    HALF_DAY = "HALF_DAY"


class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    UNPAID = "UNPAID"
    COMPASSIONATE = "COMPASSIONATE"
    OTHER = "OTHER"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    MPESA = "MPESA"
    BANK = "BANK"
    CASH = "CASH"


class PayrollStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


# ── Employee Master ───────────────────────────────────────────────────────────

class Employee(Base, TimestampMixin):
    """Core employee record. Optional link to a system User for accountability."""
    __tablename__ = "hr_employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    hire_date = Column(Date, nullable=False)
    status = Column(SAEnum(EmployeeStatus), nullable=False, default=EmployeeStatus.ACTIVE)

    # Link to system user (nullable – not every employee has a system login)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Payroll info (lightweight placeholder – no separate payment engine)
    payment_method = Column(SAEnum(PaymentMethod, name="hr_paymentmethod"), nullable=True)
    mpesa_number = Column(String(20), nullable=True)        # M-Pesa shortcode / phone
    bank_account = Column(String(50), nullable=True)
    salary_grade = Column(String(30), nullable=True)        # e.g. "G5", "Manager"

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    shift_assignments = relationship("EmployeeShiftAssignment", foreign_keys="EmployeeShiftAssignment.employee_id", back_populates="employee", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    payroll_lines = relationship("PayrollLine", back_populates="employee", cascade="all, delete-orphan")


# ── Shift Planning ────────────────────────────────────────────────────────────

class ShiftTemplate(Base, TimestampMixin):
    """Reusable shift definition (Morning, Night, Split, etc.)."""
    __tablename__ = "hr_shift_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    department = Column(String(100), nullable=True)   # null = company-wide
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    assignments = relationship("EmployeeShiftAssignment", back_populates="shift_template")


class EmployeeShiftAssignment(Base, TimestampMixin):
    """Links an employee to a shift template for a date range, with optional supervisor."""
    __tablename__ = "hr_shift_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_template_id = Column(UUID(as_uuid=True), ForeignKey("hr_shift_templates.id", ondelete="CASCADE"), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)    # null = open-ended
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="shift_assignments")
    shift_template = relationship("ShiftTemplate", back_populates="assignments")
    supervisor = relationship("Employee", foreign_keys=[supervisor_id])


# ── Attendance ────────────────────────────────────────────────────────────────

class AttendanceRecord(Base, TimestampMixin):
    """
    Daily attendance record. Future: clock_in / clock_out from biometric/RFID device.
    For now, recorded manually or via bulk import.
    """
    __tablename__ = "hr_attendance"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_hr_attendance_employee_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(SAEnum(AttendanceStatus), nullable=False)
    clock_in = Column(Time, nullable=True)      # placeholder for future device integration
    clock_out = Column(Time, nullable=True)     # placeholder for future device integration
    notes = Column(Text, nullable=True)

    # Accountability: which user recorded / last updated this record
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="attendance_records")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


# ── Leave Management ──────────────────────────────────────────────────────────

class LeaveRequest(Base, TimestampMixin):
    """Leave request with approval workflow."""
    __tablename__ = "hr_leave_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = Column(SAEnum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    approval_status = Column(SAEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)

    # Accountability: who approved/rejected, linked to system user
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_note = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="leave_requests")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class LeaveBalance(Base, TimestampMixin):
    """Snapshot of leave balance per employee per year. Updated on approval/cancellation."""
    __tablename__ = "hr_leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type", "year", name="uq_hr_leave_balance"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = Column(SAEnum(LeaveType), nullable=False)
    year = Column(Integer, nullable=False)
    entitled_days = Column(Integer, nullable=False, default=0)
    used_days = Column(Integer, nullable=False, default=0)

    employee = relationship("Employee")


# ── Payroll Foundation ────────────────────────────────────────────────────────

class PayrollPeriod(Base, TimestampMixin):
    """
    Payroll period (month/year). Export-ready: stores computed totals as JSONB.
    No separate payment engine – payment dispatched via existing finance/M-Pesa flows.
    """
    __tablename__ = "hr_payroll_periods"
    __table_args__ = (
        UniqueConstraint("period_month", "period_year", name="uq_hr_payroll_period"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_month = Column(Integer, nullable=False)   # 1-12
    period_year = Column(Integer, nullable=False)
    status = Column(SAEnum(PayrollStatus), nullable=False, default=PayrollStatus.DRAFT)
    notes = Column(Text, nullable=True)

    # Accountability: who approved payment run
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    lines = relationship("PayrollLine", back_populates="period", cascade="all, delete-orphan")


class PayrollLine(Base, TimestampMixin):
    """
    Per-employee payroll line for a period. Salary structure is a JSONB blob
    (basic, allowances, deductions) – flexible without schema migrations for
    each component change.
    Supports M-Pesa payment permission gating at API layer.
    """
    __tablename__ = "hr_payroll_lines"
    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", name="uq_hr_payroll_line"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_id = Column(UUID(as_uuid=True), ForeignKey("hr_payroll_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False, index=True)

    # Salary structure (placeholder – flexible JSONB)
    salary_components = Column(JSONB, nullable=True)
    # e.g. {"basic": 50000, "housing": 5000, "transport": 3000, "nssf": -200, "nhif": -500, "paye": -3000}

    gross_pay = Column(Integer, nullable=False, default=0)   # stored in minor units (cents/KES)
    net_pay = Column(Integer, nullable=False, default=0)

    payment_method = Column(SAEnum(PaymentMethod, name="hr_paymentmethod"), nullable=True)
    payment_reference = Column(String(100), nullable=True)   # M-Pesa TXN ID or bank ref
    is_paid = Column(Boolean, default=False, nullable=False)

    # Accountability: who initiated/authorised the payment
    paid_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    period = relationship("PayrollPeriod", back_populates="lines")
    employee = relationship("Employee", back_populates="payroll_lines")
    paid_by = relationship("User", foreign_keys=[paid_by_id])
