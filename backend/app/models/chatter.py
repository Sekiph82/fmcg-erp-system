from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, Float,
    ForeignKey, Text, Enum as SAEnum, JSON,
)
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class ReferenceType(str, enum.Enum):
    SALES_ORDER = "sales_order"
    INVOICE = "invoice"
    CUSTOMER = "customer"
    PURCHASE_ORDER = "purchase_order"
    CONTRACT = "contract"
    EMPLOYEE = "employee"
    PRODUCT = "product"
    OTHER = "other"


class ActivityType(str, enum.Enum):
    COMMENT = "comment"
    SYSTEM_EVENT = "system_event"
    STATUS_CHANGE = "status_change"
    ASSIGNMENT = "assignment"
    ATTACHMENT_ADDED = "attachment_added"
    APPROVAL_ACTION = "approval_action"
    NOTIFICATION_EVENT = "notification_event"


class Visibility(str, enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    GLOBAL = "global"


class CTAIAgentType(str, enum.Enum):
    ACTIVITY_SUMMARIZER = "activity_summarizer"
    FOLLOW_UP_ASSISTANT = "follow_up_assistant"
    INSIGHT_EXTRACTOR = "insight_extractor"


class CTAIRecStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class Activity(Base):
    __tablename__ = "chatter_activities"

    activity_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_type = Column(SAEnum(ReferenceType), nullable=False)
    reference_id = Column(String(36), nullable=False)
    activity_type = Column(SAEnum(ActivityType), default=ActivityType.COMMENT)
    title = Column(String(300), nullable=False)
    message = Column(Text)
    created_by = Column(String(100), default="system")
    visibility = Column(SAEnum(Visibility), default=Visibility.GLOBAL)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    comments = relationship(
        "ActivityComment", back_populates="activity", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "ActivityAttachment", back_populates="activity", cascade="all, delete-orphan"
    )
    mentions = relationship(
        "Mention", back_populates="activity",
        foreign_keys="Mention.activity_id",
        cascade="all, delete-orphan",
    )


class ActivityComment(Base):
    __tablename__ = "chatter_comments"

    comment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_id = Column(
        String(36), ForeignKey("chatter_activities.activity_id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String(36), nullable=True)
    user_name = Column(String(100))
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime, nullable=True)
    deleted_flag = Column(Boolean, default=False)

    activity = relationship("Activity", back_populates="comments")


class ActivityAttachment(Base):
    __tablename__ = "chatter_attachments"

    attachment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_id = Column(
        String(36), ForeignKey("chatter_activities.activity_id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(String(300), nullable=False)
    file_path = Column(String(500))
    file_size = Column(String(20))
    content_type = Column(String(100))
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="attachments")


class Mention(Base):
    __tablename__ = "chatter_mentions"

    mention_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_id = Column(
        String(36), ForeignKey("chatter_activities.activity_id", ondelete="CASCADE"), nullable=True
    )
    comment_id = Column(
        String(36), ForeignKey("chatter_comments.comment_id", ondelete="CASCADE"), nullable=True
    )
    mentioned_user = Column(String(100), nullable=False)
    notified_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="mentions", foreign_keys=[activity_id])


class CTAIRecommendation(Base):
    __tablename__ = "chatter_ai_recommendations"

    rec_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(SAEnum(CTAIAgentType), nullable=False)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(String(36), nullable=True)
    title = Column(String(300))
    body = Column(Text)
    score = Column(Float, nullable=True)
    status = Column(SAEnum(CTAIRecStatus), default=CTAIRecStatus.PENDING)
    rec_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
