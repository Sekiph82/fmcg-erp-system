"""M20 demand, material, diagnostic, and scenario evidence services."""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import Product, Material, Warehouse
from app.models.inventory import Stock, StockType
from app.models.mps import MPSPlan, MPSLine, MPSStatus, MPSFeasibilityStatus
from app.models.mrp import MRPRun, MRPRunStatus, MRPResult, DemandForecast, DemandForecastLine
from app.models.sales import SalesOrder, SOLine, SOStatus
from app.models.procurement import PurchaseOrder, POLine, POStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.bom import AdvancedBOM, AdvancedBOMLine, BOMLifecycle
from app.services.mps_engine import (
    PlanningInputError, allocate_period_quantity, decimal, explode_approved_bom,
    net_finished_goods_requirement, period_buckets, round_qty,
)


_OPEN_SALES_STATUSES = (SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING)
_OPEN_PO_STATUSES = (POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED)
_OPEN_PRODUCTION_STATUSES = (
    ProductionOrderStatus.PLANNED, ProductionOrderStatus.RELEASED,
    ProductionOrderStatus.IN_PROGRESS,
)


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "").upper()


def _period_end(start: date, period_type: object) -> date:
    kind = _enum_value(period_type)
    if kind == "DAILY":
        return start
    if kind == "WEEKLY":
        return start + timedelta(days=6)
    if kind == "MONTHLY":
        from calendar import monthrange
        return date(start.year, start.month, monthrange(start.year, start.month)[1])
    raise PlanningInputError(f"unsupported forecast period type: {kind}")


async def _scoped_plan(db: AsyncSession, mps_id: uuid.UUID) -> tuple[MPSPlan, MRPRun, Warehouse]:
    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())).scalar_one_or_none()
    if plan is None:
        raise ValueError("MPS plan not found")
    if not plan.mrp_run_id:
        raise ValueError("MPS plan must be linked to a completed MRP run with a warehouse scope")
    run = await db.get(MRPRun, plan.mrp_run_id)
    if run is None or run.status != MRPRunStatus.COMPLETED:
        raise ValueError("MPS source MRP run is missing or not COMPLETED")
    if not run.warehouse_id:
        raise ValueError("MPS source MRP run has no warehouse scope; refusing unscoped planning")
    warehouse = await db.get(Warehouse, run.warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise ValueError("MPS source warehouse is missing or inactive")
    return plan, run, warehouse


async def project_demand_and_supply(
    db: AsyncSession, mps_id: uuid.UUID, period_type: str = "WEEKLY",
) -> dict:
    """Rebuild unlocked draft lines from dated demand and scoped supply.

    Confirmed orders consume overlapping forecast in each period.  Safety
    stock is a period-end target; opening stock and dated receipts are carried
    forward, so they are counted once rather than once per bucket.
    """
    plan, run, warehouse = await _scoped_plan(db, mps_id)
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Demand projection is available only for DRAFT plans")
    buckets = period_buckets(plan.start_date, plan.end_date, period_type)

    order_rows = (await db.execute(
        select(SalesOrder, SOLine)
        .join(SOLine, SOLine.so_id == SalesOrder.id)
        .where(
            SalesOrder.status.in_(_OPEN_SALES_STATUSES),
            SalesOrder.warehouse_id == warehouse.id,
            SalesOrder.requested_delivery_date >= plan.start_date,
            SalesOrder.requested_delivery_date <= plan.end_date,
        )
        .order_by(SalesOrder.requested_delivery_date, SalesOrder.order_no, SOLine.line_no)
    )).all()

    forecast_rows = (await db.execute(
        select(DemandForecast, DemandForecastLine)
        .join(DemandForecastLine, DemandForecastLine.forecast_id == DemandForecast.id)
        .where(
            DemandForecast.status == "APPROVED",
            DemandForecast.is_approved.is_(True),
            DemandForecast.warehouse_id == warehouse.id,
            DemandForecast.start_date <= plan.end_date,
            DemandForecast.end_date >= plan.start_date,
        )
        .order_by(DemandForecastLine.period_date, DemandForecast.id)
    )).all()

    confirmed: dict[tuple[uuid.UUID, int], Decimal] = defaultdict(Decimal)
    forecast: dict[tuple[uuid.UUID, int], Decimal] = defaultdict(Decimal)
    product_ids: set[uuid.UUID] = set()
    for order, line in order_rows:
        product = await db.get(Product, line.product_id)
        if product is None or not product.is_active:
            continue
        order_uom = _enum_value(line.unit)
        product_uom = _enum_value(product.uom)
        if order_uom != product_uom:
            raise ValueError(f"Sales order {order.order_no} line {line.line_no} UOM {order_uom} does not match product UOM {product_uom}")
        demand = max(Decimal(0), decimal(line.ordered_quantity) - decimal(line.shipped_quantity))
        bucket_index = next((i for i, (_, bucket_end) in enumerate(buckets) if order.requested_delivery_date <= bucket_end), None)
        if bucket_index is not None:
            confirmed[(line.product_id, bucket_index)] += demand
            product_ids.add(line.product_id)

    for header, line in forecast_rows:
        product = await db.get(Product, header.product_id)
        if product is None or not product.is_active:
            continue
        forecast_uom = _enum_value(product.uom)
        amount = line.adjusted_qty if line.adjusted_qty is not None else line.forecast_qty
        source_end = min(header.end_date, _period_end(line.period_date, header.period_type))
        source_start = max(header.start_date, line.period_date)
        if source_end < source_start:
            continue
        allocated = allocate_period_quantity(amount, source_start, source_end, buckets)
        for index, value in enumerate(allocated):
            if value:
                forecast[(header.product_id, index)] += value
                product_ids.add(header.product_id)

    if not product_ids:
        old_lines = (await db.execute(select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(False)))).scalars().all()
        for old in old_lines:
            await db.delete(old)
        from app.services.mps_service import _refresh_plan_counters
        await _refresh_plan_counters(db, mps_id)
        await db.flush()
        return {"lines_created": 0, "demand_products": 0, "periods": len(buckets), "warehouse_id": str(warehouse.id)}

    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()}
    mps_results = (await db.execute(
        select(MRPResult).where(MRPResult.run_id == run.id, MRPResult.product_id.in_(product_ids))
    )).scalars().all()
    mrp_by_product = {row.product_id: row for row in mps_results}

    stock_rows = (await db.execute(
        select(Stock.product_id, func.sum(Stock.quantity_on_hand), func.sum(Stock.quantity_reserved), func.sum(Stock.quantity_available))
        .where(Stock.warehouse_id == warehouse.id, Stock.stock_type == StockType.PRODUCT,
               Stock.is_blocked.is_(False), Stock.product_id.in_(product_ids))
        .group_by(Stock.product_id)
    )).all()
    stock = {product_id: (decimal(on_hand), decimal(reserved), decimal(available)) for product_id, on_hand, reserved, available in stock_rows}

    company_filter = PurchaseOrder.company_id.is_(None) if warehouse.company_id is None else PurchaseOrder.company_id == warehouse.company_id
    po_rows = (await db.execute(
        select(PurchaseOrder.expected_delivery_date, POLine.product_id,
               POLine.ordered_quantity - POLine.received_quantity)
        .join(POLine, POLine.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.status.in_(_OPEN_PO_STATUSES), company_filter,
               POLine.product_id.in_(product_ids),
               POLine.ordered_quantity > POLine.received_quantity)
    )).all()
    po_supply: dict[uuid.UUID, list[tuple[date, Decimal]]] = defaultdict(list)
    for due, product_id, qty in po_rows:
        po_supply[product_id].append((due, decimal(qty)))

    wip_rows = (await db.execute(
        select(ProductionOrder.scheduled_end, ProductionOrder.product_id,
               ProductionOrder.planned_quantity, ProductionOrder.actual_quantity)
        .where(ProductionOrder.target_warehouse_id == warehouse.id,
               ProductionOrder.status.in_(_OPEN_PRODUCTION_STATUSES),
               ProductionOrder.product_id.in_(product_ids))
    )).all()
    wip_supply: dict[uuid.UUID, list[tuple[date, Decimal]]] = defaultdict(list)
    for due, product_id, planned, actual in wip_rows:
        wip_supply[product_id].append((due.date(), max(Decimal(0), decimal(planned) - decimal(actual))))

    other_plans = (await db.execute(
        select(MPSLine.product_id, MPSLine.planned_end_date, MPSLine.planned_production_qty)
        .join(MPSPlan, MPSPlan.id == MPSLine.mps_id)
        .where(MPSLine.mps_id != mps_id, MPSPlan.status == MPSStatus.APPROVED,
               MPSPlan.plant_code == plan.plant_code if plan.plant_code else MPSPlan.id == uuid.UUID(int=0),
               MPSLine.production_order_id.is_(None), MPSLine.product_id.in_(product_ids))
    )).all()
    other_supply: dict[uuid.UUID, list[tuple[date | None, Decimal]]] = defaultdict(list)
    for due, product_id, qty in other_plans:
        other_supply[product_id].append((due, decimal(qty)))

    locked_lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(True))
    )).scalars().all()
    locked_supply: dict[tuple[uuid.UUID, int], Decimal] = defaultdict(Decimal)
    for line in locked_lines:
        for index, (_, bucket_end) in enumerate(buckets):
            if line.period_end <= bucket_end and line.period_end >= buckets[index][0]:
                locked_supply[(line.product_id, index)] += decimal(line.planned_production_qty)
                break

    old_lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(False))
    )).scalars().all()
    for old in old_lines:
        await db.delete(old)
    await db.flush()

    created = 0
    for product_id in sorted(product_ids, key=str):
        product = products[product_id]
        on_hand, reserved, stored_available = stock.get(product_id, (Decimal(0), Decimal(0), Decimal(0)))
        available = max(Decimal(0), on_hand - reserved)
        for index, (bucket_start, bucket_end) in enumerate(buckets):
            confirmed_qty = confirmed[(product_id, index)]
            forecast_qty = forecast[(product_id, index)]
            if confirmed_qty == 0 and forecast_qty == 0:
                continue
            incoming = sum((qty for due, qty in po_supply[product_id] if bucket_start <= due <= bucket_end), Decimal(0))
            wip = sum((qty for due, qty in wip_supply[product_id] if bucket_start <= due <= bucket_end), Decimal(0))
            planned = sum((qty for due, qty in other_supply[product_id] if due is not None and bucket_start <= due <= bucket_end), Decimal(0))
            locked = locked_supply[(product_id, index)]
            totals = net_finished_goods_requirement(
                confirmed=confirmed_qty, forecast=forecast_qty,
                safety_stock=product.reorder_point, on_hand=available,
                reserved=0, incoming=incoming + wip + planned + locked,
            )
            # Carry projected ending stock to the next period; dated supply is cumulative.
            gross = totals["confirmed"] + totals["net_forecast"]
            available = max(Decimal(0), available + incoming + wip + planned + locked + totals["net_requirement"] - gross)
            net_qty = totals["net_requirement"]
            if net_qty <= 0:
                continue
            run_result = mrp_by_product.get(product_id)
            label = f"{bucket_start.year}-W{bucket_start.isocalendar()[1]:02d}" if period_type.upper() == "WEEKLY" else (f"{bucket_start:%Y-%m}" if period_type.upper() == "MONTHLY" else bucket_start.isoformat())
            line = MPSLine(
                line_no=f"MPS-{plan.id.hex[:8]}-{created + 1:06d}",
                mps_id=mps_id, product_id=product_id,
                mrp_result_id=run_result.id if run_result else None,
                period_label=label, period_start=bucket_start, period_end=bucket_end,
                confirmed_demand_qty=totals["confirmed"], forecast_qty=totals["forecast"],
                safety_stock_qty=totals["safety_stock"], net_requirement_qty=net_qty,
                planned_production_qty=net_qty, planned_start_date=bucket_start,
                planned_end_date=bucket_end, feasibility_status=MPSFeasibilityStatus.PENDING,
                priority_score=Decimal("50"),
                remarks="Demand projection from approved warehouse-scoped orders and forecasts; supply netted by due date.",
            )
            db.add(line)
            await db.flush()
            created += 1

    await db.flush()
    from app.services.mps_service import _refresh_plan_counters
    await _refresh_plan_counters(db, mps_id)
    return {"lines_created": created, "demand_products": len(product_ids), "periods": len(buckets), "warehouse_id": str(warehouse.id), "source_mrp_run_id": str(run.id)}


async def evaluate_material_feasibility(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Explode effective approved BOMs, net dated material supply, and persist reasons."""
    plan, run, warehouse = await _scoped_plan(db, mps_id)
    lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id).order_by(MPSLine.period_start, MPSLine.priority_score.desc(), MPSLine.line_no)
    )).scalars().all()
    product_ids = {line.product_id for line in lines}
    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()} if product_ids else {}
    recipes = (await db.execute(
        select(Recipe).where(Recipe.product_id.in_(product_ids), Recipe.status == RecipeStatus.APPROVED,
                             Recipe.is_active.is_(True),
                             ((Recipe.valid_from.is_(None)) | (Recipe.valid_from <= plan.end_date)),
                             ((Recipe.valid_to.is_(None)) | (Recipe.valid_to >= plan.start_date)))
        .order_by(Recipe.valid_from.desc().nulls_last(), Recipe.created_at.desc())
    )).scalars().all() if product_ids else []
    recipes_by_product: dict[uuid.UUID, list[Recipe]] = defaultdict(list)
    for recipe in recipes:
        recipes_by_product[recipe.product_id].append(recipe)
    boms = (await db.execute(
        select(AdvancedBOM).where(AdvancedBOM.product_id.in_(product_ids),
                                 AdvancedBOM.lifecycle.in_((BOMLifecycle.APPROVED, BOMLifecycle.RELEASED)),
                                 AdvancedBOM.is_default.is_(True),
                                 ((AdvancedBOM.effective_from.is_(None)) | (AdvancedBOM.effective_from <= plan.end_date)),
                                 ((AdvancedBOM.effective_to.is_(None)) | (AdvancedBOM.effective_to >= plan.start_date)))
        .order_by(AdvancedBOM.effective_from.desc().nulls_last(), AdvancedBOM.created_at.desc())
    )).scalars().all() if product_ids else []
    boms_by_product: dict[uuid.UUID, list[AdvancedBOM]] = defaultdict(list)
    for bom in boms:
        boms_by_product[bom.product_id].append(bom)

    recipe_ids = {r.id for r in recipes}
    recipe_items = (await db.execute(select(RecipeItem).where(RecipeItem.recipe_id.in_(recipe_ids), RecipeItem.is_optional.is_(False)))) .scalars().all() if recipe_ids else []
    recipe_items_by_id: dict[uuid.UUID, list[RecipeItem]] = defaultdict(list)
    for item in recipe_items:
        recipe_items_by_id[item.recipe_id].append(item)
    bom_ids = {b.id for b in boms}
    bom_items = (await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id.in_(bom_ids), AdvancedBOMLine.is_optional.is_(False)))) .scalars().all() if bom_ids else []
    bom_items_by_id: dict[uuid.UUID, list[AdvancedBOMLine]] = defaultdict(list)
    for item in bom_items:
        bom_items_by_id[item.bom_id].append(item)

    material_ids = {item.material_id for item in recipe_items} | {
        item.item_id for item in bom_items if _enum_value(item.item_type) == "MATERIAL" and item.item_id
    }
    materials = {m.id: m for m in (await db.execute(select(Material).where(Material.id.in_(material_ids)))).scalars().all()} if material_ids else {}
    stock_rows = (await db.execute(
        select(Stock.material_id, func.sum(Stock.quantity_on_hand), func.sum(Stock.quantity_reserved), func.sum(Stock.quantity_available))
        .where(Stock.warehouse_id == warehouse.id, Stock.stock_type == StockType.MATERIAL,
               Stock.is_blocked.is_(False), Stock.material_id.in_(material_ids))
        .group_by(Stock.material_id)
    )).all() if material_ids else []
    material_stock = {mid: max(Decimal(0), decimal(on_hand) - decimal(reserved)) for mid, on_hand, reserved, _ in stock_rows}
    remaining = dict(material_stock)

    company_filter = PurchaseOrder.company_id.is_(None) if warehouse.company_id is None else PurchaseOrder.company_id == warehouse.company_id
    material_po_rows = (await db.execute(
        select(PurchaseOrder.expected_delivery_date, POLine.material_id,
               POLine.ordered_quantity - POLine.received_quantity, POLine.unit)
        .join(POLine, POLine.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.status.in_(_OPEN_PO_STATUSES), company_filter,
               POLine.material_id.in_(material_ids),
               POLine.ordered_quantity > POLine.received_quantity)
    )).all() if material_ids else []
    material_receipts: dict[uuid.UUID, list[tuple[date, Decimal, str]]] = defaultdict(list)
    for due, material_id, qty, unit in material_po_rows:
        material_receipts[material_id].append((due, decimal(qty), _enum_value(unit)))
    prior_material_receipts: dict[uuid.UUID, Decimal] = defaultdict(Decimal)

    issues_by_line: dict[uuid.UUID, list[dict]] = defaultdict(list)
    diagnostics_to_write: list[tuple[uuid.UUID, dict]] = []
    for line in lines:
        product = products.get(line.product_id)
        if product is None:
            issues_by_line[line.id].append({"reason_code": "PRODUCT_MISSING", "priority": "CRITICAL"})
            continue
        material_needs: list[dict] = []
        required_date = line.planned_start_date or line.period_start
        bom = next((candidate for candidate in boms_by_product.get(line.product_id, [])
                    if (candidate.effective_from is None or candidate.effective_from <= required_date)
                    and (candidate.effective_to is None or candidate.effective_to >= required_date)), None)
        if bom:
            bom_uom = _enum_value(bom.base_uom)
            try:
                if bom_uom != _enum_value(product.uom):
                    raise PlanningInputError("BOM output and finished-product UOM conversion is not configured")
                material_needs = explode_approved_bom(
                    output_qty=line.planned_production_qty,
                    output_uom=bom_uom,
                    bom={"base_qty": bom.base_qty, "base_uom": bom.base_uom, "output_uom": product.uom, "lifecycle": bom.lifecycle},
                    lines=[{
                        "item_id": item.item_id, "item_type": item.item_type,
                        "required_qty": item.required_qty, "required_uom": item.required_uom,
                        "basis_type": item.basis_type, "wastage_pct": item.wastage_pct,
                        "process_loss_pct": item.process_loss_pct,
                        "is_optional": item.is_optional,
                        "substitution_policy": item.substitution_policy,
                    } for item in bom_items_by_id[bom.id]],
                )
            except PlanningInputError as exc:
                issues_by_line[line.id].append({"reason_code": "BOM_DATA_INVALID", "message": str(exc), "priority": "CRITICAL", "bom_id": str(bom.id)})
        else:
            recipe = next((candidate for candidate in recipes_by_product.get(line.product_id, [])
                           if (candidate.valid_from is None or candidate.valid_from <= required_date)
                           and (candidate.valid_to is None or candidate.valid_to >= required_date)), None)
            if recipe is None:
                issues_by_line[line.id].append({"reason_code": "APPROVED_BOM_MISSING", "message": "No effective approved BOM or recipe covers the planned date.", "priority": "CRITICAL"})
                continue
            for item in recipe_items_by_id[recipe.id]:
                material_needs.append({
                    "material_id": item.material_id,
                    "required_qty": round_qty(decimal(item.quantity) * decimal(line.planned_production_qty) * (Decimal(1) + decimal(item.loss_percentage) / Decimal(100)), 4),
                    "uom": _enum_value(item.unit),
                    "substitution_policy": "NO_SUB",
                })

        for need in material_needs:
            material_id = need["material_id"]
            material = materials.get(material_id)
            if material is None or not material.is_active:
                issues_by_line[line.id].append({"reason_code": "MATERIAL_MASTER_INVALID", "material_id": str(material_id), "priority": "CRITICAL"})
                continue
            required_uom = str(need.get("uom") or "").upper()
            material_uom = _enum_value(material.uom)
            if not required_uom or required_uom != material_uom:
                issues_by_line[line.id].append({"reason_code": "MATERIAL_UOM_MISMATCH", "material_id": str(material_id), "required_uom": required_uom, "material_uom": material_uom, "priority": "CRITICAL"})
                continue
            due_receipts = Decimal(0)
            for due, qty, unit in material_receipts.get(material_id, []):
                if due <= required_date:
                    if unit != material_uom:
                        issues_by_line[line.id].append({
                            "reason_code": "INCOMING_MATERIAL_UOM_MISMATCH",
                            "material_id": str(material_id), "po_uom": unit,
                            "material_uom": material_uom, "priority": "HIGH",
                        })
                        continue
                    due_receipts += qty
            newly_available = max(Decimal(0), due_receipts - prior_material_receipts[material_id])
            prior_material_receipts[material_id] = max(prior_material_receipts[material_id], due_receipts)
            need_qty = decimal(need["required_qty"])
            available_qty = remaining.get(material_id, Decimal(0)) + newly_available
            shortage = max(Decimal(0), need_qty - available_qty)
            remaining[material_id] = max(Decimal(0), available_qty - need_qty)
            if shortage:
                issues_by_line[line.id].append({
                    "reason_code": "MATERIAL_SHORT",
                    "material_id": str(material_id),
                    "material_code": material.code,
                    "required_qty": str(need_qty),
                    "available_qty": str(available_qty),
                    "shortage_qty": str(shortage),
                    "uom": required_uom,
                    "required_date": line.planned_start_date.isoformat() if line.planned_start_date else line.period_start.isoformat(),
                    "lead_time_days": material.lead_time_days,
                    "provenance": "warehouse stock; approved effective BOM/recipe",
                    "priority": "HIGH",
                })

    for line in lines:
        issues = issues_by_line[line.id]
        if any(i["reason_code"] != "MATERIAL_SHORT" for i in issues):
            line.feasibility_status = MPSFeasibilityStatus.INFEASIBLE
        elif issues:
            line.feasibility_status = MPSFeasibilityStatus.MATERIAL_SHORT
        elif line.feasibility_status not in (MPSFeasibilityStatus.OVERLOADED, MPSFeasibilityStatus.ON_HOLD):
            line.feasibility_status = MPSFeasibilityStatus.FEASIBLE
        diagnostics_to_write.append((line.id, {
            "reason_codes": [i["reason_code"] for i in issues],
            "issues": issues,
            "status": _enum_value(line.feasibility_status),
            "plan_id": str(mps_id),
            "warehouse_id": str(warehouse.id),
            "demand_run_id": str(run.id),
        }))
    diagnostic_run_id = await _write_diagnostics(db, mps_id, diagnostics_to_write)
    from app.services.mps_service import _refresh_plan_counters
    await _refresh_plan_counters(db, mps_id)
    return {
        "lines_evaluated": len(lines),
        "feasible_lines": sum(1 for line in lines if line.feasibility_status == MPSFeasibilityStatus.FEASIBLE),
        "material_short_lines": sum(1 for line in lines if line.feasibility_status == MPSFeasibilityStatus.MATERIAL_SHORT),
        "infeasible_lines": sum(1 for line in lines if line.feasibility_status == MPSFeasibilityStatus.INFEASIBLE),
        "diagnostic_run_id": str(diagnostic_run_id) if diagnostics_to_write else None,
    }


async def _write_diagnostics(db: AsyncSession, mps_id: uuid.UUID, rows: list[tuple[uuid.UUID, dict]]) -> uuid.UUID:
    run_id = uuid.uuid4()
    for line_id, body in rows:
        body["run_id"] = str(run_id)
        await db.execute(text(
            "INSERT INTO mps_line_diagnostics (id, mps_id, line_id, run_id, source_version, diagnostics) "
            "VALUES (:id, :mps_id, :line_id, :run_id, :source_version, CAST(:diagnostics AS JSONB))"
        ), {
            "id": uuid.uuid4(), "mps_id": mps_id, "line_id": line_id,
            "run_id": run_id, "source_version": "mps-diagnostics.v1",
            "diagnostics": json.dumps(body, default=str),
        })
    return run_id


async def list_plan_diagnostics(db: AsyncSession, mps_id: uuid.UUID) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT line_id, run_id, source_version, diagnostics, computed_at "
        "FROM mps_line_diagnostics WHERE mps_id = :mps_id "
        "ORDER BY computed_at DESC, line_id"
    ), {"mps_id": mps_id})).mappings().all()
    result = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for row in rows:
        key = (row["run_id"], row["line_id"])
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "line_id": str(row["line_id"]), "run_id": str(row["run_id"]),
            "source_version": row["source_version"], "diagnostics": row["diagnostics"],
            "computed_at": row["computed_at"].isoformat() if row["computed_at"] else None,
        })
    return result
