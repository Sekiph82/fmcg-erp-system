"""
BOM AI Agents — 3 agents for formula and compliance intelligence.

Agent 1: FORMULA_ANALYZER
  - Detect high-waste ingredients (wastage_pct > 5%)
  - Detect overly complex formulas (>20 lines)
  - Suggest consolidating similar raw material lines
  - Identify ingredients where substitutes available but cost impact not analyzed

Agent 2: PACKAGING_OPTIMIZER
  - Detect conversion profiles with total loss > 3%
  - Suggest batch size adjustments to reduce line startup losses
  - Flag packaging lines with high reject rates
  - Identify residual bulk opportunities

Agent 3: COMPLIANCE_CHECKER
  - Detect allergen-flagged lines with no labeling/compliance link
  - Detect BOMs not linked to quality spec
  - Detect released BOMs approaching effective_to date
  - Warn on incomplete nutrition data for nutrition-relevant lines
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMConversionProfile,
    BOMAIRec, BOMAgentType, BOMRecStatus, BOMLifecycle,
)


async def _add_rec(
    db: AsyncSession,
    bom_id: UUID,
    agent: BOMAgentType,
    title: str,
    explanation: str,
    impact: str,
    confidence: float,
    payload: dict = None,
) -> BOMAIRec:
    rec = BOMAIRec(
        bom_id=bom_id,
        agent_type=agent,
        title=title,
        explanation=explanation,
        impact_summary=impact,
        confidence_score=Decimal(str(round(confidence, 2))),
        payload=payload or {},
    )
    db.add(rec)
    return rec


async def run_formula_analyzer(db: AsyncSession, bom_id: UUID) -> List[BOMAIRec]:
    lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id))
    lines = lines_r.scalars().all()
    recs: List[BOMAIRec] = []

    # High-waste ingredients
    high_waste = [l for l in lines if float(l.wastage_pct) > 5.0]
    if high_waste:
        names = [l.item_name or "?" for l in high_waste[:5]]
        rec = await _add_rec(
            db, bom_id, BOMAgentType.FORMULA_ANALYZER,
            title=f"{len(high_waste)} ingredient(s) with >5% wastage — review process efficiency",
            explanation=(
                f"Ingredients {', '.join(names)} have wastage >5%. "
                f"Review mixing/handling process or supplier quality to reduce waste. "
                f"Total excess waste cost may be significant at scale."
            ),
            impact=f"Reducing wastage from {max(float(l.wastage_pct) for l in high_waste):.1f}% to 2% could reduce batch cost by an estimated {len(high_waste) * 1.5:.1f}%",
            confidence=0.82,
            payload={"high_waste_line_ids": [str(l.id) for l in high_waste]},
        )
        recs.append(rec)

    # Overly complex formula
    if len(lines) > 20:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.FORMULA_ANALYZER,
            title=f"Formula complexity: {len(lines)} lines — consider consolidation",
            explanation=(
                f"This BOM has {len(lines)} ingredient lines. "
                f"High component count increases planning complexity, procurement overhead, "
                f"and quality control requirements. Review if any similar-function ingredients can be consolidated."
            ),
            impact="Consolidating 20%+ of lines could reduce procurement SKU count and QC touchpoints",
            confidence=0.68,
        )
        recs.append(rec)

    # Lines with substitutes available but no cost analysis
    from app.models.bom import SubstitutionPolicy
    sub_no_cost = [
        l for l in lines
        if l.substitute_group_id and l.substitution_policy != SubstitutionPolicy.NO_SUB
    ]
    if sub_no_cost:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.FORMULA_ANALYZER,
            title=f"{len(sub_no_cost)} substitutable ingredient(s) — run cost impact analysis",
            explanation=(
                f"{len(sub_no_cost)} lines have approved substitutes but cost impact has not been reviewed. "
                f"If current materials are constrained, substitution cost implications should be pre-calculated."
            ),
            impact="Pre-calculating substitution costs enables faster shortage response without cost surprises",
            confidence=0.75,
        )
        recs.append(rec)

    return recs


async def run_packaging_optimizer(db: AsyncSession, bom_id: UUID) -> List[BOMAIRec]:
    # Load conversion profiles for this BOM's product
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom = bom_r.scalar_one_or_none()
    recs: List[BOMAIRec] = []
    if not bom:
        return recs

    profiles_r = await db.execute(
        select(BOMConversionProfile).where(
            BOMConversionProfile.linked_packaging_bom_id == bom_id,
            BOMConversionProfile.is_active == True,
        )
    )
    profiles = profiles_r.scalars().all()

    from app.models.bom import ComponentType
    lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id))
    lines = lines_r.scalars().all()

    pkg_lines = [l for l in lines if l.component_type == ComponentType.PACKAGING]

    for profile in profiles:
        total_loss_pct = (
            float(profile.startup_loss_pct) +
            float(profile.shutdown_loss_pct) +
            float(profile.packaging_reject_pct) +
            float(profile.residual_bulk_pct) +
            float(profile.line_purge_loss_pct)
        )
        if total_loss_pct > 3.0:
            rec = await _add_rec(
                db, bom_id, BOMAgentType.PACKAGING_OPTIMIZER,
                title=f"Conversion profile '{profile.profile_name}' has {total_loss_pct:.1f}% total loss",
                explanation=(
                    f"Total packaging conversion loss is {total_loss_pct:.1f}%, exceeding the 3% benchmark. "
                    f"Startup loss: {float(profile.startup_loss_pct):.1f}%, "
                    f"Reject rate: {float(profile.packaging_reject_pct):.1f}%, "
                    f"Residual bulk: {float(profile.residual_bulk_pct):.1f}%. "
                    f"Review line startup procedures and reject handling process."
                ),
                impact=f"Reducing loss to <3% could recover {(total_loss_pct - 3.0):.1f}% of bulk output per run",
                confidence=0.85,
                payload={"profile_id": str(profile.id)},
            )
            recs.append(rec)

    # High-wastage packaging lines
    high_pkg_waste = [l for l in pkg_lines if float(l.wastage_pct) > 3.0]
    if high_pkg_waste:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.PACKAGING_OPTIMIZER,
            title=f"{len(high_pkg_waste)} packaging material(s) with >3% wastage",
            explanation=(
                f"Packaging materials {', '.join(l.item_name or '?' for l in high_pkg_waste[:3])} "
                f"have higher-than-benchmark wastage. Review sealing, labeling, and handling procedures."
            ),
            impact="Packaging wastage reduction directly impacts COGS for high-volume SKUs",
            confidence=0.78,
        )
        recs.append(rec)

    return recs


async def run_compliance_checker(db: AsyncSession, bom_id: UUID) -> List[BOMAIRec]:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom = bom_r.scalar_one_or_none()
    recs: List[BOMAIRec] = []
    if not bom:
        return recs

    lines_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id))
    lines = lines_r.scalars().all()

    # Allergen-flagged but no compliance profile linked
    allergen_lines = [l for l in lines if l.allergen_flag]
    if allergen_lines and not bom.linked_compliance_profile_id:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.COMPLIANCE_CHECKER,
            title=f"{len(allergen_lines)} allergen-containing ingredient(s) — compliance profile not linked",
            explanation=(
                f"This BOM contains {len(allergen_lines)} allergen-flagged ingredient(s) but has no "
                f"compliance profile linked. Labeling declarations may be incomplete or non-compliant."
            ),
            impact="Missing allergen declarations can result in regulatory penalties and product recalls",
            confidence=0.95,
            payload={"allergen_line_ids": [str(l.id) for l in allergen_lines]},
        )
        recs.append(rec)

    # Released BOM approaching effective_to date
    today = date.today()
    if bom.lifecycle == BOMLifecycle.RELEASED and bom.effective_to:
        days_remaining = (bom.effective_to - today).days
        if 0 < days_remaining <= 30:
            rec = await _add_rec(
                db, bom_id, BOMAgentType.COMPLIANCE_CHECKER,
                title=f"Released BOM expires in {days_remaining} day(s) — prepare revision",
                explanation=(
                    f"BOM {bom.bom_code} has effective_to = {bom.effective_to}. "
                    f"A new version should be prepared and approved before expiry to avoid production disruption."
                ),
                impact="Expired BOM with no successor may block production order creation",
                confidence=0.90,
            )
            recs.append(rec)

    # Missing QC spec linkage for a released BOM
    if bom.lifecycle == BOMLifecycle.RELEASED and not bom.linked_quality_spec_id:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.COMPLIANCE_CHECKER,
            title="Released BOM has no quality specification linked",
            explanation=(
                f"BOM {bom.bom_code} is released but has no quality spec linked. "
                f"In-process and final QC checks may be undefined, creating audit and compliance risk."
            ),
            impact="Without QC spec linkage, QC inspection checklists cannot be auto-generated from this BOM",
            confidence=0.88,
        )
        recs.append(rec)

    # Nutrition-relevant lines without nutrition data
    nutrition_lines = [l for l in lines if l.nutrition_relevant and not l.nutrition_data]
    if nutrition_lines:
        rec = await _add_rec(
            db, bom_id, BOMAgentType.COMPLIANCE_CHECKER,
            title=f"{len(nutrition_lines)} nutrition-relevant ingredient(s) missing nutritional data",
            explanation=(
                f"{len(nutrition_lines)} lines are flagged as nutrition-relevant but have no nutritional data entered. "
                f"The per-100g nutrition roll-up will be incomplete or inaccurate."
            ),
            impact="Incomplete nutrition data prevents accurate label generation and regulatory compliance",
            confidence=0.80,
        )
        recs.append(rec)

    return recs


async def run_all_bom_ai(db: AsyncSession, bom_id: UUID) -> dict:
    await db.execute(delete(BOMAIRec).where(BOMAIRec.bom_id == bom_id))
    await db.flush()

    fa = await run_formula_analyzer(db, bom_id)
    po = await run_packaging_optimizer(db, bom_id)
    cc = await run_compliance_checker(db, bom_id)

    await db.flush()
    return {
        "formula_analyzer": len(fa),
        "packaging_optimizer": len(po),
        "compliance_checker": len(cc),
        "total": len(fa) + len(po) + len(cc),
    }
