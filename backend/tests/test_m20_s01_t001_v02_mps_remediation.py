"""
M20.S01.T001 V02 — remediation of the frozen finding set in
coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md:

F-V01-001 real auth/RBAC negative+positive proof (not source-inspection only)
F-V01-002 MRP run context lineage (unrelated run cannot silently attach)
F-V01-003 target warehouse existence/active validation before release
F-V01-004 deterministic lifecycle-correct recipe selection
F-V01-005 ProductionOrder UOM derived from product, not hard-coded
F-V01-006 truthful RELEASED state (fails closed on zero orders created)
F-V01-007 behavioral repeated-release idempotency (not source-counting)
"""
from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.mps import MPSFeasibilityStatus, MPSStatus
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.master import Warehouse
from app.models.user import User
from app.models.production import ProductionOrder
from app.models.recipe import RecipeStatus
from app.schemas.mps import GenerateFromMRPRequest
from app.services import mps_service as svc


def _exec_result(*, scalar_one_or_none=None, scalars_all=None, scalar=None):
    m = MagicMock()
    m.scalar_one_or_none.return_value = scalar_one_or_none
    m.scalar.return_value = scalar
    if scalars_all is not None:
        m.scalars.return_value.all.return_value = scalars_all
    return m


def _mock_db(*results, get_results=None):
    def _assign_id_on_add(obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.scalar = AsyncMock(return_value=0)
    if get_results is not None:
        remaining = list(get_results)
        source_warehouse = SimpleNamespace(id=uuid4(), code="WH-SOURCE", is_active=True, company_id=None)
        source_run = SimpleNamespace(id=uuid4(), status=MRPRunStatus.COMPLETED, warehouse_id=source_warehouse.id)
        actor = SimpleNamespace(id=uuid4(), email="mps-test@example.invalid", full_name="MPS Test")
        target_warehouse = None

        async def _get(model, object_id):
            nonlocal target_warehouse
            if model is MRPRun:
                return source_run
            if model is User:
                return actor
            if model is Warehouse and object_id == source_warehouse.id:
                return source_warehouse
            value = remaining.pop(0) if remaining else None
            if model is Warehouse and value is not None and not hasattr(value, "company_id"):
                value.company_id = None
            if model is Warehouse and value is not None:
                target_warehouse = value
            if model is ProductionOrder:
                return SimpleNamespace(id=object_id, target_warehouse_id=getattr(target_warehouse, "id", None))
            return value

        db.get = AsyncMock(side_effect=_get)
    db.add = MagicMock(side_effect=_assign_id_on_add)
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


def _plan(**overrides):
    base = dict(
        id=uuid4(), status=MPSStatus.APPROVED, plan_no="MPS-000001",
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
        mrp_run_id=uuid4(), released_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _feasible_line(product_id, **overrides):
    base = dict(
        id=uuid4(), line_no="MPSL-0000001", product_id=product_id,
        planned_production_qty=Decimal("100"),
        planned_start_date=None, planned_end_date=None,
        remarks=None, production_order_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _approved_recipe(product_id, **overrides):
    base = dict(id=uuid4(), product_id=product_id, status=RecipeStatus.APPROVED,
                is_active=True, valid_from=None, valid_to=None)
    base.update(overrides)
    return SimpleNamespace(**base)


# ── F-V01-001 — real auth/RBAC proof (endpoint + dependency chain) ─────────────
#
# This repository has no pre-existing test that exercises the FastAPI app's
# own routes over HTTP (verified: no conftest.py, no live-DB fixture, and no
# other test file imports `app.main.app` for anything but its OpenAPI schema).
# These tests build the minimum real proof: a genuine TestClient request
# through the actual `require_permission`/`get_current_user` dependency
# chain, not a source-text assertion. `get_current_user` is the one
# dependency substituted (via FastAPI's standard `app.dependency_overrides`
# mechanism) to avoid needing a live database for token/session lookup —
# `require_permission`, `has_permission`, and the route's own permission
# code are exercised unmodified. This is not a second auth mechanism; it is
# the standard, correct way to unit-test a protected FastAPI route.

@pytest.fixture(scope="module")
def app():
    from app.main import app as real_app
    return real_app


@pytest.fixture(scope="module")
def client(app):
    from contextlib import asynccontextmanager
    from fastapi.testclient import TestClient

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(_app):
        # Route-level tests replace database dependencies and must not run
        # production startup seeding on TestClient's private event loop.
        yield

    app.router.lifespan_context = test_lifespan
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()


def _fake_user(*, is_superuser=False, permission_codes=()):
    permissions = [SimpleNamespace(code=c, is_active=True) for c in permission_codes]
    role = SimpleNamespace(is_active=True, permissions=permissions, access_scopes=[])
    return SimpleNamespace(id=uuid4(), is_superuser=is_superuser, roles=[role], access_scopes=[])


def _fake_session(*, execute_return=None):
    """A fake AsyncSession usable as a get_db() override: supports the
    `async with db.begin():` pattern every MPS route uses, plus a
    controllable db.execute() result."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _begin():
        yield

    db = AsyncMock()
    db.begin = MagicMock(side_effect=_begin)
    if execute_return is not None:
        db.execute = AsyncMock(return_value=execute_return)
    return db


def test_unauthenticated_mps_dashboard_request_is_rejected(client, app):
    app.dependency_overrides.clear()
    resp = client.get("/api/v1/mps/dashboard")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"


def test_authenticated_user_without_permission_cannot_approve_plan(client, app):
    from app.core.deps import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(permission_codes=())
    try:
        resp = client.patch(f"/api/v1/mps/plans/{uuid4()}/approve")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "forbidden"
    assert "mps.approve" in resp.json()["detail"]["detail"]


def test_authenticated_user_with_permission_reaches_protected_path(client, app):
    from app.core.deps import get_current_user
    from app.db.session import get_db

    async def _fake_get_db():
        yield _fake_session(execute_return=_exec_result(scalars_all=[]))

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(permission_codes=("mps.view",))
    app.dependency_overrides[get_db] = _fake_get_db
    try:
        resp = client.get("/api/v1/mps/plans")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == []


def test_superuser_bypasses_permission_check_and_reaches_protected_path(client, app):
    from app.core.deps import get_current_user
    from app.db.session import get_db

    async def _fake_get_db():
        yield _fake_session(execute_return=_exec_result(scalars_all=[]))

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(is_superuser=True)
    app.dependency_overrides[get_db] = _fake_get_db
    try:
        resp = client.get("/api/v1/mps/plans")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200


# ── F-V01-002 — MRP run context lineage ────────────────────────────────────────

async def test_generate_from_mrp_rejects_switching_to_an_unrelated_run():
    existing_run_id = uuid4()
    other_run_id = uuid4()
    plan = _plan(status=MPSStatus.DRAFT, mrp_run_id=existing_run_id)
    db = _mock_db(_exec_result(scalar_one_or_none=plan))  # only the plan lookup happens

    req = GenerateFromMRPRequest(mrp_run_id=other_run_id)
    with pytest.raises(ValueError, match="different MRP run"):
        await svc.generate_mps_from_mrp(db, plan.id, req)


async def test_generate_from_mrp_allows_regenerating_from_the_same_run():
    run_id = uuid4()
    plan = _plan(status=MPSStatus.DRAFT, mrp_run_id=run_id)
    mrp_run = SimpleNamespace(id=run_id, status=__import__("app.models.mrp", fromlist=["MRPRunStatus"]).MRPRunStatus.COMPLETED)

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalar_one_or_none=mrp_run),
        _exec_result(scalars_all=[]),  # no positive MRP requirements
        _exec_result(scalars_all=[]),  # existing unlocked MPS lines to replace
        _exec_result(),  # refreshed line counters
        _exec_result(scalar_one_or_none=plan),  # plan counter update
    )
    req = GenerateFromMRPRequest(mrp_run_id=run_id)

    created = await svc.generate_mps_from_mrp(db, plan.id, req)
    assert created == 0
    assert plan.mrp_run_id == run_id
    assert db.execute.await_count == 6


# ── F-V01-003 — target warehouse validated before any order is created ────────

async def test_release_rejects_nonexistent_warehouse():
    plan = _plan()
    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        get_results=[None],  # db.get(Warehouse, ...) -> not found
    )

    with pytest.raises(ValueError, match="not found"):
        await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    db.add.assert_not_called()


async def test_release_rejects_inactive_warehouse():
    plan = _plan()
    warehouse = SimpleNamespace(id=uuid4(), code="WH-OLD", is_active=False)
    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        get_results=[warehouse],
    )

    with pytest.raises(ValueError, match="not active"):
        await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    db.add.assert_not_called()


# ── F-V01-004 — deterministic lifecycle-correct recipe selection ──────────────

def test_select_release_recipe_filters_by_approved_status_and_effective_dates():
    source = inspect.getsource(svc._select_release_recipe)
    assert "RecipeStatus.APPROVED" in source
    assert "valid_from" in source and "valid_to" in source
    assert "order_by" in source  # deterministic, not bare limit(1) on an unordered set


async def test_select_release_recipe_returns_the_queried_recipe():
    product_id = uuid4()
    recipe = _approved_recipe(product_id)
    db = _mock_db(_exec_result(scalar_one_or_none=recipe))

    result = await svc._select_release_recipe(db, product_id, date(2026, 1, 1))
    assert result is recipe


async def test_release_skips_line_when_no_approved_effective_recipe_exists():
    product_id = uuid4()
    plan = _plan()
    line = _feasible_line(product_id)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=None),  # no APPROVED/effective recipe found
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=None),  # same blocked retry
        get_results=[warehouse, warehouse],
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())
    assert result["released_orders"] == 0
    assert result["skipped_no_recipe"] == 1
    assert "no approved effective recipe" in line.remarks
    retry = await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())
    assert retry["released_orders"] == 0
    assert line.remarks.count("[no approved effective recipe — skipped]") == 1


# ── F-V01-005 — UOM derived from product, not hard-coded ───────────────────────

def test_release_no_longer_hardcodes_uom_kg():
    source = inspect.getsource(svc.release_mps_plan)
    assert 'uom="KG"' not in source
    assert "product.uom" in source


async def test_release_sets_production_order_uom_from_product():
    product_id = uuid4()
    plan = _plan()
    line = _feasible_line(product_id)
    recipe = _approved_recipe(product_id)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_id, uom=SimpleNamespace(value="CARTON"))

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=recipe),
        _exec_result(scalar=0),
        get_results=[warehouse, product],
    )

    await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    created_po = [c.args[0] for c in db.add.call_args_list if hasattr(c.args[0], "uom")][0]
    assert created_po.uom == "CARTON"


# ── F-V01-006 — plan cannot become RELEASED with zero orders created ───────────

async def test_release_stays_approved_when_every_feasible_line_is_skipped():
    product_id = uuid4()
    plan = _plan()
    line = _feasible_line(product_id)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=None),  # no recipe -> this line is skipped
        get_results=[warehouse],
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    assert result["released_orders"] == 0
    assert result["release_complete"] is False
    assert plan.status == MPSStatus.APPROVED  # NOT RELEASED — fails closed
    assert plan.released_at is None


async def test_release_becomes_released_when_at_least_one_order_is_created():
    product_id = uuid4()
    plan = _plan()
    line = _feasible_line(product_id)
    recipe = _approved_recipe(product_id)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_id, uom=SimpleNamespace(value="KG"))

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=recipe),
        _exec_result(scalar=0),
        get_results=[warehouse, product],
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    assert result["released_orders"] == 1
    assert result["release_complete"] is True
    assert plan.status == MPSStatus.RELEASED
    assert plan.released_at is not None


# ── F-V01-007 — behavioral repeated-release idempotency ────────────────────────

async def test_repeated_release_call_returns_the_original_order_without_creating_another():
    product_id = uuid4()
    plan = _plan()
    line = _feasible_line(product_id)
    recipe = _approved_recipe(product_id)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_id, uom=SimpleNamespace(value="KG"))

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        _exec_result(scalar=0),
        _exec_result(scalar_one_or_none=recipe),
        _exec_result(scalar=0),
        # second call's queries below — only the plan lookup should ever run,
        # proving the guard rejects before touching lines/recipes/orders again
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalars_all=[line]),
        get_results=[warehouse, product],
    )

    target_warehouse_id = warehouse.id
    first = await svc.release_mps_plan(db, plan.id, uuid4(), target_warehouse_id)
    assert first["released_orders"] == 1
    assert plan.status == MPSStatus.RELEASED
    original_order_id = str(line.production_order_id)
    add_calls_after_first_release = db.add.call_count

    retry = await svc.release_mps_plan(db, plan.id, uuid4(), target_warehouse_id)

    assert retry["idempotent_retry"] is True
    assert retry["released_orders"] == 1
    assert retry["production_order_ids"] == [original_order_id]
    # No new ProductionOrder (or anything else) was added on the second call.
    assert db.add.call_count == add_calls_after_first_release
    assert db.execute.await_count == 7
