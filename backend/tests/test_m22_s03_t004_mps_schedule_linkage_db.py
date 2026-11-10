"""M22.S03.T004 PostgreSQL integration coverage for MPS-to-order linkage."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.master import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.mps import MPSFeasibilityStatus, MPSLine, MPSPlan, MPSStatus
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.production import ProductionOrder
from app.models.recipe import Recipe, RecipeStatus
from app.models.user import User
from app.services.mps_service import release_mps_plan


pytestmark = pytest.mark.skipif(
    os.environ.get("M22_S03_T004_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m22_s03_t004_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get("M22_S03_T004_DISPOSABLE_TEST_DATABASE_NAME")
    if (
        os.environ.get("M22_S03_T004_DISPOSABLE_TEST_DATABASE") != "1"
        or not _is_task_database(engine.url, expected)
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback M22.S03.T004 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m22_s03_t004_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m22_s03_t004_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m22_s03_t004_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name),
        name,
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="not-used", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


async def _seed_mps_release(db, suffix: str, *, source_active: bool = True):
    source = Warehouse(
        code=f"M22-S03-T004-S-{suffix}",
        name=f"Synthetic MRP source {suffix}",
        warehouse_type=WarehouseType.RAW_MATERIAL,
        is_active=True,
    )
    target = Warehouse(
        code=f"M22-S03-T004-T-{suffix}",
        name=f"Synthetic production target {suffix}",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    product = Product(
        sku=f"M22-S03-T004-P-{suffix}",
        name=f"Synthetic MPS product {suffix}",
        category=ProductCategory.FOOD,
        uom=UnitOfMeasure.KG,
    )
    actor = User(
        email=f"m22-s03-t004-{suffix}@example.invalid",
        username=f"m22s03t004{suffix}",
        full_name=f"Synthetic MPS releaser {suffix}",
        hashed_password="test-only",
    )
    db.add_all([source, target, product, actor])
    await db.flush()

    source_run = MRPRun(
        run_no=f"M22-S03-T004-R-{suffix}",
        run_date=date(2026, 11, 1),
        status=MRPRunStatus.COMPLETED,
        warehouse_id=source.id,
    )
    recipe = Recipe(
        product_id=product.id,
        version="1",
        name=f"Synthetic MPS recipe {suffix}",
        status=RecipeStatus.APPROVED,
        is_active=True,
    )
    db.add_all([source_run, recipe])
    await db.flush()

    plan = MPSPlan(
        plan_no=f"M22-S03-T004-MPS-{suffix}",
        plan_name=f"Synthetic schedule {suffix}",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        status=MPSStatus.APPROVED,
        mrp_run_id=source_run.id,
    )
    db.add(plan)
    await db.flush()

    line = MPSLine(
        line_no=f"M22-S03-T004-L-{suffix}",
        mps_id=plan.id,
        product_id=product.id,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
        planned_start_date=date(2026, 11, 10),
        planned_end_date=date(2026, 11, 12),
        planned_production_qty=Decimal("25"),
        feasibility_status=MPSFeasibilityStatus.FEASIBLE,
    )
    db.add(line)
    await db.flush()
    if not source_active:
        # A completed MRP run must have used an active warehouse. Deactivate it
        # only after the planning snapshot exists, then verify MPS release fails closed.
        source.is_active = False
        await db.flush()
    return plan, line, source, target, actor


@pytest.mark.asyncio
async def test_mps_release_links_source_warehouse_and_line_schedule_to_order():
    _require_task_database()
    from uuid import uuid4

    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        async with db.begin():
            plan, line, source, target, actor = await _seed_mps_release(db, suffix)
            result = await release_mps_plan(db, plan.id, actor.id, target.id)

            assert result["release_complete"] is True
            assert result["released_orders"] == 1
            assert line.production_order_id is not None

            order = await db.get(ProductionOrder, line.production_order_id)
            assert order is not None
            assert order.source_warehouse_id == source.id
            assert order.target_warehouse_id == target.id
            assert order.scheduled_start == datetime.combine(
                line.planned_start_date, time.min, tzinfo=timezone.utc
            )
            assert order.scheduled_end == datetime.combine(
                line.planned_end_date, time.min, tzinfo=timezone.utc
            )


@pytest.mark.asyncio
async def test_mps_release_rejects_inactive_source_warehouse_without_creating_order():
    _require_task_database()
    from uuid import uuid4

    suffix = uuid4().hex[:20]
    async with AsyncSessionLocal() as db:
        async with db.begin():
            plan, line, _, target, actor = await _seed_mps_release(
                db, suffix, source_active=False
            )
            with pytest.raises(ValueError, match="active source MRP warehouse"):
                await release_mps_plan(db, plan.id, actor.id, target.id)

            assert line.production_order_id is None
            assert plan.status == MPSStatus.APPROVED
