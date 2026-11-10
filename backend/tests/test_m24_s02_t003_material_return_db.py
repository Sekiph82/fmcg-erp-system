"""M24.S02.T003 excess-return coverage for a task-owned PostgreSQL database."""
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
from app.models.inventory import MovementType, Stock, StockMovement
from app.models.material_flow import (
    FlowStatus,
    MaterialFlowTransaction,
    ProductionConsumption,
    QualityStatus,
)
from app.models.production import ProductionOrderStatus
from app.models.user import User
from app.schemas.material_flow import (
    ConsumptionCreate,
    MaterialIssueCreate,
    MaterialIssueLineCreate,
    MaterialReturnCreate,
)
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _reservation, _seed_order


TASK_DB_ENV = "M24_S02_T003_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s02_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S02.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s02_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s02_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s02_t003_short")
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


async def _make_issue_line(db, suffix: str):
    order_id, material_id, warehouse_id, stock_id, _, _ = await _seed_order(
        db,
        suffix,
        status=ProductionOrderStatus.IN_PROGRESS,
        stock_quantity=Decimal("5.000"),
    )
    actor = User(
        email=f"m24-s02-t003-{suffix}@example.invalid",
        username=f"m24s02t003{suffix}",
        full_name=f"Synthetic material return operator {suffix}",
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
            idempotency_key=f"m24-s02-t003-{suffix}-issue",
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


async def _consume(db, order_id, issue_line_id, actor_id, suffix):
    return await material_flow_service.record_consumption(
        db,
        ConsumptionCreate(
            production_order_id=order_id,
            flow_line_id=issue_line_id,
            idempotency_key=f"m24-s02-t003-{suffix}-consume",
            quantity_consumed=Decimal("0.500"),
        ),
        actor_id,
    )


@pytest.mark.asyncio
async def test_return_posts_blocked_stock_movement_and_consumption_lineage():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, issue_line_id, source_stock_id, actor_id = await _make_issue_line(db, suffix)
        await _consume(db, order_id, issue_line_id, actor_id, suffix)
        await db.commit()

        return_key = f"m24-s02-t003-{suffix}-return"
        returned = await material_flow_service.return_excess_material(
            db,
            issue_line_id,
            MaterialReturnCreate(idempotency_key=return_key, quantity=Decimal("1.500")),
            actor_id,
        )
        await db.commit()

        assert returned.status == FlowStatus.POSTED
        assert returned.source_document_type == "MATERIAL_ISSUE_LINE"
        assert returned.source_document_id == issue_line_id
        assert returned.lines[0].reference_line_id == issue_line_id
        assert returned.lines[0].return_flag is True
        assert returned.lines[0].quality_status == QualityStatus.QUARANTINE
        assert returned.lines[0].quantity == Decimal("1.500")

        return_events = list(
            (
                await db.scalars(
                    select(ProductionConsumption).where(
                        ProductionConsumption.idempotency_key == return_key
                    )
                )
            ).all()
        )
        assert len(return_events) == 1
        assert return_events[0].flow_line_id == issue_line_id
        assert return_events[0].return_flow_line_id == returned.lines[0].id
        assert return_events[0].operator_id == actor_id
        assert return_events[0].quantity_returned == Decimal("1.500")
        assert return_events[0].quantity_consumed == Decimal("0.000")

        movements = list(
            (
                await db.scalars(
                    select(StockMovement).where(
                        StockMovement.reference_number == returned.flow_no
                    )
                )
            ).all()
        )
        assert len(movements) == 1
        assert movements[0].movement_type == MovementType.RETURN
        assert movements[0].created_by_id == actor_id
        returned_stock = list(
            (
                await db.scalars(
                    select(Stock).where(
                        Stock.id != source_stock_id,
                        Stock.material_id == returned.lines[0].material_id,
                        Stock.warehouse_id == returned.lines[0].destination_warehouse_id,
                        Stock.quantity_on_hand == Decimal("1.500"),
                    )
                )
            ).all()
        )
        assert len(returned_stock) == 1
        assert returned_stock[0].is_blocked is True
        assert returned_stock[0].quantity_available == Decimal("1.500")

        reconciliation = await material_flow_service.compute_reconciliation(db, order_id)
        assert reconciliation.total_issued == Decimal("2.000")
        assert reconciliation.total_consumed == Decimal("0.500")
        assert reconciliation.total_returned == Decimal("1.500")
        assert reconciliation.total_variance == Decimal("0.000")


@pytest.mark.asyncio
async def test_return_retry_is_idempotent_and_cannot_return_consumed_quantity():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, issue_line_id, source_stock_id, actor_id = await _make_issue_line(db, suffix)
        await _consume(db, order_id, issue_line_id, actor_id, suffix)
        await db.commit()

        key = f"m24-s02-t003-{suffix}-same-key"
        request = MaterialReturnCreate(idempotency_key=key, quantity=Decimal("1.000"))
        first = await material_flow_service.return_excess_material(
            db, issue_line_id, request, actor_id
        )
        await db.commit()
        replay = await material_flow_service.return_excess_material(
            db, issue_line_id, request, actor_id
        )
        await db.commit()
        assert replay.id == first.id

        with pytest.raises(HTTPException) as reused:
            await material_flow_service.return_excess_material(
                db,
                issue_line_id,
                MaterialReturnCreate(idempotency_key=key, quantity=Decimal("0.500")),
                actor_id,
            )
        assert reused.value.status_code == 409
        assert reused.value.detail["error"] == "MATERIAL_RETURN_IDEMPOTENCY_KEY_REUSED"
        await db.rollback()

        with pytest.raises(HTTPException) as excess:
            await material_flow_service.return_excess_material(
                db,
                issue_line_id,
                MaterialReturnCreate(
                    idempotency_key=f"m24-s02-t003-{suffix}-overreturn",
                    quantity=Decimal("0.501"),
                ),
                actor_id,
            )
        assert excess.value.status_code == 422
        assert excess.value.detail["error"] == "MATERIAL_RETURN_EXCEEDS_UNUSED_ISSUE"
        await db.rollback()

        returns = list(
            (
                await db.scalars(
                    select(MaterialFlowTransaction).where(
                        MaterialFlowTransaction.source_document_id == issue_line_id,
                        MaterialFlowTransaction.source_document_type == "MATERIAL_ISSUE_LINE",
                    )
                )
            ).all()
        )
        assert len(returns) == 1
        source_stock = await db.get(Stock, source_stock_id)
        assert source_stock is not None
        stock_rows = list(
            (
                await db.scalars(
                    select(Stock).where(
                        Stock.id != source_stock_id,
                        Stock.material_id == source_stock.material_id,
                    )
                )
            ).all()
        )
        assert len(stock_rows) == 1
        assert stock_rows[0].quantity_on_hand == Decimal("1.000")
