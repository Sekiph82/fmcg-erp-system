"""Brand Asset / Label Design Management endpoints.

Prefix: /api/v1/brand-assets
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.brand_assets import (
    BrandAsset, AssetApprovalStage,
    AssetType, AssetStatus, ApprovalStageStatus, APPROVAL_STAGES,
)

router = APIRouter()
_SEQ = 0

_DEFAULT_COMPLIANCE = {
    "allergen_declared": False,
    "nutrition_label": False,
    "ingredient_list": False,
    "net_weight": False,
    "manufacturer_details": False,
    "expiry_date_format": False,
    "barcode_present": False,
    "kebs_mark": False,
}


def _ref() -> str:
    global _SEQ
    _SEQ += 1
    return f"DA-{datetime.utcnow().strftime('%Y%m%d')}-{_SEQ:04d}"


def _asset_out(a: BrandAsset) -> dict:
    return {
        "id": str(a.id),
        "asset_ref": a.asset_ref,
        "name": a.name,
        "asset_type": a.asset_type,
        "brand": a.brand,
        "product_name": a.product_name,
        "product_sku": a.product_sku,
        "version": a.version,
        "is_latest": a.is_latest,
        "change_notes": a.change_notes,
        "bom_version": a.bom_version,
        "bom_id": a.bom_id,
        "bom_change_flag": a.bom_change_flag,
        "file_url": a.file_url,
        "thumbnail_url": a.thumbnail_url,
        "file_format": a.file_format,
        "status": a.status,
        "compliance_checklist": a.compliance_checklist,
        "notes": a.notes,
        "created_by": a.created_by,
        "created_at": a.created_at.isoformat() if a.created_at else "",
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class AssetIn(BaseModel):
    name: str
    asset_type: AssetType = AssetType.LABEL
    brand: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    bom_version: Optional[str] = None
    bom_id: Optional[str] = None
    file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    file_format: Optional[str] = None
    file_size_kb: Optional[int] = None
    change_notes: Optional[str] = None
    notes: Optional[str] = None


class StageApproveIn(BaseModel):
    approved_by: str
    notes: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_asset(payload: AssetIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    asset = BrandAsset(
        asset_ref=_ref(),
        name=payload.name,
        asset_type=payload.asset_type,
        brand=payload.brand,
        product_name=payload.product_name,
        product_sku=payload.product_sku,
        bom_version=payload.bom_version,
        bom_id=payload.bom_id,
        file_url=payload.file_url,
        thumbnail_url=payload.thumbnail_url,
        file_format=payload.file_format,
        file_size_kb=payload.file_size_kb,
        change_notes=payload.change_notes,
        notes=payload.notes,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
        compliance_checklist=_DEFAULT_COMPLIANCE.copy(),
    )
    db.add(asset)

    # Seed approval stages
    for order, stage in enumerate(APPROVAL_STAGES, 1):
        db.add(AssetApprovalStage(asset_id=asset.id, stage_name=stage, stage_order=order))

    await db.commit()
    await db.refresh(asset)
    return _asset_out(asset)


@router.get("/")
async def list_assets(
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    product_sku: Optional[str] = None,
    bom_change_flag: Optional[bool] = None,
    latest_only: bool = True,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(BrandAsset)
    if latest_only:
        q = q.where(BrandAsset.is_latest == True)
    if asset_type:
        q = q.where(BrandAsset.asset_type == asset_type)
    if status:
        q = q.where(BrandAsset.status == status)
    if product_sku:
        q = q.where(BrandAsset.product_sku == product_sku)
    if bom_change_flag is not None:
        q = q.where(BrandAsset.bom_change_flag == bom_change_flag)
    q = q.order_by(desc(BrandAsset.created_at)).limit(limit)
    result = await db.execute(q)
    return [_asset_out(a) for a in result.scalars().all()]


@router.get("/stats")
async def asset_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    by_status_r = await db.execute(
        select(BrandAsset.status, func.count().label("cnt"))
        .where(BrandAsset.is_latest == True)
        .group_by(BrandAsset.status)
    )
    by_type_r = await db.execute(
        select(BrandAsset.asset_type, func.count().label("cnt"))
        .where(BrandAsset.is_latest == True)
        .group_by(BrandAsset.asset_type)
    )
    bom_flag_r = await db.execute(
        select(func.count()).select_from(BrandAsset).where(
            BrandAsset.bom_change_flag == True, BrandAsset.is_latest == True
        )
    )
    return {
        "total_assets": sum(r.cnt for r in (await db.execute(select(func.count().label("cnt")).select_from(BrandAsset).where(BrandAsset.is_latest == True))).all()),
        "by_status": {r.status: r.cnt for r in by_status_r.all()},
        "by_type": {r.asset_type: r.cnt for r in by_type_r.all()},
        "bom_change_alerts": bom_flag_r.scalar() or 0,
    }


@router.get("/{asset_id}")
async def get_asset(asset_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(BrandAsset)
        .options(selectinload(BrandAsset.approval_stages))
        .where(BrandAsset.id == uuid.UUID(asset_id))
    )
    asset = r.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    out = _asset_out(asset)
    out["approval_stages"] = [
        {"id": str(s.id), "stage_name": s.stage_name, "stage_order": s.stage_order,
         "status": s.status, "approved_by": s.approved_by,
         "approved_at": s.approved_at.isoformat() if s.approved_at else None,
         "notes": s.notes}
        for s in asset.approval_stages
    ]
    return out


# ── Approval Stages ───────────────────────────────────────────────────────────

@router.post("/{asset_id}/stages/{stage_id}/approve")
async def approve_stage(
    asset_id: str,
    stage_id: str,
    payload: StageApproveIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(AssetApprovalStage).where(
            AssetApprovalStage.id == uuid.UUID(stage_id),
            AssetApprovalStage.asset_id == uuid.UUID(asset_id),
        )
    )
    stage = r.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "Stage not found")
    stage.status = ApprovalStageStatus.APPROVED
    stage.approved_by = payload.approved_by
    stage.approved_at = datetime.utcnow()
    stage.notes = payload.notes

    # If all stages approved → set asset status to PRINT_READY
    all_r = await db.execute(
        select(AssetApprovalStage).where(AssetApprovalStage.asset_id == uuid.UUID(asset_id))
    )
    all_stages = all_r.scalars().all()
    if all(s.status == ApprovalStageStatus.APPROVED for s in all_stages):
        asset_r = await db.execute(select(BrandAsset).where(BrandAsset.id == uuid.UUID(asset_id)))
        asset = asset_r.scalar_one_or_none()
        if asset:
            asset.status = AssetStatus.PRINT_READY

    await db.commit()
    return {"stage_id": stage_id, "approved": True, "approved_by": payload.approved_by}


@router.post("/{asset_id}/stages/{stage_id}/reject")
async def reject_stage(
    asset_id: str,
    stage_id: str,
    payload: StageApproveIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(AssetApprovalStage).where(
            AssetApprovalStage.id == uuid.UUID(stage_id),
            AssetApprovalStage.asset_id == uuid.UUID(asset_id),
        )
    )
    stage = r.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "Stage not found")
    stage.status = ApprovalStageStatus.REJECTED
    stage.approved_by = payload.approved_by
    stage.notes = payload.notes

    # Set asset status to IN_REVIEW
    asset_r = await db.execute(select(BrandAsset).where(BrandAsset.id == uuid.UUID(asset_id)))
    asset = asset_r.scalar_one_or_none()
    if asset:
        asset.status = AssetStatus.REJECTED

    await db.commit()
    return {"stage_id": stage_id, "rejected": True}


# ── Compliance Checklist ──────────────────────────────────────────────────────

class ChecklistToggle(BaseModel):
    key: str
    value: bool


@router.patch("/{asset_id}/compliance")
async def update_compliance(
    asset_id: str,
    payload: ChecklistToggle,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(BrandAsset).where(BrandAsset.id == uuid.UUID(asset_id)))
    asset = r.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    chk = dict(asset.compliance_checklist or {})
    chk[payload.key] = payload.value
    asset.compliance_checklist = chk
    await db.commit()
    return {"key": payload.key, "value": payload.value, "checklist": chk}


# ── New Version ───────────────────────────────────────────────────────────────

@router.post("/{asset_id}/new-version", status_code=201)
async def new_version(
    asset_id: str,
    payload: AssetIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    prev_r = await db.execute(select(BrandAsset).where(BrandAsset.id == uuid.UUID(asset_id)))
    prev = prev_r.scalar_one_or_none()
    if not prev:
        raise HTTPException(404, "Asset not found")

    prev.is_latest = False

    asset = BrandAsset(
        asset_ref=_ref(),
        name=payload.name or prev.name,
        asset_type=payload.asset_type or prev.asset_type,
        brand=payload.brand or prev.brand,
        product_name=payload.product_name or prev.product_name,
        product_sku=payload.product_sku or prev.product_sku,
        version=prev.version + 1,
        previous_version_id=prev.id,
        bom_version=payload.bom_version,
        bom_id=payload.bom_id,
        file_url=payload.file_url,
        thumbnail_url=payload.thumbnail_url,
        file_format=payload.file_format,
        change_notes=payload.change_notes,
        notes=payload.notes,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
        compliance_checklist=dict(prev.compliance_checklist or _DEFAULT_COMPLIANCE),
    )
    db.add(asset)
    for order, stage in enumerate(APPROVAL_STAGES, 1):
        db.add(AssetApprovalStage(asset_id=asset.id, stage_name=stage, stage_order=order))

    await db.commit()
    await db.refresh(asset)
    return _asset_out(asset)


# ── BOM Change Alert ──────────────────────────────────────────────────────────

@router.post("/{asset_id}/flag-bom-change")
async def flag_bom_change(asset_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Flag that the linked BOM has changed — label may need update."""
    r = await db.execute(select(BrandAsset).where(BrandAsset.id == uuid.UUID(asset_id)))
    asset = r.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    asset.bom_change_flag = True
    await db.commit()
    return {"asset_id": asset_id, "bom_change_flag": True, "message": "Asset flagged for label review due to BOM change."}
