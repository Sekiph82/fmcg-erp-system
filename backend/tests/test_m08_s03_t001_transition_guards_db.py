"""M08.S03.T001 guarded PostgreSQL tests for production state transitions."""
from __future__ import annotations

import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import DowntimeLog, DowntimeReason, ProductionOrder, ProductionOrderStatus
from app.models.production_execution import ExecWorkOrder, ProdExecOrder
from app.models.recipe import Recipe, RecipeStatus
from app.services import production_service
from app.services import production_execution_service as service


pytestmark = pytest.mark.skipif(
    os.environ.get("M08_S03_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m08_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M08_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M08_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M08_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M08.S03.T001 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m08_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m08_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m08_s03_t001_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="not-used", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _order(db, suffix: str, status: str = "IN_PROGRESS") -> ProdExecOrder:
    order = ProdExecOrder(
        order_no=f"M08-T001-PO-{suffix}",
        planned_qty=Decimal("10"),
        uom="KG",
        status=status,
    )
    db.add(order)
    await db.flush()
    return order


async def _work_order(
    db,
    parent: ProdExecOrder,
    suffix: str,
    *,
    status: str = "PENDING",
    dependency_work_order_id=None,
    step_sequence: int = 1,
) -> ExecWorkOrder:
    work_order = ExecWorkOrder(
        production_order_id=parent.id,
        step_sequence=step_sequence,
        step_name=f"Synthetic step {suffix}",
        planned_qty=Decimal("10"),
        status=status,
        dependency_work_order_id=dependency_work_order_id,
    )
    db.add(work_order)
    await db.flush()
    return work_order


async def _seed_order_and_work_order(*, order_status="IN_PROGRESS", work_status="PENDING"):
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        order = await _order(db, suffix, order_status)
        work_order = await _work_order(db, order, suffix, status=work_status)
        await db.commit()
        return order.id, work_order.id


async def _seed_core_production_order(db, suffix: str, status: ProductionOrderStatus):
    product = Product(
        sku=f"M08-T001-CORE-P-{suffix}", name=f"Synthetic core product {suffix}",
        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M08-T001-CORE-W-{suffix}", name=f"Synthetic core warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    db.add_all([product, warehouse])
    await db.flush()
    recipe = Recipe(
        product_id=product.id, version="1", name=f"Synthetic core recipe {suffix}",
        status=RecipeStatus.APPROVED, is_active=True,
    )
    db.add(recipe)
    await db.flush()
    order = ProductionOrder(
        order_no=f"M08-T001-CORE-PO-{suffix}",
        product_id=product.id,
        recipe_id=recipe.id,
        planned_quantity=Decimal("10"),
        uom="KG",
        status=status,
        target_warehouse_id=warehouse.id,
        scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 10, 30, tzinfo=timezone.utc),
    )
    db.add(order)
    await db.flush()
    return order


@pytest.mark.asyncio
async def test_order_patch_rejects_engine_owned_lifecycle_fields():
    order_id, _ = await _seed_order_and_work_order()
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="status"):
            await service.update_order(db, order_id, {"status": "COMPLETED"})
        with pytest.raises(ValueError, match="completed_qty"):
            await service.update_order(db, order_id, {"completed_qty": Decimal("10")})
        await db.rollback()
        order = await service.get_order(db, order_id)
        assert order.status == "IN_PROGRESS"
        assert order.completed_qty == 0


@pytest.mark.asyncio
async def test_work_order_patch_rejects_engine_owned_state_and_started_rows_are_immutable():
    _, work_order_id = await _seed_order_and_work_order(work_status="PENDING")
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="status"):
            await service.update_work_order(db, work_order_id, {"status": "COMPLETED"})
        await db.rollback()

    async with AsyncSessionLocal() as db:
        work_order = await db.get(ExecWorkOrder, work_order_id)
        work_order.status = "IN_PROGRESS"
        await db.commit()
        with pytest.raises(ValueError, match="after production starts"):
            await service.update_work_order(db, work_order_id, {"step_name": "Changed after start"})
        await db.rollback()


@pytest.mark.asyncio
async def test_work_order_cannot_complete_before_start_or_complete_twice():
    _, work_order_id = await _seed_order_and_work_order(work_status="READY")
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            await service.complete_work_order(
                db, work_order_id, Decimal("8"), Decimal("1"), Decimal("0"),
                None, None, None, None, None, None, None,
            )
        await db.rollback()

    async with AsyncSessionLocal() as db:
        work_order = await db.get(ExecWorkOrder, work_order_id)
        work_order.status = "IN_PROGRESS"
        await db.commit()
        completed = await service.complete_work_order(
            db, work_order_id, Decimal("8"), Decimal("1"), Decimal("0"),
            None, None, None, None, None, None, None,
        )
        assert completed.status == "COMPLETED"
        completed_at = completed.completed_at
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            await service.complete_work_order(
                db, work_order_id, Decimal("7"), Decimal("2"), Decimal("0"),
                None, None, None, None, None, None, None,
            )
        await db.rollback()
        persisted = await db.get(ExecWorkOrder, work_order_id)
        assert persisted.status == "COMPLETED"
        assert persisted.completed_qty == Decimal("8")
        assert persisted.completed_at == completed_at


@pytest.mark.asyncio
async def test_work_order_start_requires_parent_running_and_completed_predecessor():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        parent = await _order(db, suffix, "RELEASED")
        predecessor = await _work_order(db, parent, f"{suffix}-previous", status="IN_PROGRESS")
        current = await _work_order(
            db, parent, f"{suffix}-current", status="PENDING",
            dependency_work_order_id=predecessor.id,
            step_sequence=2,
        )
        parent_id = parent.id
        predecessor_id = predecessor.id
        current_id = current.id
        await db.commit()
        with pytest.raises(ValueError, match="Production order must be IN_PROGRESS"):
            await service.start_work_order(db, current_id)
        await db.rollback()
        await db.execute(
            update(ProdExecOrder)
            .where(ProdExecOrder.id == parent_id)
            .values(status="IN_PROGRESS")
        )
        await db.commit()
        with pytest.raises(ValueError, match="Preceding work order must be completed"):
            await service.start_work_order(db, current_id)
        await db.rollback()
        predecessor = await db.get(ExecWorkOrder, predecessor_id)
        predecessor.status = "COMPLETED"
        await db.commit()
        started = await service.start_work_order(db, current_id)
        assert started.status == "IN_PROGRESS"
        assert started.started_at is not None


@pytest.mark.asyncio
async def test_dependency_from_another_production_order_is_rejected():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        parent = await _order(db, f"{suffix}-parent")
        foreign_parent = await _order(db, f"{suffix}-foreign")
        predecessor = await _work_order(db, foreign_parent, f"{suffix}-foreign-step", status="COMPLETED")
        current = await _work_order(
            db, parent, f"{suffix}-current", status="PENDING",
            dependency_work_order_id=predecessor.id,
            step_sequence=2,
        )
        current_id = current.id
        await db.commit()
        with pytest.raises(ValueError, match="Preceding work order must be completed"):
            await service.start_work_order(db, current_id)
        await db.rollback()
        persisted = await db.get(ExecWorkOrder, current_id)
        assert persisted.status == "PENDING"


@pytest.mark.asyncio
async def test_work_order_dependency_must_point_to_an_earlier_step():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        parent = await _order(db, suffix, "PLANNED")
        current = await _work_order(db, parent, f"{suffix}-current", status="PENDING", step_sequence=1)
        later = await _work_order(db, parent, f"{suffix}-later", status="PENDING", step_sequence=2)
        current_id, later_id = current.id, later.id
        await db.commit()
        with pytest.raises(ValueError, match="earlier step"):
            await service.update_work_order(db, current_id, {"dependency_work_order_id": later_id})
        await db.rollback()
        persisted = await db.get(ExecWorkOrder, current_id)
        assert persisted.dependency_work_order_id is None


@pytest.mark.asyncio
async def test_work_order_dependency_update_rejects_cycle_even_when_sequence_is_changed():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        parent = await _order(db, suffix, "PLANNED")
        first = await _work_order(db, parent, f"{suffix}-first", step_sequence=1)
        second = await _work_order(
            db, parent, f"{suffix}-second", step_sequence=2,
            dependency_work_order_id=first.id,
        )
        first_id, second_id = first.id, second.id
        await db.commit()

        with pytest.raises(ValueError, match="cannot contain a cycle"):
            await service.update_work_order(
                db,
                first_id,
                {"step_sequence": 3, "dependency_work_order_id": second_id},
            )
        await db.rollback()
        persisted = await db.get(ExecWorkOrder, first_id)
        assert persisted.step_sequence == 1
        assert persisted.dependency_work_order_id is None


@pytest.mark.asyncio
async def test_work_order_cannot_be_added_after_parent_starts_or_with_later_dependency():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        active_parent = await _order(db, f"{suffix}-active", "IN_PROGRESS")
        planned_parent = await _order(db, f"{suffix}-planned", "PLANNED")
        later = await _work_order(db, planned_parent, f"{suffix}-later", status="PENDING", step_sequence=3)
        active_parent_id = active_parent.id
        planned_parent_id = planned_parent.id
        later_id = later.id
        await db.commit()
        with pytest.raises(ValueError, match="after production starts"):
            await service.add_work_order(
                db, active_parent_id,
                {"step_name": "Too late", "step_sequence": 1, "planned_qty": Decimal("10")},
            )
        await db.rollback()
        with pytest.raises(ValueError, match="earlier step"):
            await service.add_work_order(
                db, planned_parent_id,
                {
                    "step_name": "Cannot depend on a later step",
                    "step_sequence": 2,
                    "planned_qty": Decimal("10"),
                    "dependency_work_order_id": later_id,
                },
            )


@pytest.mark.asyncio
async def test_concurrent_duplicate_release_allows_only_one_transition():
    order_id, _ = await _seed_order_and_work_order(order_status="DRAFT")

    async def attempt_release():
        async with AsyncSessionLocal() as db:
            try:
                return await service.release_order(db, order_id)
            except ValueError as exc:
                await db.rollback()
                return exc

    results = await asyncio.gather(attempt_release(), attempt_release())
    assert sum(not isinstance(result, ValueError) for result in results) == 1
    assert sum(isinstance(result, ValueError) for result in results) == 1
    async with AsyncSessionLocal() as db:
        persisted = await service.get_order(db, order_id)
        assert persisted.status == "RELEASED"


@pytest.mark.asyncio
async def test_completed_or_terminal_order_cannot_be_cancelled_again():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        completed = await _order(db, f"{suffix}-completed", "COMPLETED")
        closed = await _order(db, f"{suffix}-closed", "CLOSED")
        cancelled = await _order(db, f"{suffix}-cancelled", "CANCELLED")
        completed_id, closed_id, cancelled_id = completed.id, closed.id, cancelled.id
        await db.commit()
        for order_id in (completed_id, closed_id, cancelled_id):
            with pytest.raises(ValueError, match="cannot be cancelled"):
                await service.cancel_order(db, order_id)
            await db.rollback()
        assert (await service.get_order(db, completed_id)).status == "COMPLETED"
        assert (await service.get_order(db, closed_id)).status == "CLOSED"
        assert (await service.get_order(db, cancelled_id)).status == "CANCELLED"


@pytest.mark.asyncio
async def test_merge_rejects_one_or_repeated_order_before_writing():
    order_id, _ = await _seed_order_and_work_order(order_status="PLANNED")
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="two distinct"):
            await service.merge_orders(db, [order_id], "not a merge", uuid4())
        with pytest.raises(ValueError, match="two distinct"):
            await service.merge_orders(db, [order_id, order_id], "duplicate", uuid4())
        await db.rollback()
        order = await service.get_order(db, order_id)
        assert order.status == "PLANNED"


@pytest.mark.asyncio
async def test_split_requires_two_positive_quantities_and_cannot_repeat():
    order_id, _ = await _seed_order_and_work_order(order_status="PLANNED")
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="at least two positive"):
            await service.split_order(db, order_id, [Decimal("10")], "one child", uuid4())
        with pytest.raises(ValueError, match="at least two positive"):
            await service.split_order(db, order_id, [Decimal("0"), Decimal("10")], "zero child", uuid4())
        await db.rollback()
        children = await service.split_order(
            db, order_id, [Decimal("4"), Decimal("6")], "synthetic split", uuid4()
        )
        assert len(children) == 2
        assert sum(child.planned_qty for child in children) == Decimal("10")
        with pytest.raises(ValueError, match="Only DRAFT/PLANNED/RELEASED"):
            await service.split_order(db, order_id, [Decimal("5"), Decimal("5")], "repeat", uuid4())


@pytest.mark.asyncio
async def test_core_production_order_terminal_cancel_is_rejected_and_active_cancel_is_one_shot():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        completed = await _seed_core_production_order(
            db, f"{suffix}-completed", ProductionOrderStatus.COMPLETED
        )
        cancelled = await _seed_core_production_order(
            db, f"{suffix}-cancelled", ProductionOrderStatus.CANCELLED
        )
        active = await _seed_core_production_order(
            db, f"{suffix}-active", ProductionOrderStatus.IN_PROGRESS
        )
        completed_id, cancelled_id, active_id = completed.id, cancelled.id, active.id
        downtime = DowntimeLog(
            production_order_id=active_id,
            reason=DowntimeReason.MATERIAL_SHORTAGE,
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(downtime)
        await db.flush()
        downtime_id = downtime.id
        await db.commit()
        for order_id in (completed_id, cancelled_id):
            with pytest.raises(HTTPException) as denied:
                await production_service.cancel_order(db, await db.get(ProductionOrder, order_id))
            assert getattr(denied.value, "status_code", None) == 422
            await db.rollback()
        result = await production_service.cancel_order(db, await db.get(ProductionOrder, active_id))
        assert result.status == ProductionOrderStatus.CANCELLED
        await db.commit()
        persisted_downtime = await db.get(DowntimeLog, downtime_id)
        assert persisted_downtime.end_time is not None
        assert persisted_downtime.duration_minutes is not None
        assert persisted_downtime.duration_minutes >= 0
        with pytest.raises(HTTPException) as repeated:
            await production_service.cancel_order(db, await db.get(ProductionOrder, active_id))
        assert getattr(repeated.value, "status_code", None) == 422


@pytest.mark.asyncio
async def test_core_duplicate_release_serializes_on_the_order_row():
    _require_task_database()
    suffix = uuid4().hex[:18]
    async with AsyncSessionLocal() as db:
        order = await _seed_core_production_order(db, suffix, ProductionOrderStatus.PLANNED)
        order_id = order.id
        await db.commit()

    async def attempt_release():
        async with AsyncSessionLocal() as db:
            order = await db.get(ProductionOrder, order_id)
            try:
                result = await production_service.release_order(db, order)
                await db.commit()
                return result
            except HTTPException as exc:
                await db.rollback()
                return exc

    results = await asyncio.gather(attempt_release(), attempt_release())
    assert sum(not isinstance(result, HTTPException) for result in results) == 1
    assert sum(getattr(result, "status_code", None) == 422 for result in results) == 1
    async with AsyncSessionLocal() as db:
        persisted = await db.get(ProductionOrder, order_id)
        assert persisted.status == ProductionOrderStatus.RELEASED
