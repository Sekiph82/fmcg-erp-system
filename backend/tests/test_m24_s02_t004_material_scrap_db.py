"""M24.S02.T004 scrap/spillage coverage for a task-owned PostgreSQL database."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Stock, StockMovement
from app.models.material_flow import (
    FlowType,
    FlowStatus,
    MaterialFlowLine,
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
    MaterialScrapCreate,
    MaterialScrapReasonCode,
)
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _reservation, _seed_order


TASK_DB_ENV = "M24_S02_T004_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s02_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S02.T004 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s02_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s02_t004_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s02_t004_short")
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
        email=f"m24-s02-t004-{suffix}@example.invalid",
        username=f"m24s02t004{suffix}",
        full_name=f"Synthetic scrap operator {suffix}",
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
            idempotency_key=f"m24-s02-t004-{suffix}-issue",
            lines=[
                MaterialIssueLineCreate(
                    reservation_line_id=reservation.lines[0].id,
                    quantity=Decimal("2.000"),
                )
            ],
        ),
        actor.id,
    )
    issue_id = issue.id
    actor_id = actor.id
    await db.commit()
    issue = await material_flow_service.get_flow_transaction(db, issue_id)
    assert issue is not None
    return order_id, issue, stock_id, actor_id


async def _consume(db, order_id, issue_line_id, actor_id, suffix):
    return await material_flow_service.record_consumption(
        db,
        ConsumptionCreate(
            production_order_id=order_id,
            flow_line_id=issue_line_id,
            idempotency_key=f"m24-s02-t004-{suffix}-consume",
            quantity_consumed=Decimal("0.500"),
        ),
        actor_id,
    )


@pytest.mark.asyncio
async def test_scrap_is_linked_and_does_not_deplete_warehouse_stock_twice():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, issue, source_stock_id, actor_id = await _make_issued_line(db, suffix)
        issue_line = issue.lines[0]
        issue_line_id = issue_line.id
        issue_material_id = issue_line.material_id
        await _consume(db, order_id, issue_line_id, actor_id, suffix)
        await db.commit()
        returned = await material_flow_service.return_excess_material(
            db,
            issue_line_id,
            MaterialReturnCreate(
                idempotency_key=f"m24-s02-t004-{suffix}-return",
                quantity=Decimal("0.500"),
            ),
            actor_id,
        )
        returned_quantity = returned.lines[0].quantity
        await db.commit()

        stock_total_before = await db.scalar(
            select(func.coalesce(func.sum(Stock.quantity_on_hand), 0)).where(
                Stock.material_id == issue_material_id
            )
        )
        movement_count_before = await db.scalar(
            select(func.count(StockMovement.id)).where(
                StockMovement.material_id == issue_material_id
            )
        )
        key = f"m24-s02-t004-{suffix}-scrap"
        scrap = await material_flow_service.scrap_issued_material(
            db,
            issue_line_id,
            MaterialScrapCreate(
                idempotency_key=key,
                quantity=Decimal("1.000"),
                reason_code=MaterialScrapReasonCode.SPILLAGE,
                notes="Synthetic test spill during production.",
            ),
            actor_id,
        )
        scrap_id = scrap.id
        await db.commit()
        scrap = await material_flow_service.get_flow_transaction(db, scrap_id)
        assert scrap is not None

        assert scrap.status == FlowStatus.POSTED
        assert scrap.source_document_id == issue_line_id
        assert scrap.source_document_type == "MATERIAL_ISSUE_LINE"
        assert scrap.lines[0].reference_line_id == issue_line_id
        assert scrap.lines[0].scrap_flag is True
        assert scrap.lines[0].quality_status == QualityStatus.REJECTED
        event = await db.scalar(
            select(ProductionConsumption).where(
                ProductionConsumption.idempotency_key == key
            )
        )
        assert event is not None
        assert event.flow_line_id == issue_line_id
        assert event.scrap_flow_line_id == scrap.lines[0].id
        assert event.scrap_reason_code == "SPILLAGE"
        assert event.operator_id == actor_id
        assert event.quantity_scrapped == Decimal("1.000")
        assert event.quantity_variance == Decimal("0.000")
        assert returned_quantity == Decimal("0.500")

        stock_total_after = await db.scalar(
            select(func.coalesce(func.sum(Stock.quantity_on_hand), 0)).where(
                Stock.material_id == issue_material_id
            )
        )
        movement_count_after = await db.scalar(
            select(func.count(StockMovement.id)).where(
                StockMovement.material_id == issue_material_id
            )
        )
        scrap_movement_count = await db.scalar(
            select(func.count(StockMovement.id)).where(
                StockMovement.reference_number == scrap.flow_no
            )
        )
        assert Decimal(str(stock_total_after)) == Decimal(str(stock_total_before))
        assert movement_count_after == movement_count_before
        assert scrap_movement_count == 0
        assert await db.get(Stock, source_stock_id) is not None

        reconciliation = await material_flow_service.compute_reconciliation(db, order_id)
        assert reconciliation.total_issued == Decimal("2.000")
        assert reconciliation.total_consumed == Decimal("0.500")
        assert reconciliation.total_returned == Decimal("0.500")
        assert reconciliation.total_scrapped == Decimal("1.000")
        assert reconciliation.total_variance == Decimal("0.000")


@pytest.mark.asyncio
async def test_scrap_retry_is_idempotent_and_excess_is_rejected():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        _, issue, _, actor_id = await _make_issued_line(db, suffix)
        issue_line_id = issue.lines[0].id
        key = f"m24-s02-t004-{suffix}-same-key"
        request = MaterialScrapCreate(
            idempotency_key=key,
            quantity=Decimal("1.000"),
            reason_code=MaterialScrapReasonCode.DAMAGE,
            notes="Synthetic damage event.",
        )
        first = await material_flow_service.scrap_issued_material(
            db, issue_line_id, request, actor_id
        )
        await db.commit()
        replay = await material_flow_service.scrap_issued_material(
            db, issue_line_id, request, actor_id
        )
        await db.commit()
        assert replay.id == first.id

        with pytest.raises(HTTPException) as reused:
            await material_flow_service.scrap_issued_material(
                db,
                issue_line_id,
                MaterialScrapCreate(
                    idempotency_key=key,
                    quantity=Decimal("0.500"),
                    reason_code=MaterialScrapReasonCode.DAMAGE,
                    notes="Different request.",
                ),
                actor_id,
            )
        assert reused.value.status_code == 409
        assert reused.value.detail["error"] == "MATERIAL_SCRAP_IDEMPOTENCY_KEY_REUSED"
        await db.rollback()

        with pytest.raises(HTTPException) as overdrawn:
            await material_flow_service.scrap_issued_material(
                db,
                issue_line_id,
                MaterialScrapCreate(
                    idempotency_key=f"m24-s02-t004-{suffix}-overdraw",
                    quantity=Decimal("1.001"),
                    reason_code=MaterialScrapReasonCode.PROCESS_LOSS,
                    notes="Synthetic overdraw test.",
                ),
                actor_id,
            )
        assert overdrawn.value.status_code == 422
        assert overdrawn.value.detail["error"] == "MATERIAL_SCRAP_EXCEEDS_OUTSTANDING_ISSUE"
        await db.rollback()

        scrap_rows = list(
            (
                await db.scalars(
                    select(MaterialFlowTransaction).where(
                        MaterialFlowTransaction.source_document_type == "MATERIAL_ISSUE_LINE",
                        MaterialFlowTransaction.source_document_id == issue_line_id,
                        MaterialFlowTransaction.flow_type == FlowType.SCRAP,
                    )
                )
            ).all()
        )
        assert len(scrap_rows) == 1
        assert await db.scalar(
            select(func.count(MaterialFlowLine.id)).where(
                MaterialFlowLine.transaction_id == scrap_rows[0].id
            )
        ) == 1
