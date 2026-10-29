"""Production gate checks against the task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import FinishedGoodsReceipt, ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    QCDecision, QCInspection, QCStatus, QCType, QCTemplate, QCTemplateParameter, ParameterType,
)
from app.models.recipe import Recipe, RecipeStatus
from app.services import production_service
from app.services.qms_service import (
    PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
    PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
    create_quality_gate_definition,
    ensure_production_quality_gates_pass,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S02_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S02_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s02_t002_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(select(func.current_database()))).scalar_one()
    assert actual == expected


async def _template(db, name: str) -> QCTemplate:
    template = QCTemplate(
        name=name,
        qc_type=QCType.IN_PROCESS,
        is_mandatory=True,
        blocks_progression=True,
        release_required=True,
        is_active=True,
    )
    db.add(template)
    await db.flush()
    db.add(QCTemplateParameter(
        template_id=template.id,
        parameter_name=f"Synthetic parameter {name}",
        parameter_type=ParameterType.NUMERIC,
        target_value="12",
        min_value=Decimal("10"),
        max_value=Decimal("14"),
        is_critical=True,
    ))
    await db.flush()
    return template


@pytest.mark.asyncio
async def test_configured_production_gates_block_transitions_until_each_template_passes():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        product = Product(
            sku=f"M27-T002-P-{suffix}", name=f"Synthetic production product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T002-W-{suffix}", name=f"Synthetic production warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic approved recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        order = ProductionOrder(
            order_no=f"M27-T002-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id,
            scheduled_start=datetime.now(timezone.utc),
            scheduled_end=datetime.now(timezone.utc),
            batch_no=f"M27-T002-B-{suffix}",
        )
        db.add(order)
        await db.flush()
        order_id = order.id

        release_template = await _template(db, f"Synthetic release QC {suffix}")
        process_template = await _template(db, f"Synthetic completion QC {suffix}")
        release_template_id = release_template.id
        process_template_id = process_template.id
        product_id = product.id
        warehouse_id = warehouse.id
        batch_no = order.batch_no
        for index, (event, template) in enumerate((
            (PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, release_template),
            (PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, process_template),
        )):
            await create_quality_gate_definition(db, {
                "code": f"M27T002_{index}_{suffix}",
                "name": f"Synthetic production gate {index} {suffix}",
                "gate_type": "IN_PROCESS_QUALITY",
                "trigger_event": event.lower(),
                "target_module": " Production ",
                "effective_from": date.today(),
                "is_active": True,
                "is_mandatory": True,
                "required_template_ids": [template.id],
            })
        await db.commit()

        with pytest.raises(HTTPException) as release_error:
            await production_service.release_order(db, order)
        assert release_error.value.status_code == 422
        assert "accepted, passed inspection" in release_error.value.detail
        await db.rollback()
        order = await db.get(ProductionOrder, order_id)
        assert order.status == ProductionOrderStatus.PLANNED

        db.add(QCInspection(
            inspection_no=f"M27-T002-QC-R-{suffix}", qc_type=QCType.IN_PROCESS,
            status=QCStatus.PASSED, decision=QCDecision.ACCEPT,
            production_order_id=order_id, template_id=release_template_id,
            product_id=product_id, warehouse_id=warehouse_id, batch_no=batch_no,
            inspection_date=date.today(), is_mandatory=True,
            blocks_progression=True, release_required=True,
        ))
        await db.commit()
        order = await db.get(ProductionOrder, order_id)
        await ensure_production_quality_gates_pass(
            db, order, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, date.today()
        )
        await production_service.release_order(db, order)
        assert order.status == ProductionOrderStatus.RELEASED

        order.status = ProductionOrderStatus.IN_PROGRESS
        actual_start = datetime.now(timezone.utc) - timedelta(minutes=2)
        order.actual_start = actual_start
        await db.commit()
        order = await db.get(ProductionOrder, order_id)
        db.add(QCInspection(
            inspection_no=f"M27-T002-QC-EARLY-{suffix}", qc_type=QCType.IN_PROCESS,
            status=QCStatus.PASSED, decision=QCDecision.ACCEPT,
            production_order_id=order_id, template_id=process_template_id,
            product_id=product_id, warehouse_id=warehouse_id, batch_no=batch_no,
            inspection_date=date.today(), is_mandatory=True,
            blocks_progression=True, release_required=True,
            created_at=actual_start - timedelta(seconds=30),
        ))
        await db.commit()
        with pytest.raises(HTTPException) as process_error:
            await production_service.complete_order(
                db, order, SimpleNamespace(actual_quantity=Decimal("2")), uuid4(),
            )
        assert process_error.value.status_code == 422
        assert "accepted, passed inspection" in process_error.value.detail
        await db.rollback()
        assert (await db.get(ProductionOrder, order_id)).status == ProductionOrderStatus.IN_PROGRESS
        assert (await db.execute(select(func.count()).select_from(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order_id,
        ))).scalar_one() == 0

        db.add(QCInspection(
            inspection_no=f"M27-T002-QC-P-{suffix}", qc_type=QCType.IN_PROCESS,
            status=QCStatus.PASSED, decision=QCDecision.ACCEPT,
            production_order_id=order_id, template_id=process_template_id,
            product_id=product_id, warehouse_id=warehouse_id, batch_no=batch_no,
            inspection_date=date.today(), is_mandatory=True,
            blocks_progression=True, release_required=True,
        ))
        await db.commit()
        await ensure_production_quality_gates_pass(
            db, await db.get(ProductionOrder, order_id), PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, date.today()
        )
        await db.rollback()
