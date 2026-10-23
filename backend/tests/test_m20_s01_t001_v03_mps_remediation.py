"""Behavioral coverage for the frozen M20.S01.T001 V03 findings."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.v1.endpoints import mps as mps_api
from app.models.mps import MPSFeasibilityStatus, MPSStatus
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.master import Warehouse
from app.models.user import User
from app.models.recipe import RecipeStatus
from app.services import mps_service as svc


def _result(*, one=None, many=None, scalar=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalar.return_value = scalar
    if many is not None:
        result.scalars.return_value.all.return_value = many
    return result


def _plan():
    return SimpleNamespace(
        id=uuid4(),
        status=MPSStatus.APPROVED,
        plan_no="MPS- V03",
        start_date=__import__("datetime").date(2026, 1, 1),
        end_date=__import__("datetime").date(2026, 1, 31),
        released_at=None,
        mrp_run_id=uuid4(),
    )


def _line(product_id, line_no):
    return SimpleNamespace(
        id=uuid4(),
        line_no=line_no,
        product_id=product_id,
        planned_production_qty=100,
        planned_start_date=None,
        planned_end_date=None,
        remarks=None,
        production_order_id=None,
        feasibility_status=MPSFeasibilityStatus.FEASIBLE,
    )


def _recipe(product_id):
    return SimpleNamespace(
        id=uuid4(),
        product_id=product_id,
        status=RecipeStatus.APPROVED,
        is_active=True,
        valid_from=None,
        valid_to=None,
    )


def _db(results, get_results):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    db.scalar = AsyncMock(return_value=0)
    remaining = list(get_results)
    source_warehouse = SimpleNamespace(id=uuid4(), code="WH-SOURCE", is_active=True, company_id=None)
    source_run = SimpleNamespace(id=uuid4(), status=MRPRunStatus.COMPLETED, warehouse_id=source_warehouse.id)
    actor = SimpleNamespace(id=uuid4(), email="mps-test@example.invalid", full_name="MPS Test")

    async def get(model, object_id):
        if model is MRPRun:
            return source_run
        if model is User:
            return actor
        if model is Warehouse and object_id == source_warehouse.id:
            return source_warehouse
        value = remaining.pop(0) if remaining else None
        if model is Warehouse and value is not None and not hasattr(value, "company_id"):
            value.company_id = None
        return value

    db.get = AsyncMock(side_effect=get)
    db.flush = AsyncMock()

    def add(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    db.add = MagicMock(side_effect=add)
    return db


async def test_mixed_partial_release_remains_approved_and_reports_unresolved_lines():
    plan = _plan()
    product_a, product_b = uuid4(), uuid4()
    line_a, line_b = _line(product_a, "MPSL-1"), _line(product_b, "MPSL-2")
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_a, uom=SimpleNamespace(value="KG"))
    db = _db(
        [
            _result(one=plan),
            _result(many=[line_a, line_b]),
            _result(scalar=0),
            _result(one=_recipe(product_a)),
            _result(one=None),
        ],
        [warehouse, product],
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), warehouse.id)

    assert result == {
        "released_orders": 0,
        "skipped_no_recipe": 1,
        "skipped_ineligible": 0,
        "unresolved_lines": 1,
        "release_required_lines": 2,
        "release_complete": False,
    }
    assert plan.status == MPSStatus.APPROVED
    assert plan.released_at is None


@pytest.mark.parametrize("product", [None, SimpleNamespace(uom=None), SimpleNamespace(uom="NOT_A_UOM")])
async def test_release_fails_closed_for_missing_or_invalid_authoritative_product_uom(product):
    plan = _plan()
    product_id = uuid4()
    line = _line(product_id, "MPSL-1")
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    db = _db(
        [
            _result(one=plan),
            _result(many=[line]),
            _result(scalar=0),
            _result(one=_recipe(product_id)),
        ],
        [warehouse, product],
    )

    with pytest.raises(ValueError, match="(missing|valid authoritative UOM)"):
        await svc.release_mps_plan(db, plan.id, uuid4(), warehouse.id)

    db.add.assert_not_called()
    assert plan.status == MPSStatus.APPROVED


@pytest.mark.asyncio
async def test_release_endpoint_rolls_back_persisted_state_on_late_flush_failure(monkeypatch):
    """A real PostgreSQL transaction must roll back PO/link/status changes."""
    from sqlalchemy import func, select, text

    from app.core.config import settings
    from app.db.session import AsyncSessionLocal, engine
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
    from app.models.mps import MPSLine, MPSPlan
    from app.models.production import ProductionOrder
    from app.models.recipe import Recipe
    from app.models.mrp import MRPRun, MRPRunStatus
    from app.models.user import User

    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("V04 real rollback proof requires the PostgreSQL CI service")

    await engine.dispose()
    async with AsyncSessionLocal() as probe:
        await probe.execute(text("SELECT 1"))

    suffix = uuid4().hex[:10]
    plan_id = warehouse_id = product_id = recipe_id = line_id = run_id = user_id = None
    async with AsyncSessionLocal() as db:
        async with db.begin():
            warehouse = Warehouse(code=f"V04-{suffix}", name="V04 rollback warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
            product = Product(sku=f"V04-{suffix}", name="V04 rollback product", category=ProductCategory.FOOD, uom=UnitOfMeasure.KG)
            db.add_all([warehouse, product])
            await db.flush()
            source_run = MRPRun(run_no=f"V04-RUN-{suffix}", run_date=__import__("datetime").date(2026, 1, 1), status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id)
            actor = User(email=f"v04-{suffix}@example.invalid", username=f"v04-{suffix}", full_name="V04 Test", hashed_password="test")
            recipe = Recipe(product_id=product.id, version="1", name="V04 rollback recipe", status=RecipeStatus.APPROVED, is_active=True)
            db.add_all([source_run, actor, recipe])
            await db.flush()
            plan = MPSPlan(plan_no=f"V04-{suffix}", plan_name="V04 rollback plan", start_date=__import__("datetime").date(2026, 1, 1), end_date=__import__("datetime").date(2026, 1, 31), status=MPSStatus.APPROVED, mrp_run_id=source_run.id)
            db.add(plan)
            await db.flush()
            line = MPSLine(line_no=f"V04-{suffix}", mps_id=plan.id, product_id=product.id, period_start=__import__("datetime").date(2026, 1, 1), period_end=__import__("datetime").date(2026, 1, 31), planned_production_qty=100, feasibility_status=MPSFeasibilityStatus.FEASIBLE)
            db.add(line)
            await db.flush()
            plan_id, warehouse_id, product_id, recipe_id, line_id, run_id, user_id = plan.id, warehouse.id, product.id, recipe.id, line.id, source_run.id, actor.id

    original_flush = db.flush
    flush_calls = 0

    async def fail_on_final_flush(*args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise RuntimeError("V04 injected late flush failure")
        return await original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", fail_on_final_flush)
    with pytest.raises(RuntimeError, match="V04 injected"):
        await mps_api.release_plan(plan_id, warehouse_id, db, SimpleNamespace(id=user_id, is_superuser=True))

    async with AsyncSessionLocal() as verify:
        assert await verify.scalar(select(func.count()).select_from(ProductionOrder).where(ProductionOrder.product_id == product_id)) == 0
        persisted_line = await verify.get(MPSLine, line_id)
        persisted_plan = await verify.get(MPSPlan, plan_id)
        assert persisted_line.production_order_id is None
        assert persisted_plan.status == MPSStatus.APPROVED

    async with AsyncSessionLocal() as cleanup:
        async with cleanup.begin():
            await cleanup.execute(__import__("sqlalchemy").delete(MPSLine).where(MPSLine.id == line_id))
            await cleanup.execute(__import__("sqlalchemy").delete(MPSPlan).where(MPSPlan.id == plan_id))
            await cleanup.execute(__import__("sqlalchemy").delete(Recipe).where(Recipe.id == recipe_id))
            await cleanup.execute(__import__("sqlalchemy").delete(MRPRun).where(MRPRun.id == run_id))
            await cleanup.execute(__import__("sqlalchemy").delete(User).where(User.id == user_id))
            await cleanup.execute(__import__("sqlalchemy").delete(Product).where(Product.id == product_id))
            await cleanup.execute(__import__("sqlalchemy").delete(Warehouse).where(Warehouse.id == warehouse_id))


@pytest.mark.asyncio
async def test_concurrent_postgres_mps_releases_allocate_distinct_order_numbers():
    """Concurrent PostgreSQL releases must not reuse the same PO-MPS number."""
    from sqlalchemy import delete, func, select, text

    from app.core.config import settings
    from app.db.session import AsyncSessionLocal, engine
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
    from app.models.mps import MPSLine, MPSPlan
    from app.models.production import ProductionOrder
    from app.models.recipe import Recipe
    from app.models.mrp import MRPRun, MRPRunStatus
    from app.models.user import User

    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("V04 concurrency proof requires the PostgreSQL CI service")

    await engine.dispose()
    async with AsyncSessionLocal() as probe:
        await probe.execute(text("SELECT 1"))

    suffix = uuid4().hex[:10]
    plan_ids, product_ids, line_ids, recipe_ids = [], [], [], []
    async with AsyncSessionLocal() as db:
        async with db.begin():
            warehouse = Warehouse(code=f"V04-C-{suffix}", name="V04 concurrency warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
            source_run = MRPRun(run_no=f"V04-C-RUN-{suffix}", run_date=__import__("datetime").date(2026, 1, 1), status=MRPRunStatus.COMPLETED, warehouse_id=None)
            actor = User(email=f"v04-c-{suffix}@example.invalid", username=f"v04-c-{suffix}", full_name="V04 Test", hashed_password="test")
            db.add_all([warehouse, source_run, actor])
            await db.flush()
            source_run.warehouse_id = warehouse.id
            for index in range(2):
                product = Product(sku=f"V04-C-{suffix}-{index}", name=f"V04 concurrency product {index}", category=ProductCategory.FOOD, uom=UnitOfMeasure.KG)
                db.add(product)
                await db.flush()
                recipe = Recipe(product_id=product.id, version="1", name=f"V04 concurrency recipe {index}", status=RecipeStatus.APPROVED, is_active=True)
                plan = MPSPlan(plan_no=f"V04-C-{suffix}-{index}", plan_name=f"V04 concurrency plan {index}", start_date=__import__("datetime").date(2026, 1, 1), end_date=__import__("datetime").date(2026, 1, 31), status=MPSStatus.APPROVED, mrp_run_id=source_run.id)
                db.add_all([recipe, plan])
                await db.flush()
                line = MPSLine(line_no=f"V04-C-{suffix}-{index}", mps_id=plan.id, product_id=product.id, period_start=__import__("datetime").date(2026, 1, 1), period_end=__import__("datetime").date(2026, 1, 31), planned_production_qty=100, feasibility_status=MPSFeasibilityStatus.FEASIBLE)
                db.add(line)
                await db.flush()
                product_ids.append(product.id)
                recipe_ids.append(recipe.id)
                plan_ids.append(plan.id)
                line_ids.append(line.id)
            warehouse_id = warehouse.id
            source_run_id, user_id = source_run.id, actor.id

    async def release(plan_id):
        async with AsyncSessionLocal() as db:
            return await mps_api.release_plan(plan_id, warehouse_id, db, SimpleNamespace(id=user_id, is_superuser=True))

    results = await asyncio.gather(*(release(plan_id) for plan_id in plan_ids))
    assert [result["released_orders"] for result in results] == [1, 1]

    async with AsyncSessionLocal() as verify:
        orders = (await verify.scalars(select(ProductionOrder).where(ProductionOrder.product_id.in_(product_ids)))).all()
        assert len(orders) == 2
        assert len({order.order_no for order in orders}) == 2
        assert all(order.order_no.startswith("PO-MPS-") for order in orders)
        highest_number = max(int(order.order_no.removeprefix("PO-MPS-")) for order in orders)
        deleted_order_id = orders[0].id

    async with AsyncSessionLocal() as delete_session:
        async with delete_session.begin():
            await delete_session.execute(delete(ProductionOrder).where(ProductionOrder.id == deleted_order_id))

    extra_product_id = extra_recipe_id = extra_plan_id = extra_line_id = None
    async with AsyncSessionLocal() as db:
        async with db.begin():
            extra_product = Product(sku=f"V04-C-{suffix}-retry", name="V04 deletion-gap product", category=ProductCategory.FOOD, uom=UnitOfMeasure.KG)
            db.add(extra_product)
            await db.flush()
            extra_recipe = Recipe(product_id=extra_product.id, version="1", name="V04 deletion-gap recipe", status=RecipeStatus.APPROVED, is_active=True)
            extra_plan = MPSPlan(plan_no=f"V04-C-{suffix}-retry", plan_name="V04 deletion-gap plan", start_date=__import__("datetime").date(2026, 1, 1), end_date=__import__("datetime").date(2026, 1, 31), status=MPSStatus.APPROVED, mrp_run_id=source_run_id)
            db.add_all([extra_recipe, extra_plan])
            await db.flush()
            extra_line = MPSLine(line_no=f"V04-C-{suffix}-retry", mps_id=extra_plan.id, product_id=extra_product.id, period_start=__import__("datetime").date(2026, 1, 1), period_end=__import__("datetime").date(2026, 1, 31), planned_production_qty=100, feasibility_status=MPSFeasibilityStatus.FEASIBLE)
            db.add(extra_line)
            await db.flush()
            extra_product_id, extra_recipe_id = extra_product.id, extra_recipe.id
            extra_plan_id, extra_line_id = extra_plan.id, extra_line.id

    result = await release(extra_plan_id)
    assert result["released_orders"] == 1
    async with AsyncSessionLocal() as verify:
        extra_order = await verify.scalar(select(ProductionOrder).where(ProductionOrder.product_id == extra_product_id))
        assert extra_order is not None
        assert int(extra_order.order_no.removeprefix("PO-MPS-")) > highest_number

    async with AsyncSessionLocal() as cleanup:
        async with cleanup.begin():
            await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.product_id.in_(product_ids)))
            await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.product_id == extra_product_id))
            await cleanup.execute(delete(MPSLine).where(MPSLine.id.in_(line_ids)))
            await cleanup.execute(delete(MPSLine).where(MPSLine.id == extra_line_id))
            await cleanup.execute(delete(MPSPlan).where(MPSPlan.id.in_(plan_ids)))
            await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == extra_plan_id))
            await cleanup.execute(delete(Recipe).where(Recipe.id.in_(recipe_ids)))
            await cleanup.execute(delete(Recipe).where(Recipe.id == extra_recipe_id))
            await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
            await cleanup.execute(delete(Product).where(Product.id == extra_product_id))
            await cleanup.execute(delete(MRPRun).where(MRPRun.id == source_run_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
    # This test owns concurrent PostgreSQL sessions. Dispose pooled asyncpg
    # connections on this pytest-asyncio loop so the shared engine cannot leak
    # a connection/finalizer into a later test's loop.
    await engine.dispose()
