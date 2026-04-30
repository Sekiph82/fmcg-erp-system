from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.notifications import (
    NotificationCreate, BulkNotificationCreate, TemplateNotificationSend,
    NotificationOut, PreferenceUpsert, PreferenceOut,
    TemplateCreate, TemplateOut, ScheduleCreate, ScheduleOut,
    NotificationDashboard, NCNotifAIRecOut, NCNotifAIRecAck,
)
import app.services.notifications_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=NotificationDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[NotificationOut])
async def list_notifications(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[str] = None,
    read_flag: Optional[bool] = None,
    module: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_notifications(db, user_id, notification_type, priority, read_flag, module, limit, offset)


@router.post("/", response_model=NotificationOut, status_code=201)
async def create_notification(data: NotificationCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_notification(db, data)


@router.get("/unread-count")
async def unread_count(user_id: str, db: AsyncSession = Depends(get_db)):
    count = await svc.get_unread_count(db, user_id)
    return {"user_id": user_id, "unread_count": count}


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(notification_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_notification(db, notification_id)
    if not obj:
        raise HTTPException(404, "Notification not found")
    return obj


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(notification_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.mark_read(db, notification_id)
    if not obj:
        raise HTTPException(404, "Notification not found")
    return obj


@router.post("/mark-all-read")
async def mark_all_read(user_id: str, db: AsyncSession = Depends(get_db)):
    count = await svc.mark_all_read(db, user_id)
    return {"marked_read": count}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(notification_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_notification(db, notification_id)
    if not ok:
        raise HTTPException(404, "Notification not found")


# ── Send ──────────────────────────────────────────────────────────────────────

@router.post("/send/bulk", response_model=List[NotificationOut], status_code=201)
async def send_bulk(data: BulkNotificationCreate, db: AsyncSession = Depends(get_db)):
    return await svc.send_bulk(db, data)


@router.post("/send/from-template", response_model=NotificationOut, status_code=201)
async def send_from_template(data: TemplateNotificationSend, db: AsyncSession = Depends(get_db)):
    obj = await svc.send_from_template(db, data)
    if not obj:
        raise HTTPException(404, "Template not found or inactive")
    return obj


# ── Preferences ───────────────────────────────────────────────────────────────

@router.get("/preferences/{user_id}", response_model=List[PreferenceOut])
async def list_preferences(user_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.list_preferences(db, user_id)


@router.post("/preferences/{user_id}", response_model=PreferenceOut)
async def upsert_preference(user_id: str, data: PreferenceUpsert, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_preference(db, user_id, data)


@router.post("/preferences/{user_id}/seed-defaults")
async def seed_preferences(user_id: str, db: AsyncSession = Depends(get_db)):
    created = await svc.seed_default_preferences(db, user_id)
    return {"created": len(created)}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.post("/templates", response_model=TemplateOut, status_code=201)
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_template(db, data)


@router.get("/templates", response_model=List[TemplateOut])
async def list_templates(
    module: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_templates(db, module, active_only)


@router.get("/templates/{template_id}", response_model=TemplateOut)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_template(db, template_id)
    if not obj:
        raise HTTPException(404, "Template not found")
    return obj


@router.post("/templates/seed-defaults")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    count = await svc.seed_default_templates(db)
    return {"created": count}


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.post("/schedules", response_model=ScheduleOut, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_schedule(db, data)


@router.get("/schedules", response_model=List[ScheduleOut])
async def list_schedules(
    user_id: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_schedules(db, user_id, active_only)


@router.post("/schedules/process-due")
async def process_due_schedules(db: AsyncSession = Depends(get_db)):
    count = await svc.process_due_schedules(db)
    return {"processed": count}


@router.delete("/schedules/{schedule_id}", status_code=204)
async def deactivate_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.deactivate_schedule(db, schedule_id)
    if not ok:
        raise HTTPException(404, "Schedule not found")


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/delivery")
async def report_delivery(db: AsyncSession = Depends(get_db)):
    return await svc.report_delivery(db)


@router.get("/reports/unread")
async def report_unread(db: AsyncSession = Depends(get_db)):
    return await svc.report_unread(db)


@router.get("/reports/failed", response_model=List[NotificationOut])
async def report_failed(db: AsyncSession = Depends(get_db)):
    return await svc.report_failed(db)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-optimizer", response_model=List[NCNotifAIRecOut])
async def run_optimizer(db: AsyncSession = Depends(get_db)):
    return await svc.run_optimizer(db)


@router.post("/ai/run-behavior-analyzer", response_model=List[NCNotifAIRecOut])
async def run_behavior_analyzer(db: AsyncSession = Depends(get_db)):
    return await svc.run_behavior_analyzer(db)


@router.get("/ai/recommendations", response_model=List[NCNotifAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=NCNotifAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: NCNotifAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
