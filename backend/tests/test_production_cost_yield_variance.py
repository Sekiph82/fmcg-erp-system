from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.api.v1.endpoints import production_costing as costing_routes
from app.services.production_cost_service import (
    _yield_loss_variance_summary,
    get_cost_report,
)


def test_prices_yield_loss_variance_for_matching_uom():
    result = _yield_loss_variance_summary(
        [(Decimal("100"), Decimal("12"), Decimal("10"), "KG", Decimal("5"), "KG")]
    )

    assert result == {
        "yield_loss_cost_variance": 10.0,
        "yield_loss_standard_record_count": 1,
        "yield_loss_priced_record_count": 1,
        "yield_loss_unpriced_record_count": 0,
    }


def test_does_not_price_yield_loss_variance_across_different_uom():
    result = _yield_loss_variance_summary(
        [(Decimal("100"), Decimal("12"), Decimal("10"), "L", Decimal("5"), "KG")]
    )

    assert result["yield_loss_cost_variance"] is None
    assert result["yield_loss_standard_record_count"] == 1
    assert result["yield_loss_priced_record_count"] == 0
    assert result["yield_loss_unpriced_record_count"] == 1


def test_withholds_aggregate_when_any_standard_record_is_unpriced():
    result = _yield_loss_variance_summary(
        [
            (Decimal("100"), Decimal("12"), Decimal("10"), "KG", Decimal("5"), "KG"),
            (Decimal("50"), Decimal("8"), Decimal("5"), "KG", None, "KG"),
        ]
    )

    assert result["yield_loss_cost_variance"] is None
    assert result["yield_loss_standard_record_count"] == 2
    assert result["yield_loss_priced_record_count"] == 1
    assert result["yield_loss_unpriced_record_count"] == 1


def test_returns_null_exposure_when_no_standard_rows_exist():
    result = _yield_loss_variance_summary([])

    assert result == {
        "yield_loss_cost_variance": None,
        "yield_loss_standard_record_count": 0,
        "yield_loss_priced_record_count": 0,
        "yield_loss_unpriced_record_count": 0,
    }


def test_missing_recipe_standard_is_not_counted_as_a_standard_row():
    result = _yield_loss_variance_summary(
        [(Decimal("100"), Decimal("12"), None, "KG", Decimal("5"), "KG")]
    )

    assert result["yield_loss_cost_variance"] is None
    assert result["yield_loss_standard_record_count"] == 0
    assert result["yield_loss_priced_record_count"] == 0
    assert result["yield_loss_unpriced_record_count"] == 0


@pytest.mark.asyncio
async def test_product_cost_report_exposes_separate_yield_loss_amount():
    product_id = uuid.uuid4()
    report_row = SimpleNamespace(
        product_id=product_id,
        sku="TEST",
        product_name="Test product",
        product_standard_cost=Decimal("20"),
        order_count=1,
        total_qty=Decimal("100"),
        total_material_cost=Decimal("80"),
        total_labor_cost=Decimal("10"),
        total_machine_cost=Decimal("5"),
        total_energy_cost=Decimal("5"),
        total_cost=Decimal("100"),
        avg_cost_per_unit=Decimal("1"),
        avg_variance_pct=Decimal("0"),
    )
    yield_row = SimpleNamespace(
        product_id=product_id,
        expected_qty=Decimal("100"),
        loss_qty=Decimal("12"),
        standard_loss_pct=Decimal("10"),
        uom="KG",
        standard_cost=Decimal("5"),
        material_uom="KG",
    )

    class Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class Session:
        def __init__(self):
            self._results = [Result([report_row]), Result([yield_row])]

        async def execute(self, _statement):
            return self._results.pop(0)

    rows = await get_cost_report(Session())

    assert rows[0]["yield_loss_cost_variance"] == 10.0
    assert rows[0]["yield_loss_standard_record_count"] == 1
    assert rows[0]["total_cost"] == 100.0


@pytest.mark.asyncio
async def test_order_cost_route_returns_live_yield_loss_fields(monkeypatch):
    order_id = uuid.uuid4()
    order = SimpleNamespace(
        id=order_id,
        order_no="TEST-ORDER",
        product=SimpleNamespace(name="Test product", sku="TEST"),
        status=SimpleNamespace(value="IN_PROGRESS"),
        actual_quantity=Decimal("10"),
        uom="KG",
        costing_finalized_at=None,
    )
    monkeypatch.setattr(
        costing_routes, "_get_order_or_404", AsyncMock(return_value=order)
    )
    monkeypatch.setattr(
        costing_routes.svc,
        "compute_order_cost",
        AsyncMock(
            return_value={
                "total_material_cost": 0.0,
                "total_labor_cost": 0.0,
                "total_machine_cost": 0.0,
                "total_energy_cost": 0.0,
                "total_cost": 0.0,
                "cost_per_unit": 0.0,
                "standard_cost_per_unit": 0.0,
                "cost_variance_pct": None,
                "material_row_count": 0,
                "labor_row_count": 0,
                "yield_loss_cost_variance": 12.5,
                "yield_loss_standard_record_count": 2,
                "yield_loss_priced_record_count": 2,
                "yield_loss_unpriced_record_count": 0,
            }
        ),
    )

    result = await costing_routes.get_order_cost(order_id, AsyncMock(), None)

    assert result.yield_loss_cost_variance == 12.5
    assert result.yield_loss_standard_record_count == 2
    assert result.yield_loss_priced_record_count == 2
    assert result.yield_loss_unpriced_record_count == 0


@pytest.mark.asyncio
async def test_finalize_route_returns_live_yield_loss_fields(monkeypatch):
    order_id = uuid.uuid4()
    order = SimpleNamespace(
        id=order_id,
        order_no="TEST-ORDER",
        product=SimpleNamespace(name="Test product", sku="TEST"),
        status=SimpleNamespace(value="COMPLETED"),
        actual_quantity=Decimal("10"),
        uom="KG",
        total_material_cost=Decimal("0"),
        total_labor_cost=Decimal("0"),
        total_machine_cost=Decimal("0"),
        total_energy_cost=Decimal("0"),
        total_cost=Decimal("0"),
        cost_per_unit=Decimal("0"),
        standard_cost_per_unit=Decimal("0"),
        cost_variance_pct=Decimal("0"),
        costing_finalized_at=None,
    )
    monkeypatch.setattr(
        costing_routes, "_get_order_or_404", AsyncMock(return_value=order)
    )
    monkeypatch.setattr(
        costing_routes.svc, "finalize_order_cost", AsyncMock(return_value=order)
    )
    monkeypatch.setattr(
        costing_routes.svc,
        "compute_order_cost",
        AsyncMock(
            return_value={
                "yield_loss_cost_variance": -2.5,
                "yield_loss_standard_record_count": 1,
                "yield_loss_priced_record_count": 1,
                "yield_loss_unpriced_record_count": 0,
            }
        ),
    )
    db = AsyncMock()

    result = await costing_routes.finalize_order_cost(order_id, db, None)

    assert result.yield_loss_cost_variance == -2.5
    assert result.yield_loss_standard_record_count == 1
    assert result.yield_loss_priced_record_count == 1
    assert result.yield_loss_unpriced_record_count == 0
