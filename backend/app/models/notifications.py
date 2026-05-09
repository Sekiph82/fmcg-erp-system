from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class NotificationType(str, PyEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL_REQUIRED = "approval_required"
    TASK_ASSIGNED = "task_assigned"
    REMINDER = "reminder"
    SYSTEM_ALERT = "system_alert"
    ANNOUNCEMENT = "announcement"


class NotificationPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, PyEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class NCNotifAIAgentType(str, PyEnum):
    OPTIMIZER = "optimizer"
    BEHAVIOR_ANALYZER = "behavior_analyzer"


class NCNotifAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class Notification(Base):
    __tablename__ = "nc_notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    user_name = Column(String(200), nullable=True)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType, name="system_notificationtype"), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String(200), nullable=True)
    module = Column(String(100), nullable=True)
    read_flag = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NotificationPreference(Base):
    __tablename__ = "nc_notification_preferences"

    preference_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    notification_type = Column(Enum(NotificationType, name="system_notificationtype"), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    enabled_flag = Column(Boolean, default=True)
    muted_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", "channel", name="uq_nc_pref_user_type_channel"),
    )


class NotificationTemplate(Base):
    __tablename__ = "nc_notification_templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String(100), unique=True, nullable=False)
    template_name = Column(String(200), nullable=False)
    notification_type = Column(Enum(NotificationType, name="system_notificationtype"), nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    title_template = Column(String(300), nullable=False)
    message_template = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    active_flag = Column(Boolean, default=True)
    module = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationSchedule(Base):
    __tablename__ = "nc_notification_schedules"

    schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType, name="system_notificationtype"), default=NotificationType.REMINDER, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    recurring = Column(Boolean, default=False)
    recurrence_days = Column(Integer, nullable=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String(200), nullable=True)
    active_flag = Column(Boolean, default=True)
    last_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NCNotifAIRecommendation(Base):
    __tablename__ = "nc_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(NCNotifAIAgentType), nullable=False)
    status = Column(Enum(NCNotifAIRecStatus), default=NCNotifAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
