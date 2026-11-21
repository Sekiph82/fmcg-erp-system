"""M40.S02.T001 baseline module permission through the real app on disposable PostgreSQL: routes that only asked
for a signed-in user now need a right in their module (read: any right; change: a non-view right); routes with
their own checks, self-service modules and route order are unchanged; every module still registers."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine

TASK_DB_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s02_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), is_superuser=False, is_active=True, full_name="T", email="t@povu.example",
                           access_scopes=[], company_id=None, branch_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def test_registry_registers_everything_and_guards_expected_routes():
    from fastapi import APIRouter
    from app.core.module_registry import register_endpoint_routes, register_module_routes
    r = APIRouter()
    diag = register_endpoint_routes(r, environment="development") + register_module_routes(r, environment="development")
    assert [d for d in diag if d["status"] != "registered" and d["status"] != "disabled"] == []


@pytest.mark.asyncio
async def test_guard_through_the_app():
    from app.core.deps import get_current_user
    from app.main import app

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

    who = {"u": None}
    app.dependency_overrides[get_current_user] = lambda: who["u"]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            async def call(user, method, path, **kw):
                who["u"] = user
                return (await c.request(method, "/api/v1" + path, **kw)).status_code

            operator = _user("shop_floor.view", "shop_floor.execute", "production.view")
            finance_view = _user("finance.view")
            finance = _user("finance.view", "finance.edit")
            fake = uuid4()
            # invoices: an operator can neither list them nor record a payment
            assert await call(operator, "GET", "/sales/invoices/") == 403
            assert await call(operator, "POST", f"/sales/invoices/{fake}/payments",
                              json={"amount": 10, "payment_date": "2026-11-21", "method": "cash"}) == 403
            assert await call(finance_view, "GET", "/sales/invoices/") == 200
            assert await call(finance_view, "POST", f"/sales/invoices/{fake}/payments",
                              json={"amount": 10, "payment_date": "2026-11-21", "method": "cash"}) == 403   # view only
            assert await call(finance, "POST", f"/sales/invoices/{fake}/payments",
                              json={"amount": 10, "payment_date": "2026-11-21", "method": "cash"}) == 404   # passes the guard
            # tax and HR modules
            assert await call(operator, "GET", "/tax/rates") in (403, 404)
            assert await call(operator, "GET", "/recruitment/requisitions") in (403, 404)
            # routes that already had their own permission keep it: procurement module right not enough for sales orders
            assert await call(_user("procurement.view"), "GET", "/sales/orders/") == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
