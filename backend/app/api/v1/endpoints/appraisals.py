from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.appraisals import (
    AppraisalPeriodCreate, AppraisalPeriodUpdate, AppraisalPeriodOut,
    AppraisalTemplateCreate, AppraisalTemplateOut,
    AppraisalRecordCreate, AppraisalRecordOut,
    KPILineCreate, KPILineUpdate, KPILineOut,
    CompetencyLineCreate, CompetencyLineUpdate, CompetencyLineOut,
    DevelopmentPlanCreate, DevelopmentPlanUpdate, DevelopmentPlanOut,
    SelfSubmitRequest, ManagerReviewRequest, HRReviewRequest, FinalizeRequest,
    AppraisalDashboard, APAIRecOut, APAIRecAck,
)
import app.services.appraisals_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AppraisalDashboard)
async def dashboard(
    period_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_dashboard(db, period_id)


# ── Periods ───────────────────────────────────────────────────────────────────

@router.post("/periods", response_model=AppraisalPeriodOut, status_code=201)
async def create_period(data: AppraisalPeriodCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_period(db, data)


@router.get("/periods", response_model=List[AppraisalPeriodOut])
async def list_periods(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_periods(db, status)


@router.get("/periods/{period_id}", response_model=AppraisalPeriodOut)
async def get_period(period_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_period(db, period_id)
    if not obj:
        raise HTTPException(404, "Period not found")
    return obj


@router.patch("/periods/{period_id}", response_model=AppraisalPeriodOut)
async def update_period(period_id: UUID, data: AppraisalPeriodUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_period(db, period_id, data)
    if not obj:
        raise HTTPException(404, "Period not found")
    return obj


# ── Templates ─────────────────────────────────────────────────────────────────

@router.post("/templates", response_model=AppraisalTemplateOut, status_code=201)
async def create_template(data: AppraisalTemplateCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_template(db, data)


@router.get("/templates", response_model=List[AppraisalTemplateOut])
async def list_templates(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await svc.list_templates(db, active_only)


@router.get("/templates/{template_id}", response_model=AppraisalTemplateOut)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_template(db, template_id)
    if not obj:
        raise HTTPException(404, "Template not found")
    return obj


# ── Appraisal Records ─────────────────────────────────────────────────────────

@router.post("/", response_model=AppraisalRecordOut, status_code=201)
async def create_record(data: AppraisalRecordCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_record(db, data)


@router.get("/", response_model=List[AppraisalRecordOut])
async def list_records(
    period_id: Optional[UUID] = None,
    employee_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_records(db, period_id, employee_id, department_id, status)


@router.get("/{appraisal_id}", response_model=AppraisalRecordOut)
async def get_record(appraisal_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_record(db, appraisal_id)
    if not obj:
        raise HTTPException(404, "Appraisal not found")
    return obj


@router.post("/{appraisal_id}/self-submit", response_model=AppraisalRecordOut)
async def self_submit(appraisal_id: UUID, data: SelfSubmitRequest, db: AsyncSession = Depends(get_db)):
    obj = await svc.self_submit(db, appraisal_id, data)
    if not obj:
        raise HTTPException(400, "Cannot self-submit in current status")
    return obj


@router.post("/{appraisal_id}/manager-review", response_model=AppraisalRecordOut)
async def manager_review(appraisal_id: UUID, data: ManagerReviewRequest, db: AsyncSession = Depends(get_db)):
    obj = await svc.manager_review(db, appraisal_id, data)
    if not obj:
        raise HTTPException(400, "Cannot manager-review in current status")
    return obj


@router.post("/{appraisal_id}/hr-review", response_model=AppraisalRecordOut)
async def hr_review(appraisal_id: UUID, data: HRReviewRequest, db: AsyncSession = Depends(get_db)):
    obj = await svc.hr_review(db, appraisal_id, data)
    if not obj:
        raise HTTPException(400, "Cannot HR-review in current status")
    return obj


@router.post("/{appraisal_id}/finalize", response_model=AppraisalRecordOut)
async def finalize(appraisal_id: UUID, data: FinalizeRequest, db: AsyncSession = Depends(get_db)):
    obj = await svc.finalize_appraisal(db, appraisal_id, data)
    if not obj:
        raise HTTPException(400, "Cannot finalize in current status")
    return obj


@router.post("/{appraisal_id}/reject", response_model=AppraisalRecordOut)
async def reject(appraisal_id: UUID, notes: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    obj = await svc.reject_appraisal(db, appraisal_id, notes)
    if not obj:
        raise HTTPException(404, "Appraisal not found")
    return obj


@router.post("/{appraisal_id}/calculate-scores", response_model=AppraisalRecordOut)
async def calculate_scores(appraisal_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.calculate_scores(db, appraisal_id)
    if not obj:
        raise HTTPException(404, "Appraisal not found")
    return obj


# ── KPI Lines ─────────────────────────────────────────────────────────────────

@router.post("/{appraisal_id}/kpi-lines", response_model=KPILineOut, status_code=201)
async def add_kpi_line(appraisal_id: UUID, data: KPILineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_kpi_line(db, appraisal_id, data)


@router.patch("/kpi-lines/{kpi_line_id}", response_model=KPILineOut)
async def update_kpi_line(kpi_line_id: UUID, data: KPILineUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_kpi_line(db, kpi_line_id, data)
    if not obj:
        raise HTTPException(404, "KPI line not found")
    return obj


@router.delete("/kpi-lines/{kpi_line_id}", status_code=204)
async def delete_kpi_line(kpi_line_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_kpi_line(db, kpi_line_id)
    if not ok:
        raise HTTPException(404, "KPI line not found")


# ── Competency Lines ──────────────────────────────────────────────────────────

@router.post("/{appraisal_id}/competency-lines", response_model=CompetencyLineOut, status_code=201)
async def add_competency_line(appraisal_id: UUID, data: CompetencyLineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_competency_line(db, appraisal_id, data)


@router.patch("/competency-lines/{line_id}", response_model=CompetencyLineOut)
async def update_competency_line(line_id: UUID, data: CompetencyLineUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_competency_line(db, line_id, data)
    if not obj:
        raise HTTPException(404, "Competency line not found")
    return obj


@router.delete("/competency-lines/{line_id}", status_code=204)
async def delete_competency_line(line_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_competency_line(db, line_id)
    if not ok:
        raise HTTPException(404, "Competency line not found")


# ── Development Plans ─────────────────────────────────────────────────────────

@router.post("/{appraisal_id}/development-plans", response_model=DevelopmentPlanOut, status_code=201)
async def add_development_plan(
    appraisal_id: UUID,
    employee_id: str,
    data: DevelopmentPlanCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_development_plan(db, appraisal_id, employee_id, data)


@router.patch("/development-plans/{plan_id}", response_model=DevelopmentPlanOut)
async def update_development_plan(plan_id: UUID, data: DevelopmentPlanUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_development_plan(db, plan_id, data)
    if not obj:
        raise HTTPException(404, "Development plan not found")
    return obj


@router.get("/development-plans/list", response_model=List[DevelopmentPlanOut])
async def list_development_plans(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_development_plans(db, employee_id, status)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/completion")
async def report_completion(period_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.report_completion(db, period_id)


@router.get("/reports/rating-distribution")
async def report_rating_distribution(period_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_rating_distribution(db, period_id)


@router.get("/reports/promotions")
async def report_promotions(period_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_promotions(db, period_id)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-performance-insight", response_model=List[APAIRecOut])
async def run_performance_insight(db: AsyncSession = Depends(get_db)):
    return await svc.run_performance_insight(db)


@router.post("/ai/run-calibration-risk", response_model=List[APAIRecOut])
async def run_calibration_risk(db: AsyncSession = Depends(get_db)):
    return await svc.run_calibration_risk(db)


@router.post("/ai/run-development-plan", response_model=List[APAIRecOut])
async def run_development_plan_agent(db: AsyncSession = Depends(get_db)):
    return await svc.run_development_plan_agent(db)


@router.get("/ai/recommendations", response_model=List[APAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=APAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: APAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
