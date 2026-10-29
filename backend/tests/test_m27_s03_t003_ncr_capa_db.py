"""NCR/deviation to CAPA escalation linkage on task-owned disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    CorrectiveAction, CorrectiveActionStatus, DeviationStatus, ParameterType, QCDeviation, QCInspection,
    QCTestResult, QCType, RiskLevel,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.qms_service import (
    create_corrective_action,
    create_corrective_action_for_deviation,
    create_deviation,
    auto_create_deviation_from_inspection,
    link_deviation_corrective_action,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S03_T003_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s03_t003_[a-f0-9]{20,32}", expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


@pytest.mark.asyncio
async def test_high_deviations_escalate_to_one_linked_capa_and_medium_deviations_can_be_linked_once():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        reporter = User(
            email=f"reporter-{suffix}@synthetic.invalid", username=f"reporter-{suffix}",
            full_name="Synthetic deviation reporter", hashed_password="not-used",
        )
        product = Product(
            sku=f"M27-T003-P-{suffix}", name=f"Synthetic escalation product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T003-W-{suffix}", name=f"Synthetic escalation warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([reporter, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic escalation recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        now = datetime.now(timezone.utc)
        order = ProductionOrder(
            order_no=f"M27-T003-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("3"), uom="KG", status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id, scheduled_start=now, scheduled_end=now,
            batch_no=f"M27-T003-B-{suffix}",
        )
        lot = Lot(lot_number=f"M27-T003-L-{suffix}", product_id=product.id)
        db.add_all([order, lot])
        await db.flush()
        reporter_id, product_id, warehouse_id = reporter.id, product.id, warehouse.id
        order_id, lot_id = order.id, lot.id

        high = await create_deviation(db, {
            "deviation_type": "SYNTHETIC_HIGH_QC_DEVIATION", "severity": RiskLevel.HIGH,
            "description": "Synthetic high-severity deviation requiring immediate CAPA escalation.",
            "production_order_id": order_id, "lot_id": lot_id, "product_id": product_id,
        }, reporter_id)
        assert high.corrective_action_id is not None
        high_deviation_id, automatic_capa_id = high.id, high.corrective_action_id
        automatic_capa = await db.get(CorrectiveAction, automatic_capa_id)
        assert automatic_capa.trigger_type == "DEVIATION"
        assert automatic_capa.trigger_id == high_deviation_id
        assert automatic_capa.severity == RiskLevel.HIGH
        assert automatic_capa.production_order_id == order_id
        assert automatic_capa.lot_id == lot_id

        medium = await create_deviation(db, {
            "deviation_type": "SYNTHETIC_MEDIUM_QC_DEVIATION", "severity": RiskLevel.MEDIUM,
            "description": "Synthetic medium-severity deviation for a user-created CAPA link.",
            "production_order_id": order_id, "lot_id": lot_id, "product_id": product_id,
        }, reporter_id)
        medium_id = medium.id
        assert medium.corrective_action_id is None
        manual_capa = await create_corrective_action(db, {
            "title": "Synthetic medium deviation CAPA", "description": "Synthetic linked CAPA plan.",
            "severity": RiskLevel.MEDIUM, "trigger_type": "DEVIATION", "trigger_id": medium_id,
            "production_order_id": order_id, "lot_id": lot_id, "product_id": product_id,
        })
        assert medium.corrective_action_id == manual_capa.id
        assert manual_capa.trigger_id == medium_id

        with pytest.raises(ValueError, match="already has a linked CAPA"):
            await create_corrective_action_for_deviation(db, medium_id, {
                "title": "Synthetic duplicate", "description": "Must not create a second CAPA.",
                "severity": RiskLevel.MEDIUM,
            })
        under_scope = await create_deviation(db, {
            "deviation_type": "SYNTHETIC_UNLINKED_MEDIUM_QC_DEVIATION", "severity": RiskLevel.MEDIUM,
            "description": "Synthetic medium-severity deviation for severity-floor validation.",
            "production_order_id": order_id, "lot_id": lot_id, "product_id": product_id,
        }, reporter_id)
        with pytest.raises(ValueError, match="CAPA product_id must match"):
            await create_corrective_action_for_deviation(db, under_scope.id, {
                "title": "Synthetic mismatched CAPA", "description": "Cannot change product scope.",
                "product_id": uuid4(),
            })
        with pytest.raises(ValueError, match="cannot have lower severity"):
            await create_corrective_action_for_deviation(db, under_scope.id, {
                "title": "Synthetic under-scoped CAPA", "description": "Cannot downgrade severity.",
                "severity": RiskLevel.LOW,
            })
        verified_capa = await create_corrective_action(db, {
            "title": "Synthetic already-verified CAPA", "description": "Cannot reopen as an escalation.",
            "severity": RiskLevel.MEDIUM,
        })
        verified_capa.status = CorrectiveActionStatus.VERIFIED
        await db.flush()
        with pytest.raises(ValueError, match="verified CAPA cannot be linked"):
            await link_deviation_corrective_action(db, under_scope, verified_capa.id)
        assert await link_deviation_corrective_action(db, medium, manual_capa.id) is manual_capa
        assert (await db.execute(select(func.count()).select_from(CorrectiveAction).where(
            CorrectiveAction.trigger_type == "DEVIATION", CorrectiveAction.trigger_id == medium_id,
        ))).scalar_one() == 1

        inspection = QCInspection(
            inspection_no=f"M27-T003-QC-{suffix}", qc_type=QCType.IN_PROCESS,
            production_order_id=order_id, lot_id=lot_id, product_id=product_id,
            inspection_date=now.date(),
            test_results=[QCTestResult(
                parameter_name="Synthetic critical limit", parameter_type=ParameterType.NUMERIC,
                is_critical=True, is_passed=False,
            )],
        )
        db.add(inspection)
        await db.flush()
        inspection_deviation = await auto_create_deviation_from_inspection(db, inspection, reporter_id)
        assert inspection_deviation.severity == RiskLevel.CRITICAL
        assert inspection_deviation.corrective_action_id is not None
        inspection_capa = await db.get(CorrectiveAction, inspection_deviation.corrective_action_id)
        assert inspection_capa.trigger_type == "DEVIATION"
        assert inspection_capa.trigger_id == inspection_deviation.id
        assert inspection_capa.lot_id == lot_id
        await db.commit()
