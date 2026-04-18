"""
MPS AI Service — two agents:

Agent 1: OPTIMIZER
  - Analyzes line sequence and campaign grouping efficiency
  - Suggests reordering, batch merges, campaign consolidation
  - Confidence based on potential hours saved

Agent 2: RISK PREDICTOR
  - Flags lines that are overloaded (capacity risk)
  - Flags lines where material shortages exist (from MRP)
  - Flags lines near deadline with low priority
  - Predicts late orders and stockout risk
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSCampaign, MPSAIRecommendation,
    MPSAgentType, MPSRecType, MPSRecStatus,
    MPSFeasibilityStatus,
)
from app.models.mrp import MRPResult
from app.models.master import Product


def _D(v) -> Decimal:
    return Decimal("0") if v is None else Decimal(str(v))


# ── Agent 1: Optimizer ────────────────────────────────────────────────────────

async def run_optimizer_agent(db: AsyncSession, mps_id: uuid.UUID) -> List[MPSAIRecommendation]:
    lines_q = await db.execute(
        select(MPSLine)
        .where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.priority_score.desc())
    )
    lines = list(lines_q.scalars().all())

    if not lines:
        return []

    recs: List[MPSAIRecommendation] = []

    # ── 1. Sequence optimization ───────────────────────────────────────────────
    # Find lines with high priority but late planned_start relative to period_start
    late_start_lines = [
        l for l in lines
        if l.planned_start_date
        and l.period_start
        and l.planned_start_date > l.period_start
        and float(l.priority_score) > 70
        and not l.is_locked
    ]
    if late_start_lines:
        ids = [str(l.id) for l in late_start_lines[:5]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.OPTIMIZER,
            rec_type=MPSRecType.SEQUENCE,
            affected_line_ids=ids,
            recommendation=(
                f"Move {len(late_start_lines)} high-priority line(s) earlier in the schedule. "
                f"These lines have priority > 70 but start after their demand window opens, "
                f"increasing late-delivery risk. Recommended: advance start dates to align with period_start."
            ),
            impact_summary=f"Reduces late-start exposure on {len(late_start_lines)} line(s)",
            confidence_score=Decimal("78"),
        )
        db.add(rec)
        recs.append(rec)

    # ── 2. Batch merge suggestion ──────────────────────────────────────────────
    # Lines with very small batches (< 10% of capacity) on same WC same week
    from collections import defaultdict
    wc_week_lines: Dict[tuple, List[MPSLine]] = defaultdict(list)
    for l in lines:
        if l.work_center_id and l.planned_start_date:
            week_key = (
                l.work_center_id,
                l.planned_start_date.isocalendar()[0],
                l.planned_start_date.isocalendar()[1],
            )
            wc_week_lines[week_key].append(l)

    merge_candidates = []
    for key, wk_lines in wc_week_lines.items():
        small = [l for l in wk_lines if float(l.planned_production_qty or 0) < 500 and not l.is_locked]
        if len(small) >= 2:
            merge_candidates.extend(small)

    if merge_candidates:
        ids = [str(l.id) for l in merge_candidates[:6]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.OPTIMIZER,
            rec_type=MPSRecType.MERGE,
            affected_line_ids=ids,
            recommendation=(
                f"Merge {len(merge_candidates)} small-batch lines on the same work center "
                f"in the same week. Small batches (< 500 units) on one line create excessive "
                f"setup overhead. Merging reduces total changeover by an estimated "
                f"{len(merge_candidates) - len(set(l.work_center_id for l in merge_candidates))} setups."
            ),
            impact_summary=f"Reduces setup overhead on {len(merge_candidates)} small-batch lines",
            confidence_score=Decimal("72"),
        )
        db.add(rec)
        recs.append(rec)

    # ── 3. Campaign consolidation ─────────────────────────────────────────────
    camps_q = await db.execute(
        select(MPSCampaign)
        .where(MPSCampaign.mps_id == mps_id)
        .order_by(MPSCampaign.sequence_order)
    )
    campaigns = list(camps_q.scalars().all())

    # Campaigns with only 1 SKU (no grouping benefit) that share WC with another
    solo_camps = [c for c in campaigns if c.sku_count == 1]
    if len(solo_camps) >= 2:
        ids = [str(c.id) for c in solo_camps[:4]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.OPTIMIZER,
            rec_type=MPSRecType.CAMPAIGN,
            affected_line_ids=ids,
            recommendation=(
                f"{len(solo_camps)} campaigns contain only 1 SKU — no changeover savings. "
                f"Review whether any of these single-SKU campaigns can be consolidated into "
                f"adjacent campaigns with compatible base formulas to reduce total campaign switches."
            ),
            impact_summary=f"Potential to consolidate {len(solo_camps)} single-SKU campaigns",
            confidence_score=Decimal("65"),
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


# ── Agent 2: Risk Predictor ───────────────────────────────────────────────────

async def run_risk_predictor_agent(db: AsyncSession, mps_id: uuid.UUID) -> List[MPSAIRecommendation]:
    lines_q = await db.execute(
        select(MPSLine)
        .where(MPSLine.mps_id == mps_id)
    )
    lines = list(lines_q.scalars().all())

    if not lines:
        return []

    recs: List[MPSAIRecommendation] = []
    today = date.today()

    # ── 1. Overload risk ──────────────────────────────────────────────────────
    overloaded = [l for l in lines if l.feasibility_status == MPSFeasibilityStatus.OVERLOADED]
    if overloaded:
        worst = sorted(overloaded, key=lambda l: float(l.overload_hours or 0), reverse=True)[:5]
        ids = [str(l.id) for l in worst]
        total_overload = sum(float(l.overload_hours or 0) for l in overloaded)
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.RISK_PREDICTOR,
            rec_type=MPSRecType.CAPACITY,
            affected_line_ids=ids,
            recommendation=(
                f"CAPACITY RISK: {len(overloaded)} line(s) are overloaded by a total of "
                f"{total_overload:.1f} hours. The top affected lines are scheduled beyond "
                f"available work center hours. Recommended actions: shift dates, split batches, "
                f"add overtime shifts, or move to alternate work centers."
            ),
            impact_summary=f"{len(overloaded)} lines at capacity risk, {total_overload:.1f} total overload hours",
            confidence_score=Decimal("95"),
        )
        db.add(rec)
        recs.append(rec)

    # ── 2. Late delivery risk ─────────────────────────────────────────────────
    late_risk = [
        l for l in lines
        if l.period_end
        and l.planned_end_date
        and l.planned_end_date > l.period_end
        and l.feasibility_status not in (MPSFeasibilityStatus.INFEASIBLE, MPSFeasibilityStatus.ON_HOLD)
    ]
    if late_risk:
        ids = [str(l.id) for l in late_risk[:6]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.RISK_PREDICTOR,
            rec_type=MPSRecType.RISK_ALERT,
            affected_line_ids=ids,
            recommendation=(
                f"LATE DELIVERY RISK: {len(late_risk)} line(s) are scheduled to complete after "
                f"their demand period ends. This will result in stockouts or missed customer orders. "
                f"Immediate action: expedite scheduling, add capacity, or negotiate delivery dates."
            ),
            impact_summary=f"{len(late_risk)} lines will miss their demand window",
            confidence_score=Decimal("90"),
        )
        db.add(rec)
        recs.append(rec)

    # ── 3. Material shortage risk (from MRP linkage) ──────────────────────────
    mrp_ids = [l.mrp_result_id for l in lines if l.mrp_result_id]
    shortage_lines = []
    if mrp_ids:
        mrp_q = await db.execute(
            select(MRPResult).where(
                MRPResult.id.in_(mrp_ids),
                MRPResult.shortage_flag == True,
            )
        )
        shortage_mrp_ids = {r.id for r in mrp_q.scalars().all()}
        shortage_lines = [l for l in lines if l.mrp_result_id in shortage_mrp_ids]

    if shortage_lines:
        ids = [str(l.id) for l in shortage_lines[:6]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.RISK_PREDICTOR,
            rec_type=MPSRecType.RISK_ALERT,
            affected_line_ids=ids,
            recommendation=(
                f"MATERIAL SHORTAGE RISK: {len(shortage_lines)} MPS line(s) are linked to MRP results "
                f"flagged with material shortages. These production orders may be blocked at execution "
                f"due to insufficient raw materials. Trigger purchase requisitions immediately via MRP → "
                f"Procurement workflow."
            ),
            impact_summary=f"{len(shortage_lines)} lines face raw material shortages",
            confidence_score=Decimal("88"),
        )
        db.add(rec)
        recs.append(rec)

    # ── 4. Deadline urgency: lines with period_end within 7 days and PENDING ──
    urgent = [
        l for l in lines
        if l.period_end
        and (l.period_end - today).days <= 7
        and l.feasibility_status == MPSFeasibilityStatus.PENDING
    ]
    if urgent:
        ids = [str(l.id) for l in urgent[:6]]
        rec = MPSAIRecommendation(
            mps_id=mps_id,
            agent_type=MPSAgentType.RISK_PREDICTOR,
            rec_type=MPSRecType.RISK_ALERT,
            affected_line_ids=ids,
            recommendation=(
                f"URGENT: {len(urgent)} line(s) have demand deadlines within 7 days but are still "
                f"in PENDING feasibility status — capacity scheduling has not been run or has not "
                f"resolved these lines. Run capacity scheduling and review immediately."
            ),
            impact_summary=f"{len(urgent)} lines due within 7 days still unscheduled",
            confidence_score=Decimal("92"),
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


# ── Run All + Review ──────────────────────────────────────────────────────────

async def run_all_ai_agents(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    optimizer_recs = await run_optimizer_agent(db, mps_id)
    risk_recs = await run_risk_predictor_agent(db, mps_id)
    return {
        "optimizer_recommendations": len(optimizer_recs),
        "risk_alerts": len(risk_recs),
        "total": len(optimizer_recs) + len(risk_recs),
    }


async def list_ai_recommendations(db: AsyncSession, mps_id: uuid.UUID):
    q = await db.execute(
        select(MPSAIRecommendation)
        .where(MPSAIRecommendation.mps_id == mps_id)
        .order_by(MPSAIRecommendation.confidence_score.desc())
    )
    return q.scalars().all()


async def review_recommendation(
    db: AsyncSession,
    rec_id: uuid.UUID,
    accept: bool,
    user_id: uuid.UUID,
) -> MPSAIRecommendation:
    q = await db.execute(select(MPSAIRecommendation).where(MPSAIRecommendation.id == rec_id))
    rec = q.scalar_one_or_none()
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = MPSRecStatus.ACCEPTED if accept else MPSRecStatus.REJECTED
    rec.reviewed_by_id = user_id
    rec.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return rec
