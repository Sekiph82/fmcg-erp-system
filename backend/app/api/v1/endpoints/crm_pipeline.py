from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.crm import (
    CRMStageCreate, CRMStageRead, CRMStageUpdate,
    CRMRecordCreate, CRMRecordRead, CRMRecordUpdate,
    CRMInterestLineCreate, CRMInterestLineRead,
    CRMActivityCreate, CRMActivityRead, CRMActivityComplete,
    CRMCompetitorCreate, CRMCompetitorRead,
    CRMQualifyRequest, CRMConvertRequest,
    CRMCloseWonRequest, CRMCloseLostRequest,
    CRMWinLossRead,
    CRMAIRecRead, CRMAIRecAck,
)
import app.services.crm_pipeline_service as svc

router = APIRouter()


# ── Stages ────────────────────────────────────────────────────────────────────

@router.get("/stages", response_model=List[CRMStageRead])
async def list_stages(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await svc.get_stages(db, active_only=active_only)


@router.post("/stages", response_model=CRMStageRead, status_code=201)
async def create_stage(data: CRMStageCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_stage(db, data)


@router.patch("/stages/{stage_id}", response_model=CRMStageRead)
async def update_stage(stage_id: str, data: CRMStageUpdate, db: AsyncSession = Depends(get_db)):
    result = await svc.update_stage(db, stage_id, data)
    if not result:
        raise HTTPException(404, "Stage not found")
    return result


@router.post("/stages/seed-defaults", response_model=List[CRMStageRead])
async def seed_default_stages(db: AsyncSession = Depends(get_db)):
    return await svc.seed_default_stages(db)


# ── Records ───────────────────────────────────────────────────────────────────

@router.get("/leads", response_model=List[CRMRecordRead])
async def list_leads(
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_records(db, record_type="LEAD", status=status,
                                  assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                  temperature=temperature, skip=skip, limit=limit)


@router.post("/leads", response_model=CRMRecordRead, status_code=201)
async def create_lead(data: CRMRecordCreate, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMRecordType
    data.record_type = CRMRecordType.LEAD
    return await svc.create_record(db, data)


@router.get("/opportunities", response_model=List[CRMRecordRead])
async def list_opportunities(
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_records(db, record_type="OPPORTUNITY", status=status,
                                  assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                  temperature=temperature, skip=skip, limit=limit)


@router.post("/opportunities", response_model=CRMRecordRead, status_code=201)
async def create_opportunity(data: CRMRecordCreate, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMRecordType
    data.record_type = CRMRecordType.OPPORTUNITY
    return await svc.create_record(db, data)


@router.get("/records", response_model=List[CRMRecordRead])
async def list_all_records(
    record_type: Optional[str] = None,
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_records(db, record_type=record_type, status=status,
                                  assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                  temperature=temperature, skip=skip, limit=limit)


@router.post("/records", response_model=CRMRecordRead, status_code=201)
async def create_record(data: CRMRecordCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_record(db, data)


@router.get("/records/{record_id}", response_model=CRMRecordRead)
async def get_record(record_id: str, db: AsyncSession = Depends(get_db)):
    rec = await svc.get_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.patch("/records/{record_id}", response_model=CRMRecordRead)
async def update_record(record_id: str, data: CRMRecordUpdate, db: AsyncSession = Depends(get_db)):
    rec = await svc.update_record(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/qualify", response_model=CRMRecordRead)
async def qualify_record(record_id: str, data: CRMQualifyRequest, db: AsyncSession = Depends(get_db)):
    rec = await svc.qualify_record(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/convert-to-opportunity", response_model=CRMRecordRead)
async def convert_to_opportunity(record_id: str, data: CRMConvertRequest, db: AsyncSession = Depends(get_db)):
    rec = await svc.convert_to_opportunity(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/close-won", response_model=CRMRecordRead)
async def close_won(record_id: str, data: CRMCloseWonRequest, db: AsyncSession = Depends(get_db)):
    rec = await svc.close_won(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/close-lost", response_model=CRMRecordRead)
async def close_lost(record_id: str, data: CRMCloseLostRequest, db: AsyncSession = Depends(get_db)):
    rec = await svc.close_lost(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/on-hold", response_model=CRMRecordRead)
async def put_on_hold(record_id: str, notes: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    rec = await svc.put_on_hold(db, record_id, notes)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/reopen", response_model=CRMRecordRead)
async def reopen_record(record_id: str, db: AsyncSession = Depends(get_db)):
    rec = await svc.reopen_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


@router.post("/records/{record_id}/update-score", response_model=CRMRecordRead)
async def update_lead_score(record_id: str, db: AsyncSession = Depends(get_db)):
    rec = await svc.update_lead_score(db, record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


# ── Interest Lines ────────────────────────────────────────────────────────────

@router.post("/records/{record_id}/interest-lines", response_model=CRMInterestLineRead, status_code=201)
async def add_interest_line(record_id: str, data: CRMInterestLineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_interest_line(db, data)


@router.delete("/interest-lines/{line_id}", status_code=204)
async def delete_interest_line(line_id: str, db: AsyncSession = Depends(get_db)):
    if not await svc.delete_interest_line(db, line_id):
        raise HTTPException(404, "Interest line not found")


# ── Activities ────────────────────────────────────────────────────────────────

@router.get("/activities", response_model=List[CRMActivityRead])
async def list_activities(
    record_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    result_status: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_activities(db, record_id=record_id, assigned_to=assigned_to,
                                     result_status=result_status, overdue_only=overdue_only,
                                     skip=skip, limit=limit)


@router.post("/activities", response_model=CRMActivityRead, status_code=201)
async def create_activity(data: CRMActivityCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_activity(db, data)


@router.post("/activities/{activity_id}/complete", response_model=CRMActivityRead)
async def complete_activity(activity_id: str, data: CRMActivityComplete, db: AsyncSession = Depends(get_db)):
    act = await svc.complete_activity(db, activity_id, data)
    if not act:
        raise HTTPException(404, "Activity not found")
    return act


# ── Competitors ───────────────────────────────────────────────────────────────

@router.post("/competitors", response_model=CRMCompetitorRead, status_code=201)
async def add_competitor(data: CRMCompetitorCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_competitor(db, data)


# ── Deduplication ─────────────────────────────────────────────────────────────

@router.get("/check-duplicates", response_model=List[CRMRecordRead])
async def check_duplicates(
    company_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.check_duplicates(db, company_name, email, phone)


# ── Dashboard & Reports ───────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


@router.get("/forecast")
async def get_forecast(months_ahead: int = 6, db: AsyncSession = Depends(get_db)):
    return await svc.get_forecast(db, months_ahead=months_ahead)


@router.get("/reports/pipeline")
async def pipeline_report(db: AsyncSession = Depends(get_db)):
    return await svc.pipeline_report(db)


@router.get("/reports/win-loss")
async def win_loss_report(db: AsyncSession = Depends(get_db)):
    return await svc.win_loss_report(db)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-lead-prioritization")
async def run_lead_prioritization(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_lead_prioritization(db)
    return {"generated": len(recs), "message": f"Lead Prioritization agent generated {len(recs)} recommendations"}


@router.post("/ai/run-pipeline-risk")
async def run_pipeline_risk(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_pipeline_risk(db)
    return {"generated": len(recs), "message": f"Pipeline Risk agent generated {len(recs)} recommendations"}


@router.post("/ai/run-win-loss-insight")
async def run_win_loss_insight(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_win_loss_insight(db)
    return {"generated": len(recs), "message": f"Win/Loss Insight agent generated {len(recs)} recommendations"}


@router.get("/ai/recommendations", response_model=List[CRMAIRecRead])
async def get_ai_recommendations(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_ai_recommendations(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=CRMAIRecRead)
async def ack_recommendation(rec_id: str, data: CRMAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_recommendation(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
