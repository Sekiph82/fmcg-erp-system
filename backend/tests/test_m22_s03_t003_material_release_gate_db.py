"""M22.S03.T003 PostgreSQL integration coverage for material release gates."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
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
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.user import User
from app.services import production_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S03_T003_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S03.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s03_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s03_t003_short")
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


async def _seed_order(db, suffix: str, *, stock_quantity: Decimal | None, source_warehouse=True):
    creator = User(
        email=f"m22-s03-t003-creator-{suffix}@example.invalid",
        username=f"m22s03t003c{suffix}",
        full_name=f"Synthetic M22 creator {suffix}",
        hashed_password="test-only",
    )
    approver = User(
        email=f"m22-s03-t003-approver-{suffix}@example.invalid",
        username=f"m22s03t003a{suffix}",
        full_name=f"Synthetic M22 approver {suffix}",
        hashed_password="test-only",
    )
    product = Product(
        sku=f"M22-S03-T003-P-{suffix}",
        name=f"Synthetic release product {suffix}",
        category=ProductCategory.FOOD,
        uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M22-S03-T003-W-{suffix}",
        name=f"Synthetic raw warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
    )
    material = Material(
        code=f"M22-S03-T003-M-{suffix}",
        name=f"Synthetic required material {suffix}",
        material_type=MaterialType.RAW,
        uom=UnitOfMeasure.KG,
        is_active=True,
    )
    db.add_all([creator, approver, product, warehouse, material])
    await db.flush()
    recipe = Recipe(
        product_id=product.id,
        version="1",
        name=f"Synthetic release recipe {suffix}",
        status=RecipeStatus.APPROVED,
        is_active=True,
    )
    db.add(recipe)
    await db.flush()
    item = RecipeItem(
        recipe_id=recipe.id,
        material_id=material.id,
        line_no=1,
        quantity=Decimal("0.5"),
        unit="KG",
        loss_percentage=Decimal("10"),
        is_optional=False,
    )
    order = ProductionOrder(
        order_no=f"M22-S03-T003-PO-{suffix}",
        product_id=product.id,
        recipe_id=recipe.id,
        planned_quantity=Decimal("10"),
        uom="KG",
        status=ProductionOrderStatus.PLANNED,
        target_warehouse_id=warehouse.id,
        source_warehouse_id=warehouse.id if source_warehouse else None,
        scheduled_start=datetime(2026, 11, 5, 8, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 11, 5, 16, tzinfo=timezone.utc),
        created_by=creator.id,
        approved_by=approver.id,
        approved_at=datetime(2026, 11, 4, 8, tzinfo=timezone.utc),
    )
    db.add_all([item, order])
    await db.flush()
    if stock_quantity is not None:
        db.add(Stock(
            stock_type=StockType.MATERIAL,
            warehouse_id=warehouse.id,
            material_id=material.id,
            quantity_on_hand=stock_quantity,
            quantity_reserved=Decimal("0"),
            quantity_available=stock_quantity,
            is_blocked=False,
        ))
        await db.flush()
    await db.commit()
    return order.id, material.id, warehouse.id


@pytest.mark.asyncio
async def test_release_blocks_required_material_shortage_without_changing_order_status():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, _ = await _seed_order(
            db, suffix, stock_quantity=Decimal("0.549")
        )
        order = await db.get(ProductionOrder, order_id)

        with pytest.raises(HTTPException) as raised:
            await production_service.release_order(db, order, uuid4())

        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "PRODUCTION_MATERIAL_SHORTAGE"
        assert raised.value.detail["required_quantity"] == "0.550"
        assert raised.value.detail["available_quantity"] == "0.549"
        await db.rollback()
        assert (await db.get(ProductionOrder, order_id)).status == ProductionOrderStatus.PLANNED


@pytest.mark.asyncio
async def test_exact_usable_material_quantity_allows_release():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, _ = await _seed_order(
            db, suffix, stock_quantity=Decimal("0.550")
        )
        order = await db.get(ProductionOrder, order_id)

        released = await production_service.release_order(db, order, order.approved_by)

        assert released.status == ProductionOrderStatus.RELEASED
        await db.rollback()
        assert (await db.get(ProductionOrder, order_id)).status == ProductionOrderStatus.PLANNED


@pytest.mark.asyncio
async def test_blocked_quarantined_or_expired_stock_does_not_satisfy_release():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id = await _seed_order(
            db, suffix, stock_quantity=None
        )
        quarantined = Lot(
            lot_number=f"M22-S03-T003-Q-{suffix}",
            material_id=material_id,
            is_quarantine=True,
        )
        expired = Lot(
            lot_number=f"M22-S03-T003-E-{suffix}",
            material_id=material_id,
            expiry_date=date(2026, 11, 4),
            is_quarantine=False,
        )
        db.add_all([quarantined, expired])
        await db.flush()
        db.add_all([
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                lot_id=quarantined.id,
                quantity_on_hand=10,
                quantity_reserved=0,
                quantity_available=10,
                is_blocked=False,
            ),
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                lot_id=expired.id,
                quantity_on_hand=10,
                quantity_reserved=0,
                quantity_available=10,
                is_blocked=False,
            ),
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                quantity_on_hand=10,
                quantity_reserved=0,
                quantity_available=10,
                is_blocked=True,
            ),
        ])
        await db.commit()
        order = await db.get(ProductionOrder, order_id)

        with pytest.raises(HTTPException) as raised:
            await production_service.release_order(db, order, uuid4())

        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "PRODUCTION_MATERIAL_SHORTAGE"
        assert raised.value.detail["available_quantity"] == "0"
        await db.rollback()


@pytest.mark.asyncio
async def test_held_or_unreleased_qms_lots_do_not_satisfy_release():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id = await _seed_order(
            db, suffix, stock_quantity=None
        )
        held = Lot(
            lot_number=f"M22-S03-T003-H-{suffix}",
            material_id=material_id,
            is_quarantine=False,
        )
        unreleased = Lot(
            lot_number=f"M22-S03-T003-U-{suffix}",
            material_id=material_id,
            is_quarantine=False,
        )
        db.add_all([held, unreleased])
        await db.flush()
        db.add_all([
            LotQualityStatus(
                lot_id=held.id,
                release_status=ReleaseStatus.ON_HOLD,
                hold_flag=True,
            ),
            LotQualityStatus(
                lot_id=unreleased.id,
                release_status=ReleaseStatus.UNRELEASED,
            ),
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                lot_id=held.id,
                quantity_on_hand=10,
                quantity_reserved=0,
                quantity_available=10,
                is_blocked=False,
            ),
            Stock(
                stock_type=StockType.MATERIAL,
                warehouse_id=warehouse_id,
                material_id=material_id,
                lot_id=unreleased.id,
                quantity_on_hand=10,
                quantity_reserved=0,
                quantity_available=10,
                is_blocked=False,
            ),
        ])
        await db.commit()
        order = await db.get(ProductionOrder, order_id)

        with pytest.raises(HTTPException) as raised:
            await production_service.release_order(db, order, order.approved_by)

        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "PRODUCTION_MATERIAL_SHORTAGE"
        assert raised.value.detail["available_quantity"] == "0"
        await db.rollback()


@pytest.mark.asyncio
async def test_required_material_cannot_release_without_source_warehouse():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, _ = await _seed_order(
            db, suffix, stock_quantity=Decimal("10"), source_warehouse=False
        )
        order = await db.get(ProductionOrder, order_id)

        with pytest.raises(HTTPException) as raised:
            await production_service.release_order(db, order, uuid4())

        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "PRODUCTION_SOURCE_WAREHOUSE_REQUIRED"
        await db.rollback()
