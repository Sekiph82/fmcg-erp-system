"""M22.S02.T001 PostgreSQL integration coverage for routing generation/order."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.master import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_advanced import (
    Routing,
    RoutingStep,
    WorkCenter,
    WorkCenterStatus,
    WorkCenterType,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.crud import production_advanced as crud


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S02_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s02_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S02_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if os.environ.get("M22_S02_T001_DISPOSABLE_TEST_DATABASE") != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S02.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s02_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s02_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s02_t001_short")
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


@pytest.mark.asyncio
async def test_routing_generates_one_stable_work_order_per_step_in_sequence():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t001-{suffix}@example.invalid",
            username=f"m22-s02-t001-{suffix}",
            full_name=f"Synthetic M22 actor {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T001-P-{suffix}",
            name=f"Synthetic route product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M22-S02-T001-W-{suffix}",
            name=f"Synthetic route warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, product, warehouse])
        await db.flush()

        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic route recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()

        parent = ProductionOrder(
            order_no=f"M22-S02-T001-PO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=10,
            uom="KG",
            status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            created_by=actor.id,
        )
        db.add(parent)
        await db.flush()

        first_center = WorkCenter(
            work_center_id=f"M22-T001-A-{suffix}",
            name=f"Mixing center {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        second_center = WorkCenter(
            work_center_id=f"M22-T001-B-{suffix}",
            name=f"Filling center {suffix}",
            type=WorkCenterType.LINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([first_center, second_center])
        await db.flush()

        routing = Routing(
            routing_id=f"M22-T001-R-{suffix}",
            product_id=product.id,
            version=1,
            is_active=True,
        )
        db.add(routing)
        await db.flush()
        step_two = RoutingStep(
            routing_id=routing.id,
            step_number=20,
            operation="Filling",
            work_center_id=second_center.id,
            standard_time_minutes=12,
        )
        step_one = RoutingStep(
            routing_id=routing.id,
            step_number=10,
            operation="Mixing",
            work_center_id=first_center.id,
            standard_time_minutes=8,
        )
        db.add_all([step_two, step_one])
        await db.flush()

        generated = await crud.generate_work_orders_from_routing(
            db,
            parent.id,
            routing.id,
            actor.id,
        )
        assert [item.routing_step.step_number for item in generated] == [10, 20]
        assert [item.operation for item in generated] == ["Mixing", "Filling"]
        assert [item.work_center_id for item in generated] == [first_center.id, second_center.id]
        assert all(item.planned_quantity == parent.planned_quantity for item in generated)

        retried = await crud.generate_work_orders_from_routing(db, parent.id, routing.id, actor.id)
        assert [item.id for item in retried] == [item.id for item in generated]

        listed = await crud.list_work_orders(db, production_order_id=parent.id)
        assert [item.routing_step.step_number for item in listed] == [10, 20]

        with pytest.raises(ValueError, match="cannot be deleted"):
            await crud.delete_routing_step(db, step_one)

        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.delete(step_one)
                await db.flush()

        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.delete(routing)
                await db.flush()

        await db.rollback()
