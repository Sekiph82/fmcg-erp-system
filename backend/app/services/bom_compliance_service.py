"""Allergen roll-up, nutrition roll-up, and compliance summary."""
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import AdvancedBOM, AdvancedBOMLine, ComponentType
from app.schemas.bom import ComplianceSummary


ALLERGENS = [
    "dairy", "soy", "nuts", "gluten", "eggs",
    "sesame", "sulfites", "shellfish", "fish", "other",
]

NUTRITION_KEYS = [
    "calories", "protein", "fat", "saturated_fat",
    "carbohydrates", "sugars", "fiber", "sodium",
]


async def compute_compliance_summary(db: AsyncSession, bom_id: UUID) -> ComplianceSummary:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom: AdvancedBOM = bom_r.scalar_one_or_none()
    if not bom:
        raise ValueError("BOM not found")

    lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id))
    lines = lines_r.scalars().all()

    # ── Allergen roll-up ──────────────────────────────────────────────────────
    allergen_flags: Dict[str, bool] = {a: False for a in ALLERGENS}
    cross_contact_risks: List[str] = []
    critical_components: List[str] = []
    warnings: List[str] = []

    for line in lines:
        if line.allergen_flag and line.allergen_types:
            for a in line.allergen_types:
                key = a.lower()
                if key in allergen_flags:
                    allergen_flags[key] = True

        # Cross-contact: line has allergen but is not the main ingredient
        if line.allergen_flag and line.component_type not in (ComponentType.RAW, ComponentType.INTERMEDIATE):
            cross_contact_risks.append(line.item_name or "Unknown component")

        if line.critical_component:
            critical_components.append(line.item_name or "Unknown")

    # ── Nutrition roll-up ─────────────────────────────────────────────────────
    nutrition_per_100g: Optional[Dict[str, float]] = None
    total_qty = sum(float(l.required_qty) for l in lines if l.nutrition_relevant)

    if total_qty > 0:
        agg: Dict[str, float] = {k: 0.0 for k in NUTRITION_KEYS}
        for line in lines:
            if not line.nutrition_relevant or not line.nutrition_data:
                continue
            share = float(line.required_qty) / total_qty
            for key in NUTRITION_KEYS:
                if key in line.nutrition_data:
                    agg[key] += line.nutrition_data[key] * share
        nutrition_per_100g = {k: round(v, 2) for k, v in agg.items() if v > 0}

    # ── Warnings ─────────────────────────────────────────────────────────────
    present_allergens = [a for a, v in allergen_flags.items() if v]
    if present_allergens:
        warnings.append(f"Product contains allergens: {', '.join(present_allergens)}")

    if cross_contact_risks:
        warnings.append(f"Cross-contact risk from: {', '.join(cross_contact_risks[:3])}")

    if not lines:
        warnings.append("BOM has no lines defined — compliance cannot be determined")

    # Persist to BOM header
    bom.allergen_flags = allergen_flags
    if nutrition_per_100g:
        bom.nutrition_per_100g = nutrition_per_100g
    await db.flush()

    return ComplianceSummary(
        bom_id=str(bom.id),
        bom_code=bom.bom_code,
        allergen_flags=allergen_flags,
        cross_contact_risks=cross_contact_risks,
        critical_components=critical_components,
        nutrition_per_100g=nutrition_per_100g,
        warnings=warnings,
    )
