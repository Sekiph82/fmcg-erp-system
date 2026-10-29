"""Concurrent QMS hold/release checks on a task-owned disposable database."""
from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.services.qms_service import hold_lot, release_lot


pytestmark = pytest.mark.skipif(
    os.environ.get("M10_S02_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M10_S02_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"fmcg_m10_s02_t004_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(text("SELECT current_database()"))).scalar_one()
    assert actual == expected


async def _create_synthetic_lot(db) -> Lot:
    suffix = uuid4().hex[:16]
    product = Product(
        sku=f"M10-T004-{suffix}",
        name="Synthetic transaction test product",
        category=ProductCategory.OTHER,
        uom=UnitOfMeasure.PCS,
    )
    db.add(product)
    await db.flush()
    lot = Lot(lot_number=f"M10-T004-LOT-{suffix}", product_id=product.id)
    db.add(lot)
    await db.flush()
    return lot


@pytest.mark.asyncio
async def test_concurrent_first_hold_and_release_share_one_serialized_lot_status():
    async with AsyncSessionLocal() as setup:
        await _assert_task_database(setup)
        lot = await _create_synthetic_lot(setup)
        lot_id = lot.id
        await setup.commit()

    async with AsyncSessionLocal() as hold_db:
        await _assert_task_database(hold_db)
        held = await hold_lot(hold_db, lot_id, "Synthetic transaction test hold")
        assert held.hold_flag is True

        release_started = asyncio.Event()

        async def release_after_hold_row_exists():
            async with AsyncSessionLocal() as release_db:
                await _assert_task_database(release_db)
                release_started.set()
                released = await release_lot(release_db, lot_id, None, "Synthetic release")
                await release_db.commit()
                return released

        release_task = asyncio.create_task(release_after_hold_row_exists())
        await release_started.wait()
        await asyncio.sleep(0.1)
        assert not release_task.done(), "release must wait for the active lot-status transaction"

        await hold_db.commit()
        released = await asyncio.wait_for(release_task, timeout=5)
        assert released.hold_flag is False
        assert released.quarantine_flag is False
        assert released.release_status == ReleaseStatus.RELEASED

    async with AsyncSessionLocal() as verify_db:
        await _assert_task_database(verify_db)
        statuses = list((await verify_db.execute(
            select(LotQualityStatus).where(LotQualityStatus.lot_id == lot_id)
        )).scalars())
        assert len(statuses) == 1
        assert statuses[0].hold_flag is False
        assert statuses[0].release_status == ReleaseStatus.RELEASED
        assert statuses[0].fefo_eligible is True
        assert statuses[0].shipment_eligible is True


@pytest.mark.asyncio
async def test_rolling_back_hold_keeps_the_uncommitted_status_row_out_of_the_database():
    async with AsyncSessionLocal() as setup:
        await _assert_task_database(setup)
        lot = await _create_synthetic_lot(setup)
        lot_id = lot.id
        await setup.commit()

    async with AsyncSessionLocal() as hold_db:
        await _assert_task_database(hold_db)
        held = await hold_lot(hold_db, lot_id, "Synthetic rollback test hold")
        assert held.hold_flag is True
        await hold_db.rollback()

    async with AsyncSessionLocal() as verify_db:
        await _assert_task_database(verify_db)
        status = await verify_db.scalar(
            select(LotQualityStatus).where(LotQualityStatus.lot_id == lot_id)
        )
        assert status is None
