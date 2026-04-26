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

class CommissionAppliesTo(str, enum.Enum):
    SALES_REP   = "SALES_REP"
    DISTRIBUTOR = "DISTRIBUTOR"
    TEAM        = "TEAM"


class CommissionScope(str, enum.Enum):
    GLOBAL    = "GLOBAL"
    CUSTOMER  = "CUSTOMER"
    CHANNEL   = "CHANNEL"
    REGION    = "REGION"
    PRODUCT   = "PRODUCT"
    CATEGORY  = "CATEGORY"
    BRAND     = "BRAND"


class RuleStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    EXPIRED  = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class ConditionType(str, enum.Enum):
    VOLUME   = "VOLUME"
    VALUE    = "VALUE"
    PRODUCT  = "PRODUCT"
    CATEGORY = "CATEGORY"
    CUSTOMER = "CUSTOMER"
    TARGET   = "TARGET"


class CommissionType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED      = "FIXED"
    TIERED     = "TIERED"


class TxnStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    PAID     = "PAID"
    REJECTED = "REJECTED"
    REVERSED = "REVERSED"


class PayoutStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED  = "APPROVED"
    PAID      = "PAID"
    CANCELLED = "CANCELLED"


class CMAIAgentType(str, enum.Enum):
    INCENTIVE_OPTIMIZER  = "INCENTIVE_OPTIMIZER"
    FRAUD_DETECTION      = "FRAUD_DETECTION"
    PERFORMANCE_ADVISOR  = "PERFORMANCE_ADVISOR"


class CMAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class CommissionRule(Base, TimestampMixin):
    __tablename__ = "commission_rules"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code        = Column(String(50), unique=True, nullable=False, index=True)
    rule_name        = Column(String(200), nullable=False)
    applies_to       = Column(String(30), nullable=False)   # CommissionAppliesTo
    applicable_scope = Column(String(30), nullable=False, default=CommissionScope.GLOBAL.value)

    # Scope reference (only one populated based on applicable_scope)
    scope_ref_id     = Column(UUID(as_uuid=True), nullable=True)   # customer/product/category/etc

    priority         = Column(Integer, nullable=False, default=10)  # lower = higher priority
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=True)
    status           = Column(String(30), nullable=False, default=RuleStatus.DRAFT.value)

    contract_id      = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes            = Column(Text, nullable=True)

    lines        = relationship("CommissionRuleLine", back_populates="rule", cascade="all, delete-orphan")
    transactions = relationship("CommissionTxn", back_populates="rule")


class CommissionRuleLine(Base, TimestampMixin):
    __tablename__ = "commission_rule_lines"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id          = Column(UUID(as_uuid=True), ForeignKey("commission_rules.id", ondelete="CASCADE"), nullable=False)
    condition_type   = Column(String(30), nullable=False)
    min_threshold    = Column(Numeric(18, 4), nullable=True)
    max_threshold    = Column(Numeric(18, 4), nullable=True)
    commission_type  = Column(String(30), nullable=False, default=CommissionType.PERCENTAGE.value)
    commission_value = Column(Numeric(10, 4), nullable=False)   # % or fixed amount
    target_flag      = Column(Boolean, default=False)   # True = only applies if target met
    sort_order       = Column(Integer, default=0)
    notes            = Column(Text, nullable=True)

    rule = relationship("CommissionRule", back_populates="lines")


class CommissionTarget(Base, TimestampMixin):
    __tablename__ = "commission_targets"
    __table_args__ = (UniqueConstraint("entity_id", "period", "applies_to", name="uq_cm_target"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id    = Column(UUID(as_uuid=True), nullable=False, index=True)   # rep/distributor/team id
    applies_to   = Column(String(30), nullable=False)
    period       = Column(String(20), nullable=False)   # YYYY-MM or YYYY-Q1
    target_value = Column(Numeric(18, 4), nullable=False)
    actual_value = Column(Numeric(18, 4), nullable=False, default=0)
    achievement_pct = Column(Numeric(7, 3), nullable=True)
    bonus_earned = Column(Numeric(14, 4), nullable=True, default=0)
    notes        = Column(Text, nullable=True)


class CommissionTxn(Base, TimestampMixin):
    __tablename__ = "commission_txns"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id          = Column(UUID(as_uuid=True), ForeignKey("commission_rules.id"), nullable=True)
    sales_order_id   = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    invoice_id       = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    sales_rep_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    distributor_id   = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    base_amount      = Column(Numeric(14, 2), nullable=False)   # invoice/order value used
    commission_pct   = Column(Numeric(7, 4), nullable=True)
    commission_amount = Column(Numeric(14, 4), nullable=False)
    calculation_date = Column(Date, nullable=False)
    period           = Column(String(20), nullable=False)   # YYYY-MM
    status           = Column(String(30), nullable=False, default=TxnStatus.PENDING.value)
    is_reversal      = Column(Boolean, default=False)   # True = return/credit note reversal
    calc_detail      = Column(JSON, nullable=True)   # rule line applied, thresholds, etc.

    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes            = Column(Text, nullable=True)

    rule         = relationship("CommissionRule", back_populates="transactions")
    adjustments  = relationship("CommissionAdjustment", back_populates="txn", cascade="all, delete-orphan")


class CommissionAdjustment(Base, TimestampMixin):
    __tablename__ = "commission_adjustments"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txn_id            = Column(UUID(as_uuid=True), ForeignKey("commission_txns.id", ondelete="CASCADE"), nullable=False)
    adjustment_amount = Column(Numeric(14, 4), nullable=False)
    reason            = Column(Text, nullable=False)
    approved_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes             = Column(Text, nullable=True)

    txn = relationship("CommissionTxn", back_populates="adjustments")


class CommissionPayout(Base, TimestampMixin):
    __tablename__ = "commission_payouts"
    __table_args__ = (UniqueConstraint("entity_id", "period", "applies_to", name="uq_cm_payout_period"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    applies_to       = Column(String(30), nullable=False)
    period           = Column(String(20), nullable=False)
    total_commission = Column(Numeric(14, 4), nullable=False, default=0)
    adjustments_total = Column(Numeric(14, 4), nullable=False, default=0)
    net_commission   = Column(Numeric(14, 4), nullable=False, default=0)
    paid_amount      = Column(Numeric(14, 4), nullable=False, default=0)
    payment_date     = Column(Date, nullable=True)
    status           = Column(String(30), nullable=False, default=PayoutStatus.DRAFT.value)
    txn_ids          = Column(JSON, nullable=True)   # list of commission_txn IDs included
    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes            = Column(Text, nullable=True)


class CMAIRecommendation(Base, TimestampMixin):
    __tablename__ = "cm_ai_recommendations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type   = Column(String(50), nullable=False)
    status       = Column(String(50), default=CMAIRecStatus.PENDING.value)
    severity     = Column(String(20), default="INFO")
    title        = Column(String(200), nullable=False)
    body         = Column(Text, nullable=False)
    data         = Column(JSON, nullable=True)
    entity_id    = Column(UUID(as_uuid=True), nullable=True)   # rep/distributor
    rule_id      = Column(UUID(as_uuid=True), ForeignKey("commission_rules.id"), nullable=True)
