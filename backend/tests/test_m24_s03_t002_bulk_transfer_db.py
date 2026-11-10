"""M24.S03.T002 bulk WIP transfer checks for disposable PostgreSQL."""
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
from app.models.inventory import StockMovement
from app.models.material_flow import FlowStatus, FlowType, MaterialFlowTransaction
from app.models.production import ProductionOrderStatus
from app.schemas.material_flow import (
    WIPBulkTransferCreate,
    WIPBulkTransferLineCreate,
    WIPOutputCreate,
)
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _seed_order
from test_m24_s03_t001_wip_location_db import _make_wip_stages


TASK_DB_ENV = "M24_S03_T002_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s03_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S03.T002 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s03_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s03_t002_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s03_t002_short")
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
async def test_bulk_transfer_is_atomic_idempotent_and_preserves_per_origin_balances():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        origins = []
        for index, quantity in enumerate((Decimal("5.000"), Decimal("4.000")), start=1):
            output = await material_flow_service.record_wip_output(
                db,
                WIPOutputCreate(
                    idempotency_key=f"m24-s03-t002-{suffix}-output-{index}",
                    production_order_id=order_id,
                    quantity=quantity,
                    uom="KG",
                    destination_stage_id=stages[0],
                    destination_location_id=locations[0],
                ),
                actor_id,
            )
            origins.append(output.lines[0].id)

        data = WIPBulkTransferCreate(
            idempotency_key=f"m24-s03-t002-{suffix}-bulk",
            lines=[
                WIPBulkTransferLineCreate(
                    origin_line_id=origins[0],
                    quantity=Decimal("2.000"),
                    source_stage_id=stages[0],
                    source_location_id=locations[0],
                    destination_stage_id=stages[1],
                    destination_location_id=locations[1],
                ),
                WIPBulkTransferLineCreate(
                    origin_line_id=origins[1],
                    quantity=Decimal("1.000"),
                    source_stage_id=stages[0],
                    source_location_id=locations[0],
                    destination_stage_id=stages[1],
                    destination_location_id=locations[1],
                ),
            ],
        )
        transaction = await material_flow_service.transfer_wip_bulk(db, order_id, data, actor_id)
        transaction_id = transaction.id
        retry = await material_flow_service.transfer_wip_bulk(db, order_id, data, actor_id)
        balances = await material_flow_service.list_wip_balances(db, order_id)
        transaction = await material_flow_service.get_flow_transaction(db, transaction_id)
        assert transaction is not None

        assert transaction.status == FlowStatus.POSTED
        assert transaction.flow_type == FlowType.BULK_TRANSFER
        assert len(transaction.lines) == 2
        assert retry.id == transaction.id
        assert {(row.origin_line_id, row.stage_id, row.quantity) for row in balances} == {
            (origins[0], stages[0], Decimal("3.000")),
            (origins[0], stages[1], Decimal("2.000")),
            (origins[1], stages[0], Decimal("3.000")),
            (origins[1], stages[1], Decimal("1.000")),
        }
        movement_count = await db.scalar(
            select(StockMovement.id).where(StockMovement.reference_number == transaction.flow_no).limit(1)
        )
        assert movement_count is None


@pytest.mark.asyncio
async def test_bulk_transfer_rejects_overdraw_without_creating_a_partial_transaction():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        origins = []
        for index in (1, 2):
            output = await material_flow_service.record_wip_output(
                db,
                WIPOutputCreate(
                    idempotency_key=f"m24-s03-t002-{suffix}-seed-{index}",
                    production_order_id=order_id,
                    quantity=Decimal("2.000"),
                    uom="KG",
                    destination_stage_id=stages[0],
                    destination_location_id=locations[0],
                ),
                actor_id,
            )
            origins.append(output.lines[0])
        with pytest.raises(HTTPException) as overdraw:
            await material_flow_service.transfer_wip_bulk(
                db,
                order_id,
                WIPBulkTransferCreate(
                    idempotency_key=f"m24-s03-t002-{suffix}-overdraw",
                    lines=[
                        WIPBulkTransferLineCreate(
                            origin_line_id=origins[0].id,
                            quantity=Decimal("1.000"),
                            source_stage_id=stages[0],
                            source_location_id=locations[0],
                            destination_stage_id=stages[1],
                            destination_location_id=locations[1],
                        ),
                        WIPBulkTransferLineCreate(
                            origin_line_id=origins[1].id,
                            quantity=Decimal("2.001"),
                            source_stage_id=stages[0],
                            source_location_id=locations[0],
                            destination_stage_id=stages[1],
                            destination_location_id=locations[1],
                        ),
                    ],
                ),
                actor_id,
            )
        assert overdraw.value.status_code == 409
        await db.rollback()
        result = await db.execute(
            select(MaterialFlowTransaction).where(
                MaterialFlowTransaction.production_order_id == order_id,
                MaterialFlowTransaction.source_document_type == "M24_WIP_BULK_TRANSFER",
            )
        )
        assert result.scalars().all() == []
