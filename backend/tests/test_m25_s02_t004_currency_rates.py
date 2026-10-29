"""Dated Finance-rate snapshots used by landed-cost estimates."""
from datetime import date
from decimal import Decimal
import os
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import ExchangeRate, RateSource
from app.models.landed_cost import LandedCostType
from app.schemas.finance import ExchangeRateCreate
from app.schemas.landed_cost import LandedCostHeaderCreate, LandedCostHeaderUpdate, LandedCostLineCreate
from app.services.landed_cost_service import _header_totals, _resolve_rate_snapshot
from app.services import landed_cost_service as service


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _RateDB:
    def __init__(self, value):
        self.value = value
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _Result(self.value)


@pytest.mark.asyncio
async def test_non_base_currency_uses_latest_dated_finance_rate_not_after_bill_date():
    rate_id = uuid4()
    rate_row = SimpleNamespace(
        id=rate_id,
        currency="USD",
        rate_date=date(2026, 10, 28),
        rate_to_kes=Decimal("129.750000"),
        source=RateSource.CBK,
    )
    db = _RateDB(rate_row)

    snapshot = await _resolve_rate_snapshot(db, "usd", date(2026, 10, 29))

    assert snapshot == (Decimal("129.750000"), rate_id, date(2026, 10, 28), "CBK")
    sql = str(db.statement)
    assert "exchange_rates.rate_date <=" in sql
    assert "ORDER BY exchange_rates.rate_date DESC" in sql


@pytest.mark.asyncio
async def test_missing_bill_date_uses_today_and_excludes_future_rates():
    today = date.today()
    rate_row = SimpleNamespace(
        id=uuid4(), currency="EUR", rate_date=today,
        rate_to_kes=Decimal("150.000000"), source=RateSource.MANUAL,
    )
    db = _RateDB(rate_row)

    result = await _resolve_rate_snapshot(db, "EUR", None)

    assert result == (Decimal("150.000000"), rate_row.id, today, "MANUAL")
    assert "exchange_rates.rate_date <=" in str(db.statement)
    assert today in db.statement.compile().params.values()


@pytest.mark.asyncio
async def test_missing_or_non_positive_finance_rate_fails_closed():
    with pytest.raises(ValueError, match="No Finance exchange rate exists"):
        await _resolve_rate_snapshot(_RateDB(None), "EUR", date(2026, 10, 29))

    rate_row = SimpleNamespace(
        id=uuid4(), currency="EUR", rate_date=date(2026, 10, 29),
        rate_to_kes=Decimal("0"), source=RateSource.MANUAL,
    )
    with pytest.raises(ValueError, match="must be positive"):
        await _resolve_rate_snapshot(_RateDB(rate_row), "EUR", date(2026, 10, 29))


@pytest.mark.asyncio
async def test_kes_is_identity_rate_and_never_queries_finance_rates():
    db = _RateDB(None)
    target_date = date(2026, 10, 29)

    assert await _resolve_rate_snapshot(db, "kes", target_date) == (
        Decimal("1"), None, target_date, "BASE_CURRENCY",
    )
    assert db.statement is None


def test_mixed_currency_lines_sum_in_base_and_convert_to_document_currency():
    lines = [
        SimpleNamespace(amount_base=Decimal("1300.0000")),
        SimpleNamespace(amount_base=Decimal("650.0000")),
    ]

    assert _header_totals(lines, Decimal("130")) == (
        Decimal("15.0000"), Decimal("1950.0000"),
    )

    with pytest.raises(ValueError, match="must be positive"):
        _header_totals(lines, Decimal("0"))


def test_currency_inputs_are_normalized_and_manual_rates_are_rejected():
    line = LandedCostLineCreate(cost_type="FREIGHT_SEA", currency_code=" usd ")
    header = LandedCostHeaderCreate(currency_code="kes")
    assert line.currency_code == "USD"
    assert header.currency_code == "KES"

    with pytest.raises(ValidationError, match="three-letter ISO code"):
        LandedCostLineCreate(cost_type="FREIGHT_SEA", currency_code="US")
    with pytest.raises(ValidationError):
        LandedCostHeaderCreate(currency_code="USD", exchange_rate=Decimal("1"))
    with pytest.raises(ValidationError):
        LandedCostLineCreate(cost_type="FREIGHT_SEA", currency_code="USD", exchange_rate=Decimal("1"))


def test_finance_exchange_rates_require_iso_codes_and_positive_storable_rates():
    rate = ExchangeRateCreate(currency=" usd ", rate_date=date(2026, 10, 29), rate_to_kes=Decimal("129.75"))
    assert rate.currency == "USD"
    with pytest.raises(ValidationError):
        ExchangeRateCreate(currency="US", rate_date=date(2026, 10, 29), rate_to_kes=Decimal("129.75"))
    for invalid in (Decimal("0"), Decimal("-1"), Decimal("0.0000001"), Decimal("1000000000000"), Decimal("NaN")):
        with pytest.raises(ValidationError):
            ExchangeRateCreate(currency="USD", rate_date=date(2026, 10, 29), rate_to_kes=invalid)


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("M25_S02_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)
async def test_landed_cost_uses_and_recalculates_dated_finance_rate_snapshots():
    expected_name = os.environ.get("M25_S02_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s02_t004_[a-f0-9]{20}", expected_name)

    bill_date = date(2000, 1, 3)
    older_date = date(2000, 1, 2)
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_name
        legacy_values = (await db.execute(text(
            "SELECT h.exchange_rate_date, h.exchange_rate_source, l.exchange_rate_date, l.exchange_rate_source "
            "FROM lc_headers AS h JOIN lc_lines AS l ON l.header_id = h.id "
            "WHERE l.id = '25000000-0000-0000-0000-000000000039'"
        ))).one()
        assert tuple(legacy_values) == (None, None, None, None)
        db.add_all([
            ExchangeRate(currency="USD", rate_date=older_date, rate_to_kes=Decimal("1.500000"), source=RateSource.MANUAL),
            ExchangeRate(currency="USD", rate_date=bill_date, rate_to_kes=Decimal("2.000000"), source=RateSource.CBK),
            ExchangeRate(currency="XTS", rate_date=older_date, rate_to_kes=Decimal("6.000000"), source=RateSource.MANUAL),
            ExchangeRate(currency="XTS", rate_date=bill_date, rate_to_kes=Decimal("7.000000"), source=RateSource.CBK),
        ])
        await db.flush()

        document = await service.create_header(db, LandedCostHeaderCreate(
            bill_date=bill_date,
            currency_code="USD",
            cost_lines=[
                LandedCostLineCreate(cost_type=LandedCostType.FREIGHT_SEA, amount_fc=Decimal("10"), currency_code="XTS"),
                LandedCostLineCreate(cost_type=LandedCostType.CUSTOMS_DUTY, amount_fc=Decimal("100"), currency_code="KES"),
            ],
        ))
        xts_line = next(line for line in document.cost_lines if line.currency_code == "XTS")
        kes_line = next(line for line in document.cost_lines if line.currency_code == "KES")
        assert xts_line.exchange_rate == Decimal("7.000000")
        assert xts_line.exchange_rate_date == bill_date
        assert xts_line.exchange_rate_source == "CBK"
        assert xts_line.exchange_rate_id is not None
        assert xts_line.amount_base == Decimal("70.0000")
        assert kes_line.exchange_rate == Decimal("1")
        assert kes_line.exchange_rate_source == "BASE_CURRENCY"
        assert document.exchange_rate == Decimal("2.000000")
        assert document.exchange_rate_date == bill_date
        assert document.total_lc_amount_base == Decimal("170.0000")
        assert document.total_lc_amount_fc == Decimal("85.0000")

        recalculated = await service.update_header(
            db, document.id, LandedCostHeaderUpdate(bill_date=older_date),
        )
        xts_line = next(line for line in recalculated.cost_lines if line.currency_code == "XTS")
        assert xts_line.exchange_rate == Decimal("6.000000")
        assert xts_line.exchange_rate_date == older_date
        assert xts_line.exchange_rate_source == "MANUAL"
        assert xts_line.amount_base == Decimal("60.0000")
        assert recalculated.exchange_rate == Decimal("1.500000")
        assert recalculated.total_lc_amount_base == Decimal("160.0000")
        assert recalculated.total_lc_amount_fc == Decimal("106.6667")
    await engine.dispose()
