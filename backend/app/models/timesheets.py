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


class TimesheetStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    MANAGER_APPROVED = "manager_approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"


class ActivityType(str, PyEnum):
    REGULAR = "regular"
    OVERTIME = "overtime"
    TRAINING = "training"
    LEAVE = "leave"
    MEETING = "meeting"
    ADMIN = "admin"
    PROJECT = "project"
    SUPPORT = "support"
    OTHER = "other"


class ApprovalAction(str, PyEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"
    RESUBMITTED = "resubmitted"


class TSAIAgentType(str, PyEnum):
    UTILIZATION_ANALYZER = "utilization_analyzer"
    ANOMALY_DETECTOR = "anomaly_detector"


class TSAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class TimesheetHeader(Base):
    __tablename__ = "timesheet_headers"

    timesheet_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    department_id = Column(String(100), nullable=True)
    department_name = Column(String(200), nullable=True)
    manager_id = Column(String(100), nullable=True)
    manager_name = Column(String(200), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(TimesheetStatus), default=TimesheetStatus.DRAFT, nullable=False)
    total_hours = Column(Numeric(6, 2), default=Decimal("0.00"))
    overtime_hours = Column(Numeric(6, 2), default=Decimal("0.00"))
    regular_hours = Column(Numeric(6, 2), default=Decimal("0.00"))
    submitted_at = Column(DateTime, nullable=True)
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    rejection_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = relationship("TimesheetLine", back_populates="timesheet", cascade="all, delete-orphan")
    approval_logs = relationship("TimesheetApprovalLog", back_populates="timesheet", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("employee_id", "period_start", "period_end", name="uq_timesheet_employee_period"),
    )


class TimesheetLine(Base):
    __tablename__ = "timesheet_lines"

    timesheet_line_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id = Column(UUID(as_uuid=True), ForeignKey("timesheet_headers.timesheet_id"), nullable=False)
    work_date = Column(Date, nullable=False)
    project_id = Column(String(100), nullable=True)
    project_name = Column(String(200), nullable=True)
    task_id = Column(String(100), nullable=True)
    task_name = Column(String(200), nullable=True)
    activity_type = Column(Enum(ActivityType), default=ActivityType.REGULAR, nullable=False)
    cost_center_id = Column(String(100), nullable=True)
    cost_center_name = Column(String(200), nullable=True)
    hours_worked = Column(Numeric(5, 2), nullable=False)
    overtime_flag = Column(Boolean, default=False)
    billable_flag = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    timesheet = relationship("TimesheetHeader", back_populates="lines")


class TimesheetApprovalLog(Base):
    __tablename__ = "timesheet_approval_logs"

    approval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id = Column(UUID(as_uuid=True), ForeignKey("timesheet_headers.timesheet_id"), nullable=False)
    approver_id = Column(String(100), nullable=True)
    approver_name = Column(String(200), nullable=True)
    action = Column(Enum(ApprovalAction), nullable=False)
    action_date = Column(DateTime, default=datetime.utcnow)
    comments = Column(Text, nullable=True)

    timesheet = relationship("TimesheetHeader", back_populates="approval_logs")


class TSAIRecommendation(Base):
    __tablename__ = "ts_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(TSAIAgentType), nullable=False)
    status = Column(Enum(TSAIRecStatus), default=TSAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    employee_id = Column(String(100), nullable=True)
    department_id = Column(String(100), nullable=True)
    timesheet_id = Column(UUID(as_uuid=True), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
