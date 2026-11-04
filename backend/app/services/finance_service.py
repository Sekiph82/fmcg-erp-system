"""
Finance module service layer.

Responsibilities:
- Roll-up production costs from MaterialConsumption records
- Auto-match incoming M-Pesa receipts to outstanding invoices
- Compute daily cash position and M-Pesa summary reports
- Budget vs. actual queries
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional, Sequence, Tuple
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    CashAccount, CashTransaction, MpesaReconciliation,
    ProductCost, ProductionCostEntry, BudgetLine,
    ChartOfAccount, JournalEntry, JournalLine, ExchangeRate,
    CashAccountType, TxDirection, FinTxStatus, ReconciliationStatus, CostType, BudgetStatus,
    AccountType, AccountingPeriod, FiscalYear, PeriodStatus, FiscalYearStatus,
    JournalStatus, AccountingPostingBatch, PostingBatchStatus,
    InventoryAccountMapping, OperationalPostingEvent, OperationalPostingStatus,
)
from app.models.production import ProductionOrder, ProductionOrderStatus, MaterialConsumption
from app.models.sales import Invoice, SalesOrder, InvoiceStatus
from sqlalchemy import extract
from app.models.finance import Budget as BudgetModel
from app.schemas.finance import (
    CashPositionRow, MpesaSummaryRow, PaymentChannelRow,
    ReceivableRow, ReconciliationExceptionRow, BudgetVsActualRow, BudgetAlertRow,
    TrialBalanceRow, GLAccountDrillDown, GLTransactionRow,
    PLStatement, PLLineItem, BalanceSheetStatement, BSLineItem,
    FXConvertResult,
)


def _period_ym(value: date) -> str:
    return value.strftime("%Y-%m")


def validate_journal_lines_balance(
    lines: Sequence[JournalLine | dict],
    tolerance: Decimal = Decimal("0.005"),
) -> tuple[Decimal, Decimal]:
    if not lines:
        raise ValueError("Journal entry must include at least one line")

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for line in lines:
        debit = Decimal(str(line.get("debit", 0) if isinstance(line, dict) else line.debit or 0))
        credit = Decimal(str(line.get("credit", 0) if isinstance(line, dict) else line.credit or 0))
        if debit < 0 or credit < 0:
            raise ValueError("Journal line debit and credit amounts cannot be negative")
        if debit > 0 and credit > 0:
            raise ValueError("Journal line cannot have both debit and credit amounts")
        if debit == 0 and credit == 0:
            raise ValueError("Journal line must have either a debit or credit amount")
        total_debit += debit
        total_credit += credit

    if abs(total_debit - total_credit) > tolerance:
        raise ValueError(f"Journal entry is unbalanced: debit={total_debit} credit={total_credit}")
    return total_debit, total_credit


async def get_accounting_period_for_date(db: AsyncSession, posting_date: date) -> Optional[AccountingPeriod]:
    range_result = await db.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.period_start.is_not(None),
            AccountingPeriod.period_end.is_not(None),
            AccountingPeriod.period_start <= posting_date,
            AccountingPeriod.period_end >= posting_date,
        )
    )
    period = range_result.scalars().first()
    if period:
        return period

    ym_result = await db.execute(
        select(AccountingPeriod).where(AccountingPeriod.period_ym == _period_ym(posting_date))
    )
    return ym_result.scalar_one_or_none()


async def assert_posting_period_open(
    db: AsyncSession,
    posting_date: date,
    *,
    require_period: bool = False,
) -> Optional[AccountingPeriod]:
    period = await get_accounting_period_for_date(db, posting_date)
    if not period:
        if require_period:
            raise ValueError(f"No accounting period exists for {posting_date.isoformat()}")
        return None

    if period.status in {PeriodStatus.CLOSED, PeriodStatus.LOCKED}:
        raise ValueError(f"Accounting period {period.period_ym} is {period.status.value}")

    if period.fiscal_year_id:
        fiscal_year = await db.get(FiscalYear, period.fiscal_year_id)
        if fiscal_year and fiscal_year.status in {FiscalYearStatus.CLOSED, FiscalYearStatus.LOCKED}:
            raise ValueError(f"Fiscal year {fiscal_year.year_code} is {fiscal_year.status.value}")

    return period


async def assert_journal_lines_postable(db: AsyncSession, lines: Sequence[JournalLine | dict]) -> None:
    account_ids: set[uuid.UUID] = set()
    for line in lines:
        account_id = line.get("account_id") if isinstance(line, dict) else line.account_id
        if account_id:
            account_ids.add(account_id)

    if not account_ids:
        raise ValueError("Journal entry must include posting accounts")

    result = await db.execute(select(ChartOfAccount).where(ChartOfAccount.id.in_(account_ids)))
    accounts = {account.id: account for account in result.scalars().all()}
    missing = account_ids - set(accounts)
    if missing:
        raise ValueError("One or more journal line accounts do not exist")

    for account in accounts.values():
        if not account.is_active:
            raise ValueError(f"Account {account.code} is inactive")
        if account.is_control:
            raise ValueError(f"Account {account.code} is a control account and cannot be posted to directly")


async def mark_journal_posted(
    db: AsyncSession,
    entry: JournalEntry,
    user_id: uuid.UUID,
    *,
    require_period: bool = False,
) -> JournalEntry:
    if entry.is_posted or entry.status == JournalStatus.POSTED:
        raise ValueError("Entry already posted")
    if entry.status in {JournalStatus.REVERSED, JournalStatus.VOID}:
        raise ValueError(f"Entry cannot be posted from status {entry.status.value}")

    validate_journal_lines_balance(entry.lines)
    await assert_journal_lines_postable(db, entry.lines)
    await assert_posting_period_open(db, entry.entry_date, require_period=require_period)

    posted_at = datetime.now(timezone.utc)
    entry.is_posted = True
    entry.status = JournalStatus.POSTED
    entry.posted_by_id = user_id
    entry.posted_at = posted_at
    entry.locked_at = posted_at
    return entry


async def create_reversal_journal(
    db: AsyncSession,
    entry: JournalEntry,
    *,
    reversal_entry_no: str,
    reversal_date: date,
    user_id: uuid.UUID,
    description: Optional[str] = None,
) -> JournalEntry:
    if not entry.is_posted:
        raise ValueError("Only posted journal entries can be reversed")
    if entry.reversed_by_entry_id:
        raise ValueError("Journal entry already has a reversal entry")

    validate_journal_lines_balance(entry.lines)
    await assert_posting_period_open(db, reversal_date)

    reversal = JournalEntry(
        entry_no=reversal_entry_no,
        entry_date=reversal_date,
        description=description or f"Reversal of {entry.entry_no}",
        source_module="finance",
        source_event="journal_reversal",
        source_id=entry.id,
        source_ref=entry.entry_no,
        status=JournalStatus.DRAFT,
        reversal_of_entry_id=entry.id,
        created_by_id=user_id,
        notes=f"System-generated reversal draft for journal entry {entry.entry_no}.",
    )
    for line in entry.lines:
        reversal.lines.append(
            JournalLine(
                account_id=line.account_id,
                description=f"Reversal: {line.description or entry.entry_no}",
                debit=line.credit,
                credit=line.debit,
                currency=line.currency,
            )
        )

    db.add(reversal)
    await db.flush()
    entry.reversed_by_entry_id = reversal.id
    return reversal


async def get_or_create_posting_batch(
    db: AsyncSession,
    *,
    source_module: str,
    source_event: str,
    source_id: str | uuid.UUID,
    idempotency_key: str,
    source_ref: Optional[str] = None,
) -> tuple[AccountingPostingBatch, bool]:
    result = await db.execute(
        select(AccountingPostingBatch).where(AccountingPostingBatch.idempotency_key == idempotency_key)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    batch = AccountingPostingBatch(
        source_module=source_module,
        source_event=source_event,
        source_id=str(source_id),
        source_ref=source_ref,
        idempotency_key=idempotency_key,
        status=PostingBatchStatus.DRAFT,
    )
    db.add(batch)
    await db.flush()
    return batch, True


def build_operational_idempotency_key(
    source_module: str,
    source_event: str,
    source_id: str | uuid.UUID,
    source_line_id: str | uuid.UUID | None = None,
) -> str:
    parts = [source_module, source_event, str(source_id)]
    if source_line_id:
        parts.append(str(source_line_id))
    return ":".join(parts)


def _account_mapping_specificity(mapping: InventoryAccountMapping) -> tuple[int, int]:
    score = 0
    if mapping.product_id:
        score += 8
    if mapping.material_id:
        score += 8
    if mapping.category_key:
        score += 4
    if mapping.stock_type:
        score += 2
    return score, -(mapping.priority or 100)


async def find_inventory_account_mapping(
    db: AsyncSession,
    *,
    stock_type: Optional[str] = None,
    product_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    category_key: Optional[str] = None,
) -> Optional[InventoryAccountMapping]:
    filters = [InventoryAccountMapping.is_active.is_(True)]
    scope_filters = []
    scope_compatibility = []
    if product_id:
        scope_filters.append(InventoryAccountMapping.product_id == product_id)
        scope_compatibility.append(or_(
            InventoryAccountMapping.product_id.is_(None),
            InventoryAccountMapping.product_id == product_id,
        ))
    else:
        scope_compatibility.append(InventoryAccountMapping.product_id.is_(None))
    if material_id:
        scope_filters.append(InventoryAccountMapping.material_id == material_id)
        scope_compatibility.append(or_(
            InventoryAccountMapping.material_id.is_(None),
            InventoryAccountMapping.material_id == material_id,
        ))
    else:
        scope_compatibility.append(InventoryAccountMapping.material_id.is_(None))
    if category_key:
        scope_filters.append(InventoryAccountMapping.category_key == category_key)
        scope_compatibility.append(or_(
            InventoryAccountMapping.category_key.is_(None),
            InventoryAccountMapping.category_key == category_key,
        ))
    else:
        scope_compatibility.append(InventoryAccountMapping.category_key.is_(None))
    if stock_type:
        scope_filters.append(InventoryAccountMapping.stock_type == stock_type)
        scope_compatibility.append(or_(
            InventoryAccountMapping.stock_type.is_(None),
            InventoryAccountMapping.stock_type == stock_type,
        ))
    else:
        scope_compatibility.append(InventoryAccountMapping.stock_type.is_(None))
    if not scope_filters:
        return None

    result = await db.execute(
        select(InventoryAccountMapping).where(
            and_(*filters, *scope_compatibility),
            or_(*scope_filters),
        )
    )
    mappings = list(result.scalars().all())
    if not mappings:
        return None
    return sorted(mappings, key=_account_mapping_specificity, reverse=True)[0]


async def get_or_create_operational_posting_event(
    db: AsyncSession,
    *,
    source_module: str,
    source_event: str,
    source_id: str | uuid.UUID,
    event_date: date,
    source_line_id: str | uuid.UUID | None = None,
    source_ref: Optional[str] = None,
    stock_movement_id: Optional[uuid.UUID] = None,
    amount: Optional[Decimal] = None,
    currency: Optional[str] = None,
    created_by_id: Optional[uuid.UUID] = None,
    require_period: bool = False,
) -> tuple[OperationalPostingEvent, AccountingPostingBatch, bool]:
    await assert_posting_period_open(db, event_date, require_period=require_period)

    idempotency_key = build_operational_idempotency_key(
        source_module,
        source_event,
        source_id,
        source_line_id,
    )
    result = await db.execute(
        select(OperationalPostingEvent).where(OperationalPostingEvent.idempotency_key == idempotency_key)
    )
    existing_event = result.scalar_one_or_none()

    batch_source_id = source_line_id or source_id
    batch, created_batch = await get_or_create_posting_batch(
        db,
        source_module=source_module,
        source_event=source_event,
        source_id=batch_source_id,
        source_ref=source_ref,
        idempotency_key=idempotency_key,
    )
    if existing_event:
        return existing_event, batch, False

    event = OperationalPostingEvent(
        source_module=source_module,
        source_event=source_event,
        source_id=str(source_id),
        source_line_id=str(source_line_id) if source_line_id else None,
        stock_movement_id=stock_movement_id,
        posting_batch_id=batch.id,
        status=OperationalPostingStatus.PENDING,
        event_date=event_date,
        amount=amount,
        currency=currency,
        idempotency_key=idempotency_key,
        created_by_id=created_by_id,
    )
    db.add(event)
    await db.flush()
    return event, batch, created_batch


def apply_operational_posting_link(
    target: Any,
    event: OperationalPostingEvent,
    *,
    journal_entry_id: Optional[uuid.UUID] = None,
    status: Optional[OperationalPostingStatus] = None,
    error_message: Optional[str] = None,
) -> None:
    if hasattr(target, "posting_batch_id"):
        target.posting_batch_id = event.posting_batch_id
    if hasattr(target, "journal_entry_id"):
        target.journal_entry_id = journal_entry_id or event.journal_entry_id
    if hasattr(target, "accounting_status"):
        target.accounting_status = status or event.status
    if hasattr(target, "posting_error"):
        target.posting_error = error_message or event.error_message


async def mark_operational_posting_posted(
    db: AsyncSession,
    event: OperationalPostingEvent,
    batch: AccountingPostingBatch,
    *,
    journal_entry_id: uuid.UUID,
    posted_by_id: Optional[uuid.UUID] = None,
) -> OperationalPostingEvent:
    now = datetime.now(timezone.utc)
    event.status = OperationalPostingStatus.POSTED
    event.journal_entry_id = journal_entry_id
    event.error_message = None

    batch.status = PostingBatchStatus.POSTED
    batch.journal_entry_id = journal_entry_id
    batch.error_message = None
    batch.posted_by_id = posted_by_id
    batch.posted_at = now

    await db.flush()
    return event


async def mark_operational_posting_failed(
    db: AsyncSession,
    event: OperationalPostingEvent,
    batch: AccountingPostingBatch,
    *,
    error_message: str,
) -> OperationalPostingEvent:
    safe_error = error_message[:2000]
    event.status = OperationalPostingStatus.FAILED
    event.error_message = safe_error

    batch.status = PostingBatchStatus.FAILED
    batch.error_message = safe_error

    await db.flush()
    return event


async def post_purchase_invoice(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID,
) -> OperationalPostingEvent:
    """Clear posted GRNI to AP for a payable, three-way-matched supplier invoice.

    The service uses only configured posting rules and item mappings. It refuses
    incomplete source receipts, stale matching snapshots, missing account setup,
    and closed periods so an invoice cannot create accounting without its
    operational evidence.
    """
    from decimal import ROUND_HALF_UP

    from app.models.company import Company
    from app.models.finance import (
        AccountingPostingRule,
        AccountType,
        PurchaseInvoice,
        PurchaseInvoiceLine,
        PurchaseInvoiceStatus,
    )
    from app.models.invoice_match import InvoiceMatchHeader, InvoiceMatchLine, MatchOverallStatus
    from app.models.procurement import GoodsReceipt, GRNLine, GRNStatus, POLine, PurchaseOrder

    money_quantum = Decimal("0.0001")

    def money(value: Decimal) -> Decimal:
        return value.quantize(money_quantum, rounding=ROUND_HALF_UP)

    try:
        invoice = await db.scalar(
            select(PurchaseInvoice)
            .where(PurchaseInvoice.id == invoice_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not invoice:
            raise ValueError("Purchase invoice not found")

        event_result = await db.execute(
            select(OperationalPostingEvent)
            .where(
                OperationalPostingEvent.source_module == "procurement",
                OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
                OperationalPostingEvent.source_id == str(invoice.id),
                OperationalPostingEvent.source_line_id.is_(None),
            )
            .with_for_update()
        )
        existing_event = event_result.scalar_one_or_none()
        if existing_event:
            batch = await db.get(AccountingPostingBatch, existing_event.posting_batch_id) \
                if existing_event.posting_batch_id else None
            journal = await db.get(JournalEntry, existing_event.journal_entry_id) \
                if existing_event.journal_entry_id else None
            if (
                existing_event.status != OperationalPostingStatus.POSTED
                or not batch or batch.status != PostingBatchStatus.POSTED
                or batch.journal_entry_id != existing_event.journal_entry_id
                or not journal or not journal.is_posted or journal.status != JournalStatus.POSTED
                or journal.source_module != "procurement"
                or journal.source_event != "PURCHASE_INVOICE_POSTED"
                or journal.source_id != invoice.id
            ):
                raise ValueError("Purchase invoice has an inconsistent prior posting; manual reconciliation is required")
            return existing_event

        if invoice.status not in {PurchaseInvoiceStatus.DRAFT, PurchaseInvoiceStatus.RECEIVED}:
            raise ValueError(f"Purchase invoice cannot be posted from status {invoice.status.value}")
        if Decimal(str(invoice.paid_amount or 0)) != 0:
            raise ValueError("A purchase invoice with recorded payments cannot be posted")
        if not invoice.po_id:
            raise ValueError("Purchase invoice posting requires a linked purchase order and GRN evidence")

        po = await db.scalar(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == invoice.po_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not po:
            raise ValueError("Purchase invoice purchase order not found")
        if po.supplier_id != invoice.supplier_id:
            raise ValueError("Purchase invoice supplier does not match its purchase order")
        company = await db.get(Company, po.company_id) if po.company_id else None
        if not company or not (company.base_currency or "").strip():
            raise ValueError("Purchase order needs a company with a configured base currency")

        invoice_currency = (invoice.currency or "").strip().upper()
        po_currency = (po.currency or "").strip().upper()
        base_currency = company.base_currency.strip().upper()
        if not invoice_currency or invoice_currency != po_currency:
            raise ValueError("Purchase invoice currency must match its purchase order currency")
        exchange_rate = Decimal(str(po.exchange_rate or 0))
        if not exchange_rate.is_finite() or exchange_rate <= 0:
            raise ValueError("Purchase order needs a positive saved exchange rate")
        if po_currency == base_currency and exchange_rate != Decimal("1"):
            raise ValueError("Purchase order base-currency exchange rate must be 1")
        if po_currency != base_currency and exchange_rate == Decimal("1"):
            raise ValueError("Foreign-currency purchase order needs a saved non-default exchange rate")

        match = await db.scalar(
            select(InvoiceMatchHeader)
            .where(InvoiceMatchHeader.invoice_id == invoice.id)
            .order_by(InvoiceMatchHeader.run_at.desc(), InvoiceMatchHeader.created_at.desc())
            .limit(1)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        payable_statuses = {
            MatchOverallStatus.FULLY_MATCHED,
            MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
            MatchOverallStatus.APPROVED_EXCEPTION,
        }
        if (
            not match or match.po_id != po.id or match.supplier_id != invoice.supplier_id
            or not match.is_payable or match.duplicate_flag
            or match.overall_status not in payable_statuses
        ):
            raise ValueError("Purchase invoice needs a current payable three-way match with no unresolved duplicate")
        if (
            match.invoice_no != invoice.invoice_no
            or match.invoice_date != invoice.invoice_date
            or (match.currency or "").strip().upper() != (invoice.currency or "").strip().upper()
            or Decimal(str(match.invoice_total)) != Decimal(str(invoice.total_amount))
        ):
            raise ValueError("Purchase invoice changed after matching; rerun matching before posting")
        if match.overall_status == MatchOverallStatus.APPROVED_EXCEPTION and not (match.approved_by and match.approved_at):
            raise ValueError("Payable exception match has no recorded approver")

        rule_result = await db.execute(
            select(AccountingPostingRule)
            .where(
                AccountingPostingRule.source_module == "procurement",
                AccountingPostingRule.source_event == "PURCHASE_INVOICE_POSTED",
                AccountingPostingRule.is_active.is_(True),
            )
            .order_by(AccountingPostingRule.priority, AccountingPostingRule.id)
        )
        rules = list(rule_result.scalars().all())
        if not rules:
            raise ValueError("Configure an active procurement purchase-invoice posting rule before posting")
        top_priority = rules[0].priority
        top_rules = [rule for rule in rules if rule.priority == top_priority]
        if len(top_rules) != 1:
            raise ValueError("Purchase-invoice posting has ambiguous active rules at the highest priority")
        rule = top_rules[0]
        if not rule.credit_account_id:
            raise ValueError("Purchase-invoice posting rule needs an accounts-payable credit account")
        ap_account = await db.get(ChartOfAccount, rule.credit_account_id)
        if not ap_account or ap_account.account_type != AccountType.LIABILITY:
            raise ValueError("Purchase-invoice accounts-payable mapping must point to a liability account")

        invoice_lines_result = await db.execute(
            select(PurchaseInvoiceLine)
            .where(PurchaseInvoiceLine.invoice_id == invoice.id)
            .order_by(PurchaseInvoiceLine.id)
            .with_for_update()
        )
        invoice_lines = list(invoice_lines_result.scalars().all())
        if not invoice_lines:
            raise ValueError("Purchase invoice needs at least one line before posting")

        match_lines_result = await db.execute(
            select(InvoiceMatchLine)
            .options(selectinload(InvoiceMatchLine.grn_links))
            .where(InvoiceMatchLine.header_id == match.id)
            .order_by(InvoiceMatchLine.invoice_line_id, InvoiceMatchLine.id)
            .with_for_update()
        )
        match_lines = list(match_lines_result.scalars().all())
        if len(match_lines) != len(invoice_lines):
            raise ValueError("Three-way match lines are incomplete; rerun matching before posting")
        match_by_invoice_line: dict[uuid.UUID, Any] = {}
        for match_line in match_lines:
            if not match_line.invoice_line_id or match_line.invoice_line_id in match_by_invoice_line:
                raise ValueError("Three-way match must contain exactly one result for each invoice line")
            if match_line.match_status not in {
                "FULLY_MATCHED", "MATCHED_WITHIN_TOLERANCE", "APPROVED_EXCEPTION",
            }:
                raise ValueError("Every invoice line must be matched or explicitly approved before posting")
            match_by_invoice_line[match_line.invoice_line_id] = match_line

        po_lines_result = await db.execute(
            select(POLine).where(POLine.po_id == po.id).order_by(POLine.line_no, POLine.id)
        )
        po_lines = list(po_lines_result.scalars().all())
        po_line_by_id = {line.id: line for line in po_lines}

        grn_result = await db.execute(
            select(GRNLine)
            .join(GoodsReceipt, GoodsReceipt.id == GRNLine.grn_id)
            .options(selectinload(GRNLine.grn))
            .where(GoodsReceipt.po_id == po.id, GoodsReceipt.status == GRNStatus.POSTED)
            .order_by(GoodsReceipt.received_date, GoodsReceipt.id, GRNLine.id)
            .with_for_update(of=GRNLine)
        )
        grn_lines = list(grn_result.scalars().all())
        grn_by_po_line: dict[uuid.UUID, list[GRNLine]] = {}
        for grn_line in grn_lines:
            if grn_line.po_line_id in po_line_by_id:
                grn_by_po_line.setdefault(grn_line.po_line_id, []).append(grn_line)

        prior_result = await db.execute(
            select(InvoiceMatchLine.po_line_id, func.sum(InvoiceMatchLine.invoiced_qty))
            .join(InvoiceMatchHeader, InvoiceMatchHeader.id == InvoiceMatchLine.header_id)
            .where(
                InvoiceMatchHeader.po_id == po.id,
                InvoiceMatchHeader.invoice_id != invoice.id,
                InvoiceMatchHeader.overall_status.in_([status.value for status in payable_statuses]),
            )
            .group_by(InvoiceMatchLine.po_line_id)
        )
        prior_billed = {row[0]: Decimal(str(row[1] or 0)) for row in prior_result.all()}

        journal_lines: dict[uuid.UUID, dict[str, Any]] = {}

        def add_line(account: ChartOfAccount, description: str, *, debit: Decimal = Decimal("0"),
                     credit: Decimal = Decimal("0")) -> None:
            if account.id not in journal_lines:
                journal_lines[account.id] = {
                    "account": account,
                    "description": description[:255],
                    "debit": Decimal("0"),
                    "credit": Decimal("0"),
                }
            journal_lines[account.id]["debit"] += debit
            journal_lines[account.id]["credit"] += credit

        subtotal_doc = Decimal("0")
        tax_doc = Decimal("0")
        ap_base_total = Decimal("0")
        has_tax = False

        # Verify that match quantities still reflect the posted receipt set and
        # previous payable bills, then clear each source's remaining GRNI value.
        for invoice_line in invoice_lines:
            match_line = match_by_invoice_line.get(invoice_line.id)
            if not match_line:
                raise ValueError("Three-way match is missing an invoice line")
            if not match_line.po_line_id or match_line.po_line_id not in po_line_by_id:
                raise ValueError("Matched invoice line has no purchase-order line")
            po_line = po_line_by_id[match_line.po_line_id]
            if (
                (invoice_line.material_id, invoice_line.product_id)
                != (po_line.material_id, po_line.product_id)
            ):
                raise ValueError("Matched invoice line item differs from its purchase-order line")

            sources = grn_by_po_line.get(po_line.id, [])
            link_by_grn_line = {
                link.grn_line_id: link for link in match_line.grn_links if link.grn_line_id
            }
            source_ids = {source.id for source in sources}
            if set(link_by_grn_line) != source_ids:
                raise ValueError("Three-way match receipt links are stale; rerun matching before posting")
            for source in sources:
                link = link_by_grn_line[source.id]
                if Decimal(str(link.accepted_qty or 0)) != Decimal(str(source.accepted_quantity)):
                    raise ValueError("Matched receipt quantity changed; rerun matching before posting")
                if (
                    source.accounting_status != OperationalPostingStatus.POSTED
                    or not source.posting_batch_id or not source.journal_entry_id
                ):
                    raise ValueError(f"GRN line {source.id} must have posted inventory/GRNI accounting first")
                batch = await db.get(AccountingPostingBatch, source.posting_batch_id)
                journal = await db.get(JournalEntry, source.journal_entry_id)
                if (
                    not batch or batch.status != PostingBatchStatus.POSTED
                    or batch.journal_entry_id != source.journal_entry_id
                    or not journal or not journal.is_posted or journal.status != JournalStatus.POSTED
                    or journal.source_module != "procurement"
                    or journal.source_event != "GRN_INVENTORY_VALUATION_POSTED"
                    or journal.source_id != source.id
                ):
                    raise ValueError(f"GRN line {source.id} has inconsistent accounting links")

            received_qty = sum((Decimal(str(source.accepted_quantity)) for source in sources), Decimal("0"))
            previous_qty = prior_billed.get(po_line.id, Decimal("0"))
            if Decimal(str(match_line.prev_invoiced_qty or 0)) != previous_qty:
                raise ValueError("Previous billed quantity changed; rerun matching before posting")
            billable_qty = max(received_qty - previous_qty, Decimal("0"))
            if Decimal(str(match_line.billable_qty or 0)) != billable_qty:
                raise ValueError("Billable receipt quantity changed; rerun matching before posting")

            quantity = Decimal(str(invoice_line.quantity))
            unit_price = Decimal(str(invoice_line.unit_price))
            tax_rate = Decimal(str(invoice_line.tax_rate))
            if (
                Decimal(str(match_line.invoiced_qty)) != quantity
                or Decimal(str(match_line.invoiced_unit_price)) != unit_price
                or Decimal(str(match_line.invoiced_tax_rate)) != tax_rate
                or money(Decimal(str(match_line.invoiced_line_total)))
                != money(Decimal(str(invoice_line.line_total)))
            ):
                raise ValueError("Purchase invoice line changed after matching; rerun matching before posting")
            if (invoice_line.unit or "").strip().upper() != (po_line.unit or "").strip().upper():
                raise ValueError("Purchase invoice unit differs from its matched purchase-order unit")
            if not quantity.is_finite() or quantity <= 0:
                raise ValueError("Purchase invoice line quantities must be positive")
            if not unit_price.is_finite() or unit_price < 0:
                raise ValueError("Purchase invoice line unit prices cannot be negative")
            if not tax_rate.is_finite() or tax_rate < 0:
                raise ValueError("Purchase invoice line tax rates cannot be negative")

            line_net_doc = money(quantity * unit_price)
            line_total_doc = money(Decimal(str(invoice_line.line_total)))
            line_tax_doc = money(line_total_doc - line_net_doc)
            expected_tax_doc = money(line_net_doc * tax_rate)
            if line_tax_doc < 0 or abs(line_tax_doc - expected_tax_doc) > money_quantum:
                raise ValueError("Purchase invoice line totals do not reconcile to its saved tax rate")
            subtotal_doc += line_net_doc
            tax_doc += line_tax_doc
            net_base = money(line_net_doc * exchange_rate)
            tax_base = money(line_tax_doc * exchange_rate)
            ap_base_total += net_base + tax_base
            has_tax = has_tax or tax_base > 0

            remaining_prior = previous_qty
            remaining_invoice_qty = quantity
            grni_amount = Decimal("0")
            variance_account = None
            for source in sources:
                accepted_qty = Decimal(str(source.accepted_quantity))
                prior_on_source = min(accepted_qty, remaining_prior)
                remaining_prior -= prior_on_source
                available_qty = accepted_qty - prior_on_source
                allocated_qty = min(available_qty, remaining_invoice_qty)
                remaining_invoice_qty -= allocated_qty
                if allocated_qty <= 0:
                    continue

                mapping = await find_inventory_account_mapping(
                    db,
                    stock_type="MATERIAL" if source.material_id else "PRODUCT",
                    material_id=source.material_id,
                    product_id=source.product_id,
                )
                if not mapping or not mapping.grni_account_id:
                    raise ValueError(f"GRN item on line {source.id} needs an active GRNI account mapping")
                grni_account = await db.get(ChartOfAccount, mapping.grni_account_id)
                if not grni_account or grni_account.account_type != AccountType.LIABILITY:
                    raise ValueError(f"GRNI mapping for GRN line {source.id} must point to a liability account")
                receipt_unit_cost = money(Decimal(str(po_line.unit_price)) * exchange_rate)
                source_accrual = money(allocated_qty * receipt_unit_cost)
                grni_amount += source_accrual
                add_line(grni_account, f"Clear GRNI for supplier invoice {invoice.invoice_no}", debit=source_accrual)
                if mapping.variance_account_id:
                    variance_account = await db.get(ChartOfAccount, mapping.variance_account_id)

            if remaining_invoice_qty > 0 and match_line.match_status not in {
                "MATCHED_WITHIN_TOLERANCE", "APPROVED_EXCEPTION",
            }:
                raise ValueError("Invoice quantity exceeds accepted receipts without an approved match tolerance")
            if remaining_invoice_qty > 0 and match_line.match_status == "MATCHED_WITHIN_TOLERANCE" \
                    and not match_line.tolerance_rule_id:
                raise ValueError("Invoice quantity excess has no recorded tolerance rule")

            variance = net_base - grni_amount
            if variance:
                if not variance_account or variance_account.account_type != AccountType.EXPENSE:
                    raise ValueError(
                        f"Invoice price/quantity variance on PO line {po_line.line_no} needs an expense variance mapping"
                    )
                add_line(
                    variance_account,
                    f"Supplier invoice variance {invoice.invoice_no}",
                    debit=variance if variance > 0 else Decimal("0"),
                    credit=abs(variance) if variance < 0 else Decimal("0"),
                )

        if abs(subtotal_doc - Decimal(str(invoice.subtotal))) > money_quantum:
            raise ValueError("Purchase invoice subtotal does not reconcile to its lines")
        if abs(tax_doc - Decimal(str(invoice.tax_amount))) > money_quantum:
            raise ValueError("Purchase invoice tax does not reconcile to its lines")
        if abs((subtotal_doc + tax_doc) - Decimal(str(invoice.total_amount))) > money_quantum:
            raise ValueError("Purchase invoice total does not reconcile to its lines")
        if has_tax:
            if not rule.tax_account_id:
                raise ValueError("Purchase-invoice posting rule needs a recoverable-tax debit account")
            tax_account = await db.get(ChartOfAccount, rule.tax_account_id)
            if not tax_account or tax_account.account_type != AccountType.ASSET:
                raise ValueError("Purchase-invoice recoverable-tax mapping must point to an asset account")
            add_line(tax_account, f"Recoverable tax {invoice.invoice_no}", debit=money(tax_doc * exchange_rate))

        expected_ap_base = money(Decimal(str(invoice.total_amount)) * exchange_rate)
        if abs(expected_ap_base - ap_base_total) > money_quantum:
            raise ValueError("Base-currency purchase invoice total does not reconcile to its rounded lines")
        add_line(ap_account, f"Accounts payable {invoice.invoice_no}", credit=ap_base_total)

        await assert_posting_period_open(db, invoice.invoice_date, require_period=True)
        event, batch, created = await get_or_create_operational_posting_event(
            db,
            source_module="procurement",
            source_event="PURCHASE_INVOICE_POSTED",
            source_id=invoice.id,
            source_ref=invoice.invoice_no,
            event_date=invoice.invoice_date,
            amount=ap_base_total,
            currency=base_currency,
            created_by_id=user_id,
            require_period=True,
        )
        if not created or event.status != OperationalPostingStatus.PENDING:
            raise ValueError("A prior purchase-invoice posting exists but is not safely replayable")

        entry = JournalEntry(
            entry_no=f"PINV-{str(invoice.id).replace('-', '')}",
            entry_date=invoice.invoice_date,
            description=f"Supplier invoice {invoice.invoice_no}",
            source_module="procurement",
            source_event="PURCHASE_INVOICE_POSTED",
            source_id=invoice.id,
            source_ref=invoice.invoice_no,
            company_id=company.id,
            branch_id=po.branch_id,
            cost_center_id=po.cost_center_id,
            status=JournalStatus.DRAFT,
            posting_batch_id=batch.id,
            created_by_id=user_id,
        )
        for row in journal_lines.values():
            entry.lines.append(JournalLine(
                account_id=row["account"].id,
                description=row["description"],
                debit=money(row["debit"]),
                credit=money(row["credit"]),
                currency=base_currency,
            ))
        db.add(entry)
        await db.flush()
        await mark_journal_posted(db, entry, user_id, require_period=True)
        await mark_operational_posting_posted(
            db, event, batch, journal_entry_id=entry.id, posted_by_id=user_id,
        )
        invoice.status = PurchaseInvoiceStatus.RECEIVED
        await db.flush()
        return event
    except Exception:
        await db.rollback()
        raise


# ── Production Cost Rollup ────────────────────────────────────────────────────

async def rollup_production_order_costs(
    db: AsyncSession,
    production_order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> List[ProductionCostEntry]:
    """
    Derive RAW_MATERIAL and PACKAGING cost entries from MaterialConsumption
    records on a completed production order. Existing auto-derived entries are
    replaced while manually entered cost entries are preserved.
    """
    # Load production order with consumptions and material.standard_cost
    po_result = await db.execute(
        select(ProductionOrder)
        .options(
            selectinload(ProductionOrder.consumptions).selectinload(MaterialConsumption.material),
            selectinload(ProductionOrder.product),
        )
        .where(ProductionOrder.id == production_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        return []
    if po.status != ProductionOrderStatus.COMPLETED:
        raise HTTPException(
            status_code=422,
            detail="Production cost rollup is only allowed for COMPLETED production orders.",
        )

    period_ym = (po.actual_start or po.scheduled_start).strftime("%Y-%m")

    # Delete existing auto-derived entries for this PO (RAW_MATERIAL + PACKAGING)
    existing_result = await db.execute(
        select(ProductionCostEntry).where(
            ProductionCostEntry.production_order_id == production_order_id,
            ProductionCostEntry.cost_type.in_([CostType.RAW_MATERIAL, CostType.PACKAGING]),
            ProductionCostEntry.notes.like("Auto from consumption %"),
        )
    )
    for old in existing_result.scalars().all():
        await db.delete(old)
    await db.flush()

    entries = []
    from app.models.master import Material
    from app.models.inventory import StockType

    for c in po.consumptions:
        mat = c.material
        if not mat:
            continue
        unit_cost = mat.standard_cost or Decimal("0")
        amount = (c.actual_quantity * unit_cost).quantize(Decimal("0.0001"))
        # Determine cost type by material_type
        from app.models.master import MaterialType
        cost_type = CostType.PACKAGING if mat.material_type and mat.material_type.value == "PACKAGING" else CostType.RAW_MATERIAL

        entry = ProductionCostEntry(
            production_order_id=production_order_id,
            product_id=po.product_id,
            cost_type=cost_type,
            amount=amount,
            quantity=c.actual_quantity,
            unit_cost=unit_cost,
            period_ym=period_ym,
            notes=f"Auto from consumption {c.id}",
            created_by_id=user_id,
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    return entries


async def rollup_product_cost(
    db: AsyncSession,
    product_id: uuid.UUID,
    period_ym: str,
) -> ProductCost:
    """
    Aggregate all ProductionCostEntries for a product/period and write a
    ProductCost summary row. Sets actual_cost_per_unit and variance vs standard.
    """
    from app.models.master import Product
    from app.crud.finance import upsert_product_cost

    # Sum by cost type
    rows_result = await db.execute(
        select(
            ProductionCostEntry.cost_type,
            func.sum(ProductionCostEntry.amount).label("total"),
        )
        .where(
            ProductionCostEntry.product_id == product_id,
            ProductionCostEntry.period_ym == period_ym,
        )
        .group_by(ProductionCostEntry.cost_type)
    )
    by_type = {row.cost_type: Decimal(str(row.total)) for row in rows_result}

    # Total units produced this period
    from app.models.production import FinishedGoodsReceipt
    qty_result = await db.execute(
        select(func.sum(FinishedGoodsReceipt.quantity))
        .join(ProductionOrder, FinishedGoodsReceipt.production_order_id == ProductionOrder.id)
        .where(
            ProductionOrder.product_id == product_id,
            func.to_char(FinishedGoodsReceipt.created_at, "YYYY-MM") == period_ym,
        )
    )
    total_units = qty_result.scalar() or Decimal("0")

    raw = by_type.get(CostType.RAW_MATERIAL, Decimal("0"))
    pkg = by_type.get(CostType.PACKAGING, Decimal("0"))
    lab = by_type.get(CostType.LABOR, Decimal("0"))
    util = by_type.get(CostType.UTILITY, Decimal("0"))
    ovhd = by_type.get(CostType.OVERHEAD, Decimal("0"))
    total_cost = raw + pkg + lab + util + ovhd

    actual_cpu = (total_cost / total_units).quantize(Decimal("0.0001")) if total_units > 0 else None

    # Standard cost from product
    prod_result = await db.execute(select(Product).where(Product.id == product_id))
    prod = prod_result.scalar_one_or_none()
    std_cpu = prod.standard_cost if prod else None

    variance_amt = None
    variance_pct = None
    if std_cpu is not None and actual_cpu is not None and total_units > 0:
        variance_amt = ((actual_cpu - std_cpu) * total_units).quantize(Decimal("0.01"))
        variance_pct = ((actual_cpu - std_cpu) / std_cpu * 100).quantize(Decimal("0.01")) if std_cpu != 0 else None

    pc = await upsert_product_cost(
        db,
        product_id=product_id,
        period_ym=period_ym,
        raw_material_cost=raw,
        packaging_cost=pkg,
        labor_cost=lab,
        utility_cost=util,
        overhead_cost=ovhd,
        total_units_produced=total_units,
        standard_cost_per_unit=std_cpu,
        actual_cost_per_unit=actual_cpu,
        variance_amount=variance_amt,
        variance_pct=variance_pct,
    )
    return pc


# ── M-Pesa Auto-Match ─────────────────────────────────────────────────────────

async def auto_match_mpesa(db: AsyncSession, user_id: uuid.UUID) -> Tuple[int, int]:
    """
    Attempt to auto-match UNMATCHED M-Pesa reconciliation records to
    outstanding invoices by exact amount.
    Returns (matched_count, skipped_count).
    """
    from app.models.sales import InvoiceStatus

    unmatched_result = await db.execute(
        select(MpesaReconciliation)
        .options(selectinload(MpesaReconciliation.transaction))
        .where(MpesaReconciliation.status == ReconciliationStatus.UNMATCHED)
    )
    unmatched = list(unmatched_result.scalars().all())

    matched = 0
    skipped = 0

    for recon in unmatched:
        tx = recon.transaction
        if not tx:
            skipped += 1
            continue

        amount = tx.amount

        # Find invoices with exactly this outstanding balance
        inv_result = await db.execute(
            select(Invoice)
            .where(
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
                (Invoice.total_amount - Invoice.paid_amount) == amount,
            )
            .order_by(Invoice.due_date)
            .limit(1)
        )
        invoice = inv_result.scalar_one_or_none()

        if invoice:
            recon.invoice_id = invoice.id
            recon.status = ReconciliationStatus.MATCHED
            recon.matched_amount = amount
            recon.matched_by_id = user_id
            recon.matched_at = datetime.now(timezone.utc)
            matched += 1
        else:
            # Try matching against a sales order's total_value
            # (simple lookup by mpesa reference if stored)
            if tx.source_ref:
                so_result = await db.execute(
                    select(SalesOrder).where(SalesOrder.order_no == tx.source_ref)
                )
                so = so_result.scalar_one_or_none()
                if so:
                    recon.so_id = so.id
                    recon.status = ReconciliationStatus.MATCHED
                    recon.matched_amount = amount
                    recon.matched_by_id = user_id
                    recon.matched_at = datetime.now(timezone.utc)
                    matched += 1
                    continue
            skipped += 1

    await db.flush()
    return matched, skipped


async def manual_match(
    db: AsyncSession,
    recon: MpesaReconciliation,
    invoice_id: Optional[uuid.UUID],
    so_id: Optional[uuid.UUID],
    matched_amount: Optional[Decimal],
    notes: Optional[str],
    user_id: uuid.UUID,
) -> MpesaReconciliation:
    recon.invoice_id = invoice_id
    recon.so_id = so_id
    recon.matched_amount = matched_amount or recon.transaction.amount
    recon.notes = notes
    recon.status = ReconciliationStatus.MANUAL
    recon.matched_by_id = user_id
    recon.matched_at = datetime.now(timezone.utc)
    await db.flush()
    return recon


async def mark_exception(
    db: AsyncSession,
    recon: MpesaReconciliation,
    reason: str,
) -> MpesaReconciliation:
    recon.status = ReconciliationStatus.EXCEPTION
    recon.exception_reason = reason
    await db.flush()
    return recon


# ── Reports ───────────────────────────────────────────────────────────────────

async def cash_position(db: AsyncSession) -> List[CashPositionRow]:
    accounts = (await db.execute(
        select(CashAccount).where(CashAccount.is_active == True)  # noqa: E712
    )).scalars().all()

    rows = []
    for acct in accounts:
        # Pending inflows/outflows
        pending_in_r = await db.execute(
            select(func.sum(CashTransaction.amount)).where(
                CashTransaction.cash_account_id == acct.id,
                CashTransaction.status == FinTxStatus.PENDING,
                CashTransaction.direction == TxDirection.RECEIPT,
            )
        )
        pending_out_r = await db.execute(
            select(func.sum(CashTransaction.amount)).where(
                CashTransaction.cash_account_id == acct.id,
                CashTransaction.status == FinTxStatus.PENDING,
                CashTransaction.direction == TxDirection.PAYMENT,
            )
        )
        pending_in = pending_in_r.scalar() or Decimal("0")
        pending_out = pending_out_r.scalar() or Decimal("0")
        rows.append(CashPositionRow(
            account_id=acct.id,
            account_name=acct.name,
            account_type=acct.account_type,
            currency=acct.currency,
            balance=acct.current_balance,
            pending_in=Decimal(str(pending_in)),
            pending_out=Decimal(str(pending_out)),
            cleared_balance=acct.current_balance,
        ))
    return rows


async def mpesa_summary(
    db: AsyncSession, from_date: date, to_date: date
) -> List[MpesaSummaryRow]:
    """Daily M-Pesa receipt summary between two dates."""
    txns_result = await db.execute(
        select(CashTransaction)
        .join(CashAccount)
        .options(selectinload(CashTransaction.reconciliation))
        .where(
            CashAccount.account_type == CashAccountType.MPESA,
            CashTransaction.direction == TxDirection.RECEIPT,
            CashTransaction.transaction_date >= from_date,
            CashTransaction.transaction_date <= to_date,
        )
        .order_by(CashTransaction.transaction_date)
    )
    txns = list(txns_result.scalars().all())

    from collections import defaultdict
    daily: dict = defaultdict(lambda: {"count": 0, "total": Decimal("0"), "matched": 0, "unmatched": 0, "failed": 0})
    for tx in txns:
        d = tx.transaction_date
        daily[d]["count"] += 1
        daily[d]["total"] += tx.amount
        if tx.status == FinTxStatus.FAILED:
            daily[d]["failed"] += 1
        elif tx.reconciliation and tx.reconciliation.status in (ReconciliationStatus.MATCHED, ReconciliationStatus.MANUAL):
            daily[d]["matched"] += 1
        else:
            daily[d]["unmatched"] += 1

    return [
        MpesaSummaryRow(
            date=d,
            receipt_count=v["count"],
            total_received=v["total"],
            matched_count=v["matched"],
            unmatched_count=v["unmatched"],
            failed_count=v["failed"],
        )
        for d, v in sorted(daily.items(), reverse=True)
    ]


async def payment_channel_breakdown(
    db: AsyncSession, from_date: date, to_date: date
) -> List[PaymentChannelRow]:
    result = await db.execute(
        select(
            CashAccount.account_type,
            func.count(CashTransaction.id).label("cnt"),
            func.sum(CashTransaction.amount).label("total"),
        )
        .join(CashAccount, CashTransaction.cash_account_id == CashAccount.id)
        .where(
            CashTransaction.direction == TxDirection.RECEIPT,
            CashTransaction.status == FinTxStatus.CLEARED,
            CashTransaction.transaction_date >= from_date,
            CashTransaction.transaction_date <= to_date,
        )
        .group_by(CashAccount.account_type)
    )
    rows_raw = result.all()
    grand_total = sum(Decimal(str(r.total or 0)) for r in rows_raw)
    return [
        PaymentChannelRow(
            channel=r.account_type.value,
            receipt_count=r.cnt,
            total_amount=Decimal(str(r.total or 0)),
            pct_of_total=(
                (Decimal(str(r.total or 0)) / grand_total * 100).quantize(Decimal("0.01"))
                if grand_total > 0 else Decimal("0")
            ),
        )
        for r in rows_raw
    ]


async def outstanding_receivables(db: AsyncSession) -> List[ReceivableRow]:
    from app.models.sales import InvoiceStatus, Customer
    from datetime import date as date_cls
    today = date_cls.today()
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer), selectinload(Invoice.so))
        .where(Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]))
        .order_by(Invoice.due_date)
    )
    invoices = list(result.scalars().all())
    rows = []
    for inv in invoices:
        outstanding = max(inv.total_amount - inv.paid_amount, Decimal("0"))
        if outstanding <= Decimal("0.005"):
            continue
        delta = (today - inv.due_date).days
        rows.append(ReceivableRow(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            customer_name=inv.customer.name if inv.customer else "",
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            total_amount=inv.total_amount,
            paid_amount=inv.paid_amount,
            outstanding=outstanding,
            days_overdue=delta if delta > 0 else None,
            currency=inv.currency,
        ))
    return rows


async def reconciliation_exceptions(db: AsyncSession) -> List[ReconciliationExceptionRow]:
    result = await db.execute(
        select(MpesaReconciliation)
        .options(selectinload(MpesaReconciliation.transaction))
        .where(MpesaReconciliation.status.in_([
            ReconciliationStatus.UNMATCHED,
            ReconciliationStatus.EXCEPTION,
        ]))
        .order_by(MpesaReconciliation.created_at.desc())
        .limit(200)
    )
    rows = []
    for recon in result.scalars().all():
        tx = recon.transaction
        if not tx:
            continue
        rows.append(ReconciliationExceptionRow(
            transaction_id=tx.id,
            transaction_date=tx.transaction_date,
            mpesa_receipt=tx.mpesa_receipt,
            mpesa_phone=tx.mpesa_phone,
            amount=tx.amount,
            description=tx.description,
            status=recon.status,
            exception_reason=recon.exception_reason,
        ))
    return rows


async def _get_gl_actual(db: AsyncSession, account_id: uuid.UUID, year: int, month: int) -> Decimal:
    """Sum net debit (debit - credit) of posted GL lines for an account in a given year/month."""
    q = (
        select(
            func.coalesce(func.sum(JournalLine.debit), Decimal("0"))
            - func.coalesce(func.sum(JournalLine.credit), Decimal("0"))
        )
        .join(JournalLine.entry)
        .where(
            JournalLine.account_id == account_id,
            JournalEntry.is_posted.is_(True),
            extract("year", JournalEntry.entry_date) == year,
            extract("month", JournalEntry.entry_date) == month,
        )
    )
    result = await db.execute(q)
    val = result.scalar()
    return Decimal(str(val)) if val is not None else Decimal("0")


async def budget_vs_actual(
    db: AsyncSession, year: int, department: Optional[str] = None
) -> List[BudgetVsActualRow]:
    q = select(BudgetLine).join(BudgetLine.budget).where(
        BudgetLine.budget.has(year=year),
    )
    if department:
        q = q.where(BudgetLine.budget.has(department=department))
    lines_result = await db.execute(q.options(selectinload(BudgetLine.budget)))
    lines = list(lines_result.scalars().all())

    rows = []
    for bl in lines:
        budgeted = bl.budgeted_amount
        if bl.account_id:
            actual = await _get_gl_actual(db, bl.account_id, year, bl.month)
        else:
            actual = Decimal("0")
        variance = actual - budgeted
        variance_pct = (variance / budgeted * 100).quantize(Decimal("0.01")) if budgeted != 0 else None
        utilization_pct = (actual / budgeted * 100).quantize(Decimal("0.01")) if budgeted != 0 else None
        rows.append(BudgetVsActualRow(
            department=bl.budget.department,
            category=bl.category,
            month=bl.month,
            budgeted=budgeted,
            actual=actual,
            variance=variance,
            variance_pct=variance_pct,
            utilization_pct=utilization_pct,
        ))
    return rows


async def budget_alerts(
    db: AsyncSession, year: int, threshold: float = 0.9
) -> List[BudgetAlertRow]:
    """Return budget lines where actual spending exceeds threshold % of budgeted."""
    q = select(BudgetLine).join(BudgetLine.budget).where(
        BudgetLine.budget.has(year=year),
    )
    lines_result = await db.execute(q.options(selectinload(BudgetLine.budget)))
    lines = list(lines_result.scalars().all())

    alerts = []
    for bl in lines:
        if not bl.account_id or bl.budgeted_amount == 0:
            continue
        actual = await _get_gl_actual(db, bl.account_id, year, bl.month)
        utilization = actual / bl.budgeted_amount
        if utilization >= Decimal(str(threshold)):
            utilization_pct = (utilization * 100).quantize(Decimal("0.01"))
            alerts.append(BudgetAlertRow(
                budget_id=bl.budget_id,
                department=bl.budget.department,
                category=bl.category,
                month=bl.month,
                budgeted=bl.budgeted_amount,
                actual=actual,
                utilization_pct=utilization_pct,
                alert_level="CRITICAL" if utilization >= 1 else "WARNING",
            ))
    return alerts


# ── General Ledger Reports ────────────────────────────────────────────────────

async def trial_balance(
    db: AsyncSession,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> List[TrialBalanceRow]:
    """Sum posted journal lines per account for the period."""
    from sqlalchemy.orm import aliased

    q = (
        select(
            ChartOfAccount.id.label("account_id"),
            ChartOfAccount.code.label("account_code"),
            ChartOfAccount.name.label("account_name"),
            ChartOfAccount.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.is_posted == True,  # noqa: E712
            ChartOfAccount.is_control == False,  # noqa: E712
        )
    )
    if from_date:
        q = q.where(JournalEntry.entry_date >= from_date)
    if to_date:
        q = q.where(JournalEntry.entry_date <= to_date)
    q = q.group_by(
        ChartOfAccount.id, ChartOfAccount.code,
        ChartOfAccount.name, ChartOfAccount.account_type,
    ).order_by(ChartOfAccount.code)

    rows = (await db.execute(q)).all()
    result = []
    for r in rows:
        debit = Decimal(str(r.total_debit or 0))
        credit = Decimal(str(r.total_credit or 0))
        net = debit - credit
        result.append(TrialBalanceRow(
            account_id=r.account_id,
            account_code=r.account_code,
            account_name=r.account_name,
            account_type=r.account_type,
            total_debit=debit,
            total_credit=credit,
            net_balance=net,
        ))
    return result


async def profit_and_loss(
    db: AsyncSession,
    from_date: date,
    to_date: date,
) -> PLStatement:
    """P&L from posted journal entries in date range."""
    q = (
        select(
            ChartOfAccount.id.label("account_id"),
            ChartOfAccount.code.label("account_code"),
            ChartOfAccount.name.label("account_name"),
            ChartOfAccount.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.is_posted == True,  # noqa: E712
            ChartOfAccount.is_control == False,  # noqa: E712
            ChartOfAccount.account_type.in_([AccountType.REVENUE, AccountType.EXPENSE]),
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
        )
        .group_by(
            ChartOfAccount.id, ChartOfAccount.code,
            ChartOfAccount.name, ChartOfAccount.account_type,
        )
        .order_by(ChartOfAccount.account_type, ChartOfAccount.code)
    )
    rows = (await db.execute(q)).all()

    revenue_lines, expense_lines = [], []
    total_revenue = Decimal("0")
    total_expenses = Decimal("0")

    for r in rows:
        debit = Decimal(str(r.total_debit or 0))
        credit = Decimal(str(r.total_credit or 0))
        if r.account_type == AccountType.REVENUE:
            amount = credit - debit  # credit-normal
            revenue_lines.append(PLLineItem(
                account_id=r.account_id, account_code=r.account_code,
                account_name=r.account_name, amount=amount,
            ))
            total_revenue += amount
        else:  # EXPENSE
            amount = debit - credit   # debit-normal
            expense_lines.append(PLLineItem(
                account_id=r.account_id, account_code=r.account_code,
                account_name=r.account_name, amount=amount,
            ))
            total_expenses += amount

    return PLStatement(
        from_date=from_date,
        to_date=to_date,
        revenue_lines=revenue_lines,
        expense_lines=expense_lines,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        gross_profit=total_revenue - total_expenses,
        net_income=total_revenue - total_expenses,
    )


async def balance_sheet(
    db: AsyncSession,
    as_of_date: date,
) -> BalanceSheetStatement:
    """Balance Sheet as of date from all posted journal entries."""
    q = (
        select(
            ChartOfAccount.id.label("account_id"),
            ChartOfAccount.code.label("account_code"),
            ChartOfAccount.name.label("account_name"),
            ChartOfAccount.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.is_posted == True,  # noqa: E712
            ChartOfAccount.is_control == False,  # noqa: E712
            ChartOfAccount.account_type.in_([AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY]),
            JournalEntry.entry_date <= as_of_date,
        )
        .group_by(
            ChartOfAccount.id, ChartOfAccount.code,
            ChartOfAccount.name, ChartOfAccount.account_type,
        )
        .order_by(ChartOfAccount.account_type, ChartOfAccount.code)
    )
    rows = (await db.execute(q)).all()

    asset_lines, liability_lines, equity_lines = [], [], []
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for r in rows:
        debit = Decimal(str(r.total_debit or 0))
        credit = Decimal(str(r.total_credit or 0))
        if r.account_type == AccountType.ASSET:
            balance = debit - credit  # debit-normal
            asset_lines.append(BSLineItem(
                account_id=r.account_id, account_code=r.account_code,
                account_name=r.account_name, balance=balance,
            ))
            total_assets += balance
        elif r.account_type == AccountType.LIABILITY:
            balance = credit - debit  # credit-normal
            liability_lines.append(BSLineItem(
                account_id=r.account_id, account_code=r.account_code,
                account_name=r.account_name, balance=balance,
            ))
            total_liabilities += balance
        else:  # EQUITY
            balance = credit - debit  # credit-normal
            equity_lines.append(BSLineItem(
                account_id=r.account_id, account_code=r.account_code,
                account_name=r.account_name, balance=balance,
            ))
            total_equity += balance

    diff = abs(total_assets - (total_liabilities + total_equity))
    is_balanced = diff < Decimal("0.01")

    return BalanceSheetStatement(
        as_of_date=as_of_date,
        asset_lines=asset_lines,
        liability_lines=liability_lines,
        equity_lines=equity_lines,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        is_balanced=is_balanced,
    )


async def general_ledger_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    from_date: date,
    to_date: date,
) -> GLAccountDrillDown:
    """GL drill-down: transactions for an account with running balance."""
    # Load account
    account = (await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == account_id)
    )).scalar_one_or_none()
    if not account:
        return None

    # Opening balance = net of all posted lines before from_date
    ob_q = (await db.execute(
        select(
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("d"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("c"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.is_posted == True,  # noqa: E712
            JournalLine.account_id == account_id,
            JournalEntry.entry_date < from_date,
        )
    )).one()
    ob_debit = Decimal(str(ob_q.d or 0))
    ob_credit = Decimal(str(ob_q.c or 0))
    is_debit_normal = account.account_type in (AccountType.ASSET, AccountType.EXPENSE)
    opening_balance = (ob_debit - ob_credit) if is_debit_normal else (ob_credit - ob_debit)

    # Period lines
    lines_q = (await db.execute(
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.is_posted == True,  # noqa: E712
            JournalLine.account_id == account_id,
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
        )
        .order_by(JournalEntry.entry_date, JournalEntry.entry_no)
    )).all()

    transactions = []
    running = opening_balance
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for line, entry in lines_q:
        d = Decimal(str(line.debit or 0))
        c = Decimal(str(line.credit or 0))
        total_debit += d
        total_credit += c
        if is_debit_normal:
            running += d - c
        else:
            running += c - d
        transactions.append(GLTransactionRow(
            entry_id=entry.id,
            entry_no=entry.entry_no,
            entry_date=entry.entry_date,
            description=line.description or entry.description,
            source_module=entry.source_module,
            source_ref=entry.source_ref,
            debit=d,
            credit=c,
            running_balance=running,
        ))

    return GLAccountDrillDown(
        account_id=account.id,
        account_code=account.code,
        account_name=account.name,
        account_type=account.account_type,
        opening_balance=opening_balance,
        closing_balance=running,
        total_debit=total_debit,
        total_credit=total_credit,
        transactions=transactions,
    )


# ── Exchange Rate Helpers ─────────────────────────────────────────────────────

async def get_rate(
    db: AsyncSession,
    currency: str,
    as_of_date: Optional[date] = None,
) -> Optional[ExchangeRate]:
    """Return most recent exchange rate for currency on or before as_of_date."""
    if currency.upper() == "KES":
        return None
    q = (
        select(ExchangeRate)
        .where(ExchangeRate.currency == currency.upper())
    )
    if as_of_date:
        q = q.where(ExchangeRate.rate_date <= as_of_date)
    q = q.order_by(ExchangeRate.rate_date.desc()).limit(1)
    return (await db.execute(q)).scalar_one_or_none()


async def convert_to_kes(
    db: AsyncSession,
    amount: Decimal,
    currency: str,
    as_of_date: Optional[date] = None,
) -> FXConvertResult:
    """Convert amount from foreign currency to KES using the closest available rate."""
    target_date = as_of_date or date.today()
    if currency.upper() == "KES":
        return FXConvertResult(
            from_currency="KES",
            to_currency="KES",
            amount=amount,
            rate=Decimal("1"),
            converted_amount=amount,
            rate_date=target_date,
        )
    rate_obj = await get_rate(db, currency, target_date)
    if not rate_obj:
        raise ValueError(f"No exchange rate found for {currency} as of {target_date}")
    kes_amount = (amount * rate_obj.rate_to_kes).quantize(Decimal("0.01"))
    return FXConvertResult(
        from_currency=currency.upper(),
        to_currency="KES",
        amount=amount,
        rate=rate_obj.rate_to_kes,
        converted_amount=kes_amount,
        rate_date=rate_obj.rate_date,
    )
