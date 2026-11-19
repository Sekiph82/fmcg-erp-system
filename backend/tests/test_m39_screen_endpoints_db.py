"""M39.S01 regression: list/dashboard endpoints behind screens that returned 500 in the role sweep (wrong column names,
lazy loads in async, bad SQL casts, a missing schema field) answer without a server error on disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine

TASK_DB_ENV = "M39_S01_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M39_S01_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m39_s01_[a-f0-9]{24}")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

PATHS = [
    "/procurement/po/", "/procurement/delivery/schedule",
    "/production-adv/routings", "/production-adv/batch-lots", "/production-adv/qc", "/production-adv/waste",
    "/production-cost/wip", "/mrp/dashboard", "/market-intel/shelf-share/summary", "/marketing/analytics/summary",
    "/maintenance/reports/downtime-by-machine", "/utility-management/transactions/summary",
    "/analytics/inventory", "/analytics/sales", "/analytics/production", "/analytics/procurement", "/analytics/finance",
    "/utility-kpi/dashboard", "/utility-kpi/top-consumers", "/utility-kpi/trend", "/utility-kpi/electricity",
    "/utility-kpi/water", "/utility-kpi/boiler", "/utility-kpi/compressor", "/utility-kpi/soft-water", "/utility-kpi/solar",
    "/utility-kpi/chemicals", "/utility-kpi/wastewater", "/utility-kpi/machine-utility", "/pos/sales",
    "/calendar/events?start=2026-11-19T21:47:58.146Z&end=2026-11-26T21:47:58.146Z", "/notifications/me", "/notifications/me/unread-count",
]


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_screen_endpoints_do_not_fail():
    from app.main import app

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
    root = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", username="root", email="r@example.com", full_name="R",
                           is_superuser=True, is_active=True, access_scopes=[], roles=[])
    app.dependency_overrides[get_current_user] = lambda: root
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
            bad = {}
            for p in PATHS:
                r = await c.get(f"/api/v1{p}")
                if r.status_code >= 500 or r.status_code == 404:
                    bad[p] = r.status_code
            assert not bad, bad
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_my_work_lists_only_the_users_queues():
    """M39.S03.T002: 'My work today' shows only queues the user can act on, with counts and the screen to open."""
    import uuid
    from datetime import date

    from app.main import app
    from app.models.sales import Customer, CustomerChannel, SalesOrder, SOStatus

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        c = Customer(code=f"MW-{s}", name="Shop", channel=CustomerChannel.RETAIL, currency="KES")
        db.add(c)
        await db.flush()
        db.add(SalesOrder(order_no=f"MW-{s}", customer_id=c.id, order_date=date.today(), requested_delivery_date=date.today(),
                          currency="KES", status=SOStatus.DRAFT))
        await db.commit()

    def as_user(*codes):
        perms = [SimpleNamespace(code=x, module=x.split(".")[0], action=x.split(".")[1], is_active=True) for x in codes]
        return SimpleNamespace(id=uuid.uuid4(), username="u", email="u@example.com", full_name="U", is_superuser=False, is_active=True,
                               access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            app.dependency_overrides[get_current_user] = lambda: as_user("sales.view", "sales.edit")
            desk = {w["key"]: w for w in (await c.get("/api/v1/dashboard/my-work")).json()}
            assert desk["orders"]["count"] >= 1 and desk["orders"]["href"] == "/dashboard/sales?tab=orders"
            assert not {"payroll", "expenses", "picking"} & set(desk)            # nothing outside the desk's job
            app.dependency_overrides[get_current_user] = lambda: as_user("inventory.dispatch_all")
            assert "orders" not in {w["key"] for w in (await c.get("/api/v1/dashboard/my-work")).json()}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
