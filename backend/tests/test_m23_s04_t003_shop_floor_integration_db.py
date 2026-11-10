"""M23 Shop Floor execution, QC, and issued-material retry integration."""
from __future__ import annotations

import asyncio
import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.production_execution import ExecOrderMaterial, ExecWorkOrder, ProdExecOrder
from app.models.production_transition import ProductionTransitionEvent
from app.models.shop_floor import SFDowntimeLog, SFSession, WOActivityLog
from app.models.user import User
from app.services import shop_floor_service


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m23_s04_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> str:
    expected = os.environ.get("M23_S04_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M23_S04_T003_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_owned_database(engine.url, expected)
    ):
        pytest.fail("Refusing integration writes unless DATABASE_URL targets the exact loopback M23.S04.T003 database.")
    return expected


def test_database_guard_rejects_non_task_databases():
    name = "fmcg_m23_s04_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="codex_test", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m23_s04_t003_0123456789abcdef0124")
    assert not _is_task_owned_database(safe, "fmcg_m23_s04_t002_0123456789abcdef0123")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_issued_material_qc_and_finish_retries_preserve_one_execution_history():
    database_name = _require_task_owned_database()
    suffix = uuid4().hex[:20]
    user = User(
        email=f"m23-s04-t003-{suffix}@example.invalid",
        username=f"m23s04t003{suffix}",
        full_name="Synthetic Shop Floor operator",
        hashed_password="test-only",
    )
    parent = ProdExecOrder(
        order_no=f"M23-S04-T003-PO-{suffix}",
        planned_qty=Decimal("10"),
        uom="KG",
        status="IN_PROGRESS",
        line_id="SYNTHETIC-LINE-T003",
    )

    try:
        async with AsyncSessionLocal() as db:
            db.add_all([user, parent])
            await db.flush()
            work_order = ExecWorkOrder(
                production_order_id=parent.id,
                operation_code="SYNTHETIC-FILL",
                step_sequence=1,
                step_name="Synthetic filling operation",
                line_id="SYNTHETIC-LINE-T003",
                planned_qty=Decimal("10"),
                status="IN_PROGRESS",
                qc_required_flag=True,
                qc_passed=False,
            )
            db.add(work_order)
            await db.flush()
            session = SFSession(
                session_code=f"M23S04T003-{suffix}",
                authenticated_user_id=user.id,
                operator_name="Synthetic Shop Floor operator",
                line_id="SYNTHETIC-LINE-T003",
                current_work_order_id=work_order.id,
                status="ACTIVE",
            )
            material = ExecOrderMaterial(
                production_order_id=parent.id,
                work_order_id=work_order.id,
                item_type="MATERIAL",
                item_name="Synthetic issued material",
                item_code=f"SYN-MAT-{suffix}",
                required_qty=Decimal("5"),
                issued_qty=Decimal("5"),
                consumed_qty=Decimal("0"),
                returned_qty=Decimal("0"),
                scrapped_qty=Decimal("0"),
                uom="KG",
                status="ISSUED",
                lot_numbers=[f"SYN-LOT-{suffix}"],
            )
            db.add_all([session, material])
            await db.commit()
            actor_id, parent_id, work_order_id = user.id, parent.id, work_order.id
            session_id, material_id = session.id, material.id
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == database_name

            consumed = await shop_floor_service.consume_work_order_material(
                db, work_order_id, material_id, Decimal("2"),
                session_id=session_id, lot_no=f"SYN-LOT-{suffix}", actor_user_id=actor_id,
                idempotency_key="consume-retry-1", request_fingerprint="a" * 64,
            )
            assert consumed.consumed_qty == Decimal("2")

            consumed_retry = await shop_floor_service.consume_work_order_material(
                db, work_order_id, material_id, Decimal("2"),
                session_id=session_id, lot_no=f"SYN-LOT-{suffix}", actor_user_id=actor_id,
                idempotency_key="consume-retry-1", request_fingerprint="a" * 64,
            )
            assert consumed_retry.id == material_id
            assert consumed_retry.consumed_qty == Decimal("2")

            with pytest.raises(ValueError, match="Required in-process QC checkpoints"):
                await shop_floor_service.finish_work_order(
                    db, work_order_id, Decimal("4"), Decimal("0"), Decimal("0"), Decimal("12.5"),
                    session_id, "Synthetic Shop Floor operator", None,
                    actor_user_id=actor_id,
                    idempotency_key="finish-blocked-before-qc",
                    request_fingerprint="b" * 64,
                )
            await db.rollback()

            checkpoint = await shop_floor_service.record_qc_checkpoint(
                db, work_order_id,
                session_id=session_id,
                checkpoint_name="Synthetic fill weight",
                result="PASS",
                measured_value="4.0",
                unit="KG",
                actor_user_id=actor_id,
                idempotency_key="qc-retry-1",
                request_fingerprint="c" * 64,
            )
            checkpoint_retry = await shop_floor_service.record_qc_checkpoint(
                db, work_order_id,
                session_id=session_id,
                checkpoint_name="Synthetic fill weight",
                result="PASS",
                measured_value="4.0",
                unit="KG",
                actor_user_id=actor_id,
                idempotency_key="qc-retry-1",
                request_fingerprint="c" * 64,
            )
            assert checkpoint_retry.id == checkpoint.id

            finished = await shop_floor_service.finish_work_order(
                db, work_order_id, Decimal("4"), Decimal("0"), Decimal("0"), Decimal("12.5"),
                session_id, "Synthetic Shop Floor operator", None,
                actor_user_id=actor_id,
                idempotency_key="finish-retry-1",
                request_fingerprint="d" * 64,
            )
            finished_retry = await shop_floor_service.finish_work_order(
                db, work_order_id, Decimal("4"), Decimal("0"), Decimal("0"), Decimal("12.5"),
                session_id, "Synthetic Shop Floor operator", None,
                actor_user_id=actor_id,
                idempotency_key="finish-retry-1",
                request_fingerprint="d" * 64,
            )
            assert finished.status == "COMPLETED"
            assert finished_retry.status == "COMPLETED"
            assert finished_retry.completed_qty == Decimal("4")

            refreshed_material = await db.get(ExecOrderMaterial, material_id)
            assert refreshed_material.consumed_qty == Decimal("2")
            activity_count = await db.scalar(
                select(func.count()).select_from(WOActivityLog).where(
                    WOActivityLog.work_order_id == work_order_id,
                    WOActivityLog.actor_user_id == actor_id,
                    WOActivityLog.idempotency_key.in_(["consume-retry-1", "qc-retry-1", "finish-retry-1"]),
                )
            )
            assert activity_count == 3
            transition_count = await db.scalar(
                select(func.count()).select_from(ProductionTransitionEvent).where(
                    ProductionTransitionEvent.entity_id == work_order_id,
                    ProductionTransitionEvent.parent_entity_id == parent_id,
                    ProductionTransitionEvent.action == "SHOP_FLOOR_COMPLETED",
                )
            )
            assert transition_count == 1
            await db.commit()
    finally:
        # All rows are synthetic and this exact task-owned database is dropped
        # by the runner. Production transition history is append-only, so test
        # cleanup must not attempt to delete it.
        pass


@pytest.mark.asyncio
async def test_concurrent_authenticated_downtime_retries_create_one_record():
    database_name = _require_task_owned_database()
    suffix = uuid4().hex[:20]
    user = User(
        email=f"m23-s04-t003-race-{suffix}@example.invalid",
        username=f"m23s04t003race{suffix}",
        full_name="Synthetic Shop Floor operator",
        hashed_password="test-only",
    )
    key = f"downtime-race-{suffix}"
    data = {
        "created_by_user_id": None,
        "line_id": "SYNTHETIC-RACE-LINE",
        "downtime_category": "IT_ISSUE",
        "root_reason": "Synthetic concurrent retry",
        "start_idempotency_key": key,
        "start_idempotency_fingerprint": "e" * 64,
    }
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()
        data["created_by_user_id"] = user.id
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == database_name

    async def start_once():
        async with AsyncSessionLocal() as db:
            return await shop_floor_service.start_downtime(db, data)

    first, replay = await asyncio.gather(start_once(), start_once())
    assert first.id == replay.id
    assert first.created_by_user_id == user.id

    async with AsyncSessionLocal() as db:
        count = await db.scalar(
            select(func.count()).select_from(SFDowntimeLog).where(
                SFDowntimeLog.created_by_user_id == user.id,
                SFDowntimeLog.start_idempotency_key == key,
            )
        )
        assert count == 1
