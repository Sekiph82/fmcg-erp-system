"""Quality-to-inventory-to-sales blocking integration on a disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot, MovementType, Stock, StockMovement, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.quality import LotQualityStatus
from app.models.sales import (
    Customer, CustomerChannel, SOStatus, SOLine, SalesOrder, Shipment, ShipmentLine,
    ShipmentStatus,
)
from app.models.user import User
from app.services.qms_service import hold_lot
from app.services.sales_service import dispatch_shipment


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S04_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S04_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s04_t002_[a-f0-9]{20}", expected)
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


@pytest.mark.asyncio
async def test_quality_hold_blocks_sales_dispatch_without_sales_or_stock_issue_mutations():
    suffix = uuid4().hex[:16]
    shipment_no = f"M27-S04-T002-SHIP-{suffix}"
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        user = User(
            email=f"m27-s04-t002-{suffix}@example.invalid",
            username=f"m27s04t002{suffix}",
            full_name=f"Synthetic M27 S04 T002 user {suffix}",
            hashed_password="synthetic-test-only-not-a-credential",
        )
        customer = Customer(
            code=f"M27-S04-T002-C-{suffix}",
            name=f"Synthetic customer {suffix}",
            channel=CustomerChannel.WHOLESALE,
        )
        product = Product(
            sku=f"M27-S04-T002-P-{suffix}",
            name=f"Synthetic product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-S04-T002-W-{suffix}",
            name=f"Synthetic finished-goods warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([user, customer, product, warehouse])
        await db.flush()

        order = SalesOrder(
            order_no=f"M27-S04-T002-SO-{suffix}",
            customer_id=customer.id,
            order_date=date.today(),
            requested_delivery_date=date.today(),
            status=SOStatus.PICKING,
            warehouse_id=warehouse.id,
            created_by_id=user.id,
        )
        lot = Lot(
            lot_number=f"M27-S04-T002-LOT-{suffix}",
            product_id=product.id,
            manufacture_date=date.today(),
        )
        db.add_all([order, lot])
        await db.flush()
        order_line = SOLine(
            so_id=order.id,
            line_no=1,
            product_id=product.id,
            ordered_quantity=Decimal("2"),
            unit="KG",
            unit_price=Decimal("3"),
            allocated_quantity=Decimal("2"),
        )
        shipment = Shipment(
            shipment_no=shipment_no,
            so_id=order.id,
            warehouse_id=warehouse.id,
            status=ShipmentStatus.PACKED,
            scheduled_date=date.today(),
            created_by_id=user.id,
        )
        stock = Stock(
            stock_type=StockType.PRODUCT,
            warehouse_id=warehouse.id,
            product_id=product.id,
            lot_id=lot.id,
            quantity_on_hand=Decimal("8"),
            quantity_reserved=Decimal("2"),
            quantity_available=Decimal("6"),
            is_blocked=False,
        )
        db.add_all([order_line, shipment, stock])
        await db.flush()
        shipment_line = ShipmentLine(
            shipment_id=shipment.id,
            so_line_id=order_line.id,
            product_id=product.id,
            lot_id=lot.id,
            quantity=Decimal("2"),
            unit="KG",
        )
        db.add(shipment_line)
        await db.flush()
        order_id, shipment_id = order.id, shipment.id
        shipment_line_id, stock_id = shipment_line.id, stock.id
        lot_id, user_id = lot.id, user.id
        await db.commit()

        # QMS applies the hold to inventory before the Sales dispatch transaction.
        await hold_lot(db, lot_id, "Synthetic unresolved mandatory QC hold")
        await db.commit()
        held_stock = await db.get(Stock, stock_id)
        assert held_stock.is_blocked is True
        assert held_stock.quantity_on_hand == Decimal("8.000")
        assert held_stock.quantity_reserved == Decimal("2.000")
        assert held_stock.quantity_available == Decimal("0.000")

        shipment = await db.get(Shipment, shipment_id)
        with pytest.raises(HTTPException, match="held, quarantined, or unreleased") as raised:
            await dispatch_shipment(db, shipment, date.today(), user_id)
        assert raised.value.status_code == 422
        await db.rollback()

        assert (await db.get(Shipment, shipment_id)).status == ShipmentStatus.PACKED
        assert (await db.get(SalesOrder, order_id)).status == SOStatus.PICKING
        assert (await db.get(ShipmentLine, shipment_line_id)).stock_movement_id is None
        final_stock = await db.get(Stock, stock_id)
        assert final_stock.quantity_on_hand == Decimal("8.000")
        assert final_stock.quantity_reserved == Decimal("2.000")
        assert final_stock.quantity_available == Decimal("0.000")
        assert final_stock.is_blocked is True
        assert (await db.execute(
            select(func.count()).select_from(StockMovement).where(
                StockMovement.reference_number == shipment_no,
                StockMovement.movement_type == MovementType.ISSUE,
            )
        )).scalar_one() == 0
        assert (await db.execute(
            select(func.count()).select_from(LotQualityStatus).where(
                LotQualityStatus.lot_id == lot_id,
                LotQualityStatus.hold_flag.is_(True),
            )
        )).scalar_one() == 1
