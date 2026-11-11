"""M17.S02.T003 — bank statement file import into bank reconciliation on disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.bank_reconciliation import BRBankAccount, BRStatement, BRStatementLine
from app.services import bank_reconciliation_service as svc
from test_bank_statement_parsers import CAMT053, CSV, MT940

TASK_DB_ENV = "M17_S02_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M17_S02_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m17_s02_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _account(db, currency="KES", masked="****5678"):
    expected = os.environ.get(TASK_DB_NAME_ENV, "")
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
    assert TASK_DB_PATTERN.fullmatch(expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected
    account = BRBankAccount(bank_name="Synthetic Bank", account_name=f"Operating {uuid4().hex[:6]}",
                            account_number_masked=masked, currency=currency)
    db.add(account)
    await db.commit()
    return account.id


@pytest.mark.asyncio
async def test_camt_import_persists_verified_statement_and_rejects_bad_files():
    async with AsyncSessionLocal() as db:
        account_id = await _account(db)
        statement = await svc.import_statement_file(db, account_id, "CAMT053", CAMT053, "oct.xml", imported_by="tester")
        assert statement.import_source.value == "CAMT053" and statement.import_file_name == "oct.xml"
        assert statement.total_lines == 2
        assert statement.total_credits == Decimal("20000.50") and statement.total_debits == Decimal("7500.00")
        assert statement.opening_balance == Decimal("100000.00") and statement.closing_balance == Decimal("112500.50")
        lines = (await db.execute(select(BRStatementLine).where(BRStatementLine.statement_id == statement.id)
                                  .order_by(BRStatementLine.line_no))).scalars().all()
        assert [(l.debit_credit_indicator, l.amount) for l in lines] == [("C", Decimal("20000.50")), ("D", Decimal("7500.00"))]
        assert lines[0].counterparty_name == "Synthetic Retail Ltd"

        with pytest.raises(ValueError, match="already been imported"):
            await svc.import_statement_file(db, account_id, "MT940", MT940, "oct.mt940")
        await db.rollback()

        tampered = CSV.replace(b'"112,500.50"', b'"112,600.50"')
        other = await _account(db)
        with pytest.raises(ValueError, match="does not balance"):
            await svc.import_statement_file(db, other, "CSV", tampered, "bad.csv")
        await db.rollback()

        usd = await _account(db, currency="USD")
        with pytest.raises(ValueError, match="currency KES does not match"):
            await svc.import_statement_file(db, usd, "MT940", MT940, "oct.mt940")
        await db.rollback()

        wrong_account = await _account(db, masked="****9999")
        with pytest.raises(ValueError, match="account number does not match"):
            await svc.import_statement_file(db, wrong_account, "CAMT053", CAMT053, "oct.xml")
        await db.rollback()
        assert (await db.execute(select(func.count()).select_from(BRStatement).where(
            BRStatement.bank_account_id.in_([other, usd, wrong_account])))).scalar_one() == 0

        mt = await _account(db)
        imported = await svc.import_statement_file(db, mt, "MT940", MT940, "oct.mt940")
        assert imported.import_source.value == "MT940" and imported.total_lines == 2
