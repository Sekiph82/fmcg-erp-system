"""Verify the additive accepted-volume migration on task-owned disposable PostgreSQL."""
from __future__ import annotations

import os
import re

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.db.session import engine


pytestmark = pytest.mark.skipif(
    os.environ.get("M25_S02_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_accepted_volume_column_is_optional_positive_numeric():
    expected_name = os.environ.get("M25_S02_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s02_t002_[a-f0-9]{20}", expected_name)

    async with engine.connect() as connection:
        actual_name = (await connection.execute(text("SELECT current_database()"))).scalar_one()
        column = (await connection.execute(text(
            "SELECT data_type, numeric_precision, numeric_scale, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'grn_lines' "
            "AND column_name = 'accepted_volume_m3'"
        ))).one()
        allocation_volume = (await connection.execute(text(
            "SELECT data_type, numeric_precision, numeric_scale, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'lc_allocation_lines' "
            "AND column_name = 'received_volume'"
        ))).one()
        constraint = (await connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = to_regclass('grn_lines') "
            "AND conname = 'ck_grn_lines_accepted_volume_positive'"
        ))).scalar_one_or_none()

    assert actual_name == expected_name
    assert tuple(column) == ("numeric", 14, 6, "YES", None)
    assert tuple(allocation_volume) == ("numeric", 14, 6, "YES")
    assert constraint is not None
    normalized_constraint = "".join(constraint.lower().split()).replace("(", "").replace(")", "").replace("::numeric", "")
    assert normalized_constraint == "checkaccepted_volume_m3isnulloraccepted_volume_m3>0"
