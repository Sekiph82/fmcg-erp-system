"""Returnable Packaging / Container Management endpoints.

Prefix: /api/v1/containers
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.containers import (
    ContainerType, ContainerIssuance, ContainerReturn,
    ContainerCondition, IssuanceStatus,
)

router = APIRouter()

_SEQ_COUNTER: int = 0


def _gen_ref(prefix: str) -> str:
    global _SEQ_COUNTER
    _SEQ_COUNTER += 1
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d')}-{_SEQ_COUNTER:04d}"


# ── Container Types ───────────────────────────────────────────────────────────

class ContainerTypeIn(BaseModel):
    code: str
    name: str
    deposit_amount: float = 0.0
    currency: str = "KES"
    description: Optional[str] = None
    material: Optional[str] = None
    capacity_liters: Optional[float] = None
    weight_kg: Optional[float] = None


@router.post("/types", status_code=201)
async def create_type(payload: ContainerTypeIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    ct = ContainerType(**payload.model_dump())
    db.add(ct)
    await db.commit()
    await db.refresh(ct)
    return {"id": str(ct.id), "code": ct.code, "name": ct.name, "deposit_amount": float(ct.deposit_amount)}


@router.get("/types")
async def list_types(active_only: bool = True, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    q = select(ContainerType)
    if active_only:
        q = q.where(ContainerType.active_flag == True)
    q = q.order_by(ContainerType.name)
    result = await db.execute(q)
    types = result.scalars().all()
    return [
        {"id": str(t.id), "code": t.code, "name": t.name,
         "deposit_amount": float(t.deposit_amount), "currency": t.currency,
         "material": t.material, "capacity_liters": float(t.capacity_liters) if t.capacity_liters else None,
         "active_flag": t.active_flag}
        for t in types
    ]


# ── Container Issuance ────────────────────────────────────────────────────────

class IssuanceIn(BaseModel):
    customer_id: str
    customer_name: Optional[str] = None
    container_type_id: str
    qty_issued: int
    delivery_ref: Optional[str] = None
    return_due_days: int = 14
    notes: Optional[str] = None


@router.post("/issue", status_code=201)
async def issue_containers(payload: IssuanceIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    ct_r = await db.execute(select(ContainerType).where(ContainerType.id == uuid.UUID(payload.container_type_id)))
    ct = ct_r.scalar_one_or_none()
    if not ct:
        raise HTTPException(404, "Container type not found")

    due = date.today() + timedelta(days=payload.return_due_days)
    deposit = float(ct.deposit_amount) * payload.qty_issued

    issuance = ContainerIssuance(
        issuance_ref=_gen_ref("CONT"),
        customer_id=uuid.UUID(payload.customer_id),
        customer_name=payload.customer_name,
        container_type_id=ct.id,
        delivery_ref=payload.delivery_ref,
        qty_issued=payload.qty_issued,
        qty_returned=0,
        qty_outstanding=payload.qty_issued,
        deposit_charged=deposit,
        return_due_date=due,
        notes=payload.notes,
    )
    db.add(issuance)
    await db.commit()
    await db.refresh(issuance)
    return {
        "id": str(issuance.id),
        "issuance_ref": issuance.issuance_ref,
        "customer_id": str(issuance.customer_id),
        "container_type": ct.name,
        "qty_issued": issuance.qty_issued,
        "deposit_charged": float(deposit),
        "return_due_date": str(due),
        "status": issuance.status,
    }


@router.get("/issuances")
async def list_issuances(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(ContainerIssuance).options(selectinload(ContainerIssuance.container_type))
    if customer_id:
        q = q.where(ContainerIssuance.customer_id == uuid.UUID(customer_id))
    if status:
        q = q.where(ContainerIssuance.status == status)
    if overdue_only:
        q = q.where(
            ContainerIssuance.return_due_date < date.today(),
            ContainerIssuance.status.in_([IssuanceStatus.OUTSTANDING, IssuanceStatus.PARTIALLY_RETURNED]),
        )
    q = q.order_by(ContainerIssuance.issued_at.desc()).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()
    today = date.today()
    return [
        {
            "id": str(i.id),
            "issuance_ref": i.issuance_ref,
            "customer_id": str(i.customer_id),
            "customer_name": i.customer_name,
            "container_type": i.container_type.name if i.container_type else "",
            "container_type_id": str(i.container_type_id),
            "qty_issued": i.qty_issued,
            "qty_returned": i.qty_returned,
            "qty_outstanding": i.qty_outstanding,
            "deposit_charged": float(i.deposit_charged) if i.deposit_charged else 0,
            "deposit_refunded": float(i.deposit_refunded) if i.deposit_refunded else 0,
            "status": i.status,
            "return_due_date": str(i.return_due_date) if i.return_due_date else None,
            "is_overdue": i.return_due_date < today if i.return_due_date else False,
            "days_overdue": (today - i.return_due_date).days if i.return_due_date and i.return_due_date < today else 0,
            "issued_at": i.issued_at.isoformat() if i.issued_at else "",
            "notes": i.notes,
        }
        for i in items
    ]


# ── Record Return ─────────────────────────────────────────────────────────────

class ReturnIn(BaseModel):
    issuance_id: str
    qty_returned: int
    condition: ContainerCondition = ContainerCondition.GOOD
    notes: Optional[str] = None
    recorded_by: Optional[str] = None


@router.post("/return", status_code=201)
async def record_return(payload: ReturnIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(ContainerIssuance).options(selectinload(ContainerIssuance.container_type))
        .where(ContainerIssuance.id == uuid.UUID(payload.issuance_id))
    )
    issuance = r.scalar_one_or_none()
    if not issuance:
        raise HTTPException(404, "Issuance not found")
    if issuance.status in (IssuanceStatus.CLOSED, IssuanceStatus.WRITTEN_OFF):
        raise HTTPException(400, f"Issuance already {issuance.status}")

    if payload.qty_returned > issuance.qty_outstanding:
        raise HTTPException(400, f"Cannot return {payload.qty_returned} — only {issuance.qty_outstanding} outstanding")

    # Compute refund (only GOOD condition gets refund)
    deposit_per_unit = float(issuance.deposit_charged or 0) / issuance.qty_issued if issuance.qty_issued else 0
    refund = deposit_per_unit * payload.qty_returned if payload.condition == ContainerCondition.GOOD else 0

    ret = ContainerReturn(
        issuance_id=issuance.id,
        qty_returned=payload.qty_returned,
        condition=payload.condition,
        refund_amount=refund,
        notes=payload.notes,
        recorded_by=payload.recorded_by,
    )
    db.add(ret)

    # Update issuance
    issuance.qty_returned += payload.qty_returned
    issuance.qty_outstanding -= payload.qty_returned
    issuance.deposit_refunded = (float(issuance.deposit_refunded or 0)) + refund
    if issuance.qty_outstanding == 0:
        issuance.status = IssuanceStatus.CLOSED
    elif issuance.qty_returned > 0:
        issuance.status = IssuanceStatus.PARTIALLY_RETURNED

    await db.commit()
    return {"issuance_ref": issuance.issuance_ref, "qty_outstanding": issuance.qty_outstanding,
            "refund_amount": refund, "status": issuance.status}


# ── Write-off ─────────────────────────────────────────────────────────────────

class WriteOffIn(BaseModel):
    issuance_id: str
    notes: Optional[str] = None


@router.post("/write-off")
async def write_off(payload: WriteOffIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(select(ContainerIssuance).where(ContainerIssuance.id == uuid.UUID(payload.issuance_id)))
    issuance = r.scalar_one_or_none()
    if not issuance:
        raise HTTPException(404, "Issuance not found")
    if issuance.status == IssuanceStatus.CLOSED:
        raise HTTPException(400, "Already closed")
    issuance.status = IssuanceStatus.WRITTEN_OFF
    if payload.notes:
        issuance.notes = (issuance.notes or "") + f" [WRITE-OFF] {payload.notes}"
    await db.commit()
    return {"issuance_ref": issuance.issuance_ref, "status": issuance.status, "qty_written_off": issuance.qty_outstanding}


# ── Dashboard / Stats ────────────────────────────────────────────────────────

@router.get("/stats")
async def container_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    today = date.today()

    total_r = await db.execute(select(func.count()).select_from(ContainerIssuance))
    outstanding_r = await db.execute(
        select(func.sum(ContainerIssuance.qty_outstanding)).select_from(ContainerIssuance)
        .where(ContainerIssuance.status.in_([IssuanceStatus.OUTSTANDING, IssuanceStatus.PARTIALLY_RETURNED]))
    )
    overdue_r = await db.execute(
        select(func.count()).select_from(ContainerIssuance).where(
            ContainerIssuance.return_due_date < today,
            ContainerIssuance.status.in_([IssuanceStatus.OUTSTANDING, IssuanceStatus.PARTIALLY_RETURNED]),
        )
    )
    written_off_r = await db.execute(
        select(func.count()).select_from(ContainerIssuance).where(ContainerIssuance.status == IssuanceStatus.WRITTEN_OFF)
    )
    deposit_outstanding_r = await db.execute(
        select(func.sum(ContainerIssuance.deposit_charged - ContainerIssuance.deposit_refunded))
        .select_from(ContainerIssuance)
        .where(ContainerIssuance.status.in_([IssuanceStatus.OUTSTANDING, IssuanceStatus.PARTIALLY_RETURNED]))
    )

    return {
        "total_issuances": total_r.scalar() or 0,
        "containers_outstanding": int(outstanding_r.scalar() or 0),
        "overdue_issuances": overdue_r.scalar() or 0,
        "written_off_issuances": written_off_r.scalar() or 0,
        "deposit_at_risk_kes": float(deposit_outstanding_r.scalar() or 0),
    }
