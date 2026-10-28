"""Disposable PostgreSQL migration contract for recipe-standard snapshots."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_standard_loss_snapshot_column_is_nullable_and_does_not_backfill_history():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s02_t003_")

    async with AsyncSessionLocal() as db:
        actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
        assert actual_database == expected_database
        nullable = (await db.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'waste_records' "
            "AND column_name = 'standard_loss_pct'"
        ))).scalar_one()
        assert nullable == "YES"
        default = (await db.execute(text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'waste_records' "
            "AND column_name = 'standard_loss_pct'"
        ))).scalar_one()
        assert default is None