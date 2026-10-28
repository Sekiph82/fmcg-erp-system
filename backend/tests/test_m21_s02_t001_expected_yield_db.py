"""Disposable-PostgreSQL integration for persisted expected process yield."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.bom import AdvancedBOM


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_expected_process_yield_is_stored_as_input_percentage_and_legacy_rows_stay_null():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s02_t001_")
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            configured = AdvancedBOM(
                bom_code=f"M21-T001-CONFIG-{suffix}",
                bom_name="Synthetic expected-yield BOM",
                expected_process_yield_pct=Decimal("91.2500"),
            )
            legacy = AdvancedBOM(
                bom_code=f"M21-T001-LEGACY-{suffix}",
                bom_name="Synthetic legacy BOM",
            )
            db.add_all([configured, legacy])
            await db.flush()

            stored_configured = await db.get(AdvancedBOM, configured.id)
            stored_legacy = await db.get(AdvancedBOM, legacy.id)
            assert stored_configured.expected_process_yield_pct == Decimal("91.2500")
            assert stored_legacy.expected_process_yield_pct is None
        finally:
            await db.rollback()
