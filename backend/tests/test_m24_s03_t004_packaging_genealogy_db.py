"""M24.S03.T004 packaging issue/consumption linkage checks for disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.master import Material, MaterialType
from app.models.material_flow import FlowStatus, FlowType
from app.models.production import ProductionOrderStatus
from app.models.user import User
from app.schemas.material_flow import ConsumptionCreate, ReservationCreate, ReservationLineCreate, MaterialIssueCreate, MaterialIssueLineCreate
from app.services import material_flow_service
from test_m24_s01_t001_material_reservation_db import _seed_order


TASK_DB_ENV = "M24_S03_T004_DISPOSABLE_TEST_DATABASE"
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
        and re.fullmatch(r"fmcg_m24_s03_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S03.T004 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s03_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s03_t004_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s03_t004_short")
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
async def test_packaging_issue_and_actual_consumption_are_linked_to_exact_order_line():
    _require_task_database()
    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        order_id, material_id, warehouse_id, _, _, _ = await _seed_order(
            db, suffix, status=ProductionOrderStatus.IN_PROGRESS, stock_quantity=Decimal("12.000")
        )
        material = await db.get(Material, material_id)
        assert material is not None
        material.material_type = MaterialType.PACKAGING
        actor = User(
            email=f"m24-s03-t004-{suffix}@example.invalid",
            username=f"m24s03t004{suffix}",
            full_name=f"Synthetic packaging operator {suffix}",
            hashed_password="test-only",
        )
        db.add(actor)
        await db.flush()
        actor_id = actor.id
        reservation = await material_flow_service.create_reservation(
            db,
            ReservationCreate(
                production_order_id=order_id,
                lines=[ReservationLineCreate(
                    line_no=1,
                    material_id=material_id,
                    warehouse_id=warehouse_id,
                    quantity_required=Decimal("8.000"),
                    uom="KG",
                )],
            ),
            actor.id,
        )
        reservation_id = reservation.id
        reservation_line_id = reservation.lines[0].id
        await db.commit()
        issue = await material_flow_service.issue_reserved_materials(
            db,
            reservation_id,
            MaterialIssueCreate(
                idempotency_key=f"m24-s03-t004-{suffix}-package-issue",
                lines=[MaterialIssueLineCreate(reservation_line_id=reservation_line_id, quantity=Decimal("6.000"))],
            ),
            actor_id,
            flow_type=FlowType.PKG_ISSUE,
        )
        issue_id = issue.id
        issue_line_id = issue.lines[0].id
        issue_reservation_line_id = issue.lines[0].reservation_line_id
        await db.commit()
        issue = await material_flow_service.get_flow_transaction(db, issue_id)
        assert issue is not None
        issue_status = issue.status
        issue_flow_type = issue.flow_type
        issue_production_order_id = issue.production_order_id
        consumption = await material_flow_service.record_consumption(
            db,
            ConsumptionCreate(
                production_order_id=order_id,
                flow_line_id=issue_line_id,
                idempotency_key=f"m24-s03-t004-{suffix}-package-use",
                quantity_consumed=Decimal("4.000"),
                notes="Synthetic packaging use for acceptance coverage.",
            ),
            actor_id,
        )

        assert issue_status == FlowStatus.POSTED
        assert issue_flow_type == FlowType.PKG_ISSUE
        assert issue_production_order_id == order_id
        assert issue_reservation_line_id == reservation_line_id
        assert consumption.flow_line_id == issue_line_id
        assert consumption.production_order_id == order_id
        assert consumption.quantity_consumed == Decimal("4.000")
        assert consumption.quantity_variance == Decimal("2.000")
        assert consumption.operator_id == actor_id
