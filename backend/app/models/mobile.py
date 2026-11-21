"""Mobile Apps Support Layer — push tokens and app sessions."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class MobilePlatform(str, PyEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class MobilePushToken(Base):
    __tablename__ = "mobile_push_tokens"

    push_token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    platform = Column(Enum(MobilePlatform), nullable=False)
    token = Column(Text, nullable=False)
    active_flag = Column(Boolean, default=True, nullable=False)
    app_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class MobileAppSession(Base):
    __tablename__ = "mobile_app_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    platform = Column(Enum(MobilePlatform), nullable=True)
    os_version = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)



class WebPushSubscription(Base):
    """Browser push subscription of one installed PWA (M37.S03.T001)."""
    __tablename__ = "web_push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(1000), nullable=False, unique=True)
    p256dh = Column(String(200), nullable=False)
    auth = Column(String(100), nullable=False)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
