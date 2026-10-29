"""M08.S03.T002 production/inventory atomicity tests on an isolated PostgreSQL DB."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine, get_db
from app.models.inventory import Lot, MovementType, Stock, StockMovement, StockType
from app.models.master import (
    Material, MaterialType, Product, ProductCategory, UnitOfMeasure,
    Warehouse, WarehouseType,
)
from app.models.production import (
    FinishedGoodsReceipt, MaterialConsumption, ProductionOrder, ProductionOrderStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.user import User
from app.schemas.production import CompleteOrderRequest
from app.schemas.inventory import StockEntryRequest
from app.services.inventory_locking import lot_identity, stock_identity
from app.services import inventory_service
from app.services import production_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M08_S03_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m08_s03_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M08_S03_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing writes: DATABASE_URL must match the exact passwordless loopback M08.S03.T002 database.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m08_s03_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m08_s03_t002_1123456789abcdef0123")
    assert not _is_task_database(safe, "fmcg_m08_s03_t002_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _seed_production(db, suffix: str):
    user = User(
        email=f"m08-t002-{suffix}@example.invalid",
        username=f"m08t002{suffix}",
        full_name=f"Synthetic M08 T002 actor {suffix}",
        hashed_password="synthetic-test-only-not-a-credential",
    )
    material = Material(
        code=f"M08-T002-M-{suffix}", name=f"Synthetic raw material {suffix}",
        material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
    )
    product = Product(
        sku=f"M08-T002-P-{suffix}", name=f"Synthetic finished product {suffix}",
        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
    )
    raw_warehouse = Warehouse(
        code=f"M08-T002-R-{suffix}", name=f"Synthetic raw warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
    )
    finished_warehouse = Warehouse(
        code=f"M08-T002-F-{suffix}", name=f"Synthetic finished warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    db.add_all([user, material, product, raw_warehouse, finished_warehouse])
    await db.flush()
    recipe = Recipe(
        product_id=product.id, version="1", name=f"Synthetic recipe {suffix}",
        status=RecipeStatus.APPROVED, is_active=True,
    )
    db.add(recipe)
    await db.flush()
    db.add(RecipeItem(
        recipe_id=recipe.id, material_id=material.id, line_no=1,
        quantity=Decimal("2"), unit="KG", loss_percentage=Decimal("0"),
    ))
    order = ProductionOrder(
        order_no=f"M08-T002-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
        planned_quantity=Decimal("4"), uom="KG", status=ProductionOrderStatus.IN_PROGRESS,
        target_warehouse_id=finished_warehouse.id, source_warehouse_id=raw_warehouse.id,
        scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
        actual_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        batch_no=f"M08-T002-BATCH-{suffix}", created_by=user.id,
    )
    raw_stock = Stock(
        stock_type=StockType.MATERIAL, warehouse_id=raw_warehouse.id, material_id=material.id,
        quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
        quantity_available=Decimal("10"), is_blocked=False,
    )
    db.add_all([order, raw_stock])
    await db.flush()
    return user, material, product, raw_warehouse, finished_warehouse, order, raw_stock


@pytest.mark.asyncio
async def test_production_completion_commits_inventory_ledger_and_order_once():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, material, product, raw_wh, finished_wh, order, raw_stock = await _seed_production(db, suffix)
        ids = (order.id, material.id, product.id, raw_wh.id, finished_wh.id, raw_stock.id, user.id)
        order_no = order.order_no
        await db.commit()

        await production_service.complete_order(
            db, await db.get(ProductionOrder, ids[0]),
            CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
        )
        await db.commit()

        persisted = await db.get(ProductionOrder, ids[0])
        raw_stock = await db.get(Stock, ids[5])
        fg_stock = (await db.execute(select(Stock).where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.warehouse_id == ids[4], Stock.product_id == ids[2],
        ))).scalar_one()
        consumption = (await db.execute(select(MaterialConsumption).where(
            MaterialConsumption.production_order_id == ids[0],
        ))).scalars().all()
        receipt = (await db.execute(select(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == ids[0],
        ))).scalars().all()
        movements = (await db.execute(select(StockMovement).where(
            StockMovement.reference_number == order_no,
        ))).scalars().all()
        assert persisted.status == ProductionOrderStatus.COMPLETED
        assert persisted.actual_quantity == Decimal("4.000")
        assert raw_stock.quantity_on_hand == Decimal("8.000")
        assert raw_stock.quantity_available == Decimal("8.000")
        assert fg_stock.quantity_on_hand == Decimal("4.000")
        assert len(consumption) == 1 and consumption[0].actual_quantity == Decimal("2.0000")
        assert len(receipt) == 1 and receipt[0].quantity == Decimal("4.000")
        assert len(movements) == 2
        issue = next(row for row in movements if row.movement_type == MovementType.ISSUE)
        fg_movement = next(row for row in movements if row.movement_type == MovementType.RECEIPT)
        assert issue.quantity == Decimal("2.0000") and issue.created_by_id == ids[6]
        assert fg_movement.quantity == Decimal("4.000") and fg_movement.created_by_id == ids[6]
        assert consumption[0].stock_movement_id == issue.id
        assert receipt[0].stock_movement_id == fg_movement.id

        with pytest.raises(HTTPException) as repeated:
            await production_service.complete_order(
                db, persisted,
                CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
            )
        assert repeated.value.status_code == 422
        await db.rollback()

    async with AsyncSessionLocal() as verify:
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 2
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == ids[0])) == 1
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == ids[0])) == 1
        assert (await verify.get(Stock, ids[5])).quantity_on_hand == Decimal("8.000")


@pytest.mark.asyncio
async def test_completion_failure_after_material_issue_rolls_back_all_production_inventory_effects(monkeypatch):
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        user, material, product, raw_wh, finished_wh, order, raw_stock = await _seed_production(seed, suffix)
        ids = (order.id, material.id, product.id, raw_wh.id, finished_wh.id, raw_stock.id, user.id)
        order_no = order.order_no
        await seed.commit()

    async def fail_during_finished_goods_receipt(**kwargs):
        raise RuntimeError("synthetic FG receipt failure after material issue")

    monkeypatch.setattr(production_service, "_receipt_finished_goods", fail_during_finished_goods_receipt)
    dependency = get_db()
    db = await anext(dependency)
    try:
        try:
            await production_service.complete_order(
                db, await db.get(ProductionOrder, ids[0]),
                CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
            )
            pytest.fail("synthetic finished-goods failure was not raised")
        except RuntimeError as failure:
            assert "after material issue" in str(failure)
            with pytest.raises(RuntimeError, match="after material issue"):
                await dependency.athrow(failure)
    finally:
        await dependency.aclose()

    async with AsyncSessionLocal() as verify:
        order = await verify.get(ProductionOrder, ids[0])
        raw_stock = await verify.get(Stock, ids[5])
        assert order.status == ProductionOrderStatus.IN_PROGRESS
        assert order.actual_quantity is None and order.actual_end is None
        assert raw_stock.quantity_on_hand == Decimal("10.000")
        assert raw_stock.quantity_available == Decimal("10.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 0
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == ids[0])) == 0
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == ids[0])) == 0
        assert await verify.scalar(select(func.count(Stock.id)).where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.warehouse_id == ids[4], Stock.product_id == ids[2],
        )) == 0


@pytest.mark.asyncio
async def test_concurrent_completion_creates_one_consumption_and_one_finished_receipt():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        user, _, _, _, _, order, _ = await _seed_production(seed, suffix)
        order_id, user_id = order.id, user.id
        order_no = order.order_no
        await seed.commit()

    async def attempt_completion():
        async with AsyncSessionLocal() as db:
            order = await db.get(ProductionOrder, order_id)
            try:
                await production_service.complete_order(
                    db, order, CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), user_id,
                )
                await db.commit()
                return "completed"
            except HTTPException as error:
                await db.rollback()
                return error

    results = await asyncio.gather(attempt_completion(), attempt_completion())
    assert results.count("completed") == 1
    failures = [result for result in results if isinstance(result, HTTPException)]
    assert len(failures) == 1 and failures[0].status_code == 422
    async with AsyncSessionLocal() as verify:
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 2
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == order_id)) == 1
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == order_id)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("lot_managed", [True, False])
async def test_production_receipt_and_stock_entry_serialize_shared_missing_lot_and_stock(monkeypatch, lot_managed):
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        user, _, product, raw_wh, finished_wh, order, raw_stock = await _seed_production(seed, suffix)
        order_id, user_id = order.id, user.id
        order_no = order.order_no
        product_id, raw_stock_id = product.id, raw_stock.id
        warehouse_id = finished_wh.id
        lot_number = order.batch_no if lot_managed else None
        if not lot_managed:
            order.batch_no = None
        await seed.commit()

    first_has_lock = asyncio.Event()
    allow_first_to_continue = asyncio.Event()
    second_is_waiting = asyncio.Event()
    second_acquired = asyncio.Event()
    second_pid: dict[str, int] = {}
    identity = (
        lot_identity(product_id=product_id, lot_number=lot_number)
        if lot_managed
        else stock_identity(
            stock_type=StockType.PRODUCT,
            warehouse_id=warehouse_id,
            product_id=product_id,
            lot_id=None,
        )
    )
    acquire_lock = production_service.lock_inventory_identity

    async def coordinated_lock(db, key):
        if key != identity:
            await acquire_lock(db, key)
            return
        owner = db.info.get("m08_t002_lock_owner")
        if owner == "production":
            await acquire_lock(db, key)
            first_has_lock.set()
            await allow_first_to_continue.wait()
        elif owner == "stock-entry":
            second_is_waiting.set()
            await acquire_lock(db, key)
            second_acquired.set()
        else:
            await acquire_lock(db, key)

    monkeypatch.setattr(production_service, "lock_inventory_identity", coordinated_lock)
    monkeypatch.setattr(inventory_service, "lock_inventory_identity", coordinated_lock)

    async def complete_production():
        async with AsyncSessionLocal() as db:
            db.info["m08_t002_lock_owner"] = "production"
            await production_service.complete_order(
                db,
                await db.get(ProductionOrder, order_id),
                CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True),
                user_id,
            )
            await db.commit()

    async def receive_stock_entry():
        async with AsyncSessionLocal() as db:
            db.info["m08_t002_lock_owner"] = "stock-entry"
            second_pid["pid"] = await db.scalar(select(func.pg_backend_pid()))
            await inventory_service.stock_entry(
                db,
                StockEntryRequest(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=Decimal("5"),
                    lot_number=lot_number,
                    reference=f"M08-T002-STOCK-ENTRY-{suffix}",
                ),
                user_id,
            )
            await db.commit()

    production_task = asyncio.create_task(complete_production())
    stock_entry_task = None
    try:
        await asyncio.wait_for(first_has_lock.wait(), timeout=10)
        stock_entry_task = asyncio.create_task(receive_stock_entry())
        await asyncio.wait_for(second_is_waiting.wait(), timeout=10)

        observed_wait = False
        for _ in range(200):
            async with AsyncSessionLocal() as observer:
                wait_result = await observer.execute(
                    text("SELECT wait_event_type, wait_event FROM pg_stat_activity WHERE pid = :pid"),
                    {"pid": second_pid.get("pid", -1)},
                )
                wait_type = wait_result.first()
            if wait_type and wait_type[0] == "Lock" and wait_type[1] == "advisory":
                observed_wait = True
                break
            await asyncio.sleep(0.025)
        assert observed_wait, "second writer did not block on the held logical-lot advisory lock"
    finally:
        allow_first_to_continue.set()
        pending = [production_task]
        if stock_entry_task is not None:
            pending.append(stock_entry_task)
        await asyncio.gather(*pending, return_exceptions=True)
    assert second_acquired.is_set()

    async with AsyncSessionLocal() as verify:
        lot_rows = (await verify.execute(select(Lot).where(
            Lot.product_id == product_id, Lot.lot_number == lot_number,
        ))).scalars().all()
        fg_stock_rows = (await verify.execute(select(Stock).where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.warehouse_id == warehouse_id,
            Stock.product_id == product_id,
            Stock.lot_id == (lot_rows[0].id if lot_rows else None),
        ))).scalars().all()
        assert len(lot_rows) == (1 if lot_managed else 0)
        assert len(fg_stock_rows) == 1
        assert fg_stock_rows[0].quantity_on_hand == Decimal("9.000")
        assert (await verify.get(Stock, raw_stock_id)).quantity_on_hand == Decimal("8.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(
            StockMovement.reference_number.in_((order_no, f"M08-T002-STOCK-ENTRY-{suffix}")),
        )) == 3
