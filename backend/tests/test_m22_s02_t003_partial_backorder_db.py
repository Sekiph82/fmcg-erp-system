"""M22.S02.T003 PostgreSQL integration coverage for partial quantities/backorders."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.crud import production_advanced as production_crud
from app.models.inventory import Stock, StockType
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.production import (
    FinishedGoodsReceipt,
    MaterialConsumption,
    ProductionOrder,
    ProductionOrderStatus,
)
from app.models.production_advanced import (
    Routing,
    RoutingStep,
    WorkCenter,
    WorkCenterStatus,
    WorkCenterType,
    WorkOrder,
    WorkOrderStatus,
)
from app.models.production_transition import ProductionTransitionEvent
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.schemas.production import CompleteOrderRequest
from app.models.user import User
from app.services import production_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S02_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s02_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S02_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S02_T003_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S02.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s02_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s02_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s02_t003_short")
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
async def test_partial_backorder_preserves_order_context_and_transition_lineage():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t003-{suffix}@example.invalid",
            username=f"m22-s02-t003-{suffix}",
            full_name=f"Synthetic M22 actor {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T003-P-{suffix}",
            name=f"Synthetic backorder product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M22-S02-T003-W-{suffix}",
            name=f"Synthetic backorder warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic backorder recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()
        source = ProductionOrder(
            order_no=f"M22-S02-T003-PO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=10,
            uom="KG",
            batch_no=f"M22-T003-B-{suffix}",
            status=ProductionOrderStatus.COMPLETED,
            target_warehouse_id=warehouse.id,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            actual_quantity=Decimal("7.500"),
            created_by=actor.id,
        )
        db.add(source)
        await db.flush()

        backorder = await production_service._create_partial_backorder(
            db, source, Decimal("2.500"), actor.id
        )
        assert source.backordered_quantity == Decimal("2.500")
        assert backorder.backorder_of_id == source.id
        assert backorder.planned_quantity == Decimal("2.500")
        assert backorder.actual_quantity is None
        assert backorder.status == ProductionOrderStatus.PLANNED
        assert backorder.approved_by is None and backorder.approved_at is None
        assert backorder.product_id == source.product_id
        assert backorder.recipe_id == source.recipe_id
        assert backorder.batch_no == source.batch_no
        assert backorder.uom == source.uom
        assert backorder.source_warehouse_id == source.source_warehouse_id
        assert backorder.target_warehouse_id == source.target_warehouse_id

        child_event = await db.execute(
            select(ProductionTransitionEvent).where(
                ProductionTransitionEvent.entity_id == backorder.id,
                ProductionTransitionEvent.action == "BACKORDER_CREATED",
            )
        )
        assert child_event.scalar_one().parent_entity_id == source.id
        with pytest.raises(HTTPException) as duplicate:
            await production_service._create_partial_backorder(
                db, source, Decimal("2.500"), actor.id
            )
        assert duplicate.value.status_code == 422
        assert "already has a backorder" in duplicate.value.detail

        await db.commit()


@pytest.mark.asyncio
async def test_work_order_quantity_and_final_operation_reconcile_exactly():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t003-route-{suffix}@example.invalid",
            username=f"m22-s02-t003-route-{suffix}",
            full_name=f"Synthetic routing actor {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T003-RP-{suffix}",
            name=f"Synthetic routed product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M22-S02-T003-RW-{suffix}",
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
            order_no=f"M22-S02-T003-RPO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=10,
            uom="KG",
            status=ProductionOrderStatus.IN_PROGRESS,
            target_warehouse_id=warehouse.id,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            created_by=actor.id,
        )
        center = WorkCenter(
            work_center_id=f"M22-T003-RC-{suffix}",
            name=f"Synthetic routed center {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([parent, center])
        await db.flush()
        routing = Routing(
            routing_id=f"M22-T003-RT-{suffix}",
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
            standard_time_minutes=10,
        )
        db.add(step)
        await db.flush()
        work_order = WorkOrder(
            work_order_id=f"M22-T003-RWO-{suffix}",
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=center.id,
            operation=step.operation,
            status=WorkOrderStatus.IN_PROGRESS,
            planned_quantity=10,
        )
        db.add(work_order)
        await db.flush()

        with pytest.raises(ValueError, match="cannot exceed"):
            await production_crud.complete_work_order(
                db, work_order.id, actor.id, Decimal("10.001")
            )
        completed = await production_crud.complete_work_order(
            db, work_order.id, actor.id, Decimal("7.500")
        )
        assert completed.actual_quantity == Decimal("7.500")
        assert await production_service._completed_work_order_output_quantity(db, parent) == Decimal("7.500")
        await db.commit()
        with pytest.raises(HTTPException) as mismatch:
            await production_service.complete_order(
                db,
                await db.get(ProductionOrder, parent.id),
                CompleteOrderRequest(actual_quantity=Decimal("7.400"), consume_materials=False),
                actor.id,
            )
        assert mismatch.value.status_code == 422
        assert "must equal the completed output" in mismatch.value.detail
        await db.rollback()


@pytest.mark.asyncio
async def test_partial_order_completion_posts_actual_and_creates_unapproved_backorder_atomically():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t003-close-{suffix}@example.invalid",
            username=f"m22-s02-t003-close-{suffix}",
            full_name=f"Synthetic M22 closer {suffix}",
            hashed_password="test-only",
        )
        material = Material(
            code=f"M22-T003-CM-{suffix}",
            name=f"Synthetic close material {suffix}",
            material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
        )
        product = Product(
            sku=f"M22-T003-CP-{suffix}",
            name=f"Synthetic partial product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        raw_warehouse = Warehouse(
            code=f"M22-T003-CR-{suffix}",
            name=f"Synthetic raw warehouse {suffix}",
            warehouse_type=WarehouseType.RAW_MATERIAL,
        )
        finished_warehouse = Warehouse(
            code=f"M22-T003-CF-{suffix}",
            name=f"Synthetic finished warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, material, product, raw_warehouse, finished_warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic partial recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()
        order = ProductionOrder(
            order_no=f"M22-T003-CPO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=Decimal("10"),
            uom="KG",
            status=ProductionOrderStatus.IN_PROGRESS,
            source_warehouse_id=raw_warehouse.id,
            target_warehouse_id=finished_warehouse.id,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            actual_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            batch_no=f"M22-T003-CB-{suffix}",
            created_by=actor.id,
        )
        db.add_all([
            RecipeItem(
                recipe_id=recipe.id,
                material_id=material.id,
                line_no=1,
                quantity=Decimal("2"),
                unit="KG",
                loss_percentage=Decimal("0"),
            ),
            order,
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=raw_warehouse.id,
                material_id=material.id,
                quantity_on_hand=Decimal("10"),
                quantity_reserved=Decimal("0"),
                quantity_available=Decimal("10"),
                is_blocked=False,
            ),
        ])
        await db.flush()
        source_id = order.id
        source_order_no = order.order_no
        await db.commit()

        with pytest.raises(HTTPException) as overplanned:
            await production_service.complete_order(
                db,
                await db.get(ProductionOrder, source_id),
                CompleteOrderRequest(actual_quantity=Decimal("10.001"), consume_materials=True),
                actor.id,
            )
        assert overplanned.value.status_code == 422
        assert "cannot exceed" in overplanned.value.detail
        await db.rollback()

        await production_service.complete_order(
            db,
            await db.get(ProductionOrder, source_id),
            CompleteOrderRequest(actual_quantity=Decimal("7.500"), consume_materials=True),
            actor.id,
        )
        await db.commit()

        source = await db.get(ProductionOrder, source_id)
        child = (await db.execute(
            select(ProductionOrder).where(ProductionOrder.backorder_of_id == source_id)
        )).scalar_one()
        consumption = (await db.execute(
            select(MaterialConsumption).where(MaterialConsumption.production_order_id == source_id)
        )).scalar_one()
        receipt = (await db.execute(
            select(FinishedGoodsReceipt).where(FinishedGoodsReceipt.production_order_id == source_id)
        )).scalar_one()
        stock = (await db.execute(
            select(Stock).where(Stock.warehouse_id == raw_warehouse.id, Stock.material_id == material.id)
        )).scalar_one()
        events = list((await db.execute(
            select(ProductionTransitionEvent).where(
                ProductionTransitionEvent.parent_entity_id == source_id,
                ProductionTransitionEvent.action.in_(["COMPLETED_WITH_BACKORDER", "BACKORDER_CREATED"]),
            )
        )).scalars())

        assert source.status == ProductionOrderStatus.COMPLETED
        assert source.actual_quantity == Decimal("7.500")
        assert source.backordered_quantity == Decimal("2.500")
        assert child.order_no.startswith(f"{source_order_no}-BO-")
        assert child.planned_quantity == Decimal("2.500")
        assert child.status == ProductionOrderStatus.PLANNED
        assert child.actual_quantity is None
        assert child.approved_by is None and child.approved_at is None
        assert child.product_id == source.product_id and child.recipe_id == source.recipe_id
        assert child.batch_no == source.batch_no and child.uom == source.uom
        assert child.source_warehouse_id == source.source_warehouse_id
        assert child.target_warehouse_id == source.target_warehouse_id
        assert child.scheduled_start >= source.scheduled_end
        assert consumption.actual_quantity == Decimal("1.5000")
        assert receipt.quantity == Decimal("7.500")
        assert stock.quantity_on_hand == Decimal("8.500")
        assert {event.action for event in events} == {"COMPLETED_WITH_BACKORDER", "BACKORDER_CREATED"}
