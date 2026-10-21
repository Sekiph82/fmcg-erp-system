"""PostgreSQL integration coverage added from the M20 strict V03 audit."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.bom import AdvancedBOM, AdvancedBOMLine, BOMLifecycle, BasisType, ItemLinkType
from app.models.company import Company
from app.models.inventory import Stock, StockType
from app.models.master import (
    Material, MaterialType, Product, ProductCategory, UnitOfMeasure,
    Warehouse, WarehouseType,
)
from app.models.mps import (
    MPSCapacityMode, MPSChangeType, MPSFeasibilityStatus, MPSLine, MPSPlan, MPSScenarioSnapshot,
    MPSStatus, MPSWhatIfScenario,
)
from app.models.mrp import MRPResult, MRPRun, MRPRunStatus
from app.models.production import ProductionOrder
from app.models.recipe import Recipe, RecipeStatus
from app.models.planning import ResourceCalendar
from app.models.production_advanced import WorkCenter, WorkCenterType
from app.models.role import AccessScope, Permission, Role
from app.models.user import User, user_role
from app.schemas.mps import GenerateFromMRPRequest, MPSWhatIfCreate, WhatIfChange
from app.services.mps_advanced_service import evaluate_material_feasibility, list_plan_diagnostics
from app.services.mps_service import approve_mps_plan, generate_mps_from_mrp, release_mps_plan
from app.services.mps_whatif_service import (
    _validate_shift_additions,
    compare_whatif_scenarios,
    create_whatif_scenario,
)


class _RollbackFixture(Exception):
    pass


def _suffix() -> str:
    return uuid4().hex[:10]


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


@pytest.mark.asyncio
async def test_postgres_whatif_merge_exact_split_and_added_shift_resimulate_without_live_mutation():
    """Persist exact scenario operations and finite-capacity before/after metrics."""
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 scenario operation proof requires PostgreSQL")

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
            )
            second = MPSLine(
                line_no=f"M20-OPS-B-{suffix}", mps_id=plan.id, product_id=product.id,
                period_start=day, period_end=day, planned_start_date=day, planned_end_date=day,
                planned_production_qty=Decimal("60"), work_center_id=work_center.id,
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
        second_line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
        await db.flush()
        with pytest.raises(ValueError, match="matching source allocation, product, batch, campaign"):
            await create_whatif_scenario(db, plan_id, MPSWhatIfCreate(
                scenario_name="incompatible feasibility merge",
                changes=[WhatIfChange(line_id=first_id, change_type=MPSChangeType.MERGE, new_value=str(second_id))],
            ), user_id)
        second_line.feasibility_status = MPSFeasibilityStatus.PENDING
        await db.flush()
        snapshots = (await db.scalars(select(MPSScenarioSnapshot).where(
            MPSScenarioSnapshot.scenario_id.in_([merged.id, split.id, shifted.id, maximum_shift.id]),
        ))).all()
        by_scenario = {row.scenario_id: row for row in snapshots}
        assert len(by_scenario) == 4
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
async def test_postgres_seeded_mrp_bom_inventory_diagnostics_snapshot_and_release_replay():
    """Exercise a committed MRP→MPS→BOM/stock→scenario→production path."""
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 cross-module proof requires PostgreSQL")

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
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("M20 release route scope proof requires PostgreSQL")

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
