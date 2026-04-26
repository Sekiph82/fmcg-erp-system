from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class RecurrenceType(str, enum.Enum):
    WEEKLY            = "WEEKLY"
    BIWEEKLY          = "BIWEEKLY"
    MONTHLY_DATE      = "MONTHLY_DATE"   # fixed day-of-month
    MONTHLY_DAY       = "MONTHLY_DAY"    # e.g. first Monday
    CUSTOM_DAYS       = "CUSTOM_DAYS"    # every N days
    ROUTE_BASED       = "ROUTE_BASED"    # tied to delivery route schedule


class SubscriptionStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    ACTIVE    = "ACTIVE"
    PAUSED    = "PAUSED"
    EXPIRED   = "EXPIRED"
    CANCELLED = "CANCELLED"
    ARCHIVED  = "ARCHIVED"


class GenerationMode(str, enum.Enum):
    DRAFT_ONLY         = "DRAFT_ONLY"
    APPROVAL_REQUIRED  = "APPROVAL_REQUIRED"
    AUTO_CONFIRM       = "AUTO_CONFIRM"


class PriceSource(str, enum.Enum):
    CURRENT_PRICE_LIST = "CURRENT_PRICE_LIST"
    FIXED_CONTRACT     = "FIXED_CONTRACT"
    PROMOTION          = "PROMOTION"


class GenerationStatus(str, enum.Enum):
    GENERATED        = "GENERATED"
    SKIPPED          = "SKIPPED"
    FAILED           = "FAILED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CANCELLED        = "CANCELLED"


class PauseSkipAction(str, enum.Enum):
    PAUSE         = "PAUSE"
    SKIP_ONE_CYCLE = "SKIP_ONE_CYCLE"
    RESUME        = "RESUME"
    CANCEL        = "CANCEL"


class SubAIAgentType(str, enum.Enum):
    DEMAND_PREDICTOR       = "DEMAND_PREDICTOR"
    RISK_MONITOR           = "RISK_MONITOR"
    OPTIMIZATION_ASSISTANT = "OPTIMIZATION_ASSISTANT"


class SubAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class SubscriptionTemplate(Base, TimestampMixin):
    __tablename__ = "subscription_templates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code    = Column(String(50), unique=True, index=True, nullable=False)
    template_name    = Column(String(200), nullable=False)

    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    distributor_id   = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True)
    price_list_id    = Column(UUID(as_uuid=True), nullable=True)   # → pl_headers.id
    contract_id      = Column(UUID(as_uuid=True), nullable=True)
    currency         = Column(String(3), default="KES")

    recurrence_type     = Column(String(50), nullable=False)
    recurrence_interval = Column(Integer, nullable=True)           # for CUSTOM_DAYS
    recurrence_day_of_month = Column(Integer, nullable=True)       # for MONTHLY_DATE
    recurrence_weekday  = Column(Integer, nullable=True)           # 0=Mon for MONTHLY_DAY
    recurrence_week_ordinal = Column(Integer, nullable=True)       # 1=first, -1=last

    start_date             = Column(Date, nullable=False)
    end_date               = Column(Date, nullable=True)
    next_generation_date   = Column(Date, nullable=True)
    last_generation_date   = Column(Date, nullable=True)

    status          = Column(String(50), nullable=False, default=SubscriptionStatus.DRAFT.value)
    generation_mode = Column(String(50), nullable=False, default=GenerationMode.DRAFT_ONLY.value)

    delivery_address_id = Column(UUID(as_uuid=True), nullable=True)
    route_id            = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id"), nullable=True)
    payment_terms_id    = Column(UUID(as_uuid=True), nullable=True)

    allow_promotion_eval = Column(Boolean, default=True)
    price_change_threshold_pct = Column(Numeric(5, 2), nullable=True)  # alert if > N%

    notes      = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    lines           = relationship("SubscriptionLine", back_populates="template", cascade="all, delete-orphan")
    generation_logs = relationship("SubscriptionGenerationLog", back_populates="template", cascade="all, delete-orphan")
    pause_skips     = relationship("SubscriptionPauseSkip", back_populates="template", cascade="all, delete-orphan")
    ai_recs         = relationship("SubAIRecommendation", back_populates="template")


class SubscriptionLine(Base, TimestampMixin):
    __tablename__ = "subscription_lines"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id          = Column(UUID(as_uuid=True), ForeignKey("subscription_templates.id", ondelete="CASCADE"), nullable=False)
    item_id              = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    item_variant_id      = Column(UUID(as_uuid=True), nullable=True)
    uom                  = Column(String(50), nullable=False)

    quantity             = Column(Numeric(14, 3), nullable=False)
    min_quantity         = Column(Numeric(14, 3), nullable=True)
    max_quantity         = Column(Numeric(14, 3), nullable=True)
    allow_quantity_change = Column(Boolean, default=False)

    price_source         = Column(String(50), nullable=False, default=PriceSource.CURRENT_PRICE_LIST.value)
    fixed_price          = Column(Numeric(14, 4), nullable=True)
    active_flag          = Column(Boolean, default=True)
    sort_order           = Column(Integer, default=0)
    notes                = Column(Text, nullable=True)

    template = relationship("SubscriptionTemplate", back_populates="lines")


class SubscriptionGenerationLog(Base, TimestampMixin):
    __tablename__ = "subscription_generation_logs"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id             = Column(UUID(as_uuid=True), ForeignKey("subscription_templates.id", ondelete="CASCADE"), nullable=False)
    generated_so_id         = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)

    scheduled_date          = Column(Date, nullable=False)
    actual_generation_date  = Column(DateTime, nullable=True)

    generation_status       = Column(String(50), nullable=False)
    failure_reason          = Column(Text, nullable=True)
    validation_warnings     = Column(JSON, nullable=True)

    generated_by_system     = Column(Boolean, default=True)
    generated_by_user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_by             = Column(UUID(as_uuid=True), nullable=True)
    notes                   = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("template_id", "scheduled_date", name="uq_sub_gen_template_date"),
    )

    template = relationship("SubscriptionTemplate", back_populates="generation_logs")


class SubscriptionPauseSkip(Base, TimestampMixin):
    __tablename__ = "subscription_pause_skips"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("subscription_templates.id", ondelete="CASCADE"), nullable=False)

    action_type    = Column(String(50), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date, nullable=True)

    reason        = Column(Text, nullable=True)
    requested_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by   = Column(UUID(as_uuid=True), nullable=True)
    portal_request = Column(Boolean, default=False)
    notes         = Column(Text, nullable=True)

    template = relationship("SubscriptionTemplate", back_populates="pause_skips")


class SubAIRecommendation(Base, TimestampMixin):
    __tablename__ = "subscription_ai_recommendations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type   = Column(String(50), nullable=False)
    status       = Column(String(50), default=SubAIRecStatus.PENDING.value)
    severity     = Column(String(20), default="INFO")

    title        = Column(String(200), nullable=False)
    body         = Column(Text, nullable=False)
    data         = Column(JSON, nullable=True)

    template_id  = Column(UUID(as_uuid=True), ForeignKey("subscription_templates.id"), nullable=True)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    template = relationship("SubscriptionTemplate", back_populates="ai_recs")
