"""PostgreSQL finance-posting regressions for M34.S04.T004."""
from __future__ import annotations

import importlib.util
import asyncio
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text

from app.api.v1.endpoints.finance import (
    create_purchase_payment,
    list_operational_posting_events,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.finance import (
    AccountType,
    AccountingPostingRule,
    ChartOfAccount,
    JournalEntry,
    JournalLine,
    InventoryAccountMapping,
    OperationalPostingEvent,
    OperationalPostingStatus,
    PurchaseInvoiceStatus,
    PurchaseInvoiceLine,
    PurchasePayment,
)
from app.models.invoice_match import InvoiceMatchTolerance
from app.schemas.finance import PurchasePaymentCreate
from app.services import finance_service, invoice_match_service, procurement_service

_seed_module_spec = importlib.util.spec_from_file_location(
    "m06_three_way_match_seed",
    Path(__file__).with_name("test_m06_s03_t001_three_way_match_db.py"),
)
if _seed_module_spec is None or _seed_module_spec.loader is None:
    raise RuntimeError("Unable to load the established synthetic PO/GRN fixture")
_seed_module = importlib.util.module_from_spec(_seed_module_spec)
_seed_module_spec.loader.exec_module(_seed_module)
_seed_chain = _seed_module._seed_chain

pytestmark = pytest.mark.skipif(
    os.environ.get("M34_S04_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the M34.S04.T004 task-owned disposable PostgreSQL database",
)


def test_purchase_payment_schema_rejects_nonfinite_amounts():
    with pytest.raises(ValidationError):
        PurchasePaymentCreate(
            invoice_id=uuid4(),
            payment_date=date(2026, 11, 4),
            amount=Decimal("NaN"),
            method="bank",
        )


@pytest.mark.asyncio
async def test_posting_event_list_filters_and_bounds_invoice_source_ids():
    expected_database = _require_task_database()
    first_source_id = str(uuid4())
    other_source_id = str(uuid4())
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        db.add_all([
            OperationalPostingEvent(
                source_module="procurement",
                source_event="PURCHASE_INVOICE_POSTED",
                source_id=first_source_id,
                status=OperationalPostingStatus.POSTED,
                event_date=date(2026, 11, 4),
                idempotency_key=f"m34-s04-t004-test-{uuid4()}",
            ),
            OperationalPostingEvent(
                source_module="procurement",
                source_event="PURCHASE_INVOICE_POSTED",
                source_id=other_source_id,
                status=OperationalPostingStatus.POSTED,
                event_date=date(2026, 11, 4),
                idempotency_key=f"m34-s04-t004-test-{uuid4()}",
            ),
        ])
        await db.commit()

        filtered = await list_operational_posting_events(
            source_module="procurement",
            source_event="PURCHASE_INVOICE_POSTED",
            source_ids=f"{first_source_id},{first_source_id}",
            limit=300,
            db=db,
        )
        assert [event.source_id for event in filtered] == [first_source_id]

        with pytest.raises(HTTPException) as too_many_error:
            await list_operational_posting_events(
                source_ids=",".join(str(uuid4()) for _ in range(501)),
                limit=500,
                db=db,
            )
        assert too_many_error.value.status_code == 422


def _require_task_database() -> str:
    expected = os.environ.get("M34_S04_T004_DISPOSABLE_TEST_DATABASE_NAME")
    url = engine.url
    valid_name = isinstance(expected, str) and re.fullmatch(
        r"fmcg_m34_s04_t004_[a-f0-9]{24}", expected,
    ) is not None
    if not (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and valid_name
        and url.database == expected
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback "
            "M34.S04.T004 disposable database without a password."
        )
    return expected


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _configure_posting_rule(db, suffix: str, *, include_tax: bool = True):
    # The disposable database is shared by the focused test module, so replace
    # only this module's synthetic rule before exercising each new fixture.
    await db.execute(delete(AccountingPostingRule).where(
        AccountingPostingRule.source_module == "procurement",
        AccountingPostingRule.source_event == "PURCHASE_INVOICE_POSTED",
    ))
    ap_account = ChartOfAccount(
        code=f"T4AP{suffix[:8].upper()}", name="Synthetic accounts payable", account_type=AccountType.LIABILITY,
    )
    tax_account = ChartOfAccount(
        code=f"T4TX{suffix[:8].upper()}", name="Synthetic recoverable tax", account_type=AccountType.ASSET,
    )
    variance_account = ChartOfAccount(
        code=f"T4VR{suffix[:8].upper()}", name="Synthetic purchase variance", account_type=AccountType.EXPENSE,
    )
    db.add_all([ap_account, tax_account, variance_account])
    await db.flush()
    db.add(AccountingPostingRule(
        source_module="procurement",
        source_event="PURCHASE_INVOICE_POSTED",
        rule_name=f"Synthetic supplier invoice rule {suffix}",
        credit_account_id=ap_account.id,
        tax_account_id=tax_account.id if include_tax else None,
        priority=100,
        is_active=True,
    ))
    await db.flush()
    return ap_account, tax_account, variance_account


async def _ready_invoice(db, suffix: str, *, price: str = "25"):
    chain = await _seed_chain(db, suffix)
    user, _, _, material, _, po, _, grn, _, invoice, invoice_line = chain
    ap_account, tax_account, variance_account = await _configure_posting_rule(db, suffix)
    mapping = await db.scalar(
        select(InventoryAccountMapping).where(InventoryAccountMapping.material_id == material.id)
    )
    assert mapping is not None
    mapping.variance_account_id = variance_account.id

    if price != "25":
        invoice_line.unit_price = Decimal(price)
        invoice_line.line_total = Decimal("10") * Decimal(price) * Decimal("1.16")
        invoice.subtotal = Decimal("10") * Decimal(price)
        invoice.tax_amount = invoice.subtotal * Decimal("0.16")
        invoice.total_amount = invoice.subtotal + invoice.tax_amount
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic two-percent price tolerance {suffix}",
            quantity_tolerance_pct=Decimal("0"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            auto_approve_within_tolerance=True,
            block_payment_beyond_tolerance=True,
            is_active=True,
        ))
        await db.flush()

    await procurement_service.post_grn(db, grn, user.id)
    match = await invoice_match_service.run_match(db, invoice.id)
    assert match.is_payable is True
    assert match.duplicate_flag is False
    return user, material, po, invoice, ap_account, tax_account, variance_account


@pytest.mark.asyncio
async def test_payable_invoice_clears_grni_and_tax_to_ap_once():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, material, _, invoice, ap, tax, _ = await _ready_invoice(db, suffix)

        event = await finance_service.post_purchase_invoice(db, invoice.id, user.id)
        assert event.status == OperationalPostingStatus.POSTED
        assert event.currency == "KES"
        assert event.amount == Decimal("290.0000")
        assert event.journal_entry_id is not None

        journal = await db.get(JournalEntry, event.journal_entry_id)
        assert journal and journal.is_posted
        assert journal.source_event == "PURCHASE_INVOICE_POSTED"
        assert journal.source_id == invoice.id
        journal_rows = list((await db.execute(
            select(JournalLine).where(JournalLine.entry_id == journal.id)
        )).scalars().all())
        by_account = {line.account_id: line for line in journal_rows}
        mapping = await db.scalar(
            select(InventoryAccountMapping).where(InventoryAccountMapping.material_id == material.id)
        )
        assert mapping is not None
        assert by_account[mapping.grni_account_id].debit == Decimal("250.0000")
        assert by_account[tax.id].debit == Decimal("40.0000")
        assert by_account[ap.id].credit == Decimal("290.0000")
        assert sum((line.debit for line in journal_rows), Decimal("0")) == sum(
            (line.credit for line in journal_rows), Decimal("0")
        )

        replay = await finance_service.post_purchase_invoice(db, invoice.id, user.id)
        assert replay.id == event.id
        assert await db.scalar(select(OperationalPostingEvent.id).where(
            OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
            OperationalPostingEvent.source_id == str(invoice.id),
        )) == event.id


@pytest.mark.asyncio
async def test_price_tolerance_posts_variance_to_configured_expense_account():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, invoice, ap, tax, variance = await _ready_invoice(db, suffix, price="25.25")

        event = await finance_service.post_purchase_invoice(db, invoice.id, user.id)
        journal_rows = list((await db.execute(
            select(JournalLine).where(JournalLine.entry_id == event.journal_entry_id)
        )).scalars().all())
        by_account = {line.account_id: line for line in journal_rows}
        assert by_account[variance.id].debit == Decimal("2.5000")
        assert by_account[tax.id].debit == Decimal("40.4000")
        assert by_account[ap.id].credit == Decimal("292.9000")
        assert sum((line.debit for line in journal_rows), Decimal("0")) == sum(
            (line.credit for line in journal_rows), Decimal("0")
        )


@pytest.mark.asyncio
async def test_invoice_without_payable_receipt_match_is_not_posted():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        chain = await _seed_chain(db, suffix)
        user, _, _, _, _, _, _, _, _, invoice, _ = chain
        await _configure_posting_rule(db, suffix)
        match = await invoice_match_service.run_match(db, invoice.id)
        assert match.is_payable is False
        invoice_id = invoice.id

        with pytest.raises(ValueError, match="payable three-way match"):
            await finance_service.post_purchase_invoice(db, invoice_id, user.id)
        assert await db.scalar(select(OperationalPostingEvent.id).where(
            OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
            OperationalPostingEvent.source_id == str(invoice_id),
        )) is None


@pytest.mark.asyncio
async def test_invoice_edits_after_matching_require_a_new_match_before_posting():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, invoice, _, _, _ = await _ready_invoice(db, suffix)
        invoice_id = invoice.id
        invoice_line = await db.scalar(
            select(PurchaseInvoiceLine).where(PurchaseInvoiceLine.invoice_id == invoice_id)
        )
        assert invoice_line is not None
        invoice_line.unit_price += Decimal("1")
        await db.commit()

        with pytest.raises(ValueError, match="changed after matching"):
            await finance_service.post_purchase_invoice(db, invoice_id, user.id)
        assert await db.scalar(select(OperationalPostingEvent.id).where(
            OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
            OperationalPostingEvent.source_id == str(invoice_id),
        )) is None


@pytest.mark.asyncio
async def test_po_invoice_payment_waits_for_general_ledger_posting():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        chain = await _seed_chain(db, suffix)
        user, _, _, _, _, _, _, _, _, invoice, _ = chain
        user.is_superuser = True
        invoice.status = PurchaseInvoiceStatus.RECEIVED
        await db.commit()
        invoice_id = invoice.id

        with pytest.raises(HTTPException) as error:
            await create_purchase_payment(
                invoice_id,
                PurchasePaymentCreate(
                    invoice_id=invoice_id,
                    payment_date=invoice.invoice_date,
                    amount=Decimal("10"),
                    method="bank",
                ),
                db,
                user,
            )
        assert error.value.status_code == 422
        assert "general ledger" in error.value.detail.lower()


@pytest.mark.asyncio
async def test_purchase_payment_requires_invoice_scope_and_payable_status():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, invoice, _, _, _ = await _ready_invoice(db, suffix)
        invoice_id = invoice.id
        user_without_scope = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
        body = PurchasePaymentCreate(
            invoice_id=invoice_id,
            payment_date=invoice.invoice_date,
            amount=Decimal("10"),
            method="bank",
        )

        with pytest.raises(HTTPException) as scope_error:
            await create_purchase_payment(invoice_id, body, db, user_without_scope)
        assert scope_error.value.status_code == 403

        user.is_superuser = True
        invoice.status = PurchaseInvoiceStatus.CANCELLED
        await db.commit()
        with pytest.raises(HTTPException) as status_error:
            await create_purchase_payment(invoice_id, body, db, user)
        assert status_error.value.status_code == 422
        assert await db.scalar(select(PurchasePayment.id).where(
            PurchasePayment.invoice_id == invoice_id,
        )) is None


@pytest.mark.asyncio
async def test_purchase_payment_rejects_overpayment_and_serializes_concurrent_requests():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, invoice, _, _, _ = await _ready_invoice(db, suffix)
        user.is_superuser = True
        invoice_id = invoice.id
        await finance_service.post_purchase_invoice(db, invoice_id, user.id)
        await db.commit()
        payment_date = invoice.invoice_date
        outstanding = invoice.total_amount

    too_large = PurchasePaymentCreate(
        invoice_id=invoice_id,
        payment_date=payment_date,
        amount=outstanding + Decimal("0.01"),
        method="bank",
    )
    async with AsyncSessionLocal() as db:
        with pytest.raises(HTTPException) as overpayment_error:
            await create_purchase_payment(invoice_id, too_large, db, user)
        assert overpayment_error.value.status_code == 422

    async def pay(amount: Decimal):
        async with AsyncSessionLocal() as db:
            payment = PurchasePaymentCreate(
                invoice_id=invoice_id,
                payment_date=payment_date,
                amount=amount,
                method="bank",
            )
            return await create_purchase_payment(invoice_id, payment, db, user)

    outcomes = await asyncio.gather(pay(outstanding), pay(outstanding), return_exceptions=True)
    successes = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    failures = [outcome for outcome in outcomes if isinstance(outcome, HTTPException)]
    assert len(successes) == 1
    assert len(failures) == 1 and failures[0].status_code == 422

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(type(invoice), invoice_id)
        assert refreshed is not None
        assert refreshed.paid_amount == outstanding
        assert refreshed.status == PurchaseInvoiceStatus.PAID
        assert await db.scalar(select(func.count(PurchasePayment.id)).where(
            PurchasePayment.invoice_id == invoice_id,
        )) == 1
