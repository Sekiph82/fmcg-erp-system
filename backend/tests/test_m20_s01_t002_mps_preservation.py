"""Bounded M20.S01.T002 preservation contracts for existing MPS surfaces."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.v1.endpoints import mps as mps_api
from app.models.mps import MPSCapacityMode, MPSFeasibilityStatus, MPSStatus, MPSChangeType
from app.services import mps_capacity_service as capacity_svc
from app.services import mps_campaign_service as campaign_svc
from app.services import mps_service
from app.services import mps_whatif_service as whatif_svc


def _result(*, one=None, many=None, scalar=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalar.return_value = scalar
    if many is not None:
        result.scalars.return_value.all.return_value = many
    return result


def _line(*, mps_id, product_id=None, locked=False, work_center_id=None, qty="100"):
    return SimpleNamespace(
        id=uuid4(), mps_id=mps_id, product_id=product_id or uuid4(),
        is_locked=locked, work_center_id=work_center_id,
        planned_production_qty=Decimal(qty), required_hours=None,
        planned_start_date=None, planned_end_date=None,
        period_start=date(2026, 1, 5), period_end=date(2026, 1, 6),
        priority_score=Decimal("50"), feasibility_status=MPSFeasibilityStatus.PENDING,
        overload_hours=None, campaign_id=None, remarks=None,
    )


@pytest.mark.asyncio
async def test_update_line_cannot_cross_plan_boundary():
    requested_plan_id = uuid4()
    actual_plan_id = uuid4()
    line = _line(mps_id=actual_plan_id)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(one=None))

    result = await mps_service.update_mps_line(
        db, requested_plan_id, line.id,
        SimpleNamespace(model_dump=lambda exclude_unset: {"remarks": "tamper"}),
    )

    assert result is None
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_infinite_capacity_marks_only_unlocked_lines_feasible():
    plan = SimpleNamespace(id=uuid4(), status=MPSStatus.DRAFT, capacity_mode=MPSCapacityMode.INFINITE)
    unlocked = _line(mps_id=plan.id, locked=False)
    locked = _line(mps_id=plan.id, locked=True)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result(one=plan),
        _result(many=[unlocked, locked]),
        _result(many=[]),
    ])

    result = await capacity_svc.run_capacity_scheduling(db, plan.id)

    assert result == {"mode": "INFINITE", "lines_processed": 2}
    assert unlocked.feasibility_status == MPSFeasibilityStatus.FEASIBLE
    assert locked.feasibility_status == MPSFeasibilityStatus.PENDING
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_capacity_missing_plan_fails_without_mutating_lines():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(one=None))

    with pytest.raises(ValueError, match="MPS plan not found"):
        await capacity_svc.run_capacity_scheduling(db, uuid4())

    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_campaign_grouping_empty_plan_is_idempotent():
    plan = SimpleNamespace(
        id=uuid4(), status=MPSStatus.DRAFT,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_result(one=plan), _result(many=[]), _result(many=[])])

    assert await campaign_svc.run_campaign_grouping(db, plan.id) == {
        "campaigns_created": 0,
        "lines_grouped": 0,
        "ungrouped_lines": 0,
        "locked_lines_preserved": 0,
        "changeover_state": "NOT_CONFIGURED",
    }


@pytest.mark.asyncio
async def test_whatif_rejects_line_from_another_plan():
    plan_id = uuid4()
    foreign_line = _line(mps_id=uuid4())
    data = SimpleNamespace(
        changes=[SimpleNamespace(line_id=foreign_line.id, change_type=MPSChangeType.DELAY, new_value=2)],
        scenario_name="foreign-line",
        description=None,
    )
    db = AsyncMock()
    db.get_bind = MagicMock(return_value=SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
    db.execute = AsyncMock(side_effect=[
        _result(one=SimpleNamespace(id=plan_id)),
        _result(scalar=0),
        _result(many=[]),
    ])

    with pytest.raises(ValueError, match="target lines in this MPS plan"):
        await whatif_svc.create_whatif_scenario(db, plan_id, data, uuid4())

    db.add.assert_not_called()


def test_mps_surface_routes_and_frontend_api_remain_aligned():
    route_paths = {route.path for route in mps_api.router.routes}
    required = {
        "/plans/{mps_id}/run-capacity",
        "/plans/{mps_id}/run-campaigns",
        "/plans/{mps_id}/capacity-heatmap",
        "/plans/{mps_id}/campaigns",
        "/plans/{mps_id}/whatif",
        "/whatif/{scenario_id}",
    }
    assert required <= route_paths

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "mps.ts"
    frontend_source = frontend.read_text(encoding="utf-8")
    assert "`${BASE}/plans/${mpsId}/capacity-heatmap`" in frontend_source
    assert "`${BASE}/plans/${mpsId}/campaigns`" in frontend_source
    assert "`${BASE}/plans/${mpsId}/whatif`" in frontend_source
