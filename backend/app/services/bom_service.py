"""Advanced BOM CRUD, versioning, cloning, lifecycle management."""
from __future__ import annotations
import random
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMSubstituteGroup, BOMSubstitute,
    BOMConversionProfile, BOMYieldConfig, BOMAIRec,
    BOMType, BOMLifecycle, BOMRecStatus,
)
from app.schemas.bom import BOMCreate, BOMUpdate, BOMLineCreate, BOMLineUpdate


_D = lambda v: Decimal(str(v))


def _bom_code() -> str:
    sfx = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"BOM-{sfx}"


def _sub_code() -> str:
    sfx = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SG-{sfx}"


def _conv_code() -> str:
    sfx = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    return f"CONV-{sfx}"


async def _load_bom(db: AsyncSession, bom_id: UUID) -> Optional[AdvancedBOM]:
    r = await db.execute(
        select(AdvancedBOM)
        .where(AdvancedBOM.id == bom_id)
        .options(
            selectinload(AdvancedBOM.lines).selectinload(AdvancedBOMLine.substitute_group),
            selectinload(AdvancedBOM.yield_configs),
            selectinload(AdvancedBOM.ai_recs),
        )
    )
    return r.scalar_one_or_none()


# ── BOM CRUD ───────────────────────────────────────────────────────────────────

async def create_bom(db: AsyncSession, req: BOMCreate, user_id: UUID) -> AdvancedBOM:
    # resolve product name
    product_name = None
    if req.product_id:
        from app.models.master import Product
        pr = await db.execute(select(Product).where(Product.id == req.product_id))
        p = pr.scalar_one_or_none()
        product_name = p.name if p else None

    bom = AdvancedBOM(
        bom_code=_bom_code(),
        bom_name=req.bom_name,
        bom_type=req.bom_type,
        product_id=req.product_id,
        product_name=product_name,
        base_qty=req.base_qty,
        base_uom=req.base_uom,
        version_no=req.version_no,
        effective_from=req.effective_from,
        effective_to=req.effective_to,
        notes=req.notes,
        created_by_id=user_id,
    )
    db.add(bom)
    await db.flush()
    await db.refresh(bom)
    return bom


async def list_boms(
    db: AsyncSession,
    bom_type: Optional[BOMType] = None,
    lifecycle: Optional[BOMLifecycle] = None,
    product_id: Optional[UUID] = None,
) -> List[AdvancedBOM]:
    q = select(AdvancedBOM).order_by(AdvancedBOM.created_at.desc())
    if bom_type:
        q = q.where(AdvancedBOM.bom_type == bom_type)
    if lifecycle:
        q = q.where(AdvancedBOM.lifecycle == lifecycle)
    if product_id:
        q = q.where(AdvancedBOM.product_id == product_id)
    r = await db.execute(q)
    return r.scalars().all()


async def get_bom(db: AsyncSession, bom_id: UUID) -> Optional[AdvancedBOM]:
    return await _load_bom(db, bom_id)


async def update_bom(db: AsyncSession, bom: AdvancedBOM, req: BOMUpdate) -> AdvancedBOM:
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(bom, k, v)
    await db.flush()
    await db.refresh(bom)
    return bom


async def clone_bom(db: AsyncSession, source: AdvancedBOM, new_version: str, user_id: UUID) -> AdvancedBOM:
    new_bom = AdvancedBOM(
        bom_code=_bom_code(),
        bom_name=source.bom_name,
        bom_type=source.bom_type,
        product_id=source.product_id,
        product_name=source.product_name,
        base_qty=source.base_qty,
        base_uom=source.base_uom,
        version_no=new_version,
        revision_no="0",
        lifecycle=BOMLifecycle.DRAFT,
        effective_from=source.effective_from,
        effective_to=source.effective_to,
        linked_routing_id=source.linked_routing_id,
        linked_quality_spec_id=source.linked_quality_spec_id,
        linked_label_profile_id=source.linked_label_profile_id,
        notes=f"Cloned from {source.bom_code} v{source.version_no}",
        created_by_id=user_id,
    )
    db.add(new_bom)
    await db.flush()

    # clone lines
    src_lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == source.id))
    src_lines = src_lines_r.scalars().all()
    for sl in src_lines:
        nl = AdvancedBOMLine(
            bom_id=new_bom.id,
            line_no=sl.line_no,
            component_type=sl.component_type,
            item_type=sl.item_type,
            item_id=sl.item_id,
            item_name=sl.item_name,
            item_code=sl.item_code,
            child_bom_id=sl.child_bom_id,
            required_qty=sl.required_qty,
            required_uom=sl.required_uom,
            basis_type=sl.basis_type,
            concentration_pct=sl.concentration_pct,
            wastage_pct=sl.wastage_pct,
            process_loss_pct=sl.process_loss_pct,
            yield_contribution_pct=sl.yield_contribution_pct,
            fixed_consumption=sl.fixed_consumption,
            is_optional=sl.is_optional,
            qc_required=sl.qc_required,
            allergen_flag=sl.allergen_flag,
            nutrition_relevant=sl.nutrition_relevant,
            critical_component=sl.critical_component,
            substitute_group_id=sl.substitute_group_id,
            substitution_policy=sl.substitution_policy,
            consumption_stage=sl.consumption_stage,
            issue_stage=sl.issue_stage,
            allergen_types=sl.allergen_types,
            traceability_level=sl.traceability_level,
            nutrition_data=sl.nutrition_data,
            notes=sl.notes,
        )
        db.add(nl)

    # clone yield configs
    ycs_r = await db.execute(select(BOMYieldConfig).where(BOMYieldConfig.bom_id == source.id))
    for yc in ycs_r.scalars().all():
        db.add(BOMYieldConfig(
            bom_id=new_bom.id,
            loss_category=yc.loss_category,
            description=yc.description,
            basis=yc.basis,
            standard_pct=yc.standard_pct,
            max_allowable_pct=yc.max_allowable_pct,
            cost_impact_flag=yc.cost_impact_flag,
            notes=yc.notes,
        ))

    await db.flush()
    await db.refresh(new_bom)
    return new_bom


async def advance_lifecycle(db: AsyncSession, bom: AdvancedBOM, user_id: UUID) -> AdvancedBOM:
    FLOW = {
        BOMLifecycle.DRAFT: BOMLifecycle.UNDER_REVIEW,
        BOMLifecycle.UNDER_REVIEW: BOMLifecycle.APPROVED,
        BOMLifecycle.APPROVED: BOMLifecycle.RELEASED,
    }
    next_lc = FLOW.get(bom.lifecycle)
    if not next_lc:
        raise ValueError(f"Cannot advance from {bom.lifecycle}")

    if next_lc == BOMLifecycle.UNDER_REVIEW:
        pass
    elif next_lc == BOMLifecycle.APPROVED:
        bom.approved_by_id = user_id
    elif next_lc == BOMLifecycle.RELEASED:
        bom.released_by_id = user_id
        # Supersede any other released BOM for same product
        if bom.product_id:
            others_r = await db.execute(
                select(AdvancedBOM).where(
                    AdvancedBOM.product_id == bom.product_id,
                    AdvancedBOM.lifecycle == BOMLifecycle.RELEASED,
                    AdvancedBOM.id != bom.id,
                )
            )
            for other in others_r.scalars().all():
                other.lifecycle = BOMLifecycle.SUPERSEDED
                other.is_default = False
        bom.is_default = True

    bom.lifecycle = next_lc
    await db.flush()
    await db.refresh(bom)
    return bom


async def archive_bom(db: AsyncSession, bom: AdvancedBOM) -> AdvancedBOM:
    bom.lifecycle = BOMLifecycle.ARCHIVED
    bom.is_default = False
    await db.flush()
    await db.refresh(bom)
    return bom


# ── BOM Lines ─────────────────────────────────────────────────────────────────

async def add_line(db: AsyncSession, bom_id: UUID, req: BOMLineCreate) -> AdvancedBOMLine:
    line = AdvancedBOMLine(bom_id=bom_id, **req.model_dump())
    db.add(line)
    await db.flush()
    await db.refresh(line)
    return line


async def update_line(db: AsyncSession, line: AdvancedBOMLine, req: BOMLineUpdate) -> AdvancedBOMLine:
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(line, k, v)
    await db.flush()
    await db.refresh(line)
    return line


async def delete_line(db: AsyncSession, line: AdvancedBOMLine) -> None:
    await db.delete(line)
    await db.flush()


async def get_line(db: AsyncSession, line_id: UUID) -> Optional[AdvancedBOMLine]:
    r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.id == line_id))
    return r.scalar_one_or_none()


# ── Substitute Groups ─────────────────────────────────────────────────────────

async def create_substitute_group(db: AsyncSession, name: str, policy, notes: Optional[str]) -> BOMSubstituteGroup:
    sg = BOMSubstituteGroup(group_code=_sub_code(), group_name=name, policy=policy, notes=notes)
    db.add(sg)
    await db.flush()
    await db.refresh(sg)
    return sg


async def list_substitute_groups(db: AsyncSession) -> List[BOMSubstituteGroup]:
    r = await db.execute(
        select(BOMSubstituteGroup)
        .where(BOMSubstituteGroup.is_active == True)
        .options(selectinload(BOMSubstituteGroup.substitutes))
    )
    return r.scalars().all()


async def add_substitute(db: AsyncSession, req) -> BOMSubstitute:
    sub = BOMSubstitute(**req.model_dump())
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


# ── Conversion Profiles ───────────────────────────────────────────────────────

async def create_conversion_profile(db: AsyncSession, req) -> BOMConversionProfile:
    profile = BOMConversionProfile(profile_code=_conv_code(), **req.model_dump())
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def list_conversion_profiles(db: AsyncSession) -> List[BOMConversionProfile]:
    r = await db.execute(select(BOMConversionProfile).where(BOMConversionProfile.is_active == True))
    return r.scalars().all()


async def get_conversion_profile(db: AsyncSession, profile_id: UUID) -> Optional[BOMConversionProfile]:
    r = await db.execute(select(BOMConversionProfile).where(BOMConversionProfile.id == profile_id))
    return r.scalar_one_or_none()


# ── Yield Configs ─────────────────────────────────────────────────────────────

async def add_yield_config(db: AsyncSession, bom_id: UUID, req) -> BOMYieldConfig:
    yc = BOMYieldConfig(bom_id=bom_id, **req.model_dump())
    db.add(yc)
    await db.flush()
    await db.refresh(yc)
    return yc


async def list_yield_configs(db: AsyncSession, bom_id: UUID) -> List[BOMYieldConfig]:
    r = await db.execute(select(BOMYieldConfig).where(BOMYieldConfig.bom_id == bom_id))
    return r.scalars().all()


# ── AI Recs ───────────────────────────────────────────────────────────────────

async def list_ai_recs(db: AsyncSession, bom_id: UUID) -> List[BOMAIRec]:
    r = await db.execute(
        select(BOMAIRec)
        .where(BOMAIRec.bom_id == bom_id)
        .order_by(BOMAIRec.created_at.desc())
    )
    return r.scalars().all()


async def action_ai_rec(db: AsyncSession, rec_id: UUID, status: BOMRecStatus, user_id: UUID) -> BOMAIRec:
    r = await db.execute(select(BOMAIRec).where(BOMAIRec.id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        raise ValueError("AI rec not found")
    rec.status = status
    rec.actioned_by_id = user_id
    rec.actioned_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(rec)
    return rec


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    all_boms_r = await db.execute(select(AdvancedBOM))
    all_boms = all_boms_r.scalars().all()

    by_type: dict = {}
    by_lifecycle: dict = {}
    for b in all_boms:
        by_type[b.bom_type.value] = by_type.get(b.bom_type.value, 0) + 1
        by_lifecycle[b.lifecycle.value] = by_lifecycle.get(b.lifecycle.value, 0) + 1

    released = sum(1 for b in all_boms if b.lifecycle == BOMLifecycle.RELEASED)
    draft = sum(1 for b in all_boms if b.lifecycle == BOMLifecycle.DRAFT)
    review = sum(1 for b in all_boms if b.lifecycle == BOMLifecycle.UNDER_REVIEW)
    with_allergens = sum(1 for b in all_boms if b.allergen_flags)

    pending_ai_r = await db.execute(
        select(func.count(BOMAIRec.id)).where(BOMAIRec.status == BOMRecStatus.PENDING)
    )
    pending_ai = pending_ai_r.scalar() or 0

    recent = sorted(all_boms, key=lambda b: b.created_at, reverse=True)[:10]

    return {
        "total_boms": len(all_boms),
        "released_boms": released,
        "draft_boms": draft,
        "pending_review": review,
        "boms_with_allergens": with_allergens,
        "pending_ai_recs": pending_ai,
        "recent_boms": recent,
        "by_type": by_type,
        "by_lifecycle": by_lifecycle,
    }
