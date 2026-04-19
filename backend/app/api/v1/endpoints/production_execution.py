"""
Production Execution API — Production Orders, Work Orders, Genealogy.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.production_execution import (
    ProdExecOrderCreate, ProdExecOrderOut, ProdExecOrderSummary,
    ExecWorkOrderCreate, ExecWorkOrderOut, CompleteWorkOrderRequest,
    ExecOrderMaterialCreate, ExecOrderMaterialOut,
    IssueReturnMaterialRequest, BatchGenealogyOut,
    AddGenealogyRequest, CompleteOrderRequest,
    SplitOrderRequest, MergeOrdersRequest, ReworkOrderRequest,
    ExecAIRecOut, ExecDashboard, BatchRecord,
)
from app.services import production_execution_service as svc
from app.services import production_exec_ai_service as ai_svc

router = APIRouter()


def _user_id() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ExecDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Production Orders ─────────────────────────────────────────────────────────

@router.post("", response_model=ProdExecOrderOut, status_code=201)
async def create_order(
    body: ProdExecOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = body.model_dump(exclude_unset=True)
        return await svc.create_order(db, data, _user_id())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ProdExecOrderSummary])
async def list_orders(
    status: Optional[str] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_orders(db, status=status, product_id=product_id, limit=limit, offset=offset)


@router.get("/work-orders", response_model=List[ExecWorkOrderOut])
async def list_all_work_orders(
    status: Optional[str] = Query(None),
    work_center_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_work_orders(db, status=status, work_center_id=work_center_id, limit=limit)


@router.get("/{order_id}", response_model=ProdExecOrderOut)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.get_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{order_id}", response_model=ProdExecOrderOut)
async def update_order(
    order_id: uuid.UUID,
    body: ProdExecOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.update_order(db, order_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Lifecycle ──────────────────────────────────────────────────────────────────

@router.post("/{order_id}/advance", response_model=ProdExecOrderOut)
async def advance_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.advance_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/release", response_model=ProdExecOrderOut)
async def release_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.release_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/start", response_model=ProdExecOrderOut)
async def start_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.start_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/pause", response_model=ProdExecOrderOut)
async def pause_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.pause_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/complete", response_model=ProdExecOrderOut)
async def complete_order(
    order_id: uuid.UUID,
    body: CompleteOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.complete_order(
            db, order_id, body.completed_qty, body.scrap_qty, body.remarks
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/close", response_model=ProdExecOrderOut)
async def close_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.close_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=ProdExecOrderOut)
async def cancel_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.cancel_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Split / Merge / Rework ─────────────────────────────────────────────────────

@router.post("/{order_id}/split", response_model=List[ProdExecOrderOut])
async def split_order(
    order_id: uuid.UUID,
    body: SplitOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.split_order(db, order_id, body.split_qtys, body.reason, _user_id())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge", response_model=ProdExecOrderOut)
async def merge_orders(body: MergeOrdersRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.merge_orders(db, body.order_ids, body.reason, _user_id())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/rework", response_model=ProdExecOrderOut)
async def create_rework_order(
    order_id: uuid.UUID,
    body: ReworkOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.create_rework_order(db, order_id, body.qty, body.reason, _user_id())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Genealogy ──────────────────────────────────────────────────────────────────

@router.get("/{order_id}/genealogy")
async def get_genealogy(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.get_genealogy(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{order_id}/genealogy", response_model=BatchGenealogyOut, status_code=201)
async def add_genealogy_link(
    order_id: uuid.UUID,
    body: AddGenealogyRequest,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_genealogy_link(db, order_id, body.model_dump(exclude_unset=True))


# ── Batch Record ───────────────────────────────────────────────────────────────

@router.get("/{order_id}/batch-record", response_model=BatchRecord)
async def get_batch_record(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        order = await svc.get_order(db, order_id)
        return BatchRecord(
            order=order,
            work_orders=order.work_orders,
            materials=order.materials,
            genealogy=order.genealogy_links,
            generated_at=_now(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Work Orders ────────────────────────────────────────────────────────────────

@router.post("/{order_id}/work-orders", response_model=ExecWorkOrderOut, status_code=201)
async def add_work_order(
    order_id: uuid.UUID,
    body: ExecWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_work_order(db, order_id, body.model_dump(exclude_unset=True))


@router.patch("/work-orders/{wo_id}", response_model=ExecWorkOrderOut)
async def update_work_order(
    wo_id: uuid.UUID,
    body: ExecWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.update_work_order(db, wo_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/work-orders/{wo_id}/start", response_model=ExecWorkOrderOut)
async def start_work_order(wo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.start_work_order(db, wo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{wo_id}/complete", response_model=ExecWorkOrderOut)
async def complete_work_order(
    wo_id: uuid.UUID,
    body: CompleteWorkOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.complete_work_order(
            db, wo_id,
            body.completed_qty, body.scrap_qty, body.rework_qty,
            body.setup_time_actual, body.run_time_actual, body.cleanup_time_actual,
            body.scrap_category, body.scrap_reason, body.qc_passed, body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Materials ──────────────────────────────────────────────────────────────────

@router.post("/{order_id}/materials", response_model=ExecOrderMaterialOut, status_code=201)
async def add_material(
    order_id: uuid.UUID,
    body: ExecOrderMaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_material(db, order_id, body.model_dump(exclude_unset=True))


@router.post("/{order_id}/materials/issue", response_model=ExecOrderMaterialOut)
async def issue_material(
    order_id: uuid.UUID,
    body: IssueReturnMaterialRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.issue_material(db, order_id, body.material_id, body.qty, body.lot_no)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/materials/return", response_model=ExecOrderMaterialOut)
async def return_material(
    order_id: uuid.UUID,
    body: IssueReturnMaterialRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.return_material(db, order_id, body.material_id, body.qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/{order_id}/run-ai")
async def run_ai(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    total = await ai_svc.run_all_exec_ai(db, order_id)
    return {"total": total}


@router.get("/{order_id}/ai-recs", response_model=List[ExecAIRecOut])
async def list_ai_recs(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await ai_svc.list_ai_recs(db, order_id)


@router.post("/ai-recs/{rec_id}/action", response_model=ExecAIRecOut)
async def action_ai_rec(
    rec_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    try:
        status = body.get("status", "ACCEPTED")
        return await ai_svc.action_ai_rec(db, rec_id, status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
