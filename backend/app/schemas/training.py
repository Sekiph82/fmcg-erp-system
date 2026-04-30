from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.training import (
    SkillCategory, SkillLevel, TrainingType,
    SessionStatus, AssignmentStatus, CertificationStatus,
    TRAIAgentType, TRAIRecStatus,
)


# ── Skill Master ──────────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    skill_code: str
    skill_name: str
    category: SkillCategory
    description: Optional[str] = None
    active_flag: bool = True


class SkillUpdate(BaseModel):
    skill_name: Optional[str] = None
    category: Optional[SkillCategory] = None
    description: Optional[str] = None
    active_flag: Optional[bool] = None


class SkillOut(BaseModel):
    skill_id: UUID
    skill_code: str
    skill_name: str
    category: SkillCategory
    description: Optional[str]
    active_flag: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Employee Skill Profile ────────────────────────────────────────────────────

class EmployeeSkillCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    skill_id: UUID
    current_level: Optional[SkillLevel] = None
    required_level: Optional[SkillLevel] = None
    last_assessed_date: Optional[date] = None
    notes: Optional[str] = None


class EmployeeSkillUpdate(BaseModel):
    current_level: Optional[SkillLevel] = None
    required_level: Optional[SkillLevel] = None
    last_assessed_date: Optional[date] = None
    notes: Optional[str] = None


class EmployeeSkillOut(BaseModel):
    employee_skill_id: UUID
    employee_id: str
    employee_name: Optional[str]
    department_id: Optional[str]
    skill_id: UUID
    skill_name: Optional[str] = None
    skill_category: Optional[str] = None
    current_level: Optional[SkillLevel]
    required_level: Optional[SkillLevel]
    last_assessed_date: Optional[date]
    has_gap: bool = False
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Training Program ──────────────────────────────────────────────────────────

class TrainingProgramCreate(BaseModel):
    training_code: str
    training_name: str
    training_type: TrainingType
    category: SkillCategory
    duration_hours: Optional[Decimal] = None
    provider: Optional[str] = None
    cost: Optional[Decimal] = None
    mandatory_flag: bool = False
    validity_period_days: Optional[int] = None
    notes: Optional[str] = None


class TrainingProgramUpdate(BaseModel):
    training_name: Optional[str] = None
    training_type: Optional[TrainingType] = None
    category: Optional[SkillCategory] = None
    duration_hours: Optional[Decimal] = None
    provider: Optional[str] = None
    cost: Optional[Decimal] = None
    mandatory_flag: Optional[bool] = None
    validity_period_days: Optional[int] = None
    active_flag: Optional[bool] = None
    notes: Optional[str] = None


class TrainingProgramOut(BaseModel):
    training_id: UUID
    training_code: str
    training_name: str
    training_type: TrainingType
    category: SkillCategory
    duration_hours: Optional[Decimal]
    provider: Optional[str]
    cost: Optional[Decimal]
    mandatory_flag: bool
    validity_period_days: Optional[int]
    active_flag: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Training Session ──────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    training_id: UUID
    session_date: date
    end_date: Optional[date] = None
    location: Optional[str] = None
    trainer_id: Optional[str] = None
    trainer_name: Optional[str] = None
    capacity: Optional[int] = None
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    session_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    trainer_name: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[SessionStatus] = None
    notes: Optional[str] = None


class SessionOut(BaseModel):
    session_id: UUID
    training_id: UUID
    training_name: Optional[str] = None
    session_date: date
    end_date: Optional[date]
    location: Optional[str]
    trainer_id: Optional[str]
    trainer_name: Optional[str]
    capacity: Optional[int]
    enrolled_count: int
    status: SessionStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Training Assignment ───────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    training_id: UUID
    session_id: Optional[UUID] = None
    assigned_by: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class AssignmentComplete(BaseModel):
    completion_date: Optional[date] = None
    score: Optional[Decimal] = None
    notes: Optional[str] = None


class AssignmentOut(BaseModel):
    assignment_id: UUID
    employee_id: str
    employee_name: Optional[str]
    department_id: Optional[str]
    training_id: UUID
    training_name: Optional[str] = None
    session_id: Optional[UUID]
    assigned_by: Optional[str]
    due_date: Optional[date]
    completion_date: Optional[date]
    status: AssignmentStatus
    score: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Certification ─────────────────────────────────────────────────────────────

class CertificationCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    training_id: Optional[UUID] = None
    certificate_name: str
    certificate_no: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    document_url: Optional[str] = None
    notes: Optional[str] = None


class CertificationUpdate(BaseModel):
    certificate_no: Optional[str] = None
    issuer: Optional[str] = None
    expiry_date: Optional[date] = None
    status: Optional[CertificationStatus] = None
    document_url: Optional[str] = None
    notes: Optional[str] = None


class CertificationOut(BaseModel):
    certification_id: UUID
    employee_id: str
    employee_name: Optional[str]
    training_id: Optional[UUID]
    certificate_name: str
    certificate_no: Optional[str]
    issuer: Optional[str]
    issue_date: date
    expiry_date: Optional[date]
    status: CertificationStatus
    days_to_expiry: Optional[int] = None
    document_url: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    training_id: UUID
    session_id: Optional[UUID] = None
    rating: int = Field(ge=1, le=5)
    content_rating: Optional[int] = Field(default=None, ge=1, le=5)
    trainer_rating: Optional[int] = Field(default=None, ge=1, le=5)
    relevance_rating: Optional[int] = Field(default=None, ge=1, le=5)
    comments: Optional[str] = None


class FeedbackOut(BaseModel):
    feedback_id: UUID
    employee_id: str
    employee_name: Optional[str]
    training_id: UUID
    session_id: Optional[UUID]
    rating: int
    content_rating: Optional[int]
    trainer_rating: Optional[int]
    relevance_rating: Optional[int]
    comments: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TrainingDashboard(BaseModel):
    total_programs: int
    active_programs: int
    total_sessions: int
    upcoming_sessions: int
    total_assignments: int
    completed_assignments: int
    overdue_assignments: int
    total_certifications: int
    expiring_soon: int
    expired_certifications: int
    total_skill_profiles: int
    skill_gaps: int
    avg_feedback_rating: Optional[float]


# ── AI ────────────────────────────────────────────────────────────────────────

class TRAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: TRAIAgentType
    status: TRAIRecStatus
    title: str
    body: str
    employee_id: Optional[str]
    department_id: Optional[str]
    training_id: Optional[UUID]
    certification_id: Optional[UUID]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TRAIRecAck(BaseModel):
    status: TRAIRecStatus
    actioned_by: Optional[str] = None


TrainingProgramOut.model_rebuild()
SessionOut.model_rebuild()
