"""M24.S02.T001 inventory-aware issue coverage for a task-owned PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot, MovementType, Stock, StockMovement
from app.models.material_flow import (
    FlowStatus,
    MaterialFlowTransaction,
    ReservationStatus,
)
from app.models.user import User
from app.models.production import ProductionOrderStatus
from app.schemas.material_flow import MaterialIssueCreate, MaterialIssueLineCreate
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _add_lot_stock, _reservation, _seed_order


TASK_DB_ENV = "M24_S02_T001_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s02_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S02.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s02_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s02_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s02_t001_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name),
        name,
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _make_issue_fixture(db, suffix: str):
    order_id, material_id, warehouse_id, stock_id, _, _ = await _seed_order(
        db,
        suffix,
        status=ProductionOrderStatus.RELEASED,
        stock_quantity=Decimal("5.000"),
    )
    actor = User(
        email=f"m24-s02-t001-{suffix}@example.invalid",
        username=f"m24s02t001{suffix}",
        full_name=f"Synthetic material issuer {suffix}",
        hashed_password="test-only",
    )
    db.add(actor)
    await db.flush()
    reservation = await material_flow_service.create_reservation(
        db,
        _reservation(order_id, material_id, warehouse_id, "3.000"),
        actor.id,
    )
    reservation_id = reservation.id
    await db.commit()
    reservation = await material_flow_service.get_reservation(db, reservation_id)
    assert reservation is not None
    return reservation, stock_id, actor.id


def _issue(reservation, line_index: int, quantity: str, key: str) -> MaterialIssueCreate:
    return MaterialIssueCreate(
        idempotency_key=key,
        lines=[
            MaterialIssueLineCreate(
                reservation_line_id=reservation.lines[line_index].id,
                quantity=Decimal(quantity),
            )
        ],
    )


@pytest.mark.asyncio
async def test_partial_and_final_issue_are_atomic_and_idempotent():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        reservation, stock_id, actor_id = await _make_issue_fixture(db, suffix)
        first_request = _issue(reservation, 0, "1.000", f"m24-s02-t001-{suffix}-first")
        first = await material_flow_service.issue_reserved_materials(
            db, reservation.id, first_request, actor_id
        )
        await db.commit()

        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation.id)
        assert first.status == FlowStatus.POSTED
        assert first.created_by == actor_id
        assert first.source_document_type == "MATERIAL_RESERVATION"
        assert first.source_document_id == reservation.id
        assert first.lines[0].reservation_line_id == reservation.lines[0].id
        assert stock.quantity_on_hand == Decimal("4.000")
        assert stock.quantity_reserved == Decimal("2.000")
        assert stock.quantity_available == Decimal("2.000")
        assert reservation.lines[0].quantity_issued == Decimal("1.000")
        assert reservation.status == ReservationStatus.PARTIALLY_ISSUED

        replay = await material_flow_service.issue_reserved_materials(
            db, reservation.id, first_request, actor_id
        )
        await db.commit()
        assert replay.id == first.id

        second_request = _issue(reservation, 0, "2.000", f"m24-s02-t001-{suffix}-final")
        second = await material_flow_service.issue_reserved_materials(
            db, reservation.id, second_request, actor_id
        )
        await db.commit()
        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation.id)
        movements = list(
            (
                await db.scalars(
                    select(StockMovement).where(
                        StockMovement.reference_number.in_([first.flow_no, second.flow_no])
                    )
                )
            ).all()
        )
        assert len(movements) == 2
        assert all(movement.movement_type == MovementType.ISSUE for movement in movements)
        assert all(movement.created_by_id == actor_id for movement in movements)
        assert stock.quantity_on_hand == Decimal("2.000")
        assert stock.quantity_reserved == Decimal("0.000")
        assert stock.quantity_available == Decimal("2.000")
        assert reservation.lines[0].quantity_issued == Decimal("3.000")
        assert reservation.status == ReservationStatus.FULLY_ISSUED


@pytest.mark.asyncio
async def test_issue_rejects_overdrawn_and_reused_key_without_second_movement():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        reservation, stock_id, actor_id = await _make_issue_fixture(db, suffix)
        reservation_id = reservation.id
        key = f"m24-s02-t001-{suffix}-same-key"
        first = await material_flow_service.issue_reserved_materials(
            db, reservation_id, _issue(reservation, 0, "1.000", key), actor_id
        )
        first_flow_no = first.flow_no
        await db.commit()

        reservation = await material_flow_service.get_reservation(db, reservation_id)
        with pytest.raises(HTTPException) as reused:
            await material_flow_service.issue_reserved_materials(
                db, reservation_id, _issue(reservation, 0, "2.000", key), actor_id
            )
        assert reused.value.status_code == 409
        assert reused.value.detail["error"] == "MATERIAL_ISSUE_IDEMPOTENCY_KEY_REUSED"
        await db.rollback()

        reservation = await material_flow_service.get_reservation(db, reservation_id)
        with pytest.raises(HTTPException) as overdrawn:
            await material_flow_service.issue_reserved_materials(
                db,
                reservation_id,
                _issue(reservation, 0, "3.000", f"m24-s02-t001-{suffix}-overdraw"),
                actor_id,
            )
        assert overdrawn.value.status_code == 422
        assert overdrawn.value.detail["error"] == "MATERIAL_ISSUE_EXCEEDS_RESERVED_QUANTITY"
        await db.rollback()

        movements = list(
            (
                await db.scalars(
                    select(StockMovement).where(StockMovement.reference_number == first_flow_no)
                )
            ).all()
        )
        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation_id)
        assert len(movements) == 1
        assert stock.quantity_on_hand == Decimal("4.000")
        assert stock.quantity_reserved == Decimal("2.000")
        assert reservation.lines[0].quantity_issued == Decimal("1.000")


@pytest.mark.asyncio
async def test_past_event_timestamp_cannot_make_currently_expired_reserved_lot_issuable():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, _, source_location_id, _ = await _seed_order(
            db,
            suffix,
            status=ProductionOrderStatus.RELEASED,
            stock_quantity=Decimal("0.000"),
        )
        lot_id, _, stock_id = await _add_lot_stock(
            db,
            suffix=f"EXPIRY-BOUNDARY-{suffix}",
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            expiry_date=datetime.now(timezone.utc).date() + timedelta(days=2),
            quantity=Decimal("3.000"),
        )
        actor = User(
            email=f"m24-s02-t001-expiry-{suffix}@example.invalid",
            username=f"m24s02t001expiry{suffix}",
            full_name=f"Synthetic expiry checker {suffix}",
            hashed_password="test-only",
        )
        db.add(actor)
        await db.flush()
        actor_id = actor.id
        reservation = await material_flow_service.create_reservation(
            db,
            _reservation(order_id, material_id, warehouse_id, "1.000"),
            actor_id,
        )
        lot = await db.get(Lot, lot_id)
        assert lot is not None
        lot.expiry_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        reservation_id = reservation.id
        await db.commit()
        reservation = await material_flow_service.get_reservation(db, reservation_id)
        assert reservation is not None

        request = _issue(reservation, 0, "1.000", f"m24-s02-t001-{suffix}-past-date")
        request.transaction_datetime = datetime.now(timezone.utc) - timedelta(days=2)
        with pytest.raises(HTTPException) as raised:
            await material_flow_service.issue_reserved_materials(
                db, reservation_id, request, actor_id
            )
        assert raised.value.status_code == 409
        assert raised.value.detail["error"] == "MATERIAL_ISSUE_LOT_NOT_ELIGIBLE"
        await db.rollback()

        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation_id)
        movements = list(
            (
                await db.scalars(
                    select(StockMovement).where(
                        StockMovement.lot_id == lot_id
                    )
                )
            ).all()
        )
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("3.000")
        assert stock.quantity_reserved == Decimal("1.000")
        assert stock.quantity_available == Decimal("2.000")
        assert reservation is not None
        assert reservation.lines[0].quantity_issued == Decimal("0.000")
        assert movements == []


@pytest.mark.asyncio
async def test_issue_rejects_line_from_another_reservation_without_mutation():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        reservation, stock_id, actor_id = await _make_issue_fixture(db, suffix)
        reservation_id = reservation.id
        wrong_line_id = uuid4()
        request = MaterialIssueCreate(
            idempotency_key=f"m24-s02-t001-{suffix}-wrong-line",
            lines=[MaterialIssueLineCreate(reservation_line_id=wrong_line_id, quantity=Decimal("1.000"))],
        )
        with pytest.raises(HTTPException) as mismatch:
            await material_flow_service.issue_reserved_materials(
                db, reservation_id, request, actor_id
            )
        assert mismatch.value.status_code == 422
        assert mismatch.value.detail["error"] == "MATERIAL_ISSUE_RESERVATION_LINE_MISMATCH"
        await db.rollback()
        stock = await db.get(Stock, stock_id)
        reservation = await material_flow_service.get_reservation(db, reservation_id)
        assert stock.quantity_on_hand == Decimal("5.000")
        assert stock.quantity_reserved == Decimal("3.000")
        assert reservation.lines[0].quantity_issued == Decimal("0.000")
        assert await db.scalar(
            select(MaterialFlowTransaction.id).where(
                MaterialFlowTransaction.idempotency_key == request.idempotency_key
            )
        ) is None
