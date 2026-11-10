"""M24.S04.T001 stock/production posting rollback checks for disposable PostgreSQL."""
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
from app.models.material_flow import MaterialFlowTransaction, ReservationStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.services import material_flow_service
from test_m24_s02_t001_material_issue_db import _issue, _make_issue_fixture


TASK_DB_ENV = "M24_S04_T001_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s04_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S04.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s04_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s04_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s04_t001_short")
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
async def test_material_issue_rows_and_stock_balances_rollback_as_one_unit():
    _require_task_database()
    suffix = uuid4().hex[:20]
    idempotency_key = f"m24-s04-t001-{suffix}-atomic-issue"
    async with AsyncSessionLocal() as db:
        reservation, stock_id, actor_id = await _make_issue_fixture(db, suffix)
        order_id = reservation.production_order_id
        reservation_id = reservation.id
        posted = await material_flow_service.issue_reserved_materials(
            db,
            reservation.id,
            _issue(reservation, 0, "1.000", idempotency_key),
            actor_id,
        )
        assert posted.status.value == "POSTED"
        flow_no = posted.flow_no
        await db.flush()

        # Simulate a later failure before the HTTP request commits its unit of work.
        await db.rollback()

    async with AsyncSessionLocal() as verify:
        stock = await verify.get(Stock, stock_id)
        order = await verify.get(ProductionOrder, order_id)
        reservation = await material_flow_service.get_reservation(verify, reservation_id)
        transaction = await verify.scalar(
            select(MaterialFlowTransaction).where(
                MaterialFlowTransaction.idempotency_key == idempotency_key
            )
        )
        movements = list(
            (
                await verify.scalars(
                    select(StockMovement).where(
                        StockMovement.reference_number == flow_no,
                        StockMovement.movement_type == MovementType.ISSUE,
                    )
                )
            ).all()
        )
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("5.000")
        assert stock.quantity_reserved == Decimal("3.000")
        assert stock.quantity_available == Decimal("2.000")
        assert reservation is not None
        assert reservation.lines[0].quantity_issued == Decimal("0.000")
        assert reservation.status == ReservationStatus.ACTIVE
        assert order is not None and order.status == ProductionOrderStatus.RELEASED
        assert transaction is None
        assert movements == []
