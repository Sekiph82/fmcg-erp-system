"""M05.S03.T001: disposable-PostgreSQL tests for sales stock reservation integrity."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import JournalEntry
from app.models.inventory import MovementType, Stock, StockMovement, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.sales import (
    Customer,
    SOStatus,
    SOLine,
    SalesOrder,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
)
from app.services import sales_service


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m05_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> None:
    if os.environ.get("M05_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M05_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M05_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M05.S03.T001 database without a password.")


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m05_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m05_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m05_s03_t001_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _seed_context(db, suffix: str):
    product = Product(
        sku=f"M05-{suffix}", name=f"Synthetic product {suffix}",
        category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS,
    )
    warehouse = Warehouse(
        code=f"M05-{suffix}", name=f"Synthetic warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    customer = Customer(code=f"M05-{suffix}", name=f"Synthetic customer {suffix}")
    db.add_all([product, warehouse, customer])
    await db.flush()
    return product, warehouse, customer


async def _seed_order(db, suffix: str, product: Product, customer: Customer, quantity: Decimal):
    order = SalesOrder(
        order_no=f"M05-{suffix}", customer_id=customer.id,
        order_date=date(2026, 1, 1), requested_delivery_date=date(2026, 1, 2),
        status=SOStatus.CONFIRMED,
    )
    db.add(order)
    await db.flush()
    line = SOLine(
        so_id=order.id, line_no=1, product_id=product.id,
        ordered_quantity=quantity, unit="PCS", unit_price=Decimal("1.00"),
    )
    db.add(line)
    await db.flush()
    return order, line


async def _stock(db, product: Product, warehouse: Warehouse, on_hand: Decimal, reserved: Decimal = Decimal("0")):
    row = Stock(
        stock_type=StockType.PRODUCT, warehouse_id=warehouse.id, product_id=product.id,
        quantity_on_hand=on_hand, quantity_reserved=reserved,
        quantity_available=on_hand - reserved, is_blocked=False,
    )
    db.add(row)
    await db.flush()
    return row


@pytest.mark.asyncio
async def test_allocation_cancel_preserves_other_reservations_and_stock_arithmetic():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        product, warehouse, customer = await _seed_context(db, suffix)
        first_stock = await _stock(db, product, warehouse, Decimal("10"), Decimal("1"))
        second_stock = await _stock(db, product, warehouse, Decimal("10"), Decimal("2"))
        stock_ids = (first_stock.id, second_stock.id)
        first_order, first_line = await _seed_order(db, suffix + "A", product, customer, Decimal("5"))
        second_order, second_line = await _seed_order(db, suffix + "B", product, customer, Decimal("4"))
        await db.commit()

        await sales_service.allocate_so(db, first_order, warehouse.id, uuid4())
        await db.commit()
        await sales_service.allocate_so(db, second_order, warehouse.id, uuid4())
        await db.commit()

        stocks_now = list((await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))).scalars())
        assert sum(row.quantity_on_hand for row in stocks_now) == Decimal("20.000")
        assert sum(row.quantity_reserved for row in stocks_now) == Decimal("12.000")
        assert sum(row.quantity_available for row in stocks_now) == Decimal("8.000")
        assert all(row.quantity_available == row.quantity_on_hand - row.quantity_reserved for row in stocks_now)
        assert first_line.allocated_quantity == Decimal("5")
        assert second_line.allocated_quantity == Decimal("4")

        movement_count_before = await db.scalar(select(func.count(StockMovement.id)))
        await sales_service.cancel_so(db, first_order)
        await db.commit()
        stocks_after = list((await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))).scalars())
        assert sum(row.quantity_reserved for row in stocks_after) == Decimal("7.000")  # prior 3 + second order 4
        assert sum(row.quantity_available for row in stocks_after) == Decimal("13.000")
        assert all(row.quantity_on_hand == row.quantity_reserved + row.quantity_available for row in stocks_after)
        assert first_line.allocated_quantity == Decimal("0")
        assert second_line.allocated_quantity == Decimal("4")
        assert first_order.status == SOStatus.CANCELLED
        assert await db.scalar(select(func.count(StockMovement.id))) == movement_count_before

        with pytest.raises(HTTPException) as repeated_cancel:
            await sales_service.cancel_so(db, first_order)
        assert repeated_cancel.value.status_code == 422
        await db.rollback()
        unchanged_rows = list((await db.execute(select(Stock).where(Stock.id.in_(stock_ids)))).scalars())
        assert sum(row.quantity_reserved for row in unchanged_rows) == Decimal("7.000")
        assert sum(row.quantity_available for row in unchanged_rows) == Decimal("13.000")


@pytest.mark.asyncio
async def test_insufficient_allocation_is_rejected_without_persisting_stock_or_order_changes():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        product, warehouse, customer = await _seed_context(db, suffix)
        stock = await _stock(db, product, warehouse, Decimal("5"), Decimal("2"))
        order, line = await _seed_order(db, suffix + "A", product, customer, Decimal("4"))
        stock_id, order_id, line_id, warehouse_id = stock.id, order.id, line.id, warehouse.id
        await db.commit()

        persisted_order = await db.get(SalesOrder, order_id)
        with pytest.raises(HTTPException) as insufficient:
            await sales_service.allocate_so(db, persisted_order, warehouse_id, uuid4())
        assert insufficient.value.status_code == 422
        assert insufficient.value.detail["error"] == "INSUFFICIENT_STOCK"
        await db.rollback()  # same rollback performed by the request DB dependency on service failure

        stock_after = await db.get(Stock, stock_id)
        order_after = await db.get(SalesOrder, order_id)
        line_after = await db.get(SOLine, line_id)
        assert (stock_after.quantity_on_hand, stock_after.quantity_reserved, stock_after.quantity_available) == (
            Decimal("5.000"), Decimal("2.000"), Decimal("3.000"),
        )
        assert order_after.status == SOStatus.CONFIRMED
        assert line_after.allocated_quantity == Decimal("0.000")


@pytest.mark.asyncio
async def test_partial_dispatch_decreases_reserved_and_on_hand_once_without_finance_posting():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        product, warehouse, customer = await _seed_context(db, suffix)
        stock = await _stock(db, product, warehouse, Decimal("12"))
        order, line = await _seed_order(db, suffix + "A", product, customer, Decimal("4"))
        await db.commit()
        await sales_service.allocate_so(db, order, warehouse.id, uuid4())
        await db.commit()

        shipment = Shipment(
            shipment_no=f"M05-{suffix}", so_id=order.id, warehouse_id=warehouse.id,
            status=ShipmentStatus.PENDING, scheduled_date=date(2026, 1, 2),
        )
        db.add(shipment)
        await db.flush()
        shipment_line = ShipmentLine(
            shipment_id=shipment.id, so_line_id=line.id, product_id=product.id,
            quantity=Decimal("2"), unit="PCS",
        )
        db.add(shipment_line)
        await db.commit()
        shipment_id, stock_id, shipment_no, line_id = shipment.id, stock.id, shipment.shipment_no, line.id
        journal_count_before = await db.scalar(select(func.count(JournalEntry.id)))
        await db.commit()

    # Keep an intentionally stale PENDING object open while another request
    # dispatches and commits, then retry through that stale object.
    async with AsyncSessionLocal() as stale_request:
        stale_shipment = await stale_request.get(Shipment, shipment_id)
        async with AsyncSessionLocal() as dispatcher:
            loaded_shipment = await dispatcher.get(Shipment, shipment_id)
            await sales_service.dispatch_shipment(dispatcher, loaded_shipment, date(2026, 1, 2), None)
            await dispatcher.commit()

        with pytest.raises(HTTPException) as repeated_dispatch:
            await sales_service.dispatch_shipment(stale_request, stale_shipment, date(2026, 1, 2), None)
        assert repeated_dispatch.value.status_code == 422
        await stale_request.rollback()

    async with AsyncSessionLocal() as verify:
        stock_after = await verify.get(Stock, stock_id)
        refreshed_line = await verify.get(SOLine, line_id)
        movement = (await verify.execute(select(StockMovement).where(StockMovement.reference_number == shipment_no))).scalar_one()
        assert (stock_after.quantity_on_hand, stock_after.quantity_reserved, stock_after.quantity_available) == (
            Decimal("10.000"), Decimal("2.000"), Decimal("8.000"),
        )
        assert stock_after.quantity_on_hand == stock_after.quantity_reserved + stock_after.quantity_available
        assert refreshed_line.allocated_quantity == Decimal("4.000")
        assert refreshed_line.shipped_quantity == Decimal("2.000")
        assert stock_after.quantity_reserved == refreshed_line.allocated_quantity - refreshed_line.shipped_quantity
        assert movement.movement_type == MovementType.ISSUE
        assert movement.quantity == Decimal("2.000")
        assert await verify.scalar(select(func.count(JournalEntry.id))) == journal_count_before
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == shipment_no)) == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_allocation_of_one_order_cannot_reserve_twice():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as setup:
        product, warehouse, customer = await _seed_context(setup, suffix)
        stock = await _stock(setup, product, warehouse, Decimal("20"))
        order, line = await _seed_order(setup, suffix + "A", product, customer, Decimal("5"))
        stock_id, order_id, line_id, warehouse_id = stock.id, order.id, line.id, warehouse.id
        await setup.commit()

    first_flushed = asyncio.Event()
    resume_first = asyncio.Event()
    second_lock_started = asyncio.Event()
    first_task = None
    second_task = None

    async with AsyncSessionLocal() as first, AsyncSessionLocal() as second:
        first_order = await first.get(SalesOrder, order_id)
        second_order = await second.get(SalesOrder, order_id)  # deliberately stale pre-transition view
        second_pid = await second.scalar(text("select pg_backend_pid()"))
        original_flush = first.flush

        async def _pause_after_first_flush(*args, **kwargs):
            await original_flush(*args, **kwargs)
            first_flushed.set()
            await resume_first.wait()

        first.flush = _pause_after_first_flush

        async def _first_allocation():
            await sales_service.allocate_so(first, first_order, warehouse_id, uuid4())
            await first.commit()

        async def _second_allocation():
            try:
                await sales_service.allocate_so(second, second_order, warehouse_id, uuid4())
                await second.commit()
                return None
            except HTTPException as exc:
                await second.rollback()
                return exc

        first_task = asyncio.create_task(_first_allocation())
        try:
            await asyncio.wait_for(first_flushed.wait(), timeout=10)
            second_task = asyncio.create_task(_second_allocation())
            # Observe PostgreSQL itself reporting a lock wait before releasing
            # transaction one; a client-side pre-query signal is not sufficient.
            async with AsyncSessionLocal() as observer:
                for _ in range(250):
                    wait_type = await observer.scalar(
                        text("select wait_event_type from pg_stat_activity where pid = :pid"),
                        {"pid": second_pid},
                    )
                    if wait_type == "Lock":
                        second_lock_started.set()
                        break
                    await asyncio.sleep(0.02)
            await asyncio.wait_for(second_lock_started.wait(), timeout=10)
        finally:
            resume_first.set()
            await asyncio.wait_for(first_task, timeout=10)
            if second_task is not None:
                await asyncio.wait_for(second_task, timeout=10)

    second_error = await second_task
    assert isinstance(second_error, HTTPException)
    assert second_error.status_code == 422

    async with AsyncSessionLocal() as verify:
        final_stock = await verify.get(Stock, stock_id)
        final_order = await verify.get(SalesOrder, order_id)
        final_line = await verify.get(SOLine, line_id)
        assert final_stock.quantity_on_hand == Decimal("20.000")
        assert final_stock.quantity_reserved == Decimal("5.000")
        assert final_stock.quantity_available == Decimal("15.000")
        assert final_stock.quantity_available == final_stock.quantity_on_hand - final_stock.quantity_reserved
        assert final_line.allocated_quantity == Decimal("5.000")
        assert final_order.status == SOStatus.ALLOCATED


@pytest.mark.asyncio
async def test_concurrent_orders_cannot_reserve_more_than_available_stock():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as setup:
        product, warehouse, customer = await _seed_context(setup, suffix)
        stock = await _stock(setup, product, warehouse, Decimal("8"))
        first_order, first_line = await _seed_order(setup, suffix + "A", product, customer, Decimal("6"))
        second_order, second_line = await _seed_order(setup, suffix + "B", product, customer, Decimal("6"))
        stock_id = stock.id
        order_ids = (first_order.id, second_order.id)
        line_ids = (first_line.id, second_line.id)
        warehouse_id = warehouse.id
        await setup.commit()

    async def _try_allocate(order_id):
        async with AsyncSessionLocal() as db:
            order = await db.get(SalesOrder, order_id)
            try:
                await sales_service.allocate_so(db, order, warehouse_id, uuid4())
                await db.commit()
                return None
            except HTTPException as exc:
                await db.rollback()
                return exc

    first_result, second_result = await asyncio.gather(*(_try_allocate(order_id) for order_id in order_ids))
    failures = [result for result in (first_result, second_result) if result is not None]
    assert len(failures) == 1
    assert failures[0].status_code == 422
    assert failures[0].detail["error"] == "INSUFFICIENT_STOCK"

    async with AsyncSessionLocal() as verify:
        final_stock = await verify.get(Stock, stock_id)
        lines = list((await verify.execute(select(SOLine).where(SOLine.id.in_(line_ids)))).scalars())
        orders = list((await verify.execute(select(SalesOrder).where(SalesOrder.id.in_(order_ids)))).scalars())
        assert final_stock.quantity_on_hand == Decimal("8.000")
        assert final_stock.quantity_reserved == Decimal("6.000")
        assert final_stock.quantity_available == Decimal("2.000")
        assert final_stock.quantity_available == final_stock.quantity_on_hand - final_stock.quantity_reserved
        assert sum(line.allocated_quantity for line in lines) == Decimal("6.000")
        assert sum(order.status == SOStatus.ALLOCATED for order in orders) == 1
        assert sum(order.status == SOStatus.CONFIRMED for order in orders) == 1


@pytest.mark.asyncio
async def test_cancel_refreshes_allocation_after_waiting_for_concurrent_allocator():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as setup:
        product, warehouse, customer = await _seed_context(setup, suffix)
        stock = await _stock(setup, product, warehouse, Decimal("10"))
        order, line = await _seed_order(setup, suffix + "A", product, customer, Decimal("5"))
        stock_id, order_id, line_id, warehouse_id = stock.id, order.id, line.id, warehouse.id
        await setup.commit()

    async with AsyncSessionLocal() as stale_cancel:
        stale_order = await stale_cancel.get(SalesOrder, order_id)
        stale_line = await stale_cancel.get(SOLine, line_id)
        assert stale_line.allocated_quantity == Decimal("0")
        async with AsyncSessionLocal() as allocator:
            allocated_order = await allocator.get(SalesOrder, order_id)
            await sales_service.allocate_so(allocator, allocated_order, warehouse_id, uuid4())
            await allocator.commit()

        await sales_service.cancel_so(stale_cancel, stale_order)
        await stale_cancel.commit()

    async with AsyncSessionLocal() as verify:
        final_stock = await verify.get(Stock, stock_id)
        final_order = await verify.get(SalesOrder, order_id)
        final_line = await verify.get(SOLine, line_id)
        assert final_stock.quantity_reserved == Decimal("0.000")
        assert final_stock.quantity_available == Decimal("10.000")
        assert final_stock.quantity_on_hand == final_stock.quantity_reserved + final_stock.quantity_available
        assert final_order.status == SOStatus.CANCELLED
        assert final_line.allocated_quantity == Decimal("0.000")


@pytest.mark.asyncio
async def test_partial_dispatch_refreshes_cached_sales_line_before_increment():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as setup:
        product, warehouse, customer = await _seed_context(setup, suffix)
        stock = await _stock(setup, product, warehouse, Decimal("12"))
        order, line = await _seed_order(setup, suffix + "A", product, customer, Decimal("6"))
        await setup.commit()
        await sales_service.allocate_so(setup, order, warehouse.id, uuid4())
        await setup.commit()
        first_shipment = Shipment(
            shipment_no=f"M05-{suffix}A", so_id=order.id, warehouse_id=warehouse.id,
            status=ShipmentStatus.PENDING, scheduled_date=date(2026, 1, 2),
        )
        second_shipment = Shipment(
            shipment_no=f"M05-{suffix}B", so_id=order.id, warehouse_id=warehouse.id,
            status=ShipmentStatus.PENDING, scheduled_date=date(2026, 1, 2),
        )
        setup.add_all([first_shipment, second_shipment])
        await setup.flush()
        setup.add_all([
            ShipmentLine(shipment_id=first_shipment.id, so_line_id=line.id, product_id=product.id, quantity=Decimal("2"), unit="PCS"),
            ShipmentLine(shipment_id=second_shipment.id, so_line_id=line.id, product_id=product.id, quantity=Decimal("2"), unit="PCS"),
        ])
        await setup.commit()
        first_id, second_id, order_line_id, stock_id = first_shipment.id, second_shipment.id, line.id, stock.id
        first_no, second_no = first_shipment.shipment_no, second_shipment.shipment_no

    async with AsyncSessionLocal() as second_dispatch:
        second_shipment = await second_dispatch.get(Shipment, second_id)
        stale_line = await second_dispatch.get(SOLine, order_line_id)
        assert stale_line.shipped_quantity == Decimal("0")
        async with AsyncSessionLocal() as first_dispatch:
            first = await first_dispatch.get(Shipment, first_id)
            await sales_service.dispatch_shipment(first_dispatch, first, date(2026, 1, 2), None)
            await first_dispatch.commit()

        await sales_service.dispatch_shipment(second_dispatch, second_shipment, date(2026, 1, 2), None)
        await second_dispatch.commit()

    async with AsyncSessionLocal() as verify:
        final_stock = await verify.get(Stock, stock_id)
        final_line = await verify.get(SOLine, order_line_id)
        final_order = await verify.get(SalesOrder, order.id)
        movement_count = await verify.scalar(
            select(func.count(StockMovement.id)).where(StockMovement.reference_number.in_((first_no, second_no)))
        )
        assert final_stock.quantity_on_hand == Decimal("8.000")
        assert final_stock.quantity_reserved == Decimal("2.000")
        assert final_stock.quantity_available == Decimal("6.000")
        assert final_line.allocated_quantity == Decimal("6.000")
        assert final_line.shipped_quantity == Decimal("4.000")
        assert final_stock.quantity_reserved == final_line.allocated_quantity - final_line.shipped_quantity
        assert final_order.status == SOStatus.PICKING
        assert movement_count == 2


@pytest.mark.asyncio
async def test_allocator_refreshes_cached_stock_after_competing_allocation():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as setup:
        product, warehouse, customer = await _seed_context(setup, suffix)
        stock = await _stock(setup, product, warehouse, Decimal("8"))
        first_order, first_line = await _seed_order(setup, suffix + "A", product, customer, Decimal("6"))
        second_order, second_line = await _seed_order(setup, suffix + "B", product, customer, Decimal("6"))
        stock_id, first_id, second_id = stock.id, first_order.id, second_order.id
        first_line_id, second_line_id, warehouse_id = first_line.id, second_line.id, warehouse.id
        await setup.commit()

    async with AsyncSessionLocal() as stale_allocator:
        second_order = await stale_allocator.get(SalesOrder, second_id)
        stale_stock = await stale_allocator.get(Stock, stock_id)
        assert stale_stock.quantity_available == Decimal("8.000")
        async with AsyncSessionLocal() as first_allocator:
            first_order = await first_allocator.get(SalesOrder, first_id)
            await sales_service.allocate_so(first_allocator, first_order, warehouse_id, uuid4())
            await first_allocator.commit()

        with pytest.raises(HTTPException) as insufficient:
            await sales_service.allocate_so(stale_allocator, second_order, warehouse_id, uuid4())
        assert insufficient.value.status_code == 422
        assert insufficient.value.detail["error"] == "INSUFFICIENT_STOCK"
        assert insufficient.value.detail["available"] == 2.0
        await stale_allocator.rollback()

    async with AsyncSessionLocal() as verify:
        final_stock = await verify.get(Stock, stock_id)
        first_line = await verify.get(SOLine, first_line_id)
        second_line = await verify.get(SOLine, second_line_id)
        assert final_stock.quantity_on_hand == Decimal("8.000")
        assert final_stock.quantity_reserved == Decimal("6.000")
        assert final_stock.quantity_available == Decimal("2.000")
        assert final_stock.quantity_available == final_stock.quantity_on_hand - final_stock.quantity_reserved
        assert first_line.allocated_quantity == Decimal("6.000")
        assert second_line.allocated_quantity == Decimal("0.000")
