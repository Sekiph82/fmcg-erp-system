"""Real PostgreSQL coverage for profile density and configured UOM conversion."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.bom import BOMConversionProfile
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.models.utilities import UomConversion
from app.services.bom_scaling_service import calculate_conversion


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_conversion_profile_uses_density_and_direct_inverse_uom_rules():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s01_t002_")
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        async with db.begin():
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            bulk = Product(
                sku=f"M21-T002-BULK-{suffix}",
                name="Synthetic bulk product",
                category=ProductCategory.BEVERAGE,
                uom=UnitOfMeasure.KG,
            )
            carton = Product(
                sku=f"M21-T002-CARTON-{suffix}",
                name="Synthetic carton product",
                category=ProductCategory.BEVERAGE,
                uom=UnitOfMeasure.CARTON,
            )
            db.add_all([bulk, carton])
            await db.flush()

            density_profile = BOMConversionProfile(
                profile_code=f"M21-T002-DENSITY-{suffix}",
                profile_name="Synthetic density conversion",
                source_product_id=bulk.id,
                theoretical_conversion_ratio=Decimal("1000"),
                density_g_per_ml=Decimal("0.9"),
                startup_loss_pct=Decimal("0"),
                shutdown_loss_pct=Decimal("0"),
                packaging_reject_pct=Decimal("0"),
                residual_bulk_pct=Decimal("0"),
                line_purge_loss_pct=Decimal("0"),
            )
            configured_profile = BOMConversionProfile(
                profile_code=f"M21-T002-UOM-{suffix}",
                profile_name="Synthetic configured UOM conversion",
                source_product_id=carton.id,
                theoretical_conversion_ratio=Decimal("10"),
                startup_loss_pct=Decimal("0"),
                shutdown_loss_pct=Decimal("0"),
                packaging_reject_pct=Decimal("0"),
                residual_bulk_pct=Decimal("0"),
                line_purge_loss_pct=Decimal("0"),
            )
            db.add_all([
                density_profile,
                configured_profile,
                UomConversion(
                    from_uom="BOX", to_uom="CARTON", factor=Decimal("0.5"),
                    is_active=True,
                ),
                UomConversion(
                    from_uom="CARTON", to_uom="PALLET", factor=Decimal("0.25"),
                    is_active=True,
                ),
            ])
            await db.flush()

            density_result = await calculate_conversion(
                db, density_profile.id, Decimal("1"), source_uom="L"
            )
            direct_result = await calculate_conversion(
                db, configured_profile.id, Decimal("3"), source_uom="BOX"
            )
            inverse_result = await calculate_conversion(
                db, configured_profile.id, Decimal("2"), source_uom="PALLET"
            )

            assert density_result.theoretical_units == Decimal("900.00")
            assert density_result.source_uom == "L"
            assert direct_result.theoretical_units == Decimal("15.00")
            assert inverse_result.theoretical_units == Decimal("80.00")
