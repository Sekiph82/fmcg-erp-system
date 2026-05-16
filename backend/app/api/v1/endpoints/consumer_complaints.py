"""Consumer Complaint Management endpoints.

Prefix: /api/v1/consumer-complaints
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import forbidden_detail, has_permission
from app.core.deps import get_db, require_permission
from app.models.consumer_complaints import (
    ConsumerComplaint, ComplaintSeverity, ComplaintChannel, ComplaintStatus,
)

router = APIRouter()
_SEQ = 0
MODULE_KEY = "consumer_complaints"


def _ref() -> str:
    global _SEQ
    _SEQ += 1
    return f"CC-{datetime.utcnow().strftime('%Y%m%d')}-{_SEQ:04d}"


def _out(c: ConsumerComplaint) -> dict:
    return {
        "id": str(c.id),
        "complaint_ref": c.complaint_ref,
        "consumer_name": c.consumer_name,
        "consumer_contact": c.consumer_contact,
        "consumer_location": c.consumer_location,
        "channel": c.channel,
        "product_name": c.product_name,
        "lot_number": c.lot_number,
        "batch_id": str(c.batch_id) if c.batch_id else None,
        "purchase_date": c.purchase_date,
        "purchase_location": c.purchase_location,
        "severity": c.severity,
        "description": c.description,
        "status": c.status,
        "assigned_to": c.assigned_to,
        "root_cause": c.root_cause,
        "corrective_action": c.corrective_action,
        "recall_triggered_flag": c.recall_triggered_flag,
        "recall_ref": c.recall_ref,
        "regulatory_report_required": c.regulatory_report_required,
        "acknowledged_at": c.acknowledged_at.isoformat() if c.acknowledged_at else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "compensation_notes": c.compensation_notes,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


def _require_user_permission(user, action: str) -> None:
    permission_code = f"{MODULE_KEY}.{action}"
    if not has_permission(user, permission_code):
        raise HTTPException(
            status_code=403,
            detail=forbidden_detail(f"Permission '{permission_code}' required"),
        )


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComplaintIn(BaseModel):
    consumer_name: Optional[str] = None
    consumer_contact: Optional[str] = None
    consumer_location: Optional[str] = None
    channel: ComplaintChannel = ComplaintChannel.PHONE
    product_name: str
    lot_number: Optional[str] = None
    batch_id: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_location: Optional[str] = None
    severity: ComplaintSeverity = ComplaintSeverity.QUALITY
    description: str


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    assigned_to: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    recall_triggered_flag: Optional[bool] = None
    recall_ref: Optional[str] = None
    regulatory_report_required: Optional[bool] = None
    compensation_notes: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_complaint(
    payload: ComplaintIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MODULE_KEY, "create")),
):
    auto_recall = payload.severity == ComplaintSeverity.SAFETY
    complaint = ConsumerComplaint(
        complaint_ref=_ref(),
        consumer_name=payload.consumer_name,
        consumer_contact=payload.consumer_contact,
        consumer_location=payload.consumer_location,
        channel=payload.channel,
        product_name=payload.product_name,
        lot_number=payload.lot_number,
        batch_id=uuid.UUID(payload.batch_id) if payload.batch_id else None,
        purchase_date=payload.purchase_date,
        purchase_location=payload.purchase_location,
        severity=payload.severity,
        description=payload.description,
        recall_triggered_flag=auto_recall,
        regulatory_report_required=payload.severity in (ComplaintSeverity.SAFETY, ComplaintSeverity.FOREIGN_OBJECT),
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    result = _out(complaint)
    if auto_recall:
        result["warning"] = "SAFETY severity — recall flag auto-triggered. Review traceability module."
    return result


@router.get("/")
async def list_complaints(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    lot_number: Optional[str] = None,
    product_name: Optional[str] = None,
    recall_only: bool = False,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MODULE_KEY, "view")),
):
    q = select(ConsumerComplaint)
    if severity:
        q = q.where(ConsumerComplaint.severity == severity)
    if status:
        q = q.where(ConsumerComplaint.status == status)
    if lot_number:
        q = q.where(ConsumerComplaint.lot_number == lot_number)
    if product_name:
        q = q.where(ConsumerComplaint.product_name.ilike(f"%{product_name}%"))
    if recall_only:
        q = q.where(ConsumerComplaint.recall_triggered_flag == True)
    q = q.order_by(desc(ConsumerComplaint.created_at)).limit(limit)
    result = await db.execute(q)
    return [_out(c) for c in result.scalars().all()]


@router.get("/stats")
async def complaint_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MODULE_KEY, "view")),
):
    by_sev_r = await db.execute(
        select(ConsumerComplaint.severity, func.count().label("cnt"))
        .group_by(ConsumerComplaint.severity)
    )
    by_sev = {r.severity: r.cnt for r in by_sev_r.all()}

    by_status_r = await db.execute(
        select(ConsumerComplaint.status, func.count().label("cnt"))
        .group_by(ConsumerComplaint.status)
    )
    by_status = {r.status: r.cnt for r in by_status_r.all()}

    recall_r = await db.execute(
        select(func.count()).select_from(ConsumerComplaint).where(ConsumerComplaint.recall_triggered_flag == True)
    )
    open_r = await db.execute(
        select(func.count()).select_from(ConsumerComplaint).where(
            ConsumerComplaint.status.in_([ComplaintStatus.NEW, ComplaintStatus.ACKNOWLEDGED, ComplaintStatus.INVESTIGATING])
        )
    )

    return {
        "total": sum(by_sev.values()),
        "open": open_r.scalar() or 0,
        "recall_triggered": recall_r.scalar() or 0,
        "by_severity": by_sev,
        "by_status": by_status,
    }


@router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MODULE_KEY, "view")),
):
    r = await db.execute(select(ConsumerComplaint).where(ConsumerComplaint.id == uuid.UUID(complaint_id)))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Complaint not found")
    return _out(c)


@router.patch("/{complaint_id}")
async def update_complaint(
    complaint_id: str,
    payload: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(MODULE_KEY, "edit")),
):
    r = await db.execute(select(ConsumerComplaint).where(ConsumerComplaint.id == uuid.UUID(complaint_id)))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Complaint not found")

    if payload.status in (ComplaintStatus.RESOLVED, ComplaintStatus.COMPENSATED, ComplaintStatus.CLOSED):
        _require_user_permission(current_user, "close")
    if payload.status == ComplaintStatus.ESCALATED or payload.recall_triggered_flag is True or payload.recall_ref:
        _require_user_permission(current_user, "link_recall")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(c, field, val)

    now = datetime.utcnow()
    if payload.status == ComplaintStatus.ACKNOWLEDGED and not c.acknowledged_at:
        c.acknowledged_at = now
    if payload.status in (ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED) and not c.resolved_at:
        c.resolved_at = now

    await db.commit()
    return _out(c)


@router.get("/by-lot/{lot_number}")
async def complaints_by_lot(
    lot_number: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MODULE_KEY, "view")),
):
    """All complaints linked to a specific lot/batch number."""
    r = await db.execute(
        select(ConsumerComplaint)
        .where(ConsumerComplaint.lot_number == lot_number)
        .order_by(desc(ConsumerComplaint.created_at))
    )
    complaints = r.scalars().all()
    return {
        "lot_number": lot_number,
        "total": len(complaints),
        "safety_count": sum(1 for c in complaints if c.severity == ComplaintSeverity.SAFETY),
        "recall_triggered": any(c.recall_triggered_flag for c in complaints),
        "complaints": [_out(c) for c in complaints],
    }
