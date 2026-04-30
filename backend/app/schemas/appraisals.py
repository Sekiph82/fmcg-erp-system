from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.appraisals import (
    AppraisalPeriodType, AppraisalPeriodStatus, AppraisalStatus,
    FinalRating, DevelopmentPlanStatus, APAIAgentType, APAIRecStatus,
)


# ── Appraisal Period ──────────────────────────────────────────────────────────

class AppraisalPeriodCreate(BaseModel):
    period_code: str
    period_name: str
    period_type: AppraisalPeriodType
    start_date: date
    end_date: date
    review_start_date: Optional[date] = None
    review_end_date: Optional[date] = None
    notes: Optional[str] = None


class AppraisalPeriodUpdate(BaseModel):
    period_name: Optional[str] = None
    period_type: Optional[AppraisalPeriodType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    review_start_date: Optional[date] = None
    review_end_date: Optional[date] = None
    status: Optional[AppraisalPeriodStatus] = None
    notes: Optional[str] = None


class AppraisalPeriodOut(BaseModel):
    appraisal_period_id: UUID
    period_code: str
    period_name: str
    period_type: AppraisalPeriodType
    start_date: date
    end_date: date
    review_start_date: Optional[date]
    review_end_date: Optional[date]
    status: AppraisalPeriodStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Appraisal Template ────────────────────────────────────────────────────────

class AppraisalTemplateCreate(BaseModel):
    template_code: str
    template_name: str
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    employee_grade_id: Optional[str] = None
    kpi_weight_pct: Decimal = Field(default=Decimal("60.00"))
    competency_weight_pct: Decimal = Field(default=Decimal("40.00"))
    active_flag: bool = True
    notes: Optional[str] = None


class AppraisalTemplateOut(BaseModel):
    template_id: UUID
    template_code: str
    template_name: str
    department_id: Optional[str]
    role_id: Optional[str]
    employee_grade_id: Optional[str]
    kpi_weight_pct: Decimal
    competency_weight_pct: Decimal
    active_flag: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── KPI Line ──────────────────────────────────────────────────────────────────

class KPILineCreate(BaseModel):
    kpi_name: str
    kpi_description: Optional[str] = None
    target_value: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    unit: Optional[str] = None
    weight_pct: Decimal = Field(default=Decimal("0.00"))
    self_score: Optional[Decimal] = None
    comments: Optional[str] = None


class KPILineUpdate(BaseModel):
    actual_value: Optional[Decimal] = None
    self_score: Optional[Decimal] = None
    manager_score: Optional[Decimal] = None
    final_score: Optional[Decimal] = None
    comments: Optional[str] = None


class KPILineOut(BaseModel):
    kpi_line_id: UUID
    appraisal_id: UUID
    kpi_name: str
    kpi_description: Optional[str]
    target_value: Optional[Decimal]
    actual_value: Optional[Decimal]
    unit: Optional[str]
    weight_pct: Decimal
    self_score: Optional[Decimal]
    manager_score: Optional[Decimal]
    final_score: Optional[Decimal]
    comments: Optional[str]

    class Config:
        from_attributes = True


# ── Competency Line ───────────────────────────────────────────────────────────

class CompetencyLineCreate(BaseModel):
    competency_name: str
    description: Optional[str] = None
    weight_pct: Decimal = Field(default=Decimal("0.00"))
    self_rating: Optional[Decimal] = None
    comments: Optional[str] = None


class CompetencyLineUpdate(BaseModel):
    self_rating: Optional[Decimal] = None
    manager_rating: Optional[Decimal] = None
    final_rating: Optional[Decimal] = None
    comments: Optional[str] = None


class CompetencyLineOut(BaseModel):
    competency_line_id: UUID
    appraisal_id: UUID
    competency_name: str
    description: Optional[str]
    weight_pct: Decimal
    self_rating: Optional[Decimal]
    manager_rating: Optional[Decimal]
    final_rating: Optional[Decimal]
    comments: Optional[str]

    class Config:
        from_attributes = True


# ── Development Plan ──────────────────────────────────────────────────────────

class DevelopmentPlanCreate(BaseModel):
    goal_title: str
    action_plan: Optional[str] = None
    due_date: Optional[date] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    notes: Optional[str] = None


class DevelopmentPlanUpdate(BaseModel):
    goal_title: Optional[str] = None
    action_plan: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[DevelopmentPlanStatus] = None
    notes: Optional[str] = None


class DevelopmentPlanOut(BaseModel):
    development_plan_id: UUID
    appraisal_id: UUID
    employee_id: str
    goal_title: str
    action_plan: Optional[str]
    due_date: Optional[date]
    owner_id: Optional[str]
    owner_name: Optional[str]
    status: DevelopmentPlanStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Appraisal Record ──────────────────────────────────────────────────────────

class AppraisalRecordCreate(BaseModel):
    appraisal_period_id: UUID
    employee_id: str
    employee_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    template_id: Optional[UUID] = None
    notes: Optional[str] = None


class SelfSubmitRequest(BaseModel):
    self_score: Optional[Decimal] = None
    notes: Optional[str] = None


class ManagerReviewRequest(BaseModel):
    manager_score: Optional[Decimal] = None
    increment_recommendation: Optional[Decimal] = None
    promotion_recommendation: bool = False
    notes: Optional[str] = None


class HRReviewRequest(BaseModel):
    final_score: Optional[Decimal] = None
    final_rating: Optional[FinalRating] = None
    hr_notes: Optional[str] = None
    calibration_notes: Optional[str] = None


class FinalizeRequest(BaseModel):
    final_score: Optional[Decimal] = None
    final_rating: Optional[FinalRating] = None
    increment_recommendation: Optional[Decimal] = None
    promotion_recommendation: Optional[bool] = None
    hr_notes: Optional[str] = None


class AppraisalRecordOut(BaseModel):
    appraisal_id: UUID
    appraisal_period_id: UUID
    employee_id: str
    employee_name: Optional[str]
    manager_id: Optional[str]
    manager_name: Optional[str]
    department_id: Optional[str]
    department_name: Optional[str]
    template_id: Optional[UUID]
    status: AppraisalStatus
    self_score: Optional[Decimal]
    manager_score: Optional[Decimal]
    final_score: Optional[Decimal]
    final_rating: Optional[FinalRating]
    increment_recommendation: Optional[Decimal]
    promotion_recommendation: bool
    self_submitted_at: Optional[datetime]
    manager_reviewed_at: Optional[datetime]
    hr_reviewed_at: Optional[datetime]
    finalized_at: Optional[datetime]
    hr_notes: Optional[str]
    calibration_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime
    kpi_lines: List[KPILineOut] = []
    competency_lines: List[CompetencyLineOut] = []
    development_plans: List[DevelopmentPlanOut] = []

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class AppraisalDashboard(BaseModel):
    total_records: int
    self_review_pending: int
    manager_review_pending: int
    hr_review_pending: int
    calibration_pending: int
    completed: int
    avg_final_score: Optional[float]
    rating_distribution: dict
    department_avg_scores: List[dict]
    pending_development_plans: int
    promotion_recommendations: int


# ── AI ────────────────────────────────────────────────────────────────────────

class APAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: APAIAgentType
    status: APAIRecStatus
    title: str
    body: str
    appraisal_id: Optional[UUID]
    employee_id: Optional[str]
    department_id: Optional[str]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APAIRecAck(BaseModel):
    status: APAIRecStatus
    actioned_by: Optional[str] = None


AppraisalRecordOut.model_rebuild()
