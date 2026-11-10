"""M24.S04.T002 reserved-consumption genealogy checks for disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import MovementType, Stock, StockMovement
from app.models.material_flow import ReservationStatus
from app.models.master import Warehouse, WarehouseType
from app.models.production import (
    FinishedGoodsReceipt,
    MaterialConsumption,
    ProductionOrder,
    ProductionOrderStatus,
)
from app.models.quality import ReleaseStatus
from app.models.recipe import RecipeItem
from app.models.traceability import (
    GenealogyRelType,
    LotGenealogyLink,
    TraceEvent,
    TraceEventLine,
    TraceItemStage,
)
from app.models.user import User
from app.schemas.material_flow import (
    ConsumptionCreate,
    MaterialIssueCreate,
    MaterialIssueLineCreate,
)
from app.schemas.production import CompleteOrderRequest
from app.services import material_flow_service, production_service
from test_m24_s01_t001_material_reservation_db import (
    _add_lot_stock,
    _reservation,
    _seed_order,
)


TASK_DB_ENV = "M24_S04_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = f"{TASK_DB_ENV}_NAME"
pytestmark = pytest.mark.skipif(
    os.environ.get(TASK_DB_ENV) != "1",
    reason=f"requires this task's disposable PostgreSQL database ({TASK_DB_ENV}=1)",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m24_s04_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S04.T002 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s04_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s04_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s04_t002_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name), name
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_reserved_raw_consumption_creates_finished_lot_genealogy_without_double_issue():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, source_warehouse_id, _, _, _ = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.IN_PROGRESS,
            stock_quantity=Decimal("0.000"),
        )
        order = await db.get(ProductionOrder, order_id)
        assert order is not None
        order_no = order.order_no
        finished_warehouse = Warehouse(
            code=f"M24-S04-T002-FG-{suffix}",
            name=f"Synthetic finished-goods warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS,
            is_active=True,
        )
        db.add(finished_warehouse)
        await db.flush()
        order.target_warehouse_id = finished_warehouse.id
        db.add(RecipeItem(
            recipe_id=order.recipe_id,
            material_id=material_id,
            line_no=1,
            quantity=Decimal("2.0000"),
            unit="KG",
            loss_percentage=Decimal("0"),
            is_optional=False,
        ))
        lot_id, _, stock_id = await _add_lot_stock(
            db,
            suffix=suffix,
            warehouse_id=source_warehouse_id,
            material_id=material_id,
            location_id=(await db.scalar(
                select(Stock.location_id).where(
                    Stock.material_id == material_id,
                    Stock.warehouse_id == source_warehouse_id,
                )
            )),
            expiry_date=None,
            quantity=Decimal("12.000"),
            release_status=ReleaseStatus.RELEASED,
            fefo_eligible=True,
        )
        actor = User(
            email=f"m24-s04-t002-{suffix}@example.invalid",
            username=f"m24s04t002{suffix}",
            full_name=f"Synthetic genealogy operator {suffix}",
            hashed_password="test-only",
        )
        db.add(actor)
        await db.commit()

        reservation = await material_flow_service.create_reservation(
            db,
            _reservation(
                order_id,
                material_id,
                source_warehouse_id,
                "6.000",
                lot_id=lot_id,
                lot_fixed=True,
            ),
            actor.id,
        )
        reservation_id = reservation.id
        await db.commit()
        reservation = await material_flow_service.get_reservation(db, reservation_id)
        assert reservation is not None
        issue = await material_flow_service.issue_reserved_materials(
            db,
            reservation.id,
            MaterialIssueCreate(
                idempotency_key=f"m24-s04-t002-{suffix}-issue",
                lines=[MaterialIssueLineCreate(
                    reservation_line_id=reservation.lines[0].id,
                    quantity=Decimal("4.000"),
                )],
            ),
            actor.id,
        )
        issue_id = issue.id
        issue_line_id = issue.lines[0].id
        issue_source_location_id = issue.lines[0].source_location_id
        await db.commit()
        consumption = await material_flow_service.record_consumption(
            db,
            ConsumptionCreate(
                production_order_id=order_id,
                flow_line_id=issue_line_id,
                idempotency_key=f"m24-s04-t002-{suffix}-consume",
                quantity_consumed=Decimal("2.500"),
                notes="Synthetic actual raw-material consumption.",
            ),
            actor.id,
        )
        consumption_id = consumption.id
        consumed_quantity = consumption.quantity_consumed
        await db.commit()

        await production_service.complete_order(
            db,
            await db.get(ProductionOrder, order_id),
            CompleteOrderRequest(
                actual_quantity=Decimal("4.000"),
                fg_lot_number=f"M24-S04-T002-FG-LOT-{suffix}",
                consume_materials=True,
            ),
            actor.id,
        )
        await db.commit()

        issue = await material_flow_service.get_flow_transaction(db, issue_id)
        assert issue is not None

        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation.id)
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("8.000")
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("8.000")
        assert reservation is not None
        assert reservation.status == ReservationStatus.CANCELLED
        assert await db.scalar(
            select(MaterialConsumption.id).where(
                MaterialConsumption.production_order_id == order_id
            )
        ) is None
        assert await db.scalar(
            select(StockMovement.id).where(
                StockMovement.reference_number == order_no,
                StockMovement.movement_type == MovementType.ISSUE,
            )
        ) is None

        receipt = await db.scalar(
            select(FinishedGoodsReceipt).where(
                FinishedGoodsReceipt.production_order_id == order_id
            )
        )
        assert receipt is not None
        receipt_movement = await db.get(StockMovement, receipt.stock_movement_id)
        assert receipt_movement is not None and receipt_movement.lot_id is not None
        event = await db.scalar(
            select(TraceEvent).where(TraceEvent.production_order_id == order_id)
        )
        assert event is not None
        event_lines = list(
            (
                await db.scalars(
                    select(TraceEventLine).where(TraceEventLine.event_id == event.id)
                )
            ).all()
        )
        assert len(event_lines) == 1
        trace_line = event_lines[0]
        assert trace_line.material_id == material_id
        assert trace_line.source_lot_id == lot_id
        assert trace_line.child_lot_id == receipt_movement.lot_id
        assert trace_line.quantity == consumed_quantity == Decimal("2.500")
        assert trace_line.source_stage == TraceItemStage.raw_stock
        assert trace_line.dest_stage == TraceItemStage.finished_good
        assert trace_line.source_location_id == issue_source_location_id
        assert str(consumption_id) in (trace_line.notes or "")
        link = await db.scalar(
            select(LotGenealogyLink).where(
                LotGenealogyLink.production_order_id == order_id,
                LotGenealogyLink.parent_lot_id == lot_id,
                LotGenealogyLink.child_lot_id == receipt_movement.lot_id,
            )
        )
        assert link is not None
        assert link.relationship_type == GenealogyRelType.intermediate_from
        assert link.quantity_linked == Decimal("2.500")
