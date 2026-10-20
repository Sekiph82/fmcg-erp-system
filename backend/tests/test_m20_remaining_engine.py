from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest

from app.services.mps_engine import (
    PlanningInputError,
    allocate_period_quantity,
    capacity_result,
    explode_approved_bom,
    net_finished_goods_requirement,
    period_buckets,
    scenario_kpis,
)
from app.services.mps_whatif_service import _apply_change, _compute_impact
from app.models.mps import MPSChangeType


def test_weekly_buckets_are_gap_free_and_clip_partial_edges():
    buckets = period_buckets(date(2026, 1, 3), date(2026, 1, 14), "WEEKLY")
    assert buckets == [
        (date(2026, 1, 3), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 11)),
        (date(2026, 1, 12), date(2026, 1, 14)),
    ]
    assert buckets[0][0] == date(2026, 1, 3)
    assert buckets[-1][1] == date(2026, 1, 14)


def test_monthly_buckets_respect_leap_february():
    assert period_buckets(date(2028, 2, 27), date(2028, 3, 2), "MONTHLY") == [
        (date(2028, 2, 27), date(2028, 2, 29)),
        (date(2028, 3, 1), date(2028, 3, 2)),
    ]


def test_demand_allocation_conserves_quantity_over_partial_periods():
    buckets = period_buckets(date(2026, 1, 1), date(2026, 1, 10), "WEEKLY")
    allocated = allocate_period_quantity(Decimal("101.123"), date(2026, 1, 2), date(2026, 1, 9), buckets)
    assert sum(allocated) == Decimal("101.123")
    assert allocated == [Decimal("37.921"), Decimal("63.202")]


def test_demand_allocation_rejects_negative_and_invalid_periods():
    buckets = period_buckets(date(2026, 1, 1), date(2026, 1, 3), "DAILY")
    with pytest.raises(PlanningInputError):
        allocate_period_quantity(-1, date(2026, 1, 1), date(2026, 1, 2), buckets)
    with pytest.raises(PlanningInputError):
        period_buckets(date(2026, 2, 1), date(2026, 1, 1), "DAILY")


def test_confirmed_demand_nets_forecast_and_safety_stock_once():
    net = net_finished_goods_requirement(
        confirmed=70, forecast=100, safety_stock=20, on_hand=45,
        reserved=10, incoming=15, wip=5, other_planned=5,
    )
    assert net["net_forecast"] == Decimal("30.000")
    assert net["gross_demand"] == Decimal("120.000")
    assert net["total_supply"] == Decimal("60.000")
    assert net["net_requirement"] == Decimal("60.000")


def test_supply_components_are_not_double_counted_or_negative():
    net = net_finished_goods_requirement(
        confirmed=10, forecast=0, safety_stock=0, on_hand=4, reserved=7,
        incoming=3,
    )
    assert net["available_on_hand"] == Decimal("0.000")
    assert net["net_requirement"] == Decimal("7.000")
    with pytest.raises(PlanningInputError):
        net_finished_goods_requirement(confirmed=-1, forecast=0, safety_stock=0, on_hand=0, reserved=0)


def test_approved_bom_scales_batch_loss_and_optional_lines():
    rows = explode_approved_bom(
        output_qty=2500,
        output_uom="KG",
        bom={"base_qty": 1000, "base_uom": "KG", "output_uom": "KG", "lifecycle": "APPROVED"},
        lines=[
            {"item_id": "sugar", "item_type": "MATERIAL", "required_qty": 100, "required_uom": "KG", "basis_type": "PER_BATCH", "wastage_pct": 2, "process_loss_pct": 1},
            {"item_id": "optional", "item_type": "MATERIAL", "required_qty": 10, "required_uom": "KG", "basis_type": "PER_BATCH", "is_optional": True},
        ],
    )
    assert rows == [{
        "material_id": "sugar", "required_qty": Decimal("257.5000"),
        "uom": "KG", "basis_type": "PER_BATCH", "substitution_policy": "NO_SUB",
    }]


@pytest.mark.parametrize("bom,lines", [
    ({"base_qty": 0, "base_uom": "KG", "output_uom": "KG", "lifecycle": "APPROVED"}, []),
    ({"base_qty": 100, "base_uom": "L", "output_uom": "L", "lifecycle": "DRAFT"}, []),
    ({"base_qty": 100, "base_uom": "L", "output_uom": "L", "lifecycle": "APPROVED"}, [{"item_id": "x", "required_qty": 1, "required_uom": "KG", "basis_type": "PER_100KG"}]),
    ({"base_qty": 100, "base_uom": "KG", "output_uom": "KG", "lifecycle": "APPROVED"}, [{"item_id": "x", "required_qty": 1, "required_uom": "KG", "basis_type": "UNKNOWN"}]),
])
def test_bom_missing_or_incompatible_master_data_fails_closed(bom, lines):
    with pytest.raises(PlanningInputError):
        explode_approved_bom(output_qty=100, output_uom="KG", bom=bom, lines=lines)


def test_capacity_uses_explicit_calendar_and_downtime():
    assert capacity_result(9, 10, 2) == {
        "required_hours": Decimal("9.000"), "available_hours": Decimal("10.000"),
        "downtime_hours": Decimal("2.000"), "net_available_hours": Decimal("8.000"),
        "overload_hours": Decimal("1.000"), "status": "OVERLOADED",
    }
    assert capacity_result(8, 10, 2)["status"] == "FEASIBLE"
    assert capacity_result(8, 0, 0)["status"] == "OVERLOADED"
    with pytest.raises(PlanningInputError):
        capacity_result(-1, 8, 0)


def test_scenario_kpis_disclose_unknown_cost_and_units():
    result = scenario_kpis(
        lines=[{"late": False}, {"late": True}],
        material_shortages=1,
        capacity_overload_hours=Decimal("2.25"),
        changeover_hours=None,
    )
    assert result["service_level_pct"] == 50.0
    assert result["material_shortage_count"] == 1
    assert result["capacity_overload_unit"] == "hours"
    assert result["estimated_cost_delta"] is None
    assert result["cost_currency"] is None
    assert result["unknowns"] == ["cost basis or currency is not configured"]


def test_kenya_fmcg_acceptance_fixture_replays_supply_bom_and_capacity_edges():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "m20_acceptance_dataset.json").read_text(encoding="utf-8"))
    assert fixture["classification"].startswith("synthetic test fixture")
    mango = fixture["products"][0]
    net = net_finished_goods_requirement(
        confirmed=mango["confirmed_demand"], forecast=mango["forecast_demand"],
        safety_stock=mango["safety_stock"], on_hand=mango["on_hand"],
        reserved=mango["reserved"], incoming=mango["incoming_po"],
        wip=mango["wip"], other_planned=mango["other_approved_plan"],
    )
    assert net["net_requirement"] == Decimal("320.000")
    requirements = explode_approved_bom(
        output_qty=mango["planned_qty"], output_uom="PCS",
        bom={"base_qty": 1000, "base_uom": "PCS", "output_uom": "PCS", "lifecycle": "APPROVED"},
        lines=[{
            "item_id": "SUGAR-01", "item_type": "MATERIAL", "required_qty": 50,
            "required_uom": "KG", "basis_type": "PER_BATCH", "wastage_pct": 2,
            "process_loss_pct": 0,
        }],
    )
    assert requirements[0]["required_qty"] == Decimal("16.3200")
    assert Decimal(mango["material_stock"]["SUGAR-01"]["on_hand"]) - Decimal(mango["material_stock"]["SUGAR-01"]["reserved"]) < requirements[0]["required_qty"]
    assert Decimal(mango["planned_qty"]) / Decimal(mango["work_center"]["rate"]) == Decimal("4")
    assert mango["work_center"]["shifts"] == [{"start": "07:00", "end": "15:00"}]
    assert fixture["approval_release_contract"]["idempotent_retry"]
    assert capacity_result(4, 8, 1.5)["status"] == "FEASIBLE"
    overload = mango["overload_case"]
    assert capacity_result(overload["required_hours"], overload["calendar_hours"], overload["downtime_hours"])["overload_hours"] == Decimal(str(overload["expected_overload_hours"]))


def test_fixture_delayed_receipt_and_missing_master_data_remain_blocking():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "m20_acceptance_dataset.json").read_text(encoding="utf-8"))
    detergent = fixture["products"][1]
    net = net_finished_goods_requirement(
        confirmed=detergent["confirmed_demand"], forecast=detergent["forecast_demand"],
        safety_stock=detergent["safety_stock"], on_hand=detergent["on_hand"],
        reserved=detergent["reserved"], incoming=0,
    )
    assert net["net_requirement"] == Decimal("240.000")
    assert detergent["bom"]["lifecycle"] == "MISSING"
    assert detergent["work_center"]["calendar_hours"] is None
    assert detergent["cip"]["state"] == "NOT_CONFIGURED"
    assert date.fromisoformat(detergent["incoming_due_date"]) > date.fromisoformat(fixture["scope"]["horizon"][1])
    assert detergent["planned_qty"] == 240


def test_invariant_matrix_has_traceable_rows_for_all_required_contracts():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "m20_invariant_matrix.json").read_text(encoding="utf-8"))
    assert fixture["schema_version"] == "m20-invariant-matrix.v1"
    required = set(fixture["required_columns"])
    assert {"lifecycle", "owner_scope", "uom", "dates", "locks", "uniqueness",
            "nullability", "transaction", "permission", "current_enforcement",
            "counterexample", "severity", "recommended_fix"} <= required
    assert len(fixture["invariants"]) >= 10
    for row in fixture["invariants"]:
        assert row["source"] and row["entity"]
        assert required - {"entity"} <= row.keys()


def test_whatif_never_invents_currency_and_rejects_unimplemented_operations():
    original = [{"id": "line-1", "planned_end_date": "2026-01-05", "period_end": "2026-01-05", "planned_production_qty": "10"}]
    modified = {"line-1": {**original[0], "planned_end_date": "2026-01-06"}}
    assert _compute_impact(original, modified, {}) == (0.0, 1, None)
    with pytest.raises(ValueError, match="not yet simulated"):
        _apply_change({}, {"change_type": MPSChangeType.MERGE, "new_value": 1})
    with pytest.raises(ValueError, match="not yet simulated"):
        _apply_change({}, {"change_type": MPSChangeType.SHIFT_ADD, "new_value": 1})
    delayed = _apply_change({"period_start": "2026-01-01"}, {"change_type": MPSChangeType.DELAY, "new_value": 3})
    assert delayed["period_start"] == "2026-01-04"
    adjusted = _apply_change({"planned_production_qty": "10"}, {"change_type": MPSChangeType.QTY_ADJUST, "new_value": "12.5"})
    assert adjusted["planned_production_qty"] == "12.5"
    with pytest.raises(ValueError, match="whole number"):
        _apply_change({}, {"change_type": MPSChangeType.DELAY, "new_value": 1.5})
    with pytest.raises(ValueError, match="positive finite"):
        _apply_change({}, {"change_type": MPSChangeType.BATCH_SIZE, "new_value": "Infinity"})
