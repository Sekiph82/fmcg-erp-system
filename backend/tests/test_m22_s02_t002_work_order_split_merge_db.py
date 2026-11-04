"""M22.S02.T002 PostgreSQL integration coverage for split/merge lineage."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.crud import production_advanced as crud
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
from app.models.production_work_order_genealogy import ProductionWorkOrderGenealogy
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S02_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s02_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S02_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S02_T002_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S02.T002 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s02_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s02_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s02_t002_short")
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
async def test_split_and_merge_conserve_quantity_and_keep_append_only_lineage():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t002-{suffix}@example.invalid",
            username=f"m22-s02-t002-{suffix}",
            full_name=f"Synthetic M22 actor {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T002-P-{suffix}",
            name=f"Synthetic split product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M22-S02-T002-W-{suffix}",
            name=f"Synthetic split warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, product, warehouse])
        await db.flush()

        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic split recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()

        parent = ProductionOrder(
            order_no=f"M22-S02-T002-PO-{suffix}",
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
        center = WorkCenter(
            work_center_id=f"M22-T002-C-{suffix}",
            name=f"Synthetic work center {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([parent, center])
        await db.flush()

        routing = Routing(
            routing_id=f"M22-T002-R-{suffix}",
            product_id=product.id,
            version=1,
            is_active=True,
        )
        db.add(routing)
        await db.flush()
        step = RoutingStep(
            routing_id=routing.id,
            step_number=10,
            operation="Mixing",
            work_center_id=center.id,
            standard_time_minutes=8,
        )
        db.add(step)
        await db.flush()

        source = WorkOrder(
            work_order_id=f"M22-T002-WO-{suffix}",
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=center.id,
            operation=step.operation,
            status=WorkOrderStatus.PLANNED,
            planned_quantity=10,
        )
        db.add(source)
        await db.flush()

        with pytest.raises(ValueError, match="exactly equal"):
            await crud.split_work_order(db, source.id, [4, 5], actor.id)
        assert source.status == WorkOrderStatus.PLANNED

        children = await crud.split_work_order(db, source.id, [4, 6], actor.id)
        assert source.status == WorkOrderStatus.CANCELLED
        assert [row.planned_quantity for row in children] == [4, 6]
        merged = await crud.merge_work_orders(db, [row.id for row in children], actor.id)
        assert all(row.status == WorkOrderStatus.CANCELLED for row in children)
        assert merged.status == WorkOrderStatus.PLANNED
        assert merged.planned_quantity == 10

        history = await crud.list_work_order_genealogy(db, source.id)
        assert len(history) == 2
        assert all(row.action == "SPLIT" for row in history)
        merge_edges = await db.execute(
            select(ProductionWorkOrderGenealogy).where(
                ProductionWorkOrderGenealogy.action == "MERGE",
                ProductionWorkOrderGenealogy.result_work_order_id == merged.id,
            )
        )
        merge_rows = list(merge_edges.scalars().all())
        assert len(merge_rows) == 2
        assert sum((row.transferred_quantity for row in merge_rows), start=0) == 10

        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.execute(
                    update(ProductionWorkOrderGenealogy)
                    .where(ProductionWorkOrderGenealogy.id == history[0].id)
                    .values(action="MERGE")
                )
                await db.flush()

        await db.commit()
