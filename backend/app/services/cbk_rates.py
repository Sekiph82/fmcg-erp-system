"""Daily KES rates from the Central Bank of Kenya, fetched by the system itself (owner 2026-11-20).

CBK posts the day's mean rates on its home page ("Daily KES Exchange Rates ... Posted On: dd-mm-yyyy").
The backend reads that box every few hours and stores USD, GBP and EUR in exchange_rates (source CBK).
A rate finance typed by hand for the same day is never overwritten.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import date, datetime
from decimal import Decimal

import httpx
from sqlalchemy import select

log = logging.getLogger(__name__)
CBK_URL = "https://www.centralbank.go.ke/"
NAMES = {"US DOLLAR": "USD", "STG POUND": "GBP", "EURO": "EUR"}


def parse(html: str) -> tuple[date, dict[str, Decimal]]:
    """The home-page box -> (posted date, {currency: KES per unit}). ValueError if the page changed."""
    start = html.find("Daily KES Exchange Rates")
    end = html.find("</table>", start)
    if start < 0 or end < 0:
        raise ValueError("CBK rate box not found on the home page")
    box = html[start:end]
    posted = re.search(r"Posted On:\s*(\d{2}-\d{2}-\d{4})", box)
    rates = {NAMES[n.strip().upper()]: Decimal(v.replace(",", ""))
             for n, v in re.findall(r"<small>([^<]+)</small>\s*</td>\s*<td[^>]*>\s*([\d.,]+)\s*</td>", box)
             if n.strip().upper() in NAMES}
    if not posted or set(rates) != set(NAMES.values()):
        raise ValueError("CBK rate box could not be read")
    return datetime.strptime(posted.group(1), "%d-%m-%Y").date(), rates


async def store(db, posted: date, rates: dict[str, Decimal]) -> int:
    """Upsert the CBK rates for the posted day; a manual rate for that day wins. Returns rows written.

    A value more than 20 % away from the last stored rate is refused (a changed page must not reprice everything)."""
    from sqlalchemy.dialects.postgresql import insert

    from app.models.finance import ExchangeRate, RateSource

    for cur, value in rates.items():
        last = (await db.execute(select(ExchangeRate.rate_to_kes).where(ExchangeRate.currency == cur)
                                 .order_by(ExchangeRate.rate_date.desc()).limit(1))).scalar_one_or_none()
        if last and abs(value / Decimal(str(last)) - 1) > Decimal("0.2"):
            raise ValueError(f"CBK {cur} {value} is more than 20 % away from the last rate {last}; not stored")
    n = 0
    for cur, value in rates.items():
        inserted = await db.execute(insert(ExchangeRate).values(
            id=uuid.uuid4(), currency=cur, rate_date=posted, rate_to_kes=value, source=RateSource.CBK,
            notes="Fetched automatically from centralbank.go.ke").on_conflict_do_nothing(
            index_elements=["currency", "rate_date"]))
        if inserted.rowcount:
            n += 1
            continue
        row = (await db.execute(select(ExchangeRate).where(ExchangeRate.currency == cur,
                                                           ExchangeRate.rate_date == posted))).scalar_one()
        if row.source == RateSource.CBK and Decimal(str(row.rate_to_kes)) != value:
            row.rate_to_kes = value
            n += 1
    await db.flush()
    return n


async def fetch_and_store(db) -> dict:
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        resp = await client.get(CBK_URL)
        resp.raise_for_status()
    posted, rates = parse(resp.text)
    written = await store(db, posted, rates)
    return {"rate_date": posted.isoformat(), "rates": {k: float(v) for k, v in rates.items()}, "written": written}


async def run_cbk_rates(interval: int = 6 * 3600) -> None:
    """Background job: CBK posts once a working day; checking every 6 hours catches it the same day."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await fetch_and_store(db)
                await db.commit()
            log.info("CBK rates %s", result)
        except Exception:
            log.warning("CBK rate fetch failed; the last stored rate stays in use", exc_info=True)
        await asyncio.sleep(interval)
