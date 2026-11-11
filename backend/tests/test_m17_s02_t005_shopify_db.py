"""M17.S02.T005 — Shopify order import and inventory push on disposable PostgreSQL (mocked Admin API)."""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.integrations import EcommerceOrderMapping, EcommerceProductMapping, SyncStatus
from app.models.inventory import Lot, Stock, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.sales import Customer, CustomerChannel, OrderSource, PaymentMethod, SalesOrder, SOLine, SOStatus
from app.models.user import User
from app.services import shopify_service
from test_shopify_client import make_order

TASK_DB_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m17_s02_t005_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _stock(warehouse, product, available, **kw):
    return Stock(stock_type=StockType.PRODUCT, warehouse_id=warehouse.id, product_id=product.id,
                 quantity_on_hand=max(available, Decimal("0")), quantity_reserved=Decimal("0"),
                 quantity_available=available, **kw)


@pytest.mark.asyncio
async def test_orders_import_once_as_draft_sales_orders_and_stock_is_pushed(monkeypatch):
    s = uuid4().hex[:10]
    sku, late_sku = f"SKU-{s}", f"LATE-{s}"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        user = User(email=f"shop-{s}@example.invalid", username=f"shop{s}", full_name="Synthetic", hashed_password="x")
        customer = Customer(code=f"WEB-{s}", name="Synthetic web store", channel=CustomerChannel.WHOLESALE, currency="KES")
        warehouse = Warehouse(code=f"WEB-W-{s}", name="Synthetic web warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
        product = Product(sku=sku, name="Synthetic juice", category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS)
        db.add_all([user, customer, warehouse, product])
        await db.flush()
        quarantined = Lot(lot_number=f"Q-{s}", product_id=product.id, is_quarantine=True)
        expired = Lot(lot_number=f"X-{s}", product_id=product.id, expiry_date=date.today() - timedelta(days=1))
        good_lot = Lot(lot_number=f"G-{s}", product_id=product.id, expiry_date=date.today() + timedelta(days=90))
        db.add_all([quarantined, expired, good_lot])
        await db.flush()
        db.add_all([
            _stock(warehouse, product, Decimal("35.6")),                      # unlotted, sellable
            _stock(warehouse, product, Decimal("4"), lot_id=good_lot.id),     # in-date lot, sellable
            _stock(warehouse, product, Decimal("-3"), lot_id=good_lot.id),    # negative row must not net off
            _stock(warehouse, product, Decimal("10"), is_blocked=True),       # blocked
            _stock(warehouse, product, Decimal("7"), lot_id=quarantined.id),  # quarantined lot
            _stock(warehouse, product, Decimal("6"), lot_id=expired.id),      # expired lot
        ])
        await db.commit()
        ids = (user.id, customer.id, warehouse.id, product.id)

    monkeypatch.setattr(settings, "SHOPIFY_CUSTOMER_ID", str(ids[1]))
    monkeypatch.setattr(settings, "SHOPIFY_WAREHOUSE_ID", str(ids[2]))
    monkeypatch.setattr(settings, "SHOPIFY_LOCATION_ID", "777")
    base = int(s[:6], 16) % 100000
    good = make_order(base, line_items=[
        {"id": 1, "sku": sku, "quantity": 3, "price": "150.00", "total_discount": "10.00", "tax_lines": [{"rate": 0.16}]},
        {"id": 9, "sku": "REFUNDED-NOT-IN-ERP", "quantity": 1, "current_quantity": 0, "price": "5"},
    ])
    inclusive = make_order(base + 1, taxes_included=True, financial_status="pending",
                           line_items=[{"id": 3, "sku": sku, "quantity": 1, "price": "116.00", "tax_lines": [{"rate": 0.16}]}])
    unknown = make_order(base + 2, line_items=[{"id": 2, "sku": late_sku, "quantity": 1, "price": "9"}])
    cancelled = make_order(base + 3, cancelled_at="2026-11-10T09:00:00Z")
    broken = {**make_order(base + 4, line_items=[{"id": 4, "sku": sku, "quantity": 1, "price": "1"}]), "created_at": None}
    # same Shopify order name as `good` but another order id: SHOP-<name> is taken, recorded FAILED
    dup = {**make_order(base, line_items=[{"id": 5, "sku": sku, "quantity": 1, "price": "1"}]), "id": f"{1000 + base}9"}
    posted = []

    def handler(request: httpx.Request):
        path = request.url.path
        if path.endswith("/orders.json"):  # Shopify returns newest first
            return httpx.Response(200, json={"orders": [broken, dup, cancelled, unknown, inclusive, good]})
        if path.endswith("/products.json"):
            return httpx.Response(200, json={"products": [{"id": 5, "variants": [
                {"id": 51, "sku": sku, "inventory_item_id": 9001}, {"id": 52, "sku": "OTHER", "inventory_item_id": 9002}]}]})
        if path.endswith("/inventory_levels/set.json"):
            posted.append(json.loads(request.content))
            return httpx.Response(200, json={})
        return httpx.Response(404)

    async def run(fn, *args):
        client = shopify_service.ShopifyClient("synthetic-store.myshopify.com", "t", "2024-10", httpx.MockTransport(handler))
        try:
            out = await fn(db, client, *args)
            await db.commit()
            return out
        finally:
            await client.aclose()

    async def so_for(order):
        return (await db.execute(select(SalesOrder).where(
            SalesOrder.order_no == f"SHOP-{order['name'].lstrip('#')}"))).scalar_one_or_none()

    async def mapping_for(order):
        return (await db.execute(select(EcommerceOrderMapping).where(
            EcommerceOrderMapping.source_platform == "SHOPIFY",
            EcommerceOrderMapping.external_order_id == str(order["id"])))).scalar_one()

    async with AsyncSessionLocal() as db:
        result = await run(shopify_service.import_orders, None, ids[0])
        # good + inclusive imported; unknown SKU, malformed order and order-number clash FAILED; cancelled skipped
        assert (result.imported, result.failed, result.skipped) == (2, 3, 1), result.errors
        assert (await mapping_for(dup)).sync_status == SyncStatus.FAILED
        assert any(late_sku in e for e in result.errors) and any("Could not import" in e for e in result.errors)

        so = await so_for(good)
        assert so.status == SOStatus.DRAFT and so.customer_id == ids[1] and so.warehouse_id == ids[2]
        assert so.source == OrderSource.ECOMMERCE and so.payment_method == PaymentMethod.BANK_TRANSFER
        line = (await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalar_one()  # refunded line dropped
        assert (line.ordered_quantity, line.unit_price, line.tax_rate) == (Decimal("3"), Decimal("146.6667"), Decimal("16.00"))
        so2 = await so_for(inclusive)
        line2 = (await db.execute(select(SOLine).where(SOLine.so_id == so2.id))).scalar_one()
        assert line2.unit_price == Decimal("100.0000") and so2.payment_method == PaymentMethod.CREDIT  # net of 16% VAT
        assert (await mapping_for(good)).so_id == so.id
        failed = await mapping_for(unknown)
        assert failed.sync_status == SyncStatus.FAILED and failed.so_id is None
        assert (await mapping_for(broken)).sync_status == SyncStatus.FAILED

        again = await run(shopify_service.import_orders, None, ids[0])
        assert (again.imported, again.skipped) == (0, 3)  # synced orders and the cancelled one are not re-imported
        assert await so_for(unknown) is None

        db.add(Product(sku=late_sku, name="Late SKU", category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS))
        await db.commit()
        retry = await run(shopify_service.import_orders, None, ids[0])
        assert retry.imported == 1  # the FAILED order is retried in place once its SKU exists
        retried = await mapping_for(unknown)
        await db.refresh(retried)
        assert retried.sync_status == SyncStatus.SYNCED and retried.error_message is None
        assert retried.so_id == (await so_for(unknown)).id

        inventory = await run(shopify_service.sync_inventory)
        assert (inventory.synced, inventory.unmatched, inventory.failed) == (1, 1, 0)
        # 35.6 unlotted + 4 in-date lot = 39.6 -> 39; blocked, quarantined, expired and negative rows excluded
        assert posted == [{"location_id": 777, "inventory_item_id": 9001, "available": 39}]
        mapping = (await db.execute(select(EcommerceProductMapping).where(
            EcommerceProductMapping.external_product_id == "51"))).scalar_one()
        assert mapping.product_id == ids[3] and mapping.sync_status == SyncStatus.SYNCED
