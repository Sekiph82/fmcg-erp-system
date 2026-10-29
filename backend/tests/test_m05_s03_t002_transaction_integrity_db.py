"""M05.S03.T002 disposable PostgreSQL tests for cross-module transaction integrity."""
from __future__ import annotations

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
    AccountType, AccountingPeriod, AccountingPostingBatch, ChartOfAccount,
    InventoryAccountMapping, JournalEntry, PeriodStatus,
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
from app.models.procurement import (
    GoodsReceipt,
    GRNLine,
    GRNStatus,
    POStatus,
    POLine,
    PurchaseOrder,
)
from app.models.production import (
    FinishedGoodsReceipt,
    MaterialConsumption,
    ProductionOrder,
    ProductionOrderStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.sales import (
    Customer,
    SOStatus,
    SOLine,
    SalesOrder,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
)
from app.models.user import User
from app.schemas.production import CompleteOrderRequest
from app.services import production_service, procurement_service, sales_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M05_S03_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m05_s03_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M05_S03_T002_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M05_S03_T002_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M05_S03_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M05.S03.T002 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m05_s03_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m05_s03_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m05_s03_t002_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="never-used", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _base_records(db, suffix: str):
    user = User(
        email=f"m05-t002-{suffix}@example.invalid",
        username=f"m05t002{suffix}",
        full_name=f"Synthetic M05 T002 actor {suffix}",
        hashed_password="synthetic-test-only-not-a-credential",
    )
    supplier = Supplier(code=f"M05-T002-S-{suffix}", name=f"Synthetic supplier {suffix}")
    material = Material(
        code=f"M05-T002-M-{suffix}", name=f"Synthetic material {suffix}",
        material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
    )
    product = Product(
        sku=f"M05-T002-P-{suffix}", name=f"Synthetic product {suffix}",
        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
    )
    raw_warehouse = Warehouse(
        code=f"M05-T002-R-{suffix}", name=f"Synthetic raw warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
    )
    finished_warehouse = Warehouse(
        code=f"M05-T002-F-{suffix}", name=f"Synthetic finished warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    customer = Customer(code=f"M05-T002-C-{suffix}", name=f"Synthetic customer {suffix}")
    db.add_all([user, supplier, material, product, raw_warehouse, finished_warehouse, customer])
    await db.flush()
    return user, supplier, material, product, raw_warehouse, finished_warehouse, customer


async def _seed_grn(db, suffix: str):
    user, supplier, material, _, raw_wh, _, _ = await _base_records(db, suffix)
    company = Company(
        name=f"Synthetic M05 T002 Company {suffix}", short_code=f"M5{suffix[:8].upper()}",
        country="Kenya", base_currency="KES",
    )
    inventory_account = ChartOfAccount(
        code=f"M5I{suffix[:8].upper()}", name="Synthetic inventory", account_type=AccountType.ASSET,
    )
    grni_account = ChartOfAccount(
        code=f"M5G{suffix[:8].upper()}", name="Synthetic GRNI", account_type=AccountType.LIABILITY,
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
        po_no=f"M05-T002-PO-{suffix}", supplier_id=supplier.id,
        company_id=company.id, currency="KES", exchange_rate=Decimal("1"),
        order_date=date(2026, 10, 29), expected_delivery_date=date(2026, 10, 30),
        status=POStatus.ORDERED, created_by_id=user.id,
    )
    db.add(po)
    await db.flush()
    po_line = POLine(
        po_id=po.id, line_no=1, material_id=material.id,
        ordered_quantity=Decimal("6"), received_quantity=Decimal("0"), unit="KG", unit_price=Decimal("25"),
    )
    grn = GoodsReceipt(
        grn_no=f"M05-T002-GRN-{suffix}", po_id=po.id,
        company_id=company.id,
        received_date=date(2026, 10, 29), received_by_id=user.id,
        warehouse_id=raw_wh.id, status=GRNStatus.DRAFT,
    )
    db.add_all([po_line, grn])
    await db.flush()
    grn_line = GRNLine(
        grn_id=grn.id, po_line_id=po_line.id, material_id=material.id,
        received_quantity=Decimal("4"), accepted_quantity=Decimal("4"),
        rejected_quantity=Decimal("0"), unit="KG",
    )
    db.add(grn_line)
    await db.flush()
    return user, material, raw_wh, po, po_line, grn, grn_line


async def _seed_production(db, suffix: str):
    user, _, material, product, raw_wh, fg_wh, _ = await _base_records(db, suffix)
    recipe = Recipe(
        product_id=product.id, version="1", name=f"Synthetic recipe {suffix}",
        status=RecipeStatus.APPROVED, is_active=True,
    )
    db.add(recipe)
    await db.flush()
    recipe_item = RecipeItem(
        recipe_id=recipe.id, material_id=material.id, line_no=1,
        quantity=Decimal("2"), unit="KG", loss_percentage=Decimal("0"),
    )
    order = ProductionOrder(
        order_no=f"M05-T002-PROD-{suffix}", product_id=product.id,
        recipe_id=recipe.id, planned_quantity=Decimal("4"), uom="KG",
        status=ProductionOrderStatus.IN_PROGRESS, target_warehouse_id=fg_wh.id,
        source_warehouse_id=raw_wh.id, scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
        actual_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        batch_no=f"M05-T002-BATCH-{suffix}", created_by=user.id,
    )
    raw_stock = Stock(
        stock_type=StockType.MATERIAL, warehouse_id=raw_wh.id, material_id=material.id,
        quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
        quantity_available=Decimal("10"), is_blocked=False,
    )
    db.add_all([recipe_item, order, raw_stock])
    await db.flush()
    return user, material, product, raw_wh, fg_wh, order, raw_stock


async def _seed_shipment(db, suffix: str):
    user, _, _, product, _, fg_wh, customer = await _base_records(db, suffix)
    order = SalesOrder(
        order_no=f"M05-T002-SO-{suffix}", customer_id=customer.id,
        order_date=date(2026, 10, 29), requested_delivery_date=date(2026, 10, 30),
        status=SOStatus.PICKING, warehouse_id=fg_wh.id, created_by_id=user.id,
    )
    db.add(order)
    await db.flush()
    order_line = SOLine(
        so_id=order.id, line_no=1, product_id=product.id,
        ordered_quantity=Decimal("3"), unit="KG", unit_price=Decimal("2"),
        allocated_quantity=Decimal("3"), shipped_quantity=Decimal("0"),
    )
    shipment = Shipment(
        shipment_no=f"M05-T002-SHIP-{suffix}", so_id=order.id,
        warehouse_id=fg_wh.id, status=ShipmentStatus.PACKED,
        scheduled_date=date(2026, 10, 30), created_by_id=user.id,
    )
    db.add_all([order_line, shipment])
    await db.flush()
    shipment_line = ShipmentLine(
        shipment_id=shipment.id, so_line_id=order_line.id,
        product_id=product.id, quantity=Decimal("3"), unit="KG",
    )
    stock = Stock(
        stock_type=StockType.PRODUCT, warehouse_id=fg_wh.id, product_id=product.id,
        quantity_on_hand=Decimal("5"), quantity_reserved=Decimal("3"),
        quantity_available=Decimal("2"), is_blocked=False,
    )
    db.add_all([shipment_line, stock])
    await db.flush()
    return user, product, fg_wh, order, order_line, shipment, shipment_line, stock


@pytest.mark.asyncio
async def test_grn_post_commits_stock_and_po_effects_once_and_rejects_repeat():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        journal_count_before = await db.scalar(select(func.count(JournalEntry.id)))
        batch_count_before = await db.scalar(select(func.count(AccountingPostingBatch.id)))
        user, material, warehouse, po, po_line, grn, grn_line = await _seed_grn(db, suffix)
        ids = (grn.id, grn_line.id, po.id, po_line.id, material.id, warehouse.id, user.id)
        await db.commit()

        await procurement_service.post_grn(db, await db.get(GoodsReceipt, ids[0]), ids[6])
        await db.commit()

        persisted_grn = await db.get(GoodsReceipt, ids[0])
        persisted_line = await db.get(GRNLine, ids[1])
        persisted_po = await db.get(PurchaseOrder, ids[2])
        persisted_po_line = await db.get(POLine, ids[3])
        stock = (await db.execute(select(Stock).where(Stock.material_id == ids[4], Stock.warehouse_id == ids[5]))).scalar_one()
        movement = await db.get(StockMovement, persisted_line.stock_movement_id)
        assert persisted_grn.status == GRNStatus.POSTED
        assert persisted_po.status == POStatus.PARTIALLY_RECEIVED
        assert persisted_po_line.received_quantity == Decimal("4.000")
        assert stock.quantity_on_hand == Decimal("4.000")
        assert stock.quantity_available == Decimal("4.000")
        assert movement.quantity == Decimal("4.000") and movement.created_by_id == ids[6]
        assert movement.movement_type == MovementType.RECEIPT
        assert movement.journal_entry_id is not None and movement.posting_batch_id is not None
        assert movement.accounting_status.value == "POSTED"
        assert persisted_line.journal_entry_id == movement.journal_entry_id
        assert persisted_line.posting_batch_id == movement.posting_batch_id
        assert await db.scalar(select(func.count(JournalEntry.id))) == journal_count_before + 1
        assert await db.scalar(select(func.count(AccountingPostingBatch.id))) == batch_count_before + 1
        stock_id = stock.id

        with pytest.raises(HTTPException) as repeated:
            await procurement_service.post_grn(db, persisted_grn, ids[6])
        assert repeated.value.status_code == 422
        assert "already posted" in str(repeated.value.detail).lower()
        movement_reference = movement.reference_number
        await db.rollback()
        assert await db.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == movement_reference)) == 1
        assert (await db.get(Stock, stock_id)).quantity_on_hand == Decimal("4.000")


@pytest.mark.asyncio
async def test_production_completion_commits_material_and_fg_effects_once_and_rejects_repeat():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        journal_count_before = await db.scalar(select(func.count(JournalEntry.id)))
        batch_count_before = await db.scalar(select(func.count(AccountingPostingBatch.id)))
        user, material, product, raw_wh, fg_wh, order, raw_stock = await _seed_production(db, suffix)
        ids = (order.id, raw_stock.id, material.id, product.id, raw_wh.id, fg_wh.id, user.id)
        order_no = order.order_no
        await db.commit()

        await production_service.complete_order(
            db, await db.get(ProductionOrder, ids[0]),
            CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
        )
        await db.commit()

        persisted_order = await db.get(ProductionOrder, ids[0])
        raw_after = await db.get(Stock, ids[1])
        fg_stock = (await db.execute(select(Stock).where(Stock.product_id == ids[3], Stock.warehouse_id == ids[5]))).scalar_one()
        consumptions = list((await db.execute(select(MaterialConsumption).where(MaterialConsumption.production_order_id == ids[0]))).scalars())
        receipts = list((await db.execute(select(FinishedGoodsReceipt).where(FinishedGoodsReceipt.production_order_id == ids[0]))).scalars())
        assert persisted_order.status == ProductionOrderStatus.COMPLETED
        assert persisted_order.actual_quantity == Decimal("4.000")
        assert raw_after.quantity_on_hand == Decimal("8.000")
        assert len(consumptions) == 1 and consumptions[0].actual_quantity == Decimal("2.0000")
        assert len(receipts) == 1 and receipts[0].quantity == Decimal("4.000")
        movements = list((await db.execute(select(StockMovement).where(StockMovement.reference_number == order_no))).scalars())
        assert len(movements) == 2
        issue = next(row for row in movements if row.movement_type == MovementType.ISSUE)
        receipt = next(row for row in movements if row.movement_type == MovementType.RECEIPT)
        assert issue.quantity == Decimal("2.0000") and issue.created_by_id == ids[6]
        assert receipt.quantity == Decimal("4.000") and receipt.created_by_id == ids[6]
        assert receipts[0].stock_movement_id == receipt.id
        assert consumptions[0].journal_entry_id is None and consumptions[0].posting_batch_id is None
        assert receipts[0].journal_entry_id is None and receipts[0].posting_batch_id is None
        assert fg_stock.quantity_on_hand == Decimal("4.000")
        assert all(row.journal_entry_id is None and row.posting_batch_id is None for row in movements)
        assert await db.scalar(select(func.count(JournalEntry.id))) == journal_count_before
        assert await db.scalar(select(func.count(AccountingPostingBatch.id))) == batch_count_before

        with pytest.raises(HTTPException) as repeated:
            await production_service.complete_order(
                db, persisted_order,
                CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
            )
        assert repeated.value.status_code == 422
        assert "must be in_progress" in str(repeated.value.detail).lower()
        await db.rollback()
        assert await db.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == ids[0])) == 1
        assert await db.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == ids[0])) == 1
        assert await db.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 2
        assert (await db.get(Stock, ids[1])).quantity_on_hand == Decimal("8.000")


@pytest.mark.asyncio
async def test_shipment_dispatch_commits_stock_and_sales_effects_once_and_rejects_repeat():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        journal_count_before = await db.scalar(select(func.count(JournalEntry.id)))
        batch_count_before = await db.scalar(select(func.count(AccountingPostingBatch.id)))
        user, product, warehouse, order, order_line, shipment, shipment_line, stock = await _seed_shipment(db, suffix)
        ids = (shipment.id, shipment_line.id, stock.id, order.id, order_line.id, product.id, user.id)
        shipment_no = shipment.shipment_no
        await db.commit()

        await sales_service.dispatch_shipment(
            db, await db.get(Shipment, ids[0]), date(2026, 10, 30), ids[6]
        )
        await db.commit()

        persisted_shipment = await db.get(Shipment, ids[0])
        persisted_line = await db.get(ShipmentLine, ids[1])
        persisted_order = await db.get(SalesOrder, ids[3])
        persisted_order_line = await db.get(SOLine, ids[4])
        stock_after = await db.get(Stock, ids[2])
        movement = await db.get(StockMovement, persisted_line.stock_movement_id)
        assert persisted_shipment.status == ShipmentStatus.DISPATCHED
        assert persisted_shipment.dispatched_by_id == ids[6]
        assert persisted_order.status == SOStatus.SHIPPED
        assert persisted_order_line.shipped_quantity == Decimal("3.000")
        assert stock_after.quantity_on_hand == Decimal("2.000")
        assert stock_after.quantity_reserved == Decimal("0.000")
        assert stock_after.quantity_available == Decimal("2.000")
        assert movement.movement_type == MovementType.ISSUE
        assert movement.quantity == Decimal("3.000") and movement.created_by_id == ids[6]
        assert movement.journal_entry_id is None and movement.posting_batch_id is None
        assert await db.scalar(select(func.count(JournalEntry.id))) == journal_count_before
        assert await db.scalar(select(func.count(AccountingPostingBatch.id))) == batch_count_before

        with pytest.raises(HTTPException) as repeated:
            await sales_service.dispatch_shipment(db, persisted_shipment, date(2026, 10, 30), ids[6])
        assert repeated.value.status_code == 422
        assert "shipmentstatus.dispatched" in str(repeated.value.detail).lower()
        movement_reference = movement.reference_number
        await db.rollback()
        assert await db.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == movement_reference)) == 1
        assert (await db.get(Stock, ids[2])).quantity_on_hand == Decimal("2.000")


@pytest.mark.asyncio
async def test_grn_late_failure_rolls_back_stock_movement_and_po_progress():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        user, material, warehouse, po, po_line, grn, grn_line = await _seed_grn(db, suffix)
        ids = (grn.id, grn_line.id, po.id, po_line.id, material.id, warehouse.id, user.id)
        await db.commit()
        try:
            async with db.begin():
                await procurement_service.post_grn(db, await db.get(GoodsReceipt, ids[0]), ids[6])
                raise RuntimeError("synthetic late transaction failure after GRN service mutations")
        except RuntimeError as error:
            assert "synthetic late transaction failure" in str(error)

    async with AsyncSessionLocal() as verify:
        assert (await verify.get(GoodsReceipt, ids[0])).status == GRNStatus.DRAFT
        assert (await verify.get(GRNLine, ids[1])).stock_movement_id is None
        assert (await verify.get(PurchaseOrder, ids[2])).status == POStatus.ORDERED
        assert (await verify.get(POLine, ids[3])).received_quantity == Decimal("0.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == f"M05-T002-GRN-{suffix}")) == 0
        assert await verify.scalar(select(func.count(Stock.id)).where(Stock.material_id == ids[4], Stock.warehouse_id == ids[5])) == 0


@pytest.mark.asyncio
async def test_production_late_failure_rolls_back_consumption_output_and_order_completion():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        user, material, product, raw_wh, fg_wh, order, raw_stock = await _seed_production(db, suffix)
        ids = (order.id, raw_stock.id, material.id, product.id, raw_wh.id, fg_wh.id, user.id)
        order_no = order.order_no
        await db.commit()
        try:
            async with db.begin():
                await production_service.complete_order(
                    db, await db.get(ProductionOrder, ids[0]),
                    CompleteOrderRequest(actual_quantity=Decimal("4"), consume_materials=True), ids[6],
                )
                raise RuntimeError("synthetic late transaction failure after production service mutations")
        except RuntimeError as error:
            assert "synthetic late transaction failure" in str(error)

    async with AsyncSessionLocal() as verify:
        assert (await verify.get(ProductionOrder, ids[0])).status == ProductionOrderStatus.IN_PROGRESS
        assert (await verify.get(Stock, ids[1])).quantity_on_hand == Decimal("10.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == order_no)) == 0
        assert await verify.scalar(select(func.count(MaterialConsumption.id)).where(MaterialConsumption.production_order_id == ids[0])) == 0
        assert await verify.scalar(select(func.count(FinishedGoodsReceipt.id)).where(FinishedGoodsReceipt.production_order_id == ids[0])) == 0
        assert await verify.scalar(select(func.count(Stock.id)).where(Stock.product_id == ids[3], Stock.warehouse_id == ids[5])) == 0


@pytest.mark.asyncio
async def test_shipment_late_failure_rolls_back_stock_movement_and_sales_progress():
    _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        user, _, _, order, order_line, shipment, shipment_line, stock = await _seed_shipment(db, suffix)
        ids = (shipment.id, shipment_line.id, stock.id, order.id, order_line.id, user.id)
        shipment_no = shipment.shipment_no
        await db.commit()
        try:
            async with db.begin():
                await sales_service.dispatch_shipment(db, await db.get(Shipment, ids[0]), date(2026, 10, 30), ids[5])
                raise RuntimeError("synthetic late transaction failure after dispatch service mutations")
        except RuntimeError as error:
            assert "synthetic late transaction failure" in str(error)

    async with AsyncSessionLocal() as verify:
        assert (await verify.get(Shipment, ids[0])).status == ShipmentStatus.PACKED
        assert (await verify.get(ShipmentLine, ids[1])).stock_movement_id is None
        assert (await verify.get(SalesOrder, ids[3])).status == SOStatus.PICKING
        assert (await verify.get(SOLine, ids[4])).shipped_quantity == Decimal("0.000")
        persisted_stock = await verify.get(Stock, ids[2])
        assert persisted_stock.quantity_on_hand == Decimal("5.000")
        assert persisted_stock.quantity_reserved == Decimal("3.000")
        assert persisted_stock.quantity_available == Decimal("2.000")
        assert await verify.scalar(select(func.count(StockMovement.id)).where(StockMovement.reference_number == shipment_no)) == 0
