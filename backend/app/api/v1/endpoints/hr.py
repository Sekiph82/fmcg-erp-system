"""HR module endpoints – Employees, Shifts, Attendance, Leave, Payroll."""
from __future__ import annotations

from datetime import date
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.hr import (
    Employee, ShiftTemplate, EmployeeShiftAssignment,
    AttendanceRecord, LeaveRequest, LeaveBalance,
    PayrollPeriod, PayrollLine,
    ApprovalStatus, PayrollStatus,
)
from app.schemas.hr import (
    EmployeeCreate, EmployeeUpdate, EmployeeRead, EmployeeShort,
    ShiftTemplateCreate, ShiftTemplateUpdate, ShiftTemplateRead,
    ShiftAssignmentCreate, ShiftAssignmentUpdate, ShiftAssignmentRead,
    AttendanceCreate, AttendanceBulkCreate, AttendanceUpdate, AttendanceRead,
    LeaveRequestCreate, LeaveReview, LeaveRequestRead,
    LeaveBalanceRead,
    PayrollPeriodCreate, PayrollPeriodRead, PayrollPeriodDetailRead,
    PayrollLineCreate, PayrollLineUpdate, PayrollLineRead,
)

router = APIRouter()


# ── Employees ─────────────────────────────────────────────────────────────────

@router.get("/employees/", response_model=List[EmployeeShort],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_employees(
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(Employee)
    if department:
        q = q.where(Employee.department == department)
    if status:
        q = q.where(Employee.status == status)
    if search:
        q = q.where(
            Employee.full_name.ilike(f"%{search}%") |
            Employee.employee_code.ilike(f"%{search}%")
        )
    q = q.offset(skip).limit(limit).order_by(Employee.full_name)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/employees/", response_model=EmployeeRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_employee(body: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Employee).where(Employee.employee_code == body.employee_code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Employee code already exists")
    emp = Employee(**body.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.get("/employees/{employee_id}", response_model=EmployeeRead,
            dependencies=[Depends(require_permission("hr", "view"))])
async def get_employee(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


@router.patch("/employees/{employee_id}", response_model=EmployeeRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(emp, k, v)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.delete("/employees/{employee_id}", status_code=204,
               dependencies=[Depends(require_permission("hr", "edit"))])
async def delete_employee(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from fastapi import Response
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    await db.delete(emp)
    await db.commit()
    return Response(status_code=204)


# ── Shift Templates ───────────────────────────────────────────────────────────

@router.get("/shifts/templates/", response_model=List[ShiftTemplateRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_shift_templates(
    active_only: bool = Query(True),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(ShiftTemplate)
    if active_only:
        q = q.where(ShiftTemplate.is_active == True)
    result = await db.execute(q.order_by(ShiftTemplate.name).limit(limit))
    return result.scalars().all()


@router.post("/shifts/templates/", response_model=ShiftTemplateRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_shift_template(body: ShiftTemplateCreate, db: AsyncSession = Depends(get_db)):
    tmpl = ShiftTemplate(**body.model_dump())
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.patch("/shifts/templates/{template_id}", response_model=ShiftTemplateRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_shift_template(
    template_id: uuid.UUID,
    body: ShiftTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    tmpl = await db.get(ShiftTemplate, template_id)
    if not tmpl:
        raise HTTPException(404, "Shift template not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(tmpl, k, v)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


# ── Shift Assignments ─────────────────────────────────────────────────────────

@router.get("/shifts/assignments/", response_model=List[ShiftAssignmentRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_shift_assignments(
    employee_id: Optional[uuid.UUID] = Query(None),
    department: Optional[str] = Query(None),
    as_of: Optional[date] = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(EmployeeShiftAssignment)
        .options(
            selectinload(EmployeeShiftAssignment.shift_template),
            selectinload(EmployeeShiftAssignment.employee),
        )
    )
    if employee_id:
        q = q.where(EmployeeShiftAssignment.employee_id == employee_id)
    if as_of:
        q = q.where(
            EmployeeShiftAssignment.effective_from <= as_of,
            (EmployeeShiftAssignment.effective_to == None) | (EmployeeShiftAssignment.effective_to >= as_of),
        )
    if department:
        q = q.join(Employee, EmployeeShiftAssignment.employee_id == Employee.id).where(Employee.department == department)
    result = await db.execute(q.limit(limit))
    return result.scalars().all()


@router.post("/shifts/assignments/", response_model=ShiftAssignmentRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_shift_assignment(body: ShiftAssignmentCreate, db: AsyncSession = Depends(get_db)):
    asgn = EmployeeShiftAssignment(**body.model_dump())
    db.add(asgn)
    await db.commit()
    result = await db.execute(
        select(EmployeeShiftAssignment)
        .options(
            selectinload(EmployeeShiftAssignment.shift_template),
            selectinload(EmployeeShiftAssignment.employee),
        )
        .where(EmployeeShiftAssignment.id == asgn.id)
    )
    return result.scalar_one()


@router.patch("/shifts/assignments/{assignment_id}", response_model=ShiftAssignmentRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_shift_assignment(
    assignment_id: uuid.UUID,
    body: ShiftAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    asgn = await db.get(EmployeeShiftAssignment, assignment_id)
    if not asgn:
        raise HTTPException(404, "Shift assignment not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(asgn, k, v)
    await db.commit()
    result = await db.execute(
        select(EmployeeShiftAssignment)
        .options(
            selectinload(EmployeeShiftAssignment.shift_template),
            selectinload(EmployeeShiftAssignment.employee),
        )
        .where(EmployeeShiftAssignment.id == asgn.id)
    )
    return result.scalar_one()


# ── Attendance ────────────────────────────────────────────────────────────────

@router.get("/attendance/", response_model=List[AttendanceRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_attendance(
    employee_id: Optional[uuid.UUID] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(AttendanceRecord)
        .options(selectinload(AttendanceRecord.employee))
    )
    if employee_id:
        q = q.where(AttendanceRecord.employee_id == employee_id)
    if status:
        q = q.where(AttendanceRecord.status == status)
    if date_from:
        q = q.where(AttendanceRecord.attendance_date >= date_from)
    if date_to:
        q = q.where(AttendanceRecord.attendance_date <= date_to)
    if department:
        q = q.join(Employee, AttendanceRecord.employee_id == Employee.id).where(Employee.department == department)
    q = q.order_by(AttendanceRecord.attendance_date.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/attendance/", response_model=AttendanceRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def record_attendance(
    body: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rec = AttendanceRecord(**body.model_dump(), recorded_by_id=current_user.id)
    db.add(rec)
    await db.commit()
    result = await db.execute(
        select(AttendanceRecord)
        .options(selectinload(AttendanceRecord.employee))
        .where(AttendanceRecord.id == rec.id)
    )
    return result.scalar_one()


@router.post("/attendance/bulk/", response_model=List[AttendanceRead], status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def bulk_record_attendance(
    body: AttendanceBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = [
        AttendanceRecord(**r.model_dump(), recorded_by_id=current_user.id)
        for r in body.records
    ]
    db.add_all(records)
    await db.commit()
    ids = [r.id for r in records]
    result = await db.execute(
        select(AttendanceRecord)
        .options(selectinload(AttendanceRecord.employee))
        .where(AttendanceRecord.id.in_(ids))
    )
    return result.scalars().all()


@router.patch("/attendance/{record_id}", response_model=AttendanceRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_attendance(
    record_id: uuid.UUID,
    body: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(AttendanceRecord, record_id)
    if not rec:
        raise HTTPException(404, "Attendance record not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rec, k, v)
    await db.commit()
    result = await db.execute(
        select(AttendanceRecord)
        .options(selectinload(AttendanceRecord.employee))
        .where(AttendanceRecord.id == rec.id)
    )
    return result.scalar_one()


# ── Leave ─────────────────────────────────────────────────────────────────────

@router.get("/leave/", response_model=List[LeaveRequestRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_leave_requests(
    employee_id: Optional[uuid.UUID] = Query(None),
    approval_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(LeaveRequest).options(selectinload(LeaveRequest.employee))
    if employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    if approval_status:
        q = q.where(LeaveRequest.approval_status == approval_status)
    q = q.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/leave/", response_model=LeaveRequestRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_leave_request(body: LeaveRequestCreate, db: AsyncSession = Depends(get_db)):
    days = (body.end_date - body.start_date).days + 1
    req = LeaveRequest(**body.model_dump(), days_requested=days)
    db.add(req)
    await db.commit()
    result = await db.execute(
        select(LeaveRequest)
        .options(selectinload(LeaveRequest.employee))
        .where(LeaveRequest.id == req.id)
    )
    return result.scalar_one()


@router.post("/leave/{request_id}/review", response_model=LeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "approve"))])
async def review_leave_request(
    request_id: uuid.UUID,
    body: LeaveReview,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    req = await db.get(LeaveRequest, request_id)
    if not req:
        raise HTTPException(404, "Leave request not found")
    if req.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(400, f"Leave request is already {req.approval_status.value}")
    req.approval_status = body.approval_status
    req.review_note = body.review_note
    req.reviewed_by_id = current_user.id

    # Update leave balance when approved
    if body.approval_status == ApprovalStatus.APPROVED:
        bal_result = await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == req.employee_id,
                LeaveBalance.leave_type == req.leave_type,
                LeaveBalance.year == req.start_date.year,
            )
        )
        bal = bal_result.scalar_one_or_none()
        if bal:
            bal.used_days += req.days_requested

    await db.commit()
    result = await db.execute(
        select(LeaveRequest)
        .options(selectinload(LeaveRequest.employee))
        .where(LeaveRequest.id == req.id)
    )
    return result.scalar_one()


@router.get("/leave/balances/", response_model=List[LeaveBalanceRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_leave_balances(
    employee_id: Optional[uuid.UUID] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(LeaveBalance)
    if employee_id:
        q = q.where(LeaveBalance.employee_id == employee_id)
    if year:
        q = q.where(LeaveBalance.year == year)
    result = await db.execute(q.limit(limit))
    rows = result.scalars().all()
    return [
        LeaveBalanceRead(
            id=r.id,
            employee_id=r.employee_id,
            leave_type=r.leave_type,
            year=r.year,
            entitled_days=r.entitled_days,
            used_days=r.used_days,
            remaining=r.entitled_days - r.used_days,
        )
        for r in rows
    ]


# ── Payroll ───────────────────────────────────────────────────────────────────

@router.get("/payroll/periods/", response_model=List[PayrollPeriodRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_payroll_periods(
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PayrollPeriod).order_by(PayrollPeriod.period_year.desc(), PayrollPeriod.period_month.desc()).limit(limit)
    )
    return result.scalars().all()


@router.post("/payroll/periods/", response_model=PayrollPeriodRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_payroll_period(body: PayrollPeriodCreate, db: AsyncSession = Depends(get_db)):
    period = PayrollPeriod(**body.model_dump())
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.get("/payroll/periods/{period_id}", response_model=PayrollPeriodDetailRead,
            dependencies=[Depends(require_permission("hr", "view"))])
async def get_payroll_period(period_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PayrollPeriod)
        .options(selectinload(PayrollPeriod.lines).selectinload(PayrollLine.employee))
        .where(PayrollPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(404, "Payroll period not found")
    return period


@router.post("/payroll/periods/{period_id}/lines/", response_model=PayrollLineRead, status_code=201,
             dependencies=[Depends(require_permission("hr", "create"))])
async def add_payroll_line(
    period_id: uuid.UUID,
    body: PayrollLineCreate,
    db: AsyncSession = Depends(get_db),
):
    period = await db.get(PayrollPeriod, period_id)
    if not period:
        raise HTTPException(404, "Payroll period not found")
    if period.status not in (PayrollStatus.DRAFT,):
        raise HTTPException(400, "Can only add lines to DRAFT payroll periods")
    line = PayrollLine(period_id=period_id, **body.model_dump())
    db.add(line)
    await db.commit()
    result = await db.execute(
        select(PayrollLine)
        .options(selectinload(PayrollLine.employee))
        .where(PayrollLine.id == line.id)
    )
    return result.scalar_one()


@router.patch("/payroll/lines/{line_id}", response_model=PayrollLineRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_payroll_line(
    line_id: uuid.UUID,
    body: PayrollLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    line = await db.get(PayrollLine, line_id)
    if not line:
        raise HTTPException(404, "Payroll line not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(line, k, v)
    await db.commit()
    result = await db.execute(
        select(PayrollLine)
        .options(selectinload(PayrollLine.employee))
        .where(PayrollLine.id == line.id)
    )
    return result.scalar_one()


@router.post("/payroll/periods/{period_id}/approve", response_model=PayrollPeriodRead,
             dependencies=[Depends(require_permission("hr", "approve"))])
async def approve_payroll_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mark a payroll period as APPROVED. Payment dispatch is handled via the
    finance/M-Pesa layer – not here. Supports accountability linking.
    Requires 'hr.approve' permission (separate from hr.edit).
    """
    period = await db.get(PayrollPeriod, period_id)
    if not period:
        raise HTTPException(404, "Payroll period not found")
    if period.status != PayrollStatus.DRAFT:
        raise HTTPException(400, f"Period is already {period.status.value}")
    period.status = PayrollStatus.APPROVED
    period.approved_by_id = current_user.id
    await db.commit()
    await db.refresh(period)
    return period


@router.get("/payroll/periods/{period_id}/export", response_model=List[dict],
            dependencies=[Depends(require_permission("hr", "approve"))])
async def export_payroll_period(period_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Export-ready flat list of payroll lines for a period.
    Suitable for sending to payroll bureau or M-Pesa bulk payment upload.
    Requires hr.approve to prevent casual access.
    """
    result = await db.execute(
        select(PayrollLine)
        .options(selectinload(PayrollLine.employee))
        .where(PayrollLine.period_id == period_id)
    )
    lines = result.scalars().all()
    out = []
    for line in lines:
        emp = line.employee
        out.append({
            "employee_code": emp.employee_code if emp else None,
            "full_name": emp.full_name if emp else None,
            "department": emp.department if emp else None,
            "payment_method": line.payment_method.value if line.payment_method else (emp.payment_method.value if emp and emp.payment_method else None),
            "mpesa_number": emp.mpesa_number if emp else None,
            "bank_account": emp.bank_account if emp else None,
            "gross_pay": line.gross_pay,
            "net_pay": line.net_pay,
            "salary_components": line.salary_components,
            "is_paid": line.is_paid,
            "payment_reference": line.payment_reference,
        })
    return out


# ── Marketing field team summary ───────────────────────────────────────────────

@router.get("/marketing/field-team",
            dependencies=[Depends(require_permission("hr", "view"))])
async def marketing_field_team(
    db: AsyncSession = Depends(get_db),
):
    """
    Marketing-linked HR view: employees in MARKETING or FIELD_SALES department
    with a count of their customer visits from the marketing module.
    Useful for linking field marketers to campaign ownership and visit performance.
    """
    from sqlalchemy import func as sqlfunc, select as sqsel
    from app.models.hr import Employee, EmployeeStatus
    from app.models.marketing import CustomerVisit

    rows = (await db.execute(
        sqsel(
            Employee.id,
            Employee.employee_code,
            Employee.full_name,
            Employee.department,
            Employee.role,
            Employee.phone,
            Employee.email,
            Employee.status,
            sqlfunc.count(CustomerVisit.id).label("visit_count"),
        )
        .join(
            CustomerVisit,
            CustomerVisit.employee_id == Employee.id,
            isouter=True,
        )
        .where(
            Employee.department.in_(["MARKETING", "FIELD_SALES", "Field Sales", "Marketing"]),
            Employee.status == EmployeeStatus.ACTIVE,
        )
        .group_by(
            Employee.id, Employee.employee_code, Employee.full_name,
            Employee.department, Employee.role, Employee.phone,
            Employee.email, Employee.status,
        )
        .order_by(sqlfunc.count(CustomerVisit.id).desc())
    )).all()

    return [
        {
            "id": str(r.id),
            "employee_code": r.employee_code,
            "full_name": r.full_name,
            "department": r.department,
            "role": r.role,
            "phone": r.phone,
            "email": r.email,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "visit_count": r.visit_count,
        }
        for r in rows
    ]
