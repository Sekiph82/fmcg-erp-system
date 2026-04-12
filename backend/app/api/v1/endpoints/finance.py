from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models.finance import (
    ChartOfAccount, JournalEntry, JournalLine,
    CashAccount, CashTransaction, MpesaReconciliation,
    ProductCost, ProductionCostEntry, Budget, BudgetLine,
    BudgetStatus, FinTxStatus, ReconciliationStatus,
    PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment,
    PurchaseInvoiceStatus,
)
from app.schemas.finance import (
    COACreate, COAUpdate, COARead,
    JournalEntryCreate, JournalEntryRead, JournalEntryDetailRead, JournalLineRead,
    CashAccountCreate, CashAccountUpdate, CashAccountRead,
    CashTransactionCreate, CashTransactionRead,
    ManualMatchRequest, ReconciliationRead,
    ProductionCostEntryCreate, ProductionCostEntryRead, ProductCostRead,
    BudgetCreate, BudgetRead, BudgetDetailRead, BudgetLineRead,
    CashPositionRow, MpesaSummaryRow, PaymentChannelRow,
    ReceivableRow, ReconciliationExceptionRow, BudgetVsActualRow,
    PurchaseInvoiceCreate, PurchaseInvoiceRead,
    PurchaseInvoiceLineCreate, PurchaseInvoiceLineRead,
    PurchasePaymentCreate, PurchasePaymentRead,
    CustomerPaymentCreate, CustomerPaymentRead,
    CustomerLedgerRow, SupplierLedgerRow, AccountingDashboard,
)
from app.crud import finance as crud
from app.services import finance_service as svc

router = APIRouter()


# ── Chart of Accounts ─────────────────────────────────────────────────────────

@router.get("/coa/", response_model=List[COARead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_coa(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_coa(db, active_only=active_only)


@router.post("/coa/", response_model=COARead, status_code=201,
             dependencies=[Depends(require_permission("finance", "create"))])
async def create_account(
    body: COACreate,
    db: AsyncSession = Depends(get_db),
):
    acc = await crud.create_coa(db, body.model_dump())
    await db.commit()
    await db.refresh(acc)
    return acc


@router.patch("/coa/{account_id}", response_model=COARead,
              dependencies=[Depends(require_permission("finance", "edit"))])
async def update_account(
    account_id: uuid.UUID,
    body: COAUpdate,
    db: AsyncSession = Depends(get_db),
):
    acc = await crud.get_coa(db, account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(acc, k, v)
    await db.commit()
    await db.refresh(acc)
    return acc


# ── Journal Entries ───────────────────────────────────────────────────────────

@router.get("/journal/", response_model=List[JournalEntryRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_journal(
    source_module: Optional[str] = None,
    is_posted: Optional[bool] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    entries = await crud.list_journal_entries(db, source_module=source_module, is_posted=is_posted, limit=limit)
    out = []
    for e in entries:
        r = JournalEntryRead.model_validate(e)
        out.append(r)
    return out


@router.post("/journal/", response_model=JournalEntryDetailRead, status_code=201)
async def create_journal_entry(
    body: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    data = body.model_dump()
    data["lines"] = [l.model_dump() for l in body.lines]
    # Validate balanced entry
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in data["lines"])
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in data["lines"])
    if abs(total_debit - total_credit) > Decimal("0.005"):
        raise HTTPException(422, f"Journal entry is unbalanced: debit={total_debit} credit={total_credit}")
    entry = await crud.create_journal_entry(db, data, current_user.id)
    await db.commit()
    entry = await crud.get_journal_entry(db, entry.id)
    return _build_journal_detail(entry)


@router.get("/journal/{entry_id}", response_model=JournalEntryDetailRead,
            dependencies=[Depends(require_permission("finance", "view"))])
async def get_journal_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    entry = await crud.get_journal_entry(db, entry_id)
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    return _build_journal_detail(entry)


@router.post("/journal/{entry_id}/post", response_model=JournalEntryRead)
async def post_journal_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    entry = await crud.get_journal_entry(db, entry_id)
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    if entry.is_posted:
        raise HTTPException(422, "Entry already posted")
    entry.is_posted = True
    entry.posted_by_id = current_user.id
    entry.posted_at = datetime.now(timezone.utc)
    await db.commit()
    return JournalEntryRead.model_validate(entry)


# ── Cash Accounts ─────────────────────────────────────────────────────────────

@router.get("/cash-accounts/", response_model=List[CashAccountRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_cash_accounts(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_cash_accounts(db, active_only=active_only)


@router.post("/cash-accounts/", response_model=CashAccountRead, status_code=201,
             dependencies=[Depends(require_permission("finance", "create"))])
async def create_cash_account(
    body: CashAccountCreate,
    db: AsyncSession = Depends(get_db),
):
    acct = await crud.create_cash_account(db, body.model_dump())
    await db.commit()
    await db.refresh(acct)
    return acct


@router.patch("/cash-accounts/{account_id}", response_model=CashAccountRead,
              dependencies=[Depends(require_permission("finance", "edit"))])
async def update_cash_account(
    account_id: uuid.UUID,
    body: CashAccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    acct = await crud.get_cash_account(db, account_id)
    if not acct:
        raise HTTPException(404, "Cash account not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(acct, k, v)
    await db.commit()
    await db.refresh(acct)
    return acct


# ── Cash Transactions ─────────────────────────────────────────────────────────

@router.get("/cash-accounts/{account_id}/transactions", response_model=List[CashTransactionRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_account_transactions(
    account_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    txns = await crud.list_cash_transactions(
        db, cash_account_id=account_id, from_date=from_date, to_date=to_date, limit=limit
    )
    return [_build_tx_read(t) for t in txns]


@router.post("/cash-accounts/{account_id}/transactions", response_model=CashTransactionRead, status_code=201)
async def add_transaction(
    account_id: uuid.UUID,
    body: CashTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    if body.cash_account_id != account_id:
        raise HTTPException(422, "cash_account_id in body must match URL parameter")
    acct = await crud.get_cash_account(db, account_id)
    if not acct:
        raise HTTPException(404, "Cash account not found")
    tx = await crud.create_cash_transaction(db, body.model_dump(), current_user.id)
    await db.commit()
    tx = await crud.get_cash_transaction(db, tx.id)
    return _build_tx_read(tx)


@router.post("/transactions/{tx_id}/clear", response_model=CashTransactionRead)
async def clear_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    tx = await crud.get_cash_transaction(db, tx_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    tx = await crud.clear_transaction(db, tx)
    await db.commit()
    tx = await crud.get_cash_transaction(db, tx_id)
    return _build_tx_read(tx)


# ── M-Pesa Transactions (convenience filter) ──────────────────────────────────

@router.get("/mpesa/transactions", response_model=List[CashTransactionRead],
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def list_mpesa_transactions(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[FinTxStatus] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    from app.models.finance import CashAccountType
    txns = await crud.list_cash_transactions(
        db, account_type=CashAccountType.MPESA, status=status,
        from_date=from_date, to_date=to_date, limit=limit
    )
    return [_build_tx_read(t) for t in txns]


# ── M-Pesa Reconciliation ─────────────────────────────────────────────────────

@router.get("/mpesa/reconciliation", response_model=List[ReconciliationRead],
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def list_reconciliations(
    status: Optional[ReconciliationStatus] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    recons = await crud.list_reconciliations(db, status=status, limit=limit)
    return [_build_recon_read(r) for r in recons]


@router.post("/mpesa/auto-match", response_model=dict)
async def auto_match_mpesa(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("mpesa", "reconcile_payment")),
):
    matched, skipped = await svc.auto_match_mpesa(db, current_user.id)
    await db.commit()
    return {"matched": matched, "skipped": skipped}


@router.post("/mpesa/reconciliation/{recon_id}/match", response_model=ReconciliationRead)
async def manual_match(
    recon_id: uuid.UUID,
    body: ManualMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("mpesa", "reconcile_payment")),
):
    recon = await crud.get_reconciliation(db, recon_id)
    if not recon:
        raise HTTPException(404, "Reconciliation record not found")
    recon = await svc.manual_match(
        db, recon,
        invoice_id=body.invoice_id,
        so_id=body.so_id,
        matched_amount=body.matched_amount,
        notes=body.notes,
        user_id=current_user.id,
    )
    await db.commit()
    recon = await crud.get_reconciliation(db, recon_id)
    return _build_recon_read(recon)


@router.post("/mpesa/reconciliation/{recon_id}/exception", response_model=ReconciliationRead)
async def mark_exception(
    recon_id: uuid.UUID,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("mpesa", "reconcile_payment")),
):
    recon = await crud.get_reconciliation(db, recon_id)
    if not recon:
        raise HTTPException(404, "Reconciliation record not found")
    recon = await svc.mark_exception(db, recon, reason)
    await db.commit()
    recon = await crud.get_reconciliation(db, recon_id)
    return _build_recon_read(recon)


# ── Cost Accounting ───────────────────────────────────────────────────────────

@router.get("/costing/entries", response_model=List[ProductionCostEntryRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_cost_entries(
    production_order_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    period_ym: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    entries = await crud.list_production_cost_entries(
        db, production_order_id=production_order_id,
        product_id=product_id, period_ym=period_ym
    )
    return [_build_cost_entry_read(e) for e in entries]


@router.post("/costing/entries", response_model=ProductionCostEntryRead, status_code=201)
async def add_cost_entry(
    body: ProductionCostEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    entry = await crud.create_production_cost_entry(db, body.model_dump(), current_user.id)
    await db.commit()
    await db.refresh(entry)
    return _build_cost_entry_read(entry)


@router.post("/costing/rollup/{production_order_id}", response_model=List[ProductionCostEntryRead])
async def rollup_production_costs(
    production_order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    entries = await svc.rollup_production_order_costs(db, production_order_id, current_user.id)
    await db.commit()
    return [_build_cost_entry_read(e) for e in entries]


@router.post("/costing/product-rollup/{product_id}", response_model=ProductCostRead)
async def rollup_product_cost(
    product_id: uuid.UUID,
    period_ym: str = Query(..., description="Format: YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    pc = await svc.rollup_product_cost(db, product_id, period_ym)
    await db.commit()
    return _build_product_cost_read(pc)


@router.get("/costing/products", response_model=List[ProductCostRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_product_costs(
    product_id: Optional[uuid.UUID] = None,
    period_ym: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    costs = await crud.list_product_costs(db, product_id=product_id, period_ym=period_ym)
    return [_build_product_cost_read(c) for c in costs]


# ── Budget ────────────────────────────────────────────────────────────────────

@router.get("/budgets/", response_model=List[BudgetRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_budgets(
    db: AsyncSession = Depends(get_db),
):
    budgets = await crud.list_budgets(db)
    return [_build_budget_read(b) for b in budgets]


@router.post("/budgets/", response_model=BudgetDetailRead, status_code=201)
async def create_budget(
    body: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    data = body.model_dump()
    data["lines"] = [l.model_dump() for l in body.lines]
    budget = await crud.create_budget(db, data, current_user.id)
    await db.commit()
    budget = await crud.get_budget(db, budget.id)
    return _build_budget_detail(budget)


@router.get("/budgets/{budget_id}", response_model=BudgetDetailRead,
            dependencies=[Depends(require_permission("finance", "view"))])
async def get_budget(
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    budget = await crud.get_budget(db, budget_id)
    if not budget:
        raise HTTPException(404, "Budget not found")
    return _build_budget_detail(budget)


@router.post("/budgets/{budget_id}/approve", response_model=BudgetRead)
async def approve_budget(
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    budget = await crud.get_budget(db, budget_id)
    if not budget:
        raise HTTPException(404, "Budget not found")
    if budget.status == BudgetStatus.LOCKED:
        raise HTTPException(422, "Budget is locked")
    budget.status = BudgetStatus.APPROVED
    budget.approved_by_id = current_user.id
    budget.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(budget)
    return _build_budget_read(budget)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/cash-position", response_model=List[CashPositionRow],
            dependencies=[Depends(require_permission("finance", "export"))])
async def report_cash_position(
    db: AsyncSession = Depends(get_db),
):
    return await svc.cash_position(db)


@router.get("/reports/mpesa-summary", response_model=List[MpesaSummaryRow],
            dependencies=[Depends(require_permission("finance", "export"))])
async def report_mpesa_summary(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.mpesa_summary(db, from_date, to_date)


@router.get("/reports/payment-channels", response_model=List[PaymentChannelRow],
            dependencies=[Depends(require_permission("finance", "export"))])
async def report_payment_channels(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.payment_channel_breakdown(db, from_date, to_date)


@router.get("/reports/receivables", response_model=List[ReceivableRow],
            dependencies=[Depends(require_permission("finance", "view"))])
async def report_receivables(
    db: AsyncSession = Depends(get_db),
):
    return await svc.outstanding_receivables(db)


@router.get("/reports/reconciliation-exceptions", response_model=List[ReconciliationExceptionRow],
            dependencies=[Depends(require_permission("finance", "view"))])
async def report_recon_exceptions(
    db: AsyncSession = Depends(get_db),
):
    return await svc.reconciliation_exceptions(db)


@router.get("/reports/budget-vs-actual", response_model=List[BudgetVsActualRow],
            dependencies=[Depends(require_permission("finance", "view"))])
async def report_budget_vs_actual(
    year: int = Query(...),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.budget_vs_actual(db, year, department)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_journal_detail(entry: JournalEntry) -> JournalEntryDetailRead:
    r = JournalEntryDetailRead.model_validate(entry)
    lines = []
    for l in (entry.lines or []):
        lr = JournalLineRead.model_validate(l)
        if l.account:
            lr.account_code = l.account.code
            lr.account_name = l.account.name
        lines.append(lr)
    r.lines = lines
    r.total_debit = sum(l.debit for l in r.lines)
    r.total_credit = sum(l.credit for l in r.lines)
    return r


def _build_tx_read(tx: CashTransaction) -> CashTransactionRead:
    r = CashTransactionRead.model_validate(tx)
    if tx.cash_account:
        r.cash_account_name = tx.cash_account.name
        r.cash_account_type = tx.cash_account.account_type
    if tx.reconciliation:
        r.reconciliation_status = tx.reconciliation.status
    return r


def _build_recon_read(recon: MpesaReconciliation) -> ReconciliationRead:
    r = ReconciliationRead.model_validate(recon)
    if recon.transaction:
        r.tx_date = recon.transaction.transaction_date
        r.tx_amount = recon.transaction.amount
        r.mpesa_receipt = recon.transaction.mpesa_receipt
        r.mpesa_phone = recon.transaction.mpesa_phone
        r.mpesa_name = recon.transaction.mpesa_name
    if recon.invoice:
        r.invoice_no = recon.invoice.invoice_no
    if recon.so:
        r.so_no = recon.so.order_no
    return r


def _build_cost_entry_read(e: ProductionCostEntry) -> ProductionCostEntryRead:
    r = ProductionCostEntryRead.model_validate(e)
    if e.product:
        r.product_name = e.product.name
    return r


def _build_product_cost_read(pc: ProductCost) -> ProductCostRead:
    r = ProductCostRead.model_validate(pc)
    if pc.product:
        r.product_name = pc.product.name
        r.product_sku = pc.product.sku
    return r


def _build_budget_read(b: Budget) -> BudgetRead:
    r = BudgetRead.model_validate(b)
    if b.lines:
        r.total_budgeted = sum(l.budgeted_amount for l in b.lines)
    return r


def _build_budget_detail(b: Budget) -> BudgetDetailRead:
    r = BudgetDetailRead.model_validate(b)
    if b.lines:
        r.total_budgeted = sum(l.budgeted_amount for l in b.lines)
        r.lines = [BudgetLineRead.model_validate(l) for l in b.lines]
    return r


# ── Marketing spend visibility ─────────────────────────────────────────────────

@router.get("/reports/marketing-spend",
            dependencies=[Depends(require_permission("finance", "view"))])
async def marketing_spend_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-module marketing spend summary for finance visibility.
    Pulls from TradeSpend and BrandSpend in the marketing module.
    Returns period totals, category breakdown, and campaign linkage.
    ROI-ready: pair with campaign actual_revenue for full P&L view.
    """
    from sqlalchemy import func as sqlfunc, select as sqsel
    from app.models.marketing import TradeSpend, BrandSpend, Campaign, ApprovalStatus

    today = date.today()
    d_from = date_from or (today.replace(day=1))
    d_to = date_to or today

    # Trade spend totals
    trade_rows = (await db.execute(
        sqsel(
            TradeSpend.spend_type,
            TradeSpend.approval_status,
            sqlfunc.sum(TradeSpend.amount).label("total"),
            sqlfunc.count(TradeSpend.id).label("cnt"),
        )
        .where(TradeSpend.spend_date.between(d_from, d_to))
        .group_by(TradeSpend.spend_type, TradeSpend.approval_status)
        .order_by(sqlfunc.sum(TradeSpend.amount).desc())
    )).all()

    # Brand spend totals
    brand_rows = (await db.execute(
        sqsel(
            BrandSpend.spend_category,
            BrandSpend.approval_status,
            sqlfunc.sum(BrandSpend.amount).label("total"),
            sqlfunc.count(BrandSpend.id).label("cnt"),
        )
        .where(BrandSpend.spend_date.between(d_from, d_to))
        .group_by(BrandSpend.spend_category, BrandSpend.approval_status)
        .order_by(sqlfunc.sum(BrandSpend.amount).desc())
    )).all()

    total_trade = sum(float(r.total or 0) for r in trade_rows)
    total_brand = sum(float(r.total or 0) for r in brand_rows)
    approved_trade = sum(float(r.total or 0) for r in trade_rows if r.approval_status == ApprovalStatus.APPROVED)
    approved_brand = sum(float(r.total or 0) for r in brand_rows if r.approval_status == ApprovalStatus.APPROVED)

    # Campaign ROI summary for the same period
    camp_rows = (await db.execute(
        sqsel(
            Campaign.campaign_name,
            Campaign.campaign_type,
            Campaign.budget,
            Campaign.actual_revenue,
            Campaign.actual_roi,
            Campaign.approval_status,
        )
        .where(
            Campaign.start_date.between(d_from, d_to),
            Campaign.actual_revenue.isnot(None),
        )
        .order_by(Campaign.actual_roi.desc())
        .limit(10)
    )).all()

    return {
        "period": {"from": str(d_from), "to": str(d_to)},
        "summary": {
            "total_trade_spend": round(total_trade, 2),
            "total_brand_spend": round(total_brand, 2),
            "total_marketing_spend": round(total_trade + total_brand, 2),
            "approved_trade_spend": round(approved_trade, 2),
            "approved_brand_spend": round(approved_brand, 2),
            "pending_approval": round(
                (total_trade - approved_trade) + (total_brand - approved_brand), 2
            ),
        },
        "trade_spend_by_type": [
            {
                "type": r.spend_type.value if hasattr(r.spend_type, "value") else str(r.spend_type),
                "status": r.approval_status.value if hasattr(r.approval_status, "value") else str(r.approval_status),
                "total": round(float(r.total or 0), 2),
                "count": r.cnt,
            }
            for r in trade_rows
        ],
        "brand_spend_by_category": [
            {
                "category": r.spend_category.value if hasattr(r.spend_category, "value") else str(r.spend_category),
                "status": r.approval_status.value if hasattr(r.approval_status, "value") else str(r.approval_status),
                "total": round(float(r.total or 0), 2),
                "count": r.cnt,
            }
            for r in brand_rows
        ],
        "campaign_roi_summary": [
            {
                "campaign": r.campaign_name,
                "type": r.campaign_type.value if hasattr(r.campaign_type, "value") else str(r.campaign_type),
                "budget": round(float(r.budget or 0), 2),
                "actual_revenue": round(float(r.actual_revenue or 0), 2),
                "actual_roi": round(float(r.actual_roi or 0), 2),
                "approval_status": r.approval_status.value if hasattr(r.approval_status, "value") else str(r.approval_status),
            }
            for r in camp_rows
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# Finance & Accounting Module
# ══════════════════════════════════════════════════════════════════════════════

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.models.sales import Invoice, InvoiceLine, Payment, Customer, InvoiceStatus
from app.models.master import Supplier, Material, Product


# ── Sales Invoices ────────────────────────────────────────────────────────────

@router.get("/accounting/sales-invoices/", response_model=List[dict],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_sales_invoices(
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Invoice)
        .options(
            selectinload(Invoice.customer),
            selectinload(Invoice.lines).selectinload(InvoiceLine.product),
        )
        .order_by(Invoice.invoice_date.desc())
        .limit(limit)
    )
    if status:
        q = q.where(Invoice.status == status)
    if customer_id:
        q = q.where(Invoice.customer_id == customer_id)
    if from_date:
        q = q.where(Invoice.invoice_date >= from_date)
    if to_date:
        q = q.where(Invoice.invoice_date <= to_date)

    rows = (await db.execute(q)).scalars().all()
    return [_build_sales_invoice_dict(r) for r in rows]


@router.get("/accounting/sales-invoices/{invoice_id}", response_model=dict,
            dependencies=[Depends(require_permission("finance", "view"))])
async def get_sales_invoice(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    q = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.customer),
            selectinload(Invoice.lines).selectinload(InvoiceLine.product),
            selectinload(Invoice.payments),
        )
    )
    inv = (await db.execute(q)).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _build_sales_invoice_dict(inv, detail=True)


@router.post("/accounting/sales-invoices/{invoice_id}/payments",
             response_model=CustomerPaymentRead, status_code=201)
async def create_customer_payment(
    invoice_id: uuid.UUID,
    body: CustomerPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    q = select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.customer))
    inv = (await db.execute(q)).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    payment = Payment(
        invoice_id=invoice_id,
        payment_date=body.payment_date,
        amount=body.amount,
        method=body.method,
        reference=body.reference,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(payment)

    # Update invoice paid_amount and status
    inv.paid_amount = (inv.paid_amount or 0) + body.amount
    if inv.paid_amount >= inv.total_amount:
        inv.status = InvoiceStatus.PAID
    else:
        inv.status = InvoiceStatus.PARTIALLY_PAID

    await db.commit()
    await db.refresh(payment)

    r = CustomerPaymentRead.model_validate(payment)
    r.invoice_no = inv.invoice_no
    r.customer_name = inv.customer.name if inv.customer else None
    return r


# ── Purchase Invoices ─────────────────────────────────────────────────────────

@router.get("/accounting/purchase-invoices/", response_model=List[PurchaseInvoiceRead],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_purchase_invoices(
    status: Optional[PurchaseInvoiceStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(PurchaseInvoice)
        .options(
            selectinload(PurchaseInvoice.supplier),
            selectinload(PurchaseInvoice.po),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.material),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.product),
        )
        .order_by(PurchaseInvoice.invoice_date.desc())
        .limit(limit)
    )
    if status:
        q = q.where(PurchaseInvoice.status == status)
    if supplier_id:
        q = q.where(PurchaseInvoice.supplier_id == supplier_id)
    if from_date:
        q = q.where(PurchaseInvoice.invoice_date >= from_date)
    if to_date:
        q = q.where(PurchaseInvoice.invoice_date <= to_date)

    rows = (await db.execute(q)).scalars().all()
    return [_build_purchase_invoice_read(r) for r in rows]


@router.get("/accounting/purchase-invoices/{invoice_id}", response_model=PurchaseInvoiceRead,
            dependencies=[Depends(require_permission("finance", "view"))])
async def get_purchase_invoice(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    q = (
        select(PurchaseInvoice)
        .where(PurchaseInvoice.id == invoice_id)
        .options(
            selectinload(PurchaseInvoice.supplier),
            selectinload(PurchaseInvoice.po),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.material),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.product),
            selectinload(PurchaseInvoice.payments),
        )
    )
    inv = (await db.execute(q)).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Purchase invoice not found")
    return _build_purchase_invoice_read(inv)


@router.post("/accounting/purchase-invoices/", response_model=PurchaseInvoiceRead, status_code=201)
async def create_purchase_invoice(
    body: PurchaseInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    from decimal import Decimal as D

    inv = PurchaseInvoice(
        invoice_no=body.invoice_no,
        supplier_id=body.supplier_id,
        po_id=body.po_id,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        currency=body.currency,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(inv)
    await db.flush()

    subtotal = D("0")
    tax_total = D("0")
    for ld in body.lines:
        line_total = ld.quantity * ld.unit_price
        tax_amount_line = line_total * ld.tax_rate
        line = PurchaseInvoiceLine(
            invoice_id=inv.id,
            material_id=ld.material_id,
            product_id=ld.product_id,
            description=ld.description,
            quantity=ld.quantity,
            unit=ld.unit,
            unit_price=ld.unit_price,
            tax_rate=ld.tax_rate,
            line_total=line_total + tax_amount_line,
        )
        db.add(line)
        subtotal += line_total
        tax_total += tax_amount_line

    inv.subtotal = subtotal
    inv.tax_amount = tax_total
    inv.total_amount = subtotal + tax_total

    await db.commit()

    q = (
        select(PurchaseInvoice)
        .where(PurchaseInvoice.id == inv.id)
        .options(
            selectinload(PurchaseInvoice.supplier),
            selectinload(PurchaseInvoice.po),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.material),
            selectinload(PurchaseInvoice.lines).selectinload(PurchaseInvoiceLine.product),
        )
    )
    inv = (await db.execute(q)).scalar_one()
    return _build_purchase_invoice_read(inv)


@router.post("/accounting/purchase-invoices/{invoice_id}/payments",
             response_model=PurchasePaymentRead, status_code=201)
async def create_purchase_payment(
    invoice_id: uuid.UUID,
    body: PurchasePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "create")),
):
    inv = (await db.execute(
        select(PurchaseInvoice).where(PurchaseInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Purchase invoice not found")

    payment = PurchasePayment(
        invoice_id=invoice_id,
        payment_date=body.payment_date,
        amount=body.amount,
        method=body.method,
        reference=body.reference,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(payment)

    inv.paid_amount = (inv.paid_amount or 0) + body.amount
    if inv.paid_amount >= inv.total_amount:
        inv.status = PurchaseInvoiceStatus.PAID
    else:
        inv.status = PurchaseInvoiceStatus.PARTIALLY_PAID

    await db.commit()
    await db.refresh(payment)
    return PurchasePaymentRead.model_validate(payment)


# ── Payments (combined view) ──────────────────────────────────────────────────

@router.get("/accounting/payments/", response_model=List[dict],
            dependencies=[Depends(require_permission("finance", "view"))])
async def list_all_payments(
    payment_type: Optional[str] = None,   # "customer" | "supplier"
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    results = []

    if payment_type in (None, "customer"):
        q = (
            select(Payment)
            .options(
                selectinload(Payment.invoice).selectinload(Invoice.customer),
            )
            .order_by(Payment.payment_date.desc())
            .limit(limit)
        )
        if from_date:
            q = q.where(Payment.payment_date >= from_date)
        if to_date:
            q = q.where(Payment.payment_date <= to_date)
        for p in (await db.execute(q)).scalars().all():
            inv = p.invoice
            results.append({
                "id": str(p.id),
                "type": "customer",
                "payment_date": str(p.payment_date),
                "amount": float(p.amount),
                "method": getattr(p, "method", "cash"),
                "reference": p.reference,
                "notes": p.notes,
                "invoice_id": str(p.invoice_id),
                "invoice_no": inv.invoice_no if inv else None,
                "party_name": inv.customer.name if (inv and inv.customer) else None,
                "created_at": str(p.created_at),
            })

    if payment_type in (None, "supplier"):
        q = (
            select(PurchasePayment)
            .options(
                selectinload(PurchasePayment.invoice).selectinload(PurchaseInvoice.supplier),
            )
            .order_by(PurchasePayment.payment_date.desc())
            .limit(limit)
        )
        if from_date:
            q = q.where(PurchasePayment.payment_date >= from_date)
        if to_date:
            q = q.where(PurchasePayment.payment_date <= to_date)
        for p in (await db.execute(q)).scalars().all():
            inv = p.invoice
            results.append({
                "id": str(p.id),
                "type": "supplier",
                "payment_date": str(p.payment_date),
                "amount": float(p.amount),
                "method": p.method,
                "reference": p.reference,
                "notes": p.notes,
                "invoice_id": str(p.invoice_id),
                "invoice_no": inv.invoice_no if inv else None,
                "party_name": inv.supplier.name if (inv and inv.supplier) else None,
                "created_at": str(p.created_at),
            })

    # Sort combined by date desc
    results.sort(key=lambda x: x["payment_date"], reverse=True)
    return results[:limit]


# ── Customer Ledger ───────────────────────────────────────────────────────────

@router.get("/accounting/customer-ledger/", response_model=List[CustomerLedgerRow],
            dependencies=[Depends(require_permission("finance", "view"))])
async def customer_ledger(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(
            Customer.id.label("customer_id"),
            Customer.code.label("customer_code"),
            Customer.name.label("customer_name"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total_invoiced"),
            func.coalesce(func.sum(Invoice.paid_amount), 0).label("total_paid"),
        )
        .outerjoin(Invoice, Invoice.customer_id == Customer.id)
        .where(Customer.is_active == True)
        .group_by(Customer.id, Customer.code, Customer.name)
        .order_by(Customer.name)
    )).all()

    return [
        CustomerLedgerRow(
            customer_id=r.customer_id,
            customer_code=r.customer_code,
            customer_name=r.customer_name,
            total_invoiced=r.total_invoiced or 0,
            total_paid=r.total_paid or 0,
            outstanding_balance=(r.total_invoiced or 0) - (r.total_paid or 0),
        )
        for r in rows
    ]


# ── Supplier Ledger ───────────────────────────────────────────────────────────

@router.get("/accounting/supplier-ledger/", response_model=List[SupplierLedgerRow],
            dependencies=[Depends(require_permission("finance", "view"))])
async def supplier_ledger(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(
            Supplier.id.label("supplier_id"),
            Supplier.code.label("supplier_code"),
            Supplier.name.label("supplier_name"),
            func.coalesce(func.sum(PurchaseInvoice.total_amount), 0).label("total_purchases"),
            func.coalesce(func.sum(PurchaseInvoice.paid_amount), 0).label("total_paid"),
        )
        .outerjoin(PurchaseInvoice, PurchaseInvoice.supplier_id == Supplier.id)
        .where(Supplier.is_active == True)
        .group_by(Supplier.id, Supplier.code, Supplier.name)
        .order_by(Supplier.name)
    )).all()

    return [
        SupplierLedgerRow(
            supplier_id=r.supplier_id,
            supplier_code=r.supplier_code,
            supplier_name=r.supplier_name,
            total_purchases=r.total_purchases or 0,
            total_paid=r.total_paid or 0,
            outstanding_payable=(r.total_purchases or 0) - (r.total_paid or 0),
        )
        for r in rows
    ]


# ── Accounting Dashboard ──────────────────────────────────────────────────────

@router.get("/accounting/dashboard/", response_model=AccountingDashboard,
            dependencies=[Depends(require_permission("finance", "view"))])
async def accounting_dashboard(db: AsyncSession = Depends(get_db)):
    from datetime import date as dt_date

    today = dt_date.today()

    # Sales invoices totals
    si = (await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
            func.coalesce(
                func.sum(Invoice.total_amount - Invoice.paid_amount), 0
            ).label("receivables"),
        )
        .where(Invoice.status.notin_([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]))
    )).one()

    # Overdue sales invoices
    overdue_sales = (await db.execute(
        select(func.count(Invoice.id))
        .where(
            and_(
                Invoice.due_date < today,
                Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            )
        )
    )).scalar() or 0

    # Purchase invoices totals
    pi = (await db.execute(
        select(
            func.coalesce(func.sum(PurchaseInvoice.total_amount), 0).label("cost"),
            func.coalesce(
                func.sum(PurchaseInvoice.total_amount - PurchaseInvoice.paid_amount), 0
            ).label("payables"),
        )
        .where(PurchaseInvoice.status.notin_([PurchaseInvoiceStatus.CANCELLED, PurchaseInvoiceStatus.DRAFT]))
    )).one()

    # Overdue purchase invoices
    overdue_purchases = (await db.execute(
        select(func.count(PurchaseInvoice.id))
        .where(
            and_(
                PurchaseInvoice.due_date < today,
                PurchaseInvoice.status.notin_([PurchaseInvoiceStatus.PAID, PurchaseInvoiceStatus.CANCELLED]),
            )
        )
    )).scalar() or 0

    # Recent sales invoices
    recent_sales_q = (await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer))
        .order_by(Invoice.invoice_date.desc())
        .limit(5)
    )).scalars().all()

    recent_purchase_q = (await db.execute(
        select(PurchaseInvoice)
        .options(selectinload(PurchaseInvoice.supplier))
        .order_by(PurchaseInvoice.invoice_date.desc())
        .limit(5)
    )).scalars().all()

    total_revenue = float(si.revenue or 0)
    total_receivables = float(si.receivables or 0)
    total_cost = float(pi.cost or 0)
    total_payables = float(pi.payables or 0)

    return AccountingDashboard(
        total_revenue=total_revenue,
        total_receivables=total_receivables,
        total_cost=total_cost,
        total_payables=total_payables,
        cash_flow=total_receivables - total_payables,
        overdue_sales_invoices=overdue_sales,
        overdue_purchase_invoices=overdue_purchases,
        recent_sales_invoices=[
            {
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer": inv.customer.name if inv.customer else "—",
                "date": str(inv.invoice_date),
                "total": float(inv.total_amount),
                "status": inv.status.value,
            }
            for inv in recent_sales_q
        ],
        recent_purchase_invoices=[
            {
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "supplier": inv.supplier.name if inv.supplier else "—",
                "date": str(inv.invoice_date),
                "total": float(inv.total_amount),
                "status": inv.status.value,
            }
            for inv in recent_purchase_q
        ],
    )


# ── Accounting Helpers ────────────────────────────────────────────────────────

def _build_sales_invoice_dict(inv: Invoice, detail: bool = False) -> dict:
    d = {
        "id": str(inv.id),
        "invoice_no": inv.invoice_no,
        "customer_id": str(inv.customer_id),
        "customer_name": inv.customer.name if inv.customer else None,
        "customer_code": inv.customer.code if inv.customer else None,
        "invoice_date": str(inv.invoice_date),
        "due_date": str(inv.due_date),
        "status": inv.status.value,
        "currency": inv.currency,
        "subtotal": float(inv.subtotal),
        "tax_amount": float(inv.tax_amount),
        "total_amount": float(inv.total_amount),
        "paid_amount": float(inv.paid_amount),
        "outstanding": float((inv.total_amount or 0) - (inv.paid_amount or 0)),
        "notes": inv.notes,
        "created_at": str(inv.created_at),
    }
    if detail and inv.lines:
        d["lines"] = [
            {
                "id": str(ln.id),
                "product_id": str(ln.product_id),
                "product_name": ln.product.name if ln.product else None,
                "description": ln.description,
                "quantity": float(ln.quantity),
                "unit": ln.unit,
                "unit_price": float(ln.unit_price),
                "discount_pct": float(ln.discount_pct),
                "tax_rate": float(ln.tax_rate),
                "line_total": float(ln.line_total),
            }
            for ln in inv.lines
        ]
        d["payments"] = [
            {
                "id": str(p.id),
                "payment_date": str(p.payment_date),
                "amount": float(p.amount),
                "method": getattr(p, "method", "cash"),
                "reference": p.reference,
            }
            for p in (inv.payments or [])
        ]
    return d


def _build_purchase_invoice_read(inv: PurchaseInvoice) -> PurchaseInvoiceRead:
    r = PurchaseInvoiceRead.model_validate(inv)
    if inv.supplier:
        r.supplier_name = inv.supplier.name
    if inv.po:
        r.po_no = inv.po.po_no
    if inv.lines:
        lines = []
        for ln in inv.lines:
            lr = PurchaseInvoiceLineRead.model_validate(ln)
            if ln.material:
                lr.material_name = ln.material.name
            if ln.product:
                lr.product_name = ln.product.name
            lines.append(lr)
        r.lines = lines
    return r
