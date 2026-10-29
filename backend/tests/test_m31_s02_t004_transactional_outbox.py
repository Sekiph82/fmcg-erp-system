from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

from app.models.webhook import EventLog
from app.services.webhook_service import stage_event


def test_stage_event_flushes_outbox_rows_without_committing_callers_transaction():
    async def run():
        definition_result = Mock()
        definition_result.scalar_one_or_none.return_value = None
        subscriptions_result = Mock()
        subscriptions_result.scalars.return_value.all.return_value = []
        db = Mock()
        db.execute = AsyncMock(side_effect=[definition_result, subscriptions_result])
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.add = Mock()

        event = await stage_event(db, "invoice.posted", {"status": "posted"})

        assert isinstance(event, EventLog)
        db.add.assert_called_once_with(event)
        assert db.flush.await_count == 2
        db.commit.assert_not_awaited()

    asyncio.run(run())
