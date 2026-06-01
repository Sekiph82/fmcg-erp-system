"""
Finance seed data — Chart of Accounts, Cost Centers, Fiscal Year, Accounting Periods.

Prerequisite for GL posting (TASK-017.2+). Idempotent — safe to call on every startup.
No journal entries, journal lines, or posting batches are created here.
"""
from __future__ import annotations

import calendar
import logging
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import (
    AccountType,
    AccountingPeriod,
    ChartOfAccount,
    FiscalYear,
    FiscalYearStatus,
    PeriodStatus,
)
from app.models.dimensions import CostCenter, CostCenterType

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_account(
    db: AsyncSession,
    code: str,
    name: str,
    account_type: AccountType,
    *,
    is_control: bool = False,
    parent_id: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> ChartOfAccount:
    r = await db.execute(select(ChartOfAccount).where(ChartOfAccount.code == code))
    acct = r.scalar_one_or_none()
    if acct:
        return acct
    acct = ChartOfAccount(
        code=code,
        name=name,
        account_type=account_type,
        is_control=is_control,
        parent_id=parent_id,
        currency="KES",
        is_active=True,
        notes=notes,
    )
    db.add(acct)
    await db.flush()
    return acct


async def _get_or_create_cost_center(
    db: AsyncSession,
    code: str,
    name: str,
    center_type: CostCenterType,
) -> CostCenter:
    r = await db.execute(select(CostCenter).where(CostCenter.cost_center_code == code))
    cc = r.scalar_one_or_none()
    if cc:
        return cc
    cc = CostCenter(
        cost_center_code=code,
        cost_center_name=name,
        cost_center_type=center_type,
        active=True,
    )
    db.add(cc)
    await db.flush()
    return cc


async def _get_or_create_fiscal_year(
    db: AsyncSession,
    year_code: str,
    start_date: date,
    end_date: date,
) -> FiscalYear:
    r = await db.execute(select(FiscalYear).where(FiscalYear.year_code == year_code))
    fy = r.scalar_one_or_none()
    if fy:
        return fy
    fy = FiscalYear(
        year_code=year_code,
        start_date=start_date,
        end_date=end_date,
        status=FiscalYearStatus.OPEN,
        base_currency="KES",
    )
    db.add(fy)
    await db.flush()
    return fy


async def _get_or_create_accounting_period(
    db: AsyncSession,
    period_ym: str,
    fiscal_year_id: UUID,
    period_start: date,
    period_end: date,
) -> AccountingPeriod:
    r = await db.execute(
        select(AccountingPeriod).where(AccountingPeriod.period_ym == period_ym)
    )
    ap = r.scalar_one_or_none()
    if ap:
        return ap
    ap = AccountingPeriod(
        period_ym=period_ym,
        fiscal_year_id=fiscal_year_id,
        period_start=period_start,
        period_end=period_end,
        status=PeriodStatus.OPEN,
    )
    db.add(ap)
    await db.flush()
    return ap


# ── Main entry point ──────────────────────────────────────────────────────────

async def seed_finance_data(db: AsyncSession) -> None:
    logger.info("Seeding finance data...")

    # ── Chart of Accounts ─────────────────────────────────────────────────────
    # Control (roll-up) parent accounts first so leaf accounts can reference them.

    # Assets
    assets_ctrl = await _get_or_create_account(
        db, "1000", "Assets", AccountType.ASSET, is_control=True,
        notes="Control account — do not post directly",
    )
    await _get_or_create_account(
        db, "1200", "Raw Material Inventory", AccountType.ASSET,
        parent_id=assets_ctrl.id,
    )
    await _get_or_create_account(
        db, "1210", "Work In Progress Inventory", AccountType.ASSET,
        parent_id=assets_ctrl.id,
    )
    await _get_or_create_account(
        db, "1220", "Finished Goods Inventory", AccountType.ASSET,
        parent_id=assets_ctrl.id,
    )

    # Liabilities
    liab_ctrl = await _get_or_create_account(
        db, "2000", "Liabilities", AccountType.LIABILITY, is_control=True,
        notes="Control account — do not post directly",
    )
    await _get_or_create_account(
        db, "2100", "Utilities Payable", AccountType.LIABILITY,
        parent_id=liab_ctrl.id,
    )
    await _get_or_create_account(
        db, "2110", "Goods Received Not Invoiced (GRNI)", AccountType.LIABILITY,
        parent_id=liab_ctrl.id,
    )

    # Revenue
    rev_ctrl = await _get_or_create_account(
        db, "4000", "Revenue", AccountType.REVENUE, is_control=True,
        notes="Control account — do not post directly",
    )
    await _get_or_create_account(
        db, "4100", "Product Sales Revenue", AccountType.REVENUE,
        parent_id=rev_ctrl.id,
    )

    # Expenses
    exp_ctrl = await _get_or_create_account(
        db, "5000", "Expenses", AccountType.EXPENSE, is_control=True,
        notes="Control account — do not post directly",
    )
    await _get_or_create_account(
        db, "5100", "Cost of Goods Sold", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
    )
    await _get_or_create_account(
        db, "5200", "Utility Expense", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
    )
    await _get_or_create_account(
        db, "5210", "Utility Expense Clearing", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
        notes="Clearing account — credit side of utility cost allocation journals",
    )
    await _get_or_create_account(
        db, "5300", "Production Overhead", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
    )
    await _get_or_create_account(
        db, "5310", "Production Overhead Absorbed", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
        notes="Absorbed overhead offset — credit when overhead allocated to WIP",
    )
    await _get_or_create_account(
        db, "5400", "Manufacturing Variance", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
        notes="Actual vs standard cost variance",
    )
    await _get_or_create_account(
        db, "5500", "Scrap and Waste Expense", AccountType.EXPENSE,
        parent_id=exp_ctrl.id,
    )

    logger.info("Chart of Accounts seed complete")

    # ── Cost Centers ──────────────────────────────────────────────────────────

    await _get_or_create_cost_center(
        db, "LINE-1", "Production Line 1", CostCenterType.PRODUCTION,
    )
    await _get_or_create_cost_center(
        db, "LINE-2", "Production Line 2", CostCenterType.PRODUCTION,
    )
    await _get_or_create_cost_center(
        db, "MIXING", "Mixing Department", CostCenterType.PRODUCTION,
    )
    await _get_or_create_cost_center(
        db, "FILLING", "Filling Department", CostCenterType.PRODUCTION,
    )
    await _get_or_create_cost_center(
        db, "PACKING", "Packaging Department", CostCenterType.PRODUCTION,
    )
    await _get_or_create_cost_center(
        db, "OVERHEAD", "Factory Overhead", CostCenterType.ADMIN,
    )

    logger.info("Cost Centers seed complete")

    # ── Fiscal Year + Accounting Periods ──────────────────────────────────────
    # Build current fiscal year (Jan 1 → Dec 31 of current year).
    # Seed current month + prior 3 months, all OPEN.

    today = date.today()
    fy_year = today.year
    fy_start = date(fy_year, 1, 1)
    fy_end = date(fy_year, 12, 31)
    year_code = f"FY{fy_year}"

    fy = await _get_or_create_fiscal_year(db, year_code, fy_start, fy_end)
    logger.info("Fiscal year %s seeded", year_code)

    # Current month + prior 3 months
    months_to_seed = []
    yr, mo = today.year, today.month
    for _ in range(4):
        months_to_seed.append((yr, mo))
        mo -= 1
        if mo == 0:
            mo = 12
            yr -= 1

    for yr, mo in months_to_seed:
        period_ym = f"{yr:04d}-{mo:02d}"
        p_start = date(yr, mo, 1)
        p_end = date(yr, mo, calendar.monthrange(yr, mo)[1])
        # If month belongs to a different fiscal year, still link to seeded FY
        # (only happens for months prior to Jan of current year, e.g. Dec 2025)
        p_fy_id = fy.id if yr == fy_year else None
        await _get_or_create_accounting_period(
            db, period_ym, p_fy_id, p_start, p_end,
        )

    logger.info("Accounting periods seeded: %s", [f"{y:04d}-{m:02d}" for y, m in months_to_seed])

    await db.flush()
    logger.info("Finance seed complete")
