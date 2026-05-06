"""
Production Costing API
──────────────────────
Routes:
  GET  /production-cost/kpis                       – dashboard KPIs
  GET  /production-cost/report                     – per-product aggregated cost report
  GET  /production-cost/trend                      – daily cost trend
  GET  /production-cost/orders/{order_id}/cost     – live cost breakdown for one order
  POST /production-cost/orders/{order_id}/finalize – compute + persist cost to order

Query params shared by most routes:
  date_from, date_to  – YYYY-MM-DD filter on actual_end
  product_id          – filter to one product UUID
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.master import Product
from app.schemas.production_costing import (
    OrderCostBreakdown, CostReportRow, CostTrendPoint, CostKPIs,
    WIPRow, VarianceDetailRow, WorkCenterUtilRow,
)
from app.services import production_cost_service as svc

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_order_or_404(db: AsyncSession, order_id: uuid.UUID) -> ProductionOrder:
    from fastapi import HTTPException
    q = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.product))
        .where(ProductionOrder.id == order_id)
    )
    order = q.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    return order


# ── KPIs ──────────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=CostKPIs)
async def get_cost_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    return await svc.get_cost_kpis(db, date_from=date_from, date_to=date_to)


# ── Report ────────────────────────────────────────────────────────────────────

@router.get("/report", response_model=List[CostReportRow])
async def get_cost_report(
    date_from:  Optional[date]      = Query(None),
    date_to:    Optional[date]      = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    return await svc.get_cost_report(
        db, date_from=date_from, date_to=date_to, product_id=product_id,
    )


# ── Trend ─────────────────────────────────────────────────────────────────────

@router.get("/trend", response_model=List[CostTrendPoint])
async def get_cost_trend(
    date_from:  Optional[date]      = Query(None),
    date_to:    Optional[date]      = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    return await svc.get_cost_trend(
        db, date_from=date_from, date_to=date_to, product_id=product_id,
    )


# ── Per-order live breakdown ───────────────────────────────────────────────────

@router.get("/orders/{order_id}/cost", response_model=OrderCostBreakdown)
async def get_order_cost(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    order = await _get_order_or_404(db, order_id)
    cost  = await svc.compute_order_cost(db, order)

    product_name = order.product.name if order.product else None
    product_sku  = order.product.sku  if order.product else None

    return OrderCostBreakdown(
        order_id    = str(order.id),
        order_no    = order.order_no,
        product_name = product_name,
        product_sku  = product_sku,
        status      = order.status.value,
        actual_quantity       = float(order.actual_quantity) if order.actual_quantity else None,
        uom                   = order.uom,
        total_material_cost   = cost["total_material_cost"],
        total_labor_cost      = cost["total_labor_cost"],
        total_machine_cost    = cost["total_machine_cost"],
        total_energy_cost     = cost["total_energy_cost"],
        total_cost            = cost["total_cost"],
        cost_per_unit         = cost["cost_per_unit"],
        standard_cost_per_unit = cost["standard_cost_per_unit"],
        cost_variance_pct     = cost["cost_variance_pct"],
        costing_finalized_at  = (
            order.costing_finalized_at.isoformat()
            if order.costing_finalized_at else None
        ),
        material_row_count    = cost["material_row_count"],
        labor_row_count       = cost["labor_row_count"],
    )


# ── Finalize (persist) ─────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/finalize", response_model=OrderCostBreakdown)
async def finalize_order_cost(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    order = await _get_order_or_404(db, order_id)
    order = await svc.finalize_order_cost(db, order)
    await db.commit()
    await db.refresh(order)

    product_name = order.product.name if order.product else None
    product_sku  = order.product.sku  if order.product else None

    return OrderCostBreakdown(
        order_id    = str(order.id),
        order_no    = order.order_no,
        product_name = product_name,
        product_sku  = product_sku,
        status      = order.status.value,
        actual_quantity       = float(order.actual_quantity) if order.actual_quantity else None,
        uom                   = order.uom,
        total_material_cost   = float(order.total_material_cost)    if order.total_material_cost    else None,
        total_labor_cost      = float(order.total_labor_cost)       if order.total_labor_cost       else None,
        total_machine_cost    = float(order.total_machine_cost)     if order.total_machine_cost     else None,
        total_energy_cost     = float(order.total_energy_cost)      if order.total_energy_cost      else None,
        total_cost            = float(order.total_cost)             if order.total_cost             else None,
        cost_per_unit         = float(order.cost_per_unit)          if order.cost_per_unit          else None,
        standard_cost_per_unit = float(order.standard_cost_per_unit) if order.standard_cost_per_unit else None,
        cost_variance_pct     = float(order.cost_variance_pct)      if order.cost_variance_pct      else None,
        costing_finalized_at  = (
            order.costing_finalized_at.isoformat()
            if order.costing_finalized_at else None
        ),
    )


# ── WIP Valuation ─────────────────────────────────────────────────────────────

@router.get("/wip", response_model=List[WIPRow])
async def get_wip_report(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await svc.get_wip_report(db)
    return [WIPRow(**r) for r in rows]


# ── Variance Detail ───────────────────────────────────────────────────────────

@router.get("/variance-detail", response_model=List[VarianceDetailRow])
async def get_variance_detail(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await svc.get_variance_detail(db, date_from, date_to)
    return [VarianceDetailRow(**r) for r in rows]


# ── Work Center Utilization ───────────────────────────────────────────────────

@router.get("/work-center-utilization", response_model=List[WorkCenterUtilRow])
async def get_work_center_utilization(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await svc.get_work_center_utilization(db, date_from, date_to)
    return [WorkCenterUtilRow(**r) for r in rows]
