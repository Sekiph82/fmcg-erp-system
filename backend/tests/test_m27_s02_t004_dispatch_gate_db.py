"""Dispatch-gate integration on the task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot, MovementType, Stock, StockMovement, StockType
from app.models.master import (
    Product, ProductCategory, UnitOfMeasure, Warehouse,
    WarehouseType,
)
from app.models.production import FinishedGoodsReceipt, ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    QCDecision, QCInspection, QCStatus, QCType, QCTestResult, QCTemplate,
    QCTemplateParameter, ParameterType,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.sales import (
    Customer, CustomerChannel, SOStatus, SOLine, SalesOrder, Shipment, ShipmentLine,
    ShipmentStatus,
)
from app.models.user import User
from app.services.qms_service import create_quality_gate_definition
from app.services.quality_service import (
    create_qc_for_order, make_decision, release_qc_quarantine,
)
from app.services.sales_service import dispatch_shipment


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S02_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S02_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s02_t004_[a-f0-9]{20,32}", expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


async def _make_finished_goods_template(db, suffix: str) -> QCTemplate:
    template = QCTemplate(
        name=f"Synthetic dispatch template {suffix}", qc_type=QCType.FINISHED_GOODS,
        is_mandatory=True, blocks_progression=True, release_required=True, is_active=True,
    )
    db.add(template)
    await db.flush()
    db.add(QCTemplateParameter(
        template_id=template.id, parameter_name=f"Synthetic dispatch weight {suffix}",
        parameter_type=ParameterType.NUMERIC, unit="KG", target_value="10",
        min_value=Decimal("9"), max_value=Decimal("11"), is_critical=True,
    ))
    await db.flush()
    return template


async def _accept_template_inspection(db, inspection_id, user_id) -> None:
    inspection = await db.get(QCInspection, inspection_id)
    parameter = (await db.execute(
        select(QCTemplateParameter).where(QCTemplateParameter.template_id == inspection.template_id)
    )).scalar_one()
    db.add(QCTestResult(
        inspection_id=inspection.id, template_parameter_id=parameter.id,
        parameter_name=parameter.parameter_name, parameter_type=parameter.parameter_type,
        unit=parameter.unit, numeric_value=Decimal("10"), min_spec=parameter.min_value,
        max_spec=parameter.max_value, is_passed=True, is_critical=parameter.is_critical,
        tested_by_id=user_id,
    ))
    await db.flush()
    await make_decision(
        db, inspection, QCDecision.ACCEPT, user_id,
        "Synthetic dispatch QC accepted", False, False,
    )
    await db.commit()


@pytest.mark.asyncio
async def test_dispatch_is_atomic_until_linked_finished_goods_qc_passes():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        user = User(
            email=f"m27-t004-{suffix}@example.invalid", username=f"m27t004{suffix}",
            full_name=f"Synthetic M27 T004 user {suffix}",
            hashed_password="synthetic-test-only-not-a-credential",
        )
        customer = Customer(
            code=f"M27-T004-C-{suffix}", name=f"Synthetic customer {suffix}",
            channel=CustomerChannel.WHOLESALE,
        )
        product = Product(
            sku=f"M27-T004-P-{suffix}", name=f"Synthetic dispatch product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T004-W-{suffix}", name=f"Synthetic dispatch warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([user, customer, product, warehouse])
        await db.flush()

        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        order = ProductionOrder(
            order_no=f"M27-T004-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("10"), actual_quantity=Decimal("10"), uom="KG",
            status=ProductionOrderStatus.COMPLETED, target_warehouse_id=warehouse.id,
            scheduled_start=datetime.now(timezone.utc), scheduled_end=datetime.now(timezone.utc),
            actual_start=datetime.now(timezone.utc), actual_end=datetime.now(timezone.utc),
            batch_no=f"M27-T004-B-{suffix}", created_by=user.id,
        )
        db.add(order)
        await db.flush()
        lot = Lot(
            product_id=product.id, lot_number=f"M27-T004-LOT-{suffix}",
            batch_number=order.batch_no, manufacture_date=date.today(),
        )
        db.add(lot)
        await db.flush()

        receipt_movement = StockMovement(
            reference_number=f"M27-T004-RECEIPT-{suffix}", movement_type=MovementType.RECEIPT,
            stock_type=StockType.PRODUCT, movement_date=date.today(), product_id=product.id,
            lot_id=lot.id, destination_warehouse_id=warehouse.id,
            quantity=Decimal("10"), created_by_id=user.id,
        )
        stock = Stock(
            stock_type=StockType.PRODUCT, warehouse_id=warehouse.id, product_id=product.id,
            lot_id=lot.id, quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
            quantity_available=Decimal("10"), is_blocked=False,
        )
        db.add_all([receipt_movement, stock])
        await db.flush()
        receipt = FinishedGoodsReceipt(
            production_order_id=order.id, product_id=product.id, quantity=Decimal("10"),
            uom="KG", lot_number=lot.lot_number, batch_no=order.batch_no,
            warehouse_id=warehouse.id, stock_movement_id=receipt_movement.id,
        )
        sales_order = SalesOrder(
            order_no=f"M27-T004-SO-{suffix}", customer_id=customer.id,
            order_date=date.today(), requested_delivery_date=date.today(),
            status=SOStatus.PICKING, warehouse_id=warehouse.id, created_by_id=user.id,
        )
        db.add_all([receipt, sales_order])
        await db.flush()
        sales_line = SOLine(
            so_id=sales_order.id, line_no=1, product_id=product.id,
            ordered_quantity=Decimal("3"), unit="KG", unit_price=Decimal("2"),
            allocated_quantity=Decimal("3"), shipped_quantity=Decimal("0"),
        )
        shipment = Shipment(
            shipment_no=f"M27-T004-SHIP-{suffix}", so_id=sales_order.id,
            warehouse_id=warehouse.id, status=ShipmentStatus.PACKED,
            scheduled_date=date.today(), created_by_id=user.id,
        )
        db.add_all([sales_line, shipment])
        await db.flush()
        shipment_line = ShipmentLine(
            shipment_id=shipment.id, so_line_id=sales_line.id, product_id=product.id,
            lot_id=lot.id, quantity=Decimal("3"), unit="KG",
        )
        template = await _make_finished_goods_template(db, suffix)
        await create_quality_gate_definition(db, {
            "code": f"M27T004_{suffix}", "name": f"Synthetic dispatch gate {suffix}",
            "gate_type": "FINISHED_GOODS_DISPATCH_QUALITY", "trigger_event": "on_dispatch",
            "target_module": " SALES ", "effective_from": date.today(), "is_active": True,
            "is_mandatory": True, "required_template_ids": [template.id],
        })
        db.add(shipment_line)
        await db.flush()

        user_id, order_id, lot_id = user.id, order.id, lot.id
        product_id, warehouse_id = product.id, warehouse.id
        lot_number, batch_no = lot.lot_number, order.batch_no
        shipment_id, shipment_line_id, stock_id = shipment.id, shipment_line.id, stock.id
        shipment_no = shipment.shipment_no
        await db.commit()

        shipment = await db.get(Shipment, shipment_id)
        with pytest.raises(HTTPException, match="required template") as raised:
            await dispatch_shipment(db, shipment, date.today(), user_id)
        assert raised.value.status_code == 422
        await db.rollback()
        assert (await db.get(Shipment, shipment_id)).status == ShipmentStatus.PACKED
        assert (await db.get(Stock, stock_id)).quantity_on_hand == Decimal("10")
        assert (await db.execute(select(func.count()).select_from(StockMovement).where(
            StockMovement.reference_number == shipment_no,
        ))).scalar_one() == 0

        inspection = await create_qc_for_order(
            db, production_order_id=order_id, product_id=product_id,
            warehouse_id=warehouse_id, lot_number=lot_number, batch_no=batch_no,
            inspection_no=f"M27-T004-FG-QC-{suffix}", inspector_id=user_id,
            qc_type=QCType.FINISHED_GOODS,
        )
        inspection_id = inspection.id
        await db.commit()
        assert (await db.get(Stock, stock_id)).is_blocked is True
        await _accept_template_inspection(db, inspection_id, user_id)
        inspection = await db.get(QCInspection, inspection_id)
        await release_qc_quarantine(db, inspection, user_id, "Finished-goods release accepted")
        await db.commit()

        shipment = await db.get(Shipment, shipment_id)
        await dispatch_shipment(db, shipment, date.today(), user_id)
        await db.commit()
        assert (await db.get(Shipment, shipment_id)).status == ShipmentStatus.DISPATCHED
        remaining_stock = await db.get(Stock, stock_id)
        assert remaining_stock.quantity_on_hand == Decimal("7")
        assert remaining_stock.quantity_available == Decimal("7")
        movement = (await db.execute(select(StockMovement).where(
            StockMovement.reference_number == shipment_no,
            StockMovement.movement_type == MovementType.ISSUE,
        ))).scalar_one()
        assert movement.lot_id == lot_id
        assert movement.quantity == Decimal("3")
        assert (await db.get(ShipmentLine, shipment_line_id)).stock_movement_id == movement.id
