"""Finished-goods release gate checks on the task-owned disposable PostgreSQL database."""
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
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import FinishedGoodsReceipt, ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    QCDecision, QCInspection, QCStatus, QCType, QCTestResult, QCTemplate, QCTemplateParameter,
    ParameterType,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.qms_service import create_quality_gate_definition
from app.services.quality_service import create_qc_for_order, make_decision, release_qc_quarantine


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S02_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S02_T003_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s02_t003_[a-f0-9]{20,32}", expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


async def _make_template(db, name: str) -> QCTemplate:
    template = QCTemplate(
        name=name,
        qc_type=QCType.FINISHED_GOODS,
        is_mandatory=True,
        blocks_progression=True,
        release_required=True,
        is_active=True,
    )
    db.add(template)
    await db.flush()
    parameter = QCTemplateParameter(
        template_id=template.id,
        parameter_name=f"Synthetic weight {name}",
        parameter_type=ParameterType.NUMERIC,
        unit="KG",
        target_value="10",
        min_value=Decimal("9"),
        max_value=Decimal("11"),
        is_critical=True,
    )
    db.add(parameter)
    await db.flush()
    return template


async def _accept_template_inspection(db, inspection_id, user_id) -> None:
    inspection = await db.get(QCInspection, inspection_id)
    parameter = (await db.execute(
        select(QCTemplateParameter).where(QCTemplateParameter.template_id == inspection.template_id)
    )).scalar_one()
    db.add(QCTestResult(
        inspection_id=inspection.id,
        template_parameter_id=parameter.id,
        parameter_name=parameter.parameter_name,
        parameter_type=parameter.parameter_type,
        unit=parameter.unit,
        numeric_value=Decimal("10"),
        min_spec=parameter.min_value,
        max_spec=parameter.max_value,
        is_passed=True,
        is_critical=parameter.is_critical,
        tested_by_id=user_id,
    ))
    await db.flush()
    await make_decision(
        db, inspection, QCDecision.ACCEPT, user_id,
        "Synthetic template inspection accepted", False, False,
    )
    await db.commit()


@pytest.mark.asyncio
async def test_finished_goods_stock_stays_quarantined_until_every_gate_template_passes():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        user = User(
            email=f"m27-t003-{suffix}@example.invalid",
            username=f"m27t003{suffix}",
            full_name=f"Synthetic M27 T003 user {suffix}",
            hashed_password="synthetic-test-only-not-a-credential",
        )
        product = Product(
            sku=f"M27-T003-P-{suffix}", name=f"Synthetic finished product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T003-W-{suffix}", name=f"Synthetic finished warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([user, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic approved recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        order = ProductionOrder(
            order_no=f"M27-T003-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("10"), actual_quantity=Decimal("10"), uom="KG",
            status=ProductionOrderStatus.COMPLETED, target_warehouse_id=warehouse.id,
            scheduled_start=datetime.now(timezone.utc), scheduled_end=datetime.now(timezone.utc),
            actual_start=datetime.now(timezone.utc), actual_end=datetime.now(timezone.utc),
            batch_no=f"M27-T003-B-{suffix}", created_by=user.id,
        )
        db.add(order)
        await db.flush()
        lot = Lot(
            product_id=product.id, lot_number=f"M27-T003-LOT-{suffix}",
            batch_number=order.batch_no, manufacture_date=date.today(),
        )
        db.add(lot)
        await db.flush()
        movement = StockMovement(
            reference_number=f"M27-T003-RECEIPT-{suffix}", movement_type=MovementType.RECEIPT,
            stock_type=StockType.PRODUCT, movement_date=date.today(), product_id=product.id,
            lot_id=lot.id, destination_warehouse_id=warehouse.id,
            quantity=Decimal("10"), created_by_id=user.id,
        )
        stock = Stock(
            stock_type=StockType.PRODUCT, warehouse_id=warehouse.id, product_id=product.id,
            lot_id=lot.id, quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
            quantity_available=Decimal("10"), is_blocked=False,
        )
        db.add_all([movement, stock])
        await db.flush()
        receipt = FinishedGoodsReceipt(
            production_order_id=order.id, product_id=product.id, quantity=Decimal("10"),
            uom="KG", lot_number=lot.lot_number, batch_no=order.batch_no,
            warehouse_id=warehouse.id, stock_movement_id=movement.id,
        )
        db.add(receipt)
        template_ids = []
        for index in (1, 2):
            template = await _make_template(db, f"Synthetic release template {index} {suffix}")
            template_ids.append(template.id)
            await create_quality_gate_definition(db, {
                "code": f"M27T003_{index}_{suffix}",
                "name": f"Synthetic finished-goods release gate {index} {suffix}",
                "gate_type": "FINISHED_GOODS_QUALITY",
                "trigger_event": "on_finished_goods_release",
                "target_module": " Inventory ",
                "effective_from": date.today(),
                "is_active": True,
                "is_mandatory": True,
                "required_template_ids": [template.id],
            })
        order_id = order.id
        product_id = product.id
        warehouse_id = warehouse.id
        lot_id = lot.id
        lot_number = lot.lot_number
        batch_no = order.batch_no
        user_id = user.id
        await db.commit()

        primary = await create_qc_for_order(
            db, production_order_id=order_id, product_id=product_id,
            warehouse_id=warehouse_id, lot_number=lot_number,
            batch_no=batch_no, inspection_no=f"M27-T003-FG-QC-{suffix}",
            inspector_id=user_id, qc_type=QCType.FINISHED_GOODS,
        )
        primary_id = primary.id
        await db.commit()
        inspection_ids = list((await db.execute(
            select(QCInspection.id).where(
                QCInspection.production_order_id == order_id,
                QCInspection.lot_id == lot_id,
                QCInspection.qc_type == QCType.FINISHED_GOODS,
            ).order_by(QCInspection.template_id)
        )).scalars().all())
        assert len(inspection_ids) == 2
        inspections = list((await db.execute(
            select(QCInspection).where(QCInspection.id.in_(inspection_ids))
        )).scalars().all())
        assert {inspection.template_id for inspection in inspections} == set(template_ids)
        assert all(inspection.is_mandatory and inspection.quarantine_applied for inspection in inspections)
        assert stock.is_blocked is True
        remaining_id = next(item.id for item in inspections if item.id != primary_id)

        await _accept_template_inspection(db, primary_id, user_id)
        inspection = await db.get(QCInspection, primary_id)
        with pytest.raises(HTTPException, match="required QC template"):
            await release_qc_quarantine(db, inspection, user_id, "One required template remains pending")
        await db.rollback()
        stock = (await db.execute(select(Stock).where(
            Stock.warehouse_id == warehouse_id, Stock.lot_id == lot_id,
        ))).scalar_one()
        assert stock.is_blocked is True
        assert (await db.execute(select(func.count()).select_from(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order_id,
        ))).scalar_one() == 1

        await _accept_template_inspection(db, remaining_id, user_id)
        inspection = await db.get(QCInspection, primary_id)
        await release_qc_quarantine(db, inspection, user_id, "All synthetic gate templates passed")
        await db.commit()
        stock = (await db.execute(select(Stock).where(
            Stock.warehouse_id == warehouse_id, Stock.lot_id == lot_id,
        ))).scalar_one()
        assert stock.is_blocked is False
        assert stock.quantity_available == Decimal("10")
        assert (await db.execute(select(func.count()).select_from(QCInspection).where(
            QCInspection.production_order_id == order_id,
            QCInspection.lot_id == lot_id,
            QCInspection.quarantine_applied.is_(True),
        ))).scalar_one() == 0
        await db.rollback()
