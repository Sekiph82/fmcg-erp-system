"""Shop Floor Execution API endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.shop_floor import SFAIRec, SFSession
from app.schemas.shop_floor import (
    LiveStatusResponse, LiveWOItem, SFAIRecOut, SFDashboard,
    SFDowntimeCreate, SFDowntimeOut, SFSessionCreate, SFSessionOut,
    ShiftHandoverCreate, ShiftHandoverOut, StartWORequest, PauseWORequest,
    ResumeWORequest, QtyUpdateRequest, ScrapRequest, FinishWORequest,
    HelpRequest, QCTriggerRequest, NoteRequest, StopDowntimeRequest,
    SupervisorOverrideCreate, SupervisorOverrideOut, WOActivityLogOut,
)
from app.services import shop_floor_service as svc
from app.services import shop_floor_ai_service as ai_svc


router = APIRouter()


# ── Dashboard & Status ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=SFDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


@router.get("/live-status", response_model=LiveStatusResponse)
async def get_live_status(db: AsyncSession = Depends(get_db)):
    return await svc.get_live_status(db)


@router.get("/live-queue", response_model=List[LiveWOItem])
async def get_live_queue(
    line_id: Optional[str] = None,
    work_center_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_live_queue(db, line_id=line_id, work_center_id=work_center_id)


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SFSessionOut, status_code=201)
async def create_session(body: SFSessionCreate, db: AsyncSession = Depends(get_db)):
    return await svc.login_session(db, body.model_dump(exclude_none=True))


@router.get("/sessions", response_model=List[SFSessionOut])
async def list_sessions(
    status: Optional[str] = None,
    line_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SFSession).order_by(SFSession.login_time.desc()).limit(100)
    if status:
        q = q.where(SFSession.status == status)
    if line_id:
        q = q.where(SFSession.line_id == line_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/sessions/active", response_model=List[SFSessionOut])
async def get_active_sessions(db: AsyncSession = Depends(get_db)):
    return await svc.get_active_sessions(db)


@router.get("/sessions/{session_id}", response_model=SFSessionOut)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SFSession).where(SFSession.id == session_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.post("/sessions/{session_id}/logout", response_model=SFSessionOut)
async def logout_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.logout_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Work Order Execution Actions ───────────────────────────────────────────────

@router.post("/work-orders/{wo_id}/start", response_model=WOActivityLogOut)
async def start_work_order(
    wo_id: UUID, body: StartWORequest, db: AsyncSession = Depends(get_db)
):
    try:
        wo = await svc.start_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            line_id=body.line_id,
            machine_id=body.machine_id,
        )
        # Return the activity log entry
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/pause", response_model=WOActivityLogOut)
async def pause_work_order(
    wo_id: UUID, body: PauseWORequest, db: AsyncSession = Depends(get_db)
):
    try:
        await svc.pause_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            reason_code=body.reason_code,
            remarks=body.remarks,
        )
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/resume", response_model=WOActivityLogOut)
async def resume_work_order(
    wo_id: UUID, body: ResumeWORequest, db: AsyncSession = Depends(get_db)
):
    try:
        await svc.resume_work_order(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
        )
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/update-qty", response_model=WOActivityLogOut)
async def update_qty(
    wo_id: UUID, body: QtyUpdateRequest, db: AsyncSession = Depends(get_db)
):
    try:
        await svc.update_quantity(
            db, wo_id,
            qty_good=body.qty_good,
            qty_scrap=body.qty_scrap,
            qty_rework=body.qty_rework,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
        )
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/scrap", response_model=WOActivityLogOut)
async def record_scrap(
    wo_id: UUID, body: ScrapRequest, db: AsyncSession = Depends(get_db)
):
    try:
        await svc.log_scrap(
            db, wo_id,
            qty_scrap=body.qty_scrap,
            reason_code=body.reason_code,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
        )
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/finish", response_model=WOActivityLogOut)
async def finish_work_order(
    wo_id: UUID, body: FinishWORequest, db: AsyncSession = Depends(get_db)
):
    try:
        await svc.finish_work_order(
            db, wo_id,
            qty_good=body.qty_good,
            qty_scrap=body.qty_scrap,
            qty_rework=body.qty_rework,
            run_time_actual=body.run_time_actual,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
        )
        logs = await svc.get_activity_log(db, wo_id, limit=1)
        return logs[0]
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/help", response_model=WOActivityLogOut)
async def request_help(
    wo_id: UUID, body: HelpRequest, db: AsyncSession = Depends(get_db)
):
    try:
        return await svc.request_help(
            db, wo_id,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/qc-trigger", response_model=WOActivityLogOut)
async def trigger_qc(
    wo_id: UUID, body: QCTriggerRequest, db: AsyncSession = Depends(get_db)
):
    try:
        return await svc.trigger_qc(
            db, wo_id,
            session_id=body.session_id,
            operator_name=body.operator_name,
            remarks=body.remarks,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/note", response_model=WOActivityLogOut)
async def add_note(
    wo_id: UUID, body: NoteRequest, db: AsyncSession = Depends(get_db)
):
    try:
        return await svc.add_note(
            db, wo_id,
            remarks=body.remarks,
            session_id=body.session_id,
            operator_name=body.operator_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/work-orders/{wo_id}/activity", response_model=List[WOActivityLogOut])
async def get_activity_log(wo_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_activity_log(db, wo_id)


# ── Downtime ───────────────────────────────────────────────────────────────────

@router.post("/downtime", response_model=SFDowntimeOut, status_code=201)
async def start_downtime(body: SFDowntimeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.start_downtime(db, body.model_dump(exclude_none=True))


@router.get("/downtime", response_model=List[SFDowntimeOut])
async def list_downtime(
    is_closed: Optional[bool] = None,
    line_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_downtime(db, closed=is_closed, line_id=line_id)


@router.post("/downtime/{dt_id}/stop", response_model=SFDowntimeOut)
async def stop_downtime(
    dt_id: UUID, body: StopDowntimeRequest, db: AsyncSession = Depends(get_db)
):
    try:
        return await svc.stop_downtime(db, dt_id, comments=body.comments)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Shift Handovers ────────────────────────────────────────────────────────────

@router.post("/handovers", response_model=ShiftHandoverOut, status_code=201)
async def create_handover(body: ShiftHandoverCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_handover(db, body.model_dump(exclude_none=True))


@router.get("/handovers", response_model=List[ShiftHandoverOut])
async def list_handovers(
    line_id: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_handovers(db, line_id=line_id, limit=limit)


@router.post("/handovers/{handover_id}/approve", response_model=ShiftHandoverOut)
async def approve_handover(
    handover_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    approved_by = body.get("approved_by", "Supervisor")
    obj = await svc.approve_handover(db, handover_id, approved_by)
    if not obj:
        raise HTTPException(404, "Handover not found")
    return obj


# ── Supervisor Overrides ───────────────────────────────────────────────────────

@router.post("/overrides", response_model=SupervisorOverrideOut, status_code=201)
async def create_override(
    body: SupervisorOverrideCreate, db: AsyncSession = Depends(get_db)
):
    return await svc.supervisor_override(
        db,
        work_order_id=body.work_order_id,
        supervisor_name=body.supervisor_name,
        override_type=body.override_type,
        reason=body.reason,
        notes=body.notes,
        target_operator_name=body.target_operator_name,
        production_order_id=body.production_order_id,
    )


@router.get("/overrides", response_model=List[SupervisorOverrideOut])
async def list_overrides(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_overrides(db, limit=limit)


@router.get("/alerts")
async def get_alerts(db: AsyncSession = Depends(get_db)):
    return await svc.get_supervisor_alerts(db)


# ── AI Recommendations ─────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=dict)
async def run_ai_agents(db: AsyncSession = Depends(get_db)):
    return await ai_svc.run_all_agents(db)


@router.get("/ai/recs", response_model=List[SFAIRecOut])
async def list_ai_recs(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    work_order_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
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
    rec_id: UUID, body: dict, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SFAIRec).where(SFAIRec.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    action = body.get("status", "ACCEPTED")
    rec.status = action
    from datetime import datetime, timezone
    rec.actioned_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rec)
    return rec
