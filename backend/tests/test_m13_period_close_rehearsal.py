"""M13.S03.T004 finance close rehearsal on an explicitly owned PostgreSQL database."""
from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.engine import URL

from app.api.v1.endpoints.finance import router as finance_router
from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.models.finance import (
    AccountType,
    AccountingPeriod,
    AccountingPeriodCloseCheck,
    ChartOfAccount,
    JournalEntry,
    PeriodStatus,
)
from app.models.company import Company
from app.models.user import User
from app.services.finance_service import trial_balance


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m13_s03_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M13_S03_T004_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M13_S03_T004_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M13_S03_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M13.S03.T004 database.")


def test_m13_rehearsal_guard_requires_exact_unique_loopback_database():
    name = "fmcg_m13_s03_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="test", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m13_s03_t004_0123456789abcdef0124")
    assert not _is_task_owned_database(safe, "fmcg_m13_s03_t004_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.com", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user_id, *permission_codes: str, is_superuser: bool = False):
    return SimpleNamespace(
        id=user_id,
        is_superuser=is_superuser,
        roles=[SimpleNamespace(
            is_active=True,
            permissions=[SimpleNamespace(code=code, is_active=True) for code in permission_codes],
        )],
    )


def _app(actor):
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(finance_router, prefix="/api/v1/finance")

    async def override_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: actor
    return app


async def _wait_for_lock_waiters(minimum: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        async with AsyncSessionLocal() as db:
            count = await db.scalar(text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND backend_type = 'client backend' "
                "AND wait_event_type = 'Lock'"
            ))
        if count >= minimum:
            return
        await asyncio.sleep(0.025)
    pytest.fail(f"Expected at least {minimum} PostgreSQL lock waiters within {timeout}s")


async def _create_user():
    user_id = uuid4()
    async with AsyncSessionLocal() as db:
        db.add(User(
            id=user_id,
            email=f"m13-close-{user_id.hex}@example.invalid",
            username=f"m13-close-{user_id.hex}",
            full_name="Synthetic M13 Finance User",
            hashed_password="not-a-usable-password-hash",
            is_active=True,
            is_superuser=False,
        ))
        await db.commit()
    return user_id


async def _create_company(suffix: str, actor_id):
    company_id = uuid4()
    async with AsyncSessionLocal() as db:
        db.add(Company(
            id=company_id,
            name="Synthetic M13 Rehearsal Company",
            short_code=f"M13{suffix[:10].upper()}",
            country="Kenya",
            base_currency="KES",
            created_by_id=actor_id,
        ))
        await db.commit()
    return company_id


async def _create_period(client: AsyncClient, suffix: str):
    year = 3000 + int(suffix[:6], 16) % 6000
    response = await client.post("/api/v1/finance/accounting/periods/", json={
        "period_ym": f"{year}-01",
        "period_start": f"{year}-01-01",
        "period_end": f"{year}-01-31",
        "notes": "Synthetic staging rehearsal; not live financial data.",
    })
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_close_reconciliation_blocks_open_checks_and_audits_terminal_transitions():
    _require_task_owned_database()
    user_id = await _create_user()
    actor = _actor(user_id, "finance.configure", "finance.approve")
    app = _app(actor)
    suffix = uuid4().hex
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m13-close.test") as client:
            period = await _create_period(client, suffix)
            check = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"BANK_RECON_{suffix[:8]}",
                "label": "Synthetic bank reconciliation",
            })
            assert check.status_code == 201, check.text
            check_data = check.json()
            assert check_data["status"] == "PENDING"
            assert check_data["checked_by_id"] is None

            blocked = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert blocked.status_code == 409
            async with AsyncSessionLocal() as db:
                stored = await db.get(AccountingPeriod, period["id"])
                assert stored.status == PeriodStatus.OPEN
                assert stored.closed_by_id is None and stored.closed_at is None

            failed_without_reason = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_data['id']}",
                json={"status": "FAILED"},
            )
            assert failed_without_reason.status_code == 422
            failed = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_data['id']}",
                json={"status": "FAILED", "result_summary": "Synthetic unmatched statement line."},
            )
            assert failed.status_code == 200, failed.text
            assert failed.json()["checked_by_id"] == str(user_id)
            assert failed.json()["checked_at"]
            blocked_failed = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert blocked_failed.status_code == 409
            assert check_data["check_code"] in blocked_failed.json()["detail"]["blocking_check_codes"]

            passed = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_data['id']}",
                json={"status": "PASSED", "result_summary": "Synthetic statement reconciled to ledger."},
            )
            assert passed.status_code == 200, passed.text
            waived_without_reason = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"SYNTHETIC_WAIVER_{suffix[:8]}",
                "label": "Synthetic permitted exception",
                "status": "WAIVED",
            })
            assert waived_without_reason.status_code == 422
            waived = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"SYNTHETIC_WAIVER_{suffix[:8]}",
                "label": "Synthetic permitted exception",
                "status": "WAIVED",
                "result_summary": "Synthetic exception documented for rehearsal only.",
            })
            assert waived.status_code == 201, waived.text
            assert waived.json()["checked_by_id"] == str(user_id)
            assert waived.json()["checked_at"]

            closed = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert closed.status_code == 200, closed.text
            assert closed.json()["status"] == "CLOSED"
            assert closed.json()["closed_by_id"] == str(user_id)
            original_closed_at = closed.json()["closed_at"]

            repeated_close = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert repeated_close.status_code == 409
            async with AsyncSessionLocal() as db:
                stored = await db.get(AccountingPeriod, period["id"])
                assert stored.status == PeriodStatus.CLOSED
                assert str(stored.closed_by_id) == str(user_id)
                assert stored.closed_at.isoformat().replace("+00:00", "Z") == original_closed_at

            late_check_edit = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_data['id']}",
                json={"status": "PENDING"},
            )
            assert late_check_edit.status_code == 409
            late_check_create = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"LOCKED_PERIOD_{suffix[:8]}",
                "label": "Synthetic prohibited post-lock check",
            })
            assert late_check_create.status_code == 409
            locked = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/lock")
            assert locked.status_code == 200, locked.text
            assert locked.json()["status"] == "LOCKED"
            assert locked.json()["closed_by_id"] == str(user_id)
            assert locked.json()["closed_at"] == original_closed_at
            assert locked.json()["locked_by_id"] == str(user_id)
            assert locked.json()["locked_at"]
            original_locked_at = locked.json()["locked_at"]
            duplicate_lock = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/lock")
            assert duplicate_lock.status_code == 409
            async with AsyncSessionLocal() as db:
                stored = await db.get(AccountingPeriod, period["id"])
                assert stored.status == PeriodStatus.LOCKED
                assert str(stored.closed_by_id) == str(user_id)
                assert stored.closed_at.isoformat().replace("+00:00", "Z") == original_closed_at
                assert str(stored.locked_by_id) == str(user_id)
                assert stored.locked_at.isoformat().replace("+00:00", "Z") == original_locked_at
            locked_check_edit = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_data['id']}",
                json={"status": "PENDING"},
            )
            assert locked_check_edit.status_code == 409
            locked_check_create = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"LOCKED_PERIOD_{suffix[:8]}",
                "label": "Synthetic prohibited locked-period check",
            })
            assert locked_check_create.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_period_close_and_check_mutations_enforce_existing_permissions_and_states():
    _require_task_owned_database()
    user_id = await _create_user()
    actor = _actor(user_id, "finance.configure")
    app = _app(actor)
    suffix = uuid4().hex
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m13-close.test") as client:
            period = await _create_period(client, suffix)
            denied_close = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert denied_close.status_code == 403
            created = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"], "check_code": f"CHECK_{suffix[:8]}", "label": "Synthetic close check",
            })
            assert created.status_code == 201, created.text
            actor.roles[0].permissions = [SimpleNamespace(code="finance.approve", is_active=True)]
            denied_update = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{created.json()['id']}",
                json={"status": "PASSED"},
            )
            assert denied_update.status_code == 403
            lock_open = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/lock")
            assert lock_open.status_code == 409
            async with AsyncSessionLocal() as db:
                stored = await db.get(AccountingPeriod, period["id"])
                assert stored.status == PeriodStatus.OPEN
                assert stored.locked_by_id is None and stored.locked_at is None
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_closed_period_rejects_journal_post_without_changing_balanced_history():
    _require_task_owned_database()
    user_id = await _create_user()
    actor = _actor(
        user_id,
        "finance.configure",
        "finance.approve",
        "finance.create",
        "finance.post",
        is_superuser=True,
    )
    app = _app(actor)
    suffix = uuid4().hex
    company_id = await _create_company(suffix, user_id)
    account_ids = (uuid4(), uuid4())
    try:
        async with AsyncSessionLocal() as db:
            db.add_all([
                ChartOfAccount(id=account_ids[0], code=f"M13A{suffix[:6]}", name="Synthetic cash", account_type=AccountType.ASSET),
                ChartOfAccount(id=account_ids[1], code=f"M13E{suffix[:6]}", name="Synthetic expense", account_type=AccountType.EXPENSE),
            ])
            await db.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m13-close.test") as client:
            period = await _create_period(client, suffix)
            year = int(period["period_ym"][:4])
            check = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"], "check_code": f"TRIAL_BALANCE_{suffix[:8]}",
                "label": "Synthetic ledger/trial-balance reconciliation",
            })
            assert check.status_code == 201, check.text
            passed = await client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check.json()['id']}",
                json={"status": "PASSED", "result_summary": "Synthetic balanced trial balance: KES 100.00 debit = KES 100.00 credit."},
            )
            assert passed.status_code == 200, passed.text
            journal = await client.post("/api/v1/finance/journal/", json={
                "entry_no": f"M13-{suffix[:12]}",
                "entry_date": f"{year}-01-15",
                "description": "Synthetic period-close rehearsal journal",
                "company_id": str(company_id),
                "source_module": "finance",
                "source_event": "m13_s03_t004_rehearsal",
                "lines": [
                    {"account_id": str(account_ids[0]), "description": "Synthetic debit", "debit": "100.00", "credit": "0", "currency": "KES"},
                    {"account_id": str(account_ids[1]), "description": "Synthetic credit", "debit": "0", "credit": "100.00", "currency": "KES"},
                ],
            })
            assert journal.status_code == 201, journal.text
            posted = await client.post(f"/api/v1/finance/journal/{journal.json()['id']}/post")
            assert posted.status_code == 200, posted.text
            async with AsyncSessionLocal() as db:
                rows = await trial_balance(db, from_date=date(year, 1, 1), to_date=date(year, 1, 31))
                assert sum((row.total_debit for row in rows), start=0) == sum((row.total_credit for row in rows), start=0)
                assert sum((row.total_debit for row in rows), start=0) == 100

            closed = await client.post(f"/api/v1/finance/accounting/periods/{period['id']}/close")
            assert closed.status_code == 200, closed.text
            later_journal = await client.post("/api/v1/finance/journal/", json={
                "entry_no": f"M13L-{suffix[:12]}",
                "entry_date": f"{year}-01-16",
                "description": "Synthetic late period journal",
                "company_id": str(company_id),
                "source_module": "finance",
                "source_event": "m13_s03_t004_rehearsal",
                "lines": [
                    {"account_id": str(account_ids[0]), "description": "Synthetic debit", "debit": "10.00", "credit": "0", "currency": "KES"},
                    {"account_id": str(account_ids[1]), "description": "Synthetic credit", "debit": "0", "credit": "10.00", "currency": "KES"},
                ],
            })
            assert later_journal.status_code == 201, later_journal.text
            rejected = await client.post(f"/api/v1/finance/journal/{later_journal.json()['id']}/post")
            assert rejected.status_code == 422
            async with AsyncSessionLocal() as db:
                late_entry = await db.get(JournalEntry, later_journal.json()["id"])
                assert late_entry.is_posted is False
                assert late_entry.posted_at is None
                assert late_entry.company_id == company_id
                rows_after = await trial_balance(db, from_date=date(year, 1, 1), to_date=date(year, 1, 31))
                assert sum((row.total_debit for row in rows_after), start=0) == 100
                assert sum((row.total_credit for row in rows_after), start=0) == 100
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_check_update_queued_before_close_is_serialized_by_period_lock():
    _require_task_owned_database()
    user_id = await _create_user()
    actor = _actor(user_id, "finance.configure", "finance.approve")
    app = _app(actor)
    suffix = uuid4().hex
    lock_holder = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m13-close.test") as client:
            period = await _create_period(client, suffix)
            check = await client.post("/api/v1/finance/accounting/period-close-checks/", json={
                "period_id": period["id"],
                "check_code": f"RACE_{suffix[:8]}",
                "label": "Synthetic serialized close check",
            })
            assert check.status_code == 201, check.text
            check_id = check.json()["id"]

            lock_holder = AsyncSessionLocal()
            await lock_holder.begin()
            await lock_holder.execute(
                select(AccountingPeriod).where(AccountingPeriod.id == period["id"]).with_for_update()
            )
            update_task = asyncio.create_task(client.patch(
                f"/api/v1/finance/accounting/period-close-checks/{check_id}",
                json={"status": "FAILED", "result_summary": "Synthetic race-order failure."},
            ))
            await _wait_for_lock_waiters(1)
            close_task = asyncio.create_task(client.post(
                f"/api/v1/finance/accounting/periods/{period['id']}/close"
            ))
            await _wait_for_lock_waiters(2)

            await lock_holder.commit()
            update_result, close_result = await asyncio.gather(update_task, close_task)
            assert update_result.status_code == 200, update_result.text
            assert close_result.status_code == 409, close_result.text
            async with AsyncSessionLocal() as db:
                stored_period = await db.get(AccountingPeriod, period["id"])
                stored_check = await db.get(AccountingPeriodCloseCheck, check_id)
                assert stored_period.status == PeriodStatus.OPEN
                assert stored_period.closed_by_id is None and stored_period.closed_at is None
                assert stored_check.status.value == "FAILED"
                assert stored_check.result_summary == "Synthetic race-order failure."
    finally:
        if lock_holder is not None:
            await lock_holder.close()
        app.dependency_overrides.clear()
        await engine.dispose()
