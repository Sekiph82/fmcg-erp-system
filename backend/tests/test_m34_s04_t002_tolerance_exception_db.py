"""PostgreSQL approval-policy and tolerance configuration regressions for M34.S04.T002."""
from __future__ import annotations

import importlib.util
import os
import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.invoice_match import (
    InvoiceMatchHeader,
    InvoiceMatchReview,
    InvoiceMatchTolerance,
    MatchLineStatus,
    MatchOverallStatus,
)
from app.models.finance import PurchaseInvoice, PurchaseInvoiceLine
from app.models.procurement import GRNStatus
from app.schemas.invoice_match import ReviewCreate, ToleranceRuleUpdate
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
    os.environ.get("M34_S04_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the M34.S04.T002 task-owned disposable PostgreSQL database",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m34_s04_t002_[a-f0-9]{24}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M34_S04_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback "
            "M34.S04.T002 disposable database without a password."
        )
    return expected


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_configured_tolerance_role_controls_exception_approval():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, _, _, _, _, grn, _, invoice, invoice_line = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice_line.unit_price = Decimal("30")
        invoice_line.line_total = Decimal("348")
        invoice.subtotal = Decimal("300")
        invoice.tax_amount = Decimal("48")
        invoice.total_amount = Decimal("348")
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic role-gated tolerance {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("1"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            approval_role_required="finance_manager",
            priority=1,
        ))
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)
        assert match.overall_status == MatchOverallStatus.PRICE_MISMATCH
        assert match.is_payable is False
        assert match.match_lines[0].match_status == MatchLineStatus.PRICE_MISMATCH
        header_id, run_at = match.id, match.run_at

    async with AsyncSessionLocal() as unauthorized_db:
        with pytest.raises(invoice_match_service.InvoiceMatchApprovalRoleError):
            await invoice_match_service.submit_review(
                unauthorized_db,
                header_id,
                ReviewCreate(
                    action="APPROVED_EXCEPTION",
                    reviewer_name="synthetic finance staff",
                    expected_run_at=run_at,
                    justification="Synthetic variance approval record",
                ),
                actor_role_names={"finance_staff"},
            )

    async with AsyncSessionLocal() as check_db:
        unchanged = await check_db.get(InvoiceMatchHeader, header_id)
        assert unchanged.overall_status == MatchOverallStatus.PRICE_MISMATCH
        assert unchanged.is_payable is False
        assert await check_db.scalar(
            select(InvoiceMatchReview.id).where(InvoiceMatchReview.header_id == header_id)
        ) is None

    async with AsyncSessionLocal() as authorized_db:
        approved = await invoice_match_service.submit_review(
            authorized_db,
            header_id,
            ReviewCreate(
                action="APPROVED_EXCEPTION",
                reviewer_name="synthetic finance manager",
                expected_run_at=run_at,
                justification="Synthetic evidence reviewed for the configured exception",
            ),
            actor_role_names={"FINANCE_MANAGER"},
        )
        assert approved.overall_status == MatchOverallStatus.APPROVED_EXCEPTION
        assert approved.is_payable is True
        assert approved.approved_by == "synthetic finance manager"
        assert approved.match_lines[0].match_status == MatchLineStatus.APPROVED_EXCEPTION


@pytest.mark.asyncio
async def test_auto_approval_flag_holds_in_tolerance_variance_until_role_approval():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, _, _, _, _, grn, _, invoice, invoice_line = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice_line.unit_price = Decimal("25.25")
        invoice_line.line_total = Decimal("292.9")
        invoice.subtotal = Decimal("252.5")
        invoice.tax_amount = Decimal("40.4")
        invoice.total_amount = Decimal("292.9")
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic manual tolerance {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("1"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            auto_approve_within_tolerance=False,
            approval_role_required="finance_manager",
            priority=1,
        ))
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)
        assert match.overall_status == MatchOverallStatus.MATCHED_WITHIN_TOLERANCE
        assert match.review_required is True
        assert match.is_payable is False
        assert match.match_lines[0].action_required is True
        header_id, run_at = match.id, match.run_at

    async with AsyncSessionLocal() as db:
        approved = await invoice_match_service.submit_review(
            db,
            header_id,
            ReviewCreate(
                action="APPROVED_EXCEPTION",
                reviewer_name="synthetic finance manager",
                expected_run_at=run_at,
                justification="Synthetic approval of configured manual tolerance",
            ),
            actor_role_names={"finance_manager"},
        )
        assert approved.overall_status == MatchOverallStatus.APPROVED_EXCEPTION
        assert approved.is_payable is True


@pytest.mark.asyncio
async def test_explicit_policy_can_allow_payment_beyond_tolerance_without_overriding_hard_blocks():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, _, _, _, _, grn, _, invoice, invoice_line = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice_line.unit_price = Decimal("30")
        invoice_line.line_total = Decimal("348")
        invoice.subtotal = Decimal("300")
        invoice.tax_amount = Decimal("48")
        invoice.total_amount = Decimal("348")
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic nonblocking variance policy {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("1"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            block_payment_beyond_tolerance=False,
            priority=1,
        ))
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)

    assert match.overall_status == MatchOverallStatus.PRICE_MISMATCH
    assert match.review_required is True
    assert match.is_payable is True
    assert match.payment_hold_reason is None


@pytest.mark.asyncio
async def test_absolute_quantity_tolerance_is_enforced_alongside_percentage():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, _, _, _, _, grn, _, invoice, invoice_line = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        invoice_line.quantity = Decimal("10.2")
        invoice_line.line_total = Decimal("295.8")
        invoice.subtotal = Decimal("255")
        invoice.tax_amount = Decimal("40.8")
        invoice.total_amount = Decimal("295.8")
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic combined quantity tolerance {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("5"),
            quantity_tolerance_abs=Decimal("0.1"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            priority=1,
        ))
        await db.commit()
        match = await invoice_match_service.run_match(db, invoice.id)

    assert match.overall_status == MatchOverallStatus.QUANTITY_MISMATCH
    assert match.is_payable is False
    assert match.match_lines[0].qty_variance_pct == Decimal("2.000")
    assert match.match_lines[0].match_status == MatchLineStatus.QUANTITY_MISMATCH


@pytest.mark.asyncio
async def test_subsequent_invoice_variance_uses_remaining_billable_quantity():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, _, material, _, po, po_line, grn, _, first_invoice, first_line = await _seed_chain(
            db,
            suffix,
            accepted="10",
        )
        grn.status = GRNStatus.POSTED
        first_line.quantity = Decimal("9")
        first_line.line_total = Decimal("261")
        first_invoice.subtotal = Decimal("225")
        first_invoice.tax_amount = Decimal("36")
        first_invoice.total_amount = Decimal("261")
        db.add(InvoiceMatchTolerance(
            rule_name=f"Synthetic partial-billing tolerance {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("15"),
            price_tolerance_pct=Decimal("2"),
            tax_tolerance_pct=Decimal("0"),
            priority=1,
        ))
        await db.commit()

        first_match = await invoice_match_service.run_match(db, first_invoice.id)
        assert first_match.overall_status == MatchOverallStatus.MATCHED_WITHIN_TOLERANCE
        assert first_match.is_payable is True

        second_invoice = PurchaseInvoice(
            invoice_no=f"M34-T002-SECOND-{suffix}",
            supplier_id=supplier.id,
            po_id=po.id,
            invoice_date=first_invoice.invoice_date,
            due_date=first_invoice.due_date,
            currency=first_invoice.currency,
            subtotal=Decimal("25"),
            tax_amount=Decimal("4"),
            total_amount=Decimal("29"),
        )
        db.add(second_invoice)
        await db.flush()
        db.add(PurchaseInvoiceLine(
            invoice_id=second_invoice.id,
            material_id=material.id,
            description=f"Synthetic subsequent invoice {suffix}",
            quantity=Decimal("1"),
            unit=po_line.unit,
            unit_price=Decimal("25"),
            tax_rate=Decimal("0.16"),
            line_total=Decimal("29"),
        ))
        await db.commit()

        second_match = await invoice_match_service.run_match(db, second_invoice.id)

    assert second_match.overall_status == MatchOverallStatus.FULLY_MATCHED
    assert second_match.is_payable is True
    assert second_match.match_lines[0].total_accepted_qty == Decimal("10.000")
    assert second_match.match_lines[0].prev_invoiced_qty == Decimal("9.000")
    assert second_match.match_lines[0].billable_qty == Decimal("1.000")
    assert second_match.match_lines[0].qty_variance == Decimal("0.000")
    assert second_match.match_lines[0].qty_variance_pct == Decimal("0.000")
    assert second_match.match_lines[0].match_status == MatchLineStatus.FULLY_MATCHED


@pytest.mark.asyncio
async def test_tolerance_update_can_clear_optional_role_and_absolute_thresholds():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, supplier, *_ = await _seed_chain(db, suffix)
        rule = InvoiceMatchTolerance(
            rule_name=f"Synthetic clearable tolerance {suffix}",
            supplier_id=supplier.id,
            quantity_tolerance_pct=Decimal("1"),
            quantity_tolerance_abs=Decimal("2"),
            price_tolerance_pct=Decimal("2"),
            price_tolerance_abs=Decimal("1.5"),
            tax_tolerance_pct=Decimal("0"),
            approval_role_required="finance_manager",
        )
        db.add(rule)
        await db.commit()
        rule_id = rule.id

        updated = await invoice_match_service.update_tolerance_rule(
            db,
            rule_id,
            ToleranceRuleUpdate(
                approval_role_required=None,
                quantity_tolerance_abs=None,
                price_tolerance_abs=None,
            ),
        )
        assert updated is not None
        assert updated.approval_role_required is None
        assert updated.quantity_tolerance_abs is None
        assert updated.price_tolerance_abs is None


@pytest.mark.asyncio
async def test_overbilling_cannot_be_released_by_exception_approval():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, _, _, grn, _, invoice, invoice_line = await _seed_chain(db, suffix, accepted="5")
        grn.status = GRNStatus.POSTED
        invoice_line.quantity = Decimal("6")
        invoice_line.line_total = Decimal("174")
        invoice.subtotal = Decimal("150")
        invoice.tax_amount = Decimal("24")
        invoice.total_amount = Decimal("174")
        await db.commit()

        match = await invoice_match_service.run_match(db, invoice.id)
        assert match.overall_status == MatchOverallStatus.BLOCKED
        assert match.is_payable is False
        assert match.match_lines[0].match_status == MatchLineStatus.OVERBILLED
        header_id, run_at = match.id, match.run_at

    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="overbilled lines cannot be exception-approved"):
            await invoice_match_service.submit_review(
                db,
                header_id,
                ReviewCreate(
                    action="APPROVED_EXCEPTION",
                    reviewer_name="synthetic finance manager",
                    expected_run_at=run_at,
                    justification="Synthetic attempt must remain blocked",
                ),
                actor_role_names={"finance_manager"},
            )

    async with AsyncSessionLocal() as db:
        unchanged = await db.get(InvoiceMatchHeader, header_id)
        assert unchanged.overall_status == MatchOverallStatus.BLOCKED
        assert unchanged.is_payable is False
        assert await db.scalar(
            select(InvoiceMatchReview.id).where(InvoiceMatchReview.header_id == header_id)
        ) is None
