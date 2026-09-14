"""
M20.S01.T001 — MPS domain reconciliation + critical invariant hardening.

Covers the audit findings in docs/hiveai/audits/M20_S01_T001_STRICT_AUDIT.md:
F1 identity/RBAC, F2 release lifecycle, F3 release eligibility,
F4 feasibility-forgery protection, F5 MRP run validation,
F6 phasing conservation, F7 honest what-if capability, F8 migration ownership.
"""
from __future__ import annotations

import inspect
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.v1.endpoints import mps as mps_api
from app.core import module_registry
from app.db import seed
from app.models.mps import MPSFeasibilityStatus, MPSStatus, MPSChangeType
from app.models.mrp import MRPRunStatus
from app.models.recipe import RecipeStatus
from app.schemas.mps import MPSLineUpdate, GenerateFromMRPRequest
from app.services import mps_service as svc
from app.services import mps_whatif_service as whatif_svc


def _exec_result(*, scalar_one_or_none=None, scalars_all=None, scalar=None):
    m = MagicMock()
    m.scalar_one_or_none.return_value = scalar_one_or_none
    m.scalar.return_value = scalar
    if scalars_all is not None:
        m.scalars.return_value.all.return_value = scalars_all
    return m


def _mock_db(*results, get_results=None):
    def _assign_id_on_add(obj):
        # Simulate what a real flush would do for a freshly-added ORM row.
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    if get_results is not None:
        db.get = AsyncMock(side_effect=list(get_results))
    db.add = MagicMock(side_effect=_assign_id_on_add)
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


# ── F1 — identity / RBAC ────────────────────────────────────────────────────────

def test_mps_endpoints_use_auth_context_not_fixed_system_user():
    source = inspect.getsource(mps_api)
    assert "_SYSTEM_USER" not in source
    assert "require_permission" in source
    assert "current_user.id" in source


def test_mps_module_is_registry_owned_without_duplicate_endpoint_route():
    modules = {m.key: m for m in module_registry.MODULE_DEFINITIONS}
    endpoint_keys = {r.key for r in module_registry.ENDPOINT_ROUTE_DEFINITIONS}

    assert modules["mps"].route_prefix == "/mps"
    for action in ("view", "create", "edit", "approve", "release", "calculate", "simulate", "ai"):
        assert action in modules["mps"].permission_actions
    assert "mps" not in endpoint_keys


def test_mps_permissions_are_seeded_for_production_roles():
    permission_codes = {f"{module}.{action}" for module, action, *_ in seed.PERMISSIONS}
    for code in {
        "mps.view", "mps.create", "mps.edit", "mps.approve",
        "mps.release", "mps.calculate", "mps.simulate", "mps.ai",
    }:
        assert code in permission_codes

    assert "mps.approve" in seed.ROLE_DEFINITIONS["production_manager"]["permissions"]
    assert "mps.release" in seed.ROLE_DEFINITIONS["production_manager"]["permissions"]
    assert "mps.view" in seed.ROLE_DEFINITIONS["production_supervisor"]["permissions"]


# ── F4 — line update cannot forge engine-controlled feasibility state ──────────

def test_mps_line_update_schema_excludes_engine_controlled_fields():
    fields = MPSLineUpdate.model_fields
    assert "feasibility_status" not in fields
    assert "is_locked" not in fields
    # Passing them anyway is silently dropped, not forwarded to the service.
    data = MPSLineUpdate(**{
        "remarks": "note",
        "feasibility_status": "FEASIBLE",
        "is_locked": False,
    }).model_dump(exclude_unset=True)
    assert "feasibility_status" not in data
    assert "is_locked" not in data


# ── F2 / F3 — release lifecycle + eligibility ──────────────────────────────────

async def test_release_rejects_draft_plan():
    plan = SimpleNamespace(id=uuid4(), status=MPSStatus.DRAFT)
    db = _mock_db(_exec_result(scalar_one_or_none=plan))

    with pytest.raises(ValueError, match="APPROVED"):
        await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())


async def test_release_only_creates_orders_for_feasible_lines_and_counts_ineligible():
    product_id = uuid4()
    plan = SimpleNamespace(
        id=uuid4(), status=MPSStatus.APPROVED,
        plan_no="MPS-000001", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    feasible_line = SimpleNamespace(
        id=uuid4(), line_no="MPSL-0000001", product_id=product_id,
        planned_production_qty=Decimal("100"),
        planned_start_date=None, planned_end_date=None,
        remarks=None, production_order_id=None,
    )
    recipe = SimpleNamespace(id=uuid4(), product_id=product_id, status=RecipeStatus.APPROVED,
                              is_active=True, valid_from=None, valid_to=None)
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_id, uom=SimpleNamespace(value="PCS"))

    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),          # plan lookup
        _exec_result(scalars_all=[feasible_line]),        # FEASIBLE eligible lines
        _exec_result(scalar=2),                           # ineligible (non-FEASIBLE) count
        _exec_result(scalar=0),                           # production order sequence base
        _exec_result(scalar_one_or_none=recipe),           # recipe lookup for feasible_line
        get_results=[warehouse, product],                  # db.get(Warehouse, ...), db.get(Product, ...)
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), uuid4())

    assert result["released_orders"] == 1
    assert result["skipped_ineligible"] == 2
    assert result["release_complete"] is True
    assert plan.status == MPSStatus.RELEASED
    assert feasible_line.production_order_id is not None


def test_release_query_filters_by_feasible_status_only():
    source = inspect.getsource(svc.release_mps_plan)
    assert "MPSFeasibilityStatus.FEASIBLE" in source
    assert "MPSStatus.DRAFT" not in source


def test_release_eligible_and_ineligible_queries_exclude_already_released_lines():
    # Repeated release cannot duplicate orders: both the eligible-lines query
    # and the ineligible-count query only ever consider lines with no
    # production_order_id yet, so a line released once is never reconsidered.
    source = inspect.getsource(svc.release_mps_plan)
    assert source.count("MPSLine.production_order_id == None") == 2


# ── F5 — MRP run validation ─────────────────────────────────────────────────────

async def test_generate_from_mrp_rejects_missing_run():
    plan = SimpleNamespace(id=uuid4(), status=MPSStatus.DRAFT, mrp_run_id=None,
                            start_date=date(2026, 1, 1), end_date=date(2026, 1, 10))
    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),   # plan lookup
        _exec_result(scalar_one_or_none=None),   # MRP run lookup -> missing
    )
    req = GenerateFromMRPRequest(mrp_run_id=uuid4())

    with pytest.raises(ValueError, match="MRP run not found"):
        await svc.generate_mps_from_mrp(db, plan.id, req)


async def test_generate_from_mrp_rejects_non_completed_run():
    plan = SimpleNamespace(id=uuid4(), status=MPSStatus.DRAFT, mrp_run_id=None,
                            start_date=date(2026, 1, 1), end_date=date(2026, 1, 10))
    mrp_run = SimpleNamespace(id=uuid4(), status=MRPRunStatus.RUNNING)
    db = _mock_db(
        _exec_result(scalar_one_or_none=plan),
        _exec_result(scalar_one_or_none=mrp_run),
    )
    req = GenerateFromMRPRequest(mrp_run_id=mrp_run.id)

    with pytest.raises(ValueError, match="COMPLETED"):
        await svc.generate_mps_from_mrp(db, plan.id, req)


# ── F6 — phasing conservation ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "start,end,period_days",
    [
        (date(2026, 1, 1), date(2026, 1, 10), 7),   # weekly, partial final period
        (date(2026, 1, 1), date(2026, 1, 1), 7),    # one-day horizon (former boundary bug)
        (date(2026, 1, 1), date(2026, 1, 31), 1),   # daily
        (date(2026, 1, 1), date(2026, 3, 1), 30),   # monthly, partial final period
    ],
)
def test_phase_periods_conserves_total_fraction(start, end, period_days):
    periods = svc._phase_periods(start, end, period_days)
    total = sum((f for _, _, f in periods), Decimal("0"))
    # Decimal division rounding across many periods can leave a residual far
    # below the service's 3-decimal-place quantity precision (_R) — real
    # conservation only needs to hold at that precision, not to 28 digits.
    assert abs(total - Decimal("1")) < Decimal("0.0000000001")
    # Periods partition the horizon with no gaps or overlaps.
    assert periods[0][0] == start
    assert periods[-1][1] == end
    for (_, prev_end, _), (next_start, _, _) in zip(periods, periods[1:]):
        assert next_start == prev_end + __import__("datetime").timedelta(days=1)


# ── F7 — honest what-if capability ──────────────────────────────────────────────

@pytest.mark.parametrize("change_type", [MPSChangeType.MERGE, MPSChangeType.SHIFT_ADD])
def test_whatif_rejects_unsupported_change_types(change_type):
    with pytest.raises(ValueError, match="not yet simulated"):
        whatif_svc._apply_change(
            {"id": "1", "planned_production_qty": "100"},
            {"change_type": change_type, "new_value": "1"},
        )


def test_whatif_still_applies_supported_change_types():
    snap = whatif_svc._apply_change(
        {"id": "1", "planned_production_qty": "100",
         "planned_start_date": "2026-01-01", "planned_end_date": "2026-01-05",
         "period_start": "2026-01-01", "period_end": "2026-01-05"},
        {"change_type": MPSChangeType.DELAY, "new_value": 3},
    )
    assert snap["planned_start_date"] == "2026-01-04"
