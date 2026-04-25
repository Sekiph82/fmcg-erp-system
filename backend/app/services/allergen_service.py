"""Allergen + Nutrition Management Service — roll-up engine, AI agents, label readiness."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergen import (
    AllergenMaster, MaterialAllergenProfile, MaterialAllergenLine,
    NutritionProfile, NutritionProfileLine,
    ProductAllergenSummary, ProductNutritionSummary,
    AllergenChangeLog, ProductServingConfig, ANAIRecommendation,
    AllergenCategory, PresenceType, CrossContactRisk,
    NutrientBasis, NutrientSource, LabelBasisType,
    AllergenChangeType, ANAIAgentType, ANAIRecStatus,
)
from app.models.bom import AdvancedBOM, AdvancedBOMLine, ItemLinkType
from app.models.recipe import Recipe, RecipeItem
from app.models.master import Product, Material


# ── Default Allergens ─────────────────────────────────────────────────────────

DEFAULT_ALLERGENS = [
    ("MILK",      "Milk / Dairy",         "Milk",          "MAJOR", 1),
    ("SOY",       "Soy",                  "Soya",          "MAJOR", 2),
    ("PEANUT",    "Peanuts",              "Peanuts",       "MAJOR", 3),
    ("TREENUTS",  "Tree Nuts",            "Nuts",          "MAJOR", 4),
    ("GLUTEN",    "Gluten",               "Gluten-containing cereals", "MAJOR", 5),
    ("WHEAT",     "Wheat",                "Wheat",         "MAJOR", 6),
    ("EGG",       "Eggs",                 "Eggs",          "MAJOR", 7),
    ("SESAME",    "Sesame",               "Sesame",        "MAJOR", 8),
    ("SULFITES",  "Sulfites / SO₂",       "Sulphur dioxide", "MAJOR", 9),
    ("FISH",      "Fish",                 "Fish",          "MAJOR", 10),
    ("SHELLFISH", "Shellfish / Crustaceans", "Crustaceans", "MAJOR", 11),
    ("MUSTARD",   "Mustard",              "Mustard",       "MAJOR", 12),
    ("CELERY",    "Celery",               "Celery",        "MAJOR", 13),
    ("LUPIN",     "Lupin",                "Lupin",         "MAJOR", 14),
    ("MOLLUSCS",  "Molluscs",             "Molluscs",      "MAJOR", 15),
]

DEFAULT_NUTRIENTS = [
    ("energy_kcal",    "Energy",          "kcal"),
    ("energy_kj",      "Energy",          "kJ"),
    ("protein",        "Protein",         "g"),
    ("total_fat",      "Total Fat",       "g"),
    ("saturated_fat",  "Saturated Fat",   "g"),
    ("trans_fat",      "Trans Fat",       "g"),
    ("carbohydrates",  "Carbohydrates",   "g"),
    ("sugars",         "of which Sugars", "g"),
    ("added_sugars",   "Added Sugars",    "g"),
    ("fiber",          "Dietary Fiber",   "g"),
    ("sodium",         "Sodium",          "mg"),
    ("salt",           "Salt",            "g"),
    ("cholesterol",    "Cholesterol",     "mg"),
]


async def seed_default_allergens(db: AsyncSession) -> int:
    existing_r = await db.execute(select(AllergenMaster.allergen_code))
    existing = {r[0] for r in existing_r.all()}
    added = 0
    for code, name, reg_name, cat, sort in DEFAULT_ALLERGENS:
        if code not in existing:
            db.add(AllergenMaster(allergen_code=code, allergen_name=name, regulatory_name=reg_name, category=cat, sort_order=sort))
            added += 1
    await db.flush()
    return added


# ── Allergen Master CRUD ──────────────────────────────────────────────────────

async def list_allergens(db: AsyncSession, active_only: bool = True) -> List[AllergenMaster]:
    q = select(AllergenMaster)
    if active_only:
        q = q.where(AllergenMaster.is_active == True)
    r = await db.execute(q.order_by(AllergenMaster.sort_order, AllergenMaster.allergen_name))
    return list(r.scalars())


async def create_allergen(db: AsyncSession, data: dict) -> AllergenMaster:
    a = AllergenMaster(**data)
    db.add(a)
    await db.flush()
    return a


async def get_allergen(db: AsyncSession, allergen_id: uuid.UUID) -> Optional[AllergenMaster]:
    r = await db.execute(select(AllergenMaster).where(AllergenMaster.id == allergen_id))
    return r.scalar_one_or_none()


async def update_allergen(db: AsyncSession, allergen_id: uuid.UUID, data: dict) -> Optional[AllergenMaster]:
    a = await get_allergen(db, allergen_id)
    if not a:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(a, k, v)
    return a


# ── Material Allergen Profile CRUD ────────────────────────────────────────────

async def get_material_allergen_profile(db: AsyncSession, material_id: uuid.UUID) -> Optional[MaterialAllergenProfile]:
    r = await db.execute(
        select(MaterialAllergenProfile).where(MaterialAllergenProfile.material_id == material_id)
    )
    return r.scalar_one_or_none()


async def create_or_replace_allergen_profile(
    db: AsyncSession, material_id: uuid.UUID, data: dict
) -> MaterialAllergenProfile:
    lines_data = data.pop("lines", [])

    existing = await get_material_allergen_profile(db, material_id)
    if existing:
        for line in existing.lines:
            await db.delete(line)
        for k, v in data.items():
            setattr(existing, k, v)
        profile = existing
    else:
        profile = MaterialAllergenProfile(material_id=material_id, **data)
        db.add(profile)
    await db.flush()

    has_contains = False
    has_may = False
    for line_d in lines_data:
        line = MaterialAllergenLine(profile_id=profile.id, **line_d)
        db.add(line)
        if line_d.get("presence_type") == "CONTAINS":
            has_contains = True
        elif line_d.get("presence_type") == "MAY_CONTAIN":
            has_may = True

    profile.allergen_present_flag = has_contains
    profile.allergen_may_contain_flag = has_may
    return profile


async def list_material_allergen_profiles(
    db: AsyncSession, has_allergens: Optional[bool] = None
) -> List[dict]:
    q = (
        select(MaterialAllergenProfile, Material.name.label("material_name"))
        .join(Material, MaterialAllergenProfile.material_id == Material.id)
    )
    if has_allergens is True:
        q = q.where(MaterialAllergenProfile.allergen_present_flag == True)
    r = await db.execute(q.order_by(Material.name))
    result = []
    for profile, mat_name in r.all():
        d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
        d["material_name"] = mat_name
        d["lines"] = []
        result.append(d)
    return result


async def get_profile_with_lines(db: AsyncSession, material_id: uuid.UUID) -> Optional[dict]:
    profile = await get_material_allergen_profile(db, material_id)
    if not profile:
        return None
    mat_r = await db.execute(select(Material.name).where(Material.id == material_id))
    mat_name = mat_r.scalar_one_or_none()
    lines = []
    for line in profile.lines:
        ld = {c.name: getattr(line, c.name) for c in line.__table__.columns}
        if line.allergen:
            ld["allergen_code"] = line.allergen.allergen_code
            ld["allergen_name"] = line.allergen.allergen_name
        lines.append(ld)
    d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
    d["lines"] = lines
    d["material_name"] = mat_name
    return d


# ── Nutrition Profile CRUD ────────────────────────────────────────────────────

async def get_nutrition_profile_for_material(db: AsyncSession, material_id: uuid.UUID) -> Optional[NutritionProfile]:
    r = await db.execute(
        select(NutritionProfile).where(
            and_(NutritionProfile.material_id == material_id, NutritionProfile.is_active == True)
        )
    )
    return r.scalar_one_or_none()


async def get_nutrition_profile_for_product(db: AsyncSession, product_id: uuid.UUID) -> Optional[NutritionProfile]:
    r = await db.execute(
        select(NutritionProfile).where(
            and_(NutritionProfile.product_id == product_id, NutritionProfile.is_active == True)
        )
    )
    return r.scalar_one_or_none()


async def create_nutrition_profile(db: AsyncSession, data: dict) -> NutritionProfile:
    lines_data = data.pop("lines", [])
    profile = NutritionProfile(**data)
    db.add(profile)
    await db.flush()
    for line_d in lines_data:
        db.add(NutritionProfileLine(profile_id=profile.id, **line_d))
    return profile


async def update_nutrition_line(db: AsyncSession, line_id: uuid.UUID, data: dict) -> Optional[NutritionProfileLine]:
    r = await db.execute(select(NutritionProfileLine).where(NutritionProfileLine.id == line_id))
    line = r.scalar_one_or_none()
    if not line:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(line, k, v)
    return line


async def add_nutrition_line(db: AsyncSession, profile_id: uuid.UUID, data: dict) -> NutritionProfileLine:
    line = NutritionProfileLine(profile_id=profile_id, **data)
    db.add(line)
    await db.flush()
    return line


async def list_nutrition_profiles(db: AsyncSession, entity_type: str = "material") -> List[dict]:
    if entity_type == "material":
        q = (
            select(NutritionProfile, Material.name.label("entity_name"))
            .join(Material, NutritionProfile.material_id == Material.id)
            .where(NutritionProfile.material_id.isnot(None))
        )
    else:
        q = (
            select(NutritionProfile, Product.name.label("entity_name"))
            .join(Product, NutritionProfile.product_id == Product.id)
            .where(NutritionProfile.product_id.isnot(None))
        )
    r = await db.execute(q.where(NutritionProfile.is_active == True).order_by("entity_name"))
    result = []
    for profile, ename in r.all():
        d = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
        d["entity_name"] = ename
        d["lines"] = [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in profile.lines]
        result.append(d)
    return result


# ── Allergen Roll-Up Engine ───────────────────────────────────────────────────

async def _get_material_allergens(db: AsyncSession, material_id: uuid.UUID) -> List[MaterialAllergenLine]:
    profile = await get_material_allergen_profile(db, material_id)
    if not profile:
        return []
    r = await db.execute(
        select(MaterialAllergenLine)
        .where(MaterialAllergenLine.profile_id == profile.id)
        .options()
    )
    lines = list(r.scalars())
    for line in lines:
        _ = line.allergen
    return lines


def _build_allergen_statement(contains: List[str], may_contain: List[str]) -> Tuple[str, str]:
    contains_stmt = ""
    may_contain_stmt = ""
    if contains:
        contains_stmt = "Contains: " + ", ".join(contains)
    if may_contain:
        may_contain_stmt = "May contain traces of: " + ", ".join(may_contain)
    return contains_stmt, may_contain_stmt


async def rollup_allergens_from_bom(db: AsyncSession, bom_id: uuid.UUID) -> dict:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom = bom_r.scalar_one_or_none()
    if not bom:
        return {}

    lines_r = await db.execute(
        select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id)
    )
    bom_lines = list(lines_r.scalars())

    contains_map: Dict[str, dict] = {}
    may_contain_map: Dict[str, dict] = {}
    free_from: List[str] = []
    ingredient_allergen_map: Dict[str, List[str]] = {}

    for bl in bom_lines:
        if bl.item_type != ItemLinkType.MATERIAL or not bl.item_id:
            if bl.child_bom_id:
                child_result = await rollup_allergens_from_bom(db, bl.child_bom_id)
                for a in child_result.get("contains", []):
                    contains_map[a["allergen_code"]] = a
                for a in child_result.get("may_contain", []):
                    if a["allergen_code"] not in contains_map:
                        may_contain_map[a["allergen_code"]] = a
            continue

        allergen_lines = await _get_material_allergens(db, bl.item_id)
        mat_allergens = []
        for al in allergen_lines:
            allergen = al.allergen
            if not allergen:
                continue
            entry = {
                "allergen_code": allergen.allergen_code,
                "allergen_name": allergen.allergen_name,
                "presence_type": al.presence_type,
                "declaration_required": al.declaration_required,
                "critical_flag": al.critical_flag,
                "source_materials": [bl.item_name or str(bl.item_id)],
            }
            mat_allergens.append(allergen.allergen_code)
            if al.presence_type == PresenceType.CONTAINS:
                if allergen.allergen_code in contains_map:
                    contains_map[allergen.allergen_code]["source_materials"].append(bl.item_name or str(bl.item_id))
                else:
                    contains_map[allergen.allergen_code] = entry.copy()
            elif al.presence_type in (PresenceType.MAY_CONTAIN, PresenceType.PRODUCED_IN_SAME_FACILITY):
                if allergen.allergen_code not in contains_map:
                    if allergen.allergen_code in may_contain_map:
                        may_contain_map[allergen.allergen_code]["source_materials"].append(bl.item_name or str(bl.item_id))
                    else:
                        may_contain_map[allergen.allergen_code] = entry.copy()
            elif al.presence_type == PresenceType.FREE_FROM:
                if allergen.allergen_name not in free_from:
                    free_from.append(allergen.allergen_name)

        if mat_allergens and bl.item_name:
            ingredient_allergen_map[bl.item_name] = mat_allergens

    declaration_required = [v for v in contains_map.values() if v.get("declaration_required")]
    cross_risk = CrossContactRisk.NONE
    if contains_map:
        cross_risk = CrossContactRisk.HIGH
    elif may_contain_map:
        cross_risk = CrossContactRisk.MEDIUM

    contains_list = list(contains_map.values())
    may_list = list(may_contain_map.values())
    contains_stmt, may_stmt = _build_allergen_statement(
        [v["allergen_name"] for v in contains_list],
        [v["allergen_name"] for v in may_list],
    )

    return {
        "product_id": str(bom.product_id) if bom.product_id else None,
        "bom_id": str(bom_id),
        "bom_version": bom.version_no,
        "contains": contains_list,
        "may_contain": may_list,
        "free_from": free_from,
        "declaration_required": declaration_required,
        "cross_contact_risk": cross_risk,
        "label_statement": contains_stmt,
        "may_contain_statement": may_stmt,
        "ingredient_allergen_map": ingredient_allergen_map,
    }


async def rollup_allergens_from_recipe(db: AsyncSession, recipe_id: uuid.UUID) -> dict:
    recipe_r = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = recipe_r.scalar_one_or_none()
    if not recipe:
        return {}

    items_r = await db.execute(select(RecipeItem).where(RecipeItem.recipe_id == recipe_id))
    items = list(items_r.scalars())

    contains_map: Dict[str, dict] = {}
    may_contain_map: Dict[str, dict] = {}
    ingredient_map: Dict[str, List[str]] = {}

    for item in items:
        if not item.material_id:
            continue
        allergen_lines = await _get_material_allergens(db, item.material_id)
        mat_r = await db.execute(select(Material.name).where(Material.id == item.material_id))
        mat_name = mat_r.scalar_one_or_none() or str(item.material_id)
        mat_allergens = []
        for al in allergen_lines:
            if not al.allergen:
                continue
            code = al.allergen.allergen_code
            mat_allergens.append(code)
            entry = {
                "allergen_code": code, "allergen_name": al.allergen.allergen_name,
                "presence_type": al.presence_type, "declaration_required": al.declaration_required,
                "critical_flag": al.critical_flag, "source_materials": [mat_name],
            }
            if al.presence_type == PresenceType.CONTAINS:
                contains_map.setdefault(code, entry)
                if mat_name not in contains_map[code]["source_materials"]:
                    contains_map[code]["source_materials"].append(mat_name)
            elif al.presence_type in (PresenceType.MAY_CONTAIN, PresenceType.PRODUCED_IN_SAME_FACILITY):
                if code not in contains_map:
                    may_contain_map.setdefault(code, entry)
        if mat_allergens:
            ingredient_map[mat_name] = mat_allergens

    contains_list = list(contains_map.values())
    may_list = list(may_contain_map.values())
    contains_stmt, may_stmt = _build_allergen_statement(
        [v["allergen_name"] for v in contains_list],
        [v["allergen_name"] for v in may_list],
    )
    cross_risk = CrossContactRisk.HIGH if contains_map else (CrossContactRisk.MEDIUM if may_contain_map else CrossContactRisk.NONE)

    return {
        "product_id": str(recipe.product_id),
        "bom_id": None, "bom_version": recipe.version,
        "contains": contains_list, "may_contain": may_list, "free_from": [],
        "declaration_required": [v for v in contains_list if v.get("declaration_required")],
        "cross_contact_risk": cross_risk,
        "label_statement": contains_stmt, "may_contain_statement": may_stmt,
        "ingredient_allergen_map": ingredient_map,
    }


async def save_product_allergen_summary(
    db: AsyncSession, product_id: uuid.UUID, rollup: dict
) -> ProductAllergenSummary:
    r = await db.execute(
        select(ProductAllergenSummary).where(ProductAllergenSummary.product_id == product_id)
    )
    summary = r.scalar_one_or_none()
    contains_codes = [v["allergen_code"] for v in rollup.get("contains", [])]
    may_codes = [v["allergen_code"] for v in rollup.get("may_contain", [])]
    decl = [{"code": v["allergen_code"], "name": v["allergen_name"]} for v in rollup.get("declaration_required", [])]

    if summary:
        summary.contains_allergens = contains_codes
        summary.may_contain_allergens = may_codes
        summary.declaration_required = decl
        summary.cross_contact_risk = rollup.get("cross_contact_risk", CrossContactRisk.NONE)
        summary.label_statement = rollup.get("label_statement", "")
        summary.may_contain_statement = rollup.get("may_contain_statement", "")
        summary.last_calculated_at = datetime.now(timezone.utc)
        summary.bom_id = uuid.UUID(rollup["bom_id"]) if rollup.get("bom_id") else None
        summary.bom_version = rollup.get("bom_version")
        summary.is_stale = False
    else:
        summary = ProductAllergenSummary(
            product_id=product_id,
            contains_allergens=contains_codes,
            may_contain_allergens=may_codes,
            declaration_required=decl,
            cross_contact_risk=rollup.get("cross_contact_risk", CrossContactRisk.NONE),
            label_statement=rollup.get("label_statement", ""),
            may_contain_statement=rollup.get("may_contain_statement", ""),
            last_calculated_at=datetime.now(timezone.utc),
            bom_id=uuid.UUID(rollup["bom_id"]) if rollup.get("bom_id") else None,
            bom_version=rollup.get("bom_version"),
            calculation_source=rollup.get("source", "BOM"),
        )
        db.add(summary)
    await db.flush()
    return summary


# ── Nutrition Roll-Up Engine ──────────────────────────────────────────────────

def _D(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


async def rollup_nutrition_from_bom(db: AsyncSession, bom_id: uuid.UUID, serving_size_g: Optional[Decimal] = None) -> dict:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom = bom_r.scalar_one_or_none()
    if not bom:
        return {}

    lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id))
    bom_lines = list(lines_r.scalars())

    base_qty = _D(bom.base_qty) if bom.base_qty else Decimal("1000")
    nutrient_totals: Dict[str, Dict] = {}
    missing_profiles: List[str] = []
    covered_qty = Decimal("0")

    for bl in bom_lines:
        if bl.item_type != ItemLinkType.MATERIAL or not bl.item_id:
            continue
        req_qty = _D(bl.required_qty or 0)
        loss_pct = _D(getattr(bl, "loss_percentage", 0) or 0)
        net_qty = req_qty * (1 - loss_pct / 100)
        weight_factor = net_qty / base_qty if base_qty else Decimal("0")
        covered_qty += net_qty

        profile = await get_nutrition_profile_for_material(db, bl.item_id)
        if not profile:
            mat_name = bl.item_name or str(bl.item_id)
            if mat_name not in missing_profiles:
                missing_profiles.append(mat_name)
            continue

        for line in profile.lines:
            code = line.nutrient_code
            val_per_100 = _D(line.value)
            contribution = val_per_100 * weight_factor * 100
            if code not in nutrient_totals:
                nutrient_totals[code] = {"name": line.nutrient_name, "unit": line.unit, "total": Decimal("0")}
            nutrient_totals[code]["total"] += contribution

    completeness = (covered_qty / base_qty * 100) if base_qty else Decimal("0")

    per_100g: Dict[str, Any] = {}
    per_serving: Dict[str, Any] = {}
    nutrients = []

    for code, data in nutrient_totals.items():
        val = data["total"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        per_100g[code] = {"value": float(val), "unit": data["unit"], "name": data["name"]}
        srv_val = None
        if serving_size_g:
            srv_val = (val * serving_size_g / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            per_serving[code] = {"value": float(srv_val), "unit": data["unit"], "name": data["name"]}
        nutrients.append({
            "nutrient_code": code, "nutrient_name": data["name"], "unit": data["unit"],
            "value_per_100g": val, "value_per_serving": srv_val,
        })

    return {
        "product_id": str(bom.product_id) if bom.product_id else None,
        "bom_id": str(bom_id), "bom_version": bom.version_no,
        "serving_size_g": serving_size_g,
        "servings_per_pack": None,
        "nutrients": nutrients, "per_100g": per_100g, "per_serving": per_serving, "per_unit": {},
        "completeness_pct": completeness.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
        "missing_profiles": missing_profiles,
    }


async def rollup_nutrition_from_recipe(db: AsyncSession, recipe_id: uuid.UUID, serving_size_g: Optional[Decimal] = None) -> dict:
    recipe_r = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = recipe_r.scalar_one_or_none()
    if not recipe:
        return {}

    items_r = await db.execute(select(RecipeItem).where(RecipeItem.recipe_id == recipe_id))
    items = list(items_r.scalars())

    nutrient_totals: Dict[str, Dict] = {}
    missing_profiles: List[str] = []
    total_qty = Decimal("0")
    covered_qty = Decimal("0")

    for item in items:
        qty = _D(item.quantity)
        loss = _D(item.loss_percentage or 0)
        net = qty * (1 - loss / 100)
        total_qty += net

    if total_qty == 0:
        total_qty = Decimal("1000")

    for item in items:
        qty = _D(item.quantity)
        loss = _D(item.loss_percentage or 0)
        net = qty * (1 - loss / 100)
        weight_factor = net / total_qty

        profile = await get_nutrition_profile_for_material(db, item.material_id)
        if not profile:
            mat_r = await db.execute(select(Material.name).where(Material.id == item.material_id))
            mat_name = mat_r.scalar_one_or_none() or str(item.material_id)
            if mat_name not in missing_profiles:
                missing_profiles.append(mat_name)
            continue
        covered_qty += net
        for line in profile.lines:
            code = line.nutrient_code
            val_per_100 = _D(line.value)
            contribution = val_per_100 * weight_factor * 100
            if code not in nutrient_totals:
                nutrient_totals[code] = {"name": line.nutrient_name, "unit": line.unit, "total": Decimal("0")}
            nutrient_totals[code]["total"] += contribution

    completeness = (covered_qty / total_qty * 100) if total_qty else Decimal("0")
    per_100g: Dict[str, Any] = {}
    per_serving: Dict[str, Any] = {}
    nutrients = []
    for code, data in nutrient_totals.items():
        val = data["total"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        per_100g[code] = {"value": float(val), "unit": data["unit"], "name": data["name"]}
        srv_val = None
        if serving_size_g:
            srv_val = (val * serving_size_g / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            per_serving[code] = {"value": float(srv_val), "unit": data["unit"], "name": data["name"]}
        nutrients.append({
            "nutrient_code": code, "nutrient_name": data["name"], "unit": data["unit"],
            "value_per_100g": val, "value_per_serving": srv_val,
        })

    return {
        "product_id": str(recipe.product_id),
        "bom_id": None, "bom_version": recipe.version,
        "serving_size_g": serving_size_g, "servings_per_pack": None,
        "nutrients": nutrients, "per_100g": per_100g, "per_serving": per_serving, "per_unit": {},
        "completeness_pct": completeness.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
        "missing_profiles": missing_profiles,
    }


async def save_product_nutrition_summary(
    db: AsyncSession, product_id: uuid.UUID, rollup: dict
) -> ProductNutritionSummary:
    r = await db.execute(
        select(ProductNutritionSummary).where(ProductNutritionSummary.product_id == product_id)
    )
    summary = r.scalar_one_or_none()
    if summary:
        summary.nutrition_per_100g = rollup.get("per_100g")
        summary.nutrition_per_serving = rollup.get("per_serving")
        summary.bom_id = uuid.UUID(rollup["bom_id"]) if rollup.get("bom_id") else None
        summary.bom_version = rollup.get("bom_version")
        summary.last_calculated_at = datetime.now(timezone.utc)
        summary.is_stale = False
    else:
        summary = ProductNutritionSummary(
            product_id=product_id,
            nutrition_per_100g=rollup.get("per_100g"),
            nutrition_per_serving=rollup.get("per_serving"),
            bom_id=uuid.UUID(rollup["bom_id"]) if rollup.get("bom_id") else None,
            bom_version=rollup.get("bom_version"),
            last_calculated_at=datetime.now(timezone.utc),
            calculation_source=rollup.get("source", "BOM"),
        )
        db.add(summary)
    await db.flush()
    return summary


# ── Product Summary Getters ───────────────────────────────────────────────────

async def get_product_allergen_summary(db: AsyncSession, product_id: uuid.UUID) -> Optional[dict]:
    r = await db.execute(
        select(ProductAllergenSummary, Product.name.label("product_name"))
        .join(Product, ProductAllergenSummary.product_id == Product.id)
        .where(ProductAllergenSummary.product_id == product_id)
    )
    row = r.first()
    if not row:
        return None
    summary, pname = row
    d = {c.name: getattr(summary, c.name) for c in summary.__table__.columns}
    d["product_name"] = pname
    return d


async def get_product_nutrition_summary(db: AsyncSession, product_id: uuid.UUID) -> Optional[dict]:
    r = await db.execute(
        select(ProductNutritionSummary, Product.name.label("product_name"))
        .join(Product, ProductNutritionSummary.product_id == Product.id)
        .where(ProductNutritionSummary.product_id == product_id)
    )
    row = r.first()
    if not row:
        return None
    summary, pname = row
    d = {c.name: getattr(summary, c.name) for c in summary.__table__.columns}
    d["product_name"] = pname
    return d


async def list_product_allergen_summaries(db: AsyncSession) -> List[dict]:
    r = await db.execute(
        select(ProductAllergenSummary, Product.name.label("product_name"))
        .join(Product, ProductAllergenSummary.product_id == Product.id)
        .order_by(Product.name)
    )
    result = []
    for summary, pname in r.all():
        d = {c.name: getattr(summary, c.name) for c in summary.__table__.columns}
        d["product_name"] = pname
        result.append(d)
    return result


async def list_product_nutrition_summaries(db: AsyncSession) -> List[dict]:
    r = await db.execute(
        select(ProductNutritionSummary, Product.name.label("product_name"))
        .join(Product, ProductNutritionSummary.product_id == Product.id)
        .order_by(Product.name)
    )
    result = []
    for summary, pname in r.all():
        d = {c.name: getattr(summary, c.name) for c in summary.__table__.columns}
        d["product_name"] = pname
        result.append(d)
    return result


# ── Allergen Change Detection ─────────────────────────────────────────────────

async def compare_bom_allergens(
    db: AsyncSession, bom_id_a: uuid.UUID, bom_id_b: uuid.UUID
) -> dict:
    rollup_a = await rollup_allergens_from_bom(db, bom_id_a)
    rollup_b = await rollup_allergens_from_bom(db, bom_id_b)

    bom_a_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_a))
    bom_b_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_b))
    bom_a = bom_a_r.scalar_one_or_none()
    bom_b = bom_b_r.scalar_one_or_none()

    set_a = {v["allergen_code"] for v in rollup_a.get("contains", [])} | {v["allergen_code"] for v in rollup_a.get("may_contain", [])}
    set_b = {v["allergen_code"] for v in rollup_b.get("contains", [])} | {v["allergen_code"] for v in rollup_b.get("may_contain", [])}

    added = list(set_b - set_a)
    removed = list(set_a - set_b)

    contains_a = {v["allergen_code"]: v["presence_type"] for v in rollup_a.get("contains", [])}
    may_a = {v["allergen_code"]: v["presence_type"] for v in rollup_a.get("may_contain", [])}
    map_a = {**contains_a, **may_a}
    contains_b = {v["allergen_code"]: v["presence_type"] for v in rollup_b.get("contains", [])}
    may_b = {v["allergen_code"]: v["presence_type"] for v in rollup_b.get("may_contain", [])}
    map_b = {**contains_b, **may_b}

    changed = []
    for code in set_a & set_b:
        if map_a.get(code) != map_b.get(code):
            changed.append({"allergen_code": code, "from": map_a.get(code), "to": map_b.get(code)})

    decl_a = {v["allergen_code"] for v in rollup_a.get("declaration_required", [])}
    decl_b = {v["allergen_code"] for v in rollup_b.get("declaration_required", [])}
    decl_changes = []
    for code in (decl_a | decl_b) - (decl_a & decl_b):
        decl_changes.append({"allergen_code": code, "declared_in_a": code in decl_a, "declared_in_b": code in decl_b})

    return {
        "bom_id_a": bom_id_a,
        "bom_id_b": bom_id_b,
        "version_a": bom_a.version_no if bom_a else "?",
        "version_b": bom_b.version_no if bom_b else "?",
        "added_allergens": added,
        "removed_allergens": removed,
        "changed_presence": changed,
        "declaration_changes": decl_changes,
        "is_identical": not added and not removed and not changed and not decl_changes,
    }


async def compare_bom_nutrition(
    db: AsyncSession, bom_id_a: uuid.UUID, bom_id_b: uuid.UUID, threshold_pct: Decimal = Decimal("10")
) -> dict:
    rollup_a = await rollup_nutrition_from_bom(db, bom_id_a)
    rollup_b = await rollup_nutrition_from_bom(db, bom_id_b)
    bom_a_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_a))
    bom_b_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_b))
    bom_a = bom_a_r.scalar_one_or_none()
    bom_b = bom_b_r.scalar_one_or_none()

    per_a = rollup_a.get("per_100g", {})
    per_b = rollup_b.get("per_100g", {})
    all_codes = set(per_a.keys()) | set(per_b.keys())
    changed = []
    is_significant = False
    for code in all_codes:
        val_a = Decimal(str(per_a.get(code, {}).get("value", 0)))
        val_b = Decimal(str(per_b.get(code, {}).get("value", 0)))
        if val_a == 0 and val_b == 0:
            continue
        ref = val_a if val_a != 0 else val_b
        diff_pct = abs(val_b - val_a) / ref * 100 if ref else Decimal("0")
        changed.append({
            "nutrient_code": code,
            "name": per_b.get(code, per_a.get(code, {})).get("name", code),
            "value_a": float(val_a),
            "value_b": float(val_b),
            "change_pct": float(diff_pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
        })
        if diff_pct >= threshold_pct:
            is_significant = True

    changed.sort(key=lambda x: -abs(x["change_pct"]))
    return {
        "bom_id_a": bom_id_a, "bom_id_b": bom_id_b,
        "version_a": bom_a.version_no if bom_a else "?",
        "version_b": bom_b.version_no if bom_b else "?",
        "changed_nutrients": changed,
        "is_significant_change": is_significant,
        "significance_threshold_pct": threshold_pct,
    }


# ── Allergen Change Log ───────────────────────────────────────────────────────

async def list_change_logs(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
    review_pending: Optional[bool] = None,
    limit: int = 100,
) -> List[dict]:
    q = (
        select(AllergenChangeLog, Product.name.label("product_name"), AllergenMaster.allergen_name)
        .outerjoin(Product, AllergenChangeLog.product_id == Product.id)
        .outerjoin(AllergenMaster, AllergenChangeLog.allergen_id == AllergenMaster.id)
    )
    if product_id:
        q = q.where(AllergenChangeLog.product_id == product_id)
    if review_pending is True:
        q = q.where(or_(AllergenChangeLog.label_review_done == False, AllergenChangeLog.qc_review_done == False))
    r = await db.execute(q.order_by(AllergenChangeLog.created_at.desc()).limit(limit))
    result = []
    for log, pname, aname in r.all():
        d = {c.name: getattr(log, c.name) for c in log.__table__.columns}
        d["product_name"] = pname
        d["allergen_name"] = aname
        result.append(d)
    return result


async def mark_review_done(db: AsyncSession, log_id: uuid.UUID, review_type: str) -> Optional[AllergenChangeLog]:
    r = await db.execute(select(AllergenChangeLog).where(AllergenChangeLog.id == log_id))
    log = r.scalar_one_or_none()
    if not log:
        return None
    if review_type == "label":
        log.label_review_done = True
    elif review_type == "qc":
        log.qc_review_done = True
    return log


# ── Serving Config ────────────────────────────────────────────────────────────

async def get_serving_config(db: AsyncSession, product_id: uuid.UUID) -> Optional[ProductServingConfig]:
    r = await db.execute(
        select(ProductServingConfig).where(ProductServingConfig.product_id == product_id)
    )
    return r.scalar_one_or_none()


async def upsert_serving_config(db: AsyncSession, product_id: uuid.UUID, data: dict) -> ProductServingConfig:
    existing = await get_serving_config(db, product_id)
    if existing:
        for k, v in data.items():
            if v is not None:
                setattr(existing, k, v)
        return existing
    cfg = ProductServingConfig(product_id=product_id, **data)
    db.add(cfg)
    await db.flush()
    return cfg


# ── Label Readiness ───────────────────────────────────────────────────────────

async def get_label_readiness(db: AsyncSession, product_id: uuid.UUID) -> dict:
    prod_r = await db.execute(select(Product.name).where(Product.id == product_id))
    prod_name = prod_r.scalar_one_or_none() or str(product_id)

    allergen_r = await db.execute(
        select(ProductAllergenSummary).where(ProductAllergenSummary.product_id == product_id)
    )
    allergen_summary = allergen_r.scalar_one_or_none()

    nutrition_r = await db.execute(
        select(ProductNutritionSummary).where(ProductNutritionSummary.product_id == product_id)
    )
    nutrition_summary = nutrition_r.scalar_one_or_none()

    serving_r = await db.execute(
        select(ProductServingConfig).where(ProductServingConfig.product_id == product_id)
    )
    serving_config = serving_r.scalar_one_or_none()

    open_logs_r = await db.execute(
        select(func.count()).select_from(AllergenChangeLog).where(
            and_(
                AllergenChangeLog.product_id == product_id,
                or_(AllergenChangeLog.label_review_done == False, AllergenChangeLog.qc_review_done == False),
            )
        )
    )
    open_logs = open_logs_r.scalar() or 0

    pending_label_r = await db.execute(
        select(func.count()).select_from(AllergenChangeLog).where(
            and_(AllergenChangeLog.product_id == product_id, AllergenChangeLog.label_review_done == False)
        )
    )
    pending_label = pending_label_r.scalar() or 0

    pending_qc_r = await db.execute(
        select(func.count()).select_from(AllergenChangeLog).where(
            and_(AllergenChangeLog.product_id == product_id, AllergenChangeLog.qc_review_done == False)
        )
    )
    pending_qc = pending_qc_r.scalar() or 0

    warnings = []
    score = 0

    if allergen_summary:
        score += 25
        if allergen_summary.is_stale:
            warnings.append("Allergen summary is stale — recalculate from BOM")
        else:
            score += 10
    else:
        warnings.append("Allergen summary not computed — run allergen roll-up")

    if nutrition_summary:
        score += 25
        if nutrition_summary.is_stale:
            warnings.append("Nutrition summary is stale — recalculate from BOM")
        else:
            score += 10
    else:
        warnings.append("Nutrition summary not computed — run nutrition roll-up")

    if serving_config:
        score += 15
    else:
        warnings.append("No serving size config — required for label declaration")

    if open_logs == 0:
        score += 15
    else:
        warnings.append(f"{open_logs} open allergen change logs requiring review")

    return {
        "product_id": product_id,
        "product_name": prod_name,
        "allergen_summary_complete": allergen_summary is not None,
        "allergen_summary_stale": allergen_summary.is_stale if allergen_summary else False,
        "nutrition_summary_complete": nutrition_summary is not None,
        "nutrition_summary_stale": nutrition_summary.is_stale if nutrition_summary else False,
        "serving_config_present": serving_config is not None,
        "open_change_logs": open_logs,
        "pending_label_reviews": pending_label,
        "pending_qc_reviews": pending_qc,
        "readiness_score": min(score, 100),
        "warnings": warnings,
        "last_checked": datetime.now(timezone.utc),
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    async def _count(model, *filters):
        q = select(func.count()).select_from(model)
        for f in filters:
            q = q.where(f)
        return (await db.execute(q)).scalar() or 0

    total_allergens = await _count(AllergenMaster, AllergenMaster.is_active == True)
    mat_profiles    = await _count(MaterialAllergenProfile)
    all_mat         = await _count(Material, Material.is_active == True)
    prod_allergen   = await _count(ProductAllergenSummary)
    prod_nutrition  = await _count(ProductNutritionSummary)
    stale_allergen  = await _count(ProductAllergenSummary, ProductAllergenSummary.is_stale == True)
    stale_nutrition = await _count(ProductNutritionSummary, ProductNutritionSummary.is_stale == True)
    open_logs       = await _count(AllergenChangeLog, or_(AllergenChangeLog.label_review_done == False, AllergenChangeLog.qc_review_done == False))
    pending_label   = await _count(AllergenChangeLog, AllergenChangeLog.label_review_done == False)
    ai_pending      = await _count(ANAIRecommendation, ANAIRecommendation.status == ANAIRecStatus.PENDING)
    high_risk       = await _count(MaterialAllergenProfile, MaterialAllergenProfile.cross_contact_risk_level.in_(["HIGH", "CRITICAL"]))

    return {
        "total_allergens": total_allergens,
        "materials_with_allergen_profiles": mat_profiles,
        "materials_missing_profiles": max(0, all_mat - mat_profiles),
        "products_with_allergen_summaries": prod_allergen,
        "products_with_nutrition_summaries": prod_nutrition,
        "stale_allergen_summaries": stale_allergen,
        "stale_nutrition_summaries": stale_nutrition,
        "open_change_logs": open_logs,
        "pending_label_reviews": pending_label,
        "ai_pending": ai_pending,
        "high_risk_cross_contact": high_risk,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_allergen_risk_monitor(db: AsyncSession) -> List[ANAIRecommendation]:
    recs: List[ANAIRecommendation] = []

    # Materials with CRITICAL cross-contact risk
    high_risk_r = await db.execute(
        select(MaterialAllergenProfile, Material.name.label("mname"))
        .join(Material, MaterialAllergenProfile.material_id == Material.id)
        .where(MaterialAllergenProfile.cross_contact_risk_level.in_(["HIGH", "CRITICAL"]))
    )
    high_risk = high_risk_r.all()
    if high_risk:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.ALLERGEN_RISK_MONITOR,
            title=f"{len(high_risk)} materials with HIGH/CRITICAL cross-contact risk",
            description=f"Materials: {', '.join(r[1] for r in high_risk[:5])}{'…' if len(high_risk) > 5 else ''}",
            recommendation="Review cleaning validation records and production sequencing for these materials. Ensure separation protocols and CCP controls are in place.",
            severity="HIGH",
            agent_metadata={"count": len(high_risk)},
        )
        db.add(rec)
        recs.append(rec)

    # Materials with no allergen profile
    all_mat_r = await db.execute(select(Material.id, Material.name))
    all_mats = all_mat_r.all()
    profiled_r = await db.execute(select(MaterialAllergenProfile.material_id))
    profiled_ids = {str(r[0]) for r in profiled_r.all()}
    unprofile = [(str(mid), mname) for mid, mname in all_mats if str(mid) not in profiled_ids]
    if unprofile:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.ALLERGEN_RISK_MONITOR,
            title=f"{len(unprofile)} materials missing allergen profiles",
            description=f"Materials without allergen data: {', '.join(n for _, n in unprofile[:5])}{'…' if len(unprofile) > 5 else ''}",
            recommendation="Collect supplier allergen declarations and complete allergen profiles for all raw materials to enable accurate roll-up.",
            severity="HIGH",
            agent_metadata={"count": len(unprofile)},
        )
        db.add(rec)
        recs.append(rec)

    # Products with stale allergen summaries
    stale_r = await db.execute(
        select(ProductAllergenSummary, Product.name.label("pname"))
        .join(Product, ProductAllergenSummary.product_id == Product.id)
        .where(ProductAllergenSummary.is_stale == True)
    )
    stale = stale_r.all()
    if stale:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.ALLERGEN_RISK_MONITOR,
            title=f"{len(stale)} products with stale allergen summaries",
            description=f"Products needing recalculation: {', '.join(r[1] for r in stale[:5])}",
            recommendation="Re-run allergen roll-up for these products. Label declarations may be outdated after BOM changes.",
            severity="CRITICAL",
            agent_metadata={"count": len(stale)},
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


async def run_nutrition_change_analyzer(db: AsyncSession) -> List[ANAIRecommendation]:
    recs: List[ANAIRecommendation] = []

    # Products with stale nutrition summaries
    stale_r = await db.execute(
        select(ProductNutritionSummary, Product.name.label("pname"))
        .join(Product, ProductNutritionSummary.product_id == Product.id)
        .where(ProductNutritionSummary.is_stale == True)
    )
    stale = stale_r.all()
    if stale:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.NUTRITION_CHANGE_ANALYZER,
            title=f"{len(stale)} products with stale nutrition panels",
            description=f"Products: {', '.join(r[1] for r in stale[:5])}",
            recommendation="Re-run nutrition roll-up. Declared nutrition values on labels may no longer match current formulation.",
            severity="HIGH",
            agent_metadata={"count": len(stale)},
        )
        db.add(rec)
        recs.append(rec)

    # Materials with no nutrition profile
    all_mat_r = await db.execute(select(Material.id, Material.name))
    all_mats = all_mat_r.all()
    nutri_r = await db.execute(select(NutritionProfile.material_id).where(NutritionProfile.material_id.isnot(None)))
    nutri_ids = {str(r[0]) for r in nutri_r.all()}
    missing_nutri = [(str(mid), mname) for mid, mname in all_mats if str(mid) not in nutri_ids]
    if missing_nutri:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.NUTRITION_CHANGE_ANALYZER,
            title=f"{len(missing_nutri)} materials missing nutrition profiles",
            description=f"Materials without nutrition data: {', '.join(n for _, n in missing_nutri[:5])}{'…' if len(missing_nutri) > 5 else ''}",
            recommendation="Add nutrition profiles (per 100g) for all raw materials used in formulations to enable accurate panel calculation.",
            severity="MEDIUM",
            agent_metadata={"count": len(missing_nutri)},
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


async def run_label_compliance_assistant(db: AsyncSession) -> List[ANAIRecommendation]:
    recs: List[ANAIRecommendation] = []

    # Products missing serving config
    all_prod_r = await db.execute(select(Product.id, Product.name).where(Product.is_active == True))
    all_prods = all_prod_r.all()
    serving_r = await db.execute(select(ProductServingConfig.product_id))
    serving_ids = {str(r[0]) for r in serving_r.all()}
    no_serving = [(str(pid), pname) for pid, pname in all_prods if str(pid) not in serving_ids]
    if no_serving:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.LABEL_COMPLIANCE_ASSISTANT,
            title=f"{len(no_serving)} products missing serving size configuration",
            description=f"Products: {', '.join(n for _, n in no_serving[:5])}{'…' if len(no_serving) > 5 else ''}",
            recommendation="Configure serving size and servings-per-pack for all finished goods to enable regulatory nutrition declaration.",
            severity="MEDIUM",
            agent_metadata={"count": len(no_serving)},
        )
        db.add(rec)
        recs.append(rec)

    # Open allergen change logs requiring label review
    open_label_r = await db.execute(
        select(func.count()).select_from(AllergenChangeLog).where(AllergenChangeLog.label_review_done == False)
    )
    open_label = open_label_r.scalar() or 0
    if open_label > 0:
        rec = ANAIRecommendation(
            agent_type=ANAIAgentType.LABEL_COMPLIANCE_ASSISTANT,
            title=f"{open_label} allergen change logs require label review",
            description="BOM or ingredient changes have introduced allergen differences that have not been reviewed for label impact.",
            recommendation="Review all open allergen change logs. Update product labels, packaging artwork, and regulatory submissions as needed.",
            severity="CRITICAL",
            agent_metadata={"open_label_reviews": open_label},
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


async def list_ai_recommendations(
    db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None
) -> List[ANAIRecommendation]:
    q = select(ANAIRecommendation)
    if agent_type:
        q = q.where(ANAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(ANAIRecommendation.status == status)
    r = await db.execute(q.order_by(ANAIRecommendation.created_at.desc()))
    return list(r.scalars())


async def review_ai_rec(db: AsyncSession, rec_id: uuid.UUID, status: str, reviewed_by: Optional[str]) -> Optional[ANAIRecommendation]:
    r = await db.execute(select(ANAIRecommendation).where(ANAIRecommendation.id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        return None
    rec.status = status
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.now(timezone.utc)
    return rec
