"""Disposable PostgreSQL integration for recipe-standard yield-loss costing."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.master import Material, MaterialType, Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_advanced import WasteCategory, WasteRecord, WasteType
from app.models.recipe import Recipe, RecipeStatus
from app.services.production_cost_service import compute_order_cost, finalize_order_cost, get_cost_report


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_recipe_standard_loss_is_priced_separately_from_finalized_production_cost():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert re.fullmatch(r"fmcg_m21_s05_t003_[a-f0-9]{20,32}", expected_database)
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.database == expected_database
    suffix = uuid4().hex[:12]
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            company = Company(name=f"M21 T003 synthetic company {suffix}", short_code=f"M21{suffix}")
            db.add(company)
            await db.flush()
            warehouse = Warehouse(
                code=f"M21-T003-WH-{suffix}", name="M21 T003 synthetic warehouse",
                warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
            )
            product = Product(
                sku=f"M21-T003-P-{suffix}", name="M21 T003 synthetic product",
                category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                standard_cost=Decimal("20"),
            )
            material = Material(
                code=f"M21-T003-M-{suffix}", name="M21 T003 synthetic material",
                material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
                standard_cost=Decimal("5"),
            )
            db.add_all([warehouse, product, material])
            await db.flush()

            recipe = Recipe(
                product_id=product.id, version="1", name="Synthetic costing recipe",
                status=RecipeStatus.APPROVED, is_active=True,
            )
            db.add(recipe)
            await db.flush()
            order = ProductionOrder(
                order_no=f"M21-T003-ORDER-{suffix}", product_id=product.id,
                recipe_id=recipe.id, planned_quantity=Decimal("100"),
                actual_quantity=Decimal("100"), uom="KG",
                status=ProductionOrderStatus.COMPLETED,
                target_warehouse_id=warehouse.id,
                scheduled_start=now, scheduled_end=now,
                actual_start=now, actual_end=now,
            )
            db.add(order)
            await db.flush()
            db.add(WasteRecord(
                waste_id=f"M21-T003-WASTE-{suffix}", production_order_id=order.id,
                material_id=material.id, waste_type=WasteType.MATERIAL,
                waste_category=WasteCategory.NORMAL,
                expected_qty=Decimal("100"), actual_qty=Decimal("88"),
                loss_qty=Decimal("12"), loss_pct=Decimal("12"),
                standard_loss_pct=Decimal("10"), uom="KG",
            ))
            await db.flush()

            computed = await compute_order_cost(db, order)
            assert computed["yield_loss_cost_variance"] == pytest.approx(10.0)
            assert computed["yield_loss_standard_record_count"] == 1
            assert computed["yield_loss_priced_record_count"] == 1
            assert computed["yield_loss_unpriced_record_count"] == 0
            assert computed["total_cost"] == pytest.approx(0.0)

            finalized = await finalize_order_cost(db, order)
            assert finalized.total_material_cost == Decimal("0.0000")
            assert finalized.total_labor_cost == Decimal("0.0000")
            assert finalized.total_machine_cost == Decimal("0.0000")
            assert finalized.total_energy_cost == Decimal("0.0000")
            assert finalized.total_cost == Decimal("0.0000")
            assert finalized.costing_finalized_at is not None

            report = await get_cost_report(db, product_id=product.id)
            assert len(report) == 1
            assert report[0]["total_cost"] == pytest.approx(0.0)
            assert report[0]["yield_loss_cost_variance"] == pytest.approx(10.0)
            assert report[0]["yield_loss_standard_record_count"] == 1
            assert report[0]["yield_loss_priced_record_count"] == 1
            assert report[0]["yield_loss_unpriced_record_count"] == 0
        finally:
            await db.rollback()
