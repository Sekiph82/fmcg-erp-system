import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    ForeignKey, Enum, DateTime, JSON, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ChannelType(str, enum.Enum):
    TEAM   = "TEAM"    # shared team channel (Production, Sales, etc.)
    DIRECT = "DIRECT"  # 1-to-1 DM


class MemberRole(str, enum.Enum):
    ADMIN  = "ADMIN"
    MEMBER = "MEMBER"


class ChatChannel(Base, TimestampMixin):
    """Team channel or direct-message thread."""
    __tablename__ = "chat_channels"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(100), nullable=False)
    slug            = Column(String(100), unique=True, nullable=False, index=True)
    channel_type    = Column(Enum(ChannelType), nullable=False, default=ChannelType.TEAM)
    description     = Column(String(500), nullable=True)
    is_archived     = Column(Boolean, default=False, nullable=False)
    module_context  = Column(String(50), nullable=True)   # e.g. "production", "sales" — optional context
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    members    = relationship("ChannelMember", back_populates="channel", cascade="all, delete-orphan")
    messages   = relationship("ChannelMessage", back_populates="channel", cascade="all, delete-orphan",
                              primaryjoin="and_(ChannelMessage.channel_id==ChatChannel.id, ChannelMessage.parent_id==None)",
                              order_by="ChannelMessage.created_at")


class ChannelMember(Base, TimestampMixin):
    """Membership of a user in a channel."""
    __tablename__ = "channel_members"
    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_channel_member"),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id   = Column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role         = Column(Enum(MemberRole), nullable=False, default=MemberRole.MEMBER)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    joined_at    = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    channel = relationship("ChatChannel", back_populates="members")
    user    = relationship("User", foreign_keys=[user_id])


class ChannelMessage(Base, TimestampMixin):
    """A message posted in a channel. parent_id set = thread reply."""
    __tablename__ = "channel_messages"
    __table_args__ = (
        Index("ix_msg_channel_created", "channel_id", "created_at"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id  = Column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body        = Column(Text, nullable=False)
    parent_id   = Column(UUID(as_uuid=True), ForeignKey("channel_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    is_edited   = Column(Boolean, default=False, nullable=False)
    edited_at   = Column(DateTime(timezone=True), nullable=True)
    is_deleted  = Column(Boolean, default=False, nullable=False)

    # Cross-module link (optional)
    link_module = Column(String(50),  nullable=True)   # "sales" / "production" / "quality" etc.
    link_type   = Column(String(100), nullable=True)   # "SalesOrder" / "ProductionOrder" etc.
    link_id     = Column(UUID(as_uuid=True), nullable=True)
    link_ref    = Column(String(100), nullable=True)   # human-readable ref e.g. "SO-0042"

    # @mentions — list of user UUIDs as strings
    mentions = Column(JSON, nullable=True, default=list)

    channel = relationship("ChatChannel", back_populates="messages", foreign_keys=[channel_id])
    sender  = relationship("User", foreign_keys=[sender_id])
    replies = relationship("ChannelMessage", foreign_keys=[parent_id],
                           primaryjoin="ChannelMessage.parent_id==ChannelMessage.id",
                           order_by="ChannelMessage.created_at")
