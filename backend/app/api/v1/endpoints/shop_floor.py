"""Shop Floor Execution API endpoints."""
from __future__ import annotations

import uuid
import hashlib
import json
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.access_control import (
    can_modify_scope, can_perform_in_scope, can_view_scope,
    has_any_permission, has_permission,
)
from app.core.deps import get_current_user
from app.models.shop_floor import SFAIRec, SFDowntimeLog, SFSession
from app.models.production_execution import ExecWorkOrder, ProdExecOrder
from app.models.master import Product
from app.schemas.shop_floor import (
    LiveStatusResponse, LiveWOItem, SFAIRecOut, SFDashboard,
    SFDowntimeCreate, SFDowntimeOut, SFSessionCreate, SFSessionOut,
    ShiftHandoverCreate, ShiftHandoverOut, StartWORequest, PauseWORequest,
    ResumeWORequest, QtyUpdateRequest, ScrapRequest, FinishWORequest,
    HelpRequest, QCTriggerRequest, NoteRequest, StopDowntimeRequest,
    SupervisorOverrideCreate, SupervisorOverrideOut, WOActivityLogOut,
    SFMaterialConsumptionRequest, SFOperationMaterialOut, SFQCCheckpointRequest,
)
from app.services import shop_floor_service as svc
from app.services import shop_floor_ai_service as ai_svc


router = APIRouter(dependencies=[Depends(get_current_user)])

_SCOPED_VIEW_PERMISSIONS = ("shop_floor.view_own_scope", "production.view_own_scope")
_GLOBAL_VIEW_PERMISSIONS = ("production.view", "production.view_all")


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def _has_global_view(user) -> bool:
    return any(has_permission(user, code) for code in _GLOBAL_VIEW_PERMISSIONS)


def _require_global_view(user) -> None:
    if not _has_global_view(user):
        raise _forbidden("A broad production view permission is required for aggregate shop-floor data.")


def _require_line_view(user, line_id: Optional[str]) -> None:
    if _has_global_view(user):
        return
    if not line_id or not any(has_permission(user, code) for code in _SCOPED_VIEW_PERMISSIONS):
        raise _forbidden("A production-line scoped view permission is required.")
    if not can_perform_in_scope(user, "production_line", line_id, "view"):
        raise _forbidden("The requested production line is outside the user's view scope.")


def _require_line_edit(user, line_id: Optional[str]) -> None:
    if has_permission(user, "production.edit") or has_permission(user, "production.edit_all"):
        return
    if not line_id:
        raise _forbidden("A production line is required for scoped execution actions.")
    scoped_edit = (
        has_permission(user, "production.edit_own_scope")
        or has_permission(user, "production_execution.update_own_line")
    )
    if not scoped_edit or not can_perform_in_scope(user, "production_line", line_id, "edit"):
        raise _forbidden("A scoped production edit permission is required for this line.")


def _require_production_approval(user) -> None:
    if not has_permission(user, "production.approve"):
        raise _forbidden("Production approval permission is required for supervisor decisions.")


def _execution_idempotency_context(
    idempotency_key: str,
    *,
    action: str,
    resource_id: str,
    user,
    body,
) -> tuple[str, str]:
    key = idempotency_key.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", key):
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key must contain 1 to 128 letters, digits, '.', '_', ':', or '-'.",
        )
    request_data = {
        "action": action,
        "resource_id": resource_id,
        "actor_user_id": str(user.id),
        "body": body.model_dump(mode="json"),
    }
    canonical = json.dumps(request_data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return key, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _execution_activity_response(
    db: AsyncSession,
    *,
    work_order_id: UUID,
    user,
    idempotency_key: str,
) -> WOActivityLogOut:
    event = await svc.get_execution_idempotency_event(
        db, work_order_id, user.id, idempotency_key,
    )
    if event is None:
        raise HTTPException(status_code=500, detail="Execution action was not recorded with its idempotency key.")
    return event


def _execution_action_error(error: ValueError) -> HTTPException:
    if isinstance(error, svc.IdempotencyConflictError):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=400, detail=str(error))


async def _get_session(db: AsyncSession, session_id: UUID) -> SFSession:
    result = await db.execute(select(SFSession).where(SFSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Operator session not found")
    return session


async def _require_execution_session(
    db: AsyncSession,
    user,
    session_id: Optional[UUID],
    *,
    work_order_id: Optional[UUID] = None,
) -> SFSession:
    if session_id is None:
        raise _forbidden("An authenticated operator session is required for execution actions.")
    session = await _get_session(db, session_id)
    if session.status != "ACTIVE":
        raise _forbidden("The operator session is no longer active.")
    if str(session.authenticated_user_id or "") != str(user.id):
        raise _forbidden("The operator session belongs to a different authenticated user.")
    _require_line_edit(user, session.line_id)
    if work_order_id is not None:
        result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == work_order_id))
        work_order = result.scalar_one_or_none()
        if work_order is None:
            raise HTTPException(status_code=404, detail="Work order not found")
        if work_order.line_id and session.line_id != work_order.line_id:
            raise _forbidden("The work order is outside the active operator session line.")
        if not work_order.line_id and not (has_permission(user, "production.edit") or has_permission(user, "production.edit_all")):
            raise _forbidden("A scoped operator cannot act on a work order without a production-line assignment.")
    return session


async def _require_qc_session_and_scope(
    db: AsyncSession,
    user,
    session_id: Optional[UUID],
    work_order_id: UUID,
    *,
    action: str,
) -> SFSession:
    if session_id is None:
        raise _forbidden("An authenticated operator session is required for QC checkpoints.")
    session = await _get_session(db, session_id)
    if session.status != "ACTIVE":
        raise _forbidden("The operator session is no longer active.")
    if str(session.authenticated_user_id or "") != str(user.id):
        raise _forbidden("The operator session belongs to a different authenticated user.")
    result = await db.execute(
        select(ExecWorkOrder.line_id, Product.category)
        .join(ProdExecOrder, ExecWorkOrder.production_order_id == ProdExecOrder.id)
        .outerjoin(Product, Product.id == ProdExecOrder.product_id)
        .where(ExecWorkOrder.id == work_order_id)
    )
    context = result.one_or_none()
    if context is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    line_id, category = context
    if line_id:
        if session.line_id != line_id:
            raise _forbidden("The work order is outside the active operator session line.")
        if action == "view":
            _require_line_view(user, line_id)
        else:
            _require_line_edit(user, line_id)
    elif action == "view":
        _require_global_view(user)
    elif not has_any_permission(user, ("production.edit", "production.edit_all")):
        raise _forbidden("A scoped operator cannot record QC against a work order without a production line.")
    if session.current_work_order_id != work_order_id:
        raise _forbidden("Start this work order in the active operator session before recording QC.")

    category_value = str(getattr(category, "value", category)) if category is not None else None
    if action == "view":
        if has_any_permission(user, ("quality.view", "quality.view_all")):
            return session
        if category_value and can_view_scope(user, "quality", "product_category", category_value):
            return session
        raise _forbidden("Quality view permission is required for this product category.")
    if action == "edit":
        has_quality_view = has_any_permission(user, ("quality.view", "quality.view_all")) or bool(
            category_value and can_view_scope(user, "quality", "product_category", category_value)
        )
        if not has_quality_view:
            raise _forbidden("Quality view permission is required before recording a checkpoint.")
        if has_permission(user, "quality.edit_all"):
            return session
        if category_value and can_modify_scope(user, "quality", "edit", "product_category", category_value):
            return session
        raise _forbidden("Quality edit permission is required for this product category.")
    raise ValueError(f"Unsupported QC permission action: {action}")


# ── Dashboard & Status ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=SFDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    return await svc.get_dashboard(db)


@router.get("/live-status", response_model=LiveStatusResponse)
async def get_live_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    return await svc.get_live_status(db)


@router.get("/live-queue", response_model=List[LiveWOItem])
async def get_live_queue(
    line_id: Optional[str] = None,
    work_center_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_line_view(current_user, line_id)
    return await svc.get_live_queue(db, line_id=line_id, work_center_id=work_center_id)


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SFSessionOut, status_code=201)
async def create_session(
    body: SFSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_line_edit(current_user, body.line_id)
    data = body.model_dump(exclude_none=True)
    data["authenticated_user_id"] = current_user.id
    return await svc.login_session(db, data)


@router.get("/sessions", response_model=List[SFSessionOut])
async def list_sessions(
    status: Optional[str] = None,
    line_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if _has_global_view(current_user):
        pass
    else:
        _require_line_view(current_user, line_id)
    q = select(SFSession).order_by(SFSession.login_time.desc()).limit(100)
    if status:
        q = q.where(SFSession.status == status)
    if line_id:
        q = q.where(SFSession.line_id == line_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/sessions/active", response_model=List[SFSessionOut])
async def get_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    return await svc.get_active_sessions(db)


@router.get("/sessions/{session_id}", response_model=SFSessionOut)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(SFSession).where(SFSession.id == session_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Session not found")
    if str(obj.authenticated_user_id or "") != str(current_user.id):
        _require_line_view(current_user, obj.line_id)
    return obj


@router.post("/sessions/{session_id}/logout", response_model=SFSessionOut)
async def logout_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        session = await _get_session(db, session_id)
        if str(session.authenticated_user_id or "") != str(current_user.id):
            _require_line_edit(current_user, session.line_id)
        return await svc.logout_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Work Order Execution Actions ───────────────────────────────────────────────

@router.post("/work-orders/{wo_id}/start", response_model=WOActivityLogOut)
async def start_work_order(
    wo_id: UUID, body: StartWORequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="start", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.start_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            line_id=body.line_id,
            machine_id=body.machine_id,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/pause", response_model=WOActivityLogOut)
async def pause_work_order(
    wo_id: UUID, body: PauseWORequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="pause", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.pause_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            reason_code=body.reason_code,
            remarks=body.remarks,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/resume", response_model=WOActivityLogOut)
async def resume_work_order(
    wo_id: UUID, body: ResumeWORequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="resume", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.resume_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/update-qty", response_model=WOActivityLogOut)
async def update_qty(
    wo_id: UUID, body: QtyUpdateRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="update-qty", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.update_quantity(
            db, wo_id,
            qty_good=body.qty_good,
            qty_scrap=body.qty_scrap,
            qty_rework=body.qty_rework,
            scrap_category=body.scrap_category,
            scrap_reason=body.scrap_reason,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/scrap", response_model=WOActivityLogOut)
async def record_scrap(
    wo_id: UUID, body: ScrapRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="scrap", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.log_scrap(
            db, wo_id,
            qty_scrap=body.qty_scrap,
            scrap_category=body.scrap_category,
            scrap_reason=body.scrap_reason,
            reason_code=body.reason_code,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/finish", response_model=WOActivityLogOut)
async def finish_work_order(
    wo_id: UUID, body: FinishWORequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="finish", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.finish_work_order(
            db, wo_id,
            qty_good=body.qty_good,
            qty_scrap=body.qty_scrap,
            qty_rework=body.qty_rework,
            run_time_actual=body.run_time_actual,
            scrap_category=body.scrap_category,
            scrap_reason=body.scrap_reason,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/help", response_model=WOActivityLogOut)
async def request_help(
    wo_id: UUID, body: HelpRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="help", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.request_help(
            db, wo_id,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/qc-trigger", response_model=WOActivityLogOut)
async def trigger_qc(
    wo_id: UUID, body: QCTriggerRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="qc-trigger", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.trigger_qc(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.post("/work-orders/{wo_id}/note", response_model=WOActivityLogOut)
async def add_note(
    wo_id: UUID, body: NoteRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_execution_session(db, current_user, body.session_id, work_order_id=wo_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="note", resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        await svc.add_note(
            db, wo_id,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.get("/work-orders/{wo_id}/activity", response_model=List[WOActivityLogOut])
async def get_activity_log(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _has_global_view(current_user):
        line_result = await db.execute(select(ExecWorkOrder.line_id).where(ExecWorkOrder.id == wo_id))
        line_id = line_result.scalar_one_or_none()
        _require_line_view(current_user, line_id)
    return await svc.get_activity_log(db, wo_id)


@router.get("/work-orders/{wo_id}/materials", response_model=List[SFOperationMaterialOut])
async def get_work_order_materials(
    wo_id: UUID,
    session_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = await _require_execution_session(
        db, current_user, session_id, work_order_id=wo_id,
    )
    if session.current_work_order_id != wo_id:
        raise _forbidden("Start this work order in the active operator session before viewing its materials.")
    try:
        return await svc.list_work_order_materials(db, wo_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post(
    "/work-orders/{wo_id}/materials/{material_id}/consume",
    response_model=SFOperationMaterialOut,
)
async def consume_work_order_material(
    wo_id: UUID,
    material_id: UUID,
    body: SFMaterialConsumptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    session = await _require_execution_session(
        db, current_user, body.session_id, work_order_id=wo_id,
    )
    if session.current_work_order_id != wo_id:
        raise _forbidden("Start this work order in the active operator session before consuming materials.")
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action=f"materials/{material_id}/consume",
        resource_id=f"work-order:{wo_id}", user=current_user, body=body,
    )
    try:
        return await svc.consume_work_order_material(
            db,
            wo_id,
            material_id,
            body.qty,
            session_id=body.session_id,
            lot_no=body.lot_no,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
    except ValueError as e:
        raise _execution_action_error(e)


@router.get("/work-orders/{wo_id}/qc-checkpoints", response_model=List[WOActivityLogOut])
async def get_work_order_qc_checkpoints(
    wo_id: UUID,
    session_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _require_qc_session_and_scope(
        db, current_user, session_id, wo_id, action="view",
    )
    try:
        return await svc.get_qc_checkpoints(db, wo_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/qc-checkpoints", response_model=WOActivityLogOut, status_code=201)
async def record_work_order_qc_checkpoint(
    wo_id: UUID,
    body: SFQCCheckpointRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    await _require_qc_session_and_scope(
        db, current_user, body.session_id, wo_id, action="edit",
    )
    key, fingerprint = _execution_idempotency_context(
        idempotency_key, action="qc-checkpoints", resource_id=f"work-order:{wo_id}",
        user=current_user, body=body,
    )
    try:
        await svc.record_qc_checkpoint(
            db,
            wo_id,
            session_id=body.session_id,
            checkpoint_name=body.checkpoint_name,
            result=body.result,
            measured_value=body.measured_value,
            unit=body.unit,
            notes=body.notes,
            actor_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        return await _execution_activity_response(
            db, work_order_id=wo_id, user=current_user, idempotency_key=key,
        )
    except ValueError as e:
        raise _execution_action_error(e)


# ── Downtime ───────────────────────────────────────────────────────────────────

@router.post("/downtime", response_model=SFDowntimeOut, status_code=201)
async def start_downtime(
    body: SFDowntimeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    if body.production_order_id is not None and body.work_order_id is None:
        raise _forbidden("Order-linked downtime must reference its execution work order.")
    if body.session_id is not None:
        await _require_execution_session(db, current_user, body.session_id, work_order_id=body.work_order_id)
    elif body.work_order_id is not None or body.production_order_id is not None:
        raise _forbidden("An authenticated operator session is required for work-order-linked downtime.")
    else:
        _require_line_edit(current_user, body.line_id)
    key, fingerprint = _execution_idempotency_context(
        idempotency_key,
        action="downtime-start",
        resource_id=f"work-order:{body.work_order_id}" if body.work_order_id else f"line:{body.line_id}",
        user=current_user,
        body=body,
    )
    data = body.model_dump(exclude_none=True)
    data["created_by_user_id"] = current_user.id
    data["start_idempotency_key"] = key
    data["start_idempotency_fingerprint"] = fingerprint
    try:
        return await svc.start_downtime(db, data)
    except svc.IdempotencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/downtime", response_model=List[SFDowntimeOut])
async def list_downtime(
    is_closed: Optional[bool] = None,
    line_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_line_view(current_user, line_id)
    return await svc.list_downtime(db, closed=is_closed, line_id=line_id)


@router.post("/downtime/{dt_id}/stop", response_model=SFDowntimeOut)
async def stop_downtime(
    dt_id: UUID, body: StopDowntimeRequest, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    try:
        dt = await db.get(SFDowntimeLog, dt_id)
        if dt is None:
            raise HTTPException(status_code=404, detail="Downtime record not found")
        if str(dt.created_by_user_id or "") == str(current_user.id):
            _require_line_edit(current_user, dt.line_id)
        else:
            _require_production_approval(current_user)
        key, fingerprint = _execution_idempotency_context(
            idempotency_key,
            action="downtime-stop",
            resource_id=f"downtime:{dt_id}",
            user=current_user,
            body=body,
        )
        return await svc.stop_downtime(
            db,
            dt_id,
            comments=body.comments,
            closed_by_user_id=current_user.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
    except svc.IdempotencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(409 if "already closed" in str(e).lower() else 404, str(e))


# ── Shift Handovers ────────────────────────────────────────────────────────────

@router.post("/handovers", response_model=ShiftHandoverOut, status_code=201)
async def create_handover(
    body: ShiftHandoverCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_line_edit(current_user, body.line_id)
    data = body.model_dump(exclude_none=True)
    data["created_by_user_id"] = current_user.id
    data["outgoing_supervisor_id"] = None
    data["outgoing_supervisor"] = current_user.full_name
    return await svc.create_handover(db, data)


@router.get("/handovers", response_model=List[ShiftHandoverOut])
async def list_handovers(
    line_id: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_line_view(current_user, line_id)
    return await svc.list_handovers(db, line_id=line_id, limit=limit)


@router.post("/handovers/{handover_id}/approve", response_model=ShiftHandoverOut)
async def approve_handover(
    handover_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_production_approval(current_user)
    obj = await svc.approve_handover(
        db, handover_id, current_user.full_name, approved_by_user_id=current_user.id
    )
    if not obj:
        raise HTTPException(404, "Handover not found")
    return obj


# ── Supervisor Overrides ───────────────────────────────────────────────────────

@router.post("/overrides", response_model=SupervisorOverrideOut, status_code=201)
async def create_override(
    body: SupervisorOverrideCreate, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_production_approval(current_user)
    data = body.model_dump(exclude_none=True)
    data["supervisor_name"] = current_user.full_name
    data["actor_user_id"] = current_user.id
    return await svc.supervisor_override(
        db,
        **data,
    )


@router.get("/overrides", response_model=List[SupervisorOverrideOut])
async def list_overrides(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    return await svc.list_overrides(db, limit=limit)


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    return await svc.get_supervisor_alerts(db)


# ── AI Recommendations ─────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=dict)
async def run_ai_agents(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_production_approval(current_user)
    return await ai_svc.run_all_agents(db)


@router.get("/ai/recs", response_model=List[SFAIRecOut])
async def list_ai_recs(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    work_order_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_global_view(current_user)
    q = select(SFAIRec).order_by(SFAIRec.created_at.desc()).limit(100)
    if status:
        q = q.where(SFAIRec.status == status)
    if agent_type:
        q = q.where(SFAIRec.agent_type == agent_type)
    if work_order_id:
        q = q.where(SFAIRec.work_order_id == work_order_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/ai/recs/{rec_id}/action", response_model=SFAIRecOut)
async def action_ai_rec(
    rec_id: UUID, body: dict, db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_production_approval(current_user)
    result = await db.execute(select(SFAIRec).where(SFAIRec.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    action = body.get("status", "ACCEPTED")
    if action not in {"ACCEPTED", "REJECTED"}:
        raise HTTPException(status_code=422, detail="Recommendation action must be ACCEPTED or REJECTED")
    rec.status = action
    from datetime import datetime, timezone
    rec.actioned_at = datetime.now(timezone.utc)
    rec.actioned_by_user_id = current_user.id
    await db.commit()
    await db.refresh(rec)
    return rec
