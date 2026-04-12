from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import production as crud
from app.services import production_service as svc
from app.models.production import (
    ProductionPlanStatus, ProductionOrderStatus,
)
from app.schemas.production import (
    ProductionPlanCreate, ProductionPlanUpdate,
    ProductionPlanRead, ProductionPlanDetailRead,
    PlanLineCreate, PlanLineRead,
    ProductionOrderCreate, ProductionOrderRead, ProductionOrderDetailRead,
    DowntimeLogCreate, DowntimeLogClose, DowntimeLogRead,
    OEEMetrics, CompleteOrderRequest,
    ProductionSummary,
    MaterialConsumptionRead, FinishedGoodsReceiptRead,
)

router = APIRouter()


def _enrich_plan_read(plan) -> ProductionPlanRead:
    return ProductionPlanRead.model_validate(plan)


def _enrich_order(order) -> ProductionOrderRead:
    read = ProductionOrderRead.model_validate(order)
    if order.product:
        read.product_name = order.product.name
        read.product_sku = order.product.sku
    if order.recipe:
        read.recipe_name = order.recipe.name
    if order.target_warehouse:
        read.target_warehouse_name = order.target_warehouse.name
    return read


def _enrich_order_detail(order) -> ProductionOrderDetailRead:
    detail = ProductionOrderDetailRead.model_validate(order)
    if order.product:
        detail.product_name = order.product.name
        detail.product_sku = order.product.sku
    if order.recipe:
        detail.recipe_name = order.recipe.name
    if order.target_warehouse:
        detail.target_warehouse_name = order.target_warehouse.name

    detail.consumptions = []
    for c in order.consumptions:
        r = MaterialConsumptionRead.model_validate(c)
        if c.material:
            r.material_name = c.material.name
            r.material_code = c.material.code
        if c.lot:
            r.lot_number = c.lot.lot_number
        if c.source_warehouse:
            r.source_warehouse_name = c.source_warehouse.name
        detail.consumptions.append(r)

    detail.fg_receipts = []
    for fg in order.fg_receipts:
        r = FinishedGoodsReceiptRead.model_validate(fg)
        if fg.warehouse:
            r.warehouse_name = fg.warehouse.name
        detail.fg_receipts.append(r)

    detail.downtime_logs = [DowntimeLogRead.model_validate(d) for d in order.downtime_logs]

    if order.status == ProductionOrderStatus.COMPLETED:
        from app.services.production_service import _compute_oee
        detail.oee = _compute_oee(order)

    return detail


# ── Production Plans ──────────────────────────────────────────────────────────

@router.get("/plans/", response_model=List[ProductionPlanRead])
async def list_plans(
    status: Optional[ProductionPlanStatus] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plans = await crud.list_plans(db, status=status, skip=skip, limit=limit)
    return [_enrich_plan_read(p) for p in plans]


@router.post("/plans/", response_model=ProductionPlanRead, status_code=201)
async def create_plan(
    data: ProductionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = await crud.create_plan(db, data, current_user.id)
    await db.commit()
    await db.refresh(obj)
    return ProductionPlanRead.model_validate(obj)


@router.get("/plans/{plan_id}", response_model=ProductionPlanDetailRead)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plan = await crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, detail="Production plan not found")
    detail = ProductionPlanDetailRead.model_validate(plan)
    lines = []
    for line in plan.lines:
        lr = PlanLineRead.model_validate(line)
        if line.product:
            lr.product_name = line.product.name
            lr.product_sku = line.product.sku
        if line.recipe:
            lr.recipe_name = line.recipe.name
            lr.recipe_version = line.recipe.version
        if line.target_warehouse:
            lr.target_warehouse_name = line.target_warehouse.name
        lines.append(lr)
    detail.lines = lines
    return detail


@router.patch("/plans/{plan_id}", response_model=ProductionPlanRead)
async def update_plan(
    plan_id: uuid.UUID, data: ProductionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plan = await crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, detail="Plan not found")
    if plan.status not in (ProductionPlanStatus.DRAFT,):
        raise HTTPException(422, detail="Only DRAFT plans can be updated.")
    plan = await crud.update_plan(db, plan, data)
    await db.commit()
    await db.refresh(plan)
    return ProductionPlanRead.model_validate(plan)


@router.post("/plans/{plan_id}/confirm", response_model=ProductionPlanRead)
async def confirm_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plan = await crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, detail="Plan not found")
    if plan.status != ProductionPlanStatus.DRAFT:
        raise HTTPException(422, detail="Only DRAFT plans can be confirmed.")
    if not plan.lines:
        raise HTTPException(422, detail="Cannot confirm a plan with no lines.")
    plan.status = ProductionPlanStatus.CONFIRMED
    await db.commit()
    await db.refresh(plan)
    return ProductionPlanRead.model_validate(plan)


@router.post("/plans/{plan_id}/lines", response_model=PlanLineRead, status_code=201)
async def add_plan_line(
    plan_id: uuid.UUID, data: PlanLineCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plan = await crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, detail="Plan not found")
    if plan.status not in (ProductionPlanStatus.DRAFT,):
        raise HTTPException(422, detail="Only DRAFT plans can be modified.")
    line = await crud.add_plan_line(db, plan_id, data)
    await db.commit()
    await db.refresh(line)
    return PlanLineRead.model_validate(line)


@router.delete("/plans/{plan_id}/lines/{line_id}", status_code=204)
async def delete_plan_line(
    plan_id: uuid.UUID, line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    plan = await crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, detail="Plan not found")
    if plan.status not in (ProductionPlanStatus.DRAFT,):
        raise HTTPException(422, detail="Only DRAFT plans can be modified.")
    line = await crud.get_plan_line(db, line_id)
    if not line or line.plan_id != plan_id:
        raise HTTPException(404, detail="Plan line not found")
    await crud.delete_plan_line(db, line)
    await db.commit()


# ── Production Orders ─────────────────────────────────────────────────────────

@router.get("/orders/", response_model=List[ProductionOrderRead])
async def list_orders(
    status: Optional[ProductionOrderStatus] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    orders = await crud.list_orders(db, status=status, product_id=product_id, skip=skip, limit=limit)
    return [_enrich_order(o) for o in orders]


@router.post("/orders/", response_model=ProductionOrderRead, status_code=201)
async def create_order(
    data: ProductionOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = await crud.create_order(db, data, current_user.id)
    await db.commit()
    order = await crud.get_order(db, obj.id)
    return _enrich_order(order)


@router.get("/orders/{order_id}", response_model=ProductionOrderDetailRead)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Production order not found")
    return _enrich_order_detail(order)


# ── Execution ─────────────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/release", response_model=ProductionOrderRead)
async def release_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    order = await svc.release_order(db, order)
    await db.commit()
    order = await crud.get_order(db, order_id)
    return _enrich_order(order)


@router.post("/orders/{order_id}/start", response_model=ProductionOrderRead)
async def start_order(
    order_id: uuid.UUID,
    actual_start: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    order = await svc.start_order(db, order, actual_start)
    await db.commit()
    order = await crud.get_order(db, order_id)
    return _enrich_order(order)


@router.post("/orders/{order_id}/pause", response_model=DowntimeLogRead)
async def pause_order(
    order_id: uuid.UUID, req: DowntimeLogCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    log = await svc.pause_order(db, order, req)
    await db.commit()
    await db.refresh(log)
    return DowntimeLogRead.model_validate(log)


@router.post("/orders/{order_id}/resume", response_model=DowntimeLogRead)
async def resume_order(
    order_id: uuid.UUID, req: DowntimeLogClose,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    log = await svc.resume_order(db, order, req)
    await db.commit()
    await db.refresh(log)
    return DowntimeLogRead.model_validate(log)


@router.post("/orders/{order_id}/complete", response_model=ProductionOrderDetailRead)
async def complete_order(
    order_id: uuid.UUID, req: CompleteOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    await svc.complete_order(db, order, req, current_user.id)
    await db.commit()
    order = await crud.get_order(db, order_id)
    return _enrich_order_detail(order)


@router.post("/orders/{order_id}/cancel", response_model=ProductionOrderRead)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    order = await svc.cancel_order(db, order)
    await db.commit()
    order = await crud.get_order(db, order_id)
    return _enrich_order(order)


# ── OEE ───────────────────────────────────────────────────────────────────────

@router.get("/orders/{order_id}/oee", response_model=OEEMetrics)
async def get_oee(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_order_oee(db, order_id)


# ── Downtime ──────────────────────────────────────────────────────────────────

@router.get("/downtime/", response_model=List[DowntimeLogRead])
async def list_downtime(
    order_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    logs = await crud.list_downtime_logs(db, order_id=order_id, skip=skip, limit=limit)
    return [DowntimeLogRead.model_validate(l) for l in logs]


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/summary", response_model=ProductionSummary)
async def production_report(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    product_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_production_report(db, date_from, date_to, product_id)
