"""M45.S01.T014 advanced CPQ and contract lifecycle on top of quotations, price lists, promotions, contracts,
subscriptions and payment links."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class QuoteTemplate(Base):
    __tablename__ = "cpq_quote_templates"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(100), nullable=False, unique=True)
    lines      = Column(JSON, nullable=False)          # [{"product_id", "qty", "discount_pct"}] priced from the price book
    notes      = Column(Text, nullable=True)
    valid_days = Column(Integer, nullable=False, default=14)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ContractTemplate(Base):
    __tablename__ = "cpq_contract_templates"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                = Column(String(100), nullable=False, unique=True)
    contract_type       = Column(String(50), nullable=False, default="SUPPLY")
    clauses             = Column(JSON, nullable=False)  # [{"title", "text"}] with {customer}, {quote_no}, {total} placeholders
    term_months         = Column(Integer, nullable=False, default=12)
    auto_renew          = Column(Boolean, nullable=False, default=False)
    renewal_notice_days = Column(Integer, nullable=False, default=30)


class QuoteApproval(Base):
    """One level of a multi-step discount approval for one quote version."""
    __tablename__ = "cpq_approvals"
    __table_args__ = (UniqueConstraint("quote_id", "level", name="uq_cpq_approval_level"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id   = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    level      = Column(Integer, nullable=False)
    permission = Column(String(60), nullable=False)
    approver   = Column(String(100), nullable=False)
    approver_id = Column(UUID(as_uuid=True), nullable=False)
    discount_pct = Column(Numeric(8, 4), nullable=False)        # the discount that was approved
    decided_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QuotePromo(Base):
    __tablename__ = "cpq_quote_promos"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id    = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_code = Column(String(60), nullable=False)
    scheme_name = Column(String(200), nullable=False)
    benefit     = Column(Numeric(18, 4), nullable=False)
    details     = Column(JSON, nullable=False)


class ContractRenewal(Base):
    __tablename__ = "cpq_renewals"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id      = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, unique=True)
    source_quote_id  = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    renewal_quote_id = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    notified_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BillingAttempt(Base):
    """Recurring billing for subscription orders: payment link sent, reminders retried, settled from the link."""
    __tablename__ = "cpq_billing"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id   = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, unique=True)
    link_id      = Column(UUID(as_uuid=True), ForeignKey("pay_links.id", ondelete="SET NULL"), nullable=True)
    attempts     = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    status       = Column(String(10), nullable=False, default="OPEN")   # OPEN | PAID | GAVE_UP
