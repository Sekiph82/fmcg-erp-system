from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class CRMRecordType(str, enum.Enum):
    LEAD        = "LEAD"
    OPPORTUNITY = "OPPORTUNITY"


class CRMAccountType(str, enum.Enum):
    PROSPECT         = "PROSPECT"
    CUSTOMER         = "CUSTOMER"
    DISTRIBUTOR      = "DISTRIBUTOR"
    RETAILER         = "RETAILER"
    MODERN_TRADE     = "MODERN_TRADE"
    INSTITUTIONAL    = "INSTITUTIONAL"
    SUPPLIER_XSELL   = "SUPPLIER_XSELL"
    OTHER            = "OTHER"


class CRMSourceType(str, enum.Enum):
    WEBSITE     = "WEBSITE"
    REFERRAL    = "REFERRAL"
    FIELD_SALES = "FIELD_SALES"
    EVENT       = "EVENT"
    OUTBOUND    = "OUTBOUND"
    INBOUND     = "INBOUND"
    CAMPAIGN    = "CAMPAIGN"
    MANUAL      = "MANUAL"
    IMPORT      = "IMPORT"


class CRMStageType(str, enum.Enum):
    LEAD        = "LEAD"
    OPPORTUNITY = "OPPORTUNITY"
    TERMINAL    = "TERMINAL"
    NURTURING   = "NURTURING"


class CRMTemperature(str, enum.Enum):
    COLD = "COLD"
    WARM = "WARM"
    HOT  = "HOT"


class CRMStatus(str, enum.Enum):
    OPEN     = "OPEN"
    WON      = "WON"
    LOST     = "LOST"
    ON_HOLD  = "ON_HOLD"
    ARCHIVED = "ARCHIVED"


class CRMActivityType(str, enum.Enum):
    CALL              = "CALL"
    EMAIL             = "EMAIL"
    MEETING           = "MEETING"
    WHATSAPP          = "WHATSAPP"
    VISIT             = "VISIT"
    TASK              = "TASK"
    NOTE              = "NOTE"
    DEMO              = "DEMO"
    SAMPLE_SENT       = "SAMPLE_SENT"
    QUOTATION_SENT    = "QUOTATION_SENT"
    NEGOTIATION       = "NEGOTIATION"
    COMPLAINT_FOLLOWUP = "COMPLAINT_FOLLOWUP"
    OTHER             = "OTHER"


class CRMActivityResult(str, enum.Enum):
    PLANNED     = "PLANNED"
    COMPLETED   = "COMPLETED"
    NO_RESPONSE = "NO_RESPONSE"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED   = "CANCELLED"


class CRMLossReason(str, enum.Enum):
    PRICE_TOO_HIGH        = "PRICE_TOO_HIGH"
    COMPETITOR_RELATION   = "COMPETITOR_RELATION"
    PRODUCT_MISMATCH      = "PRODUCT_MISMATCH"
    TIMELINE_ISSUE        = "TIMELINE_ISSUE"
    NO_BUDGET             = "NO_BUDGET"
    NO_RESPONSE           = "NO_RESPONSE"
    COMPETITOR_PROMO      = "COMPETITOR_PROMO"
    DISTRIBUTOR_CONFLICT  = "DISTRIBUTOR_CONFLICT"
    CAPACITY_SUPPLY       = "CAPACITY_SUPPLY"
    INTERNAL_FOLLOWUP     = "INTERNAL_FOLLOWUP"
    OTHER                 = "OTHER"


class CRMWinReason(str, enum.Enum):
    BETTER_PRICE       = "BETTER_PRICE"
    BETTER_PRODUCT_FIT = "BETTER_PRODUCT_FIT"
    FASTER_RESPONSE    = "FASTER_RESPONSE"
    STRONGER_RELATION  = "STRONGER_RELATION"
    AVAILABILITY       = "AVAILABILITY"
    TECHNICAL_SUPPORT  = "TECHNICAL_SUPPORT"
    PROMOTION_SUPPORT  = "PROMOTION_SUPPORT"
    OTHER              = "OTHER"


class CRMAIAgentType(str, enum.Enum):
    LEAD_PRIORITIZATION = "LEAD_PRIORITIZATION"
    PIPELINE_RISK       = "PIPELINE_RISK"
    WIN_LOSS_INSIGHT    = "WIN_LOSS_INSIGHT"


class CRMAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class CRMPipelineStage(Base, TimestampMixin):
    __tablename__ = "crm_pipeline_stages"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_code            = Column(String(50), nullable=False, unique=True)
    stage_name            = Column(String(100), nullable=False)
    stage_type            = Column(Enum(CRMStageType), nullable=False)
    default_probability   = Column(Numeric(5, 2), default=0)
    sequence_no           = Column(Integer, nullable=False, default=0)
    active_flag           = Column(Boolean, default=True)
    color_code            = Column(String(20))
    notes                 = Column(Text)

    records = relationship("CRMRecord", back_populates="stage", foreign_keys="CRMRecord.stage_id")


class CRMRecord(Base, TimestampMixin):
    __tablename__ = "crm_records"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type           = Column(Enum(CRMRecordType), nullable=False, default=CRMRecordType.LEAD)
    lead_code             = Column(String(50), unique=True)
    opportunity_code      = Column(String(50), unique=True)
    account_type          = Column(Enum(CRMAccountType), default=CRMAccountType.PROSPECT)
    company_name          = Column(String(200), nullable=False)
    contact_person_name   = Column(String(200))
    contact_email         = Column(String(200))
    contact_phone         = Column(String(50))
    alternate_contact     = Column(String(200))
    customer_id           = Column(String(50))
    distributor_id        = Column(String(50))
    source_type           = Column(Enum(CRMSourceType), default=CRMSourceType.MANUAL)
    source_detail         = Column(String(200))
    region_id             = Column(String(50))
    country_id            = Column(String(50))
    channel_id            = Column(String(50))
    industry_segment      = Column(String(100))
    assigned_rep_id       = Column(String(50))
    assigned_team_id      = Column(String(50))
    stage_id              = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id"), nullable=True)
    probability_pct       = Column(Numeric(5, 2), default=0)
    probability_override  = Column(Boolean, default=False)
    expected_close_date   = Column(Date)
    expected_revenue      = Column(Numeric(18, 2), default=0)
    expected_margin       = Column(Numeric(18, 2), default=0)
    currency              = Column(String(10), default="KES")
    lead_score            = Column(Integer, default=0)
    temperature           = Column(Enum(CRMTemperature), default=CRMTemperature.COLD)
    next_action_date      = Column(Date)
    status                = Column(Enum(CRMStatus), default=CRMStatus.OPEN)
    qualified_flag        = Column(Boolean, default=False)
    qualified_date        = Column(Date)
    converted_date        = Column(Date)
    linked_quotation_id   = Column(String(50))
    linked_order_id       = Column(String(50))
    created_by            = Column(String(50))
    updated_by            = Column(String(50))
    notes                 = Column(Text)

    stage         = relationship("CRMPipelineStage", back_populates="records", foreign_keys=[stage_id])
    interest_lines = relationship("CRMInterestLine", back_populates="record", cascade="all, delete-orphan")
    activities    = relationship("CRMActivity", back_populates="record", cascade="all, delete-orphan")
    competitors   = relationship("CRMCompetitor", back_populates="record", cascade="all, delete-orphan")
    win_loss      = relationship("CRMWinLoss", back_populates="record", uselist=False, cascade="all, delete-orphan")


class CRMInterestLine(Base, TimestampMixin):
    __tablename__ = "crm_interest_lines"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id           = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    item_id                 = Column(String(50))
    item_name               = Column(String(200))
    category_id             = Column(String(50))
    brand_id                = Column(String(50))
    expected_qty            = Column(Numeric(18, 3))
    expected_frequency      = Column(String(50))
    expected_value          = Column(Numeric(18, 2))
    competitive_brand       = Column(String(200))
    competitor_price        = Column(Numeric(18, 2))
    notes                   = Column(Text)

    record = relationship("CRMRecord", back_populates="interest_lines")


class CRMActivity(Base, TimestampMixin):
    __tablename__ = "crm_activities"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id       = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    activity_type       = Column(Enum(CRMActivityType), nullable=False)
    subject             = Column(String(300), nullable=False)
    description         = Column(Text)
    activity_datetime   = Column(DateTime)
    due_datetime        = Column(DateTime)
    completed_datetime  = Column(DateTime)
    assigned_to         = Column(String(50))
    created_by          = Column(String(50))
    result_status       = Column(Enum(CRMActivityResult), default=CRMActivityResult.PLANNED)
    outcome_code        = Column(String(100))
    next_step           = Column(Text)
    notes               = Column(Text)

    record = relationship("CRMRecord", back_populates="activities")


class CRMCompetitor(Base, TimestampMixin):
    __tablename__ = "crm_competitors"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id        = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    competitor_name      = Column(String(200), nullable=False)
    competitor_product   = Column(String(200))
    offer_type          = Column(String(100))
    competitor_price     = Column(Numeric(18, 2))
    competitor_strength  = Column(Text)
    competitor_weakness  = Column(Text)
    risk_level           = Column(String(20))
    notes                = Column(Text)

    record = relationship("CRMRecord", back_populates="competitors")


class CRMWinLoss(Base, TimestampMixin):
    __tablename__ = "crm_win_loss"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id    = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False, unique=True)
    final_status     = Column(String(10), nullable=False)
    close_date       = Column(Date)
    final_revenue    = Column(Numeric(18, 2))
    final_margin     = Column(Numeric(18, 2))
    loss_reason_code = Column(Enum(CRMLossReason))
    win_reason_code  = Column(Enum(CRMWinReason))
    competitor_name  = Column(String(200))
    narrative        = Column(Text)
    recorded_by      = Column(String(50))
    notes            = Column(Text)

    record = relationship("CRMRecord", back_populates="win_loss")


class CRMAIRecommendation(Base, TimestampMixin):
    __tablename__ = "crm_ai_recommendations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type     = Column(Enum(CRMAIAgentType), nullable=False)
    crm_record_id  = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=True)
    title          = Column(String(300), nullable=False)
    body           = Column(Text, nullable=False)
    priority       = Column(String(20))
    action_label   = Column(String(100))
    status         = Column(Enum(CRMAIRecStatus), default=CRMAIRecStatus.PENDING)
    acknowledged_by = Column(String(50))
    notes          = Column(Text)
