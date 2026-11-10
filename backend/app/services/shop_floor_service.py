"""
Shop Floor Execution Service — sessions, activity logs, downtime, handovers, supervisor controls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shop_floor import (
    SFSession, WOActivityLog, SFDowntimeLog,
    ShiftHandover, SupervisorOverride, SFAIRec,
)
from app.services.production_transition_history import record_shop_floor_transition
from app.models.production_execution import ExecOrderMaterial, ExecWorkOrder, ProdExecOrder
from app.services.machine_operator_service import validate_operator_qualification


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_code() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SES-{ts}-{str(uuid.uuid4())[:4].upper()}"


async def _get_session_context(
    db: AsyncSession, session_id: uuid.UUID, *, allow_inactive: bool = False
) -> SFSession:
    result = await db.execute(select(SFSession).where(SFSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise ValueError("Operator session not found")
    if not allow_inactive and session.status != "ACTIVE":
        raise ValueError("Operator session is not active")
    return session


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
    duration_minutes: Optional[Decimal] = None,
    reason_code: Optional[str] = None,
    remarks: Optional[str] = None,
    extra_data: Optional[dict] = None,
    allow_inactive_session: bool = False,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    idempotency_fingerprint: Optional[str] = None,
) -> WOActivityLog:
    session = (
        await _get_session_context(db, session_id, allow_inactive=allow_inactive_session)
        if session_id is not None else None
    )

    entry = WOActivityLog(
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        session_id=session_id,
        actor_user_id=actor_user_id or (session.authenticated_user_id if session else None),
        operator_id=session.operator_id if session else None,
        operator_name=session.operator_name if session else operator_name,
        team_id=session.team_id if session else None,
        machine_id=session.machine_id if session else None,
        line_id=session.line_id if session else line_id,
        shift_id=session.shift_id if session else None,
        event_type=event_type,
        qty_good=qty_good,
        qty_scrap=qty_scrap,
        qty_rework=qty_rework,
        duration_minutes=duration_minutes,
        reason_code=reason_code,
        remarks=remarks,
        extra_data=extra_data,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    db.add(entry)
    await db.flush()
    return entry


class IdempotencyConflictError(ValueError):
    """An idempotency key was replayed with a different execution request."""


async def _find_idempotent_execution_event(
    db: AsyncSession,
    work_order_id: uuid.UUID,
    actor_user_id: Optional[uuid.UUID],
    idempotency_key: Optional[str],
    request_fingerprint: Optional[str],
) -> Optional[WOActivityLog]:
    if idempotency_key is None:
        return None
    if actor_user_id is None or request_fingerprint is None:
        raise ValueError("Authenticated actor and request fingerprint are required for idempotent execution")
    result = await db.execute(
        select(WOActivityLog)
        .where(
            WOActivityLog.work_order_id == work_order_id,
            WOActivityLog.actor_user_id == actor_user_id,
            WOActivityLog.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        return None
    if existing.idempotency_fingerprint != request_fingerprint:
        raise IdempotencyConflictError(
            "This idempotency key was already used for a different Shop Floor action or payload."
        )
    return existing


async def get_execution_idempotency_event(
    db: AsyncSession,
    work_order_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    idempotency_key: str,
) -> Optional[WOActivityLog]:
    result = await db.execute(
        select(WOActivityLog).where(
            WOActivityLog.work_order_id == work_order_id,
            WOActivityLog.actor_user_id == actor_user_id,
            WOActivityLog.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


async def _get_wo(db: AsyncSession, wo_id: uuid.UUID) -> ExecWorkOrder:
    result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise ValueError(f"Work order {wo_id} not found")
    return wo


async def _lock_wo_context(
    db: AsyncSession, wo_id: uuid.UUID
) -> tuple[ProdExecOrder, ExecWorkOrder]:
    parent_id_result = await db.execute(
        select(ExecWorkOrder.production_order_id).where(ExecWorkOrder.id == wo_id)
    )
    parent_id = parent_id_result.scalar_one_or_none()
    if parent_id is None:
        raise ValueError(f"Work order {wo_id} not found")

    # Match the production execution service's parent-then-child lock order.
    parent_result = await db.execute(
        select(ProdExecOrder)
        .where(ProdExecOrder.id == parent_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    parent = parent_result.scalar_one_or_none()
    if parent is None:
        raise ValueError("Parent production order not found")

    work_order_result = await db.execute(
        select(ExecWorkOrder)
        .where(ExecWorkOrder.id == wo_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    work_order = work_order_result.scalar_one_or_none()
    if work_order is None:
        raise ValueError(f"Work order {wo_id} not found")
    if work_order.production_order_id != parent.id:
        raise ValueError("Work order changed production order during transition")
    return parent, work_order


def _require_parent_in_progress(parent: ProdExecOrder) -> None:
    if parent.status != "IN_PROGRESS":
        raise ValueError(
            f"Production order must be IN_PROGRESS for shop-floor work (status={parent.status})"
        )


def _material_outstanding_qty(material: ExecOrderMaterial) -> Decimal:
    issued = material.issued_qty or Decimal("0")
    consumed = material.consumed_qty or Decimal("0")
    returned = material.returned_qty or Decimal("0")
    if any(not value.is_finite() for value in (issued, consumed, returned)):
        raise ValueError("Material issue, consumption, and return totals must be finite")
    outstanding = issued - consumed - returned
    if outstanding < Decimal("0"):
        raise ValueError("Material consumption totals exceed the issued quantity")
    return outstanding


async def list_work_order_materials(
    db: AsyncSession, wo_id: uuid.UUID,
) -> List[ExecOrderMaterial]:
    context_result = await db.execute(
        select(ProdExecOrder, ExecWorkOrder)
        .join(ExecWorkOrder, ExecWorkOrder.production_order_id == ProdExecOrder.id)
        .where(ExecWorkOrder.id == wo_id)
    )
    context = context_result.one_or_none()
    if context is None:
        raise ValueError(f"Work order {wo_id} not found")
    parent, work_order = context
    _require_parent_in_progress(parent)
    if work_order.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Materials are available only for an active work order")

    material_result = await db.execute(
        select(ExecOrderMaterial)
        .where(
            ExecOrderMaterial.production_order_id == parent.id,
            ExecOrderMaterial.work_order_id == work_order.id,
        )
        .order_by(ExecOrderMaterial.created_at, ExecOrderMaterial.id)
    )
    materials = list(material_result.scalars().all())
    for material in materials:
        _material_outstanding_qty(material)
    return materials


async def consume_work_order_material(
    db: AsyncSession,
    wo_id: uuid.UUID,
    material_id: uuid.UUID,
    qty: Decimal,
    *,
    session_id: uuid.UUID,
    lot_no: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecOrderMaterial:
    if not qty.is_finite() or qty <= Decimal("0"):
        raise ValueError("Material consumption quantity must be finite and greater than zero")

    parent, work_order = await _lock_wo_context(db, wo_id)
    replay = await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    )
    if replay is not None:
        material_id = (replay.extra_data or {}).get("material_id")
        if not material_id:
            raise RuntimeError("Idempotent material-consumption event has no material reference")
        replay_result = await db.execute(
            select(ExecOrderMaterial).where(
                ExecOrderMaterial.id == uuid.UUID(str(material_id)),
                ExecOrderMaterial.production_order_id == parent.id,
                ExecOrderMaterial.work_order_id == work_order.id,
            )
        )
        material = replay_result.scalar_one_or_none()
        if material is None:
            raise RuntimeError("Idempotent material-consumption target no longer exists")
        return material
    _require_parent_in_progress(parent)
    if work_order.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Material can be consumed only by an active work order")
    session = await _get_session_context(db, session_id)
    if session.current_work_order_id != work_order.id:
        raise ValueError("Operator session is not assigned to this active work order")

    material_result = await db.execute(
        select(ExecOrderMaterial)
        .where(
            ExecOrderMaterial.id == material_id,
            ExecOrderMaterial.production_order_id == parent.id,
            ExecOrderMaterial.work_order_id == work_order.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    material = material_result.scalar_one_or_none()
    if material is None:
        raise ValueError("Material is not assigned to this work order")
    outstanding = _material_outstanding_qty(material)
    if material.status != "ISSUED" or outstanding <= Decimal("0"):
        raise ValueError("Only outstanding issued material can be consumed")
    if qty > outstanding:
        raise ValueError("Material consumption cannot exceed the unconsumed, unreturned issued quantity")

    lots = list(dict.fromkeys(str(value) for value in (material.lot_numbers or []) if value))
    if lot_no is not None and lot_no not in lots:
        raise ValueError("Selected lot was not recorded on this material issue")
    if lot_no is None and len(lots) == 1:
        lot_no = lots[0]
    if lot_no is None and len(lots) > 1:
        raise ValueError("Select one of the recorded lots for this material consumption")

    material.consumed_qty = (material.consumed_qty or Decimal("0")) + qty
    remaining = outstanding - qty
    material.status = "CONSUMED" if remaining == Decimal("0") else "ISSUED"
    await _log_event(
        db,
        work_order.id,
        parent.id,
        "MATERIAL_CONSUMPTION",
        session_id=session_id,
        extra_data={
            "material_id": str(material.id),
            "item_id": str(material.item_id) if material.item_id else None,
            "item_code": material.item_code,
            "item_name": material.item_name,
            "qty": str(qty),
            "uom": material.uom,
            "lot_no": lot_no,
        },
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    await db.refresh(material)
    return material


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
            "qc_passed": wo.qc_passed,
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
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo

    session = await _get_session_context(db, session_id) if session_id is not None else None
    session_operator_id = session.operator_id if session is not None else None
    if (
        session_operator_id is not None
        and wo.assigned_operator_id is not None
        and session_operator_id != wo.assigned_operator_id
    ):
        raise ValueError("The active operator does not match the operator assigned to this work order")

    session_machine_id = session.machine_id if session is not None else None
    selected_machine_id = machine_id or session_machine_id or wo.machine_id
    if session_machine_id is not None and machine_id is not None and machine_id != session_machine_id:
        raise ValueError("The selected machine does not match the active operator session")
    if wo.machine_id is not None and selected_machine_id is not None and selected_machine_id != wo.machine_id:
        raise ValueError("The selected machine does not match the work-order assignment")

    session_work_center_id = session.work_center_id if session is not None else None
    selected_work_center_id = wo.work_center_id or session_work_center_id
    if (
        wo.work_center_id is not None
        and session_work_center_id is not None
        and wo.work_center_id != session_work_center_id
    ):
        raise ValueError("The work order is outside the active operator session work center")

    qualification_blocks, _ = await validate_operator_qualification(
        db,
        operator_id=session_operator_id or wo.assigned_operator_id,
        machine_id=selected_machine_id,
        work_center_id=selected_work_center_id,
    )
    if qualification_blocks:
        raise ValueError(f"Operator qualification failed: {'; '.join(qualification_blocks)}")

    _require_parent_in_progress(parent)
    if wo.status not in {"READY", "PENDING"}:
        raise ValueError(f"Work order cannot be started from status {wo.status}")
    if wo.dependency_work_order_id:
        predecessor_result = await db.execute(
            select(ExecWorkOrder)
            .where(ExecWorkOrder.id == wo.dependency_work_order_id)
            .execution_options(populate_existing=True)
        )
        predecessor = predecessor_result.scalar_one_or_none()
        if (
            predecessor is None
            or predecessor.production_order_id != wo.production_order_id
            or predecessor.status != "COMPLETED"
        ):
            raise ValueError("Preceding work order must be completed before this step can start")
    previous_status = wo.status
    wo.status = "IN_PROGRESS"
    if not wo.started_at:
        wo.started_at = _now()
    await record_shop_floor_transition(
        db, session_id=session_id, entity_id=wo.id,
        parent_entity_id=parent.id, action="SHOP_FLOOR_STARTED",
        from_status=previous_status, to_status=wo.status,
    )
    await _log_event(
        db, wo_id, wo.production_order_id, "START",
        session_id=session_id, operator_name=operator_name, line_id=line_id,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    if session is not None:
        session.current_work_order_id = wo_id
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
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo
    _require_parent_in_progress(parent)
    if wo.status != "IN_PROGRESS":
        raise ValueError("Work order must be IN_PROGRESS to pause")
    previous_status = wo.status
    wo.status = "PAUSED"
    await record_shop_floor_transition(
        db, session_id=session_id, entity_id=wo.id,
        parent_entity_id=parent.id, action="SHOP_FLOOR_PAUSED",
        from_status=previous_status, to_status=wo.status,
    )
    await _log_event(
        db, wo_id, wo.production_order_id, "PAUSE",
        session_id=session_id, operator_name=operator_name,
        reason_code=reason_code, remarks=remarks,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def resume_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo
    _require_parent_in_progress(parent)
    if wo.status not in {"PAUSED"}:
        raise ValueError("Work order must be PAUSED to resume")
    previous_status = wo.status
    wo.status = "IN_PROGRESS"
    await record_shop_floor_transition(
        db, session_id=session_id, entity_id=wo.id,
        parent_entity_id=parent.id, action="SHOP_FLOOR_RESUMED",
        from_status=previous_status, to_status=wo.status,
    )
    await _log_event(
        db, wo_id, wo.production_order_id, "RESUME",
        session_id=session_id, operator_name=operator_name,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
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
    scrap_category: Optional[str] = None,
    scrap_reason: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    quantity_values = (qty_good, qty_scrap, qty_rework)
    if any(not value.is_finite() or value < Decimal("0") for value in quantity_values):
        raise ValueError("Quantities must be finite and non-negative")
    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo
    _require_parent_in_progress(parent)
    if wo.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Work-order quantities can only be updated while the work order is active")
    wo.completed_qty = qty_good
    wo.scrap_qty = qty_scrap
    wo.rework_qty = qty_rework
    if qty_scrap > Decimal("0"):
        if scrap_category is not None:
            wo.scrap_category = scrap_category
        if scrap_reason is not None:
            wo.scrap_reason = scrap_reason
    else:
        wo.scrap_category = None
        wo.scrap_reason = None
    await _log_event(
        db, wo_id, wo.production_order_id, "QTY_UPDATE",
        session_id=session_id, operator_name=operator_name,
        qty_good=qty_good, qty_scrap=qty_scrap, qty_rework=qty_rework,
        reason_code=scrap_category if qty_scrap > Decimal("0") else None,
        remarks=(scrap_reason or remarks) if qty_scrap > Decimal("0") else remarks,
        extra_data={"scrap_category": scrap_category} if scrap_category is not None else None,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
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
    scrap_category: Optional[str] = None,
    scrap_reason: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    if not qty_scrap.is_finite() or qty_scrap <= Decimal("0"):
        raise ValueError("Scrap quantity must be finite and greater than zero")
    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo
    _require_parent_in_progress(parent)
    if wo.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Scrap can only be logged while the work order is active")
    wo.scrap_qty = (wo.scrap_qty or Decimal("0")) + qty_scrap
    if scrap_category is not None:
        wo.scrap_category = scrap_category
    if scrap_reason or reason_code or remarks:
        wo.scrap_reason = scrap_reason or reason_code or remarks
    await _log_event(
        db, wo_id, wo.production_order_id, "SCRAP",
        session_id=session_id, operator_name=operator_name,
        qty_scrap=qty_scrap, reason_code=scrap_category or reason_code,
        remarks=scrap_reason or remarks,
        extra_data={"scrap_category": scrap_category} if scrap_category is not None else None,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    await db.refresh(wo)
    return wo


async def get_qc_checkpoints(
    db: AsyncSession, wo_id: uuid.UUID,
) -> List[WOActivityLog]:
    result = await db.execute(
        select(WOActivityLog)
        .where(
            WOActivityLog.work_order_id == wo_id,
            WOActivityLog.event_type == "QC_CHECKPOINT",
        )
        .order_by(WOActivityLog.created_at, WOActivityLog.timestamp_start, WOActivityLog.id)
    )
    events = list(result.scalars().all())
    events.sort(key=lambda event: (
        0 if isinstance((event.extra_data or {}).get("checkpoint_sequence"), int) else 1,
        (event.extra_data or {}).get("checkpoint_sequence", 0)
        if isinstance((event.extra_data or {}).get("checkpoint_sequence"), int)
        else (event.created_at or event.timestamp_start or _now()),
        str(event.id),
    ))
    return events


async def record_qc_checkpoint(
    db: AsyncSession,
    wo_id: uuid.UUID,
    *,
    session_id: uuid.UUID,
    checkpoint_name: str,
    result: str,
    measured_value: Optional[str] = None,
    unit: Optional[str] = None,
    notes: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> WOActivityLog:
    checkpoint_name = checkpoint_name.strip()
    if not checkpoint_name or len(checkpoint_name) > 100:
        raise ValueError("QC checkpoint name must contain 1 to 100 characters")
    if result not in {"PASS", "FAIL"}:
        raise ValueError("QC checkpoint result must be PASS or FAIL")
    if measured_value is not None and len(measured_value) > 200:
        raise ValueError("QC measured value cannot exceed 200 characters")
    if unit is not None and len(unit) > 30:
        raise ValueError("QC measurement unit cannot exceed 30 characters")
    if notes is not None and len(notes) > 2000:
        raise ValueError("QC checkpoint notes cannot exceed 2000 characters")

    parent, work_order = await _lock_wo_context(db, wo_id)
    replay = await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    )
    if replay is not None:
        return replay
    _require_parent_in_progress(parent)
    if work_order.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("QC checkpoints can be recorded only while the work order is active")
    session = await _get_session_context(db, session_id)
    if session.current_work_order_id != work_order.id:
        raise ValueError("Operator session is not assigned to this active work order")

    previous = await get_qc_checkpoints(db, work_order.id)
    previous.sort(key=lambda event: (
        0 if isinstance((event.extra_data or {}).get("checkpoint_sequence"), int) else 1,
        (event.extra_data or {}).get("checkpoint_sequence", 0)
        if isinstance((event.extra_data or {}).get("checkpoint_sequence"), int)
        else (event.created_at or event.timestamp_start or _now()),
        str(event.id),
    ))
    latest_by_checkpoint: dict[str, str] = {}
    max_sequence = 0
    for event in previous:
        data = event.extra_data or {}
        name = data.get("checkpoint_name")
        outcome = data.get("result")
        sequence = data.get("checkpoint_sequence")
        if isinstance(sequence, int):
            max_sequence = max(max_sequence, sequence)
        if isinstance(name, str) and outcome in {"PASS", "FAIL"}:
            latest_by_checkpoint[" ".join(name.split()).casefold()] = outcome
    latest_by_checkpoint[" ".join(checkpoint_name.split()).casefold()] = result
    work_order.qc_passed = bool(latest_by_checkpoint) and all(
        outcome == "PASS" for outcome in latest_by_checkpoint.values()
    )

    entry = await _log_event(
        db,
        work_order.id,
        parent.id,
        "QC_CHECKPOINT",
        session_id=session_id,
        remarks=notes,
        extra_data={
            "checkpoint_name": checkpoint_name,
            "checkpoint_sequence": max_sequence + 1,
            "result": result,
            "measured_value": measured_value,
            "unit": unit,
        },
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    await db.refresh(entry)
    return entry


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
    scrap_category: Optional[str] = None,
    scrap_reason: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> ExecWorkOrder:
    finish_values = (qty_good, qty_scrap, qty_rework)
    if any(not value.is_finite() or value < Decimal("0") for value in finish_values):
        raise ValueError("Completion quantities must be finite and non-negative")
    if run_time_actual is not None and (
        not run_time_actual.is_finite() or run_time_actual < Decimal("0")
    ):
        raise ValueError("Actual runtime must be finite and non-negative")

    parent, wo = await _lock_wo_context(db, wo_id)
    if await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    ) is not None:
        return wo
    _require_parent_in_progress(parent)
    if wo.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Work order must be IN_PROGRESS or PAUSED to finish")
    if wo.qc_required_flag and wo.qc_passed is not True:
        raise ValueError("Required in-process QC checkpoints must all pass before work-order completion")
    previous_status = wo.status
    wo.status = "COMPLETED"
    wo.completed_qty = qty_good
    wo.scrap_qty = qty_scrap
    wo.rework_qty = qty_rework
    if qty_scrap > Decimal("0"):
        if scrap_category is not None:
            wo.scrap_category = scrap_category
        if scrap_reason is not None:
            wo.scrap_reason = scrap_reason
    else:
        wo.scrap_category = None
        wo.scrap_reason = None
    wo.completed_at = _now()
    if run_time_actual is not None:
        wo.run_time_actual = run_time_actual
    await record_shop_floor_transition(
        db, session_id=session_id, entity_id=wo.id,
        parent_entity_id=parent.id, action="SHOP_FLOOR_COMPLETED",
        from_status=previous_status, to_status=wo.status,
    )

    await _log_event(
        db, wo_id, wo.production_order_id, "FINISH",
        session_id=session_id, operator_name=operator_name,
        qty_good=qty_good, qty_scrap=qty_scrap, qty_rework=qty_rework,
        duration_minutes=run_time_actual,
        reason_code=scrap_category if qty_scrap > Decimal("0") else None,
        remarks=(scrap_reason or remarks) if qty_scrap > Decimal("0") else remarks,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )

    # Unblock next WO in chain
    next_result = await db.execute(
        select(ExecWorkOrder)
        .where(ExecWorkOrder.dependency_work_order_id == wo_id)
        .where(ExecWorkOrder.status == "PENDING")
    )
    for nwo in next_result.scalars().all():
        previous_status = nwo.status
        nwo.status = "READY"
        await record_shop_floor_transition(
            db, session_id=session_id, entity_id=nwo.id,
            parent_entity_id=parent.id, action="SHOP_FLOOR_READY",
            from_status=previous_status, to_status=nwo.status,
        )

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
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> WOActivityLog:
    parent, wo = await _lock_wo_context(db, wo_id)
    replay = await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    )
    if replay is not None:
        return replay
    entry = await _log_event(
        db, wo_id, parent.id, "HELP_REQUEST",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    return entry


async def trigger_qc(
    db: AsyncSession,
    wo_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    remarks: Optional[str],
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> WOActivityLog:
    parent, wo = await _lock_wo_context(db, wo_id)
    replay = await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    )
    if replay is not None:
        return replay
    entry = await _log_event(
        db, wo_id, parent.id, "QC_TRIGGER",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
    )
    await db.commit()
    return entry


async def add_note(
    db: AsyncSession,
    wo_id: uuid.UUID,
    remarks: str,
    session_id: Optional[uuid.UUID],
    operator_name: Optional[str],
    actor_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> WOActivityLog:
    parent, wo = await _lock_wo_context(db, wo_id)
    replay = await _find_idempotent_execution_event(
        db, wo_id, actor_user_id, idempotency_key, request_fingerprint,
    )
    if replay is not None:
        return replay
    entry = await _log_event(
        db, wo_id, parent.id, "NOTE",
        session_id=session_id, operator_name=operator_name, remarks=remarks,
        actor_user_id=actor_user_id, idempotency_key=idempotency_key,
        idempotency_fingerprint=request_fingerprint,
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
    payload = data.copy()
    idempotency_key = payload.get("start_idempotency_key")
    fingerprint = payload.get("start_idempotency_fingerprint")
    if idempotency_key:
        existing_result = await db.execute(
            select(SFDowntimeLog)
            .where(
                SFDowntimeLog.created_by_user_id == payload.get("created_by_user_id"),
                SFDowntimeLog.start_idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            if existing.start_idempotency_fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "This idempotency key was already used for a different downtime request."
                )
            return existing
    if payload.get("production_order_id") is not None and payload.get("work_order_id") is None:
        raise ValueError("Order-linked downtime must reference its execution work order")
    if payload.get("work_order_id") is not None:
        parent, work_order = await _lock_wo_context(db, payload["work_order_id"])
        _require_parent_in_progress(parent)
        if work_order.status not in {"IN_PROGRESS", "PAUSED"}:
            raise ValueError("Downtime linked to a work order requires an active operation")
        supplied_parent_id = payload.get("production_order_id")
        if supplied_parent_id is not None and supplied_parent_id != parent.id:
            raise ValueError("Downtime production order does not match the linked work order")
        payload["production_order_id"] = parent.id
        if payload.get("line_id") and work_order.line_id and payload["line_id"] != work_order.line_id:
            raise ValueError("Downtime line does not match the linked work order")
        if not payload.get("line_id"):
            payload["line_id"] = work_order.line_id
    if payload.get("session_id") is not None:
        session = await _get_session_context(db, payload["session_id"])
        payload.update({
            "operator_id": session.operator_id,
            "operator_name": session.operator_name,
            "team_id": session.team_id,
            "machine_id": session.machine_id,
            "line_id": session.line_id,
            "shift_id": session.shift_id,
            "created_by_user_id": session.authenticated_user_id,
        })

    if idempotency_key:
        inserted = await db.execute(
            postgresql_insert(SFDowntimeLog)
            .values(
                id=uuid.uuid4(),
                **payload,
                is_closed=False,
                start_time=_now(),
            )
            .on_conflict_do_nothing(
                index_elements=[SFDowntimeLog.created_by_user_id, SFDowntimeLog.start_idempotency_key],
            )
            .returning(SFDowntimeLog)
        )
        dt = inserted.scalar_one_or_none()
        if dt is None:
            existing_result = await db.execute(
                select(SFDowntimeLog).where(
                    SFDowntimeLog.created_by_user_id == payload.get("created_by_user_id"),
                    SFDowntimeLog.start_idempotency_key == idempotency_key,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is None:
                raise RuntimeError("The downtime idempotency conflict row was not visible after insert arbitration.")
            if existing.start_idempotency_fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "This idempotency key was already used for a different downtime request."
                )
            return existing
    else:
        dt = SFDowntimeLog(**payload, is_closed=False, start_time=_now())
        db.add(dt)
        await db.flush()
    if payload.get("work_order_id"):
        await _log_event(
            db,
            payload["work_order_id"],
            payload.get("production_order_id"),
            "DOWNTIME_START",
            session_id=payload.get("session_id"),
            operator_name=payload.get("operator_name"),
            line_id=payload.get("line_id"),
            reason_code=payload.get("downtime_category"),
            remarks=payload.get("root_reason"),
        )
    await db.commit()
    await db.refresh(dt)
    return dt


async def stop_downtime(
    db: AsyncSession,
    downtime_id: uuid.UUID,
    comments: Optional[str],
    *,
    closed_by_user_id: Optional[uuid.UUID] = None,
    idempotency_key: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
) -> SFDowntimeLog:
    result = await db.execute(
        select(SFDowntimeLog)
        .where(SFDowntimeLog.id == downtime_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    dt = result.scalar_one_or_none()
    if not dt:
        raise ValueError("Downtime record not found")
    if dt.stop_idempotency_key is not None:
        if dt.stop_idempotency_key != idempotency_key or dt.stop_idempotency_fingerprint != request_fingerprint:
            if dt.stop_idempotency_key == idempotency_key:
                raise IdempotencyConflictError(
                    "This idempotency key was already used for a different downtime stop request."
                )
            raise ValueError("Downtime record is already closed")
        return dt
    if dt.is_closed:
        raise ValueError("Downtime record is already closed")
    dt.stop_idempotency_key = idempotency_key
    dt.stop_idempotency_fingerprint = request_fingerprint
    dt.end_time = _now()
    dt.is_closed = True
    dt.closed_by_user_id = closed_by_user_id
    elapsed = (dt.end_time - dt.start_time).total_seconds() / 60
    dt.duration_minutes = Decimal(str(round(elapsed, 2)))
    if comments:
        dt.comments = comments
    if dt.work_order_id:
        await _log_event(
            db, dt.work_order_id, dt.production_order_id, "DOWNTIME_STOP",
            session_id=dt.session_id,
            operator_name=dt.operator_name, line_id=dt.line_id,
            duration_minutes=dt.duration_minutes,
            allow_inactive_session=True,
            actor_user_id=closed_by_user_id,
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


async def approve_handover(
    db: AsyncSession,
    handover_id: uuid.UUID,
    approved_by: str,
    *,
    approved_by_user_id: Optional[uuid.UUID] = None,
) -> ShiftHandover:
    result = await db.execute(select(ShiftHandover).where(ShiftHandover.id == handover_id))
    ho = result.scalar_one_or_none()
    if not ho:
        raise ValueError("Handover not found")
    ho.is_approved = True
    ho.approved_by = approved_by
    ho.approved_by_user_id = approved_by_user_id
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
    actor_user_id: Optional[uuid.UUID] = None,
) -> SupervisorOverride:
    ov = SupervisorOverride(
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        actor_user_id=actor_user_id,
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
            actor_user_id=actor_user_id,
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
