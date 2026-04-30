from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.expenses import (
    ExpenseStatus, ReimbursementMethod, AdvanceSettlementStatus,
    PolicyViolationSeverity, ExpAIAgentType, ExpAIRecStatus,
)


# ── Category ──────────────────────────────────────────────────────────────────

class ExpenseCategoryCreate(BaseModel):
    category_code: str
    category_name: str
    default_gl_account_id: Optional[UUID] = None
    default_cost_center_id: Optional[UUID] = None
    receipt_required_flag: bool = True
    approval_required_flag: bool = True
    taxable_flag: bool = False
    daily_limit_amount: Optional[Decimal] = None
    monthly_limit_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class ExpenseCategoryRead(ExpenseCategoryCreate):
    expense_category_id: UUID
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Policy ────────────────────────────────────────────────────────────────────

class ExpensePolicyCreate(BaseModel):
    policy_name: str
    category_id: UUID
    employee_grade_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    max_amount_per_line: Optional[Decimal] = None
    max_amount_per_day: Optional[Decimal] = None
    max_amount_per_month: Optional[Decimal] = None
    receipt_required_above_amount: Optional[Decimal] = None
    approval_level_required: int = 1
    notes: Optional[str] = None


class ExpensePolicyRead(ExpensePolicyCreate):
    expense_policy_id: UUID
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Claim Line ────────────────────────────────────────────────────────────────

class ExpenseClaimLineCreate(BaseModel):
    expense_category_id: UUID
    expense_date: date
    description: str
    vendor_name: Optional[str] = None
    receipt_no: Optional[str] = None
    claimed_amount: Decimal
    tax_amount: Decimal = Decimal("0")
    currency: str = "KES"
    payment_method_used: Optional[str] = None
    cost_center_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    sales_route_id: Optional[UUID] = None
    attachment_ref: Optional[str] = None
    notes: Optional[str] = None


class ExpenseClaimLineRead(ExpenseClaimLineCreate):
    expense_line_id: UUID
    expense_claim_id: UUID
    approved_amount: Optional[Decimal]
    policy_violation_flag: bool
    policy_violation_note: Optional[str]
    policy_violation_severity: Optional[PolicyViolationSeverity]
    line_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseClaimLineApprove(BaseModel):
    expense_line_id: UUID
    approved_amount: Decimal
    notes: Optional[str] = None


# ── Claim Header ─────────────────────────────────────────────────────────────

class ExpenseClaimCreate(BaseModel):
    employee_id: UUID
    department_id: Optional[UUID] = None
    claim_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: str = "KES"
    reimbursement_method: ReimbursementMethod = ReimbursementMethod.BANK
    advance_id: Optional[UUID] = None
    notes: Optional[str] = None
    lines: List[ExpenseClaimLineCreate] = []


class ExpenseClaimRead(BaseModel):
    expense_claim_id: UUID
    claim_no: str
    employee_id: UUID
    department_id: Optional[UUID]
    claim_date: date
    period_start: Optional[date]
    period_end: Optional[date]
    currency: str
    total_claimed_amount: Decimal
    total_approved_amount: Decimal
    total_rejected_amount: Decimal
    advance_deducted: Decimal
    reimbursement_method: ReimbursementMethod
    status: ExpenseStatus
    submitted_at: Optional[datetime]
    approved_by_manager: Optional[UUID]
    manager_approved_at: Optional[datetime]
    approved_by_finance: Optional[UUID]
    finance_approved_at: Optional[datetime]
    rejected_by: Optional[UUID]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    paid_at: Optional[datetime]
    payment_reference: Optional[str]
    advance_id: Optional[UUID]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    lines: List[ExpenseClaimLineRead] = []

    model_config = {"from_attributes": True}


class ExpenseClaimApproveReject(BaseModel):
    approver_id: UUID
    notes: Optional[str] = None
    line_approvals: Optional[List[ExpenseClaimLineApprove]] = None


class ExpenseClaimPayRequest(BaseModel):
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    advance_deducted: Optional[Decimal] = None


# ── Advance ───────────────────────────────────────────────────────────────────

class ExpenseAdvanceCreate(BaseModel):
    employee_id: UUID
    advance_date: date
    advance_amount: Decimal
    currency: str = "KES"
    purpose: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class ExpenseAdvanceRead(ExpenseAdvanceCreate):
    advance_id: UUID
    advance_no: str
    settled_amount: Decimal
    settlement_status: AdvanceSettlementStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseAdvanceSettle(BaseModel):
    expense_claim_id: UUID
    settle_amount: Decimal


# ── Reports ───────────────────────────────────────────────────────────────────

class ExpenseDashboardResponse(BaseModel):
    total_claims: int
    pending_approval: int
    approved_unpaid: int
    total_reimbursed_month: Decimal
    total_claimed_month: Decimal
    policy_violations_open: int
    overdue_advances: int
    ai_alerts: int


# ── AI ────────────────────────────────────────────────────────────────────────

class ExpAIRecRead(BaseModel):
    rec_id: UUID
    agent_type: ExpAIAgentType
    subject: str
    body: str
    ref_expense_claim_id: Optional[UUID]
    ref_employee_id: Optional[UUID]
    status: ExpAIRecStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpAIRecAck(BaseModel):
    status: ExpAIRecStatus
    notes: Optional[str] = None
