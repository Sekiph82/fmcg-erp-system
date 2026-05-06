"""
Production Costing Engine
─────────────────────────
Computes actual production costs per order by aggregating:

  1. Material cost   – Σ (actual_quantity × material.standard_cost) per MaterialConsumption
  2. Labor cost      – Σ (hours_worked × work_center.labor_rate_per_hour) per LaborLog
  3. Machine cost    – Σ (duration_min/60 × work_center.machine_cost_per_hour) per WorkOrder
  4. Energy cost     – Σ total_cost from utility_transactions WHERE batch_id = order.batch_no
                       OR production_order_id reference in notes (best-effort)

All monetary values in KES.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production import (
    ProductionOrder, MaterialConsumption, FinishedGoodsReceipt,
    ProductionOrderStatus,
)
from app.models.production_advanced import WorkOrder, LaborLog
from app.models.master import Material, Product
from app.models.utility_management import UtilityTransaction


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Core: compute cost for a single order ────────────────────────────────────

async def compute_order_cost(
    db: AsyncSession,
    order: ProductionOrder,
) -> dict:
    """
    Compute full cost breakdown for one ProductionOrder.
    Returns a dict of cost components (does NOT flush/commit).
    """

    # 1. Material cost
    # ─────────────────────────────────────────────────────────────────────────
    mat_q = await db.execute(
        select(
            MaterialConsumption.actual_quantity,
            MaterialConsumption.standard_quantity,
            Material.standard_cost,
        )
        .join(Material, MaterialConsumption.material_id == Material.id)
        .where(MaterialConsumption.production_order_id == order.id)
    )
    mat_rows = mat_q.all()

    total_material_cost = Decimal("0")
    total_standard_material_cost = Decimal("0")
    for actual_qty, std_qty, std_cost in mat_rows:
        c = _dec(std_cost)
        total_material_cost         += _dec(actual_qty) * c
        total_standard_material_cost += _dec(std_qty)   * c

    # 2. Labor cost
    # ─────────────────────────────────────────────────────────────────────────
    # LaborLog → WorkOrder → WorkCenter.labor_rate_per_hour
    labor_q = await db.execute(
        select(
            LaborLog.hours_worked,
            # work_center labor rate via join
        )
        .join(WorkOrder, LaborLog.work_order_id == WorkOrder.id)
        .where(WorkOrder.production_order_id == order.id)
        .where(LaborLog.hours_worked.isnot(None))
    )
    # We need the rate too — do a more complete join
    from app.models.production_advanced import WorkCenter
    labor_q2 = await db.execute(
        select(
            LaborLog.hours_worked,
            WorkCenter.labor_rate_per_hour,
        )
        .join(WorkOrder, LaborLog.work_order_id == WorkOrder.id)
        .join(WorkCenter, WorkOrder.work_center_id == WorkCenter.id)
        .where(WorkOrder.production_order_id == order.id)
        .where(LaborLog.hours_worked.isnot(None))
    )
    labor_rows = labor_q2.all()

    total_labor_cost = Decimal("0")
    for hours, rate in labor_rows:
        total_labor_cost += _dec(hours) * _dec(rate)

    # 3. Machine cost
    # ─────────────────────────────────────────────────────────────────────────
    # WorkOrder duration (end_time - start_time) × machine_cost_per_hour
    from app.models.production_advanced import WorkCenter
    wo_q = await db.execute(
        select(
            WorkOrder.start_time,
            WorkOrder.end_time,
            WorkCenter.machine_cost_per_hour,
        )
        .join(WorkCenter, WorkOrder.work_center_id == WorkCenter.id)
        .where(WorkOrder.production_order_id == order.id)
        .where(WorkOrder.start_time.isnot(None))
        .where(WorkOrder.end_time.isnot(None))
    )
    wo_rows = wo_q.all()

    total_machine_cost = Decimal("0")
    for start, end, rate in wo_rows:
        if start and end and rate:
            hours = Decimal(str((end - start).total_seconds() / 3600))
            total_machine_cost += hours * _dec(rate)

    # 4. Energy cost (best-effort from utility_transactions)
    # ─────────────────────────────────────────────────────────────────────────
    total_energy_cost = Decimal("0")
    if order.batch_no:
        energy_q = await db.execute(
            select(func.coalesce(func.sum(UtilityTransaction.total_cost), 0))
            .where(UtilityTransaction.batch_id == order.batch_no)
        )
        total_energy_cost = _dec(energy_q.scalar())

    # 5. Totals
    # ─────────────────────────────────────────────────────────────────────────
    total_cost = (
        total_material_cost + total_labor_cost + total_machine_cost + total_energy_cost
    )

    actual_qty = _dec(order.actual_quantity) if order.actual_quantity else Decimal("0")
    cost_per_unit = (total_cost / actual_qty) if actual_qty > 0 else None

    # Standard cost per unit: from product.standard_cost (snapshot at completion)
    std_prod_q = await db.execute(
        select(Product.standard_cost).where(Product.id == order.product_id)
    )
    standard_cost_per_unit = _dec(std_prod_q.scalar())

    # Cost variance %
    cost_variance_pct = None
    if cost_per_unit is not None and standard_cost_per_unit > 0:
        cost_variance_pct = (
            (cost_per_unit - standard_cost_per_unit) / standard_cost_per_unit * 100
        )

    return {
        "total_material_cost":    float(total_material_cost),
        "total_labor_cost":       float(total_labor_cost),
        "total_machine_cost":     float(total_machine_cost),
        "total_energy_cost":      float(total_energy_cost),
        "total_cost":             float(total_cost),
        "cost_per_unit":          float(cost_per_unit)          if cost_per_unit          is not None else None,
        "standard_cost_per_unit": float(standard_cost_per_unit) if standard_cost_per_unit else None,
        "cost_variance_pct":      float(cost_variance_pct)      if cost_variance_pct      is not None else None,
        "material_row_count":     len(mat_rows),
        "labor_row_count":        len(labor_rows),
    }


async def finalize_order_cost(
    db: AsyncSession,
    order: ProductionOrder,
) -> ProductionOrder:
    """
    Compute cost and persist to production_order record.
    Only allowed when order is COMPLETED.
    """
    if order.status != ProductionOrderStatus.COMPLETED:
        raise HTTPException(
            status_code=422,
            detail="Cost can only be finalized for COMPLETED production orders.",
        )

    cost = await compute_order_cost(db, order)

    order.total_material_cost    = cost["total_material_cost"]
    order.total_labor_cost       = cost["total_labor_cost"]
    order.total_machine_cost     = cost["total_machine_cost"]
    order.total_energy_cost      = cost["total_energy_cost"]
    order.total_cost             = cost["total_cost"]
    order.cost_per_unit          = cost["cost_per_unit"]
    order.standard_cost_per_unit = cost["standard_cost_per_unit"]
    order.cost_variance_pct      = cost["cost_variance_pct"]
    order.costing_finalized_at   = _now()

    await db.flush()
    return order


# ── Aggregate report ──────────────────────────────────────────────────────────

async def get_cost_report(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
    product_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """
    Aggregated cost report per product — uses pre-finalized cost columns.
    Only includes COMPLETED orders with costing_finalized_at set.
    """
    filters = [
        ProductionOrder.status == ProductionOrderStatus.COMPLETED,
        ProductionOrder.costing_finalized_at.isnot(None),
    ]
    if date_from:
        filters.append(
            func.date(ProductionOrder.actual_end) >= date_from
        )
    if date_to:
        filters.append(
            func.date(ProductionOrder.actual_end) <= date_to
        )
    if product_id:
        filters.append(ProductionOrder.product_id == product_id)

    q = await db.execute(
        select(
            Product.id.label("product_id"),
            Product.sku,
            Product.name.label("product_name"),
            Product.standard_cost.label("product_standard_cost"),
            func.count(ProductionOrder.id).label("order_count"),
            func.sum(ProductionOrder.actual_quantity).label("total_qty"),
            func.sum(ProductionOrder.total_material_cost).label("total_material_cost"),
            func.sum(ProductionOrder.total_labor_cost).label("total_labor_cost"),
            func.sum(ProductionOrder.total_machine_cost).label("total_machine_cost"),
            func.sum(ProductionOrder.total_energy_cost).label("total_energy_cost"),
            func.sum(ProductionOrder.total_cost).label("total_cost"),
            func.avg(ProductionOrder.cost_per_unit).label("avg_cost_per_unit"),
            func.avg(ProductionOrder.cost_variance_pct).label("avg_variance_pct"),
        )
        .join(Product, ProductionOrder.product_id == Product.id)
        .where(and_(*filters))
        .group_by(Product.id, Product.sku, Product.name, Product.standard_cost)
        .order_by(func.sum(ProductionOrder.total_cost).desc())
    )
    rows = q.all()

    result = []
    for r in rows:
        total = float(r.total_cost or 0)
        mat   = float(r.total_material_cost or 0)
        lab   = float(r.total_labor_cost    or 0)
        mach  = float(r.total_machine_cost  or 0)
        eng   = float(r.total_energy_cost   or 0)
        result.append({
            "product_id":            str(r.product_id),
            "sku":                   r.sku,
            "product_name":          r.product_name,
            "standard_cost_per_unit": float(r.product_standard_cost or 0),
            "order_count":           int(r.order_count),
            "total_qty":             float(r.total_qty or 0),
            "total_material_cost":   mat,
            "total_labor_cost":      lab,
            "total_machine_cost":    mach,
            "total_energy_cost":     eng,
            "total_cost":            total,
            "avg_cost_per_unit":     float(r.avg_cost_per_unit or 0),
            "avg_variance_pct":      float(r.avg_variance_pct  or 0),
            "material_pct":          round(mat  / total * 100, 2) if total else 0,
            "labor_pct":             round(lab  / total * 100, 2) if total else 0,
            "machine_pct":           round(mach / total * 100, 2) if total else 0,
            "energy_pct":            round(eng  / total * 100, 2) if total else 0,
        })
    return result


# ── Daily trend ───────────────────────────────────────────────────────────────

async def get_cost_trend(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
    product_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """Daily cost trend — aggregated by actual_end date."""
    filters = [
        ProductionOrder.status == ProductionOrderStatus.COMPLETED,
        ProductionOrder.costing_finalized_at.isnot(None),
        ProductionOrder.actual_end.isnot(None),
    ]
    if date_from:
        filters.append(func.date(ProductionOrder.actual_end) >= date_from)
    if date_to:
        filters.append(func.date(ProductionOrder.actual_end) <= date_to)
    if product_id:
        filters.append(ProductionOrder.product_id == product_id)

    q = await db.execute(
        select(
            func.date(ProductionOrder.actual_end).label("day"),
            func.sum(ProductionOrder.total_material_cost).label("material_cost"),
            func.sum(ProductionOrder.total_labor_cost).label("labor_cost"),
            func.sum(ProductionOrder.total_machine_cost).label("machine_cost"),
            func.sum(ProductionOrder.total_energy_cost).label("energy_cost"),
            func.sum(ProductionOrder.total_cost).label("total_cost"),
            func.sum(ProductionOrder.actual_quantity).label("total_qty"),
            func.avg(ProductionOrder.cost_per_unit).label("avg_cost_per_unit"),
            func.count(ProductionOrder.id).label("order_count"),
        )
        .where(and_(*filters))
        .group_by(func.date(ProductionOrder.actual_end))
        .order_by(func.date(ProductionOrder.actual_end))
    )

    return [
        {
            "date":             str(r.day),
            "material_cost":    float(r.material_cost or 0),
            "labor_cost":       float(r.labor_cost    or 0),
            "machine_cost":     float(r.machine_cost  or 0),
            "energy_cost":      float(r.energy_cost   or 0),
            "total_cost":       float(r.total_cost    or 0),
            "total_qty":        float(r.total_qty     or 0),
            "avg_cost_per_unit": float(r.avg_cost_per_unit or 0),
            "order_count":      int(r.order_count),
        }
        for r in q.all()
    ]


# ── KPI summary ───────────────────────────────────────────────────────────────

async def get_cost_kpis(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
) -> dict:
    """High-level KPIs for the costing dashboard."""
    filters = [
        ProductionOrder.status == ProductionOrderStatus.COMPLETED,
        ProductionOrder.costing_finalized_at.isnot(None),
    ]
    if date_from:
        filters.append(func.date(ProductionOrder.actual_end) >= date_from)
    if date_to:
        filters.append(func.date(ProductionOrder.actual_end) <= date_to)

    q = await db.execute(
        select(
            func.count(ProductionOrder.id).label("order_count"),
            func.sum(ProductionOrder.actual_quantity).label("total_qty"),
            func.sum(ProductionOrder.total_material_cost).label("total_material_cost"),
            func.sum(ProductionOrder.total_labor_cost).label("total_labor_cost"),
            func.sum(ProductionOrder.total_machine_cost).label("total_machine_cost"),
            func.sum(ProductionOrder.total_energy_cost).label("total_energy_cost"),
            func.sum(ProductionOrder.total_cost).label("total_cost"),
            func.avg(ProductionOrder.cost_per_unit).label("avg_cost_per_unit"),
            func.avg(ProductionOrder.cost_variance_pct).label("avg_variance_pct"),
        )
        .where(and_(*filters))
    )
    r = q.one()

    total = float(r.total_cost or 0)
    mat   = float(r.total_material_cost or 0)
    lab   = float(r.total_labor_cost    or 0)
    mach  = float(r.total_machine_cost  or 0)
    eng   = float(r.total_energy_cost   or 0)

    # Over-budget count (variance_pct > 5%)
    over_q = await db.execute(
        select(func.count(ProductionOrder.id))
        .where(and_(*filters, ProductionOrder.cost_variance_pct > 5))
    )
    over_budget_count = int(over_q.scalar() or 0)

    return {
        "order_count":          int(r.order_count or 0),
        "total_qty":            float(r.total_qty or 0),
        "total_material_cost":  mat,
        "total_labor_cost":     lab,
        "total_machine_cost":   mach,
        "total_energy_cost":    eng,
        "total_cost":           total,
        "avg_cost_per_unit":    float(r.avg_cost_per_unit or 0),
        "avg_variance_pct":     float(r.avg_variance_pct  or 0),
        "over_budget_count":    over_budget_count,
        "material_pct":         round(mat  / total * 100, 2) if total else 0,
        "labor_pct":            round(lab  / total * 100, 2) if total else 0,
        "machine_pct":          round(mach / total * 100, 2) if total else 0,
        "energy_pct":           round(eng  / total * 100, 2) if total else 0,
        "flag_high_variance":   (float(r.avg_variance_pct or 0)) > 10,
        "flag_high_material":   (mat / total * 100 if total else 0) > 70,
    }


# ── WIP Valuation ─────────────────────────────────────────────────────────────

async def get_wip_report(db: AsyncSession) -> List[dict]:
    """
    Compute current WIP value for all IN_PROGRESS production orders.
    WIP = materials consumed so far + labor logged so far + machine time so far.
    """
    from app.models.production_advanced import WorkCenter
    orders_q = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.product))
        .where(ProductionOrder.status == ProductionOrderStatus.IN_PROGRESS)
        .order_by(ProductionOrder.scheduled_start)
    )
    orders = orders_q.scalars().all()

    rows = []
    for order in orders:
        cost = await compute_order_cost(db, order)
        rows.append({
            "order_id":          str(order.id),
            "order_no":          order.order_no,
            "product_name":      order.product.name if order.product else None,
            "product_sku":       order.product.sku  if order.product else None,
            "planned_quantity":  float(order.planned_quantity),
            "actual_quantity":   float(order.actual_quantity) if order.actual_quantity else None,
            "uom":               order.uom,
            "status":            order.status.value,
            "wip_material_cost": cost["total_material_cost"],
            "wip_labor_cost":    cost["total_labor_cost"],
            "wip_machine_cost":  cost["total_machine_cost"],
            "wip_total":         (cost["total_material_cost"] or 0)
                                 + (cost["total_labor_cost"] or 0)
                                 + (cost["total_machine_cost"] or 0),
            "scheduled_start":   order.scheduled_start.isoformat() if order.scheduled_start else None,
            "scheduled_end":     order.scheduled_end.isoformat()   if order.scheduled_end   else None,
        })
    return rows


# ── Variance Detail ───────────────────────────────────────────────────────────

async def get_variance_detail(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[dict]:
    """
    Per-order variance detail: material/labor/machine standard vs actual with $ variance.
    Includes both COMPLETED (finalized) and IN_PROGRESS orders with partial costs.
    """
    from app.models.production_advanced import WorkCenter, RoutingStep, Routing
    filters = [
        ProductionOrder.status.in_([ProductionOrderStatus.IN_PROGRESS, ProductionOrderStatus.COMPLETED])
    ]
    if date_from:
        filters.append(func.date(ProductionOrder.scheduled_start) >= date_from)
    if date_to:
        filters.append(func.date(ProductionOrder.scheduled_start) <= date_to)

    orders_q = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.product))
        .where(*filters)
        .order_by(ProductionOrder.scheduled_start.desc())
        .limit(200)
    )
    orders = orders_q.scalars().all()

    rows = []
    for order in orders:
        cost = await compute_order_cost(db, order)
        std_cost_unit = _dec(order.standard_cost_per_unit) if order.standard_cost_per_unit else None
        planned_qty = _dec(order.planned_quantity)

        # Standard total = standard_cost_per_unit × planned_quantity
        # Break standard cost into components using ratio from compute:
        # We don't store std component breakdown, so approximate from routing
        # Standard material = total_standard_material (recompute subset)
        mat_q = await db.execute(
            select(
                func.coalesce(func.sum(
                    MaterialConsumption.standard_quantity * Material.standard_cost
                ), 0)
            )
            .join(Material, MaterialConsumption.material_id == Material.id)
            .where(MaterialConsumption.production_order_id == order.id)
        )
        std_material = _dec(mat_q.scalar())

        # Standard labor from routing: Σ (standard_time_min/60 × labor_rate) per step
        # Use work orders linked to order → routing step standard times
        std_labor_q = await db.execute(
            select(
                func.coalesce(func.sum(
                    RoutingStep.standard_time_minutes * WorkCenter.labor_rate_per_hour / 60
                ), 0)
            )
            .join(WorkOrder, WorkOrder.routing_step_id == RoutingStep.id)
            .join(WorkCenter, WorkOrder.work_center_id == WorkCenter.id)
            .where(WorkOrder.production_order_id == order.id)
        )
        std_labor = _dec(std_labor_q.scalar())

        # Standard machine from routing steps
        std_machine_q = await db.execute(
            select(
                func.coalesce(func.sum(
                    RoutingStep.standard_time_minutes * WorkCenter.machine_cost_per_hour / 60
                ), 0)
            )
            .join(WorkOrder, WorkOrder.routing_step_id == RoutingStep.id)
            .join(WorkCenter, WorkOrder.work_center_id == WorkCenter.id)
            .where(WorkOrder.production_order_id == order.id)
        )
        std_machine = _dec(std_machine_q.scalar())

        act_material = _dec(cost["total_material_cost"])
        act_labor    = _dec(cost["total_labor_cost"])
        act_machine  = _dec(cost["total_machine_cost"])

        mat_var   = act_material - std_material
        lab_var   = act_labor    - std_labor
        mach_var  = act_machine  - std_machine
        total_var = mat_var + lab_var + mach_var

        std_total = std_material + std_labor + std_machine
        var_pct = float(total_var / std_total * 100) if std_total > 0 else None

        rows.append({
            "order_id":             str(order.id),
            "order_no":             order.order_no,
            "product_name":         order.product.name if order.product else None,
            "product_sku":          order.product.sku  if order.product else None,
            "status":               order.status.value,
            "actual_quantity":      float(order.actual_quantity) if order.actual_quantity else None,
            "std_material_cost":    float(std_material),
            "actual_material_cost": float(act_material),
            "material_variance":    float(mat_var),
            "std_labor_cost":       float(std_labor),
            "actual_labor_cost":    float(act_labor),
            "labor_variance":       float(lab_var),
            "std_machine_cost":     float(std_machine),
            "actual_machine_cost":  float(act_machine),
            "machine_variance":     float(mach_var),
            "total_variance":       float(total_var),
            "variance_pct":         var_pct,
        })
    return rows


# ── Work Center Utilization ───────────────────────────────────────────────────

async def get_work_center_utilization(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> List[dict]:
    """
    For each work center: actual hours used vs capacity in the date range.
    Capacity hours = capacity value treated as units/hr × 8hr/day × days.
    Actual hours = sum of completed WorkOrder durations.
    """
    from app.models.production_advanced import WorkCenter, WorkOrderStatus

    wc_q = await db.execute(
        select(WorkCenter).where(WorkCenter.status.in_(["ACTIVE", "MAINTENANCE"]))
        .order_by(WorkCenter.name)
    )
    work_centers = wc_q.scalars().all()

    days_in_range = max((date_to - date_from).days + 1, 1)

    rows = []
    for wc in work_centers:
        # Actual hours from WorkOrders with start_time/end_time in range
        wo_q = await db.execute(
            select(WorkOrder.start_time, WorkOrder.end_time)
            .where(
                WorkOrder.work_center_id == wc.id,
                WorkOrder.start_time.isnot(None),
                WorkOrder.end_time.isnot(None),
                func.date(WorkOrder.start_time) >= date_from,
                func.date(WorkOrder.start_time) <= date_to,
            )
        )
        wo_rows = wo_q.all()

        actual_hours = sum(
            (end - start).total_seconds() / 3600
            for start, end in wo_rows
            if start and end
        )
        completed_orders = len(wo_rows)

        # Capacity: assume 8-hour shift, 1 shift/day by default
        # Use work center capacity_uom as signal — if "units/hr" we can't convert
        # Fall back to: 8 hr/day × days_in_range
        capacity_hours = 8.0 * days_in_range

        utilization_pct = (actual_hours / capacity_hours * 100) if capacity_hours > 0 else None

        # Labor + machine cost from LaborLog and WorkOrder durations in range
        labor_q = await db.execute(
            select(func.coalesce(func.sum(LaborLog.hours_worked), 0))
            .join(WorkOrder, LaborLog.work_order_id == WorkOrder.id)
            .where(
                WorkOrder.work_center_id == wc.id,
                func.date(WorkOrder.start_time) >= date_from,
                func.date(WorkOrder.start_time) <= date_to,
            )
        )
        labor_hours = _dec(labor_q.scalar())
        labor_cost = float(labor_hours * _dec(wc.labor_rate_per_hour)) if wc.labor_rate_per_hour else 0.0
        machine_cost = float(_dec(actual_hours) * _dec(wc.machine_cost_per_hour)) if wc.machine_cost_per_hour else 0.0

        rows.append({
            "work_center_id":        str(wc.id),
            "work_center_name":      wc.name,
            "work_center_code":      wc.work_center_id,
            "capacity_hours":        capacity_hours,
            "actual_hours_used":     round(actual_hours, 2),
            "utilization_pct":       round(utilization_pct, 1) if utilization_pct is not None else None,
            "completed_orders":      completed_orders,
            "labor_cost_incurred":   round(labor_cost, 2),
            "machine_cost_incurred": round(machine_cost, 2),
        })
    return rows
