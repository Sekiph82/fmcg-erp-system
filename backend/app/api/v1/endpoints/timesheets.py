from typing import List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.timesheets import (
    TimesheetCreate, TimesheetSubmit, TimesheetApprove, TimesheetReject,
    TimesheetFinalize, TimesheetOut,
    TimesheetLineCreate, TimesheetLineUpdate, TimesheetLineOut,
    ApprovalLogOut, TimesheetDashboard, TSAIRecOut, TSAIRecAck,
)
import app.services.timesheets_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=TimesheetDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Timesheets ────────────────────────────────────────────────────────────────

@router.post("/", response_model=TimesheetOut, status_code=201)
async def create_timesheet(data: TimesheetCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_timesheet(db, data)


@router.get("/", response_model=List[TimesheetOut])
async def list_timesheets(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    period_start: Optional[date] = None,
    department_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_timesheets(db, employee_id, status, period_start, department_id)


@router.get("/{timesheet_id}", response_model=TimesheetOut)
async def get_timesheet(timesheet_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_timesheet(db, timesheet_id)
    if not obj:
        raise HTTPException(404, "Timesheet not found")
    return obj


@router.post("/{timesheet_id}/submit", response_model=TimesheetOut)
async def submit(timesheet_id: UUID, data: TimesheetSubmit, db: AsyncSession = Depends(get_db)):
    obj = await svc.submit_timesheet(db, timesheet_id, data)
    if not obj:
        raise HTTPException(400, "Cannot submit in current status")
    return obj


@router.post("/{timesheet_id}/approve", response_model=TimesheetOut)
async def approve(timesheet_id: UUID, data: TimesheetApprove, db: AsyncSession = Depends(get_db)):
    obj = await svc.approve_timesheet(db, timesheet_id, data)
    if not obj:
        raise HTTPException(400, "Cannot approve in current status")
    return obj


@router.post("/{timesheet_id}/reject", response_model=TimesheetOut)
async def reject(timesheet_id: UUID, data: TimesheetReject, db: AsyncSession = Depends(get_db)):
    obj = await svc.reject_timesheet(db, timesheet_id, data)
    if not obj:
        raise HTTPException(400, "Cannot reject in current status")
    return obj


@router.post("/{timesheet_id}/finalize", response_model=TimesheetOut)
async def finalize(timesheet_id: UUID, data: TimesheetFinalize, db: AsyncSession = Depends(get_db)):
    obj = await svc.finalize_timesheet(db, timesheet_id, data)
    if not obj:
        raise HTTPException(400, "Cannot finalize in current status")
    return obj


# ── Lines ─────────────────────────────────────────────────────────────────────

@router.post("/{timesheet_id}/lines", response_model=TimesheetLineOut, status_code=201)
async def add_line(timesheet_id: UUID, data: TimesheetLineCreate, db: AsyncSession = Depends(get_db)):
    try:
        obj = await svc.add_line(db, timesheet_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not obj:
        raise HTTPException(404, "Timesheet not found")
    return obj


@router.patch("/lines/{line_id}", response_model=TimesheetLineOut)
async def update_line(line_id: UUID, data: TimesheetLineUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_line(db, line_id, data)
    if not obj:
        raise HTTPException(404, "Line not found")
    return obj


@router.delete("/lines/{line_id}", status_code=204)
async def delete_line(line_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_line(db, line_id)
    if not ok:
        raise HTTPException(404, "Line not found")


@router.post("/{timesheet_id}/auto-fill")
async def auto_fill(timesheet_id: UUID, attendance_hours: List[dict], db: AsyncSession = Depends(get_db)):
    count = await svc.auto_fill_from_attendance(db, timesheet_id, attendance_hours)
    return {"lines_added": count}


# ── Approval Queue ────────────────────────────────────────────────────────────

@router.get("/approval-queue/pending", response_model=List[TimesheetOut])
async def approval_queue(department_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_timesheets(db, status="submitted", department_id=department_id)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/summary")
async def report_summary(period_start: Optional[date] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_summary(db, period_start)


@router.get("/reports/utilization")
async def report_utilization(period_start: Optional[date] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_utilization(db, period_start)


@router.get("/reports/overtime")
async def report_overtime(period_start: Optional[date] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_overtime(db, period_start)


@router.get("/reports/project-time")
async def report_project_time(project_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_project_time_report(db, project_id)


@router.get("/reports/activity-summary")
async def report_activity_summary(period_start: Optional[date] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_activity_summary(db, period_start)


@router.get("/payroll-input")
async def payroll_input(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_payroll_input(db, period_start, period_end)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-utilization-analyzer", response_model=List[TSAIRecOut])
async def run_utilization_analyzer(db: AsyncSession = Depends(get_db)):
    return await svc.run_utilization_analyzer(db)


@router.post("/ai/run-anomaly-detector", response_model=List[TSAIRecOut])
async def run_anomaly_detector(db: AsyncSession = Depends(get_db)):
    return await svc.run_anomaly_detector(db)


@router.get("/ai/recommendations", response_model=List[TSAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=TSAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: TSAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
