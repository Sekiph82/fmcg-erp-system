from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.services import webhook_dispatcher
from app.services import webhook_service


class _SessionContext:
    def __init__(self):
        self.session = object()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc_info):
        return False


@pytest.mark.parametrize("interval", [float("nan"), float("inf"), float("-inf")])
def test_settings_reject_non_finite_dispatch_intervals(interval):
    with pytest.raises(ValueError, match="finite and positive"):
        Settings(WEBHOOK_DISPATCH_INTERVAL_SECONDS=interval)


@pytest.mark.asyncio
@pytest.mark.parametrize("interval", [float("nan"), float("inf"), float("-inf")])
async def test_dispatcher_rejects_non_finite_runtime_intervals(interval):
    with pytest.raises(ValueError, match="finite and positive"):
        await webhook_dispatcher.run_webhook_dispatcher(interval_seconds=interval)


@pytest.mark.asyncio
async def test_dispatch_cycle_uses_fresh_sessions_for_pending_and_retries(monkeypatch):
    sessions = []

    def session_factory():
        context = _SessionContext()
        sessions.append(context)
        return context

    pending = AsyncMock(return_value=2)
    retries = AsyncMock(return_value=3)
    monkeypatch.setattr(webhook_dispatcher, "process_pending_deliveries", pending)
    monkeypatch.setattr(webhook_dispatcher, "process_retry_deliveries", retries)

    result = await webhook_dispatcher._process_cycle(session_factory, batch_size=17)

    assert result == (2, 3)
    assert len(sessions) == 2
    pending.assert_awaited_once_with(sessions[0].session, limit=17)
    retries.assert_awaited_once_with(sessions[1].session, limit=17)


@pytest.mark.asyncio
async def test_pending_and_retry_claims_skip_rows_locked_by_another_worker():
    class _EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class _Database:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _EmptyResult()

        async def commit(self):
            return None

    db = _Database()

    await webhook_service.process_pending_deliveries(db)
    await webhook_service.process_retry_deliveries(db)

    assert len(db.statements) == 2
    for statement in db.statements:
        sql = str(statement.compile(dialect=postgresql.dialect()))
        assert "FOR UPDATE SKIP LOCKED" in sql


@pytest.mark.asyncio
async def test_dispatch_loop_repeats_and_cancellation_stops_promptly(monkeypatch):
    pending = AsyncMock(return_value=1)
    retries = AsyncMock(return_value=0)
    monkeypatch.setattr(webhook_dispatcher, "process_pending_deliveries", pending)
    monkeypatch.setattr(webhook_dispatcher, "process_retry_deliveries", retries)
    sleep_count = 0

    async def stop_after_two_cycles(_delay):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(webhook_dispatcher.asyncio, "sleep", stop_after_two_cycles)

    with pytest.raises(asyncio.CancelledError):
        await webhook_dispatcher.run_webhook_dispatcher(
            session_factory=_SessionContext,
            interval_seconds=0.01,
            batch_size=9,
        )

    assert pending.await_count == 2
    assert retries.await_count == 2


@pytest.mark.asyncio
async def test_dispatch_loop_logs_a_failed_cycle_and_keeps_running(monkeypatch):
    pending = AsyncMock(side_effect=[RuntimeError("temporary database issue"), 0])
    retries = AsyncMock(return_value=0)
    monkeypatch.setattr(webhook_dispatcher, "process_pending_deliveries", pending)
    monkeypatch.setattr(webhook_dispatcher, "process_retry_deliveries", retries)
    sleep_count = 0

    async def stop_after_recovery(_delay):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(webhook_dispatcher.asyncio, "sleep", stop_after_recovery)

    with pytest.raises(asyncio.CancelledError):
        await webhook_dispatcher.run_webhook_dispatcher(
            session_factory=_SessionContext,
            interval_seconds=0.01,
            batch_size=5,
        )

    assert pending.await_count == 2
    retries.assert_awaited_once()


@pytest.mark.asyncio
async def test_application_lifespan_starts_and_cancels_dispatcher(monkeypatch):
    from app import main
    from app.db import seed_finance

    class _StartupSession(_SessionContext):
        pass

    async def no_op_seed(_db):
        return None

    started = asyncio.Event()
    stopped = asyncio.Event()

    async def dispatcher_loop():
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            stopped.set()
            raise

    monkeypatch.setattr(main, "AsyncSessionLocal", _StartupSession)
    monkeypatch.setattr(main, "seed_admin", no_op_seed)
    monkeypatch.setattr(main, "seed_management_users", no_op_seed)
    monkeypatch.setattr(seed_finance, "seed_finance_data", no_op_seed)
    monkeypatch.setattr(main.settings, "SEED_DEMO_DATA", False)
    monkeypatch.setattr(main, "run_webhook_dispatcher", dispatcher_loop)

    async with main.lifespan(SimpleNamespace()):
        await asyncio.wait_for(started.wait(), timeout=1)

    assert stopped.is_set()
