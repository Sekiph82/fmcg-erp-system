"""M07.S03.T001 synthetic PostgreSQL verification of the order-to-payment subledger."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.engine import URL

from app.crud.sales import get_shipment
from app.db.session import AsyncSessionLocal, engine
from app.api.v1.endpoints.finance import create_customer_payment as create_finance_customer_payment
from app.api.v1.endpoints.sales import record_payment as create_sales_payment
from app.models.inventory import Stock, StockMovement, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.sales import (
    Customer,
    Invoice,
    InvoiceStatus,
    Payment,
    SOStatus,
    SalesOrder,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
    SOLine,
)
from app.models.user import User
from app.models.finance import (
    AccountType,
    AccountingPostingBatch,
    AccountingPostingRule,
    ChartOfAccount,
    JournalEntry,
    JournalLine,
    JournalStatus,
    OperationalPostingEvent,
    OperationalPostingStatus,
    PostingBatchStatus,
)
from app.schemas.finance import CustomerPaymentCreate
from app.schemas.sales import PaymentCreate
from app.services import sales_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M07_S03_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m07_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M07_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M07_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M07_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M07.S03.T001 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m07_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m07_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m07_s03_t001_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="never-used", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


async def _assert_posted_source_journal(
    db, *, source_id, source_event: str, debit: Decimal, credit: Decimal,
    expected_accounts: dict,
) -> JournalEntry:
    event = (await db.execute(
        select(OperationalPostingEvent).where(
            OperationalPostingEvent.source_module == "sales",
            OperationalPostingEvent.source_event == source_event,
            OperationalPostingEvent.source_id == str(source_id),
        )
    )).scalar_one()
    assert event.status == OperationalPostingStatus.POSTED
    assert event.journal_entry_id is not None
    batch = await db.get(AccountingPostingBatch, event.posting_batch_id)
    assert batch is not None
    assert batch.status == PostingBatchStatus.POSTED
    assert batch.journal_entry_id == event.journal_entry_id
    entry = (await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == event.journal_entry_id)
    )).scalar_one()
    assert entry.status == JournalStatus.POSTED
    assert entry.is_posted is True
    assert entry.source_module == "sales"
    assert entry.source_event == source_event
    assert entry.source_id == source_id
    assert sum((line.debit for line in entry.lines), Decimal("0")) == debit
    assert sum((line.credit for line in entry.lines), Decimal("0")) == credit
    actual_accounts = {}
    for line in entry.lines:
        prior_debit, prior_credit = actual_accounts.get(line.account_id, (Decimal("0"), Decimal("0")))
        actual_accounts[line.account_id] = (prior_debit + line.debit, prior_credit + line.credit)
    assert actual_accounts == expected_accounts
    return entry


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_confirmed_order_dispatch_invoice_and_customer_payment_subledger():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user = User(
            email=f"m07-t001-{suffix}@example.invalid",
            username=f"m07t001{suffix}",
            full_name="Synthetic M07 T001 actor",
            hashed_password="synthetic-test-only-not-a-credential",
        )
        customer = Customer(code=f"M07-T001-C-{suffix}", name="Synthetic customer M07 T001")
        product = Product(
            sku=f"M07-T001-P-{suffix}", name="Synthetic finished product",
            category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS,
        )
        warehouse = Warehouse(
            code=f"M07-T001-W-{suffix}", name="Synthetic finished-goods warehouse",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([user, customer, product, warehouse])
        await db.flush()
        user_id = user.id

        receivables = ChartOfAccount(
            code=f"M07AR{suffix[:10]}", name="Synthetic trade receivables",
            account_type=AccountType.ASSET, currency="KES",
        )
        alternate_receivables = ChartOfAccount(
            code=f"M07ARX{suffix[:9]}", name="Synthetic alternate receivables",
            account_type=AccountType.ASSET, currency="KES",
        )
        revenue = ChartOfAccount(
            code=f"M07REV{suffix[:9]}", name="Synthetic sales revenue",
            account_type=AccountType.REVENUE, currency="KES",
        )
        output_tax = ChartOfAccount(
            code=f"M07TAX{suffix[:9]}", name="Synthetic output tax payable",
            account_type=AccountType.LIABILITY, currency="KES",
        )
        cash_clearing = ChartOfAccount(
            code=f"M07CASH{suffix[:8]}", name="Synthetic cash clearing",
            account_type=AccountType.ASSET, currency="KES",
        )
        bank_clearing = ChartOfAccount(
            code=f"M07BANK{suffix[:8]}", name="Synthetic bank clearing",
            account_type=AccountType.ASSET, currency="KES",
        )
        mpesa_clearing = ChartOfAccount(
            code=f"M07MPESA{suffix[:7]}", name="Synthetic mobile-money clearing",
            account_type=AccountType.ASSET, currency="KES",
        )
        db.add_all([
            receivables, alternate_receivables, revenue, output_tax,
            cash_clearing, bank_clearing, mpesa_clearing,
        ])
        await db.flush()
        receivables_id = receivables.id
        alternate_receivables_id = alternate_receivables.id
        revenue_id = revenue.id
        output_tax_id = output_tax.id
        cash_clearing_id = cash_clearing.id
        bank_clearing_id = bank_clearing.id
        mpesa_clearing_id = mpesa_clearing.id
        invoice_rule = AccountingPostingRule(
            source_module="sales",
            source_event="SALES_INVOICE_ISSUED",
            rule_name="Synthetic M07 invoice posting rule",
            debit_account_id=receivables.id,
            credit_account_id=revenue.id,
            tax_account_id=output_tax.id,
            priority=1,
            is_active=True,
        )
        cash_rule = AccountingPostingRule(
            source_module="sales",
            source_event="CUSTOMER_PAYMENT_RECEIVED_CASH",
            rule_name="Synthetic M07 cash receipt posting rule",
            credit_account_id=receivables.id,
            clearing_account_id=cash_clearing.id,
            priority=1,
            is_active=True,
        )
        bank_rule = AccountingPostingRule(
            source_module="sales",
            source_event="CUSTOMER_PAYMENT_RECEIVED_BANK",
            rule_name="Synthetic M07 bank receipt posting rule",
            credit_account_id=receivables.id,
            clearing_account_id=bank_clearing.id,
            priority=1,
            is_active=True,
        )
        mpesa_rule = AccountingPostingRule(
            source_module="sales",
            source_event="CUSTOMER_PAYMENT_RECEIVED_MPESA",
            rule_name="Synthetic M07 mobile-money receipt posting rule",
            credit_account_id=receivables.id,
            clearing_account_id=mpesa_clearing.id,
            priority=1,
            is_active=True,
        )
        db.add_all([invoice_rule, cash_rule, bank_rule, mpesa_rule])
        await db.flush()
        cash_rule_id = cash_rule.id

        stock = Stock(
            stock_type=StockType.PRODUCT,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity_on_hand=Decimal("10"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("10"),
            is_blocked=False,
        )
        order = SalesOrder(
            order_no=f"M07-T001-SO-{suffix}",
            customer_id=customer.id,
            order_date=date(2026, 10, 28),
            requested_delivery_date=date(2026, 10, 29),
            status=SOStatus.CONFIRMED,
            currency="KES",
        )
        db.add_all([stock, order])
        await db.flush()
        order_line = SOLine(
            so_id=order.id,
            line_no=1,
            product_id=product.id,
            ordered_quantity=Decimal("3"),
            unit="PCS",
            unit_price=Decimal("10"),
            tax_rate=Decimal("0.16"),
        )
        fractional_cent_line = SOLine(
            so_id=order.id,
            line_no=2,
            product_id=product.id,
            ordered_quantity=Decimal("1"),
            unit="PCS",
            unit_price=Decimal("0.005"),
            tax_rate=Decimal("0.16"),
        )
        db.add_all([order_line, fractional_cent_line])
        await db.flush()
        await db.commit()

        await sales_service.allocate_so(db, order, warehouse.id, user.id)
        await db.commit()
        shipment = Shipment(
            shipment_no=f"M07-T001-SH-{suffix}",
            so_id=order.id,
            warehouse_id=warehouse.id,
            status=ShipmentStatus.PENDING,
            scheduled_date=date(2026, 10, 29),
        )
        db.add(shipment)
        await db.flush()
        shipment_line = ShipmentLine(
            shipment_id=shipment.id,
            so_line_id=order_line.id,
            product_id=product.id,
            quantity=Decimal("3"),
            unit="PCS",
        )
        fractional_cent_shipment_line = ShipmentLine(
            shipment_id=shipment.id,
            so_line_id=fractional_cent_line.id,
            product_id=product.id,
            quantity=Decimal("1"),
            unit="PCS",
        )
        db.add_all([shipment_line, fractional_cent_shipment_line])
        await db.commit()

        await sales_service.dispatch_shipment(db, shipment, date(2026, 10, 29), user.id)
        await db.commit()
        shipment = await get_shipment(db, shipment.id)
        assert shipment is not None
        shipment_no = shipment.shipment_no
        assert shipment.status == ShipmentStatus.DISPATCHED
        assert order.status == SOStatus.SHIPPED

        invoice = await sales_service.invoice_from_shipment(
            db,
            shipment,
            invoice_no=f"M07-T001-INV-{suffix}",
            invoice_date=date(2026, 10, 29),
            due_date=date(2026, 11, 28),
            user_id=user.id,
        )
        await db.commit()
        invoice_id = invoice.id
        assert order.status == SOStatus.INVOICED
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.subtotal == Decimal("30.00")
        assert invoice.tax_amount == Decimal("4.80")
        assert invoice.total_amount == Decimal("34.80")
        assert invoice.paid_amount == Decimal("0.0000")
        invoice_journal = await _assert_posted_source_journal(
            db,
            source_id=invoice.id,
            source_event="SALES_INVOICE_ISSUED",
            debit=Decimal("34.8000"),
            credit=Decimal("34.8000"),
            expected_accounts={
                receivables.id: (Decimal("34.8000"), Decimal("0")),
                revenue.id: (Decimal("0"), Decimal("30.0000")),
                output_tax.id: (Decimal("0"), Decimal("4.8000")),
            },
        )
        assert invoice_journal.source_ref == invoice.invoice_no

        # Missing channel mappings fail closed and do not create a subledger payment.
        cash_rule.is_active = False
        await db.commit()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as missing_rule_error:
            await sales_service.record_payment(
                db, invoice, Decimal("10.00"), date(2026, 10, 30),
                f"M07-T001-PAY-MISSING-{suffix}", None, user_id,
            )
        assert missing_rule_error.value.status_code == 422
        assert "No active accounting posting rule" in str(missing_rule_error.value.detail)
        await db.rollback()
        invoice = await db.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.paid_amount == Decimal("0.0000")
        assert await db.scalar(select(func.count(Payment.id)).where(Payment.invoice_id == invoice_id)) == 0
        cash_rule = await db.get(AccountingPostingRule, cash_rule_id)
        assert cash_rule is not None
        cash_rule.is_active = True
        await db.commit()

        cash_rule.credit_account_id = alternate_receivables_id
        await db.commit()
        with pytest.raises(HTTPException) as wrong_receivables_error:
            await sales_service.record_payment(
                db, invoice, Decimal("10.00"), date(2026, 10, 30),
                f"M07-T001-PAY-WRONG-AR-{suffix}", None, user_id,
            )
        assert wrong_receivables_error.value.status_code == 422
        await db.rollback()
        invoice = await db.get(Invoice, invoice_id)
        assert invoice is not None
        cash_rule = await db.get(AccountingPostingRule, cash_rule_id)
        assert cash_rule is not None
        cash_rule.credit_account_id = receivables_id
        await db.commit()

        with pytest.raises(HTTPException) as overpayment_error:
            await sales_service.record_payment(
                db, invoice, Decimal("34.81"), date(2026, 10, 30),
                f"M07-T001-PAY-OVER-{suffix}", None, user_id,
            )
        assert overpayment_error.value.status_code == 422
        await db.rollback()
        invoice = await db.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.paid_amount == Decimal("0.0000")

        partial = await sales_service.record_payment(
            db, invoice, Decimal("10.00"), date(2026, 10, 30), f"M07-T001-PAY-A-{suffix}", None, user_id,
        )
        await db.commit()
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID
        assert invoice.paid_amount == Decimal("10.0000")

        current_user = await db.get(User, user_id)
        assert current_user is not None
        bank = await create_sales_payment(
            invoice_id,
            PaymentCreate(
                payment_date=date(2026, 10, 31),
                amount=Decimal("10.00"),
                method="bank",
                reference=f"M07-T001-PAY-B-{suffix}",
            ),
            db=db,
            current_user=current_user,
        )
        mpesa = await create_finance_customer_payment(
            invoice_id,
            CustomerPaymentCreate(
                invoice_id=invoice_id,
                payment_date=date(2026, 11, 1),
                amount=invoice.total_amount - invoice.paid_amount,
                method="mpesa",
                reference=f"M07-T001-PAY-C-{suffix}",
            ),
            db=db,
            current_user=current_user,
        )
        assert bank.method == "bank"
        assert mpesa.method == "mpesa"
        await db.refresh(invoice)
        persisted_payments = await db.execute(
            select(Payment).where(Payment.invoice_id == invoice_id)
        )
        assert len(list(persisted_payments.scalars().all())) == 3
        assert len({partial.id, bank.id, mpesa.id}) == 3
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.paid_amount == invoice.total_amount
        partial_journal = await _assert_posted_source_journal(
            db,
            source_id=partial.id,
            source_event="CUSTOMER_PAYMENT_RECEIVED_CASH",
            debit=Decimal("10.0000"),
            credit=Decimal("10.0000"),
            expected_accounts={
                cash_clearing_id: (Decimal("10.0000"), Decimal("0")),
                receivables_id: (Decimal("0"), Decimal("10.0000")),
            },
        )
        bank_journal = await _assert_posted_source_journal(
            db,
            source_id=bank.id,
            source_event="CUSTOMER_PAYMENT_RECEIVED_BANK",
            debit=Decimal("10.0000"),
            credit=Decimal("10.0000"),
            expected_accounts={
                bank_clearing_id: (Decimal("10.0000"), Decimal("0")),
                receivables_id: (Decimal("0"), Decimal("10.0000")),
            },
        )
        mpesa_journal = await _assert_posted_source_journal(
            db,
            source_id=mpesa.id,
            source_event="CUSTOMER_PAYMENT_RECEIVED_MPESA",
            debit=Decimal("14.8000"),
            credit=Decimal("14.8000"),
            expected_accounts={
                mpesa_clearing_id: (Decimal("14.8000"), Decimal("0")),
                receivables_id: (Decimal("0"), Decimal("14.8000")),
            },
        )
        assert len({partial_journal.id, bank_journal.id, mpesa_journal.id}) == 3
        movement_count = await db.scalar(
            select(func.count(StockMovement.id)).where(
                StockMovement.reference_number == shipment_no
            )
        )
        assert movement_count == 2
