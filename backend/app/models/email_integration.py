import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer,
    ForeignKey, Enum, DateTime, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class EmailProvider(str, enum.Enum):
    GMAIL   = "GMAIL"
    OUTLOOK = "OUTLOOK"
    SMTP    = "SMTP"


class EmailAccount(Base, TimestampMixin):
    """Connected email account for syncing / sending."""
    __tablename__ = "email_accounts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider        = Column(Enum(EmailProvider), nullable=False)
    email_address   = Column(String(255), nullable=False, index=True)
    display_name    = Column(String(255), nullable=True)
    is_active       = Column(Boolean, default=True, nullable=False)
    sync_enabled    = Column(Boolean, default=True, nullable=False)
    last_sync_at    = Column(DateTime(timezone=True), nullable=True)
    sync_error      = Column(Text, nullable=True)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    threads    = relationship("EmailThread", back_populates="account", cascade="all, delete-orphan")


class EmailThread(Base, TimestampMixin):
    """
    A conversation thread (group of related emails).
    Can be linked to any ERP record via linked_module + linked_object_id.
    """
    __tablename__ = "email_threads"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id         = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_thread_id = Column(String(500), nullable=True, index=True)   # Gmail thread ID etc.
    subject            = Column(String(1000), nullable=False)
    snippet            = Column(String(500), nullable=True)
    participants       = Column(JSON, nullable=True)   # list of email strings
    is_read            = Column(Boolean, default=False, nullable=False)
    message_count      = Column(Integer, default=0, nullable=False)
    last_message_at    = Column(DateTime(timezone=True), nullable=True)

    # ERP record link
    linked_module      = Column(String(50),  nullable=True, index=True)  # customer / supplier / sales_order
    linked_object_id   = Column(UUID(as_uuid=True), nullable=True, index=True)
    linked_object_ref  = Column(String(100), nullable=True)

    account  = relationship("EmailAccount", back_populates="threads")
    messages = relationship("EmailMessage", back_populates="thread",
                            cascade="all, delete-orphan",
                            order_by="EmailMessage.received_at")


class EmailMessage(Base, TimestampMixin):
    """Individual email message within a thread."""
    __tablename__ = "email_messages"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id           = Column(UUID(as_uuid=True), ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    external_message_id = Column(String(500), nullable=True)
    from_email          = Column(String(255), nullable=False)
    from_name           = Column(String(255), nullable=True)
    to_emails           = Column(JSON, nullable=False, default=list)
    cc_emails           = Column(JSON, nullable=True, default=list)
    subject             = Column(String(1000), nullable=False)
    body_text           = Column(Text, nullable=True)
    body_html           = Column(Text, nullable=True)
    received_at         = Column(DateTime(timezone=True), nullable=False)
    is_inbound          = Column(Boolean, nullable=False, default=True)
    is_read             = Column(Boolean, default=False, nullable=False)
    has_attachments     = Column(Boolean, default=False, nullable=False)
    sent_by_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    thread   = relationship("EmailThread", back_populates="messages")
    sent_by  = relationship("User", foreign_keys=[sent_by_id])


class EmailTemplate(Base, TimestampMixin):
    """Reusable email templates for sending from ERP records."""
    __tablename__ = "email_templates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String(200), nullable=False)
    module           = Column(String(50), nullable=True)   # customer / supplier / invoice / etc.
    subject_template = Column(String(1000), nullable=False)
    body_template    = Column(Text, nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)
    created_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
