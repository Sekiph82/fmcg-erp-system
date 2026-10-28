"""Disposable-PostgreSQL integration proof for persisted nested BOM recursion."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.bom import (
    AdvancedBOM,
    AdvancedBOMLine,
    BOMLifecycle,
    BOMType,
    ComponentType,
    ItemLinkType,
)
from app.services.bom_explosion_service import explode_bom


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


class _RollbackFixture(Exception):
    pass


@pytest.mark.asyncio
async def test_postgres_explosion_loads_nested_bom_and_aggregates_reused_child():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s03_t001_")
    suffix = uuid4().hex[:12]
    root_code = f"M21-T001-ROOT-{suffix}"

    await engine.dispose()
    async with AsyncSessionLocal() as db:
        try:
            async with db.begin():
                actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
                assert actual_database == expected_database

                root = AdvancedBOM(
                    bom_code=root_code,
                    bom_name="Synthetic finished product",
                    bom_type=BOMType.MULTILEVEL,
                    base_qty=100,
                    base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED,
                )
                child = AdvancedBOM(
                    bom_code=f"M21-T001-CHILD-{suffix}",
                    bom_name="Synthetic intermediate premix",
                    bom_type=BOMType.INTERMEDIATE,
                    base_qty=10,
                    base_uom="KG",
                    lifecycle=BOMLifecycle.RELEASED,
                )
                db.add_all([root, child])
                await db.flush()

                db.add_all([
                    AdvancedBOMLine(
                        bom_id=root.id,
                        line_no=1,
                        item_type=ItemLinkType.PRODUCT,
                        component_type=ComponentType.INTERMEDIATE,
                        item_name="Premix A",
                        child_bom_id=child.id,
                        required_qty=25,
                        required_uom="KG",
                        wastage_pct=4,
                    ),
                    AdvancedBOMLine(
                        bom_id=root.id,
                        line_no=2,
                        item_type=ItemLinkType.PRODUCT,
                        component_type=ComponentType.INTERMEDIATE,
                        item_name="Premix B",
                        child_bom_id=child.id,
                        required_qty=25,
                        required_uom="KG",
                        wastage_pct=4,
                    ),
                    AdvancedBOMLine(
                        bom_id=child.id,
                        line_no=1,
                        item_type=ItemLinkType.MATERIAL,
                        component_type=ComponentType.RAW,
                        item_name="Synthetic sugar",
                        item_code=f"M21-T001-SUGAR-{suffix}",
                        required_qty=3,
                        required_uom="KG",
                        wastage_pct=2,
                    ),
                ])
                await db.flush()

                result = await explode_bom(db, root.id, Decimal("100"))

                assert result.total_levels == 2
                assert len(result.nodes) == 2
                assert all(len(node.children) == 1 for node in result.nodes)
                assert len(result.flat_requirements) == 1
                assert result.flat_requirements[0]["item_name"] == "Synthetic sugar"
                assert result.flat_requirements[0]["total_qty"] == 15.6
                assert result.flat_requirements[0]["total_adjusted_qty"] == 15.912
                raise _RollbackFixture()
        except _RollbackFixture:
            pass

    async with AsyncSessionLocal() as db:
        remaining = await db.scalar(
            select(func.count(AdvancedBOM.id)).where(AdvancedBOM.bom_code == root_code)
        )
        assert remaining == 0
