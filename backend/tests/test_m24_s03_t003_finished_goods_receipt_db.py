"""M24.S03.T003 WIP-to-finished-goods posting checks for disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.material_flow import FlowStatus, FlowType, MaterialFlowTransaction
from app.models.production import ProductionOrderStatus
from app.schemas.material_flow import WIPOutputCreate, WIPTransferCreate
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _seed_order
from test_m24_s03_t001_wip_location_db import _make_wip_stages


TASK_DB_ENV = "M24_S03_T003_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S03.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s03_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s03_t003_short")
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
async def test_finished_goods_receipt_consumes_every_wip_origin_and_keeps_location_lineage():
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
                    idempotency_key=f"m24-s03-t003-{suffix}-output-{index}",
                    production_order_id=order_id,
                    quantity=quantity,
                    uom="KG",
                    destination_stage_id=stages[0],
                    destination_location_id=locations[0],
                ),
                actor_id,
            )
            origins.append(output.lines[0])

        await material_flow_service.transfer_wip(
            db,
            order_id,
            origins[0].id,
            WIPTransferCreate(
                idempotency_key=f"m24-s03-t003-{suffix}-partial-transfer",
                quantity=Decimal("2.000"),
                source_stage_id=stages[0],
                source_location_id=locations[0],
                destination_stage_id=stages[1],
                destination_location_id=locations[1],
            ),
            actor_id,
        )
        receipt = await material_flow_service.receive_wip_finished_goods(
            db,
            order_id,
            quantity=Decimal("9.000"),
            destination_warehouse_id=warehouse_id,
            created_by=actor_id,
        )
        balances = await material_flow_service.list_wip_balances(db, order_id)

        assert receipt is not None
        assert receipt.status == FlowStatus.POSTED
        assert receipt.flow_type == FlowType.FG_RECEIPT
        assert receipt.source_document_type == "M24_WIP_FG_RECEIPT"
        assert receipt.idempotency_key == f"M24-WIP-FG-RECEIPT:{order_id}"
        assert len(receipt.lines) == 3
        assert {line.reference_line_id for line in receipt.lines} == {origin.id for origin in origins}
        assert all(line.destination_warehouse_id == warehouse_id for line in receipt.lines)
        assert all(line.destination_stage_id is None and line.destination_location_id is None for line in receipt.lines)
        assert balances == []


@pytest.mark.asyncio
async def test_finished_goods_receipt_rejects_quantity_mismatch_without_posting():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        await material_flow_service.record_wip_output(
            db,
            WIPOutputCreate(
                idempotency_key=f"m24-s03-t003-{suffix}-output",
                production_order_id=order_id,
                quantity=Decimal("6.000"),
                uom="KG",
                destination_stage_id=stages[0],
                destination_location_id=locations[0],
            ),
            actor_id,
        )

        with pytest.raises(HTTPException) as mismatch:
            await material_flow_service.receive_wip_finished_goods(
                db,
                order_id,
                quantity=Decimal("5.000"),
                destination_warehouse_id=warehouse_id,
                created_by=actor_id,
            )
        assert mismatch.value.status_code == 409
        await db.rollback()
        result = await db.execute(
            select(MaterialFlowTransaction).where(
                MaterialFlowTransaction.production_order_id == order_id,
                MaterialFlowTransaction.source_document_type == "M24_WIP_FG_RECEIPT",
            )
        )
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_finished_goods_rejects_wip_output_with_mismatched_source_document():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        request = WIPOutputCreate(
            idempotency_key=f"m24-s03-t003-{suffix}-bad-source-document",
            production_order_id=order_id,
            quantity=Decimal("6.000"),
            uom="KG",
            destination_stage_id=stages[0],
            destination_location_id=locations[0],
        )
        output = await material_flow_service.record_wip_output(db, request, actor_id)
        output_id = output.id
        await db.execute(
            update(MaterialFlowTransaction)
            .where(MaterialFlowTransaction.id == output_id)
            .values(source_document_id=uuid4())
        )
        await db.commit()

        assert await material_flow_service.list_wip_balances(db, order_id) == []
        with pytest.raises(HTTPException) as retry:
            await material_flow_service.record_wip_output(db, request, actor_id)
        assert retry.value.status_code == 409

        with pytest.raises(HTTPException) as receipt:
            await material_flow_service.receive_wip_finished_goods(
                db,
                order_id,
                quantity=Decimal("6.000"),
                destination_warehouse_id=warehouse_id,
                created_by=actor_id,
            )
        assert receipt.value.status_code == 409
        await db.rollback()
        assert await db.scalar(
            select(MaterialFlowTransaction.id).where(
                MaterialFlowTransaction.production_order_id == order_id,
                MaterialFlowTransaction.source_document_type == "M24_WIP_FG_RECEIPT",
            )
        ) is None
