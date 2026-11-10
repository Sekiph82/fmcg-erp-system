"""M22.S04.T003 cross-module PostgreSQL transaction regression."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.inventory import Lot, Stock, StockType
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.mps import MPSFeasibilityStatus, MPSLine, MPSPlan, MPSStatus
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_transition import ProductionTransitionEvent
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.user import User
from app.services.mps_service import release_mps_plan
from app.services.production_service import approve_order, release_order


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S04_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s04_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S04_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S04_T003_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S04.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s04_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s04_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s04_t003_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name),
        name,
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="not-used", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_mps_order_material_qc_and_transition_history_share_safe_boundaries():
    _require_task_database()
    suffix = uuid4().hex[:20]

    async with AsyncSessionLocal() as db:
        mps_actor = User(
            email=f"m22-s04-t003-mps-{suffix}@example.invalid",
            username=f"m22s04t003m{suffix}",
            full_name=f"Synthetic MPS releaser {suffix}",
            hashed_password="test-only",
        )
        approver = User(
            email=f"m22-s04-t003-approver-{suffix}@example.invalid",
            username=f"m22s04t003a{suffix}",
            full_name=f"Synthetic production approver {suffix}",
            hashed_password="test-only",
        )
        source = Warehouse(
            code=f"M22-S04-T003-S-{suffix}",
            name=f"Synthetic MRP source {suffix}",
            warehouse_type=WarehouseType.RAW_MATERIAL,
        )
        target = Warehouse(
            code=f"M22-S04-T003-T-{suffix}",
            name=f"Synthetic production target {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        product = Product(
            sku=f"M22-S04-T003-P-{suffix}",
            name=f"Synthetic scheduled product {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        material = Material(
            code=f"M22-S04-T003-M-{suffix}",
            name=f"Synthetic scheduled input {suffix}",
            material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
            is_active=True,
        )
        db.add_all([mps_actor, approver, source, target, product, material])
        await db.flush()

        source_run = MRPRun(
            run_no=f"M22-S04-T003-R-{suffix}",
            run_date=date(2026, 11, 1),
            status=MRPRunStatus.COMPLETED,
            warehouse_id=source.id,
        )
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic cross-module recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add_all([source_run, recipe])
        await db.flush()

        recipe_item = RecipeItem(
            recipe_id=recipe.id,
            material_id=material.id,
            line_no=1,
            quantity=Decimal("0.5"),
            unit="KG",
            loss_percentage=Decimal("10"),
            is_optional=False,
        )
        plan = MPSPlan(
            plan_no=f"M22-S04-T003-MPS-{suffix}",
            plan_name=f"Synthetic cross-module plan {suffix}",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status=MPSStatus.APPROVED,
            mrp_run_id=source_run.id,
        )
        db.add_all([recipe_item, plan])
        await db.flush()
        line = MPSLine(
            line_no=f"M22-S04-T003-L-{suffix}",
            mps_id=plan.id,
            product_id=product.id,
            period_start=date(2026, 11, 1),
            period_end=date(2026, 11, 30),
            planned_start_date=date(2026, 11, 10),
            planned_end_date=date(2026, 11, 12),
            planned_production_qty=Decimal("10"),
            feasibility_status=MPSFeasibilityStatus.FEASIBLE,
        )
        lot = Lot(
            lot_number=f"M22-S04-T003-LOT-{suffix}",
            material_id=material.id,
            expiry_date=date(2026, 11, 10),
            is_quarantine=False,
        )
        db.add_all([line, lot])
        await db.flush()
        lot_status = LotQualityStatus(
            lot_id=lot.id,
            release_status=ReleaseStatus.ON_HOLD,
            hold_flag=True,
        )
        stock = Stock(
            stock_type=StockType.MATERIAL,
            warehouse_id=source.id,
            material_id=material.id,
            lot_id=lot.id,
            quantity_on_hand=Decimal("0.550"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("0.550"),
            is_blocked=False,
        )
        db.add_all([lot_status, stock])
        await db.flush()
        mps_actor_id = mps_actor.id
        approver_id = approver.id
        source_id = source.id
        target_id = target.id
        plan_id = plan.id
        line_id = line.id
        lot_status_id = lot_status.id
        stock_id = stock.id
        await db.commit()

        mps_result = await release_mps_plan(db, plan_id, mps_actor_id, target_id)
        assert mps_result["release_complete"] is True
        assert mps_result["released_orders"] == 1
        await db.commit()
        order_id = line.production_order_id
        assert order_id is not None

        retry = await release_mps_plan(db, plan_id, mps_actor_id, target_id)
        assert retry["idempotent_retry"] is True
        assert retry["production_order_ids"] == [str(order_id)]

        order = await db.get(ProductionOrder, order_id)
        assert order.source_warehouse_id == source_id
        assert order.target_warehouse_id == target_id
        assert order.planned_quantity == Decimal("10.000")
        assert order.scheduled_start.date() == line.planned_start_date
        assert order.scheduled_end.date() == line.planned_end_date

        await approve_order(db, order, approver_id)
        await db.commit()

        with pytest.raises(HTTPException) as held_lot:
            await release_order(db, order, approver_id)
        assert held_lot.value.status_code == 422
        assert held_lot.value.detail["error"] == "PRODUCTION_MATERIAL_SHORTAGE"
        assert held_lot.value.detail["required_quantity"] == "0.550"
        assert held_lot.value.detail["available_quantity"] == "0"
        await db.rollback()

        async with AsyncSessionLocal() as verify:
            persisted_order = await verify.get(ProductionOrder, order_id)
            persisted_line = await verify.get(MPSLine, line_id)
            persisted_plan = await verify.get(MPSPlan, plan_id)
            persisted_stock = await verify.get(Stock, stock_id)
            assert persisted_order.status == ProductionOrderStatus.PLANNED
            assert persisted_order.approved_by == approver_id
            assert persisted_line.production_order_id == order_id
            assert persisted_plan.status == MPSStatus.RELEASED
            assert persisted_stock.quantity_available == Decimal("0.550")
            assert await verify.scalar(
                select(func.count()).select_from(AuditLog).where(
                    AuditLog.event_type == "MPS_PLAN_RELEASED",
                    AuditLog.target_id == str(plan_id),
                )
            ) == 1

        async with AsyncSessionLocal() as release_session:
            persisted_lot_status = await release_session.get(LotQualityStatus, lot_status_id)
            persisted_lot_status.release_status = ReleaseStatus.RELEASED
            persisted_lot_status.hold_flag = False
            await release_session.commit()

        async with AsyncSessionLocal() as release_session:
            order = await release_session.get(ProductionOrder, order_id)
            released = await release_order(release_session, order, approver_id)
            assert released.status == ProductionOrderStatus.RELEASED
            await release_session.commit()

        async with AsyncSessionLocal() as verify:
            persisted_order = await verify.get(ProductionOrder, order_id)
            persisted_stock = await verify.get(Stock, stock_id)
            transitions = list((await verify.scalars(
                select(ProductionTransitionEvent)
                .where(
                    ProductionTransitionEvent.parent_entity_type == "PRODUCTION_ORDER",
                    ProductionTransitionEvent.parent_entity_id == order_id,
                )
                .order_by(ProductionTransitionEvent.event_seq)
            )).all())
            assert persisted_order.status == ProductionOrderStatus.RELEASED
            assert persisted_stock.quantity_available == Decimal("0.550")
            assert [event.action for event in transitions] == [
                "CREATED_BY_MPS",
                "APPROVED",
                "RELEASED",
            ]
            assert transitions[0].actor_id == mps_actor_id
            assert transitions[1].actor_id == transitions[2].actor_id == approver_id
