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


class AppraisalPeriodType(str, PyEnum):
    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    QUARTERLY = "quarterly"
    PROBATION = "probation"
    PROJECT_BASED = "project_based"
    CUSTOM = "custom"


class AppraisalPeriodStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class AppraisalStatus(str, PyEnum):
    DRAFT = "draft"
    SELF_REVIEW = "self_review"
    MANAGER_REVIEW = "manager_review"
    HR_REVIEW = "hr_review"
    CALIBRATION = "calibration"
    COMPLETED = "completed"
    REJECTED = "rejected"


class FinalRating(str, PyEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MEETS_EXPECTATIONS = "meets_expectations"
    IMPROVEMENT_NEEDED = "improvement_needed"


class DevelopmentPlanStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class APAIAgentType(str, PyEnum):
    PERFORMANCE_INSIGHT = "performance_insight"
    CALIBRATION_RISK = "calibration_risk"
    DEVELOPMENT_PLAN = "development_plan"


class APAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class AppraisalPeriod(Base):
    __tablename__ = "appraisal_periods"

    appraisal_period_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_code = Column(String(50), unique=True, nullable=False)
    period_name = Column(String(200), nullable=False)
    period_type = Column(Enum(AppraisalPeriodType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    review_start_date = Column(Date, nullable=True)
    review_end_date = Column(Date, nullable=True)
    status = Column(Enum(AppraisalPeriodStatus), default=AppraisalPeriodStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    records = relationship("AppraisalRecord", back_populates="period", lazy="dynamic")


class AppraisalTemplate(Base):
    __tablename__ = "appraisal_templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String(50), unique=True, nullable=False)
    template_name = Column(String(200), nullable=False)
    department_id = Column(String(100), nullable=True)
    role_id = Column(String(100), nullable=True)
    employee_grade_id = Column(String(100), nullable=True)
    kpi_weight_pct = Column(Numeric(5, 2), default=Decimal("60.00"))
    competency_weight_pct = Column(Numeric(5, 2), default=Decimal("40.00"))
    active_flag = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    records = relationship("AppraisalRecord", back_populates="template", lazy="dynamic")


class AppraisalRecord(Base):
    __tablename__ = "appraisal_records"

    appraisal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appraisal_period_id = Column(UUID(as_uuid=True), ForeignKey("appraisal_periods.appraisal_period_id"), nullable=False)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    manager_id = Column(String(100), nullable=True)
    manager_name = Column(String(200), nullable=True)
    department_id = Column(String(100), nullable=True)
    department_name = Column(String(200), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("appraisal_templates.template_id"), nullable=True)
    status = Column(Enum(AppraisalStatus), default=AppraisalStatus.DRAFT, nullable=False)
    self_score = Column(Numeric(5, 2), nullable=True)
    manager_score = Column(Numeric(5, 2), nullable=True)
    final_score = Column(Numeric(5, 2), nullable=True)
    final_rating = Column(Enum(FinalRating), nullable=True)
    increment_recommendation = Column(Numeric(5, 2), nullable=True)
    promotion_recommendation = Column(Boolean, default=False)
    self_submitted_at = Column(DateTime, nullable=True)
    manager_reviewed_at = Column(DateTime, nullable=True)
    hr_reviewed_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    hr_notes = Column(Text, nullable=True)
    calibration_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    period = relationship("AppraisalPeriod", back_populates="records")
    template = relationship("AppraisalTemplate", back_populates="records")
    kpi_lines = relationship("AppraisalKPILine", back_populates="appraisal", cascade="all, delete-orphan")
    competency_lines = relationship("AppraisalCompetencyLine", back_populates="appraisal", cascade="all, delete-orphan")
    development_plans = relationship("AppraisalDevelopmentPlan", back_populates="appraisal", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("appraisal_period_id", "employee_id", name="uq_appraisal_period_employee"),
    )


class AppraisalKPILine(Base):
    __tablename__ = "appraisal_kpi_lines"

    kpi_line_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appraisal_id = Column(UUID(as_uuid=True), ForeignKey("appraisal_records.appraisal_id"), nullable=False)
    kpi_name = Column(String(300), nullable=False)
    kpi_description = Column(Text, nullable=True)
    target_value = Column(Numeric(15, 4), nullable=True)
    actual_value = Column(Numeric(15, 4), nullable=True)
    unit = Column(String(50), nullable=True)
    weight_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    self_score = Column(Numeric(5, 2), nullable=True)
    manager_score = Column(Numeric(5, 2), nullable=True)
    final_score = Column(Numeric(5, 2), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appraisal = relationship("AppraisalRecord", back_populates="kpi_lines")


class AppraisalCompetencyLine(Base):
    __tablename__ = "appraisal_competency_lines"

    competency_line_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appraisal_id = Column(UUID(as_uuid=True), ForeignKey("appraisal_records.appraisal_id"), nullable=False)
    competency_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    weight_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    self_rating = Column(Numeric(3, 1), nullable=True)
    manager_rating = Column(Numeric(3, 1), nullable=True)
    final_rating = Column(Numeric(3, 1), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appraisal = relationship("AppraisalRecord", back_populates="competency_lines")


class AppraisalDevelopmentPlan(Base):
    __tablename__ = "appraisal_development_plans"

    development_plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appraisal_id = Column(UUID(as_uuid=True), ForeignKey("appraisal_records.appraisal_id"), nullable=False)
    employee_id = Column(String(100), nullable=False)
    goal_title = Column(String(300), nullable=False)
    action_plan = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    status = Column(Enum(DevelopmentPlanStatus), default=DevelopmentPlanStatus.OPEN, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appraisal = relationship("AppraisalRecord", back_populates="development_plans")


class APAIRecommendation(Base):
    __tablename__ = "ap_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(APAIAgentType), nullable=False)
    status = Column(Enum(APAIRecStatus), default=APAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    appraisal_id = Column(UUID(as_uuid=True), nullable=True)
    employee_id = Column(String(100), nullable=True)
    department_id = Column(String(100), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
