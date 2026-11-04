"""M34.S05.T003: API-level three-way-match to finance posting workflow."""
from __future__ import annotations

import importlib.util
import os
import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.finance import (
    AccountType,
    AccountingPostingRule,
    ChartOfAccount,
    InventoryAccountMapping,
    JournalEntry,
    JournalLine,
    OperationalPostingEvent,
    OperationalPostingStatus,
)
from app.models.inventory import Stock, StockMovement
from app.models.invoice_match import (
    InvoiceMatchGRNLink,
    InvoiceMatchHeader,
    InvoiceMatchLine,
    MatchOverallStatus,
)
from app.models.procurement import GRNStatus, POStatus
from app.models.two_factor import TwoFAMethod, User2FASettings
from app.models.user import User


TASK_DB_ENV = "M34_S05_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S05_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s05_t003_[a-f0-9]{24}")

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
    os.environ.get(TASK_DB_ENV) != "1",
    reason="requires this task's explicitly guarded disposable PostgreSQL database",
)


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    url = engine.url
    if not (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected, str)
        and TASK_DB_PATTERN.fullmatch(expected)
        and url.database == expected
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this task's exact "
            "passwordless loopback PostgreSQL database."
        )
    return expected


def _auth_cookies(user: User) -> dict[str, str]:
    return {
        settings.AUTH_COOKIE_NAME: create_access_token(
            str(user.id), session_version=user.auth_session_version,
        )
    }


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_grn_match_and_finance_posting_are_one_authenticated_workflow(monkeypatch):
    expected_database = _require_task_database()
    monkeypatch.setattr(settings, "SECRET_KEY", "M34-S05-T003-SYNTHETIC-ONLY-SECRET-KEY")
    suffix = uuid4().hex[:16]
    client_transport = ASGITransport(app=app)

    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, material, warehouse, po, _, grn, _, invoice, _ = await _seed_chain(db, suffix)
        user.is_superuser = True
        db.add(User2FASettings(
            user_id=user.id,
            is_enabled=True,
            method=TwoFAMethod.TOTP,
            secret_key=f"SYNTHETIC-M34-S05-T003-{suffix}",
        ))

        ap_account = ChartOfAccount(
            code=f"T3AP{suffix[:8].upper()}",
            name="Synthetic accounts payable",
            account_type=AccountType.LIABILITY,
        )
        tax_account = ChartOfAccount(
            code=f"T3TX{suffix[:8].upper()}",
            name="Synthetic recoverable tax",
            account_type=AccountType.ASSET,
        )
        variance_account = ChartOfAccount(
            code=f"T3VR{suffix[:8].upper()}",
            name="Synthetic purchase variance",
            account_type=AccountType.EXPENSE,
        )
        db.add_all([ap_account, tax_account, variance_account])
        await db.flush()
        db.add(AccountingPostingRule(
            source_module="procurement",
            source_event="PURCHASE_INVOICE_POSTED",
            rule_name=f"Synthetic invoice posting rule {suffix}",
            credit_account_id=ap_account.id,
            tax_account_id=tax_account.id,
            priority=100,
            is_active=True,
        ))
        mapping = await db.scalar(
            select(InventoryAccountMapping).where(InventoryAccountMapping.material_id == material.id)
        )
        assert mapping is not None
        mapping.variance_account_id = variance_account.id
        ids = {
            "user": user.id,
            "material": material.id,
            "warehouse": warehouse.id,
            "po": po.id,
            "grn": grn.id,
            "invoice": invoice.id,
        }
        expected_total = invoice.total_amount
        grn_no = grn.grn_no
        await db.commit()

    cookies = _auth_cookies(user)
    async with AsyncClient(
        transport=client_transport,
        base_url="http://m34-s05-t003.test",
        cookies=cookies,
    ) as client:
        # A draft receipt cannot clear the invoice hold or create a ledger event.
        blocked_match = await client.post(
            "/api/v1/invoice-match/run",
            json={"invoice_id": str(ids["invoice"])},
        )
        assert blocked_match.status_code == 200, blocked_match.text
        assert blocked_match.json()["overall_status"] == MatchOverallStatus.BLOCKED.value
        assert blocked_match.json()["is_payable"] is False
        assert "GRN" in blocked_match.json()["payment_hold_reason"]

        rejected_post = await client.post(
            f"/api/v1/finance/accounting/purchase-invoices/{ids['invoice']}/post",
        )
        assert rejected_post.status_code == 422, rejected_post.text

        async with AsyncSessionLocal() as db:
            assert await db.scalar(select(OperationalPostingEvent.id).where(
                OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
                OperationalPostingEvent.source_id == str(ids["invoice"]),
            )) is None

        # Posting the GRN through procurement updates stock and makes the saved
        # PO/GRN/invoice quantities eligible for a new payable match.
        posted_grn = await client.post(f"/api/v1/procurement/grn/{ids['grn']}/post")
        assert posted_grn.status_code == 200, posted_grn.text
        assert posted_grn.json()["status"] == GRNStatus.POSTED.value

        match_response = await client.post(
            "/api/v1/invoice-match/run",
            json={"invoice_id": str(ids["invoice"]), "force_rerun": True},
        )
        assert match_response.status_code == 200, match_response.text
        matched = match_response.json()
        assert matched["overall_status"] == MatchOverallStatus.FULLY_MATCHED.value
        assert matched["is_payable"] is True
        assert matched["invoice_id"] == str(ids["invoice"])
        assert len(matched["match_lines"]) == 1
        match_line = matched["match_lines"][0]
        assert match_line["po_line_id"]
        assert Decimal(match_line["total_accepted_qty"]) == Decimal("10")
        assert Decimal(match_line["billable_qty"]) == Decimal("10")
        assert Decimal(match_line["invoiced_qty"]) == Decimal("10")
        assert len(match_line["grn_links"]) == 1
        assert match_line["grn_links"][0]["grn_id"] == str(ids["grn"])

        posted_event = await client.post(
            f"/api/v1/finance/accounting/purchase-invoices/{ids['invoice']}/post",
        )
        assert posted_event.status_code == 200, posted_event.text
        event_payload = posted_event.json()
        assert event_payload["source_module"] == "procurement"
        assert event_payload["source_event"] == "PURCHASE_INVOICE_POSTED"
        assert event_payload["source_id"] == str(ids["invoice"])
        assert event_payload["status"] == OperationalPostingStatus.POSTED.value
        assert Decimal(event_payload["amount"]) == expected_total
        assert event_payload["journal_entry_id"]

        replay = await client.post(
            f"/api/v1/finance/accounting/purchase-invoices/{ids['invoice']}/post",
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == event_payload["id"]

        invoice_read = await client.get(
            f"/api/v1/finance/accounting/purchase-invoices/{ids['invoice']}",
        )
        assert invoice_read.status_code == 200, invoice_read.text
        # GL posting is linked through the immutable event; the invoice remains
        # RECEIVED until the separate supplier-payment lifecycle changes it.
        assert invoice_read.json()["status"] == "RECEIVED"

    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        persisted_grn = await db.get(type(grn), ids["grn"])
        persisted_po = await db.get(type(po), ids["po"])
        assert persisted_grn and persisted_grn.status == GRNStatus.POSTED
        assert persisted_po and persisted_po.status == POStatus.RECEIVED

        stock = await db.scalar(select(Stock).where(
            Stock.material_id == ids["material"], Stock.warehouse_id == ids["warehouse"],
        ))
        assert stock is not None and stock.quantity_on_hand == Decimal("10")
        assert await db.scalar(select(func.count(StockMovement.id)).where(
            StockMovement.reference_number == grn_no,
        )) == 1

        match = await db.scalar(select(InvoiceMatchHeader).where(
            InvoiceMatchHeader.invoice_id == ids["invoice"],
        ))
        assert match and match.is_payable is True
        match_line = await db.scalar(select(InvoiceMatchLine).where(
            InvoiceMatchLine.header_id == match.id,
        ))
        assert match_line is not None
        assert await db.scalar(select(func.count(InvoiceMatchGRNLink.id)).where(
            InvoiceMatchGRNLink.match_line_id == match_line.id,
        )) == 1

        event = await db.scalar(select(OperationalPostingEvent).where(
            OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
            OperationalPostingEvent.source_id == str(ids["invoice"]),
        ))
        assert event is not None and str(event.id) == event_payload["id"]
        assert event.status == OperationalPostingStatus.POSTED
        journal = await db.get(JournalEntry, event.journal_entry_id)
        assert journal and journal.is_posted and journal.source_id == ids["invoice"]
        lines = list((await db.execute(
            select(JournalLine).where(JournalLine.entry_id == journal.id)
        )).scalars().all())
        assert sum((line.debit for line in lines), start=Decimal("0")) == sum(
            (line.credit for line in lines), start=Decimal("0")
        )
        by_account = {line.account_id: line for line in lines}
        assert by_account[mapping.grni_account_id].debit == Decimal("250")
        assert by_account[tax_account.id].debit == Decimal("40")
        assert by_account[ap_account.id].credit == Decimal("290")
        assert await db.scalar(select(func.count(OperationalPostingEvent.id)).where(
            OperationalPostingEvent.source_event == "PURCHASE_INVOICE_POSTED",
            OperationalPostingEvent.source_id == str(ids["invoice"]),
        )) == 1
