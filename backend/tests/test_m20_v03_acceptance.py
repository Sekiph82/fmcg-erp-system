"""PostgreSQL integration coverage added from the M20 strict V03 audit."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
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
from app.models.hr import Employee, EmployeeShiftAssignment, ShiftTemplate
from app.models.inventory import Stock, StockType
from app.models.machine_operator import Machine, MachineFamily, OperatorProfile
from app.models.master import (
    Material, MaterialType, Product, ProductCategory, Supplier, UnitOfMeasure,
    Warehouse, WarehouseType,
)
from app.models.mps import (
    MPSCampaign, MPSCapacityMode, MPSCapacitySlot, MPSChangeType, MPSFeasibilityStatus, MPSLine, MPSPlan, MPSScenarioSnapshot,
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
from app.models.planning import ChangeoverMatrix, ResourceCalendar
from app.models.production_advanced import DowntimeEvent, WorkCenter, WorkCenterStatus, WorkCenterType
from app.models.role import AccessScope, Permission, Role
from app.models.user import User, user_role
from app.models.sales import Customer, SalesOrder, SOStatus, SOLine
from app.schemas.mps import (
    GenerateFromMRPRequest, MPSLineConstraintDiagnosticOut, MPSLineUpdate, MPSWhatIfCreate, WhatIfChange,
)
from app.services.mps_advanced_service import (
    evaluate_material_feasibility, list_plan_diagnostics, project_demand_and_supply,
)
from app.services.mps_capacity_service import run_capacity_scheduling_validated
from app.services.mps_campaign_service import run_campaign_grouping_validated, list_campaigns
from app.services.mps_service import (
    _next_seq, approve_mps_plan, generate_mps_from_mrp, release_mps_plan, update_mps_line,
)
from app.services.mps_whatif_service import (
    _next_scenario_no,
    _apply_change,
    _batch_count_for_quantity,
    _expand_candidate_lines,
    _scenario_changeover_hours,
    _scenario_standard_cost_total,
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


def test_virtual_cost_currency_and_ambiguous_campaign_sequence_remain_unknown():
    product_id = uuid4()
    product = SimpleNamespace(
        id=product_id, sku="SYN-001", category="BEVERAGE",
        standard_cost=Decimal("12.50"), standard_cost_currency="KES",
    )
    lines = [{
        "id": str(uuid4()), "product_id": str(product_id), "work_center_id": str(uuid4()),
        "planned_production_qty": "4", "planned_start_date": "2026-11-03", "planned_end_date": "2026-11-03",
    }]
    total, unknown = _scenario_standard_cost_total(lines, {product_id: product}, "KES")
    assert total == Decimal("50.00") and not unknown
    product.standard_cost_currency = None
    total, unknown = _scenario_standard_cost_total(lines, {product_id: product}, "KES")
    assert total is None and "PRODUCT_STANDARD_COST_CURRENCY_MISSING:SYN-001" in unknown
    product.standard_cost_currency = "USD"
    total, unknown = _scenario_standard_cost_total(lines, {product_id: product}, "KES")
    assert total is None and "PRODUCT_STANDARD_COST_CURRENCY_MISMATCH:SYN-001" in unknown

    work_center_id = uuid4()
    household_id = uuid4()
    first, second = dict(lines[0]), dict(lines[0])
    first["work_center_id"] = second["work_center_id"] = str(work_center_id)
    second["id"], second["product_id"] = str(uuid4()), str(household_id)
    products = {
        product_id: product,
        household_id: SimpleNamespace(id=household_id, sku="SYN-002", category="HOUSEHOLD"),
    }
    transition = SimpleNamespace(
        work_center_id=work_center_id, from_family="BEVERAGE", to_family="HOUSEHOLD",
        changeover_minutes=45, cip_minutes=60, is_active=True,
    )
    same_day = _scenario_changeover_hours([first, second], products, [transition])
    assert same_day["status"] == "PARTIAL_INPUTS"
    assert "CAMPAIGN_SEQUENCE_NOT_CONFIGURED:2026-11-03" in same_day["unknown_reasons"]
    assert not same_day["capacity_loads"]

    first["planned_end_date"] = "2026-11-04"
    second["planned_start_date"] = second["planned_end_date"] = "2026-11-04"
    overlapping = _scenario_changeover_hours([first, second], products, [transition])
    assert overlapping["status"] == "PARTIAL_INPUTS"
    assert any(reason.startswith("CAMPAIGN_WINDOWS_OVERLAP:") for reason in overlapping["unknown_reasons"])
    assert not overlapping["capacity_loads"]


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


def test_shift_add_requires_realistic_non_overlapping_calendar_intervals():
    wc_id = uuid4()
    day = date(2026, 11, 3)
    key = (wc_id, day)
    calendar = SimpleNamespace(
        available_hours=Decimal("8"), is_holiday=False, is_maintenance=False,
        shift_1_start="08:00", shift_1_end="16:00",
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    def added(start_time: str, end_time: str, hours: str) -> dict:
        start_hour, start_minute = (int(part) for part in start_time.split(":"))
        end_hour, end_minute = (int(part) for part in end_time.split(":"))
        return {
            "work_center_id": wc_id, "date": day,
            "start_time": start_time, "end_time": end_time,
            "start_minute": start_hour * 60 + start_minute,
            "end_minute": (24 * 60 if end_time == "00:00" else end_hour * 60 + end_minute),
            "hours": Decimal(hours),
        }

    valid, unknown = _validate_shift_additions(
        [added("00:00", "08:00", "8"), added("16:00", "00:00", "8")], {key: calendar},
    )
    assert valid == {key: Decimal("16")}
    assert not unknown
    with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining"):
        _validate_shift_additions(
            [added("00:00", "08:00", "8"), added("16:00", "00:00", "8.001")], {key: calendar},
        )
    with pytest.raises(ValueError, match="overlaps a configured work-center shift"):
        _validate_shift_additions([added("15:00", "20:00", "5")], {key: calendar})
    with pytest.raises(ValueError, match="intervals overlap"):
        _validate_shift_additions(
            [added("16:00", "20:00", "4"), added("19:00", "23:00", "4")], {key: calendar},
        )

    overlapping = SimpleNamespace(**{
        **calendar.__dict__, "shift_2_start": "15:00", "shift_2_end": "20:00",
    })
    valid, unknown = _validate_shift_additions([added("00:00", "01:00", "1")], {key: overlapping})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_SHIFTS_OVERLAP"}

    valid, unknown = _validate_shift_additions([added("00:00", "01:00", "1")], {})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_NOT_CONFIGURED"}

    no_shift_policy = SimpleNamespace(
        available_hours=Decimal("8"), is_holiday=False, is_maintenance=False,
        shift_1_start=None, shift_1_end=None,
        shift_2_start=None, shift_2_end=None,
        shift_3_start=None, shift_3_end=None,
    )
    valid, unknown = _validate_shift_additions([added("00:00", "01:00", "1")], {key: no_shift_policy})
    assert valid == {}
    assert unknown == {"SHIFT_ADD_CALENDAR_SHIFT_WINDOWS_NOT_CONFIGURED"}

    full_day = SimpleNamespace(
        available_hours=Decimal("24"), is_holiday=False, is_maintenance=False,
        shift_1_start="00:00", shift_1_end="08:00",
        shift_2_start="08:00", shift_2_end="16:00",
        shift_3_start="16:00", shift_3_end="00:00",
    )
    with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining"):
        _validate_shift_additions([added("16:00", "17:00", "1")], {key: full_day})

    downtime = SimpleNamespace(
        work_center_id=wc_id,
        start_time=datetime(2026, 11, 3, 9, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        duration_min=None,
    )
    valid, unknown = _validate_shift_additions([added("16:00", "17:00", "1")], {key: calendar}, [downtime])
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
            changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                "date": day.isoformat(), "start_time": "16:00", "end_time": "18:00", "hours": "2",
            })],
        ), user_id)
        maximum_shift = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
            scenario_name="aggregate shifts stay within daily calendar",
            changes=[
                WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                    "date": day.isoformat(), "start_time": "16:00", "end_time": "20:00", "hours": "4",
                }),
                WhatIfChange(line_id=second_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                    "date": day.isoformat(), "start_time": "20:00", "end_time": "00:00", "hours": "4",
                }),
            ],
        ), user_id)
        with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining work-center calendar hours"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="aggregate shift exceeds physical day",
                changes=[
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                        "date": day.isoformat(), "start_time": "16:00", "end_time": "00:00", "hours": "8",
                    }),
                    WhatIfChange(line_id=second_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                        "date": day.isoformat(), "start_time": "00:00", "end_time": "09:00", "hours": "9",
                    }),
                ],
            ), user_id)
        full_day_calendar = await db.scalar(select(ResourceCalendar).where(
            ResourceCalendar.work_center_id == work_center.id,
            ResourceCalendar.calendar_date == day,
        ))
        assert full_day_calendar is not None
        full_day_calendar.available_hours = 24
        full_day_calendar.shift_1_start, full_day_calendar.shift_1_end = "00:00", "08:00"
        full_day_calendar.shift_2_start, full_day_calendar.shift_2_end = "08:00", "16:00"
        full_day_calendar.shift_3_start, full_day_calendar.shift_3_end = "16:00", "00:00"
        await db.flush()
        with pytest.raises(ValueError, match="Aggregate SHIFT_ADD hours exceed remaining work-center calendar hours"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="aggregate additions rejected after a full-day calendar",
                changes=[
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                        "date": day.isoformat(), "start_time": "00:00", "end_time": "01:00", "hours": "1",
                    }),
                    WhatIfChange(line_id=second_id, change_type=MPSChangeType.SHIFT_ADD, new_value={
                        "date": day.isoformat(), "start_time": "01:00", "end_time": "02:00", "hours": "1",
                    }),
                ],
            ), user_id)
        full_day_calendar.available_hours = 8
        full_day_calendar.shift_1_start, full_day_calendar.shift_1_end = "08:00", "16:00"
        full_day_calendar.shift_2_start = full_day_calendar.shift_2_end = None
        full_day_calendar.shift_3_start = full_day_calendar.shift_3_end = None
        await db.flush()
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
        source_run = MRPRun(
            run_no=f"M20-OPS-SOURCE-{suffix}", run_date=day,
            status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
        )
        db.add(source_run)
        await db.flush()
        source_result = MRPResult(run_id=source_run.id, product_id=product.id)
        db.add(source_result)
        await db.flush()
        second_line.mrp_result_id = source_result.id
        await db.flush()
        with pytest.raises(ValueError, match="matching source allocation, product, batch, campaign"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="incompatible MRP source merge",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
            ), user_id)
        second_line.mrp_result_id = None
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
        with pytest.raises(ValueError, match="MERGE/SPLIT lines cannot have conflicting scenario changes"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="reject chained merge of consumed lines",
                changes=[
                    WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id)),
                    WhatIfChange(line_id=second_id, change_type=MPSChangeType.MERGE, new_value=str(first_id)),
                ],
            ), user_id)
        second_line.is_locked = True
        await db.flush()
        with pytest.raises(ValueError, match="What-if MERGE cannot target a locked MPS line"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="reject locked merge source",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
            ), user_id)
        second_line.is_locked = False
        await db.flush()
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
            {
                "work_center_id": str((await db.get(MPSLine, first_id)).work_center_id),
                "date": day.isoformat(), "start_time": "16:00", "end_time": "20:00", "hours": "4",
            },
            {
                "work_center_id": str((await db.get(MPSLine, second_id)).work_center_id),
                "date": day.isoformat(), "start_time": "20:00", "end_time": "00:00", "hours": "4",
            },
        ]
        assert by_scenario[shifted.id].assumptions["shift_additions"] == [
            {
                "work_center_id": str((await db.get(MPSLine, first_id)).work_center_id),
                "date": day.isoformat(), "start_time": "16:00", "end_time": "18:00", "hours": "2",
            },
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
    assert fixture["virtual_assumptions"]["source"] == "OWNER_AUTHORIZED_SYNTHETIC_DEMO_ASSUMPTIONS"
    assert fixture["virtual_assumptions"]["not_operational_data"] is True
    assert all("minimum_run_qty" in product and "standard_cost_currency" in product for product in fixture["products"])
    assert fixture["virtual_assumptions"]["changeover_rules"][0]["cip_minutes"] > 0
    staffing = fixture["virtual_assumptions"]["staffing_assumption"]
    assert staffing["not_operational_data"] is True
    assert staffing["operators_per_filling_machine"] == len(staffing["employees"]) == 2
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
                    category=ProductCategory[mango["category"]], uom=UnitOfMeasure[mango["uom"]],
                    minimum_run_qty=mango["minimum_run_qty"], standard_cost=mango["standard_cost"],
                    standard_cost_currency=mango["standard_cost_currency"],
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
    changeover_day = capacity_day + timedelta(days=6)
    mismatch_day = capacity_day + timedelta(days=7)
    company_id = warehouse_id = product_id = run_id = plan_id = work_center_id = second_work_center_id = conversion_id = None
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
                second_work_center = WorkCenter(
                    work_center_id=f"M20-CAP-WC2-{suffix}", name="Synthetic mismatched campaign member center",
                    type=WorkCenterType.LINE, capacity=Decimal("10000"), capacity_uom="G/HR",
                )
                db.add_all([company, warehouse, product, work_center, second_work_center])
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
                    ResourceCalendar(
                        work_center_id=work_center.id, calendar_date=changeover_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="16:00",
                    ),
                    ResourceCalendar(
                        work_center_id=second_work_center.id, calendar_date=mismatch_day, available_hours=8,
                        shift_1_start="08:00", shift_1_end="16:00",
                    ),
                    ChangeoverMatrix(
                        work_center_id=work_center.id, from_family="FOOD", to_family="FOOD",
                        changeover_minutes=30, is_active=True,
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
                    start_date=capacity_day, end_date=mismatch_day, mrp_run=run,
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
                changeover = MPSLine(
                    line_no=f"M20-CAP-CHANGEOVER-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=changeover_day, period_end=changeover_day,
                    planned_start_date=changeover_day, planned_end_date=changeover_day,
                    planned_production_qty=10, work_center_id=work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                mismatched_member = MPSLine(
                    line_no=f"M20-CAP-CAMPAIGN-MISMATCH-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=mismatch_day, period_end=mismatch_day,
                    planned_start_date=mismatch_day, planned_end_date=mismatch_day,
                    planned_production_qty=10, work_center_id=second_work_center.id,
                    feasibility_status=MPSFeasibilityStatus.PENDING,
                )
                db.add_all([
                    locked, concurrent, maintenance, invalid_shift, attribution_locked,
                    attribution_unlocked, overnight, invalid_downtime, bad_date, negative, changeover,
                    mismatched_member,
                ])
                await db.flush()
                overnight_campaign = MPSCampaign(
                    campaign_code=f"M20-CAP-CAMP1-{suffix}", campaign_name="Synthetic preceding campaign",
                    mps_id=plan.id, work_center_id=work_center.id,
                    campaign_start=overnight_day, campaign_end=overnight_day, sequence_order=1,
                )
                changeover_campaign = MPSCampaign(
                    campaign_code=f"M20-CAP-CAMP2-{suffix}", campaign_name="Synthetic successor campaign",
                    mps_id=plan.id, work_center_id=work_center.id,
                    campaign_start=changeover_day, campaign_end=changeover_day,
                    sequence_order=2, total_changeover_hrs=Decimal("9.000"),
                )
                db.add_all([overnight_campaign, changeover_campaign])
                await db.flush()
                overnight.campaign_id = overnight_campaign.id
                changeover.campaign_id = changeover_campaign.id
                await db.flush()
                company_id, warehouse_id, product_id = company.id, warehouse.id, product.id
                run_id, plan_id, work_center_id, conversion_id = run.id, plan.id, work_center.id, conversion.id
                second_work_center_id = second_work_center.id
                locked_id, concurrent_id, maintenance_id = locked.id, concurrent.id, maintenance.id
                invalid_shift_id = invalid_shift.id
                attribution_locked_id, attribution_unlocked_id = attribution_locked.id, attribution_unlocked.id
                overnight_id = overnight.id
                invalid_downtime_id = invalid_downtime.id
                bad_date_id, negative_id = bad_date.id, negative.id
            changeover_id = changeover.id
            mismatched_member_id = mismatched_member.id

            result = await run_capacity_scheduling_validated(db, plan_id)
            assert result["mode"] == "FINITE"
            assert result["overloaded_lines"] == 5
            slots = (await db.scalars(select(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id))).all()
            slots_by_day = {slot.slot_date: slot for slot in slots}
            assert set(slots_by_day) == {
                capacity_day, maintenance_day, invalid_shift_day, attribution_day, overnight_day,
                invalid_downtime_day, changeover_day, mismatch_day,
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
            assert slots_by_day[changeover_day].allocated_hours == Decimal("1.500")
            assert slots_by_day[changeover_day].overload_hours == Decimal("0.000")
            assert (await db.get(MPSLine, locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert (await db.get(MPSLine, concurrent_id)).required_hours == Decimal("6.000")
            assert (await db.get(MPSLine, concurrent_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, maintenance_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, invalid_shift_id)).feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert (await db.get(MPSLine, attribution_locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert (await db.get(MPSLine, attribution_unlocked_id)).feasibility_status == MPSFeasibilityStatus.OVERLOADED
            assert (await db.get(MPSLine, overnight_id)).feasibility_status == MPSFeasibilityStatus.FEASIBLE
            assert (await db.get(MPSLine, changeover_id)).feasibility_status == MPSFeasibilityStatus.PENDING
            assert (await db.get(MPSLine, invalid_downtime_id)).feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            diagnostics = await list_plan_diagnostics(db, plan_id)
            by_line = {uuid.UUID(row["line_id"]): row for row in diagnostics}
            capacity_rows = [row for row in diagnostics if row["source_version"] == "mps-capacity.v1"]
            line_count = len((await db.scalars(select(MPSLine).where(MPSLine.mps_id == plan_id))).all())
            assert len(capacity_rows) == line_count
            assert {row["run_id"] for row in capacity_rows} == {result["diagnostic_run_id"]}
            assert all(row["diagnostics"]["evaluation_kind"] == "CAPACITY" for row in capacity_rows)
            assert all(row["diagnostics"]["recalculation_state"] == "CURRENT" for row in capacity_rows)
            assert all(row["diagnostics"]["scenario_provenance"] == "BASE_PLAN" for row in capacity_rows)
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
            slot_overload = next(
                issue for issue in by_line[attribution_unlocked_id]["diagnostics"]["issues"]
                if issue["reason_code"] == "CAPACITY_OVERLOAD"
            )
            matching_slot = slots_by_day[attribution_day]
            assert slot_overload["capacity_slot_id"] == str(matching_slot.id)
            assert slot_overload["capacity_slot_key"] == f"{work_center_id}:{attribution_day.isoformat()}"
            assert slot_overload["slot_required_hours"] == str(matching_slot.allocated_hours)
            assert slot_overload["net_available_hours"] == str(matching_slot.available_hours - matching_slot.downtime_hours)
            assert str(attribution_locked_id) in slot_overload["affected_line_ids"]
            assert str(attribution_unlocked_id) in slot_overload["affected_line_ids"]
            capacity_api = MPSLineConstraintDiagnosticOut.model_validate(by_line[attribution_unlocked_id])
            capacity_api_issue = next(
                issue for issue in capacity_api.diagnostics.issues
                if issue.reason_code == "CAPACITY_OVERLOAD"
            )
            assert capacity_api_issue.capacity_slot_id == matching_slot.id
            assert set(capacity_api_issue.affected_line_ids) >= {attribution_locked_id, attribution_unlocked_id}

            # Re-running the same capacity calculation replaces slot rows,
            # preserves the previous diagnostic run as superseded history,
            # and publishes one new current run without duplicate line rows.
            first_capacity_slot_values = {
                (slot.work_center_id, slot.slot_date): (
                    slot.available_hours, slot.allocated_hours, slot.downtime_hours, slot.overload_hours,
                ) for slot in slots
            }
            repeat_result = await run_capacity_scheduling_validated(db, plan_id)
            assert repeat_result["diagnostic_run_id"] != result["diagnostic_run_id"]
            repeated_slots = (await db.scalars(select(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id))).all()
            assert {
                (slot.work_center_id, slot.slot_date): (
                    slot.available_hours, slot.allocated_hours, slot.downtime_hours, slot.overload_hours,
                ) for slot in repeated_slots
            } == first_capacity_slot_values
            repeat_rows = [row for row in await list_plan_diagnostics(db, plan_id) if row["source_version"] == "mps-capacity.v1"]
            assert len(repeat_rows) == line_count * 2
            assert all(
                row["diagnostics"]["recalculation_state"] == (
                    "CURRENT" if row["run_id"] == repeat_result["diagnostic_run_id"] else "SUPERSEDED"
                ) for row in repeat_rows
            )
            assert all(
                row["diagnostics"].get("superseded_by_run_id") == repeat_result["diagnostic_run_id"]
                for row in repeat_rows if row["run_id"] == result["diagnostic_run_id"]
            )
            superseded_api = MPSLineConstraintDiagnosticOut.model_validate(
                next(row for row in repeat_rows if row["run_id"] == result["diagnostic_run_id"])
            )
            assert superseded_api.diagnostics.superseded_by_run_id == uuid.UUID(repeat_result["diagnostic_run_id"])
            changeover_diagnostic = by_line[changeover_id]["diagnostics"]
            applied_setup = next(
                issue for issue in changeover_diagnostic["issues"]
                if issue["reason_code"] == "CHANGEOVER_CAPACITY_APPLIED"
            )
            assert applied_setup["duration_minutes"] == 30
            assert Decimal(applied_setup["changeover_hours"]) == Decimal("0.500")
            assert applied_setup["capacity_date"] == changeover_day.isoformat()
            assert "CIP_NOT_CONFIGURED" in changeover_diagnostic["reason_codes"]
            assert changeover_campaign.total_changeover_hrs == Decimal("9.000")

            matrix = (await db.scalars(select(ChangeoverMatrix).where(
                ChangeoverMatrix.work_center_id == work_center.id,
                ChangeoverMatrix.from_family == "FOOD",
                ChangeoverMatrix.to_family == "FOOD",
            ))).one()
            matrix.is_active = False
            await db.flush()
            missing_config_run = await run_capacity_scheduling_validated(db, plan_id)
            missing_config_slots = (await db.scalars(
                select(MPSCapacitySlot).where(
                    MPSCapacitySlot.mps_id == plan_id,
                    MPSCapacitySlot.work_center_id == work_center.id,
                    MPSCapacitySlot.slot_date == changeover_day,
                )
            )).all()
            assert len(missing_config_slots) == 1
            assert missing_config_slots[0].allocated_hours == Decimal("1.000")
            missing_config_diagnostic = next(
                row["diagnostics"] for row in await list_plan_diagnostics(db, plan_id)
                if row["run_id"] == missing_config_run["diagnostic_run_id"]
                and uuid.UUID(row["line_id"]) == changeover_id
            )
            assert "CHANGEOVER_NOT_CONFIGURED" in missing_config_diagnostic["reason_codes"]
            assert "CHANGEOVER_CAPACITY_APPLIED" not in missing_config_diagnostic["reason_codes"]
            matrix.is_active = True
            await db.flush()

            # A malformed middle campaign on another work center must block
            # the declared center's transition chain instead of being skipped.
            mismatched_campaign = MPSCampaign(
                campaign_code=f"M20-CAP-CAMP-MISMATCH-{suffix}", campaign_name="Synthetic mismatched campaign",
                mps_id=plan_id, work_center_id=work_center.id,
                campaign_start=mismatch_day - timedelta(days=1),
                campaign_end=mismatch_day - timedelta(days=1), sequence_order=2,
            )
            changeover_campaign.sequence_order = 3
            db.add(mismatched_campaign)
            await db.flush()
            mismatched_member.campaign_id = mismatched_campaign.id
            await db.flush()
            mismatch_run = await run_capacity_scheduling_validated(db, plan_id)
            mismatch_slots = (await db.scalars(
                select(MPSCapacitySlot).where(
                    MPSCapacitySlot.mps_id == plan_id,
                    MPSCapacitySlot.work_center_id == work_center.id,
                    MPSCapacitySlot.slot_date == changeover_day,
                )
            )).all()
            assert len(mismatch_slots) == 1
            assert mismatch_slots[0].allocated_hours == Decimal("1.000")
            latest_mismatch_rows = [
                row for row in await list_plan_diagnostics(db, plan_id)
                if row["run_id"] == mismatch_run["diagnostic_run_id"]
            ]
            mismatch_diagnostic = next(
                row["diagnostics"] for row in latest_mismatch_rows
                if uuid.UUID(row["line_id"]) == changeover_id
            )
            assert "CHANGEOVER_CAPACITY_APPLIED" not in mismatch_diagnostic["reason_codes"]
            assert "CHANGEOVER_SEQUENCE_INVALID" in mismatch_diagnostic["reason_codes"]
            member_diagnostic = next(
                row["diagnostics"] for row in latest_mismatch_rows
                if uuid.UUID(row["line_id"]) == mismatched_member_id
            )
            sequence_issue = next(
                issue for issue in member_diagnostic["issues"]
                if issue["reason_code"] == "CHANGEOVER_SEQUENCE_INVALID"
            )
            assert str(work_center.id) in sequence_issue["work_center_ids"]
            assert str(second_work_center_id) in sequence_issue["work_center_ids"]

            mismatched_member.campaign_id = None
            await db.delete(mismatched_campaign)
            work_center.status = WorkCenterStatus.INACTIVE
            await db.flush()
            inactive_run = await run_capacity_scheduling_validated(db, plan_id)
            assert await db.scalar(select(func.count()).select_from(MPSCapacitySlot).where(
                MPSCapacitySlot.mps_id == plan_id,
                MPSCapacitySlot.work_center_id == work_center.id,
                MPSCapacitySlot.slot_date == changeover_day,
            )) == 0
            inactive_diagnostic = next(
                row["diagnostics"] for row in await list_plan_diagnostics(db, plan_id)
                if row["run_id"] == inactive_run["diagnostic_run_id"]
                and uuid.UUID(row["line_id"]) == changeover_id
            )
            assert "WORK_CENTER_INACTIVE" in inactive_diagnostic["reason_codes"]
            assert "CHANGEOVER_CAPACITY_APPLIED" not in inactive_diagnostic["reason_codes"]

            plan = await db.get(MPSPlan, plan_id)
            plan.capacity_mode = MPSCapacityMode.INFINITE
            await db.flush()
            infinite_result = await run_capacity_scheduling_validated(db, plan_id)
            assert infinite_result["mode"] == "INFINITE"
            assert infinite_result["recalculation_state"] == "NOT_APPLICABLE"
            after_infinite = [row for row in await list_plan_diagnostics(db, plan_id) if row["source_version"] == "mps-capacity.v1"]
            assert all(
                row["diagnostics"]["recalculation_state"] == (
                    "NOT_APPLICABLE" if row["run_id"] == inactive_run["diagnostic_run_id"] else "SUPERSEDED"
                ) for row in after_infinite
            )
            assert (await db.get(MPSLine, locked_id)).feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert await db.scalar(select(func.count()).select_from(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id)) == 0
            plan.capacity_mode = MPSCapacityMode.FINITE
            work_center.status = WorkCenterStatus.ACTIVE
            await db.flush()
            restored_finite = await run_capacity_scheduling_validated(db, plan_id)
            after_restored_finite = [
                row for row in await list_plan_diagnostics(db, plan_id)
                if row["source_version"] == "mps-capacity.v1"
            ]
            assert all(
                row["diagnostics"]["recalculation_state"] == (
                    "CURRENT" if row["run_id"] == restored_finite["diagnostic_run_id"] else "SUPERSEDED"
                ) for row in after_restored_finite
            )
            assert all(
                row["diagnostics"]["superseded_by_run_id"] == restored_finite["diagnostic_run_id"]
                for row in after_restored_finite if row["run_id"] == inactive_run["diagnostic_run_id"]
            )
            assert await db.scalar(select(func.count()).select_from(MPSCapacitySlot).where(MPSCapacitySlot.mps_id == plan_id)) > 0
    finally:
        await engine.dispose()
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if work_center_id is not None:
                    work_center_ids = [work_center_id]
                    if second_work_center_id is not None:
                        work_center_ids.append(second_work_center_id)
                    await cleanup.execute(delete(DowntimeEvent).where(DowntimeEvent.work_center_id.in_(work_center_ids)))
                    await cleanup.execute(delete(ResourceCalendar).where(ResourceCalendar.work_center_id.in_(work_center_ids)))
                    await cleanup.execute(delete(WorkCenter).where(WorkCenter.id.in_(work_center_ids)))
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
                await db.flush()
                inactive_safety_product.is_active = False
                await db.flush()
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
                assert comparison["material_status"] == "COMPLETE"
                assert comparison["material_shortage_quantity_by_uom_delta"] == {"KG": "4.0000"}
                assert comparison["service_level_unit"] == "percentage_points"
                assert comparison["delay_count_unit"] == "lines"
                assert comparison["capacity_unit"] == "hours"
                assert comparison["changeover_unit"] == "hours"
                assert comparison["cost_delta"] is None
                assert comparison["cost_delta_status"] == "UNKNOWN_COST_OR_CURRENCY_BASIS"
                assert comparison["confidence_status"] == "PARTIAL_INPUTS"
                assert "COST_BASIS_OR_COMPANY_CURRENCY_NOT_CONFIGURED" in comparison["unknowns"]
                assert not any(reason.startswith("CIP_") for reason in comparison["unknowns"])
                assert comparison["metric_sources"]["material_shortages"].endswith("grouped by source UOM")
                assert comparison["baseline_version"] == "mps-whatif.v1"
                assert comparison["candidate_version"] == "mps-whatif.v1"

                snapshot_rows = (await db.scalars(select(MPSScenarioSnapshot).where(
                    MPSScenarioSnapshot.scenario_id.in_(scenario_ids),
                ))).all()
                assert len(snapshot_rows) == 2
                assert baseline.created_by_id == user_id
                assert candidate.created_by_id == user_id
                assert {row.created_by_id for row in snapshot_rows} == {user_id}
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
async def test_postgres_virtual_factory_minimum_run_cip_capacity_and_kes_costing():
    """Exercise owner-authorized synthetic assumptions through real MPS services."""
    _require_disposable_m20_postgres()
    await engine.dispose()
    suffix = _suffix()
    day_one = date(2026, 11, 3)
    day_two = date(2026, 11, 4)
    company_id = warehouse_id = run_id = plan_id = work_center_id = None
    product_ids: list[uuid.UUID] = []
    user_id = None
    employee_ids: list[uuid.UUID] = []
    operator_profile_ids: list[uuid.UUID] = []
    shift_template_id = machine_id = None
    fixture = json.loads((Path(__file__).parent / "fixtures" / "m20_acceptance_dataset.json").read_text(encoding="utf-8"))
    staffing = fixture["virtual_assumptions"]["staffing_assumption"]
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(
                    name=f"Synthetic Nairobi Foods {suffix}", short_code=f"SYN{suffix[:8]}",
                    country="Kenya", base_currency="KES",
                )
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"NBO-DEMO-{suffix}", name="Synthetic finished goods warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                beverage = Product(
                    sku=f"JU-MNG-500-{suffix}", name="Synthetic mango drink 500 ml",
                    category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS,
                    minimum_run_qty=250, standard_cost=Decimal("42.5000"), standard_cost_currency="KES",
                )
                detergent = Product(
                    sku=f"DET-1L-{suffix}", name="Synthetic dish liquid 1 L",
                    category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS,
                    minimum_run_qty=180, standard_cost=Decimal("68.0000"), standard_cost_currency="KES",
                )
                center = WorkCenter(
                    work_center_id=f"FILL-DEMO-{suffix}", name="Synthetic shared filling line",
                    type=WorkCenterType.LINE, capacity=60, capacity_uom="PCS/HR",
                    status=WorkCenterStatus.ACTIVE,
                )
                user = User(
                    email=f"planner-{suffix}@example.invalid", username=f"planner-{suffix}",
                    full_name="Synthetic Planner", hashed_password="synthetic-test-only",
                )
                db.add_all([warehouse, beverage, detergent, center, user])
                await db.flush()
                machine = Machine(
                    machine_code=f"M20-FILLER-{suffix}", machine_name="Synthetic filling machine",
                    machine_family=MachineFamily.FILLING, work_center_id=center.id,
                    rated_capacity_per_hour=60, capacity_uom="PCS/HR",
                    labor_requirement_standard=staffing["operators_per_filling_machine"],
                    notes="Owner-authorized synthetic fixture only; not an installed machine.",
                )
                shift_template = ShiftTemplate(
                    name=f"FILL-01 synthetic day {suffix}",
                    start_time=time(7, 0), end_time=time(15, 0),
                    department="Production", company_id=company.id,
                    notes="Synthetic acceptance shift only; not a live roster.",
                )
                synthetic_employees = [
                    Employee(
                        employee_code=f"{entry['employee_code']}-{suffix}",
                        full_name=entry["name"], department="Production", role=entry["role"],
                        hire_date=date(2025, 1, 1), company_id=company.id,
                    )
                    for entry in staffing["employees"]
                ]
                db.add_all([machine, shift_template, *synthetic_employees])
                await db.flush()
                synthetic_operators = [
                    OperatorProfile(
                        operator_code=f"{employee.employee_code}-PROFILE",
                        employee_id=employee.id, full_name=employee.full_name,
                        department="Production", primary_work_center_id=center.id,
                        primary_machine_id=machine.id,
                        notes="Synthetic acceptance operator only; no real employee identity.",
                    )
                    for employee in synthetic_employees
                ]
                db.add_all(synthetic_operators)
                db.add_all([
                    EmployeeShiftAssignment(
                        employee_id=employee.id, company_id=company.id,
                        shift_template_id=shift_template.id,
                        effective_from=day_one, effective_to=day_two,
                        notes="Synthetic M20 acceptance roster only; not an operating schedule.",
                    )
                    for employee in synthetic_employees
                ])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-VIRTUAL-RUN-{suffix}", run_date=day_one,
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-VIRTUAL-PLAN-{suffix}",
                    plan_name="Owner-authorized synthetic FMCG acceptance plan",
                    start_date=day_one, end_date=day_two, capacity_mode=MPSCapacityMode.FINITE,
                    mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                first = MPSLine(
                    line_no=f"M20-VIRTUAL-BEV-{suffix}", mps_id=plan.id, product_id=beverage.id,
                    period_start=day_one, period_end=day_one, planned_start_date=day_one,
                    planned_end_date=day_one, planned_production_qty=300,
                    required_hours=Decimal("5"), work_center_id=center.id,
                )
                second = MPSLine(
                    line_no=f"M20-VIRTUAL-HOUSE-{suffix}", mps_id=plan.id, product_id=detergent.id,
                    period_start=day_two, period_end=day_two, planned_start_date=day_two,
                    planned_end_date=day_two, planned_production_qty=120,
                    required_hours=Decimal("2"), work_center_id=center.id,
                )
                db.add_all([
                    first, second,
                    ResourceCalendar(
                        work_center_id=center.id, calendar_date=day_one, available_hours=8,
                        shift_1_start="07:00", shift_1_end="15:00",
                    ),
                    ResourceCalendar(
                        work_center_id=center.id, calendar_date=day_two, available_hours=8,
                        shift_1_start="07:00", shift_1_end="15:00",
                    ),
                    ChangeoverMatrix(
                        work_center_id=center.id, from_family="BEVERAGE", to_family="HOUSEHOLD",
                        changeover_minutes=45, cip_minutes=60,
                        notes="Synthetic demo assumption only; not factory operating data.",
                    ),
                ])
                await db.flush()
                company_id, warehouse_id, run_id = company.id, warehouse.id, run.id
                plan_id, work_center_id = plan.id, center.id
                product_ids = [beverage.id, detergent.id]
                user_id = user.id
                employee_ids = [employee.id for employee in synthetic_employees]
                operator_profile_ids = [operator.id for operator in synthetic_operators]
                shift_template_id, machine_id = shift_template.id, machine.id
                first_id, second_id = first.id, second.id

            campaign = await run_campaign_grouping_validated(db, plan_id)
            assert campaign["campaigns_created"] == 2
            assert machine.labor_requirement_standard == Decimal(str(staffing["operators_per_filling_machine"]))
            assert await db.scalar(select(func.count()).select_from(OperatorProfile).where(
                OperatorProfile.id.in_(operator_profile_ids),
                OperatorProfile.primary_work_center_id == work_center_id,
            )) == staffing["operators_per_filling_machine"]
            assert await db.scalar(select(func.count()).select_from(EmployeeShiftAssignment).where(
                EmployeeShiftAssignment.employee_id.in_(employee_ids),
                EmployeeShiftAssignment.shift_template_id == shift_template_id,
            )) == staffing["operators_per_filling_machine"]
            campaign_rows = await list_campaigns(db, plan_id)
            assert sorted(row.total_changeover_hrs for row in campaign_rows) == [Decimal("0.000"), Decimal("0.750")]
            diagnostics = await list_plan_diagnostics(db, plan_id)
            by_line = {uuid.UUID(row["line_id"]): row["diagnostics"] for row in diagnostics}
            assert "MINIMUM_RUN_CONFIGURED" in by_line[first_id]["reason_codes"]
            assert "MINIMUM_RUN_NOT_MET" in by_line[second_id]["reason_codes"]
            assert "CIP_CONFIGURED" in by_line[second_id]["reason_codes"]
            assert "CIP_NOT_CONFIGURED" in by_line[first_id]["reason_codes"]

            await run_capacity_scheduling_validated(db, plan_id)
            slots = (await db.scalars(select(MPSCapacitySlot).where(
                MPSCapacitySlot.mps_id == plan_id,
                MPSCapacitySlot.work_center_id == work_center_id,
                MPSCapacitySlot.slot_date == day_two,
            ))).all()
            assert len(slots) == 1
            assert slots[0].allocated_hours == Decimal("3.750"), "2 production hours + 45-minute setup + 60-minute CIP"
            capacity_rows = await list_plan_diagnostics(db, plan_id)
            capacity_diagnostic = next(
                row["diagnostics"] for row in capacity_rows
                if row["source_version"] == "mps-capacity.v1" and uuid.UUID(row["line_id"]) == second_id
            )
            applied_cip = next(issue for issue in capacity_diagnostic["issues"] if issue["reason_code"] == "CIP_CAPACITY_APPLIED")
            assert applied_cip["duration_minutes"] == 60
            assert applied_cip["capacity_date"] == day_two.isoformat()

            baseline = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name=f"synthetic KES baseline {suffix}",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.QTY_ADJUST, new_value="300")],
            ), user_id)
            candidate = await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name=f"synthetic KES candidate {suffix}",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.QTY_ADJUST, new_value="400")],
            ), user_id)
            assert baseline.impact_cost_delta == Decimal("0.0000")
            assert baseline.impact_cost_currency == "KES"
            assert candidate.impact_cost_delta == Decimal("4250.0000")
            assert candidate.impact_cost_currency == "KES"
            comparison = await compare_whatif_scenarios(db, plan_id, baseline.id, candidate.id)
            assert comparison["cost_delta"] == 4250.0
            assert comparison["cost_currency"] == "KES"
            assert comparison["cost_delta_status"] == "COMPLETE"
            assert comparison["changeover_unit"] == "hours"
            assert comparison["cip_status"] == "COMPLETE"
            assert comparison["cip_hours_delta"] == 0.0
            assert comparison["confidence_status"] == "PARTIAL_INPUTS", "missing BOM remains explicitly unknown"

            snapshot = await db.scalar(select(MPSScenarioSnapshot).where(
                MPSScenarioSnapshot.scenario_id == candidate.id,
            ))
            assert snapshot is not None
            assert snapshot.assumptions["cost_basis"]["currency"] == "KES"
            assert snapshot.assumptions["cost_basis"]["fx_policy"] == "same-currency base-currency values only; no FX conversion"
            assert snapshot.results["cip_hours"] == 1.0
            assert snapshot.results["cost_delta_status"] == "COMPLETE"

            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(Product(
                        sku=f"INVALID-MIN-{suffix}", name="Invalid synthetic product",
                        category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS, minimum_run_qty=0,
                    ))
                    await db.flush()
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(Product(
                        sku=f"INVALID-CURRENCY-{suffix}", name="Invalid synthetic product",
                        category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS,
                        standard_cost=Decimal("10"), standard_cost_currency="kes",
                    ))
                    await db.flush()
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(ChangeoverMatrix(
                        work_center_id=work_center_id, from_family="INVALID", to_family="NEGATIVE",
                        changeover_minutes=0, cip_minutes=-1,
                    ))
                    await db.flush()
    finally:
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if operator_profile_ids:
                    await cleanup.execute(delete(OperatorProfile).where(OperatorProfile.id.in_(operator_profile_ids)))
                if machine_id is not None:
                    await cleanup.execute(delete(Machine).where(Machine.id == machine_id))
                if employee_ids:
                    await cleanup.execute(delete(EmployeeShiftAssignment).where(EmployeeShiftAssignment.employee_id.in_(employee_ids)))
                    await cleanup.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
                if shift_template_id is not None:
                    await cleanup.execute(delete(ShiftTemplate).where(ShiftTemplate.id == shift_template_id))
                if work_center_id is not None:
                    await cleanup.execute(delete(ChangeoverMatrix).where(ChangeoverMatrix.work_center_id == work_center_id))
                    await cleanup.execute(delete(ResourceCalendar).where(ResourceCalendar.work_center_id == work_center_id))
                    await cleanup.execute(delete(WorkCenter).where(WorkCenter.id == work_center_id))
                if product_ids:
                    await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_whatif_http_permissions_scope_lifecycle_and_comparison():
    """Exercise scenario API serialization, auth/scope gates, persistence, and rollback."""
    _require_disposable_m20_postgres()

    from httpx import ASGITransport, AsyncClient

    from app.core.deps import get_current_user, get_db
    from app.main import app

    await engine.dispose()
    suffix = _suffix()
    saved_overrides = app.dependency_overrides.copy()
    plan_id = foreign_plan_id = user_id = warehouse_id = run_id = product_id = company_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"Synthetic what-if company {suffix}", short_code=f"WIF{suffix[:8]}", base_currency="KES")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-WHATIF-HTTP-WH-{suffix}", name="Synthetic what-if API warehouse",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                product = Product(
                    sku=f"M20-WHATIF-HTTP-P-{suffix}", name="Synthetic what-if API product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                    standard_cost=Decimal("2.5000"), standard_cost_currency="KES",
                )
                user = User(
                    email=f"m20-whatif-http-{suffix}@example.invalid",
                    username=f"m20-whatif-http-{suffix}", full_name="M20 What-If API Actor",
                    hashed_password="test-only", is_superuser=True,
                )
                db.add_all([warehouse, product, user])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-WHATIF-HTTP-RUN-{suffix}", run_date=date(2026, 10, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add(run)
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-WHATIF-HTTP-PLAN-{suffix}", plan_name="Synthetic what-if API plan",
                    start_date=date(2026, 10, 1), end_date=date(2026, 10, 31), mrp_run_id=run.id,
                )
                foreign_plan = MPSPlan(
                    plan_no=f"M20-WHATIF-HTTP-FOREIGN-{suffix}", plan_name="Synthetic foreign scenario plan",
                    start_date=date(2026, 10, 1), end_date=date(2026, 10, 31), mrp_run_id=run.id,
                )
                db.add_all([plan, foreign_plan])
                await db.flush()
                db.add_all([
                    MPSLine(
                        line_no=f"M20-WHATIF-HTTP-L-{suffix}", mps_id=plan.id, product_id=product.id,
                        period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                        planned_production_qty=Decimal("5"),
                    ),
                    MPSLine(
                        line_no=f"M20-WHATIF-HTTP-FL-{suffix}", mps_id=foreign_plan.id, product_id=product.id,
                        period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                        planned_production_qty=Decimal("5"),
                    ),
                ])
                await db.flush()
                plan_id, foreign_plan_id = plan.id, foreign_plan.id
                user_id, warehouse_id, run_id, product_id, company_id = user.id, warehouse.id, run.id, product.id, company.id

        async def override_db():
            async with AsyncSessionLocal() as session:
                yield session

        async with AsyncSessionLocal() as auth_db:
            principal = await auth_db.get(User, user_id)
        current_actor = principal

        async def override_user():
            return current_actor

        async def get_scenario_line_id(target_plan_id):
            async with AsyncSessionLocal() as db:
                return await db.scalar(select(MPSLine.id).where(MPSLine.mps_id == target_plan_id))

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://m20-whatif.test",
        ) as client:
            route = f"/api/v1/mps/plans/{plan_id}/whatif"
            line_id = await get_scenario_line_id(plan_id)
            invalid = await client.post(route, json={
                "scenario_name": "invalid quantity",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "abc"}],
            })
            assert invalid.status_code == 400, invalid.text
            async with AsyncSessionLocal() as verify:
                assert await verify.scalar(select(func.count()).select_from(MPSWhatIfScenario).where(
                    MPSWhatIfScenario.mps_id == plan_id,
                )) == 0

            baseline = await client.post(route, json={
                "scenario_name": "HTTP baseline",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "5"}],
            })
            assert baseline.status_code == 201, baseline.text
            assert baseline.json()["created_by_id"] == str(user_id)
            assert baseline.json()["impact_cost_currency"] == "KES"
            candidate = await client.post(route, json={
                "scenario_name": "HTTP candidate",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "10"}],
            })
            assert candidate.status_code == 201, candidate.text
            assert candidate.json()["impact_cost_currency"] == "KES"

            foreign_line_id = await get_scenario_line_id(foreign_plan_id)
            foreign = await client.post(f"/api/v1/mps/plans/{foreign_plan_id}/whatif", json={
                "scenario_name": "HTTP foreign scenario",
                "changes": [{"line_id": str(foreign_line_id), "change_type": "QTY_ADJUST", "new_value": "6"}],
            })
            assert foreign.status_code == 201, foreign.text

            listed = await client.get(route)
            assert listed.status_code == 200, listed.text
            assert {scenario["id"] for scenario in listed.json()} == {baseline.json()["id"], candidate.json()["id"]}
            detail = await client.get(f"/api/v1/mps/whatif/{baseline.json()['id']}")
            assert detail.status_code == 200, detail.text
            assert detail.json()["scenario_name"] == "HTTP baseline"
            assert detail.json()["impact_cost_currency"] == "KES"
            assert all(item["impact_cost_currency"] == "KES" for item in listed.json())

            compare_route = f"/api/v1/mps/plans/{plan_id}/scenario-comparison"
            comparison = await client.get(compare_route, params={
                "baseline_id": baseline.json()["id"],
                "candidate_id": candidate.json()["id"],
            })
            assert comparison.status_code == 200, comparison.text
            comparison_payload = comparison.json()
            assert comparison_payload["service_level_unit"] == "percentage_points"
            assert comparison_payload["capacity_unit"] == "hours"
            assert comparison_payload["changeover_unit"] == "hours"
            assert comparison_payload["cost_delta"] == 12.5
            assert comparison_payload["cost_currency"] == "KES"

            cross_plan = await client.get(compare_route, params={
                "baseline_id": baseline.json()["id"],
                "candidate_id": foreign.json()["id"],
            })
            assert cross_plan.status_code == 400, cross_plan.text

            current_actor = SimpleNamespace(
                is_superuser=False,
                id=user_id,
                roles=[SimpleNamespace(is_active=True, permissions=[
                    SimpleNamespace(code="mps.simulate", is_active=True),
                    SimpleNamespace(code="mps.edit_own_scope", is_active=True),
                ])],
                access_scopes=[SimpleNamespace(
                    scope_type="warehouse", scope_id=str(warehouse_id), is_active=True, can_edit=True,
                )],
            )
            scoped_create = await client.post(route, json={
                "scenario_name": "in-scope planner scenario",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "7"}],
            })
            assert scoped_create.status_code == 201, scoped_create.text
            assert scoped_create.json()["created_by_id"] == str(user_id)

            current_actor = SimpleNamespace(
                is_superuser=False,
                id=user_id,
                roles=[SimpleNamespace(is_active=True, permissions=[
                    SimpleNamespace(code="mps.simulate", is_active=True),
                ])],
                access_scopes=[],
            )
            out_of_scope = await client.post(route, json={
                "scenario_name": "out-of-scope scenario",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "7"}],
            })
            assert out_of_scope.status_code == 403
            current_actor = SimpleNamespace(
                is_superuser=False,
                roles=[SimpleNamespace(is_active=True, permissions=[
                    SimpleNamespace(code="mps.view", is_active=True),
                ])],
                access_scopes=[SimpleNamespace(
                    scope_type="warehouse", scope_id=str(warehouse_id), is_active=True, can_edit=True,
                )],
            )
            missing_simulate_permission = await client.post(route, json={
                "scenario_name": "missing simulate permission",
                "changes": [{"line_id": str(line_id), "change_type": "QTY_ADJUST", "new_value": "7"}],
            })
            assert missing_simulate_permission.status_code == 403
            current_actor = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
            missing_view_permission = await client.get(route)
            assert missing_view_permission.status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None or foreign_plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(
                        MPSPlan.id.in_([value for value in (plan_id, foreign_plan_id) if value is not None]),
                    ))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_mps_approval_reopen_and_release_integrity():
    """Exercise approval prerequisites, blocked-line repair, release integrity and immutability."""
    _require_disposable_m20_postgres()
    await engine.dispose()

    suffix = _suffix()
    company_id = warehouse_id = alternate_warehouse_id = work_center_id = actor_id = None
    product_id = recipe_id = run_id = plan_id = None
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                company = Company(name=f"M20 lifecycle {suffix}", short_code=f"ML{suffix}")
                db.add(company)
                await db.flush()
                warehouse = Warehouse(
                    code=f"M20-LIFE-{suffix}", name="Synthetic lifecycle source",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                alternate_warehouse = Warehouse(
                    code=f"M20-LIFE-X-{suffix}", name="Synthetic alternate target",
                    warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
                )
                actor = User(
                    email=f"m20-lifecycle-{suffix}@example.invalid",
                    username=f"m20-lifecycle-{suffix}", full_name="M20 Lifecycle Actor",
                    hashed_password="test",
                )
                product = Product(
                    sku=f"M20-LIFE-P-{suffix}", name="Synthetic lifecycle product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                work_center = WorkCenter(
                    work_center_id=f"M20-LIFE-WC-{suffix}", name="Synthetic lifecycle line",
                    type=WorkCenterType.LINE, capacity=Decimal("100"), capacity_uom="KG/HR",
                )
                db.add_all([warehouse, alternate_warehouse, actor, product, work_center])
                await db.flush()
                db.add(ResourceCalendar(
                    work_center_id=work_center.id, calendar_date=date(2026, 10, 1),
                    available_hours=8, shift_1_start="08:00", shift_1_end="16:00",
                ))
                await db.flush()
                recipe = Recipe(
                    product_id=product.id, version="1", name="Synthetic approved recipe",
                    status=RecipeStatus.APPROVED, is_active=True,
                )
                run = MRPRun(
                    run_no=f"M20-LIFE-RUN-{suffix}", run_date=date(2026, 10, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                db.add_all([recipe, run])
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-LIFE-PLAN-{suffix}", plan_name="Synthetic lifecycle plan",
                    start_date=date(2026, 10, 1), end_date=date(2026, 10, 31),
                    status=MPSStatus.DRAFT, mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                company_id, warehouse_id = company.id, warehouse.id
                alternate_warehouse_id = alternate_warehouse.id
                work_center_id = work_center.id
                actor_id, product_id = actor.id, product.id
                recipe_id, run_id, plan_id = recipe.id, run.id, plan.id

                with pytest.raises(ValueError, match="at least one positive production line"):
                    await approve_mps_plan(db, plan.id, actor.id)
                assert plan.status == MPSStatus.DRAFT

                feasible_line = MPSLine(
                    line_no=f"M20-LIFE-L1-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=date(2026, 10, 1), period_end=date(2026, 10, 15),
                    planned_start_date=date(2026, 10, 1), planned_end_date=date(2026, 10, 1),
                    work_center_id=work_center.id, planned_production_qty=Decimal("300"),
                    feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                )
                blocked_line = MPSLine(
                    line_no=f"M20-LIFE-L2-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=date(2026, 10, 16), period_end=date(2026, 10, 31),
                    planned_start_date=date(2026, 10, 1), planned_end_date=date(2026, 10, 1),
                    work_center_id=work_center.id, planned_production_qty=Decimal("1000"),
                    feasibility_status=MPSFeasibilityStatus.MATERIAL_SHORT,
                )
                db.add_all([feasible_line, blocked_line])
                await db.flush()
                with pytest.raises(ValueError, match="Every positive production line must be FEASIBLE"):
                    await approve_mps_plan(db, plan.id, actor.id)
                assert plan.status == MPSStatus.DRAFT
                blocked_line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
                await db.flush()
                await approve_mps_plan(db, plan.id, actor.id)
                assert plan.status == MPSStatus.APPROVED
                assert plan.approved_by_id == actor.id and plan.approved_at is not None
                assert await update_mps_line(
                    db, plan.id, uuid4(), MPSLineUpdate(remarks="missing line"), actor.id,
                ) is None
                assert plan.status == MPSStatus.APPROVED and plan.approved_by_id == actor.id
                with pytest.raises(ValueError, match="At least one editable MPS line field"):
                    await update_mps_line(db, plan.id, feasible_line.id, MPSLineUpdate(), actor.id)
                assert await update_mps_line(
                    db, plan.id, feasible_line.id,
                    MPSLineUpdate(planned_production_qty=feasible_line.planned_production_qty), actor.id,
                ) is feasible_line
                assert plan.status == MPSStatus.APPROVED and plan.approved_by_id == actor.id

                # Simulate persisted feasibility drift after approval. Release
                # must fail closed, and an authenticated edit must revoke that
                # approval before the draft can be recalculated and reapproved.
                blocked_line.feasibility_status = MPSFeasibilityStatus.OVERLOADED
                await db.flush()
                blocked_release = await release_mps_plan(db, plan.id, actor.id, warehouse.id)
                assert blocked_release["released_orders"] == 0
                assert blocked_release["skipped_ineligible"] == 1
                assert blocked_release["release_complete"] is False
                assert plan.status == MPSStatus.APPROVED
                assert await db.scalar(select(func.count()).select_from(ProductionOrder).where(
                    ProductionOrder.product_id == product.id,
                )) == 0

                await update_mps_line(
                    db, plan.id, blocked_line.id,
                    MPSLineUpdate(
                        planned_production_qty=Decimal("300"),
                        remarks="Re-evaluate and obtain approval again",
                    ), actor.id,
                )
                assert plan.status == MPSStatus.DRAFT
                assert plan.approved_by_id is None and plan.approved_at is None
                assert blocked_line.is_locked is False
                reopen_event = await db.scalar(select(func.count()).select_from(AuditLog).where(
                    AuditLog.event_type == "MPS_PLAN_REOPENED_FOR_EDIT",
                    AuditLog.target_id == str(plan.id), AuditLog.actor_id == actor.id,
                ))
                assert reopen_event == 1

                # Capacity re-evaluation must be able to clear the overload on
                # the repaired line before approval is restored.
                capacity = await run_capacity_scheduling_validated(db, plan.id)
                assert capacity["overloaded_lines"] == 0
                assert blocked_line.feasibility_status == MPSFeasibilityStatus.FEASIBLE
                await approve_mps_plan(db, plan.id, actor.id)
                assert plan.status == MPSStatus.APPROVED

                # ON_HOLD lines are engine-protected. The authenticated
                # planner must explicitly clear the hold, which invalidates
                # approval and unlocks the line for feasibility recalculation.
                feasible_line.feasibility_status = MPSFeasibilityStatus.ON_HOLD
                feasible_line.is_locked = True
                await db.flush()
                with pytest.raises(ValueError, match="explicitly cleared"):
                    await update_mps_line(
                        db, plan.id, feasible_line.id,
                        MPSLineUpdate(remarks="cannot edit a held line directly"), actor.id,
                    )
                assert feasible_line.feasibility_status == MPSFeasibilityStatus.ON_HOLD
                await update_mps_line(
                    db, plan.id, feasible_line.id, MPSLineUpdate(clear_hold=True), actor.id,
                )
                assert plan.status == MPSStatus.DRAFT
                assert plan.approved_by_id is None and plan.approved_at is None
                assert feasible_line.feasibility_status == MPSFeasibilityStatus.PENDING
                assert feasible_line.is_locked is False
                hold_clear_event = await db.scalar(select(func.count()).select_from(AuditLog).where(
                    AuditLog.event_type == "MPS_LINE_HOLD_CLEARED",
                    AuditLog.target_id == str(feasible_line.id), AuditLog.actor_id == actor.id,
                ))
                assert hold_clear_event == 1
                capacity = await run_capacity_scheduling_validated(db, plan.id)
                assert capacity["overloaded_lines"] == 0
                assert feasible_line.feasibility_status == MPSFeasibilityStatus.FEASIBLE
                await approve_mps_plan(db, plan.id, actor.id)
                assert plan.status == MPSStatus.APPROVED
                reopen_events = await db.scalar(select(func.count()).select_from(AuditLog).where(
                    AuditLog.event_type == "MPS_PLAN_REOPENED_FOR_EDIT",
                    AuditLog.target_id == str(plan.id), AuditLog.actor_id == actor.id,
                ))
                assert reopen_events == 2

                # A positive line already linked to an order must block a new
                # release regardless of target; silently skipping it would
                # permit a mixed-target or partial release.
                prelinked_order = ProductionOrder(
                    order_no=f"PO-M20-PRELINK-{suffix}", product_id=product.id,
                    recipe_id=recipe.id, planned_quantity=feasible_line.planned_production_qty,
                    uom="KG", status=ProductionOrderStatus.PLANNED,
                    target_warehouse_id=alternate_warehouse.id,
                    scheduled_start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    scheduled_end=datetime(2026, 10, 15, tzinfo=timezone.utc), created_by=actor.id,
                )
                db.add(prelinked_order)
                await db.flush()
                feasible_line.production_order_id = prelinked_order.id
                await db.flush()
                with pytest.raises(ValueError, match="already contains production-order links"):
                    await release_mps_plan(db, plan.id, actor.id, warehouse.id)
                assert plan.status == MPSStatus.APPROVED and plan.released_at is None
                assert await db.scalar(select(func.count()).select_from(ProductionOrder).where(
                    ProductionOrder.product_id == product.id,
                )) == 1

                feasible_line.production_order_id = None
                await db.delete(prelinked_order)
                await db.flush()
                released = await release_mps_plan(db, plan.id, actor.id, warehouse.id)
                assert released["release_complete"] is True
                assert released["released_orders"] == 2
                assert plan.status == MPSStatus.RELEASED and plan.released_at is not None
                released_ids = set(released["production_order_ids"])
                retry = await release_mps_plan(db, plan.id, actor.id, warehouse.id)
                assert retry["idempotent_retry"] is True
                assert set(retry["production_order_ids"]) == released_ids
                assert await db.scalar(select(func.count()).select_from(ProductionOrder).where(
                    ProductionOrder.product_id == product.id,
                )) == 2

                with pytest.raises(ValueError, match="Only unreleased DRAFT or APPROVED MPS plans can be edited"):
                    await update_mps_line(
                        db, plan.id, feasible_line.id, MPSLineUpdate(remarks="must remain immutable"), actor.id,
                    )
                with pytest.raises(ValueError, match="DRAFT plans"):
                    await generate_mps_from_mrp(
                        db, plan.id, GenerateFromMRPRequest(mrp_run_id=run.id, period_type="MONTHLY"),
                    )
                release_events = await db.scalar(select(func.count()).select_from(AuditLog).where(
                    AuditLog.event_type == "MPS_PLAN_RELEASED",
                    AuditLog.target_id == str(plan.id), AuditLog.actor_id == actor.id,
                ))
                assert release_events == 1
    finally:
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(ProductionOrder).where(ProductionOrder.product_id == product_id))
                    if actor_id is not None:
                        await cleanup.execute(delete(AuditLog).where(AuditLog.actor_id == actor_id))
                    await cleanup.execute(delete(AuditLog).where(AuditLog.target_id == str(plan_id)))
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if recipe_id is not None:
                    await cleanup.execute(delete(Recipe).where(Recipe.id == recipe_id))
                if run_id is not None:
                    await cleanup.execute(delete(MRPRun).where(MRPRun.id == run_id))
                if product_id is not None:
                    await cleanup.execute(delete(Product).where(Product.id == product_id))
                if actor_id is not None:
                    await cleanup.execute(delete(User).where(User.id == actor_id))
                if alternate_warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == alternate_warehouse_id))
                if warehouse_id is not None:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id == warehouse_id))
                if company_id is not None:
                    await cleanup.execute(delete(Company).where(Company.id == company_id))
                if work_center_id is not None:
                    await cleanup.execute(delete(ResourceCalendar).where(ResourceCalendar.work_center_id == work_center_id))
                    await cleanup.execute(delete(WorkCenter).where(WorkCenter.id == work_center_id))
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
    permission_created = approval_permission_created = approve_own_permission_created = False
    approval_permission_id = approve_own_permission_id = None
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
                approval_permission = await db.scalar(select(Permission).where(Permission.code == "mps.approve"))
                if approval_permission is None:
                    approval_permission = Permission(code="mps.approve", name="Approve MPS", module="mps", action="approve")
                    db.add(approval_permission)
                    await db.flush()
                    approval_permission_created = True
                approve_own_permission = await db.scalar(select(Permission).where(Permission.code == "mps.approve_own_scope"))
                approve_own_permission_was_created = approve_own_permission is None
                if approve_own_permission is None:
                    approve_own_permission = Permission(
                        code="mps.approve_own_scope", name="Approve MPS in own scope",
                        module="mps", action="approve_own_scope",
                    )
                    db.add(approve_own_permission)
                    await db.flush()
                    approve_own_permission_created = True
                role = Role(name=f"M20-release-{suffix}", description="Scoped M20 test permissions")
                role.permissions.extend([permission, own_permission, approval_permission, approve_own_permission])
                role.access_scopes.append(AccessScope(
                    scope_type="warehouse", scope_id=str(wh_a.id),
                    can_view=True, can_approve=True, can_release=True,
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
                approval_plan = MPSPlan(
                    plan_no=f"M20-SCOPE-APPROVE-{suffix}", plan_name="M20 scoped approval",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
                    status=MPSStatus.DRAFT, mrp_run_id=run_ids[0],
                )
                db.add(approval_plan)
                await db.flush()
                db.add(MPSLine(
                    line_no=f"M20-SCOPE-APPROVE-L-{suffix}",
                    mps_id=approval_plan.id, product_id=product_ids[0],
                    period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                    planned_production_qty=Decimal("3"),
                    feasibility_status=MPSFeasibilityStatus.FEASIBLE,
                ))
                await db.flush()
                approval_plan_id = approval_plan.id
                plan_ids.append(approval_plan.id)
                actor_ids.extend([allowed.id, denied.id])
                role_id, permission_id = role.id, permission.id
                own_permission_id = own_permission.id if own_permission_was_created else None
                approval_permission_id = approval_permission.id
                approve_own_permission_id = approve_own_permission.id if approve_own_permission_was_created else None

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

                approve_route = f"/api/v1/mps/plans/{approval_plan_id}/approve"
                current_actor = denied
                no_approve_permission = await client.patch(approve_route)
                assert no_approve_permission.status_code == 403

                current_actor = allowed
                wrong_approval_scope = await client.patch(f"/api/v1/mps/plans/{plan_ids[1]}/approve")
                assert wrong_approval_scope.status_code == 403

                approved_response = await client.patch(approve_route)
                assert approved_response.status_code == 200, approved_response.text
                assert approved_response.json()["status"] == MPSStatus.APPROVED.value

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
            failed_release_audit = await verify.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[2]),
            ))
            assert failed_release_audit == 0, "rolled-back release must not retain an audit event"
            released_audit = await verify.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[0]),
                AuditLog.actor_id == actor_ids[0],
            ))
            assert released_audit == 1
            release_event = await verify.scalar(select(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[0]),
                AuditLog.actor_id == actor_ids[0],
            ))
            assert release_event is not None
            assert release_event.actor_email == f"m20-allowed-{suffix}@example.invalid"
            assert release_event.created_at is not None
            assert release_event.before_value["status"] == MPSStatus.APPROVED.value
            assert release_event.after_value["status"] == MPSStatus.RELEASED.value
            assert release_event.details["target_warehouse_id"] == str(warehouse_ids[0])
            concurrent_audit = await verify.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_RELEASED",
                AuditLog.target_id == str(plan_ids[3]),
                AuditLog.actor_id == actor_ids[0],
            ))
            assert concurrent_audit == 1
            assert await verify.scalar(select(MPSPlan.status).where(MPSPlan.id == plan_ids[3])) == MPSStatus.RELEASED
            approved_plan = await verify.get(MPSPlan, approval_plan_id)
            assert approved_plan is not None
            assert approved_plan.status == MPSStatus.APPROVED
            assert approved_plan.approved_by_id == actor_ids[0]
            assert approved_plan.approved_at is not None
            approval_audit = await verify.scalar(select(AuditLog).where(
                AuditLog.event_type == "MPS_PLAN_APPROVED",
                AuditLog.target_id == str(approval_plan_id),
            ))
            assert approval_audit is not None
            assert approval_audit.actor_id == actor_ids[0]
            assert approval_audit.actor_email == f"m20-allowed-{suffix}@example.invalid"
            assert approval_audit.created_at is not None
            assert approval_audit.before_value["status"] == MPSStatus.DRAFT.value
            assert approval_audit.after_value["status"] == MPSStatus.APPROVED.value
            assert approval_audit.after_value["approved_by_id"] == str(actor_ids[0])
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
                if approval_permission_created and approval_permission_id is not None:
                    permission = await cleanup.get(Permission, approval_permission_id)
                    if permission is not None and permission.code == "mps.approve":
                        assigned = await cleanup.scalar(select(func.count()).select_from(role_permission).where(
                            role_permission.c.permission_id == approval_permission_id,
                        ))
                        if assigned == 0:
                            await cleanup.delete(permission)
                if own_permission_id is not None:
                    own_permission = await cleanup.get(Permission, own_permission_id)
                    if own_permission is not None:
                        await cleanup.delete(own_permission)
                if approve_own_permission_id is not None:
                    approve_own_permission = await cleanup.get(Permission, approve_own_permission_id)
                    if approve_own_permission is not None:
                        await cleanup.delete(approve_own_permission)
                if actor_ids:
                    await cleanup.execute(delete(User).where(User.id.in_(actor_ids)))
                if warehouse_ids:
                    await cleanup.execute(delete(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
                if company_ids:
                    await cleanup.execute(delete(Company).where(Company.id.in_(company_ids)))
        await engine.dispose()


@pytest.mark.asyncio
async def test_campaign_grouping_is_stable_and_fails_closed_on_invalid_scope():
    """Exercise grouping using test-only synthetic masters in disposable PostgreSQL."""
    _require_disposable_m20_postgres()
    await engine.dispose()
    suffix = _suffix()
    first_day = date(2026, 11, 1)
    plan_id = None
    product_ids: list[uuid.UUID] = []
    work_center_ids: list[uuid.UUID] = []
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                products = [
                    Product(sku=f"M20-CAMP-{letter}-{suffix}", name=f"Synthetic campaign {letter}",
                            category=category, uom=UnitOfMeasure.KG, is_active=active)
                    for letter, category, active in (
                        ("A", ProductCategory.FOOD, True),
                        ("B", ProductCategory.BEVERAGE, True),
                        ("C", ProductCategory.HOUSEHOLD, True),
                        ("D", ProductCategory.FOOD, True),
                        ("E", ProductCategory.PERSONAL_CARE, True),
                        ("INACTIVE", ProductCategory.FOOD, True),
                    )
                ]
                db.add_all(products)
                await db.flush()
                product_by_letter = dict(zip(("A", "B", "C", "D", "E", "INACTIVE"), products))
                active_wc = WorkCenter(
                    work_center_id=f"M20-CAMP-WC-{suffix}", name="Synthetic active campaign center",
                    type=WorkCenterType.LINE, status=WorkCenterStatus.ACTIVE,
                )
                second_active_wc = WorkCenter(
                    work_center_id=f"M20-CAMP-WC2-{suffix}", name="Synthetic second campaign center",
                    type=WorkCenterType.LINE, status=WorkCenterStatus.ACTIVE,
                )
                unanchored_wc = WorkCenter(
                    work_center_id=f"M20-CAMP-WC3-{suffix}", name="Synthetic unanchored-lock campaign center",
                    type=WorkCenterType.LINE, status=WorkCenterStatus.ACTIVE,
                )
                ambiguous_wc = WorkCenter(
                    work_center_id=f"M20-CAMP-WC4-{suffix}", name="Synthetic ambiguous-lock campaign center",
                    type=WorkCenterType.LINE, status=WorkCenterStatus.ACTIVE,
                )
                inactive_wc = WorkCenter(
                    work_center_id=f"M20-CAMP-WCI-{suffix}", name="Synthetic inactive campaign center",
                    type=WorkCenterType.LINE, status=WorkCenterStatus.INACTIVE,
                )
                db.add_all([active_wc, second_active_wc, unanchored_wc, ambiguous_wc, inactive_wc])
                await db.flush()
                plan = MPSPlan(
                    plan_no=f"M20-OPS-PLAN-CAMP-{suffix}", plan_name="Synthetic campaign grouping plan",
                    start_date=first_day, end_date=first_day + timedelta(days=20), status=MPSStatus.DRAFT,
                )
                db.add(plan)
                await db.flush()
                locked_campaign = MPSCampaign(
                    campaign_code=f"M20-CAMP-LOCK-{suffix}", campaign_name="Synthetic locked campaign",
                    mps_id=plan.id, work_center_id=active_wc.id, campaign_start=first_day,
                    campaign_end=first_day, sequence_order=4, sku_count=1,
                )
                stale_campaign = MPSCampaign(
                    campaign_code=f"M20-CAMP-STALE-{suffix}", campaign_name="Synthetic stale campaign",
                    mps_id=plan.id, work_center_id=active_wc.id, campaign_start=first_day,
                    campaign_end=first_day, sequence_order=8, sku_count=1,
                )
                later_locked_campaign = MPSCampaign(
                    campaign_code=f"M20-CAMP-LOCK2-{suffix}", campaign_name="Synthetic later locked campaign",
                    mps_id=plan.id, work_center_id=second_active_wc.id,
                    campaign_start=first_day + timedelta(days=10), campaign_end=first_day + timedelta(days=10),
                    sequence_order=5, sku_count=1,
                )
                ambiguous_locked_campaign = MPSCampaign(
                    campaign_code=f"M20-CAMP-LOCK3-{suffix}", campaign_name="Synthetic ambiguous locked campaign",
                    mps_id=plan.id, work_center_id=ambiguous_wc.id,
                    campaign_start=first_day + timedelta(days=18), campaign_end=first_day + timedelta(days=18),
                    sequence_order=6, sku_count=1,
                )
                db.add_all([locked_campaign, stale_campaign, later_locked_campaign, ambiguous_locked_campaign])
                # Synthetic rows prove active transition lookup and date-window gating only.
                db.add_all([
                    ChangeoverMatrix(
                        work_center_id=active_wc.id, from_family="FOOD", to_family="HOUSEHOLD",
                        changeover_minutes=20, is_active=True,
                    ),
                    ChangeoverMatrix(
                        work_center_id=active_wc.id, from_family="FOOD", to_family="FOOD",
                        changeover_minutes=15, is_active=True,
                    ),
                    ChangeoverMatrix(
                        work_center_id=active_wc.id, from_family="HOUSEHOLD", to_family="BEVERAGE",
                        changeover_minutes=30, is_active=True,
                    ),
                    ChangeoverMatrix(
                        work_center_id=active_wc.id, from_family="BEVERAGE", to_family="FOOD",
                        changeover_minutes=-15, is_active=True,
                    ),
                    ChangeoverMatrix(
                        work_center_id=active_wc.id, from_family="beverage", to_family="food",
                        changeover_minutes=10, is_active=True,
                    ),
                    ChangeoverMatrix(
                        work_center_id=second_active_wc.id, from_family="PERSONAL_CARE",
                        to_family="BEVERAGE", changeover_minutes=12, is_active=True,
                    ),
                ])
                await db.flush()

                def make_line(label, product, start, end, **values):
                    return MPSLine(
                        line_no=f"M20-CAMP-{label}-{suffix}", mps_id=plan.id, product_id=product.id,
                        period_start=first_day + timedelta(days=start),
                        period_end=first_day + timedelta(days=end),
                        planned_production_qty=values.pop("quantity", Decimal("10")),
                        required_hours=values.pop("hours", Decimal("1")),
                        work_center_id=values.pop("work_center_id", active_wc.id),
                        batch_size_qty=values.pop("batch_size", None),
                        num_batches=values.pop("num_batches", None),
                        priority_score=values.pop("priority_score", Decimal("50")), **values,
                    )

                locked = make_line("LOCKED", product_by_letter["A"], 0, 0,
                                   campaign_id=locked_campaign.id, is_locked=True,
                                   feasibility_status=MPSFeasibilityStatus.ON_HOLD)
                locked2 = make_line("LOCKED2", product_by_letter["B"], 10, 10,
                                     work_center_id=second_active_wc.id,
                                     campaign_id=later_locked_campaign.id, is_locked=True,
                                     feasibility_status=MPSFeasibilityStatus.ON_HOLD)
                a1 = make_line("A1", product_by_letter["A"], 1, 1, quantity=Decimal("20"),
                               batch_size=Decimal("10"), num_batches=2)
                a2 = make_line("A2", product_by_letter["A"], 2, 2, quantity=Decimal("30"),
                               batch_size=Decimal("10"), num_batches=3)
                c = make_line("C", product_by_letter["C"], 2, 3, quantity=Decimal("15"),
                              batch_size=Decimal("10"), num_batches=1)
                b = make_line("B", product_by_letter["B"], 6, 7)
                d = make_line("D", product_by_letter["D"], 8, 9)
                no_wc = make_line("NO-WC", product_by_letter["A"], 8, 8, work_center_id=None)
                inactive_wc_line = make_line("INACTIVE-WC", product_by_letter["A"], 9, 9,
                                             work_center_id=inactive_wc.id)
                inactive_product_line = make_line("INACTIVE-PRODUCT", product_by_letter["INACTIVE"], 10, 10)
                no_hours = make_line("NO-HOURS", product_by_letter["B"], 11, 11, hours=None)
                bad_priority = make_line("BAD-PRIORITY", product_by_letter["B"], 12, 12,
                                         priority_score=Decimal("NaN"))
                before_locked = make_line("BEFORE-LOCKED", product_by_letter["E"], 5, 6,
                                          work_center_id=second_active_wc.id)
                unanchored_locked = make_line(
                    "UNANCHORED-LOCKED", product_by_letter["A"], 15, 15,
                    work_center_id=unanchored_wc.id, is_locked=True,
                    feasibility_status=MPSFeasibilityStatus.ON_HOLD,
                )
                unanchored_open = make_line(
                    "UNANCHORED-OPEN", product_by_letter["A"], 16, 16,
                    work_center_id=unanchored_wc.id,
                )
                ambiguous_locked = make_line(
                    "AMBIGUOUS-LOCKED", product_by_letter["A"], 18, 18,
                    work_center_id=inactive_wc.id, campaign_id=ambiguous_locked_campaign.id,
                    is_locked=True, feasibility_status=MPSFeasibilityStatus.ON_HOLD,
                )
                ambiguous_open = make_line(
                    "AMBIGUOUS-OPEN", product_by_letter["A"], 19, 19,
                    work_center_id=ambiguous_wc.id,
                )
                bad_batch_count = make_line("BAD-BATCH-COUNT", product_by_letter["B"], 13, 13,
                                            num_batches=0)
                zero_hours = make_line("ZERO-HOURS", product_by_letter["B"], 14, 14,
                                       quantity=Decimal("10"), hours=Decimal("0"))
                db.add_all([
                    locked, locked2, a1, a2, c, b, d, no_wc, inactive_wc_line,
                    inactive_product_line, no_hours, bad_priority, before_locked,
                    unanchored_locked, unanchored_open, ambiguous_locked, ambiguous_open,
                    bad_batch_count, zero_hours,
                ])
                await db.flush()
                product_by_letter["INACTIVE"].is_active = False
                await db.flush()
                plan_id = plan.id
                line_ids = {
                    key: value.id for key, value in {
                        "locked": locked, "locked2": locked2,
                        "a1": a1, "a2": a2, "c": c, "b": b, "d": d,
                        "before_locked": before_locked,
                        "unanchored_locked": unanchored_locked,
                        "unanchored_open": unanchored_open,
                        "ambiguous_locked": ambiguous_locked,
                        "ambiguous_open": ambiguous_open,
                        "no_wc": no_wc, "inactive_wc": inactive_wc_line,
                        "inactive_product": inactive_product_line, "no_hours": no_hours,
                        "bad_priority": bad_priority, "bad_batch_count": bad_batch_count,
                        "zero_hours": zero_hours,
                    }.items()
                }
                locked_campaign_id, locked_campaign_2_id = locked_campaign.id, later_locked_campaign.id
                ambiguous_locked_campaign_id = ambiguous_locked_campaign.id
                stale_campaign_id = stale_campaign.id
                product_ids = [product.id for product in products]
                work_center_ids = [active_wc.id, second_active_wc.id, inactive_wc.id, unanchored_wc.id, ambiguous_wc.id]

            result = await run_campaign_grouping_validated(db, plan_id)
            assert result["campaigns_created"] == 5
            assert result["lines_grouped"] == 6
            assert result["ungrouped_lines"] == 9
            assert result["locked_lines_preserved"] == 4
            campaigns = await list_campaigns(db, plan_id)
            assert len(campaigns) == 8
            assert any(c.id == locked_campaign_id and c.sequence_order == 4 for c in campaigns)
            assert any(c.id == locked_campaign_2_id and c.sequence_order == 5 for c in campaigns)
            assert all(c.id != stale_campaign_id for c in campaigns)
            locked_ids = {locked_campaign_id, locked_campaign_2_id, ambiguous_locked_campaign_id}
            unlocked = [c for c in campaigns if c.id not in locked_ids]
            signature = [
                (c.work_center_id, c.campaign_code, c.sequence_order, c.campaign_start, c.campaign_end,
                 c.total_changeover_hrs)
                for c in unlocked
            ]
            by_work_center = {}
            for campaign in unlocked:
                by_work_center.setdefault(campaign.work_center_id, []).append(campaign.sequence_order)
            assert sorted(by_work_center[work_center_ids[0]]) == [5, 6, 7, 8]
            assert by_work_center[work_center_ids[1]] == [4]
            assert len({item[1] for item in signature}) == 5
            lines = (await db.scalars(select(MPSLine).where(MPSLine.id.in_(list(line_ids.values()))))).all()
            by_id = {line.id: line for line in lines}
            campaign_by_id = {campaign.id: campaign for campaign in campaigns}
            assert by_id[line_ids["a1"]].campaign_id == by_id[line_ids["a2"]].campaign_id
            assert by_id[line_ids["locked"]].campaign_id == locked_campaign_id
            assert by_id[line_ids["locked2"]].campaign_id == locked_campaign_2_id
            assert by_id[line_ids["c"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert by_id[line_ids["d"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert by_id[line_ids["before_locked"]].feasibility_status == MPSFeasibilityStatus.PENDING
            assert campaign_by_id[by_id[line_ids["before_locked"]].campaign_id].sequence_order == 4
            assert campaign_by_id[by_id[line_ids["before_locked"]].campaign_id].total_changeover_hrs == Decimal("0.200")
            assert by_id[line_ids["unanchored_locked"]].campaign_id is None
            assert by_id[line_ids["unanchored_locked"]].feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert by_id[line_ids["unanchored_open"]].campaign_id is None
            assert by_id[line_ids["unanchored_open"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert by_id[line_ids["ambiguous_locked"]].campaign_id == ambiguous_locked_campaign_id
            assert by_id[line_ids["ambiguous_locked"]].feasibility_status == MPSFeasibilityStatus.ON_HOLD
            assert by_id[line_ids["ambiguous_open"]].campaign_id is None
            assert by_id[line_ids["ambiguous_open"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert by_id[line_ids["bad_batch_count"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert by_id[line_ids["zero_hours"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE
            assert campaign_by_id[by_id[line_ids["a1"]].campaign_id].total_changeover_hrs == Decimal("0.250")
            assert campaign_by_id[by_id[line_ids["b"]].campaign_id].total_changeover_hrs == Decimal("0.500")
            assert campaign_by_id[by_id[line_ids["c"]].campaign_id].total_changeover_hrs == Decimal("0.000")
            assert campaign_by_id[by_id[line_ids["d"]].campaign_id].total_changeover_hrs == Decimal("0.000")
            for key in (
                "no_wc", "inactive_wc", "inactive_product", "no_hours", "bad_priority",
                "bad_batch_count", "zero_hours",
            ):
                assert by_id[line_ids[key]].campaign_id is None
            assert by_id[line_ids["no_hours"]].feasibility_status == MPSFeasibilityStatus.PENDING
            assert by_id[line_ids["bad_priority"]].feasibility_status == MPSFeasibilityStatus.INFEASIBLE

            diagnostics = await list_plan_diagnostics(db, plan_id)
            by_line = {uuid.UUID(row["line_id"]): row["diagnostics"] for row in diagnostics}
            for key, reason in (
                ("c", "CAMPAIGN_WINDOWS_OVERLAP"), ("c", "BATCH_SIZE_NOT_ALIGNED"),
                ("d", "CHANGEOVER_CONFIGURATION_INVALID"),
                ("before_locked", "CHANGEOVER_TO_LOCKED_CAMPAIGN_CONFIGURED"),
                ("unanchored_open", "LOCKED_CAMPAIGN_SEQUENCE_INVALID"),
                ("unanchored_locked", "LOCKED_CAMPAIGN_SEQUENCE_NOT_CONFIGURED"),
                ("ambiguous_open", "LOCKED_CAMPAIGN_SEQUENCE_INVALID"),
                ("ambiguous_locked", "LOCKED_CAMPAIGN_WORK_CENTER_AMBIGUOUS"),
                ("no_wc", "WORK_CENTER_MISSING"), ("inactive_wc", "WORK_CENTER_INACTIVE"),
                ("inactive_product", "PRODUCT_MASTER_INACTIVE"),
                ("no_hours", "PRODUCTION_HOURS_NOT_CONFIGURED"),
                ("bad_priority", "CAMPAIGN_PRIORITY_INVALID"),
                ("bad_batch_count", "BATCH_COUNT_INVALID"),
                ("zero_hours", "PRODUCTION_HOURS_INVALID"),
            ):
                assert reason in by_line[line_ids[key]]["reason_codes"]
            assert "CHANGEOVER_NOT_CONFIGURED" not in by_line[line_ids["a1"]]["reason_codes"]
            for key in ("a1", "a2", "b", "c", "before_locked"):
                assert "CIP_NOT_CONFIGURED" in by_line[line_ids[key]]["reason_codes"]
                assert "MINIMUM_RUN_NOT_CONFIGURED" in by_line[line_ids[key]]["reason_codes"]
            assert "CIP_CONFIGURATION_INVALID" in by_line[line_ids["d"]]["reason_codes"]
            assert "MINIMUM_RUN_NOT_CONFIGURED" in by_line[line_ids["d"]]["reason_codes"]

            rerun = await run_campaign_grouping_validated(db, plan_id)
            assert rerun["campaigns_created"] == 5
            rerun_campaigns = [
                c for c in await list_campaigns(db, plan_id) if c.id not in locked_ids
            ]
            assert [(c.work_center_id, c.campaign_code, c.sequence_order, c.campaign_start, c.campaign_end,
                     c.total_changeover_hrs)
                    for c in rerun_campaigns] == signature

            for line in lines:
                line.is_locked = True
            await db.flush()
            all_locked_result = await run_campaign_grouping_validated(db, plan_id)
            assert all_locked_result["campaigns_created"] == 0
            assert all_locked_result["lines_grouped"] == 0
            assert all_locked_result["ungrouped_lines"] == 0
            assert all_locked_result["locked_lines_preserved"] == len(lines)
            all_locked_diagnostics = await list_plan_diagnostics(db, plan_id)
            all_locked_by_line = {
                uuid.UUID(row["line_id"]): row["diagnostics"] for row in all_locked_diagnostics
                if row["run_id"] == all_locked_result["diagnostic_run_id"]
            }
            assert len(all_locked_by_line) == len(lines)
            assert "LOCKED_CAMPAIGN_SEQUENCE_NOT_CONFIGURED" in all_locked_by_line[
                line_ids["unanchored_locked"]
            ]["reason_codes"]
            assert "LOCKED_CAMPAIGN_WORK_CENTER_AMBIGUOUS" in all_locked_by_line[
                line_ids["ambiguous_locked"]
            ]["reason_codes"]
    finally:
        async with AsyncSessionLocal() as cleanup:
            async with cleanup.begin():
                if plan_id is not None:
                    await cleanup.execute(delete(MPSPlan).where(MPSPlan.id == plan_id))
                if work_center_ids:
                    await cleanup.execute(delete(ChangeoverMatrix).where(
                        ChangeoverMatrix.work_center_id.in_(work_center_ids),
                    ))
                    await cleanup.execute(delete(WorkCenter).where(WorkCenter.id.in_(work_center_ids)))
                if product_ids:
                    await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
        await engine.dispose()
