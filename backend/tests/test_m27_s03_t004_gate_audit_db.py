"""Gate history durability, filtering, and immutability on task-owned PostgreSQL."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    LotQualityStatus, QualityGateAuditEvent, QualityGateDefinition, QualityGateSeverity,
    QCDecision, QCInspection, QCStatus, QCType, QCTemplate,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.qms_service import (
    PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
    ensure_production_quality_gates_pass,
)
from app.services.qms_service import FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT, release_lot

pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S03_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S03_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s03_t004_[a-f0-9]{20,32}", expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


@pytest.mark.asyncio
async def test_blocked_gate_history_survives_outer_rollback_is_scoped_and_append_only(monkeypatch):
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        actor = User(
            email=f"actor-{suffix}@synthetic.invalid", username=f"actor-{suffix}",
            full_name="Synthetic gate evaluator", hashed_password="not-used",
        )
        product = Product(
            sku=f"M27-T004-P-{suffix}", name=f"Synthetic gate product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T004-W-{suffix}", name=f"Synthetic gate warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic gate recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        now = datetime.now(timezone.utc)
        order = ProductionOrder(
            order_no=f"M27-T004-PO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id, scheduled_start=now, scheduled_end=now,
            batch_no=f"M27-T004-B-{suffix}",
        )
        template = QCTemplate(name=f"M27-T004-QC-{suffix}", qc_type=QCType.IN_PROCESS)
        db.add_all([order, template])
        await db.flush()
        gate = QualityGateDefinition(
            code=f"M27T004_{suffix.upper()}", name="Synthetic release gate", gate_type="QUALITY",
            trigger_event=PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, target_module="production",
            is_active=True, version=7, effective_from=date.today(), severity=QualityGateSeverity.HIGH,
            is_mandatory=True, waiver_allowed=False, required_templates=[template],
        )
        db.add(gate)
        await db.commit()
        order_id = order.id
        actor_id = actor.id
        gate_id = gate.id

        with pytest.raises(ValueError, match="has no accepted, passed inspection"):
            await ensure_production_quality_gates_pass(
                db, order, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, date.today(), actor_id=actor_id,
            )
        await db.rollback()

    async with AsyncSessionLocal() as audit_db:
        await _assert_task_database(audit_db)
        event = (await audit_db.execute(select(QualityGateAuditEvent).where(
            QualityGateAuditEvent.business_id == order_id,
            QualityGateAuditEvent.gate_definition_id == gate_id,
        ))).scalar_one()
        assert event.result == "BLOCKED"
        assert event.gate_code == f"M27T004_{suffix.upper()}"
        assert event.gate_version == 7
        assert event.required_template_name == f"M27-T004-QC-{suffix}"
        assert event.evaluated_by_id == actor_id

    from app.api.v1.endpoints import qms as qms_api

    monkeypatch.setattr(qms_api, "has_any_permission", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(qms_api, "can_modify_scope", lambda *_args, **_kwargs: True)
    async with AsyncSessionLocal() as api_db:
        events = await qms_api.list_quality_gate_audit_history(
            scope_type=None, scope_id=None, business_type="PRODUCTION_ORDER", business_id=order_id,
            gate_definition_id=gate_id, result="BLOCKED", limit=100, db=api_db, current_user=object(),
        )
        assert len(events) == 1
        assert events[0].id == event.id
        assert events[0].policy_snapshot["is_mandatory"] is True

    for statement in (
        "UPDATE quality_gate_audit_events SET reason = 'rewritten'",
        "DELETE FROM quality_gate_audit_events",
        "TRUNCATE quality_gate_audit_events",
    ):
        async with AsyncSessionLocal() as immutable_db:
            with pytest.raises(DBAPIError):
                await immutable_db.execute(text(statement))
                await immutable_db.commit()
            await immutable_db.rollback()


@pytest.mark.asyncio
async def test_lot_release_history_records_both_gate_pass_and_unresolved_inspection_block():
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        actor = User(
            email=f"release-{suffix}@synthetic.invalid", username=f"release-{suffix}",
            full_name="Synthetic lot release reviewer", hashed_password="not-used",
        )
        product = Product(
            sku=f"M27-T004-RP-{suffix}", name=f"Synthetic release product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse = Warehouse(
            code=f"M27-T004-RW-{suffix}", name=f"Synthetic release warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([actor, product, warehouse])
        await db.flush()
        recipe = Recipe(
            product_id=product.id, version="1", name=f"Synthetic release recipe {suffix}",
            status=RecipeStatus.APPROVED, is_active=True,
        )
        db.add(recipe)
        await db.flush()
        now = datetime.now(timezone.utc)
        order = ProductionOrder(
            order_no=f"M27-T004-RPO-{suffix}", product_id=product.id, recipe_id=recipe.id,
            planned_quantity=Decimal("2"), uom="KG", status=ProductionOrderStatus.PLANNED,
            target_warehouse_id=warehouse.id, scheduled_start=now, scheduled_end=now,
            batch_no=f"M27-T004-RB-{suffix}",
        )
        lot = Lot(lot_number=f"M27-T004-RL-{suffix}", product_id=product.id)
        template = QCTemplate(name=f"M27-T004-FG-{suffix}", qc_type=QCType.FINISHED_GOODS)
        db.add_all([order, lot, template])
        await db.flush()
        gate = QualityGateDefinition(
            code=f"M27T004R_{suffix.upper()}", name="Synthetic finished-goods release gate",
            gate_type="QUALITY", trigger_event=FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT,
            target_module="inventory", is_active=True, version=3, effective_from=date.today(),
            severity=QualityGateSeverity.HIGH, is_mandatory=True, waiver_allowed=False,
            required_templates=[template],
        )
        passed_inspection = QCInspection(
            inspection_no=f"M27-T004-PASS-{suffix}", qc_type=QCType.FINISHED_GOODS,
            status=QCStatus.PASSED, decision=QCDecision.ACCEPT, production_order_id=order.id,
            lot_id=lot.id, product_id=product.id, warehouse_id=warehouse.id, template=template,
            inspection_date=date.today(), is_mandatory=True, blocks_progression=True, release_required=True,
        )
        unresolved_inspection = QCInspection(
            inspection_no=f"M27-T004-PENDING-{suffix}", qc_type=QCType.IN_PROCESS,
            status=QCStatus.PENDING, decision=None, production_order_id=order.id,
            lot_id=lot.id, product_id=product.id, warehouse_id=warehouse.id,
            inspection_date=date.today(), is_mandatory=True, blocks_progression=True, release_required=True,
        )
        db.add_all([gate, passed_inspection, unresolved_inspection])
        db.add(LotQualityStatus(lot_id=lot.id))
        await db.commit()
        lot_id, actor_id = lot.id, actor.id

        with pytest.raises(ValueError, match="mandatory quality inspection is unresolved"):
            await release_lot(db, lot_id, actor_id, "Synthetic release blocked by pending inspection")
        await db.rollback()

    async with AsyncSessionLocal() as audit_db:
        await _assert_task_database(audit_db)
        events = list((await audit_db.execute(select(QualityGateAuditEvent).where(
            QualityGateAuditEvent.scope_type == "LOT",
            QualityGateAuditEvent.scope_id == lot_id,
        ))).scalars())
        assert {event.result for event in events} == {"PASS", "BLOCKED"}
        assert len({event.evaluation_id for event in events}) == 1
        assert all(event.evaluated_by_id == actor_id for event in events)


@pytest.mark.asyncio
async def test_no_mandatory_gate_is_recorded_as_no_gate():
    from types import SimpleNamespace

    order_id = uuid4()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        await ensure_production_quality_gates_pass(
            db, SimpleNamespace(id=order_id, order_no="SYNTHETIC-NO-GATE"),
            PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, date.today(), actor_id=None,
        )
        await db.rollback()

    async with AsyncSessionLocal() as audit_db:
        event = (await audit_db.execute(select(QualityGateAuditEvent).where(
            QualityGateAuditEvent.business_id == order_id,
            QualityGateAuditEvent.result == "NO_GATE",
        ))).scalar_one()
        assert event.gate_code == "NO_ACTIVE_GATE"
        assert event.gate_version == 0
