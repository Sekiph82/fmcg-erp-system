"""
Production Execution API — Production Orders, Work Orders, Genealogy.
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.access_control import can_modify_scope, forbidden_detail, has_any_permission
from app.core.deps import get_current_user
from app.models.production_execution import ExecAIRec, ExecWorkOrder
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_execution_action(user, action: str, record) -> None:
    if action == "view" and has_any_permission(user, ("production.view", "production.view_all")):
        return
    scopes = [
        ("factory", getattr(record, "plant_id", None)),
        ("section", getattr(record, "section_id", None)),
        ("production_line", getattr(record, "line_id", None)),
    ]
    scopes = [(scope_type, scope_id) for scope_type, scope_id in scopes if scope_id is not None]
    if not scopes:
        scopes = [("global", "ALL")]
    if any(can_modify_scope(user, "production", action, scope_type, scope_id) for scope_type, scope_id in scopes):
        return
    raise HTTPException(
        status_code=403,
        detail=forbidden_detail("Required production permission and operational scope are missing."),
    )


def _require_broad_execution_view(user) -> None:
    if not has_any_permission(user, ("production.view", "production.view_all")):
        raise HTTPException(
            status_code=403,
            detail=forbidden_detail("Broad production view permission is required for aggregate data."),
        )


def _require_scope_change(user, action: str, record, changes: dict, fallback=None) -> None:
    def resolved(values):
        scope = {}
        for field in ("plant_id", "section_id", "line_id"):
            value = values.get(field, getattr(record, field, None))
            if value is None and fallback is not None:
                value = getattr(fallback, field, None)
            scope[field] = value
        return SimpleNamespace(**scope)

    current = resolved({})
    target = resolved(changes)
    _require_execution_action(user, action, current)
    for field in ("plant_id", "section_id", "line_id"):
        if field not in changes or getattr(target, field) == getattr(current, field):
            continue
        changed_scope = SimpleNamespace(plant_id=None, section_id=None, line_id=None)
        setattr(changed_scope, field, getattr(target, field))
        _require_execution_action(user, action, changed_scope)


async def _get_order_for_action(db: AsyncSession, order_id: uuid.UUID, user, action: str):
    try:
        order = (
            await svc.get_order(db, order_id)
            if action == "view"
            else await svc._load_order(db, order_id, for_update=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _require_execution_action(user, action, order)
    return order


async def _get_work_order_parent_for_action(
    db: AsyncSession, work_order_id: uuid.UUID, user, action: str
):
    result = await db.execute(
        select(ExecWorkOrder.production_order_id).where(ExecWorkOrder.id == work_order_id)
    )
    parent_id = result.scalar_one_or_none()
    if parent_id is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    return await _get_order_for_action(db, parent_id, user, action)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ExecDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_broad_execution_view(current_user)
    return await svc.get_dashboard(db)


# ── Production Orders ─────────────────────────────────────────────────────────

@router.post("", response_model=ProdExecOrderOut, status_code=201)
async def create_order(
    body: ProdExecOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_execution_action(current_user, "create", body)
    try:
        data = body.model_dump(exclude_unset=True)
        return await svc.create_order(db, data, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ProdExecOrderSummary])
async def list_orders(
    status: Optional[str] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    orders = await svc.list_orders(db, status=status, product_id=product_id, limit=limit, offset=offset)
    if not has_any_permission(current_user, ("production.view", "production.view_all")):
        orders = [
            order for order in orders
            if any(
                can_modify_scope(current_user, "production", "view", scope_type, scope_id)
                for scope_type, scope_id in (
                    ("factory", order.plant_id),
                    ("section", order.section_id),
                    ("production_line", order.line_id),
                )
                if scope_id is not None
            )
        ]
    return orders


@router.get("/work-orders", response_model=List[ExecWorkOrderOut])
async def list_all_work_orders(
    status: Optional[str] = Query(None),
    work_center_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_broad_execution_view(current_user)
    return await svc.list_work_orders(db, status=status, work_center_id=work_center_id, limit=limit)


@router.get("/{order_id}", response_model=ProdExecOrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        order = await svc.get_order(db, order_id)
        _require_execution_action(current_user, "view", order)
        return order
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{order_id}", response_model=ProdExecOrderOut)
async def update_order(
    order_id: uuid.UUID,
    body: ProdExecOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        order = await _get_order_for_action(db, order_id, current_user, "edit")
        changes = body.model_dump(exclude_unset=True)
        _require_scope_change(current_user, "edit", order, changes)
        return await svc.update_order(db, order_id, changes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Lifecycle ──────────────────────────────────────────────────────────────────

@router.post("/{order_id}/advance", response_model=ProdExecOrderOut)
async def advance_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        order = await svc._load_order(db, order_id, for_update=True)
        action = {
            "PLANNED": "release",
            "IN_PROGRESS": "close",
            "COMPLETED": "close",
        }.get(order.status, "edit")
        _require_execution_action(current_user, action, order)
        return await svc.advance_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/release", response_model=ProdExecOrderOut)
async def release_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "release")
        return await svc.release_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/start", response_model=ProdExecOrderOut)
async def start_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.start_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/pause", response_model=ProdExecOrderOut)
async def pause_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.pause_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/complete", response_model=ProdExecOrderOut)
async def complete_order(
    order_id: uuid.UUID,
    body: CompleteOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "close")
        return await svc.complete_order(
            db, order_id, body.completed_qty, body.scrap_qty, body.remarks
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/close", response_model=ProdExecOrderOut)
async def close_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "close")
        return await svc.close_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=ProdExecOrderOut)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "cancel")
        return await svc.cancel_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Split / Merge / Rework ─────────────────────────────────────────────────────

@router.post("/{order_id}/split", response_model=List[ProdExecOrderOut])
async def split_order(
    order_id: uuid.UUID,
    body: SplitOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.split_order(db, order_id, body.split_qtys, body.reason, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge", response_model=ProdExecOrderOut)
async def merge_orders(
    body: MergeOrdersRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        if not body.order_ids:
            raise HTTPException(status_code=422, detail="At least two production orders are required to merge")
        for order_id in sorted(set(body.order_ids), key=str):
            await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.merge_orders(db, body.order_ids, body.reason, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/rework", response_model=ProdExecOrderOut)
async def create_rework_order(
    order_id: uuid.UUID,
    body: ReworkOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.create_rework_order(db, order_id, body.qty, body.reason, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Genealogy ──────────────────────────────────────────────────────────────────

@router.get("/{order_id}/genealogy")
async def get_genealogy(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "view")
        return await svc.get_genealogy(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{order_id}/genealogy", response_model=BatchGenealogyOut, status_code=201)
async def add_genealogy_link(
    order_id: uuid.UUID,
    body: AddGenealogyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _get_order_for_action(db, order_id, current_user, "edit")
    return await svc.add_genealogy_link(db, order_id, body.model_dump(exclude_unset=True))


# ── Batch Record ───────────────────────────────────────────────────────────────

@router.get("/{order_id}/batch-record", response_model=BatchRecord)
async def get_batch_record(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        order = await svc.get_order(db, order_id)
        _require_execution_action(current_user, "view", order)
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
    current_user=Depends(get_current_user),
):
    parent = await _get_order_for_action(db, order_id, current_user, "edit")
    changes = body.model_dump(exclude_unset=True)
    _require_scope_change(current_user, "edit", parent, changes, fallback=parent)
    return await svc.add_work_order(db, order_id, changes)


@router.patch("/work-orders/{wo_id}", response_model=ExecWorkOrderOut)
async def update_work_order(
    wo_id: uuid.UUID,
    body: ExecWorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        parent = await _get_work_order_parent_for_action(db, wo_id, current_user, "edit")
        work_order_result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
        work_order = work_order_result.scalar_one_or_none()
        if work_order is None:
            raise HTTPException(status_code=404, detail="Work order not found")
        changes = body.model_dump(exclude_unset=True)
        _require_scope_change(current_user, "edit", work_order, changes, fallback=parent)
        return await svc.update_work_order(db, wo_id, changes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/work-orders/{wo_id}/start", response_model=ExecWorkOrderOut)
async def start_work_order(
    wo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_work_order_parent_for_action(db, wo_id, current_user, "edit")
        return await svc.start_work_order(db, wo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{wo_id}/complete", response_model=ExecWorkOrderOut)
async def complete_work_order(
    wo_id: uuid.UUID,
    body: CompleteWorkOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_work_order_parent_for_action(db, wo_id, current_user, "close")
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
    current_user=Depends(get_current_user),
):
    await _get_order_for_action(db, order_id, current_user, "edit")
    return await svc.add_material(db, order_id, body.model_dump(exclude_unset=True))


@router.post("/{order_id}/materials/issue", response_model=ExecOrderMaterialOut)
async def issue_material(
    order_id: uuid.UUID,
    body: IssueReturnMaterialRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.issue_material(db, order_id, body.material_id, body.qty, body.lot_no)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/materials/return", response_model=ExecOrderMaterialOut)
async def return_material(
    order_id: uuid.UUID,
    body: IssueReturnMaterialRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _get_order_for_action(db, order_id, current_user, "edit")
        return await svc.return_material(db, order_id, body.material_id, body.qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/{order_id}/run-ai")
async def run_ai(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _get_order_for_action(db, order_id, current_user, "edit")
    total = await ai_svc.run_all_exec_ai(db, order_id)
    return {"total": total}


@router.get("/{order_id}/ai-recs", response_model=List[ExecAIRecOut])
async def list_ai_recs(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _get_order_for_action(db, order_id, current_user, "view")
    return await ai_svc.list_ai_recs(db, order_id)


@router.post("/ai-recs/{rec_id}/action", response_model=ExecAIRecOut)
async def action_ai_rec(
    rec_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        result = await db.execute(select(ExecAIRec.production_order_id).where(ExecAIRec.id == rec_id))
        order_id = result.scalar_one_or_none()
        if order_id is None:
            raise HTTPException(status_code=404, detail="AI recommendation not found")
        await _get_order_for_action(db, order_id, current_user, "edit")
        status = body.get("status", "ACCEPTED")
        return await ai_svc.action_ai_rec(db, rec_id, status)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
