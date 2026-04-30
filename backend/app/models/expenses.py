from __future__ import annotations
import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ExpenseStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    MANAGER_APPROVED = "manager_approved"
    FINANCE_APPROVED = "finance_approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class ReimbursementMethod(str, PyEnum):
    PAYROLL = "payroll"
    AP = "ap"
    BANK = "bank"
    CASH = "cash"
    MANUAL = "manual"


class AdvanceSettlementStatus(str, PyEnum):
    OPEN = "open"
    PARTIALLY_SETTLED = "partially_settled"
    SETTLED = "settled"
    OVERDUE = "overdue"


class PolicyViolationSeverity(str, PyEnum):
    WARNING = "warning"
    BLOCK = "block"


class ExpAIAgentType(str, PyEnum):
    RISK_MONITOR = "risk_monitor"
    POLICY_OPTIMIZER = "policy_optimizer"
    REIMBURSEMENT_ASSISTANT = "reimbursement_assistant"


class ExpAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


# ── Expense Category ──────────────────────────────────────────────────────────

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    expense_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code = Column(String(30), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    default_gl_account_id = Column(UUID(as_uuid=True), nullable=True)
    default_cost_center_id = Column(UUID(as_uuid=True), nullable=True)
    receipt_required_flag = Column(Boolean, default=True)
    approval_required_flag = Column(Boolean, default=True)
    taxable_flag = Column(Boolean, default=False)
    daily_limit_amount = Column(Numeric(14, 2), nullable=True)
    monthly_limit_amount = Column(Numeric(14, 2), nullable=True)
    active_flag = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("ExpenseClaimLine", back_populates="category")
    policies = relationship("ExpensePolicy", back_populates="category")


# ── Expense Policy ────────────────────────────────────────────────────────────

class ExpensePolicy(Base):
    __tablename__ = "expense_policies"

    expense_policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name = Column(String(150), nullable=False)
    employee_grade_id = Column(UUID(as_uuid=True), nullable=True)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.expense_category_id"), nullable=False)
    max_amount_per_line = Column(Numeric(14, 2), nullable=True)
    max_amount_per_day = Column(Numeric(14, 2), nullable=True)
    max_amount_per_month = Column(Numeric(14, 2), nullable=True)
    receipt_required_above_amount = Column(Numeric(14, 2), nullable=True)
    approval_level_required = Column(Integer, default=1)
    active_flag = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("ExpenseCategory", back_populates="policies")


# ── Expense Claim Header ──────────────────────────────────────────────────────

class ExpenseClaim(Base):
    __tablename__ = "expense_claims"

    expense_claim_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_no = Column(String(30), unique=True, nullable=False)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    claim_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    currency = Column(String(3), default="KES")
    total_claimed_amount = Column(Numeric(14, 2), default=0)
    total_approved_amount = Column(Numeric(14, 2), default=0)
    total_rejected_amount = Column(Numeric(14, 2), default=0)
    advance_deducted = Column(Numeric(14, 2), default=0)
    reimbursement_method = Column(Enum(ReimbursementMethod), default=ReimbursementMethod.BANK)
    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT)
    submitted_at = Column(DateTime, nullable=True)
    approved_by_manager = Column(UUID(as_uuid=True), nullable=True)
    manager_approved_at = Column(DateTime, nullable=True)
    approved_by_finance = Column(UUID(as_uuid=True), nullable=True)
    finance_approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    advance_id = Column(UUID(as_uuid=True), ForeignKey("expense_advances.advance_id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = relationship("ExpenseClaimLine", back_populates="claim", cascade="all, delete-orphan")
    advance = relationship("ExpenseAdvance", back_populates="claims")


# ── Expense Claim Line ────────────────────────────────────────────────────────

class ExpenseClaimLine(Base):
    __tablename__ = "expense_claim_lines"

    expense_line_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_claim_id = Column(UUID(as_uuid=True), ForeignKey("expense_claims.expense_claim_id"), nullable=False)
    expense_category_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.expense_category_id"), nullable=False)
    expense_date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    vendor_name = Column(String(150), nullable=True)
    receipt_no = Column(String(100), nullable=True)
    claimed_amount = Column(Numeric(14, 2), nullable=False)
    approved_amount = Column(Numeric(14, 2), nullable=True)
    tax_amount = Column(Numeric(14, 2), default=0)
    currency = Column(String(3), default="KES")
    payment_method_used = Column(String(50), nullable=True)
    cost_center_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    sales_route_id = Column(UUID(as_uuid=True), nullable=True)
    attachment_ref = Column(String(500), nullable=True)
    policy_violation_flag = Column(Boolean, default=False)
    policy_violation_note = Column(Text, nullable=True)
    policy_violation_severity = Column(Enum(PolicyViolationSeverity), nullable=True)
    line_status = Column(String(30), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("ExpenseClaim", back_populates="lines")
    category = relationship("ExpenseCategory", back_populates="lines")


# ── Expense Advance ───────────────────────────────────────────────────────────

class ExpenseAdvance(Base):
    __tablename__ = "expense_advances"

    advance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    advance_no = Column(String(30), unique=True, nullable=False)
    advance_date = Column(Date, nullable=False)
    advance_amount = Column(Numeric(14, 2), nullable=False)
    settled_amount = Column(Numeric(14, 2), default=0)
    currency = Column(String(3), default="KES")
    purpose = Column(String(255), nullable=True)
    settlement_status = Column(Enum(AdvanceSettlementStatus), default=AdvanceSettlementStatus.OPEN)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    claims = relationship("ExpenseClaim", back_populates="advance")


# ── Expense Accounting Entry ──────────────────────────────────────────────────

class ExpenseAccountingEntry(Base):
    __tablename__ = "expense_accounting_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_claim_id = Column(UUID(as_uuid=True), ForeignKey("expense_claims.expense_claim_id"), nullable=False)
    entry_date = Column(Date, nullable=False)
    debit_account = Column(String(100), nullable=False)
    credit_account = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), default=0)
    cost_center_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(String(255), nullable=True)
    posted_at = Column(DateTime, default=datetime.utcnow)


# ── AI Recommendation ─────────────────────────────────────────────────────────

class ExpAIRecommendation(Base):
    __tablename__ = "exp_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(ExpAIAgentType), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    ref_expense_claim_id = Column(UUID(as_uuid=True), nullable=True)
    ref_employee_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(ExpAIRecStatus), default=ExpAIRecStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime, nullable=True)
    actioned_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
