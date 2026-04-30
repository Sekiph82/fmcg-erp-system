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


class EmploymentType(str, PyEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"


class RequisitionStatus(str, PyEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PostingChannel(str, PyEnum):
    INTERNAL = "internal"
    WEBSITE = "website"
    JOB_PORTAL = "job_portal"
    AGENCY = "agency"
    REFERRAL = "referral"


class PostingStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


class CandidateSource(str, PyEnum):
    PORTAL = "portal"
    REFERRAL = "referral"
    AGENCY = "agency"
    MANUAL = "manual"
    LINKEDIN = "linkedin"
    JOB_PORTAL = "job_portal"


class PipelineStatus(str, PyEnum):
    ACTIVE = "active"
    MOVED = "moved"
    REJECTED = "rejected"
    HIRED = "hired"
    ON_HOLD = "on_hold"
    WITHDRAWN = "withdrawn"


class InterviewType(str, PyEnum):
    ONLINE = "online"
    ONSITE = "onsite"
    PHONE = "phone"
    PANEL = "panel"


class InterviewDecision(str, PyEnum):
    PASS = "pass"
    FAIL = "fail"
    HOLD = "hold"
    PENDING = "pending"


class OfferStatus(str, PyEnum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEGOTIATING = "negotiating"
    EXPIRED = "expired"


class StageType(str, PyEnum):
    ACTIVE = "active"
    FINAL_HIRE = "final_hire"
    FINAL_REJECT = "final_reject"


class RTAIAgentType(str, PyEnum):
    CANDIDATE_MATCHER = "candidate_matcher"
    HIRING_RISK_DETECTOR = "hiring_risk_detector"
    PIPELINE_OPTIMIZER = "pipeline_optimizer"


class RTAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


# ── Recruitment Pipeline Stage ────────────────────────────────────────────────

class RecruitmentStage(Base):
    __tablename__ = "recruitment_stages"

    stage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_code = Column(String(50), unique=True, nullable=False)
    stage_name = Column(String(100), nullable=False)
    sequence = Column(Integer, nullable=False, default=1)
    stage_type = Column(Enum(StageType), default=StageType.ACTIVE)
    active_flag = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipelines = relationship("CandidatePipeline", back_populates="stage")
    interviews = relationship("Interview", back_populates="stage")
    history = relationship("CandidatePipelineHistory", back_populates="stage")


# ── Job Requisition ───────────────────────────────────────────────────────────

class JobRequisition(Base):
    __tablename__ = "job_requisitions"

    requisition_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requisition_code = Column(String(30), unique=True, nullable=False)
    job_title = Column(String(150), nullable=False)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    location = Column(String(150), nullable=True)
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME)
    headcount = Column(Integer, default=1)
    filled_count = Column(Integer, default=0)
    requested_by = Column(UUID(as_uuid=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    status = Column(Enum(RequisitionStatus), default=RequisitionStatus.DRAFT)
    opening_date = Column(Date, nullable=True)
    closing_date = Column(Date, nullable=True)
    job_description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    salary_min = Column(Numeric(14, 2), nullable=True)
    salary_max = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(3), default="KES")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    postings = relationship("JobPosting", back_populates="requisition")
    pipelines = relationship("CandidatePipeline", back_populates="requisition")
    interviews = relationship("Interview", back_populates="requisition")
    offers = relationship("Offer", back_populates="requisition")


# ── Job Posting ───────────────────────────────────────────────────────────────

class JobPosting(Base):
    __tablename__ = "job_postings"

    posting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requisition_id = Column(UUID(as_uuid=True), ForeignKey("job_requisitions.requisition_id"), nullable=False)
    posting_channel = Column(Enum(PostingChannel), default=PostingChannel.WEBSITE)
    posting_url = Column(String(500), nullable=True)
    publish_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(Enum(PostingStatus), default=PostingStatus.DRAFT)
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requisition = relationship("JobRequisition", back_populates="postings")


# ── Candidate ─────────────────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_code = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    cv_attachment = Column(String(500), nullable=True)
    source = Column(Enum(CandidateSource), default=CandidateSource.MANUAL)
    current_employer = Column(String(150), nullable=True)
    current_title = Column(String(150), nullable=True)
    years_experience = Column(Integer, nullable=True)
    education_level = Column(String(100), nullable=True)
    skills_tags = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    blacklisted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pipelines = relationship("CandidatePipeline", back_populates="candidate")
    interviews = relationship("Interview", back_populates="candidate")
    offers = relationship("Offer", back_populates="candidate")


# ── Candidate Pipeline ────────────────────────────────────────────────────────

class CandidatePipeline(Base):
    __tablename__ = "candidate_pipelines"

    pipeline_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.candidate_id"), nullable=False)
    requisition_id = Column(UUID(as_uuid=True), ForeignKey("job_requisitions.requisition_id"), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("recruitment_stages.stage_id"), nullable=False)
    assigned_recruiter = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(PipelineStatus), default=PipelineStatus.ACTIVE)
    application_date = Column(Date, nullable=True)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    screening_score = Column(Integer, nullable=True)
    overall_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("candidate_id", "requisition_id", name="uq_candidate_requisition"),)

    candidate = relationship("Candidate", back_populates="pipelines")
    requisition = relationship("JobRequisition", back_populates="pipelines")
    stage = relationship("RecruitmentStage", back_populates="pipelines")
    history = relationship("CandidatePipelineHistory", back_populates="pipeline", cascade="all, delete-orphan")


# ── Candidate Pipeline History ────────────────────────────────────────────────

class CandidatePipelineHistory(Base):
    __tablename__ = "candidate_pipeline_history"

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("candidate_pipelines.pipeline_id"), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("recruitment_stages.stage_id"), nullable=False)
    moved_by = Column(UUID(as_uuid=True), nullable=True)
    moved_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    pipeline = relationship("CandidatePipeline", back_populates="history")
    stage = relationship("RecruitmentStage", back_populates="history")


# ── Interview ─────────────────────────────────────────────────────────────────

class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.candidate_id"), nullable=False)
    requisition_id = Column(UUID(as_uuid=True), ForeignKey("job_requisitions.requisition_id"), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("recruitment_stages.stage_id"), nullable=True)
    interviewer_id = Column(UUID(as_uuid=True), nullable=True)
    interview_date = Column(DateTime, nullable=False)
    interview_type = Column(Enum(InterviewType), default=InterviewType.ONSITE)
    location_or_link = Column(String(500), nullable=True)
    feedback = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    technical_score = Column(Integer, nullable=True)
    cultural_score = Column(Integer, nullable=True)
    decision = Column(Enum(InterviewDecision), default=InterviewDecision.PENDING)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interviews")
    requisition = relationship("JobRequisition", back_populates="interviews")
    stage = relationship("RecruitmentStage", back_populates="interviews")


# ── Offer ─────────────────────────────────────────────────────────────────────

class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_code = Column(String(30), unique=True, nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.candidate_id"), nullable=False)
    requisition_id = Column(UUID(as_uuid=True), ForeignKey("job_requisitions.requisition_id"), nullable=False)
    offer_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    salary_offer = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="KES")
    joining_date = Column(Date, nullable=True)
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME)
    status = Column(Enum(OfferStatus), default=OfferStatus.DRAFT)
    sent_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    negotiation_notes = Column(Text, nullable=True)
    employee_id_created = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="offers")
    requisition = relationship("JobRequisition", back_populates="offers")


# ── AI Recommendation ─────────────────────────────────────────────────────────

class RTAIRecommendation(Base):
    __tablename__ = "rt_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(RTAIAgentType), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    ref_requisition_id = Column(UUID(as_uuid=True), nullable=True)
    ref_candidate_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(RTAIRecStatus), default=RTAIRecStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime, nullable=True)
    actioned_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
