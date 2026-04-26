from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date,
    ForeignKey, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class TPMPeriodType(str, enum.Enum):
    ANNUAL       = "ANNUAL"
    QUARTERLY    = "QUARTERLY"
    MONTHLY      = "MONTHLY"
    EVENT_BASED  = "EVENT_BASED"


class TPMPlanStatus(str, enum.Enum):
    DRAFT        = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    ACTIVE       = "ACTIVE"
    CLOSED       = "CLOSED"
    ARCHIVED     = "ARCHIVED"


class TPMPromotionType(str, enum.Enum):
    DISCOUNT     = "DISCOUNT"
    FREE_GOODS   = "FREE_GOODS"
    VISIBILITY   = "VISIBILITY"
    DISPLAY      = "DISPLAY"
    REBATE       = "REBATE"
    OFF_INVOICE  = "OFF_INVOICE"
    BILL_BACK    = "BILL_BACK"
    LISTING_FEE  = "LISTING_FEE"
    BUNDLE       = "BUNDLE"
    EVENT        = "EVENT"
    CUSTOM       = "CUSTOM"


class TPMObjectiveType(str, enum.Enum):
    VOLUME              = "VOLUME"
    MARKET_SHARE        = "MARKET_SHARE"
    DISTRIBUTION_GAIN   = "DISTRIBUTION_GAIN"
    STOCK_CLEARANCE     = "STOCK_CLEARANCE"
    LAUNCH_SUPPORT      = "LAUNCH_SUPPORT"
    RETENTION           = "RETENTION"
    SEASONAL_PUSH       = "SEASONAL_PUSH"
    CHANNEL_ACTIVATION  = "CHANNEL_ACTIVATION"


class TPMPromotionStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    PROPOSED   = "PROPOSED"
    APPROVED   = "APPROVED"
    ACTIVE     = "ACTIVE"
    COMPLETED  = "COMPLETED"
    CANCELLED  = "CANCELLED"
    SETTLED    = "SETTLED"
    ARCHIVED   = "ARCHIVED"


class TPMBudgetType(str, enum.Enum):
    DISCOUNT_BUDGET    = "DISCOUNT_BUDGET"
    FREE_GOODS_BUDGET  = "FREE_GOODS_BUDGET"
    DISPLAY_BUDGET     = "DISPLAY_BUDGET"
    REBATE_BUDGET      = "REBATE_BUDGET"
    LISTING_FEE_BUDGET = "LISTING_FEE_BUDGET"
    MIXED              = "MIXED"


class TPMBaselineMethod(str, enum.Enum):
    PRIOR_PERIOD         = "PRIOR_PERIOD"
    SAME_PERIOD_LAST_YEAR = "SAME_PERIOD_LAST_YEAR"
    ROLLING_AVERAGE      = "ROLLING_AVERAGE"
    MANUAL               = "MANUAL"


class TPMClaimantType(str, enum.Enum):
    CUSTOMER    = "CUSTOMER"
    DISTRIBUTOR = "DISTRIBUTOR"
    INTERNAL    = "INTERNAL"


class TPMClaimType(str, enum.Enum):
    REBATE                      = "REBATE"
    DEDUCTION                   = "DEDUCTION"
    BILL_BACK                   = "BILL_BACK"
    DISPLAY_FEE                 = "DISPLAY_FEE"
    LISTING_FEE                 = "LISTING_FEE"
    FREE_GOODS_ADJUSTMENT       = "FREE_GOODS_ADJUSTMENT"
    OFF_INVOICE_RECONCILIATION  = "OFF_INVOICE_RECONCILIATION"
    CUSTOM                      = "CUSTOM"


class TPMClaimStatus(str, enum.Enum):
    DRAFT              = "DRAFT"
    SUBMITTED          = "SUBMITTED"
    UNDER_REVIEW       = "UNDER_REVIEW"
    APPROVED           = "APPROVED"
    PARTIALLY_SETTLED  = "PARTIALLY_SETTLED"
    SETTLED            = "SETTLED"
    REJECTED           = "REJECTED"
    CANCELLED          = "CANCELLED"


class TPMAIAgentType(str, enum.Enum):
    ROI_ANALYST         = "ROI_ANALYST"
    BUDGET_RISK_MONITOR = "BUDGET_RISK_MONITOR"
    PLANNER_ASSISTANT   = "PLANNER_ASSISTANT"


class TPMAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class TPMPlan(Base, TimestampMixin):
    __tablename__ = "tpm_plans"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_code            = Column(String(50), unique=True, nullable=False)
    plan_name            = Column(String(200), nullable=False)
    fiscal_year          = Column(Integer, nullable=False)
    period_type          = Column(Enum(TPMPeriodType), nullable=False, default=TPMPeriodType.ANNUAL)
    plan_start_date      = Column(Date, nullable=False)
    plan_end_date        = Column(Date, nullable=False)
    status               = Column(Enum(TPMPlanStatus), nullable=False, default=TPMPlanStatus.DRAFT)
    owner_user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    total_planned_budget = Column(Numeric(18, 2), default=0)
    total_approved_budget= Column(Numeric(18, 2), default=0)
    total_actual_spend   = Column(Numeric(18, 2), default=0)
    notes                = Column(Text)

    promotions = relationship("TPMPromotion", back_populates="plan", cascade="all, delete-orphan")


class TPMPromotion(Base, TimestampMixin):
    __tablename__ = "tpm_promotions"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promotion_code       = Column(String(50), unique=True, nullable=False)
    promotion_name       = Column(String(200), nullable=False)
    tpm_plan_id          = Column(UUID(as_uuid=True), ForeignKey("tpm_plans.id"), nullable=True)
    linked_scheme_id     = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=True)
    promotion_type       = Column(Enum(TPMPromotionType), nullable=False)
    objective_type       = Column(Enum(TPMObjectiveType), nullable=False)
    status               = Column(Enum(TPMPromotionStatus), nullable=False, default=TPMPromotionStatus.DRAFT)
    valid_from           = Column(Date, nullable=False)
    valid_to             = Column(Date, nullable=False)
    brand_id             = Column(String(100))
    category_id          = Column(String(100))
    channel_id           = Column(String(100))
    region_id            = Column(String(100))
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    distributor_group_id = Column(String(100))
    approved_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes                = Column(Text)

    plan          = relationship("TPMPlan", back_populates="promotions")
    budget_lines  = relationship("TPMBudgetLine", back_populates="promotion", cascade="all, delete-orphan")
    expected_perf = relationship("TPMExpectedPerf", back_populates="promotion", uselist=False, cascade="all, delete-orphan")
    actual_perf   = relationship("TPMActualPerf", back_populates="promotion", uselist=False, cascade="all, delete-orphan")
    claims        = relationship("TPMClaim", back_populates="promotion")


class TPMBudgetLine(Base, TimestampMixin):
    __tablename__ = "tpm_budget_lines"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tpm_promotion_id        = Column(UUID(as_uuid=True), ForeignKey("tpm_promotions.id"), nullable=False)
    budget_type             = Column(Enum(TPMBudgetType), nullable=False)
    planned_spend_amount    = Column(Numeric(18, 2), default=0)
    approved_spend_amount   = Column(Numeric(18, 2), default=0)
    actual_spend_amount     = Column(Numeric(18, 2), default=0)
    accrued_spend_amount    = Column(Numeric(18, 2), default=0)
    settled_spend_amount    = Column(Numeric(18, 2), default=0)
    remaining_budget_amount = Column(Numeric(18, 2), default=0)
    cost_center_id          = Column(UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True)
    dimension_value_id      = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=True)
    notes                   = Column(Text)

    promotion = relationship("TPMPromotion", back_populates="budget_lines")


class TPMExpectedPerf(Base, TimestampMixin):
    __tablename__ = "tpm_expected_perf"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tpm_promotion_id     = Column(UUID(as_uuid=True), ForeignKey("tpm_promotions.id"), nullable=False, unique=True)
    baseline_volume      = Column(Numeric(18, 3), default=0)
    target_volume        = Column(Numeric(18, 3), default=0)
    expected_uplift_qty  = Column(Numeric(18, 3), default=0)
    expected_uplift_pct  = Column(Numeric(10, 2), default=0)
    expected_revenue     = Column(Numeric(18, 2), default=0)
    expected_margin_impact = Column(Numeric(18, 2), default=0)
    expected_roi_pct     = Column(Numeric(10, 2), default=0)
    baseline_method      = Column(Enum(TPMBaselineMethod), nullable=False, default=TPMBaselineMethod.PRIOR_PERIOD)
    assumptions          = Column(Text)
    notes                = Column(Text)

    promotion = relationship("TPMPromotion", back_populates="expected_perf")


class TPMActualPerf(Base, TimestampMixin):
    __tablename__ = "tpm_actual_perf"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tpm_promotion_id     = Column(UUID(as_uuid=True), ForeignKey("tpm_promotions.id"), nullable=False, unique=True)
    actual_volume        = Column(Numeric(18, 3), default=0)
    actual_uplift_qty    = Column(Numeric(18, 3), default=0)
    actual_uplift_pct    = Column(Numeric(10, 2), default=0)
    actual_revenue       = Column(Numeric(18, 2), default=0)
    actual_margin_impact = Column(Numeric(18, 2), default=0)
    actual_spend         = Column(Numeric(18, 2), default=0)
    actual_roi_pct       = Column(Numeric(10, 2), default=0)
    post_event_notes     = Column(Text)

    promotion = relationship("TPMPromotion", back_populates="actual_perf")


class TPMClaim(Base, TimestampMixin):
    __tablename__ = "tpm_claims"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_no              = Column(String(50), unique=True, nullable=False)
    tpm_promotion_id      = Column(UUID(as_uuid=True), ForeignKey("tpm_promotions.id"), nullable=False)
    claimant_type         = Column(Enum(TPMClaimantType), nullable=False)
    claimant_id           = Column(UUID(as_uuid=True), nullable=True)
    claim_date            = Column(Date, nullable=False)
    claim_type            = Column(Enum(TPMClaimType), nullable=False)
    claimed_amount        = Column(Numeric(18, 2), default=0)
    approved_amount       = Column(Numeric(18, 2), default=0)
    rejected_amount       = Column(Numeric(18, 2), default=0)
    settled_amount        = Column(Numeric(18, 2), default=0)
    status                = Column(Enum(TPMClaimStatus), nullable=False, default=TPMClaimStatus.DRAFT)
    reference_document_no = Column(String(100))
    reviewer_notes        = Column(Text)
    notes                 = Column(Text)

    promotion  = relationship("TPMPromotion", back_populates="claims")
    claim_lines = relationship("TPMClaimLine", back_populates="claim", cascade="all, delete-orphan")


class TPMClaimLine(Base, TimestampMixin):
    __tablename__ = "tpm_claim_lines"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tpm_claim_id         = Column(UUID(as_uuid=True), ForeignKey("tpm_claims.id"), nullable=False)
    source_order_id      = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    source_scheme_id     = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=True)
    item_id              = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    quantity_basis       = Column(Numeric(18, 3))
    rate_basis           = Column(Numeric(18, 4))
    claimed_amount       = Column(Numeric(18, 2), default=0)
    approved_amount      = Column(Numeric(18, 2), default=0)
    supporting_doc_ref   = Column(String(200))
    notes                = Column(Text)

    claim = relationship("TPMClaim", back_populates="claim_lines")


class TPMAIRecommendation(Base, TimestampMixin):
    __tablename__ = "tpm_ai_recommendations"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type        = Column(Enum(TPMAIAgentType), nullable=False)
    tpm_promotion_id  = Column(UUID(as_uuid=True), ForeignKey("tpm_promotions.id"), nullable=True)
    tpm_claim_id      = Column(UUID(as_uuid=True), ForeignKey("tpm_claims.id"), nullable=True)
    title             = Column(String(300), nullable=False)
    detail            = Column(Text)
    severity          = Column(String(20))
    status            = Column(Enum(TPMAIRecStatus), nullable=False, default=TPMAIRecStatus.PENDING)
    actioned_notes    = Column(Text)
