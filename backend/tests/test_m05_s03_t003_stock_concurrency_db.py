"""M05.S03.T003: disposable PostgreSQL negative-stock and concurrent-retry tests."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.finance import (
    AccountType, AccountingPeriod, ChartOfAccount, InventoryAccountMapping, PeriodStatus,
)
from app.models.inventory import MovementType, Stock, StockMovement, StockType
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.procurement import GoodsReceipt, GRNLine, GRNStatus, POStatus, POLine, PurchaseOrder
from app.models.production import (
    FinishedGoodsReceipt,
    MaterialConsumption,
    ProductionOrder,
    ProductionOrderStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.user import User
from app.schemas.inventory import StockIssueRequest
from app.schemas.production import CompleteOrderRequest
from app.services import inventory_service, production_service, procurement_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M05_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m05_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M05_S03_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M05_S03_T003_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M05_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M05.S03.T003 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m05_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m05_s03_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m05_s03_t003_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="synthetic-only", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _wait_until_backend_is_blocked(db, pid: int) -> None:
    for _ in range(100):
        waiting = await db.scalar(
            text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid AND datname = current_database()"),
            {"pid": pid},
        )
        if waiting == "Lock":
            return
        await asyncio.sleep(0.05)
    pytest.fail(f"PostgreSQL backend {pid} never entered a lock wait")


async def _base(db, suffix: str):
    user = User(
        email=f"m05-t003-{suffix}@example.invalid", username=f"m05t003{suffix}",
        full_name=f"Synthetic M05 T003 actor {suffix}",
        hashed_password="synthetic-test-only-not-a-credential",
    )
    supplier = Supplier(code=f"M05-T003-S-{suffix}", name=f"Synthetic supplier {suffix}")
    material = Material(
        code=f"M05-T003-M-{suffix}", name=f"Synthetic material {suffix}",
        material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
    )
    product = Product(
        sku=f"M05-T003-P-{suffix}", name=f"Synthetic product {suffix}",
        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
    )
    raw_wh = Warehouse(code=f"M05-T003-R-{suffix}", name=f"Synthetic raw warehouse {suffix}", warehouse_type=WarehouseType.RAW_MATERIAL)
    fg_wh = Warehouse(code=f"M05-T003-F-{suffix}", name=f"Synthetic finished warehouse {suffix}", warehouse_type=WarehouseType.FINISHED_GOODS)
    db.add_all([user, supplier, material, product, raw_wh, fg_wh])
    await db.flush()
    return user, supplier, material, product, raw_wh, fg_wh


async def _seed_grn(db, suffix: str):
    user, supplier, material, _, raw_wh, _ = await _base(db, suffix)
    company = Company(
        name=f"Synthetic M05 T003 Company {suffix}", short_code=f"M3{suffix[:8].upper()}",
        country="Kenya", base_currency="KES",
    )
    inventory_account = ChartOfAccount(
        code=f"M3I{suffix[:8].upper()}", name="Synthetic inventory", account_type=AccountType.ASSET,
    )
    grni_account = ChartOfAccount(
        code=f"M3G{suffix[:8].upper()}", name="Synthetic GRNI", account_type=AccountType.LIABILITY,
    )
    db.add_all([company, inventory_account, grni_account])
    await db.flush()
    raw_wh.company_id = company.id
    db.add(InventoryAccountMapping(
        material_id=material.id, stock_type="MATERIAL", valuation_method="FIFO",
        inventory_account_id=inventory_account.id, grni_account_id=grni_account.id, is_active=True,
    ))
    if not await db.scalar(select(AccountingPeriod.id).where(AccountingPeriod.period_ym == "2026-10")):
        db.add(AccountingPeriod(
            period_ym="2026-10", period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
            status=PeriodStatus.OPEN, notes="Synthetic receipt-posting test period.",
        ))
    po = PurchaseOrder(
        po_no=f"M05-T003-PO-{suffix}", supplier_id=supplier.id,
        company_id=company.id, currency="KES", exchange_rate=Decimal("1"),
        order_date=date(2026, 10, 29), expected_delivery_date=date(2026, 10, 30),
        status=POStatus.ORDERED, created_by_id=user.id,
    )
    db.add(po)
    await db.flush()
    po_line = POLine(po_id=po.id, line_no=1, material_id=material.id, ordered_quantity=Decimal("8"), received_quantity=Decimal("0"), unit="KG", unit_price=Decimal("25"))
    grn = GoodsReceipt(
        grn_no=f"M05-T003-GRN-{suffix}", po_id=po.id,
        company_id=company.id,
        received_date=date(2026, 10, 29), received_by_id=user.id,
        warehouse_id=raw_wh.id, status=GRNStatus.DRAFT,
    )
    db.add_all([po_line, grn])
    await db.flush()
    line = GRNLine(
        grn_id=grn.id, po_line_id=po_line.id, material_id=material.id,
        received_quantity=Decimal("4"), accepted_quantity=Decimal("4"), rejected_quantity=Decimal("0"), unit="KG",
    )
    db.add(line)
    await db.flush()
    return user, material, raw_wh, po, po_line, grn, line


async def _seed_production(db, suffix: str, material_quantity: Decimal, stock_quantity: Decimal):
    user, _, material, product, raw_wh, fg_wh = await _base(db, suffix)
    recipe = Recipe(product_id=product.id, version="1", name=f"Synthetic recipe {suffix}", status=RecipeStatus.APPROVED, is_active=True)
    db.add(recipe)
    await db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, material_id=material.id, line_no=1, quantity=material_quantity, unit="KG", loss_percentage=Decimal("0")))
    order = ProductionOrder(
        order_no=f"M05-T003-PROD-{suffix}", product_id=product.id, recipe_id=recipe.id,
        planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.IN_PROGRESS,
        target_warehouse_id=fg_wh.id, source_warehouse_id=raw_wh.id,
        scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
        actual_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        batch_no=f"M05-T003-BATCH-{suffix}", created_by=user.id,
    )
    stock = Stock(
        stock_type=StockType.MATERIAL, warehouse_id=raw_wh.id, material_id=material.id,
        quantity_on_hand=stock_quantity, quantity_reserved=Decimal("0"),
        quantity_available=stock_quantity, is_blocked=False,
    )
    db.add_all([order, stock])
    await db.flush()
    return user, material, product, raw_wh, fg_wh, recipe, order, stock


async def _complete_worker(order_id, user_id, actual_quantity: Decimal, pid_ready=None, start_event=None):
    async with AsyncSessionLocal() as db:
        order = await db.get(ProductionOrder, order_id)
        pid = (await db.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        if pid_ready is not None:
            pid_ready.set_result(pid)
        if start_event is not None:
            await start_event.wait()
        try:
            await production_service.complete_order(
                db, order, CompleteOrderRequest(actual_quantity=actual_quantity, consume_materials=True), user_id,
            )
            await db.commit()
            return pid, "committed"
        except HTTPException as error:
            await db.rollback()
            return pid, error


@pytest.mark.asyncio
async def test_inventory_issue_rejects_quantity_above_available_without_mutation():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, _, _, product, _, fg_wh = await _base(db, suffix)
        stock = Stock(stock_type=StockType.PRODUCT, warehouse_id=fg_wh.id, product_id=product.id, quantity_on_hand=Decimal("3"), quantity_reserved=Decimal("1"), quantity_available=Decimal("2"), is_blocked=False)
        db.add(stock)
        await db.flush()
        stock_id, user_id, product_id, warehouse_id = stock.id, user.id, product.id, fg_wh.id
        await db.commit()

        with pytest.raises(HTTPException) as insufficient:
            await inventory_service.stock_issue(
                db,
                StockIssueRequest(product_id=product_id, warehouse_id=warehouse_id, quantity=Decimal("3"), reference=f"M05-T003-ISSUE-{suffix}"),
                user_id,
            )
        assert insufficient.value.status_code == 422
        assert insufficient.value.detail["error"] == "INSUFFICIENT_STOCK"
        await db.rollback()
        assert (await db.get(Stock, stock_id)).quantity_on_hand == Decimal("3.000")
        assert (await db.get(Stock, stock_id)).quantity_available == Decimal("2.000")
        assert await db.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == f"M05-T003-ISSUE-{suffix}")) == 0


@pytest.mark.asyncio
async def test_concurrent_duplicate_grn_post_waits_and_posts_only_once():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        assert (await seed.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, material, warehouse, po, po_line, grn, line = await _seed_grn(seed, suffix)
        ids = (grn.id, po.id, po_line.id, line.id, material.id, warehouse.id, user.id)
        grn_no = grn.grn_no
        await seed.commit()

    async with AsyncSessionLocal() as blocker, AsyncSessionLocal() as observer:
        blocker_tx = await blocker.begin()
        pid_ready = asyncio.get_running_loop().create_future()
        start_event = asyncio.Event()

        async def post_once():
            async with AsyncSessionLocal() as db:
                stale_grn = await db.get(GoodsReceipt, ids[0])
                pid = (await db.execute(text("SELECT pg_backend_pid()"))).scalar_one()
                pid_ready.set_result(pid)
                await start_event.wait()
                try:
                    await procurement_service.post_grn(db, stale_grn, ids[6])
                    await db.commit()
                    return pid, "committed"
                except HTTPException as error:
                    await db.rollback()
                    return pid, error

        worker = asyncio.create_task(post_once())
        worker_pid = await asyncio.wait_for(pid_ready, timeout=5)
        try:
            first_grn = await blocker.get(GoodsReceipt, ids[0])
            await procurement_service.post_grn(blocker, first_grn, ids[6])
            start_event.set()
            await _wait_until_backend_is_blocked(observer, worker_pid)
        finally:
            start_event.set()
            await blocker_tx.commit()
        outcome = await worker

    assert isinstance(outcome[1], HTTPException), "the second stale GRN post must be rejected after the row lock refresh"
    assert outcome[1].status_code == 422 and "already posted" in str(outcome[1].detail).lower()
    async with AsyncSessionLocal() as verify:
        assert (await verify.get(GoodsReceipt, ids[0])).status == GRNStatus.POSTED
        assert (await verify.get(POLine, ids[2])).received_quantity == Decimal("4.000")
        stock_rows = list((await verify.execute(select(Stock).where(Stock.material_id == ids[4], Stock.warehouse_id == ids[5]))).scalars())
        assert sum((row.quantity_on_hand for row in stock_rows), Decimal("0")) == Decimal("4.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == grn_no)) == 1
        assert (await verify.get(GRNLine, ids[3])).stock_movement_id is not None


@pytest.mark.asyncio
async def test_concurrent_duplicate_production_completion_waits_and_posts_only_once():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        assert (await seed.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, material, product, raw_wh, fg_wh, _, order, stock = await _seed_production(db=seed, suffix=suffix, material_quantity=Decimal("2"), stock_quantity=Decimal("10"))
        ids = (order.id, stock.id, product.id, fg_wh.id, user.id)
        order_no = order.order_no
        await seed.commit()

    async with AsyncSessionLocal() as blocker, AsyncSessionLocal() as observer:
        blocker_tx = await blocker.begin()
        pid_ready = asyncio.get_running_loop().create_future()
        start_event = asyncio.Event()
        worker = asyncio.create_task(_complete_worker(ids[0], ids[4], Decimal("2"), pid_ready, start_event))
        worker_pid = await asyncio.wait_for(pid_ready, timeout=5)
        try:
            first_order = await blocker.get(ProductionOrder, ids[0])
            await production_service.complete_order(
                blocker, first_order,
                CompleteOrderRequest(actual_quantity=Decimal("2"), consume_materials=True), ids[4],
            )
            start_event.set()
            await _wait_until_backend_is_blocked(observer, worker_pid)
        finally:
            start_event.set()
            await blocker_tx.commit()
        outcome = await worker

    assert isinstance(outcome[1], HTTPException), "the second stale completion must be rejected after the order lock refresh"
    assert outcome[1].status_code == 422 and "must be in_progress" in str(outcome[1].detail).lower()
    async with AsyncSessionLocal() as verify:
        assert (await verify.get(ProductionOrder, ids[0])).status == ProductionOrderStatus.COMPLETED
        assert (await verify.get(Stock, ids[1])).quantity_on_hand == Decimal("8.000")
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == ids[0])) == 1
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == ids[0])) == 1
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 2
        fg_stock = (await verify.execute(select(Stock).where(Stock.product_id == ids[2], Stock.warehouse_id == ids[3]))).scalar_one()
        assert fg_stock.quantity_on_hand == Decimal("2.000")


@pytest.mark.asyncio
async def test_concurrent_production_orders_cannot_consume_more_than_shared_stock():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as seed:
        assert (await seed.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user, material, product, raw_wh, fg_wh, recipe, first, stock = await _seed_production(seed, suffix + "A", Decimal("4"), Decimal("6"))
        second = ProductionOrder(
            order_no=f"M05-T003-PROD-{suffix}B", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.IN_PROGRESS,
            target_warehouse_id=fg_wh.id, source_warehouse_id=raw_wh.id,
            scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
            actual_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
            batch_no=f"M05-T003-BATCH-{suffix}B", created_by=user.id,
        )
        seed.add(second)
        await seed.flush()
        ids = (first.id, second.id, stock.id, material.id, user.id)
        await seed.commit()

    async with AsyncSessionLocal() as blocker, AsyncSessionLocal() as observer:
        blocker_tx = await blocker.begin()
        await blocker.execute(select(Stock.id).where(Stock.id == ids[2]).with_for_update())
        first_ready = asyncio.get_running_loop().create_future()
        second_ready = asyncio.get_running_loop().create_future()
        first_worker = asyncio.create_task(_complete_worker(ids[0], ids[4], Decimal("2"), first_ready))
        second_worker = asyncio.create_task(_complete_worker(ids[1], ids[4], Decimal("2"), second_ready))
        pids = await asyncio.wait_for(asyncio.gather(first_ready, second_ready), timeout=5)
        try:
            for pid in pids:
                await _wait_until_backend_is_blocked(observer, pid)
        finally:
            await blocker_tx.commit()
        outcomes = await asyncio.gather(first_worker, second_worker)

    successes = [result for _, result in outcomes if result == "committed"]
    failures = [result for _, result in outcomes if isinstance(result, HTTPException)]
    assert len(successes) == 1 and len(failures) == 1
    assert failures[0].status_code == 422 and failures[0].detail["error"] == "INSUFFICIENT_MATERIAL"
    async with AsyncSessionLocal() as verify:
        stock_after = await verify.get(Stock, ids[2])
        assert stock_after.quantity_on_hand == Decimal("2.000")
        assert stock_after.quantity_available == Decimal("2.000")
        assert stock_after.quantity_on_hand >= Decimal("0")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.material_id == ids[3])) == 1
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id.in_((ids[0], ids[1])))) == 1
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id.in_((ids[0], ids[1])))) == 1
