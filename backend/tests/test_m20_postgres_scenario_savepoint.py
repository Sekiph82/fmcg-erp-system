"""PostgreSQL behavioral proof for isolated what-if material simulations."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.master import Material, MaterialType, Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
from app.models.mps import MPSLine, MPSPlan
from app.models.mrp import MRPRun, MRPRunStatus
from app.models.bom import AdvancedBOM, AdvancedBOMLine, BOMLifecycle, BasisType
from app.services.mps_whatif_service import _simulate_scenario_materials


class _RollbackFixture(Exception):
    pass


@pytest.mark.asyncio
async def test_postgres_material_resimulation_uses_real_bom_supply_and_rolls_back_all_live_changes():
    if "postgresql" not in str(settings.DATABASE_URL):
        pytest.skip("MPS material savepoint proof requires PostgreSQL")

    suffix = uuid4().hex[:12]
    async with AsyncSessionLocal() as db:
        try:
            async with db.begin():
                warehouse = Warehouse(
                    code=f"M20-WH-{suffix}", name="M20 material scenario test", warehouse_type=WarehouseType.FINISHED_GOODS,
                )
                product = Product(
                    sku=f"M20-P-{suffix}", name="M20 material scenario product",
                    category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
                )
                material = Material(
                    code=f"M20-M-{suffix}", name="M20 material scenario component",
                    material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
                )
                db.add_all([warehouse, product, material])
                await db.flush()
                run = MRPRun(
                    run_no=f"M20-RUN-{suffix}", run_date=date(2026, 1, 1),
                    status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
                )
                root_bom = AdvancedBOM(
                    bom_code=f"M20-ROOT-{suffix}", bom_name="M20 nested root BOM",
                    product_id=product.id, base_qty=1, base_uom="KG",
                    lifecycle=BOMLifecycle.APPROVED, is_default=True,
                )
                child_bom = AdvancedBOM(
                    bom_code=f"M20-CHILD-{suffix}", bom_name="M20 nested subassembly BOM",
                    base_qty=1, base_uom="KG", lifecycle=BOMLifecycle.APPROVED, is_default=False,
                )
                db.add_all([run, root_bom, child_bom])
                await db.flush()
                db.add_all([
                    AdvancedBOMLine(
                        bom_id=root_bom.id, line_no=1, child_bom_id=child_bom.id,
                        required_qty=2, required_uom="KG", basis_type=BasisType.PER_UNIT,
                    ),
                    AdvancedBOMLine(
                        bom_id=child_bom.id, line_no=1, item_id=material.id,
                        required_qty=1, required_uom="KG", basis_type=BasisType.PER_UNIT,
                    ),
                ])
                plan = MPSPlan(
                    plan_no=f"M20-PLAN-{suffix}", plan_name="M20 material scenario plan",
                    start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), mrp_run_id=run.id,
                )
                db.add(plan)
                await db.flush()
                line = MPSLine(
                    line_no=f"M20-LINE-{suffix}", mps_id=plan.id, product_id=product.id,
                    period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                    planned_production_qty=1, planned_start_date=date(2026, 1, 1),
                    planned_end_date=date(2026, 1, 31),
                )
                db.add(line)
                await db.flush()
                plan_id = plan.id
                line_id = line.id

                result = await _simulate_scenario_materials(db, plan_id, {
                    str(line_id): {
                        "planned_production_qty": "10",
                        "planned_start_date": "2026-01-01",
                        "planned_end_date": "2026-01-31",
                    }
                })
                assert result["status"] == "COMPLETE", repr(result)
                assert result["baseline_shortage_count"] == 1
                assert result["candidate_shortage_count"] == 1
                assert result["baseline_shortage_quantity_by_uom"] == {"KG": "2.0000"}
                assert result["candidate_shortage_quantity_by_uom"] == {"KG": "20.0000"}

                persisted_line = await db.get(MPSLine, line_id)
                assert persisted_line.planned_production_qty == Decimal("1.000")
                diagnostics_count = await db.scalar(
                    text("SELECT COUNT(*) FROM mps_line_diagnostics WHERE mps_id = :mps_id"),
                    {"mps_id": plan_id},
                )
                assert diagnostics_count == 0
                raise _RollbackFixture()
        except _RollbackFixture:
            pass
