"""Employee self-service for the signed-in employee (M38.S04.T001).

The employee is resolved from the staff login (``Employee.user_id`` / ``ESSAccount.user_id``) — never from an id in the
request — so a person only ever sees and changes their own leave, attendance, requests, documents, notifications and
payslips. The first visit of a linked employee creates their ESS record automatically (no separate ESS password).
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.services import ess_service as svc

router = APIRouter()


class LeaveIn(BaseModel):
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=1000)


class RequestIn(BaseModel):
    request_type: str
    subject: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)


class ProfileIn(BaseModel):
    personal_email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=500)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=30)


async def _me(db: AsyncSession, user):
    """(ESS account, HR employee) of the signed-in user; creates the ESS account for a linked employee on first use."""
    from app.models.ess import ESSAccount, ESSEmployeeProfile
    from app.models.hr import Employee

    hr = (await db.execute(select(Employee).where(Employee.user_id == user.id).limit(1))).scalar_one_or_none()
    cond = [ESSAccount.user_id == user.id] + ([ESSAccount.hr_employee_id == hr.id] if hr else [])
    acc = (await db.execute(select(ESSAccount).where(or_(*cond)).limit(1))).scalar_one_or_none()
    if acc is None:
        if hr is None:
            raise HTTPException(404, "Your login is not linked to an employee record yet. Please contact HR.")
        acc = ESSAccount(employee_id=hr.id, user_id=user.id, hr_employee_id=hr.id,
                         email=(hr.email or user.email or f"{hr.employee_code}@employee.invalid").lower(),
                         password_hash="!staff-login-only")  # unusable: ESS uses the staff session
        db.add(acc)
        db.add(ESSEmployeeProfile(employee_id=hr.id, hr_employee_id=hr.id, full_name=hr.full_name,
                                  email=acc.email, phone=hr.phone, job_title=hr.role, department_name=hr.department,
                                  joining_date=hr.hire_date, grade=hr.salary_grade))
        await db.commit()
    return acc, hr


def _rows(items):
    return [{k: (v.value if hasattr(v, "value") else v) for k, v in vars(i).items() if not k.startswith("_")} for i in items]


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, hr = await _me(db, user)
    profile = await svc.get_profile(db, acc.employee_id)
    dash = await svc.get_dashboard(db, acc.employee_id)
    return {"employee": {"code": hr.employee_code, "name": hr.full_name, "department": hr.department, "role": hr.role,
                         "hire_date": str(hr.hire_date), "email": hr.email, "phone": hr.phone} if hr else None,
            "profile": _rows([profile])[0] if profile else None, "dashboard": dash}


@router.patch("/profile")
async def update_profile(body: ProfileIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.schemas.ess import ESSProfileUpdate

    acc, _ = await _me(db, user)
    p = await svc.update_profile(db, acc.employee_id, ESSProfileUpdate(**body.model_dump(exclude_unset=True)))
    if p is None:
        raise HTTPException(404, "Profile not found")
    return _rows([p])[0]


@router.get("/leave")
async def leave(year: Optional[int] = Query(None, ge=2000, le=2100), db: AsyncSession = Depends(get_db),
                user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return {"types": _rows(await svc.list_leave_types(db)),
            "balances": _rows(await svc.get_leave_balances(db, acc.employee_id, year)),
            "requests": _rows(await svc.list_leave_requests(db, employee_id=acc.employee_id))}


@router.post("/leave", status_code=201)
async def request_leave(body: LeaveIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.schemas.ess import ESSLeaveRequestCreate

    acc, _ = await _me(db, user)
    if body.end_date < body.start_date:
        raise HTTPException(422, "The end date is before the start date.")
    req = await svc.create_leave_request(db, ESSLeaveRequestCreate(employee_id=acc.employee_id, **body.model_dump()))
    req = await svc.submit_leave_request(db, req.leave_request_id)  # goes straight to the approver
    return _rows([req])[0]


@router.post("/leave/{leave_request_id}/cancel")
async def cancel_leave(leave_request_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    req = await svc.cancel_leave(db, leave_request_id, acc.employee_id)  # only the employee's own request
    if req is None:
        raise HTTPException(404, "Leave request not found or can no longer be cancelled")
    return _rows([req])[0]


@router.get("/attendance")
async def attendance(month: int = Query(..., ge=1, le=12), year: int = Query(..., ge=2000, le=2100),
                     db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return {"records": _rows(await svc.list_attendance(db, acc.employee_id, month=month, year=year)),
            "summary": await svc.attendance_summary(db, acc.employee_id, year, month)}


@router.get("/requests")
async def requests(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return _rows(await svc.list_requests(db, employee_id=acc.employee_id))


@router.post("/requests", status_code=201)
async def create_request(body: RequestIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.ess import ESSRequestType
    from app.schemas.ess import ESSRequestCreate

    acc, _ = await _me(db, user)
    try:
        rtype = ESSRequestType(body.request_type)
    except ValueError:
        raise HTTPException(422, "Unknown request type")
    r = await svc.create_request(db, ESSRequestCreate(employee_id=acc.employee_id, request_type=rtype,
                                                      subject=body.subject, description=body.description))
    r = await svc.submit_request(db, r.request_id)
    return _rows([r])[0]


@router.get("/documents")
async def documents(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return _rows(await svc.list_documents(db, acc.employee_id))  # only documents marked visible to the employee


@router.get("/notifications")
async def notifications(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return _rows(await svc.list_notifications(db, acc.employee_id))


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    n = await svc.mark_read(db, notification_id, acc.employee_id)
    if n is None:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.get("/payslips")
async def payslips(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """The employee's own payslips from approved/paid payroll runs."""
    from app.models.payroll_ke import KePayrollLine, PayrollRun, PayrollRunStatus, Payslip

    _, hr = await _me(db, user)
    if hr is None:
        return []
    rows = (await db.execute(select(Payslip, PayrollRun, KePayrollLine)
                             .join(PayrollRun, PayrollRun.id == Payslip.run_id)
                             .join(KePayrollLine, KePayrollLine.id == Payslip.payroll_line_id)
                             .where(Payslip.employee_id == hr.id,
                                    PayrollRun.status.in_((PayrollRunStatus.APPROVED, PayrollRunStatus.PAID)))
                             .order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc()))).all()
    out = []
    for slip, run, line in rows:
        out.append({"id": str(slip.id), "period": f"{run.period_year}-{run.period_month:02d}", "issue_date": str(slip.issue_date),
                    "gross": float(line.gross_salary or 0), "net": float(line.net_salary or 0),
                    "paye": float(line.paye_amount or 0), "nhif": float(line.nhif_amount or 0),
                    "nssf": float(line.nssf_employee or 0), "housing_levy": float(line.housing_levy or 0),
                    "components": line.components_json})
        if slip.viewed_at is None:
            from datetime import datetime, timezone

            slip.viewed_at = datetime.now(timezone.utc)
    await db.commit()
    return out


class ClockIn(BaseModel):
    action: str = Field(pattern=r"^(in|out)$")


@router.post("/attendance/clock")
async def clock(body: ClockIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Check in / out for today at the server's time (employees cannot back-date or type their own hours)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.models.ess import ESSAttendanceRecord
    from app.schemas.ess import ESSAttendanceCreate

    acc, _ = await _me(db, user)
    # attendance is kept in factory local time (naive columns; lateness is measured against 08:30 local)
    # ponytail: single factory time zone; take it from the employee's company if sites span time zones
    now = datetime.now(ZoneInfo("Africa/Nairobi")).replace(tzinfo=None, microsecond=0)
    today = now.date()
    rec = (await db.execute(select(ESSAttendanceRecord).where(ESSAttendanceRecord.employee_id == acc.employee_id,
                                                              ESSAttendanceRecord.attendance_date == today))).scalar_one_or_none()
    if body.action == "in":
        if rec is not None and rec.check_in is not None:
            raise HTTPException(409, "You already checked in today.")
        data = ESSAttendanceCreate(employee_id=acc.employee_id, attendance_date=today, check_in=now)
    else:
        if rec is None or rec.check_in is None:
            raise HTTPException(409, "Check in first.")
        if rec.check_out is not None:
            raise HTTPException(409, "You already checked out today.")
        data = ESSAttendanceCreate(employee_id=acc.employee_id, attendance_date=today, check_in=rec.check_in, check_out=now)
    r = await svc.upsert_attendance(db, data)
    return _rows([r])[0]


@router.post("/notifications/read-all")
async def read_all(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return {"marked_read": await svc.mark_all_read(db, acc.employee_id)}
