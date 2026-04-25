"""Promotional Schemes Auto-Apply models."""
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class SchemeStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    APPROVED  = "APPROVED"
    ACTIVE    = "ACTIVE"
    EXPIRED   = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    ARCHIVED  = "ARCHIVED"


class SchemeType(str, enum.Enum):
    BUY_X_GET_Y           = "BUY_X_GET_Y"
    PERCENT_DISCOUNT      = "PERCENT_DISCOUNT"
    FIXED_DISCOUNT        = "FIXED_DISCOUNT"
    TIERED_DISCOUNT       = "TIERED_DISCOUNT"
    QTY_BREAK_PRICE       = "QTY_BREAK_PRICE"
    SPEND_BASED           = "SPEND_BASED"
    MIX_AND_MATCH         = "MIX_AND_MATCH"
    BUNDLE                = "BUNDLE"
    FREE_GOODS_DIFF_SKU   = "FREE_GOODS_DIFF_SKU"
    CHANNEL_DEAL          = "CHANNEL_DEAL"


class TriggerBasis(str, enum.Enum):
    SKU         = "SKU"
    CATEGORY    = "CATEGORY"
    BRAND       = "BRAND"
    ORDER_TOTAL = "ORDER_TOTAL"
    QUANTITY    = "QUANTITY"
    VALUE       = "VALUE"
    MIX_SET     = "MIX_SET"


class RewardType(str, enum.Enum):
    FREE_GOODS      = "FREE_GOODS"
    PERCENT_DISCOUNT = "PERCENT_DISCOUNT"
    FIXED_DISCOUNT  = "FIXED_DISCOUNT"
    SPECIAL_PRICE   = "SPECIAL_PRICE"
    BUNDLE_PRICE    = "BUNDLE_PRICE"


class PromoApplicationType(str, enum.Enum):
    AUTO             = "AUTO"
    MANUAL_APPROVED  = "MANUAL_APPROVED"
    MANUAL_OVERRIDE  = "MANUAL_OVERRIDE"
    REJECTED         = "REJECTED"


class PromoImpactType(str, enum.Enum):
    DISCOUNT         = "DISCOUNT"
    FREE_GOODS       = "FREE_GOODS"
    SPECIAL_PRICE    = "SPECIAL_PRICE"
    ORDER_DISCOUNT   = "ORDER_DISCOUNT"
    BUNDLE_ADJUSTMENT = "BUNDLE_ADJUSTMENT"


class OverrideStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PromoAIAgentType(str, enum.Enum):
    CONFLICT_ADVISOR  = "CONFLICT_ADVISOR"
    COST_MONITOR      = "COST_MONITOR"
    UPSELL_ASSISTANT  = "UPSELL_ASSISTANT"


class PromoAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Promotional Scheme Header ──────────────────────────────────────────────────

class PromoScheme(Base, TimestampMixin):
    __tablename__ = "promo_schemes"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_code               = Column(String(50), unique=True, nullable=False)
    scheme_name               = Column(String(200), nullable=False)
    scheme_type               = Column(Enum(SchemeType), nullable=False)
    status                    = Column(Enum(SchemeStatus), default=SchemeStatus.DRAFT)
    valid_from                = Column(Date, nullable=False)
    valid_to                  = Column(Date, nullable=False)
    priority_rank             = Column(Integer, default=10)
    stackable                 = Column(Boolean, default=False)
    exclusive                 = Column(Boolean, default=False)
    requires_approval_override = Column(Boolean, default=False)
    cost_center_id            = Column(UUID(as_uuid=True), nullable=True)
    notes                     = Column(Text)
    approved_by_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    eligibility_scopes = relationship("PromoEligibility", back_populates="scheme", cascade="all, delete-orphan")
    rule_lines         = relationship("PromoRuleLine", back_populates="scheme", cascade="all, delete-orphan")
    order_applications = relationship("SalesOrderPromo", back_populates="scheme")


# ── Eligibility Scope ──────────────────────────────────────────────────────────

class PromoEligibility(Base, TimestampMixin):
    __tablename__ = "promo_eligibilities"

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id                  = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=False)
    applies_to_customer_id     = Column(UUID(as_uuid=True), nullable=True)
    applies_to_customer_group  = Column(String(100), nullable=True)
    applies_to_distributor_group = Column(String(100), nullable=True)
    applies_to_region          = Column(String(100), nullable=True)
    applies_to_channel         = Column(String(100), nullable=True)
    applies_to_sales_team      = Column(String(100), nullable=True)
    applies_to_price_list_id   = Column(UUID(as_uuid=True), nullable=True)
    applies_to_item_id         = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    applies_to_item_category   = Column(String(100), nullable=True)
    applies_to_brand           = Column(String(100), nullable=True)
    min_order_qty              = Column(Numeric(14, 3))
    min_order_value            = Column(Numeric(14, 2))
    active                     = Column(Boolean, default=True)
    notes                      = Column(Text)

    scheme = relationship("PromoScheme", back_populates="eligibility_scopes")


# ── Promotion Rule Lines ───────────────────────────────────────────────────────

class PromoRuleLine(Base, TimestampMixin):
    __tablename__ = "promo_rule_lines"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id                 = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=False)
    trigger_basis             = Column(Enum(TriggerBasis), nullable=False, default=TriggerBasis.SKU)
    trigger_item_id           = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    trigger_category          = Column(String(100))
    trigger_brand             = Column(String(100))
    min_trigger_qty           = Column(Numeric(14, 3), default=0)
    min_trigger_value         = Column(Numeric(14, 2), default=0)
    max_trigger_qty           = Column(Numeric(14, 3))
    reward_type               = Column(Enum(RewardType), nullable=False)
    reward_item_id            = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    reward_qty                = Column(Numeric(14, 3))
    reward_percent            = Column(Numeric(6, 4))
    reward_amount             = Column(Numeric(14, 2))
    reward_special_unit_price = Column(Numeric(14, 4))
    max_reward_qty            = Column(Numeric(14, 3))
    repeatable                = Column(Boolean, default=False)
    sort_order                = Column(Integer, default=1)
    notes                     = Column(Text)

    scheme       = relationship("PromoScheme", back_populates="rule_lines")
    trigger_item = relationship("Product", foreign_keys=[trigger_item_id])
    reward_item  = relationship("Product", foreign_keys=[reward_item_id])


# ── Tiered Discount Lines ──────────────────────────────────────────────────────

class PromoTierLine(Base, TimestampMixin):
    __tablename__ = "promo_tier_lines"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_line_id    = Column(UUID(as_uuid=True), ForeignKey("promo_rule_lines.id"), nullable=False)
    min_qty         = Column(Numeric(14, 3), nullable=False)
    max_qty         = Column(Numeric(14, 3))
    min_value       = Column(Numeric(14, 2))
    max_value       = Column(Numeric(14, 2))
    reward_percent  = Column(Numeric(6, 4))
    reward_amount   = Column(Numeric(14, 2))
    unit_price      = Column(Numeric(14, 4))
    sort_order      = Column(Integer, default=1)

    rule_line = relationship("PromoRuleLine")


# ── Sales Order Promo Application ─────────────────────────────────────────────

class SalesOrderPromo(Base, TimestampMixin):
    __tablename__ = "sales_order_promos"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id           = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=False)
    scheme_id                = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=False)
    application_type         = Column(Enum(PromoApplicationType), default=PromoApplicationType.AUTO)
    calculated_benefit_amount = Column(Numeric(14, 2), default=0)
    promo_cost_estimate      = Column(Numeric(14, 2), default=0)
    stack_sequence           = Column(Integer, default=1)
    applied_by_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes                    = Column(Text)

    scheme      = relationship("PromoScheme", back_populates="order_applications")
    line_impacts = relationship("SalesOrderPromoLine", back_populates="order_promo", cascade="all, delete-orphan")


# ── Sales Order Promo Line Impact ─────────────────────────────────────────────

class SalesOrderPromoLine(Base, TimestampMixin):
    __tablename__ = "sales_order_promo_lines"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_promo_id   = Column(UUID(as_uuid=True), ForeignKey("sales_order_promos.id"), nullable=False)
    sales_order_line_id = Column(UUID(as_uuid=True), nullable=True)
    source_rule_id   = Column(UUID(as_uuid=True), ForeignKey("promo_rule_lines.id"), nullable=True)
    impact_type      = Column(Enum(PromoImpactType), nullable=False)
    impacted_qty     = Column(Numeric(14, 3))
    impacted_amount  = Column(Numeric(14, 2))
    reward_item_id   = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    reward_qty       = Column(Numeric(14, 3))
    notes            = Column(Text)

    order_promo  = relationship("SalesOrderPromo", back_populates="line_impacts")
    reward_item  = relationship("Product", foreign_keys=[reward_item_id])
    source_rule  = relationship("PromoRuleLine", foreign_keys=[source_rule_id])


# ── Promo Override Request ────────────────────────────────────────────────────

class PromoOverrideRequest(Base, TimestampMixin):
    __tablename__ = "promo_override_requests"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id      = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=False)
    scheme_id           = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=True)
    requested_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status              = Column(Enum(OverrideStatus), default=OverrideStatus.PENDING)
    requested_discount_pct = Column(Numeric(6, 4))
    requested_free_qty  = Column(Numeric(14, 3))
    reason              = Column(Text, nullable=False)
    approver_notes      = Column(Text)

    scheme = relationship("PromoScheme")


# ── Scheme Usage Tally ────────────────────────────────────────────────────────

class PromoUsageTally(Base, TimestampMixin):
    __tablename__ = "promo_usage_tallies"
    __table_args__ = (UniqueConstraint("scheme_id", "tally_month"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id        = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=False)
    tally_month      = Column(String(7), nullable=False)  # YYYY-MM
    order_count      = Column(Integer, default=0)
    total_discount   = Column(Numeric(14, 2), default=0)
    total_free_value = Column(Numeric(14, 2), default=0)
    total_cost       = Column(Numeric(14, 2), default=0)

    scheme = relationship("PromoScheme")


# ── AI Recommendations ────────────────────────────────────────────────────────

class PromoAIRecommendation(Base, TimestampMixin):
    __tablename__ = "promo_ai_recommendations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type  = Column(Enum(PromoAIAgentType), nullable=False)
    title       = Column(String(300), nullable=False)
    detail      = Column(Text)
    severity    = Column(String(20), default="info")
    status      = Column(Enum(PromoAIRecStatus), default=PromoAIRecStatus.PENDING)
    scheme_id   = Column(UUID(as_uuid=True), ForeignKey("promo_schemes.id"), nullable=True)
