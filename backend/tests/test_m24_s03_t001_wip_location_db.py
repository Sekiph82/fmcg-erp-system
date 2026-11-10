"""M24.S03.T001 WIP output/location ledger coverage for disposable PostgreSQL."""
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
from app.models.material_flow import FlowStatus, FlowStage, MaterialFlowLine, MaterialFlowTransaction, StageType
from app.models.production import ProductionOrderStatus
from app.models.user import User
from app.models.wms import StorageLocation, WarehouseZone, ZoneType
from app.schemas.material_flow import WIPOutputCreate, WIPTransferCreate
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _seed_order


TASK_DB_ENV = "M24_S03_T001_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S03.T001 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s03_t001_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s03_t001_short")
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


async def _make_wip_stages(db, warehouse_id, suffix: str, actor_suffix: str):
    zone = WarehouseZone(
        warehouse_id=warehouse_id,
        code=f"M24-S03-T001-Z-{suffix}",
        name=f"Synthetic WIP zone {suffix}",
        zone_type=ZoneType.SEMI_FINISHED,
        is_active=True,
    )
    db.add(zone)
    await db.flush()
    locations = [
        StorageLocation(
            zone_id=zone.id,
            code=f"M24-S03-T001-L{index}-{suffix}",
            name=f"Synthetic WIP location {index} {suffix}",
            is_active=True,
            is_blocked=False,
        )
        for index in (1, 2)
    ]
    db.add_all(locations)
    await db.flush()
    stages = [
        FlowStage(
            stage_code=f"M24-S03-T001-S{index}-{suffix}",
            stage_name=f"Synthetic WIP stage {index} {suffix}",
            stage_type=StageType.MIXING if index == 1 else StageType.INTERMEDIATE_HOLD,
            warehouse_id=warehouse_id,
            location_id=locations[index - 1].id,
            quality_default_status="QUARANTINE",
            active_flag=True,
        )
        for index in (1, 2)
    ]
    actor = User(
        email=f"m24-s03-t001-{actor_suffix}@example.invalid",
        username=f"m24s03t001{actor_suffix}",
        full_name=f"Synthetic WIP operator {actor_suffix}",
        hashed_password="test-only",
    )
    db.add_all([*stages, actor])
    await db.flush()
    stage_ids = [stage.id for stage in stages]
    location_ids = [location.id for location in locations]
    actor_id = actor.id
    await db.commit()
    return stage_ids, location_ids, actor_id


@pytest.mark.asyncio
async def test_wip_output_and_partial_transfer_preserve_location_balances_and_idempotency():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        output = await material_flow_service.record_wip_output(
            db,
            WIPOutputCreate(
                idempotency_key=f"m24-s03-t001-{suffix}-output",
                production_order_id=order_id,
                quantity=Decimal("8.000"),
                uom="KG",
                destination_stage_id=stages[0],
                destination_location_id=locations[0],
            ),
            actor_id,
        )
        output_id = output.id
        origin_line_id = output.lines[0].id
        retry = await material_flow_service.record_wip_output(
            db,
            WIPOutputCreate(
                idempotency_key=f"m24-s03-t001-{suffix}-output",
                production_order_id=order_id,
                quantity=Decimal("8.000"),
                uom="KG",
                destination_stage_id=stages[0],
                destination_location_id=locations[0],
            ),
            actor_id,
        )
        transfer_data = WIPTransferCreate(
            idempotency_key=f"m24-s03-t001-{suffix}-transfer",
            quantity=Decimal("3.000"),
            source_stage_id=stages[0],
            source_location_id=locations[0],
            destination_stage_id=stages[1],
            destination_location_id=locations[1],
        )
        transfer = await material_flow_service.transfer_wip(
            db, order_id, origin_line_id, transfer_data, actor_id
        )
        transfer_id = transfer.id
        transfer_retry = await material_flow_service.transfer_wip(
            db, order_id, origin_line_id, transfer_data, actor_id
        )
        balances = await material_flow_service.list_wip_balances(db, order_id)
        output = await material_flow_service.get_flow_transaction(db, output_id)
        transfer = await material_flow_service.get_flow_transaction(db, transfer_id)
        assert output is not None and transfer is not None

        assert output.status == FlowStatus.POSTED
        assert output.flow_type.value == "INTERMEDIATE_CREATE"
        assert retry.id == output_id
        assert transfer.status == FlowStatus.POSTED
        assert transfer.flow_type.value == "STAGE_TRANSFER"
        assert transfer.lines[0].reference_line_id == origin_line_id
        assert transfer_retry.id == transfer_id
        assert {(row.stage_id, row.location_id, row.quantity) for row in balances} == {
            (stages[0], locations[0], Decimal("5.000")),
            (stages[1], locations[1], Decimal("3.000")),
        }

        with pytest.raises(HTTPException) as overdraw:
            await material_flow_service.transfer_wip(
                db,
                order_id,
                origin_line_id,
                WIPTransferCreate(
                    idempotency_key=f"m24-s03-t001-{suffix}-overdraw",
                    quantity=Decimal("6.000"),
                    source_stage_id=stages[0],
                    source_location_id=locations[0],
                    destination_stage_id=stages[1],
                    destination_location_id=locations[1],
                ),
                actor_id,
            )
        assert overdraw.value.status_code == 409

        records = await db.execute(
            select(MaterialFlowTransaction).where(
                MaterialFlowTransaction.production_order_id == order_id,
                MaterialFlowTransaction.source_document_type.in_(("M24_WIP_OUTPUT", "M24_WIP_TRANSFER")),
            )
        )
        assert len(records.scalars().all()) == 2
        assert await db.get(MaterialFlowLine, origin_line_id) is not None


@pytest.mark.asyncio
async def test_wip_output_rejects_quantity_over_plan_and_mismatched_stage_location():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, _, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("0")
        )
        stages, locations, actor_id = await _make_wip_stages(db, warehouse_id, suffix, suffix)
        with pytest.raises(HTTPException) as over_plan:
            await material_flow_service.record_wip_output(
                db,
                WIPOutputCreate(
                    idempotency_key=f"m24-s03-t001-{suffix}-overplan",
                    production_order_id=order_id,
                    quantity=Decimal("10.001"),
                    uom="KG",
                    destination_stage_id=stages[0],
                    destination_location_id=locations[0],
                ),
                actor_id,
            )
        assert over_plan.value.status_code == 409
        await db.rollback()

        with pytest.raises(HTTPException) as wrong_location:
            await material_flow_service.record_wip_output(
                db,
                WIPOutputCreate(
                    idempotency_key=f"m24-s03-t001-{suffix}-wrongloc",
                    production_order_id=order_id,
                    quantity=Decimal("1.000"),
                    uom="KG",
                    destination_stage_id=stages[0],
                    destination_location_id=locations[1],
                ),
                actor_id,
            )
        assert wrong_location.value.status_code == 422
