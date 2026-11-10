"""M24.S01.T001 PostgreSQL checks for released-order material reservations."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
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
from app.models.recipe import Recipe, RecipeStatus
from app.models.material_flow import ReservationStatus
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.models.wms import StorageLocation, WarehouseZone, ZoneType
from app.schemas.material_flow import ReservationCreate, ReservationLineCreate
from app.services import material_flow_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M24_S01_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m24_s01_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M24_S01_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M24_S01_T001_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M24.S01.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s01_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s01_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s01_t001_short")
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


async def _seed_order(
    db,
    suffix: str,
    *,
    status: ProductionOrderStatus,
    stock_quantity: Decimal,
    configure_staging: bool = True,
):
    product = Product(
        sku=f"M24-S01-T001-P-{suffix}",
        name=f"Synthetic reservation product {suffix}",
        category=ProductCategory.FOOD,
        uom=UnitOfMeasure.KG,
    )
    warehouse = Warehouse(
        code=f"M24-S01-T001-W-{suffix}",
        name=f"Synthetic reservation warehouse {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
        is_active=True,
    )
    material = Material(
        code=f"M24-S01-T001-M-{suffix}",
        name=f"Synthetic reservation material {suffix}",
        material_type=MaterialType.RAW,
        uom=UnitOfMeasure.KG,
        is_active=True,
    )
    db.add_all([product, warehouse, material])
    await db.flush()
    raw_zone = WarehouseZone(
        warehouse_id=warehouse.id,
        code=f"M24-S01-T003-RZ-{suffix}",
        name=f"Synthetic raw zone {suffix}",
        zone_type=ZoneType.RAW_MATERIAL,
        is_active=True,
    )
    db.add(raw_zone)
    staging_zone = None
    if configure_staging:
        staging_zone = WarehouseZone(
            warehouse_id=warehouse.id,
            code=f"M24-S01-T003-SZ-{suffix}",
            name=f"Synthetic staging zone {suffix}",
            zone_type=ZoneType.STAGING,
            is_active=True,
        )
        db.add(staging_zone)
    await db.flush()
    source_location = StorageLocation(
        zone_id=raw_zone.id,
        code=f"M24-S01-T003-SOURCE-{suffix}",
        name=f"Synthetic source location {suffix}",
        is_active=True,
        is_blocked=False,
    )
    db.add(source_location)
    staging_location = None
    if staging_zone is not None:
        staging_location = StorageLocation(
            zone_id=staging_zone.id,
            code=f"M24-S01-T003-STAGE-{suffix}",
            name=f"Synthetic staging location {suffix}",
            is_active=True,
            is_blocked=False,
        )
        db.add(staging_location)
    await db.flush()
    recipe = Recipe(
        product_id=product.id,
        version="1",
        name=f"Synthetic reservation recipe {suffix}",
        status=RecipeStatus.APPROVED,
        is_active=True,
    )
    db.add(recipe)
    await db.flush()
    order = ProductionOrder(
        order_no=f"M24-S01-T001-PO-{suffix}",
        product_id=product.id,
        recipe_id=recipe.id,
        planned_quantity=Decimal("10"),
        uom="KG",
        status=status,
        target_warehouse_id=warehouse.id,
        source_warehouse_id=warehouse.id,
        scheduled_start=datetime(2026, 11, 10, 8, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 11, 10, 16, tzinfo=timezone.utc),
    )
    db.add(order)
    await db.flush()
    stock = Stock(
        stock_type=StockType.MATERIAL,
        warehouse_id=warehouse.id,
        material_id=material.id,
        quantity_on_hand=stock_quantity,
        quantity_reserved=Decimal("0"),
        quantity_available=stock_quantity,
        location_id=source_location.id,
        is_blocked=False,
    )
    db.add(stock)
    await db.commit()
    return (
        order.id,
        material.id,
        warehouse.id,
        stock.id,
        source_location.id,
        staging_location.id if staging_location else None,
    )


async def _add_lot_stock(
    db,
    *,
    suffix: str,
    material_id,
    warehouse_id,
    location_id,
    expiry_date: date | None,
    quantity: Decimal,
    release_status: ReleaseStatus | None = ReleaseStatus.RELEASED,
    fefo_eligible: bool = True,
):
    lot = Lot(
        lot_number=f"M24-S01-T004-{suffix}",
        material_id=material_id,
        manufacture_date=date(2026, 1, 1),
        expiry_date=expiry_date,
        is_quarantine=False,
    )
    db.add(lot)
    await db.flush()
    if release_status is not None:
        db.add(
            LotQualityStatus(
                lot_id=lot.id,
                qc_status="PASSED" if release_status == ReleaseStatus.RELEASED else "PENDING",
                release_status=release_status,
                fefo_eligible=fefo_eligible,
                hold_flag=False,
                quarantine_flag=False,
            )
        )
    stock = Stock(
        stock_type=StockType.MATERIAL,
        warehouse_id=warehouse_id,
        material_id=material_id,
        lot_id=lot.id,
        location_id=location_id,
        quantity_on_hand=quantity,
        quantity_reserved=Decimal("0"),
        quantity_available=quantity,
        is_blocked=False,
    )
    db.add(stock)
    await db.flush()
    return lot.id, lot.lot_number, stock.id


def _reservation(
    order_id,
    material_id,
    warehouse_id,
    quantity: str,
    *,
    staging_location_id=None,
    lot_id=None,
    lot_fixed: bool = False,
):
    return ReservationCreate(
        production_order_id=order_id,
        lines=[
            ReservationLineCreate(
                line_no=1,
                item_type="material",
                material_id=material_id,
                lot_id=lot_id,
                warehouse_id=warehouse_id,
                staging_location_id=staging_location_id,
                lot_fixed=lot_fixed,
                quantity_required=Decimal(quantity),
                uom="KG",
            )
        ],
    )


@pytest.mark.asyncio
async def test_reservation_requires_released_order_and_preserves_stock_on_rejection():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, stock_id, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.PLANNED, stock_quantity=Decimal("5.000")
        )
        with pytest.raises(HTTPException) as raised:
            await material_flow_service.create_reservation(
                db, _reservation(order_id, material_id, warehouse_id, "2.000")
            )
        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "PRODUCTION_ORDER_NOT_RELEASED"
        await db.rollback()
        stock = await db.get(Stock, stock_id)
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("5.000")


@pytest.mark.asyncio
async def test_reservation_decrements_available_and_cancel_restores_unissued_balance():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, stock_id, source_location_id, staging_location_id = await _seed_order(
            db, suffix, status=ProductionOrderStatus.RELEASED, stock_quantity=Decimal("5.000")
        )
        reservation = await material_flow_service.create_reservation(
            db, _reservation(order_id, material_id, warehouse_id, "3.000")
        )
        assert reservation.lines[0].source_location_id == source_location_id
        assert reservation.lines[0].staging_location_id == staging_location_id
        await db.commit()
        stock = await db.get(Stock, stock_id)
        assert stock.quantity_reserved == Decimal("3.000")
        assert stock.quantity_available == Decimal("2.000")
        assert len(reservation.lines) == 1
        assert reservation.lines[0].quantity_reserved == Decimal("3.000")

        cancelled = await material_flow_service.cancel_reservation(db, reservation.id)
        await db.commit()
        stock = await db.get(Stock, stock_id)
        assert cancelled.status.value == "CANCELLED"
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("5.000")


@pytest.mark.asyncio
async def test_shortage_does_not_create_or_partially_apply_reservation():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, stock_id, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.RELEASED, stock_quantity=Decimal("1.000")
        )
        with pytest.raises(HTTPException) as raised:
            await material_flow_service.create_reservation(
                db, _reservation(order_id, material_id, warehouse_id, "2.000")
            )
        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "MATERIAL_RESERVATION_SHORTAGE"
        await db.rollback()
        stock = await db.get(Stock, stock_id)
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("1.000")


@pytest.mark.asyncio
async def test_pick_list_reports_only_outstanding_qty_without_changing_inventory():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, stock_id, source_location_id, staging_location_id = await _seed_order(
            db, suffix, status=ProductionOrderStatus.RELEASED, stock_quantity=Decimal("5.000")
        )
        reservation = await material_flow_service.create_reservation(
            db, _reservation(order_id, material_id, warehouse_id, "3.000")
        )
        await db.commit()
        reservation.lines[0].quantity_issued = Decimal("1.000")
        reservation.status = ReservationStatus.PARTIALLY_ISSUED
        stock = await db.get(Stock, stock_id)
        stock.quantity_on_hand = Decimal("4.000")
        stock.quantity_reserved = Decimal("2.000")
        stock.quantity_available = Decimal("2.000")
        await db.commit()

        pick_list = await material_flow_service.generate_material_pick_list(db, reservation.id)

        assert pick_list is not None
        assert len(pick_list.lines) == 1
        assert pick_list.lines[0].quantity_to_pick == Decimal("2.000")
        assert pick_list.lines[0].material_id == material_id
        assert pick_list.lines[0].source_location_id == source_location_id
        assert pick_list.lines[0].source_location_code.startswith("M24-S01-T003-SOURCE-")
        assert pick_list.lines[0].staging_location_id == staging_location_id
        assert pick_list.lines[0].staging_location_code.startswith("M24-S01-T003-STAGE-")
        unchanged_stock = await db.get(Stock, stock_id)
        assert unchanged_stock.quantity_on_hand == Decimal("4.000")
        assert unchanged_stock.quantity_reserved == Decimal("2.000")
        assert unchanged_stock.quantity_available == Decimal("2.000")


@pytest.mark.asyncio
async def test_multiple_staging_locations_require_explicit_selection_without_stock_mutation():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, stock_id, _, staging_location_id = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.RELEASED,
            stock_quantity=Decimal("5.000"),
        )
        staging_zone = await db.scalar(
            select(WarehouseZone).where(
                WarehouseZone.warehouse_id == warehouse_id,
                WarehouseZone.zone_type == ZoneType.STAGING,
            )
        )
        db.add(
            StorageLocation(
                zone_id=staging_zone.id,
                code=f"M24-S01-T003-ALT-{suffix}",
                name=f"Second synthetic staging location {suffix}",
                is_active=True,
                is_blocked=False,
            )
        )
        await db.commit()

        with pytest.raises(HTTPException) as raised:
            await material_flow_service.create_reservation(
                db, _reservation(order_id, material_id, warehouse_id, "2.000")
            )
        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "RESERVATION_STAGING_LOCATION_REQUIRED"
        await db.rollback()
        stock = await db.get(Stock, stock_id)
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("5.000")

        foreign_warehouse = Warehouse(
            code=f"M24-S01-T003-FOREIGN-{suffix}",
            name=f"Foreign synthetic warehouse {suffix}",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            is_active=True,
        )
        db.add(foreign_warehouse)
        await db.flush()
        foreign_zone = WarehouseZone(
            warehouse_id=foreign_warehouse.id,
            code=f"M24-S01-T003-FZ-{suffix}",
            name=f"Foreign synthetic staging zone {suffix}",
            zone_type=ZoneType.STAGING,
            is_active=True,
        )
        db.add(foreign_zone)
        await db.flush()
        foreign_location = StorageLocation(
            zone_id=foreign_zone.id,
            code=f"M24-S01-T003-FLOC-{suffix}",
            name=f"Foreign synthetic staging location {suffix}",
            is_active=True,
            is_blocked=False,
        )
        db.add(foreign_location)
        await db.flush()
        foreign_location_id = foreign_location.id
        await db.commit()

        with pytest.raises(HTTPException) as foreign_raised:
            await material_flow_service.create_reservation(
                db,
                _reservation(
                    order_id,
                    material_id,
                    warehouse_id,
                    "2.000",
                    staging_location_id=foreign_location_id,
                ),
            )
        assert foreign_raised.value.status_code == 422
        assert foreign_raised.value.detail["error"] == "RESERVATION_STAGING_LOCATION_INVALID"
        await db.rollback()

        reservation = await material_flow_service.create_reservation(
            db,
            _reservation(
                order_id,
                material_id,
                warehouse_id,
                "2.000",
                staging_location_id=staging_location_id,
            ),
        )
        assert reservation.lines[0].staging_location_id == staging_location_id


@pytest.mark.asyncio
async def test_missing_staging_configuration_remains_explicitly_unassigned():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, _, source_location_id, _ = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.RELEASED,
            stock_quantity=Decimal("3.000"),
            configure_staging=False,
        )
        reservation = await material_flow_service.create_reservation(
            db, _reservation(order_id, material_id, warehouse_id, "1.000")
        )
        assert reservation.lines[0].source_location_id == source_location_id
        assert reservation.lines[0].staging_location_id is None


@pytest.mark.asyncio
async def test_reservation_allocates_eligible_lots_in_fefo_order():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, _, source_location_id, _ = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.RELEASED,
            stock_quantity=Decimal("0.000"),
        )
        await _add_lot_stock(
            db,
            suffix=f"UNRELEASED-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 11, 12),
            quantity=Decimal("20.000"),
            release_status=ReleaseStatus.UNRELEASED,
            fefo_eligible=False,
        )
        await _add_lot_stock(
            db,
            suffix=f"EXPIRED-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 11, 9),
            quantity=Decimal("20.000"),
        )
        earliest_lot_id, earliest_lot_number, _ = await _add_lot_stock(
            db,
            suffix=f"EARLY-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 11, 15),
            quantity=Decimal("2.000"),
        )
        later_lot_id, _, _ = await _add_lot_stock(
            db,
            suffix=f"LATER-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 12, 1),
            quantity=Decimal("2.000"),
        )
        non_expiring_lot_id, _, _ = await _add_lot_stock(
            db,
            suffix=f"NO-EXPIRY-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=None,
            quantity=Decimal("1.000"),
        )

        reservation = await material_flow_service.create_reservation(
            db, _reservation(order_id, material_id, warehouse_id, "5.000")
        )

        assert [line.lot_id for line in reservation.lines] == [
            earliest_lot_id,
            later_lot_id,
            non_expiring_lot_id,
        ]
        assert [line.quantity_reserved for line in reservation.lines] == [
            Decimal("2.000"),
            Decimal("2.000"),
            Decimal("1.000"),
        ]
        assert all(line.fefo_lot_candidate == earliest_lot_number for line in reservation.lines)


@pytest.mark.asyncio
async def test_fixed_non_fefo_lot_is_rejected_before_inventory_changes():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, _, source_location_id, _ = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.RELEASED,
            stock_quantity=Decimal("0.000"),
        )
        first_lot_id, first_lot_number, _ = await _add_lot_stock(
            db,
            suffix=f"FIRST-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 11, 15),
            quantity=Decimal("2.000"),
        )
        selected_lot_id, _, _ = await _add_lot_stock(
            db,
            suffix=f"LATER-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=date(2026, 12, 1),
            quantity=Decimal("2.000"),
        )

        with pytest.raises(HTTPException) as raised:
            await material_flow_service.create_reservation(
                db,
                _reservation(
                    order_id,
                    material_id,
                    warehouse_id,
                    "1.000",
                    lot_id=selected_lot_id,
                    lot_fixed=True,
                ),
            )

        assert raised.value.status_code == 422
        assert raised.value.detail["error"] == "MATERIAL_RESERVATION_NON_FEFO_LOT"
        assert raised.value.detail["recommended_lot_id"] == str(first_lot_id)
        assert raised.value.detail["recommended_lot_number"] == first_lot_number
        await db.rollback()
        stocks = list((await db.scalars(select(Stock).where(Stock.warehouse_id == warehouse_id))).all())
        assert all(stock.quantity_reserved == Decimal("0.000") for stock in stocks)
        assert all(stock.quantity_available == stock.quantity_on_hand for stock in stocks)
