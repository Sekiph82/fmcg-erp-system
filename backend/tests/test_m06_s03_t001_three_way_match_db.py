"""M06.S03.T001 synthetic PostgreSQL verification of the PO/GRN/invoice chain."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import PurchaseInvoice, PurchaseInvoiceLine
from app.models.inventory import Stock, StockMovement
from app.models.master import Material, MaterialType, Supplier, UnitOfMeasure, Warehouse, WarehouseType
from app.models.user import User
from app.models.invoice_match import (
    InvoiceMatchGRNLink,
    InvoiceMatchHeader,
    InvoiceMatchLine,
    MatchLineStatus,
    MatchOverallStatus,
)
from app.models.procurement import (
    GoodsReceipt,
    GRNLine,
    GRNStatus,
    POStatus,
    POLine,
    PurchaseOrder,
)
from app.services import invoice_match_service, procurement_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M06_S03_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m06_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M06_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M06_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M06_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M06.S03.T001 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m06_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m06_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m06_s03_t001_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="never-used", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _seed_chain(db, suffix: str, accepted: str = "10"):
    user = User(
        email=f"m06-t001-{suffix}@example.invalid", username=f"m06t001{suffix}",
        full_name=f"Synthetic M06 T001 actor {suffix}",
        hashed_password="synthetic-test-only-not-a-credential",
    )
    supplier = Supplier(code=f"M06-T001-S-{suffix}", name=f"Synthetic supplier {suffix}")
    other_supplier = Supplier(code=f"M06-T001-X-{suffix}", name=f"Other synthetic supplier {suffix}")
    material = Material(
        code=f"M06-T001-M-{suffix}", name=f"Synthetic raw material {suffix}",
        material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M06-T001-W-{suffix}", name=f"Synthetic raw warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
    )
    db.add_all([user, supplier, other_supplier, material, warehouse])
    await db.flush()

    po = PurchaseOrder(
        po_no=f"M06-T001-PO-{suffix}", supplier_id=supplier.id,
        order_date=date(2026, 10, 29), expected_delivery_date=date(2026, 10, 30),
        currency="KES", status=POStatus.ORDERED,
    )
    db.add(po)
    await db.flush()
    po_line = POLine(
        po_id=po.id, line_no=1, material_id=material.id,
        ordered_quantity=Decimal("10"), unit="KG",
        unit_price=Decimal("25"), tax_rate=Decimal("0.16"),
    )
    grn = GoodsReceipt(
        grn_no=f"M06-T001-GRN-{suffix}", po_id=po.id,
        received_date=date(2026, 10, 29), warehouse_id=warehouse.id,
        status=GRNStatus.DRAFT,
    )
    db.add_all([po_line, grn])
    await db.flush()
    grn_line = GRNLine(
        grn_id=grn.id, po_line_id=po_line.id, material_id=material.id,
        received_quantity=Decimal(accepted), accepted_quantity=Decimal(accepted),
        rejected_quantity=Decimal("0"), unit="KG",
    )
    db.add(grn_line)
    await db.flush()

    quantity = Decimal(accepted)
    invoice = PurchaseInvoice(
        invoice_no=f"M06-T001-INV-{suffix}", supplier_id=supplier.id,
        po_id=po.id, invoice_date=date(2026, 10, 29), due_date=date(2026, 11, 28),
        currency="KES", subtotal=quantity * Decimal("25"),
        tax_amount=quantity * Decimal("25") * Decimal("0.16"),
        total_amount=quantity * Decimal("25") * Decimal("1.16"),
    )
    db.add(invoice)
    await db.flush()
    invoice_line = PurchaseInvoiceLine(
        invoice_id=invoice.id, material_id=material.id,
        description=f"Synthetic line {suffix}", quantity=quantity, unit="KG",
        unit_price=Decimal("25"), tax_rate=Decimal("0.16"),
        line_total=quantity * Decimal("25") * Decimal("1.16"),
    )
    db.add(invoice_line)
    await db.flush()
    return user, supplier, other_supplier, material, warehouse, po, po_line, grn, grn_line, invoice, invoice_line


@pytest.mark.asyncio
async def test_draft_grn_cannot_make_invoice_payable_and_posted_chain_matches_once():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, material, warehouse, po, po_line, grn, grn_line, invoice, _ = await _seed_chain(db, suffix)
        ids = (material.id, warehouse.id, po.id, po_line.id, grn.id, grn_line.id, invoice.id, user.id, grn.grn_no)
        await db.commit()

        before_stock = await db.scalar(select(func.count(Stock.id)).where(
            Stock.material_id == ids[0], Stock.warehouse_id == ids[1],
        ))
        assert before_stock == 0

        draft_match = await invoice_match_service.run_match(db, ids[6])
        assert draft_match.overall_status == MatchOverallStatus.BLOCKED
        assert draft_match.is_payable is False
        assert "GRN" in (draft_match.payment_hold_reason or "")
        draft_line = draft_match.match_lines[0]
        assert draft_line.match_status == MatchLineStatus.MISSING_GRN
        assert draft_line.total_accepted_qty == Decimal("0")
        assert draft_line.billable_qty == Decimal("0")
        assert draft_line.grn_links == []
        assert await db.scalar(select(func.count(StockMovement.id)).where(
            StockMovement.reference_number == ids[8],
        )) == 0

        await procurement_service.post_grn(db, await db.get(GoodsReceipt, ids[4]), ids[7])
        await db.commit()
        persisted_grn = await db.get(GoodsReceipt, ids[4])
        persisted_po = await db.get(PurchaseOrder, ids[2])
        persisted_po_line = await db.get(POLine, ids[3])
        await db.refresh(persisted_grn)
        await db.refresh(persisted_po)
        await db.refresh(persisted_po_line)
        assert persisted_grn.status == GRNStatus.POSTED
        assert persisted_po.status == POStatus.RECEIVED
        assert persisted_po_line.received_quantity == Decimal("10.000")
        posted_match = await invoice_match_service.run_match(db, ids[6], force_rerun=True)
        assert posted_match.overall_status == MatchOverallStatus.FULLY_MATCHED
        assert posted_match.is_payable is True
        posted_line = posted_match.match_lines[0]
        assert posted_line.po_line_id == ids[3]
        assert posted_line.total_received_qty == Decimal("10.000")
        assert posted_line.total_accepted_qty == Decimal("10.000")
        assert posted_line.prev_invoiced_qty == Decimal("0")
        assert posted_line.billable_qty == Decimal("10.000")
        assert posted_line.invoiced_qty == Decimal("10.000")
        assert len(posted_line.grn_links) == 1
        assert posted_line.grn_links[0].grn_id == ids[4]
        assert posted_line.grn_links[0].grn_line_id == ids[5]
        assert posted_line.grn_links[0].accepted_qty == Decimal("10.000")

        stable_match = await invoice_match_service.run_match(db, ids[6])
        assert stable_match.id == posted_match.id
        assert await db.scalar(select(func.count(InvoiceMatchHeader.id)).where(
            InvoiceMatchHeader.invoice_id == ids[6],
        )) == 1
        assert await db.scalar(select(func.count(InvoiceMatchLine.id)).where(
            InvoiceMatchLine.header_id == posted_match.id,
        )) == 1
        assert await db.scalar(select(func.count(InvoiceMatchGRNLink.id)).where(
            InvoiceMatchGRNLink.match_line_id == posted_line.id,
        )) == 1
        persisted_stock = (await db.execute(select(Stock).where(
            Stock.material_id == ids[0], Stock.warehouse_id == ids[1],
        ))).scalar_one()
        assert persisted_stock.quantity_on_hand == Decimal("10.000")
        assert await db.scalar(select(func.count(StockMovement.id)).where(
            StockMovement.reference_number == ids[8],
        )) == 1


@pytest.mark.asyncio
async def test_cumulative_invoice_over_remaining_accepted_quantity_remains_on_hold():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, supplier, _, material, _, po, _, grn, _, first_invoice, _ = await _seed_chain(db, suffix, accepted="10")
        await db.commit()
        await procurement_service.post_grn(db, await db.get(GoodsReceipt, grn.id), user.id)
        await db.commit()

        first_match = await invoice_match_service.run_match(db, first_invoice.id)
        first_line = first_match.match_lines[0]
        assert first_match.is_payable is True
        assert first_line.total_accepted_qty == Decimal("10.000")
        assert first_line.billable_qty == Decimal("10.000")
        assert first_line.invoiced_qty == Decimal("10.000")

        second_invoice = PurchaseInvoice(
            invoice_no=f"M06-T001-SECOND-{suffix}", supplier_id=supplier.id,
            po_id=po.id, invoice_date=date(2026, 10, 30), due_date=date(2026, 11, 29),
            currency="KES", subtotal=Decimal("125"), tax_amount=Decimal("20"),
            total_amount=Decimal("145"),
        )
        db.add(second_invoice)
        await db.flush()
        db.add(PurchaseInvoiceLine(
            invoice_id=second_invoice.id, material_id=material.id,
            description=f"Synthetic cumulative billing line {suffix}", quantity=Decimal("5"), unit="KG",
            unit_price=Decimal("25"), tax_rate=Decimal("0.16"), line_total=Decimal("145"),
        ))
        await db.commit()

        match = await invoice_match_service.run_match(db, second_invoice.id)
        line = match.match_lines[0]
        assert line.total_accepted_qty == Decimal("10.000")
        assert line.prev_invoiced_qty == Decimal("10.000")
        assert line.billable_qty == Decimal("0.000")
        assert line.invoiced_qty == Decimal("5.000")
        assert line.match_status == MatchLineStatus.OVERBILLED
        assert match.overall_status == MatchOverallStatus.BLOCKED
        assert match.is_payable is False


@pytest.mark.asyncio
async def test_late_match_failure_rolls_back_match_rows_without_reversing_posted_receipt(monkeypatch):
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, material, warehouse, _, _, grn, _, invoice, _ = await _seed_chain(db, suffix)
        await db.commit()
        await procurement_service.post_grn(db, await db.get(GoodsReceipt, grn.id), user.id)
        await db.commit()
        invoice_id = invoice.id
        grn_no = grn.grn_no
        stock_id = (await db.execute(select(Stock.id).where(
            Stock.material_id == material.id, Stock.warehouse_id == warehouse.id,
        ))).scalar_one()

        def fail_after_match_rows(*_args):
            raise RuntimeError("synthetic late failure after match-row writes")

        monkeypatch.setattr(invoice_match_service, "_compute_payment_hold", fail_after_match_rows)
        with pytest.raises(RuntimeError, match="synthetic late failure"):
            await invoice_match_service.run_match(db, invoice_id)
        await db.rollback()

        assert await db.scalar(select(func.count(InvoiceMatchHeader.id)).where(
            InvoiceMatchHeader.invoice_id == invoice_id,
        )) == 0
        invoice_header_ids = select(InvoiceMatchHeader.id).where(InvoiceMatchHeader.invoice_id == invoice_id)
        invoice_line_ids = select(InvoiceMatchLine.id).where(InvoiceMatchLine.header_id.in_(invoice_header_ids))
        assert await db.scalar(select(func.count(InvoiceMatchLine.id)).where(
            InvoiceMatchLine.header_id.in_(invoice_header_ids),
        )) == 0
        assert await db.scalar(select(func.count(InvoiceMatchGRNLink.id)).where(
            InvoiceMatchGRNLink.match_line_id.in_(invoice_line_ids),
        )) == 0
        assert await db.scalar(select(func.count(StockMovement.id)).where(
            StockMovement.reference_number == grn_no,
        )) == 1
        persisted_stock = await db.get(Stock, stock_id)
        assert persisted_stock.quantity_on_hand == Decimal("10.000")


@pytest.mark.asyncio
async def test_invoice_from_different_supplier_cannot_match_po():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, other_supplier, _, _, po, _, grn, _, invoice, _ = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice.supplier_id = other_supplier.id
        ids = (invoice.id, po.id)
        await db.commit()

        with pytest.raises(ValueError, match="Invoice supplier does not match linked purchase order supplier"):
            await invoice_match_service.run_match(db, ids[0])
        assert await db.scalar(select(func.count(InvoiceMatchHeader.id)).where(
            InvoiceMatchHeader.invoice_id == ids[0],
        )) == 0
