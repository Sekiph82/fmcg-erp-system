from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import re

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import (
    Notification, NotificationPreference, NotificationTemplate,
    NotificationSchedule, NCNotifAIRecommendation,
    NotificationType, NotificationPriority, NotificationChannel,
    NotificationStatus, NCNotifAIAgentType, NCNotifAIRecStatus,
)
from app.schemas.notifications import (
    NotificationCreate, BulkNotificationCreate, TemplateNotificationSend,
    PreferenceUpsert, TemplateCreate, ScheduleCreate, NCNotifAIRecAck,
)


# ── Template rendering ────────────────────────────────────────────────────────

def _render(template: str, variables: Dict[str, str]) -> str:
    for k, v in variables.items():
        template = template.replace(f"{{{{{k}}}}}", v)
    return template


# ── Notifications ─────────────────────────────────────────────────────────────

async def create_notification(db: AsyncSession, data: NotificationCreate) -> Notification:
    notif = Notification(**data.model_dump())
    if not data.scheduled_for:
        notif.status = NotificationStatus.SENT
        notif.sent_at = datetime.utcnow()
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def send_bulk(db: AsyncSession, data: BulkNotificationCreate) -> List[Notification]:
    created = []
    payload = data.model_dump()
    user_ids = payload.pop("user_ids")
    for uid in user_ids:
        notif = Notification(user_id=uid, **payload)
        notif.status = NotificationStatus.SENT
        notif.sent_at = datetime.utcnow()
        db.add(notif)
        created.append(notif)
    await db.commit()
    return created


async def send_from_template(db: AsyncSession, data: TemplateNotificationSend) -> Optional[Notification]:
    result = await db.execute(
        select(NotificationTemplate).where(
            and_(NotificationTemplate.template_code == data.template_code,
                 NotificationTemplate.active_flag == True)
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        return None
    title = _render(tpl.title_template, data.variables)
    message = _render(tpl.message_template, data.variables)
    notif = Notification(
        user_id=data.user_id,
        title=title,
        message=message,
        notification_type=tpl.notification_type,
        channel=tpl.channel,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        module=tpl.module,
        status=NotificationStatus.SENT,
        sent_at=datetime.utcnow(),
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def list_notifications(
    db: AsyncSession,
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[str] = None,
    read_flag: Optional[bool] = None,
    module: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Notification]:
    q = select(Notification).order_by(Notification.created_at.desc())
    if user_id:
        q = q.where(Notification.user_id == user_id)
    if notification_type:
        q = q.where(Notification.notification_type == notification_type)
    if priority:
        q = q.where(Notification.priority == priority)
    if read_flag is not None:
        q = q.where(Notification.read_flag == read_flag)
    if module:
        q = q.where(Notification.module == module)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


async def get_notification(db: AsyncSession, notification_id: UUID) -> Optional[Notification]:
    result = await db.execute(select(Notification).where(Notification.notification_id == notification_id))
    return result.scalar_one_or_none()


async def mark_read(db: AsyncSession, notification_id: UUID) -> Optional[Notification]:
    notif = await get_notification(db, notification_id)
    if not notif:
        return None
    notif.read_flag = True
    notif.read_at = datetime.utcnow()
    notif.status = NotificationStatus.READ
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(Notification).where(
            and_(Notification.user_id == user_id, Notification.read_flag == False)
        )
    )
    count = 0
    for notif in result.scalars().all():
        notif.read_flag = True
        notif.read_at = datetime.utcnow()
        notif.status = NotificationStatus.READ
        count += 1
    if count:
        await db.commit()
    return count


async def delete_notification(db: AsyncSession, notification_id: UUID) -> bool:
    notif = await get_notification(db, notification_id)
    if not notif:
        return False
    await db.delete(notif)
    await db.commit()
    return True


async def get_unread_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count(Notification.notification_id)).where(
            and_(Notification.user_id == user_id, Notification.read_flag == False)
        )
    )
    return result.scalar() or 0


# ── Preferences ───────────────────────────────────────────────────────────────

async def upsert_preference(db: AsyncSession, user_id: str, data: PreferenceUpsert) -> NotificationPreference:
    result = await db.execute(
        select(NotificationPreference).where(
            and_(NotificationPreference.user_id == user_id,
                 NotificationPreference.notification_type == data.notification_type,
                 NotificationPreference.channel == data.channel)
        )
    )
    pref = result.scalar_one_or_none()
    if pref:
        pref.enabled_flag = data.enabled_flag
        pref.muted_until = data.muted_until
        pref.updated_at = datetime.utcnow()
    else:
        pref = NotificationPreference(user_id=user_id, **data.model_dump())
        db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref


async def list_preferences(db: AsyncSession, user_id: str) -> List[NotificationPreference]:
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        .order_by(NotificationPreference.notification_type)
    )
    return result.scalars().all()


async def seed_default_preferences(db: AsyncSession, user_id: str) -> List[NotificationPreference]:
    defaults = [
        (NotificationType.APPROVAL_REQUIRED, NotificationChannel.IN_APP, True),
        (NotificationType.APPROVAL_REQUIRED, NotificationChannel.EMAIL, True),
        (NotificationType.TASK_ASSIGNED, NotificationChannel.IN_APP, True),
        (NotificationType.REMINDER, NotificationChannel.IN_APP, True),
        (NotificationType.SYSTEM_ALERT, NotificationChannel.IN_APP, True),
        (NotificationType.INFO, NotificationChannel.IN_APP, True),
        (NotificationType.WARNING, NotificationChannel.IN_APP, True),
        (NotificationType.ANNOUNCEMENT, NotificationChannel.IN_APP, True),
    ]
    created = []
    for ntype, channel, enabled in defaults:
        existing = await db.execute(
            select(NotificationPreference).where(
                and_(NotificationPreference.user_id == user_id,
                     NotificationPreference.notification_type == ntype,
                     NotificationPreference.channel == channel)
            )
        )
        if not existing.scalar_one_or_none():
            pref = NotificationPreference(user_id=user_id, notification_type=ntype, channel=channel, enabled_flag=enabled)
            db.add(pref)
            created.append(pref)
    if created:
        await db.commit()
    return created


# ── Templates ─────────────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, data: TemplateCreate) -> NotificationTemplate:
    tpl = NotificationTemplate(**data.model_dump())
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def list_templates(db: AsyncSession, module: Optional[str] = None, active_only: bool = False, limit: int = 200) -> List[NotificationTemplate]:
    q = select(NotificationTemplate).order_by(NotificationTemplate.template_code)
    if module:
        q = q.where(NotificationTemplate.module == module)
    if active_only:
        q = q.where(NotificationTemplate.active_flag == True)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_template(db: AsyncSession, template_id: UUID) -> Optional[NotificationTemplate]:
    result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.template_id == template_id))
    return result.scalar_one_or_none()


async def seed_default_templates(db: AsyncSession) -> int:
    defaults = [
        ("APPROVAL_REQ", "Approval Required", NotificationType.APPROVAL_REQUIRED, NotificationChannel.IN_APP,
         "Action Required: {{document_type}} Approval",
         "{{document_type}} #{{reference_id}} submitted by {{submitter}} requires your approval.", None),
        ("LEAVE_APPROVED", "Leave Approved", NotificationType.INFO, NotificationChannel.IN_APP,
         "Leave Request Approved",
         "Your leave request from {{start_date}} to {{end_date}} has been approved by {{approver}}.", "ess"),
        ("LEAVE_REJECTED", "Leave Rejected", NotificationType.WARNING, NotificationChannel.IN_APP,
         "Leave Request Rejected",
         "Your leave request from {{start_date}} to {{end_date}} has been rejected. Reason: {{reason}}.", "ess"),
        ("TIMESHEET_APPROVED", "Timesheet Approved", NotificationType.INFO, NotificationChannel.IN_APP,
         "Timesheet Approved",
         "Your timesheet for {{period_start}} - {{period_end}} has been approved.", "timesheets"),
        ("TIMESHEET_REJECTED", "Timesheet Rejected", NotificationType.WARNING, NotificationChannel.IN_APP,
         "Timesheet Rejected",
         "Your timesheet for {{period_start}} - {{period_end}} was rejected. {{comments}}", "timesheets"),
        ("CERT_EXPIRING", "Certification Expiring", NotificationType.REMINDER, NotificationChannel.IN_APP,
         "Certificate Expiring Soon",
         "Your {{certificate_name}} expires in {{days}} days. Please initiate renewal.", "training"),
        ("TASK_ASSIGNED", "Task Assigned", NotificationType.TASK_ASSIGNED, NotificationChannel.IN_APP,
         "New Task Assigned: {{task_name}}",
         "You have been assigned: {{task_name}}. Due: {{due_date}}.", None),
        ("STOCK_LOW", "Low Stock Alert", NotificationType.WARNING, NotificationChannel.IN_APP,
         "Low Stock Alert: {{item_name}}",
         "{{item_name}} stock is below reorder point. Current: {{current_qty}} {{uom}}.", "inventory"),
        ("PAYMENT_RECEIVED", "Payment Received", NotificationType.INFO, NotificationChannel.IN_APP,
         "Payment Received: {{amount}}",
         "Payment of {{amount}} received from {{customer}} for invoice {{invoice_no}}.", "sales"),
        ("SYSTEM_ALERT", "System Alert", NotificationType.SYSTEM_ALERT, NotificationChannel.IN_APP,
         "System Alert: {{alert_title}}",
         "{{alert_message}}", None),
    ]
    count = 0
    for code, name, ntype, channel, title_tpl, msg_tpl, module in defaults:
        existing = await db.execute(select(NotificationTemplate).where(NotificationTemplate.template_code == code))
        if not existing.scalar_one_or_none():
            tpl = NotificationTemplate(
                template_code=code, template_name=name,
                notification_type=ntype, channel=channel,
                title_template=title_tpl, message_template=msg_tpl,
                module=module,
            )
            db.add(tpl)
            count += 1
    if count:
        await db.commit()
    return count


# ── Schedules ─────────────────────────────────────────────────────────────────

async def create_schedule(db: AsyncSession, data: ScheduleCreate) -> NotificationSchedule:
    schedule = NotificationSchedule(**data.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def list_schedules(db: AsyncSession, user_id: Optional[str] = None, active_only: bool = True, limit: int = 200) -> List[NotificationSchedule]:
    q = select(NotificationSchedule).order_by(NotificationSchedule.scheduled_for)
    if user_id:
        q = q.where(NotificationSchedule.user_id == user_id)
    if active_only:
        q = q.where(NotificationSchedule.active_flag == True)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def process_due_schedules(db: AsyncSession) -> int:
    now = datetime.utcnow()
    result = await db.execute(
        select(NotificationSchedule).where(
            and_(NotificationSchedule.active_flag == True,
                 NotificationSchedule.scheduled_for <= now)
        )
    )
    count = 0
    for schedule in result.scalars().all():
        notif = Notification(
            user_id=schedule.user_id,
            title=schedule.title,
            message=schedule.message,
            notification_type=schedule.notification_type,
            channel=schedule.channel,
            reference_type=schedule.reference_type,
            reference_id=schedule.reference_id,
            status=NotificationStatus.SENT,
            sent_at=now,
        )
        db.add(notif)
        schedule.last_sent_at = now
        if schedule.recurring and schedule.recurrence_days:
            schedule.scheduled_for = now + timedelta(days=schedule.recurrence_days)
        else:
            schedule.active_flag = False
        count += 1
    if count:
        await db.commit()
    return count


async def deactivate_schedule(db: AsyncSession, schedule_id: UUID) -> bool:
    result = await db.execute(select(NotificationSchedule).where(NotificationSchedule.schedule_id == schedule_id))
    s = result.scalar_one_or_none()
    if not s:
        return False
    s.active_flag = False
    await db.commit()
    return True


# ── Module trigger (used by other modules) ────────────────────────────────────

async def trigger_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    priority: str = "normal",
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    module: Optional[str] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id, title=title, message=message,
        notification_type=notification_type, priority=priority,
        reference_type=reference_type, reference_id=reference_id,
        module=module, status=NotificationStatus.SENT, sent_at=datetime.utcnow(),
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total = (await db.execute(select(func.count(Notification.notification_id)))).scalar() or 0
    unread = (await db.execute(select(func.count(Notification.notification_id)).where(Notification.read_flag == False))).scalar() or 0
    sent_today = (await db.execute(select(func.count(Notification.notification_id)).where(Notification.created_at >= today_start))).scalar() or 0
    failed = (await db.execute(select(func.count(Notification.notification_id)).where(Notification.status == NotificationStatus.FAILED))).scalar() or 0

    type_result = await db.execute(
        select(Notification.notification_type, func.count(Notification.notification_id).label("c"))
        .group_by(Notification.notification_type)
    )
    by_type = {r.notification_type: r.c for r in type_result.all()}

    priority_result = await db.execute(
        select(Notification.priority, func.count(Notification.notification_id).label("c"))
        .group_by(Notification.priority)
    )
    by_priority = {r.priority: r.c for r in priority_result.all()}

    channel_result = await db.execute(
        select(Notification.channel, func.count(Notification.notification_id).label("c"))
        .group_by(Notification.channel)
    )
    by_channel = {r.channel: r.c for r in channel_result.all()}

    module_result = await db.execute(
        select(Notification.module, func.count(Notification.notification_id).label("c"))
        .where(Notification.module.isnot(None))
        .group_by(Notification.module)
        .order_by(func.count(Notification.notification_id).desc())
        .limit(5)
    )
    top_modules = [{"module": r.module, "count": r.c} for r in module_result.all()]

    pending_schedules = (await db.execute(
        select(func.count(NotificationSchedule.schedule_id)).where(NotificationSchedule.active_flag == True)
    )).scalar() or 0

    return {
        "total_notifications": total, "unread_count": unread,
        "sent_today": sent_today, "failed_count": failed,
        "by_type": by_type, "by_priority": by_priority,
        "by_channel": by_channel, "top_modules": top_modules,
        "pending_schedules": pending_schedules,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_delivery(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Notification.channel, Notification.status, func.count(Notification.notification_id).label("c"))
        .group_by(Notification.channel, Notification.status)
        .order_by(Notification.channel, Notification.status)
    )
    return [{"channel": r.channel, "status": r.status, "count": r.c} for r in result.all()]


async def report_unread(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Notification.user_id, func.count(Notification.notification_id).label("unread"))
        .where(Notification.read_flag == False)
        .group_by(Notification.user_id)
        .order_by(func.count(Notification.notification_id).desc())
        .limit(50)
    )
    return [{"user_id": r.user_id, "unread_count": r.unread} for r in result.all()]


async def report_failed(db: AsyncSession) -> List[Notification]:
    result = await db.execute(
        select(Notification).where(Notification.status == NotificationStatus.FAILED)
        .order_by(Notification.created_at.desc()).limit(100)
    )
    return result.scalars().all()


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_optimizer(db: AsyncSession) -> List[NCNotifAIRecommendation]:
    # Users with >50 unread: suggest muting low-priority types
    unread_result = await db.execute(
        select(Notification.user_id, func.count(Notification.notification_id).label("cnt"))
        .where(Notification.read_flag == False)
        .group_by(Notification.user_id)
        .having(func.count(Notification.notification_id) > 50)
    )
    recs = []
    for row in unread_result.all():
        rec = NCNotifAIRecommendation(
            agent_type=NCNotifAIAgentType.OPTIMIZER,
            title=f"High unread count: {row.user_id}",
            body=(
                f"User {row.user_id} has {row.cnt} unread notifications. "
                f"Consider muting INFO-level notifications or increasing digest frequency to reduce noise."
            ),
            user_id=row.user_id,
            score=row.cnt,
        )
        db.add(rec)
        recs.append(rec)

    # High failure rate types
    fail_result = await db.execute(
        select(Notification.channel, func.count(Notification.notification_id).label("fails"))
        .where(Notification.status == NotificationStatus.FAILED)
        .group_by(Notification.channel)
        .having(func.count(Notification.notification_id) > 5)
    )
    for row in fail_result.all():
        rec = NCNotifAIRecommendation(
            agent_type=NCNotifAIAgentType.OPTIMIZER,
            title=f"High failure rate: {row.channel} channel",
            body=(
                f"Channel '{row.channel}' has {row.fails} failed deliveries. "
                f"Review channel configuration or switch to an alternative delivery method."
            ),
            score=row.fails,
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        await db.commit()
    return recs[:10]


async def run_behavior_analyzer(db: AsyncSession) -> List[NCNotifAIRecommendation]:
    # Users who never read notifications
    result = await db.execute(
        select(Notification.user_id, func.count(Notification.notification_id).label("total"),
               func.sum(func.cast(Notification.read_flag, Integer=True) if False else Notification.read_flag.cast("integer")).label("read_cnt"))
        .group_by(Notification.user_id)
        .having(func.count(Notification.notification_id) >= 10)
    )
    recs = []
    for row in result.all():
        total = row.total or 0
        read_cnt = row.read_cnt or 0
        if total > 0 and (read_cnt / total) < 0.1:
            rec = NCNotifAIRecommendation(
                agent_type=NCNotifAIAgentType.BEHAVIOR_ANALYZER,
                title=f"Low engagement: {row.user_id}",
                body=(
                    f"User {row.user_id} reads only {int(read_cnt/total*100)}% of notifications "
                    f"({read_cnt}/{total}). Consider reviewing notification relevance or delivery channel."
                ),
                user_id=row.user_id,
                score=int(read_cnt / total * 100),
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs[:10]


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None, limit: int = 200) -> List[NCNotifAIRecommendation]:
    q = select(NCNotifAIRecommendation).order_by(NCNotifAIRecommendation.created_at.desc())
    if status:
        q = q.where(NCNotifAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: NCNotifAIRecAck) -> Optional[NCNotifAIRecommendation]:
    result = await db.execute(select(NCNotifAIRecommendation).where(NCNotifAIRecommendation.rec_id == rec_id))
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
