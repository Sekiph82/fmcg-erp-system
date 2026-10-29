"""Hold/quarantine stock parity on the task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot, MovementType, Stock, StockMovement, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.quality import QCDecision, QCInspection, QCStatus, QCType, LotQualityStatus, ReleaseStatus
from app.services import qms_service


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S03_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S03_T001_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m27_s03_t001_[a-f0-9]{20}", expected)
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


@pytest.mark.asyncio
async def test_hold_release_and_dispatch_share_physical_lot_disposition(monkeypatch):
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        product = Product(
            sku=f"M27-T001-P-{suffix}", name=f"Synthetic hold product {suffix}",
            category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
        )
        warehouse_a = Warehouse(
            code=f"M27-T001-WA-{suffix}", name=f"Synthetic warehouse A {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        warehouse_b = Warehouse(
            code=f"M27-T001-WB-{suffix}", name=f"Synthetic warehouse B {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        db.add_all([product, warehouse_a, warehouse_b])
        await db.flush()
        lot = Lot(lot_number=f"M27-T001-LOT-{suffix}", product_id=product.id)
        db.add(lot)
        await db.flush()
        stocks = [
            Stock(
                stock_type=StockType.PRODUCT, warehouse_id=warehouse_a.id, product_id=product.id,
                lot_id=lot.id, quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("3"),
                quantity_available=Decimal("7"), is_blocked=False,
            ),
            Stock(
                stock_type=StockType.PRODUCT, warehouse_id=warehouse_b.id, product_id=product.id,
                lot_id=lot.id, quantity_on_hand=Decimal("5"), quantity_reserved=Decimal("2"),
                quantity_available=Decimal("3"), is_blocked=False,
            ),
        ]
        db.add_all(stocks)
        await db.flush()
        inspection = QCInspection(
            inspection_no=f"M27-T001-QC-{suffix}", qc_type=QCType.FINISHED_GOODS,
            status=QCStatus.FAILED, lot_id=lot.id, product_id=product.id,
            warehouse_id=warehouse_a.id, inspection_date=date.today(), is_mandatory=True,
            blocks_progression=True, release_required=True, decision=None,
        )
        db.add(inspection)
        await db.commit()
        lot_id, product_id = lot.id, product.id
        stock_ids = [row.id for row in stocks]
        inspection_id = inspection.id

        held = await qms_service.hold_lot(db, lot_id, "Synthetic mandatory QC hold", quarantine=True)
        await db.flush()
        assert held.hold_flag is True
        assert held.quarantine_flag is True
        assert held.shipment_eligible is False
        held_lot = await db.get(Lot, lot_id)
        assert held_lot.is_quarantine is True
        held_stocks = [await db.get(Stock, stock_id) for stock_id in stock_ids]
        assert [(row.is_blocked, row.quantity_reserved, row.quantity_available) for row in held_stocks] == [
            (True, Decimal("3.000"), Decimal("0.000")),
            (True, Decimal("2.000"), Decimal("0.000")),
        ]
        await db.commit()

        async def no_dispatch_gates(*_args):
            return []

        monkeypatch.setattr(qms_service, "list_dispatch_quality_gates", no_dispatch_gates)
        shipment = SimpleNamespace(
            shipment_no=f"M27-T001-SHIP-{suffix}",
            lines=[SimpleNamespace(lot_id=lot_id, product_id=product_id)],
        )
        with pytest.raises(ValueError, match="held, quarantined, or unreleased"):
            await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())
        await db.rollback()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        with pytest.raises(ValueError, match="mandatory quality inspection is unresolved"):
            await qms_service.release_lot(db, lot_id, None, "Synthetic attempted release")
        await db.rollback()

        inspection = await db.get(QCInspection, inspection_id)
        inspection.status = QCStatus.PASSED
        inspection.decision = QCDecision.ACCEPT
        await db.flush()
        released = await qms_service.release_lot(db, lot_id, None, "Synthetic accepted QC release")
        assert released.release_status == ReleaseStatus.RELEASED
        assert released.shipment_eligible is True
        await db.commit()

        released_stocks = [await db.get(Stock, stock_id) for stock_id in stock_ids]
        assert [(row.is_blocked, row.quantity_reserved, row.quantity_available) for row in released_stocks] == [
            (False, Decimal("3.000"), Decimal("7.000")),
            (False, Decimal("2.000"), Decimal("3.000")),
        ]
        assert (await db.get(Lot, lot_id)).is_quarantine is False
        assert (await db.execute(
            select(func.count()).select_from(StockMovement).where(
                StockMovement.lot_id == lot_id,
                StockMovement.movement_type == MovementType.ADJUSTMENT,
            )
        )).scalar_one() == 4

        await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())\n