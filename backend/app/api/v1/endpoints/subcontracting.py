"""Subcontracting System — API endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.subcontracting import SCOrderStatus
from app.schemas.subcontracting import (
    SCDashboard, SCIssueCreate, SCIssueOut, SCIssueLineOut,
    SCOrderCreate, SCOrderOut, SCOrderLineOut,
    SCPerformanceOut, SCReceiptCreate, SCReceiptOut, SCReceiptLineOut,
    SCAIRecOut, SCYieldOut,
    SubcontractorLocationCreate, SubcontractorLocationOut,
    SubcontractorStockRow,
)
from app.services import subcontracting_service as svc

router = APIRouter()


def _loc_out(loc) -> SubcontractorLocationOut:
    out = SubcontractorLocationOut.model_validate(loc)
    if loc.supplier:
        out.supplier_name = loc.supplier.name
    if loc.warehouse:
        out.warehouse_name = loc.warehouse.name
        out.warehouse_code = loc.warehouse.code
    return out


def _line_out(l) -> SCOrderLineOut:
    out = SCOrderLineOut.model_validate(l)
    if l.product:  out.product_name  = l.product.name
    if l.material: out.material_name = l.material.name
    return out


def _order_out(o) -> SCOrderOut:
    out = SCOrderOut.model_validate(o)
    if o.supplier:  out.supplier_name  = o.supplier.name
    if o.warehouse: out.warehouse_name = o.warehouse.name
    if hasattr(o, "lines"):
        out.lines = [_line_out(l) for l in o.lines]
    return out


def _issue_out(i) -> SCIssueOut:
    out = SCIssueOut.model_validate(i)
    if hasattr(i, "lines"):
        lines = []
        for l in i.lines:
            lo = SCIssueLineOut.model_validate(l)
            if l.material: lo.material_name = l.material.name; lo.material_code = l.material.code
            if l.lot:      lo.lot_number = l.lot.lot_number
            lines.append(lo)
        out.lines = lines
    return out


def _receipt_out(r) -> SCReceiptOut:
    out = SCReceiptOut.model_validate(r)
    if hasattr(r, "lines"):
        lines = []
        for l in r.lines:
            lo = SCReceiptLineOut.model_validate(l)
            if l.product:  lo.product_name  = l.product.name
            if l.material: lo.material_name = l.material.name
            lines.append(lo)
        out.lines = lines
    return out


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=SCDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Subcontractor Locations ───────────────────────────────────────────────────

@router.get("/locations", response_model=List[SubcontractorLocationOut])
async def list_locations(db: AsyncSession = Depends(get_db)):
    locs = await svc.list_locations(db)
    return [_loc_out(l) for l in locs]


@router.post("/locations", response_model=SubcontractorLocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: SubcontractorLocationCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        loc = await svc.create_location(db, payload)
        await db.commit()
        await db.refresh(loc)
        return _loc_out(loc)
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=List[SCOrderOut])
async def list_orders(
    status_filter: Optional[SCOrderStatus] = Query(None, alias="status"),
    supplier_id:   Optional[UUID] = None,
    skip:  int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    orders = await svc.list_orders(db, status=status_filter, supplier_id=supplier_id,
                                   skip=skip, limit=limit)
    return [_order_out(o) for o in orders]


@router.post("/orders", response_model=SCOrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: SCOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await svc.create_order(db, payload, None)
        await db.commit()
        fresh = await svc.get_order(db, order.id)
        return _order_out(fresh)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/orders/{order_id}", response_model=SCOrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    order = await svc.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return _order_out(order)


@router.post("/orders/{order_id}/approve", response_model=SCOrderOut)
async def approve_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        order = await svc.approve_order(db, order_id, None)
        await db.commit()
        fresh = await svc.get_order(db, order.id)
        return _order_out(fresh)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/orders/{order_id}/complete", response_model=SCOrderOut)
async def complete_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        order = await svc.complete_order(db, order_id)
        await db.commit()
        fresh = await svc.get_order(db, order.id)
        return _order_out(fresh)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Material Issue ────────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/issue-material",
             response_model=SCIssueOut, status_code=status.HTTP_201_CREATED)
async def issue_material(
    order_id: UUID,
    payload:  SCIssueCreate,
    db: AsyncSession = Depends(get_db),
):
    payload.order_id = order_id
    try:
        issue = await svc.issue_materials(db, payload, None)
        await db.commit()
        await db.refresh(issue)
        return _issue_out(issue)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/orders/{order_id}/issues", response_model=List[SCIssueOut])
async def list_issues(order_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.subcontracting import SubcontractMaterialIssue
    from sqlalchemy.orm import selectinload
    q = (
        select(SubcontractMaterialIssue)
        .options(
            selectinload(SubcontractMaterialIssue.lines).selectinload(
                SubcontractMaterialIssueLine.material),
            selectinload(SubcontractMaterialIssue.lines).selectinload(
                SubcontractMaterialIssueLine.lot),
        )
        .where(SubcontractMaterialIssue.order_id == order_id)
    )
    from app.models.subcontracting import SubcontractMaterialIssueLine
    issues = list((await db.execute(q)).scalars().all())
    return [_issue_out(i) for i in issues]


# ── Goods Receipt ─────────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/receive",
             response_model=SCReceiptOut, status_code=status.HTTP_201_CREATED)
async def receive_goods(
    order_id: UUID,
    payload:  SCReceiptCreate,
    db: AsyncSession = Depends(get_db),
):
    payload.order_id = order_id
    try:
        receipt = await svc.receive_goods(db, payload, None)
        await db.commit()
        await db.refresh(receipt)
        return _receipt_out(receipt)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/orders/{order_id}/receipts", response_model=List[SCReceiptOut])
async def list_receipts(order_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.subcontracting import SubcontractReceipt, SubcontractReceiptLine
    q = (
        select(SubcontractReceipt)
        .options(
            selectinload(SubcontractReceipt.lines).selectinload(SubcontractReceiptLine.product),
            selectinload(SubcontractReceipt.lines).selectinload(SubcontractReceiptLine.material),
        )
        .where(SubcontractReceipt.order_id == order_id)
    )
    receipts = list((await db.execute(q)).scalars().all())
    return [_receipt_out(r) for r in receipts]


# ── Yield ─────────────────────────────────────────────────────────────────────

@router.get("/orders/{order_id}/yield", response_model=List[SCYieldOut])
async def get_yield(order_id: UUID, db: AsyncSession = Depends(get_db)):
    records = await svc.list_yield_records(db, order_id=order_id)
    return [SCYieldOut.model_validate(r) for r in records]


@router.get("/yield/report", response_model=List[SCYieldOut])
async def yield_report(
    abnormal_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    records = await svc.list_yield_records(db, abnormal_only=abnormal_only)
    return [SCYieldOut.model_validate(r) for r in records]


# ── Stock at subcontractor ────────────────────────────────────────────────────

@router.get("/stock", response_model=List[SubcontractorStockRow])
async def subcontractor_stock(
    supplier_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_subcontractor_stock(db, supplier_id=supplier_id)


# ── Performance ───────────────────────────────────────────────────────────────

@router.get("/performance", response_model=List[SCPerformanceOut])
async def get_performance(
    supplier_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    records = await svc.list_performance(db, supplier_id=supplier_id)
    result = []
    for r in records:
        out = SCPerformanceOut.model_validate(r)
        if r.supplier: out.supplier_name = r.supplier.name
        if r.order:    out.order_no      = r.order.order_no
        result.append(out)
    return result


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/ai/run")
async def run_ai_for_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    counts = await svc.run_ai_agents(db, order_id=order_id)
    await db.commit()
    return {"generated": sum(counts.values()), "by_agent": counts}


@router.post("/ai/run")
async def run_all_ai_agents(db: AsyncSession = Depends(get_db)):
    counts = await svc.run_ai_agents(db, order_id=None)
    await db.commit()
    return {"generated": sum(counts.values()), "by_agent": counts}


@router.get("/ai/recommendations", response_model=List[SCAIRecOut])
async def list_ai_recs(
    order_id:    Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    recs = await svc.list_ai_recs(db, order_id=order_id, supplier_id=supplier_id)
    result = []
    for r in recs:
        out = SCAIRecOut.model_validate(r)
        if r.supplier: out.supplier_name = r.supplier.name
        if r.order:    out.order_no      = r.order.order_no
        result.append(out)
    return result


@router.post("/ai/recommendations/{rec_id}/action", response_model=SCAIRecOut)
async def action_ai_rec(
    rec_id: UUID,
    notes:  Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        rec = await svc.action_ai_rec(db, rec_id, notes)
        await db.commit()
        await db.refresh(rec)
        out = SCAIRecOut.model_validate(rec)
        return out
    except ValueError as e:
        raise HTTPException(404, str(e))
