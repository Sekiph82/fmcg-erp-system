"""M20 demand, material, diagnostic, and scenario evidence services."""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, text
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.master import Product, Material, Warehouse
from app.models.inventory import Stock, StockType
from app.models.mps import MPSPlan, MPSLine, MPSStatus, MPSFeasibilityStatus
from app.models.mrp import MRPRun, MRPRunStatus, MRPResult, DemandForecast, DemandForecastLine
from app.models.sales import SalesOrder, SOLine, SOStatus
from app.models.procurement import PurchaseOrder, POLine, POStatus
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.bom import AdvancedBOM, AdvancedBOMLine, BOMLifecycle, BOMYieldConfig
from app.services.mps_engine import (
    PlanningInputError, allocate_period_quantity, allocate_weighted_quantity, decimal, explode_approved_bom,
    period_buckets, round_qty,
)
from app.services.utilities_service import convert_uom


_OPEN_SALES_STATUSES = (SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING)
_OPEN_PO_STATUSES = (POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED)
_OPEN_PRODUCTION_STATUSES = (
    ProductionOrderStatus.PLANNED, ProductionOrderStatus.RELEASED,
    ProductionOrderStatus.IN_PROGRESS,
)


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "").upper()


def _configured_bom_yield_loss(configs: list[BOMYieldConfig]) -> Decimal:
    """Return total configured input loss; reject unsupported or contradictory yield master data."""
    total_pct = Decimal(0)
    categories: set[str] = set()
    for config in configs:
        category = _enum_value(config.loss_category)
        basis = str(config.basis or "").strip().upper()
        pct = decimal(config.standard_pct)
        maximum = decimal(config.max_allowable_pct) if config.max_allowable_pct is not None else None
        if category in categories:
            raise PlanningInputError(f"duplicate BOM yield-loss configuration for {category}")
        categories.add(category)
        if basis != "PCT_OF_INPUT":
            raise PlanningInputError(f"unsupported BOM yield-loss basis: {basis or 'missing'}")
        if pct < 0 or pct >= 100 or (maximum is not None and (maximum < 0 or pct > maximum)):
            raise PlanningInputError(f"invalid BOM yield-loss percentage for {category}")
        total_pct += pct
    if total_pct >= 100:
        raise PlanningInputError("total BOM yield loss must be less than 100 percent")
    return total_pct


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
    daily_buckets: list[tuple[date, date]] = []
    cursor = plan.start_date
    while cursor <= plan.end_date:
        daily_buckets.append((cursor, cursor))
        cursor += timedelta(days=1)

    sales_company_scope = SalesOrder.company_id.is_(None) if warehouse.company_id is None else SalesOrder.company_id == warehouse.company_id
    order_rows = (await db.execute(
        select(SalesOrder, SOLine)
        .join(SOLine, SOLine.so_id == SalesOrder.id)
        .where(
            SalesOrder.status.in_(_OPEN_SALES_STATUSES),
            SalesOrder.warehouse_id == warehouse.id,
            sales_company_scope,
            SalesOrder.requested_delivery_date >= plan.start_date,
            SalesOrder.requested_delivery_date <= plan.end_date,
        )
        .order_by(SalesOrder.requested_delivery_date, SalesOrder.order_no, SOLine.line_no)
    )).all()

    forecast_rows = []
    if run.include_forecast:
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

    # A product can have multiple approved forecast runs (the model/start key
    # permits it). Without a selected-model policy, summing overlapping runs
    # double counts demand, so reject that ambiguous input rather than choose.
    forecast_headers: dict[uuid.UUID, dict[uuid.UUID, DemandForecast]] = defaultdict(dict)
    for header, _line in forecast_rows:
        forecast_headers[header.product_id][header.id] = header
    for product_id, headers_by_id in forecast_headers.items():
        headers = sorted(headers_by_id.values(), key=lambda header: (header.start_date, header.end_date, str(header.id)))
        for index, header in enumerate(headers):
            for earlier in headers[:index]:
                if header.start_date <= earlier.end_date and earlier.start_date <= header.end_date:
                    raise ValueError(
                        f"Overlapping approved forecasts for product {product_id} in warehouse {warehouse.id}; "
                        "select one forecast run before MPS projection"
                    )

    confirmed_by_date: dict[tuple[uuid.UUID, date], Decimal] = defaultdict(Decimal)
    forecast_by_date: dict[tuple[uuid.UUID, date], Decimal] = defaultdict(Decimal)
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
        if plan.start_date <= order.requested_delivery_date <= plan.end_date:
            confirmed_by_date[(line.product_id, order.requested_delivery_date)] += demand
            product_ids.add(line.product_id)

    for header, line in forecast_rows:
        product = await db.get(Product, header.product_id)
        if product is None or not product.is_active:
            continue
        amount = line.adjusted_qty if line.adjusted_qty is not None else line.forecast_qty
        source_end = min(header.end_date, _period_end(line.period_date, header.period_type))
        source_start = max(header.start_date, line.period_date)
        if source_end < source_start:
            continue
        # Preserve the established MPS-period allocation and then spread each
        # period's quantity over its dates.  Allocating directly to individual
        # days can move a rounding residual across a period boundary, changing
        # the period total (for example 42.857 to 42.856) even though the
        # source forecast quantity is unchanged.
        allocated_by_period = allocate_period_quantity(amount, source_start, source_end, buckets)
        for period_index, (bucket_start, bucket_end) in enumerate(buckets):
            period_qty = allocated_by_period[period_index]
            if not period_qty:
                continue
            daily_start = max(source_start, bucket_start)
            daily_end = min(source_end, bucket_end)
            allocated_by_day = allocate_period_quantity(period_qty, daily_start, daily_end, daily_buckets)
            for day_index, value in enumerate(allocated_by_day):
                if value:
                    forecast_by_date[(header.product_id, daily_buckets[day_index][0])] += value
                    product_ids.add(header.product_id)

    # Use the completed MRP run's demand/safety-stock snapshot so products
    # below their configured safety target are planned even without an order
    # or forecast, and policy toggles remain consistent with that source run.
    mrp_results = (await db.execute(
        select(MRPResult).where(MRPResult.run_id == run.id)
    )).scalars().all()
    mrp_by_product = {row.product_id: row for row in mrp_results}
    if run.include_safety_stock:
        active_safety_products = (await db.execute(
            select(MRPResult.product_id)
            .join(Product, Product.id == MRPResult.product_id)
            .where(
                MRPResult.run_id == run.id,
                MRPResult.safety_stock_qty > 0,
                Product.is_active.is_(True),
            )
        )).scalars().all()
        product_ids.update(active_safety_products)

    if not product_ids:
        old_lines = (await db.execute(select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(False)))).scalars().all()
        for old in old_lines:
            await db.delete(old)
        from app.services.mps_service import _refresh_plan_counters
        await _refresh_plan_counters(db, mps_id)
        await db.flush()
        return {
            "lines_created": 0, "demand_products": 0, "periods": len(buckets),
            "warehouse_id": str(warehouse.id), "source_mrp_run_id": str(run.id),
            "supply_breakdown": [], "excluded_purchase_orders": [],
        }

    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()}
    stock_rows = (await db.execute(
        select(Stock.product_id, func.sum(Stock.quantity_on_hand), func.sum(Stock.quantity_reserved), func.sum(Stock.quantity_available))
        .where(Stock.warehouse_id == warehouse.id, Stock.stock_type == StockType.PRODUCT,
               Stock.is_blocked.is_(False), Stock.product_id.in_(product_ids))
        .group_by(Stock.product_id)
    )).all()
    stock = {product_id: (decimal(on_hand), decimal(reserved), decimal(available)) for product_id, on_hand, reserved, available in stock_rows}
    for product_id, (on_hand, reserved, stored_available) in stock.items():
        product = products[product_id]
        if on_hand < 0 or reserved < 0 or reserved > on_hand or stored_available != on_hand - reserved:
            raise ValueError(
                f"Inventory quantities are inconsistent for product {product.sku} in warehouse {warehouse.code}; "
                "on-hand, reserved and available must reconcile before MPS projection"
            )

    warehouse_company_scope = Warehouse.company_id.is_(None) if warehouse.company_id is None else Warehouse.company_id == warehouse.company_id
    warehouse_scope_rows = (await db.execute(
        select(Warehouse.branch_id, func.count(Warehouse.id))
        .where(warehouse_company_scope, Warehouse.is_active.is_(True))
        .group_by(Warehouse.branch_id)
    )).all()
    warehouse_count_by_branch = {branch_id: count for branch_id, count in warehouse_scope_rows}
    warehouse_count_in_company = sum(warehouse_count_by_branch.values())

    purchase_company_scope = PurchaseOrder.company_id.is_(None) if warehouse.company_id is None else PurchaseOrder.company_id == warehouse.company_id
    po_rows = (await db.execute(
        select(PurchaseOrder.po_no, PurchaseOrder.branch_id, PurchaseOrder.expected_delivery_date,
               POLine.product_id, POLine.ordered_quantity - POLine.received_quantity, POLine.unit)
        .join(POLine, POLine.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.status.in_(_OPEN_PO_STATUSES), purchase_company_scope,
               POLine.product_id.in_(product_ids),
               POLine.ordered_quantity > POLine.received_quantity)
    )).all()
    po_supply: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    excluded_purchase_orders: list[dict[str, object]] = []
    for po_no, branch_id, due, product_id, qty, unit in po_rows:
        branch_matches = branch_id == warehouse.branch_id
        scope_is_unambiguous = (
            warehouse_count_in_company == 1
            if branch_id is None
            else branch_matches and warehouse_count_by_branch.get(branch_id, 0) == 1
        )
        if not scope_is_unambiguous:
            excluded_purchase_orders.append({
                "po_no": po_no,
                "product_id": str(product_id),
                "expected_delivery_date": due.isoformat(),
                "open_quantity": str(decimal(qty)),
                "uom": _enum_value(unit),
                "reason": "PURCHASE_ORDER_DESTINATION_AMBIGUOUS",
            })
            continue
        if due < plan.start_date or due > plan.end_date:
            excluded_purchase_orders.append({
                "po_no": po_no,
                "product_id": str(product_id),
                "expected_delivery_date": due.isoformat(),
                "open_quantity": str(decimal(qty)),
                "uom": _enum_value(unit),
                "reason": "PURCHASE_ORDER_OVERDUE" if due < plan.start_date else "PURCHASE_ORDER_AFTER_HORIZON",
            })
            continue
        product = products[product_id]
        try:
            normalized_qty = await convert_uom(db, decimal(qty), _enum_value(unit), _enum_value(product.uom))
        except HTTPException as exc:
            raise ValueError(
                f"Purchase order {po_no} UOM {_enum_value(unit)} cannot be converted to product UOM {_enum_value(product.uom)}"
            ) from exc
        po_supply[product_id][due] += decimal(normalized_qty)

    wip_rows = (await db.execute(
        select(ProductionOrder.scheduled_end, ProductionOrder.product_id,
               ProductionOrder.planned_quantity, ProductionOrder.actual_quantity,
               ProductionOrder.uom, ProductionOrder.order_no)
        .where(ProductionOrder.target_warehouse_id == warehouse.id,
               ProductionOrder.status.in_(_OPEN_PRODUCTION_STATUSES),
               ProductionOrder.product_id.in_(product_ids))
    )).all()
    wip_supply: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for due, product_id, planned, actual, unit, order_no in wip_rows:
        open_qty = max(Decimal(0), decimal(planned) - decimal(actual))
        try:
            normalized_qty = await convert_uom(db, open_qty, _enum_value(unit), _enum_value(products[product_id].uom))
        except HTTPException as exc:
            raise ValueError(
                f"Production order {order_no} UOM {_enum_value(unit)} cannot be converted to product UOM {_enum_value(products[product_id].uom)}"
            ) from exc
        due_date = due.date()
        if plan.start_date <= due_date <= plan.end_date:
            wip_supply[product_id][due_date] += decimal(normalized_qty)

    other_plans = (await db.execute(
        select(MPSLine.planned_end_date, MPSLine.product_id, MPSLine.planned_production_qty)
        .join(MPSPlan, MPSPlan.id == MPSLine.mps_id)
        .join(MRPRun, MRPRun.id == MPSPlan.mrp_run_id)
        .where(MPSLine.mps_id != mps_id, MPSPlan.status == MPSStatus.APPROVED,
               MRPRun.warehouse_id == warehouse.id,
               MPSLine.production_order_id.is_(None), MPSLine.product_id.in_(product_ids))
    )).all()
    other_supply: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for due, product_id, qty in other_plans:
        if due is not None and plan.start_date <= due <= plan.end_date:
            other_supply[product_id][due] += decimal(qty)

    locked_lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(True))
    )).scalars().all()
    locked_supply: dict[uuid.UUID, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for line in locked_lines:
        if plan.start_date <= line.period_end <= plan.end_date:
            locked_supply[line.product_id][line.period_end] += decimal(line.planned_production_qty)

    old_lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id, MPSLine.is_locked.is_(False))
    )).scalars().all()
    for old in old_lines:
        await db.delete(old)
    await db.flush()

    created = 0
    supply_breakdown: list[dict[str, object]] = []
    bucket_days_map = [
        [day_start for day_start, _ in daily_buckets if bucket_start <= day_start <= bucket_end]
        for bucket_start, bucket_end in buckets
    ]
    for product_id in sorted(product_ids, key=str):
        product = products[product_id]
        on_hand, reserved, stored_available = stock.get(product_id, (Decimal(0), Decimal(0), Decimal(0)))
        available = max(Decimal(0), on_hand - reserved)
        for index, (bucket_start, bucket_end) in enumerate(buckets):
            bucket_days = bucket_days_map[index]
            confirmed_qty = sum((confirmed_by_date[(product_id, day)] for day in bucket_days), Decimal(0))
            gross_forecast_qty = sum((forecast_by_date[(product_id, day)] for day in bucket_days), Decimal(0))
            net_forecast_qty = max(Decimal(0), gross_forecast_qty - confirmed_qty)
            net_forecast_by_date: dict[date, Decimal] = {}
            if gross_forecast_qty > 0:
                forecast_days = [day for day in bucket_days if forecast_by_date[(product_id, day)] > 0]
                allocated_net = allocate_weighted_quantity(
                    net_forecast_qty,
                    [forecast_by_date[(product_id, day)] for day in forecast_days],
                )
                if allocated_net:
                    net_forecast_by_date.update(zip(forecast_days, allocated_net))
            mrp_result = mrp_by_product.get(product_id)
            safety_target = (
                decimal(mrp_result.safety_stock_qty)
                if run.include_safety_stock and mrp_result is not None else Decimal(0)
            )
            opening_available = available
            min_projected = available
            receipt_totals = {
                "purchase_order": Decimal(0), "work_in_progress": Decimal(0),
                "approved_mps": Decimal(0), "locked_mps": Decimal(0),
            }
            dated_receipts: list[dict[str, object]] = []
            for day in bucket_days:
                day_receipts = {
                    "purchase_order": po_supply[product_id].get(day, Decimal(0)),
                    "work_in_progress": wip_supply[product_id].get(day, Decimal(0)),
                    "approved_mps": other_supply[product_id].get(day, Decimal(0)),
                    "locked_mps": locked_supply[product_id].get(day, Decimal(0)),
                }
                for source, quantity in day_receipts.items():
                    if quantity:
                        receipt_totals[source] += quantity
                        dated_receipts.append({"date": day.isoformat(), "source": source, "quantity": str(round_qty(quantity))})
                        available += quantity
                available -= confirmed_by_date[(product_id, day)] + net_forecast_by_date.get(day, Decimal(0))
                min_projected = min(min_projected, available)

            ending_before_production = available
            net_qty = max(Decimal(0), -min_projected, safety_target - ending_before_production)
            available = max(Decimal(0), ending_before_production + net_qty)
            supply_breakdown.append({
                "product_id": str(product_id),
                "period_start": bucket_start.isoformat(),
                "period_end": bucket_end.isoformat(),
                "opening_on_hand_qty": str(round_qty(on_hand)) if index == 0 else None,
                "opening_reserved_qty": str(round_qty(reserved if index == 0 else Decimal(0))),
                "opening_available_qty": str(round_qty(opening_available)),
                "confirmed_demand_qty": str(round_qty(confirmed_qty)),
                "forecast_qty": str(round_qty(net_forecast_qty)),
                "safety_stock_target_qty": str(round_qty(safety_target)),
                "incoming_purchase_order_qty": str(round_qty(receipt_totals["purchase_order"])),
                "work_in_progress_qty": str(round_qty(receipt_totals["work_in_progress"])),
                "approved_mps_supply_qty": str(round_qty(receipt_totals["approved_mps"])),
                "locked_mps_supply_qty": str(round_qty(receipt_totals["locked_mps"])),
                "planned_production_qty": str(round_qty(net_qty)),
                "projected_ending_available_qty": str(round_qty(available)),
                "dated_receipts": dated_receipts,
            })
            if net_qty <= 0:
                continue
            label = f"{bucket_start.year}-W{bucket_start.isocalendar()[1]:02d}" if period_type.upper() == "WEEKLY" else (f"{bucket_start:%Y-%m}" if period_type.upper() == "MONTHLY" else bucket_start.isoformat())
            line = MPSLine(
                line_no=f"MPS-{plan.id.hex[:8]}-{created + 1:06d}",
                mps_id=mps_id, product_id=product_id,
                mrp_result_id=mrp_result.id if mrp_result else None,
                period_label=label, period_start=bucket_start, period_end=bucket_end,
                confirmed_demand_qty=round_qty(confirmed_qty), forecast_qty=round_qty(net_forecast_qty),
                safety_stock_qty=round_qty(safety_target), net_requirement_qty=round_qty(net_qty),
                planned_production_qty=round_qty(net_qty), planned_start_date=bucket_start,
                planned_end_date=bucket_end, feasibility_status=MPSFeasibilityStatus.PENDING,
                priority_score=Decimal("50"),
                remarks="Demand projection from warehouse-scoped orders, forecasts and dated supply; supply netted by due date.",
            )
            db.add(line)
            await db.flush()
            created += 1

    await db.flush()
    from app.services.mps_service import _refresh_plan_counters
    await _refresh_plan_counters(db, mps_id)
    return {
        "lines_created": created, "demand_products": len(product_ids), "periods": len(buckets),
        "warehouse_id": str(warehouse.id), "source_mrp_run_id": str(run.id),
        "supply_breakdown": supply_breakdown,
        "excluded_purchase_orders": excluded_purchase_orders,
    }


def _constraint_provenance(reason_code: str) -> str:
    if reason_code.startswith("MATERIAL_"):
        return "warehouse stock; approved effective BOM/recipe"
    if reason_code.startswith("APPROVED_BOM") or reason_code == "BOM_DATA_INVALID":
        return "approved effective BOM and its configured components, yield, and UOM"
    if reason_code.startswith("APPROVED_RECIPE") or reason_code == "RECIPE_DATA_INVALID":
        return "approved effective recipe and its configured ingredients"
    if reason_code == "PRODUCT_MASTER_INVALID":
        return "product master data"
    if reason_code == "MPS_QUANTITY_INVALID":
        return "planned MPS line quantity"
    return "MPS material-feasibility evaluation"


def _constraint_priority(reason_code: str) -> str:
    # A material shortage is actionable but does not invalidate its BOM/master
    # data. All other evaluator reasons indicate a blocking data/input defect.
    return "HIGH" if reason_code == "MATERIAL_SHORT" else "CRITICAL"


async def evaluate_material_feasibility(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Explode effective approved BOMs, net dated material supply, and persist reasons."""
    plan, run, warehouse = await _scoped_plan(db, mps_id)
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Material feasibility evaluation is only allowed for DRAFT MPS plans")
    lines = (await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id).order_by(
            func.coalesce(MPSLine.planned_start_date, MPSLine.period_start),
            MPSLine.priority_score.desc(), MPSLine.line_no,
        )
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

    # Load the approved child-BOM closure referenced by the selected root BOMs.
    # The engine enforces date effectivity, lifecycle, UOM, depth and cycles;
    # this loader deliberately omits absent/unapproved child rows so the
    # material feasibility result fails closed with a traceable BOM error.
    child_boms: dict[str, dict] = {}
    pending_child_ids = {
        item.child_bom_id for item in bom_items if item.child_bom_id is not None
    }
    visited_child_ids: set[uuid.UUID] = set()
    for _depth in range(16):
        batch_ids = pending_child_ids - visited_child_ids
        if not batch_ids:
            break
        visited_child_ids.update(batch_ids)
        child_headers = (await db.execute(
            select(AdvancedBOM).where(
                AdvancedBOM.id.in_(batch_ids),
                AdvancedBOM.lifecycle.in_((BOMLifecycle.APPROVED, BOMLifecycle.RELEASED)),
            )
        )).scalars().all()
        child_lines = (await db.execute(
            select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id.in_(batch_ids))
        )).scalars().all()
        child_lines_by_id: dict[uuid.UUID, list[AdvancedBOMLine]] = defaultdict(list)
        for child_line in child_lines:
            child_lines_by_id[child_line.bom_id].append(child_line)
        pending_child_ids = set()
        for child_header in child_headers:
            lines_for_child = child_lines_by_id.get(child_header.id, [])
            child_boms[str(child_header.id)] = {
                "bom": {
                    "id": child_header.id,
                    "base_qty": child_header.base_qty,
                    "base_uom": child_header.base_uom,
                    "lifecycle": child_header.lifecycle,
                    "effective_from": child_header.effective_from,
                    "effective_to": child_header.effective_to,
                },
                "lines": [{
                    "item_id": item.item_id, "item_type": item.item_type,
                    "required_qty": item.required_qty, "required_uom": item.required_uom,
                    "basis_type": item.basis_type, "wastage_pct": item.wastage_pct,
                    "process_loss_pct": item.process_loss_pct,
                    "is_optional": item.is_optional,
                    "substitution_policy": item.substitution_policy,
                    "substitute_group_id": item.substitute_group_id,
                    "child_bom_id": item.child_bom_id,
                } for item in lines_for_child],
            }
            pending_child_ids.update(
                item.child_bom_id for item in lines_for_child if item.child_bom_id is not None
            )

    loaded_bom_ids = bom_ids | {
        uuid.UUID(bom_id) for bom_id in child_boms
    }
    yield_configs_by_bom: dict[uuid.UUID, list[BOMYieldConfig]] = defaultdict(list)
    if loaded_bom_ids:
        yield_configs = (await db.execute(
            select(BOMYieldConfig).where(BOMYieldConfig.bom_id.in_(loaded_bom_ids))
        )).scalars().all()
        for config in yield_configs:
            yield_configs_by_bom[config.bom_id].append(config)
    for child_id, child in child_boms.items():
        try:
            child["bom"]["yield_loss_pct"] = _configured_bom_yield_loss(yield_configs_by_bom.get(uuid.UUID(child_id), []))
        except PlanningInputError as exc:
            child["bom"]["yield_config_error"] = str(exc)

    material_ids = {item.material_id for item in recipe_items} | {
        item.item_id for item in bom_items
        if _enum_value(item.item_type) == "MATERIAL" and item.item_id
    } | {
        item["item_id"] for children in child_boms.values() for item in children["lines"]
        if _enum_value(item.get("item_type")) == "MATERIAL" and item.get("item_id")
    }
    materials = {m.id: m for m in (await db.execute(select(Material).where(Material.id.in_(material_ids)))).scalars().all()} if material_ids else {}
    stock_rows = (await db.execute(
        select(Stock.material_id, Stock.quantity_on_hand, Stock.quantity_reserved, Stock.quantity_available)
        .where(Stock.warehouse_id == warehouse.id, Stock.stock_type == StockType.MATERIAL,
               Stock.is_blocked.is_(False), Stock.material_id.in_(material_ids))
    )).all() if material_ids else []
    material_stock: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    invalid_stock_materials: set[uuid.UUID] = set()
    for material_id, on_hand_value, reserved_value, available_value in stock_rows:
        on_hand, reserved, available = map(decimal, (on_hand_value, reserved_value, available_value))
        if on_hand < 0 or reserved < 0 or reserved > on_hand or available != on_hand - reserved:
            invalid_stock_materials.add(material_id)
            continue
        material_stock[material_id] += available
    remaining = dict(material_stock)

    warehouse_company_scope = Warehouse.company_id.is_(None) if warehouse.company_id is None else Warehouse.company_id == warehouse.company_id
    warehouse_scope_rows = (await db.execute(
        select(Warehouse.branch_id, func.count(Warehouse.id))
        .where(warehouse_company_scope, Warehouse.is_active.is_(True))
        .group_by(Warehouse.branch_id)
    )).all()
    warehouse_count_by_branch = {branch_id: count for branch_id, count in warehouse_scope_rows}
    warehouse_count_in_company = sum(warehouse_count_by_branch.values())

    company_filter = PurchaseOrder.company_id.is_(None) if warehouse.company_id is None else PurchaseOrder.company_id == warehouse.company_id
    material_po_rows = (await db.execute(
        select(PurchaseOrder.po_no, PurchaseOrder.branch_id, PurchaseOrder.expected_delivery_date, POLine.material_id,
               POLine.ordered_quantity - POLine.received_quantity, POLine.unit)
        .join(POLine, POLine.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.status.in_(_OPEN_PO_STATUSES), company_filter,
               POLine.material_id.in_(material_ids),
               POLine.ordered_quantity > POLine.received_quantity)
    )).all() if material_ids else []
    material_receipts: dict[uuid.UUID, list[tuple[date, Decimal, str]]] = defaultdict(list)
    excluded_material_receipts: dict[uuid.UUID, list[dict[str, str]]] = defaultdict(list)
    for po_no, branch_id, due, material_id, qty_value, unit in material_po_rows:
        branch_matches = branch_id == warehouse.branch_id
        scope_is_unambiguous = (
            warehouse_count_in_company == 1
            if branch_id is None
            else branch_matches and warehouse_count_by_branch.get(branch_id, 0) == 1
        )
        if not scope_is_unambiguous:
            excluded_material_receipts[material_id].append({
                "po_no": po_no, "due_date": due.isoformat(),
                "reason": "PURCHASE_ORDER_DESTINATION_AMBIGUOUS",
            })
            continue
        if material_id not in materials:
            continue
        try:
            normalized_qty = await convert_uom(
                db, decimal(qty_value), _enum_value(unit), _enum_value(materials[material_id].uom),
            )
        except (HTTPException, MultipleResultsFound):
            excluded_material_receipts[material_id].append({
                "po_no": po_no, "due_date": due.isoformat(),
                "reason": "PURCHASE_ORDER_UOM_UNCONVERTIBLE",
            })
            continue
        material_receipts[material_id].append((due, decimal(normalized_qty), _enum_value(materials[material_id].uom)))
    prior_material_receipts: dict[uuid.UUID, Decimal] = defaultdict(Decimal)

    issues_by_line: dict[uuid.UUID, list[dict]] = defaultdict(list)
    diagnostics_to_write: list[tuple[uuid.UUID, dict]] = []
    for line in lines:
        product = products.get(line.product_id)
        if product is None or not product.is_active:
            issues_by_line[line.id].append({"reason_code": "PRODUCT_MASTER_INVALID", "priority": "CRITICAL"})
            continue
        material_needs: list[dict] = []
        required_date = line.planned_start_date or line.period_start
        if decimal(line.planned_production_qty) < 0:
            issues_by_line[line.id].append({
                "reason_code": "MPS_QUANTITY_INVALID", "priority": "CRITICAL",
                "planned_production_qty": str(line.planned_production_qty),
            })
            continue
        effective_boms = [candidate for candidate in boms_by_product.get(line.product_id, [])
                          if (candidate.effective_from is None or candidate.effective_from <= required_date)
                          and (candidate.effective_to is None or candidate.effective_to >= required_date)]
        if len(effective_boms) > 1:
            issues_by_line[line.id].append({
                "reason_code": "APPROVED_BOM_AMBIGUOUS", "priority": "CRITICAL",
                "bom_ids": [str(candidate.id) for candidate in effective_boms],
                "required_date": required_date.isoformat(),
            })
            continue
        bom = effective_boms[0] if effective_boms else None
        if bom:
            bom_uom = _enum_value(bom.base_uom)
            try:
                output_qty = await convert_uom(
                    db, decimal(line.planned_production_qty), _enum_value(product.uom), bom_uom,
                )
                yield_loss_pct = _configured_bom_yield_loss(yield_configs_by_bom.get(bom.id, []))
                material_needs = explode_approved_bom(
                    output_qty=output_qty,
                    output_uom=bom_uom,
                    bom={"id": bom.id, "base_qty": bom.base_qty, "base_uom": bom.base_uom, "output_uom": product.uom, "lifecycle": bom.lifecycle, "yield_loss_pct": yield_loss_pct},
                    lines=[{
                        "item_id": item.item_id, "item_type": item.item_type,
                        "required_qty": item.required_qty, "required_uom": item.required_uom,
                        "basis_type": item.basis_type, "wastage_pct": item.wastage_pct,
                        "process_loss_pct": item.process_loss_pct,
                        "is_optional": item.is_optional,
                        "substitution_policy": item.substitution_policy,
                        "substitute_group_id": item.substitute_group_id,
                        "child_bom_id": item.child_bom_id,
                    } for item in bom_items_by_id[bom.id]],
                    child_boms=child_boms,
                    as_of=required_date,
                )
            except (PlanningInputError, HTTPException, MultipleResultsFound) as exc:
                issues_by_line[line.id].append({"reason_code": "BOM_DATA_INVALID", "message": str(exc), "priority": "CRITICAL", "bom_id": str(bom.id)})
        else:
            effective_recipes = [candidate for candidate in recipes_by_product.get(line.product_id, [])
                                 if (candidate.valid_from is None or candidate.valid_from <= required_date)
                                 and (candidate.valid_to is None or candidate.valid_to >= required_date)]
            if len(effective_recipes) > 1:
                issues_by_line[line.id].append({
                    "reason_code": "APPROVED_RECIPE_AMBIGUOUS", "priority": "CRITICAL",
                    "recipe_ids": [str(candidate.id) for candidate in effective_recipes],
                    "required_date": required_date.isoformat(),
                })
                continue
            recipe = effective_recipes[0] if effective_recipes else None
            if recipe is None:
                issues_by_line[line.id].append({"reason_code": "APPROVED_BOM_MISSING", "message": "No effective approved BOM or recipe covers the planned date.", "priority": "CRITICAL"})
                continue
            recipe_data_invalid = False
            for item in recipe_items_by_id[recipe.id]:
                recipe_qty = decimal(item.quantity)
                loss_percentage = decimal(item.loss_percentage)
                if recipe_qty < 0 or loss_percentage < 0 or loss_percentage >= 100:
                    issues_by_line[line.id].append({
                        "reason_code": "RECIPE_DATA_INVALID", "priority": "CRITICAL",
                        "recipe_id": str(recipe.id), "recipe_item_id": str(item.id),
                    })
                    recipe_data_invalid = True
                    break
                material_needs.append({
                    "material_id": item.material_id,
                    "required_qty": round_qty(recipe_qty * decimal(line.planned_production_qty) * (Decimal(1) + loss_percentage / Decimal(100)), 4),
                    "uom": _enum_value(item.unit),
                    "substitution_policy": "NO_SUB",
                })
            if recipe_data_invalid:
                continue

        for need in material_needs:
            material_id = need["material_id"]
            material = materials.get(material_id)
            if material is None or not material.is_active or material.lead_time_days is None or material.lead_time_days < 0:
                issues_by_line[line.id].append({"reason_code": "MATERIAL_MASTER_INVALID", "material_id": str(material_id), "priority": "CRITICAL"})
                continue
            required_uom = str(need.get("uom") or "").upper()
            material_uom = _enum_value(material.uom)
            try:
                if not required_uom:
                    raise HTTPException(status_code=422, detail="Material requirement has no UOM")
                need_qty = round_qty(
                    decimal(await convert_uom(db, decimal(need["required_qty"]), required_uom, material_uom)),
                    4,
                )
            except (HTTPException, MultipleResultsFound) as exc:
                message = exc.detail if isinstance(exc, HTTPException) else "Multiple active UOM conversion rows match this material requirement"
                issues_by_line[line.id].append({"reason_code": "MATERIAL_UOM_MISMATCH", "material_id": str(material_id), "required_uom": required_uom, "material_uom": material_uom, "message": str(message), "priority": "CRITICAL"})
                continue
            if material_id in invalid_stock_materials:
                issues_by_line[line.id].append({
                    "reason_code": "MATERIAL_STOCK_INVALID", "material_id": str(material_id),
                    "material_code": material.code, "priority": "CRITICAL",
                })
                continue
            due_receipts = Decimal(0)
            for due, qty, unit in material_receipts.get(material_id, []):
                if due <= required_date:
                    due_receipts += qty
            newly_available = max(Decimal(0), due_receipts - prior_material_receipts[material_id])
            prior_material_receipts[material_id] = max(prior_material_receipts[material_id], due_receipts)
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
                    "uom": material_uom,
                    "required_date": line.planned_start_date.isoformat() if line.planned_start_date else line.period_start.isoformat(),
                    "lead_time_days": material.lead_time_days,
                    "latest_order_date": (required_date - timedelta(days=material.lead_time_days)).isoformat(),
                    "substitution_policy": _enum_value(need.get("substitution_policy")) or "NO_SUB",
                    "substitute_group_id": str(need["substitute_group_id"]) if need.get("substitute_group_id") else None,
                    "excluded_receipts": [receipt for receipt in excluded_material_receipts.get(material_id, [])
                                          if date.fromisoformat(receipt["due_date"]) <= required_date],
                    "provenance": "warehouse stock; approved effective BOM/recipe",
                    "priority": "HIGH",
                })

    for line in lines:
        issues = issues_by_line[line.id]
        required_date = line.planned_start_date or line.period_start
        for issue in issues:
            reason_code = str(issue.get("reason_code") or "MPS_CONSTRAINT_UNKNOWN")
            issue.setdefault("required_date", required_date.isoformat())
            issue.setdefault("planned_quantity", str(line.planned_production_qty))
            issue.setdefault("priority", _constraint_priority(reason_code))
            issue.setdefault("provenance", _constraint_provenance(reason_code))
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
            "line_no": line.line_no,
            "planned_quantity": str(line.planned_production_qty),
            "required_date": required_date.isoformat(),
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


async def _write_diagnostics(
    db: AsyncSession,
    mps_id: uuid.UUID,
    rows: list[tuple[uuid.UUID, dict]],
    *,
    source_version: str = "mps-diagnostics.v1",
    supersede_current: bool = False,
) -> uuid.UUID:
    run_id = uuid.uuid4()
    if supersede_current:
        await db.execute(text(
            "UPDATE mps_line_diagnostics "
            "SET diagnostics = jsonb_set("
            "  jsonb_set(diagnostics, '{recalculation_state}', to_jsonb('SUPERSEDED'::text), true), "
            "  '{superseded_by_run_id}', to_jsonb(CAST(:run_id AS text)), true) "
            "WHERE mps_id = :mps_id AND source_version = :source_version "
            "  AND diagnostics->>'recalculation_state' IN ('CURRENT', 'NOT_APPLICABLE')"
        ), {"mps_id": mps_id, "source_version": source_version, "run_id": str(run_id)})
    for line_id, body in rows:
        body["run_id"] = str(run_id)
        await db.execute(text(
            "INSERT INTO mps_line_diagnostics (id, mps_id, line_id, run_id, source_version, diagnostics) "
            "VALUES (:id, :mps_id, :line_id, :run_id, :source_version, CAST(:diagnostics AS JSONB))"
        ), {
            "id": uuid.uuid4(), "mps_id": mps_id, "line_id": line_id,
            "run_id": run_id, "source_version": source_version,
            "diagnostics": json.dumps(body, default=str),
        })
    return run_id


async def list_plan_diagnostics(db: AsyncSession, mps_id: uuid.UUID) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT d.line_id, d.run_id, d.source_version, d.diagnostics, d.computed_at, "
        "l.line_no, l.planned_production_qty, COALESCE(l.planned_start_date, l.period_start) AS required_date "
        "FROM mps_line_diagnostics AS d JOIN mps_lines AS l ON l.id = d.line_id AND l.mps_id = d.mps_id "
        "WHERE d.mps_id = :mps_id ORDER BY d.computed_at DESC, d.line_id"
    ), {"mps_id": mps_id})).mappings().all()
    result = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for row in rows:
        key = (row["run_id"], row["line_id"])
        if key in seen:
            continue
        seen.add(key)
        diagnostic = dict(row["diagnostics"])
        diagnostic.setdefault("line_no", row["line_no"])
        diagnostic.setdefault("planned_quantity", str(row["planned_production_qty"]))
        diagnostic.setdefault("required_date", row["required_date"].isoformat())
        for issue in diagnostic.get("issues", []):
            reason_code = str(issue.get("reason_code") or "MPS_CONSTRAINT_UNKNOWN")
            issue.setdefault("planned_quantity", str(row["planned_production_qty"]))
            issue.setdefault("required_date", row["required_date"].isoformat())
            issue.setdefault("priority", _constraint_priority(reason_code))
            issue.setdefault("provenance", _constraint_provenance(reason_code))
        result.append({
            "line_id": str(row["line_id"]), "run_id": str(row["run_id"]),
            "source_version": row["source_version"], "diagnostics": diagnostic,
            "computed_at": row["computed_at"].isoformat() if row["computed_at"] else None,
        })
    return result
