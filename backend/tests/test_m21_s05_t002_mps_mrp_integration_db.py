"""Disposable PostgreSQL integration for MRP-to-MPS BOM feasibility."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.bom import (
    AdvancedBOM,
    AdvancedBOMLine,
    BOMLifecycle,
    BOMYieldConfig,
    BasisType,
    ItemLinkType,
    LossCategory,
)
from app.models.company import Company
from app.models.inventory import Stock, StockType
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.mps import MPSFeasibilityStatus, MPSLine, MPSPlan
from app.models.mrp import MRPResult, MRPRun, MRPRunStatus
from app.models.utilities import UomConversion
from app.schemas.mps import GenerateFromMRPRequest
from app.services.mps_advanced_service import evaluate_material_feasibility, list_plan_diagnostics
from app.services.mps_service import generate_mps_from_mrp


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_completed_mrp_generates_linked_mps_line_and_yield_adjusted_material_shortage():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert re.fullmatch(r"fmcg_m21_s05_t002_[a-f0-9]{20,32}", expected_database)
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.database == expected_database
    suffix = uuid4().hex[:12]
    start_day = date(2026, 10, 1)

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            company = Company(name=f"M21 T002 synthetic company {suffix}", short_code=f"M21{suffix}")
            db.add(company)
            await db.flush()
            warehouse = Warehouse(
                code=f"M21-T002-WH-{suffix}", name="M21 T002 synthetic warehouse",
                warehouse_type=WarehouseType.RAW_MATERIAL, company_id=company.id,
            )
            product = Product(
                sku=f"M21-T002-P-{suffix}", name="M21 T002 synthetic product",
                category=ProductCategory.FOOD, uom=UnitOfMeasure.KG,
            )
            material = Material(
                code=f"M21-T002-M-{suffix}", name="M21 T002 synthetic material",
                material_type=MaterialType.RAW, uom=UnitOfMeasure.KG,
            )
            db.add_all([warehouse, product, material])
            await db.flush()

            run = MRPRun(
                run_no=f"M21-T002-RUN-{suffix}", run_date=start_day,
                status=MRPRunStatus.COMPLETED, warehouse_id=warehouse.id,
            )
            db.add(run)
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
            db.add(result)
            plan = MPSPlan(
                plan_no=f"M21-T002-PLAN-{suffix}", plan_name="M21 T002 synthetic MPS plan",
                start_date=start_day, end_date=date(2026, 10, 30), mrp_run_id=run.id,
            )
            db.add(plan)
            await db.flush()

            bom = AdvancedBOM(
                bom_code=f"M21-T002-BOM-{suffix}", bom_name="M21 T002 approved synthetic BOM",
                product_id=product.id, base_qty=Decimal("1"), base_uom="KG",
                lifecycle=BOMLifecycle.APPROVED, is_default=True,
                effective_from=start_day, effective_to=date(2026, 10, 30),
            )
            db.add(bom)
            await db.flush()
            db.add_all([
                AdvancedBOMLine(
                    bom_id=bom.id, line_no=1, item_type=ItemLinkType.MATERIAL,
                    item_id=material.id, required_qty=Decimal("1000"), required_uom="G",
                    basis_type=BasisType.PER_BATCH,
                ),
                BOMYieldConfig(
                    bom_id=bom.id, loss_category=LossCategory.PROCESS_LOSS,
                    basis="PCT_OF_INPUT", standard_pct=Decimal("10"),
                    max_allowable_pct=Decimal("15"),
                ),
                Stock(
                    stock_type=StockType.MATERIAL, warehouse_id=warehouse.id,
                    material_id=material.id, quantity_on_hand=Decimal("5.4"),
                    quantity_reserved=Decimal("0"), quantity_available=Decimal("5.4"),
                ),
                UomConversion(
                    from_uom="G", to_uom="KG", factor=Decimal("0.001"), is_active=True,
                ),
            ])
            await db.flush()

            created = await generate_mps_from_mrp(
                db, plan.id,
                GenerateFromMRPRequest(mrp_run_id=run.id, period_type="MONTHLY"),
            )
            assert created == 1
            line = await db.scalar(select(MPSLine).where(MPSLine.mps_id == plan.id))
            assert line is not None
            assert line.mrp_result_id == result.id
            assert line.product_id == product.id
            assert line.net_requirement_qty == Decimal("5.000")
            assert line.planned_production_qty == Decimal("5.000")
            assert plan.mrp_run_id == run.id

            evaluated = await evaluate_material_feasibility(db, plan.id)
            assert evaluated["lines_evaluated"] == 1
            assert evaluated["material_short_lines"] == 1
            assert evaluated["infeasible_lines"] == 0
            assert line.feasibility_status == MPSFeasibilityStatus.MATERIAL_SHORT

            diagnostics = await list_plan_diagnostics(db, plan.id)
            assert len(diagnostics) == 1
            issues = diagnostics[0]["diagnostics"]["issues"]
            assert [issue["reason_code"] for issue in issues] == ["MATERIAL_SHORT"]
            shortage = issues[0]
            assert Decimal(shortage["required_qty"]) == Decimal("5.5556")
            assert Decimal(shortage["available_qty"]) == Decimal("5.4")
            assert Decimal(shortage["shortage_qty"]) == Decimal("0.1556")
            assert shortage["uom"] == "KG"
            assert shortage["provenance"] == "warehouse stock; approved effective BOM/recipe"
        finally:
            await db.rollback()
