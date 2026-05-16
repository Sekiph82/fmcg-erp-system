"""Advanced BOM / Formula / Packaging BOM — REST endpoints."""
from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.access_control import forbidden_detail, has_permission
from app.core.deps import require_permission
from app.db.session import get_db
from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMSubstituteGroup, BOMSubstitute,
    BOMConversionProfile, BOMYieldConfig,
    BOMType, BOMLifecycle, BOMRecStatus,
)
from app.schemas.bom import (
    BOMCreate, BOMUpdate, BOMOut, BOMSummary,
    BOMLineCreate, BOMLineUpdate, BOMLineOut,
    SubstGroupCreate, SubstGroupOut,
    SubstituteCreate, SubstituteOut,
    ConversionProfileCreate, ConversionProfileOut, ConversionCalcResult,
    YieldConfigCreate, YieldConfigOut,
    ExplosionResult, ScalingRequest, ScalingResult,
    CostingResult, ComplianceSummary, VersionDiff,
    BOMAIRecOut, BOMAIRecAction,
    BOMDashboard,
)
from app.services import (
    bom_service as svc,
    bom_explosion_service as explode_svc,
    bom_scaling_service as scale_svc,
    bom_costing_service as cost_svc,
    bom_compliance_service as comp_svc,
    bom_ai_service as ai_svc,
)

router = APIRouter()


def _require_user_permission(user, action: str) -> None:
    if not has_permission(user, f"bom.{action}"):
        permission_code = f"bom.{action}"
        raise HTTPException(status_code=403, detail=forbidden_detail(f"Permission '{permission_code}' required"))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=BOMDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    data = await svc.get_dashboard(db)
    return BOMDashboard(**data)


# ── BOM CRUD ───────────────────────────────────────────────────────────────────

@router.post("", response_model=BOMSummary, status_code=201)
async def create_bom(
    body: BOMCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("bom", "create")),
):
    bom = await svc.create_bom(db, body, current_user.id)
    await db.commit()
    await db.refresh(bom)
    return bom


@router.get("", response_model=List[BOMSummary])
async def list_boms(
    bom_type: Optional[BOMType] = None,
    lifecycle: Optional[BOMLifecycle] = None,
    product_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    return await svc.list_boms(db, bom_type, lifecycle, product_id)


@router.get("/{bom_id}", response_model=BOMOut)
async def get_bom(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    bom = await svc.get_bom(db, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    return bom


@router.patch("/{bom_id}", response_model=BOMSummary)
async def update_bom(
    bom_id: UUID,
    body: BOMUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "edit")),
):
    bom = await svc.get_bom(db, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    updated = await svc.update_bom(db, bom, body)
    await db.commit()
    await db.refresh(updated)
    return updated


@router.post("/{bom_id}/clone", response_model=BOMSummary)
async def clone_bom(
    bom_id: UUID,
    new_version: str = Query(..., description="New version number, e.g. 2.0"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("bom", "create")),
):
    bom = await svc.get_bom(db, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    cloned = await svc.clone_bom(db, bom, new_version, current_user.id)
    await db.commit()
    await db.refresh(cloned)
    return cloned


@router.post("/{bom_id}/advance", response_model=BOMSummary)
async def advance_lifecycle(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("bom", "view")),
):
    bom = await svc.get_bom(db, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    if bom.lifecycle == BOMLifecycle.DRAFT:
        _require_user_permission(current_user, "edit")
    elif bom.lifecycle == BOMLifecycle.UNDER_REVIEW:
        _require_user_permission(current_user, "approve")
    elif bom.lifecycle == BOMLifecycle.APPROVED:
        _require_user_permission(current_user, "release")
    try:
        updated = await svc.advance_lifecycle(db, bom, current_user.id)
        await db.commit()
        await db.refresh(updated)
        return updated
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{bom_id}/archive", response_model=BOMSummary)
async def archive_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "archive")),
):
    bom = await svc.get_bom(db, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    updated = await svc.archive_bom(db, bom)
    await db.commit()
    await db.refresh(updated)
    return updated


# ── BOM Lines ─────────────────────────────────────────────────────────────────

@router.post("/{bom_id}/lines", response_model=BOMLineOut, status_code=201)
async def add_line(
    bom_id: UUID,
    body: BOMLineCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "edit")),
):
    line = await svc.add_line(db, bom_id, body)
    await db.commit()
    await db.refresh(line)
    return line


@router.get("/{bom_id}/lines", response_model=List[BOMLineOut])
async def list_lines(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    r = await db.execute(
        select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id).order_by(AdvancedBOMLine.line_no)
    )
    return r.scalars().all()


@router.patch("/lines/{line_id}", response_model=BOMLineOut)
async def update_line(
    line_id: UUID,
    body: BOMLineUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "edit")),
):
    line = await svc.get_line(db, line_id)
    if not line:
        raise HTTPException(404, "BOM line not found")
    updated = await svc.update_line(db, line, body)
    await db.commit()
    await db.refresh(updated)
    return updated


@router.delete("/lines/{line_id}", status_code=204)
async def delete_line(line_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "delete"))):
    line = await svc.get_line(db, line_id)
    if not line:
        raise HTTPException(404, "BOM line not found")
    await svc.delete_line(db, line)
    await db.commit()


# ── Explosion ─────────────────────────────────────────────────────────────────

@router.get("/{bom_id}/explode", response_model=ExplosionResult)
async def explode_bom(
    bom_id: UUID,
    target_qty: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    try:
        return await explode_svc.explode_bom(db, bom_id, target_qty)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Batch Scaling ─────────────────────────────────────────────────────────────

@router.post("/{bom_id}/scale", response_model=ScalingResult)
async def scale_bom(
    bom_id: UUID,
    body: ScalingRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    try:
        return await scale_svc.scale_bom(db, bom_id, body.target_qty, body.target_uom)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Costing ───────────────────────────────────────────────────────────────────

@router.get("/{bom_id}/costing", response_model=CostingResult)
async def get_costing(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "cost"))):
    try:
        result = await cost_svc.compute_bom_cost(db, bom_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Version Comparison ────────────────────────────────────────────────────────

@router.get("/{bom_id}/compare/{other_id}")
async def compare_versions(
    bom_id: UUID,
    other_id: UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    return await cost_svc.compare_bom_versions(db, bom_id, other_id)


# ── Compliance Summary ────────────────────────────────────────────────────────

@router.get("/{bom_id}/compliance-summary", response_model=ComplianceSummary)
async def get_compliance_summary(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    try:
        result = await comp_svc.compute_compliance_summary(db, bom_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/{bom_id}/run-ai")
async def run_ai(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "ai"))):
    result = await ai_svc.run_all_bom_ai(db, bom_id)
    await db.commit()
    return result


@router.get("/{bom_id}/ai-recommendations", response_model=List[BOMAIRecOut])
async def list_ai_recs(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    return await svc.list_ai_recs(db, bom_id)


@router.post("/ai-recommendations/{rec_id}/action", response_model=BOMAIRecOut)
async def action_ai_rec(
    rec_id: UUID,
    body: BOMAIRecAction,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("bom", "ai")),
):
    try:
        rec = await svc.action_ai_rec(db, rec_id, body.status, current_user.id)
        await db.commit()
        await db.refresh(rec)
        return rec
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Yield Configs ─────────────────────────────────────────────────────────────

@router.post("/{bom_id}/yield-configs", response_model=YieldConfigOut, status_code=201)
async def add_yield_config(
    bom_id: UUID,
    body: YieldConfigCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "edit")),
):
    yc = await svc.add_yield_config(db, bom_id, body)
    await db.commit()
    await db.refresh(yc)
    return yc


@router.get("/{bom_id}/yield-configs", response_model=List[YieldConfigOut])
async def list_yield_configs(bom_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    return await svc.list_yield_configs(db, bom_id)


# ── Substitute Groups ─────────────────────────────────────────────────────────

@router.post("/substitute-groups", response_model=SubstGroupOut, status_code=201)
async def create_substitute_group(
    body: SubstGroupCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "create")),
):
    from app.models.bom import SubstitutionPolicy
    sg = await svc.create_substitute_group(db, body.group_name, body.policy, body.notes)
    await db.commit()
    await db.refresh(sg)
    return sg


@router.get("/substitute-groups", response_model=List[SubstGroupOut])
async def list_substitute_groups(db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    return await svc.list_substitute_groups(db)


@router.post("/substitutes", response_model=SubstituteOut, status_code=201)
async def add_substitute(
    body: SubstituteCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "create")),
):
    sub = await svc.add_substitute(db, body)
    await db.commit()
    await db.refresh(sub)
    return sub


# ── Conversion Profiles ───────────────────────────────────────────────────────

@router.post("/conversion-profiles", response_model=ConversionProfileOut, status_code=201)
async def create_conversion_profile(
    body: ConversionProfileCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "create")),
):
    profile = await svc.create_conversion_profile(db, body)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/conversion-profiles", response_model=List[ConversionProfileOut])
async def list_conversion_profiles(db: AsyncSession = Depends(get_db), _=Depends(require_permission("bom", "view"))):
    return await svc.list_conversion_profiles(db)


@router.post("/conversion-profiles/{profile_id}/calculate", response_model=ConversionCalcResult)
async def calculate_conversion(
    profile_id: UUID,
    source_qty: Decimal = Query(...),
    source_uom: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("bom", "view")),
):
    try:
        return await scale_svc.calculate_conversion(db, profile_id, source_qty, source_uom)
    except ValueError as e:
        raise HTTPException(404, str(e))
