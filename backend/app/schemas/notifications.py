from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.notifications import (
    NotificationType, NotificationPriority, NotificationChannel,
    NotificationStatus, NCNotifAIAgentType, NCNotifAIRecStatus,
)


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    module: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    created_by: Optional[str] = None


class BulkNotificationCreate(BaseModel):
    user_ids: List[str]
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    module: Optional[str] = None
    created_by: Optional[str] = None


class TemplateNotificationSend(BaseModel):
    template_code: str
    user_id: str
    variables: Dict[str, str] = {}
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class NotificationOut(BaseModel):
    notification_id: UUID
    user_id: str
    user_name: Optional[str]
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    channel: NotificationChannel
    status: NotificationStatus
    reference_type: Optional[str]
    reference_id: Optional[str]
    module: Optional[str]
    read_flag: bool
    read_at: Optional[datetime]
    sent_at: Optional[datetime]
    scheduled_for: Optional[datetime]
    retry_count: int
    error_message: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Preference ────────────────────────────────────────────────────────────────

class PreferenceUpsert(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel
    enabled_flag: bool = True
    muted_until: Optional[datetime] = None


class PreferenceOut(BaseModel):
    preference_id: UUID
    user_id: str
    notification_type: NotificationType
    channel: NotificationChannel
    enabled_flag: bool
    muted_until: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Template ──────────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    template_code: str
    template_name: str
    notification_type: NotificationType
    channel: NotificationChannel = NotificationChannel.IN_APP
    title_template: str
    message_template: str
    language: str = "en"
    module: Optional[str] = None


class TemplateOut(BaseModel):
    template_id: UUID
    template_code: str
    template_name: str
    notification_type: NotificationType
    channel: NotificationChannel
    title_template: str
    message_template: str
    language: str
    active_flag: bool
    module: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    user_id: str
    title: str
    message: str
    notification_type: NotificationType = NotificationType.REMINDER
    channel: NotificationChannel = NotificationChannel.IN_APP
    scheduled_for: datetime
    recurring: bool = False
    recurrence_days: Optional[int] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class ScheduleOut(BaseModel):
    schedule_id: UUID
    user_id: str
    title: str
    message: str
    notification_type: NotificationType
    channel: NotificationChannel
    scheduled_for: datetime
    recurring: bool
    recurrence_days: Optional[int]
    reference_type: Optional[str]
    reference_id: Optional[str]
    active_flag: bool
    last_sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class NotificationDashboard(BaseModel):
    total_notifications: int
    unread_count: int
    sent_today: int
    failed_count: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]
    by_channel: Dict[str, int]
    top_modules: List[Dict[str, Any]]
    pending_schedules: int


# ── AI ────────────────────────────────────────────────────────────────────────

class NCNotifAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: NCNotifAIAgentType
    status: NCNotifAIRecStatus
    title: str
    body: str
    user_id: Optional[str]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NCNotifAIRecAck(BaseModel):
    status: NCNotifAIRecStatus
    actioned_by: Optional[str] = None
