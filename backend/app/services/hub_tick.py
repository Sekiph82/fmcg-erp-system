"""Background jobs added in M45/M46, run from the CRM automation loop (every 15 s). Each job uses its own session and
is isolated: one failing job never stops the others. Jobs are idempotent and cheap when there is nothing to do.

Daily steps keep a per-step ledger (ci_settings key "daily_ledger": {step: last successful day}), claimed under an
advisory lock, so one failing step is retried on the next tick without skipping the others, and two workers never
run the same step twice (M46.S01.T008).
"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


async def _step_customer_intel(db) -> None:
    from app.services import customer_intel_service as ci
    await ci.run_daily(db)


async def _step_source_retention(db) -> None:
    from app.services.customer_data_service import purge_expired
    await purge_expired(db)


async def _step_sensitive_retention(db) -> None:
    from app.services.sensitive_service import apply_retention
    await apply_retention(db)


async def _step_dq_snapshot(db) -> None:
    from app.services.data_sync_service import snapshot
    await snapshot(db)


async def _step_renewals(db) -> None:
    from app.services import cpq_service
    await cpq_service.renewals_tick(db)


async def _step_billing(db) -> None:
    from app.services import cpq_service
    await cpq_service.billing_tick(db)


async def _step_smart_properties(db) -> None:     # M47.S01.T010 rule-filled contact properties
    from app.services import crm_contact_service
    await crm_contact_service.recompute_smart_properties(db)


async def _step_expire_payment_attempts(db) -> None:
    from app.services import payment_link_service
    await payment_link_service.expire_stale(db)


DAILY = {"customer_intel": _step_customer_intel, "source_retention": _step_source_retention,
         "sensitive_retention": _step_sensitive_retention, "dq_snapshot": _step_dq_snapshot,
         "renewals": _step_renewals, "billing": _step_billing, "smart_properties": _step_smart_properties}


async def run_daily_steps(db, today: date | None = None) -> dict:
    """Run each daily step at most once per day; a failure is logged and retried later. Returns {step: status}."""
    from sqlalchemy import text
    from app.models.customer_intel import CISetting
    today = today or date.today()
    out = {}
    for name, fn in DAILY.items():
        got = (await db.execute(text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"), {"k": f"daily:{name}"})).scalar()
        if not got:
            out[name] = "busy"
            await db.rollback()
            continue
        row = await db.get(CISetting, "daily_ledger")
        ledger = dict(row.value) if row else {}
        if ledger.get(name) == today.isoformat():
            out[name] = "done"
            await db.rollback()
            continue
        try:
            await fn(db)
            row = await db.get(CISetting, "daily_ledger")
            ledger = dict(row.value) if row else {}
            ledger[name] = today.isoformat()
            if row is None:
                db.add(CISetting(key="daily_ledger", value=ledger, updated_by="scheduler"))
            else:
                row.value = ledger
            await db.commit()
            out[name] = "ran"
        except Exception:
            await db.rollback()
            logger.exception("daily step %s failed; it is retried on the next tick", name)
            out[name] = "failed"
    return out


async def _daily(db) -> None:
    await run_daily_steps(db)


async def _payment_attempts(db) -> None:
    await _step_expire_payment_attempts(db)
    await db.commit()


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


async def _data_sync(db) -> None:
    from app.services import data_sync_service
    await data_sync_service.tick(db)


JOBS = [_daily, _payment_attempts, _agents, _warehouse_exports, _sla, _data_sync]


async def tick() -> None:
    from app.db.session import AsyncSessionLocal
    for job in JOBS:
        try:
            async with AsyncSessionLocal() as db:
                await job(db)
        except Exception:
            logger.exception("hub job %s failed", job.__name__)
