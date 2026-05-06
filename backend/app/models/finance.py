import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class CashAccountType(str, enum.Enum):
    CASH = "CASH"
    BANK = "BANK"
    MPESA = "MPESA"


class TxDirection(str, enum.Enum):
    RECEIPT = "RECEIPT"    # money in
    PAYMENT = "PAYMENT"    # money out


class FinTxStatus(str, enum.Enum):
    PENDING = "PENDING"
    CLEARED = "CLEARED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class ReconciliationStatus(str, enum.Enum):
    UNMATCHED = "UNMATCHED"
    MATCHED = "MATCHED"
    MANUAL = "MANUAL"
    EXCEPTION = "EXCEPTION"


class BudgetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"


class BudgetType(str, enum.Enum):
    OPEX = "OPEX"
    CAPEX = "CAPEX"


class CostType(str, enum.Enum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PACKAGING = "PACKAGING"
    LABOR = "LABOR"
    UTILITY = "UTILITY"
    OVERHEAD = "OVERHEAD"
    MARKETING_TRADE = "MARKETING_TRADE"   # trade spend (discounts, shelf fees, distributor support)
    MARKETING_BRAND = "MARKETING_BRAND"  # brand spend (media, agency, events, sampling)


# ── General Ledger ────────────────────────────────────────────────────────────

class ChartOfAccount(Base, TimestampMixin):
    """
    Chart of Accounts (COA). Supports a parent/child hierarchy.
    is_control=True marks summary accounts that cannot be posted to directly.
    """
    __tablename__ = "chart_of_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True)
    is_control = Column(Boolean, default=False, nullable=False)   # True = roll-up only
    currency = Column(String(10), nullable=False, default="KES")
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    parent = relationship("ChartOfAccount", remote_side=[id], back_populates="children")
    children = relationship("ChartOfAccount", back_populates="parent")
    journal_lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_no = Column(String(50), unique=True, nullable=False, index=True)
    entry_date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    source_module = Column(String(50), nullable=True)   # sales | procurement | production | finance
    source_id = Column(UUID(as_uuid=True), nullable=True)
    source_ref = Column(String(100), nullable=True)     # human-readable reference
    is_posted = Column(Boolean, default=False, nullable=False)
    posted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    lines = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")
    posted_by = relationship("User", foreign_keys=[posted_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class JournalLine(Base, TimestampMixin):
    __tablename__ = "journal_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False)
    description = Column(String(255), nullable=True)
    debit = Column(Numeric(18, 4), nullable=False, default=0)
    credit = Column(Numeric(18, 4), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="KES")

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("ChartOfAccount", back_populates="journal_lines")


# ── Cash / Bank / M-Pesa Accounts ─────────────────────────────────────────────

class CashAccount(Base, TimestampMixin):
    """
    Represents a physical or virtual cash account:
    - Cash float / petty cash
    - Bank account
    - M-Pesa business wallet (Lipa Na M-Pesa / Paybill / Till)
    """
    __tablename__ = "cash_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    account_type = Column(Enum(CashAccountType), nullable=False)
    account_number = Column(String(100), nullable=True)   # bank acct, Paybill/Till no.
    bank_name = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=False, default="KES")
    opening_balance = Column(Numeric(18, 4), nullable=False, default=0)
    current_balance = Column(Numeric(18, 4), nullable=False, default=0)
    gl_account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    gl_account = relationship("ChartOfAccount")
    transactions = relationship("CashTransaction", back_populates="cash_account",
                                order_by="CashTransaction.transaction_date.desc()")


class CashTransaction(Base, TimestampMixin):
    """
    One row per money movement against a CashAccount.
    M-Pesa transactions carry mpesa_phone and mpesa_receipt for reconciliation.
    source_module / source_id link back to the originating document.
    """
    __tablename__ = "cash_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_account_id = Column(UUID(as_uuid=True), ForeignKey("cash_accounts.id", ondelete="RESTRICT"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    direction = Column(Enum(TxDirection), nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    description = Column(String(255), nullable=False)
    reference = Column(String(100), nullable=True)
    status = Column(Enum(FinTxStatus), nullable=False, default=FinTxStatus.PENDING)
    # M-Pesa fields
    mpesa_phone = Column(String(20), nullable=True)
    mpesa_receipt = Column(String(100), nullable=True, index=True)
    mpesa_name = Column(String(100), nullable=True)
    # Source linkage (nullable — can be standalone)
    source_module = Column(String(50), nullable=True)
    source_id = Column(UUID(as_uuid=True), nullable=True)
    source_ref = Column(String(100), nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    cash_account = relationship("CashAccount", back_populates="transactions")
    journal_entry = relationship("JournalEntry")
    created_by = relationship("User")
    reconciliation = relationship("MpesaReconciliation", back_populates="transaction", uselist=False)


class MpesaReconciliation(Base, TimestampMixin):
    """
    Links an incoming M-Pesa CashTransaction to a sales Invoice or SalesOrder.
    Auto-match tries by amount; manual match is the fallback.
    """
    __tablename__ = "mpesa_reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_transaction_id = Column(UUID(as_uuid=True), ForeignKey("cash_transactions.id", ondelete="CASCADE"),
                                  unique=True, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(ReconciliationStatus), nullable=False, default=ReconciliationStatus.UNMATCHED)
    matched_amount = Column(Numeric(16, 4), nullable=True)
    matched_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    matched_at = Column(DateTime(timezone=True), nullable=True)
    exception_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    transaction = relationship("CashTransaction", back_populates="reconciliation")
    invoice = relationship("Invoice")
    so = relationship("SalesOrder")
    matched_by = relationship("User")


# ── Cost Accounting ───────────────────────────────────────────────────────────

class ProductCost(Base, TimestampMixin):
    """
    Rolled-up cost per product per month.
    Populated by finance_service.rollup_product_cost().
    """
    __tablename__ = "product_costs"
    __table_args__ = (UniqueConstraint("product_id", "period_ym", name="uq_product_cost_period"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    period_ym = Column(String(7), nullable=False)          # "2026-04"
    raw_material_cost = Column(Numeric(18, 4), nullable=False, default=0)
    packaging_cost = Column(Numeric(18, 4), nullable=False, default=0)
    labor_cost = Column(Numeric(18, 4), nullable=False, default=0)
    utility_cost = Column(Numeric(18, 4), nullable=False, default=0)
    overhead_cost = Column(Numeric(18, 4), nullable=False, default=0)
    total_units_produced = Column(Numeric(14, 3), nullable=False, default=0)
    standard_cost_per_unit = Column(Numeric(14, 4), nullable=True)
    actual_cost_per_unit = Column(Numeric(14, 4), nullable=True)
    variance_amount = Column(Numeric(14, 4), nullable=True)
    variance_pct = Column(Numeric(8, 4), nullable=True)

    product = relationship("Product")


class ProductionCostEntry(Base, TimestampMixin):
    """
    Individual cost line against a production order.
    RAW_MATERIAL / PACKAGING entries are auto-populated from MaterialConsumption.
    LABOR / UTILITY / OVERHEAD are entered manually or imported.
    """
    __tablename__ = "production_cost_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    cost_type = Column(Enum(CostType), nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=True)
    unit_cost = Column(Numeric(14, 4), nullable=True)
    period_ym = Column(String(7), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    production_order = relationship("ProductionOrder")
    product = relationship("Product")
    created_by = relationship("User")


# ── Budget ────────────────────────────────────────────────────────────────────

class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("year", "department", "version", name="uq_budget_year_dept_ver"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year = Column(Integer, nullable=False)
    department = Column(String(100), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    status = Column(Enum(BudgetStatus), nullable=False, default=BudgetStatus.DRAFT)
    budget_type = Column(Enum(BudgetType), nullable=False, default=BudgetType.OPEX)
    version = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    lines = relationship("BudgetLine", back_populates="budget", cascade="all, delete-orphan",
                         order_by="BudgetLine.month")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


class BudgetLine(Base, TimestampMixin):
    __tablename__ = "budget_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)        # Sales, COGS, Salaries, Utilities…
    account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True)
    month = Column(Integer, nullable=False)               # 1–12
    budgeted_amount = Column(Numeric(18, 4), nullable=False, default=0)

    budget = relationship("Budget", back_populates="lines")
    account = relationship("ChartOfAccount")


# ── Purchase Invoices ─────────────────────────────────────────────────────────

class RateSource(str, enum.Enum):
    MANUAL = "MANUAL"
    CBK = "CBK"        # Central Bank of Kenya
    ECB = "ECB"        # European Central Bank
    API = "API"


class ExchangeRate(Base, TimestampMixin):
    """
    Daily exchange rates vs KES base currency.
    One row per currency per date.
    """
    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("currency", "rate_date", name="uq_exchange_rate_date"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    currency = Column(String(10), nullable=False, index=True)   # e.g. "USD"
    rate_date = Column(Date, nullable=False, index=True)
    rate_to_kes = Column(Numeric(18, 6), nullable=False)        # 1 unit of currency = X KES
    source = Column(Enum(RateSource), nullable=False, default=RateSource.MANUAL)
    notes = Column(String(255), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User")


class PeriodStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LOCKED = "LOCKED"


class AccountingPeriod(Base, TimestampMixin):
    """
    Accounting period lock. Prevents posting to closed/locked periods.
    """
    __tablename__ = "accounting_periods"
    __table_args__ = (UniqueConstraint("period_ym", name="uq_accounting_period_ym"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_ym = Column(String(7), nullable=False, index=True)   # "2026-04"
    status = Column(Enum(PeriodStatus), nullable=False, default=PeriodStatus.OPEN)
    closed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    closed_by = relationship("User")


class PurchaseInvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RECEIVED = "RECEIVED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PurchaseInvoice(Base, TimestampMixin):
    """Supplier invoice received for goods/materials purchased."""
    __tablename__ = "purchase_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_no = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(PurchaseInvoiceStatus), nullable=False, default=PurchaseInvoiceStatus.DRAFT)
    currency = Column(String(10), nullable=False, default="KES")
    subtotal = Column(Numeric(16, 4), nullable=False, default=0)
    tax_amount = Column(Numeric(16, 4), nullable=False, default=0)
    total_amount = Column(Numeric(16, 4), nullable=False, default=0)
    paid_amount = Column(Numeric(16, 4), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier = relationship("Supplier")
    po = relationship("PurchaseOrder")
    created_by = relationship("User")
    lines = relationship("PurchaseInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("PurchasePayment", back_populates="invoice", order_by="PurchasePayment.payment_date")


class PurchaseInvoiceLine(Base, TimestampMixin):
    __tablename__ = "purchase_invoice_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(255), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(20), nullable=False, default="KG")
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    tax_rate = Column(Numeric(6, 4), nullable=False, default=0)
    line_total = Column(Numeric(16, 4), nullable=False, default=0)

    invoice = relationship("PurchaseInvoice", back_populates="lines")
    material = relationship("Material")
    product = relationship("Product")


class PurchasePayment(Base, TimestampMixin):
    """Payment made against a purchase invoice."""
    __tablename__ = "purchase_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    method = Column(String(20), nullable=False, default="bank")   # cash | bank | mpesa
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    invoice = relationship("PurchaseInvoice", back_populates="payments")
    created_by = relationship("User")
