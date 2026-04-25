"""
Bank Reconciliation System — Models
Bank statement import, auto-match, manual/split reconciliation,
M-Pesa support, close/lock workflow.
"""
import enum
import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ─── Enums ────────────────────────────────────────────────────────────────────

class BRAccountType(str, enum.Enum):
    CURRENT      = "CURRENT"
    SAVINGS      = "SAVINGS"
    MOBILE_MONEY = "MOBILE_MONEY"
    OVERDRAFT    = "OVERDRAFT"


class BRImportSource(str, enum.Enum):
    CSV    = "CSV"
    OFX    = "OFX"
    MANUAL = "MANUAL"
    MPESA  = "MPESA"
    API    = "API"


class BRStatementStatus(str, enum.Enum):
    DRAFT              = "DRAFT"
    IMPORTED           = "IMPORTED"
    IN_RECONCILIATION  = "IN_RECONCILIATION"
    RECONCILED         = "RECONCILED"
    CLOSED             = "CLOSED"
    LOCKED             = "LOCKED"


class BRLineMatchStatus(str, enum.Enum):
    UNMATCHED           = "UNMATCHED"
    SUGGESTED_MATCH     = "SUGGESTED_MATCH"
    PARTIALLY_MATCHED   = "PARTIALLY_MATCHED"
    MATCHED             = "MATCHED"
    IGNORED             = "IGNORED"
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    NEEDS_REVIEW        = "NEEDS_REVIEW"


class BRMatchMethod(str, enum.Enum):
    AUTO       = "AUTO"
    MANUAL     = "MANUAL"
    SPLIT      = "SPLIT"
    RULE_BASED = "RULE_BASED"


class BRERPTransactionType(str, enum.Enum):
    AR_PAYMENT       = "AR_PAYMENT"
    AP_PAYMENT       = "AP_PAYMENT"
    PURCHASE_PAYMENT = "PURCHASE_PAYMENT"
    EXPENSE_PAYMENT  = "EXPENSE_PAYMENT"
    PAYROLL          = "PAYROLL"
    TRANSFER         = "TRANSFER"
    MPESA_COLLECTION = "MPESA_COLLECTION"
    MPESA_PAYOUT     = "MPESA_PAYOUT"
    BANK_CHARGE      = "BANK_CHARGE"
    INTEREST         = "INTEREST"
    REFUND           = "REFUND"
    JOURNAL_ENTRY    = "JOURNAL_ENTRY"


class BRAdjustmentType(str, enum.Enum):
    BANK_CHARGE   = "BANK_CHARGE"
    INTEREST      = "INTEREST"
    ROUNDING      = "ROUNDING"
    FX_DIFFERENCE = "FX_DIFFERENCE"
    WRITE_OFF     = "WRITE_OFF"
    OTHER         = "OTHER"


class BRRuleConditionType(str, enum.Enum):
    NARRATION_CONTAINS   = "NARRATION_CONTAINS"
    REFERENCE_STARTS_WITH = "REFERENCE_STARTS_WITH"
    REFERENCE_CONTAINS   = "REFERENCE_CONTAINS"
    AMOUNT_EQUALS        = "AMOUNT_EQUALS"
    AMOUNT_RANGE         = "AMOUNT_RANGE"
    PAYEE_NAME_CONTAINS  = "PAYEE_NAME_CONTAINS"
    ACCOUNT_SPECIFIC     = "ACCOUNT_SPECIFIC"


class BRAIAgentType(str, enum.Enum):
    MATCH_CONFIDENCE = "MATCH_CONFIDENCE"
    CASH_ANOMALY     = "CASH_ANOMALY"
    RULE_OPTIMIZER   = "RULE_OPTIMIZER"


class BRAIRecStatus(str, enum.Enum):
    PENDING   = "PENDING"
    ACCEPTED  = "ACCEPTED"
    REJECTED  = "REJECTED"
    DISMISSED = "DISMISSED"


# ─── Models ───────────────────────────────────────────────────────────────────

class BRBankAccount(Base, TimestampMixin):
    """Bank / mobile-money account master for reconciliation."""
    __tablename__ = "br_bank_accounts"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_name                = Column(String(100), nullable=False)
    branch_name              = Column(String(100), nullable=True)
    account_name             = Column(String(255), nullable=False)
    account_number_masked    = Column(String(50),  nullable=True)
    currency                 = Column(String(3),   nullable=False, default="KES")
    country                  = Column(String(2),   nullable=False, default="KE")
    account_type             = Column(Enum(BRAccountType), nullable=False, default=BRAccountType.CURRENT)
    reconciliation_enabled   = Column(Boolean, nullable=False, default=True)
    mobile_money_flag        = Column(Boolean, nullable=False, default=False)
    mpesa_till_or_paybill_no = Column(String(20), nullable=True)
    gl_account_id            = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True)
    cash_account_id          = Column(UUID(as_uuid=True), ForeignKey("cash_accounts.id", ondelete="SET NULL"), nullable=True)
    active                   = Column(Boolean, nullable=False, default=True)
    notes                    = Column(Text, nullable=True)

    statements   = relationship("BRStatement", back_populates="bank_account", cascade="all, delete-orphan")
    rules        = relationship("BRRule", back_populates="bank_account", foreign_keys="BRRule.bank_account_id")
    gl_account   = relationship("ChartOfAccount")
    cash_account = relationship("CashAccount")


class BRStatement(Base, TimestampMixin):
    """Bank statement header — one per imported statement period."""
    __tablename__ = "br_statements"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_no       = Column(String(50), nullable=False, unique=True)
    bank_account_id    = Column(UUID(as_uuid=True), ForeignKey("br_bank_accounts.id", ondelete="RESTRICT"), nullable=False)
    statement_date     = Column(Date, nullable=False)
    period_start_date  = Column(Date, nullable=False)
    period_end_date    = Column(Date, nullable=False)
    opening_balance    = Column(Numeric(14, 4), nullable=False, default=0)
    closing_balance    = Column(Numeric(14, 4), nullable=False, default=0)
    statement_currency = Column(String(3), nullable=False, default="KES")
    import_source      = Column(Enum(BRImportSource), nullable=False, default=BRImportSource.MANUAL)
    import_file_name   = Column(String(255), nullable=True)
    status             = Column(Enum(BRStatementStatus), nullable=False, default=BRStatementStatus.DRAFT)
    imported_by        = Column(String(100), nullable=True)
    imported_at        = Column(DateTime(timezone=True), nullable=True)
    closed_by          = Column(String(100), nullable=True)
    closed_at          = Column(DateTime(timezone=True), nullable=True)
    notes              = Column(Text, nullable=True)
    total_credits      = Column(Numeric(14, 4), nullable=False, default=0)
    total_debits       = Column(Numeric(14, 4), nullable=False, default=0)
    total_lines        = Column(Integer, nullable=False, default=0)

    bank_account  = relationship("BRBankAccount", back_populates="statements")
    lines         = relationship("BRStatementLine", back_populates="statement", cascade="all, delete-orphan", order_by="BRStatementLine.line_no")
    adjustments   = relationship("BRAdjustment", back_populates="statement", cascade="all, delete-orphan")
    ai_recs       = relationship("BRAIRecommendation", back_populates="statement", foreign_keys="BRAIRecommendation.statement_id")


class BRStatementLine(Base, TimestampMixin):
    """One parsed line from a bank statement."""
    __tablename__ = "br_statement_lines"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id         = Column(UUID(as_uuid=True), ForeignKey("br_statements.id", ondelete="CASCADE"), nullable=False)
    line_no              = Column(Integer, nullable=False, default=0)
    transaction_date     = Column(Date, nullable=False)
    value_date           = Column(Date, nullable=True)
    external_reference   = Column(String(100), nullable=True)
    bank_reference       = Column(String(100), nullable=True)
    narration            = Column(Text, nullable=True)
    counterparty_name    = Column(String(255), nullable=True)
    amount               = Column(Numeric(14, 4), nullable=False)
    debit_credit_indicator = Column(String(1), nullable=False, default="C")  # D or C
    running_balance      = Column(Numeric(14, 4), nullable=True)
    normalized_reference = Column(String(100), nullable=True)
    normalized_narration = Column(String(500), nullable=True)
    match_status         = Column(Enum(BRLineMatchStatus), nullable=False, default=BRLineMatchStatus.UNMATCHED)
    matched_amount       = Column(Numeric(14, 4), nullable=False, default=0)
    unmatched_amount     = Column(Numeric(14, 4), nullable=False, default=0)
    reconciliation_notes = Column(Text, nullable=True)
    is_duplicate_suspected = Column(Boolean, nullable=False, default=False)
    raw_data             = Column(JSON, nullable=True)

    statement = relationship("BRStatement", back_populates="lines")
    matches   = relationship("BRMatch", back_populates="statement_line", cascade="all, delete-orphan")
    ai_recs   = relationship("BRAIRecommendation", back_populates="statement_line", foreign_keys="BRAIRecommendation.statement_line_id")


class BRMatch(Base, TimestampMixin):
    """Reconciliation match: statement line ↔ ERP transaction."""
    __tablename__ = "br_matches"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_line_id      = Column(UUID(as_uuid=True), ForeignKey("br_statement_lines.id", ondelete="CASCADE"), nullable=False)
    erp_transaction_type   = Column(Enum(BRERPTransactionType), nullable=False)
    erp_transaction_id     = Column(UUID(as_uuid=True), nullable=True)   # generic — no FK
    erp_reference          = Column(String(100), nullable=True)
    erp_transaction_date   = Column(Date, nullable=True)
    erp_amount             = Column(Numeric(14, 4), nullable=True)
    erp_description        = Column(String(500), nullable=True)
    matched_amount         = Column(Numeric(14, 4), nullable=False)
    match_method           = Column(Enum(BRMatchMethod), nullable=False, default=BRMatchMethod.MANUAL)
    confidence_score       = Column(Numeric(5, 4), nullable=True)
    rule_id                = Column(UUID(as_uuid=True), ForeignKey("br_rules.id", ondelete="SET NULL"), nullable=True)
    is_active              = Column(Boolean, nullable=False, default=True)
    created_by             = Column(String(100), nullable=True)
    approved_by            = Column(String(100), nullable=True)
    approved_at            = Column(DateTime(timezone=True), nullable=True)
    notes                  = Column(Text, nullable=True)

    statement_line = relationship("BRStatementLine", back_populates="matches")
    rule           = relationship("BRRule", foreign_keys=[rule_id])


class BRRule(Base, TimestampMixin):
    """Reusable auto-match rule for a bank account or globally."""
    __tablename__ = "br_rules"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id         = Column(UUID(as_uuid=True), ForeignKey("br_bank_accounts.id", ondelete="CASCADE"), nullable=True)
    rule_name               = Column(String(200), nullable=False)
    condition_type          = Column(Enum(BRRuleConditionType), nullable=False)
    condition_value         = Column(String(500), nullable=False)
    target_transaction_type = Column(Enum(BRERPTransactionType), nullable=False)
    auto_apply              = Column(Boolean, nullable=False, default=True)
    confidence_weight       = Column(Numeric(5, 4), nullable=False, default=0.8)
    priority                = Column(Integer, nullable=False, default=100)
    active                  = Column(Boolean, nullable=False, default=True)
    notes                   = Column(Text, nullable=True)

    bank_account = relationship("BRBankAccount", back_populates="rules", foreign_keys=[bank_account_id])


class BRAdjustment(Base, TimestampMixin):
    """Bank charges, interest, rounding differences posted as adjustments."""
    __tablename__ = "br_adjustments"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id       = Column(UUID(as_uuid=True), ForeignKey("br_statements.id", ondelete="CASCADE"), nullable=False)
    statement_line_id  = Column(UUID(as_uuid=True), ForeignKey("br_statement_lines.id", ondelete="SET NULL"), nullable=True)
    adjustment_type    = Column(Enum(BRAdjustmentType), nullable=False)
    amount             = Column(Numeric(14, 4), nullable=False)
    description        = Column(String(500), nullable=False)
    gl_account_id      = Column(UUID(as_uuid=True), nullable=True)
    auto_created       = Column(Boolean, nullable=False, default=False)
    posted             = Column(Boolean, nullable=False, default=False)
    posted_by          = Column(String(100), nullable=True)
    posted_at          = Column(DateTime(timezone=True), nullable=True)
    created_by         = Column(String(100), nullable=True)

    statement      = relationship("BRStatement", back_populates="adjustments")
    statement_line = relationship("BRStatementLine", foreign_keys=[statement_line_id])


class BRAIRecommendation(Base, TimestampMixin):
    """AI-generated recommendation for bank reconciliation."""
    __tablename__ = "br_ai_recommendations"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id       = Column(UUID(as_uuid=True), ForeignKey("br_statements.id", ondelete="SET NULL"), nullable=True)
    statement_line_id  = Column(UUID(as_uuid=True), ForeignKey("br_statement_lines.id", ondelete="SET NULL"), nullable=True)
    agent_type         = Column(Enum(BRAIAgentType), nullable=False)
    title              = Column(String(500), nullable=False)
    explanation        = Column(Text, nullable=True)
    impact_summary     = Column(String(500), nullable=True)
    suggested_action   = Column(Text, nullable=True)
    priority           = Column(String(10), nullable=False, default="MEDIUM")
    confidence_score   = Column(Numeric(5, 4), nullable=True)
    status             = Column(Enum(BRAIRecStatus), nullable=False, default=BRAIRecStatus.PENDING)
    actioned_by        = Column(String(100), nullable=True)
    actioned_at        = Column(DateTime(timezone=True), nullable=True)

    statement      = relationship("BRStatement", back_populates="ai_recs", foreign_keys=[statement_id])
    statement_line = relationship("BRStatementLine", back_populates="ai_recs", foreign_keys=[statement_line_id])
