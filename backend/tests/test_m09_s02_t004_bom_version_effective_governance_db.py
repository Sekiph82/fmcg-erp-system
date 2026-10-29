"""PostgreSQL-only BOM guards, restricted to a named task-owned database."""
from __future__ import annotations

import os
import re
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal, engine
from app.models.bom import AdvancedBOM


pytestmark = pytest.mark.skipif(
    os.environ.get("M09_S02_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_database_identity(db) -> None:
    expected = os.environ.get("M09_S02_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"fmcg_m09_s02_t004_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(text("SELECT current_database()"))).scalar_one()
    assert actual == expected


@pytest.mark.asyncio
async def test_postgres_constraints_reject_blank_bom_versions_and_reversed_dates():
    invalid_values = (
        {"version_no": " \t\n ", "revision_no": "0"},
        {"version_no": "v1", "revision_no": " \t\n "},
        {
            "version_no": "v1",
            "revision_no": "0",
            "effective_from": date(2026, 11, 2),
            "effective_to": date(2026, 11, 1),
        },
    )
    for invalid in invalid_values:
        async with AsyncSessionLocal() as db:
            try:
                await _assert_database_identity(db)
                db.add(
                    AdvancedBOM(
                        bom_code=f"M09-T004-{uuid4().hex[:16]}",
                        bom_name="Synthetic invalid BOM",
                        **invalid,
                    )
                )
                with pytest.raises(IntegrityError):
                    await db.flush()
            finally:
                await db.rollback()


@pytest.mark.asyncio
async def test_postgres_constraints_allow_equal_and_unbounded_effective_dates():
    async with AsyncSessionLocal() as db:
        try:
            await _assert_database_identity(db)
            boundary = date(2026, 11, 1)
            equal = AdvancedBOM(
                bom_code=f"M09-T004-{uuid4().hex[:16]}",
                bom_name="Synthetic one-day BOM",
                version_no="opaque/rev-A",
                revision_no="revision-0",
                effective_from=boundary,
                effective_to=boundary,
            )
            open_ended = AdvancedBOM(
                bom_code=f"M09-T004-{uuid4().hex[:16]}",
                bom_name="Synthetic open-ended BOM",
                version_no="future-v2",
                revision_no="0",
                effective_from=boundary,
                effective_to=None,
            )
            db.add_all([equal, open_ended])
            await db.flush()
        finally:
            await db.rollback()
