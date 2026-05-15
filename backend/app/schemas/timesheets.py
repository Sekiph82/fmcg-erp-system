from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from app.models.timesheets import (
    TimesheetStatus, ActivityType, ApprovalAction,
    TSAIAgentType, TSAIRecStatus,
)


# ── Timesheet Line ────────────────────────────────────────────────────────────

class TimesheetLineCreate(BaseModel):
    work_date: date
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    activity_type: ActivityType = ActivityType.REGULAR
    cost_center_id: Optional[str] = None
    cost_center_name: Optional[str] = None
    hours_worked: Decimal = Field(gt=0, le=24)
    overtime_flag: bool = False
    billable_flag: bool = False
    notes: Optional[str] = None


class TimesheetLineUpdate(BaseModel):
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    activity_type: Optional[ActivityType] = None
    cost_center_id: Optional[str] = None
    cost_center_name: Optional[str] = None
    hours_worked: Optional[Decimal] = Field(default=None, gt=0, le=24)
    overtime_flag: Optional[bool] = None
    billable_flag: Optional[bool] = None
    notes: Optional[str] = None


class TimesheetLineOut(BaseModel):
    timesheet_line_id: UUID
    timesheet_id: UUID
    work_date: date
    project_id: Optional[str]
    project_name: Optional[str]
    task_id: Optional[str]
    task_name: Optional[str]
    activity_type: ActivityType
    cost_center_id: Optional[str]
    cost_center_name: Optional[str]
    hours_worked: Decimal
    overtime_flag: bool
    billable_flag: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Approval Log ──────────────────────────────────────────────────────────────

class ApprovalLogOut(BaseModel):
    approval_id: UUID
    timesheet_id: UUID
    approver_id: Optional[str]
    approver_name: Optional[str]
    action: ApprovalAction
    action_date: datetime
    comments: Optional[str]

    class Config:
        from_attributes = True


# ── Timesheet Header ──────────────────────────────────────────────────────────

class TimesheetCreate(BaseModel):
    employee_id: str
    hr_employee_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_employee_id: Optional[UUID] = None
    manager_name: Optional[str] = None
    period_start: date
    period_end: date
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_dates(self) -> "TimesheetCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be >= period_start")
        return self


class TimesheetSubmit(BaseModel):
    notes: Optional[str] = None


class TimesheetApprove(BaseModel):
    approver_id: Optional[str] = None
    approver_user_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    comments: Optional[str] = None


class TimesheetReject(BaseModel):
    approver_id: Optional[str] = None
    approver_user_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    comments: str


class TimesheetFinalize(BaseModel):
    finalized_by: Optional[str] = None
    finalized_by_id: Optional[UUID] = None
    payroll_run_id: Optional[UUID] = None
    comments: Optional[str] = None


class TimesheetOut(BaseModel):
    timesheet_id: UUID
    employee_id: str
    hr_employee_id: Optional[UUID]
    company_id: Optional[UUID]
    branch_id: Optional[UUID]
    employee_name: Optional[str]
    department_id: Optional[str]
    department_name: Optional[str]
    manager_id: Optional[str]
    manager_employee_id: Optional[UUID]
    manager_name: Optional[str]
    period_start: date
    period_end: date
    status: TimesheetStatus
    total_hours: Decimal
    overtime_hours: Decimal
    regular_hours: Decimal
    submitted_at: Optional[datetime]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    payroll_run_id: Optional[UUID]
    finalized_by_id: Optional[UUID]
    finalized_at: Optional[datetime]
    rejection_count: int
    notes: Optional[str]
    created_at: datetime
    lines: List[TimesheetLineOut] = []
    approval_logs: List[ApprovalLogOut] = []

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TimesheetDashboard(BaseModel):
    total_timesheets: int
    draft: int
    submitted: int
    manager_approved: int
    rejected: int
    finalized: int
    total_hours_this_period: float
    overtime_hours_this_period: float
    avg_hours_per_employee: float
    pending_approval: int
    employees_with_timesheets: int
    project_hours: List[dict]


# ── AI ────────────────────────────────────────────────────────────────────────

class TSAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: TSAIAgentType
    status: TSAIRecStatus
    title: str
    body: str
    employee_id: Optional[str]
    department_id: Optional[str]
    timesheet_id: Optional[UUID]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TSAIRecAck(BaseModel):
    status: TSAIRecStatus
    actioned_by: Optional[str] = None


TimesheetOut.model_rebuild()
