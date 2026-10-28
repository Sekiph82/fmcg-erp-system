from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.mps_engine import (
    PlanningInputError,
    allocate_period_quantity,
    allocate_weighted_quantity,
    capacity_result,
    explode_approved_bom,
    net_finished_goods_requirement,
    period_buckets,
    scenario_kpis,
)
from app.services.mps_capacity_service import (
    _calendar_shift_windows, _cross_calendar_shift_errors, _validated_calendar_hours,
)
from app.services.mps_whatif_service import _apply_change, _compute_impact, _expand_candidate_lines, _scenario_capacity_loads, _scenario_changeover_hours
from app.models.mps import MPSCapacityMode, MPSChangeType


def test_capacity_calendar_validates_shift_overlap_totals_and_overnight_windows():
    day = date(2026, 11, 7)
    overnight = SimpleNamespace(
        available_hours=Decimal("8"),
        shift_1_start="22:00", shift_1_end="06:00",
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    assert _validated_calendar_hours(overnight) == (Decimal("8"), None)
    start, end = _calendar_shift_windows(overnight, day)[0]
    assert start == datetime(2026, 11, 7, 22, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 8, 6, tzinfo=timezone.utc)

    overlap = SimpleNamespace(
        available_hours=Decimal("10"),
        shift_1_start="08:00", shift_1_end="14:00",
        shift_2_start="13:00", shift_2_end="17:00",
        shift_3_start=None, shift_3_end=None,
    )
    declared, error = _validated_calendar_hours(overlap)
    assert declared is None
    assert error == "shifts 1 and 2 overlap"

    work_center_id = uuid4()
    day_shift = SimpleNamespace(
        work_center_id=work_center_id, calendar_date=day, available_hours=Decimal("8"),
        is_holiday=False, is_maintenance=False,
        shift_1_start="22:00", shift_1_end="06:00",
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    next_day_shift = SimpleNamespace(
        work_center_id=work_center_id, calendar_date=day + timedelta(days=1),
        available_hours=Decimal("8"), is_holiday=False, is_maintenance=False,
        shift_1_start="02:00", shift_1_end="10:00",
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    overlap_errors = _cross_calendar_shift_errors([day_shift, next_day_shift])
    assert set(overlap_errors) == {
        (work_center_id, day), (work_center_id, day + timedelta(days=1)),
    }


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


def test_small_demand_allocations_conserve_quantity_without_negative_residuals():
    start = date(2026, 1, 1)
    daily = period_buckets(start, date(2026, 1, 6), "DAILY")
    by_period = allocate_period_quantity(Decimal("0.004"), start, date(2026, 1, 6), daily)
    by_forecast_day = allocate_weighted_quantity(Decimal("0.002"), [Decimal("0.001")] * 6)

    assert all(quantity >= 0 for quantity in by_period)
    assert sum(by_period) == Decimal("0.004")
    assert all(quantity >= 0 for quantity in by_forecast_day)
    assert sum(by_forecast_day) == Decimal("0.002")
    with pytest.raises(PlanningInputError, match="at least one allocation weight"):
        allocate_weighted_quantity(Decimal("0.001"), [])
    assert allocate_weighted_quantity(Decimal("0"), []) == []


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
        "substitute_group_id": None,
    }]


def test_approved_bom_grosses_up_input_for_configured_percent_of_input_yield_loss():
    rows = explode_approved_bom(
        output_qty=100,
        output_uom="KG",
        bom={
            "base_qty": 100, "base_uom": "KG", "lifecycle": "APPROVED",
            "yield_loss_pct": Decimal("10"),
        },
        lines=[{
            "item_id": "sugar", "item_type": "MATERIAL", "required_qty": 100,
            "required_uom": "KG", "basis_type": "PER_BATCH",
        }],
    )
    assert rows[0]["required_qty"] == Decimal("111.1111")


def test_approved_bom_rejects_unsupported_yield_basis_fail_closed():
    with pytest.raises(PlanningInputError, match="unsupported BOM yield-loss basis"):
        explode_approved_bom(
            output_qty=100,
            output_uom="KG",
            bom={
                "base_qty": 100, "base_uom": "KG", "lifecycle": "APPROVED",
                "yield_config_error": "unsupported BOM yield-loss basis: PCT_OF_OUTPUT",
            },
            lines=[{
                "item_id": "sugar", "item_type": "MATERIAL", "required_qty": 100,
                "required_uom": "KG", "basis_type": "PER_BATCH",
            }],
        )


def test_nested_approved_bom_explodes_to_leaf_material_with_each_level_loss():
    root_id, child_id = "root-bom", "intermediate-bom"
    rows = explode_approved_bom(
        output_qty=200, output_uom="KG",
        bom={"id": root_id, "base_qty": 100, "base_uom": "KG", "lifecycle": "APPROVED"},
        lines=[{
            "item_id": "intermediate", "item_type": "PRODUCT", "child_bom_id": child_id,
            "required_qty": 25, "required_uom": "KG", "basis_type": "PER_BATCH",
            "wastage_pct": 4, "process_loss_pct": 0,
        }],
        child_boms={child_id: {
            "bom": {"id": child_id, "base_qty": 10, "base_uom": "KG", "lifecycle": "RELEASED"},
            "lines": [{
                "item_id": "sugar", "item_type": "MATERIAL", "required_qty": 3,
                "required_uom": "KG", "basis_type": "PER_BATCH", "wastage_pct": 2,
            }],
        }},
        as_of=date(2026, 1, 1),
    )
    assert len(rows) == 1
    assert rows[0]["material_id"] == "sugar"
    assert rows[0]["required_qty"] == Decimal("15.9120")


@pytest.mark.parametrize("child_boms,as_of,match", [
    ({}, date(2026, 1, 1), "missing or unavailable"),
    ({"child": {"bom": {"id": "child", "base_qty": 10, "base_uom": "L", "lifecycle": "APPROVED"}, "lines": []}}, date(2026, 1, 1), "UOM"),
    ({"child": {"bom": {"id": "child", "base_qty": 10, "base_uom": "KG", "lifecycle": "DRAFT"}, "lines": []}}, date(2026, 1, 1), "approved/released"),
    ({"child": {"bom": {"id": "child", "base_qty": 10, "base_uom": "KG", "lifecycle": "APPROVED", "effective_from": date(2026, 2, 1)}, "lines": []}}, date(2026, 1, 1), "not effective"),
])
def test_nested_bom_fails_closed_for_missing_or_invalid_child(child_boms, as_of, match):
    with pytest.raises(PlanningInputError, match=match):
        explode_approved_bom(
            output_qty=20, output_uom="KG",
            bom={"id": "root", "base_qty": 10, "base_uom": "KG", "lifecycle": "APPROVED"},
            lines=[{"child_bom_id": "child", "item_type": "PRODUCT", "required_qty": 1,
                    "required_uom": "KG", "basis_type": "PER_BATCH"}],
            child_boms=child_boms, as_of=as_of,
        )


def test_nested_bom_cycle_is_rejected_with_path():
    with pytest.raises(PlanningInputError, match="cycle detected"):
        explode_approved_bom(
            output_qty=10, output_uom="KG",
            bom={"id": "root", "base_qty": 10, "base_uom": "KG", "lifecycle": "APPROVED"},
            lines=[{"child_bom_id": "child", "item_type": "PRODUCT", "required_qty": 10,
                    "required_uom": "KG", "basis_type": "PER_BATCH"}],
            child_boms={"child": {
                "bom": {"id": "child", "base_qty": 10, "base_uom": "KG", "lifecycle": "APPROVED"},
                "lines": [{"child_bom_id": "root", "item_type": "PRODUCT", "required_qty": 10,
                           "required_uom": "KG", "basis_type": "PER_BATCH"}],
            }, "root": {
                "bom": {"id": "root", "base_qty": 10, "base_uom": "KG", "lifecycle": "APPROVED"},
                "lines": [],
            }},
        )


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
    assert detergent["work_center"]["calendar_hours"] == 8
    assert detergent["campaign"]["family"] == "HOUSEHOLD"
    assert detergent["cip"]["state"] == "CONFIGURED"
    assert detergent["standard_cost_currency"] == fixture["scope"]["base_currency"]
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


def test_developer_portal_tables_are_registered_for_database_bootstrap():
    import app.models  # noqa: F401
    from app.db.base import Base

    assert "dev_api_keys" in Base.metadata.tables
    assert "dev_api_key_usage_logs" in Base.metadata.tables
    usage_log = Base.metadata.tables["dev_api_key_usage_logs"]
    assert any(fk.target_fullname == "dev_api_keys.key_id" and fk.ondelete == "CASCADE" for fk in usage_log.foreign_keys)


def test_mps_diagnostics_and_scenario_snapshot_tables_are_registered_for_database_bootstrap():
    import app.models  # noqa: F401
    from app.db.base import Base

    assert "mps_line_diagnostics" in Base.metadata.tables
    assert "mps_scenario_snapshots" in Base.metadata.tables
    diagnostics = Base.metadata.tables["mps_line_diagnostics"]
    snapshots = Base.metadata.tables["mps_scenario_snapshots"]
    assert any(fk.target_fullname == "mps_plans.id" and fk.ondelete == "CASCADE" for fk in diagnostics.foreign_keys)
    assert any(fk.target_fullname == "mps_lines.id" and fk.ondelete == "CASCADE" for fk in diagnostics.foreign_keys)
    assert any(fk.target_fullname == "mps_whatif_scenarios.id" and fk.ondelete == "CASCADE" for fk in snapshots.foreign_keys)
    assert str(diagnostics.c.diagnostics.type).upper() == "JSONB"
    assert str(snapshots.c.assumptions.type).upper() == "JSONB"


def test_whatif_preserves_unknown_currency_and_supports_exact_split_merge_and_shift_inputs():
    original = [{"id": "line-1", "planned_end_date": "2026-01-05", "period_end": "2026-01-05", "planned_production_qty": "10"}]
    modified = {"line-1": {**original[0], "planned_end_date": "2026-01-06"}}
    assert _compute_impact(original, modified, {}) == (0.0, 1, None)
    split = _apply_change(
        {"id": "line-1", "planned_production_qty": "10.000"},
        {"change_type": MPSChangeType.SPLIT, "new_value": {"quantities": ["3.125", "6.875"]}},
    )
    assert split["planned_production_qty"] == "10.000"
    assert split["_split_quantities"] == ["3.125", "6.875"]
    assert [line["planned_production_qty"] for line in _expand_candidate_lines([split])] == ["3.125", "6.875"]
    with pytest.raises(ValueError, match="sum exactly"):
        _apply_change(
            {"planned_production_qty": "10.000"},
            {"change_type": MPSChangeType.SPLIT, "new_value": ["4", "5"]},
        )
    merged = _apply_change(
        {"id": "line-1", "planned_production_qty": "10"},
        {"change_type": MPSChangeType.MERGE, "new_value": "line-2"},
    )
    assert merged["_merge_with_line_id"] == "line-2"
    shifted = _apply_change(
        {"id": "line-1", "planned_production_qty": "10"},
        {"change_type": MPSChangeType.SHIFT_ADD, "new_value": {
            "date": "2026-01-02", "start_time": "16:00", "end_time": "20:00", "hours": "4",
        }},
    )
    assert shifted["_added_shifts"] == [{
        "date": "2026-01-02", "start_time": "16:00", "end_time": "20:00", "hours": "4",
    }]
    delayed = _apply_change({"period_start": "2026-01-01"}, {"change_type": MPSChangeType.DELAY, "new_value": 3})
    assert delayed["period_start"] == "2026-01-04"
    adjusted = _apply_change({"planned_production_qty": "10"}, {"change_type": MPSChangeType.QTY_ADJUST, "new_value": "12.5"})
    assert adjusted["planned_production_qty"] == "12.5"
    with pytest.raises(ValueError, match="whole number"):
        _apply_change({}, {"change_type": MPSChangeType.DELAY, "new_value": 1.5})
    with pytest.raises(ValueError, match="positive finite"):
        _apply_change({}, {"change_type": MPSChangeType.BATCH_SIZE, "new_value": "Infinity"})


def test_whatif_capacity_simulation_uses_rate_calendar_and_downtime():
    wc_id, product_id = uuid4(), uuid4()
    work_center = SimpleNamespace(id=wc_id, capacity=80, capacity_uom="PCS/HR", status="active")
    product = SimpleNamespace(id=product_id, uom="PCS")
    day = date(2026, 11, 3)
    calendar = SimpleNamespace(work_center_id=wc_id, calendar_date=day, available_hours=8, is_holiday=False, is_maintenance=False)
    downtime = SimpleNamespace(
        work_center_id=wc_id,
        start_time=datetime(2026, 11, 3, 7, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 3, 8, 30, tzinfo=timezone.utc),
        duration_min=90,
    )
    line = {
        "product_id": str(product_id), "work_center_id": str(wc_id),
        "planned_production_qty": "600", "planned_start_date": day.isoformat(),
        "planned_end_date": day.isoformat(), "period_start": day.isoformat(), "period_end": day.isoformat(),
    }
    result = _scenario_capacity_loads(
        [line], {wc_id: work_center}, {product_id: product}, {(wc_id, day): calendar}, [downtime], MPSCapacityMode.FINITE,
    )
    assert result["status"] == "COMPLETE"
    assert result["overload_hours"] == 1.0
    gap = _scenario_capacity_loads([line], {wc_id: work_center}, {product_id: product}, {}, [], MPSCapacityMode.FINITE)
    assert gap["status"] == "PARTIAL_INPUTS"
    assert gap["overload_hours"] is None

    with_shift = _scenario_capacity_loads(
        [line], {wc_id: work_center}, {product_id: product}, {(wc_id, day): calendar}, [downtime],
        MPSCapacityMode.FINITE, {(wc_id, day): Decimal("2")},
    )
    assert with_shift["status"] == "COMPLETE"
    assert with_shift["overload_hours"] == 0.0


def test_whatif_changeover_uses_configured_transition_and_reports_missing_transition():
    wc_id = uuid4()
    product_a, product_b = uuid4(), uuid4()
    products = {
        product_a: SimpleNamespace(category="FOOD"),
        product_b: SimpleNamespace(category="BEVERAGE"),
    }
    lines = [
        {"id": "a", "work_center_id": str(wc_id), "product_id": str(product_a),
         "period_start": "2026-01-01", "period_end": "2026-01-01"},
        {"id": "b", "work_center_id": str(wc_id), "product_id": str(product_b),
         "period_start": "2026-01-02", "period_end": "2026-01-02"},
    ]
    configured = SimpleNamespace(
        work_center_id=wc_id, from_family="FOOD", to_family="BEVERAGE",
        changeover_minutes=30, cip_minutes=None, is_active=True,
    )
    result = _scenario_changeover_hours(lines, products, [configured])
    assert result["hours"] == 0.5
    assert result["status"] == "COMPLETE"
    assert result["transition_count"] == 1
    assert result["cip_status"] == "PARTIAL_INPUTS"
    assert result["cip_unknown_reasons"] == ["CIP_NOT_CONFIGURED:FOOD->BEVERAGE"]
    missing = _scenario_changeover_hours(lines, products, [])
    assert missing["status"] == "PARTIAL_INPUTS"
    assert missing["hours"] == 0.0
    assert "CHANGEOVER_NOT_CONFIGURED:FOOD->BEVERAGE" in missing["unknown_reasons"]
    assert "CIP_NOT_CONFIGURED:FOOD->BEVERAGE" in missing["unknown_reasons"]
