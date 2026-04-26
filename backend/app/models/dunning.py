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

class DunningActionType(str, enum.Enum):
    EMAIL             = "EMAIL"
    SMS               = "SMS"
    WHATSAPP          = "WHATSAPP"
    TASK              = "TASK"
    CALL_REMINDER     = "CALL_REMINDER"
    CREDIT_HOLD       = "CREDIT_HOLD"
    MANAGER_ESCALATION= "MANAGER_ESCALATION"
    FINAL_NOTICE      = "FINAL_NOTICE"
    LEGAL_REVIEW_FLAG = "LEGAL_REVIEW_FLAG"
    PORTAL_NOTIFICATION = "PORTAL_NOTIFICATION"


class DunningCaseStatus(str, enum.Enum):
    OPEN          = "OPEN"
    ON_HOLD       = "ON_HOLD"
    DISPUTED      = "DISPUTED"
    PROMISE_TO_PAY= "PROMISE_TO_PAY"
    RESOLVED      = "RESOLVED"
    CLOSED        = "CLOSED"
    ESCALATED     = "ESCALATED"


class DunningActionOutcome(str, enum.Enum):
    SENT           = "SENT"
    DELIVERED      = "DELIVERED"
    FAILED         = "FAILED"
    ACKNOWLEDGED   = "ACKNOWLEDGED"
    MANUAL_LOGGED  = "MANUAL_LOGGED"
    SKIPPED        = "SKIPPED"


class PTPStatus(str, enum.Enum):
    OPEN           = "OPEN"
    PARTIALLY_MET  = "PARTIALLY_MET"
    MET            = "MET"
    BROKEN         = "BROKEN"
    CANCELLED      = "CANCELLED"


class DunningExceptionType(str, enum.Enum):
    HOLD_SKIP                  = "HOLD_SKIP"
    CREDIT_HOLD_OVERRIDE       = "CREDIT_HOLD_OVERRIDE"
    DISPUTED_INVOICE_EXCLUSION = "DISPUTED_INVOICE_EXCLUSION"
    COLLECTOR_OVERRIDE         = "COLLECTOR_OVERRIDE"
    CUSTOMER_SPECIAL_TERMS     = "CUSTOMER_SPECIAL_TERMS"


class DunningAIAgentType(str, enum.Enum):
    COLLECTION_PRIORITIZATION = "COLLECTION_PRIORITIZATION"
    PAYMENT_RISK_MONITOR      = "PAYMENT_RISK_MONITOR"
    EFFECTIVENESS_ASSISTANT   = "EFFECTIVENESS_ASSISTANT"


class DunningAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class DunningPolicy(Base, TimestampMixin):
    __tablename__ = "dunning_policies"

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_code                 = Column(String(50), nullable=False, unique=True)
    policy_name                 = Column(String(200), nullable=False)
    active_flag                 = Column(Boolean, nullable=False, default=True)
    applies_to_customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    applies_to_channel          = Column(String(60), nullable=True)
    applies_to_region           = Column(String(100), nullable=True)
    applies_to_country          = Column(String(100), nullable=True)
    applies_to_segment          = Column(String(100), nullable=True)
    default_flag                = Column(Boolean, nullable=False, default=False)
    auto_credit_hold_days       = Column(Integer, nullable=True)
    auto_credit_hold_amount     = Column(Numeric(16, 2), nullable=True)
    notes                       = Column(Text, nullable=True)

    levels = relationship("DunningLevel", back_populates="policy", cascade="all, delete-orphan", order_by="DunningLevel.level_no")


class DunningLevel(Base, TimestampMixin):
    __tablename__ = "dunning_levels"
    __table_args__ = (UniqueConstraint("policy_id", "level_no", name="uq_dunning_level"),)

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id             = Column(UUID(as_uuid=True), ForeignKey("dunning_policies.id"), nullable=False)
    level_no              = Column(Integer, nullable=False)
    level_name            = Column(String(100), nullable=False)
    days_overdue_from     = Column(Integer, nullable=False)
    days_overdue_to       = Column(Integer, nullable=True)
    action_type           = Column(Enum(DunningActionType), nullable=False, default=DunningActionType.EMAIL)
    template_code         = Column(String(100), nullable=True)
    auto_send_flag        = Column(Boolean, nullable=False, default=True)
    requires_approval_flag= Column(Boolean, nullable=False, default=False)
    apply_credit_hold_flag= Column(Boolean, nullable=False, default=False)
    escalate_to_role      = Column(String(100), nullable=True)
    active_flag           = Column(Boolean, nullable=False, default=True)
    notes                 = Column(Text, nullable=True)

    policy = relationship("DunningPolicy", back_populates="levels")


class DunningTemplate(Base, TimestampMixin):
    __tablename__ = "dunning_templates"
    __table_args__ = (UniqueConstraint("template_code", "language", name="uq_dunning_template"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String(100), nullable=False)
    language      = Column(String(10), nullable=False, default="en")
    subject       = Column(String(300), nullable=False)
    body_text     = Column(Text, nullable=False)
    channel       = Column(Enum(DunningActionType), nullable=False, default=DunningActionType.EMAIL)
    active_flag   = Column(Boolean, nullable=False, default=True)
    notes         = Column(Text, nullable=True)


class DunningCase(Base, TimestampMixin):
    __tablename__ = "dunning_cases"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_no                  = Column(String(50), nullable=False, unique=True)
    customer_id              = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    policy_id                = Column(UUID(as_uuid=True), ForeignKey("dunning_policies.id"), nullable=True)
    current_level_no         = Column(Integer, nullable=False, default=0)
    case_status              = Column(Enum(DunningCaseStatus), nullable=False, default=DunningCaseStatus.OPEN)
    total_overdue_amount     = Column(Numeric(16, 2), nullable=False, default=0)
    oldest_due_date          = Column(Date, nullable=True)
    latest_action_date       = Column(DateTime(timezone=True), nullable=True)
    next_action_date         = Column(Date, nullable=True)
    assigned_collector_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    credit_hold_flag         = Column(Boolean, nullable=False, default=False)
    credit_hold_reason       = Column(Text, nullable=True)
    credit_hold_date         = Column(Date, nullable=True)
    priority_score           = Column(Integer, nullable=False, default=0)
    collector_notes          = Column(Text, nullable=True)
    notes                    = Column(Text, nullable=True)

    invoice_links  = relationship("DunningCaseInvoice", back_populates="case", cascade="all, delete-orphan")
    action_logs    = relationship("DunningActionLog", back_populates="case", cascade="all, delete-orphan")
    ptps           = relationship("DunningPTP", back_populates="case", cascade="all, delete-orphan")
    exceptions     = relationship("DunningException", back_populates="case", cascade="all, delete-orphan")


class DunningCaseInvoice(Base, TimestampMixin):
    __tablename__ = "dunning_case_invoices"
    __table_args__ = (UniqueConstraint("case_id", "invoice_id", name="uq_dunning_case_inv"),)

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id                 = Column(UUID(as_uuid=True), ForeignKey("dunning_cases.id"), nullable=False)
    invoice_id              = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    invoice_number          = Column(String(80), nullable=False)
    invoice_due_date        = Column(Date, nullable=False)
    invoice_balance_amount  = Column(Numeric(16, 2), nullable=False)
    days_overdue            = Column(Integer, nullable=False, default=0)
    dispute_flag            = Column(Boolean, nullable=False, default=False)
    dispute_reason          = Column(Text, nullable=True)
    promise_to_pay_date     = Column(Date, nullable=True)
    excluded_from_dunning   = Column(Boolean, nullable=False, default=False)
    notes                   = Column(Text, nullable=True)

    case = relationship("DunningCase", back_populates="invoice_links")


class DunningActionLog(Base):
    __tablename__ = "dunning_action_logs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id             = Column(UUID(as_uuid=True), ForeignKey("dunning_cases.id"), nullable=False)
    invoice_id          = Column(UUID(as_uuid=True), nullable=True)
    level_no            = Column(Integer, nullable=False)
    action_type         = Column(Enum(DunningActionType), nullable=False)
    channel_type        = Column(String(40), nullable=True)
    action_datetime     = Column(DateTime(timezone=True), nullable=False)
    sent_by_system_flag = Column(Boolean, nullable=False, default=True)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    template_code       = Column(String(100), nullable=True)
    outcome_status      = Column(Enum(DunningActionOutcome), nullable=False, default=DunningActionOutcome.SENT)
    external_message_ref= Column(String(200), nullable=True)
    rendered_subject    = Column(String(400), nullable=True)
    rendered_body       = Column(Text, nullable=True)
    notes               = Column(Text, nullable=True)

    case = relationship("DunningCase", back_populates="action_logs")


class DunningPTP(Base, TimestampMixin):
    __tablename__ = "dunning_ptps"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id              = Column(UUID(as_uuid=True), ForeignKey("dunning_cases.id"), nullable=False)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    promised_amount      = Column(Numeric(16, 2), nullable=False)
    promised_date        = Column(Date, nullable=False)
    recorded_by          = Column(String(200), nullable=False)
    recorded_at          = Column(DateTime(timezone=True), nullable=False)
    status               = Column(Enum(PTPStatus), nullable=False, default=PTPStatus.OPEN)
    notes                = Column(Text, nullable=True)

    case = relationship("DunningCase", back_populates="ptps")


class DunningException(Base, TimestampMixin):
    __tablename__ = "dunning_exceptions"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id          = Column(UUID(as_uuid=True), ForeignKey("dunning_cases.id"), nullable=False)
    exception_type   = Column(Enum(DunningExceptionType), nullable=False)
    approved_by      = Column(String(200), nullable=False)
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=True)
    reason           = Column(Text, nullable=False)
    notes            = Column(Text, nullable=True)

    case = relationship("DunningCase", back_populates="exceptions")


class DunningAIRecommendation(Base, TimestampMixin):
    __tablename__ = "dunning_ai_recommendations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id        = Column(UUID(as_uuid=True), ForeignKey("dunning_cases.id"), nullable=True)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    agent_type     = Column(Enum(DunningAIAgentType), nullable=False)
    status         = Column(Enum(DunningAIRecStatus), nullable=False, default=DunningAIRecStatus.PENDING)
    title          = Column(String(300), nullable=False)
    body           = Column(Text, nullable=False)
    severity       = Column(String(20), nullable=False, default="INFO")
    reference_type = Column(String(80), nullable=True)
    reference_id   = Column(String(80), nullable=True)
    actioned_by    = Column(String(200), nullable=True)
    actioned_at    = Column(DateTime(timezone=True), nullable=True)
