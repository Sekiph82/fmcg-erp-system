"""Quality Management System (QMS) + HACCP API endpoints."""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.quality import (
    QCType, QCStatus, QCDecision, QCInspection, QCTestResult,
    QCTemplate, QCTemplateParameter,
    HazardAnalysis, CriticalControlPoint, CCPMonitoringLog,
    CorrectiveAction, CorrectiveActionStatus, CorrectiveActionStep,
    QCDeviation, DeviationStatus, RiskLevel,
    LotQualityStatus, ReleaseStatus, AllergenValidationRecord,
    QMSAIRecommendation, QMSAIAgentType, QMSAIRecStatus,
    InstrumentCalibration, AQLSamplingPlan, CertificateOfAnalysis,
)
from app.schemas.qms import (
    QCTemplateCreate, QCTemplateUpdate, QCTemplateRead,
    HazardAnalysisCreate, HazardAnalysisUpdate, HazardAnalysisRead,
    CCPCreate, CCPUpdate, CCPRead,
    CCPMonitoringCreate, CCPMonitoringRead,
    CorrectiveActionCreate, CorrectiveActionUpdate, CorrectiveActionRead,
    QCDeviationCreate, QCDeviationUpdate, QCDeviationRead,
    LotQualityStatusRead, LotReleaseRequest, LotHoldRequest,
    AllergenValidationCreate, AllergenValidationRead,
    QMSAIRecRead, QMSAIRecReview,
    QMSDashboard, QCGateCheck,
)
from app.services import qms_service as svc
from app.crud import quality as qc_crud
from app.services import quality_service as qc_svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=QMSDashboard)
async def qms_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = await svc.get_qms_dashboard(db)
    return QMSDashboard(**data)


# ── QC Gate Check ─────────────────────────────────────────────────────────────

@router.get("/gate-check", response_model=QCGateCheck)
async def qc_gate_check(
    lot_id: uuid.UUID,
    stage: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await svc.check_qc_gate(db, lot_id, stage)
    return QCGateCheck(lot_id=lot_id, stage=stage, **result)


# ── QC Templates ──────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[QCTemplateRead])
async def list_templates(
    qc_type: Optional[QCType] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    templates = await svc.list_templates(db, qc_type=qc_type, active_only=active_only)
    return [_build_template_read(t) for t in templates]


@router.post("/templates", response_model=QCTemplateRead, status_code=201)
async def create_template(
    body: QCTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = body.model_dump()
    t = await svc.create_template(db, data)
    await db.commit()
    t = await svc.get_template(db, t.id)
    return _build_template_read(t)


@router.get("/templates/{template_id}", response_model=QCTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return _build_template_read(t)


@router.patch("/templates/{template_id}", response_model=QCTemplateRead)
async def update_template(
    template_id: uuid.UUID,
    body: QCTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t = await svc.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await db.commit()
    t = await svc.get_template(db, template_id)
    return _build_template_read(t)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from fastapi import Response
    t = await svc.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    await db.delete(t)
    await db.commit()
    return Response(status_code=204)


# ── HACCP Hazard Analysis ─────────────────────────────────────────────────────

@router.get("/haccp/hazards", response_model=List[HazardAnalysisRead])
async def list_hazards(
    product_id: Optional[uuid.UUID] = None,
    hazard_type: Optional[str] = None,
    is_ccp: Optional[bool] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(HazardAnalysis)
    if active_only:
        q = q.where(HazardAnalysis.is_active == True)
    if product_id:
        q = q.where(HazardAnalysis.product_id == product_id)
    if hazard_type:
        q = q.where(HazardAnalysis.hazard_type == hazard_type)
    if is_ccp is not None:
        q = q.where(HazardAnalysis.is_ccp == is_ccp)
    r = await db.execute(q.order_by(HazardAnalysis.process_step))
    hazards = list(r.scalars())
    return [_build_hazard_read(h) for h in hazards]


@router.post("/haccp/hazards", response_model=HazardAnalysisRead, status_code=201)
async def create_hazard(
    body: HazardAnalysisCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    h = await svc.create_hazard_analysis(db, body.model_dump(), current_user.id)
    await db.commit()
    r = await db.execute(select(HazardAnalysis).where(HazardAnalysis.id == h.id))
    h = r.scalar_one()
    return _build_hazard_read(h)


@router.patch("/haccp/hazards/{hazard_id}", response_model=HazardAnalysisRead)
async def update_hazard(
    hazard_id: uuid.UUID,
    body: HazardAnalysisUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(HazardAnalysis).where(HazardAnalysis.id == hazard_id))
    h = r.scalar_one_or_none()
    if not h:
        raise HTTPException(404, "Hazard analysis not found")
    updates = body.model_dump(exclude_unset=True)
    if "likelihood_score" in updates and "severity_score" in updates:
        updates["risk_score"] = updates["likelihood_score"] * updates["severity_score"]
    elif "likelihood_score" in updates and h.severity_score:
        updates["risk_score"] = updates["likelihood_score"] * h.severity_score
    elif "severity_score" in updates and h.likelihood_score:
        updates["risk_score"] = h.likelihood_score * updates["severity_score"]
    for k, v in updates.items():
        setattr(h, k, v)
    await db.commit()
    r = await db.execute(select(HazardAnalysis).where(HazardAnalysis.id == hazard_id))
    h = r.scalar_one()
    return _build_hazard_read(h)


# ── Critical Control Points ───────────────────────────────────────────────────

@router.get("/haccp/ccp", response_model=List[CCPRead])
async def list_ccps(
    product_id: Optional[uuid.UUID] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(CriticalControlPoint)
    if active_only:
        q = q.where(CriticalControlPoint.is_active == True)
    if product_id:
        q = q.where(CriticalControlPoint.product_id == product_id)
    r = await db.execute(q.order_by(CriticalControlPoint.ccp_no))
    ccps = list(r.scalars())
    result = []
    for c in ccps:
        rd = _build_ccp_read(c)
        # Recent violations count
        rv = await db.execute(
            select(func.count()).select_from(CCPMonitoringLog)
            .where(CCPMonitoringLog.ccp_id == c.id, CCPMonitoringLog.is_violation == True)
        )
        rd.recent_violations = rv.scalar() or 0
        # Last monitored
        rl = await db.execute(
            select(CCPMonitoringLog.monitoring_datetime)
            .where(CCPMonitoringLog.ccp_id == c.id)
            .order_by(CCPMonitoringLog.monitoring_datetime.desc())
            .limit(1)
        )
        rd.last_monitored_at = rl.scalar_one_or_none()
        result.append(rd)
    return result


@router.post("/haccp/ccp", response_model=CCPRead, status_code=201)
async def create_ccp(
    body: CCPCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await svc.create_ccp(db, body.model_dump())
    await db.commit()
    r = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == c.id))
    c = r.scalar_one()
    return _build_ccp_read(c)


@router.get("/haccp/ccp/{ccp_id}", response_model=CCPRead)
async def get_ccp(
    ccp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == ccp_id))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "CCP not found")
    rd = _build_ccp_read(c)
    rv = await db.execute(
        select(func.count()).select_from(CCPMonitoringLog)
        .where(CCPMonitoringLog.ccp_id == ccp_id, CCPMonitoringLog.is_violation == True)
    )
    rd.recent_violations = rv.scalar() or 0
    return rd


@router.patch("/haccp/ccp/{ccp_id}", response_model=CCPRead)
async def update_ccp(
    ccp_id: uuid.UUID,
    body: CCPUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == ccp_id))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "CCP not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    await db.commit()
    r = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == ccp_id))
    return _build_ccp_read(r.scalar_one())


# ── CCP Monitoring ────────────────────────────────────────────────────────────

@router.get("/haccp/ccp/{ccp_id}/logs", response_model=List[CCPMonitoringRead])
async def list_ccp_logs(
    ccp_id: uuid.UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(CCPMonitoringLog)
        .where(CCPMonitoringLog.ccp_id == ccp_id)
        .order_by(CCPMonitoringLog.monitoring_datetime.desc())
        .limit(limit)
    )
    logs = list(r.scalars())
    # fetch ccp name
    rc = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == ccp_id))
    ccp = rc.scalar_one_or_none()
    return [_build_monitoring_read(l, ccp) for l in logs]


@router.post("/haccp/monitoring", response_model=CCPMonitoringRead, status_code=201)
async def record_ccp_monitoring(
    body: CCPMonitoringCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == body.ccp_id))
    ccp = r.scalar_one_or_none()
    if not ccp:
        raise HTTPException(404, "CCP not found")
    log = await svc.record_ccp_monitoring(db, ccp, body.model_dump(), current_user.id)
    await db.commit()
    r2 = await db.execute(select(CCPMonitoringLog).where(CCPMonitoringLog.id == log.id))
    log = r2.scalar_one()
    return _build_monitoring_read(log, ccp)


@router.get("/haccp/violations", response_model=List[CCPMonitoringRead])
async def list_violations(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(CCPMonitoringLog)
        .where(CCPMonitoringLog.is_violation == True)
        .order_by(CCPMonitoringLog.monitoring_datetime.desc())
        .limit(limit)
    )
    logs = list(r.scalars())
    result = []
    for log in logs:
        rc = await db.execute(select(CriticalControlPoint).where(CriticalControlPoint.id == log.ccp_id))
        ccp = rc.scalar_one_or_none()
        result.append(_build_monitoring_read(log, ccp))
    return result


# ── QC Deviations ─────────────────────────────────────────────────────────────

@router.get("/deviations", response_model=List[QCDeviationRead])
async def list_deviations(
    status: Optional[DeviationStatus] = None,
    severity: Optional[RiskLevel] = None,
    product_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(QCDeviation)
    if status:
        q = q.where(QCDeviation.status == status)
    if severity:
        q = q.where(QCDeviation.severity == severity)
    if product_id:
        q = q.where(QCDeviation.product_id == product_id)
    r = await db.execute(q.order_by(QCDeviation.created_at.desc()))
    devs = list(r.scalars())
    return [_build_deviation_read(d) for d in devs]


@router.post("/deviations", response_model=QCDeviationRead, status_code=201)
async def create_deviation(
    body: QCDeviationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    d = await svc.create_deviation(db, body.model_dump(), current_user.id)
    await db.commit()
    r = await db.execute(select(QCDeviation).where(QCDeviation.id == d.id))
    return _build_deviation_read(r.scalar_one())


@router.get("/deviations/{deviation_id}", response_model=QCDeviationRead)
async def get_deviation(
    deviation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(QCDeviation).where(QCDeviation.id == deviation_id))
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Deviation not found")
    return _build_deviation_read(d)


@router.patch("/deviations/{deviation_id}", response_model=QCDeviationRead)
async def update_deviation(
    deviation_id: uuid.UUID,
    body: QCDeviationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(QCDeviation).where(QCDeviation.id == deviation_id))
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Deviation not found")
    updates = body.model_dump(exclude_unset=True)
    if updates.get("status") == DeviationStatus.RESOLVED:
        from datetime import datetime, timezone
        updates["resolved_at"] = datetime.now(timezone.utc)
        updates["resolved_by_id"] = current_user.id
    for k, v in updates.items():
        setattr(d, k, v)
    await db.commit()
    r = await db.execute(select(QCDeviation).where(QCDeviation.id == deviation_id))
    return _build_deviation_read(r.scalar_one())


# ── Corrective Actions ────────────────────────────────────────────────────────

@router.get("/corrective-actions", response_model=List[CorrectiveActionRead])
async def list_corrective_actions(
    status: Optional[CorrectiveActionStatus] = None,
    severity: Optional[RiskLevel] = None,
    assigned_to_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(CorrectiveAction)
    if status:
        q = q.where(CorrectiveAction.status == status)
    if severity:
        q = q.where(CorrectiveAction.severity == severity)
    if assigned_to_id:
        q = q.where(CorrectiveAction.assigned_to_id == assigned_to_id)
    r = await db.execute(q.order_by(CorrectiveAction.created_at.desc()))
    cas = list(r.scalars())
    return [_build_ca_read(ca) for ca in cas]


@router.post("/corrective-actions", response_model=CorrectiveActionRead, status_code=201)
async def create_corrective_action(
    body: CorrectiveActionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ca = await svc.create_corrective_action(db, body.model_dump())
    await db.commit()
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca.id))
    return _build_ca_read(r.scalar_one())


@router.get("/corrective-actions/{ca_id}", response_model=CorrectiveActionRead)
async def get_corrective_action(
    ca_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    ca = r.scalar_one_or_none()
    if not ca:
        raise HTTPException(404, "Corrective action not found")
    return _build_ca_read(ca)


@router.patch("/corrective-actions/{ca_id}", response_model=CorrectiveActionRead)
async def update_corrective_action(
    ca_id: uuid.UUID,
    body: CorrectiveActionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    ca = r.scalar_one_or_none()
    if not ca:
        raise HTTPException(404, "Corrective action not found")
    updates = body.model_dump(exclude_unset=True)
    if updates.get("status") == CorrectiveActionStatus.COMPLETED:
        from datetime import datetime, timezone
        updates["completed_at"] = datetime.now(timezone.utc)
    for k, v in updates.items():
        setattr(ca, k, v)
    await db.commit()
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    return _build_ca_read(r.scalar_one())


@router.post("/corrective-actions/{ca_id}/steps/{step_id}/complete", response_model=CorrectiveActionRead)
async def complete_ca_step(
    ca_id: uuid.UUID,
    step_id: uuid.UUID,
    completion_notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await svc.complete_ca_step(db, step_id, completion_notes)
    await db.commit()
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    ca = r.scalar_one_or_none()
    if not ca:
        raise HTTPException(404, "Corrective action not found")
    return _build_ca_read(ca)


@router.post("/corrective-actions/{ca_id}/verify", response_model=CorrectiveActionRead)
async def verify_corrective_action(
    ca_id: uuid.UUID,
    effectiveness_check: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import datetime, timezone
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    ca = r.scalar_one_or_none()
    if not ca:
        raise HTTPException(404, "Corrective action not found")
    ca.status = CorrectiveActionStatus.VERIFIED
    ca.verified_at = datetime.now(timezone.utc)
    ca.verified_by_id = current_user.id
    ca.effectiveness_check = effectiveness_check
    await db.commit()
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    return _build_ca_read(r.scalar_one())


# ── Lot Quality Status ────────────────────────────────────────────────────────

@router.get("/lot-status/{lot_id}", response_model=LotQualityStatusRead)
async def get_lot_quality_status(
    lot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(LotQualityStatus).where(LotQualityStatus.lot_id == lot_id))
    lqs = r.scalar_one_or_none()
    if not lqs:
        raise HTTPException(404, "No quality status record for this lot")
    return LotQualityStatusRead.model_validate(lqs)


@router.get("/lot-status", response_model=List[LotQualityStatusRead])
async def list_lot_quality_statuses(
    release_status: Optional[ReleaseStatus] = None,
    hold_flag: Optional[bool] = None,
    quarantine_flag: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(LotQualityStatus)
    if release_status:
        q = q.where(LotQualityStatus.release_status == release_status)
    if hold_flag is not None:
        q = q.where(LotQualityStatus.hold_flag == hold_flag)
    if quarantine_flag is not None:
        q = q.where(LotQualityStatus.quarantine_flag == quarantine_flag)
    r = await db.execute(q.order_by(LotQualityStatus.created_at.desc()))
    return [LotQualityStatusRead.model_validate(lqs) for lqs in r.scalars()]


@router.post("/lot-status/release", response_model=LotQualityStatusRead)
async def release_lot(
    body: LotReleaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lqs = await svc.release_lot(db, body.lot_id, current_user.id, body.release_notes)
    await db.commit()
    r = await db.execute(select(LotQualityStatus).where(LotQualityStatus.lot_id == body.lot_id))
    return LotQualityStatusRead.model_validate(r.scalar_one())


@router.post("/lot-status/hold", response_model=LotQualityStatusRead)
async def hold_lot(
    body: LotHoldRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lqs = await svc.hold_lot(
        db, body.lot_id, body.hold_reason, body.quarantine, body.quarantine_location
    )
    await db.commit()
    r = await db.execute(select(LotQualityStatus).where(LotQualityStatus.lot_id == body.lot_id))
    return LotQualityStatusRead.model_validate(r.scalar_one())


# ── Allergen Validation ───────────────────────────────────────────────────────

@router.get("/allergen-validations", response_model=List[AllergenValidationRead])
async def list_allergen_validations(
    production_order_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(AllergenValidationRecord)
    if production_order_id:
        q = q.where(AllergenValidationRecord.production_order_id == production_order_id)
    r = await db.execute(q.order_by(AllergenValidationRecord.created_at.desc()))
    records = list(r.scalars())
    return [_build_av_read(rec) for rec in records]


@router.post("/allergen-validations", response_model=AllergenValidationRead, status_code=201)
async def create_allergen_validation(
    body: AllergenValidationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rec = await svc.create_allergen_validation(db, body.model_dump(), current_user.id)
    await db.commit()
    r = await db.execute(select(AllergenValidationRecord).where(AllergenValidationRecord.id == rec.id))
    return _build_av_read(r.scalar_one())


@router.patch("/allergen-validations/{val_id}", response_model=AllergenValidationRead)
async def update_allergen_validation(
    val_id: uuid.UUID,
    body: AllergenValidationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(AllergenValidationRecord).where(AllergenValidationRecord.id == val_id))
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Allergen validation not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rec, k, v)
    await db.commit()
    r = await db.execute(select(AllergenValidationRecord).where(AllergenValidationRecord.id == val_id))
    return _build_av_read(r.scalar_one())


# ── AI Recommendations ────────────────────────────────────────────────────────

@router.get("/ai/recommendations", response_model=List[QMSAIRecRead])
async def list_ai_recommendations(
    agent_type: Optional[QMSAIAgentType] = None,
    status: Optional[QMSAIRecStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(QMSAIRecommendation)
    if agent_type:
        q = q.where(QMSAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(QMSAIRecommendation.status == status)
    r = await db.execute(q.order_by(QMSAIRecommendation.created_at.desc()))
    return [QMSAIRecRead.model_validate(rec) for rec in r.scalars()]


@router.post("/ai/run/quality-risk", response_model=List[QMSAIRecRead], status_code=201)
async def run_quality_risk(
    production_order_id: Optional[uuid.UUID] = Query(None),
    lot_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    recs = await svc.run_quality_risk_predictor(db, production_order_id, lot_id)
    await db.commit()
    return [QMSAIRecRead.model_validate(r) for r in recs]


@router.post("/ai/run/deviation-analyzer", response_model=List[QMSAIRecRead], status_code=201)
async def run_deviation_analyzer(
    product_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    recs = await svc.run_deviation_analyzer(db, product_id)
    await db.commit()
    return [QMSAIRecRead.model_validate(r) for r in recs]


@router.post("/ai/run/haccp-assistant", response_model=List[QMSAIRecRead], status_code=201)
async def run_haccp_assistant(
    product_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    recs = await svc.run_haccp_assistant(db, product_id)
    await db.commit()
    return [QMSAIRecRead.model_validate(r) for r in recs]


@router.post("/ai/recommendations/{rec_id}/review", response_model=QMSAIRecRead)
async def review_ai_recommendation(
    rec_id: uuid.UUID,
    body: QMSAIRecReview,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import datetime, timezone
    r = await db.execute(select(QMSAIRecommendation).where(QMSAIRecommendation.id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "AI recommendation not found")
    rec.status = body.status
    rec.review_note = body.review_note
    rec.reviewed_by_id = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    r = await db.execute(select(QMSAIRecommendation).where(QMSAIRecommendation.id == rec_id))
    return QMSAIRecRead.model_validate(r.scalar_one())


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/qc-summary")
async def qc_summary_report(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    qc_type: Optional[QCType] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(QCInspection)
    if from_date:
        q = q.where(QCInspection.inspection_date >= from_date)
    if to_date:
        q = q.where(QCInspection.inspection_date <= to_date)
    if qc_type:
        q = q.where(QCInspection.qc_type == qc_type)
    r = await db.execute(q)
    insp = list(r.scalars())
    total = len(insp)
    by_status = {}
    for i in insp:
        key = i.status.value
        by_status[key] = by_status.get(key, 0) + 1
    passed = by_status.get("PASSED", 0)
    failed = by_status.get("FAILED", 0)
    return {
        "total": total,
        "by_status": by_status,
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "fail_rate": round(failed / total * 100, 2) if total else 0,
    }


@router.get("/reports/ccp-violations")
async def ccp_violation_report(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(CCPMonitoringLog).where(CCPMonitoringLog.is_violation == True)
    if from_date:
        q = q.where(func.date(CCPMonitoringLog.monitoring_datetime) >= from_date)
    if to_date:
        q = q.where(func.date(CCPMonitoringLog.monitoring_datetime) <= to_date)
    r = await db.execute(q.order_by(CCPMonitoringLog.monitoring_datetime.desc()))
    logs = list(r.scalars())
    by_ccp: dict = {}
    for log in logs:
        key = str(log.ccp_id)
        by_ccp[key] = by_ccp.get(key, 0) + 1
    return {
        "total_violations": len(logs),
        "violations_by_ccp": by_ccp,
        "recent_violations": [
            {
                "id": str(l.id),
                "ccp_id": str(l.ccp_id),
                "monitoring_datetime": l.monitoring_datetime.isoformat(),
                "recorded_value": float(l.recorded_value) if l.recorded_value else None,
                "deviation_amount": float(l.deviation_amount) if l.deviation_amount else None,
            }
            for l in logs[:20]
        ],
    }


@router.get("/reports/deviations")
async def deviation_report(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(QCDeviation)
    if from_date:
        q = q.where(func.date(QCDeviation.created_at) >= from_date)
    if to_date:
        q = q.where(func.date(QCDeviation.created_at) <= to_date)
    r = await db.execute(q)
    devs = list(r.scalars())
    by_severity: dict = {}
    by_type: dict = {}
    by_status: dict = {}
    for d in devs:
        by_severity[d.severity.value] = by_severity.get(d.severity.value, 0) + 1
        by_type[d.deviation_type] = by_type.get(d.deviation_type, 0) + 1
        by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
    return {
        "total": len(devs),
        "by_severity": by_severity,
        "by_type": by_type,
        "by_status": by_status,
        "open": by_status.get("OPEN", 0),
        "resolved": by_status.get("RESOLVED", 0),
    }


@router.get("/reports/lot-quality")
async def lot_quality_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(LotQualityStatus))
    statuses = list(r.scalars())
    by_release: dict = {}
    for s in statuses:
        key = s.release_status.value
        by_release[key] = by_release.get(key, 0) + 1
    return {
        "total_lots_tracked": len(statuses),
        "by_release_status": by_release,
        "fefo_eligible": sum(1 for s in statuses if s.fefo_eligible),
        "shipment_eligible": sum(1 for s in statuses if s.shipment_eligible),
        "on_hold": sum(1 for s in statuses if s.hold_flag),
        "quarantined": sum(1 for s in statuses if s.quarantine_flag),
    }


# ── Builders ──────────────────────────────────────────────────────────────────

def _build_template_read(t: QCTemplate) -> QCTemplateRead:
    r = QCTemplateRead.model_validate(t)
    r.product_name = t.product.name if t.product else None
    r.material_name = t.material.name if t.material else None
    return r


def _build_hazard_read(h: HazardAnalysis) -> HazardAnalysisRead:
    r = HazardAnalysisRead.model_validate(h)
    r.product_name = h.product.name if h.product else None
    r.material_name = h.material.name if h.material else None
    return r


def _build_ccp_read(c: CriticalControlPoint) -> CCPRead:
    r = CCPRead.model_validate(c)
    r.product_name = c.product.name if c.product else None
    return r


def _build_monitoring_read(l: CCPMonitoringLog, ccp: Optional[CriticalControlPoint]) -> CCPMonitoringRead:
    r = CCPMonitoringRead.model_validate(l)
    r.ccp_name = ccp.ccp_name if ccp else None
    r.recorded_by_name = l.recorded_by.full_name if l.recorded_by else None
    return r


def _build_deviation_read(d: QCDeviation) -> QCDeviationRead:
    r = QCDeviationRead.model_validate(d)
    r.product_name = d.product.name if d.product else None
    r.material_name = d.material.name if d.material else None
    r.assigned_to_name = d.assigned_to.full_name if d.assigned_to else None
    return r


def _build_ca_read(ca: CorrectiveAction) -> CorrectiveActionRead:
    r = CorrectiveActionRead.model_validate(ca)
    r.assigned_to_name = ca.assigned_to.full_name if ca.assigned_to else None
    r.product_name = ca.product.name if ca.product else None
    r.steps_total = len(ca.steps) if ca.steps else 0
    r.steps_completed = sum(1 for s in (ca.steps or []) if s.is_completed)
    return r


def _build_av_read(rec: AllergenValidationRecord) -> AllergenValidationRead:
    r = AllergenValidationRead.model_validate(rec)
    r.previous_product_name = rec.previous_product.name if rec.previous_product else None
    r.current_product_name = rec.current_product.name if rec.current_product else None
    return r


# ── Instrument Calibration ────────────────────────────────────────────────────

@router.get("/calibration", response_model=list)
async def list_calibrations(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from datetime import datetime, timedelta
    today = date.today()
    q = select(InstrumentCalibration)
    if status:
        q = q.where(InstrumentCalibration.status == status)
    r = await db.execute(q.order_by(InstrumentCalibration.next_calibration_due))
    instruments = list(r.scalars())
    rows = []
    for inst in instruments:
        days_until_due = None
        if inst.next_calibration_due:
            days_until_due = (inst.next_calibration_due - today).days
        rows.append({
            "id": str(inst.id),
            "instrument_id": inst.instrument_id,
            "instrument_name": inst.instrument_name,
            "instrument_type": inst.instrument_type,
            "location": inst.location,
            "serial_no": inst.serial_no,
            "last_calibration_date": inst.last_calibration_date.isoformat() if inst.last_calibration_date else None,
            "next_calibration_due": inst.next_calibration_due.isoformat() if inst.next_calibration_due else None,
            "calibration_interval_days": inst.calibration_interval_days,
            "calibration_authority": inst.calibration_authority,
            "certificate_ref": inst.certificate_ref,
            "status": inst.status,
            "days_until_due": days_until_due,
            "is_overdue": days_until_due is not None and days_until_due < 0,
            "is_active": inst.is_active,
            "notes": inst.notes,
        })
    return rows


@router.post("/calibration", status_code=201)
async def create_calibration(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import timedelta
    last_date = None
    if body.get("last_calibration_date"):
        from datetime import date as date_cls
        last_date = date_cls.fromisoformat(body["last_calibration_date"])
    interval = body.get("calibration_interval_days", 365)
    next_due = None
    if last_date:
        from datetime import timedelta
        next_due = last_date + timedelta(days=interval)
    status = "CURRENT"
    if next_due:
        days = (next_due - date.today()).days
        if days < 0:
            status = "OVERDUE"
        elif days <= 30:
            status = "DUE_SOON"
    inst = InstrumentCalibration(
        instrument_id=body["instrument_id"],
        instrument_name=body["instrument_name"],
        instrument_type=body.get("instrument_type", ""),
        location=body.get("location"),
        manufacturer=body.get("manufacturer"),
        model_no=body.get("model_no"),
        serial_no=body.get("serial_no"),
        last_calibration_date=last_date,
        next_calibration_due=next_due,
        calibration_interval_days=interval,
        calibration_authority=body.get("calibration_authority"),
        certificate_ref=body.get("certificate_ref"),
        status=status,
        notes=body.get("notes"),
        calibrated_by_id=current_user.id,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return {"id": str(inst.id), "instrument_id": inst.instrument_id, "status": inst.status}


@router.patch("/calibration/{instrument_id}")
async def update_calibration(
    instrument_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import timedelta
    r = await db.execute(select(InstrumentCalibration).where(InstrumentCalibration.id == instrument_id))
    inst = r.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "Instrument not found")
    allowed = ["instrument_name", "instrument_type", "location", "manufacturer", "model_no",
               "serial_no", "calibration_interval_days", "calibration_authority", "certificate_ref",
               "status", "is_active", "notes"]
    for k in allowed:
        if k in body:
            setattr(inst, k, body[k])
    if "last_calibration_date" in body and body["last_calibration_date"]:
        from datetime import date as date_cls
        last_date = date_cls.fromisoformat(body["last_calibration_date"])
        inst.last_calibration_date = last_date
        inst.next_calibration_due = last_date + timedelta(days=inst.calibration_interval_days)
        days = (inst.next_calibration_due - date.today()).days
        inst.status = "OVERDUE" if days < 0 else "DUE_SOON" if days <= 30 else "CURRENT"
        inst.calibrated_by_id = current_user.id
    await db.commit()
    await db.refresh(inst)
    return {"id": str(inst.id), "status": inst.status}


# ── AQL Sampling Plans ────────────────────────────────────────────────────────

@router.get("/aql-plans", response_model=list)
async def list_aql_plans(
    product_id: Optional[uuid.UUID] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    q = select(AQLSamplingPlan).options(
        selectinload(AQLSamplingPlan.product),
        selectinload(AQLSamplingPlan.material),
    )
    if product_id:
        q = q.where(AQLSamplingPlan.product_id == product_id)
    if active_only:
        q = q.where(AQLSamplingPlan.is_active == True)
    r = await db.execute(q.order_by(AQLSamplingPlan.lot_size_min))
    plans = list(r.scalars())
    return [
        {
            "id": str(p.id),
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "product_name": p.product.name if p.product else None,
            "lot_size_min": p.lot_size_min,
            "lot_size_max": p.lot_size_max,
            "sample_size": p.sample_size,
            "aql_level": p.aql_level,
            "aql_value": float(p.aql_value),
            "acceptance_number": p.acceptance_number,
            "rejection_number": p.rejection_number,
            "inspection_level": p.inspection_level,
            "applies_to_type": p.applies_to_type,
            "is_active": p.is_active,
            "notes": p.notes,
        }
        for p in plans
    ]


@router.post("/aql-plans", status_code=201)
async def create_aql_plan(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from decimal import Decimal
    plan = AQLSamplingPlan(
        plan_code=body["plan_code"],
        plan_name=body["plan_name"],
        product_id=uuid.UUID(body["product_id"]) if body.get("product_id") else None,
        material_id=uuid.UUID(body["material_id"]) if body.get("material_id") else None,
        product_category=body.get("product_category"),
        lot_size_min=int(body["lot_size_min"]),
        lot_size_max=int(body["lot_size_max"]) if body.get("lot_size_max") else None,
        sample_size=int(body["sample_size"]),
        aql_level=body.get("aql_level", "II"),
        aql_value=Decimal(str(body["aql_value"])),
        acceptance_number=int(body["acceptance_number"]),
        rejection_number=int(body["rejection_number"]),
        inspection_level=body.get("inspection_level", "Normal"),
        applies_to_type=body.get("applies_to_type", "INCOMING"),
        notes=body.get("notes"),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return {"id": str(plan.id), "plan_code": plan.plan_code}


@router.patch("/aql-plans/{plan_id}")
async def update_aql_plan(
    plan_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(AQLSamplingPlan).where(AQLSamplingPlan.id == plan_id))
    plan = r.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "AQL plan not found")
    allowed = ["plan_name", "sample_size", "aql_value", "acceptance_number", "rejection_number",
               "inspection_level", "is_active", "notes"]
    for k in allowed:
        if k in body:
            setattr(plan, k, body[k])
    await db.commit()
    return {"id": str(plan.id), "plan_code": plan.plan_code}


# ── Certificate of Analysis ───────────────────────────────────────────────────

@router.get("/coa", response_model=list)
async def list_coa(
    lot_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    q = select(CertificateOfAnalysis).options(
        selectinload(CertificateOfAnalysis.product),
        selectinload(CertificateOfAnalysis.lot),
    )
    if lot_id:
        q = q.where(CertificateOfAnalysis.lot_id == lot_id)
    if customer_id:
        q = q.where(CertificateOfAnalysis.customer_id == customer_id)
    if status:
        q = q.where(CertificateOfAnalysis.status == status)
    r = await db.execute(q.order_by(CertificateOfAnalysis.issue_date.desc()))
    coas = list(r.scalars())
    return [
        {
            "id": str(c.id),
            "coa_no": c.coa_no,
            "lot_id": str(c.lot_id),
            "lot_number": c.lot_number,
            "batch_no": c.batch_no,
            "product_name": c.product.name if c.product else None,
            "issue_date": c.issue_date.isoformat(),
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "manufacture_date": c.manufacture_date.isoformat() if c.manufacture_date else None,
            "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            "overall_result": c.overall_result,
            "status": c.status,
            "notes": c.notes,
        }
        for c in coas
    ]


@router.post("/coa", status_code=201)
async def create_coa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import date as date_cls
    test_snapshot = None
    inspection_id = uuid.UUID(body["inspection_id"]) if body.get("inspection_id") else None
    if inspection_id:
        insp_r = await db.execute(
            select(QCInspection).where(QCInspection.id == inspection_id)
        )
        insp = insp_r.scalar_one_or_none()
        if insp:
            results_r = await db.execute(
                select(QCTestResult).where(QCTestResult.inspection_id == inspection_id)
            )
            results = list(results_r.scalars())
            test_snapshot = [
                {
                    "parameter_name": t.parameter_name,
                    "unit": t.unit,
                    "numeric_value": float(t.numeric_value) if t.numeric_value else None,
                    "text_value": t.text_value,
                    "min_spec": float(t.min_spec) if t.min_spec else None,
                    "max_spec": float(t.max_spec) if t.max_spec else None,
                    "is_passed": t.is_passed,
                    "is_critical": t.is_critical,
                }
                for t in results
            ]
    coa = CertificateOfAnalysis(
        coa_no=body["coa_no"],
        lot_id=uuid.UUID(body["lot_id"]),
        product_id=uuid.UUID(body["product_id"]) if body.get("product_id") else None,
        inspection_id=inspection_id,
        issue_date=date_cls.fromisoformat(body["issue_date"]),
        valid_until=date_cls.fromisoformat(body["valid_until"]) if body.get("valid_until") else None,
        customer_id=uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
        lot_number=body.get("lot_number"),
        batch_no=body.get("batch_no"),
        manufacture_date=date_cls.fromisoformat(body["manufacture_date"]) if body.get("manufacture_date") else None,
        expiry_date=date_cls.fromisoformat(body["expiry_date"]) if body.get("expiry_date") else None,
        test_results_snapshot=test_snapshot,
        overall_result=body.get("overall_result", "PASS"),
        status="DRAFT",
        issued_by_id=current_user.id,
        notes=body.get("notes"),
    )
    db.add(coa)
    await db.commit()
    await db.refresh(coa)
    return {"id": str(coa.id), "coa_no": coa.coa_no, "status": coa.status}


@router.post("/coa/{coa_id}/issue")
async def issue_coa(
    coa_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(CertificateOfAnalysis).where(CertificateOfAnalysis.id == coa_id))
    coa = r.scalar_one_or_none()
    if not coa:
        raise HTTPException(404, "CoA not found")
    coa.status = "ISSUED"
    coa.approved_by_id = current_user.id
    await db.commit()
    return {"id": str(coa.id), "coa_no": coa.coa_no, "status": coa.status}
