"""Owner 2026-11-20: the system keeps the KES rates current by itself from the Central Bank of Kenya home page."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import ExchangeRate, RateSource
from app.services.cbk_rates import parse, store

TASK_DB_ENV = "M39_CBK_DISPOSABLE_TEST_DATABASE"
TASK_DB_PATTERN = re.compile(r"fmcg_m39_cbk_[a-f0-9]{24}")

# the CBK home-page box as served on 2026-11-20 (trimmed)
PAGE = """<th class="tg-hgcj" colspan="3">Daily KES Exchange Rates<br></th></tr>
<tr><td class="tg-4eph" colspan="2"><small>US DOLLAR</small></td>
    <td class="tg-4eph">130.00</td></tr>
<tr><td class="tg-4eph" colspan="2"><small>STG POUND</small></td>
    <td class="tg-4eph">170.35</td></tr>
<tr><td class="tg-4eph" colspan="2"><small>EURO</small></td>
    <td class="tg-4eph">142.71</td></tr>
<tr><td  colspan="3" style="text-align:right;"><i>Posted On: 20-11-2026</i></td></tr></table>
<th class="tg-hgcj" colspan="4">Key Rates<br></th><tr><td><small>CBR</small></td><td>9.00</td></tr>"""


def test_parse_reads_the_daily_box_only():
    posted, rates = parse(PAGE)
    assert posted == date(2026, 11, 20)
    assert rates == {"USD": Decimal("130.00"), "GBP": Decimal("170.35"), "EUR": Decimal("142.71")}


def test_parse_refuses_a_changed_page():
    with pytest.raises(ValueError):
        parse("<html>maintenance</html>")


needs_db = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture
async def _dispose_engine():
    yield
    await engine.dispose()


@needs_db
@pytest.mark.asyncio
async def test_store_inserts_updates_and_keeps_a_manual_rate(_dispose_engine):
    assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_ENV + "_NAME", "")), "not the disposable database"
    assert TASK_DB_PATTERN.fullmatch(engine.url.database or "")
    day = date(2031, 1, 6)
    async with AsyncSessionLocal() as db:
        db.add(ExchangeRate(currency="EUR", rate_date=day, rate_to_kes=Decimal("150"), source=RateSource.MANUAL))
        await db.flush()
        assert await store(db, day, {"USD": Decimal("130.00"), "EUR": Decimal("142.71")}) == 1
        assert await store(db, day, {"USD": Decimal("130.00")}) == 0           # same value: nothing to write
        assert await store(db, day, {"USD": Decimal("130.25")}) == 1           # CBK corrected: follow it
        with pytest.raises(ValueError):                                          # a broken page: refused
            await store(db, day, {"USD": Decimal("13025")})
        rows = {r.currency: r for r in (await db.execute(select(ExchangeRate).where(ExchangeRate.rate_date == day))).scalars()}
        assert rows["USD"].rate_to_kes == Decimal("130.25") and rows["USD"].source == RateSource.CBK
        assert rows["EUR"].rate_to_kes == Decimal("150") and rows["EUR"].source == RateSource.MANUAL
        await db.rollback()
