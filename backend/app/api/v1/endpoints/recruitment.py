from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.recruitment import (
    RequisitionStatus, PipelineStatus, OfferStatus, RTAIRecStatus,
)
from app.schemas.recruitment import (
    RecruitmentStageCreate, RecruitmentStageRead,
    JobRequisitionCreate, JobRequisitionRead, JobRequisitionApprove,
    JobPostingCreate, JobPostingRead,
    CandidateCreate, CandidateRead,
    PipelineCreate, PipelineMoveStage, PipelineRead, PipelineHistoryRead,
    InterviewCreate, InterviewRead, InterviewFeedback,
    OfferCreate, OfferRead, OfferRespond,
    RecruitmentDashboardResponse,
    RTAIRecRead, RTAIRecAck,
)
from app.services import recruitment_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=RecruitmentDashboardResponse)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Stages ────────────────────────────────────────────────────────────────────

@router.get("/stages", response_model=List[RecruitmentStageRead])
async def list_stages(db: AsyncSession = Depends(get_db)):
    return await svc.list_stages(db)


@router.post("/stages", response_model=RecruitmentStageRead)
async def create_stage(data: RecruitmentStageCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_stage(db, data)


@router.post("/stages/seed-defaults", response_model=List[RecruitmentStageRead])
async def seed_defaults(db: AsyncSession = Depends(get_db)):
    return await svc.seed_default_stages(db)


# ── Requisitions ──────────────────────────────────────────────────────────────

@router.get("/requisitions", response_model=List[JobRequisitionRead])
async def list_requisitions(
    status: Optional[RequisitionStatus] = None,
    department_id: Optional[UUID] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_requisitions(db, status=status, department_id=department_id, skip=skip, limit=limit)


@router.post("/requisitions", response_model=JobRequisitionRead)
async def create_requisition(data: JobRequisitionCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_requisition(db, data)


@router.get("/requisitions/{req_id}", response_model=JobRequisitionRead)
async def get_requisition(req_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await svc.get_requisition(db, req_id)
    if not r:
        raise HTTPException(404, "Requisition not found")
    return r


@router.patch("/requisitions/{req_id}", response_model=JobRequisitionRead)
async def update_requisition(req_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    r = await svc.update_requisition(db, req_id, data)
    if not r:
        raise HTTPException(404, "Requisition not found")
    return r


@router.post("/requisitions/{req_id}/approve", response_model=JobRequisitionRead)
async def approve_requisition(req_id: UUID, data: JobRequisitionApprove, db: AsyncSession = Depends(get_db)):
    r = await svc.approve_requisition(db, req_id, data)
    if not r:
        raise HTTPException(400, "Cannot approve — wrong status or not found")
    return r


@router.post("/requisitions/{req_id}/open", response_model=JobRequisitionRead)
async def open_requisition(req_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await svc.open_requisition(db, req_id)
    if not r:
        raise HTTPException(400, "Cannot open — must be approved first")
    return r


@router.post("/requisitions/{req_id}/close", response_model=JobRequisitionRead)
async def close_requisition(req_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await svc.close_requisition(db, req_id)
    if not r:
        raise HTTPException(404, "Requisition not found")
    return r


# ── Postings ──────────────────────────────────────────────────────────────────

@router.get("/postings", response_model=List[JobPostingRead])
async def list_postings(
    requisition_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_postings(db, requisition_id=requisition_id)


@router.post("/postings", response_model=JobPostingRead)
async def create_posting(data: JobPostingCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_posting(db, data)


@router.post("/postings/{posting_id}/publish", response_model=JobPostingRead)
async def publish_posting(posting_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await svc.publish_posting(db, posting_id)
    if not p:
        raise HTTPException(404, "Posting not found")
    return p


# ── Candidates ────────────────────────────────────────────────────────────────

@router.get("/candidates", response_model=List[CandidateRead])
async def list_candidates(
    search: Optional[str] = None,
    source: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_candidates(db, search=search, source=source, skip=skip, limit=limit)


@router.post("/candidates", response_model=CandidateRead)
async def create_candidate(data: CandidateCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_candidate(db, data)


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
async def get_candidate(candidate_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await svc.get_candidate(db, candidate_id)
    if not c:
        raise HTTPException(404, "Candidate not found")
    return c


@router.patch("/candidates/{candidate_id}", response_model=CandidateRead)
async def update_candidate(candidate_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    c = await svc.update_candidate(db, candidate_id, data)
    if not c:
        raise HTTPException(404, "Candidate not found")
    return c


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.get("/pipeline", response_model=List[PipelineRead])
async def list_pipeline(
    requisition_id: Optional[UUID] = None,
    stage_id: Optional[UUID] = None,
    status: Optional[PipelineStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_pipelines(db, requisition_id=requisition_id, stage_id=stage_id, status=status)


@router.post("/pipeline", response_model=PipelineRead)
async def add_to_pipeline(data: PipelineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_to_pipeline(db, data)


@router.get("/pipeline/{pipeline_id}", response_model=PipelineRead)
async def get_pipeline(pipeline_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await svc.get_pipeline(db, pipeline_id)
    if not p:
        raise HTTPException(404, "Pipeline record not found")
    return p


@router.post("/pipeline/{pipeline_id}/move", response_model=PipelineRead)
async def move_stage(pipeline_id: UUID, data: PipelineMoveStage, db: AsyncSession = Depends(get_db)):
    p = await svc.move_pipeline_stage(db, pipeline_id, data)
    if not p:
        raise HTTPException(400, "Cannot move stage")
    return p


@router.post("/pipeline/{pipeline_id}/reject", response_model=PipelineRead)
async def reject_candidate(
    pipeline_id: UUID,
    notes: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    p = await svc.reject_pipeline(db, pipeline_id, notes)
    if not p:
        raise HTTPException(404, "Pipeline not found")
    return p


# ── Interviews ────────────────────────────────────────────────────────────────

@router.get("/interviews", response_model=List[InterviewRead])
async def list_interviews(
    candidate_id: Optional[UUID] = None,
    requisition_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_interviews(db, candidate_id=candidate_id, requisition_id=requisition_id)


@router.post("/interviews", response_model=InterviewRead)
async def schedule_interview(data: InterviewCreate, db: AsyncSession = Depends(get_db)):
    return await svc.schedule_interview(db, data)


@router.get("/interviews/{interview_id}", response_model=InterviewRead)
async def get_interview(interview_id: UUID, db: AsyncSession = Depends(get_db)):
    iv = await svc.get_interview(db, interview_id)
    if not iv:
        raise HTTPException(404, "Interview not found")
    return iv


@router.post("/interviews/{interview_id}/feedback", response_model=InterviewRead)
async def record_feedback(interview_id: UUID, data: InterviewFeedback, db: AsyncSession = Depends(get_db)):
    iv = await svc.record_feedback(db, interview_id, data)
    if not iv:
        raise HTTPException(404, "Interview not found")
    return iv


# ── Offers ────────────────────────────────────────────────────────────────────

@router.get("/offers", response_model=List[OfferRead])
async def list_offers(
    requisition_id: Optional[UUID] = None,
    status: Optional[OfferStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_offers(db, requisition_id=requisition_id, status=status)


@router.post("/offers", response_model=OfferRead)
async def create_offer(data: OfferCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_offer(db, data)


@router.get("/offers/{offer_id}", response_model=OfferRead)
async def get_offer(offer_id: UUID, db: AsyncSession = Depends(get_db)):
    o = await svc.get_offer(db, offer_id)
    if not o:
        raise HTTPException(404, "Offer not found")
    return o


@router.post("/offers/{offer_id}/send", response_model=OfferRead)
async def send_offer(offer_id: UUID, db: AsyncSession = Depends(get_db)):
    o = await svc.send_offer(db, offer_id)
    if not o:
        raise HTTPException(400, "Cannot send offer — wrong status")
    return o


@router.post("/offers/{offer_id}/respond", response_model=OfferRead)
async def respond_to_offer(offer_id: UUID, data: OfferRespond, db: AsyncSession = Depends(get_db)):
    o = await svc.respond_to_offer(db, offer_id, data)
    if not o:
        raise HTTPException(400, "Cannot respond — wrong status")
    return o


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/pipeline-by-stage")
async def report_pipeline_by_stage(db: AsyncSession = Depends(get_db)):
    return await svc.report_pipeline_by_stage(db)


@router.get("/reports/source-effectiveness")
async def report_source_effectiveness(db: AsyncSession = Depends(get_db)):
    return await svc.report_source_effectiveness(db)


@router.get("/reports/offer-acceptance")
async def report_offer_acceptance(db: AsyncSession = Depends(get_db)):
    return await svc.report_offer_acceptance(db)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-candidate-matcher")
async def run_candidate_matcher(db: AsyncSession = Depends(get_db)):
    count = await svc.run_candidate_matcher(db)
    return {"generated": count}


@router.post("/ai/run-hiring-risk-detector")
async def run_hiring_risk_detector(db: AsyncSession = Depends(get_db)):
    count = await svc.run_hiring_risk_detector(db)
    return {"generated": count}


@router.post("/ai/run-pipeline-optimizer")
async def run_pipeline_optimizer(db: AsyncSession = Depends(get_db)):
    count = await svc.run_pipeline_optimizer(db)
    return {"generated": count}


@router.get("/ai/recommendations", response_model=List[RTAIRecRead])
async def list_recs(status: Optional[RTAIRecStatus] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=RTAIRecRead)
async def ack_rec(rec_id: UUID, data: RTAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
