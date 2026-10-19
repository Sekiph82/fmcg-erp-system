"""Behavioral coverage for the frozen M20.S01.T001 V03 findings."""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import mps as mps_api
from app.models.mps import MPSFeasibilityStatus, MPSStatus
from app.models.recipe import RecipeStatus
from app.services import mps_service as svc


def _result(*, one=None, many=None, scalar=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalar.return_value = scalar
    if many is not None:
        result.scalars.return_value.all.return_value = many
    return result


def _plan():
    return SimpleNamespace(
        id=uuid4(),
        status=MPSStatus.APPROVED,
        plan_no="MPS- V03",
        start_date=__import__("datetime").date(2026, 1, 1),
        end_date=__import__("datetime").date(2026, 1, 31),
        released_at=None,
    )


def _line(product_id, line_no):
    return SimpleNamespace(
        id=uuid4(),
        line_no=line_no,
        product_id=product_id,
        planned_production_qty=100,
        planned_start_date=None,
        planned_end_date=None,
        remarks=None,
        production_order_id=None,
        feasibility_status=MPSFeasibilityStatus.FEASIBLE,
    )


def _recipe(product_id):
    return SimpleNamespace(
        id=uuid4(),
        product_id=product_id,
        status=RecipeStatus.APPROVED,
        is_active=True,
        valid_from=None,
        valid_to=None,
    )


def _db(results, get_results):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    db.get = AsyncMock(side_effect=get_results)
    db.flush = AsyncMock()

    def add(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    db.add = MagicMock(side_effect=add)
    return db


async def test_mixed_partial_release_remains_approved_and_reports_unresolved_lines():
    plan = _plan()
    product_a, product_b = uuid4(), uuid4()
    line_a, line_b = _line(product_a, "MPSL-1"), _line(product_b, "MPSL-2")
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    product = SimpleNamespace(id=product_a, uom=SimpleNamespace(value="KG"))
    db = _db(
        [
            _result(one=plan),
            _result(many=[line_a, line_b]),
            _result(scalar=0),
            _result(scalar=0),
            _result(one=_recipe(product_a)),
            _result(one=None),
        ],
        [warehouse, product],
    )

    result = await svc.release_mps_plan(db, plan.id, uuid4(), warehouse.id)

    assert result == {
        "released_orders": 1,
        "skipped_no_recipe": 1,
        "skipped_ineligible": 0,
        "unresolved_lines": 1,
        "release_required_lines": 2,
        "release_complete": False,
    }
    assert plan.status == MPSStatus.APPROVED
    assert plan.released_at is None


@pytest.mark.parametrize("product", [None, SimpleNamespace(uom=None), SimpleNamespace(uom="NOT_A_UOM")])
async def test_release_fails_closed_for_missing_or_invalid_authoritative_product_uom(product):
    plan = _plan()
    product_id = uuid4()
    line = _line(product_id, "MPSL-1")
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    db = _db(
        [
            _result(one=plan),
            _result(many=[line]),
            _result(scalar=0),
            _result(scalar=0),
            _result(one=_recipe(product_id)),
        ],
        [warehouse, product],
    )

    with pytest.raises(ValueError, match="(missing|valid authoritative UOM)"):
        await svc.release_mps_plan(db, plan.id, uuid4(), warehouse.id)

    db.add.assert_not_called()
    assert plan.status == MPSStatus.APPROVED


class _TransactionalReleaseDB:
    """Transaction-bound fake proving the endpoint owns rollback scope.

    This intentionally does not claim PostgreSQL persistence proof. It models
    the existing AsyncSession.begin contract and records whether an order
    would survive the outer transaction after a later-line integrity failure.
    """

    def __init__(self, results, get_results, plan, lines):
        self.execute = AsyncMock(side_effect=results)
        self.get = AsyncMock(side_effect=get_results)
        self.flush = AsyncMock()
        self.pending_orders = []
        self.committed_orders = []
        self.plan = plan
        self.lines = lines

        def add(obj):
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            self.pending_orders.append(obj)

        self.add = MagicMock(side_effect=add)

        @asynccontextmanager
        async def begin():
            try:
                yield self
            except BaseException:
                self.pending_orders.clear()
                for line in self.lines:
                    line.production_order_id = None
                self.plan.status = MPSStatus.APPROVED
                raise
            else:
                self.committed_orders.extend(self.pending_orders)

        self.begin = MagicMock(side_effect=begin)


async def test_release_endpoint_rolls_back_first_flushed_order_when_later_line_fails():
    plan = _plan()
    product_a, product_b = uuid4(), uuid4()
    line_a, line_b = _line(product_a, "MPSL-1"), _line(product_b, "MPSL-2")
    warehouse = SimpleNamespace(id=uuid4(), code="WH-1", is_active=True)
    valid_product = SimpleNamespace(id=product_a, uom=SimpleNamespace(value="KG"))
    db = _TransactionalReleaseDB(
        [
            _result(one=plan),
            _result(many=[line_a, line_b]),
            _result(scalar=0),
            _result(scalar=0),
            _result(one=_recipe(product_a)),
            _result(one=_recipe(product_b)),
        ],
        [warehouse, valid_product, None],
        plan,
        [line_a, line_b],
    )

    with pytest.raises(HTTPException) as exc_info:
        await mps_api.release_plan(
            plan.id,
            warehouse.id,
            db,
            SimpleNamespace(id=uuid4()),
        )

    assert exc_info.value.status_code == 400
    assert db.flush.await_count >= 1
    assert db.committed_orders == []
    assert db.pending_orders == []
    assert line_a.production_order_id is None
    assert plan.status == MPSStatus.APPROVED
