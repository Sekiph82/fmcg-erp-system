"""M22.S04.T001 PostgreSQL coverage for parent lifecycle and transition history."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from app.db.session import AsyncSessionLocal, engine
from app.models.master import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_transition import ProductionTransitionEvent
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.production_service import approve_order, release_order


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S04_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s04_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S04_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S04_T001_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S04.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s04_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s04_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s04_t001_short")
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


async def _seed_planned_order(db, suffix: str):
    creator = User(
        email=f"m22-s04-t001-creator-{suffix}@example.invalid",
        username=f"m22s04t001c{suffix}",
        full_name=f"Synthetic order creator {suffix}",
        hashed_password="test-only",
    )
    approver = User(
        email=f"m22-s04-t001-approver-{suffix}@example.invalid",
        username=f"m22s04t001a{suffix}",
        full_name=f"Synthetic order approver {suffix}",
        hashed_password="test-only",
    )
    product = Product(
        sku=f"M22-S04-T001-P-{suffix}",
        name=f"Synthetic lifecycle product {suffix}",
        category=ProductCategory.FOOD,
        uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M22-S04-T001-W-{suffix}",
        name=f"Synthetic lifecycle warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    db.add_all([creator, approver, product, warehouse])
    await db.flush()
    recipe = Recipe(
        product_id=product.id,
        version="1",
        name=f"Synthetic lifecycle recipe {suffix}",
        status=RecipeStatus.APPROVED,
        is_active=True,
    )
    db.add(recipe)
    await db.flush()
    order = ProductionOrder(
        order_no=f"M22-S04-T001-PO-{suffix}",
        product_id=product.id,
        recipe_id=recipe.id,
        planned_quantity=Decimal("10"),
        uom="KG",
        status=ProductionOrderStatus.PLANNED,
        target_warehouse_id=warehouse.id,
        scheduled_start=datetime(2026, 11, 10, 8, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 11, 10, 16, tzinfo=timezone.utc),
        created_by=creator.id,
    )
    db.add(order)
    await db.flush()
    return order, creator, approver


@pytest.mark.asyncio
async def test_order_approval_release_history_is_attributed_ordered_and_append_only():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        async with db.begin():
            order, creator, approver = await _seed_planned_order(db, suffix)

            with pytest.raises(HTTPException) as self_approval:
                await approve_order(db, order, creator.id)
            assert self_approval.value.detail == "The order creator cannot approve the same production order."
            assert order.approved_by is None

            approved = await approve_order(db, order, approver.id)
            assert approved.status == ProductionOrderStatus.PLANNED
            assert approved.approved_by == approver.id
            assert approved.approved_at is not None

            with pytest.raises(HTTPException) as repeated_approval:
                await approve_order(db, approved, creator.id)
            assert repeated_approval.value.detail == "Production order approval has already been recorded."

            released = await release_order(db, approved, approver.id)
            assert released.status == ProductionOrderStatus.RELEASED

            events = list((await db.scalars(
                select(ProductionTransitionEvent)
                .where(
                    ProductionTransitionEvent.entity_type == "PRODUCTION_ORDER",
                    ProductionTransitionEvent.entity_id == order.id,
                )
                .order_by(ProductionTransitionEvent.event_seq)
            )).all())
            assert [event.action for event in events] == ["APPROVED", "RELEASED"]
            assert [event.event_seq for event in events] == sorted(event.event_seq for event in events)
            assert all(event.actor_id == approver.id for event in events)
            assert all(event.actor_label == str(approver.id) for event in events)
            assert [(event.from_status, event.to_status) for event in events] == [
                ("PLANNED", "PLANNED"),
                ("PLANNED", "RELEASED"),
            ]

            with pytest.raises(DBAPIError, match="Production transition history is append-only"):
                async with db.begin_nested():
                    await db.execute(
                        update(ProductionTransitionEvent)
                        .where(ProductionTransitionEvent.id == events[0].id)
                        .values(action="FORGED")
                    )

            with pytest.raises(DBAPIError, match="Production transition history is append-only"):
                async with db.begin_nested():
                    await db.execute(
                        delete(ProductionTransitionEvent).where(
                            ProductionTransitionEvent.id == events[0].id
                        )
                    )
