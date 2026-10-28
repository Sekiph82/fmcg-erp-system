"""Disposable-PostgreSQL integration for the spillage enum and loss configs."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal
from app.models.bom import AdvancedBOM, BOMYieldConfig, LossCategory


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_distinct_filling_packaging_and_spillage_loss_configurations_persist():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s02_t002_")
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database
            bom = AdvancedBOM(
                bom_code=f"M21-T002-{suffix}",
                bom_name="Synthetic filling and packaging BOM",
            )
            db.add(bom)
            await db.flush()

            configs = [
                BOMYieldConfig(bom_id=bom.id, loss_category=category, standard_pct=Decimal(value))
                for category, value in (
                    (LossCategory.FILLING, "1.250"),
                    (LossCategory.PACKAGING_REJECT, "0.500"),
                    (LossCategory.SPILLAGE, "0.125"),
                )
            ]
            db.add_all(configs)
            await db.flush()

            labels = set((await db.execute(text(
                "SELECT enumlabel FROM pg_enum "
                "JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                "WHERE pg_type.typname = 'losscategory'"
            ))).scalars().all())
            assert "SPILLAGE" in labels
            stored = await db.execute(
                text(
                    "SELECT loss_category::text, standard_pct "
                    "FROM bom_yield_configs WHERE bom_id = :bom_id ORDER BY loss_category::text"
                ),
                {"bom_id": bom.id},
            )
            assert {row[0]: Decimal(row[1]) for row in stored.all()} == {
                "FILLING": Decimal("1.250"),
                "PACKAGING_REJECT": Decimal("0.500"),
                "SPILLAGE": Decimal("0.125"),
            }

            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(BOMYieldConfig(
                        bom_id=bom.id,
                        loss_category=LossCategory.SPILLAGE,
                        standard_pct=Decimal("NaN"),
                    ))
                    await db.flush()

            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(BOMYieldConfig(
                        bom_id=bom.id,
                        loss_category=LossCategory.SPILLAGE,
                        standard_pct=Decimal("1"),
                        max_allowable_pct=Decimal("NaN"),
                    ))
                    await db.flush()
        finally:
            await db.rollback()
