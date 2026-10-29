from types import SimpleNamespace
import asyncio
import os
import re
from unittest.mock import AsyncMock
import inspect
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.params import Depends as DependsType
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.api.v1.endpoints import production_costing
from app.db.session import AsyncSessionLocal, engine
from app.models.finance import CostType, ProductionCostEntry
from app.models.inventory import Lot, MovementType, Stock, StockMovement, StockType
from app.models.master import Material, MaterialType, Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.quality import QCDecision, QCStatus, QCType, QCTestResult, ParameterType
from app.models.production import (
    FinishedGoodsReceipt,
    MaterialConsumption,
    ProductionOrder,
    ProductionOrderStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.traceability import LotGenealogyLink
from app.models.user import User
from app.schemas.production import CompleteOrderRequest
from app.services import finance_service, production_service, quality_service
from app.services.quality_service import make_decision


@pytest.mark.asyncio
async def test_qc_rejects_acceptance_when_a_critical_result_failed_without_mutation():
    inspection = SimpleNamespace(
        status=QCStatus.PENDING,
        test_results=[SimpleNamespace(is_passed=False, is_critical=True)],
        decision=None,
        decided_by_id=None,
        decided_at=None,
        decision_notes=None,
        rework_candidate=False,
    )
    db = SimpleNamespace(flush=AsyncMock())

    with pytest.raises(HTTPException) as error:
        await make_decision(
            db,
            inspection,
            QCDecision.ACCEPT,
            uuid.uuid4(),
            None,
            False,
            False,
        )

    assert error.value.status_code == 422
    assert inspection.decision is None
    assert inspection.status == QCStatus.PENDING
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_qc_accepts_inspection_when_all_recorded_results_pass():
    inspection = SimpleNamespace(
        status=QCStatus.IN_PROGRESS,
        test_results=[
            SimpleNamespace(is_passed=True, is_critical=True),
            SimpleNamespace(is_passed=True, is_critical=False),
        ],
        decision=None,
        decided_by_id=None,
        decided_at=None,
        decision_notes=None,
        rework_candidate=False,
    )
    db = SimpleNamespace(flush=AsyncMock())
    user_id = uuid.uuid4()

    result = await make_decision(
        db,
        inspection,
        QCDecision.ACCEPT,
        user_id,
        "Synthetic verification approval",
        False,
        False,
    )

    assert result is inspection
    assert inspection.decision == QCDecision.ACCEPT
    assert inspection.status == QCStatus.PASSED
    assert inspection.decided_by_id == user_id
    db.flush.assert_awaited_once()


def _required_permission(endpoint):
    for parameter in inspect.signature(endpoint).parameters.values():
        if isinstance(parameter.default, DependsType):
            dependency = parameter.default.dependency
            if getattr(dependency, "__name__", None) == "_check":
                return dependency
    raise AssertionError(f"{endpoint.__name__} has no required permission dependency")


@pytest.mark.parametrize(
    ("endpoint", "permission_code"),
    [
        (production_costing.get_cost_kpis, "finance.view"),
        (production_costing.get_cost_report, "finance.view"),
        (production_costing.get_cost_trend, "finance.view"),
        (production_costing.get_order_cost, "finance.view"),
        (production_costing.finalize_order_cost, "finance.create"),
        (production_costing.get_wip_report, "finance.view"),
        (production_costing.get_variance_detail, "finance.view"),
        (production_costing.get_work_center_utilization, "finance.view"),
    ],
)
def test_production_cost_routes_require_expected_finance_permission(endpoint, permission_code):
    dependency = _required_permission(endpoint)
    freevars = dict(zip(
        dependency.__code__.co_freevars,
        (cell.cell_contents for cell in dependency.__closure__ or ()),
    ))

    assert freevars.get("permission_code") == permission_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "permission_code"),
    [
        (production_costing.get_cost_kpis, "finance.view"),
        (production_costing.get_cost_report, "finance.view"),
        (production_costing.get_cost_trend, "finance.view"),
        (production_costing.get_order_cost, "finance.view"),
        (production_costing.finalize_order_cost, "finance.create"),
        (production_costing.get_wip_report, "finance.view"),
        (production_costing.get_variance_detail, "finance.view"),
        (production_costing.get_work_center_utilization, "finance.view"),
    ],
)
async def test_production_cost_permission_denies_missing_finance_role(endpoint, permission_code):
    dependency = _required_permission(endpoint)
    user_without_permission = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
    with pytest.raises(HTTPException) as error:
        await dependency(current_user=user_without_permission)
    assert error.value.status_code == 403

    permission = SimpleNamespace(code=permission_code, is_active=True)
    role = SimpleNamespace(is_active=True, permissions=[permission])
    authorized_user = SimpleNamespace(is_superuser=False, roles=[role], access_scopes=[])
    assert await dependency(current_user=authorized_user) is authorized_user


DB_ONLY = pytest.mark.skipif(
    os.environ.get("M08_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_database_engine_after_test():
    yield
    await engine.dispose()


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m08_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M08_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing writes: DATABASE_URL must match the exact passwordless loopback M08.S03.T003 database.")
    return expected


async def _seed_completed_order(db, suffix: str):
    user = User(
        email=f"m08-t003-{suffix}@example.invalid",
        username=f"m08t003{suffix}",
        full_name=f"Synthetic M08 T003 actor {suffix}",
        hashed_password="synthetic-test-only-not-a-credential",
    )
    product = Product(
        sku=f"M08-T003-P-{suffix}", name=f"Synthetic finished product {suffix}",
        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
    )
    material = Material(
        code=f"M08-T003-M-{suffix}", name=f"Synthetic raw material {suffix}",
        material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
        standard_cost=Decimal("3.0000"),
    )
    warehouse = Warehouse(
        code=f"M08-T003-W-{suffix}", name=f"Synthetic finished warehouse {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    raw_warehouse = Warehouse(
        code=f"M08-T003-R-{suffix}", name=f"Synthetic raw warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
    )
    db.add_all([user, product, material, warehouse, raw_warehouse])
    await db.flush()
    recipe = Recipe(
        product_id=product.id, version="1", name=f"Synthetic recipe {suffix}",
        status=RecipeStatus.APPROVED, is_active=True,
    )
    db.add(recipe)
    await db.flush()
    db.add(RecipeItem(
        recipe_id=recipe.id, material_id=material.id, line_no=1,
        quantity=Decimal("2"), unit="KG", loss_percentage=Decimal("0"),
    ))
    order = ProductionOrder(
        order_no=f"M08-T003-PO-{suffix}", product_id=product.id,
        recipe_id=recipe.id, planned_quantity=Decimal("4"), actual_quantity=Decimal("4"),
        uom="KG", status=ProductionOrderStatus.COMPLETED,
        target_warehouse_id=warehouse.id, source_warehouse_id=raw_warehouse.id,
        scheduled_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
        actual_start=datetime(2026, 10, 29, tzinfo=timezone.utc),
        actual_end=datetime(2026, 10, 29, 1, tzinfo=timezone.utc),
        batch_no=f"M08-T003-BATCH-{suffix}", created_by=user.id,
    )
    db.add(order)
    await db.flush()
    return user, product, material, raw_warehouse, warehouse, order


@DB_ONLY
@pytest.mark.asyncio
async def test_production_completion_records_explicit_source_lot_and_finished_goods_genealogy():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, product, material, raw_warehouse, _, order = await _seed_completed_order(db, suffix)
        order.status = ProductionOrderStatus.IN_PROGRESS
        source_lot = Lot(
            material_id=material.id, lot_number=f"RM-{suffix}",
            batch_number=f"RM-BATCH-{suffix}", manufacture_date=date(2026, 10, 29),
        )
        db.add(source_lot)
        await db.flush()
        db.add(Stock(
            stock_type=StockType.MATERIAL, warehouse_id=raw_warehouse.id,
            material_id=material.id, lot_id=source_lot.id,
            quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
            quantity_available=Decimal("10"), is_blocked=False,
        ))
        await db.commit()

        await production_service.complete_order(
            db,
            order,
            CompleteOrderRequest(
                actual_quantity=Decimal("4"),
                fg_lot_number=f"FG-{suffix}",
                material_lot_ids={material.id: source_lot.id},
            ),
            user.id,
        )
        await db.commit()

        consumption = (await db.execute(select(MaterialConsumption).where(
            MaterialConsumption.production_order_id == order.id,
        ))).scalar_one()
        issue = await db.get(StockMovement, consumption.stock_movement_id)
        receipt = (await db.execute(select(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order.id,
        ))).scalar_one()
        receipt_movement = await db.get(StockMovement, receipt.stock_movement_id)
        links = list((await db.execute(select(LotGenealogyLink).where(
            LotGenealogyLink.production_order_id == order.id,
        ))).scalars().all())

        assert consumption.lot_id == source_lot.id
        assert issue.lot_id == source_lot.id
        assert receipt_movement.lot_id is not None
        assert len(links) == 1
        assert links[0].parent_lot_id == source_lot.id
        assert links[0].child_lot_id == receipt_movement.lot_id
        assert links[0].quantity_linked == Decimal("2.0000")


@DB_ONLY
@pytest.mark.asyncio
async def test_production_completion_does_not_guess_between_multiple_source_lots():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, _, material, raw_warehouse, _, order = await _seed_completed_order(db, suffix)
        order.status = ProductionOrderStatus.IN_PROGRESS
        lots = [
            Lot(material_id=material.id, lot_number=f"RM-{suffix}-{index}")
            for index in (1, 2)
        ]
        db.add_all(lots)
        await db.flush()
        db.add_all([
            Stock(
                stock_type=StockType.MATERIAL, warehouse_id=raw_warehouse.id,
                material_id=material.id, lot_id=lot.id,
                quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
                quantity_available=Decimal("10"), is_blocked=False,
            )
            for lot in lots
        ])
        await db.commit()

        with pytest.raises(HTTPException) as error:
            await production_service.complete_order(
                db, order, CompleteOrderRequest(actual_quantity=Decimal("4")), user.id,
            )
        assert error.value.status_code == 422
        assert error.value.detail["error"] == "SOURCE_LOT_SELECTION_REQUIRED"
        persisted_order = await db.get(ProductionOrder, order.id)
        assert persisted_order.status == ProductionOrderStatus.IN_PROGRESS
        assert (await db.execute(select(func.count()).select_from(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order.id,
        ))).scalar_one() == 0
        await db.rollback()


@DB_ONLY
@pytest.mark.asyncio
async def test_production_completion_requires_a_finished_goods_lot_for_qc_lineage():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, _, _, _, _, order = await _seed_completed_order(db, suffix)
        order.status = ProductionOrderStatus.IN_PROGRESS
        order.batch_no = None
        await db.commit()

        with pytest.raises(HTTPException) as error:
            await production_service.complete_order(
                db, order, CompleteOrderRequest(actual_quantity=Decimal("4")), user.id,
            )
        assert error.value.status_code == 422
        assert "lot number" in error.value.detail.lower()
        assert (await db.execute(select(func.count()).select_from(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order.id,
        ))).scalar_one() == 0
        await db.rollback()


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m08_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m08_s03_t003_1123456789abcdef0123")
    assert not _is_task_database(safe, "fmcg_m08_s03_t003_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@DB_ONLY
@pytest.mark.asyncio
async def test_finished_goods_qc_quarantines_and_releases_exact_production_lot():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, product, _, _, warehouse, order = await _seed_completed_order(db, suffix)
        lot = Lot(
            product_id=product.id, lot_number=f"FG-{suffix}",
            batch_number=order.batch_no, manufacture_date=date(2026, 10, 29),
        )
        db.add(lot)
        await db.flush()
        movement = StockMovement(
            reference_number=order.order_no, movement_type=MovementType.RECEIPT,
            stock_type=StockType.PRODUCT, movement_date=date(2026, 10, 29),
            product_id=product.id, lot_id=lot.id, destination_warehouse_id=warehouse.id,
            quantity=Decimal("4"), created_by_id=user.id,
        )
        db.add(movement)
        stock = Stock(
            stock_type=StockType.PRODUCT, warehouse_id=warehouse.id,
            product_id=product.id, lot_id=lot.id, quantity_on_hand=Decimal("4"),
            quantity_reserved=Decimal("0"), quantity_available=Decimal("4"),
            is_blocked=False,
        )
        db.add_all([stock, FinishedGoodsReceipt(
            production_order_id=order.id, product_id=product.id,
            quantity=Decimal("4"), uom="KG", lot_number=lot.lot_number,
            batch_no=order.batch_no, warehouse_id=warehouse.id,
            stock_movement=movement,
        )])
        await db.flush()

        inspection = await quality_service.create_qc_for_order(
            db, production_order_id=order.id, product_id=product.id,
            warehouse_id=warehouse.id, lot_number=lot.lot_number,
            batch_no=order.batch_no, inspection_no=f"QC-{suffix}",
            inspector_id=user.id, qc_type=QCType.FINISHED_GOODS,
        )
        assert inspection.lot_id == lot.id
        assert inspection.is_mandatory is True
        assert inspection.quarantine_applied is True
        assert stock.is_blocked is True
        assert stock.quantity_available == Decimal("0")
        await quality_service.make_decision(
            db, inspection, QCDecision.REJECT, user.id, "Synthetic failed test",
            rework_candidate=False, apply_quarantine=True,
        )
        await db.flush()
        assert stock.is_blocked is True
        assert stock.quantity_available == Decimal("0")

        with pytest.raises(HTTPException) as rejected_release:
            await quality_service.release_qc_quarantine(db, inspection, user.id, "Cannot release rejected lot")
        assert rejected_release.value.status_code == 422

        retest = await quality_service.create_qc_for_order(
            db, production_order_id=order.id, product_id=product.id,
            warehouse_id=warehouse.id, lot_number=lot.lot_number,
            batch_no=order.batch_no, inspection_no=f"RETEST-{suffix}",
            inspector_id=user.id, qc_type=QCType.FINISHED_GOODS,
        )
        db.add(QCTestResult(
            inspection_id=retest.id,
            parameter_name="Synthetic release check",
            parameter_type=ParameterType.PASS_FAIL,
            is_passed=True,
            is_critical=True,
            tested_by_id=user.id,
        ))
        await db.flush()
        await quality_service.make_decision(
            db, retest, QCDecision.ACCEPT, user.id, "Synthetic passing retest",
            rework_candidate=False, apply_quarantine=False,
        )
        await db.flush()
        await quality_service.release_qc_quarantine(db, retest, user.id, "Synthetic retest passed")
        await db.flush()
        assert stock.is_blocked is False
        assert stock.quantity_reserved == Decimal("0")
        assert stock.quantity_available == Decimal("4")
        await db.rollback()


@DB_ONLY
@pytest.mark.asyncio
async def test_completed_order_cost_rollup_is_idempotent_and_preserves_manual_costs():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, product, material, warehouse, _, order = await _seed_completed_order(db, suffix)
        db.add(MaterialConsumption(
            production_order_id=order.id, material_id=material.id,
            standard_quantity=Decimal("4"), actual_quantity=Decimal("4"),
            variance_quantity=Decimal("0"), unit="KG", source_warehouse_id=warehouse.id,
        ))
        db.add_all([
            ProductionCostEntry(
                production_order_id=order.id, product_id=product.id,
                cost_type=CostType.RAW_MATERIAL, amount=Decimal("99"),
                period_ym="2026-10", notes="Manual finance adjustment", created_by_id=user.id,
            ),
            ProductionCostEntry(
                production_order_id=order.id, product_id=product.id,
                cost_type=CostType.RAW_MATERIAL, amount=Decimal("1"),
                period_ym="2026-10", notes="Auto from consumption old", created_by_id=user.id,
            ),
        ])
        await db.commit()
        first = await finance_service.rollup_production_order_costs(db, order.id, user.id)
        await db.commit()
        second = await finance_service.rollup_production_order_costs(db, order.id, user.id)
        await db.commit()

        rows = list((await db.execute(select(ProductionCostEntry).where(
            ProductionCostEntry.production_order_id == order.id,
        ))).scalars().all())
        auto_rows = [row for row in rows if row.notes and row.notes.startswith("Auto from consumption ")]
        manual_rows = [row for row in rows if row.notes == "Manual finance adjustment"]
        assert len(first) == len(second) == 1
        assert len(auto_rows) == len(manual_rows) == 1
        assert auto_rows[0].amount == Decimal("12.0000")
        assert manual_rows[0].amount == Decimal("99.0000")


@DB_ONLY
@pytest.mark.asyncio
async def test_cost_rollup_rejects_incomplete_order_without_writing_entries():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, _, _, _, _, order = await _seed_completed_order(db, suffix)
        order.status = ProductionOrderStatus.IN_PROGRESS
        await db.commit()

        with pytest.raises(HTTPException) as error:
            await finance_service.rollup_production_order_costs(db, order.id, user.id)
        assert error.value.status_code == 422
        assert (await db.execute(select(func.count()).select_from(ProductionCostEntry).where(
            ProductionCostEntry.production_order_id == order.id,
        ))).scalar_one() == 0
        await db.rollback()


@DB_ONLY
@pytest.mark.asyncio
async def test_concurrent_cost_rollups_serialize_on_production_order():
    expected_database = _require_task_database()
    suffix = uuid.uuid4().hex[:16]
    async with AsyncSessionLocal() as first_db:
        assert (await first_db.execute(select(func.current_database()))).scalar_one() == expected_database
        user, _, material, warehouse, _, order = await _seed_completed_order(first_db, suffix)
        first_db.add(MaterialConsumption(
            production_order_id=order.id, material_id=material.id,
            standard_quantity=Decimal("2"), actual_quantity=Decimal("2"),
            variance_quantity=Decimal("0"), unit="KG", source_warehouse_id=warehouse.id,
        ))
        await first_db.commit()

        first_rows = await finance_service.rollup_production_order_costs(first_db, order.id, user.id)
        assert len(first_rows) == 1

        second_started = asyncio.Event()

        async def _second_rollup():
            async with AsyncSessionLocal() as second_db:
                second_started.set()
                rows = await finance_service.rollup_production_order_costs(second_db, order.id, user.id)
                await second_db.commit()
                return rows

        second_task = asyncio.create_task(_second_rollup())
        await second_started.wait()

        deadline = asyncio.get_running_loop().time() + 5
        observed_wait = False
        while asyncio.get_running_loop().time() < deadline:
            async with AsyncSessionLocal() as probe_db:
                observed_wait = bool((await probe_db.execute(text(
                    """SELECT EXISTS (
                           SELECT 1 FROM pg_stat_activity
                           WHERE pid <> pg_backend_pid()
                             AND wait_event_type = 'Lock'
                             AND query ILIKE '%production_orders%'
                       )"""
                ))).scalar_one())
            if observed_wait:
                break
            if second_task.done():
                break
            await asyncio.sleep(0.02)

        assert observed_wait, "second rollup did not wait on the production-order row lock"
        await first_db.commit()
        second_rows = await second_task
        assert len(second_rows) == 1

        async with AsyncSessionLocal() as verify_db:
            rows = list((await verify_db.execute(select(ProductionCostEntry).where(
                ProductionCostEntry.production_order_id == order.id,
                ProductionCostEntry.notes.like("Auto from consumption %"),
            ))).scalars().all())
            assert len(rows) == 1
            assert rows[0].amount == Decimal("6.0000")
