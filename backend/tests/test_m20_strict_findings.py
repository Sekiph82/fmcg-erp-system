"""PostgreSQL regression tests for strict M20 audit findings F11 and F12."""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.mps import MPSFeasibilityStatus, MPSLine, MPSPlan, MPSStatus
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.production import ProductionOrder
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.mps_service import release_mps_plan
from app.services.mps_whatif_service import _simulate_scenario_materials


class _RollbackFixture(Exception):
    pass


@pytest.mark.asyncio
async def test_postgres_released_plan_with_partial_order_links_fails_idempotent_retry_closed():
    """A RELEASED header must not hide an unreleased positive-quantity line."""
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 release-integrity proof requires PostgreSQL")

    # The application engine is shared while pytest-asyncio uses function
    # loops; dispose pooled asyncpg connections at the test boundary.
    await engine.dispose()
    suffix = uuid4().hex[:12]
    async with AsyncSessionLocal() as db:
        try:
            async with db.begin():
                warehouse = Warehouse(
                    code=f"M20-F11-WH-{suffix}", name="M20 F11 warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS,
                )
                product = Product(
                    sku=f"M20-F11-P-{suffix}", name="M20 F11 product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                db.add_all([warehouse, product])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-F11-RUN-{suffix}", run_date=date(2026, 1, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                recipe = Recipe(
                    product_id=product.id, version="1", name="M20 F11 approved recipe",
                    status=RecipeStatus.APPROVED, is_active=True,
                )
                actor = User(
                    email=f"m20-f11-{suffix}@example.invalid", username=f"m20-f11-{suffix}",
                    full_name="M20 F11 Test", hashed_password="test",
                )
                db.add_all([recipe, actor])
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-F11-PLAN-{suffix}", plan_name="M20 F11 partial release",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                    status=MPSStatus.RELEASED, mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                production_order = ProductionOrder(
                    order_no=f"PO-M20-F11-{suffix}", product_id=product.id,
                    recipe_id=recipe.id, planned_quantity=1, uom="KG",
                    target_warehouse_id=warehouse.id,
                    scheduled_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    scheduled_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    created_by=actor.id,
                )
                db.add(production_order)
                await db.flush()
                line = MPSLine(
                    line_no=f"M20-F11-LINE-{suffix}", mps_id=plan.id,
                    product_id=product.id, period_start=date(2026, 1, 1),
                    period_end=date(2026, 1, 31), planned_production_qty=1,
                    feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                    production_order_id=production_order.id,
                )
                db.add(line)
                await db.flush()
                await db.delete(production_order)
                await db.flush()
                await db.refresh(line)
                assert line.production_order_id is None

                with pytest.raises(ValueError, match="missing production-order links"):
                    await release_mps_plan(db, plan.id, uuid4(), warehouse.id)
                raise _RollbackFixture()
        except _RollbackFixture:
            pass
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_material_shortage_is_complete_calculation_but_unknown_bom_is_partial():
    """A shortage is a computed result; absent approved master data is unknown."""
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 scenario status proof requires PostgreSQL")

    await engine.dispose()
    suffix = uuid4().hex[:12]
    async with AsyncSessionLocal() as db:
        try:
            async with db.begin():
                warehouse = Warehouse(
                    code=f"M20-F12-WH-{suffix}", name="M20 F12 warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS,
                )
                product = Product(
                    sku=f"M20-F12-P-{suffix}", name="M20 F12 product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                db.add_all([warehouse, product])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-F12-RUN-{suffix}", run_date=date(2026, 1, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-F12-PLAN-{suffix}", plan_name="M20 F12 unknown input",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                    mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                line = MPSLine(
                    line_no=f"M20-F12-LINE-{suffix}", mps_id=plan.id,
                    product_id=product.id, period_start=date(2026, 1, 1),
                    period_end=date(2026, 1, 31), planned_production_qty=1,
                    planned_start_date=date(2026, 1, 1), planned_end_date=date(2026, 1, 31),
                )
                db.add(line)
                await db.flush()

                result = await _simulate_scenario_materials(db, plan.id, {
                    str(line.id): {
                        "planned_production_qty": "2",
                        "planned_start_date": "2026-01-01",
                        "planned_end_date": "2026-01-31",
                    }
                })
                assert result["status"] == "PARTIAL_INPUTS", repr(result)
                assert "baseline_infeasible_lines" in result, repr(result)
                assert result["baseline_infeasible_lines"] == 1
                assert result["candidate_infeasible_lines"] == 1
                assert result["shortage_count_delta"] is None
                assert result["unknown_reasons"]
                raise _RollbackFixture()
        except _RollbackFixture:
            pass
    await engine.dispose()
