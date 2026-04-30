from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appraisals import (
    AppraisalPeriod, AppraisalTemplate, AppraisalRecord,
    AppraisalKPILine, AppraisalCompetencyLine, AppraisalDevelopmentPlan,
    APAIRecommendation,
    AppraisalPeriodStatus, AppraisalPeriodType, AppraisalStatus,
    FinalRating, DevelopmentPlanStatus, APAIAgentType, APAIRecStatus,
)
from app.schemas.appraisals import (
    AppraisalPeriodCreate, AppraisalPeriodUpdate,
    AppraisalTemplateCreate, AppraisalRecordCreate,
    KPILineCreate, KPILineUpdate,
    CompetencyLineCreate, CompetencyLineUpdate,
    DevelopmentPlanCreate, DevelopmentPlanUpdate,
    SelfSubmitRequest, ManagerReviewRequest, HRReviewRequest, FinalizeRequest,
    APAIRecAck,
)


# ── Rating Band ───────────────────────────────────────────────────────────────

def _score_to_rating(score: Decimal) -> FinalRating:
    if score >= 90:
        return FinalRating.EXCELLENT
    elif score >= 75:
        return FinalRating.GOOD
    elif score >= 60:
        return FinalRating.MEETS_EXPECTATIONS
    else:
        return FinalRating.IMPROVEMENT_NEEDED


def _compute_weighted_score(lines: list, self_field: str, manager_field: str) -> Optional[Decimal]:
    total_weight = sum(Decimal(str(getattr(l, "weight_pct") or 0)) for l in lines)
    if not total_weight:
        return None
    score = Decimal("0")
    for line in lines:
        w = Decimal(str(getattr(line, "weight_pct") or 0))
        s = getattr(line, manager_field) or getattr(line, self_field) or Decimal("0")
        score += w * Decimal(str(s))
    return (score / total_weight).quantize(Decimal("0.01"))


# ── Period ────────────────────────────────────────────────────────────────────

async def create_period(db: AsyncSession, data: AppraisalPeriodCreate) -> AppraisalPeriod:
    period = AppraisalPeriod(**data.model_dump())
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


async def list_periods(db: AsyncSession, status: Optional[str] = None) -> List[AppraisalPeriod]:
    q = select(AppraisalPeriod).order_by(AppraisalPeriod.start_date.desc())
    if status:
        q = q.where(AppraisalPeriod.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def get_period(db: AsyncSession, period_id: UUID) -> Optional[AppraisalPeriod]:
    result = await db.execute(select(AppraisalPeriod).where(AppraisalPeriod.appraisal_period_id == period_id))
    return result.scalar_one_or_none()


async def update_period(db: AsyncSession, period_id: UUID, data: AppraisalPeriodUpdate) -> Optional[AppraisalPeriod]:
    period = await get_period(db, period_id)
    if not period:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(period, k, v)
    period.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(period)
    return period


# ── Template ──────────────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, data: AppraisalTemplateCreate) -> AppraisalTemplate:
    tpl = AppraisalTemplate(**data.model_dump())
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def list_templates(db: AsyncSession, active_only: bool = False) -> List[AppraisalTemplate]:
    q = select(AppraisalTemplate).order_by(AppraisalTemplate.template_name)
    if active_only:
        q = q.where(AppraisalTemplate.active_flag == True)
    result = await db.execute(q)
    return result.scalars().all()


async def get_template(db: AsyncSession, template_id: UUID) -> Optional[AppraisalTemplate]:
    result = await db.execute(select(AppraisalTemplate).where(AppraisalTemplate.template_id == template_id))
    return result.scalar_one_or_none()


# ── Appraisal Record ──────────────────────────────────────────────────────────

async def create_record(db: AsyncSession, data: AppraisalRecordCreate) -> AppraisalRecord:
    record = AppraisalRecord(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_records(
    db: AsyncSession,
    period_id: Optional[UUID] = None,
    employee_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[AppraisalRecord]:
    q = (
        select(AppraisalRecord)
        .options(
            selectinload(AppraisalRecord.kpi_lines),
            selectinload(AppraisalRecord.competency_lines),
            selectinload(AppraisalRecord.development_plans),
        )
        .order_by(AppraisalRecord.created_at.desc())
    )
    if period_id:
        q = q.where(AppraisalRecord.appraisal_period_id == period_id)
    if employee_id:
        q = q.where(AppraisalRecord.employee_id == employee_id)
    if department_id:
        q = q.where(AppraisalRecord.department_id == department_id)
    if status:
        q = q.where(AppraisalRecord.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def get_record(db: AsyncSession, appraisal_id: UUID) -> Optional[AppraisalRecord]:
    result = await db.execute(
        select(AppraisalRecord)
        .options(
            selectinload(AppraisalRecord.kpi_lines),
            selectinload(AppraisalRecord.competency_lines),
            selectinload(AppraisalRecord.development_plans),
        )
        .where(AppraisalRecord.appraisal_id == appraisal_id)
    )
    return result.scalar_one_or_none()


async def self_submit(db: AsyncSession, appraisal_id: UUID, data: SelfSubmitRequest) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record or record.status not in (AppraisalStatus.DRAFT, AppraisalStatus.SELF_REVIEW):
        return None
    if data.self_score is not None:
        record.self_score = data.self_score
    if data.notes:
        record.notes = data.notes
    record.status = AppraisalStatus.MANAGER_REVIEW
    record.self_submitted_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def manager_review(db: AsyncSession, appraisal_id: UUID, data: ManagerReviewRequest) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record or record.status != AppraisalStatus.MANAGER_REVIEW:
        return None
    if data.manager_score is not None:
        record.manager_score = data.manager_score
    if data.increment_recommendation is not None:
        record.increment_recommendation = data.increment_recommendation
    record.promotion_recommendation = data.promotion_recommendation
    if data.notes:
        record.notes = data.notes
    record.status = AppraisalStatus.HR_REVIEW
    record.manager_reviewed_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def hr_review(db: AsyncSession, appraisal_id: UUID, data: HRReviewRequest) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record or record.status != AppraisalStatus.HR_REVIEW:
        return None
    if data.final_score is not None:
        record.final_score = data.final_score
    if data.final_rating is not None:
        record.final_rating = data.final_rating
    elif record.final_score is not None:
        record.final_rating = _score_to_rating(record.final_score)
    if data.hr_notes:
        record.hr_notes = data.hr_notes
    if data.calibration_notes:
        record.calibration_notes = data.calibration_notes
    record.status = AppraisalStatus.CALIBRATION
    record.hr_reviewed_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def finalize_appraisal(db: AsyncSession, appraisal_id: UUID, data: FinalizeRequest) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record or record.status not in (AppraisalStatus.CALIBRATION, AppraisalStatus.HR_REVIEW):
        return None
    if data.final_score is not None:
        record.final_score = data.final_score
    if data.final_rating is not None:
        record.final_rating = data.final_rating
    elif record.final_score is not None:
        record.final_rating = _score_to_rating(record.final_score)
    if data.increment_recommendation is not None:
        record.increment_recommendation = data.increment_recommendation
    if data.promotion_recommendation is not None:
        record.promotion_recommendation = data.promotion_recommendation
    if data.hr_notes:
        record.hr_notes = data.hr_notes
    record.status = AppraisalStatus.COMPLETED
    record.finalized_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def reject_appraisal(db: AsyncSession, appraisal_id: UUID, notes: Optional[str] = None) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record:
        return None
    record.status = AppraisalStatus.REJECTED
    if notes:
        record.hr_notes = notes
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


# ── KPI Lines ─────────────────────────────────────────────────────────────────

async def add_kpi_line(db: AsyncSession, appraisal_id: UUID, data: KPILineCreate) -> AppraisalKPILine:
    line = AppraisalKPILine(appraisal_id=appraisal_id, **data.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def update_kpi_line(db: AsyncSession, kpi_line_id: UUID, data: KPILineUpdate) -> Optional[AppraisalKPILine]:
    result = await db.execute(select(AppraisalKPILine).where(AppraisalKPILine.kpi_line_id == kpi_line_id))
    line = result.scalar_one_or_none()
    if not line:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(line, k, v)
    await db.commit()
    await db.refresh(line)
    return line


async def delete_kpi_line(db: AsyncSession, kpi_line_id: UUID) -> bool:
    result = await db.execute(select(AppraisalKPILine).where(AppraisalKPILine.kpi_line_id == kpi_line_id))
    line = result.scalar_one_or_none()
    if not line:
        return False
    await db.delete(line)
    await db.commit()
    return True


# ── Competency Lines ──────────────────────────────────────────────────────────

async def add_competency_line(db: AsyncSession, appraisal_id: UUID, data: CompetencyLineCreate) -> AppraisalCompetencyLine:
    line = AppraisalCompetencyLine(appraisal_id=appraisal_id, **data.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def update_competency_line(db: AsyncSession, line_id: UUID, data: CompetencyLineUpdate) -> Optional[AppraisalCompetencyLine]:
    result = await db.execute(select(AppraisalCompetencyLine).where(AppraisalCompetencyLine.competency_line_id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(line, k, v)
    await db.commit()
    await db.refresh(line)
    return line


async def delete_competency_line(db: AsyncSession, line_id: UUID) -> bool:
    result = await db.execute(select(AppraisalCompetencyLine).where(AppraisalCompetencyLine.competency_line_id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return False
    await db.delete(line)
    await db.commit()
    return True


# ── Development Plans ─────────────────────────────────────────────────────────

async def add_development_plan(db: AsyncSession, appraisal_id: UUID, employee_id: str, data: DevelopmentPlanCreate) -> AppraisalDevelopmentPlan:
    plan = AppraisalDevelopmentPlan(appraisal_id=appraisal_id, employee_id=employee_id, **data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_development_plan(db: AsyncSession, plan_id: UUID, data: DevelopmentPlanUpdate) -> Optional[AppraisalDevelopmentPlan]:
    result = await db.execute(select(AppraisalDevelopmentPlan).where(AppraisalDevelopmentPlan.development_plan_id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(plan, k, v)
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return plan


async def list_development_plans(db: AsyncSession, employee_id: Optional[str] = None, status: Optional[str] = None) -> List[AppraisalDevelopmentPlan]:
    q = select(AppraisalDevelopmentPlan).order_by(AppraisalDevelopmentPlan.due_date)
    if employee_id:
        q = q.where(AppraisalDevelopmentPlan.employee_id == employee_id)
    if status:
        q = q.where(AppraisalDevelopmentPlan.status == status)
    result = await db.execute(q)
    return result.scalars().all()


# ── Score Calculation ─────────────────────────────────────────────────────────

async def calculate_scores(db: AsyncSession, appraisal_id: UUID) -> Optional[AppraisalRecord]:
    record = await get_record(db, appraisal_id)
    if not record:
        return None
    template = await get_template(db, record.template_id) if record.template_id else None
    kpi_w = Decimal(str(template.kpi_weight_pct if template else 60))
    comp_w = Decimal(str(template.competency_weight_pct if template else 40))

    kpi_score = _compute_weighted_score(record.kpi_lines, "self_score", "manager_score")
    comp_score = _compute_weighted_score(record.competency_lines, "self_rating", "manager_rating")

    if kpi_score is not None and comp_score is not None:
        record.final_score = ((kpi_score * kpi_w + comp_score * comp_w) / Decimal("100")).quantize(Decimal("0.01"))
        record.final_rating = _score_to_rating(record.final_score)
    elif kpi_score is not None:
        record.final_score = kpi_score
        record.final_rating = _score_to_rating(kpi_score)
    elif comp_score is not None:
        record.final_score = comp_score
        record.final_rating = _score_to_rating(comp_score)

    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession, period_id: Optional[UUID] = None) -> Dict[str, Any]:
    q = select(AppraisalRecord)
    if period_id:
        q = q.where(AppraisalRecord.appraisal_period_id == period_id)
    result = await db.execute(q)
    records = result.scalars().all()

    status_counts: Dict[str, int] = {}
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    rating_dist: Dict[str, int] = {}
    scores = []
    dept_scores: Dict[str, list] = {}
    for r in records:
        if r.final_rating:
            rating_dist[r.final_rating] = rating_dist.get(r.final_rating, 0) + 1
        if r.final_score:
            scores.append(float(r.final_score))
        if r.department_name and r.final_score:
            dept_scores.setdefault(r.department_name, []).append(float(r.final_score))

    dept_avg = [
        {"department": dept, "avg_score": round(sum(s) / len(s), 2)}
        for dept, s in dept_scores.items()
    ]

    dev_result = await db.execute(
        select(func.count(AppraisalDevelopmentPlan.development_plan_id)).where(
            AppraisalDevelopmentPlan.status.in_([DevelopmentPlanStatus.OPEN, DevelopmentPlanStatus.IN_PROGRESS])
        )
    )
    promo_count = sum(1 for r in records if r.promotion_recommendation)

    return {
        "total_records": len(records),
        "self_review_pending": status_counts.get(AppraisalStatus.SELF_REVIEW, 0),
        "manager_review_pending": status_counts.get(AppraisalStatus.MANAGER_REVIEW, 0),
        "hr_review_pending": status_counts.get(AppraisalStatus.HR_REVIEW, 0),
        "calibration_pending": status_counts.get(AppraisalStatus.CALIBRATION, 0),
        "completed": status_counts.get(AppraisalStatus.COMPLETED, 0),
        "avg_final_score": round(sum(scores) / len(scores), 2) if scores else None,
        "rating_distribution": rating_dist,
        "department_avg_scores": dept_avg,
        "pending_development_plans": dev_result.scalar() or 0,
        "promotion_recommendations": promo_count,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_completion(db: AsyncSession, period_id: UUID) -> Dict[str, Any]:
    result = await db.execute(select(AppraisalRecord).where(AppraisalRecord.appraisal_period_id == period_id))
    records = result.scalars().all()
    total = len(records)
    completed = sum(1 for r in records if r.status == AppraisalStatus.COMPLETED)
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_rate_pct": round(completed / total * 100, 1) if total else 0,
        "by_status": {s: sum(1 for r in records if r.status == s) for s in AppraisalStatus},
    }


async def report_rating_distribution(db: AsyncSession, period_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = select(AppraisalRecord).where(AppraisalRecord.final_rating.isnot(None))
    if period_id:
        q = q.where(AppraisalRecord.appraisal_period_id == period_id)
    result = await db.execute(q)
    records = result.scalars().all()
    dist: Dict[str, int] = {}
    for r in records:
        dist[r.final_rating] = dist.get(r.final_rating, 0) + 1
    return [{"rating": k, "count": v} for k, v in dist.items()]


async def report_promotions(db: AsyncSession, period_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = select(AppraisalRecord).where(AppraisalRecord.promotion_recommendation == True)
    if period_id:
        q = q.where(AppraisalRecord.appraisal_period_id == period_id)
    result = await db.execute(q)
    records = result.scalars().all()
    return [
        {
            "employee_id": r.employee_id,
            "employee_name": r.employee_name,
            "department": r.department_name,
            "final_score": float(r.final_score) if r.final_score else None,
            "final_rating": r.final_rating,
            "increment_recommendation": float(r.increment_recommendation) if r.increment_recommendation else None,
        }
        for r in records
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_performance_insight(db: AsyncSession) -> List[APAIRecommendation]:
    result = await db.execute(
        select(AppraisalRecord)
        .options(selectinload(AppraisalRecord.kpi_lines))
        .where(AppraisalRecord.status == AppraisalStatus.COMPLETED)
        .where(AppraisalRecord.final_score.isnot(None))
    )
    records = result.scalars().all()
    recs = []
    low_performers = [r for r in records if r.final_score and r.final_score < 60]
    for r in low_performers[:10]:
        rec = APAIRecommendation(
            agent_type=APAIAgentType.PERFORMANCE_INSIGHT,
            title=f"Low performer: {r.employee_name or r.employee_id}",
            body=(
                f"Employee {r.employee_name or r.employee_id} scored {r.final_score} "
                f"({r.final_rating}). Consider coaching or a performance improvement plan."
            ),
            appraisal_id=r.appraisal_id,
            employee_id=r.employee_id,
            department_id=r.department_id,
            score=int(r.final_score),
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_calibration_risk(db: AsyncSession) -> List[APAIRecommendation]:
    result = await db.execute(
        select(AppraisalRecord).where(AppraisalRecord.final_score.isnot(None))
    )
    records = result.scalars().all()
    dept_scores: Dict[str, list] = {}
    for r in records:
        if r.department_id and r.final_score:
            dept_scores.setdefault(r.department_id, []).append({
                "score": float(r.final_score), "name": r.department_name, "id": r.employee_id
            })
    recs = []
    for dept_id, items in dept_scores.items():
        scores = [i["score"] for i in items]
        avg = sum(scores) / len(scores)
        high = [i for i in items if i["score"] >= 90]
        dept_name = items[0].get("name", dept_id)
        if avg >= 85 and len(items) >= 3:
            rec = APAIRecommendation(
                agent_type=APAIAgentType.CALIBRATION_RISK,
                title=f"Rating inflation detected: {dept_name}",
                body=(
                    f"Department '{dept_name}' has an average score of {avg:.1f} "
                    f"with {len(high)} employees rated 90+. Review for rating inflation."
                ),
                department_id=dept_id,
                score=int(avg),
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_development_plan_agent(db: AsyncSession) -> List[APAIRecommendation]:
    result = await db.execute(
        select(AppraisalRecord)
        .options(selectinload(AppraisalRecord.development_plans))
        .where(AppraisalRecord.status == AppraisalStatus.COMPLETED)
    )
    records = result.scalars().all()
    recs = []
    no_plan = [r for r in records if not r.development_plans]
    for r in no_plan[:10]:
        rec = APAIRecommendation(
            agent_type=APAIAgentType.DEVELOPMENT_PLAN,
            title=f"No development plan: {r.employee_name or r.employee_id}",
            body=(
                f"Appraisal for {r.employee_name or r.employee_id} is completed but "
                f"has no development plan. Add training goals or coaching actions."
            ),
            appraisal_id=r.appraisal_id,
            employee_id=r.employee_id,
            department_id=r.department_id,
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None) -> List[APAIRecommendation]:
    q = select(APAIRecommendation).order_by(APAIRecommendation.created_at.desc())
    if status:
        q = q.where(APAIRecommendation.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: APAIRecAck) -> Optional[APAIRecommendation]:
    result = await db.execute(select(APAIRecommendation).where(APAIRecommendation.rec_id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    if data.actioned_by:
        rec.actioned_by = data.actioned_by
        rec.actioned_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rec)
    return rec
