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
        from app.services.customer_data_service import purge_expired   # T002/T003 source retention
        await purge_expired(db)
        from app.services.sensitive_service import apply_retention   # T017 retention hook
        await apply_retention(db)
        await db.commit()
    _last_daily = today


async def _agents(db) -> None:
    from app.services import agent_service
    await agent_service.tick(db)


async def _warehouse_exports(db) -> None:
    from app.services import warehouse_export_service
    await warehouse_export_service.tick(db)


async def _sla(db) -> None:
    from app.services import service_desk_service
    await service_desk_service.tick(db)
    await db.commit()


JOBS = [_daily_customer_intel, _agents, _warehouse_exports, _sla]


async def tick() -> None:
    from app.db.session import AsyncSessionLocal
    for job in JOBS:
        try:
            async with AsyncSessionLocal() as db:
                await job(db)
        except Exception:
            logger.exception("M45 job %s failed", job.__name__)
