from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dunning import (
    DunningPolicyCreate, DunningPolicyUpdate, DunningPolicyOut,
    DunningLevelCreate, DunningLevelOut,
    DunningTemplateCreate, DunningTemplateOut,
    DunningCaseOut, DunningCaseNoteUpdate, DunningCaseAssign,
    DunningCaseInvoiceOut, DunningDisputeSet,
    DunningActionLogOut, DunningReminderRequest, DunningManualNote,
    DunningPTPCreate, DunningPTPUpdate, DunningPTPOut,
    DunningExceptionCreate, DunningExceptionOut,
    CreditHoldApply, CreditHoldRelease,
    DunningAIRecAck, DunningAIRecOut,
)
import app.services.dunning_service as svc

router = APIRouter()


# ── Policies ───────────────────────────────────────────────────────────────────

@router.get("/policies", response_model=List[DunningPolicyOut])
async def list_policies(active_only: bool = Query(False), db: AsyncSession = Depends(get_db)):
    return await svc.list_policies(db, active_only=active_only)


@router.post("/policies", response_model=DunningPolicyOut)
async def create_policy(payload: DunningPolicyCreate, db: AsyncSession = Depends(get_db)):
    pol = await svc.create_policy(db, payload)
    await db.commit()
    await db.refresh(pol)
    return pol


@router.get("/policies/{policy_id}", response_model=DunningPolicyOut)
async def get_policy(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    pol = await svc.get_policy(db, policy_id)
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@router.put("/policies/{policy_id}", response_model=DunningPolicyOut)
async def update_policy(policy_id: uuid.UUID, payload: DunningPolicyUpdate, db: AsyncSession = Depends(get_db)):
    pol = await svc.update_policy(db, policy_id, payload)
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.commit()
    await db.refresh(pol)
    return pol


@router.get("/policies/{policy_id}/levels", response_model=List[DunningLevelOut])
async def list_levels(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_levels(db, policy_id)


@router.post("/policies/{policy_id}/levels", response_model=DunningLevelOut)
async def add_level(policy_id: uuid.UUID, payload: DunningLevelCreate, db: AsyncSession = Depends(get_db)):
    lvl = await svc.add_level(db, policy_id, payload)
    await db.commit()
    await db.refresh(lvl)
    return lvl


# ── Templates ──────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[DunningTemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    return await svc.list_templates(db)


@router.post("/templates", response_model=DunningTemplateOut)
async def create_template(payload: DunningTemplateCreate, db: AsyncSession = Depends(get_db)):
    tmpl = await svc.create_template(db, payload)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


# ── Overdue Detection ──────────────────────────────────────────────────────────

@router.post("/run-overdue-detection")
async def run_overdue_detection(db: AsyncSession = Depends(get_db)):
    result = await svc.run_overdue_detection(db)
    await db.commit()
    return result


@router.post("/check-broken-ptps")
async def check_broken_ptps(db: AsyncSession = Depends(get_db)):
    count = await svc.check_broken_ptps(db)
    await db.commit()
    return {"broken_ptps_flagged": count}


# ── Cases ──────────────────────────────────────────────────────────────────────

@router.get("/cases", response_model=List[DunningCaseOut])
async def list_cases(
    status: Optional[str] = Query(None),
    collector_id: Optional[uuid.UUID] = Query(None),
    credit_hold: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_cases(db, status=status, collector_id=collector_id, credit_hold=credit_hold, limit=limit)


@router.get("/cases/{case_id}", response_model=DunningCaseOut)
async def get_case(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    case = await svc.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/cases/{case_id}/notes", response_model=DunningCaseOut)
async def update_notes(case_id: uuid.UUID, payload: DunningCaseNoteUpdate, db: AsyncSession = Depends(get_db)):
    case = await svc.update_case_notes(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/cases/{case_id}/assign", response_model=DunningCaseOut)
async def assign_case(case_id: uuid.UUID, payload: DunningCaseAssign, db: AsyncSession = Depends(get_db)):
    case = await svc.assign_case(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/cases/{case_id}/close", response_model=DunningCaseOut)
async def close_case(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    case = await svc.close_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.commit()
    await db.refresh(case)
    return case


# ── Case Invoices ──────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/invoices", response_model=List[DunningCaseInvoiceOut])
async def get_case_invoices(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_case_invoices(db, case_id)


@router.post("/cases/{case_id}/dispute", response_model=DunningCaseInvoiceOut)
async def set_dispute(case_id: uuid.UUID, payload: DunningDisputeSet, db: AsyncSession = Depends(get_db)):
    link = await svc.set_dispute(db, case_id, payload)
    if not link:
        raise HTTPException(status_code=404, detail="Invoice link not found")
    await db.commit()
    await db.refresh(link)
    return link


# ── Actions ────────────────────────────────────────────────────────────────────

@router.post("/cases/{case_id}/send-reminder", response_model=DunningActionLogOut)
async def send_reminder(case_id: uuid.UUID, payload: DunningReminderRequest, db: AsyncSession = Depends(get_db)):
    try:
        log = await svc.send_reminder(db, case_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(log)
    return log


@router.post("/cases/{case_id}/add-note", response_model=DunningActionLogOut)
async def add_note(case_id: uuid.UUID, payload: DunningManualNote, db: AsyncSession = Depends(get_db)):
    try:
        log = await svc.add_manual_note(db, case_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/cases/{case_id}/actions", response_model=List[DunningActionLogOut])
async def list_actions(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_action_logs(db, case_id)


# ── PTP ────────────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/ptps", response_model=List[DunningPTPOut])
async def list_ptps(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_ptps(db, case_id)


@router.post("/cases/{case_id}/set-promise-to-pay", response_model=DunningPTPOut)
async def create_ptp(case_id: uuid.UUID, payload: DunningPTPCreate, db: AsyncSession = Depends(get_db)):
    try:
        ptp = await svc.create_ptp(db, case_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(ptp)
    return ptp


@router.patch("/ptps/{ptp_id}", response_model=DunningPTPOut)
async def update_ptp(ptp_id: uuid.UUID, payload: DunningPTPUpdate, db: AsyncSession = Depends(get_db)):
    ptp = await svc.update_ptp(db, ptp_id, payload)
    if not ptp:
        raise HTTPException(status_code=404, detail="PTP not found")
    await db.commit()
    await db.refresh(ptp)
    return ptp


# ── Exceptions ─────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/exceptions", response_model=List[DunningExceptionOut])
async def list_exceptions(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_exceptions(db, case_id)


@router.post("/cases/{case_id}/exceptions", response_model=DunningExceptionOut)
async def create_exception(case_id: uuid.UUID, payload: DunningExceptionCreate, db: AsyncSession = Depends(get_db)):
    exc = await svc.create_exception(db, case_id, payload)
    await db.commit()
    await db.refresh(exc)
    return exc


# ── Credit Hold ────────────────────────────────────────────────────────────────

@router.post("/cases/{case_id}/apply-credit-hold", response_model=DunningCaseOut)
async def apply_credit_hold(case_id: uuid.UUID, payload: CreditHoldApply, db: AsyncSession = Depends(get_db)):
    case = await svc.apply_credit_hold(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/cases/{case_id}/release-credit-hold", response_model=DunningCaseOut)
async def release_credit_hold(case_id: uuid.UUID, payload: CreditHoldRelease, db: AsyncSession = Depends(get_db)):
    case = await svc.release_credit_hold(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.commit()
    await db.refresh(case)
    return case


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/ai/run")
async def run_ai(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_ai_agents(db)
    await db.commit()
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[DunningAIRecOut])
async def list_ai_recs(case_id: Optional[uuid.UUID] = Query(None), db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, case_id=case_id)


@router.post("/ai/recommendations/{rec_id}/ack", response_model=DunningAIRecOut)
async def ack_rec(rec_id: uuid.UUID, payload: DunningAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/dashboard")
async def report_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.report_dashboard(db)


@router.get("/reports/aging")
async def report_aging(db: AsyncSession = Depends(get_db)):
    return await svc.aging_report(db)


@router.get("/reports/effectiveness")
async def report_effectiveness(db: AsyncSession = Depends(get_db)):
    return await svc.report_effectiveness(db)


@router.get("/reports/workqueue")
async def report_workqueue(
    collector_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.report_collector_workqueue(db, collector_id=collector_id)


@router.get("/reports/ptp-fulfillment")
async def report_ptp(db: AsyncSession = Depends(get_db)):
    return await svc.report_ptp_fulfillment(db)
