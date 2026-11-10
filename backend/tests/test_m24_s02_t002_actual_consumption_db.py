"""M24.S02.T002 actual-consumption coverage for a task-owned PostgreSQL database."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Stock
from app.models.material_flow import ProductionConsumption
from app.models.production import ProductionOrderStatus
from app.models.user import User
from app.schemas.material_flow import (
    MaterialIssueCreate,
    MaterialIssueLineCreate,
    ConsumptionCreate,
)
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _reservation, _seed_order


TASK_DB_ENV = "M24_S02_T002_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s02_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S02.T002 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s02_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s02_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s02_t002_short")
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


async def _make_issued_line(db, suffix: str):
    order_id, material_id, warehouse_id, stock_id, _, _ = await _seed_order(
        db,
        suffix,
        status=ProductionOrderStatus.IN_PROGRESS,
        stock_quantity=Decimal("5.000"),
    )
    actor = User(
        email=f"m24-s02-t002-{suffix}@example.invalid",
        username=f"m24s02t002{suffix}",
        full_name=f"Synthetic consumption operator {suffix}",
        hashed_password="test-only",
    )
    db.add(actor)
    await db.flush()
    reservation = await material_flow_service.create_reservation(
        db,
        _reservation(order_id, material_id, warehouse_id, "3.000"),
        actor.id,
    )
    await db.flush()
    issue = await material_flow_service.issue_reserved_materials(
        db,
        reservation.id,
        MaterialIssueCreate(
            idempotency_key=f"m24-s02-t002-{suffix}-issue",
            lines=[
                MaterialIssueLineCreate(
                    reservation_line_id=reservation.lines[0].id,
                    quantity=Decimal("2.000"),
                )
            ],
        ),
        actor.id,
    )
    await db.commit()
    return order_id, issue.lines[0].id, stock_id, actor.id


def _consumption(order_id, flow_line_id, quantity: str, key: str) -> ConsumptionCreate:
    return ConsumptionCreate(
        production_order_id=order_id,
        flow_line_id=flow_line_id,
        idempotency_key=key,
        quantity_consumed=Decimal(quantity),
    )


@pytest.mark.asyncio
async def test_consumption_links_to_posted_issue_and_leaves_stock_unchanged():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, flow_line_id, stock_id, actor_id = await _make_issued_line(db, suffix)
        request = _consumption(
            order_id, flow_line_id, "1.250", f"m24-s02-t002-{suffix}-consume"
        )
        consumption = await material_flow_service.record_consumption(db, request, actor_id)
        await db.commit()

        stock = await db.get(Stock, stock_id)
        assert consumption.flow_line_id == flow_line_id
        assert consumption.operator_id == actor_id
        assert consumption.quantity_issued == Decimal("2.000")
        assert consumption.quantity_consumed == Decimal("1.250")
        assert consumption.quantity_variance == Decimal("0.750")
        assert consumption.quantity_returned == Decimal("0.000")
        assert consumption.quantity_scrapped == Decimal("0.000")
        assert stock.quantity_on_hand == Decimal("3.000")
        assert stock.quantity_reserved == Decimal("1.000")
        assert stock.quantity_available == Decimal("2.000")


@pytest.mark.asyncio
async def test_consumption_retry_is_idempotent_and_overconsumption_is_rejected():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, flow_line_id, stock_id, actor_id = await _make_issued_line(db, suffix)
        key = f"m24-s02-t002-{suffix}-same-key"
        request = _consumption(order_id, flow_line_id, "1.000", key)
        first = await material_flow_service.record_consumption(db, request, actor_id)
        await db.commit()

        replay = await material_flow_service.record_consumption(db, request, actor_id)
        await db.commit()
        assert replay.id == first.id

        with pytest.raises(HTTPException) as reused:
            await material_flow_service.record_consumption(
                db,
                _consumption(order_id, flow_line_id, "0.500", key),
                actor_id,
            )
        assert reused.value.status_code == 409
        assert reused.value.detail["error"] == "MATERIAL_CONSUMPTION_IDEMPOTENCY_KEY_REUSED"
        await db.rollback()

        with pytest.raises(HTTPException) as overdrawn:
            await material_flow_service.record_consumption(
                db,
                _consumption(
                    order_id,
                    flow_line_id,
                    "1.001",
                    f"m24-s02-t002-{suffix}-overdraw",
                ),
                actor_id,
            )
        assert overdrawn.value.status_code == 422
        assert overdrawn.value.detail["error"] == "MATERIAL_CONSUMPTION_EXCEEDS_ISSUED_QUANTITY"
        await db.rollback()

        rows = list(
            (
                await db.scalars(
                    select(ProductionConsumption).where(
                        ProductionConsumption.flow_line_id == flow_line_id
                    )
                )
            ).all()
        )
        stock = await db.get(Stock, stock_id)
        assert len(rows) == 1
        assert rows[0].quantity_consumed == Decimal("1.000")
        assert stock.quantity_on_hand == Decimal("3.000")
        assert stock.quantity_reserved == Decimal("1.000")
        assert stock.quantity_available == Decimal("2.000")
