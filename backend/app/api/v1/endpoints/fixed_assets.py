"""Fixed Asset Accounting + Depreciation API endpoints."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.fixed_assets import (
    FAAssetCategory, FAFixedAsset, FADepreciationSchedule,
    FAAssetEvent, FAAssetDisposal, FAAssetComponent, FAAIRecommendation,
    FAAssetStatus, ScheduleStatus, AssetEventType, FAIRecStatus,
    DepreciationStartRule,
)
from app.models.user import User
from app.schemas.fixed_assets import (
    FAAssetCategoryCreate, FAAssetCategoryUpdate, FAAssetCategoryRead,
    FAFixedAssetCreate, FAFixedAssetUpdate, FAFixedAssetRead,
    FACapitalizeRequest, FATransferRequest, FARevaluationRequest,
    FAImpairmentRequest, FADisposalRequest, FADisposalRead,
    FADepreciationScheduleRead, FADepreciationGenerateRequest,
    FADepreciationPostRequest, FADepreciationPostResult,
    FAAssetEventRead, FAComponentCreate, FAComponentRead,
    FALegacyImportRequest, FALegacyImportResult,
    FANBVReportRow, FAAIRecRead, FAAIRecAck,
)
from app.services import fixed_assets_service as svc

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────

def _cat_read(c: FAAssetCategory) -> FAAssetCategoryRead:
    return FAAssetCategoryRead.model_validate(c)


def _asset_read(a: FAFixedAsset) -> FAFixedAssetRead:
    d = FAFixedAssetRead.model_validate(a)
    if a.category:
        d.category_name = a.category.category_name
    return d


def _sched_read(s: FADepreciationSchedule) -> FADepreciationScheduleRead:
    return FADepreciationScheduleRead.model_validate(s)


def _event_read(e: FAAssetEvent) -> FAAssetEventRead:
    return FAAssetEventRead.model_validate(e)


async def _get_asset_or_404(db: AsyncSession, asset_id: UUID) -> FAFixedAsset:
    result = await db.execute(
        select(FAFixedAsset)
        .options(
            selectinload(FAFixedAsset.category),
            selectinload(FAFixedAsset.schedule_lines),
            selectinload(FAFixedAsset.events),
            selectinload(FAFixedAsset.components),
        )
        .where(FAFixedAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    return asset


# ── Asset Categories ───────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[FAAssetCategoryRead])
async def list_categories(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAAssetCategory)
    if active_only:
        q = q.where(FAAssetCategory.is_active == True)
    q = q.order_by(FAAssetCategory.category_code)
    result = await db.execute(q)
    return [_cat_read(c) for c in result.scalars().all()]


@router.post("/categories", response_model=FAAssetCategoryRead, status_code=201)
async def create_category(
    payload: FAAssetCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cat = FAAssetCategory(**payload.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return _cat_read(cat)


@router.patch("/categories/{cat_id}", response_model=FAAssetCategoryRead)
async def update_category(
    cat_id: UUID,
    payload: FAAssetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(FAAssetCategory).where(FAAssetCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    return _cat_read(cat)


# ── Asset Master ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[FAFixedAssetRead])
async def list_assets(
    status: Optional[FAAssetStatus] = None,
    category_id: Optional[UUID] = None,
    cost_center: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAFixedAsset).options(selectinload(FAFixedAsset.category))
    if status:
        q = q.where(FAFixedAsset.status == status)
    if category_id:
        q = q.where(FAFixedAsset.asset_category_id == category_id)
    if cost_center:
        q = q.where(FAFixedAsset.cost_center.ilike(f"%{cost_center}%"))
    if location:
        q = q.where(FAFixedAsset.location.ilike(f"%{location}%"))
    if search:
        q = q.where(
            FAFixedAsset.asset_name.ilike(f"%{search}%") |
            FAFixedAsset.asset_code.ilike(f"%{search}%")
        )
    q = q.order_by(FAFixedAsset.asset_code).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_asset_read(a) for a in result.scalars().all()]


@router.post("", response_model=FAFixedAssetRead, status_code=201)
async def create_asset(
    payload: FAFixedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    depreciable_base = data["local_currency_cost"] - data["salvage_value"]
    data["depreciable_base"] = depreciable_base
    data["net_book_value"] = data["local_currency_cost"]
    if data.get("is_legacy_import") and data.get("legacy_accumulated_depreciation"):
        data["accumulated_depreciation"] = data["legacy_accumulated_depreciation"]
        data["net_book_value"] = data["local_currency_cost"] - data["legacy_accumulated_depreciation"]

    asset = FAFixedAsset(**data)
    db.add(asset)

    # Acquisition event
    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.LEGACY_IMPORT if data.get("is_legacy_import") else AssetEventType.ACQUISITION,
        event_date=payload.acquisition_date or date.today(),
        amount=payload.local_currency_cost,
        nbv_before=Decimal("0"),
        nbv_after=asset.net_book_value,
        user_id=current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(asset)
    result2 = await db.execute(
        select(FAFixedAsset).options(selectinload(FAFixedAsset.category)).where(FAFixedAsset.id == asset.id)
    )
    return _asset_read(result2.scalar_one())


@router.get("/{asset_id}", response_model=FAFixedAssetRead)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _asset_read(await _get_asset_or_404(db, asset_id))


@router.patch("/{asset_id}", response_model=FAFixedAssetRead)
async def update_asset(
    asset_id: UUID,
    payload: FAFixedAssetUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    if asset.status == FAAssetStatus.DISPOSED:
        raise HTTPException(400, "Cannot update a disposed asset")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(asset, k, v)
    if payload.salvage_value is not None:
        asset.depreciable_base = asset.local_currency_cost - asset.salvage_value
    await db.commit()
    await db.refresh(asset)
    return _asset_read(asset)


# ── Capitalize ─────────────────────────────────────────────────────────────────

@router.post("/{asset_id}/capitalize", response_model=FAFixedAssetRead)
async def capitalize_asset(
    asset_id: UUID,
    payload: FACapitalizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    if asset.status != FAAssetStatus.DRAFT:
        raise HTTPException(400, "Only DRAFT assets can be capitalized")

    start_rule = asset.category.depreciation_start_rule if asset.category else DepreciationStartRule.FIRST_OF_NEXT_MONTH
    event = svc.capitalize_asset(
        asset, payload.capitalization_date, payload.in_service_date,
        payload.depreciation_start_date, start_rule, current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(asset)
    return _asset_read(asset)


# ── Transfer ───────────────────────────────────────────────────────────────────

@router.post("/{asset_id}/transfer", response_model=FAAssetEventRead)
async def transfer_asset(
    asset_id: UUID,
    payload: FATransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    event = svc.transfer_asset(asset, payload, current_user.id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_read(event)


# ── Revaluation ────────────────────────────────────────────────────────────────

@router.post("/{asset_id}/revalue", response_model=FAAssetEventRead)
async def revalue_asset(
    asset_id: UUID,
    payload: FARevaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    if asset.status not in (FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED):
        raise HTTPException(400, "Revaluation only allowed for ACTIVE or IMPAIRED assets")
    event = svc.revalue_asset(asset, payload, current_user.id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_read(event)


# ── Impairment ─────────────────────────────────────────────────────────────────

@router.post("/{asset_id}/impair", response_model=FAAssetEventRead)
async def impair_asset(
    asset_id: UUID,
    payload: FAImpairmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    if asset.status not in (FAAssetStatus.ACTIVE,):
        raise HTTPException(400, "Impairment only allowed for ACTIVE assets")
    event = svc.impair_asset(asset, payload, current_user.id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_read(event)


# ── Disposal ───────────────────────────────────────────────────────────────────

@router.post("/{asset_id}/dispose", response_model=FADisposalRead)
async def dispose_asset(
    asset_id: UUID,
    payload: FADisposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    if asset.status in (FAAssetStatus.DISPOSED, FAAssetStatus.RETIRED):
        raise HTTPException(400, "Asset is already disposed or retired")
    disposal, event = svc.dispose_asset(asset, payload, current_user.id)
    db.add(disposal)
    db.add(event)
    # Cancel all future PLANNED depreciation
    for line in asset.schedule_lines:
        if line.schedule_status == ScheduleStatus.PLANNED:
            line.schedule_status = ScheduleStatus.REVERSED
    await db.commit()
    await db.refresh(disposal)
    return FADisposalRead.model_validate(disposal)


# ── Depreciation Schedule ──────────────────────────────────────────────────────

@router.get("/{asset_id}/depreciation-schedule", response_model=List[FADepreciationScheduleRead])
async def get_schedule(
    asset_id: UUID,
    status_filter: Optional[ScheduleStatus] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    lines = asset.schedule_lines
    if status_filter:
        lines = [l for l in lines if l.schedule_status == status_filter]
    return [_sched_read(l) for l in lines]


@router.post("/depreciation/generate", response_model=dict)
async def generate_schedule(
    payload: FADepreciationGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAFixedAsset).options(
        selectinload(FAFixedAsset.category),
        selectinload(FAFixedAsset.schedule_lines),
    ).where(FAFixedAsset.status.in_([FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED]))
    if payload.asset_ids:
        q = q.where(FAFixedAsset.id.in_(payload.asset_ids))
    result = await db.execute(q)
    assets = result.scalars().all()

    total_generated = 0
    for asset in assets:
        # Remove existing PLANNED lines before re-generating
        for line in list(asset.schedule_lines):
            if line.schedule_status == ScheduleStatus.PLANNED:
                await db.delete(line)

        start_rule = (asset.category.depreciation_start_rule
                      if asset.category else DepreciationStartRule.FIRST_OF_NEXT_MONTH)
        new_lines = svc.generate_depreciation_schedule(asset, start_rule, payload.through_date)
        for line in new_lines:
            db.add(line)
        total_generated += len(new_lines)

    await db.commit()
    return {"assets_processed": len(assets), "lines_generated": total_generated}


@router.post("/depreciation/post", response_model=FADepreciationPostResult)
async def post_depreciation(
    payload: FADepreciationPostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(FADepreciationSchedule)
        .options(selectinload(FADepreciationSchedule.asset))
        .where(
            FADepreciationSchedule.schedule_status == ScheduleStatus.PLANNED,
            FADepreciationSchedule.period_start >= payload.period_start,
            FADepreciationSchedule.period_end <= payload.period_end,
        )
    )
    if payload.asset_ids:
        q = q.where(FADepreciationSchedule.asset_id.in_(payload.asset_ids))
    result = await db.execute(q)
    lines = result.scalars().all()

    total_amount = Decimal("0")
    posted_count = 0
    failed: list[str] = []
    posting_date = payload.period_end

    for line in lines:
        try:
            updated_line, event = svc.post_depreciation_line(line, posting_date)
            total_amount += updated_line.posted_amount or Decimal("0")
            posted_count += 1
            if not payload.dry_run:
                db.add(event)
        except Exception as e:
            failed.append(f"{line.asset_id}: {e}")

    if not payload.dry_run:
        await db.commit()

    return FADepreciationPostResult(
        total_assets=len({l.asset_id for l in lines}),
        total_posted=posted_count,
        total_amount=total_amount,
        failed=failed,
        dry_run=payload.dry_run,
    )


# ── Asset Events ───────────────────────────────────────────────────────────────

@router.get("/{asset_id}/events", response_model=List[FAAssetEventRead])
async def get_events(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    return [_event_read(e) for e in asset.events]


# ── Components ─────────────────────────────────────────────────────────────────

@router.get("/{asset_id}/components", response_model=List[FAComponentRead])
async def get_components(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    return [FAComponentRead.model_validate(c) for c in asset.components]


@router.post("/{asset_id}/components", response_model=FAComponentRead, status_code=201)
async def add_component(
    asset_id: UUID,
    payload: FAComponentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    asset = await _get_asset_or_404(db, asset_id)
    comp = FAAssetComponent(
        parent_asset_id=asset.id,
        net_book_value=payload.component_cost - payload.salvage_value,
        **payload.model_dump(),
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return FAComponentRead.model_validate(comp)


# ── Legacy Import ──────────────────────────────────────────────────────────────

@router.post("/import-legacy", response_model=FALegacyImportResult)
async def import_legacy(
    payload: FALegacyImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    succeeded = 0
    failed: list[str] = []

    for row in payload.rows:
        try:
            local_cost = row.original_cost
            dep_base = local_cost - row.salvage_value
            nbv = local_cost - row.accumulated_depreciation_to_date

            asset = FAFixedAsset(
                asset_code=row.asset_code,
                asset_name=row.asset_name,
                asset_category_id=row.asset_category_id,
                original_cost=local_cost,
                currency="KES",
                exchange_rate=Decimal("1"),
                local_currency_cost=local_cost,
                salvage_value=row.salvage_value,
                depreciable_base=dep_base,
                useful_life_months=row.useful_life_months,
                depreciation_method=row.depreciation_method,
                depreciation_frequency="MONTHLY",
                accumulated_depreciation=row.accumulated_depreciation_to_date,
                net_book_value=nbv,
                in_service_date=row.in_service_date,
                capitalization_date=row.in_service_date,
                status=FAAssetStatus.ACTIVE,
                cost_center=row.cost_center,
                location=row.location,
                is_legacy_import=True,
                legacy_accumulated_depreciation=row.accumulated_depreciation_to_date,
                notes=row.notes,
            )
            db.add(asset)

            event = FAAssetEvent(
                asset_id=asset.id,
                event_type=AssetEventType.LEGACY_IMPORT,
                event_date=payload.as_of_date,
                amount=local_cost,
                nbv_before=Decimal("0"),
                nbv_after=nbv,
                user_id=current_user.id,
                notes=f"Legacy import as of {payload.as_of_date}",
            )
            db.add(event)
            succeeded += 1
        except Exception as e:
            failed.append(f"{row.asset_code}: {e}")

    await db.commit()
    return FALegacyImportResult(total=len(payload.rows), succeeded=succeeded, failed=failed)


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/nbv", response_model=List[FANBVReportRow])
async def nbv_report(
    as_of_date: date = Query(default=None),
    category_id: Optional[UUID] = None,
    cost_center: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not as_of_date:
        as_of_date = date.today()
    q = select(FAFixedAsset).options(selectinload(FAFixedAsset.category)).where(
        FAFixedAsset.status.notin_([FAAssetStatus.DRAFT, FAAssetStatus.ARCHIVED])
    )
    if category_id:
        q = q.where(FAFixedAsset.asset_category_id == category_id)
    if cost_center:
        q = q.where(FAFixedAsset.cost_center.ilike(f"%{cost_center}%"))
    result = await db.execute(q)
    assets = result.scalars().all()
    return [
        FANBVReportRow(
            asset_id=str(a.id),
            asset_code=a.asset_code,
            asset_name=a.asset_name,
            category=a.category.category_name if a.category else "",
            cost_center=a.cost_center,
            original_cost=a.local_currency_cost,
            accumulated_depreciation=a.accumulated_depreciation,
            net_book_value=a.net_book_value,
            status=a.status.value,
            as_of_date=as_of_date,
        )
        for a in assets
    ]


@router.get("/reports/register", response_model=List[FAFixedAssetRead])
async def asset_register(
    status_filter: Optional[FAAssetStatus] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAFixedAsset).options(selectinload(FAFixedAsset.category))
    if status_filter:
        q = q.where(FAFixedAsset.status == status_filter)
    q = q.order_by(FAFixedAsset.asset_code)
    result = await db.execute(q)
    return [_asset_read(a) for a in result.scalars().all()]


# ── AI Recommendations ─────────────────────────────────────────────────────────

@router.get("/ai/recommendations", response_model=List[FAAIRecRead])
async def get_ai_recs(
    status_filter: Optional[FAIRecStatus] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAAIRecommendation)
    if status_filter:
        q = q.where(FAAIRecommendation.status == status_filter)
    q = q.order_by(FAAIRecommendation.created_at.desc()).limit(200)
    result = await db.execute(q)
    return [FAAIRecRead.model_validate(r) for r in result.scalars().all()]


@router.post("/ai/run-agents", response_model=dict)
async def run_ai_agents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(FAFixedAsset).where(FAFixedAsset.status == FAAssetStatus.ACTIVE)
    result = await db.execute(q)
    assets = result.scalars().all()
    recs = svc.run_ai_agents(assets)
    for r in recs:
        db.add(r)
    await db.commit()
    return {"recommendations_generated": len(recs)}


@router.patch("/ai/recommendations/{rec_id}", response_model=FAAIRecRead)
async def ack_ai_rec(
    rec_id: UUID,
    payload: FAAIRecAck,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    result = await db.execute(select(FAAIRecommendation).where(FAAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = payload.status
    if payload.action_taken:
        rec.action_taken = payload.action_taken
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rec)
    return FAAIRecRead.model_validate(rec)


# ── Dashboard summary ──────────────────────────────────────────────────────────

@router.get("/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total_q = await db.execute(select(func.count()).select_from(FAFixedAsset))
    active_q = await db.execute(
        select(func.count()).select_from(FAFixedAsset).where(FAFixedAsset.status == FAAssetStatus.ACTIVE)
    )
    nbv_q = await db.execute(
        select(func.sum(FAFixedAsset.net_book_value)).where(
            FAFixedAsset.status.in_([FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED])
        )
    )
    cost_q = await db.execute(
        select(func.sum(FAFixedAsset.local_currency_cost)).where(
            FAFixedAsset.status.in_([FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED])
        )
    )
    accum_q = await db.execute(
        select(func.sum(FAFixedAsset.accumulated_depreciation)).where(
            FAFixedAsset.status.in_([FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED])
        )
    )
    pending_depr_q = await db.execute(
        select(func.count()).select_from(FADepreciationSchedule).where(
            FADepreciationSchedule.schedule_status == ScheduleStatus.PLANNED
        )
    )
    ai_pending_q = await db.execute(
        select(func.count()).select_from(FAAIRecommendation).where(
            FAAIRecommendation.status == FAIRecStatus.PENDING
        )
    )
    return {
        "total_assets": total_q.scalar() or 0,
        "active_assets": active_q.scalar() or 0,
        "total_nbv": float(nbv_q.scalar() or 0),
        "total_cost": float(cost_q.scalar() or 0),
        "total_accumulated_depreciation": float(accum_q.scalar() or 0),
        "pending_depreciation_lines": pending_depr_q.scalar() or 0,
        "ai_pending_recommendations": ai_pending_q.scalar() or 0,
    }
