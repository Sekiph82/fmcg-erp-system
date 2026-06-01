from __future__ import annotations
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.recruitment import (
    RecruitmentStage, JobRequisition, JobPosting, Candidate,
    CandidatePipeline, CandidatePipelineHistory, Interview, Offer,
    RTAIRecommendation,
    EmploymentType, RequisitionStatus, PostingStatus, PipelineStatus,
    InterviewDecision, OfferStatus, RTAIAgentType, RTAIRecStatus,
)
from app.schemas.recruitment import (
    RecruitmentStageCreate, JobRequisitionCreate, JobRequisitionApprove,
    JobPostingCreate, CandidateCreate, PipelineCreate, PipelineMoveStage,
    InterviewCreate, InterviewFeedback, OfferCreate, OfferRespond, RTAIRecAck,
)


# ── Number generators ─────────────────────────────────────────────────────────

async def _next_req_code(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count()).select_from(JobRequisition))).scalar_one() + 1
    return f"REQ-{n:05d}"


async def _next_candidate_code(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count()).select_from(Candidate))).scalar_one() + 1
    return f"CAN-{n:06d}"


async def _next_offer_code(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count()).select_from(Offer))).scalar_one() + 1
    return f"OFR-{n:05d}"


# ── Stage CRUD ────────────────────────────────────────────────────────────────

async def list_stages(db: AsyncSession) -> List[RecruitmentStage]:
    result = await db.execute(select(RecruitmentStage).order_by(RecruitmentStage.sequence))
    return list(result.scalars().all())


async def create_stage(db: AsyncSession, data: RecruitmentStageCreate) -> RecruitmentStage:
    s = RecruitmentStage(**data.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def seed_default_stages(db: AsyncSession) -> List[RecruitmentStage]:
    existing = (await db.execute(select(func.count()).select_from(RecruitmentStage))).scalar_one()
    if existing > 0:
        return await list_stages(db)
    defaults = [
        ("REQ_CREATED",  "Requisition Created",  1, "active"),
        ("JOB_POSTED",   "Job Posted",            2, "active"),
        ("APP_RECEIVED", "Application Received",  3, "active"),
        ("SCREENING",    "Screening",             4, "active"),
        ("INTERVIEW_1",  "Interview Stage 1",     5, "active"),
        ("INTERVIEW_2",  "Interview Stage 2",     6, "active"),
        ("FINAL_IV",     "Final Interview",       7, "active"),
        ("OFFER_MADE",   "Offer Made",            8, "active"),
        ("HIRED",        "Hired",                 9, "final_hire"),
        ("REJECTED",     "Rejected",             10, "final_reject"),
        ("ON_HOLD",      "On Hold",              11, "active"),
    ]
    from app.models.recruitment import StageType
    stages = []
    for code, name, seq, stype in defaults:
        s = RecruitmentStage(
            stage_code=code, stage_name=name, sequence=seq,
            stage_type=StageType(stype),
        )
        db.add(s)
        stages.append(s)
    await db.commit()
    return await list_stages(db)


async def get_stage(db: AsyncSession, stage_id: UUID) -> Optional[RecruitmentStage]:
    r = await db.execute(select(RecruitmentStage).where(RecruitmentStage.stage_id == stage_id))
    return r.scalar_one_or_none()


async def get_stage_by_code(db: AsyncSession, code: str) -> Optional[RecruitmentStage]:
    r = await db.execute(select(RecruitmentStage).where(RecruitmentStage.stage_code == code))
    return r.scalar_one_or_none()


# ── Requisition CRUD ──────────────────────────────────────────────────────────

async def list_requisitions(
    db: AsyncSession,
    status: Optional[RequisitionStatus] = None,
    department_id: Optional[UUID] = None,
    skip: int = 0, limit: int = 50,
) -> List[JobRequisition]:
    q = select(JobRequisition)
    filters = []
    if status:
        filters.append(JobRequisition.status == status)
    if department_id:
        filters.append(JobRequisition.department_id == department_id)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q.order_by(JobRequisition.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_requisition(db: AsyncSession, req_id: UUID) -> Optional[JobRequisition]:
    r = await db.execute(select(JobRequisition).where(JobRequisition.requisition_id == req_id))
    return r.scalar_one_or_none()


async def create_requisition(db: AsyncSession, data: JobRequisitionCreate) -> JobRequisition:
    code = await _next_req_code(db)
    req = JobRequisition(requisition_code=code, **data.model_dump())
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def approve_requisition(db: AsyncSession, req_id: UUID, data: JobRequisitionApprove) -> Optional[JobRequisition]:
    req = await get_requisition(db, req_id)
    if not req or req.status not in (RequisitionStatus.DRAFT,):
        return None
    req.status = RequisitionStatus.APPROVED
    req.approved_by = data.approver_id
    req.approved_at = datetime.utcnow()
    if data.notes:
        req.notes = (req.notes or "") + f"\n[Approval] {data.notes}"
    await db.commit()
    await db.refresh(req)
    return req


async def open_requisition(db: AsyncSession, req_id: UUID) -> Optional[JobRequisition]:
    req = await get_requisition(db, req_id)
    if not req or req.status != RequisitionStatus.APPROVED:
        return None
    req.status = RequisitionStatus.OPEN
    await db.commit()
    await db.refresh(req)
    return req


async def close_requisition(db: AsyncSession, req_id: UUID) -> Optional[JobRequisition]:
    req = await get_requisition(db, req_id)
    if not req:
        return None
    req.status = RequisitionStatus.CLOSED
    await db.commit()
    await db.refresh(req)
    return req


async def update_requisition(db: AsyncSession, req_id: UUID, data: dict) -> Optional[JobRequisition]:
    req = await get_requisition(db, req_id)
    if not req:
        return None
    for k, v in data.items():
        setattr(req, k, v)
    await db.commit()
    await db.refresh(req)
    return req


# ── Job Posting CRUD ──────────────────────────────────────────────────────────

async def list_postings(db: AsyncSession, requisition_id: Optional[UUID] = None, limit: int = 200) -> List[JobPosting]:
    q = select(JobPosting)
    if requisition_id:
        q = q.where(JobPosting.requisition_id == requisition_id)
    result = await db.execute(q.order_by(JobPosting.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def create_posting(db: AsyncSession, data: JobPostingCreate) -> JobPosting:
    posting = JobPosting(**data.model_dump())
    db.add(posting)
    await db.commit()
    await db.refresh(posting)
    return posting


async def publish_posting(db: AsyncSession, posting_id: UUID) -> Optional[JobPosting]:
    r = await db.execute(select(JobPosting).where(JobPosting.posting_id == posting_id))
    posting = r.scalar_one_or_none()
    if not posting:
        return None
    posting.status = PostingStatus.ACTIVE
    posting.publish_date = date.today()
    await db.commit()
    await db.refresh(posting)
    return posting


# ── Candidate CRUD ────────────────────────────────────────────────────────────

async def list_candidates(
    db: AsyncSession,
    search: Optional[str] = None,
    source: Optional[str] = None,
    skip: int = 0, limit: int = 50,
) -> List[Candidate]:
    q = select(Candidate).where(Candidate.blacklisted == False)
    if search:
        q = q.where(or_(
            Candidate.full_name.ilike(f"%{search}%"),
            Candidate.email.ilike(f"%{search}%"),
            Candidate.skills_tags.ilike(f"%{search}%"),
        ))
    if source:
        q = q.where(Candidate.source == source)
    result = await db.execute(q.order_by(Candidate.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_candidate(db: AsyncSession, candidate_id: UUID) -> Optional[Candidate]:
    r = await db.execute(select(Candidate).where(Candidate.candidate_id == candidate_id))
    return r.scalar_one_or_none()


async def get_candidate_by_email(db: AsyncSession, email: str) -> Optional[Candidate]:
    r = await db.execute(select(Candidate).where(Candidate.email == email))
    return r.scalar_one_or_none()


async def create_candidate(db: AsyncSession, data: CandidateCreate) -> Candidate:
    existing = await get_candidate_by_email(db, data.email)
    if existing:
        return existing
    code = await _next_candidate_code(db)
    cand = Candidate(candidate_code=code, **data.model_dump())
    db.add(cand)
    await db.commit()
    await db.refresh(cand)
    return cand


async def update_candidate(db: AsyncSession, candidate_id: UUID, data: dict) -> Optional[Candidate]:
    cand = await get_candidate(db, candidate_id)
    if not cand:
        return None
    for k, v in data.items():
        setattr(cand, k, v)
    await db.commit()
    await db.refresh(cand)
    return cand


# ── Pipeline CRUD ─────────────────────────────────────────────────────────────

async def list_pipelines(
    db: AsyncSession,
    requisition_id: Optional[UUID] = None,
    stage_id: Optional[UUID] = None,
    status: Optional[PipelineStatus] = None,
    limit: int = 200,
) -> List[CandidatePipeline]:
    q = select(CandidatePipeline).options(
        selectinload(CandidatePipeline.candidate),
        selectinload(CandidatePipeline.stage),
        selectinload(CandidatePipeline.history),
    )
    filters = []
    if requisition_id:
        filters.append(CandidatePipeline.requisition_id == requisition_id)
    if stage_id:
        filters.append(CandidatePipeline.stage_id == stage_id)
    if status:
        filters.append(CandidatePipeline.status == status)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q.order_by(CandidatePipeline.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_pipeline(db: AsyncSession, pipeline_id: UUID) -> Optional[CandidatePipeline]:
    r = await db.execute(
        select(CandidatePipeline)
        .options(selectinload(CandidatePipeline.history))
        .where(CandidatePipeline.pipeline_id == pipeline_id)
    )
    return r.scalar_one_or_none()


async def add_to_pipeline(db: AsyncSession, data: PipelineCreate) -> CandidatePipeline:
    pipeline = CandidatePipeline(**data.model_dump())
    db.add(pipeline)
    await db.flush()
    hist = CandidatePipelineHistory(
        pipeline_id=pipeline.pipeline_id,
        stage_id=data.stage_id,
        notes="Initial application",
    )
    db.add(hist)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def move_pipeline_stage(
    db: AsyncSession, pipeline_id: UUID, data: PipelineMoveStage
) -> Optional[CandidatePipeline]:
    pipeline = await get_pipeline(db, pipeline_id)
    if not pipeline:
        return None
    stage = await get_stage(db, data.stage_id)
    if not stage:
        return None
    pipeline.stage_id = data.stage_id
    pipeline.last_update = datetime.utcnow()

    from app.models.recruitment import StageType
    if stage.stage_type == StageType.FINAL_HIRE:
        pipeline.status = PipelineStatus.HIRED
        await _mark_hired(db, pipeline)
    elif stage.stage_type == StageType.FINAL_REJECT:
        pipeline.status = PipelineStatus.REJECTED
    else:
        pipeline.status = PipelineStatus.ACTIVE

    hist = CandidatePipelineHistory(
        pipeline_id=pipeline_id,
        stage_id=data.stage_id,
        moved_by=data.moved_by,
        notes=data.notes,
    )
    db.add(hist)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def _mark_hired(db: AsyncSession, pipeline: CandidatePipeline) -> None:
    req = await get_requisition(db, pipeline.requisition_id)
    if req:
        req.filled_count = (req.filled_count or 0) + 1
        if req.filled_count >= req.headcount:
            req.status = RequisitionStatus.CLOSED


async def reject_pipeline(db: AsyncSession, pipeline_id: UUID, notes: str = "") -> Optional[CandidatePipeline]:
    pipeline = await get_pipeline(db, pipeline_id)
    if not pipeline:
        return None
    reject_stage = await get_stage_by_code(db, "REJECTED")
    pipeline.status = PipelineStatus.REJECTED
    if reject_stage:
        pipeline.stage_id = reject_stage.stage_id
        hist = CandidatePipelineHistory(
            pipeline_id=pipeline_id, stage_id=reject_stage.stage_id, notes=notes or "Rejected"
        )
        db.add(hist)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


# ── Interview CRUD ────────────────────────────────────────────────────────────

async def list_interviews(
    db: AsyncSession,
    candidate_id: Optional[UUID] = None,
    requisition_id: Optional[UUID] = None,
    limit: int = 200,
) -> List[Interview]:
    q = select(Interview)
    filters = []
    if candidate_id:
        filters.append(Interview.candidate_id == candidate_id)
    if requisition_id:
        filters.append(Interview.requisition_id == requisition_id)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q.order_by(Interview.interview_date.desc()).limit(limit))
    return list(result.scalars().all())


async def get_interview(db: AsyncSession, interview_id: UUID) -> Optional[Interview]:
    r = await db.execute(select(Interview).where(Interview.interview_id == interview_id))
    return r.scalar_one_or_none()


async def schedule_interview(db: AsyncSession, data: InterviewCreate) -> Interview:
    iv = Interview(**data.model_dump())
    db.add(iv)
    await db.commit()
    await db.refresh(iv)
    return iv


async def record_feedback(db: AsyncSession, interview_id: UUID, data: InterviewFeedback) -> Optional[Interview]:
    iv = await get_interview(db, interview_id)
    if not iv:
        return None
    iv.feedback = data.feedback
    iv.score = data.score
    iv.technical_score = data.technical_score
    iv.cultural_score = data.cultural_score
    iv.decision = data.decision
    iv.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(iv)
    return iv


async def interviews_this_week(db: AsyncSession) -> int:
    start = date.today() - timedelta(days=date.today().weekday())
    end = start + timedelta(days=7)
    r = await db.execute(
        select(func.count()).select_from(Interview).where(
            and_(Interview.interview_date >= start, Interview.interview_date < end)
        )
    )
    return r.scalar_one()


# ── Offer CRUD ────────────────────────────────────────────────────────────────

async def list_offers(
    db: AsyncSession,
    requisition_id: Optional[UUID] = None,
    status: Optional[OfferStatus] = None,
    limit: int = 200,
) -> List[Offer]:
    q = select(Offer)
    filters = []
    if requisition_id:
        filters.append(Offer.requisition_id == requisition_id)
    if status:
        filters.append(Offer.status == status)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q.order_by(Offer.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_offer(db: AsyncSession, offer_id: UUID) -> Optional[Offer]:
    r = await db.execute(select(Offer).where(Offer.offer_id == offer_id))
    return r.scalar_one_or_none()


async def create_offer(db: AsyncSession, data: OfferCreate) -> Offer:
    code = await _next_offer_code(db)
    offer = Offer(offer_code=code, **data.model_dump())
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    return offer


async def send_offer(db: AsyncSession, offer_id: UUID) -> Optional[Offer]:
    offer = await get_offer(db, offer_id)
    if not offer or offer.status not in (OfferStatus.DRAFT, OfferStatus.NEGOTIATING):
        return None
    offer.status = OfferStatus.SENT
    offer.sent_at = datetime.utcnow()
    await db.commit()
    await db.refresh(offer)
    return offer


async def respond_to_offer(db: AsyncSession, offer_id: UUID, data: OfferRespond) -> Optional[Offer]:
    offer = await get_offer(db, offer_id)
    if not offer or offer.status not in (OfferStatus.SENT, OfferStatus.NEGOTIATING):
        return None
    offer.status = data.status
    offer.responded_at = datetime.utcnow()
    if data.rejection_reason:
        offer.rejection_reason = data.rejection_reason
    if data.negotiation_notes:
        offer.negotiation_notes = data.negotiation_notes
    if data.joining_date:
        offer.joining_date = data.joining_date
    if data.status == OfferStatus.ACCEPTED:
        await _trigger_hire(db, offer)
    await db.commit()
    await db.refresh(offer)
    return offer


async def _trigger_hire(db: AsyncSession, offer: Offer) -> None:
    hired_stage = await get_stage_by_code(db, "HIRED")
    if not hired_stage:
        return
    r = await db.execute(
        select(CandidatePipeline).where(
            and_(
                CandidatePipeline.candidate_id == offer.candidate_id,
                CandidatePipeline.requisition_id == offer.requisition_id,
            )
        )
    )
    pipeline = r.scalar_one_or_none()
    if pipeline:
        pipeline.status = PipelineStatus.HIRED
        pipeline.stage_id = hired_stage.stage_id
        hist = CandidatePipelineHistory(
            pipeline_id=pipeline.pipeline_id,
            stage_id=hired_stage.stage_id,
            notes=f"Offer {offer.offer_code} accepted — candidate hired",
        )
        db.add(hist)
    req = await get_requisition(db, offer.requisition_id)
    if req:
        req.filled_count = (req.filled_count or 0) + 1
        if req.filled_count >= req.headcount:
            req.status = RequisitionStatus.CLOSED


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    open_reqs = (await db.execute(
        select(func.count()).select_from(JobRequisition).where(JobRequisition.status == RequisitionStatus.OPEN)
    )).scalar_one()
    total_candidates = (await db.execute(
        select(func.count()).select_from(Candidate).where(Candidate.blacklisted == False)
    )).scalar_one()
    active_pipelines = (await db.execute(
        select(func.count()).select_from(CandidatePipeline).where(CandidatePipeline.status == PipelineStatus.ACTIVE)
    )).scalar_one()
    iv_this_week = await interviews_this_week(db)
    pending_offers = (await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status.in_([OfferStatus.DRAFT, OfferStatus.SENT]))
    )).scalar_one()
    month_start = date.today().replace(day=1)
    hires = (await db.execute(
        select(func.count()).select_from(Offer).where(
            and_(Offer.status == OfferStatus.ACCEPTED, Offer.responded_at >= month_start)
        )
    )).scalar_one()

    # avg time to hire: from first pipeline entry to hired offer
    accepted = await db.execute(
        select(Offer).where(
            and_(Offer.status == OfferStatus.ACCEPTED, Offer.sent_at.isnot(None), Offer.responded_at.isnot(None))
        ).limit(20)
    )
    accepted_list = accepted.scalars().all()
    if accepted_list:
        deltas = [(o.responded_at - o.sent_at).days for o in accepted_list if o.sent_at and o.responded_at]
        avg_days = sum(deltas) / len(deltas) if deltas else 0.0
    else:
        avg_days = 0.0

    ai_alerts = (await db.execute(
        select(func.count()).select_from(RTAIRecommendation).where(RTAIRecommendation.status == RTAIRecStatus.PENDING)
    )).scalar_one()

    return {
        "open_requisitions": open_reqs,
        "total_candidates": total_candidates,
        "active_pipelines": active_pipelines,
        "interviews_this_week": iv_this_week,
        "pending_offers": pending_offers,
        "hires_this_month": hires,
        "avg_time_to_hire_days": round(avg_days, 1),
        "ai_alerts": ai_alerts,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_pipeline_by_stage(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            RecruitmentStage.stage_name,
            func.count(CandidatePipeline.pipeline_id).label("count"),
        )
        .join(CandidatePipeline, CandidatePipeline.stage_id == RecruitmentStage.stage_id)
        .where(CandidatePipeline.status == PipelineStatus.ACTIVE)
        .group_by(RecruitmentStage.stage_name, RecruitmentStage.sequence)
        .order_by(RecruitmentStage.sequence)
    )
    return [dict(r._mapping) for r in result.all()]


async def report_source_effectiveness(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            Candidate.source,
            func.count(Candidate.candidate_id).label("candidates"),
            func.count(CandidatePipeline.pipeline_id).label("applied"),
        )
        .outerjoin(CandidatePipeline, CandidatePipeline.candidate_id == Candidate.candidate_id)
        .group_by(Candidate.source)
    )
    return [dict(r._mapping) for r in result.all()]


async def report_offer_acceptance(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count()).select_from(Offer))).scalar_one()
    accepted = (await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status == OfferStatus.ACCEPTED)
    )).scalar_one()
    rejected = (await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status == OfferStatus.REJECTED)
    )).scalar_one()
    return {
        "total_offers": total,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate_pct": round(accepted / total * 100, 1) if total else 0.0,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def _save_rec(db: AsyncSession, agent: RTAIAgentType, subject: str, body: str, **kwargs) -> None:
    rec = RTAIRecommendation(agent_type=agent, subject=subject, body=body, **kwargs)
    db.add(rec)


async def run_candidate_matcher(db: AsyncSession) -> int:
    count = 0
    # Find open requisitions with <5 active candidates
    result = await db.execute(
        select(JobRequisition).where(JobRequisition.status == RequisitionStatus.OPEN)
    )
    reqs = result.scalars().all()
    for req in reqs:
        active = (await db.execute(
            select(func.count()).select_from(CandidatePipeline).where(
                and_(
                    CandidatePipeline.requisition_id == req.requisition_id,
                    CandidatePipeline.status == PipelineStatus.ACTIVE,
                )
            )
        )).scalar_one()
        if active < 3:
            await _save_rec(
                db, RTAIAgentType.CANDIDATE_MATCHER,
                f"Low candidate pool: {req.job_title}",
                f"Requisition {req.requisition_code} ({req.job_title}) has only {active} active candidate(s). "
                f"Consider expanding sourcing channels or reviewing job requirements.",
                ref_requisition_id=req.requisition_id,
            )
            count += 1
    await db.commit()
    return count


async def run_hiring_risk_detector(db: AsyncSession) -> int:
    count = 0
    # Offers sent >5 days ago with no response
    cutoff = datetime.utcnow() - timedelta(days=5)
    result = await db.execute(
        select(Offer).where(
            and_(Offer.status == OfferStatus.SENT, Offer.sent_at <= cutoff)
        )
    )
    overdue = result.scalars().all()
    for o in overdue:
        cand = await get_candidate(db, o.candidate_id)
        name = cand.full_name if cand else str(o.candidate_id)
        days_waiting = (datetime.utcnow() - o.sent_at).days
        await _save_rec(
            db, RTAIAgentType.HIRING_RISK_DETECTOR,
            f"Offer risk: {name} — {days_waiting} days no response",
            f"Offer {o.offer_code} for {name} was sent {days_waiting} days ago with no response. "
            f"Follow up immediately to prevent candidate loss. Consider salary negotiation if needed.",
            ref_candidate_id=o.candidate_id,
        )
        count += 1

    # Multiple failed interviews for same candidate
    result2 = await db.execute(
        select(Interview.candidate_id, func.count().label("fails"))
        .where(Interview.decision == InterviewDecision.FAIL)
        .group_by(Interview.candidate_id)
        .having(func.count() > 1)
    )
    for row in result2.all():
        cand = await get_candidate(db, row.candidate_id)
        name = cand.full_name if cand else str(row.candidate_id)
        await _save_rec(
            db, RTAIAgentType.HIRING_RISK_DETECTOR,
            f"Repeated interview failures: {name}",
            f"Candidate {name} has failed {row.fails} interviews. Review profile fit before investing further resources.",
            ref_candidate_id=row.candidate_id,
        )
        count += 1

    await db.commit()
    return count


async def run_pipeline_optimizer(db: AsyncSession) -> int:
    count = 0
    # Stages with >10 candidates stuck (no movement in 7+ days)
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(
            RecruitmentStage.stage_name,
            CandidatePipeline.stage_id,
            func.count().label("stuck"),
        )
        .join(RecruitmentStage, RecruitmentStage.stage_id == CandidatePipeline.stage_id)
        .where(
            and_(
                CandidatePipeline.status == PipelineStatus.ACTIVE,
                CandidatePipeline.last_update <= cutoff,
            )
        )
        .group_by(RecruitmentStage.stage_name, CandidatePipeline.stage_id)
        .having(func.count() >= 3)
    )
    for row in result.all():
        await _save_rec(
            db, RTAIAgentType.PIPELINE_OPTIMIZER,
            f"Bottleneck at stage: {row.stage_name}",
            f"Stage '{row.stage_name}' has {row.stuck} candidate(s) with no movement in 7+ days. "
            f"This may indicate an interviewer bandwidth issue or delayed decision-making.",
        )
        count += 1

    # Requisitions open >60 days without a hire
    cutoff60 = date.today() - timedelta(days=60)
    result2 = await db.execute(
        select(JobRequisition).where(
            and_(
                JobRequisition.status == RequisitionStatus.OPEN,
                JobRequisition.opening_date <= cutoff60,
            )
        )
    )
    for req in result2.scalars().all():
        await _save_rec(
            db, RTAIAgentType.PIPELINE_OPTIMIZER,
            f"Long open requisition: {req.job_title}",
            f"Requisition {req.requisition_code} ({req.job_title}) has been open for 60+ days with {req.filled_count}/{req.headcount} filled. "
            f"Consider reviewing the requirements, compensation range, or sourcing strategy.",
            ref_requisition_id=req.requisition_id,
        )
        count += 1

    await db.commit()
    return count


async def list_ai_recs(db: AsyncSession, status: Optional[RTAIRecStatus] = None, limit: int = 200) -> List[RTAIRecommendation]:
    q = select(RTAIRecommendation)
    if status:
        q = q.where(RTAIRecommendation.status == status)
    result = await db.execute(q.order_by(RTAIRecommendation.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: RTAIRecAck) -> Optional[RTAIRecommendation]:
    r = await db.execute(select(RTAIRecommendation).where(RTAIRecommendation.rec_id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    rec.actioned_at = datetime.utcnow()
    if data.notes:
        rec.notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec
