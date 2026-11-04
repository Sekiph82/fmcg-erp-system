"""M22.S02.T004 disposable PostgreSQL coverage for canonical rework lineage."""
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

from app.crud import production_advanced as production_crud
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure
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
from app.models.production_transition import ProductionTransitionEvent
from app.models.production_work_order_genealogy import ProductionWorkOrderGenealogy
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.production_service import _completed_work_order_output_quantity


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S02_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s02_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S02_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S02_T004_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S02.T004 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s02_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s02_t004_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s02_t004_short")
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
async def test_rework_is_linked_quantity_conserving_and_blocks_parent_close_until_done():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t004-{suffix}@example.invalid",
            username=f"m22s02t004{suffix}",
            full_name=f"Synthetic M22 rework actor {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T004-P-{suffix}",
            name=f"Synthetic rework product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        db.add_all([actor, product])
        await db.flush()
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic rework recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()
        parent = ProductionOrder(
            order_no=f"M22-T004-PO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=Decimal("10"),
            uom="KG",
            status=ProductionOrderStatus.IN_PROGRESS,
            approved_by=actor.id,
            approved_at=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            created_by=actor.id,
        )
        center = WorkCenter(
            work_center_id=f"M22-T004-WC-{suffix}",
            name=f"Synthetic rework center {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([parent, center])
        await db.flush()
        routing = Routing(
            routing_id=f"M22-T004-RT-{suffix}",
            product_id=product.id,
            version=1,
            is_active=True,
        )
        db.add(routing)
        await db.flush()
        early_step = RoutingStep(
            routing_id=routing.id,
            step_number=5,
            operation="Preparation",
            work_center_id=center.id,
            standard_time_minutes=5,
        )
        step = RoutingStep(
            routing_id=routing.id,
            step_number=10,
            operation="Filling",
            work_center_id=center.id,
            standard_time_minutes=10,
        )
        db.add_all([early_step, step])
        await db.flush()
        nonterminal_source = WorkOrder(
            work_order_id=f"M22-T004-EARLY-{suffix}",
            production_order_id=parent.id,
            routing_step_id=early_step.id,
            work_center_id=center.id,
            operation=early_step.operation,
            status=WorkOrderStatus.COMPLETED,
            planned_quantity=Decimal("1"),
            actual_quantity=Decimal("1"),
        )
        source = WorkOrder(
            work_order_id=f"M22-T004-SRC-{suffix}",
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=center.id,
            operation=step.operation,
            status=WorkOrderStatus.COMPLETED,
            planned_quantity=Decimal("10"),
            actual_quantity=Decimal("10"),
            start_time=datetime(2026, 11, 4, 9, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 4, 10, tzinfo=timezone.utc),
        )
        db.add_all([nonterminal_source, source])
        await db.flush()
        source_id = source.id
        nonterminal_source_id = nonterminal_source.id
        parent_id = parent.id
        await db.commit()

        manual_operation = WorkOrder(
            work_order_id=f"M22-T004-MANUAL-{suffix}",
            production_order_id=parent.id,
            routing_step_id=None,
            work_center_id=center.id,
            operation="Manual inspection",
            status=WorkOrderStatus.PLANNED,
            planned_quantity=Decimal("1"),
        )
        db.add(manual_operation)
        await db.flush()
        manual_operation_id = manual_operation.id
        await db.commit()
        with pytest.raises(ValueError, match="Routed and manual"):
            await production_crud.create_work_order_rework(
                db, source_id, Decimal("1.000"), "Correct mixed-route defect", actor.id
            )
        await db.rollback()
        manual_operation = await db.get(WorkOrder, manual_operation_id)
        manual_operation.status = WorkOrderStatus.CANCELLED
        await db.commit()

        with pytest.raises(ValueError, match="terminal routing operation"):
            await production_crud.create_work_order_rework(
                db, nonterminal_source_id, Decimal("1.000"), "Correct preparation defect", actor.id
            )
        await db.rollback()
        result = await production_crud.create_work_order_rework(
            db, source_id, Decimal("2.000"), "Seal inspection found a correctable defect", actor.id
        )
        await db.commit()

        source = await db.get(WorkOrder, source_id)
        result_id = result.id
        assert result.status == WorkOrderStatus.PLANNED
        assert result.planned_quantity == Decimal("2.000")
        assert result.actual_quantity is None
        assert result.rework_of_id == source.id
        assert result.rework_reason == "Seal inspection found a correctable defect"
        assert result.production_order_id == source.production_order_id == parent_id
        assert result.routing_step_id == source.routing_step_id
        assert result.work_center_id == source.work_center_id
        assert source.rework_quantity == Decimal("2.000")
        with pytest.raises(HTTPException) as unfinished:
            await _completed_work_order_output_quantity(db, await db.get(ProductionOrder, parent_id))
        assert unfinished.value.status_code == 422
        assert "Every active work order must be completed" in unfinished.value.detail

        edge = (await db.execute(
            select(ProductionWorkOrderGenealogy).where(
                ProductionWorkOrderGenealogy.action == "REWORK",
                ProductionWorkOrderGenealogy.source_work_order_id == source_id,
                ProductionWorkOrderGenealogy.result_work_order_id == result_id,
            )
        )).scalar_one()
        assert edge.transferred_quantity == Decimal("2.000")
        assert edge.actor_id == actor.id
        actions = set((await db.execute(
            select(ProductionTransitionEvent.action).where(
                ProductionTransitionEvent.parent_entity_id == parent_id,
                ProductionTransitionEvent.entity_id.in_([source_id, result_id]),
            )
        )).scalars())
        assert actions >= {"REWORK_QUANTITY_ASSIGNED", "REWORK_CREATED"}

        await production_crud.start_work_order(db, result_id, actor.id)
        await production_crud.complete_work_order(db, result_id, actor.id, Decimal("2.000"))
        await db.commit()
        assert await _completed_work_order_output_quantity(
            db, await db.get(ProductionOrder, parent_id)
        ) == Decimal("10.000")


@pytest.mark.asyncio
async def test_rework_cannot_exceed_unreworked_output_or_reopen_terminal_parent():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        actor = User(
            email=f"m22-s02-t004-guard-{suffix}@example.invalid",
            username=f"m22s02t004g{suffix}",
            full_name=f"Synthetic M22 rework guard {suffix}",
            hashed_password="test-only",
        )
        product = Product(
            sku=f"M22-S02-T004-GP-{suffix}",
            name=f"Synthetic rework guard product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        db.add_all([actor, product])
        await db.flush()
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic rework guard recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()
        parent = ProductionOrder(
            order_no=f"M22-T004-GPO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=Decimal("10"),
            uom="KG",
            status=ProductionOrderStatus.COMPLETED,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
            actual_quantity=Decimal("5"),
            created_by=actor.id,
        )
        center = WorkCenter(
            work_center_id=f"M22-T004-GWC-{suffix}",
            name=f"Synthetic rework guard center {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([parent, center])
        await db.flush()
        routing = Routing(
            routing_id=f"M22-T004-GRT-{suffix}",
            product_id=product.id,
            version=1,
            is_active=True,
        )
        db.add(routing)
        await db.flush()
        step = RoutingStep(
            routing_id=routing.id,
            step_number=10,
            operation="Filling",
            work_center_id=center.id,
            standard_time_minutes=10,
        )
        db.add(step)
        await db.flush()
        source = WorkOrder(
            work_order_id=f"M22-T004-GSRC-{suffix}",
            production_order_id=parent.id,
            routing_step_id=step.id,
            work_center_id=center.id,
            operation=step.operation,
            status=WorkOrderStatus.COMPLETED,
            planned_quantity=Decimal("10"),
            actual_quantity=Decimal("5"),
            rework_quantity=Decimal("4"),
        )
        db.add(source)
        await db.flush()
        source_id = source.id
        await db.commit()

        with pytest.raises(ValueError, match="cannot exceed"):
            await production_crud.create_work_order_rework(
                db, source_id, Decimal("2.000"), "A separate failed seal needs repair", actor.id
            )
        await db.rollback()
        with pytest.raises(ValueError, match="completed"):
            await production_crud.create_work_order_rework(
                db, source_id, Decimal("1.000"), "Attempt to reopen terminal order", actor.id
            )
        await db.rollback()
