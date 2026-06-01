from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, and_, or_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ess import (
    ESSAccount, ESSEmployeeProfile, ESSLeaveType, ESSLeaveBalance,
    ESSLeaveRequest, ESSAttendanceRecord, ESSRequest, ESSNotification,
    ESSDocument, ESSActivityLog, ESSAIRecommendation,
    ESSAccountStatus, LeaveStatus, AttendanceStatus,
    ESSRequestStatus, ESSRequestType, NotificationType,
    ESSAIAgentType, ESSAIRecStatus,
)
from app.schemas.ess import (
    ESSAccountCreate, ESSProfileCreate, ESSProfileUpdate,
    ESSLeaveTypeCreate, ESSLeaveBalanceUpsert,
    ESSLeaveRequestCreate, ESSLeaveApproveReject,
    ESSAttendanceCreate, ESSRequestCreate, ESSRequestReview,
    ESSDocumentCreate, ESSAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hash_: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hash_


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


async def _next_leave_no(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count()).select_from(ESSLeaveRequest))).scalar_one() + 1
    return f"LVR-{n:06d}"


async def _next_request_no(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count()).select_from(ESSRequest))).scalar_one() + 1
    return f"ESR-{n:06d}"


async def _log_activity(db: AsyncSession, employee_id: UUID, activity_type: str, description: str = "", reference_id: UUID = None):
    log = ESSActivityLog(
        employee_id=employee_id,
        activity_type=activity_type,
        description=description,
        reference_id=reference_id,
    )
    db.add(log)


async def _push_notification(db: AsyncSession, employee_id: UUID, n_type: NotificationType, title: str, body: str, ref_id: UUID = None):
    notif = ESSNotification(
        employee_id=employee_id,
        notification_type=n_type,
        title=title,
        body=body,
        reference_id=ref_id,
    )
    db.add(notif)


# ── Account CRUD ──────────────────────────────────────────────────────────────

async def create_account(db: AsyncSession, data: ESSAccountCreate) -> ESSAccount:
    acc = ESSAccount(
        employee_id=data.employee_id,
        email=data.email,
        password_hash=_hash_password(data.password),
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


async def get_account_by_email(db: AsyncSession, email: str) -> Optional[ESSAccount]:
    r = await db.execute(select(ESSAccount).where(ESSAccount.email == email))
    return r.scalar_one_or_none()


async def get_account_by_employee(db: AsyncSession, employee_id: UUID) -> Optional[ESSAccount]:
    r = await db.execute(select(ESSAccount).where(ESSAccount.employee_id == employee_id))
    return r.scalar_one_or_none()


async def login(db: AsyncSession, email: str, password: str) -> Optional[dict]:
    acc = await get_account_by_email(db, email)
    if not acc or acc.status != ESSAccountStatus.ACTIVE:
        return None
    if not _verify_password(password, acc.password_hash):
        acc.failed_attempts = (acc.failed_attempts or 0) + 1
        if acc.failed_attempts >= 5:
            acc.status = ESSAccountStatus.SUSPENDED
        await db.commit()
        return None
    acc.last_login = datetime.utcnow()
    acc.failed_attempts = 0
    token = _generate_token()
    await _log_activity(db, acc.employee_id, "LOGIN", f"Login from email {email}")
    await db.commit()
    return {
        "ess_account_id": acc.ess_account_id,
        "employee_id": acc.employee_id,
        "email": acc.email,
        "token": token,
        "status": acc.status,
    }


async def list_accounts(db: AsyncSession, limit: int = 200) -> List[ESSAccount]:
    r = await db.execute(select(ESSAccount).order_by(ESSAccount.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def update_account_status(db: AsyncSession, employee_id: UUID, status: ESSAccountStatus) -> Optional[ESSAccount]:
    acc = await get_account_by_employee(db, employee_id)
    if not acc:
        return None
    acc.status = status
    await db.commit()
    await db.refresh(acc)
    return acc


# ── Profile CRUD ──────────────────────────────────────────────────────────────

async def upsert_profile(db: AsyncSession, data: ESSProfileCreate) -> ESSEmployeeProfile:
    r = await db.execute(select(ESSEmployeeProfile).where(ESSEmployeeProfile.employee_id == data.employee_id))
    profile = r.scalar_one_or_none()
    if profile:
        for k, v in data.model_dump().items():
            setattr(profile, k, v)
    else:
        profile = ESSEmployeeProfile(**data.model_dump())
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_profile(db: AsyncSession, employee_id: UUID) -> Optional[ESSEmployeeProfile]:
    r = await db.execute(select(ESSEmployeeProfile).where(ESSEmployeeProfile.employee_id == employee_id))
    return r.scalar_one_or_none()


async def update_profile(db: AsyncSession, employee_id: UUID, data: ESSProfileUpdate) -> Optional[ESSEmployeeProfile]:
    profile = await get_profile(db, employee_id)
    if not profile:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(profile, k, v)
    await _log_activity(db, employee_id, "PROFILE_UPDATE", "Employee updated own profile")
    await db.commit()
    await db.refresh(profile)
    return profile


# ── Leave Types ───────────────────────────────────────────────────────────────

async def list_leave_types(db: AsyncSession) -> List[ESSLeaveType]:
    r = await db.execute(select(ESSLeaveType).where(ESSLeaveType.active_flag == True).order_by(ESSLeaveType.type_name))
    return list(r.scalars().all())


async def create_leave_type(db: AsyncSession, data: ESSLeaveTypeCreate) -> ESSLeaveType:
    lt = ESSLeaveType(**data.model_dump())
    db.add(lt)
    await db.commit()
    await db.refresh(lt)
    return lt


async def seed_leave_types(db: AsyncSession) -> List[ESSLeaveType]:
    existing = (await db.execute(select(func.count()).select_from(ESSLeaveType))).scalar_one()
    if existing > 0:
        return await list_leave_types(db)
    defaults = [
        ("ANNUAL", "Annual Leave", 21, 5, True, False, True),
        ("SICK", "Sick Leave", 10, 0, True, True, True),
        ("MATERNITY", "Maternity Leave", 90, 0, True, True, True),
        ("PATERNITY", "Paternity Leave", 14, 0, True, False, True),
        ("COMPASSIONATE", "Compassionate Leave", 3, 0, True, True, True),
        ("STUDY", "Study Leave", 10, 0, True, True, True),
        ("UNPAID", "Unpaid Leave", 0, 0, True, False, False),
    ]
    types = []
    for code, name, days, cf, req_appr, req_doc, paid in defaults:
        lt = ESSLeaveType(
            type_code=code, type_name=name,
            annual_entitlement_days=days, carry_forward_max=cf,
            requires_approval=req_appr, requires_document=req_doc, paid_leave=paid,
        )
        db.add(lt)
        types.append(lt)
    await db.commit()
    return await list_leave_types(db)


# ── Leave Balance ─────────────────────────────────────────────────────────────

async def get_leave_balances(db: AsyncSession, employee_id: UUID, year: Optional[int] = None) -> List[ESSLeaveBalance]:
    yr = year or date.today().year
    r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(ESSLeaveBalance.employee_id == employee_id, ESSLeaveBalance.year == yr)
        )
    )
    return list(r.scalars().all())


async def upsert_leave_balance(db: AsyncSession, data: ESSLeaveBalanceUpsert) -> ESSLeaveBalance:
    r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(
                ESSLeaveBalance.employee_id == data.employee_id,
                ESSLeaveBalance.leave_type_id == data.leave_type_id,
                ESSLeaveBalance.year == data.year,
            )
        )
    )
    bal = r.scalar_one_or_none()
    if bal:
        bal.entitled_days = data.entitled_days
        bal.carried_forward = data.carried_forward
        bal.adjusted_days = data.adjusted_days
    else:
        bal = ESSLeaveBalance(**data.model_dump())
        db.add(bal)
    await db.commit()
    await db.refresh(bal)
    return bal


async def _init_employee_leave_balances(db: AsyncSession, employee_id: UUID, year: int) -> None:
    leave_types = await list_leave_types(db)
    for lt in leave_types:
        r = await db.execute(
            select(ESSLeaveBalance).where(
                and_(
                    ESSLeaveBalance.employee_id == employee_id,
                    ESSLeaveBalance.leave_type_id == lt.leave_type_id,
                    ESSLeaveBalance.year == year,
                )
            )
        )
        existing = r.scalar_one_or_none()
        if not existing:
            bal = ESSLeaveBalance(
                employee_id=employee_id,
                leave_type_id=lt.leave_type_id,
                year=year,
                entitled_days=Decimal(str(lt.annual_entitlement_days)),
            )
            db.add(bal)


# ── Leave Requests ────────────────────────────────────────────────────────────

def _working_days(start: date, end: date) -> Decimal:
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return Decimal(str(days))


async def list_leave_requests(
    db: AsyncSession,
    employee_id: Optional[UUID] = None,
    status: Optional[LeaveStatus] = None,
    limit: int = 200,
) -> List[ESSLeaveRequest]:
    q = select(ESSLeaveRequest)
    filters = []
    if employee_id:
        filters.append(ESSLeaveRequest.employee_id == employee_id)
    if status:
        filters.append(ESSLeaveRequest.status == status)
    if filters:
        q = q.where(and_(*filters))
    r = await db.execute(q.order_by(ESSLeaveRequest.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def create_leave_request(db: AsyncSession, data: ESSLeaveRequestCreate) -> ESSLeaveRequest:
    days = _working_days(data.start_date, data.end_date)
    req_no = await _next_leave_no(db)
    req = ESSLeaveRequest(
        leave_request_no=req_no,
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        start_date=data.start_date,
        end_date=data.end_date,
        days_requested=days,
        reason=data.reason,
        attachment_ref=data.attachment_ref,
    )
    db.add(req)
    await db.flush()
    # Reserve pending days in balance
    bal_r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(
                ESSLeaveBalance.employee_id == data.employee_id,
                ESSLeaveBalance.leave_type_id == data.leave_type_id,
                ESSLeaveBalance.year == data.start_date.year,
            )
        )
    )
    bal = bal_r.scalar_one_or_none()
    if bal:
        bal.pending_days = (bal.pending_days or Decimal("0")) + days
    await _log_activity(db, data.employee_id, "LEAVE_REQUEST", f"Leave request {req_no} submitted", req.leave_request_id)
    await db.commit()
    await db.refresh(req)
    return req


async def submit_leave_request(db: AsyncSession, leave_request_id: UUID) -> Optional[ESSLeaveRequest]:
    r = await db.execute(select(ESSLeaveRequest).where(ESSLeaveRequest.leave_request_id == leave_request_id))
    req = r.scalar_one_or_none()
    if not req or req.status != LeaveStatus.DRAFT:
        return None
    req.status = LeaveStatus.SUBMITTED
    await db.commit()
    await db.refresh(req)
    return req


async def approve_leave(db: AsyncSession, leave_request_id: UUID, data: ESSLeaveApproveReject) -> Optional[ESSLeaveRequest]:
    r = await db.execute(select(ESSLeaveRequest).where(ESSLeaveRequest.leave_request_id == leave_request_id))
    req = r.scalar_one_or_none()
    if not req or req.status not in (LeaveStatus.SUBMITTED, LeaveStatus.DRAFT):
        return None
    req.status = LeaveStatus.APPROVED
    req.approved_by = data.approver_id
    req.approved_at = datetime.utcnow()
    # Move pending → taken
    bal_r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(
                ESSLeaveBalance.employee_id == req.employee_id,
                ESSLeaveBalance.leave_type_id == req.leave_type_id,
                ESSLeaveBalance.year == req.start_date.year,
            )
        )
    )
    bal = bal_r.scalar_one_or_none()
    if bal:
        bal.pending_days = max(Decimal("0"), (bal.pending_days or Decimal("0")) - req.days_requested)
        bal.taken_days = (bal.taken_days or Decimal("0")) + req.days_requested
    await _push_notification(
        db, req.employee_id, NotificationType.LEAVE_APPROVED,
        "Leave Approved",
        f"Your leave request {req.leave_request_no} has been approved.",
        req.leave_request_id,
    )
    await db.commit()
    await db.refresh(req)
    return req


async def reject_leave(db: AsyncSession, leave_request_id: UUID, data: ESSLeaveApproveReject) -> Optional[ESSLeaveRequest]:
    r = await db.execute(select(ESSLeaveRequest).where(ESSLeaveRequest.leave_request_id == leave_request_id))
    req = r.scalar_one_or_none()
    if not req or req.status not in (LeaveStatus.SUBMITTED, LeaveStatus.DRAFT):
        return None
    req.status = LeaveStatus.REJECTED
    req.approved_by = data.approver_id
    req.rejection_reason = data.rejection_reason
    # Release pending days
    bal_r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(
                ESSLeaveBalance.employee_id == req.employee_id,
                ESSLeaveBalance.leave_type_id == req.leave_type_id,
                ESSLeaveBalance.year == req.start_date.year,
            )
        )
    )
    bal = bal_r.scalar_one_or_none()
    if bal:
        bal.pending_days = max(Decimal("0"), (bal.pending_days or Decimal("0")) - req.days_requested)
    await _push_notification(
        db, req.employee_id, NotificationType.LEAVE_REJECTED,
        "Leave Rejected",
        f"Your leave request {req.leave_request_no} was rejected. Reason: {data.rejection_reason or 'N/A'}",
        req.leave_request_id,
    )
    await db.commit()
    await db.refresh(req)
    return req


async def cancel_leave(db: AsyncSession, leave_request_id: UUID, employee_id: UUID) -> Optional[ESSLeaveRequest]:
    r = await db.execute(select(ESSLeaveRequest).where(
        and_(ESSLeaveRequest.leave_request_id == leave_request_id, ESSLeaveRequest.employee_id == employee_id)
    ))
    req = r.scalar_one_or_none()
    if not req or req.status not in (LeaveStatus.DRAFT, LeaveStatus.SUBMITTED):
        return None
    req.status = LeaveStatus.CANCELLED
    bal_r = await db.execute(
        select(ESSLeaveBalance).where(
            and_(
                ESSLeaveBalance.employee_id == req.employee_id,
                ESSLeaveBalance.leave_type_id == req.leave_type_id,
                ESSLeaveBalance.year == req.start_date.year,
            )
        )
    )
    bal = bal_r.scalar_one_or_none()
    if bal:
        bal.pending_days = max(Decimal("0"), (bal.pending_days or Decimal("0")) - req.days_requested)
    await db.commit()
    await db.refresh(req)
    return req


# ── Attendance ────────────────────────────────────────────────────────────────

async def list_attendance(
    db: AsyncSession,
    employee_id: UUID,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> List[ESSAttendanceRecord]:
    q = select(ESSAttendanceRecord).where(ESSAttendanceRecord.employee_id == employee_id)
    if month and year:
        q = q.where(
            and_(
                extract("month", ESSAttendanceRecord.attendance_date) == month,
                extract("year", ESSAttendanceRecord.attendance_date) == year,
            )
        )
    r = await db.execute(q.order_by(ESSAttendanceRecord.attendance_date.desc()))
    return list(r.scalars().all())


async def upsert_attendance(db: AsyncSession, data: ESSAttendanceCreate) -> ESSAttendanceRecord:
    r = await db.execute(
        select(ESSAttendanceRecord).where(
            and_(
                ESSAttendanceRecord.employee_id == data.employee_id,
                ESSAttendanceRecord.attendance_date == data.attendance_date,
            )
        )
    )
    rec = r.scalar_one_or_none()
    hours = None
    late = 0
    if data.check_in and data.check_out:
        delta = data.check_out - data.check_in
        hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
        # Late if check-in after 08:30
        expected = data.check_in.replace(hour=8, minute=30, second=0, microsecond=0)
        if data.check_in > expected:
            late = int((data.check_in - expected).total_seconds() / 60)

    if rec:
        rec.check_in = data.check_in
        rec.check_out = data.check_out
        rec.status = data.status
        rec.hours_worked = hours
        rec.late_minutes = late
        rec.notes = data.notes
    else:
        rec = ESSAttendanceRecord(
            employee_id=data.employee_id,
            attendance_date=data.attendance_date,
            check_in=data.check_in,
            check_out=data.check_out,
            status=data.status,
            hours_worked=hours,
            late_minutes=late,
            notes=data.notes,
        )
        db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def attendance_summary(db: AsyncSession, employee_id: UUID, year: int, month: int) -> dict:
    records = await list_attendance(db, employee_id, month, year)
    present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
    on_leave = sum(1 for r in records if r.status == AttendanceStatus.ON_LEAVE)
    total_hours = sum(float(r.hours_worked or 0) for r in records)
    return {
        "present": present, "absent": absent, "late": late,
        "on_leave": on_leave, "total_hours": round(total_hours, 1),
        "total_records": len(records),
    }


# ── ESS Requests ──────────────────────────────────────────────────────────────

async def list_requests(
    db: AsyncSession,
    employee_id: Optional[UUID] = None,
    status: Optional[ESSRequestStatus] = None,
    limit: int = 200,
) -> List[ESSRequest]:
    q = select(ESSRequest)
    filters = []
    if employee_id:
        filters.append(ESSRequest.employee_id == employee_id)
    if status:
        filters.append(ESSRequest.status == status)
    if filters:
        q = q.where(and_(*filters))
    r = await db.execute(q.order_by(ESSRequest.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def create_request(db: AsyncSession, data: ESSRequestCreate) -> ESSRequest:
    req_no = await _next_request_no(db)
    req = ESSRequest(
        request_no=req_no,
        employee_id=data.employee_id,
        request_type=data.request_type,
        request_date=date.today(),
        subject=data.subject,
        description=data.description,
        attachment_ref=data.attachment_ref,
        reference_id=data.reference_id,
    )
    db.add(req)
    await db.flush()
    await _log_activity(db, data.employee_id, "REQUEST_SUBMITTED", f"ESS request {req_no}: {data.subject}", req.request_id)
    await db.commit()
    await db.refresh(req)
    return req


async def submit_request(db: AsyncSession, request_id: UUID) -> Optional[ESSRequest]:
    r = await db.execute(select(ESSRequest).where(ESSRequest.request_id == request_id))
    req = r.scalar_one_or_none()
    if not req or req.status != ESSRequestStatus.DRAFT:
        return None
    req.status = ESSRequestStatus.SUBMITTED
    await db.commit()
    await db.refresh(req)
    return req


async def review_request(db: AsyncSession, request_id: UUID, data: ESSRequestReview) -> Optional[ESSRequest]:
    r = await db.execute(select(ESSRequest).where(ESSRequest.request_id == request_id))
    req = r.scalar_one_or_none()
    if not req:
        return None
    req.status = data.status
    req.approved_by = data.approver_id
    req.approved_at = datetime.utcnow()
    req.hr_notes = data.hr_notes
    await _push_notification(
        db, req.employee_id, NotificationType.REQUEST_UPDATE,
        f"Request {req.request_no} {data.status.value}",
        f"Your request '{req.subject}' has been {data.status.value}. {data.hr_notes or ''}",
        req.request_id,
    )
    await db.commit()
    await db.refresh(req)
    return req


# ── Documents ─────────────────────────────────────────────────────────────────

async def list_documents(
    db: AsyncSession,
    employee_id: UUID,
    doc_type: Optional[str] = None,
) -> List[ESSDocument]:
    q = select(ESSDocument).where(
        and_(ESSDocument.employee_id == employee_id, ESSDocument.visible_to_employee == True)
    )
    if doc_type:
        q = q.where(ESSDocument.document_type == doc_type)
    r = await db.execute(q.order_by(ESSDocument.created_at.desc()))
    return list(r.scalars().all())


async def upload_document(db: AsyncSession, data: ESSDocumentCreate) -> ESSDocument:
    doc = ESSDocument(**data.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ── Notifications ─────────────────────────────────────────────────────────────

async def list_notifications(db: AsyncSession, employee_id: UUID, unread_only: bool = False) -> List[ESSNotification]:
    q = select(ESSNotification).where(ESSNotification.employee_id == employee_id)
    if unread_only:
        q = q.where(ESSNotification.read_flag == False)
    r = await db.execute(q.order_by(ESSNotification.created_at.desc()).limit(50))
    return list(r.scalars().all())


async def mark_read(db: AsyncSession, notification_id: UUID, employee_id: UUID) -> Optional[ESSNotification]:
    r = await db.execute(
        select(ESSNotification).where(
            and_(ESSNotification.notification_id == notification_id, ESSNotification.employee_id == employee_id)
        )
    )
    notif = r.scalar_one_or_none()
    if not notif:
        return None
    notif.read_flag = True
    notif.read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, employee_id: UUID) -> int:
    r = await db.execute(
        select(ESSNotification).where(
            and_(ESSNotification.employee_id == employee_id, ESSNotification.read_flag == False)
        )
    )
    unread = r.scalars().all()
    for n in unread:
        n.read_flag = True
        n.read_at = datetime.utcnow()
    await db.commit()
    return len(unread)


async def broadcast_notification(db: AsyncSession, n_type: NotificationType, title: str, body: str) -> int:
    accs = await list_accounts_raw(db)
    for acc in accs:
        n = ESSNotification(
            employee_id=acc.employee_id,
            notification_type=n_type,
            title=title,
            body=body,
        )
        db.add(n)
    await db.commit()
    return len(accs)


async def list_accounts_raw(db: AsyncSession) -> List[ESSAccount]:
    r = await db.execute(select(ESSAccount).where(ESSAccount.status == ESSAccountStatus.ACTIVE))
    return list(r.scalars().all())


# ── Activity Log ──────────────────────────────────────────────────────────────

async def list_activity(db: AsyncSession, employee_id: UUID, limit: int = 50) -> List[ESSActivityLog]:
    r = await db.execute(
        select(ESSActivityLog)
        .where(ESSActivityLog.employee_id == employee_id)
        .order_by(ESSActivityLog.created_at.desc())
        .limit(limit)
    )
    return list(r.scalars().all())


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession, employee_id: UUID) -> dict:
    profile = await get_profile(db, employee_id)
    today = date.today()

    pending_leave = (await db.execute(
        select(func.count()).select_from(ESSLeaveRequest).where(
            and_(ESSLeaveRequest.employee_id == employee_id,
                 ESSLeaveRequest.status.in_([LeaveStatus.DRAFT, LeaveStatus.SUBMITTED]))
        )
    )).scalar_one()

    unread = (await db.execute(
        select(func.count()).select_from(ESSNotification).where(
            and_(ESSNotification.employee_id == employee_id, ESSNotification.read_flag == False)
        )
    )).scalar_one()

    pending_reqs = (await db.execute(
        select(func.count()).select_from(ESSRequest).where(
            and_(ESSRequest.employee_id == employee_id,
                 ESSRequest.status.in_([ESSRequestStatus.DRAFT, ESSRequestStatus.SUBMITTED]))
        )
    )).scalar_one()

    # Annual leave available
    annual_type = (await db.execute(select(ESSLeaveType).where(ESSLeaveType.type_code == "ANNUAL"))).scalar_one_or_none()
    annual_available = 0.0
    if annual_type:
        bal_r = await db.execute(
            select(ESSLeaveBalance).where(
                and_(
                    ESSLeaveBalance.employee_id == employee_id,
                    ESSLeaveBalance.leave_type_id == annual_type.leave_type_id,
                    ESSLeaveBalance.year == today.year,
                )
            )
        )
        bal = bal_r.scalar_one_or_none()
        if bal:
            annual_available = bal.available_days

    # Attendance this month
    att_count = (await db.execute(
        select(func.count()).select_from(ESSAttendanceRecord).where(
            and_(
                ESSAttendanceRecord.employee_id == employee_id,
                extract("month", ESSAttendanceRecord.attendance_date) == today.month,
                extract("year", ESSAttendanceRecord.attendance_date) == today.year,
                ESSAttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        )
    )).scalar_one()

    docs_count = (await db.execute(
        select(func.count()).select_from(ESSDocument).where(
            and_(ESSDocument.employee_id == employee_id, ESSDocument.visible_to_employee == True)
        )
    )).scalar_one()

    days_since = 0
    if profile and profile.joining_date:
        days_since = (today - profile.joining_date).days

    return {
        "employee_name": profile.full_name if profile else "Employee",
        "job_title": profile.job_title if profile else None,
        "department_name": profile.department_name if profile else None,
        "days_since_joining": days_since,
        "pending_leave_requests": pending_leave,
        "unread_notifications": unread,
        "pending_requests": pending_reqs,
        "annual_leave_available": annual_available,
        "attendance_this_month": att_count,
        "documents_count": docs_count,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def _save_rec(db: AsyncSession, agent: ESSAIAgentType, subject: str, body: str, emp_id: UUID = None) -> None:
    rec = ESSAIRecommendation(agent_type=agent, subject=subject, body=body, ref_employee_id=emp_id)
    db.add(rec)


async def run_employee_assistant(db: AsyncSession) -> int:
    count = 0
    today = date.today()
    # Employees with low leave balance
    low_bal = await db.execute(
        select(ESSLeaveBalance).where(
            and_(ESSLeaveBalance.year == today.year, ESSLeaveBalance.entitled_days > 0)
        )
    )
    for bal in low_bal.scalars().all():
        avail = bal.available_days
        if 0 < avail <= 3:
            await _save_rec(
                db, ESSAIAgentType.EMPLOYEE_ASSISTANT,
                "Low leave balance alert",
                f"Employee has only {avail:.1f} days of leave remaining for {today.year}. Consider planning leave carefully.",
                bal.employee_id,
            )
            count += 1

    # Employees with pending leave requests > 5 days
    cutoff = datetime.utcnow() - timedelta(days=5)
    pending = await db.execute(
        select(ESSLeaveRequest).where(
            and_(ESSLeaveRequest.status == LeaveStatus.SUBMITTED, ESSLeaveRequest.created_at <= cutoff)
        )
    )
    for req in pending.scalars().all():
        await _save_rec(
            db, ESSAIAgentType.EMPLOYEE_ASSISTANT,
            f"Leave request pending {req.leave_request_no}",
            f"Leave request {req.leave_request_no} has been pending approval for 5+ days. Follow up with your manager.",
            req.employee_id,
        )
        count += 1

    await db.commit()
    return count


async def run_hr_support_assistant(db: AsyncSession) -> int:
    count = 0
    # Requests in SUBMITTED status for > 3 days
    cutoff = datetime.utcnow() - timedelta(days=3)
    delayed = await db.execute(
        select(ESSRequest).where(
            and_(ESSRequest.status == ESSRequestStatus.SUBMITTED, ESSRequest.created_at <= cutoff)
        )
    )
    reqs = delayed.scalars().all()
    if reqs:
        await _save_rec(
            db, ESSAIAgentType.HR_SUPPORT_ASSISTANT,
            f"{len(reqs)} ESS requests awaiting HR review",
            f"{len(reqs)} employee request(s) have been in submitted status for 3+ days without HR response. Review and resolve to maintain employee satisfaction.",
        )
        count += 1

    # High leave rejection rate (>30%)
    total_decided = (await db.execute(
        select(func.count()).select_from(ESSLeaveRequest).where(
            ESSLeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.REJECTED])
        )
    )).scalar_one()
    rejected = (await db.execute(
        select(func.count()).select_from(ESSLeaveRequest).where(ESSLeaveRequest.status == LeaveStatus.REJECTED)
    )).scalar_one()
    if total_decided > 5 and rejected / total_decided > 0.3:
        await _save_rec(
            db, ESSAIAgentType.HR_SUPPORT_ASSISTANT,
            "High leave rejection rate detected",
            f"{rejected} of {total_decided} leave decisions were rejections ({rejected/total_decided*100:.0f}%). Review leave policies to ensure fairness.",
        )
        count += 1

    await db.commit()
    return count


async def list_ai_recs(db: AsyncSession, status: Optional[ESSAIRecStatus] = None, limit: int = 200) -> List[ESSAIRecommendation]:
    q = select(ESSAIRecommendation)
    if status:
        q = q.where(ESSAIRecommendation.status == status)
    r = await db.execute(q.order_by(ESSAIRecommendation.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: ESSAIRecAck) -> Optional[ESSAIRecommendation]:
    r = await db.execute(select(ESSAIRecommendation).where(ESSAIRecommendation.rec_id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    rec.actioned_at = datetime.utcnow()
    if data.notes:
        rec.notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec
