"""M22.S03.T001 disposable PostgreSQL coverage for operation linkage."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.master import (
    Product,
    ProductCategory,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_advanced import (
    WorkCenter,
    WorkCenterStatus,
    WorkCenterType,
    WorkOrder,
    WorkOrderStatus,
)
from app.models.recipe import Recipe, RecipeStatus
from app.models.subcontracting import SCOrderStatus
from app.models.user import User
from app.schemas.subcontracting import SCOrderCreate, SCReceiptCreate, SCReceiptLineCreate
from app.services import subcontracting_service
from app.services.production_service import _completed_work_order_output_quantity
from app.crud import production_advanced as production_crud
from sqlalchemy import select
from app.models.subcontracting import SubcontractReceiptLine


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S03_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S03_T001_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S03.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s03_t001_short")
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
async def test_subcontract_order_links_only_to_an_open_canonical_work_order():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        product = Product(
            sku=f"M22-S03-T001-P-{suffix}",
            name=f"Synthetic subcontract output {suffix}",
            category=ProductCategory.FOOD,
            uom=UnitOfMeasure.KG,
        )
        supplier = Supplier(code=f"M22-S03-T001-S-{suffix}", name=f"Synthetic processor {suffix}")
        actor = User(
            email=f"m22-s03-t001-{suffix}@example.invalid",
            username=f"m22s03t001{suffix}",
            full_name=f"Synthetic subcontract actor {suffix}",
            hashed_password="test-only",
        )
        warehouse = Warehouse(
            code=f"M22-S03-T001-W-{suffix}",
            name=f"Synthetic finished goods {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([product, supplier, warehouse, actor])
        await db.flush()
        recipe = Recipe(
            product_id=product.id,
            version="1",
            name=f"Synthetic subcontract recipe {suffix}",
            status=RecipeStatus.APPROVED,
            is_active=True,
        )
        db.add(recipe)
        await db.flush()
        parent = ProductionOrder(
            order_no=f"M22-T001-PO-{suffix}",
            product_id=product.id,
            recipe_id=recipe.id,
            planned_quantity=Decimal("12"),
            uom="KG",
            status=ProductionOrderStatus.IN_PROGRESS,
            approved_by=actor.id,
            approved_at=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            target_warehouse_id=warehouse.id,
            scheduled_start=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
            scheduled_end=datetime(2026, 11, 4, 16, tzinfo=timezone.utc),
        )
        center = WorkCenter(
            work_center_id=f"M22-T001-WC-{suffix}",
            name=f"Synthetic subcontract operation {suffix}",
            type=WorkCenterType.MACHINE,
            status=WorkCenterStatus.ACTIVE,
        )
        db.add_all([parent, center])
        await db.flush()
        work_order = WorkOrder(
            work_order_id=f"M22-T001-WO-{suffix}",
            production_order_id=parent.id,
            work_center_id=center.id,
            operation="External finishing",
            status=WorkOrderStatus.PLANNED,
            planned_quantity=Decimal("12"),
        )
        db.add(work_order)
        await db.flush()
        work_order_id = work_order.id
        work_order_code = work_order.work_order_id
        supplier_id = supplier.id
        product_id = product.id
        warehouse_id = warehouse.id
        parent_id = parent.id
        actor_id = actor.id
        await db.commit()

        linked = await subcontracting_service.create_order(
            db,
            SCOrderCreate(
                supplier_id=supplier_id,
                order_date=date(2026, 11, 4),
                warehouse_id=warehouse_id,
                work_order_id=work_order_id,
            ),
            actor_id,
        )
        linked.status = SCOrderStatus.ISSUED
        await db.commit()
        linked_id = linked.id
        loaded = await subcontracting_service.get_order(db, linked_id)
        assert loaded is not None
        assert loaded.work_order_id == work_order_id
        assert loaded.work_order.work_order_id == work_order_code
        assert loaded.status == SCOrderStatus.ISSUED

        with pytest.raises(ValueError, match="accepted product output"):
            await subcontracting_service.complete_order(db, linked_id, actor_id)
        await db.rollback()

        receipt = await subcontracting_service.receive_goods(
            db,
            SCReceiptCreate(
                order_id=linked_id,
                receipt_date=date(2026, 11, 4),
                lines=[SCReceiptLineCreate(
                    line_no=1,
                    product_id=product_id,
                    quantity_received=Decimal("10"),
                    quantity_accepted=Decimal("9"),
                    quantity_rejected=Decimal("1"),
                    uom="KG",
                )],
            ),
            actor_id,
        )
        receipt_id = receipt.id
        await db.commit()
        receipt_line = (await db.execute(
            select(SubcontractReceiptLine).where(SubcontractReceiptLine.receipt_id == receipt_id)
        )).scalar_one()
        assert receipt_line.stock_movement_id is None
        assert receipt_line.quantity_accepted == Decimal("9")

        # A single partial receipt is a valid completed subcontract operation at its accepted amount.
        await subcontracting_service.complete_order(db, linked_id, actor_id)
        await db.commit()
        completed_subcontract = await subcontracting_service.get_order(db, linked_id)
        assert completed_subcontract is not None
        assert completed_subcontract.completed_by_id == actor_id
        await production_crud.start_work_order(db, work_order_id, actor_id)
        with pytest.raises(ValueError, match="must equal accepted output"):
            await production_crud.complete_work_order(db, work_order_id, actor_id, Decimal("10"))
        await production_crud.complete_work_order(db, work_order_id, actor_id, Decimal("9"))
        await db.commit()
        assert await _completed_work_order_output_quantity(
            db, await db.get(ProductionOrder, parent_id)
        ) == Decimal("9")

        legacy_unlinked = await subcontracting_service.create_order(
            db,
            SCOrderCreate(supplier_id=supplier_id, order_date=date(2026, 11, 4)),
            actor_id,
        )
        await db.commit()
        assert legacy_unlinked.work_order_id is None
