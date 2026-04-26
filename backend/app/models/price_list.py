from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, Enum, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class PLType(str, enum.Enum):
    STANDARD       = "STANDARD"
    WHOLESALE      = "WHOLESALE"
    RETAIL         = "RETAIL"
    EXPORT         = "EXPORT"
    DISTRIBUTOR    = "DISTRIBUTOR"
    MODERN_TRADE   = "MODERN_TRADE"
    CUSTOMER_SPECIFIC = "CUSTOMER_SPECIFIC"
    PROMO          = "PROMO"
    CUSTOM         = "CUSTOM"


class PLStatus(str, enum.Enum):
    DRAFT        = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    ACTIVE       = "ACTIVE"
    EXPIRED      = "EXPIRED"
    ARCHIVED     = "ARCHIVED"


class PLDiscountType(str, enum.Enum):
    PERCENTAGE    = "PERCENTAGE"
    FIXED_AMOUNT  = "FIXED_AMOUNT"
    OVERRIDE_PRICE= "OVERRIDE_PRICE"


class PLApprovalAction(str, enum.Enum):
    SUBMITTED  = "SUBMITTED"
    APPROVED   = "APPROVED"
    REJECTED   = "REJECTED"
    WITHDRAWN  = "WITHDRAWN"


class PLDiscountScope(str, enum.Enum):
    LINE        = "LINE"
    ORDER       = "ORDER"
    CUSTOMER    = "CUSTOMER"
    VOLUME      = "VOLUME"
    CHANNEL     = "CHANNEL"
    MANUAL      = "MANUAL"
    PROMOTIONAL = "PROMOTIONAL"


class PLChangeType(str, enum.Enum):
    PRICE_CHANGE   = "PRICE_CHANGE"
    TIER_CHANGE    = "TIER_CHANGE"
    STATUS_CHANGE  = "STATUS_CHANGE"
    ASSIGNMENT_CHANGE = "ASSIGNMENT_CHANGE"
    APPROVAL       = "APPROVAL"


class PLAIAgentType(str, enum.Enum):
    PRICING_RISK_MONITOR    = "PRICING_RISK_MONITOR"
    PRICE_OPTIMIZATION      = "PRICE_OPTIMIZATION"
    DISCOUNT_ABUSE_DETECTOR = "DISCOUNT_ABUSE_DETECTOR"


class PLAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class PLHeader(Base, TimestampMixin):
    __tablename__ = "pl_headers"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_code     = Column(String(50), nullable=False, unique=True)
    price_list_name     = Column(String(200), nullable=False)
    currency            = Column(String(10), nullable=False, default="KES")
    pl_type             = Column(Enum(PLType), nullable=False, default=PLType.STANDARD)
    country             = Column(String(100), nullable=True)
    region              = Column(String(100), nullable=True)
    channel             = Column(String(80), nullable=True)
    customer_id         = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    distributor_id      = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True)
    valid_from          = Column(Date, nullable=False)
    valid_to            = Column(Date, nullable=True)
    status              = Column(Enum(PLStatus), nullable=False, default=PLStatus.DRAFT)
    priority_rank       = Column(Integer, nullable=False, default=50)
    default_flag        = Column(Boolean, nullable=False, default=False)
    linked_promo_id     = Column(UUID(as_uuid=True), nullable=True)
    minimum_margin_pct  = Column(Numeric(6, 2), nullable=True)
    max_manual_discount = Column(Numeric(6, 2), nullable=True)
    created_by          = Column(String(200), nullable=True)
    approved_by         = Column(String(200), nullable=True)
    approved_at         = Column(DateTime(timezone=True), nullable=True)
    notes               = Column(Text, nullable=True)

    lines       = relationship("PLLine", back_populates="header", cascade="all, delete-orphan")
    assignments = relationship("PLAssignment", back_populates="header", cascade="all, delete-orphan")
    approvals   = relationship("PLApproval", back_populates="header", cascade="all, delete-orphan")


class PLLine(Base, TimestampMixin):
    __tablename__ = "pl_lines"
    __table_args__ = (UniqueConstraint("header_id", "product_id", "uom", name="uq_pl_line"),)

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id         = Column(UUID(as_uuid=True), ForeignKey("pl_headers.id"), nullable=False)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    brand             = Column(String(100), nullable=True)
    category          = Column(String(100), nullable=True)
    uom               = Column(String(20), nullable=False, default="KG")
    base_price        = Column(Numeric(14, 4), nullable=False)
    minimum_price     = Column(Numeric(14, 4), nullable=True)
    recommended_price = Column(Numeric(14, 4), nullable=True)
    currency          = Column(String(10), nullable=False, default="KES")
    tax_included_flag = Column(Boolean, nullable=False, default=False)
    valid_from        = Column(Date, nullable=True)
    valid_to          = Column(Date, nullable=True)
    active_flag       = Column(Boolean, nullable=False, default=True)
    notes             = Column(Text, nullable=True)

    header = relationship("PLHeader", back_populates="lines")
    tiers  = relationship("PLTier", back_populates="line", cascade="all, delete-orphan", order_by="PLTier.min_qty")


class PLTier(Base, TimestampMixin):
    __tablename__ = "pl_tiers"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id              = Column(UUID(as_uuid=True), ForeignKey("pl_lines.id"), nullable=False)
    min_qty              = Column(Numeric(14, 3), nullable=False)
    max_qty              = Column(Numeric(14, 3), nullable=True)
    unit_price           = Column(Numeric(14, 4), nullable=True)
    discount_pct         = Column(Numeric(6, 3), nullable=True)
    fixed_discount_amount= Column(Numeric(14, 4), nullable=True)
    effective_margin_pct = Column(Numeric(6, 2), nullable=True)
    active_flag          = Column(Boolean, nullable=False, default=True)

    line = relationship("PLLine", back_populates="tiers")


class PLAssignment(Base, TimestampMixin):
    __tablename__ = "pl_assignments"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id      = Column(UUID(as_uuid=True), ForeignKey("pl_headers.id"), nullable=False)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True)
    channel        = Column(String(80), nullable=True)
    region         = Column(String(100), nullable=True)
    country        = Column(String(100), nullable=True)
    segment        = Column(String(100), nullable=True)
    valid_from     = Column(Date, nullable=False)
    valid_to       = Column(Date, nullable=True)
    priority_rank  = Column(Integer, nullable=False, default=50)
    active_flag    = Column(Boolean, nullable=False, default=True)
    notes          = Column(Text, nullable=True)

    header = relationship("PLHeader", back_populates="assignments")


class PLDiscountRule(Base, TimestampMixin):
    __tablename__ = "pl_discount_rules"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code             = Column(String(50), nullable=False, unique=True)
    rule_name             = Column(String(200), nullable=False)
    scope                 = Column(Enum(PLDiscountScope), nullable=False, default=PLDiscountScope.LINE)
    discount_type         = Column(Enum(PLDiscountType), nullable=False)
    discount_value        = Column(Numeric(14, 4), nullable=False)
    max_discount_pct      = Column(Numeric(6, 2), nullable=True)
    requires_approval     = Column(Boolean, nullable=False, default=False)
    min_margin_pct        = Column(Numeric(6, 2), nullable=True)
    applies_to_pl_type    = Column(String(40), nullable=True)
    applies_to_channel    = Column(String(80), nullable=True)
    applies_to_customer_id= Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    reason_required       = Column(Boolean, nullable=False, default=False)
    valid_from            = Column(Date, nullable=True)
    valid_to              = Column(Date, nullable=True)
    active_flag           = Column(Boolean, nullable=False, default=True)
    notes                 = Column(Text, nullable=True)


class PLApproval(Base, TimestampMixin):
    __tablename__ = "pl_approvals"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id      = Column(UUID(as_uuid=True), ForeignKey("pl_headers.id"), nullable=False)
    action         = Column(Enum(PLApprovalAction), nullable=False)
    submitted_by   = Column(String(200), nullable=False)
    reviewed_by    = Column(String(200), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)
    notes          = Column(Text, nullable=True)

    header = relationship("PLHeader", back_populates="approvals")


class PLChangeHistory(Base):
    __tablename__ = "pl_change_history"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id      = Column(UUID(as_uuid=True), ForeignKey("pl_headers.id"), nullable=False)
    line_id        = Column(UUID(as_uuid=True), nullable=True)
    change_type    = Column(Enum(PLChangeType), nullable=False)
    changed_by     = Column(String(200), nullable=False)
    changed_at     = Column(DateTime(timezone=True), nullable=False)
    old_value_json = Column(JSON, nullable=True)
    new_value_json = Column(JSON, nullable=True)
    notes          = Column(Text, nullable=True)


class PLAIRecommendation(Base, TimestampMixin):
    __tablename__ = "pl_ai_recommendations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    header_id      = Column(UUID(as_uuid=True), ForeignKey("pl_headers.id"), nullable=True)
    line_id        = Column(UUID(as_uuid=True), nullable=True)
    agent_type     = Column(Enum(PLAIAgentType), nullable=False)
    status         = Column(Enum(PLAIRecStatus), nullable=False, default=PLAIRecStatus.PENDING)
    title          = Column(String(300), nullable=False)
    body           = Column(Text, nullable=False)
    severity       = Column(String(20), nullable=False, default="INFO")
    reference_type = Column(String(80), nullable=True)
    reference_id   = Column(String(80), nullable=True)
    actioned_by    = Column(String(200), nullable=True)
    actioned_at    = Column(DateTime(timezone=True), nullable=True)
