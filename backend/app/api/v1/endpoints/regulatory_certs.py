"""Regulatory Certificate Tracking endpoints.

Prefix: /api/v1/regulatory-certs
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.regulatory_certs import (
    RegulatoryCertificate, CertAuditEntry,
    CertAuthority, CertEntityType, CertStatus,
)

router = APIRouter()
_SEQ = 0


def _ref() -> str:
    global _SEQ
    _SEQ += 1
    return f"CERT-{datetime.utcnow().strftime('%Y%m')}-{_SEQ:04d}"


def _out(c: RegulatoryCertificate) -> dict:
    today = date.today()
    days_to_expiry = None
    if c.expiry_date:
        days_to_expiry = (c.expiry_date - today).days
    return {
        "id": str(c.id),
        "cert_ref": c.cert_ref,
        "certificate_number": c.certificate_number,
        "authority": c.authority,
        "entity_type": c.entity_type,
        "entity_id": c.entity_id,
        "entity_name": c.entity_name,
        "country": c.country,
        "issuing_body": c.issuing_body,
        "scope": c.scope,
        "issued_date": str(c.issued_date) if c.issued_date else None,
        "expiry_date": str(c.expiry_date) if c.expiry_date else None,
        "days_to_expiry": days_to_expiry,
        "status": c.status,
        "document_url": c.document_url,
        "renewal_notes": c.renewal_notes,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class CertIn(BaseModel):
    entity_name: str
    authority: CertAuthority = CertAuthority.KEBS
    entity_type: CertEntityType = CertEntityType.PRODUCT
    entity_id: Optional[str] = None
    certificate_number: Optional[str] = None
    country: str = "Kenya"
    issuing_body: Optional[str] = None
    scope: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: CertStatus = CertStatus.ACTIVE
    document_url: Optional[str] = None
    renewal_notes: Optional[str] = None


class CertUpdate(BaseModel):
    status: Optional[CertStatus] = None
    expiry_date: Optional[date] = None
    issued_date: Optional[date] = None
    certificate_number: Optional[str] = None
    document_url: Optional[str] = None
    renewal_notes: Optional[str] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_cert(payload: CertIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    cert = RegulatoryCertificate(
        cert_ref=_ref(),
        certificate_number=payload.certificate_number,
        authority=payload.authority,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        entity_name=payload.entity_name,
        country=payload.country,
        issuing_body=payload.issuing_body,
        scope=payload.scope,
        issued_date=payload.issued_date,
        expiry_date=payload.expiry_date,
        status=payload.status,
        document_url=payload.document_url,
        renewal_notes=payload.renewal_notes,
    )
    db.add(cert)
    # Audit entry
    entry = CertAuditEntry(
        cert_id=cert.id,
        action="ISSUED",
        performed_by=getattr(current_user, "username", None) or str(current_user.id),
        notes="Certificate registered",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(cert)
    return _out(cert)


@router.get("/")
async def list_certs(
    authority: Optional[str] = None,
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    entity_id: Optional[str] = None,
    active_only: bool = True,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(RegulatoryCertificate)
    if active_only:
        q = q.where(RegulatoryCertificate.is_active == True)
    if authority:
        q = q.where(RegulatoryCertificate.authority == authority)
    if entity_type:
        q = q.where(RegulatoryCertificate.entity_type == entity_type)
    if status:
        q = q.where(RegulatoryCertificate.status == status)
    if entity_id:
        q = q.where(RegulatoryCertificate.entity_id == entity_id)
    q = q.order_by(RegulatoryCertificate.expiry_date.asc().nullslast()).limit(limit)
    result = await db.execute(q)
    return [_out(c) for c in result.scalars().all()]


@router.get("/expiring")
async def expiring_certs(
    days: int = Query(90, ge=1, le=365),
    include_expired: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Certificates expiring within N days (+ already expired if include_expired=true)."""
    today = date.today()
    cutoff = today + timedelta(days=days)
    conditions = [
        RegulatoryCertificate.is_active == True,
        RegulatoryCertificate.expiry_date.isnot(None),
        RegulatoryCertificate.status.in_([CertStatus.ACTIVE, CertStatus.PENDING_RENEWAL]),
    ]
    if include_expired:
        conditions.append(RegulatoryCertificate.expiry_date <= cutoff)
    else:
        conditions.append(RegulatoryCertificate.expiry_date >= today)
        conditions.append(RegulatoryCertificate.expiry_date <= cutoff)

    result = await db.execute(
        select(RegulatoryCertificate)
        .where(*conditions)
        .order_by(RegulatoryCertificate.expiry_date.asc())
    )
    certs = result.scalars().all()
    return [
        {**_out(c), "expired": c.expiry_date < today if c.expiry_date else False}
        for c in certs
    ]


@router.get("/stats")
async def cert_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    today = date.today()
    total_r = await db.execute(select(func.count()).select_from(RegulatoryCertificate).where(RegulatoryCertificate.is_active == True))
    expired_r = await db.execute(
        select(func.count()).select_from(RegulatoryCertificate).where(
            RegulatoryCertificate.is_active == True,
            RegulatoryCertificate.expiry_date < today,
            RegulatoryCertificate.status.in_([CertStatus.ACTIVE, CertStatus.PENDING_RENEWAL]),
        )
    )
    expiring_r = await db.execute(
        select(func.count()).select_from(RegulatoryCertificate).where(
            RegulatoryCertificate.is_active == True,
            RegulatoryCertificate.expiry_date.between(today, today + timedelta(days=90)),
            RegulatoryCertificate.status == CertStatus.ACTIVE,
        )
    )
    by_auth_r = await db.execute(
        select(RegulatoryCertificate.authority, func.count().label("cnt"))
        .where(RegulatoryCertificate.is_active == True)
        .group_by(RegulatoryCertificate.authority)
    )
    return {
        "total_active": total_r.scalar() or 0,
        "expired": expired_r.scalar() or 0,
        "expiring_90d": expiring_r.scalar() or 0,
        "by_authority": {r.authority: r.cnt for r in by_auth_r.all()},
    }


@router.get("/{cert_id}")
async def get_cert(cert_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(RegulatoryCertificate)
        .options(selectinload(RegulatoryCertificate.audit_entries))
        .where(RegulatoryCertificate.id == uuid.UUID(cert_id))
    )
    cert = r.scalar_one_or_none()
    if not cert:
        raise HTTPException(404, "Certificate not found")
    out = _out(cert)
    out["audit_history"] = [
        {"action": e.action, "performed_by": e.performed_by, "notes": e.notes,
         "created_at": e.created_at.isoformat() if e.created_at else ""}
        for e in sorted(cert.audit_entries, key=lambda e: e.created_at or datetime.min, reverse=True)
    ]
    return out


@router.patch("/{cert_id}")
async def update_cert(cert_id: str, payload: CertUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(select(RegulatoryCertificate).where(RegulatoryCertificate.id == uuid.UUID(cert_id)))
    cert = r.scalar_one_or_none()
    if not cert:
        raise HTTPException(404, "Certificate not found")

    action = "UPDATED"
    if payload.status and payload.status != cert.status:
        action = payload.status.value

    for field, val in payload.model_dump(exclude_none=True, exclude={"performed_by", "notes"}).items():
        setattr(cert, field, val)

    entry = CertAuditEntry(
        cert_id=cert.id,
        action=action,
        performed_by=payload.performed_by or "system",
        notes=payload.notes,
    )
    db.add(entry)
    await db.commit()
    return _out(cert)
