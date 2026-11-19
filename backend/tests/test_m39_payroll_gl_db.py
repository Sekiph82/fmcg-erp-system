"""M39 hand-off HR → accounting: approving a payroll run books it in the general ledger through the payroll posting
rule (gross expense = net pay payable + statutory deductions payable), once; without a rule, approval still works."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import AccountingPostingRule, AccountType, ChartOfAccount, JournalEntry, JournalLine
from app.models.payroll_ke import PayrollRun, PayrollRunStatus
from app.models.user import User
from app.services.payroll_ke_service import approve_payroll_run, post_payroll_to_gl

TASK_DB_ENV = "M39_PAY_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M39_PAY_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m39_pay_[a-f0-9]{24}")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _run(year: int) -> PayrollRun:
    return PayrollRun(run_no=f"PR-{uuid.uuid4().hex[:8]}", period_month=1, period_year=year, period_start=date(year, 1, 1),
                      period_end=date(year, 1, 31), status=PayrollRunStatus.CALCULATED, total_gross=Decimal("100000"),
                      total_paye=Decimal("20000"), total_nhif=Decimal("2750"), total_nssf=Decimal("2160"),
                      total_housing_levy=Decimal("1500"), total_net=Decimal("73590"))


@pytest.mark.asyncio
async def test_approved_payroll_is_booked_in_the_ledger():
    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        hr = User(email=f"hr-{s}@example.com", username=f"hr{s}", full_name="HR", hashed_password="x")
        db.add(hr)
        await db.flush()
        # no rule yet: approval works, nothing is booked
        bare = _run(2101)
        db.add(bare)
        await db.flush()
        await approve_payroll_run(db, bare, hr.id)
        assert bare.status == PayrollRunStatus.APPROVED
        assert (await db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.source_id == bare.id))).scalar() == 0

        exp, net, ded = (ChartOfAccount(code=f"PAYX{s}", name="Salaries", account_type=AccountType.EXPENSE, currency="KES"),
                         ChartOfAccount(code=f"PAYN{s}", name="Net pay payable", account_type=AccountType.LIABILITY, currency="KES"),
                         ChartOfAccount(code=f"PAYD{s}", name="Statutory payable", account_type=AccountType.LIABILITY, currency="KES"))
        db.add_all([exp, net, ded])
        await db.flush()
        db.add(AccountingPostingRule(source_module="payroll", source_event="PAYROLL_APPROVED", rule_name="Payroll",
                                     debit_account_id=exp.id, credit_account_id=net.id, tax_account_id=ded.id,
                                     priority=1, is_active=True))
        run = _run(2102)
        db.add(run)
        await db.flush()
        await approve_payroll_run(db, run, hr.id)
        await db.commit()

        je = (await db.execute(select(JournalEntry).where(JournalEntry.source_id == run.id))).scalar_one()
        assert je.source_module == "payroll" and je.is_posted and je.entry_date == date(2102, 1, 31)
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert lines == {(exp.id, Decimal("100000"), Decimal("0")), (net.id, Decimal("0"), Decimal("73590")),
                         (ded.id, Decimal("0"), Decimal("26410"))}, lines
        again = await post_payroll_to_gl(db, run, hr.id)       # booked once, never twice
        assert again.id == je.id


@pytest.mark.asyncio
async def test_finance_approved_expense_claim_is_booked_in_the_ledger():
    from sqlalchemy.orm import selectinload

    from app.models.expenses import ExpenseClaim
    from app.services.expenses_service import _post_claim_to_gl

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        fin = User(email=f"fin-{s}@example.com", username=f"fin{s}", full_name="Fin", hashed_password="x")
        exp, pay = (ChartOfAccount(code=f"EXPX{s}", name="Travel", account_type=AccountType.EXPENSE, currency="KES"),
                    ChartOfAccount(code=f"EXPP{s}", name="Employee payable", account_type=AccountType.LIABILITY, currency="KES"))
        db.add_all([fin, exp, pay])
        await db.flush()
        claim = ExpenseClaim(claim_no=f"EC-{s}", employee_id=uuid.uuid4(), claim_date=date.today(),
                             total_approved_amount=Decimal("5000"), approved_by_finance=fin.id)
        db.add(claim)
        await db.flush()
        claim = (await db.execute(select(ExpenseClaim).options(selectinload(ExpenseClaim.lines))
                                  .where(ExpenseClaim.expense_claim_id == claim.expense_claim_id))).scalar_one()
        assert await _post_claim_to_gl(db, claim) is None                   # no rule: sub-ledger only
        db.add(AccountingPostingRule(source_module="expenses", source_event="EXPENSE_FINANCE_APPROVED", rule_name="Expenses",
                                     debit_account_id=exp.id, credit_account_id=pay.id, priority=1, is_active=True))
        await db.flush()
        je = await _post_claim_to_gl(db, claim)
        await db.commit()
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert je.source_module == "expenses" and lines == {(exp.id, Decimal("5000"), Decimal("0")), (pay.id, Decimal("0"), Decimal("5000"))}
