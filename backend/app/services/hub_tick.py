"""Background jobs added in M45, run from the CRM automation loop (every 15 s). Each job uses its own session and
is isolated: one failing job never stops the others. Jobs are idempotent and cheap when there is nothing to do."""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)
_last_daily: date | None = None


async def _daily_customer_intel(db) -> None:
    global _last_daily
    from sqlalchemy import select
    from app.models.customer_intel import CIHealthSnapshot
    from app.services import customer_intel_service as ci
    today = date.today()
    if _last_daily == today:
        return
    if (await db.execute(select(CIHealthSnapshot.id).where(CIHealthSnapshot.day == today).limit(1))).first() is None:
        await ci.run_daily(db)
        await db.commit()
    _last_daily = today


JOBS = [_daily_customer_intel]


async def tick() -> None:
    from app.db.session import AsyncSessionLocal
    for job in JOBS:
        try:
            async with AsyncSessionLocal() as db:
                await job(db)
        except Exception:
            logger.exception("M45 job %s failed", job.__name__)
