from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.finance import (
    AccountType, CashAccountType, TxDirection, FinTxStatus,
    ReconciliationStatus, BudgetStatus, BudgetType, CostType,
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
    source_event: Optional[str] = None
    source_ref: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    lines: List[JournalLineCreate] = []


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entry_no: str
    entry_date: date
    description: str
    source_module: Optional[str]
    source_event: Optional[str] = None
    source_ref: Optional[str]
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    status: Optional["JournalStatus"] = None
    reversal_of_entry_id: Optional[uuid.UUID] = None
    reversed_by_entry_id: Optional[uuid.UUID] = None
    posting_batch_id: Optional[uuid.UUID] = None
    is_posted: bool
    posted_at: Optional[datetime]
    locked_at: Optional[datetime] = None
    created_at: datetime
    total_debit: Optional[Decimal] = None
    total_credit: Optional[Decimal] = None


class JournalEntryDetailRead(JournalEntryRead):
    lines: List[JournalLineRead] = []


class JournalReversalCreate(BaseModel):
    reversal_entry_no: str
    reversal_date: date
    description: Optional[str] = None


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
    budget_type: BudgetType = BudgetType.OPEX
    notes: Optional[str] = None
    lines: List[BudgetLineCreate] = []


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    year: int
    department: str
    currency: str
    status: BudgetStatus
    budget_type: BudgetType
    version: int
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
    utilization_pct: Optional[Decimal] = None  # actual/budgeted * 100


class BudgetAlertRow(BaseModel):
    budget_id: uuid.UUID
    department: str
    category: str
    month: int
    budgeted: Decimal
    actual: Decimal
    utilization_pct: Decimal
    alert_level: str  # WARNING (>90%) | CRITICAL (>100%)


# ── Purchase Invoices (Accounting module) ─────────────────────────────────────

from app.models.finance import (  # noqa: E402
    PurchaseInvoiceStatus, PeriodStatus, RateSource,
    FiscalYearStatus, JournalStatus,
    RecurringJournalFrequency, RecurringJournalStatus,
    PostingBatchStatus, PaymentAllocationPartyType,
    CurrencyRevaluationStatus, AccountingCloseCheckStatus,
    OperationalPostingStatus,
)


# --- Enterprise accounting core foundations ---

class FiscalYearCreate(BaseModel):
    year_code: str
    start_date: date
    end_date: date
    base_currency: str = "KES"
    retained_earnings_account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class FiscalYearUpdate(BaseModel):
    status: Optional[FiscalYearStatus] = None
    retained_earnings_account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class FiscalYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    year_code: str
    start_date: date
    end_date: date
    status: FiscalYearStatus
    base_currency: str
    retained_earnings_account_id: Optional[uuid.UUID]
    closed_by_id: Optional[uuid.UUID]
    closed_at: Optional[datetime]
    locked_by_id: Optional[uuid.UUID]
    locked_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime


class AccountingPeriodCloseCheckCreate(BaseModel):
    period_id: uuid.UUID
    check_code: str
    label: str
    status: AccountingCloseCheckStatus = AccountingCloseCheckStatus.PENDING
    result_summary: Optional[str] = None


class AccountingPeriodCloseCheckUpdate(BaseModel):
    status: AccountingCloseCheckStatus
    result_summary: Optional[str] = None


class AccountingPeriodCloseCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    period_id: uuid.UUID
    check_code: str
    label: str
    status: AccountingCloseCheckStatus
    result_summary: Optional[str]
    checked_by_id: Optional[uuid.UUID]
    checked_at: Optional[datetime]
    created_at: datetime


class RecurringJournalTemplateLineCreate(BaseModel):
    account_id: uuid.UUID
    description: Optional[str] = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    cost_center_id: Optional[uuid.UUID] = None


class RecurringJournalTemplateLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    template_id: uuid.UUID
    account_id: uuid.UUID
    description: Optional[str]
    debit: Decimal
    credit: Decimal
    cost_center_id: Optional[uuid.UUID]


class RecurringJournalTemplateCreate(BaseModel):
    template_no: str
    name: str
    description: Optional[str] = None
    frequency: RecurringJournalFrequency
    start_date: date
    end_date: Optional[date] = None
    next_run_date: date
    default_memo: Optional[str] = None
    lines: List[RecurringJournalTemplateLineCreate] = []


class RecurringJournalTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[RecurringJournalFrequency] = None
    status: Optional[RecurringJournalStatus] = None
    end_date: Optional[date] = None
    next_run_date: Optional[date] = None
    default_memo: Optional[str] = None


class RecurringJournalTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    template_no: str
    name: str
    description: Optional[str]
    frequency: RecurringJournalFrequency
    status: RecurringJournalStatus
    start_date: date
    end_date: Optional[date]
    next_run_date: date
    last_run_date: Optional[date]
    default_memo: Optional[str]
    created_by_id: Optional[uuid.UUID]
    created_at: datetime
    lines: List[RecurringJournalTemplateLineRead] = []


class AccountingPostingBatchCreate(BaseModel):
    source_module: str
    source_event: str
    source_id: str
    source_ref: Optional[str] = None
    idempotency_key: str


class AccountingPostingBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_module: str
    source_event: str
    source_id: str
    source_ref: Optional[str]
    status: PostingBatchStatus
    journal_entry_id: Optional[uuid.UUID]
    idempotency_key: str
    error_message: Optional[str]
    posted_by_id: Optional[uuid.UUID]
    posted_at: Optional[datetime]
    created_at: datetime


class AccountingPostingRuleCreate(BaseModel):
    source_module: str
    source_event: str
    rule_name: str
    debit_account_id: Optional[uuid.UUID] = None
    credit_account_id: Optional[uuid.UUID] = None
    tax_account_id: Optional[uuid.UUID] = None
    clearing_account_id: Optional[uuid.UUID] = None
    priority: int = 100
    notes: Optional[str] = None


class AccountingPostingRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    debit_account_id: Optional[uuid.UUID] = None
    credit_account_id: Optional[uuid.UUID] = None
    tax_account_id: Optional[uuid.UUID] = None
    clearing_account_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class AccountingPostingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_module: str
    source_event: str
    rule_name: str
    debit_account_id: Optional[uuid.UUID]
    credit_account_id: Optional[uuid.UUID]
    tax_account_id: Optional[uuid.UUID]
    clearing_account_id: Optional[uuid.UUID]
    is_active: bool
    priority: int
    notes: Optional[str]
    created_at: datetime


class OperationalPostingLinkRead(BaseModel):
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None


class OperationalPostingEventCreate(BaseModel):
    source_module: str
    source_event: str
    source_id: str
    source_line_id: Optional[str] = None
    stock_movement_id: Optional[uuid.UUID] = None
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    status: OperationalPostingStatus = OperationalPostingStatus.PENDING
    event_date: date
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    idempotency_key: str
    reversal_event_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None


class OperationalPostingEventUpdate(BaseModel):
    posting_batch_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    status: Optional[OperationalPostingStatus] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    reversal_event_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None


class OperationalPostingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_module: str
    source_event: str
    source_id: str
    source_line_id: Optional[str]
    stock_movement_id: Optional[uuid.UUID]
    posting_batch_id: Optional[uuid.UUID]
    journal_entry_id: Optional[uuid.UUID]
    status: OperationalPostingStatus
    event_date: date
    amount: Optional[Decimal]
    currency: Optional[str]
    idempotency_key: str
    reversal_event_id: Optional[uuid.UUID]
    error_message: Optional[str]
    created_by_id: Optional[uuid.UUID]
    created_at: datetime


class InventoryAccountMappingBase(BaseModel):
    stock_type: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    category_key: Optional[str] = None
    valuation_method: Optional[str] = None
    inventory_account_id: Optional[uuid.UUID] = None
    wip_account_id: Optional[uuid.UUID] = None
    finished_goods_account_id: Optional[uuid.UUID] = None
    cogs_account_id: Optional[uuid.UUID] = None
    grni_account_id: Optional[uuid.UUID] = None
    landed_cost_clearing_account_id: Optional[uuid.UUID] = None
    variance_account_id: Optional[uuid.UUID] = None
    scrap_account_id: Optional[uuid.UUID] = None
    is_active: bool = True
    priority: int = 100
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_mapping_scope(self):
        if not any([self.stock_type, self.product_id, self.material_id, self.category_key]):
            raise ValueError("At least one mapping scope is required")
        return self


class InventoryAccountMappingCreate(InventoryAccountMappingBase):
    pass


class InventoryAccountMappingUpdate(BaseModel):
    stock_type: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    category_key: Optional[str] = None
    valuation_method: Optional[str] = None
    inventory_account_id: Optional[uuid.UUID] = None
    wip_account_id: Optional[uuid.UUID] = None
    finished_goods_account_id: Optional[uuid.UUID] = None
    cogs_account_id: Optional[uuid.UUID] = None
    grni_account_id: Optional[uuid.UUID] = None
    landed_cost_clearing_account_id: Optional[uuid.UUID] = None
    variance_account_id: Optional[uuid.UUID] = None
    scrap_account_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class InventoryAccountMappingRead(InventoryAccountMappingBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class PaymentAllocationCreate(BaseModel):
    party_type: PaymentAllocationPartyType
    customer_payment_id: Optional[uuid.UUID] = None
    supplier_payment_id: Optional[uuid.UUID] = None
    sales_invoice_id: Optional[uuid.UUID] = None
    purchase_invoice_id: Optional[uuid.UUID] = None
    allocated_amount: Decimal
    allocation_date: date
    notes: Optional[str] = None


class PaymentAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    party_type: PaymentAllocationPartyType
    customer_payment_id: Optional[uuid.UUID]
    supplier_payment_id: Optional[uuid.UUID]
    sales_invoice_id: Optional[uuid.UUID]
    purchase_invoice_id: Optional[uuid.UUID]
    allocated_amount: Decimal
    allocation_date: date
    notes: Optional[str]
    created_by_id: Optional[uuid.UUID]
    created_at: datetime


class CurrencyRevaluationLineCreate(BaseModel):
    account_id: uuid.UUID
    foreign_currency_balance: Decimal = Decimal("0")
    book_base_balance: Decimal = Decimal("0")
    revalued_base_balance: Decimal = Decimal("0")
    gain_loss_amount: Decimal = Decimal("0")


class CurrencyRevaluationLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    run_id: uuid.UUID
    account_id: uuid.UUID
    foreign_currency_balance: Decimal
    book_base_balance: Decimal
    revalued_base_balance: Decimal
    gain_loss_amount: Decimal


class CurrencyRevaluationRunCreate(BaseModel):
    run_no: str
    as_of_date: date
    currency: str
    rate_id: Optional[uuid.UUID] = None
    unrealized_gain_account_id: Optional[uuid.UUID] = None
    unrealized_loss_account_id: Optional[uuid.UUID] = None
    lines: List[CurrencyRevaluationLineCreate] = []


class CurrencyRevaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    run_no: str
    as_of_date: date
    currency: str
    rate_id: Optional[uuid.UUID]
    status: CurrencyRevaluationStatus
    journal_entry_id: Optional[uuid.UUID]
    unrealized_gain_account_id: Optional[uuid.UUID]
    unrealized_loss_account_id: Optional[uuid.UUID]
    created_by_id: Optional[uuid.UUID]
    posted_by_id: Optional[uuid.UUID]
    posted_at: Optional[datetime]
    created_at: datetime
    lines: List[CurrencyRevaluationLineRead] = []


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


# ── General Ledger Reports ────────────────────────────────────────────────────

class TrialBalanceRow(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: AccountType
    total_debit: Decimal
    total_credit: Decimal
    net_balance: Decimal  # debit - credit; sign convention per account type


class GLTransactionRow(BaseModel):
    entry_id: uuid.UUID
    entry_no: str
    entry_date: date
    description: str
    source_module: Optional[str]
    source_ref: Optional[str]
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class GLAccountDrillDown(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: AccountType
    opening_balance: Decimal
    closing_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    transactions: List[GLTransactionRow] = []


class PLLineItem(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    amount: Decimal


class PLStatement(BaseModel):
    from_date: date
    to_date: date
    revenue_lines: List[PLLineItem] = []
    expense_lines: List[PLLineItem] = []
    total_revenue: Decimal
    total_expenses: Decimal
    gross_profit: Decimal
    net_income: Decimal


class BSLineItem(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    balance: Decimal


class BalanceSheetStatement(BaseModel):
    as_of_date: date
    asset_lines: List[BSLineItem] = []
    liability_lines: List[BSLineItem] = []
    equity_lines: List[BSLineItem] = []
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    is_balanced: bool


# ── Accounting Periods ────────────────────────────────────────────────────────

class PeriodCreate(BaseModel):
    period_ym: str   # "YYYY-MM"
    fiscal_year_id: Optional[uuid.UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    notes: Optional[str] = None


class PeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    period_ym: str
    fiscal_year_id: Optional[uuid.UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: PeriodStatus
    closed_at: Optional[datetime]
    close_notes: Optional[str] = None
    locked_by_id: Optional[uuid.UUID] = None
    locked_at: Optional[datetime] = None
    notes: Optional[str]
    created_at: datetime


# ── Exchange Rates ────────────────────────────────────────────────────────────

class ExchangeRateCreate(BaseModel):
    currency: str
    rate_date: date
    rate_to_kes: Decimal
    source: RateSource = RateSource.MANUAL
    notes: Optional[str] = None


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    currency: str
    rate_date: date
    rate_to_kes: Decimal
    source: RateSource
    notes: Optional[str]
    created_at: datetime


class FXConvertResult(BaseModel):
    from_currency: str
    to_currency: str
    amount: Decimal
    rate: Decimal
    converted_amount: Decimal
    rate_date: date
