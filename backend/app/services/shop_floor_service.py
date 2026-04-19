"""
Shop Floor Execution Service — sessions, activity logs, downtime, handovers, supervisor controls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shop_floor import (
    SFSession, WOActivityLog, SFDowntimeLog,
    ShiftHandover, SupervisorOverride, SFAIRec,
)
from app.models.production_execution import ExecWorkOrder, ProdExecOrder


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_code() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SES-{ts}-{str(uuid.uuid4())[:4].upper()}"


def _derive_live_status(wo: ExecWorkOrder, active_downtime: bool, last_event_type: Optional[str]) -> str:
    """Map ExecWorkOrder.status + context to shop-floor live status."""
    if wo.status == "COMPLETED":
        return "COMPLETED"
    if wo.status == "CANCELLED":
        return "CANCELLED"
    if wo.status == "PENDING":
        return "WAITING"
    if active_downtime:
        return "BLOCKED"
    if last_event_type == "HELP_REQUEST":
        return "SUPERVISOR_REVIEW"
    if last_event_type == "QC_TRIGGER":
        return "QC_HOLD"
    if wo.status == "PAUSED":
        return "PAUSED"
    if wo.status == "IN_PROGRESS":
        return "RUNNING"
    if wo.status == "READY":
        return "READY"
    return "WAITING"


async def _log_event(
    db: AsyncSession,
    work_order_id: uuid.UUID,
    production_order_id: Optional[uuid.UUID],
    event_type: str,
    session_id: Optional[uuid.UUID] = None,
    operator_name: Optional[str] = None,
    line_id: Optional[str] = None,
    qty_good: Optional[Decimal] = None,
    qty_scrap: Optional[Decimal] = None,
    qty_rework: Optional[Decimal] = None,
    reason_code: Optional[str] = None,
    remarks: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> WOActivityLog:
    entry = WOActivityLog(
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        session_id=session_id,
        operator_name=operator_name,
        line_id=line_id,
        event_type=event_type,
        qty_good=qty_good,
        qty_scrap=qty_scrap,
        qty_rework=qty_rework,
        reason_code=reason_code,
        remarks=remarks,
        extra_data=extra_data,
    )
    db.add(entry)
    await db.flush()
    return entry


async def _get_wo(db: AsyncSession, wo_id: uuid.UUID) -> ExecWorkOrder:
    result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise ValueError(f"Work order {wo_id} not found")
    return wo


# ── Sessions ───────────────────────────────────────────────────────────────────

async def login_session(db: AsyncSession, data: dict) -> SFSession:
    session = SFSession(
        session_code=_session_code(),
        status="ACTIVE",
        login_time=_now(),
        **data,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def logout_session(db: AsyncSession, session_id: uuid.UUID) -> SFSession:
    result = await db.execute(select(SFSession).where(SFSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")
    session.status = "LOGGED_OUT"
    session.logout_time = _now()
    await db.commit()
    await db.refresh(session)
    return session


async def get_active_sessions(db: AsyncSession) -> List[SFSession]:
    result = await db.execute(
        select(SFSession).where(SFSession.status == "ACTIVE").order_by(SFSession.login_time.desc())
    )
    return result.scalars().all()


# ── Live Queue ─────────────────────────────────────────────────────────────────

async def get_live_queue(
    db: AsyncSession,
    work_center_id: Optional[uuid.UUID] = None,
    line_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    q = (
        select(ExecWorkOrder, ProdExecOrder)
        .join(ProdExecOrder, ExecWorkOrder.production_order_id == ProdExecOrder.id, isouter=True)
        .where(ExecWorkOrder.status.in_(["READY", "IN_PROGRESS", "PAUSED", "PENDING"]))
        .order_by(ProdExecOrder.priority.asc(), ExecWorkOrder.step_sequence.asc())
        .limit(limit)
    )
    if work_center_id:
        q = q.where(ExecWorkOrder.work_center_id == work_center_id)
    if line_id:
        q = q.where(ExecWorkOrder.line_id == line_id)

    result = await db.execute(q)
    rows = result.all()

    items = []
    for wo, po in rows:
        # Get last event
        log_result = await db.execute(
            select(WOActivityLog)
            .where(WOActivityLog.work_order_id == wo.id)
            .order_by(WOActivityLog.created_at.desc())
            .limit(1)
        )
        last_log = log_result.scalar_one_or_none()

        # Check active downtime
        dt_result = await db.execute(
            select(SFDowntimeLog)
            .where(SFDowntimeLog.work_order_id == wo.id)
            .where(SFDowntimeLog.is_closed == False)  # noqa
            .limit(1)
        )
        active_dt = dt_result.scalar_one_or_none()

        last_event_type = last_log.event_type if last_log else None
        live_status = _derive_live_status(wo, active_dt is not None, last_event_type)

        if status_filter and live_status != status_filter:
            continue

        items.append({
            "id": str(wo.id),
            "work_order_id": str(wo.id),
            "production_order_id": str(wo.production_order_id) if wo.production_order_id else None,
            "order_no": po.order_no if po else None,
            "step_sequence": wo.step_sequence,
            "step_name": wo.step_name,
            "work_center_id": str(wo.work_center_id) if wo.work_center_id else None,
            "line_id": wo.line_id,
            "planned_qty": float(wo.planned_qty),
            "completed_qty": float(wo.completed_qty or 0),
            "scrap_qty": float(wo.scrap_qty or 0),
            "status": wo.status,
            "live_status": live_status,
            "started_at": wo.started_at.isoformat() if wo.started_at else None,
            "planned_start": po.planned_start.isoformat() if po and po.planned_start else None,
            "planned_end": po.planned_end.isoformat() if po and po.planned_end else None,
            "product_name": po.product_name if po else None,
            "batch_no": po.batch_no if po else None,
            "qc_required_flag": bool(wo.qc_required_flag),
            "has_active_downtime": active_dt is not None,
            "last_event": last_log.event_type if last_log else None,
            "last_event_time": last_log.created_at.isoformat() if last_log else None,
            "operator_name": last_log.operator_name if last_log else None,
        })

    return items


# ── Work Order Execution ───────────────────────────────────────────────────────

async def start_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    line_id: Optional[str],
    machine_id: Optional[uuid.UUID],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    if wo.status not in {"READY", "PENDING", "PAUSED"}:
        raise ValueError(f"Work order cannot be started from status {wo.status}")
    wo.status = "IN_PROGRESS"
    if not wo.started_at:
        wo.started_at = _now()
    await _log_event(
        db, wo_id, wo.production_order_id, "START",
        session_id=session_id, operator_name=operator_name, line_id=line_id,
    )
    if session_id:
        s_result = await db.execute(select(SFSession).where(SFSession.id == session_id))
        sess = s_result.scalar_one_or_none()
        if sess:
            sess.current_work_order_id = wo_id
    await db.commit()
    await db.refresh(wo)
    return wo


async def pause_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    reason_code: Optional[str],
    remarks: Optional[str],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    if wo.status != "IN_PROGRESS":
        raise ValueError("Work order must be IN_PROGRESS to pause")
    wo.status = "PAUSED"
    await _log_event(
        db, wo_id, wo.production_order_id, "PAUSE",
        session_id=session_id, operator_name=operator_name,
        reason_code=reason_code, remarks=remarks,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def resume_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    if wo.status not in {"PAUSED"}:
        raise ValueError("Work order must be PAUSED to resume")
    wo.status = "IN_PROGRESS"
    await _log_event(
        db, wo_id, wo.production_order_id, "RESUME",
        session_id=session_id, operator_name=operator_name,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def update_quantity(
    db: AsyncSession,
    wo_id: uuid.UUID,
    qty_good: Decimal,
    qty_scrap: Decimal,
    qty_rework: Decimal,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    remarks: Optional[str],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    if qty_good < 0 or qty_scrap < 0 or qty_rework < 0:
        raise ValueError("Quantities cannot be negative")
    wo.completed_qty = qty_good
    wo.scrap_qty = qty_scrap
    wo.rework_qty = qty_rework
    await _log_event(
        db, wo_id, wo.production_order_id, "QTY_UPDATE",
        session_id=session_id, operator_name=operator_name,
        qty_good=qty_good, qty_scrap=qty_scrap, qty_rework=qty_rework,
        remarks=remarks,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def log_scrap(
    db: AsyncSession,
    wo_id: uuid.UUID,
    qty_scrap: Decimal,
    reason_code: Optional[str],
    remarks: Optional[str],
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    wo.scrap_qty = (wo.scrap_qty or Decimal("0")) + qty_scrap
    await _log_event(
        db, wo_id, wo.production_order_id, "SCRAP",
        session_id=session_id, operator_name=operator_name,
        qty_scrap=qty_scrap, reason_code=reason_code, remarks=remarks,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def finish_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    qty_good: Decimal,
    qty_scrap: Decimal,
    qty_rework: Decimal,
    run_time_actual: Optional[Decimal],
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    remarks: Optional[str],
) -> ExecWorkOrder:
    wo = await _get_wo(db, wo_id)
    if wo.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Work order must be IN_PROGRESS or PAUSED to finish")
    wo.status = "COMPLETED"
    wo.completed_qty = qty_good
    wo.scrap_qty = qty_scrap
    wo.rework_qty = qty_rework
    wo.completed_at = _now()
    if run_time_actual is not None:
        wo.run_time_actual = run_time_actual

    await _log_event(
        db, wo_id, wo.production_order_id, "FINISH",
        session_id=session_id, operator_name=operator_name,
        qty_good=qty_good, qty_scrap=qty_scrap, qty_rework=qty_rework,
        remarks=remarks,
    )

    # Unblock next WO in chain
    next_result = await db.execute(
        select(ExecWorkOrder)
        .where(ExecWorkOrder.dependency_work_order_id == wo_id)
        .where(ExecWorkOrder.status == "PENDING")
    )
    for nwo in next_result.scalars().all():
        nwo.status = "READY"

    if session_id:
        s_result = await db.execute(select(SFSession).where(SFSession.id == session_id))
        sess = s_result.scalar_one_or_none()
        if sess:
            sess.current_work_order_id = None

    await db.commit()
    await db.refresh(wo)
    return wo


async def request_help(
    db: AsyncSession,
    wo_id: uuid.UUID,
    remarks: str,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
) -> WOActivityLog:
    wo = await _get_wo(db, wo_id)
    entry = await _log_event(
        db, wo_id, wo.production_order_id, "HELP_REQUEST",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
    )
    await db.commit()
    return entry


async def trigger_qc(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    remarks: Optional[str],
) -> WOActivityLog:
    wo = await _get_wo(db, wo_id)
    entry = await _log_event(
        db, wo_id, wo.production_order_id, "QC_TRIGGER",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
    )
    await db.commit()
    return entry


async def add_note(
    db: AsyncSession,
    wo_id: uuid.UUID,
    remarks: str,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
) -> WOActivityLog:
    wo = await _get_wo(db, wo_id)
    entry = await _log_event(
        db, wo_id, wo.production_order_id, "NOTE",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
    )
    await db.commit()
    return entry


async def get_activity_log(db: AsyncSession, wo_id: uuid.UUID, limit: int = 100) -> List[WOActivityLog]:
    result = await db.execute(
        select(WOActivityLog)
        .where(WOActivityLog.work_order_id == wo_id)
        .order_by(WOActivityLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ── Downtime ───────────────────────────────────────────────────────────────────

async def start_downtime(db: AsyncSession, data: dict) -> SFDowntimeLog:
    dt = SFDowntimeLog(**data, is_closed=False, start_time=_now())
    db.add(dt)
    if data.get("work_order_id"):
        await _log_event(
            db,
            data["work_order_id"],
            data.get("production_order_id"),
            "DOWNTIME_START",
            operator_name=data.get("operator_name"),
            line_id=data.get("line_id"),
            reason_code=data.get("downtime_category"),
            remarks=data.get("root_reason"),
        )
    await db.commit()
    await db.refresh(dt)
    return dt


async def stop_downtime(
    db: AsyncSession, downtime_id: uuid.UUID, comments: Optional[str]
) -> SFDowntimeLog:
    result = await db.execute(select(SFDowntimeLog).where(SFDowntimeLog.id == downtime_id))
    dt = result.scalar_one_or_none()
    if not dt:
        raise ValueError("Downtime record not found")
    dt.end_time = _now()
    dt.is_closed = True
    elapsed = (dt.end_time - dt.start_time).total_seconds() / 60
    dt.duration_minutes = Decimal(str(round(elapsed, 2)))
    if comments:
        dt.comments = comments
    if dt.work_order_id:
        await _log_event(
            db, dt.work_order_id, dt.production_order_id, "DOWNTIME_STOP",
            operator_name=dt.operator_name, line_id=dt.line_id,
            duration_minutes=dt.duration_minutes,
        )
    await db.commit()
    await db.refresh(dt)
    return dt


async def get_active_downtimes(db: AsyncSession) -> List[SFDowntimeLog]:
    result = await db.execute(
        select(SFDowntimeLog)
        .where(SFDowntimeLog.is_closed == False)  # noqa
        .order_by(SFDowntimeLog.start_time.desc())
    )
    return result.scalars().all()


async def list_downtime(
    db: AsyncSession,
    line_id: Optional[str] = None,
    closed: Optional[bool] = None,
    limit: int = 100,
) -> List[SFDowntimeLog]:
    q = select(SFDowntimeLog).order_by(SFDowntimeLog.start_time.desc()).limit(limit)
    if line_id:
        q = q.where(SFDowntimeLog.line_id == line_id)
    if closed is not None:
        q = q.where(SFDowntimeLog.is_closed == closed)
    result = await db.execute(q)
    return result.scalars().all()


# ── Shift Handover ─────────────────────────────────────────────────────────────

async def create_handover(db: AsyncSession, data: dict) -> ShiftHandover:
    ho = ShiftHandover(**data, handover_time=_now())
    db.add(ho)
    await db.commit()
    await db.refresh(ho)
    return ho


async def approve_handover(db: AsyncSession, handover_id: uuid.UUID, approved_by: str) -> ShiftHandover:
    result = await db.execute(select(ShiftHandover).where(ShiftHandover.id == handover_id))
    ho = result.scalar_one_or_none()
    if not ho:
        raise ValueError("Handover not found")
    ho.is_approved = True
    ho.approved_by = approved_by
    ho.approved_at = _now()
    await db.commit()
    await db.refresh(ho)
    return ho


async def list_handovers(
    db: AsyncSession, line_id: Optional[str] = None, limit: int = 50
) -> List[ShiftHandover]:
    q = select(ShiftHandover).order_by(ShiftHandover.handover_time.desc()).limit(limit)
    if line_id:
        q = q.where(ShiftHandover.line_id == line_id)
    result = await db.execute(q)
    return result.scalars().all()


# ── Supervisor Controls ────────────────────────────────────────────────────────

async def supervisor_override(
    db: AsyncSession,
    work_order_id: Optional[uuid.UUID],
    supervisor_name: str,
    override_type: str,
    reason: Optional[str],
    notes: Optional[str],
    target_operator_name: Optional[str],
    production_order_id: Optional[uuid.UUID],
) -> SupervisorOverride:
    ov = SupervisorOverride(
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        supervisor_name=supervisor_name,
        override_type=override_type,
        reason=reason,
        notes=notes,
        target_operator_name=target_operator_name,
        approved_at=_now(),
    )
    db.add(ov)
    if work_order_id:
        await _log_event(
            db, work_order_id, production_order_id, "SUPERVISOR_OVERRIDE",
            operator_name=supervisor_name, reason_code=override_type, remarks=reason,
        )
    await db.commit()
    await db.refresh(ov)
    return ov


async def get_supervisor_alerts(db: AsyncSession) -> List[dict]:
    """Identify situations requiring supervisor attention."""
    alerts = []
    now = _now()

    # Active downtimes > 30 min
    dt_result = await db.execute(
        select(SFDowntimeLog).where(SFDowntimeLog.is_closed == False)  # noqa
    )
    for dt in dt_result.scalars().all():
        elapsed_min = (now - dt.start_time).total_seconds() / 60
        if elapsed_min > 30:
            alerts.append({
                "type": "LONG_DOWNTIME",
                "severity": "HIGH" if elapsed_min > 60 else "MEDIUM",
                "message": f"Downtime on line {dt.line_id or '?'}: {dt.downtime_category} — {int(elapsed_min)} min",
                "line_id": dt.line_id,
                "work_order_id": str(dt.work_order_id) if dt.work_order_id else None,
            })

    # Open help requests in last 2 hrs
    help_result = await db.execute(
        select(WOActivityLog)
        .where(WOActivityLog.event_type == "HELP_REQUEST")
        .where(WOActivityLog.timestamp_start >= now - timedelta(hours=2))
        .order_by(WOActivityLog.created_at.desc())
    )
    for log in help_result.scalars().all():
        alerts.append({
            "type": "HELP_REQUEST",
            "severity": "MEDIUM",
            "message": f"Help requested: {log.remarks or 'No details'}",
            "work_order_id": str(log.work_order_id),
            "operator_name": log.operator_name,
        })

    # QC holds older than 1 hr
    qc_result = await db.execute(
        select(WOActivityLog)
        .where(WOActivityLog.event_type == "QC_TRIGGER")
        .where(WOActivityLog.timestamp_start >= now - timedelta(hours=8))
        .order_by(WOActivityLog.created_at.desc())
    )
    for log in qc_result.scalars().all():
        elapsed_min = (now - log.created_at).total_seconds() / 60
        if elapsed_min > 60:
            alerts.append({
                "type": "QC_HOLD_LONG",
                "severity": "HIGH",
                "message": f"QC hold {int(elapsed_min)} min — work order step",
                "work_order_id": str(log.work_order_id),
            })

    # Delayed work orders
    wo_result = await db.execute(
        select(ExecWorkOrder, ProdExecOrder)
        .join(ProdExecOrder, ExecWorkOrder.production_order_id == ProdExecOrder.id, isouter=True)
        .where(ExecWorkOrder.status == "IN_PROGRESS")
        .where(ProdExecOrder.planned_end < now)
    )
    for wo, po in wo_result.all():
        if po:
            delay_min = (now - po.planned_end).total_seconds() / 60
            alerts.append({
                "type": "DELAYED_ORDER",
                "severity": "HIGH" if delay_min > 60 else "MEDIUM",
                "message": f"Order {po.order_no} is {int(delay_min)} min late — step: {wo.step_name}",
                "work_order_id": str(wo.id),
                "production_order_id": str(po.id),
            })

    return alerts[:20]  # cap for performance


async def list_overrides(
    db: AsyncSession, limit: int = 100
) -> List[SupervisorOverride]:
    result = await db.execute(
        select(SupervisorOverride).order_by(SupervisorOverride.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


# ── Live Status ────────────────────────────────────────────────────────────────

async def get_live_status(db: AsyncSession) -> dict:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_sess = (await db.execute(
        select(func.count()).select_from(SFSession).where(SFSession.status == "ACTIVE")
    )).scalar() or 0

    running = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "IN_PROGRESS")
    )).scalar() or 0

    paused = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "PAUSED")
    )).scalar() or 0

    waiting = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "READY")
    )).scalar() or 0

    active_dt = (await db.execute(
        select(func.count()).select_from(SFDowntimeLog).where(SFDowntimeLog.is_closed == False)  # noqa
    )).scalar() or 0

    # QC holds — count WOs with last event = QC_TRIGGER and status != COMPLETED
    qc_result = await db.execute(
        select(func.count(WOActivityLog.work_order_id.distinct()))
        .where(WOActivityLog.event_type == "QC_TRIGGER")
        .where(WOActivityLog.timestamp_start >= today_start)
    )
    qc_hold = qc_result.scalar() or 0

    help_result = await db.execute(
        select(func.count()).select_from(WOActivityLog)
        .where(WOActivityLog.event_type == "HELP_REQUEST")
        .where(WOActivityLog.timestamp_start >= today_start)
    )
    help_open = help_result.scalar() or 0

    good_qty = (await db.execute(
        select(func.sum(WOActivityLog.qty_good))
        .where(WOActivityLog.event_type == "FINISH")
        .where(WOActivityLog.timestamp_start >= today_start)
    )).scalar() or 0

    scrap_qty = (await db.execute(
        select(func.sum(WOActivityLog.qty_scrap))
        .where(WOActivityLog.timestamp_start >= today_start)
    )).scalar() or 0

    alerts = await get_supervisor_alerts(db)

    return {
        "total_work_orders": running + paused + waiting,
        "running": running,
        "paused": paused,
        "waiting": waiting,
        "qc_hold": qc_hold,
        "active_sessions": active_sess,
        "active_downtime": active_dt,
        "alerts": alerts[:5],
        "by_line": {},
        "timestamp": now.isoformat(),
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_sess = (await db.execute(
        select(func.count()).select_from(SFSession).where(SFSession.status == "ACTIVE")
    )).scalar() or 0

    running = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "IN_PROGRESS")
    )).scalar() or 0

    paused = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "PAUSED")
    )).scalar() or 0

    active_dts_result = await db.execute(
        select(SFDowntimeLog).where(SFDowntimeLog.is_closed == False).order_by(SFDowntimeLog.start_time.desc()).limit(10)  # noqa
    )
    active_dts = active_dts_result.scalars().all()

    recent_ho_result = await db.execute(
        select(ShiftHandover).order_by(ShiftHandover.handover_time.desc()).limit(5)
    )
    recent_handovers = recent_ho_result.scalars().all()

    pending_ai = (await db.execute(
        select(func.count()).select_from(SFAIRec).where(SFAIRec.status == "PENDING")
    )).scalar() or 0

    good_qty = (await db.execute(
        select(func.sum(WOActivityLog.qty_good))
        .where(WOActivityLog.event_type.in_(["FINISH", "QTY_UPDATE"]))
        .where(WOActivityLog.timestamp_start >= today_start)
    )).scalar() or 0

    scrap_qty = (await db.execute(
        select(func.sum(WOActivityLog.qty_scrap))
        .where(WOActivityLog.timestamp_start >= today_start)
    )).scalar() or 0

    help_count = (await db.execute(
        select(func.count()).select_from(WOActivityLog)
        .where(WOActivityLog.event_type == "HELP_REQUEST")
        .where(WOActivityLog.timestamp_start >= today_start)
    )).scalar() or 0

    ov_count = (await db.execute(
        select(func.count()).select_from(SupervisorOverride)
        .where(SupervisorOverride.created_at >= today_start)
    )).scalar() or 0

    qc_result = await db.execute(
        select(func.count(WOActivityLog.work_order_id.distinct()))
        .where(WOActivityLog.event_type == "QC_TRIGGER")
        .where(WOActivityLog.timestamp_start >= today_start)
    )
    qc_hold = qc_result.scalar() or 0

    return {
        "active_sessions": active_sess,
        "running_work_orders": running,
        "paused_work_orders": paused,
        "qc_hold_count": qc_hold,
        "active_downtime_count": len(active_dts),
        "help_requests_open": help_count,
        "total_scrap_today": float(scrap_qty),
        "total_good_qty_today": float(good_qty),
        "pending_ai_recs": pending_ai,
        "recent_handovers": recent_handovers,
        "active_downtimes": active_dts,
        "supervisor_overrides_today": ov_count,
    }
