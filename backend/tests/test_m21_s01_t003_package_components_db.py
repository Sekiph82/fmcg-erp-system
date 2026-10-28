"""Disposable-PostgreSQL coverage for packaging requirements by target SKU."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.bom import (
    AdvancedBOM,
    AdvancedBOMLine,
    BOMConversionProfile,
    BOMType,
    BasisType,
    ComponentType,
    ItemLinkType,
)
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.models.utilities import UomConversion
from app.services.bom_scaling_service import calculate_package_components


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_profile_returns_component_quantities_for_its_exact_packaging_sku():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s01_t003_")
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            target = Product(
                sku=f"M21-T003-SKU-500ML-{suffix}",
                name="Synthetic 500 ml packaged SKU",
                category=ProductCategory.BEVERAGE,
                uom=UnitOfMeasure.PCS,
            )
            db.add(target)
            await db.flush()

            packaging_bom = AdvancedBOM(
                bom_code=f"M21-T003-PKG-{suffix}",
                bom_name="Synthetic package BOM for 500 ml SKU",
                bom_type=BOMType.PACKAGING,
                product_id=target.id,
                product_name=target.name,
                base_qty=Decimal("100"),
                base_uom="PCS",
            )
            db.add(packaging_bom)
            await db.flush()

            profile = BOMConversionProfile(
                profile_code=f"M21-T003-PROFILE-{suffix}",
                profile_name="Synthetic 500 ml conversion profile",
                target_product_id=target.id,
                target_product_name=target.name,
                linked_packaging_bom_id=packaging_bom.id,
                theoretical_conversion_ratio=Decimal("1"),
            )
            bottle_id, cap_id = uuid4(), uuid4()
            db.add_all([
                profile,
                UomConversion(
                    from_uom="CARTON",
                    to_uom="PCS",
                    factor=Decimal("12"),
                    is_active=True,
                ),
                AdvancedBOMLine(
                    bom_id=packaging_bom.id,
                    line_no=1,
                    component_type=ComponentType.PACKAGING,
                    item_type=ItemLinkType.PRODUCT,
                    item_id=bottle_id,
                    item_name="Synthetic bottle",
                    item_code=f"M21-T003-BOTTLE-{suffix}",
                    required_qty=Decimal("1"),
                    required_uom="PCS",
                    basis_type=BasisType.PER_UNIT,
                ),
                AdvancedBOMLine(
                    bom_id=packaging_bom.id,
                    line_no=2,
                    component_type=ComponentType.PACKAGING,
                    item_type=ItemLinkType.PRODUCT,
                    item_id=cap_id,
                    item_name="Synthetic cap",
                    item_code=f"M21-T003-CAP-{suffix}",
                    required_qty=Decimal("1"),
                    required_uom="PCS",
                    basis_type=BasisType.PER_UNIT,
                    wastage_pct=Decimal("2"),
                ),
                AdvancedBOMLine(
                    bom_id=packaging_bom.id,
                    line_no=3,
                    component_type=ComponentType.INTERMEDIATE,
                    item_type=ItemLinkType.PRODUCT,
                    item_id=uuid4(),
                    item_name="Synthetic bulk liquid",
                    required_qty=Decimal("0.5"),
                    required_uom="L",
                    basis_type=BasisType.PER_UNIT,
                ),
            ])
            await db.flush()

            result = await calculate_package_components(
                db, profile.id, Decimal("250")
            )

            assert result.target_sku == target.sku
            assert result.normalized_qty == Decimal("250")
            assert result.normalized_uom == "PCS"
            assert [component.item_id for component in result.components] == [
                bottle_id,
                cap_id,
            ]
            assert [component.scaled_qty for component in result.components] == [
                Decimal("250.0000"),
                Decimal("250.0000"),
            ]
            assert result.components[1].adjusted_qty == Decimal("255.0000")

            carton_result = await calculate_package_components(
                db, profile.id, Decimal("2"), target_uom="CARTON"
            )
            assert carton_result.requested_uom == "CARTON"
            assert carton_result.normalized_qty == Decimal("24")
            assert carton_result.normalized_uom == "PCS"
            assert [component.scaled_qty for component in carton_result.components] == [
                Decimal("24.0000"),
                Decimal("24.0000"),
            ]
            assert carton_result.components[1].adjusted_qty == Decimal("24.4800")
        finally:
            await db.rollback()
