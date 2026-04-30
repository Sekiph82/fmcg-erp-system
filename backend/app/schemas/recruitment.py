from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.recruitment import (
    EmploymentType, RequisitionStatus, PostingChannel, PostingStatus,
    CandidateSource, PipelineStatus, InterviewType, InterviewDecision,
    OfferStatus, StageType, RTAIAgentType, RTAIRecStatus,
)


# ── Stage ─────────────────────────────────────────────────────────────────────

class RecruitmentStageCreate(BaseModel):
    stage_code: str
    stage_name: str
    sequence: int = 1
    stage_type: StageType = StageType.ACTIVE


class RecruitmentStageRead(RecruitmentStageCreate):
    stage_id: UUID
    active_flag: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Requisition ───────────────────────────────────────────────────────────────

class JobRequisitionCreate(BaseModel):
    job_title: str
    department_id: Optional[UUID] = None
    location: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    headcount: int = 1
    requested_by: Optional[UUID] = None
    opening_date: Optional[date] = None
    closing_date: Optional[date] = None
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str = "KES"
    notes: Optional[str] = None


class JobRequisitionRead(JobRequisitionCreate):
    requisition_id: UUID
    requisition_code: str
    filled_count: int
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    status: RequisitionStatus
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class JobRequisitionApprove(BaseModel):
    approver_id: UUID
    notes: Optional[str] = None


# ── Job Posting ───────────────────────────────────────────────────────────────

class JobPostingCreate(BaseModel):
    requisition_id: UUID
    posting_channel: PostingChannel = PostingChannel.WEBSITE
    posting_url: Optional[str] = None
    publish_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class JobPostingRead(JobPostingCreate):
    posting_id: UUID
    status: PostingStatus
    views_count: int
    applications_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Candidate ─────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    cv_attachment: Optional[str] = None
    source: CandidateSource = CandidateSource.MANUAL
    current_employer: Optional[str] = None
    current_title: Optional[str] = None
    years_experience: Optional[int] = None
    education_level: Optional[str] = None
    skills_tags: Optional[str] = None
    notes: Optional[str] = None


class CandidateRead(CandidateCreate):
    candidate_id: UUID
    candidate_code: str
    blacklisted: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineCreate(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    stage_id: UUID
    assigned_recruiter: Optional[UUID] = None
    application_date: Optional[date] = None
    screening_score: Optional[int] = None
    notes: Optional[str] = None


class PipelineMoveStage(BaseModel):
    stage_id: UUID
    moved_by: Optional[UUID] = None
    notes: Optional[str] = None


class PipelineRead(BaseModel):
    pipeline_id: UUID
    candidate_id: UUID
    requisition_id: UUID
    stage_id: UUID
    assigned_recruiter: Optional[UUID]
    status: PipelineStatus
    application_date: Optional[date]
    last_update: datetime
    screening_score: Optional[int]
    overall_score: Optional[int]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class PipelineHistoryRead(BaseModel):
    history_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    moved_by: Optional[UUID]
    moved_at: datetime
    notes: Optional[str]
    model_config = {"from_attributes": True}


# ── Interview ─────────────────────────────────────────────────────────────────

class InterviewCreate(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    stage_id: Optional[UUID] = None
    interviewer_id: Optional[UUID] = None
    interview_date: datetime
    interview_type: InterviewType = InterviewType.ONSITE
    location_or_link: Optional[str] = None
    notes: Optional[str] = None


class InterviewRead(InterviewCreate):
    interview_id: UUID
    feedback: Optional[str]
    score: Optional[int]
    technical_score: Optional[int]
    cultural_score: Optional[int]
    decision: InterviewDecision
    completed_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class InterviewFeedback(BaseModel):
    feedback: str
    score: Optional[int] = None
    technical_score: Optional[int] = None
    cultural_score: Optional[int] = None
    decision: InterviewDecision


# ── Offer ─────────────────────────────────────────────────────────────────────

class OfferCreate(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    offer_date: date
    expiry_date: Optional[date] = None
    salary_offer: Decimal
    currency: str = "KES"
    joining_date: Optional[date] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    negotiation_notes: Optional[str] = None
    notes: Optional[str] = None


class OfferRead(OfferCreate):
    offer_id: UUID
    offer_code: str
    status: OfferStatus
    sent_at: Optional[datetime]
    responded_at: Optional[datetime]
    rejection_reason: Optional[str]
    employee_id_created: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class OfferRespond(BaseModel):
    status: OfferStatus
    rejection_reason: Optional[str] = None
    negotiation_notes: Optional[str] = None
    joining_date: Optional[date] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class RecruitmentDashboardResponse(BaseModel):
    open_requisitions: int
    total_candidates: int
    active_pipelines: int
    interviews_this_week: int
    pending_offers: int
    hires_this_month: int
    avg_time_to_hire_days: float
    ai_alerts: int


# ── AI ────────────────────────────────────────────────────────────────────────

class RTAIRecRead(BaseModel):
    rec_id: UUID
    agent_type: RTAIAgentType
    subject: str
    body: str
    ref_requisition_id: Optional[UUID]
    ref_candidate_id: Optional[UUID]
    status: RTAIRecStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class RTAIRecAck(BaseModel):
    status: RTAIRecStatus
    notes: Optional[str] = None
