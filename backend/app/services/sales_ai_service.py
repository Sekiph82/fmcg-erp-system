"""M47.S01.T009 optional sales AI (meeting recaps, quote drafts) inside a monthly budget.

Off unless a budget is set (ci_settings key "sales_ai": {"monthly_budget": <amount>}) AND a real provider is configured.
The estimated cost is reserved atomically before the call, so concurrent requests cannot overspend. Any failure or
missing budget returns None and the caller uses its deterministic rules. Callers validate every AI item against
stored facts (verbatim transcript quotes, known products) before using it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EST_COST = 0.02          # reserved per call (provider-reported usage is not trusted to be present)


async def budget(db: AsyncSession) -> float:
    from app.models.customer_intel import CISetting
    row = await db.get(CISetting, "sales_ai")
    try:
        return float((row.value or {}).get("monthly_budget") or 0) if row else 0.0
    except (TypeError, ValueError):
        return 0.0


async def _reserve(db: AsyncSession, limit: float) -> bool:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    await db.execute(text("INSERT INTO sales_ai_usage (month, spent, calls) VALUES (:m, 0, 0) ON CONFLICT (month) DO NOTHING"), {"m": month})
    got = (await db.execute(text("UPDATE sales_ai_usage SET spent = spent + :e, calls = calls + 1 WHERE month = :m "
                                 "AND spent + :e <= :b RETURNING month"), {"e": EST_COST, "m": month, "b": limit})).first()
    return got is not None


async def structured(db: AsyncSession, prompt: str, system: str, schema: str) -> Optional[Any]:
    limit = await budget(db)
    if limit <= 0:
        return None
    from app.core.ai_safety import build_safe_system_prompt
    from app.services.ai_provider import get_ai_provider
    provider = get_ai_provider()
    if type(provider).__name__ == "MockProvider" or not await _reserve(db, limit):
        return None
    try:
        obj, _ = await provider.generate_structured_output(prompt, system=build_safe_system_prompt(system), schema_hint=schema)
        return obj
    except Exception:                 # provider down / malformed: the reservation stays (it may have been billed)
        return None
