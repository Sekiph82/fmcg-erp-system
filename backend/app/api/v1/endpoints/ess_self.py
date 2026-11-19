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
    """(ESS account, HR employee) of the signed-in user; creates or links the ESS account on first use.
    Fails closed when the login maps to more than one employee, or the employee / ESS account is not active."""
    from sqlalchemy.exc import IntegrityError

    from app.models.ess import ESSAccount, ESSAccountStatus, ESSEmployeeProfile
    from app.models.hr import Employee, EmployeeStatus

    hrs = (await db.execute(select(Employee).where(Employee.user_id == user.id).limit(2))).scalars().all()
    if len(hrs) > 1:
        raise HTTPException(409, "Your login is linked to more than one employee record. Please contact HR.")
    hr = hrs[0] if hrs else None
    if hr is not None and hr.status not in (EmployeeStatus.ACTIVE, EmployeeStatus.ON_LEAVE):
        raise HTTPException(403, "Self-service is only available to current employees.")
    # an existing account for this person: by login, by HR link, or created earlier by HR with the HR id
    cond = [ESSAccount.user_id == user.id] + ([ESSAccount.hr_employee_id == hr.id, ESSAccount.employee_id == hr.id] if hr else [])
    accs = (await db.execute(select(ESSAccount).where(or_(*cond)))).scalars().all()
    if hr is not None:
        accs = [a for a in accs if a.hr_employee_id in (None, hr.id)]  # never another employee's account
    if len(accs) > 1:
        raise HTTPException(409, "More than one self-service account matches your login. Please contact HR.")
    acc = accs[0] if accs else None
    if acc is None and hr is None:
        raise HTTPException(404, "Your login is not linked to an employee record yet. Please contact HR.")
    if acc is not None and acc.status not in (None, ESSAccountStatus.ACTIVE):
        raise HTTPException(403, "Your self-service account is not active. Please contact HR.")
    try:
        if acc is None:
            email = (hr.email or user.email or "").lower()
            taken = email and (await db.execute(select(ESSAccount.ess_account_id).where(ESSAccount.email == email))).first()
            acc = ESSAccount(employee_id=hr.id, user_id=user.id, hr_employee_id=hr.id,
                             email=f"{hr.employee_code.lower()}@employee.invalid" if (taken or not email) else email,
                             password_hash="!staff-login-only")  # unusable: ESS uses the staff session
            db.add(acc)
            await db.flush()
        elif hr is not None and (acc.user_id != user.id or acc.hr_employee_id != hr.id):
            acc.user_id, acc.hr_employee_id = user.id, hr.id  # backfill links on an account HR created earlier
        if hr is not None and (await db.execute(select(ESSEmployeeProfile.profile_id).where(
                ESSEmployeeProfile.employee_id == acc.employee_id))).first() is None:
            db.add(ESSEmployeeProfile(employee_id=acc.employee_id, hr_employee_id=hr.id, full_name=hr.full_name,
                                      email=acc.email, phone=hr.phone, job_title=hr.role, department_name=hr.department,
                                      joining_date=hr.hire_date, grade=hr.salary_grade))
        await db.commit()
    except IntegrityError:  # a parallel first request created it: use that one
        await db.rollback()
        acc = (await db.execute(select(ESSAccount).where(or_(*cond)).limit(1))).scalar_one()
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

    from app.models.ess import ESSLeaveRequest, ESSLeaveType, LeaveStatus

    acc, _ = await _me(db, user)
    if body.end_date < body.start_date:
        raise HTTPException(422, "The end date is before the start date.")
    if body.start_date < date.today():
        raise HTTPException(422, "Leave cannot start in the past; ask HR to record past leave.")
    if (body.end_date - body.start_date).days > 92 or body.start_date.year != body.end_date.year:
        raise HTTPException(422, "Request at most 3 months at a time, within one calendar year.")
    lt = await db.get(ESSLeaveType, body.leave_type_id)
    if lt is None or getattr(lt, "is_active", True) is False:
        raise HTTPException(422, "Unknown leave type.")
    days = svc._working_days(body.start_date, body.end_date)
    if days <= 0:
        raise HTTPException(422, "The selected dates contain no working days.")
    overlap = (await db.execute(select(ESSLeaveRequest.leave_request_id).where(
        ESSLeaveRequest.employee_id == acc.employee_id,
        ESSLeaveRequest.status.in_([s for s in LeaveStatus if s.value in ("draft", "submitted", "approved")]),
        ESSLeaveRequest.start_date <= body.end_date, ESSLeaveRequest.end_date >= body.start_date).limit(1))).first()
    if overlap:
        raise HTTPException(409, "You already have a leave request for these dates.")
    bal = next((b for b in await svc.get_leave_balances(db, acc.employee_id, body.start_date.year)
                if b.leave_type_id == body.leave_type_id), None)
    if bal is not None:
        available = (bal.entitled_days or 0) + (bal.carried_forward or 0) + (bal.adjusted_days or 0) - (bal.taken_days or 0) - (bal.pending_days or 0)
        if days > available:
            raise HTTPException(422, f"Not enough leave left: {available} day(s) available, {days} requested.")
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
        data = ESSAttendanceCreate(employee_id=acc.employee_id, attendance_date=today, check_in=now,
                                   **({"status": rec.status, "notes": rec.notes} if rec is not None else {}))
    else:
        if rec is None or rec.check_in is None:
            raise HTTPException(409, "Check in first.")
        if rec.check_out is not None:
            raise HTTPException(409, "You already checked out today.")
        data = ESSAttendanceCreate(employee_id=acc.employee_id, attendance_date=today, check_in=rec.check_in, check_out=now,
                                   status=rec.status, notes=rec.notes)  # keep what HR recorded for the day
    from sqlalchemy.exc import IntegrityError

    try:
        r = await svc.upsert_attendance(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Already recorded; refresh.")
    return _rows([r])[0]


@router.post("/notifications/read-all")
async def read_all(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    acc, _ = await _me(db, user)
    return {"marked_read": await svc.mark_all_read(db, acc.employee_id)}
