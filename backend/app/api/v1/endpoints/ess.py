from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import require_permission
from app.db.session import get_db
from app.models.ess import (
    LeaveStatus, ESSRequestStatus, ESSDocumentType, ESSAIRecStatus, ESSAccountStatus,
)
from app.schemas.ess import (
    ESSLoginRequest, ESSLoginResponse,
    ESSAccountCreate, ESSAccountRead,
    ESSProfileCreate, ESSProfileRead, ESSProfileUpdate,
    ESSLeaveTypeCreate, ESSLeaveTypeRead,
    ESSLeaveBalanceRead, ESSLeaveBalanceUpsert,
    ESSLeaveRequestCreate, ESSLeaveRequestRead, ESSLeaveApproveReject,
    ESSAttendanceCreate, ESSAttendanceRead,
    ESSRequestCreate, ESSRequestRead, ESSRequestReview,
    ESSDocumentCreate, ESSDocumentRead,
    ESSNotificationRead,
    ESSDashboardResponse,
    ESSActivityLogRead,
    ESSAIRecRead, ESSAIRecAck,
)
from app.services import ess_service as svc

router = APIRouter()


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=ESSLoginResponse)
async def login(data: ESSLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.login(db, data.email, data.password)
    if not result:
        raise HTTPException(401, "Invalid credentials or account suspended")
    return result


@router.post("/accounts", response_model=ESSAccountRead,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_account(data: ESSAccountCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_account(db, data)


@router.get("/accounts", response_model=List[ESSAccountRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    return await svc.list_accounts(db)


@router.patch("/accounts/{employee_id}/status", response_model=ESSAccountRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_account_status(
    employee_id: UUID, status: ESSAccountStatus,
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.update_account_status(db, employee_id, status)
    if not acc:
        raise HTTPException(404, "Account not found")
    return acc


# ── Profile ───────────────────────────────────────────────────────────────────

@router.post("/profiles", response_model=ESSProfileRead,
             dependencies=[Depends(require_permission("hr", "create"))])
async def upsert_profile(data: ESSProfileCreate, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_profile(db, data)


@router.get("/profiles/{employee_id}", response_model=ESSProfileRead,
            dependencies=[Depends(require_permission("hr", "view"))])
async def get_profile(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await svc.get_profile(db, employee_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    return p


@router.patch("/profiles/{employee_id}", response_model=ESSProfileRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def update_profile(employee_id: UUID, data: ESSProfileUpdate, db: AsyncSession = Depends(get_db)):
    p = await svc.update_profile(db, employee_id, data)
    if not p:
        raise HTTPException(404, "Profile not found")
    return p


# ── Leave Types ───────────────────────────────────────────────────────────────

@router.get("/leave-types", response_model=List[ESSLeaveTypeRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_leave_types(db: AsyncSession = Depends(get_db)):
    return await svc.list_leave_types(db)


@router.post("/leave-types", response_model=ESSLeaveTypeRead,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_leave_type(data: ESSLeaveTypeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_leave_type(db, data)


@router.post("/leave-types/seed", response_model=List[ESSLeaveTypeRead],
             dependencies=[Depends(require_permission("hr", "create"))])
async def seed_leave_types(db: AsyncSession = Depends(get_db)):
    return await svc.seed_leave_types(db)


# ── Leave Balances ────────────────────────────────────────────────────────────

@router.get("/leave-balances/{employee_id}", response_model=List[ESSLeaveBalanceRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def get_leave_balances(
    employee_id: UUID,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_leave_balances(db, employee_id, year)


@router.post("/leave-balances", response_model=ESSLeaveBalanceRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def upsert_leave_balance(data: ESSLeaveBalanceUpsert, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_leave_balance(db, data)


# ── Leave Requests ────────────────────────────────────────────────────────────

@router.get("/leave-requests", response_model=List[ESSLeaveRequestRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_leave_requests(
    employee_id: Optional[UUID] = None,
    status: Optional[LeaveStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_leave_requests(db, employee_id=employee_id, status=status)


@router.post("/leave-requests", response_model=ESSLeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_leave_request(data: ESSLeaveRequestCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_leave_request(db, data)


@router.post("/leave-requests/{leave_request_id}/submit", response_model=ESSLeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def submit_leave_request(leave_request_id: UUID, db: AsyncSession = Depends(get_db)):
    req = await svc.submit_leave_request(db, leave_request_id)
    if not req:
        raise HTTPException(400, "Cannot submit — wrong status")
    return req


@router.post("/leave-requests/{leave_request_id}/approve", response_model=ESSLeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "approve"))])
async def approve_leave(leave_request_id: UUID, data: ESSLeaveApproveReject, db: AsyncSession = Depends(get_db)):
    req = await svc.approve_leave(db, leave_request_id, data)
    if not req:
        raise HTTPException(400, "Cannot approve")
    return req


@router.post("/leave-requests/{leave_request_id}/reject", response_model=ESSLeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "approve"))])
async def reject_leave(leave_request_id: UUID, data: ESSLeaveApproveReject, db: AsyncSession = Depends(get_db)):
    req = await svc.reject_leave(db, leave_request_id, data)
    if not req:
        raise HTTPException(400, "Cannot reject")
    return req


@router.post("/leave-requests/{leave_request_id}/cancel", response_model=ESSLeaveRequestRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def cancel_leave(
    leave_request_id: UUID,
    employee_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    req = await svc.cancel_leave(db, leave_request_id, employee_id)
    if not req:
        raise HTTPException(400, "Cannot cancel")
    return req


# ── Attendance ────────────────────────────────────────────────────────────────

@router.get("/attendance/{employee_id}", response_model=List[ESSAttendanceRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_attendance(
    employee_id: UUID,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_attendance(db, employee_id, month=month, year=year)


@router.post("/attendance", response_model=ESSAttendanceRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def upsert_attendance(data: ESSAttendanceCreate, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_attendance(db, data)


@router.get("/attendance/{employee_id}/summary",
            dependencies=[Depends(require_permission("hr", "view"))])
async def attendance_summary(
    employee_id: UUID,
    month: int = Query(default=None),
    year: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    import datetime as dt
    m = month or dt.date.today().month
    y = year or dt.date.today().year
    return await svc.attendance_summary(db, employee_id, y, m)


# ── ESS Requests ──────────────────────────────────────────────────────────────

@router.get("/requests", response_model=List[ESSRequestRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_requests(
    employee_id: Optional[UUID] = None,
    status: Optional[ESSRequestStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_requests(db, employee_id=employee_id, status=status)


@router.post("/requests", response_model=ESSRequestRead,
             dependencies=[Depends(require_permission("hr", "create"))])
async def create_request(data: ESSRequestCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_request(db, data)


@router.post("/requests/{request_id}/submit", response_model=ESSRequestRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def submit_request(request_id: UUID, db: AsyncSession = Depends(get_db)):
    req = await svc.submit_request(db, request_id)
    if not req:
        raise HTTPException(400, "Cannot submit")
    return req


@router.patch("/requests/{request_id}/review", response_model=ESSRequestRead,
              dependencies=[Depends(require_permission("hr", "approve"))])
async def review_request(request_id: UUID, data: ESSRequestReview, db: AsyncSession = Depends(get_db)):
    req = await svc.review_request(db, request_id, data)
    if not req:
        raise HTTPException(404, "Request not found")
    return req


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents/{employee_id}", response_model=List[ESSDocumentRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_documents(
    employee_id: UUID,
    doc_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_documents(db, employee_id, doc_type=doc_type)


@router.post("/documents", response_model=ESSDocumentRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def upload_document(data: ESSDocumentCreate, db: AsyncSession = Depends(get_db)):
    return await svc.upload_document(db, data)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications/{employee_id}", response_model=List[ESSNotificationRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_notifications(
    employee_id: UUID,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_notifications(db, employee_id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", response_model=ESSNotificationRead,
             dependencies=[Depends(require_permission("hr", "edit"))])
async def mark_read(
    notification_id: UUID,
    employee_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    n = await svc.mark_read(db, notification_id, employee_id)
    if not n:
        raise HTTPException(404, "Notification not found")
    return n


@router.post("/notifications/{employee_id}/mark-all-read",
             dependencies=[Depends(require_permission("hr", "edit"))])
async def mark_all_read(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    count = await svc.mark_all_read(db, employee_id)
    return {"marked_read": count}


@router.post("/notifications/broadcast",
             dependencies=[Depends(require_permission("hr", "approve"))])
async def broadcast(
    title: str = Query(...),
    body: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from app.models.ess import NotificationType
    count = await svc.broadcast_notification(db, NotificationType.HR_ANNOUNCEMENT, title, body)
    return {"sent_to": count}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/{employee_id}", response_model=ESSDashboardResponse,
            dependencies=[Depends(require_permission("hr", "view"))])
async def dashboard(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db, employee_id)


# ── Activity ──────────────────────────────────────────────────────────────────

@router.get("/activity/{employee_id}", response_model=List[ESSActivityLogRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def activity_log(employee_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await svc.list_activity(db, employee_id, limit=limit)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-employee-assistant",
             dependencies=[Depends(require_permission("hr", "approve"))])
async def run_employee_assistant(db: AsyncSession = Depends(get_db)):
    count = await svc.run_employee_assistant(db)
    return {"generated": count}


@router.post("/ai/run-hr-support-assistant",
             dependencies=[Depends(require_permission("hr", "approve"))])
async def run_hr_support_assistant(db: AsyncSession = Depends(get_db)):
    count = await svc.run_hr_support_assistant(db)
    return {"generated": count}


@router.get("/ai/recommendations", response_model=List[ESSAIRecRead],
            dependencies=[Depends(require_permission("hr", "view"))])
async def list_recs(status: Optional[ESSAIRecStatus] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=ESSAIRecRead,
              dependencies=[Depends(require_permission("hr", "edit"))])
async def ack_rec(rec_id: UUID, data: ESSAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
