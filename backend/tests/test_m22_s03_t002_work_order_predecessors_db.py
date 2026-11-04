"""M22.S03.T002 PostgreSQL integration coverage for routed operation gates."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.engine import URL

from app.crud import production_advanced as crud
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_advanced import (
    Routing,
    RoutingStep,
    WorkCenter,
    WorkCenterStatus,
    WorkCenterType,
    WorkOrder,
    WorkOrderStatus,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S03_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s03_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S03_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S03_T002_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S03.T002 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s03_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s03_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s03_t002_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name),
        name,
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="not-used", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _seed_routed_order(
    db, suffix: str, *, step_count: int = 3, include_work_orders: bool = True
):
    actor = User(
        email=f"m22-s03-t002-{suffix}@example.invalid",
        username=f"m22s03t002{suffix}",
        full_name=f"Synthetic M22 actor {suffix}",
        hashed_password="test-only",
    )
    product = Product(
        sku=f"M22-S03-T002-P-{suffix}",
        name=f"Synthetic routed product {suffix}",
        category=ProductCategory.FOOD,
        uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M22-S03-T002-W-{suffix}",
        name=f"Synthetic routed warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    db.add_all([actor, product, warehouse])
    await db.flush()
    recipe = Recipe(
        product_id=product.id,
        version="1",
        name=f"Synthetic routed recipe {suffix}",
        status=RecipeStatus.APPROVED,
        is_active=True,
    )
    db.add(recipe)
    await db.flush()
    parent = ProductionOrder(
        order_no=f"M22-S03-T002-PO-{suffix}",
        product_id=product.id,
        recipe_id=recipe.id,
        planned_quantity=10,
        uom="KG",
        status=ProductionOrderStatus.IN_PROGRESS,
        approved_by=actor.id,
        approved_at=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
        target_warehouse_id=warehouse.id,
        scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
    )
    routing = Routing(
        routing_id=f"M22-S03-T002-R-{suffix}",
        product_id=product.id,
        version=1,
        name=f"Synthetic sequential route {suffix}",
        is_active=True,
    )
    centers = [
        WorkCenter(
            work_center_id=f"M22-S03-T002-WC-{suffix}-{index}",
            name=f"Synthetic work center {suffix}-{index}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        for index in range(1, step_count + 1)
    ]
    db.add_all([parent, routing, *centers])
    await db.flush()
    steps = [
        RoutingStep(
            routing_id=routing.id,
            step_number=index,
            operation=f"Synthetic operation {index}",
            work_center_id=center.id,
            standard_time_minutes=10,
        )
        for index, center in enumerate(centers, start=1)
    ]
    db.add_all(steps)
    await db.flush()
    work_orders = [
        WorkOrder(
            work_order_id=f"M22-S03-T002-WO-{suffix}-{index}",
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=step.work_center_id,
            operation=step.operation,
            status=WorkOrderStatus.PLANNED,
            planned_quantity=10,
        )
        for index, step in enumerate(steps, start=1)
    ] if include_work_orders else []
    db.add_all(work_orders)
    await db.flush()
    return actor, parent, steps, work_orders


@pytest.mark.asyncio
async def test_every_prior_routing_step_must_be_complete_before_starting_successor():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        actor, _, _, work_orders = await _seed_routed_order(db, suffix)
        first, second, third = work_orders
        second.status = WorkOrderStatus.COMPLETED
        await db.commit()

        with pytest.raises(ValueError, match="Predecessor operation step 1 must be completed"):
            await crud.start_work_order(db, third.id, actor.id)

        first.status = WorkOrderStatus.COMPLETED
        await db.commit()
        started = await crud.start_work_order(db, third.id, actor.id)
        assert started.status == WorkOrderStatus.IN_PROGRESS
        await db.rollback()


@pytest.mark.asyncio
async def test_missing_or_cancelled_predecessor_cannot_be_treated_as_complete():
    _require_task_database()

    async with AsyncSessionLocal() as db:
        suffix = uuid4().hex[:20]
        actor, _, steps, work_orders = await _seed_routed_order(db, suffix, step_count=2)
        work_orders[0].status = WorkOrderStatus.CANCELLED
        await db.commit()
        with pytest.raises(ValueError, match="Predecessor operation step 1 has no active work order"):
            await crud.start_work_order(db, work_orders[1].id, actor.id)
        await db.rollback()

        suffix = uuid4().hex[:20]
        actor, parent, steps, work_orders = await _seed_routed_order(db, suffix, step_count=2)
        await db.delete(work_orders[0])
        await db.flush()
        with pytest.raises(ValueError, match="Predecessor operation step 1 has no active work order"):
            await crud.start_work_order(db, work_orders[1].id, actor.id)
        await db.rollback()


@pytest.mark.asyncio
async def test_completed_split_replacement_satisfies_its_routing_step():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        actor, _, steps, work_orders = await _seed_routed_order(db, suffix, step_count=2)
        source = work_orders[0]
        source.status = WorkOrderStatus.CANCELLED
        replacement = WorkOrder(
            work_order_id=f"M22-S03-T002-SPLIT-{suffix}",
            production_order_id=source.production_order_id,
            routing_step_id=steps[0].id,
            work_center_id=steps[0].work_center_id,
            operation=steps[0].operation,
            status=WorkOrderStatus.COMPLETED,
            planned_quantity=5,
            actual_quantity=5,
        )
        db.add(replacement)
        await db.commit()

        started = await crud.start_work_order(db, work_orders[1].id, actor.id)
        assert started.status == WorkOrderStatus.IN_PROGRESS
        await db.rollback()


@pytest.mark.asyncio
async def test_unrouted_work_order_keeps_the_existing_manual_start_behavior():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        actor, parent, steps, _ = await _seed_routed_order(
            db, suffix, step_count=1, include_work_orders=False
        )
        manual = WorkOrder(
            work_order_id=f"M22-S03-T002-MANUAL-{suffix}",
            production_order_id=parent.id,
            routing_step_id=None,
            work_center_id=steps[0].work_center_id,
            operation="Manual operation",
            status=WorkOrderStatus.PLANNED,
            planned_quantity=10,
        )
        db.add(manual)
        await db.flush()
        started = await crud.start_work_order(db, manual.id, actor.id)
        assert started.status == WorkOrderStatus.IN_PROGRESS
        await db.rollback()
