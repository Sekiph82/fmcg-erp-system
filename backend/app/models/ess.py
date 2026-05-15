from __future__ import annotations
import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ESSAccountStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class EmploymentStatus(str, PyEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    RESIGNED = "resigned"
    TERMINATED = "terminated"
    PROBATION = "probation"


class LeaveStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AttendanceStatus(str, PyEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"
    WORK_FROM_HOME = "work_from_home"


class ESSRequestType(str, PyEnum):
    LEAVE = "leave"
    EXPENSE = "expense"
    PROFILE_UPDATE = "profile_update"
    DOCUMENT = "document"
    CERTIFICATE = "certificate"
    PAYSLIP = "payslip"
    OTHER = "other"


class ESSRequestStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class NotificationType(str, PyEnum):
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    REQUEST_UPDATE = "request_update"
    HR_ANNOUNCEMENT = "hr_announcement"
    REMINDER = "reminder"
    SYSTEM = "system"
    PAYSLIP_READY = "payslip_ready"


class ESSDocumentType(str, PyEnum):
    PAYSLIP = "payslip"
    CONTRACT = "contract"
    OFFER_LETTER = "offer_letter"
    EXPERIENCE_CERT = "experience_cert"
    SALARY_CERT = "salary_cert"
    HR_LETTER = "hr_letter"
    APPRAISAL = "appraisal"
    OTHER = "other"


class ESSAIAgentType(str, PyEnum):
    EMPLOYEE_ASSISTANT = "employee_assistant"
    HR_SUPPORT_ASSISTANT = "hr_support_assistant"


class ESSAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


# ── ESS Account ───────────────────────────────────────────────────────────────

class ESSAccount(Base):
    __tablename__ = "ess_accounts"

    ess_account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    hr_employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    status = Column(Enum(ESSAccountStatus), default=ESSAccountStatus.ACTIVE)
    last_login = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    reset_token = Column(String(100), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("ESSEmployeeProfile", back_populates="account", uselist=False)
    activity_logs = relationship("ESSActivityLog", back_populates="account")
    user = relationship("User", foreign_keys=[user_id])
    hr_employee = relationship("Employee", foreign_keys=[hr_employee_id])


# ── Employee Profile ──────────────────────────────────────────────────────────

class ESSEmployeeProfile(Base):
    __tablename__ = "ess_employee_profiles"

    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("ess_accounts.employee_id"), unique=True, nullable=False)
    hr_employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(200), nullable=False)
    personal_email = Column(String(200), nullable=True)
    phone = Column(String(30), nullable=True)
    address = Column(Text, nullable=True)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    department_name = Column(String(150), nullable=True)
    manager_id = Column(UUID(as_uuid=True), nullable=True)
    manager_name = Column(String(150), nullable=True)
    job_title = Column(String(150), nullable=True)
    joining_date = Column(Date, nullable=True)
    employment_status = Column(Enum(EmploymentStatus), default=EmploymentStatus.ACTIVE)
    grade = Column(String(50), nullable=True)
    profile_photo = Column(String(500), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    national_id = Column(String(30), nullable=True)
    emergency_contact_name = Column(String(150), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("ESSAccount", back_populates="profile")
    hr_employee = relationship("Employee", foreign_keys=[hr_employee_id])


# ── Leave Type ────────────────────────────────────────────────────────────────

class ESSLeaveType(Base):
    __tablename__ = "ess_leave_types"

    leave_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_code = Column(String(30), unique=True, nullable=False)
    type_name = Column(String(100), nullable=False)
    annual_entitlement_days = Column(Integer, default=21)
    carry_forward_max = Column(Integer, default=0)
    requires_approval = Column(Boolean, default=True)
    requires_document = Column(Boolean, default=False)
    paid_leave = Column(Boolean, default=True)
    active_flag = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    balances = relationship("ESSLeaveBalance", back_populates="leave_type")
    requests = relationship("ESSLeaveRequest", back_populates="leave_type")


# ── Leave Balance ─────────────────────────────────────────────────────────────

class ESSLeaveBalance(Base):
    __tablename__ = "ess_leave_balances"

    balance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("ess_leave_types.leave_type_id"), nullable=False)
    year = Column(Integer, nullable=False)
    entitled_days = Column(Numeric(5, 1), default=0)
    taken_days = Column(Numeric(5, 1), default=0)
    pending_days = Column(Numeric(5, 1), default=0)
    carried_forward = Column(Numeric(5, 1), default=0)
    adjusted_days = Column(Numeric(5, 1), default=0)

    __table_args__ = (UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance"),)

    leave_type = relationship("ESSLeaveType", back_populates="balances")

    @property
    def available_days(self):
        return float(self.entitled_days) + float(self.carried_forward) + float(self.adjusted_days) - float(self.taken_days) - float(self.pending_days)


# ── Leave Request ─────────────────────────────────────────────────────────────

class ESSLeaveRequest(Base):
    __tablename__ = "ess_leave_requests"

    leave_request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leave_request_no = Column(String(30), unique=True, nullable=False)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("ess_leave_types.leave_type_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Numeric(5, 1), nullable=False)
    reason = Column(Text, nullable=True)
    attachment_ref = Column(String(500), nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.DRAFT)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    leave_type = relationship("ESSLeaveType", back_populates="requests")


# ── Attendance Record ─────────────────────────────────────────────────────────

class ESSAttendanceRecord(Base):
    __tablename__ = "ess_attendance_records"

    attendance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    attendance_date = Column(Date, nullable=False)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    status = Column(Enum(AttendanceStatus, name="ess_attendancestatus"), default=AttendanceStatus.PRESENT)
    hours_worked = Column(Numeric(4, 2), nullable=True)
    overtime_hours = Column(Numeric(4, 2), default=0)
    late_minutes = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_employee_attendance_date"),)


# ── ESS Request ───────────────────────────────────────────────────────────────

class ESSRequest(Base):
    __tablename__ = "ess_requests"

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_no = Column(String(30), unique=True, nullable=False)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    request_type = Column(Enum(ESSRequestType), nullable=False)
    request_date = Column(Date, nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    attachment_ref = Column(String(500), nullable=True)
    status = Column(Enum(ESSRequestStatus), default=ESSRequestStatus.DRAFT)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    hr_notes = Column(Text, nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Notification ──────────────────────────────────────────────────────────────

class ESSNotification(Base):
    __tablename__ = "ess_notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    notification_type = Column(Enum(NotificationType, name="ess_notificationtype"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    read_flag = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── ESS Document ──────────────────────────────────────────────────────────────

class ESSDocument(Base):
    __tablename__ = "ess_documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    document_type = Column(Enum(ESSDocumentType), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_ref = Column(String(500), nullable=True)
    period = Column(String(30), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), nullable=True)
    visible_to_employee = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Activity Log ──────────────────────────────────────────────────────────────

class ESSActivityLog(Base):
    __tablename__ = "ess_activity_logs"

    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("ess_accounts.employee_id"), nullable=False)
    activity_type = Column(String(80), nullable=False)
    description = Column(String(500), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("ESSAccount", back_populates="activity_logs")


# ── AI Recommendation ─────────────────────────────────────────────────────────

class ESSAIRecommendation(Base):
    __tablename__ = "ess_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(ESSAIAgentType), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    ref_employee_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(ESSAIRecStatus), default=ESSAIRecStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
