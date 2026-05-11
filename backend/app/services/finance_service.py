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
from typing import List, Optional, Sequence, Tuple
import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    CashAccount, CashTransaction, MpesaReconciliation,
    ProductCost, ProductionCostEntry, BudgetLine,
    ChartOfAccount, JournalEntry, JournalLine, ExchangeRate,
    CashAccountType, TxDirection, FinTxStatus, ReconciliationStatus, CostType, BudgetStatus,
    AccountType, AccountingPeriod, FiscalYear, PeriodStatus, FiscalYearStatus,
    JournalStatus, AccountingPostingBatch, PostingBatchStatus,
)
from app.models.production import ProductionOrder, MaterialConsumption
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


# ── Production Cost Rollup ────────────────────────────────────────────────────

async def rollup_production_order_costs(
    db: AsyncSession,
    production_order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> List[ProductionCostEntry]:
    """
    Derive RAW_MATERIAL and PACKAGING cost entries from MaterialConsumption
    records on a production order. Existing entries for the PO are replaced.
    """
    # Load production order with consumptions and material.standard_cost
    po_result = await db.execute(
        select(ProductionOrder)
        .options(
            selectinload(ProductionOrder.consumptions).selectinload(MaterialConsumption.material),
            selectinload(ProductionOrder.product),
        )
        .where(ProductionOrder.id == production_order_id)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        return []

    period_ym = (po.actual_start or po.scheduled_start).strftime("%Y-%m")

    # Delete existing auto-derived entries for this PO (RAW_MATERIAL + PACKAGING)
    existing_result = await db.execute(
        select(ProductionCostEntry).where(
            ProductionCostEntry.production_order_id == production_order_id,
            ProductionCostEntry.cost_type.in_([CostType.RAW_MATERIAL, CostType.PACKAGING]),
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
