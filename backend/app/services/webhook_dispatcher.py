"""Application-lifespan worker for pending webhook deliveries."""
from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.webhook_service import process_pending_deliveries, process_retry_deliveries

logger = logging.getLogger(__name__)


async def _process_cycle(
    session_factory: Callable[[], AsyncSession], batch_size: int
) -> tuple[int, int]:
    """Use short-lived sessions for pending and due retry batches."""
    async with session_factory() as db:
        pending_count = await process_pending_deliveries(db, limit=batch_size)

    async with session_factory() as db:
        retry_count = await process_retry_deliveries(db, limit=batch_size)

    return pending_count, retry_count


async def run_webhook_dispatcher(
    *,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    interval_seconds: float | None = None,
    batch_size: int | None = None,
) -> None:
    """Continuously dispatch events until the application cancels this task.

    The API runs multiple ASGI workers. Each worker may poll, while the
    service's PostgreSQL ``FOR UPDATE SKIP LOCKED`` claims ensure a delivery
    attempt is processed by at most one worker at a time. Transient failures
    are logged and retried on the next poll; cancellation is allowed through
    so the app lifespan can shut down promptly.
    """
    interval = (
        settings.WEBHOOK_DISPATCH_INTERVAL_SECONDS
        if interval_seconds is None
        else interval_seconds
    )
    limit = (
        settings.WEBHOOK_DISPATCH_BATCH_SIZE if batch_size is None else batch_size
    )
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("interval_seconds must be finite and positive")
    if limit < 1:
        raise ValueError("batch_size must be at least 1")

    logger.info(
        "Webhook dispatcher started (interval=%ss, batch_size=%s)", interval, limit
    )
    while True:
        try:
            pending_count, retry_count = await _process_cycle(session_factory, limit)
            if pending_count or retry_count:
                logger.info(
                    "Webhook dispatcher processed pending=%s due_retries=%s",
                    pending_count,
                    retry_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Webhook dispatcher cycle failed; it will retry")

        await asyncio.sleep(interval)
