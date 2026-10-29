"""M25.S03.T003 synthetic PostgreSQL reconciliation and audit tests."""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.models.finance import AccountingPostingBatch, JournalEntry, OperationalPostingEvent
from app.models.landed_cost import (
    LandedCostActualVariancePosting,
    LandedCostAllocationLine,
    LandedCostGRNLink,
    LandedCostLineActual,
)
from app.models.procurement import GRNStatus, GoodsReceipt
from app.services import landed_cost_service as service
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_m25_s03_t002_landed_cost_variance_posting import (
    _actor,
    _prepare_posted_landed_cost,
    _record_actual,
)


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m25_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M25_S03_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M25_S03_T003_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M25_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration reads/writes: DATABASE_URL must match the exact loopback M25.S03.T003 database.")


async def _link_source_grn(ids, header_id) -> None:
    async with AsyncSessionLocal() as db:
        db.add(LandedCostGRNLink(header_id=header_id, grn_id=ids["grn"], grn_no="SYNTHETIC-GRN"))
        await db.commit()


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m25_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t003_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def test_rounding_reconciliation_uses_posting_remainder_for_tiny_variances():
    allocations = [
        SimpleNamespace(id=uuid4(), allocated_amount=Decimal("33.3333")),
        SimpleNamespace(id=uuid4(), allocated_amount=Decimal("33.3333")),
        SimpleNamespace(id=uuid4(), allocated_amount=Decimal("33.3334")),
    ]
    shares = service._allocate_reconciliation_variance(allocations, Decimal("0.0001"))
    assert list(shares.values()) == [Decimal("0.0000"), Decimal("0.0000"), Decimal("0.0001")]
    assert {allocation_id for allocation_id, amount in shares.items() if amount} == {allocations[2].id}


@pytest.mark.asyncio(loop_scope="session")
async def test_reconciliation_links_initial_and_variance_postings_without_writes():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("100.0000"), capitalizable=True, partial_stock=True,
    )
    await _link_source_grn(ids, header_id)
    await _record_actual(ids, header_id, line_id, Decimal("120.0000"))
    async with AsyncSessionLocal() as db:
        await service.post_landed_cost_actual_variance(db, header_id, line_id, posted_by_id=ids["user"])
        before = (
            await db.scalar(select(func.count()).select_from(OperationalPostingEvent)),
            await db.scalar(select(func.count()).select_from(AccountingPostingBatch)),
            await db.scalar(select(func.count()).select_from(JournalEntry)),
            await db.scalar(select(func.count()).select_from(LandedCostActualVariancePosting)),
        )
        report = await service.reconcile_landed_cost(db, header_id)
        after = (
            await db.scalar(select(func.count()).select_from(OperationalPostingEvent)),
            await db.scalar(select(func.count()).select_from(AccountingPostingBatch)),
            await db.scalar(select(func.count()).select_from(JournalEntry)),
            await db.scalar(select(func.count()).select_from(LandedCostActualVariancePosting)),
        )
        assert report is not None
        assert report.status == "RECONCILED", [(check.check_id, check.detail) for check in report.checks if check.status == "FAIL"]
        assert all(check.status in {"PASS", "NOT_APPLICABLE"} for check in report.checks)
        assert {entry.entry_type for entry in report.audit_entries} >= {
            "ACTUAL_RECORDED", "LANDED_COST_POST", "LANDED_COST_ACTUAL_VARIANCE_POST", "JOURNAL",
        }
        assert before == after


@pytest.mark.asyncio(loop_scope="session")
async def test_pending_variance_is_reported_without_claiming_reconciled():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("40.0000"), capitalizable=False,
    )
    await _link_source_grn(ids, header_id)
    await _record_actual(ids, header_id, line_id, Decimal("45.0000"))
    async with AsyncSessionLocal() as db:
        report = await service.reconcile_landed_cost(db, header_id)
    assert report is not None
    assert report.status == "PENDING", [(check.check_id, check.detail) for check in report.checks if check.status == "FAIL"]
    assert any(check.status == "PENDING" for check in report.checks)


@pytest.mark.asyncio(loop_scope="session")
async def test_posted_zero_variance_without_posting_link_is_an_exception():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("40.0000"), capitalizable=False,
    )
    await _link_source_grn(ids, header_id)
    await _record_actual(ids, header_id, line_id, Decimal("40.0000"))
    async with AsyncSessionLocal() as db:
        actual = await db.scalar(select(LandedCostLineActual).where(
            LandedCostLineActual.lc_line_id == line_id,
        ))
        actual.variance_status = "POSTED"
        await db.commit()
        report = await service.reconcile_landed_cost(db, header_id)
    assert report is not None
    assert report.status == "EXCEPTIONS"
    assert any(check.status == "FAIL" and check.check_id.startswith("actual:") for check in report.checks)


@pytest.mark.asyncio(loop_scope="session")
async def test_missing_posted_source_link_is_an_exception_and_report_stays_read_only():
    _require_task_owned_database()
    ids, header_id, _, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("25.0000"), capitalizable=False,
    )
    await _link_source_grn(ids, header_id)
    async with AsyncSessionLocal() as db:
        allocation = await db.scalar(select(LandedCostAllocationLine).where(
            LandedCostAllocationLine.header_id == header_id,
        ))
        allocation.journal_entry_id = None
        await db.commit()
        before = await db.scalar(select(func.count()).select_from(OperationalPostingEvent))
        report = await service.reconcile_landed_cost(db, header_id)
        after = await db.scalar(select(func.count()).select_from(OperationalPostingEvent))
        assert report is not None
        assert report.status == "EXCEPTIONS"
        assert any(check.status == "FAIL" and "journal" in check.detail.lower() for check in report.checks)
        assert after == before
        await db.rollback()


@pytest.mark.asyncio(loop_scope="session")
async def test_reassigned_allocation_grn_is_detected_against_its_original_grn_line():
    _require_task_owned_database()
    ids, header_id, _, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("25.0000"), capitalizable=False,
    )
    await _link_source_grn(ids, header_id)
    other_grn_id = uuid4()
    async with AsyncSessionLocal() as db:
        db.add(GoodsReceipt(
            id=other_grn_id, grn_no=f"SYNTHETIC-OTHER-{uuid4().hex[:8]}",
            po_id=ids["po"], company_id=ids["company"], received_date=date(2026, 6, 15),
            warehouse_id=ids["warehouse"], received_by_id=ids["user"], status=GRNStatus.POSTED,
        ))
        await db.flush()
        db.add(LandedCostGRNLink(header_id=header_id, grn_id=other_grn_id, grn_no="SYNTHETIC-OTHER-GRN"))
        allocation = await db.scalar(select(LandedCostAllocationLine).where(
            LandedCostAllocationLine.header_id == header_id,
        ))
        allocation.grn_id = other_grn_id
        await db.commit()
        report = await service.reconcile_landed_cost(db, header_id)
    assert report is not None
    assert report.status == "EXCEPTIONS"
    assert any(check.check_id.endswith(":source") and check.status == "FAIL" for check in report.checks)


@pytest.mark.asyncio(loop_scope="session")
async def test_reconciliation_endpoint_requires_finance_view_permission():
    _require_task_owned_database()
    ids, header_id, _, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("18.0000"), capitalizable=False,
    )
    await _link_source_grn(ids, header_id)
    from fastapi import FastAPI
    from app.api.v1.endpoints.landed_cost import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/landed-cost")

    async def override_db():
        async with AsyncSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(ids["user"], "procurement.view")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.get(f"/api/v1/landed-cost/{header_id}/reconciliation")
        assert denied.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: _actor(ids["user"], "finance.view")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        allowed = await client.get(f"/api/v1/landed-cost/{header_id}/reconciliation")
        assert allowed.status_code == 200, allowed.text
        payload = allowed.json()
        assert payload["status"] == "RECONCILED", [
            (check["check_id"], check["detail"])
            for check in payload["checks"] if check["status"] == "FAIL"
        ]
        assert payload["audit_entries"]
