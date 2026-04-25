"""Allergen + Nutrition Management — API endpoints."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.allergen import (
    AllergenMasterCreate, AllergenMasterUpdate, AllergenMasterOut,
    MaterialAllergenProfileCreate, MaterialAllergenProfileUpdate, MaterialAllergenProfileOut,
    NutritionProfileCreate, NutritionProfileOut, NutritionLineCreate, NutritionLineUpdate, NutritionLineOut,
    AllergenRollupResult, NutritionRollupResult,
    ProductAllergenSummaryOut, ProductNutritionSummaryOut,
    AllergenChangeLogOut,
    ServingConfigCreate, ServingConfigOut,
    LabelReadinessOut,
    BOMAllergenComparisonOut, BOMNutritionComparisonOut,
    ANAIRecOut, ANAIRecReview,
    ANDashboardOut,
)
from app.services import allergen_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ANDashboardOut)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Allergen Master ───────────────────────────────────────────────────────────

@router.get("/allergens", response_model=List[AllergenMasterOut])
async def list_allergens(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    return await svc.list_allergens(db, active_only)


@router.post("/allergens", response_model=AllergenMasterOut, status_code=201)
async def create_allergen(payload: AllergenMasterCreate, db: AsyncSession = Depends(get_db)):
    a = await svc.create_allergen(db, payload.model_dump())
    await db.commit()
    await db.refresh(a)
    return a


@router.get("/allergens/{allergen_id}", response_model=AllergenMasterOut)
async def get_allergen(allergen_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await svc.get_allergen(db, allergen_id)
    if not a:
        raise HTTPException(404, "Allergen not found")
    return a


@router.patch("/allergens/{allergen_id}", response_model=AllergenMasterOut)
async def update_allergen(allergen_id: uuid.UUID, payload: AllergenMasterUpdate, db: AsyncSession = Depends(get_db)):
    a = await svc.update_allergen(db, allergen_id, payload.model_dump(exclude_none=True))
    if not a:
        raise HTTPException(404, "Allergen not found")
    await db.commit()
    await db.refresh(a)
    return a


@router.post("/allergens/seed-defaults", status_code=201)
async def seed_defaults(db: AsyncSession = Depends(get_db)):
    added = await svc.seed_default_allergens(db)
    await db.commit()
    return {"added": added}


# ── Material Allergen Profiles ─────────────────────────────────────────────────

@router.get("/materials/allergen-profiles", response_model=List[MaterialAllergenProfileOut])
async def list_allergen_profiles(
    has_allergens: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await svc.list_material_allergen_profiles(db, has_allergens)
    return [MaterialAllergenProfileOut.model_validate(r) for r in rows]


@router.get("/materials/{material_id}/allergen-profile", response_model=MaterialAllergenProfileOut)
async def get_allergen_profile(material_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    d = await svc.get_profile_with_lines(db, material_id)
    if not d:
        raise HTTPException(404, "No allergen profile for this material")
    return MaterialAllergenProfileOut.model_validate(d)


@router.post("/materials/{material_id}/allergen-profile", response_model=MaterialAllergenProfileOut, status_code=201)
async def upsert_allergen_profile(
    material_id: uuid.UUID,
    payload: MaterialAllergenProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    data["material_id"] = material_id
    profile = await svc.create_or_replace_allergen_profile(db, material_id, data)
    await db.commit()
    d = await svc.get_profile_with_lines(db, material_id)
    return MaterialAllergenProfileOut.model_validate(d)


@router.patch("/materials/{material_id}/allergen-profile", response_model=MaterialAllergenProfileOut)
async def update_allergen_profile(
    material_id: uuid.UUID,
    payload: MaterialAllergenProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    profile = await svc.get_material_allergen_profile(db, material_id)
    if not profile:
        raise HTTPException(404, "No allergen profile for this material")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(profile, k, v)
    await db.commit()
    d = await svc.get_profile_with_lines(db, material_id)
    return MaterialAllergenProfileOut.model_validate(d)


# ── Nutrition Profiles ────────────────────────────────────────────────────────

@router.get("/nutrition-profiles", response_model=List[NutritionProfileOut])
async def list_nutrition_profiles(
    entity_type: str = Query("material", regex="^(material|product)$"),
    db: AsyncSession = Depends(get_db),
):
    rows = await svc.list_nutrition_profiles(db, entity_type)
    return [NutritionProfileOut.model_validate(r) for r in rows]


@router.get("/materials/{material_id}/nutrition-profile", response_model=NutritionProfileOut)
async def get_material_nutrition(material_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.master import Material as Mat
    profile = await svc.get_nutrition_profile_for_material(db, material_id)
    if not profile:
        raise HTTPException(404, "No nutrition profile for this material")
    from app.db.session import get_db as _
    from sqlalchemy.ext.asyncio import AsyncSession as AS
    mat_r = await db.execute(select(Mat.name).where(Mat.id == material_id))
    mat_name = mat_r.scalar_one_or_none()
    d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
    d["entity_name"] = mat_name
    d["lines"] = [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in profile.lines]
    return NutritionProfileOut.model_validate(d)


@router.post("/materials/{material_id}/nutrition-profile", response_model=NutritionProfileOut, status_code=201)
async def create_material_nutrition(
    material_id: uuid.UUID,
    payload: NutritionProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    data["material_id"] = material_id
    profile = await svc.create_nutrition_profile(db, data)
    await db.commit()
    await db.refresh(profile)
    d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
    d["entity_name"] = None
    d["lines"] = [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in profile.lines]
    return NutritionProfileOut.model_validate(d)


@router.post("/products/{product_id}/nutrition-profile", response_model=NutritionProfileOut, status_code=201)
async def create_product_nutrition(
    product_id: uuid.UUID,
    payload: NutritionProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    data["product_id"] = product_id
    profile = await svc.create_nutrition_profile(db, data)
    await db.commit()
    await db.refresh(profile)
    d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
    d["entity_name"] = None
    d["lines"] = [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in profile.lines]
    return NutritionProfileOut.model_validate(d)


@router.post("/nutrition-profiles/{profile_id}/lines", response_model=NutritionLineOut, status_code=201)
async def add_nutrition_line(
    profile_id: uuid.UUID,
    payload: NutritionLineCreate,
    db: AsyncSession = Depends(get_db),
):
    line = await svc.add_nutrition_line(db, profile_id, payload.model_dump())
    await db.commit()
    await db.refresh(line)
    return line


@router.patch("/nutrition-profiles/lines/{line_id}", response_model=NutritionLineOut)
async def update_nutrition_line(
    line_id: uuid.UUID,
    payload: NutritionLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    line = await svc.update_nutrition_line(db, line_id, payload.model_dump(exclude_none=True))
    if not line:
        raise HTTPException(404, "Nutrition line not found")
    await db.commit()
    await db.refresh(line)
    return line


# ── Roll-Up Endpoints ─────────────────────────────────────────────────────────

@router.get("/bom/{bom_id}/allergen-rollup", response_model=AllergenRollupResult)
async def bom_allergen_rollup(bom_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await svc.rollup_allergens_from_bom(db, bom_id)
    if not result:
        raise HTTPException(404, "BOM not found")
    return AllergenRollupResult.model_validate(result)


@router.get("/bom/{bom_id}/nutrition-rollup", response_model=NutritionRollupResult)
async def bom_nutrition_rollup(
    bom_id: uuid.UUID,
    serving_size_g: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await svc.rollup_nutrition_from_bom(db, bom_id, serving_size_g)
    if not result:
        raise HTTPException(404, "BOM not found")
    return NutritionRollupResult.model_validate(result)


@router.get("/recipe/{recipe_id}/allergen-rollup", response_model=AllergenRollupResult)
async def recipe_allergen_rollup(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await svc.rollup_allergens_from_recipe(db, recipe_id)
    if not result:
        raise HTTPException(404, "Recipe not found")
    return AllergenRollupResult.model_validate(result)


@router.get("/recipe/{recipe_id}/nutrition-rollup", response_model=NutritionRollupResult)
async def recipe_nutrition_rollup(
    recipe_id: uuid.UUID,
    serving_size_g: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await svc.rollup_nutrition_from_recipe(db, recipe_id, serving_size_g)
    if not result:
        raise HTTPException(404, "Recipe not found")
    return NutritionRollupResult.model_validate(result)


# ── Product Allergen Summary ──────────────────────────────────────────────────

@router.get("/products/allergen-summaries", response_model=List[ProductAllergenSummaryOut])
async def list_allergen_summaries(db: AsyncSession = Depends(get_db)):
    rows = await svc.list_product_allergen_summaries(db)
    return [ProductAllergenSummaryOut.model_validate(r) for r in rows]


@router.get("/products/{product_id}/allergen-summary", response_model=ProductAllergenSummaryOut)
async def get_allergen_summary(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    d = await svc.get_product_allergen_summary(db, product_id)
    if not d:
        raise HTTPException(404, "No allergen summary for this product")
    return ProductAllergenSummaryOut.model_validate(d)


@router.post("/products/{product_id}/allergen-summary/calculate")
async def calculate_allergen_summary(
    product_id: uuid.UUID,
    bom_id: Optional[uuid.UUID] = None,
    recipe_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    if bom_id:
        rollup = await svc.rollup_allergens_from_bom(db, bom_id)
        rollup["source"] = "BOM"
    elif recipe_id:
        rollup = await svc.rollup_allergens_from_recipe(db, recipe_id)
        rollup["source"] = "RECIPE"
    else:
        raise HTTPException(400, "Provide bom_id or recipe_id")
    summary = await svc.save_product_allergen_summary(db, product_id, rollup)
    await db.commit()
    return {"id": str(summary.id), "calculated": True}


# ── Product Nutrition Summary ─────────────────────────────────────────────────

@router.get("/products/nutrition-summaries", response_model=List[ProductNutritionSummaryOut])
async def list_nutrition_summaries(db: AsyncSession = Depends(get_db)):
    rows = await svc.list_product_nutrition_summaries(db)
    return [ProductNutritionSummaryOut.model_validate(r) for r in rows]


@router.get("/products/{product_id}/nutrition-summary", response_model=ProductNutritionSummaryOut)
async def get_nutrition_summary(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    d = await svc.get_product_nutrition_summary(db, product_id)
    if not d:
        raise HTTPException(404, "No nutrition summary for this product")
    return ProductNutritionSummaryOut.model_validate(d)


@router.post("/products/{product_id}/nutrition-summary/calculate")
async def calculate_nutrition_summary(
    product_id: uuid.UUID,
    bom_id: Optional[uuid.UUID] = None,
    recipe_id: Optional[uuid.UUID] = None,
    serving_size_g: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
):
    if bom_id:
        rollup = await svc.rollup_nutrition_from_bom(db, bom_id, serving_size_g)
        rollup["source"] = "BOM"
    elif recipe_id:
        rollup = await svc.rollup_nutrition_from_recipe(db, recipe_id, serving_size_g)
        rollup["source"] = "RECIPE"
    else:
        raise HTTPException(400, "Provide bom_id or recipe_id")
    summary = await svc.save_product_nutrition_summary(db, product_id, rollup)
    await db.commit()
    return {"id": str(summary.id), "calculated": True}


# ── Serving Config ────────────────────────────────────────────────────────────

@router.get("/products/{product_id}/serving-config", response_model=ServingConfigOut)
async def get_serving_config(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_serving_config(db, product_id)
    if not cfg:
        raise HTTPException(404, "No serving config for this product")
    return cfg


@router.post("/products/{product_id}/serving-config", response_model=ServingConfigOut, status_code=201)
async def upsert_serving_config(
    product_id: uuid.UUID,
    payload: ServingConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_none=True)
    data.pop("product_id", None)
    cfg = await svc.upsert_serving_config(db, product_id, data)
    await db.commit()
    await db.refresh(cfg)
    return cfg


# ── Label Readiness ───────────────────────────────────────────────────────────

@router.get("/products/{product_id}/label-readiness", response_model=LabelReadinessOut)
async def get_label_readiness(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return LabelReadinessOut.model_validate(
        await svc.get_label_readiness(db, product_id)
    )


# ── BOM Comparison ────────────────────────────────────────────────────────────

@router.get("/bom/compare/{bom_id_a}/{bom_id_b}/allergens", response_model=BOMAllergenComparisonOut)
async def compare_allergens(bom_id_a: uuid.UUID, bom_id_b: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return BOMAllergenComparisonOut.model_validate(
        await svc.compare_bom_allergens(db, bom_id_a, bom_id_b)
    )


@router.get("/bom/compare/{bom_id_a}/{bom_id_b}/nutrition", response_model=BOMNutritionComparisonOut)
async def compare_nutrition(
    bom_id_a: uuid.UUID,
    bom_id_b: uuid.UUID,
    threshold_pct: Decimal = Decimal("10"),
    db: AsyncSession = Depends(get_db),
):
    return BOMNutritionComparisonOut.model_validate(
        await svc.compare_bom_nutrition(db, bom_id_a, bom_id_b, threshold_pct)
    )


# ── Allergen Change Logs ──────────────────────────────────────────────────────

@router.get("/change-logs", response_model=List[AllergenChangeLogOut])
async def list_change_logs(
    product_id: Optional[uuid.UUID] = None,
    review_pending: Optional[bool] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = await svc.list_change_logs(db, product_id, review_pending, limit)
    return [AllergenChangeLogOut.model_validate(r) for r in rows]


@router.patch("/change-logs/{log_id}/mark-reviewed")
async def mark_reviewed(
    log_id: uuid.UUID,
    review_type: str = Query(..., regex="^(label|qc)$"),
    db: AsyncSession = Depends(get_db),
):
    log = await svc.mark_review_done(db, log_id, review_type)
    if not log:
        raise HTTPException(404, "Change log not found")
    await db.commit()
    return {"id": str(log_id), "review_type": review_type, "marked": True}


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-allergen-risk-monitor", status_code=201)
async def run_allergen_monitor(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_allergen_risk_monitor(db)
    await db.commit()
    return {"generated": len(recs)}


@router.post("/ai/run-nutrition-change-analyzer", status_code=201)
async def run_nutrition_analyzer(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_nutrition_change_analyzer(db)
    await db.commit()
    return {"generated": len(recs)}


@router.post("/ai/run-label-compliance-assistant", status_code=201)
async def run_label_assistant(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_label_compliance_assistant(db)
    await db.commit()
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[ANAIRecOut])
async def list_recommendations(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recommendations(db, agent_type, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=ANAIRecOut)
async def review_recommendation(
    rec_id: uuid.UUID,
    payload: ANAIRecReview,
    db: AsyncSession = Depends(get_db),
):
    rec = await svc.review_ai_rec(db, rec_id, payload.status, payload.reviewed_by)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/raw-material-allergens")
async def report_rm_allergens(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.allergen import MaterialAllergenProfile, MaterialAllergenLine, AllergenMaster
    from app.models.master import Material
    q = (
        select(
            Material.code, Material.name,
            MaterialAllergenProfile.cross_contact_risk_level,
            MaterialAllergenProfile.allergen_present_flag,
            MaterialAllergenProfile.allergen_may_contain_flag,
            MaterialAllergenProfile.supplier_allergen_statement_ref,
            MaterialAllergenProfile.allergen_review_date,
        )
        .join(MaterialAllergenProfile, Material.id == MaterialAllergenProfile.material_id)
        .order_by(Material.name)
    )
    r = await db.execute(q)
    return [dict(row._mapping) for row in r.all()]


@router.get("/reports/finished-product-allergens")
async def report_fg_allergens(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.allergen import ProductAllergenSummary
    from app.models.master import Product
    q = (
        select(Product.name, ProductAllergenSummary)
        .join(ProductAllergenSummary, Product.id == ProductAllergenSummary.product_id)
        .order_by(Product.name)
    )
    r = await db.execute(q)
    return [
        {
            "product_name": pname,
            "contains": summary.contains_allergens,
            "may_contain": summary.may_contain_allergens,
            "declaration_required": summary.declaration_required,
            "label_statement": summary.label_statement,
            "is_stale": summary.is_stale,
            "last_calculated_at": str(summary.last_calculated_at) if summary.last_calculated_at else None,
        }
        for pname, summary in r.all()
    ]


@router.get("/reports/nutrition-completeness")
async def report_nutrition_completeness(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.master import Material
    from app.models.allergen import NutritionProfile, NutritionProfileLine
    r = await db.execute(
        select(
            Material.name, Material.code,
            func.count(NutritionProfileLine.id).label("nutrient_count"),
            func.bool_and(NutritionProfileLine.approved_flag).label("all_approved"),
        )
        .outerjoin(NutritionProfile, Material.id == NutritionProfile.material_id)
        .outerjoin(NutritionProfileLine, NutritionProfile.id == NutritionProfileLine.profile_id)
        .group_by(Material.name, Material.code)
        .order_by(Material.name)
    )
    return [dict(row._mapping) for row in r.all()]


@router.get("/reports/missing-supplier-statements")
async def report_missing_statements(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.master import Material
    from app.models.allergen import MaterialAllergenProfile
    r = await db.execute(
        select(Material.name, Material.code, MaterialAllergenProfile.allergen_review_date, MaterialAllergenProfile.cross_contact_risk_level)
        .join(MaterialAllergenProfile, Material.id == MaterialAllergenProfile.material_id)
        .where(or_(
            MaterialAllergenProfile.supplier_allergen_statement_ref.is_(None),
            MaterialAllergenProfile.supplier_allergen_statement_ref == "",
        ))
        .order_by(Material.name)
    )
    return [dict(row._mapping) for row in r.all()]


from sqlalchemy import func, or_
