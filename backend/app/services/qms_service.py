"""QMS Service — blocking logic, CCP enforcement, sampling, AI agents."""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    QCInspection, QCStatus, QCDecision, QCTemplate, QCTemplateParameter,
    HazardAnalysis, CriticalControlPoint, CCPMonitoringLog,
    CorrectiveAction, CorrectiveActionStatus, CorrectiveActionStep,
    QCDeviation, DeviationStatus, RiskLevel,
    LotQualityStatus, ReleaseStatus, AllergenValidationRecord,
    QMSAIRecommendation, QMSAIAgentType, QMSAIRecStatus,
    SamplingMethod,
)
from app.models.inventory import Lot


# ── Sequence Helpers ──────────────────────────────────────────────────────────

async def _next_seq(db: AsyncSession, model, no_col: str, prefix: str) -> str:
    result = await db.execute(
        select(func.count()).select_from(model)
    )
    count = result.scalar() or 0
    return f"{prefix}-{str(count + 1).zfill(5)}"


# ── QC Template CRUD ──────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, data: dict) -> QCTemplate:
    params = data.pop("parameters", [])
    tmpl = QCTemplate(**data)
    db.add(tmpl)
    await db.flush()
    for p in params:
        db.add(QCTemplateParameter(template_id=tmpl.id, **p))
    return tmpl


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> Optional[QCTemplate]:
    r = await db.execute(select(QCTemplate).where(QCTemplate.id == template_id))
    return r.scalar_one_or_none()


async def list_templates(db: AsyncSession, qc_type=None, active_only=True) -> List[QCTemplate]:
    q = select(QCTemplate)
    if active_only:
        q = q.where(QCTemplate.is_active == True)
    if qc_type:
        q = q.where(QCTemplate.qc_type == qc_type)
    r = await db.execute(q.order_by(QCTemplate.name))
    return list(r.scalars())


# ── Sampling ──────────────────────────────────────────────────────────────────

def calculate_sample_size(template: QCTemplate, total_qty: float = 0.0) -> float:
    if template.sampling_method == SamplingMethod.FIXED:
        return float(template.sample_size or 1)
    if template.sampling_method == SamplingMethod.PERCENTAGE:
        pct = float(template.sample_percentage or 5) / 100
        return max(1.0, total_qty * pct)
    return float(template.sample_size or 1)


# ── QC Blocking / Release Logic ───────────────────────────────────────────────

async def check_qc_gate(db: AsyncSession, lot_id: uuid.UUID, stage: Optional[str] = None) -> dict:
    """Check if a lot is allowed to proceed. Returns blocking status."""
    q = (
        select(QCInspection)
        .where(
            QCInspection.lot_id == lot_id,
            QCInspection.is_mandatory == True,
            QCInspection.blocks_progression == True,
        )
    )
    if stage:
        q = q.where(QCInspection.qc_sub_type == stage)
    r = await db.execute(q.order_by(QCInspection.created_at.desc()))
    inspections = list(r.scalars())

    if not inspections:
        return {"blocked": False, "reason": None, "inspection_id": None,
                "inspection_no": None, "inspection_status": None}

    for insp in inspections:
        if insp.status in (QCStatus.PENDING, QCStatus.IN_PROGRESS):
            return {
                "blocked": True,
                "reason": f"Mandatory QC inspection {insp.inspection_no} is still {insp.status.value}",
                "inspection_id": str(insp.id),
                "inspection_no": insp.inspection_no,
                "inspection_status": insp.status.value,
            }
        if insp.status == QCStatus.FAILED:
            return {
                "blocked": True,
                "reason": f"Mandatory QC inspection {insp.inspection_no} has FAILED",
                "inspection_id": str(insp.id),
                "inspection_no": insp.inspection_no,
                "inspection_status": insp.status.value,
            }

    return {"blocked": False, "reason": None, "inspection_id": None,
            "inspection_no": None, "inspection_status": None}


async def get_or_create_lot_quality_status(db: AsyncSession, lot_id: uuid.UUID) -> LotQualityStatus:
    r = await db.execute(select(LotQualityStatus).where(LotQualityStatus.lot_id == lot_id))
    lqs = r.scalar_one_or_none()
    if not lqs:
        lqs = LotQualityStatus(lot_id=lot_id)
        db.add(lqs)
        await db.flush()
    return lqs


async def hold_lot(db: AsyncSession, lot_id: uuid.UUID, hold_reason: str,
                   quarantine: bool = False, quarantine_location: Optional[str] = None) -> LotQualityStatus:
    lqs = await get_or_create_lot_quality_status(db, lot_id)
    lqs.hold_flag = True
    lqs.hold_reason = hold_reason
    lqs.release_status = ReleaseStatus.QUARANTINED if quarantine else ReleaseStatus.ON_HOLD
    lqs.quarantine_flag = quarantine
    lqs.quarantine_location = quarantine_location
    lqs.fefo_eligible = False
    lqs.shipment_eligible = False
    return lqs


async def release_lot(db: AsyncSession, lot_id: uuid.UUID,
                      released_by_id: uuid.UUID, notes: Optional[str] = None) -> LotQualityStatus:
    lqs = await get_or_create_lot_quality_status(db, lot_id)
    lqs.hold_flag = False
    lqs.quarantine_flag = False
    lqs.release_status = ReleaseStatus.RELEASED
    lqs.released_by_id = released_by_id
    lqs.released_at = datetime.now(timezone.utc)
    lqs.release_notes = notes
    lqs.fefo_eligible = True
    lqs.shipment_eligible = True
    return lqs


async def update_lot_qc_status_from_inspection(db: AsyncSession, inspection: QCInspection) -> None:
    """Sync lot quality status based on a completed inspection decision."""
    if not inspection.lot_id:
        return
    lqs = await get_or_create_lot_quality_status(db, inspection.lot_id)
    lqs.last_inspection_id = inspection.id

    if inspection.decision == QCDecision.ACCEPT:
        lqs.qc_status = "PASSED"
        lqs.hold_flag = False
        lqs.quarantine_flag = False
        lqs.release_status = ReleaseStatus.RELEASED
        lqs.fefo_eligible = True
        lqs.shipment_eligible = True

    elif inspection.decision == QCDecision.REJECT:
        lqs.qc_status = "FAILED"
        lqs.hold_flag = True
        lqs.quarantine_flag = True
        lqs.release_status = ReleaseStatus.QUARANTINED
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False

    elif inspection.decision == QCDecision.CONDITIONAL_RELEASE:
        lqs.qc_status = "CONDITIONAL"
        lqs.hold_flag = False
        lqs.release_status = ReleaseStatus.ON_HOLD
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False

    elif inspection.decision == QCDecision.REWORK:
        lqs.qc_status = "FAILED"
        lqs.hold_flag = True
        lqs.release_status = ReleaseStatus.REWORK
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False


# ── HACCP / CCP ───────────────────────────────────────────────────────────────

async def create_hazard_analysis(db: AsyncSession, data: dict, created_by_id: uuid.UUID) -> HazardAnalysis:
    no = await _next_seq(db, HazardAnalysis, "hazard_no", "HA")
    score = None
    if data.get("likelihood_score") and data.get("severity_score"):
        score = data["likelihood_score"] * data["severity_score"]
    hazard = HazardAnalysis(
        hazard_no=no,
        risk_score=score,
        created_by_id=created_by_id,
        **data,
    )
    db.add(hazard)
    return hazard


async def create_ccp(db: AsyncSession, data: dict) -> CriticalControlPoint:
    no = await _next_seq(db, CriticalControlPoint, "ccp_no", "CCP")
    ccp = CriticalControlPoint(ccp_no=no, **data)
    db.add(ccp)
    return ccp


def check_ccp_limits(ccp: CriticalControlPoint, value: float) -> tuple[bool, float]:
    """Returns (is_within_limits, deviation_amount)."""
    within = True
    deviation = 0.0
    if ccp.critical_limit_min is not None and value < float(ccp.critical_limit_min):
        within = False
        deviation = abs(float(ccp.critical_limit_min) - value)
    if ccp.critical_limit_max is not None and value > float(ccp.critical_limit_max):
        within = False
        deviation = max(deviation, abs(value - float(ccp.critical_limit_max)))
    return within, deviation


async def record_ccp_monitoring(
    db: AsyncSession,
    ccp: CriticalControlPoint,
    data: dict,
    recorded_by_id: uuid.UUID,
) -> CCPMonitoringLog:
    value = float(data.get("recorded_value") or 0)
    within, deviation = check_ccp_limits(ccp, value)

    log = CCPMonitoringLog(
        ccp_id=ccp.id,
        recorded_by_id=recorded_by_id,
        is_within_limits=within,
        is_violation=not within,
        deviation_amount=Decimal(str(deviation)) if deviation else None,
        **data,
    )
    db.add(log)
    await db.flush()

    if not within:
        ca = await _auto_create_corrective_action_for_ccp(db, ccp, log)
        log.corrective_action_id = ca.id
        log.process_blocked = True

    return log


async def _auto_create_corrective_action_for_ccp(
    db: AsyncSession, ccp: CriticalControlPoint, log: CCPMonitoringLog
) -> CorrectiveAction:
    no = await _next_seq(db, CorrectiveAction, "ca_no", "CA")
    ca = CorrectiveAction(
        ca_no=no,
        title=f"CCP Violation: {ccp.ccp_name} — {ccp.parameter_name} out of limits",
        description=(
            f"CCP {ccp.ccp_no} violation detected at {log.monitoring_datetime}. "
            f"Recorded value: {log.recorded_value} {ccp.parameter_unit or ''}. "
            f"Critical limits: min={ccp.critical_limit_min}, max={ccp.critical_limit_max}."
        ),
        severity=RiskLevel.CRITICAL,
        trigger_type="CCP_VIOLATION",
        trigger_id=log.id,
        production_order_id=log.production_order_id,
        lot_id=log.lot_id,
        assigned_to_id=ccp.responsible_user_id,
    )
    db.add(ca)
    await db.flush()

    steps_text = ccp.corrective_action_description.split(";") if ccp.corrective_action_description else []
    for i, step in enumerate(steps_text[:5], 1):
        step = step.strip()
        if step:
            db.add(CorrectiveActionStep(
                corrective_action_id=ca.id,
                step_no=i,
                step_description=step,
                assigned_to_id=ccp.responsible_user_id,
            ))
    return ca


# ── Corrective Actions ────────────────────────────────────────────────────────

async def create_corrective_action(db: AsyncSession, data: dict) -> CorrectiveAction:
    steps = data.pop("steps", [])
    no = await _next_seq(db, CorrectiveAction, "ca_no", "CA")
    ca = CorrectiveAction(ca_no=no, **data)
    db.add(ca)
    await db.flush()
    for s in steps:
        db.add(CorrectiveActionStep(corrective_action_id=ca.id, **s))
    return ca


async def complete_ca_step(db: AsyncSession, step_id: uuid.UUID,
                           completion_notes: Optional[str] = None) -> CorrectiveActionStep:
    r = await db.execute(select(CorrectiveActionStep).where(CorrectiveActionStep.id == step_id))
    step = r.scalar_one_or_none()
    if step:
        step.is_completed = True
        step.completed_at = datetime.now(timezone.utc)
        step.completion_notes = completion_notes
        await _check_ca_completion(db, step.corrective_action_id)
    return step


async def _check_ca_completion(db: AsyncSession, ca_id: uuid.UUID) -> None:
    r = await db.execute(
        select(CorrectiveActionStep).where(CorrectiveActionStep.corrective_action_id == ca_id)
    )
    steps = list(r.scalars())
    if steps and all(s.is_completed for s in steps):
        r2 = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
        ca = r2.scalar_one_or_none()
        if ca and ca.status == CorrectiveActionStatus.IN_PROGRESS:
            ca.status = CorrectiveActionStatus.COMPLETED
            ca.completed_at = datetime.now(timezone.utc)


# ── QC Deviations ─────────────────────────────────────────────────────────────

async def create_deviation(db: AsyncSession, data: dict, reported_by_id: uuid.UUID) -> QCDeviation:
    no = await _next_seq(db, QCDeviation, "deviation_no", "DEV")
    dev = QCDeviation(deviation_no=no, reported_by_id=reported_by_id, **data)
    db.add(dev)
    return dev


async def auto_create_deviation_from_inspection(
    db: AsyncSession, inspection: QCInspection, reported_by_id: uuid.UUID
) -> QCDeviation:
    no = await _next_seq(db, QCDeviation, "deviation_no", "DEV")
    critical_fails = [t for t in (inspection.test_results or []) if t.is_critical and t.is_passed is False]
    severity = RiskLevel.CRITICAL if critical_fails else RiskLevel.HIGH
    dev = QCDeviation(
        deviation_no=no,
        inspection_id=inspection.id,
        production_order_id=inspection.production_order_id,
        lot_id=inspection.lot_id,
        product_id=inspection.product_id,
        material_id=inspection.material_id,
        deviation_type="QC_FAILURE",
        severity=severity,
        description=f"QC inspection {inspection.inspection_no} failed. "
                    f"Critical failures: {len(critical_fails)}",
        reported_by_id=reported_by_id,
    )
    db.add(dev)
    return dev


# ── Allergen Validation ───────────────────────────────────────────────────────

async def create_allergen_validation(
    db: AsyncSession, data: dict, validated_by_id: uuid.UUID
) -> AllergenValidationRecord:
    no = await _next_seq(db, AllergenValidationRecord, "validation_no", "AV")
    rec = AllergenValidationRecord(
        validation_no=no,
        validated_by_id=validated_by_id,
        **data,
    )
    db.add(rec)
    return rec


# ── QMS Dashboard ─────────────────────────────────────────────────────────────

async def get_qms_dashboard(db: AsyncSession) -> dict:
    today = date.today()

    total = (await db.execute(select(func.count()).select_from(QCInspection))).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.status == QCStatus.PENDING)
    )).scalar() or 0
    passed_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.PASSED)
    )).scalar() or 0
    failed_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.FAILED)
    )).scalar() or 0
    cond_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.CONDITIONAL_RELEASE)
    )).scalar() or 0

    from datetime import timedelta
    week_ago = today - timedelta(days=7)
    total_7d = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date >= week_ago, QCInspection.status.in_([QCStatus.PASSED, QCStatus.FAILED]))
    )).scalar() or 0
    passed_7d = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date >= week_ago, QCInspection.status == QCStatus.PASSED)
    )).scalar() or 0
    pass_rate = round((passed_7d / total_7d * 100), 1) if total_7d else 0.0

    open_devs = (await db.execute(
        select(func.count()).select_from(QCDeviation)
        .where(QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]))
    )).scalar() or 0
    crit_devs = (await db.execute(
        select(func.count()).select_from(QCDeviation)
        .where(QCDeviation.severity == RiskLevel.CRITICAL,
               QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]))
    )).scalar() or 0

    open_cas = (await db.execute(
        select(func.count()).select_from(CorrectiveAction)
        .where(CorrectiveAction.status.in_([CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS]))
    )).scalar() or 0
    overdue_cas = (await db.execute(
        select(func.count()).select_from(CorrectiveAction)
        .where(CorrectiveAction.due_date < today,
               CorrectiveAction.status.in_([CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS]))
    )).scalar() or 0

    active_ccps = (await db.execute(
        select(func.count()).select_from(CriticalControlPoint)
        .where(CriticalControlPoint.is_active == True)
    )).scalar() or 0
    ccp_violations = (await db.execute(
        select(func.count()).select_from(CCPMonitoringLog)
        .where(CCPMonitoringLog.is_violation == True,
               func.date(CCPMonitoringLog.monitoring_datetime) >= week_ago)
    )).scalar() or 0

    hold_lots = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.hold_flag == True)
    )).scalar() or 0
    quarantine_lots = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.quarantine_flag == True)
    )).scalar() or 0
    pending_release = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.release_status == ReleaseStatus.UNRELEASED)
    )).scalar() or 0

    av_pending = (await db.execute(
        select(func.count()).select_from(AllergenValidationRecord)
        .where(AllergenValidationRecord.validation_passed == None)
    )).scalar() or 0

    ai_pending = (await db.execute(
        select(func.count()).select_from(QMSAIRecommendation)
        .where(QMSAIRecommendation.status == QMSAIRecStatus.PENDING)
    )).scalar() or 0

    return dict(
        total_inspections=total,
        pending_inspections=pending,
        passed_today=passed_today,
        failed_today=failed_today,
        conditional_today=cond_today,
        pass_rate_7d=pass_rate,
        open_deviations=open_devs,
        critical_deviations=crit_devs,
        open_corrective_actions=open_cas,
        overdue_corrective_actions=overdue_cas,
        active_ccps=active_ccps,
        ccp_violations_7d=ccp_violations,
        lots_on_hold=hold_lots,
        lots_quarantined=quarantine_lots,
        lots_pending_release=pending_release,
        allergen_validations_pending=av_pending,
        ai_recommendations_pending=ai_pending,
    )


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_quality_risk_predictor(
    db: AsyncSession, production_order_id: Optional[uuid.UUID] = None, lot_id: Optional[uuid.UUID] = None
) -> List[QMSAIRecommendation]:
    """Agent 1: Predict likely QC failures and high-risk batches."""
    recs: List[QMSAIRecommendation] = []

    # Analyze historical failure rate for this product/lot
    if lot_id:
        r = await db.execute(
            select(QCInspection).where(QCInspection.lot_id == lot_id)
        )
        insp_list = list(r.scalars())
        fails = [i for i in insp_list if i.status == QCStatus.FAILED]
        if fails:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
                lot_id=lot_id,
                production_order_id=production_order_id,
                title="High QC failure rate detected for this lot",
                explanation=f"{len(fails)} out of {len(insp_list)} inspections failed for this lot.",
                recommendation="Perform additional IQC checks before releasing. "
                               "Review supplier quality for incoming materials.",
                risk_level=RiskLevel.HIGH,
                confidence_score=Decimal("82.5"),
                priority_score=8,
                payload={"fail_count": len(fails), "total": len(insp_list)},
            )
            db.add(rec)
            recs.append(rec)

    # Check for open deviations linked to production order
    if production_order_id:
        r = await db.execute(
            select(QCDeviation).where(
                QCDeviation.production_order_id == production_order_id,
                QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]),
            )
        )
        open_devs = list(r.scalars())
        if open_devs:
            crit_devs = [d for d in open_devs if d.severity == RiskLevel.CRITICAL]
            title = "Open deviations linked to this production order"
            risk = RiskLevel.CRITICAL if crit_devs else RiskLevel.HIGH
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
                production_order_id=production_order_id,
                title=title,
                explanation=f"{len(open_devs)} open deviation(s) including {len(crit_devs)} critical.",
                recommendation="Resolve all open deviations before releasing finished goods. "
                               "Ensure corrective actions are documented and verified.",
                risk_level=risk,
                confidence_score=Decimal("90.0"),
                priority_score=9,
                payload={"open_deviations": len(open_devs), "critical": len(crit_devs)},
            )
            db.add(rec)
            recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
            production_order_id=production_order_id,
            lot_id=lot_id,
            title="No high-risk indicators detected",
            explanation="Based on historical QC data, this batch appears to be low-risk.",
            recommendation="Proceed with standard QC protocols. "
                           "Monitor CCP parameters during production.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("75.0"),
            priority_score=2,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs


async def run_deviation_analyzer(db: AsyncSession, product_id: Optional[uuid.UUID] = None) -> List[QMSAIRecommendation]:
    """Agent 2: Detect recurring failures and process instability."""
    recs: List[QMSAIRecommendation] = []

    q = select(QCDeviation)
    if product_id:
        q = q.where(QCDeviation.product_id == product_id)
    r = await db.execute(q.where(QCDeviation.status != DeviationStatus.CLOSED))
    devs = list(r.scalars())

    # Group by type
    by_type: dict = {}
    for d in devs:
        by_type.setdefault(d.deviation_type, []).append(d)

    for dtype, group in by_type.items():
        if len(group) >= 2:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
                title=f"Recurring deviation pattern: {dtype}",
                explanation=f"{len(group)} deviations of type '{dtype}' found. "
                            f"This indicates a systemic process issue.",
                recommendation="Investigate root cause systematically. "
                               "Consider process re-validation or supplier change. "
                               "Update HACCP plan if applicable.",
                risk_level=RiskLevel.HIGH if len(group) >= 3 else RiskLevel.MEDIUM,
                confidence_score=Decimal(str(min(95, 60 + len(group) * 10))),
                priority_score=min(10, 5 + len(group)),
                payload={"deviation_type": dtype, "count": len(group)},
            )
            db.add(rec)
            recs.append(rec)

    # Check CCP violation frequency
    r2 = await db.execute(
        select(CCPMonitoringLog).where(CCPMonitoringLog.is_violation == True)
    )
    violations = list(r2.scalars())
    by_ccp: dict = {}
    for v in violations:
        by_ccp.setdefault(str(v.ccp_id), []).append(v)

    for ccp_id, viol_list in by_ccp.items():
        if len(viol_list) >= 2:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
                ccp_id=uuid.UUID(ccp_id),
                title=f"Repeated CCP violations detected ({len(viol_list)} times)",
                explanation=f"CCP {ccp_id[:8]}… has violated critical limits {len(viol_list)} times.",
                recommendation="Review CCP critical limits. Re-calibrate monitoring equipment. "
                               "Retrain responsible personnel. Consider process capability study.",
                risk_level=RiskLevel.CRITICAL,
                confidence_score=Decimal("88.0"),
                priority_score=10,
                payload={"ccp_id": ccp_id, "violation_count": len(viol_list)},
            )
            db.add(rec)
            recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
            title="Process appears stable — no recurring deviations",
            explanation="No significant deviation patterns detected in recent data.",
            recommendation="Continue current quality monitoring protocols. "
                           "Review deviations monthly for early trend detection.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("70.0"),
            priority_score=1,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs


async def run_haccp_assistant(db: AsyncSession, product_id: Optional[uuid.UUID] = None) -> List[QMSAIRecommendation]:
    """Agent 3: Suggest missing CCPs and weak control points."""
    recs: List[QMSAIRecommendation] = []

    # Load existing hazard analyses
    q = select(HazardAnalysis).where(HazardAnalysis.is_active == True)
    if product_id:
        q = q.where(HazardAnalysis.product_id == product_id)
    r = await db.execute(q)
    hazards = list(r.scalars())

    # Load existing CCPs
    ccp_q = select(CriticalControlPoint).where(CriticalControlPoint.is_active == True)
    if product_id:
        ccp_q = ccp_q.where(CriticalControlPoint.product_id == product_id)
    r2 = await db.execute(ccp_q)
    ccps = list(r2.scalars())

    # Find high-risk hazards without CCP
    high_risk_no_ccp = [
        h for h in hazards
        if h.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not h.is_ccp
    ]
    if high_risk_no_ccp:
        for h in high_risk_no_ccp[:3]:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.HACCP_ASSISTANT,
                title=f"Potential missing CCP: {h.process_step} — {h.hazard_type.value}",
                explanation=f"Hazard {h.hazard_no} at '{h.process_step}' is rated {h.risk_level.value} "
                            f"but has no associated CCP.",
                recommendation=f"Evaluate whether a Critical Control Point is needed at '{h.process_step}'. "
                               f"Suggested control: {h.control_measure}. "
                               f"Define critical limits, monitoring frequency, and corrective action.",
                risk_level=h.risk_level,
                confidence_score=Decimal("85.0"),
                priority_score=9,
                payload={"hazard_id": str(h.id), "hazard_no": h.hazard_no,
                         "process_step": h.process_step, "hazard_type": h.hazard_type.value},
            )
            db.add(rec)
            recs.append(rec)

    # CCPs with no recent monitoring logs
    for ccp in ccps:
        r3 = await db.execute(
            select(func.count()).select_from(CCPMonitoringLog)
            .where(CCPMonitoringLog.ccp_id == ccp.id)
        )
        log_count = r3.scalar() or 0
        if log_count == 0:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.HACCP_ASSISTANT,
                ccp_id=ccp.id,
                title=f"CCP {ccp.ccp_no} has no monitoring records",
                explanation=f"CCP '{ccp.ccp_name}' exists but has no monitoring logs recorded.",
                recommendation=f"Begin monitoring {ccp.parameter_name} as per schedule ({ccp.monitoring_frequency}). "
                               f"Ensure records are maintained for regulatory compliance.",
                risk_level=RiskLevel.HIGH,
                confidence_score=Decimal("92.0"),
                priority_score=8,
                payload={"ccp_id": str(ccp.id), "ccp_no": ccp.ccp_no},
            )
            db.add(rec)
            recs.append(rec)

    # Allergen-related CCP check
    allergen_ccps = [c for c in ccps if c.allergen_related]
    if not allergen_ccps and ccps:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.HACCP_ASSISTANT,
            title="No allergen-specific CCPs defined",
            explanation="No CCPs are marked as allergen-related. "
                        "If allergens are present in your facility, this may be a compliance gap.",
            recommendation="Review your allergen risk assessment. "
                           "Define a CCP for allergen cross-contact control including "
                           "cleaning validation and verification testing.",
            risk_level=RiskLevel.HIGH,
            confidence_score=Decimal("78.0"),
            priority_score=7,
            payload={"total_ccps": len(ccps)},
        )
        db.add(rec)
        recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.HACCP_ASSISTANT,
            title="HACCP plan appears adequate",
            explanation="All high-risk hazards have associated CCPs and monitoring is active.",
            recommendation="Review the HACCP plan annually or when process changes occur. "
                           "Verify CCP effectiveness through periodic re-validation.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("72.0"),
            priority_score=2,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs
