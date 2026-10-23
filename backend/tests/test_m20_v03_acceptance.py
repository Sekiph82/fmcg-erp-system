"""PostgreSQL integration coverage added from the M20 strict V03 audit."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import uuid
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMLifecycle, BOMSubstituteGroup, BOMYieldConfig,
    BasisType, ItemLinkType, LossCategory, SubstitutionPolicy,
)
from app.models.company import Branch, Company
from app.models.inventory import Stock, StockType
from app.models.master import (
    Material, MaterialType, Product, ProductCategory, Supplier, UnitOfMeasure,
    Warehouse, WarehouseType,
)
from app.models.mps import (
    MPSCapacityMode, MPSCapacitySlot, MPSChangeType, MPSFeasibilityStatus, MPSLine, MPSPlan, MPSScenarioSnapshot,
    MPSStatus, MPSWhatIfScenario,
)
from app.models.mrp import (
    DemandForecast, DemandForecastLine, ForecastModelType, ForecastStatus,
    MRPResult, MRPRun, MRPRunStatus, PeriodType,
)
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.procurement import PurchaseOrder, POLine, POStatus
from app.models.recipe import Recipe, RecipeStatus
from app.models.utilities import UomConversion
from app.models.planning import ResourceCalendar
from app.models.production_advanced import DowntimeEvent, WorkCenter, WorkCenterType
from app.models.role import AccessScope, Permission, Role
from app.models.user import User, user_role
from app.models.sales import Customer, SalesOrder, SOStatus, SOLine
from app.schemas.mps import (
    GenerateFromMRPRequest, MPSLineConstraintDiagnosticOut, MPSWhatIfCreate, WhatIfChange,
)
from app.services.mps_advanced_service import (
    evaluate_material_feasibility, list_plan_diagnostics, project_demand_and_supply,
)
from app.services.mps_capacity_service import run_capacity_scheduling_validated
from app.services.mps_service import _next_seq, approve_mps_plan, generate_mps_from_mrp, release_mps_plan
from app.services.mps_whatif_service import (
    _next_scenario_no,
    _apply_change,
    _batch_count_for_quantity,
    _expand_candidate_lines,
    _validate_shift_additions,
    compare_whatif_scenarios,
    create_whatif_scenario,
)


class _RollbackFixture(Exception):
    pass


def _suffix() -> str:
    return uuid4().hex[:10]


def _is_task_owned_disposable_m20_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m20_[a-z0-9]+_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_disposable_m20_postgres() -> None:
    """Require an exact, per-run database identity before any integration write."""
    if os.environ.get("M20_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M20_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    url = engine.url
    expected_name = os.environ.get("M20_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_disposable_m20_database(url, expected_name):
        pytest.fail(
            "Refusing M20 integration writes: DATABASE_URL must target the exact loopback PostgreSQL database "
            "named by M20_DISPOSABLE_TEST_DATABASE_NAME (fmcg_m20_<task>_<20-32 hex chars>)."
        )


def test_m20_disposable_database_guard_requires_exact_unique_loopback_target():
    name = "fmcg_m20_t004_0123456789abcdef0123"
    safe_url = URL.create("postgresql+asyncpg", username="test", password="hidden", host="127.0.0.1", database=name)
    assert _is_task_owned_disposable_m20_database(safe_url, name)
    assert not _is_task_owned_disposable_m20_database(safe_url, "fmcg_m20_t004_0123456789abcdef0124")
    assert not _is_task_owned_disposable_m20_database(safe_url, "fmcg_m20_t004_short")
    remote_url = URL.create("postgresql+asyncpg", host="db.example.com", database=name)
    assert not _is_task_owned_disposable_m20_database(remote_url, name)
    sqlite_url = URL.create("sqlite+aiosqlite", database=name)
    assert not _is_task_owned_disposable_m20_database(sqlite_url, name)


@pytest.mark.asyncio
async def test_mps_number_sequences_advance_past_existing_rows_and_are_concurrent_safe():
    _require_disposable_m20_postgres()
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        plan_numbers = (await db.execute(select(MPSPlan.plan_no))).scalars().all()
        line_numbers = (await db.execute(select(MPSLine.line_no))).scalars().all()

    def largest(values, prefix):
        suffixes = [value[len(prefix):] for value in values if isinstance(value, str) and value.startswith(prefix)]
        numbers = [int(suffix) for suffix in suffixes if suffix.isdigit()]
        return max(numbers, default=0)

    max_plan = largest(plan_numbers, "MPS-")
    max_line = largest(line_numbers, "MPSL-")

    async def allocate(prefix, column):
        async with AsyncSessionLocal() as db:
            async with db.begin():
                return await _next_seq(db, prefix, column)

    plan_values, line_values = await asyncio.gather(
        asyncio.gather(*(allocate("MPS-", MPSPlan.plan_no) for _ in range(12))),
        asyncio.gather(*(allocate("MPSL-", MPSLine.line_no) for _ in range(12))),
    )
    assert len(set(plan_values)) == len(plan_values)
    assert len(set(line_values)) == len(line_values)
    assert min(int(value.removeprefix("MPS-")) for value in plan_values) > max_plan
    assert min(int(value.removeprefix("MPSL-")) for value in line_values) > max_line

    async def allocate_scenario():
        async with AsyncSessionLocal() as db:
            async with db.begin():
                return await _next_scenario_no(db, uuid4())

    scenario_values = await asyncio.gather(*(allocate_scenario() for _ in range(12)))
    assert len(set(scenario_values)) == len(scenario_values)


def test_shift_add_uses_calendar_remaining_hours_and_rejects_overlap_evidence():
    wc_id = uuid4()
    day = date(2026, 11, 3)
    key = (wc_id, day)
    calendar = SimpleNamespace(
        available_hours=Decimal("8"), is_holiday=False, is_maintenance=False,
        shift_1_start="08:00", shift_1_end="16:00",
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    valid, unknown = _validate_shift_additions({key: Decimal("16")}, {key: calendar})
    assert valid == {key: Decimal("16")}
    assert not unknown
    with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining"):
        _validate_shift_additions({key: Decimal("16.001")}, {key: calendar})

    overlapping = SimpleNamespace(**{
        **calendar.__dict__, "shift_2_start": "15:00", "shift_2_end": "20:00",
    })
    valid, unknown = _validate_shift_additions({key: Decimal("1")}, {key: overlapping})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_SHIFTS_OVERLAP"}

    valid, unknown = _validate_shift_additions({key: Decimal("1")}, {})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_NOT_CONFIGURED"}

    no_shift_policy = SimpleNamespace(
        available_hours=Decimal("8"), is_holiday=False, is_maintenance=False,
        shift_1_start=None, shift_1_end=None,
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    valid, unknown = _validate_shift_additions({key: Decimal("1")}, {key: no_shift_policy})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_SHIFT_WINDOWS_NOT_CONFIGURED"}

    full_day = SimpleNamespace(
        available_hours=Decimal("24"), is_holiday=False, is_maintenance=False,
        shift_1_start="00:00", shift_1_end="08:00",
        shift_2_start="08:00", shift_2_end="16:00",
        shift_3_start="16:00", shift_3_end="00:00",
    )
    with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining"):
        _validate_shift_additions({key: Decimal("1")}, {key: full_day})

    downtime = SimpleNamespace(
        work_center_id=wc_id,
        start_time=datetime(2026, 11, 3, 9, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        duration_min=None,
    )
    valid, unknown = _validate_shift_additions({key: Decimal("1")}, {key: calendar}, [downtime])
    assert valid == {}
    assert unknown == {"SHIFT_ADD_DOWNTIME_OVERLAP_UNRESOLVED"}


def test_structural_scenarios_preserve_configured_batch_counts():
    line = {
        "id": "line-1",
        "planned_production_qty": "40",
        "batch_size_qty": "10",
        "num_batches": 4,
        "required_hours": "4",
    }
    assert _batch_count_for_quantity(line, Decimal("40")) == 4

    split = _apply_change(line.copy(), {
        "change_type": MPSChangeType.SPLIT,
        "new_value": {"quantities": ["20", "20"]},
    })
    candidate = _expand_candidate_lines([split])
    assert [line["planned_production_qty"] for line in candidate] == ["20", "20"]
    assert [line["num_batches"] for line in candidate] == [2, 2]
    assert [line["required_hours"] for line in candidate] == [None, None]

    with pytest.raises(ValueError, match="exact multiple of batch_size_qty"):
        _apply_change(line.copy(), {
            "change_type": MPSChangeType.SPLIT,
            "new_value": {"quantities": ["15", "25"]},
        })

    with pytest.raises(ValueError, match="does not match planned quantity"):
        _batch_count_for_quantity({**line, "num_batches": 3}, Decimal("40"))


@pytest.mark.asyncio
async def test_postgres_whatif_merge_exact_split_and_added_shift_resimulate_without_live_mutation():
    """Persist exact scenario operations and finite-capacity before/after metrics."""
    _require_disposable_m20_postgres()
    await engine.dispose()

    suffix = _suffix()
    day = date(2026, 11, 3)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            warehouse = Warehouse(
                code=f"M20-OPS-WH-{suffix}", name="M20 scenario operation warehouse",
                warehouse_type=WarehouseType.FINISHED_GOODS,
            )
            product = Product(
                sku=f"M20-OPS-P-{suffix}", name="M20 scenario operation product",
                category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
            )
            user = User(
                email=f"m20-ops-{suffix}@example.invalid", username=f"m20-ops-{suffix}",
                full_name="M20 scenario operations", hashed_password="test",
            )
            db.add_all([warehouse, product, user])
            await db.flush()
            work_center = WorkCenter(
                work_center_id=f"M20-OPS-WC-{suffix}", name="M20 scenario work center",
                type=WorkCenterType.LINE, capacity=10, capacity_uom="KG/HR",
            )
            db.add(work_center)
            await db.flush()
            db.add(ResourceCalendar(
                work_center_id=work_center.id, calendar_date=day,
                available_hours=8, shift_1_start="08:00", shift_1_end="16:00",
                is_holiday=False, is_maintenance=False,
            ))
            run = MRPRun(
                run_no=f"M20-OPS-RUN-{suffix}", run_date=day,
                status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
            )
            plan = MPSPlan(
                plan_no=f"M20-OPS-PLAN-{suffix}", plan_name="M20 scenario operation plan",
                start_date=day, end_date=day, mrp_run=run, capacity_mode=MPSCapacityMode.FINITE,
            )
            db.add(plan)
            await db.flush()
            first = MPSLine(
                line_no=f"M20-OPS-A-{suffix}", mps_id=plan.id, product_id=product.id,
                period_start=day, period_end=day, planned_start_date=day, planned_end_date=day,
                planned_production_qty=Decimal("40"), work_center_id=work_center.id,
                mrp_result_id=None, batch_size_qty=None, campaign_id=None,
                priority_score=Decimal("50"), feasibility_status=MPSFeasibilityStatus.PENDING,
            )
            second = MPSLine(
                line_no=f"M20-OPS-B-{suffix}", mps_id=plan.id, product_id=product.id,
                period_start=day, period_end=day, planned_start_date=day, planned_end_date=day,
                planned_production_qty=Decimal("60"), work_center_id=work_center.id,
                mrp_result_id=None, batch_size_qty=None, campaign_id=None,
                priority_score=Decimal("50"), feasibility_status=MPSFeasibilityStatus.PENDING,
            )
            db.add_all([first, second])
            await db.flush()
            plan_id, first_id, second_id, user_id = plan.id, first.id, second.id, user.id

        merged = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="merge equivalent schedules",
            changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
        ), user_id)
        split = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="exact split",
            changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.SPLIT, new_value={"quantities": ["15.125", "24.875"]})],
        ), user_id)
        shifted = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="add configured finite shift",
            changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={"date": day.isoformat(), "hours": "2"})],
        ), user_id)
        maximum_shift = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="aggregate shifts stay within daily calendar",
            changes=[
                WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={"date": day.isoformat(), "hours": "8"}),
                WhatIfChange(line_id=second_id, change_type=MPSChangeType.SHIFT_ADD, new_value={"date": day.isoformat(), "hours": "8"}),
            ],
        ), user_id)
        with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining work-center calendar hours"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="aggregate shift exceeds physical day",
                changes=[
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={"date": day.isoformat(), "hours": "9"}),
                    WhatIfChange(line_id=second_id, change_type=MPSChangeType.SHIFT_ADD, new_value={"date": day.isoformat(), "hours": "8"}),
                ],
            ), user_id)
        with pytest.raises(ValueError, match="MERGE/SPLIT lines cannot have conflicting scenario changes"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="merge split conflict",
                changes=[
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id)),
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.SPLIT, new_value={"quantities": ["20", "80"]}),
                ],
            ), user_id)
        second_line = await db.get(MPSLine, second_id)
        second_line.priority_score = Decimal("49")
        await db.flush()
        with pytest.raises(ValueError, match="matching source allocation, product, batch, campaign"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="incompatible priority merge",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
            ), user_id)
        second_line.priority_score = Decimal("50")
        second_line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
        await db.flush()
        with pytest.raises(ValueError, match="matching source allocation, product, batch, campaign"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="incompatible feasibility merge",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
            ), user_id)
        second_line.feasibility_status = MPSFeasibilityStatus.PENDING
        first_line = await db.get(MPSLine, first_id)
        first_line.batch_size_qty = Decimal("10")
        first_line.num_batches = 4
        first_line.required_hours = Decimal("4")
        second_line.batch_size_qty = Decimal("10")
        second_line.num_batches = 6
        second_line.required_hours = Decimal("6")
        await db.flush()
        merge_fields = (
            "product_id", "mrp_result_id", "period_start", "period_end",
            "planned_start_date", "planned_end_date", "work_center_id",
            "batch_size_qty", "campaign_id", "priority_score", "feasibility_status",
        )
        mismatched_fields = [
            field for field in merge_fields
            if getattr(first_line, field) != getattr(second_line, field)
        ]
        assert not mismatched_fields, f"batch merge fixture fields differ: {mismatched_fields}"
        batched_merge = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="merge compatible batch allocations",
            changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
        ), user_id)
        snapshots = (await db.scalars(select(MPSScenarioSnapshot).where(
            MPSScenarioSnapshot.scenario_id.in_([merged.id, split.id, shifted.id, maximum_shift.id, batched_merge.id]),
        ))).all()
        by_scenario = {row.scenario_id: row for row in snapshots}
        assert len(by_scenario) == 5
        batched_results = by_scenario[batched_merge.id].results
        merged_candidate = next(line for line in batched_results["modified_lines"] if line["id"] == str(first_id))
        assert Decimal(merged_candidate["planned_production_qty"]) == Decimal("100")
        assert merged_candidate["num_batches"] == 10
        assert merged_candidate["required_hours"] is None
        merged_lines = by_scenario[merged.id].results["modified_lines"]
        assert len(merged_lines) == 1
        assert Decimal(merged_lines[0]["planned_production_qty"]) == Decimal("100.000")
        split_lines = by_scenario[split.id].results["modified_lines"]
        assert [Decimal(line["planned_production_qty"]) for line in split_lines] == [Decimal("15.125"), Decimal("24.875"), Decimal("60.000")]
        assert sum((Decimal(line["planned_production_qty"]) for line in split_lines), Decimal(0)) == Decimal("100.000")
        assert by_scenario[merged.id].results["capacity_overload_hours"] == 2.0
        assert by_scenario[split.id].results["capacity_overload_hours"] == 2.0
        assert by_scenario[shifted.id].results["capacity_overload_hours"] == 0.0
        assert by_scenario[maximum_shift.id].results["capacity_overload_hours"] == 0.0
        assert by_scenario[maximum_shift.id].assumptions["shift_additions"] == [
            {"work_center_id": str((await db.get(MPSLine, first_id)).work_center_id), "date": day.isoformat(), "hours": "16"},
        ]
        assert by_scenario[shifted.id].assumptions["shift_additions"] == [
            {"work_center_id": str((await db.get(MPSLine, first_id)).work_center_id), "date": day.isoformat(), "hours": "2"},
        ]
        assert await db.scalar(select(func.sum(MPSLine.planned_production_qty)).where(
            MPSLine.mps_id == plan_id,
        )) == Decimal("100.000"), "scenario operations must not mutate live plan lines"


@pytest.mark.asyncio
async def test_postgres_kenya_fixture_drives_real_mps_material_feasibility_service():
    """Seed the published synthetic acceptance fixture and exercise MPS/BOM/stock services."""
    _require_disposable_m20_postgres()
    await engine.dispose()

    fixture = json.loads((Path(__file__).parent / "fixtures" / "m20_acceptance_dataset.json").read_text(encoding="utf-8"))
    assert fixture["classification"].startswith("synthetic test fixture")
    mango = fixture["products"][0]
    suffix = _suffix()
    start_day = date.fromisoformat(fixture["scope"]["horizon"][0])
    end_day = date.fromisoformat(fixture["scope"]["horizon"][1])
    company_id = warehouse_id = product_id = material_id = run_id = plan_id = None
    bom_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"{fixture['scope']['company']} {suffix}", short_code=f"M20{suffix}")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"{fixture['scope']['warehouse']}-{suffix}",
                    name=f"{fixture['scope']['warehouse']} synthetic acceptance warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                product = Product(
                    sku=f"{mango['sku']}-{suffix}", name=mango["name"],
                    category=ProductCategory.FOOD, uom=UnitOfMeasure[mango["uom"]],
                )
                material_record = mango["bom"]["components"][0]
                material = Material(
                    code=f"{material_record['material_code']}-{suffix}",
                    name="Synthetic acceptance sugar", material_type=MaterialType.RAW,
                    uom=UnitOfMeasure[material_record["uom"]],
                )
                db.add_all([warehouse, product, material])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-FIXTURE-RUN-{suffix}", run_date=start_day,
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                bom = AdvancedBOM(
                    bom_code=f"M20-FIXTURE-BOM-{suffix}",
                    bom_name=f"{mango['sku']} synthetic approved BOM",
                    product_id=product.id,
                    base_qty=mango["bom"]["base_qty"],
                    base_uom=mango["bom"]["base_uom"],
                    lifecycle=BOMLifecycle[mango["bom"]["lifecycle"]],
                    is_default=True, effective_from=start_day, effective_to=end_day,
                )
                db.add(bom)
                await db.flush()
                db.add_all([
                    AdvancedBOMLine(
                        bom_id=bom.id, line_no=1, item_type=ItemLinkType.MATERIAL,
                        item_id=material.id, required_qty=material_record["required_qty"],
                        required_uom=material_record["uom"],
                        basis_type=BasisType[material_record["basis_type"]],
                        wastage_pct=material_record["wastage_pct"],
                        process_loss_pct=material_record["process_loss_pct"],
                    ),
                    Stock(
                        stock_type=StockType.MATERIAL, warehouse_id=warehouse.id,
                        material_id=material.id,
                        quantity_on_hand=mango["material_stock"][material_record["material_code"]]["on_hand"],
                        quantity_reserved=mango["material_stock"][material_record["material_code"]]["reserved"],
                        quantity_available=(
                            Decimal(str(mango["material_stock"][material_record["material_code"]]["on_hand"]))
                            - Decimal(str(mango["material_stock"][material_record["material_code"]]["reserved"]))
                        ),
                    ),
                ])
                plan = MPSPlan(
                    plan_no=f"M20-FIXTURE-PLAN-{suffix}",
                    plan_name=f"{fixture['dataset_id']} {mango['sku']}",
                    start_date=start_day, end_date=end_day, mrp_run=run,
                )
                db.add(plan)
                await db.flush()
                line = MPSLine(
                    line_no=f"M20-FIXTURE-LINE-{suffix}", mps_id=plan.id,
                    product_id=product.id, period_start=start_day, period_end=end_day,
                    planned_start_date=start_day, planned_end_date=end_day,
                    planned_production_qty=mango["planned_qty"],
                )
                db.add(line)
                await db.flush()
                company_id, warehouse_id = company.id, warehouse.id
                product_id, material_id, run_id = product.id, material.id, run.id
                plan_id, bom_id = plan.id, bom.id
                line_id = line.id

            evaluation = await evaluate_material_feasibility(db, plan_id)
            assert evaluation["lines_evaluated"] == 1
            assert evaluation["material_short_lines"] == 1
            assert evaluation["infeasible_lines"] == 0
            diagnostics = await list_plan_diagnostics(db, plan_id)
            assert len(diagnostics) == 1
            issue = diagnostics[0]["diagnostics"]["issues"][0]
            expected_required = (
                Decimal(str(mango["planned_qty"]))
                * Decimal(str(material_record["required_qty"]))
                / Decimal(str(mango["bom"]["base_qty"]))
                * (Decimal("1") + Decimal(str(material_record["wastage_pct"])) / Decimal("100"))
            ).quantize(Decimal("0.0001"))
            expected_available = (
                Decimal(str(mango["material_stock"][material_record["material_code"]]["on_hand"]))
                - Decimal(str(mango["material_stock"][material_record["material_code"]]["reserved"]))
            )
            assert issue["reason_code"] == "MATERIAL_SHORT"
            assert Decimal(issue["required_qty"]) == expected_required == Decimal("16.3200")
            assert Decimal(issue["available_qty"]) == expected_available == Decimal("10")
            assert Decimal(issue["shortage_qty"]) == Decimal("6.3200")
            assert issue["uom"] == material_record["uom"]
            assert diagnostics[0]["line_id"] == str(line_id)
            details = diagnostics[0]["diagnostics"]
            assert details["line_no"] == f"M20-FIXTURE-LINE-{suffix}"
            assert Decimal(details["planned_quantity"]) == Decimal(str(mango["planned_qty"]))
            assert details["required_date"] == start_day.isoformat()
            assert issue["required_date"] == start_day.isoformat()
            assert Decimal(issue["planned_quantity"]) == Decimal(str(mango["planned_qty"]))
            assert issue["priority"] == "HIGH"
            assert issue["provenance"] == "warehouse stock; approved effective BOM/recipe"
            api_diagnostic = MPSLineConstraintDiagnosticOut.model_validate(diagnostics[0])
            assert api_diagnostic.diagnostics.issues[0].shortage_qty == Decimal("6.3200")
            assert api_diagnostic.diagnostics.issues[0].material_id == str(material_id)
            await db.execute(text(
                "UPDATE mps_line_diagnostics AS diagnostic SET diagnostics = jsonb_set("
                "diagnostic.diagnostics - 'line_no' - 'planned_quantity' - 'required_date', '{issues}', "
                "COALESCE((SELECT jsonb_agg(issue.value - 'planned_quantity' - 'required_date' - 'priority' - 'provenance') "
                "FROM jsonb_array_elements(diagnostic.diagnostics->'issues') AS issue(value)), '[]'::jsonb)) "
                "WHERE diagnostic.run_id = :run_id AND diagnostic.line_id = :line_id"
            ), {"run_id": api_diagnostic.run_id, "line_id": line_id})
            legacy_diagnostic = (await list_plan_diagnostics(db, plan_id))[0]
            legacy_api_diagnostic = MPSLineConstraintDiagnosticOut.model_validate(legacy_diagnostic)
            legacy_issue = legacy_api_diagnostic.diagnostics.issues[0]
            assert legacy_issue.priority == "HIGH"
            assert legacy_issue.provenance == "warehouse stock; approved effective BOM/recipe"
            assert legacy_issue.required_date == start_day
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if bom_id is not None:
                    await cleanup.execute(delete(AdvancedBOM).where(AdvancedBOM.id == bom_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if material_id is not None:
                    await cleanup.execute(delete(Stock).where(Stock.material_id == material_id))
                    await cleanup.execute(delete(Material).where(Material.id == material_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_postgres_mps_capacity_reconciles_rate_shifts_downtime_locks_and_modes():
    """Finite capacity must use configured units/calendars and preserve locked commitments."""
    _require_disposable_m20_postgres()
    await engine.dispose()
    suffix = _suffix()
    capacity_day = date(2026, 11, 3)
    maintenance_day = capacity_day + timedelta(days=1)
    invalid_shift_day = capacity_day + timedelta(days=2)
    attribution_day = capacity_day + timedelta(days=3)
    overnight_day = capacity_day + timedelta(days=4)
    invalid_downtime_day = capacity_day + timedelta(days=5)
    company_id = warehouse_id = product_id = run_id = plan_id = work_center_id = conversion_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 capacity {suffix}", short_code=f"C{suffix[:8]}")
                warehouse = Warehouse(
                    code=f"M20-CAP-WH-{suffix}", name="Synthetic capacity warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                product = Product(
                    sku=f"M20-CAP-P-{suffix}", name="Synthetic capacity product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                work_center = WorkCenter(
                    work_center_id=f"M20-CAP-WC-{suffix}", name="Synthetic aggregate-rate work center",
                    type=WorkCenterType.LINE, capacity=Decimal("10000"), capacity_uom="G/HR",
                )
                db.add_all([company, warehouse, product, work_center])
                await db.flush()
                conversion = UomConversion(from_uom="G", to_uom="KG", factor=Decimal("0.001"), is_active=True)
                db.add_all([
                    conversion,
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=capacity_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="12:00",
                        shift_2_start="13:00", shift_2_end="17:00",
                    ),
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=maintenance_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="16:00", is_maintenance=True,
                    ),
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=invalid_shift_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="14:00",
                        shift_2_start="13:00", shift_2_end="17:00",
                    ),
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=attribution_day, available_hours=10,
                        shift_1_start="07:00", shift_1_end="17:00",
                    ),
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=overnight_day, available_hours=8,
                        shift_1_start="22:00", shift_1_end="06:00",
                    ),
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=invalid_downtime_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="16:00",
                    ),
                    DowntimeEvent(
                        downtime_id=f"M20-CAP-DT1-{suffix}", work_center_id=work_center.id,
                        start_time=datetime(2026, 11, 3, 8, tzinfo=timezone.utc),
                        end_time=datetime(2026, 11, 3, 10, tzinfo=timezone.utc), reason="synthetic downtime window 1",
                    ),
                    DowntimeEvent(
                        downtime_id=f"M20-CAP-DT2-{suffix}", work_center_id=work_center.id,
                        start_time=datetime(2026, 11, 3, 9, tzinfo=timezone.utc),
                        end_time=datetime(2026, 11, 3, 11, tzinfo=timezone.utc), reason="synthetic overlapping downtime window",
                    ),
                    DowntimeEvent(
                        downtime_id=f"M20-CAP-DT3-{suffix}", work_center_id=work_center.id,
                        start_time=datetime.combine(overnight_day + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).replace(hour=1),
                        end_time=datetime.combine(overnight_day + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).replace(hour=3),
                        reason="synthetic downtime inside overnight shift",
                    ),
                    DowntimeEvent(
                        downtime_id=f"M20-CAP-DT4-{suffix}", work_center_id=work_center.id,
                        start_time=datetime.combine(invalid_downtime_day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=17),
                        end_time=datetime.combine(invalid_downtime_day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=7),
                        reason="synthetic reversed downtime envelope crossing the shift",
                    ),
                    DowntimeEvent(
                        downtime_id=f"M20-CAP-DT5-{suffix}", work_center_id=work_center.id,
                        start_time=datetime.combine(invalid_downtime_day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=17),
                        duration_min=-600,
                        reason="synthetic negative-duration downtime envelope crossing the shift",
                    ),
                ])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-CAP-RUN-{suffix}", run_date=capacity_day,
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                plan = MPSPlan(
                    plan_no=f"M20-CAP-PLAN-{suffix}", plan_name="Synthetic capacity acceptance plan",
                    start_date=capacity_day, end_date=invalid_downtime_day, mrp_run=run,
                    capacity_mode=MPSCapacityMode.FINITE,
                )
                db.add(plan)
                await db.flush()
                locked = MPSLine(
                    line_no=f"M20-CAP-LOCKED-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=capacity_day, period_end=capacity_day, planned_start_date=capacity_day,
                    planned_end_date=capacity_day, planned_production_qty=60, work_center_id=work_center.id,
                    is_locked=True, feasibility_status=MPSFeasibilityStatus.ON_HOLD, priority_score=100,
                )
                concurrent = MPSLine(
                    line_no=f"M20-CAP-LINE-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=capacity_day, period_end=capacity_day, planned_start_date=capacity_day,
                    planned_end_date=capacity_day, planned_production_qty=60, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING, priority_score=50,
                )
                maintenance = MPSLine(
                    line_no=f"M20-CAP-MAINT-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=maintenance_day, period_end=maintenance_day, planned_start_date=maintenance_day,
                    planned_end_date=maintenance_day, planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING, priority_score=40,
                )
                invalid_shift = MPSLine(
                    line_no=f"M20-CAP-SHIFT-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=invalid_shift_day, period_end=invalid_shift_day, planned_start_date=invalid_shift_day,
                    planned_end_date=invalid_shift_day, planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                attribution_locked = MPSLine(
                    line_no=f"M20-CAP-ATTR-LOCK-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=attribution_day, period_end=attribution_day, planned_start_date=attribution_day,
                    planned_end_date=attribution_day, planned_production_qty=110, work_center_id=work_center.id,
                    is_locked=True, feasibility_status=MPSFeasibilityStatus.ON_HOLD, priority_score=10,
                )
                attribution_unlocked = MPSLine(
                    line_no=f"M20-CAP-ATTR-OPEN-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=attribution_day, period_end=attribution_day, planned_start_date=attribution_day,
                    planned_end_date=attribution_day, planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING, priority_score=100,
                )
                overnight = MPSLine(
                    line_no=f"M20-CAP-NIGHT-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=overnight_day, period_end=overnight_day, planned_start_date=overnight_day,
                    planned_end_date=overnight_day, planned_production_qty=50, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                invalid_downtime = MPSLine(
                    line_no=f"M20-CAP-DOWNTIME-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=invalid_downtime_day, period_end=invalid_downtime_day,
                    planned_start_date=invalid_downtime_day, planned_end_date=invalid_downtime_day,
                    planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                bad_date = MPSLine(
                    line_no=f"M20-CAP-DATE-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=capacity_day, period_end=maintenance_day, planned_start_date=maintenance_day,
                    planned_end_date=capacity_day, planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                negative = MPSLine(
                    line_no=f"M20-CAP-NEG-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=capacity_day, period_end=capacity_day, planned_start_date=capacity_day,
                    planned_end_date=capacity_day, planned_production_qty=-10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                db.add_all([
                    locked, concurrent, maintenance, invalid_shift, attribution_locked,
                    attribution_unlocked, overnight, invalid_downtime, bad_date, negative,
                ])
                await db.flush()
                company_id, warehouse_id, product_id = company.id, warehouse.id, product.id
                run_id, plan_id, work_center_id, conversion_id = run.id, plan.id, work_center.id, conversion.id
                locked_id, concurrent_id, maintenance_id = locked.id, concurrent.id, maintenance.id
                invalid_shift_id = invalid_shift.id
                attribution_locked_id, attribution_unlocked_id = attribution_locked.id, attribution_unlocked.id
                overnight_id = overnight.id
                invalid_downtime_id = invalid_downtime.id
                bad_date_id, negative_id = bad_date.id, negative.id

            result = await run_capacity_scheduling_validated(db, plan_id)
            assert result["mode"] == "FINITE"
            assert result["overloaded_lines"] == 5
            slots = (await db.scalars(select(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id))).all()
            slots_by_day = {slot.slot_date: slot for slot in slots}
            assert set(slots_by_day) == {
                capacity_day, maintenance_day, invalid_shift_day, attribution_day, overnight_day,
                invalid_downtime_day,
            }
            assert slots_by_day[capacity_day].allocated_hours == Decimal("12.000")
            assert slots_by_day[capacity_day].available_hours == Decimal("8.000")
            assert slots_by_day[capacity_day].downtime_hours == Decimal("3.000")
            assert slots_by_day[capacity_day].overload_hours == Decimal("7.000")
            assert slots_by_day[maintenance_day].available_hours == Decimal("0.000")
            assert slots_by_day[maintenance_day].overload_hours == Decimal("1.000")
            assert slots_by_day[invalid_shift_day].available_hours == Decimal("0.000")
            assert slots_by_day[invalid_shift_day].overload_hours == Decimal("1.000")
            assert slots_by_day[attribution_day].allocated_hours == Decimal("12.000")
            assert slots_by_day[attribution_day].overload_hours == Decimal("2.000")
            assert slots_by_day[overnight_day].available_hours == Decimal("8.000")
            assert slots_by_day[overnight_day].downtime_hours == Decimal("2.000")
            assert slots_by_day[overnight_day].overload_hours == Decimal("0.000")
            assert slots_by_day[invalid_downtime_day].available_hours == Decimal("8.000")
            assert slots_by_day[invalid_downtime_day].downtime_hours == Decimal("8.000")
            assert slots_by_day[invalid_downtime_day].overload_hours == Decimal("1.000")
            assert (await db.get(MPSLine, locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert (await db.get(MPSLine, concurrent_id)).required_hours == Decimal("6.000")
            assert (await db.get(MPSLine, concurrent_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, maintenance_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, invalid_shift_id)).feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert (await db.get(MPSLine, attribution_locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert (await db.get(MPSLine, attribution_unlocked_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, overnight_id)).feasibility_status == MPSFeasibilityStatus.FEASIBLE
            assert (await db.get(MPSLine, invalid_downtime_id)).feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            diagnostics = await list_plan_diagnostics(db, plan_id)
            by_line = {uuid.UUID(row["line_id"]): row for row in diagnostics}
            locked_api = MPSLineConstraintDiagnosticOut.model_validate(by_line[locked_id])
            assert locked_api.diagnostics.issues[0].reason_code == "CAPACITY_OVERLOAD"
            assert locked_api.diagnostics.issues[0].overload_hours == Decimal("1.000")
            assert locked_api.diagnostics.issues[0].capacity_date == capacity_day
            assert by_line[concurrent_id]["diagnostics"]["issues"][0]["reason_code"] == "CAPACITY_OVERLOAD"
            assert by_line[bad_date_id]["diagnostics"]["issues"][0]["reason_code"] == "CAPACITY_DATE_RANGE_INVALID"
            assert by_line[negative_id]["diagnostics"]["issues"][0]["reason_code"] == "CAPACITY_QUANTITY_INVALID"
            assert "CAPACITY_CALENDAR_INVALID" in by_line[invalid_shift_id]["diagnostics"]["reason_codes"]
            assert "DOWNTIME_DATA_INVALID" in by_line[invalid_downtime_id]["diagnostics"]["reason_codes"]
            assert Decimal(by_line[attribution_locked_id]["diagnostics"]["issues"][0]["overload_hours"]) == Decimal("1")
            assert Decimal(by_line[attribution_unlocked_id]["diagnostics"]["issues"][0]["overload_hours"]) == Decimal("1")
            assert Decimal(by_line[attribution_unlocked_id]["diagnostics"]["issues"][0]["required_hours"]) == Decimal("1.000")

            plan = await db.get(MPSPlan, plan_id)
            plan.capacity_mode = MPSCapacityMode.INFINITE
            await db.flush()
            infinite_result = await run_capacity_scheduling_validated(db, plan_id)
            assert infinite_result["mode"] == "INFINITE"
            assert (await db.get(MPSLine, locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert await db.scalar(select(func.count()).select_from(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id)) == 0
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if work_center_id is not None:
                    await cleanup.execute(delete(DowntimeEvent).where(DowntimeEvent.work_center_id == work_center_id))
                    await cleanup.execute(delete(ResourceCalendar).where(ResourceCalendar.work_center_id == work_center_id))
                    await cleanup.execute(delete(WorkCenter).where(WorkCenter.id == work_center_id))
                if conversion_id is not None:
                    await cleanup.execute(delete(UomConversion).where(UomConversion.id == conversion_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_mps_material_feasibility_fails_closed_on_ambiguous_bom_and_scopes_material_supply():
    """Convert BOM units, keep ambiguous receipts/substitutes out, and reject overlapping approved BOMs."""
    _require_disposable_m20_postgres()
    await engine.dispose()

    suffix = _suffix()
    start_day = date(2026, 10, 1)
    company_id = warehouse_id = other_warehouse_id = product_id = material_id = alternative_id = None
    run_id = plan_id = bom_id = duplicate_bom_id = supplier_id = purchase_order_id = None
    substitute_group_id = conversion_id = duplicate_conversion_id = None
    line_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 material scope {suffix}", short_code=f"M20{suffix}")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-MAT-{suffix}", name="M20 material target warehouse",
                    warehouse_type=WarehouseType.RAW_MATERIAL, company_id=company.id,
                )
                other_warehouse = Warehouse(
                    code=f"M20-MAT-OTHER-{suffix}", name="M20 other company warehouse",
                    warehouse_type=WarehouseType.RAW_MATERIAL, company_id=company.id,
                )
                product = Product(
                    sku=f"M20-MAT-{suffix}", name="M20 synthetic product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                material = Material(
                    code=f"M20-RAW-{suffix}", name="M20 synthetic raw material",
                    material_type=MaterialType.RAW, uom=UnitOfMeasure.KG, lead_time_days=5,
                )
                alternative = Material(
                    code=f"M20-ALT-{suffix}", name="M20 synthetic substitute",
                    material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
                )
                supplier = Supplier(code=f"M20-SUP-{suffix}", name="M20 synthetic supplier")
                db.add_all([warehouse, other_warehouse, product, material, alternative, supplier])
                await db.flush()
                run = MRPRun(run_no=f"M20-MAT-RUN-{suffix}", run_date=start_day,
                             status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id)
                db.add(run)
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-MAT-PLAN-{suffix}", plan_name="M20 synthetic material scope",
                    start_date=start_day, end_date=start_day, mrp_run=run,
                )
                db.add(plan)
                await db.flush()
                line = MPSLine(
                    line_no=f"M20-MAT-LINE-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=start_day, period_end=start_day,
                    planned_start_date=start_day, planned_end_date=start_day,
                    planned_production_qty=Decimal("2"),
                )
                group = BOMSubstituteGroup(
                    group_code=f"M20-GROUP-{suffix}", group_name="M20 approval-gated substitutes",
                    policy=SubstitutionPolicy.PLANNER_APPROVAL,
                )
                db.add_all([line, group])
                await db.flush()
                bom = AdvancedBOM(
                    bom_code=f"M20-BOM-{suffix}", bom_name="M20 approved synthetic BOM",
                    product_id=product.id, base_qty=Decimal("1"), base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED, is_default=True,
                    effective_from=start_day, effective_to=start_day,
                )
                db.add(bom)
                await db.flush()
                bom_line = AdvancedBOMLine(
                    bom_id=bom.id, line_no=1, item_type=ItemLinkType.MATERIAL,
                    item_id=material.id, required_qty=Decimal("1000"), required_uom="G",
                    basis_type=BasisType.PER_BATCH, substitution_policy=SubstitutionPolicy.PLANNER_APPROVAL,
                    substitute_group_id=group.id,
                )
                yield_config = BOMYieldConfig(
                    bom_id=bom.id, loss_category=LossCategory.PROCESS_LOSS,
                    basis="PCT_OF_INPUT", standard_pct=Decimal("10"),
                    max_allowable_pct=Decimal("15"),
                )
                stock = Stock(
                    stock_type=StockType.MATERIAL, warehouse_id=warehouse.id, material_id=material.id,
                    quantity_on_hand=Decimal("2"), quantity_reserved=Decimal("0.5"),
                    quantity_available=Decimal("1.5"),
                )
                conversion = UomConversion(from_uom="G", to_uom="KG", factor=Decimal("0.001"), is_active=True)
                po = PurchaseOrder(
                    po_no=f"M20-PO-{suffix}", supplier_id=supplier.id, company_id=company.id,
                    branch_id=None, order_date=start_day, expected_delivery_date=start_day,
                    status=POStatus.ORDERED,
                )
                db.add_all([bom_line, yield_config, stock, conversion, po])
                await db.flush()
                po_line = POLine(
                    po_id=po.id, line_no=1, material_id=material.id,
                    ordered_quantity=Decimal("1000"), received_quantity=Decimal("0"), unit="G",
                )
                db.add(po_line)
                await db.flush()
                company_id, warehouse_id, other_warehouse_id = company.id, warehouse.id, other_warehouse.id
                product_id, material_id, alternative_id = product.id, material.id, alternative.id
                run_id, plan_id, bom_id, supplier_id = run.id, plan.id, bom.id, supplier.id
                purchase_order_id, substitute_group_id, conversion_id, line_id = po.id, group.id, conversion.id, line.id

            evaluation = await evaluate_material_feasibility(db, plan_id)
            await db.commit()
            assert evaluation["infeasible_lines"] == 0
            assert evaluation["material_short_lines"] == 1
            diagnostics = await list_plan_diagnostics(db, plan_id)
            issues = diagnostics[0]["diagnostics"]["issues"]
            assert [issue["reason_code"] for issue in issues] == ["MATERIAL_SHORT"]
            shortage = issues[0]
            assert Decimal(shortage["required_qty"]) == Decimal("2.2222")
            assert Decimal(shortage["available_qty"]) == Decimal("1.5")
            assert Decimal(shortage["shortage_qty"]) == Decimal("0.7222")
            assert shortage["uom"] == "KG"
            assert shortage["latest_order_date"] == "2026-09-26"
            assert shortage["substitution_policy"] == "PLANNER_APPROVAL"
            assert shortage["substitute_group_id"] == str(substitute_group_id)
            assert shortage["excluded_receipts"] == [{
                "po_no": f"M20-PO-{suffix}", "due_date": start_day.isoformat(),
                "reason": "PURCHASE_ORDER_DESTINATION_AMBIGUOUS",
            }]
            assert diagnostics[0]["line_id"] == str(line_id)
            await db.commit()

            async with db.begin():
                duplicate_conversion = UomConversion(
                    from_uom="G", to_uom="KG", factor=Decimal("0.001"), is_active=True,
                )
                db.add(duplicate_conversion)
                await db.flush()
                duplicate_conversion_id = duplicate_conversion.id
            evaluation = await evaluate_material_feasibility(db, plan_id)
            await db.commit()
            assert evaluation["infeasible_lines"] == 1
            diagnostics = await list_plan_diagnostics(db, plan_id)
            duplicate_conversion_issue = diagnostics[0]["diagnostics"]["issues"][0]
            assert duplicate_conversion_issue["reason_code"] == "MATERIAL_UOM_MISMATCH"
            assert "Multiple active UOM conversion rows" in duplicate_conversion_issue["message"]
            await db.commit()

            async with db.begin():
                await db.execute(
                    UomConversion.__table__.update()
                    .where(UomConversion.id == duplicate_conversion_id)
                    .values(is_active=False)
                )
                duplicate_bom = AdvancedBOM(
                    bom_code=f"M20-BOM-DUP-{suffix}", bom_name="Overlapping approved synthetic BOM",
                    product_id=product_id, base_qty=Decimal("1"), base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED, is_default=True,
                    effective_from=start_day, effective_to=start_day,
                )
                db.add(duplicate_bom)
                await db.flush()
                duplicate_bom_id = duplicate_bom.id
            evaluation = await evaluate_material_feasibility(db, plan_id)
            await db.commit()
            assert evaluation["infeasible_lines"] == 1
            await db.refresh(line)
            assert line.feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            diagnostics = await list_plan_diagnostics(db, plan_id)
            issues = diagnostics[0]["diagnostics"]["issues"]
            assert issues[0]["reason_code"] == "APPROVED_BOM_AMBIGUOUS"
            assert set(issues[0]["bom_ids"]) == {str(bom_id), str(duplicate_bom_id)}
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if duplicate_bom_id is not None:
                    await cleanup.execute(delete(AdvancedBOM).where(AdvancedBOM.id == duplicate_bom_id))
                if bom_id is not None:
                    await cleanup.execute(delete(AdvancedBOM).where(AdvancedBOM.id == bom_id))
                if purchase_order_id is not None:
                    await cleanup.execute(delete(POLine).where(POLine.po_id == purchase_order_id))
                    await cleanup.execute(delete(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id))
                if substitute_group_id is not None:
                    await cleanup.execute(delete(BOMSubstituteGroup).where(BOMSubstituteGroup.id == substitute_group_id))
                if conversion_id is not None:
                    await cleanup.execute(delete(UomConversion).where(UomConversion.id == conversion_id))
                if duplicate_conversion_id is not None:
                    await cleanup.execute(delete(UomConversion).where(UomConversion.id == duplicate_conversion_id))
                if material_id is not None or alternative_id is not None:
                    ids = [value for value in (material_id, alternative_id) if value is not None]
                    await cleanup.execute(delete(Stock).where(Stock.material_id.in_(ids)))
                    await cleanup.execute(delete(Material).where(Material.id.in_(ids)))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if warehouse_id is not None or other_warehouse_id is not None:
                    ids = [value for value in (warehouse_id, other_warehouse_id) if value is not None]
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id.in_(ids)))
                if supplier_id is not None:
                    await cleanup.execute(delete(Supplier).where(Supplier.id == supplier_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_mps_material_receipts_are_allocated_in_required_date_order_within_period():
    """A later-dated PO receipt must not cover an earlier line sharing the same period bucket."""
    _require_disposable_m20_postgres()
    await engine.dispose()

    suffix = _suffix()
    first_day = date(2026, 10, 1)
    company_id = warehouse_id = product_id = material_id = supplier_id = None
    run_id = plan_id = bom_id = po_id = None
    early_line_id = late_line_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 receipt order {suffix}", short_code=f"M2O{suffix}")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-ORDER-{suffix}", name="M20 material-order target",
                    warehouse_type=WarehouseType.RAW_MATERIAL, company_id=company.id,
                )
                product = Product(
                    sku=f"M20-ORDER-{suffix}", name="M20 date-order product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                material = Material(
                    code=f"M20-ORDER-RAW-{suffix}", name="M20 date-order material",
                    material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
                )
                supplier = Supplier(code=f"M20-ORDER-SUP-{suffix}", name="M20 date-order supplier")
                db.add_all([warehouse, product, material, supplier])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-ORDER-RUN-{suffix}", run_date=first_day,
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-ORDER-PLAN-{suffix}", plan_name="M20 chronological material allocation",
                    start_date=first_day, end_date=first_day + timedelta(days=9), mrp_run=run,
                )
                db.add(plan)
                await db.flush()
                early = MPSLine(
                    line_no=f"M20-EARLY-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=first_day, period_end=first_day + timedelta(days=6),
                    planned_start_date=first_day + timedelta(days=1),
                    planned_end_date=first_day + timedelta(days=2),
                    planned_production_qty=Decimal("3"), priority_score=Decimal("1"),
                )
                late = MPSLine(
                    line_no=f"M20-LATE-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=first_day, period_end=first_day + timedelta(days=6),
                    planned_start_date=first_day + timedelta(days=6),
                    planned_end_date=first_day + timedelta(days=7),
                    planned_production_qty=Decimal("2"), priority_score=Decimal("99"),
                )
                db.add_all([early, late])
                await db.flush()
                bom = AdvancedBOM(
                    bom_code=f"M20-ORDER-BOM-{suffix}", bom_name="M20 date-order BOM",
                    product_id=product.id, base_qty=Decimal("1"), base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED, is_default=True,
                    effective_from=first_day, effective_to=first_day + timedelta(days=9),
                )
                db.add(bom)
                await db.flush()
                db.add(AdvancedBOMLine(
                    bom_id=bom.id, line_no=1, item_type=ItemLinkType.MATERIAL,
                    item_id=material.id, required_qty=Decimal("1"), required_uom="KG",
                    basis_type=BasisType.PER_UNIT,
                ))
                po = PurchaseOrder(
                    po_no=f"M20-ORDER-PO-{suffix}", supplier_id=supplier.id,
                    company_id=company.id, order_date=first_day,
                    expected_delivery_date=first_day + timedelta(days=4), status=POStatus.ORDERED,
                )
                db.add(po)
                await db.flush()
                db.add(POLine(
                    po_id=po.id, line_no=1, material_id=material.id,
                    ordered_quantity=Decimal("5"), received_quantity=Decimal("0"), unit="KG",
                ))
                await db.flush()
                company_id, warehouse_id = company.id, warehouse.id
                product_id, material_id, supplier_id = product.id, material.id, supplier.id
                run_id, plan_id, bom_id, po_id = run.id, plan.id, bom.id, po.id
                early_line_id, late_line_id = early.id, late.id

            evaluation = await evaluate_material_feasibility(db, plan_id)
            await db.commit()
            assert evaluation["lines_evaluated"] == 2
            diagnostics = await list_plan_diagnostics(db, plan_id)
            by_line = {row["line_id"]: row["diagnostics"] for row in diagnostics}
            early_issue = by_line[str(early_line_id)]["issues"][0]
            assert early_issue["reason_code"] == "MATERIAL_SHORT"
            assert Decimal(early_issue["shortage_qty"]) == Decimal("3.0000")
            assert by_line[str(late_line_id)]["issues"] == []
            await db.refresh(early)
            await db.refresh(late)
            assert early.feasibility_status == MPSFeasibilityStatus.MATERIAL_SHORT
            assert late.feasibility_status == MPSFeasibilityStatus.FEASIBLE
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if bom_id is not None:
                    await cleanup.execute(delete(AdvancedBOM).where(AdvancedBOM.id == bom_id))
                if po_id is not None:
                    await cleanup.execute(delete(POLine).where(POLine.po_id == po_id))
                    await cleanup.execute(delete(PurchaseOrder).where(PurchaseOrder.id == po_id))
                if material_id is not None:
                    await cleanup.execute(delete(Stock).where(Stock.material_id == material_id))
                    await cleanup.execute(delete(Material).where(Material.id == material_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if supplier_id is not None:
                    await cleanup.execute(delete(Supplier).where(Supplier.id == supplier_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_postgres_mps_demand_projection_nets_forecast_and_carries_mrp_safety_target():
    """Dated orders, approved forecast and the source-run safety policy net once by bucket."""
    _require_disposable_m20_postgres()
    await engine.dispose()
    suffix = _suffix()
    company_id = warehouse_id = customer_id = run_id = None
    product_ids: list = []
    plan_ids: list = []
    order_ids: list = []
    forecast_ids: list = []
    start = date(2026, 1, 1)
    end = date(2026, 1, 14)
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 demand {suffix}", short_code=f"D{suffix}")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-D-{suffix}", name="M20 synthetic demand warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                customer = Customer(code=f"M20-D-{suffix}", name="Synthetic demand customer")
                confirmed_product = Product(
                    sku=f"M20-D-SO-{suffix}", name="Demand with order and forecast",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG, reorder_point=Decimal("999"),
                )
                safety_only_product = Product(
                    sku=f"M20-D-SS-{suffix}", name="Safety target only",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG, reorder_point=Decimal("0"),
                )
                inactive_safety_product = Product(
                    sku=f"M20-D-INACTIVE-{suffix}", name="Inactive safety target",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG, reorder_point=Decimal("0"),
                    is_active=False,
                )
                db.add_all([warehouse, customer, confirmed_product, safety_only_product, inactive_safety_product])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-D-RUN-{suffix}", run_date=start,
                    planning_horizon_days=30, status=MRPRunStatus.COMPLETED,
                    include_forecast=True, include_safety_stock=True, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                db.add_all([
                    MRPResult(
                        run_id=run.id, product_id=confirmed_product.id,
                        safety_stock_qty=Decimal("20"),
                    ),
                    MRPResult(
                        run_id=run.id, product_id=safety_only_product.id,
                        safety_stock_qty=Decimal("10"),
                    ),
                    MRPResult(
                        run_id=run.id, product_id=inactive_safety_product.id,
                        safety_stock_qty=Decimal("25"),
                    ),
                ])
                confirmed_order = SalesOrder(
                    order_no=f"M20-D-SO-{suffix}", customer_id=customer.id,
                    order_date=start, requested_delivery_date=date(2026, 1, 2),
                    status=SOStatus.CONFIRMED, warehouse_id=warehouse.id, company_id=company.id,
                )
                cancelled_order = SalesOrder(
                    order_no=f"M20-D-CANCEL-{suffix}", customer_id=customer.id,
                    order_date=start, requested_delivery_date=date(2026, 1, 2),
                    status=SOStatus.CANCELLED, warehouse_id=warehouse.id, company_id=company.id,
                )
                db.add_all([confirmed_order, cancelled_order])
                await db.flush()
                db.add_all([
                    SOLine(
                        so_id=confirmed_order.id, line_no=1, product_id=confirmed_product.id,
                        ordered_quantity=Decimal("80"), shipped_quantity=Decimal("20"), unit="KG",
                    ),
                    SOLine(
                        so_id=cancelled_order.id, line_no=1, product_id=confirmed_product.id,
                        ordered_quantity=Decimal("500"), shipped_quantity=Decimal("0"), unit="KG",
                    ),
                ])
                approved_forecast = DemandForecast(
                    product_id=confirmed_product.id, warehouse_id=warehouse.id,
                    forecast_model=ForecastModelType.MOVING_AVG, period_type=PeriodType.WEEKLY,
                    start_date=start, end_date=date(2026, 1, 7), status=ForecastStatus.APPROVED,
                    is_approved=True,
                )
                draft_forecast = DemandForecast(
                    product_id=confirmed_product.id, warehouse_id=warehouse.id,
                    forecast_model=ForecastModelType.SEASONAL, period_type=PeriodType.WEEKLY,
                    start_date=start, end_date=date(2026, 1, 7), status=ForecastStatus.DRAFT,
                    is_approved=False,
                )
                db.add_all([approved_forecast, draft_forecast])
                await db.flush()
                db.add_all([
                    DemandForecastLine(forecast_id=approved_forecast.id, period_date=start, forecast_qty=Decimal("100")),
                    DemandForecastLine(forecast_id=draft_forecast.id, period_date=start, forecast_qty=Decimal("900")),
                ])

                def plan_for(plan_no: str) -> MPSPlan:
                    return MPSPlan(
                        plan_no=plan_no, plan_name="Synthetic demand projection",
                        start_date=start, end_date=end, mrp_run_id=run.id,
                    )

                plan = plan_for(f"M20-D-PLAN-{suffix}")
                no_forecast_plan = plan_for(f"M20-D-NOFC-{suffix}")
                no_safety_plan = plan_for(f"M20-D-NOSS-{suffix}")
                overlapping_plan = plan_for(f"M20-D-OVERLAP-{suffix}")
                db.add_all([plan, no_forecast_plan, no_safety_plan, overlapping_plan])
                await db.flush()
                company_id, warehouse_id, customer_id = company.id, warehouse.id, customer.id
                run_id = run.id
                product_ids = [confirmed_product.id, safety_only_product.id, inactive_safety_product.id]
                plan_ids = [plan.id, no_forecast_plan.id, no_safety_plan.id, overlapping_plan.id]
                order_ids = [confirmed_order.id, cancelled_order.id]
                forecast_ids = [approved_forecast.id, draft_forecast.id]

            async with db.begin():
                result = await project_demand_and_supply(db, plan.id, "WEEKLY")
                assert result["lines_created"] == 3
                projected = (await db.execute(
                    select(MPSLine).where(MPSLine.mps_id == plan.id).order_by(MPSLine.period_start, MPSLine.product_id)
                )).scalars().all()
                by_product_period = {(line.product_id, line.period_start): line for line in projected}
                first_a = by_product_period[(confirmed_product.id, date(2026, 1, 1))]
                second_a = by_product_period[(confirmed_product.id, date(2026, 1, 5))]
                first_b = by_product_period[(safety_only_product.id, date(2026, 1, 1))]
                assert first_a.confirmed_demand_qty == Decimal("60.000")
                assert first_a.forecast_qty == Decimal("0.000")
                assert first_a.safety_stock_qty == Decimal("20.000")
                assert first_a.net_requirement_qty == Decimal("80.000")
                assert second_a.confirmed_demand_qty == Decimal("0.000")
                assert second_a.forecast_qty == Decimal("42.857")
                assert second_a.safety_stock_qty == Decimal("20.000")
                assert second_a.net_requirement_qty == Decimal("42.857")
                assert first_b.confirmed_demand_qty == Decimal("0.000")
                assert first_b.forecast_qty == Decimal("0.000")
                assert first_b.safety_stock_qty == Decimal("10.000")
                assert first_b.net_requirement_qty == Decimal("10.000")
                assert inactive_safety_product.id not in by_product_period

                run.include_forecast = False
                await db.flush()
                no_forecast = await project_demand_and_supply(db, no_forecast_plan.id, "WEEKLY")
                assert no_forecast["lines_created"] == 2
                no_forecast_lines = (await db.execute(
                    select(MPSLine).where(MPSLine.mps_id == no_forecast_plan.id)
                )).scalars().all()
                assert all(line.forecast_qty == Decimal("0.000") for line in no_forecast_lines)

                run.include_safety_stock = False
                await db.flush()
                no_safety = await project_demand_and_supply(db, no_safety_plan.id, "WEEKLY")
                assert no_safety["lines_created"] == 1
                no_safety_lines = (await db.execute(
                    select(MPSLine).where(MPSLine.mps_id == no_safety_plan.id)
                )).scalars().all()
                assert len(no_safety_lines) == 1
                assert no_safety_lines[0].product_id == confirmed_product.id
                assert no_safety_lines[0].safety_stock_qty == Decimal("0.000")

                run.include_forecast = True
                run.include_safety_stock = True
                await db.flush()
                ambiguous_forecast = DemandForecast(
                    product_id=confirmed_product.id, warehouse_id=warehouse.id,
                    forecast_model=ForecastModelType.SEASONAL, period_type=PeriodType.WEEKLY,
                    start_date=date(2026, 1, 4), end_date=date(2026, 1, 10),
                    status=ForecastStatus.APPROVED, is_approved=True,
                )
                db.add(ambiguous_forecast)
                await db.flush()
                db.add(DemandForecastLine(
                    forecast_id=ambiguous_forecast.id, period_date=date(2026, 1, 4), forecast_qty=Decimal("50"),
                ))
                await db.flush()
                with pytest.raises(ValueError, match="Overlapping approved forecasts"):
                    await project_demand_and_supply(db, overlapping_plan.id, "WEEKLY")
                assert (await db.scalar(select(func.count()).select_from(MPSLine).where(
                    MPSLine.mps_id == overlapping_plan.id,
                ))) == 0
        forecast_ids.append(ambiguous_forecast.id)
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_ids:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id.in_(plan_ids)))
                if order_ids:
                    await cleanup.execute(delete(SalesOrder).where(SalesOrder.id.in_(order_ids)))
                if forecast_ids:
                    await cleanup.execute(delete(DemandForecast).where(DemandForecast.id.in_(forecast_ids)))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if product_ids:
                    await cleanup.execute(delete(Stock).where(Stock.product_id.in_(product_ids)))
                    await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if customer_id is not None:
                    await cleanup.execute(delete(Customer).where(Customer.id == customer_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_postgres_mps_supply_projection_scopes_and_nets_dated_receipts():
    """Inventory, PO, WIP and approved MPS supply are scoped, dated and reported separately."""
    _require_disposable_m20_postgres()
    await engine.dispose()
    suffix = _suffix()
    company_id = warehouse_ids = branch_ids = supplier_id = product_id = customer_id = None
    recipe_id = None
    run_ids: list = []
    plan_ids: list = []
    order_ids: list = []
    po_ids: list = []
    production_order_ids: list = []
    conversion_id = None
    start = date(2026, 1, 1)
    end = date(2026, 1, 14)
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 supply {suffix}", short_code=f"S{suffix}")
                db.add(company)
                await db.flush()
                branch_a = Branch(company_id=company.id, name="Supply branch A", branch_code=f"A{suffix[:6]}")
                branch_b = Branch(company_id=company.id, name="Supply branch B", branch_code=f"B{suffix[:6]}")
                supplier = Supplier(code=f"M20-S-{suffix}", name="Synthetic M20 supplier")
                customer = Customer(code=f"M20-S-C-{suffix}", name="Synthetic M20 customer", company_id=company.id)
                product = Product(
                    sku=f"M20-S-FG-{suffix}", name="Dated supply test product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                db.add_all([branch_a, branch_b, supplier, customer, product])
                await db.flush()
                target = Warehouse(
                    code=f"M20-S-A-{suffix}", name="Target MPS warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                    branch_id=branch_a.id,
                )
                other_warehouse = Warehouse(
                    code=f"M20-S-B-{suffix}", name="Other branch warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                    branch_id=branch_b.id,
                )
                db.add_all([target, other_warehouse])
                await db.flush()
                source_run = MRPRun(
                    run_no=f"M20-S-RUN-A-{suffix}", run_date=start, planning_horizon_days=30,
                    status=MRPRunStatus.COMPLETED, include_forecast=False, include_safety_stock=False,
                    warehouse_id=target.id,
                )
                same_warehouse_run = MRPRun(
                    run_no=f"M20-S-RUN-PLAN-A-{suffix}", run_date=start, planning_horizon_days=30,
                    status=MRPRunStatus.COMPLETED, include_forecast=False, include_safety_stock=False,
                    warehouse_id=target.id,
                )
                other_warehouse_run = MRPRun(
                    run_no=f"M20-S-RUN-B-{suffix}", run_date=start, planning_horizon_days=30,
                    status=MRPRunStatus.COMPLETED, include_forecast=False, include_safety_stock=False,
                    warehouse_id=other_warehouse.id,
                )
                recipe = Recipe(
                    product_id=product.id, version=f"M20-{suffix}", name="Synthetic WIP recipe",
                    status=RecipeStatus.DRAFT,
                )
                db.add_all([source_run, same_warehouse_run, other_warehouse_run, recipe])
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-S-PLAN-{suffix}", plan_name="Dated inventory supply projection",
                    plant_code="SHARED-PLANT-CODE", start_date=start, end_date=end,
                    mrp_run_id=source_run.id,
                )
                approved_same_warehouse_plan = MPSPlan(
                    plan_no=f"M20-S-APP-A-{suffix}", plan_name="Approved same-warehouse supply",
                    plant_code="SHARED-PLANT-CODE", start_date=start, end_date=end,
                    mrp_run_id=same_warehouse_run.id, status=MPSStatus.APPROVED,
                )
                approved_other_warehouse_plan = MPSPlan(
                    plan_no=f"M20-S-APP-B-{suffix}", plan_name="Approved other-warehouse supply",
                    plant_code="SHARED-PLANT-CODE", start_date=start, end_date=end,
                    mrp_run_id=other_warehouse_run.id, status=MPSStatus.APPROVED,
                )
                db.add_all([plan, approved_same_warehouse_plan, approved_other_warehouse_plan])
                await db.flush()
                db.add_all([
                    MPSLine(
                        line_no=f"M20-S-L-A-{suffix}", mps_id=approved_same_warehouse_plan.id,
                        product_id=product.id, period_start=start, period_end=date(2026, 1, 4),
                        planned_end_date=start, planned_production_qty=Decimal("3"),
                    ),
                    MPSLine(
                        line_no=f"M20-S-L-B-{suffix}", mps_id=approved_other_warehouse_plan.id,
                        product_id=product.id, period_start=start, period_end=date(2026, 1, 4),
                        planned_end_date=start, planned_production_qty=Decimal("500"),
                    ),
                ])
                db.add_all([
                    Stock(
                        stock_type=StockType.PRODUCT, warehouse_id=target.id, product_id=product.id,
                        quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("4"),
                        quantity_available=Decimal("6"),
                    ),
                    Stock(
                        stock_type=StockType.PRODUCT, warehouse_id=other_warehouse.id, product_id=product.id,
                        quantity_on_hand=Decimal("100"), quantity_reserved=Decimal("0"),
                        quantity_available=Decimal("100"),
                    ),
                ])
                order = SalesOrder(
                    order_no=f"M20-S-SO-{suffix}", customer_id=customer.id,
                    order_date=start, requested_delivery_date=date(2026, 1, 2),
                    status=SOStatus.CONFIRMED, warehouse_id=target.id, company_id=company.id,
                )
                db.add(order)
                await db.flush()
                db.add(SOLine(
                    so_id=order.id, line_no=1, product_id=product.id,
                    ordered_quantity=Decimal("20"), shipped_quantity=Decimal("0"), unit="KG",
                ))
                target_po = PurchaseOrder(
                    po_no=f"M20-S-PO-A-{suffix}", supplier_id=supplier.id,
                    company_id=company.id, branch_id=branch_a.id,
                    order_date=start, expected_delivery_date=date(2026, 1, 4),
                    status=POStatus.ORDERED,
                )
                other_branch_po = PurchaseOrder(
                    po_no=f"M20-S-PO-B-{suffix}", supplier_id=supplier.id,
                    company_id=company.id, branch_id=branch_b.id,
                    order_date=start, expected_delivery_date=start,
                    status=POStatus.ORDERED,
                )
                unassigned_po = PurchaseOrder(
                    po_no=f"M20-S-PO-GLOBAL-{suffix}", supplier_id=supplier.id,
                    company_id=company.id, branch_id=None,
                    order_date=start, expected_delivery_date=start,
                    status=POStatus.APPROVED,
                )
                db.add_all([target_po, other_branch_po, unassigned_po])
                await db.flush()
                db.add_all([
                    POLine(
                        po_id=target_po.id, line_no=1, product_id=product.id,
                        ordered_quantity=Decimal("5000"), received_quantity=Decimal("0"), unit="G",
                    ),
                    POLine(
                        po_id=other_branch_po.id, line_no=1, product_id=product.id,
                        ordered_quantity=Decimal("100"), received_quantity=Decimal("0"), unit="KG",
                    ),
                    POLine(
                        po_id=unassigned_po.id, line_no=1, product_id=product.id,
                        ordered_quantity=Decimal("200"), received_quantity=Decimal("0"), unit="KG",
                    ),
                ])
                conversion = UomConversion(from_uom="G", to_uom="KG", factor=Decimal("0.001"))
                work_order = ProductionOrder(
                    order_no=f"M20-S-WIP-A-{suffix}", product_id=product.id, recipe_id=recipe.id,
                    planned_quantity=Decimal("5"), actual_quantity=Decimal("3"), uom="KG",
                    status=ProductionOrderStatus.IN_PROGRESS, target_warehouse_id=target.id,
                    scheduled_start=datetime(2026, 1, 1, 8), scheduled_end=datetime(2026, 1, 1, 16),
                )
                other_warehouse_work = ProductionOrder(
                    order_no=f"M20-S-WIP-B-{suffix}", product_id=product.id, recipe_id=recipe.id,
                    planned_quantity=Decimal("100"), actual_quantity=Decimal("0"), uom="KG",
                    status=ProductionOrderStatus.IN_PROGRESS, target_warehouse_id=other_warehouse.id,
                    scheduled_start=datetime(2026, 1, 1, 8), scheduled_end=datetime(2026, 1, 1, 16),
                )
                db.add_all([conversion, work_order, other_warehouse_work])
                await db.flush()
                company_id = company.id
                branch_ids = [branch_a.id, branch_b.id]
                warehouse_ids = [target.id, other_warehouse.id]
                supplier_id, product_id, recipe_id, customer_id = supplier.id, product.id, recipe.id, customer.id
                conversion_id = conversion.id
                run_ids = [source_run.id, same_warehouse_run.id, other_warehouse_run.id]
                plan_ids = [plan.id, approved_same_warehouse_plan.id, approved_other_warehouse_plan.id]
                order_ids = [order.id]
                po_ids = [target_po.id, other_branch_po.id, unassigned_po.id]
                production_order_ids = [work_order.id, other_warehouse_work.id]

            async with db.begin():
                result = await project_demand_and_supply(db, plan.id, "WEEKLY")
                assert result["lines_created"] == 1
                assert len(result["excluded_purchase_orders"]) == 2
                excluded_reasons = {item["reason"] for item in result["excluded_purchase_orders"]}
                assert excluded_reasons == {"PURCHASE_ORDER_DESTINATION_AMBIGUOUS"}
                detail = next(item for item in result["supply_breakdown"] if item["period_start"] == start.isoformat())
                assert detail["opening_on_hand_qty"] == "10.000"
                assert detail["opening_reserved_qty"] == "4.000"
                assert detail["opening_available_qty"] == "6.000"
                assert detail["incoming_purchase_order_qty"] == "5.000"
                assert detail["work_in_progress_qty"] == "2.000"
                assert detail["approved_mps_supply_qty"] == "3.000"
                assert detail["planned_production_qty"] == "9.000"
                assert detail["projected_ending_available_qty"] == "5.000"
                assert detail["dated_receipts"] == [
                    {"date": "2026-01-01", "source": "work_in_progress", "quantity": "2.000"},
                    {"date": "2026-01-01", "source": "approved_mps", "quantity": "3.000"},
                    {"date": "2026-01-04", "source": "purchase_order", "quantity": "5.000"},
                ]
                line = (await db.execute(
                    select(MPSLine).where(MPSLine.mps_id == plan.id)
                )).scalar_one()
                assert line.net_requirement_qty == Decimal("9.000")

                invalid_uom_po = PurchaseOrder(
                    po_no=f"M20-S-PO-UOM-{suffix}", supplier_id=supplier.id,
                    company_id=company.id, branch_id=branch_a.id,
                    order_date=start, expected_delivery_date=date(2026, 1, 2),
                    status=POStatus.ORDERED,
                )
                db.add(invalid_uom_po)
                await db.flush()
                invalid_uom_line = POLine(
                    po_id=invalid_uom_po.id, line_no=1, product_id=product.id,
                    ordered_quantity=Decimal("1"), received_quantity=Decimal("0"), unit="CARTON",
                )
                db.add(invalid_uom_line)
                await db.flush()
                po_ids.append(invalid_uom_po.id)
                with pytest.raises(ValueError, match="cannot be converted to product UOM"):
                    await project_demand_and_supply(db, plan.id, "WEEKLY")
                assert (await db.scalar(
                    select(func.count()).select_from(MPSLine).where(MPSLine.mps_id == plan.id)
                )) == 1

                target_stock = (await db.execute(
                    select(Stock).where(Stock.warehouse_id == warehouse_ids[0], Stock.product_id == product.id)
                )).scalar_one()
                target_stock.quantity_available = Decimal("20")
                await db.flush()
                with pytest.raises(ValueError, match="Inventory quantities are inconsistent"):
                    await project_demand_and_supply(db, plan.id, "WEEKLY")
                assert (await db.scalar(
                    select(func.count()).select_from(MPSLine).where(MPSLine.mps_id == plan.id)
                )) == 1

    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if production_order_ids:
                    await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.id.in_(production_order_ids)))
                if po_ids:
                    await cleanup.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(po_ids)))
                if plan_ids:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id.in_(plan_ids)))
                if order_ids:
                    await cleanup.execute(delete(SalesOrder).where(SalesOrder.id.in_(order_ids)))
                if run_ids:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id.in_(run_ids)))
                if product_id is not None:
                    await cleanup.execute(delete(Stock).where(Stock.product_id == product_id))
                if recipe_id is not None:
                    await cleanup.execute(delete(Recipe).where(Recipe.id == recipe_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if conversion_id is not None:
                    await cleanup.execute(delete(UomConversion).where(UomConversion.id == conversion_id))
                if warehouse_ids:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
                if branch_ids:
                    await cleanup.execute(delete(Branch).where(Branch.id.in_(branch_ids)))
                if supplier_id is not None:
                    await cleanup.execute(delete(Supplier).where(Supplier.id == supplier_id))
                if customer_id is not None:
                    await cleanup.execute(delete(Customer).where(Customer.id == customer_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))


@pytest.mark.asyncio
async def test_postgres_seeded_mrp_bom_inventory_diagnostics_snapshot_and_release_replay():
    """Exercise a committed MRP→MPS→BOM/stock→scenario→production path."""
    _require_disposable_m20_postgres()

    await engine.dispose()
    suffix = _suffix()
    company_id = warehouse_id = product_id = material_id = run_id = plan_id = user_id = None
    recipe_id = bom_id = None
    scenario_ids: list = []
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 V03 {suffix}", short_code=f"M20{suffix}")
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-V3-WH-{suffix}", name="M20 V03 acceptance warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                product = Product(
                    sku=f"M20-V3-P-{suffix}", name="M20 V03 test product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                material = Material(
                    code=f"M20-V3-M-{suffix}", name="M20 V03 test material",
                    material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
                )
                user = User(
                    email=f"m20-v3-{suffix}@example.invalid", username=f"m20-v3-{suffix}",
                    full_name="M20 V03 acceptance", hashed_password="test",
                )
                db.add_all([warehouse, product, material, user])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-V3-RUN-{suffix}", run_date=date(2026, 1, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                recipe = Recipe(
                    product_id=product.id, version="1", name="M20 V03 release recipe",
                    status=RecipeStatus.APPROVED, is_active=True,
                )
                bom = AdvancedBOM(
                    bom_code=f"M20-V3-BOM-{suffix}", bom_name="M20 V03 effective BOM",
                    product_id=product.id, base_qty=1, base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED, is_default=True,
                    effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
                )
                db.add_all([run, recipe, bom])
                await db.flush()
                result = MRPResult(
                    run_id=run.id, product_id=product.id,
                    so_demand_qty=Decimal("5"), forecast_demand_qty=Decimal("0"),
                    safety_stock_qty=Decimal("0"), gross_demand_qty=Decimal("5"),
                    stock_on_hand_qty=Decimal("0"), incoming_po_qty=Decimal("0"),
                    incoming_prod_qty=Decimal("0"), total_supply_qty=Decimal("0"),
                    net_requirement_qty=Decimal("5"), shortage_flag=True,
                    suggested_production_qty=Decimal("5"),
                )
                db.add_all([
                    result,
                    AdvancedBOMLine(
                        bom_id=bom.id, line_no=1, item_type=ItemLinkType.MATERIAL,
                        item_id=material.id, required_qty=1, required_uom="KG",
                        basis_type=BasisType.PER_UNIT,
                    ),
                    Stock(
                        stock_type=StockType.MATERIAL, warehouse_id=warehouse.id,
                        material_id=material.id, quantity_on_hand=6,
                        quantity_reserved=0, quantity_available=6,
                    ),
                ])
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-V3-PLAN-{suffix}", plan_name="M20 V03 end-to-end plan",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 30),
                    mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                company_id, warehouse_id = company.id, warehouse.id
                product_id, material_id = product.id, material.id
                run_id, plan_id, user_id = run.id, plan.id, user.id
                recipe_id, bom_id = recipe.id, bom.id

        async with AsyncSessionLocal() as db:
            async with db.begin():
                created = await generate_mps_from_mrp(
                    db, plan_id, GenerateFromMRPRequest(mrp_run_id=run_id, period_type="MONTHLY"),
                )
                assert created == 1
                line = await db.scalar(select(MPSLine).where(MPSLine.mps_id == plan_id))
                assert line is not None and line.mrp_result_id is not None
                assert line.planned_production_qty == Decimal("5.000")
                line_id = line.id

                first_eval = await evaluate_material_feasibility(db, plan_id)
                assert first_eval["lines_evaluated"] == 1
                assert first_eval["feasible_lines"] == 1
                first_diagnostics = await list_plan_diagnostics(db, plan_id)
                assert len(first_diagnostics) == 1
                first_run_id = first_diagnostics[0]["run_id"]
                assert all(row["diagnostics"]["issues"] == [] for row in first_diagnostics)

                second_eval = await evaluate_material_feasibility(db, plan_id)
                second_diagnostics = await list_plan_diagnostics(db, plan_id)
                assert second_eval["feasible_lines"] == 1
                assert len(second_diagnostics) == 2
                assert any(row["run_id"] != first_run_id for row in second_diagnostics)

                baseline = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                    scenario_name="baseline quantity",
                    changes=[WhatIfChange(line_id=line_id, change_type=MPSChangeType.QTY_ADJUST, new_value="5")],
                ), user_id)
                candidate = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                    scenario_name="increased quantity",
                    changes=[WhatIfChange(line_id=line_id, change_type=MPSChangeType.QTY_ADJUST, new_value="10")],
                ), user_id)
                scenario_ids = [baseline.id, candidate.id]
                assert await db.scalar(select(MPSLine.planned_production_qty).where(
                    MPSLine.id == line_id,
                )) == Decimal("5.000"), "what-if must not mutate the live MPS line"

                comparison = await compare_whatif_scenarios(db, plan_id, baseline.id, candidate.id)
                assert comparison["material_shortage_count_delta"] == 1
                assert comparison["cost_delta"] is None
                assert comparison["cost_delta_status"] == "UNKNOWN_NO_APPROVED_CURRENCY_BASIS"
                assert comparison["baseline_version"] == "mps-whatif.v1"
                assert comparison["candidate_version"] == "mps-whatif.v1"

                snapshot_rows = (await db.scalars(select(MPSScenarioSnapshot).where(
                    MPSScenarioSnapshot.scenario_id.in_(scenario_ids),
                ))).all()
                assert len(snapshot_rows) == 2
                snapshots_before = {
                    row.scenario_id: (row.assumptions, row.results) for row in snapshot_rows
                }
                assert snapshots_before[baseline.id][1]["material_shortage_quantity_by_uom"] == {}
                assert snapshots_before[candidate.id][1]["material_shortage_quantity_by_uom"] == {"KG": "4.0000"}

                before_scenario_count = await db.scalar(select(func.count()).select_from(MPSWhatIfScenario))
                try:
                    async with db.begin_nested():
                        rolled_back = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                            scenario_name="rollback scenario",
                            changes=[WhatIfChange(line_id=line_id, change_type=MPSChangeType.QTY_ADJUST, new_value="11")],
                        ), user_id)
                        await db.flush()
                        raise _RollbackFixture()
                except _RollbackFixture:
                    pass
                after_scenario_count = await db.scalar(select(func.count()).select_from(MPSWhatIfScenario))
                assert after_scenario_count == before_scenario_count
                assert await db.get(MPSScenarioSnapshot, rolled_back.id) is None

                plan_status = await approve_mps_plan(db, plan_id, user_id)
                assert plan_status.status == MPSStatus.APPROVED
                released = await release_mps_plan(db, plan_id, user_id, warehouse_id)
                assert released["release_complete"] is True
                assert released["released_orders"] == 1

        async with AsyncSessionLocal() as verify:
            persisted = await list_plan_diagnostics(verify, plan_id)
            assert len(persisted) == 2
            snapshots_after = (await verify.scalars(select(MPSScenarioSnapshot).where(
                MPSScenarioSnapshot.scenario_id.in_(scenario_ids),
            ))).all()
            assert len(snapshots_after) == 2
            assert {
                row.scenario_id: (row.assumptions, row.results) for row in snapshots_after
            } == snapshots_before
            replayed = await compare_whatif_scenarios(verify, plan_id, *scenario_ids)
            assert replayed == comparison
            line = await verify.scalar(select(MPSLine).where(MPSLine.mps_id == plan_id))
            assert line is not None and line.planned_production_qty == Decimal("5.000")
            order = await verify.scalar(select(ProductionOrder).where(ProductionOrder.product_id == product_id))
            assert order is not None and order.recipe_id == recipe_id
            assert order.target_warehouse_id == warehouse_id
            assert order.planned_quantity == Decimal("5.000")
            assert await verify.scalar(text(
                "SELECT COUNT(*) FROM mps_line_diagnostics WHERE mps_id = :plan_id"
            ), {"plan_id": plan_id}) == 2

        # The schema rejects a duplicate snapshot version for the same scenario.
        from sqlalchemy.exc import IntegrityError
        async with AsyncSessionLocal() as db:
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    await db.execute(text("""
                        INSERT INTO mps_scenario_snapshots
                          (id, scenario_id, snapshot_version, assumptions, results)
                        VALUES (:id, :scenario_id, 'mps-whatif.v1', '{}'::jsonb, '{}'::jsonb)
                    """), {"id": uuid4(), "scenario_id": scenario_ids[0]})
            await db.rollback()
        async with AsyncSessionLocal() as verify:
            assert await verify.scalar(select(func.count()).select_from(MPSScenarioSnapshot).where(
                MPSScenarioSnapshot.scenario_id.in_(scenario_ids),
            )) == 2
    finally:
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.product_id == product_id))
                    await cleanup.execute(delete(AuditLog).where(AuditLog.target_id == str(plan_id)))
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if bom_id is not None:
                    await cleanup.execute(delete(AdvancedBOM).where(AdvancedBOM.id == bom_id))
                if recipe_id is not None:
                    await cleanup.execute(delete(Recipe).where(Recipe.id == recipe_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPResult).where(MRPResult.run_id == run_id))
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if material_id is not None:
                    await cleanup.execute(delete(Stock).where(Stock.material_id == material_id))
                    await cleanup.execute(delete(Material).where(Material.id == material_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_release_http_permission_company_warehouse_and_atomic_rollback(monkeypatch):
    """Exercise the real release route's RBAC/scope and DB transaction boundary."""
    _require_disposable_m20_postgres()

    from httpx import ASGITransport, AsyncClient

    from app.core.deps import get_current_user, get_db
    from app.main import app
    from app.models.mps import MPSWhatIfScenario
    from app.models.role import role_permission
    import app.api.v1.endpoints.mps as mps_endpoint

    await engine.dispose()
    suffix = _suffix()
    company_ids: list = []
    warehouse_ids: list = []
    product_ids: list = []
    recipe_ids: list = []
    run_ids: list = []
    plan_ids: list = []
    actor_ids: list = []
    role_id = permission_id = own_permission_id = None
    permission_created = False
    saved_overrides = app.dependency_overrides.copy()
    release_impl = mps_endpoint.release_mps_plan
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company_a = Company(name=f"M20 Scope A {suffix}", short_code=f"MA{suffix}")
                company_b = Company(name=f"M20 Scope B {suffix}", short_code=f"MB{suffix}")
                db.add_all([company_a, company_b])
                await db.flush()
                wh_a = Warehouse(code=f"M20-SCOPE-A-{suffix}", name="M20 scoped A", warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company_a.id)
                wh_b = Warehouse(code=f"M20-SCOPE-B-{suffix}", name="M20 scoped B", warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company_b.id)
                allowed = User(email=f"m20-allowed-{suffix}@example.invalid", username=f"m20-allowed-{suffix}", full_name="M20 Allowed", hashed_password="test")
                denied = User(email=f"m20-denied-{suffix}@example.invalid", username=f"m20-denied-{suffix}", full_name="M20 Denied", hashed_password="test")
                db.add_all([wh_a, wh_b, allowed, denied])
                await db.flush()
                permission = await db.scalar(select(Permission).where(Permission.code == "mps.release"))
                if permission is None:
                    permission = Permission(code="mps.release", name="Release MPS", module="mps", action="release")
                    db.add(permission)
                    await db.flush()
                    permission_created = True
                own_permission = await db.scalar(select(Permission).where(Permission.code == "mps.release_own_scope"))
                own_permission_was_created = own_permission is None
                if own_permission is None:
                    own_permission = Permission(
                        code="mps.release_own_scope", name="Release MPS in own scope",
                        module="mps", action="release_own_scope",
                    )
                    db.add(own_permission)
                    await db.flush()
                role = Role(name=f"M20-release-{suffix}", description="Scoped M20 test permission")
                role.permissions.extend([permission, own_permission])
                role.access_scopes.append(AccessScope(
                    scope_type="warehouse", scope_id=str(wh_a.id),
                    can_view=True, can_release=True,
                ))
                db.add(role)
                await db.flush()
                await db.execute(user_role.insert().values(user_id=allowed.id, role_id=role.id))
                for index, warehouse in enumerate((wh_a, wh_b)):
                    product = Product(
                        sku=f"M20-SCOPE-P-{suffix}-{index}", name=f"M20 scope product {index}",
                        category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                    )
                    db.add(product)
                    await db.flush()
                    recipe = Recipe(
                        product_id=product.id, version="1", name="M20 scope recipe",
                        status=RecipeStatus.APPROVED, is_active=True,
                    )
                    run = MRPRun(
                        run_no=f"M20-SCOPE-RUN-{suffix}-{index}", run_date=date(2026, 1, 1),
                        status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                    )
                    db.add_all([recipe, run])
                    await db.flush()
                    plan = MPSPlan(
                        plan_no=f"M20-SCOPE-PLAN-{suffix}-{index}", plan_name="M20 scope release",
                        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                        status=MPSStatus.APPROVED, mrp_run_id=run.id,
                        approved_by_id=allowed.id,
                    )
                    db.add(plan)
                    await db.flush()
                    for line_index in range(2 if index == 0 else 1):
                        db.add(MPSLine(
                            line_no=f"M20-SCOPE-L-{suffix}-{index}-{line_index}",
                            mps_id=plan.id, product_id=product.id,
                            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                            planned_production_qty=Decimal("3"),
                            feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                        ))
                    await db.flush()
                    company_ids.append(warehouse.company_id)
                    warehouse_ids.append(warehouse.id)
                    product_ids.append(product.id)
                    recipe_ids.append(recipe.id)
                    run_ids.append(run.id)
                    plan_ids.append(plan.id)
                # A second in-scope plan gives the post-flush failure its own
                # untouched records so the route transaction rollback is observable.
                rollback_plan = MPSPlan(
                    plan_no=f"M20-SCOPE-ROLLBACK-{suffix}", plan_name="M20 scoped rollback",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                    status=MPSStatus.APPROVED, mrp_run_id=run_ids[0],
                    approved_by_id=allowed.id,
                )
                db.add(rollback_plan)
                await db.flush()
                db.add(MPSLine(
                    line_no=f"M20-SCOPE-ROLLBACK-L-{suffix}",
                    mps_id=rollback_plan.id, product_id=product_ids[0],
                    period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                    planned_production_qty=Decimal("3"),
                    feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                ))
                await db.flush()
                plan_ids.append(rollback_plan.id)
                concurrent_plan = MPSPlan(
                    plan_no=f"M20-SCOPE-CONCURRENT-{suffix}", plan_name="M20 scoped concurrent release",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                    status=MPSStatus.APPROVED, mrp_run_id=run_ids[0],
                    approved_by_id=allowed.id,
                )
                db.add(concurrent_plan)
                await db.flush()
                for line_index in range(2):
                    db.add(MPSLine(
                        line_no=f"M20-SCOPE-CONCURRENT-L-{suffix}-{line_index}",
                        mps_id=concurrent_plan.id, product_id=product_ids[0],
                        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                        planned_production_qty=Decimal("3"),
                        feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                    ))
                await db.flush()
                plan_ids.append(concurrent_plan.id)
                actor_ids.extend([allowed.id, denied.id])
                role_id, permission_id = role.id, permission.id
                own_permission_id = own_permission.id if own_permission_was_created else None

        async def override_db():
            async with AsyncSessionLocal() as session:
                yield session

        async with AsyncSessionLocal() as auth_db:
            allowed = (await auth_db.execute(select(User).options(
                selectinload(User.access_scopes),
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.access_scopes),
            ).where(User.id == actor_ids[0]))).scalar_one()
            denied = (await auth_db.execute(select(User).options(
                selectinload(User.access_scopes),
                selectinload(User.roles).selectinload(Role.permissions),
            ).where(User.id == actor_ids[1]))).scalar_one()
            current_actor = allowed

            async def override_user():
                return current_actor

            app.dependency_overrides[get_db] = override_db
            app.dependency_overrides[get_current_user] = override_user
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://m20.test",
            ) as client:
                route = f"/api/v1/mps/plans/{plan_ids[0]}/release"
                success = await client.post(route, params={"target_warehouse_id": str(warehouse_ids[0])})
                assert success.status_code == 200, success.text
                first = success.json()
                assert first["released_orders"] == 2 and first["release_complete"] is True

                retry = await client.post(route, params={"target_warehouse_id": str(warehouse_ids[0])})
                assert retry.status_code == 200, retry.text
                assert retry.json()["idempotent_retry"] is True
                assert retry.json()["released_orders"] == first["released_orders"]
                assert retry.json()["release_complete"] is True

                # Two real route requests race for one approved plan. The row
                # lock must serialize them into one release and one verified
                # idempotent retry, with no duplicate production orders.
                concurrent_route = f"/api/v1/mps/plans/{plan_ids[3]}/release"
                concurrent_results = await asyncio.gather(
                    client.post(concurrent_route, params={"target_warehouse_id": str(warehouse_ids[0])}),
                    client.post(concurrent_route, params={"target_warehouse_id": str(warehouse_ids[0])}),
                )
                assert [response.status_code for response in concurrent_results] == [200, 200]
                concurrent_payloads = [response.json() for response in concurrent_results]
                assert sorted(payload["idempotent_retry"] for payload in concurrent_payloads) == [False, True]
                assert all(payload["released_orders"] == 2 for payload in concurrent_payloads)

                wrong_target = await client.post(route, params={"target_warehouse_id": str(warehouse_ids[1])})
                assert wrong_target.status_code == 403

                wrong_source = await client.post(
                    f"/api/v1/mps/plans/{plan_ids[1]}/release",
                    params={"target_warehouse_id": str(warehouse_ids[1])},
                )
                assert wrong_source.status_code == 403

                current_actor = denied
                no_permission = await client.post(route, params={"target_warehouse_id": str(warehouse_ids[0])})
                assert no_permission.status_code == 403

                current_actor = allowed
                async def fail_after_orders(*args, **kwargs):
                    result = await original(*args, **kwargs)
                    assert result["released_orders"] == 1
                    raise RuntimeError("injected post-flush route failure")

                monkeypatch.setattr(mps_endpoint, "release_mps_plan", fail_after_orders)
                rollback_route = f"/api/v1/mps/plans/{plan_ids[2]}/release"
                rollback = await client.post(rollback_route, params={"target_warehouse_id": str(warehouse_ids[0])})
                assert rollback.status_code == 500

        monkeypatch.setattr(mps_endpoint, "release_mps_plan", release_impl)
        async with AsyncSessionLocal() as verify:
            assert await verify.scalar(select(func.count()).select_from(ProductionOrder).where(
                ProductionOrder.product_id == product_ids[0],
            )) == 4
            assert await verify.scalar(select(func.count()).select_from(ProductionOrder).where(
                ProductionOrder.product_id == product_ids[1],
            )) == 0
            assert await verify.scalar(select(func.count()).select_from(ProductionOrder).where(
                ProductionOrder.product_id == product_ids[0],
            )) == 4, "failed second release must roll back its production order"
            assert await verify.scalar(select(MPSPlan.status).where(MPSPlan.id == plan_ids[0])) == MPSStatus.RELEASED
            assert await verify.scalar(select(MPSPlan.status).where(MPSPlan.id == plan_ids[1])) == MPSStatus.APPROVED
            assert await verify.scalar(select(MPSPlan.status).where(MPSPlan.id == plan_ids[2])) == MPSStatus.APPROVED
            released_audit = await verify.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[0]),
                AuditLog.actor_id == actor_ids[0],
            ))
            assert released_audit == 1
            concurrent_audit = await verify.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[3]),
                AuditLog.actor_id == actor_ids[0],
            ))
            assert concurrent_audit == 1
            assert await verify.scalar(select(MPSPlan.status).where(MPSPlan.id == plan_ids[3])) == MPSStatus.RELEASED
    finally:
        monkeypatch.setattr(mps_endpoint, "release_mps_plan", release_impl)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_ids:
                    await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.product_id.in_(product_ids)))
                    await cleanup.execute(delete(AuditLog).where(AuditLog.target_id.in_([str(v) for v in plan_ids if v.int != 0])))
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id.in_(plan_ids)))
                if run_ids:
                    await cleanup.execute(delete(MRPResult).where(MRPResult.run_id.in_(run_ids)))
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id.in_(run_ids)))
                if recipe_ids:
                    await cleanup.execute(delete(Recipe).where(Recipe.id.in_(recipe_ids)))
                if product_ids:
                    await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
                if role_id is not None:
                    await cleanup.execute(delete(AccessScope).where(AccessScope.role_id == role_id))
                    await cleanup.execute(delete(role_permission).where(role_permission.c.role_id == role_id))
                    await cleanup.execute(delete(Role).where(Role.id == role_id))
                if permission_created and permission_id is not None:
                    permission = await cleanup.get(Permission, permission_id)
                    if permission is not None and permission.code == "mps.release":
                        assigned = await cleanup.scalar(select(func.count()).select_from(role_permission).where(
                            role_permission.c.permission_id == permission_id,
                        ))
                        if assigned == 0:
                            await cleanup.delete(permission)
                if own_permission_id is not None:
                    own_permission = await cleanup.get(Permission, own_permission_id)
                    if own_permission is not None:
                        await cleanup.delete(own_permission)
                if actor_ids:
                    await cleanup.execute(delete(User).where(User.id.in_(actor_ids)))
                if warehouse_ids:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
                if company_ids:
                    await cleanup.execute(delete(Company).where(Company.id.in_(company_ids)))
        await engine.dispose()
