from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tpm import (
    TPMPlan, TPMPromotion, TPMBudgetLine, TPMExpectedPerf, TPMActualPerf,
    TPMClaim, TPMClaimLine, TPMAIRecommendation,
    TPMPlanStatus, TPMPromotionStatus, TPMClaimStatus,
    TPMAIAgentType, TPMAIRecStatus,
)
from app.schemas.tpm import (
    TPMPlanCreate, TPMPromotionCreate, TPMBudgetLineCreate,
    TPMExpectedPerfCreate, TPMActualPerfCreate,
    TPMClaimCreate, TPMClaimReviewRequest, TPMClaimSettleRequest,
    TPMAIRecAckRequest,
    TPMDashboard, BudgetVsActualRow, ROIRow, ClaimAgingRow,
)


# ── Plans ─────────────────────────────────────────────────────────────────────

async def get_plans(db: AsyncSession, status: Optional[str] = None, fiscal_year: Optional[int] = None):
    q = select(TPMPlan).options(selectinload(TPMPlan.promotions))
    if status:
        q = q.where(TPMPlan.status == status)
    if fiscal_year:
        q = q.where(TPMPlan.fiscal_year == fiscal_year)
    q = q.order_by(TPMPlan.fiscal_year.desc(), TPMPlan.plan_start_date)
    result = await db.execute(q)
    plans = result.scalars().all()
    out = []
    for p in plans:
        d = p.__dict__.copy()
        d["promotion_count"] = len(p.promotions)
        out.append(d)
    return out


async def create_plan(db: AsyncSession, data: TPMPlanCreate) -> TPMPlan:
    plan = TPMPlan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_plan(db: AsyncSession, plan_id: str) -> Optional[TPMPlan]:
    result = await db.execute(
        select(TPMPlan).where(TPMPlan.id == plan_id)
        .options(selectinload(TPMPlan.promotions))
    )
    return result.scalar_one_or_none()


async def approve_plan(db: AsyncSession, plan_id: str, approver_id: Optional[str] = None) -> TPMPlan:
    plan = await get_plan(db, plan_id)
    plan.status = TPMPlanStatus.APPROVED
    plan.approved_by = approver_id
    plan.total_approved_budget = plan.total_planned_budget
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan_status(db: AsyncSession, plan_id: str, status: TPMPlanStatus) -> TPMPlan:
    plan = await get_plan(db, plan_id)
    plan.status = status
    await db.commit()
    await db.refresh(plan)
    return plan


# ── Promotions ────────────────────────────────────────────────────────────────

async def get_promotions(
    db: AsyncSession,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    promotion_type: Optional[str] = None,
    channel_id: Optional[str] = None,
    brand_id: Optional[str] = None,
):
    q = (
        select(TPMPromotion)
        .options(
            selectinload(TPMPromotion.budget_lines),
            selectinload(TPMPromotion.expected_perf),
            selectinload(TPMPromotion.actual_perf),
        )
        .order_by(TPMPromotion.valid_from)
    )
    if status:
        q = q.where(TPMPromotion.status == status)
    if plan_id:
        q = q.where(TPMPromotion.tpm_plan_id == plan_id)
    if promotion_type:
        q = q.where(TPMPromotion.promotion_type == promotion_type)
    if channel_id:
        q = q.where(TPMPromotion.channel_id == channel_id)
    if brand_id:
        q = q.where(TPMPromotion.brand_id == brand_id)
    result = await db.execute(q)
    return result.scalars().all()


async def create_promotion(db: AsyncSession, data: TPMPromotionCreate) -> TPMPromotion:
    promo = TPMPromotion(**data.model_dump())
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


async def get_promotion(db: AsyncSession, promo_id: str) -> Optional[TPMPromotion]:
    result = await db.execute(
        select(TPMPromotion)
        .where(TPMPromotion.id == promo_id)
        .options(
            selectinload(TPMPromotion.budget_lines),
            selectinload(TPMPromotion.expected_perf),
            selectinload(TPMPromotion.actual_perf),
            selectinload(TPMPromotion.claims),
        )
    )
    return result.scalar_one_or_none()


async def approve_promotion(db: AsyncSession, promo_id: str, approver_id: Optional[str] = None) -> TPMPromotion:
    promo = await get_promotion(db, promo_id)
    promo.status = TPMPromotionStatus.APPROVED
    promo.approved_by = approver_id
    await db.commit()
    await db.refresh(promo)
    return promo


async def update_promotion_status(db: AsyncSession, promo_id: str, status: TPMPromotionStatus) -> TPMPromotion:
    promo = await get_promotion(db, promo_id)
    promo.status = status
    await db.commit()
    await db.refresh(promo)
    return promo


async def link_scheme(db: AsyncSession, promo_id: str, scheme_id: str) -> TPMPromotion:
    promo = await get_promotion(db, promo_id)
    promo.linked_scheme_id = scheme_id
    await db.commit()
    await db.refresh(promo)
    return promo


# ── Budget Lines ──────────────────────────────────────────────────────────────

async def add_budget_line(db: AsyncSession, promo_id: str, data: TPMBudgetLineCreate) -> TPMBudgetLine:
    line = TPMBudgetLine(
        tpm_promotion_id=promo_id,
        remaining_budget_amount=data.planned_spend_amount,
        **data.model_dump(),
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def update_actual_spend(db: AsyncSession, budget_line_id: str, actual_amount: Decimal):
    result = await db.execute(select(TPMBudgetLine).where(TPMBudgetLine.id == budget_line_id))
    line = result.scalar_one_or_none()
    if line:
        line.actual_spend_amount = actual_amount
        line.remaining_budget_amount = (line.approved_spend_amount or line.planned_spend_amount) - actual_amount
        await db.commit()


# ── Performance ───────────────────────────────────────────────────────────────

async def set_expected_perf(db: AsyncSession, promo_id: str, data: TPMExpectedPerfCreate) -> TPMExpectedPerf:
    result = await db.execute(select(TPMExpectedPerf).where(TPMExpectedPerf.tpm_promotion_id == promo_id))
    perf = result.scalar_one_or_none()
    if perf:
        for k, v in data.model_dump().items():
            setattr(perf, k, v)
    else:
        perf = TPMExpectedPerf(tpm_promotion_id=promo_id, **data.model_dump())
        db.add(perf)
    await db.commit()
    await db.refresh(perf)
    return perf


async def set_actual_perf(db: AsyncSession, promo_id: str, data: TPMActualPerfCreate) -> TPMActualPerf:
    result = await db.execute(select(TPMActualPerf).where(TPMActualPerf.tpm_promotion_id == promo_id))
    perf = result.scalar_one_or_none()

    exp_result = await db.execute(select(TPMExpectedPerf).where(TPMExpectedPerf.tpm_promotion_id == promo_id))
    exp = exp_result.scalar_one_or_none()

    # Compute derived metrics
    uplift_pct = Decimal("0")
    roi_pct    = Decimal("0")
    if exp and exp.baseline_volume and exp.baseline_volume > 0:
        uplift_pct = (data.actual_uplift_qty / exp.baseline_volume) * 100
    if data.actual_spend and data.actual_spend > 0:
        net_benefit = data.actual_revenue + data.actual_margin_impact
        roi_pct = ((net_benefit - data.actual_spend) / data.actual_spend) * 100

    payload = data.model_dump()
    payload["actual_uplift_pct"] = uplift_pct
    payload["actual_roi_pct"]    = roi_pct

    if perf:
        for k, v in payload.items():
            setattr(perf, k, v)
    else:
        perf = TPMActualPerf(tpm_promotion_id=promo_id, **payload)
        db.add(perf)
    await db.commit()
    await db.refresh(perf)
    return perf


# ── Claims ────────────────────────────────────────────────────────────────────

async def get_claims(db: AsyncSession, status: Optional[str] = None, promotion_id: Optional[str] = None):
    q = select(TPMClaim).options(selectinload(TPMClaim.claim_lines)).order_by(TPMClaim.claim_date.desc())
    if status:
        q = q.where(TPMClaim.status == status)
    if promotion_id:
        q = q.where(TPMClaim.tpm_promotion_id == promotion_id)
    result = await db.execute(q)
    return result.scalars().all()


async def create_claim(db: AsyncSession, data: TPMClaimCreate) -> TPMClaim:
    lines_data = data.claim_lines
    claim_dict = data.model_dump(exclude={"claim_lines"})

    # Generate claim_no
    count_result = await db.execute(select(func.count(TPMClaim.id)))
    count = count_result.scalar_one() or 0
    claim_dict["claim_no"] = f"CLM-{datetime.utcnow().year}-{count + 1:05d}"

    claim = TPMClaim(**claim_dict)
    db.add(claim)
    await db.flush()

    for ld in lines_data:
        line = TPMClaimLine(tpm_claim_id=claim.id, **ld.model_dump())
        db.add(line)

    await db.commit()
    await db.refresh(claim)
    return claim


async def get_claim(db: AsyncSession, claim_id: str) -> Optional[TPMClaim]:
    result = await db.execute(
        select(TPMClaim).where(TPMClaim.id == claim_id)
        .options(selectinload(TPMClaim.claim_lines))
    )
    return result.scalar_one_or_none()


async def review_claim(db: AsyncSession, claim_id: str, req: TPMClaimReviewRequest) -> TPMClaim:
    claim = await get_claim(db, claim_id)
    if req.approved:
        claim.status = TPMClaimStatus.APPROVED
        claim.approved_amount = req.approved_amount or claim.claimed_amount
        claim.rejected_amount = claim.claimed_amount - claim.approved_amount
    else:
        claim.status = TPMClaimStatus.REJECTED
        claim.rejected_amount = claim.claimed_amount
        claim.approved_amount = Decimal("0")
    if req.reviewer_notes:
        claim.reviewer_notes = req.reviewer_notes
    await db.commit()
    await db.refresh(claim)
    return claim


async def settle_claim(db: AsyncSession, claim_id: str, req: TPMClaimSettleRequest) -> TPMClaim:
    claim = await get_claim(db, claim_id)
    claim.settled_amount = (claim.settled_amount or Decimal("0")) + req.settle_amount
    if req.reference_document_no:
        claim.reference_document_no = req.reference_document_no
    if claim.settled_amount >= claim.approved_amount:
        claim.status = TPMClaimStatus.SETTLED
    else:
        claim.status = TPMClaimStatus.PARTIALLY_SETTLED
    await db.commit()
    await db.refresh(claim)
    return claim


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    active_plans = await db.execute(
        select(func.count(TPMPlan.id)).where(TPMPlan.status == TPMPlanStatus.ACTIVE)
    )
    active_promos = await db.execute(
        select(func.count(TPMPromotion.id)).where(TPMPromotion.status == TPMPromotionStatus.ACTIVE)
    )
    budget_agg = await db.execute(
        select(func.sum(TPMPlan.total_planned_budget), func.sum(TPMPlan.total_actual_spend))
    )
    budget_row = budget_agg.one()

    claim_agg = await db.execute(
        select(func.count(TPMClaim.id), func.sum(TPMClaim.claimed_amount))
        .where(TPMClaim.status.in_(["SUBMITTED", "UNDER_REVIEW", "APPROVED"]))
    )
    claim_row = claim_agg.one()

    pending_approvals = await db.execute(
        select(func.count(TPMPromotion.id)).where(TPMPromotion.status == TPMPromotionStatus.PROPOSED)
    )

    status_counts = await db.execute(
        select(TPMPromotion.status, func.count(TPMPromotion.id)).group_by(TPMPromotion.status)
    )

    top_promos_q = await db.execute(
        select(TPMPromotion)
        .options(selectinload(TPMPromotion.budget_lines), selectinload(TPMPromotion.actual_perf))
        .where(TPMPromotion.status.in_(["ACTIVE", "COMPLETED"]))
        .order_by(TPMPromotion.valid_from.desc())
        .limit(5)
    )

    return {
        "active_plans":          active_plans.scalar_one() or 0,
        "active_promotions":     active_promos.scalar_one() or 0,
        "total_planned_budget":  budget_row[0] or Decimal("0"),
        "total_actual_spend":    budget_row[1] or Decimal("0"),
        "open_claims":           claim_row[0] or 0,
        "open_claims_amount":    claim_row[1] or Decimal("0"),
        "pending_approvals":     pending_approvals.scalar_one() or 0,
        "promotions_by_status":  {str(r[0].value): r[1] for r in status_counts.all()},
        "top_promotions":        [
            {
                "id":             str(p.id),
                "promotion_code": p.promotion_code,
                "promotion_name": p.promotion_name,
                "status":         p.status.value,
                "valid_from":     str(p.valid_from),
                "valid_to":       str(p.valid_to),
            }
            for p in top_promos_q.scalars().all()
        ],
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_budget_vs_actual(db: AsyncSession, fiscal_year: Optional[int] = None) -> list:
    q = (
        select(TPMPromotion)
        .options(
            selectinload(TPMPromotion.budget_lines),
            selectinload(TPMPromotion.actual_perf),
        )
    )
    if fiscal_year:
        q = q.join(TPMPlan, TPMPromotion.tpm_plan_id == TPMPlan.id).where(TPMPlan.fiscal_year == fiscal_year)
    result = await db.execute(q)
    rows = []
    for p in result.scalars().all():
        planned  = sum(bl.planned_spend_amount  for bl in p.budget_lines) or Decimal("0")
        approved = sum(bl.approved_spend_amount for bl in p.budget_lines) or Decimal("0")
        actual   = sum(bl.actual_spend_amount   for bl in p.budget_lines) or Decimal("0")
        accrued  = sum(bl.accrued_spend_amount  for bl in p.budget_lines) or Decimal("0")
        variance = approved - actual
        util_pct = (actual / approved * 100) if approved > 0 else Decimal("0")
        rows.append({
            "promotion_id":    str(p.id),
            "promotion_code":  p.promotion_code,
            "promotion_name":  p.promotion_name,
            "promotion_type":  p.promotion_type.value,
            "planned":         planned,
            "approved":        approved,
            "actual":          actual,
            "accrued":         accrued,
            "variance":        variance,
            "utilization_pct": round(util_pct, 1),
        })
    return rows


async def report_roi(db: AsyncSession) -> list:
    q = select(TPMPromotion).options(
        selectinload(TPMPromotion.expected_perf),
        selectinload(TPMPromotion.actual_perf),
    ).where(TPMPromotion.status.in_(["COMPLETED", "ACTIVE"]))
    result = await db.execute(q)
    rows = []
    for p in result.scalars().all():
        exp = p.expected_perf
        act = p.actual_perf
        rows.append({
            "promotion_id":       str(p.id),
            "promotion_code":     p.promotion_code,
            "promotion_name":     p.promotion_name,
            "objective_type":     p.objective_type.value,
            "expected_roi_pct":   float(exp.expected_roi_pct) if exp else 0,
            "actual_roi_pct":     float(act.actual_roi_pct) if act else 0,
            "expected_uplift_pct":float(exp.expected_uplift_pct) if exp else 0,
            "actual_uplift_pct":  float(act.actual_uplift_pct) if act else 0,
            "actual_spend":       float(act.actual_spend) if act else 0,
            "roi_vs_plan":        float(act.actual_roi_pct - exp.expected_roi_pct) if (act and exp) else 0,
        })
    return sorted(rows, key=lambda r: r["actual_roi_pct"], reverse=True)


async def report_claim_aging(db: AsyncSession) -> list:
    q = select(TPMClaim).options(selectinload(TPMClaim.claim_lines)).where(
        TPMClaim.status.not_in([TPMClaimStatus.SETTLED, TPMClaimStatus.CANCELLED, TPMClaimStatus.REJECTED])
    )
    result = await db.execute(q)
    today  = date.today()
    rows   = []
    for c in result.scalars().all():
        promo_result = await db.execute(select(TPMPromotion.promotion_name).where(TPMPromotion.id == c.tpm_promotion_id))
        promo_name = promo_result.scalar_one_or_none() or "—"
        rows.append({
            "claim_id":       str(c.id),
            "claim_no":       c.claim_no,
            "promotion_name": promo_name,
            "claimant_type":  c.claimant_type.value,
            "claim_type":     c.claim_type.value,
            "claimed_amount": float(c.claimed_amount),
            "approved_amount":float(c.approved_amount),
            "settled_amount": float(c.settled_amount),
            "status":         c.status.value,
            "claim_date":     c.claim_date,
            "age_days":       (today - c.claim_date).days,
        })
    return sorted(rows, key=lambda r: r["age_days"], reverse=True)


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_agents(db: AsyncSession) -> dict:
    recs = []

    # Agent 1: ROI Analyst — find completed promotions with poor ROI
    roi_q = await db.execute(
        select(TPMPromotion)
        .options(selectinload(TPMPromotion.expected_perf), selectinload(TPMPromotion.actual_perf))
        .where(TPMPromotion.status == TPMPromotionStatus.COMPLETED)
    )
    for promo in roi_q.scalars().all():
        act = promo.actual_perf
        exp = promo.expected_perf
        if act and exp and act.actual_roi_pct < (exp.expected_roi_pct * Decimal("0.5")):
            recs.append(TPMAIRecommendation(
                agent_type=TPMAIAgentType.ROI_ANALYST,
                tpm_promotion_id=promo.id,
                title=f"Underperforming ROI: {promo.promotion_name}",
                detail=(
                    f"Expected ROI {float(exp.expected_roi_pct):.1f}% but achieved {float(act.actual_roi_pct):.1f}%. "
                    f"Actual spend KES {float(act.actual_spend):,.0f} delivered below-target uplift. "
                    "Review targeting, timing, or discount depth before repeating."
                ),
                severity="warning",
            ))

    # Agent 2: Budget Risk Monitor — promotions near/over budget
    budget_q = await db.execute(
        select(TPMPromotion)
        .options(selectinload(TPMPromotion.budget_lines))
        .where(TPMPromotion.status == TPMPromotionStatus.ACTIVE)
    )
    for promo in budget_q.scalars().all():
        for bl in promo.budget_lines:
            approved = bl.approved_spend_amount or bl.planned_spend_amount
            if approved > 0 and bl.actual_spend_amount >= approved * Decimal("0.9"):
                recs.append(TPMAIRecommendation(
                    agent_type=TPMAIAgentType.BUDGET_RISK_MONITOR,
                    tpm_promotion_id=promo.id,
                    title=f"Budget at risk: {promo.promotion_name} ({bl.budget_type.value})",
                    detail=(
                        f"Actual spend KES {float(bl.actual_spend_amount):,.0f} is "
                        f"{float(bl.actual_spend_amount/approved*100):.0f}% of approved budget "
                        f"KES {float(approved):,.0f}. Promotion is still active."
                    ),
                    severity="critical" if bl.actual_spend_amount >= approved else "warning",
                ))

    # Agent 3: Planner Assistant — overlapping promotions same channel/brand
    active_q = await db.execute(
        select(TPMPromotion).where(
            TPMPromotion.status.in_([TPMPromotionStatus.ACTIVE, TPMPromotionStatus.APPROVED])
        )
    )
    active_list = active_q.scalars().all()
    seen_pairs: set = set()
    for i, a in enumerate(active_list):
        for b in active_list[i+1:]:
            pair = tuple(sorted([str(a.id), str(b.id)]))
            if pair in seen_pairs:
                continue
            # Overlap check
            overlap_dates = a.valid_from <= b.valid_to and b.valid_from <= a.valid_to
            overlap_channel = a.channel_id and b.channel_id and a.channel_id == b.channel_id
            overlap_brand   = a.brand_id   and b.brand_id   and a.brand_id   == b.brand_id
            if overlap_dates and (overlap_channel or overlap_brand):
                seen_pairs.add(pair)
                recs.append(TPMAIRecommendation(
                    agent_type=TPMAIAgentType.PLANNER_ASSISTANT,
                    title=f"Promotion overlap: {a.promotion_name} & {b.promotion_name}",
                    detail=(
                        f"Both promotions are active in overlapping periods "
                        f"({a.valid_from}–{a.valid_to} / {b.valid_from}–{b.valid_to}) "
                        f"targeting {'same channel ' + a.channel_id if overlap_channel else ''}"
                        f"{'same brand ' + a.brand_id if overlap_brand else ''}. "
                        "Check for cannibalization risk."
                    ),
                    severity="warning",
                ))

    for rec in recs:
        db.add(rec)
    await db.commit()
    return {"generated": len(recs)}


async def get_ai_recs(db: AsyncSession, status: Optional[str] = None) -> list:
    q = select(TPMAIRecommendation).order_by(TPMAIRecommendation.created_at.desc())
    if status:
        q = q.where(TPMAIRecommendation.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: str, req: TPMAIRecAckRequest):
    result = await db.execute(select(TPMAIRecommendation).where(TPMAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if rec:
        rec.status = req.status
        if req.actioned_notes:
            rec.actioned_notes = req.actioned_notes
        await db.commit()
    return rec
