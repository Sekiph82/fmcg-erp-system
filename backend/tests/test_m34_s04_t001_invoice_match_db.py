"""PostgreSQL acceptance coverage for M34.S04.T001 matching invariants."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import PurchaseInvoice, PurchaseInvoiceLine
from app.models.invoice_match import InvoiceMatchHeader, InvoiceMatchLine, InvoiceMatchReview, MatchLineStatus
from app.models.procurement import GRNStatus, POLine
from app.schemas.invoice_match import MatchHeaderOut, ReviewCreate
from app.services import invoice_match_service

_seed_module_spec = importlib.util.spec_from_file_location(
    "m06_three_way_match_seed",
    Path(__file__).with_name("test_m06_s03_t001_three_way_match_db.py"),
)
if _seed_module_spec is None or _seed_module_spec.loader is None:
    raise RuntimeError("Unable to load the established synthetic PO/GRN/invoice fixture")
_seed_module = importlib.util.module_from_spec(_seed_module_spec)
_seed_module_spec.loader.exec_module(_seed_module)
_seed_chain = _seed_module._seed_chain


pytestmark = pytest.mark.skipif(
    os.environ.get("M34_S04_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the M34.S04.T001 task-owned disposable PostgreSQL database",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m34_s04_t001_[a-f0-9]{24}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M34_S04_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback "
            "M34.S04.T001 disposable database without a password."
        )
    return expected


def test_database_guard_accepts_only_the_exact_loopback_task_database():
    name = "fmcg_m34_s04_t001_0123456789abcdef01234567"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m34_s04_t001_1123456789abcdef01234567")
    assert not _is_task_database(safe, "fmcg_m34_s04_t001_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_currency_uom_and_ambiguous_po_line_inputs_are_blocked():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, po, po_line, grn, grn_line, invoice, invoice_line = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice.currency = "USD"
        await db.commit()

        currency_match = await invoice_match_service.run_match(db, invoice.id)
        assert currency_match.overall_status == "BLOCKED"
        assert currency_match.is_payable is False
        assert "currency" in (currency_match.match_lines[0].notes or "").lower()

        invoice.currency = "KES"
        invoice_line.unit = "EA"
        await db.commit()
        unit_match = await invoice_match_service.run_match(db, invoice.id, force_rerun=True)
        assert unit_match.overall_status == "BLOCKED"
        assert "unit" in (unit_match.match_lines[0].notes or "").lower()

        invoice_line.unit = "KG"
        grn_line.unit = "EA"
        await db.commit()
        receipt_unit_match = await invoice_match_service.run_match(db, invoice.id, force_rerun=True)
        assert receipt_unit_match.overall_status == "BLOCKED"
        assert "receipt unit" in (receipt_unit_match.match_lines[0].notes or "").lower()

        grn_line.unit = "KG"
        db.add(POLine(
            po_id=po.id,
            line_no=2,
            material_id=po_line.material_id,
            ordered_quantity=Decimal("2"),
            unit="KG",
            unit_price=Decimal("30"),
            tax_rate=Decimal("0.16"),
        ))
        await db.commit()
        ambiguous_match = await invoice_match_service.run_match(db, invoice.id, force_rerun=True)
        assert ambiguous_match.overall_status == "BLOCKED"
        assert ambiguous_match.is_payable is False
        assert "multiple PO lines" in (ambiguous_match.match_lines[0].notes or "")


@pytest.mark.asyncio
async def test_force_rerun_cannot_replace_a_reviewed_match():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, _, _, _, _, invoice, _ = await _seed_chain(db, suffix)
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)
        original_status = match.overall_status
        match = await invoice_match_service.submit_review(
            db,
            match.id,
            ReviewCreate(
                action="INFO_REQUESTED",
                reviewer_name="synthetic reviewer",
                expected_run_at=match.run_at,
            ),
        )
        assert match.reviewed_at is not None
        response = MatchHeaderOut.model_validate(match)
        assert response.reviews[0].expected_run_at is None

        with pytest.raises(ValueError, match="reviewed or approved match cannot be rerun"):
            await invoice_match_service.run_match(db, invoice.id, force_rerun=True)

        persisted = await db.get(InvoiceMatchHeader, match.id)
        assert persisted.overall_status == original_status
        assert await db.scalar(select(func.count(InvoiceMatchLine.id)).where(
            InvoiceMatchLine.header_id == match.id,
        )) == 1


@pytest.mark.asyncio
async def test_review_started_before_rerun_is_rejected_as_stale(monkeypatch):
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, _, _, grn, _, invoice, _ = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)
        match_id, invoice_id = match.id, invoice.id
        match.run_at = datetime(2000, 1, 1)
        await db.commit()

    review_started = asyncio.Event()
    allow_review_to_lock = asyncio.Event()
    original_lock = invoice_match_service._lock_match_source_rows
    pause_next_lock = True

    async def pause_review_lock(db, invoice_id):
        nonlocal pause_next_lock
        if pause_next_lock:
            pause_next_lock = False
            review_started.set()
            await allow_review_to_lock.wait()
        return await original_lock(db, invoice_id)

    monkeypatch.setattr(invoice_match_service, "_lock_match_source_rows", pause_review_lock)

    async def review_old_result():
        async with AsyncSessionLocal() as db:
            return await invoice_match_service.submit_review(
                db,
                match_id,
                ReviewCreate(
                    action="APPROVED_EXCEPTION",
                    reviewer_name="synthetic reviewer",
                    justification="synthetic review against the pre-rerun result",
                    expected_run_at=datetime(2000, 1, 1),
                ),
            )

    review_task = asyncio.create_task(review_old_result())
    await review_started.wait()
    async with AsyncSessionLocal() as rerun_db:
        await invoice_match_service.run_match(rerun_db, invoice_id, force_rerun=True)
    allow_review_to_lock.set()
    with pytest.raises(ValueError, match="Match was rerun during review"):
        await review_task

    async with AsyncSessionLocal() as stale_client_db:
        with pytest.raises(ValueError, match="Match result changed"):
            await invoice_match_service.submit_review(
                stale_client_db,
                match_id,
                ReviewCreate(
                    action="APPROVED_EXCEPTION",
                    reviewer_name="synthetic stale reviewer",
                    justification="client supplied the prior run version",
                    expected_run_at=datetime(2000, 1, 1),
                ),
            )

    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(InvoiceMatchReview.id)).where(
            InvoiceMatchReview.header_id == match_id,
        )) == 0
        persisted = await db.get(InvoiceMatchHeader, match_id)
        assert persisted.approved_at is None
        assert persisted.reviewed_at is None


@pytest.mark.asyncio
async def test_same_invoice_and_same_po_concurrent_runs_do_not_duplicate_or_overbill():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, material, _, po, _, grn, _, first_invoice, _ = await _seed_chain(db, suffix, accepted="6")
        grn.status = GRNStatus.POSTED
        second_invoice = PurchaseInvoice(
            invoice_no=f"M34-T001-SECOND-{suffix}",
            supplier_id=supplier.id,
            po_id=po.id,
            invoice_date=date(2026, 11, 4),
            due_date=date(2026, 12, 4),
            currency="KES",
            subtotal=Decimal("150"),
            tax_amount=Decimal("24"),
            total_amount=Decimal("174"),
        )
        db.add(second_invoice)
        await db.flush()
        db.add(PurchaseInvoiceLine(
            invoice_id=second_invoice.id,
            material_id=material.id,
            description=f"Synthetic concurrent invoice {suffix}",
            quantity=Decimal("6"),
            unit="KG",
            unit_price=Decimal("25"),
            tax_rate=Decimal("0.16"),
            line_total=Decimal("174"),
        ))
        await db.commit()
        first_id, second_id = first_invoice.id, second_invoice.id

    async def run(invoice_id):
        async with AsyncSessionLocal() as db:
            return await invoice_match_service.run_match(db, invoice_id)

    outcomes = await asyncio.gather(run(first_id), run(first_id), run(second_id))
    assert outcomes[0].id == outcomes[1].id
    async with AsyncSessionLocal() as db:
        first_headers = (await db.execute(
            select(InvoiceMatchHeader).where(InvoiceMatchHeader.invoice_id == first_id)
        )).scalars().all()
        second_headers = (await db.execute(
            select(InvoiceMatchHeader).where(InvoiceMatchHeader.invoice_id == second_id)
        )).scalars().all()
        assert len(first_headers) == 1
        assert len(second_headers) == 1
        statuses = {first_headers[0].overall_status, second_headers[0].overall_status}
        assert "FULLY_MATCHED" in statuses
        assert "BLOCKED" in statuses
        blocked = first_headers[0] if first_headers[0].overall_status == "BLOCKED" else second_headers[0]
        blocked_line = (await db.execute(
            select(InvoiceMatchLine).where(InvoiceMatchLine.header_id == blocked.id)
        )).scalar_one()
        assert blocked_line.match_status == MatchLineStatus.OVERBILLED
        assert blocked.is_payable is False
