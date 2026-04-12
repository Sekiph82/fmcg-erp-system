from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.finance import (
    AccountType, CashAccountType, TxDirection, FinTxStatus,
    ReconciliationStatus, BudgetStatus, CostType,
)


# ── Chart of Accounts ─────────────────────────────────────────────────────────

class COACreate(BaseModel):
    code: str
    name: str
    account_type: AccountType
    parent_id: Optional[uuid.UUID] = None
    is_control: bool = False
    currency: str = "KES"
    notes: Optional[str] = None


class COAUpdate(BaseModel):
    name: Optional[str] = None
    is_control: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class COARead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    parent_id: Optional[uuid.UUID]
    is_control: bool
    currency: str
    is_active: bool
    notes: Optional[str]
    created_at: datetime


# ── Journal Entry ─────────────────────────────────────────────────────────────

class JournalLineCreate(BaseModel):
    account_id: uuid.UUID
    description: Optional[str] = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    currency: str = "KES"


class JournalLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    description: Optional[str]
    debit: Decimal
    credit: Decimal
    currency: str


class JournalEntryCreate(BaseModel):
    entry_no: str
    entry_date: date
    description: str
    source_module: Optional[str] = None
    source_ref: Optional[str] = None
    notes: Optional[str] = None
    lines: List[JournalLineCreate] = []


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entry_no: str
    entry_date: date
    description: str
    source_module: Optional[str]
    source_ref: Optional[str]
    is_posted: bool
    posted_at: Optional[datetime]
    created_at: datetime
    total_debit: Optional[Decimal] = None
    total_credit: Optional[Decimal] = None


class JournalEntryDetailRead(JournalEntryRead):
    lines: List[JournalLineRead] = []


# ── Cash Accounts ─────────────────────────────────────────────────────────────

class CashAccountCreate(BaseModel):
    name: str
    account_type: CashAccountType
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    currency: str = "KES"
    opening_balance: Decimal = Decimal("0")
    gl_account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class CashAccountUpdate(BaseModel):
    name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    gl_account_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CashAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    account_type: CashAccountType
    account_number: Optional[str]
    bank_name: Optional[str]
    currency: str
    opening_balance: Decimal
    current_balance: Decimal
    gl_account_id: Optional[uuid.UUID]
    is_active: bool
    notes: Optional[str]
    created_at: datetime


# ── Cash Transactions ─────────────────────────────────────────────────────────

class CashTransactionCreate(BaseModel):
    cash_account_id: uuid.UUID
    transaction_date: date
    direction: TxDirection
    amount: Decimal
    description: str
    reference: Optional[str] = None
    status: FinTxStatus = FinTxStatus.PENDING
    # M-Pesa
    mpesa_phone: Optional[str] = None
    mpesa_receipt: Optional[str] = None
    mpesa_name: Optional[str] = None
    # Source link
    source_module: Optional[str] = None
    source_ref: Optional[str] = None


class CashTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cash_account_id: uuid.UUID
    cash_account_name: Optional[str] = None
    cash_account_type: Optional[CashAccountType] = None
    transaction_date: date
    direction: TxDirection
    amount: Decimal
    description: str
    reference: Optional[str]
    status: FinTxStatus
    mpesa_phone: Optional[str]
    mpesa_receipt: Optional[str]
    mpesa_name: Optional[str]
    source_module: Optional[str]
    source_ref: Optional[str]
    created_at: datetime
    reconciliation_status: Optional[ReconciliationStatus] = None


# ── M-Pesa Reconciliation ─────────────────────────────────────────────────────

class ManualMatchRequest(BaseModel):
    invoice_id: Optional[uuid.UUID] = None
    so_id: Optional[uuid.UUID] = None
    matched_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class ReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cash_transaction_id: uuid.UUID
    invoice_id: Optional[uuid.UUID]
    invoice_no: Optional[str] = None
    so_id: Optional[uuid.UUID]
    so_no: Optional[str] = None
    status: ReconciliationStatus
    matched_amount: Optional[Decimal]
    exception_reason: Optional[str]
    notes: Optional[str]
    matched_at: Optional[datetime]
    created_at: datetime
    # Denormalised from the transaction for convenience
    tx_date: Optional[date] = None
    tx_amount: Optional[Decimal] = None
    mpesa_receipt: Optional[str] = None
    mpesa_phone: Optional[str] = None
    mpesa_name: Optional[str] = None


# ── Cost Accounting ───────────────────────────────────────────────────────────

class ProductionCostEntryCreate(BaseModel):
    production_order_id: uuid.UUID
    product_id: uuid.UUID
    cost_type: CostType
    amount: Decimal
    quantity: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    period_ym: str   # "YYYY-MM"
    notes: Optional[str] = None


class ProductionCostEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    production_order_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    cost_type: CostType
    amount: Decimal
    quantity: Optional[Decimal]
    unit_cost: Optional[Decimal]
    period_ym: str
    notes: Optional[str]
    created_at: datetime


class ProductCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    period_ym: str
    raw_material_cost: Decimal
    packaging_cost: Decimal
    labor_cost: Decimal
    utility_cost: Decimal
    overhead_cost: Decimal
    total_units_produced: Decimal
    standard_cost_per_unit: Optional[Decimal]
    actual_cost_per_unit: Optional[Decimal]
    variance_amount: Optional[Decimal]
    variance_pct: Optional[Decimal]
    updated_at: Optional[datetime] = None


# ── Budget ────────────────────────────────────────────────────────────────────

class BudgetLineCreate(BaseModel):
    category: str
    account_id: Optional[uuid.UUID] = None
    month: int                           # 1–12
    budgeted_amount: Decimal


class BudgetLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: str
    account_id: Optional[uuid.UUID]
    month: int
    budgeted_amount: Decimal


class BudgetCreate(BaseModel):
    year: int
    department: str
    currency: str = "KES"
    notes: Optional[str] = None
    lines: List[BudgetLineCreate] = []


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    year: int
    department: str
    currency: str
    status: BudgetStatus
    notes: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]
    total_budgeted: Optional[Decimal] = None


class BudgetDetailRead(BudgetRead):
    lines: List[BudgetLineRead] = []


# ── Reports ───────────────────────────────────────────────────────────────────

class CashPositionRow(BaseModel):
    account_id: uuid.UUID
    account_name: str
    account_type: CashAccountType
    currency: str
    balance: Decimal
    pending_in: Decimal
    pending_out: Decimal
    cleared_balance: Decimal


class MpesaSummaryRow(BaseModel):
    date: date
    receipt_count: int
    total_received: Decimal
    matched_count: int
    unmatched_count: int
    failed_count: int


class PaymentChannelRow(BaseModel):
    channel: str        # CASH | BANK | MPESA
    receipt_count: int
    total_amount: Decimal
    pct_of_total: Decimal


class ReceivableRow(BaseModel):
    invoice_id: uuid.UUID
    invoice_no: str
    customer_name: str
    invoice_date: date
    due_date: date
    total_amount: Decimal
    paid_amount: Decimal
    outstanding: Decimal
    days_overdue: Optional[int]
    currency: str


class ReconciliationExceptionRow(BaseModel):
    transaction_id: uuid.UUID
    transaction_date: date
    mpesa_receipt: Optional[str]
    mpesa_phone: Optional[str]
    amount: Decimal
    description: str
    status: ReconciliationStatus
    exception_reason: Optional[str]


class BudgetVsActualRow(BaseModel):
    department: str
    category: str
    month: int
    budgeted: Decimal
    actual: Decimal
    variance: Decimal
    variance_pct: Optional[Decimal]


# ── Purchase Invoices (Accounting module) ─────────────────────────────────────

from app.models.finance import PurchaseInvoiceStatus  # noqa: E402


class PurchaseInvoiceLineCreate(BaseModel):
    material_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    quantity: Decimal
    unit: str = "KG"
    unit_price: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")


class PurchaseInvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    material_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    description: Optional[str]
    quantity: Decimal
    unit: str
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal
    material_name: Optional[str] = None
    product_name: Optional[str] = None


class PurchaseInvoiceCreate(BaseModel):
    invoice_no: str
    supplier_id: uuid.UUID
    po_id: Optional[uuid.UUID] = None
    invoice_date: date
    due_date: date
    currency: str = "KES"
    notes: Optional[str] = None
    lines: List[PurchaseInvoiceLineCreate] = []


class PurchaseInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_no: str
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    po_id: Optional[uuid.UUID]
    po_no: Optional[str] = None
    invoice_date: date
    due_date: date
    status: PurchaseInvoiceStatus
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    notes: Optional[str]
    created_at: datetime
    lines: List[PurchaseInvoiceLineRead] = []


# ── Purchase Payments ─────────────────────────────────────────────────────────

class PurchasePaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    payment_date: date
    amount: Decimal
    method: str = "bank"   # cash | bank | mpesa
    reference: Optional[str] = None
    notes: Optional[str] = None


class PurchasePaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    payment_date: date
    amount: Decimal
    method: str
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Customer Payment (extended read with method) ──────────────────────────────

class CustomerPaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    payment_date: date
    amount: Decimal
    method: str = "cash"   # cash | bank | mpesa
    reference: Optional[str] = None
    notes: Optional[str] = None


class CustomerPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_no: Optional[str] = None
    customer_name: Optional[str] = None
    payment_date: date
    amount: Decimal
    method: str
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Ledgers ───────────────────────────────────────────────────────────────────

class CustomerLedgerRow(BaseModel):
    customer_id: uuid.UUID
    customer_code: str
    customer_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal


class SupplierLedgerRow(BaseModel):
    supplier_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    total_purchases: Decimal
    total_paid: Decimal
    outstanding_payable: Decimal


# ── Accounting Dashboard ──────────────────────────────────────────────────────

class AccountingDashboard(BaseModel):
    total_revenue: Decimal
    total_receivables: Decimal
    total_cost: Decimal
    total_payables: Decimal
    cash_flow: Decimal
    overdue_sales_invoices: int
    overdue_purchase_invoices: int
    recent_sales_invoices: List[dict] = []
    recent_purchase_invoices: List[dict] = []
