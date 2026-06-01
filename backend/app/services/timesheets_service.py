from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.timesheets import (
    TimesheetHeader, TimesheetLine, TimesheetApprovalLog, TSAIRecommendation,
    TimesheetStatus, ActivityType, ApprovalAction, TSAIAgentType, TSAIRecStatus,
)
from app.schemas.timesheets import (
    TimesheetCreate, TimesheetSubmit, TimesheetApprove, TimesheetReject,
    TimesheetFinalize, TimesheetLineCreate, TimesheetLineUpdate, TSAIRecAck,
)

MAX_DAILY_HOURS = Decimal("16")
OVERTIME_THRESHOLD = Decimal("8")


def _recalc_totals(timesheet: TimesheetHeader, lines: list) -> None:
    total = sum(Decimal(str(l.hours_worked)) for l in lines)
    overtime = sum(Decimal(str(l.hours_worked)) for l in lines if l.overtime_flag)
    timesheet.total_hours = total
    timesheet.overtime_hours = overtime
    timesheet.regular_hours = total - overtime


# ── Timesheet Header ──────────────────────────────────────────────────────────

async def create_timesheet(db: AsyncSession, data: TimesheetCreate) -> TimesheetHeader:
    ts = TimesheetHeader(**data.model_dump())
    db.add(ts)
    await db.commit()
    await db.refresh(ts)
    return ts


async def list_timesheets(
    db: AsyncSession,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    period_start: Optional[date] = None,
    department_id: Optional[str] = None,
    limit: int = 200,
) -> List[TimesheetHeader]:
    q = (
        select(TimesheetHeader)
        .options(selectinload(TimesheetHeader.lines), selectinload(TimesheetHeader.approval_logs))
        .order_by(TimesheetHeader.period_start.desc())
    )
    if employee_id:
        q = q.where(TimesheetHeader.employee_id == employee_id)
    if status:
        q = q.where(TimesheetHeader.status == status)
    if period_start:
        q = q.where(TimesheetHeader.period_start >= period_start)
    if department_id:
        q = q.where(TimesheetHeader.department_id == department_id)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_timesheet(db: AsyncSession, timesheet_id: UUID) -> Optional[TimesheetHeader]:
    result = await db.execute(
        select(TimesheetHeader)
        .options(selectinload(TimesheetHeader.lines), selectinload(TimesheetHeader.approval_logs))
        .where(TimesheetHeader.timesheet_id == timesheet_id)
    )
    return result.scalar_one_or_none()


async def submit_timesheet(db: AsyncSession, timesheet_id: UUID, data: TimesheetSubmit) -> Optional[TimesheetHeader]:
    ts = await get_timesheet(db, timesheet_id)
    if not ts or ts.status not in (TimesheetStatus.DRAFT, TimesheetStatus.REJECTED):
        return None
    if data.notes:
        ts.notes = data.notes
    ts.status = TimesheetStatus.SUBMITTED
    ts.submitted_at = datetime.utcnow()
    ts.updated_at = datetime.utcnow()
    log = TimesheetApprovalLog(
        timesheet_id=timesheet_id,
        action=ApprovalAction.SUBMITTED if ts.rejection_count == 0 else ApprovalAction.RESUBMITTED,
        action_date=datetime.utcnow(),
        comments=data.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(ts)
    return ts


async def approve_timesheet(db: AsyncSession, timesheet_id: UUID, data: TimesheetApprove) -> Optional[TimesheetHeader]:
    ts = await get_timesheet(db, timesheet_id)
    if not ts or ts.status != TimesheetStatus.SUBMITTED:
        return None
    ts.status = TimesheetStatus.MANAGER_APPROVED
    ts.approved_by = data.approver_name or data.approver_id
    ts.approved_at = datetime.utcnow()
    ts.updated_at = datetime.utcnow()
    log = TimesheetApprovalLog(
        timesheet_id=timesheet_id,
        approver_id=data.approver_id,
        approver_name=data.approver_name,
        action=ApprovalAction.APPROVED,
        action_date=datetime.utcnow(),
        comments=data.comments,
    )
    db.add(log)
    await db.commit()
    await db.refresh(ts)
    return ts


async def reject_timesheet(db: AsyncSession, timesheet_id: UUID, data: TimesheetReject) -> Optional[TimesheetHeader]:
    ts = await get_timesheet(db, timesheet_id)
    if not ts or ts.status not in (TimesheetStatus.SUBMITTED, TimesheetStatus.MANAGER_APPROVED):
        return None
    ts.status = TimesheetStatus.REJECTED
    ts.rejection_count = (ts.rejection_count or 0) + 1
    ts.updated_at = datetime.utcnow()
    log = TimesheetApprovalLog(
        timesheet_id=timesheet_id,
        approver_id=data.approver_id,
        approver_name=data.approver_name,
        action=ApprovalAction.REJECTED,
        action_date=datetime.utcnow(),
        comments=data.comments,
    )
    db.add(log)
    await db.commit()
    await db.refresh(ts)
    return ts


async def finalize_timesheet(db: AsyncSession, timesheet_id: UUID, data: TimesheetFinalize) -> Optional[TimesheetHeader]:
    ts = await get_timesheet(db, timesheet_id)
    if not ts or ts.status != TimesheetStatus.MANAGER_APPROVED:
        return None
    ts.status = TimesheetStatus.FINALIZED
    ts.finalized_at = datetime.utcnow()
    ts.updated_at = datetime.utcnow()
    log = TimesheetApprovalLog(
        timesheet_id=timesheet_id,
        approver_id=data.finalized_by,
        approver_name=data.finalized_by,
        action=ApprovalAction.FINALIZED,
        action_date=datetime.utcnow(),
        comments=data.comments,
    )
    db.add(log)
    await db.commit()
    await db.refresh(ts)
    return ts


# ── Timesheet Lines ───────────────────────────────────────────────────────────

async def add_line(db: AsyncSession, timesheet_id: UUID, data: TimesheetLineCreate) -> TimesheetLine:
    ts = await get_timesheet(db, timesheet_id)
    if not ts:
        return None

    # daily total validation
    existing_result = await db.execute(
        select(func.sum(TimesheetLine.hours_worked)).where(
            and_(TimesheetLine.timesheet_id == timesheet_id, TimesheetLine.work_date == data.work_date)
        )
    )
    existing_hours = existing_result.scalar() or Decimal("0")
    if existing_hours + data.hours_worked > MAX_DAILY_HOURS:
        raise ValueError(f"Total daily hours cannot exceed {MAX_DAILY_HOURS} (currently {existing_hours})")

    line = TimesheetLine(timesheet_id=timesheet_id, **data.model_dump())
    db.add(line)

    # recalculate header totals
    all_lines_result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_id == timesheet_id))
    all_lines = list(all_lines_result.scalars().all()) + [line]
    _recalc_totals(ts, all_lines)
    ts.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(line)
    return line


async def update_line(db: AsyncSession, line_id: UUID, data: TimesheetLineUpdate) -> Optional[TimesheetLine]:
    result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_line_id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(line, k, v)

    ts = await get_timesheet(db, line.timesheet_id)
    if ts:
        all_lines_result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_id == line.timesheet_id))
        _recalc_totals(ts, all_lines_result.scalars().all())
        ts.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(line)
    return line


async def delete_line(db: AsyncSession, line_id: UUID) -> bool:
    result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_line_id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return False
    ts_id = line.timesheet_id
    await db.delete(line)

    ts = await get_timesheet(db, ts_id)
    if ts:
        all_lines_result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_id == ts_id))
        _recalc_totals(ts, all_lines_result.scalars().all())
        ts.updated_at = datetime.utcnow()

    await db.commit()
    return True


async def auto_fill_from_attendance(db: AsyncSession, timesheet_id: UUID, attendance_hours: List[Dict[str, Any]]) -> int:
    """attendance_hours: [{"date": "2026-01-01", "hours": 8.0}]"""
    ts = await get_timesheet(db, timesheet_id)
    if not ts:
        return 0
    count = 0
    for entry in attendance_hours:
        work_date = date.fromisoformat(str(entry["date"]))
        hours = Decimal(str(entry.get("hours", 8)))
        line = TimesheetLine(
            timesheet_id=timesheet_id,
            work_date=work_date,
            activity_type=ActivityType.REGULAR,
            hours_worked=hours,
        )
        db.add(line)
        count += 1
    all_lines_result = await db.execute(select(TimesheetLine).where(TimesheetLine.timesheet_id == timesheet_id))
    all_lines = list(all_lines_result.scalars().all())
    _recalc_totals(ts, all_lines)
    ts.updated_at = datetime.utcnow()
    await db.commit()
    return count


# ── Payroll Export ────────────────────────────────────────────────────────────

async def get_payroll_input(db: AsyncSession, period_start: date, period_end: date) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(TimesheetHeader)
        .options(selectinload(TimesheetHeader.lines))
        .where(
            and_(
                TimesheetHeader.status == TimesheetStatus.FINALIZED,
                TimesheetHeader.period_start >= period_start,
                TimesheetHeader.period_end <= period_end,
            )
        )
    )
    timesheets = result.scalars().all()
    return [
        {
            "employee_id": ts.employee_id,
            "employee_name": ts.employee_name,
            "period_start": str(ts.period_start),
            "period_end": str(ts.period_end),
            "regular_hours": float(ts.regular_hours or 0),
            "overtime_hours": float(ts.overtime_hours or 0),
            "total_hours": float(ts.total_hours or 0),
        }
        for ts in timesheets
    ]


# ── Project Time ──────────────────────────────────────────────────────────────

async def get_project_time_report(db: AsyncSession, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    q = select(
        TimesheetLine.project_id,
        TimesheetLine.project_name,
        func.sum(TimesheetLine.hours_worked).label("total_hours"),
        func.count(TimesheetLine.timesheet_line_id.distinct()).label("entries"),
    ).where(TimesheetLine.project_id.isnot(None)).group_by(TimesheetLine.project_id, TimesheetLine.project_name)
    if project_id:
        q = q.where(TimesheetLine.project_id == project_id)
    result = await db.execute(q)
    return [
        {"project_id": r.project_id, "project_name": r.project_name, "total_hours": float(r.total_hours or 0), "entries": r.entries}
        for r in result.all()
    ]


async def get_activity_summary(db: AsyncSession, period_start: Optional[date] = None) -> List[Dict[str, Any]]:
    q = select(
        TimesheetLine.activity_type,
        func.sum(TimesheetLine.hours_worked).label("total_hours"),
    ).group_by(TimesheetLine.activity_type)
    if period_start:
        q = q.join(TimesheetHeader, TimesheetLine.timesheet_id == TimesheetHeader.timesheet_id).where(TimesheetHeader.period_start >= period_start)
    result = await db.execute(q)
    return [{"activity_type": r.activity_type, "total_hours": float(r.total_hours or 0)} for r in result.all()]


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(TimesheetHeader).options(selectinload(TimesheetHeader.lines)))
    all_ts = result.scalars().all()

    status_counts: Dict[str, int] = {}
    for ts in all_ts:
        status_counts[ts.status] = status_counts.get(ts.status, 0) + 1

    finalized = [ts for ts in all_ts if ts.status == TimesheetStatus.FINALIZED]
    total_h = sum(float(ts.total_hours or 0) for ts in finalized)
    ot_h = sum(float(ts.overtime_hours or 0) for ts in finalized)
    unique_emps = len({ts.employee_id for ts in all_ts})
    avg_h = total_h / unique_emps if unique_emps else 0

    project_result = await db.execute(
        select(TimesheetLine.project_name, func.sum(TimesheetLine.hours_worked).label("h"))
        .where(TimesheetLine.project_id.isnot(None))
        .group_by(TimesheetLine.project_name)
        .order_by(func.sum(TimesheetLine.hours_worked).desc())
        .limit(5)
    )
    project_hours = [{"project": r.project_name, "hours": float(r.h or 0)} for r in project_result.all()]

    return {
        "total_timesheets": len(all_ts),
        "draft": status_counts.get(TimesheetStatus.DRAFT, 0),
        "submitted": status_counts.get(TimesheetStatus.SUBMITTED, 0),
        "manager_approved": status_counts.get(TimesheetStatus.MANAGER_APPROVED, 0),
        "rejected": status_counts.get(TimesheetStatus.REJECTED, 0),
        "finalized": status_counts.get(TimesheetStatus.FINALIZED, 0),
        "total_hours_this_period": round(total_h, 2),
        "overtime_hours_this_period": round(ot_h, 2),
        "avg_hours_per_employee": round(avg_h, 2),
        "pending_approval": status_counts.get(TimesheetStatus.SUBMITTED, 0),
        "employees_with_timesheets": unique_emps,
        "project_hours": project_hours,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_utilization(db: AsyncSession, period_start: Optional[date] = None) -> List[Dict[str, Any]]:
    q = select(TimesheetHeader).options(selectinload(TimesheetHeader.lines)).where(
        TimesheetHeader.status.in_([TimesheetStatus.FINALIZED, TimesheetStatus.MANAGER_APPROVED])
    )
    if period_start:
        q = q.where(TimesheetHeader.period_start >= period_start)
    result = await db.execute(q)
    timesheets = result.scalars().all()
    emp_data: Dict[str, Dict] = {}
    for ts in timesheets:
        e = ts.employee_id
        if e not in emp_data:
            emp_data[e] = {"employee_id": e, "employee_name": ts.employee_name, "department": ts.department_name, "total_hours": 0, "overtime_hours": 0, "timesheet_count": 0}
        emp_data[e]["total_hours"] += float(ts.total_hours or 0)
        emp_data[e]["overtime_hours"] += float(ts.overtime_hours or 0)
        emp_data[e]["timesheet_count"] += 1
    return sorted(emp_data.values(), key=lambda x: x["total_hours"], reverse=True)


async def report_overtime(db: AsyncSession, period_start: Optional[date] = None) -> List[Dict[str, Any]]:
    rows = await report_utilization(db, period_start)
    return [r for r in rows if r["overtime_hours"] > 0]


async def report_summary(db: AsyncSession, period_start: Optional[date] = None) -> Dict[str, Any]:
    q = select(TimesheetHeader)
    if period_start:
        q = q.where(TimesheetHeader.period_start >= period_start)
    result = await db.execute(q)
    ts_list = result.scalars().all()
    total_h = sum(float(ts.total_hours or 0) for ts in ts_list)
    ot_h = sum(float(ts.overtime_hours or 0) for ts in ts_list)
    return {
        "total_timesheets": len(ts_list),
        "total_hours": round(total_h, 2),
        "overtime_hours": round(ot_h, 2),
        "regular_hours": round(total_h - ot_h, 2),
        "by_status": {s: sum(1 for ts in ts_list if ts.status == s) for s in TimesheetStatus},
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_utilization_analyzer(db: AsyncSession) -> List[TSAIRecommendation]:
    result = await db.execute(
        select(TimesheetHeader).where(TimesheetHeader.status.in_([TimesheetStatus.FINALIZED, TimesheetStatus.MANAGER_APPROVED]))
    )
    timesheets = result.scalars().all()
    emp_hours: Dict[str, Dict] = {}
    for ts in timesheets:
        e = ts.employee_id
        emp_hours.setdefault(e, {"name": ts.employee_name, "dept": ts.department_id, "total": 0, "ts_id": ts.timesheet_id})
        emp_hours[e]["total"] += float(ts.total_hours or 0)
    recs = []
    # Underutilized: < 35 hours per timesheet on average
    for emp_id, data in emp_hours.items():
        ts_result = await db.execute(select(func.count(TimesheetHeader.timesheet_id)).where(TimesheetHeader.employee_id == emp_id))
        count = ts_result.scalar() or 1
        avg_hours = data["total"] / count
        if avg_hours < 35:
            rec = TSAIRecommendation(
                agent_type=TSAIAgentType.UTILIZATION_ANALYZER,
                title=f"Low utilization: {data['name'] or emp_id}",
                body=f"Employee {data['name'] or emp_id} averages {avg_hours:.1f}h per period. Consider reviewing workload allocation.",
                employee_id=emp_id,
                department_id=data.get("dept"),
                score=int(avg_hours),
            )
            db.add(rec)
            recs.append(rec)
        elif avg_hours > 55:
            rec = TSAIRecommendation(
                agent_type=TSAIAgentType.UTILIZATION_ANALYZER,
                title=f"Overtime risk: {data['name'] or emp_id}",
                body=f"Employee {data['name'] or emp_id} averages {avg_hours:.1f}h per period. Risk of burnout — review workload.",
                employee_id=emp_id,
                department_id=data.get("dept"),
                score=int(avg_hours),
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs[:15]


async def run_anomaly_detector(db: AsyncSession) -> List[TSAIRecommendation]:
    result = await db.execute(
        select(TimesheetLine, TimesheetHeader.employee_id, TimesheetHeader.employee_name)
        .join(TimesheetHeader, TimesheetLine.timesheet_id == TimesheetHeader.timesheet_id)
    )
    rows = result.all()
    recs = []
    seen = set()
    for line, emp_id, emp_name in rows:
        if float(line.hours_worked) > 14 and emp_id not in seen:
            seen.add(emp_id)
            rec = TSAIRecommendation(
                agent_type=TSAIAgentType.ANOMALY_DETECTOR,
                title=f"Abnormal daily hours: {emp_name or emp_id}",
                body=f"Employee {emp_name or emp_id} logged {line.hours_worked}h on {line.work_date}. Review for accuracy.",
                employee_id=emp_id,
                timesheet_id=line.timesheet_id,
                score=int(float(line.hours_worked)),
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs[:10]


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None, limit: int = 200) -> List[TSAIRecommendation]:
    q = select(TSAIRecommendation).order_by(TSAIRecommendation.created_at.desc())
    if status:
        q = q.where(TSAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: TSAIRecAck) -> Optional[TSAIRecommendation]:
    result = await db.execute(select(TSAIRecommendation).where(TSAIRecommendation.rec_id == rec_id))
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
