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

class ContractType(str, enum.Enum):
    CUSTOMER_SALES    = "CUSTOMER_SALES"
    DISTRIBUTOR       = "DISTRIBUTOR"
    SUPPLIER          = "SUPPLIER"
    REBATE            = "REBATE"
    VOLUME_INCENTIVE  = "VOLUME_INCENTIVE"
    LISTING_DISPLAY   = "LISTING_DISPLAY"
    SERVICE_FEE       = "SERVICE_FEE"
    FRAMEWORK         = "FRAMEWORK"


class PartyType(str, enum.Enum):
    CUSTOMER    = "CUSTOMER"
    DISTRIBUTOR = "DISTRIBUTOR"
    SUPPLIER    = "SUPPLIER"


class ContractStatus(str, enum.Enum):
    DRAFT        = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    ACTIVE       = "ACTIVE"
    EXPIRED      = "EXPIRED"
    TERMINATED   = "TERMINATED"
    ARCHIVED     = "ARCHIVED"


class TermType(str, enum.Enum):
    PRICE          = "PRICE"
    REBATE         = "REBATE"
    DISCOUNT       = "DISCOUNT"
    VOLUME_TARGET  = "VOLUME_TARGET"
    SERVICE_FEE    = "SERVICE_FEE"
    PENALTY        = "PENALTY"
    PAYMENT_TERMS  = "PAYMENT_TERMS"
    OTHER          = "OTHER"


class ValueType(str, enum.Enum):
    FIXED      = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    QUANTITY   = "QUANTITY"
    THRESHOLD  = "THRESHOLD"


class RebateType(str, enum.Enum):
    VOLUME       = "VOLUME"
    VALUE        = "VALUE"
    TARGET_BASED = "TARGET_BASED"


class CalcBasis(str, enum.Enum):
    INVOICE    = "INVOICE"
    NET_SALES  = "NET_SALES"
    QUANTITY   = "QUANTITY"


class SettlementFreq(str, enum.Enum):
    MONTHLY   = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY    = "YEARLY"
    ON_DEMAND = "ON_DEMAND"


class ApprovalAction(str, enum.Enum):
    SUBMITTED  = "SUBMITTED"
    APPROVED   = "APPROVED"
    REJECTED   = "REJECTED"
    REVISION   = "REVISION"


class CTAIAgentType(str, enum.Enum):
    RISK_MONITOR       = "RISK_MONITOR"
    RENEWAL_ADVISOR    = "RENEWAL_ADVISOR"
    COMPLIANCE_MONITOR = "COMPLIANCE_MONITOR"


class CTAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_code   = Column(String(50), unique=True, nullable=False, index=True)
    contract_name   = Column(String(200), nullable=False)
    contract_type   = Column(String(50), nullable=False)
    party_type      = Column(String(30), nullable=False)
    party_id        = Column(UUID(as_uuid=True), nullable=False, index=True)  # customer/distributor/supplier

    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=True)
    status          = Column(String(50), nullable=False, default=ContractStatus.DRAFT.value)

    currency        = Column(String(3), nullable=False, default="KES")
    payment_terms_id = Column(UUID(as_uuid=True), nullable=True)
    price_list_id   = Column(UUID(as_uuid=True), nullable=True)

    auto_renew      = Column(Boolean, default=False)
    renewal_notice_days = Column(Integer, default=30)

    linked_promo_ids = Column(JSON, nullable=True)  # list of promo IDs
    linked_tpm_plan_id = Column(UUID(as_uuid=True), nullable=True)

    notes           = Column(Text, nullable=True)
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at     = Column(DateTime, nullable=True)
    terminated_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    terminated_at   = Column(DateTime, nullable=True)
    termination_reason = Column(Text, nullable=True)

    current_version = Column(Integer, default=1)

    terms        = relationship("ContractTerm", back_populates="contract", cascade="all, delete-orphan")
    rebates      = relationship("ContractRebate", back_populates="contract", cascade="all, delete-orphan")
    performance  = relationship("ContractPerformance", back_populates="contract", cascade="all, delete-orphan")
    versions     = relationship("ContractVersion", back_populates="contract", cascade="all, delete-orphan")
    approvals    = relationship("ContractApproval", back_populates="contract", cascade="all, delete-orphan")
    ai_recs      = relationship("CTAIRecommendation", back_populates="contract")


class ContractTerm(Base, TimestampMixin):
    __tablename__ = "contract_terms"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id   = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    term_type     = Column(String(50), nullable=False)
    item_id       = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    category_id   = Column(UUID(as_uuid=True), nullable=True)
    brand_id      = Column(UUID(as_uuid=True), nullable=True)
    value_type    = Column(String(30), nullable=False, default=ValueType.FIXED.value)
    value         = Column(Numeric(18, 4), nullable=False)
    min_threshold = Column(Numeric(18, 4), nullable=True)
    max_threshold = Column(Numeric(18, 4), nullable=True)
    valid_from    = Column(Date, nullable=True)
    valid_to      = Column(Date, nullable=True)
    active_flag   = Column(Boolean, default=True)
    notes         = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="terms")


class ContractRebate(Base, TimestampMixin):
    __tablename__ = "contract_rebates"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id          = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    rebate_name          = Column(String(100), nullable=True)
    rebate_type          = Column(String(30), nullable=False, default=RebateType.VOLUME.value)
    calculation_basis    = Column(String(30), nullable=False, default=CalcBasis.INVOICE.value)
    item_id              = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    threshold            = Column(Numeric(18, 4), nullable=True)   # min qty or value to qualify
    rebate_pct           = Column(Numeric(7, 4), nullable=True)
    rebate_amount        = Column(Numeric(14, 4), nullable=True)   # fixed amount alternative
    settlement_frequency = Column(String(30), nullable=False, default=SettlementFreq.QUARTERLY.value)
    accrued_amount       = Column(Numeric(14, 4), nullable=False, default=0)
    settled_amount       = Column(Numeric(14, 4), nullable=False, default=0)
    active_flag          = Column(Boolean, default=True)
    notes                = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="rebates")


class ContractPerformance(Base, TimestampMixin):
    __tablename__ = "contract_performance"
    __table_args__ = (UniqueConstraint("contract_id", "period", name="uq_contract_perf_period"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id     = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    period          = Column(String(20), nullable=False)   # YYYY-MM or YYYY-Q1
    target_value    = Column(Numeric(18, 4), nullable=True)
    actual_value    = Column(Numeric(18, 4), nullable=True, default=0)
    achievement_pct = Column(Numeric(7, 3), nullable=True)
    rebate_earned   = Column(Numeric(14, 4), nullable=True, default=0)
    status          = Column(String(30), nullable=False, default="OPEN")  # OPEN/CLOSED/SETTLED
    notes           = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="performance")


class ContractVersion(Base, TimestampMixin):
    __tablename__ = "contract_versions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id    = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version_no     = Column(Integer, nullable=False)
    change_summary = Column(Text, nullable=True)
    snapshot       = Column(JSON, nullable=True)   # full contract snapshot at this version
    effective_date = Column(Date, nullable=True)
    approved_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (UniqueConstraint("contract_id", "version_no", name="uq_contract_version"),)

    contract = relationship("Contract", back_populates="versions")


class ContractApproval(Base, TimestampMixin):
    __tablename__ = "contract_approvals"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    action      = Column(String(30), nullable=False)   # SUBMITTED/APPROVED/REJECTED/REVISION
    actioned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    comments    = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="approvals")


class CTAIRecommendation(Base, TimestampMixin):
    __tablename__ = "ct_ai_recommendations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type   = Column(String(50), nullable=False)
    status       = Column(String(50), default=CTAIRecStatus.PENDING.value)
    severity     = Column(String(20), default="INFO")
    title        = Column(String(200), nullable=False)
    body         = Column(Text, nullable=False)
    data         = Column(JSON, nullable=True)
    contract_id  = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    party_id     = Column(UUID(as_uuid=True), nullable=True)

    contract = relationship("Contract", back_populates="ai_recs")
