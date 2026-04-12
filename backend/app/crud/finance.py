from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    ChartOfAccount, JournalEntry, JournalLine,
    CashAccount, CashTransaction, MpesaReconciliation,
    ProductCost, ProductionCostEntry,
    Budget, BudgetLine,
    CashAccountType, ReconciliationStatus, FinTxStatus, TxDirection, BudgetStatus,
)


# ── Chart of Accounts ─────────────────────────────────────────────────────────

async def list_coa(db: AsyncSession, active_only: bool = False) -> List[ChartOfAccount]:
    q = select(ChartOfAccount).options(selectinload(ChartOfAccount.parent))
    if active_only:
        q = q.where(ChartOfAccount.is_active == True)  # noqa: E712
    q = q.order_by(ChartOfAccount.code)
    return list((await db.execute(q)).scalars().all())


async def get_coa(db: AsyncSession, account_id: uuid.UUID) -> Optional[ChartOfAccount]:
    result = await db.execute(select(ChartOfAccount).where(ChartOfAccount.id == account_id))
    return result.scalar_one_or_none()


async def create_coa(db: AsyncSession, data: dict) -> ChartOfAccount:
    acc = ChartOfAccount(**data)
    db.add(acc)
    await db.flush()
    await db.refresh(acc)
    return acc


# ── Journal Entries ───────────────────────────────────────────────────────────

async def list_journal_entries(
    db: AsyncSession,
    source_module: Optional[str] = None,
    is_posted: Optional[bool] = None,
    limit: int = 100,
) -> List[JournalEntry]:
    q = select(JournalEntry)
    if source_module:
        q = q.where(JournalEntry.source_module == source_module)
    if is_posted is not None:
        q = q.where(JournalEntry.is_posted == is_posted)
    q = q.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def get_journal_entry(db: AsyncSession, entry_id: uuid.UUID) -> Optional[JournalEntry]:
    result = await db.execute(
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.lines).selectinload(JournalLine.account),
            selectinload(JournalEntry.created_by),
        )
        .where(JournalEntry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def create_journal_entry(
    db: AsyncSession, data: dict, user_id: uuid.UUID
) -> JournalEntry:
    lines_data = data.pop("lines", [])
    entry = JournalEntry(**data, created_by_id=user_id)
    db.add(entry)
    await db.flush()
    for ld in lines_data:
        db.add(JournalLine(entry_id=entry.id, **ld))
    await db.flush()
    await db.refresh(entry)
    return entry


# ── Cash Accounts ─────────────────────────────────────────────────────────────

async def list_cash_accounts(db: AsyncSession, active_only: bool = True) -> List[CashAccount]:
    q = select(CashAccount)
    if active_only:
        q = q.where(CashAccount.is_active == True)  # noqa: E712
    q = q.order_by(CashAccount.account_type, CashAccount.name)
    return list((await db.execute(q)).scalars().all())


async def get_cash_account(db: AsyncSession, account_id: uuid.UUID) -> Optional[CashAccount]:
    result = await db.execute(select(CashAccount).where(CashAccount.id == account_id))
    return result.scalar_one_or_none()


async def create_cash_account(db: AsyncSession, data: dict) -> CashAccount:
    acc = CashAccount(**data, current_balance=data.get("opening_balance", Decimal("0")))
    db.add(acc)
    await db.flush()
    await db.refresh(acc)
    return acc


# ── Cash Transactions ─────────────────────────────────────────────────────────

async def list_cash_transactions(
    db: AsyncSession,
    cash_account_id: Optional[uuid.UUID] = None,
    account_type: Optional[CashAccountType] = None,
    status: Optional[FinTxStatus] = None,
    from_date=None,
    to_date=None,
    limit: int = 200,
) -> List[CashTransaction]:
    q = (
        select(CashTransaction)
        .options(selectinload(CashTransaction.cash_account),
                 selectinload(CashTransaction.reconciliation))
        .order_by(CashTransaction.transaction_date.desc(), CashTransaction.created_at.desc())
    )
    if cash_account_id:
        q = q.where(CashTransaction.cash_account_id == cash_account_id)
    if account_type:
        q = q.join(CashAccount).where(CashAccount.account_type == account_type)
    if status:
        q = q.where(CashTransaction.status == status)
    if from_date:
        q = q.where(CashTransaction.transaction_date >= from_date)
    if to_date:
        q = q.where(CashTransaction.transaction_date <= to_date)
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_cash_transaction(db: AsyncSession, tx_id: uuid.UUID) -> Optional[CashTransaction]:
    result = await db.execute(
        select(CashTransaction)
        .options(selectinload(CashTransaction.cash_account),
                 selectinload(CashTransaction.reconciliation))
        .where(CashTransaction.id == tx_id)
    )
    return result.scalar_one_or_none()


async def create_cash_transaction(
    db: AsyncSession, data: dict, user_id: uuid.UUID
) -> CashTransaction:
    tx = CashTransaction(**data, created_by_id=user_id)
    db.add(tx)
    await db.flush()
    # Update account balance
    acct_result = await db.execute(
        select(CashAccount).where(CashAccount.id == tx.cash_account_id).with_for_update()
    )
    acct = acct_result.scalar_one_or_none()
    if acct and tx.status == FinTxStatus.CLEARED:
        if tx.direction == TxDirection.RECEIPT:
            acct.current_balance += tx.amount
        else:
            acct.current_balance -= tx.amount
    await db.flush()
    # For M-Pesa receipts, auto-create reconciliation record
    if acct and acct.account_type == CashAccountType.MPESA and tx.direction == TxDirection.RECEIPT:
        recon = MpesaReconciliation(
            cash_transaction_id=tx.id,
            status=ReconciliationStatus.UNMATCHED,
        )
        db.add(recon)
        await db.flush()
    await db.refresh(tx)
    return tx


async def clear_transaction(db: AsyncSession, tx: CashTransaction) -> CashTransaction:
    """Mark a PENDING transaction as CLEARED and update account balance."""
    if tx.status != FinTxStatus.PENDING:
        return tx
    tx.status = FinTxStatus.CLEARED
    acct_result = await db.execute(
        select(CashAccount).where(CashAccount.id == tx.cash_account_id).with_for_update()
    )
    acct = acct_result.scalar_one_or_none()
    if acct:
        if tx.direction == TxDirection.RECEIPT:
            acct.current_balance += tx.amount
        else:
            acct.current_balance -= tx.amount
    await db.flush()
    return tx


# ── M-Pesa Reconciliation ─────────────────────────────────────────────────────

async def list_reconciliations(
    db: AsyncSession,
    status: Optional[ReconciliationStatus] = None,
    limit: int = 200,
) -> List[MpesaReconciliation]:
    q = (
        select(MpesaReconciliation)
        .options(
            selectinload(MpesaReconciliation.transaction).selectinload(CashTransaction.cash_account),
            selectinload(MpesaReconciliation.invoice),
            selectinload(MpesaReconciliation.so),
        )
        .order_by(MpesaReconciliation.created_at.desc())
    )
    if status:
        q = q.where(MpesaReconciliation.status == status)
    return list((await db.execute(q.limit(limit))).scalars().all())


async def get_reconciliation(
    db: AsyncSession, recon_id: uuid.UUID
) -> Optional[MpesaReconciliation]:
    result = await db.execute(
        select(MpesaReconciliation)
        .options(
            selectinload(MpesaReconciliation.transaction),
            selectinload(MpesaReconciliation.invoice),
            selectinload(MpesaReconciliation.so),
        )
        .where(MpesaReconciliation.id == recon_id)
    )
    return result.scalar_one_or_none()


# ── Cost Accounting ───────────────────────────────────────────────────────────

async def list_production_cost_entries(
    db: AsyncSession,
    production_order_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    period_ym: Optional[str] = None,
) -> List[ProductionCostEntry]:
    q = select(ProductionCostEntry).options(selectinload(ProductionCostEntry.product))
    if production_order_id:
        q = q.where(ProductionCostEntry.production_order_id == production_order_id)
    if product_id:
        q = q.where(ProductionCostEntry.product_id == product_id)
    if period_ym:
        q = q.where(ProductionCostEntry.period_ym == period_ym)
    q = q.order_by(ProductionCostEntry.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def create_production_cost_entry(
    db: AsyncSession, data: dict, user_id: uuid.UUID
) -> ProductionCostEntry:
    entry = ProductionCostEntry(**data, created_by_id=user_id)
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_product_costs(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
    period_ym: Optional[str] = None,
) -> List[ProductCost]:
    q = select(ProductCost).options(selectinload(ProductCost.product))
    if product_id:
        q = q.where(ProductCost.product_id == product_id)
    if period_ym:
        q = q.where(ProductCost.period_ym == period_ym)
    q = q.order_by(ProductCost.period_ym.desc())
    return list((await db.execute(q)).scalars().all())


async def upsert_product_cost(
    db: AsyncSession,
    product_id: uuid.UUID,
    period_ym: str,
    **kwargs,
) -> ProductCost:
    result = await db.execute(
        select(ProductCost)
        .where(ProductCost.product_id == product_id, ProductCost.period_ym == period_ym)
        .with_for_update()
    )
    pc = result.scalar_one_or_none()
    if pc is None:
        pc = ProductCost(product_id=product_id, period_ym=period_ym)
        db.add(pc)
    for k, v in kwargs.items():
        setattr(pc, k, v)
    await db.flush()
    await db.refresh(pc)
    return pc


# ── Budgets ───────────────────────────────────────────────────────────────────

async def list_budgets(db: AsyncSession) -> List[Budget]:
    q = select(Budget).options(selectinload(Budget.created_by)).order_by(Budget.year.desc(), Budget.department)
    return list((await db.execute(q)).scalars().all())


async def get_budget(db: AsyncSession, budget_id: uuid.UUID) -> Optional[Budget]:
    result = await db.execute(
        select(Budget)
        .options(
            selectinload(Budget.lines).selectinload(BudgetLine.account),
            selectinload(Budget.created_by),
            selectinload(Budget.approved_by),
        )
        .where(Budget.id == budget_id)
    )
    return result.scalar_one_or_none()


async def create_budget(db: AsyncSession, data: dict, user_id: uuid.UUID) -> Budget:
    lines_data = data.pop("lines", [])
    budget = Budget(**data, created_by_id=user_id)
    db.add(budget)
    await db.flush()
    for ld in lines_data:
        db.add(BudgetLine(budget_id=budget.id, **ld))
    await db.flush()
    await db.refresh(budget)
    return budget
