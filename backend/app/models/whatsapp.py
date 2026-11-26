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
    # Bearer token, encrypted at rest (enc:v2: Fernet envelope, webhook-secret key). Legacy plaintext rows stay readable
    # and are encrypted when the token is next saved. Read/write through .api_token only; never returned by the API.
    api_token_stored     = Column("api_token", Text, nullable=True)
    webhook_verify_token = Column(String(100), nullable=True)
    provider             = Column(String(50), nullable=False, default="META")  # META / TWILIO / AFRICASTALKING
    is_active            = Column(Boolean, default=True, nullable=False)
    is_demo_mode         = Column(Boolean, default=True, nullable=False)  # True = simulate sends
    created_by_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    messages   = relationship("WhatsAppMessage", back_populates="config", cascade="all, delete-orphan")

    @property
    def api_token(self):
        from app.services.webhook_service import _read_webhook_secret
        return _read_webhook_secret(self.api_token_stored)

    @api_token.setter
    def api_token(self, value):
        from app.services.webhook_service import _store_webhook_secret
        self.api_token_stored = _store_webhook_secret(value) if value else None

    @property
    def api_token_hint(self):
        """Masked: last 4 characters only, or None when no token is stored."""
        if not self.api_token_stored:
            return None
        try:
            token = self.api_token or ""
        except Exception:
            return "set (cannot be read with the current key)"
        return "••••" + token[-4:] if len(token) > 8 else "••••"


class WhatsAppConsent(Base):
    """WhatsApp permission per phone (E.164, '+digits'). OPTED_OUT (customer replied STOP/UNSUBSCRIBE/ACHA/DUR, or staff
    recorded it) blocks every outbound message; only the customer's own START lifts it. OPTED_IN is required for
    business-initiated messages outside the 24-hour window after the customer's last message."""
    __tablename__ = "whatsapp_consents"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone          = Column(String(20), nullable=False, unique=True, index=True)
    status         = Column(String(12), nullable=False)    # OPTED_IN | OPTED_OUT
    source         = Column(String(100), nullable=True)    # inbound:STOP | manual:<user> ...
    consent_text   = Column(Text, nullable=True)           # proof / wording the customer agreed to
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=False)


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
