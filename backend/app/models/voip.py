import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class CallDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CallOutcome(str, enum.Enum):
    ANSWERED = "ANSWERED"
    NO_ANSWER = "NO_ANSWER"
    BUSY = "BUSY"
    VOICEMAIL = "VOICEMAIL"
    FAILED = "FAILED"


class CallLog(Base, TimestampMixin):
    __tablename__ = "call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_ref = Column(String(100), unique=True, nullable=False, index=True)
    direction = Column(String(20), nullable=False, default="OUTBOUND")
    phone_number = Column(String(50), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    crm_record_id = Column(UUID(as_uuid=True), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    outcome = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    recording_url = Column(String(500), nullable=True)
    call_script_id = Column(UUID(as_uuid=True), ForeignKey("call_scripts.id", ondelete="SET NULL"), nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(DateTime, nullable=True)
    tags = Column(String(300), nullable=True)
    # M36.S04.T002 recording consent and retention
    recording_consent = Column(Boolean, default=False, nullable=False)
    consent_note = Column(String(300), nullable=True)            # how consent was given, e.g. "agreed at call start"
    recording_expires_at = Column(DateTime(timezone=True), nullable=True)
    transcript = Column(Text, nullable=True)
    # M43.S01.T008 provider lifecycle
    provider = Column(String(30), nullable=True)
    provider_session_id = Column(String(100), nullable=True)   # partial unique index in migration 0073
    status = Column(String(15), nullable=True)            # QUEUED|RINGING|ANSWERED|COMPLETED|NO_ANSWER|BUSY|FAILED
    ivr_menu_id = Column(UUID(as_uuid=True), ForeignKey("voice_ivr_menus.id", ondelete="SET NULL"), nullable=True)
    ivr_step = Column(String(20), nullable=True)
    dialer_session_id = Column(UUID(as_uuid=True), ForeignKey("voice_dialer_sessions.id", ondelete="SET NULL"), nullable=True)
    cost_amount = Column(String(20), nullable=True)
    cost_currency = Column(String(10), nullable=True)
    # M43.S01.T009 transcription
    transcript_segments = Column(JSONB, nullable=True)     # [{"start": s, "end": s, "speaker": "A", "text": "..."}]
    transcript_language = Column(String(10), nullable=True)
    transcription_status = Column(String(15), nullable=True)   # PENDING|DONE|FAILED|WITHDRAWN
    transcription_error = Column(String(300), nullable=True)
    transcription_attempts = Column(Integer, nullable=False, default=0, server_default="0")

    customer = relationship("Customer", foreign_keys=[customer_id])
    agent = relationship("User", foreign_keys=[agent_id])
    call_script = relationship("CallScript", foreign_keys=[call_script_id])


class CallScript(Base, TimestampMixin):
    __tablename__ = "call_scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    purpose = Column(String(100), nullable=False, default="sales")
    script_text = Column(Text, nullable=False)
    talking_points = Column(Text, nullable=True)
    objection_handlers = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])


class VoiceAgentProfile(Base):
    """M43.S01.T008: the phone an agent answers on (click-to-call rings it first; IVR teams dial it)."""
    __tablename__ = "voice_agent_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    phone_number = Column(String(50), nullable=False)
    available = Column(Boolean, nullable=False, default=True)


class VoiceIvrMenu(Base, TimestampMixin):
    """Inbound IVR menu on one provider number: greeting, digit options → team users / numbers."""
    __tablename__ = "voice_ivr_menus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    phone_number = Column(String(50), nullable=False, unique=True)
    greeting_text = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False, default=list)    # [{"digit": "1", "label": "Sales", "user_ids": [...], "phone_numbers": [...]}]
    record_calls = Column(Boolean, nullable=False, default=False)
    consent_text = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class DialerSession(Base, TimestampMixin):
    """Power dialer: one agent works through a queue of numbers, one call at a time."""
    __tablename__ = "voice_dialer_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    status = Column(String(10), nullable=False, default="ACTIVE")    # ACTIVE | PAUSED | DONE
    items = Column(JSONB, nullable=False, default=list)              # [{"phone", "crm_record_id", "customer_id", "label", "state", "call_id"}]
    current_index = Column(Integer, nullable=True)
