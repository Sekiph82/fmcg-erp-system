"""Waiver lifecycle and gate enforcement against the task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    DeviationStatus, QCDecision, QCDeviation, QCInspection, QCStatus, QCType,
    QCTemplate, QCTemplateParameter, ParameterType, QualityGateWaiver,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.qms_service import (
    create_quality_gate_definition,
    decide_quality_gate_waiver,
    ensure_finished_goods_quality_gates_pass,
    has_active_quality_gate_waiver,
    request_quality_gate_waiver,
    revoke_quality_gate_waiver,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S03_T002_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S03_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s03_t002_[a-f0-9]{20,32}", expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


@pytest.mark.asyncio
async def test_noncritical_waiver_requires_independent_approval_expires_and_never_clears_failed_qc():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        requester = User(
            email=f"requester-{suffix}@synthetic.invalid", username=f"requester-{suffix}",
            full_name="Synthetic QA requester", hashed_password="not-used",
        )
        reviewer = User(
            email=f"reviewer-{suffix}@synthetic.invalid", username=f"reviewer-{suffix}",
            full_name="Synthetic QA reviewer", hashed_password="not-used",
        )
        product = Product(
            sku=f"M27-T002-P-{suffix}", name=f"Synthetic waiver product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T002-W-{suffix}", name=f"Synthetic waiver warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([requester, reviewer, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic approved recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        now = datetime.now(timezone.utc)
        order = ProductionOrder(
            order_no=f"M27-T002-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id, scheduled_start=now, scheduled_end=now,
            batch_no=f"M27-T002-B-{suffix}",
        )
        lot = Lot(lot_number=f"M27-T002-L-{suffix}", product_id=product.id)
        db.add_all([order, lot])
        await db.flush()
        deviation = QCDeviation(
            deviation_no=f"M27-T002-DEV-{suffix}", deviation_type="SYNTHETIC_QC_GAP",
            status=DeviationStatus.OPEN, description="Synthetic missing QC gate evidence",
            production_order_id=order.id, lot_id=lot.id, reported_by_id=requester.id,
        )
        template = QCTemplate(
            name=f"Synthetic FG gate {suffix}", qc_type=QCType.FINISHED_GOODS,
            is_mandatory=True, blocks_progression=True, release_required=True, is_active=True,
        )
        db.add_all([deviation, template])
        await db.flush()
        db.add(QCTemplateParameter(
            template_id=template.id, parameter_name="Synthetic acidity", parameter_type=ParameterType.NUMERIC,
            target_value="4", min_value=Decimal("3"), max_value=Decimal("5"), is_critical=False,
        ))
        await db.flush()
        gate = await create_quality_gate_definition(db, {
            "code": f"M27T002_{suffix}", "name": f"Synthetic waiver gate {suffix}",
            "gate_type": "FINISHED_GOODS_QUALITY", "trigger_event": "ON_FINISHED_GOODS_RELEASE",
            "target_module": "inventory", "effective_from": date.today(), "is_active": True,
            "is_mandatory": True, "severity": "MEDIUM", "waiver_allowed": True,
            "waiver_reason_required": True, "waiver_approval_required": True,
            "required_template_ids": [template.id],
        })
        gate_id, deviation_id, lot_id = gate.id, deviation.id, lot.id
        order_id, product_id, warehouse_id, template_id = order.id, product.id, warehouse.id, template.id
        requester_id, reviewer_id = requester.id, reviewer.id
        lot_number = lot.lot_number
        await db.commit()

        inspection_context = SimpleNamespace(
            production_order_id=order_id, lot_id=lot_id, lot_number=lot_number,
        )
        with pytest.raises(ValueError, match="no accepted, passed inspection"):
            await ensure_finished_goods_quality_gates_pass(db, inspection_context, date.today())
        await db.rollback()

        waiver = await request_quality_gate_waiver(db, {
            "gate_definition_id": gate_id, "deviation_id": deviation_id, "scope_type": "LOT",
            "scope_id": lot_id, "reason": "Synthetic temporary evidence-system outage",
        }, requester_id)
        waiver_id = waiver.id
        await db.commit()
        assert waiver.status == "PENDING"

        with pytest.raises(ValueError, match="requester cannot approve"):
            await decide_quality_gate_waiver(db, waiver_id, "APPROVE", requester_id)
        await db.rollback()
        waiver = await decide_quality_gate_waiver(db, waiver_id, "APPROVE", reviewer_id, "Reviewed synthetic controls")
        assert waiver.status == "APPROVED"
        assert waiver.expires_at == waiver.decided_at + timedelta(hours=24)
        await db.commit()

        linked_deviation = await db.get(QCDeviation, deviation_id)
        linked_deviation.status = DeviationStatus.CLOSED
        await db.commit()
        await ensure_finished_goods_quality_gates_pass(db, inspection_context, date.today())
        assert not await has_active_quality_gate_waiver(
            db, gate_id, "LOT", lot_id, as_of=waiver.expires_at + timedelta(seconds=1)
        )

        db.add(QCInspection(
            inspection_no=f"M27-T002-QC-FAIL-{suffix}", qc_type=QCType.FINISHED_GOODS,
            status=QCStatus.FAILED, decision=QCDecision.REJECT,
            production_order_id=order_id, lot_id=lot_id, product_id=product_id,
            warehouse_id=warehouse_id, template_id=template_id, inspection_date=date.today(),
            is_mandatory=True, blocks_progression=True, release_required=True,
        ))
        await db.commit()
        with pytest.raises(ValueError, match="still unresolved"):
            await ensure_finished_goods_quality_gates_pass(db, inspection_context, date.today())
        await db.rollback()

        waiver = await revoke_quality_gate_waiver(db, waiver_id, reviewer_id, "Synthetic hold restored")
        assert waiver.status == "REVOKED"
        assert waiver.decided_by_id == reviewer_id
        assert waiver.revoked_by_id == reviewer_id
        await db.commit()
        assert (await db.execute(select(QualityGateWaiver.status).where(
            QualityGateWaiver.id == waiver_id,
        ))).scalar_one() == "REVOKED"
