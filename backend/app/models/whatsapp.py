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


class WAMessageDirection(str, enum.Enum):
    INBOUND  = "INBOUND"
    OUTBOUND = "OUTBOUND"


class WAMessageType(str, enum.Enum):
    TEXT     = "TEXT"
    TEMPLATE = "TEMPLATE"
    IMAGE    = "IMAGE"
    DOCUMENT = "DOCUMENT"
    AUDIO    = "AUDIO"


class WAMessageStatus(str, enum.Enum):
    QUEUED    = "QUEUED"
    SENT      = "SENT"
    DELIVERED = "DELIVERED"
    READ      = "READ"
    FAILED    = "FAILED"


class WhatsAppConfig(Base, TimestampMixin):
    """WhatsApp Business API configuration (one per ERP instance)."""
    __tablename__ = "whatsapp_configs"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name         = Column(String(255), nullable=False)
    business_phone_id    = Column(String(100), nullable=True)   # Meta WABA phone number ID
    business_phone_no    = Column(String(20),  nullable=True)   # e.g. +254700000000
    api_token            = Column(Text, nullable=True)          # Bearer token (store encrypted in prod)
    webhook_verify_token = Column(String(100), nullable=True)
    provider             = Column(String(50), nullable=False, default="META")  # META / TWILIO / AFRICASTALKING
    is_active            = Column(Boolean, default=True, nullable=False)
    is_demo_mode         = Column(Boolean, default=True, nullable=False)  # True = simulate sends
    created_by_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    messages   = relationship("WhatsAppMessage", back_populates="config", cascade="all, delete-orphan")


class WhatsAppMessage(Base, TimestampMixin):
    """Log of every WhatsApp message sent or received."""
    __tablename__ = "whatsapp_messages"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id        = Column(UUID(as_uuid=True), ForeignKey("whatsapp_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    direction        = Column(Enum(WAMessageDirection), nullable=False, index=True)
    message_type     = Column(Enum(WAMessageType),      nullable=False, default=WAMessageType.TEXT)
    status           = Column(Enum(WAMessageStatus),    nullable=False, default=WAMessageStatus.QUEUED)

    phone            = Column(String(20),  nullable=False, index=True)   # E.164 format
    contact_name     = Column(String(255), nullable=True)
    body             = Column(Text,        nullable=True)
    template_name    = Column(String(100), nullable=True)
    template_vars    = Column(JSON,        nullable=True)   # list of variable substitutions

    external_msg_id  = Column(String(200), nullable=True)   # WhatsApp message ID
    error_message    = Column(Text,        nullable=True)
    delivered_at     = Column(DateTime(timezone=True), nullable=True)
    read_at          = Column(DateTime(timezone=True), nullable=True)

    # ERP record link
    linked_module    = Column(String(50),  nullable=True)
    linked_object_id = Column(UUID(as_uuid=True), nullable=True)
    linked_object_ref = Column(String(100), nullable=True)

    sent_by_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    config   = relationship("WhatsAppConfig", back_populates="messages")
    sent_by  = relationship("User", foreign_keys=[sent_by_id])


class WhatsAppTemplate(Base, TimestampMixin):
    """
    Pre-approved WhatsApp message templates.
    In production these must match templates approved in Meta Business Manager.
    """
    __tablename__ = "whatsapp_templates"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(100), nullable=False, unique=True, index=True)
    display_name  = Column(String(255), nullable=False)
    category      = Column(String(50),  nullable=False, default="UTILITY")   # UTILITY / MARKETING / AUTHENTICATION
    language      = Column(String(10),  nullable=False, default="en")
    header_text   = Column(String(500), nullable=True)
    body_template = Column(Text,        nullable=False)   # Use {{1}}, {{2}} for variables
    footer_text   = Column(String(500), nullable=True)
    buttons       = Column(JSON,        nullable=True)   # list of button dicts
    variable_count = Column(Integer,    nullable=False, default=0)
    module_context = Column(String(50), nullable=True)   # invoice / order / delivery / payment
    is_active     = Column(Boolean,     default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
