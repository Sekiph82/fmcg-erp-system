"""
MRP Engine Service
──────────────────
Flow: Demand Consolidation → Net Requirements → BOM Explosion → Suggestions
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Stock, StockType, Lot
from app.models.master import Product, Material
from app.models.mrp import (
    DemandForecast, DemandForecastLine,
    MRPResult, MRPRun, MRPRunStatus, MRPSuggestion,
    SuggestionStatus, SuggestionType,
)
from app.models.procurement import (
    POStatus, PurchaseOrder, POLine,
    PurchaseRequisition, PRLine, PRStatus,
)
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.sales import SalesOrder, SOLine, SOStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    q = Decimal("0." + "0" * dp)
    return v.quantize(q, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _run_no() -> str:
    from datetime import date as _date
    d = _date.today().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:6].upper()
    return f"MRP-{d}-{short}"


# ── Supply / demand helpers ───────────────────────────────────────────────────

async def _build_so_demand(
    db: AsyncSession,
    run_date: date,
    horizon_date: date,
    warehouse_id: Optional[UUID],
) -> dict[UUID, Decimal]:
    """Aggregate unshipped confirmed SO quantity per product."""
    q = (
        select(
            SOLine.product_id,
            func.sum(SOLine.ordered_quantity - SOLine.shipped_quantity).label("qty"),
        )
        .join(SalesOrder, SOLine.so_id == SalesOrder.id)
        .where(
            SalesOrder.status.in_([
                SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING,
            ]),
            SalesOrder.requested_delivery_date <= horizon_date,
            SalesOrder.requested_delivery_date >= run_date,
        )
        .group_by(SOLine.product_id)
    )
    if warehouse_id:
        q = q.where(SalesOrder.warehouse_id == warehouse_id)
    rows = (await db.execute(q)).all()
    return {r.product_id: max(Decimal("0"), _D(r.qty)) for r in rows}


async def _build_forecast_demand(
    db: AsyncSession,
    run_date: date,
    horizon_date: date,
) -> dict[UUID, Decimal]:
    """Sum approved/draft forecast quantities per product in the planning horizon."""
    q = (
        select(
            DemandForecast.product_id,
            func.sum(
                func.coalesce(DemandForecastLine.adjusted_qty, DemandForecastLine.forecast_qty)
            ).label("qty"),
        )
        .join(DemandForecastLine, DemandForecastLine.forecast_id == DemandForecast.id)
        .where(
            DemandForecastLine.period_date >= run_date,
            DemandForecastLine.period_date <= horizon_date,
        )
        .group_by(DemandForecast.product_id)
    )
    rows = (await db.execute(q)).all()
    return {r.product_id: _D(r.qty) for r in rows}


async def _build_product_stock_map(
    db: AsyncSession,
    warehouse_id: Optional[UUID],
) -> dict[UUID, Decimal]:
    """Available product stock (excluding blocked, QC hold, expired lots)."""
    today = date.today()
    q = (
        select(
            Stock.product_id,
            func.sum(Stock.quantity_available).label("qty"),
        )
        .outerjoin(Lot, Stock.lot_id == Lot.id)
        .where(
            Stock.stock_type == StockType.PRODUCT,
            Stock.is_blocked == False,
            Stock.product_id.isnot(None),
        )
        .where(
            # Exclude expired lots
            (Lot.expiry_date.is_(None)) | (Lot.expiry_date > today)
        )
        .where(
            # Exclude QC hold lots
            (Lot.is_quarantine.is_(None)) | (Lot.is_quarantine == False)
        )
        .group_by(Stock.product_id)
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)
    rows = (await db.execute(q)).all()
    return {r.product_id: max(Decimal("0"), _D(r.qty)) for r in rows}


async def _build_material_stock_map(
    db: AsyncSession,
    warehouse_id: Optional[UUID],
) -> dict[UUID, Decimal]:
    """Available material stock (excluding blocked / QC hold / expired)."""
    today = date.today()
    q = (
        select(
            Stock.material_id,
            func.sum(Stock.quantity_available).label("qty"),
        )
        .outerjoin(Lot, Stock.lot_id == Lot.id)
        .where(
            Stock.stock_type == StockType.MATERIAL,
            Stock.is_blocked == False,
            Stock.material_id.isnot(None),
        )
        .where(
            (Lot.expiry_date.is_(None)) | (Lot.expiry_date > today)
        )
        .where(
            (Lot.is_quarantine.is_(None)) | (Lot.is_quarantine == False)
        )
        .group_by(Stock.material_id)
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)
    rows = (await db.execute(q)).all()
    return {r.material_id: max(Decimal("0"), _D(r.qty)) for r in rows}


async def _build_incoming_po_map(
    db: AsyncSession,
    horizon_date: date,
    warehouse_id: Optional[UUID],
) -> dict[UUID, Decimal]:
    """Open PO remaining qty per product due within horizon."""
    q = (
        select(
            POLine.product_id,
            func.sum(POLine.ordered_quantity - POLine.received_quantity).label("qty"),
        )
        .join(PurchaseOrder, POLine.po_id == PurchaseOrder.id)
        .where(
            POLine.product_id.isnot(None),
            PurchaseOrder.status.in_([
                POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED,
            ]),
            PurchaseOrder.expected_delivery_date <= horizon_date,
        )
        .group_by(POLine.product_id)
    )
    rows = (await db.execute(q)).all()
    return {r.product_id: max(Decimal("0"), _D(r.qty)) for r in rows}


async def _build_incoming_material_po_map(
    db: AsyncSession,
    horizon_date: date,
) -> dict[UUID, Decimal]:
    """Open PO remaining qty per material due within horizon."""
    q = (
        select(
            POLine.material_id,
            func.sum(POLine.ordered_quantity - POLine.received_quantity).label("qty"),
        )
        .join(PurchaseOrder, POLine.po_id == PurchaseOrder.id)
        .where(
            POLine.material_id.isnot(None),
            PurchaseOrder.status.in_([
                POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED,
            ]),
            PurchaseOrder.expected_delivery_date <= horizon_date,
        )
        .group_by(POLine.material_id)
    )
    rows = (await db.execute(q)).all()
    return {r.material_id: max(Decimal("0"), _D(r.qty)) for r in rows}


async def _build_incoming_prod_map(
    db: AsyncSession,
    horizon_date: date,
) -> dict[UUID, Decimal]:
    """Open production orders target qty per product due within horizon."""
    q = (
        select(
            ProductionOrder.product_id,
            func.sum(ProductionOrder.target_quantity).label("qty"),
        )
        .where(
            ProductionOrder.status.in_([
                ProductionOrderStatus.PLANNED,
                ProductionOrderStatus.RELEASED,
                ProductionOrderStatus.IN_PROGRESS,
            ]),
        )
        .group_by(ProductionOrder.product_id)
    )
    rows = (await db.execute(q)).all()
    return {r.product_id: _D(r.qty) for r in rows}


# ── BOM Explosion ─────────────────────────────────────────────────────────────

async def _explode_bom(
    db: AsyncSession,
    product_id: UUID,
    qty_needed: Decimal,
) -> list[tuple[UUID, Decimal, str]]:
    """
    Single-level BOM explosion.
    Returns list of (material_id, gross_qty_needed, uom).
    """
    recipe_q = await db.execute(
        select(Recipe)
        .where(
            Recipe.product_id == product_id,
            Recipe.is_active == True,
            Recipe.status == RecipeStatus.APPROVED,
        )
        .order_by(Recipe.valid_from.desc().nullslast())
        .limit(1)
    )
    recipe = recipe_q.scalar_one_or_none()
    if not recipe:
        return []

    items_q = await db.execute(
        select(RecipeItem, Material.lead_time_days, Material.reorder_point,
               Material.supplier_id, Material.uom)
        .join(Material, RecipeItem.material_id == Material.id)
        .where(
            RecipeItem.recipe_id == recipe.id,
            RecipeItem.is_optional == False,
        )
    )
    items = items_q.all()

    requirements = []
    for row in items:
        item = row.RecipeItem
        loss_factor = Decimal("1") + _D(item.loss_percentage) / Decimal("100")
        material_need = _R(_D(item.quantity) * qty_needed * loss_factor)
        uom = str(item.unit)
        requirements.append((item.material_id, material_need, uom))

    return requirements


# ── PR / Production Order generation ─────────────────────────────────────────

async def _next_pr_no(db: AsyncSession) -> str:
    count = (await db.execute(select(func.count()).select_from(PurchaseRequisition))).scalar() or 0
    return f"MRP-PR-{count + 1:05d}"


async def _next_po_no(db: AsyncSession) -> str:
    count = (await db.execute(select(func.count()).select_from(ProductionOrder))).scalar() or 0
    return f"MRP-PO-{count + 1:05d}"


async def convert_suggestion_to_pr(
    db: AsyncSession,
    suggestion: MRPSuggestion,
    requester_id: UUID,
) -> PurchaseRequisition:
    pr_no = await _next_pr_no(db)
    pr = PurchaseRequisition(
        pr_no=pr_no,
        requester_id=requester_id,
        required_date=suggestion.required_date,
        notes=f"Auto-generated from MRP run. Suggestion ID: {suggestion.id}",
        status=PRStatus.DRAFT,
    )
    db.add(pr)
    await db.flush()

    line = PRLine(
        pr_id=pr.id,
        line_no=1,
        material_id=suggestion.material_id,
        product_id=suggestion.product_id,
        quantity=suggestion.suggested_qty,
        unit=suggestion.uom or "KG",
        estimated_unit_cost=None,
        preferred_supplier_id=suggestion.preferred_supplier_id,
        notes=f"MRP-driven requirement",
    )
    db.add(line)

    suggestion.status = SuggestionStatus.CONVERTED
    suggestion.converted_pr_id = pr.id
    await db.flush()
    return pr


async def convert_suggestion_to_production_order(
    db: AsyncSession,
    suggestion: MRPSuggestion,
    created_by_id: UUID,
) -> ProductionOrder:
    from app.models.production import ProductionPlan, ProductionPlanLine, ProductionPlanStatus

    # Find active recipe
    recipe_q = await db.execute(
        select(Recipe)
        .where(
            Recipe.product_id == suggestion.product_id,
            Recipe.is_active == True,
            Recipe.status == RecipeStatus.APPROVED,
        )
        .limit(1)
    )
    recipe = recipe_q.scalar_one_or_none()

    order_no = await _next_po_no(db)
    product = await db.get(Product, suggestion.product_id)

    order = ProductionOrder(
        order_no=order_no,
        plan_line_id=None,
        product_id=suggestion.product_id,
        recipe_id=recipe.id if recipe else None,
        target_quantity=suggestion.suggested_qty,
        uom=suggestion.uom or (str(product.uom) if product else "PCS"),
        target_warehouse_id=None,
        planned_date=datetime.combine(suggestion.planned_start_date or suggestion.required_date,
                                       datetime.min.time()).replace(tzinfo=timezone.utc),
        status=ProductionOrderStatus.PLANNED,
        created_by=created_by_id,
    )
    db.add(order)

    suggestion.status = SuggestionStatus.CONVERTED
    suggestion.converted_production_order_id = order.id
    await db.flush()
    return order


# ── Main MRP Engine ────────────────────────────────────────────────────────────

async def create_mrp_run(
    db: AsyncSession,
    *,
    planning_horizon_days: int = 90,
    include_forecast: bool = True,
    include_safety_stock: bool = True,
    warehouse_id: Optional[UUID] = None,
    triggered_by_id: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> MRPRun:
    run = MRPRun(
        run_no=_run_no(),
        run_date=date.today(),
        planning_horizon_days=planning_horizon_days,
        include_forecast=include_forecast,
        include_safety_stock=include_safety_stock,
        warehouse_id=warehouse_id,
        triggered_by_id=triggered_by_id,
        notes=notes,
    )
    db.add(run)
    await db.flush()
    return run


async def execute_mrp_run(db: AsyncSession, run_id: UUID) -> MRPRun:
    run = await db.get(MRPRun, run_id)
    if not run:
        raise ValueError(f"MRP run {run_id} not found")
    if run.status not in (MRPRunStatus.QUEUED,):
        raise ValueError(f"Run {run.run_no} is in status {run.status}, cannot execute")

    run.status = MRPRunStatus.RUNNING
    run.started_at = _now()
    await db.flush()

    try:
        await _do_mrp(db, run)
        run.status = MRPRunStatus.COMPLETED
    except Exception as exc:
        run.status = MRPRunStatus.FAILED
        run.error_message = str(exc)[:1000]
        run.completed_at = _now()
        await db.flush()
        raise

    run.completed_at = _now()
    await db.flush()
    return run


async def _do_mrp(db: AsyncSession, run: MRPRun) -> None:
    horizon_date = run.run_date + timedelta(days=run.planning_horizon_days)

    # ── 1. Build demand maps ──────────────────────────────────────────────────
    so_demand = await _build_so_demand(db, run.run_date, horizon_date, run.warehouse_id)

    forecast_demand: dict[UUID, Decimal] = {}
    if run.include_forecast:
        forecast_demand = await _build_forecast_demand(db, run.run_date, horizon_date)

    # ── 2. Build supply maps ──────────────────────────────────────────────────
    product_stock  = await _build_product_stock_map(db, run.warehouse_id)
    material_stock = await _build_material_stock_map(db, run.warehouse_id)
    incoming_po    = await _build_incoming_po_map(db, horizon_date, run.warehouse_id)
    incoming_mat_po = await _build_incoming_material_po_map(db, horizon_date)
    incoming_prod  = await _build_incoming_prod_map(db, horizon_date)

    # ── 3. Get all active products ────────────────────────────────────────────
    products_raw = (await db.execute(
        select(Product).where(Product.is_active == True)
    )).scalars().all()
    product_map = {p.id: p for p in products_raw}

    # Relevant products: anything with demand or below reorder point
    relevant_ids: set[UUID] = set(so_demand.keys()) | set(forecast_demand.keys())
    for p in products_raw:
        if _D(p.reorder_point) > 0:
            available = product_stock.get(p.id, Decimal("0"))
            if available <= _D(p.reorder_point):
                relevant_ids.add(p.id)

    # ── 4. Net requirements per product ──────────────────────────────────────
    results: list[MRPResult] = []
    production_suggestions: list[MRPSuggestion] = []

    for pid in relevant_ids:
        product = product_map.get(pid)
        if not product:
            continue

        so_qty  = so_demand.get(pid, Decimal("0"))
        fc_qty  = forecast_demand.get(pid, Decimal("0"))
        # SO overrides forecast when larger
        demand_qty = max(so_qty, fc_qty)

        safety = _D(product.reorder_point) if run.include_safety_stock else Decimal("0")
        gross_demand = demand_qty + safety

        stock_qty  = product_stock.get(pid, Decimal("0"))
        po_qty     = incoming_po.get(pid, Decimal("0"))
        prod_qty   = incoming_prod.get(pid, Decimal("0"))
        total_supply = stock_qty + po_qty + prod_qty

        net_req = max(Decimal("0"), gross_demand - total_supply)
        shortage = net_req > 0

        result = MRPResult(
            run_id=run.id,
            product_id=pid,
            so_demand_qty=so_qty,
            forecast_demand_qty=fc_qty,
            safety_stock_qty=safety,
            gross_demand_qty=gross_demand,
            stock_on_hand_qty=stock_qty,
            incoming_po_qty=po_qty,
            incoming_prod_qty=prod_qty,
            total_supply_qty=total_supply,
            net_requirement_qty=net_req,
            shortage_flag=shortage,
            suggested_production_qty=_R(net_req) if shortage else None,
        )
        db.add(result)
        results.append(result)

        if shortage:
            # Production suggestion for finished product
            required = horizon_date
            # Push required_date earlier based on first SO due date
            # (simplified: use horizon; detailed scheduling in MPS phase)
            sug = MRPSuggestion(
                run_id=run.id,
                suggestion_type=SuggestionType.PRODUCTION,
                product_id=pid,
                material_id=None,
                suggested_qty=_R(net_req),
                uom=str(product.uom) if product.uom else "PCS",
                required_date=required,
                planned_start_date=required - timedelta(days=7),
                driver_product_id=pid,
                net_requirement_qty=_R(net_req),
            )
            db.add(sug)
            production_suggestions.append(sug)

    await db.flush()

    # ── 5. BOM explosion for each production suggestion ───────────────────────
    mat_requirements: dict[UUID, Decimal] = {}   # material_id → total qty needed
    mat_uom_map:      dict[UUID, str]     = {}
    mat_driver_map:   dict[UUID, UUID]    = {}   # material_id → driver product_id

    for sug in production_suggestions:
        if not sug.product_id:
            continue
        bom = await _explode_bom(db, sug.product_id, sug.suggested_qty)
        for mat_id, mat_qty, mat_uom in bom:
            existing = mat_requirements.get(mat_id, Decimal("0"))
            mat_requirements[mat_id] = existing + mat_qty
            mat_uom_map[mat_id] = mat_uom
            if mat_id not in mat_driver_map:
                mat_driver_map[mat_id] = sug.product_id

    # ── 6. Procurement suggestions for material shortages ─────────────────────
    procurement_suggestions: list[MRPSuggestion] = []

    if mat_requirements:
        materials_q = await db.execute(
            select(Material).where(Material.id.in_(list(mat_requirements.keys())))
        )
        materials = {m.id: m for m in materials_q.scalars().all()}

        for mat_id, total_needed in mat_requirements.items():
            mat_avail    = material_stock.get(mat_id, Decimal("0"))
            mat_incoming = incoming_mat_po.get(mat_id, Decimal("0"))
            net_mat      = max(Decimal("0"), total_needed - mat_avail - mat_incoming)

            if net_mat <= 0:
                continue

            mat = materials.get(mat_id)
            lead_days    = int(mat.lead_time_days) if mat else 14
            moq          = Decimal("0")
            supplier_id  = mat.supplier_id if mat else None
            est_cost     = _R(net_mat * _D(mat.standard_cost)) if mat and mat.standard_cost else None
            mat_uom      = mat_uom_map.get(mat_id, str(mat.uom) if mat else "KG")

            # Apply MOQ if defined
            order_qty = max(net_mat, moq) if moq > 0 else net_mat

            required = horizon_date
            order_by = required - timedelta(days=lead_days)

            proc_sug = MRPSuggestion(
                run_id=run.id,
                suggestion_type=SuggestionType.PROCUREMENT,
                product_id=None,
                material_id=mat_id,
                suggested_qty=_R(order_qty),
                uom=mat_uom,
                required_date=required,
                planned_start_date=order_by,
                driver_product_id=mat_driver_map.get(mat_id),
                net_requirement_qty=_R(net_mat),
                moq=moq if moq > 0 else None,
                preferred_supplier_id=supplier_id,
                estimated_cost=est_cost,
            )
            db.add(proc_sug)
            procurement_suggestions.append(proc_sug)

    await db.flush()

    # ── 7. Update run totals ──────────────────────────────────────────────────
    run.product_count    = len(results)
    run.shortage_count   = sum(1 for r in results if r.shortage_flag)
    run.suggestion_count = len(production_suggestions) + len(procurement_suggestions)
    await db.flush()
