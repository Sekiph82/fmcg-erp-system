"""Disposable PostgreSQL integration for non-crediting BOM secondary outputs."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.bom import AdvancedBOM, AdvancedBOMLine, BOMType, BasisType, ComponentType, ItemLinkType
from app.services.bom_costing_service import compute_bom_cost


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_secondary_output_lines_persist_as_quantities_without_reducing_bom_cost():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert re.fullmatch(r"fmcg_m21_s03_t002_[a-f0-9]{20,32}", expected_database)
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.database == expected_database
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        try:
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
            bom = AdvancedBOM(
                bom_code=f"M21-T002-BOM-{suffix}", bom_name="Synthetic multi-output BOM",
                bom_type=BOMType.COPRODUCT, base_qty=Decimal("100"), base_uom="KG",
            )
            db.add(bom)
            await db.flush()
            co_product_id = uuid4()
            by_product_id = uuid4()
            db.add_all([
                AdvancedBOMLine(
                    bom_id=bom.id, line_no=1, component_type=ComponentType.RAW,
                    item_type=ItemLinkType.MATERIAL, item_id=uuid4(), item_name="Synthetic raw input",
                    required_qty=Decimal("10"), required_uom="KG", basis_type=BasisType.PER_BATCH,
                    unit_cost=Decimal("2"),
                ),
                AdvancedBOMLine(
                    bom_id=bom.id, line_no=2, component_type=ComponentType.CO_PRODUCT,
                    item_type=ItemLinkType.PRODUCT, item_id=co_product_id,
                    item_code="CO-SYNTHETIC", item_name="Synthetic co-product",
                    required_qty=Decimal("3.5"), required_uom="L", basis_type=BasisType.PER_BATCH,
                    unit_cost=Decimal("50"),
                ),
                AdvancedBOMLine(
                    bom_id=bom.id, line_no=3, component_type=ComponentType.BY_PRODUCT,
                    item_type=ItemLinkType.PRODUCT, item_id=by_product_id,
                    item_code="BY-SYNTHETIC", item_name="Synthetic by-product",
                    required_qty=Decimal("1.25"), required_uom="KG", basis_type=BasisType.PER_BATCH,
                    unit_cost=Decimal("25"),
                ),
            ])
            await db.flush()

            result = await compute_bom_cost(db, bom.id)
            assert result.raw_material_cost == Decimal("20.0000")
            assert result.total_batch_cost == Decimal("20.0000")
            assert result.cost_per_uom == Decimal("0.2000")
            assert result.by_product_credit == Decimal("0.0000")
            assert [(row.quantity, row.uom) for row in result.co_product_outputs] == [
                (Decimal("3.5000"), "L"),
            ]
            assert [(row.quantity, row.uom) for row in result.by_product_outputs] == [
                (Decimal("1.2500"), "KG"),
            ]
            assert len(result.lines) == 1

            persisted = await db.scalar(select(AdvancedBOM).where(AdvancedBOM.id == bom.id))
            assert persisted.standard_batch_cost == Decimal("20.0000")
            assert persisted.by_product_credit == Decimal("0.0000")
        finally:
            await db.rollback()
