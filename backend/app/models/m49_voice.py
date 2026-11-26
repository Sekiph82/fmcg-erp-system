"""M49.S01.T004/T005 contact-center and transcription tables (migration 0079).

Queues, agent presence, missed-call callbacks, transfers, dispositions, voicemail, webhook replay keys and the
transcription job/edit trail. Extends call_logs/voice_* (M36/M43); nothing here replaces them.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base, TimestampMixin


class VoiceQueue(Base, TimestampMixin):
    __tablename__ = "voice_queues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    direction = Column(String(8), nullable=False, default="INBOUND")            # INBOUND | OUTBOUND
    strategy = Column(String(12), nullable=False, default="LONGEST_IDLE")       # LONGEST_IDLE | RING_ALL
    member_user_ids = Column(JSONB, nullable=False, default=list)
    max_wait_seconds = Column(Integer, nullable=False, default=60)
    overflow = Column(String(10), nullable=False, default="CALLBACK")           # CALLBACK | VOICEMAIL
    is_active = Column(Boolean, nullable=False, default=True)


class VoiceQueueEntry(Base):
    __tablename__ = "voice_queue_entries"
    __table_args__ = (Index("ix_voice_queue_entries_q_state", "queue_id", "state"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("voice_queues.id", ondelete="CASCADE"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("call_logs.id", ondelete="SET NULL"), nullable=True, index=True)
    phone_number = Column(String(50), nullable=False)
    state = Column(String(10), nullable=False, default="WAITING")               # WAITING | ASSIGNED | OVERFLOW
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    enqueued_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class VoicePresence(Base):
    __tablename__ = "voice_agent_presence"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(10), nullable=False, default="OFFLINE")              # AVAILABLE | BUSY | AWAY | OFFLINE
    status_since = Column(DateTime(timezone=True), nullable=False)
    current_call_id = Column(UUID(as_uuid=True), nullable=True)


class VoiceCallback(Base, TimestampMixin):
    """One open callback request per phone number (a repeat miss only counts up: idempotent)."""
    __tablename__ = "voice_callbacks"
    __table_args__ = (Index("uq_voice_callback_open", "phone_number", unique=True, postgresql_where="state = 'PENDING'"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(50), nullable=False)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("voice_queues.id", ondelete="SET NULL"), nullable=True)
    source_call_id = Column(UUID(as_uuid=True), ForeignKey("call_logs.id", ondelete="SET NULL"), nullable=True)
    state = Column(String(10), nullable=False, default="PENDING")               # PENDING | DONE | EXPIRED | CANCELLED
    missed_count = Column(Integer, nullable=False, default=1)
    attempts = Column(Integer, nullable=False, default=0)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_outcome = Column(String(20), nullable=True)
    done_at = Column(DateTime(timezone=True), nullable=True)


class VoiceTransfer(Base, TimestampMixin):
    __tablename__ = "voice_transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(5), nullable=False)                                    # COLD | WARM
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    to_number = Column(String(50), nullable=False)
    state = Column(String(12), nullable=False, default="REQUESTED")  # REQUESTED|CONSULTING|READY|DECLINED|COMPLETED|FAILED
    provider_ref = Column(String(80), nullable=True)                            # consult-leg call SID
    error = Column(String(300), nullable=True)


class VoiceCallDisposition(Base):
    __tablename__ = "voice_call_dispositions"

    call_id = Column(UUID(as_uuid=True), ForeignKey("call_logs.id", ondelete="CASCADE"), primary_key=True)
    code = Column(String(24), nullable=False)
    note = Column(String(500), nullable=True)
    set_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    set_at = Column(DateTime(timezone=True), nullable=False)


class VoiceVoicemail(Base):
    __tablename__ = "voice_voicemails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("voice_queues.id", ondelete="SET NULL"), nullable=True)
    phone_number = Column(String(50), nullable=False)
    provider_recording_id = Column(String(64), nullable=False, unique=True)
    recording_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class VoiceProviderEvent(Base):
    """Webhook replay guard: one row per (provider, event key)."""
    __tablename__ = "voice_provider_events"
    __table_args__ = (UniqueConstraint("provider", "event_key", name="uq_voice_provider_event"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(20), nullable=False)
    event_key = Column(String(200), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False)


class TranscriptJob(Base, TimestampMixin):
    __tablename__ = "m49_transcript_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(8), nullable=False)                             # call | meeting
    source_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    engine = Column(String(12), nullable=False)                                 # openai | local | http | manual
    model = Column(String(40), nullable=True)
    language_requested = Column(String(6), nullable=False, default="auto")      # auto | en | sw | tr
    language_detected = Column(String(10), nullable=True)
    diarize = Column(Boolean, nullable=False, default=False)
    status = Column(String(14), nullable=False, default="PENDING")  # PENDING|DONE|FAILED|NOT_AVAILABLE|WITHDRAWN|EXPIRED
    review_status = Column(String(10), nullable=False, default="UNREVIEWED")    # UNREVIEWED | REVIEWED
    error_code = Column(String(24), nullable=True)
    error = Column(String(300), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    segments = Column(JSONB, nullable=True)                                     # redacted [{start,end,speaker,text,edited}]
    redacted_segments = Column(Integer, nullable=False, default=0)
    quality = Column(JSONB, nullable=True)                                      # provider signals and flags only
    warnings = Column(JSONB, nullable=True)
    participants_consented = Column(Boolean, nullable=False, default=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)


class TranscriptEdit(Base):
    __tablename__ = "m49_transcript_edits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("m49_transcript_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False)
    old_text = Column(Text, nullable=False)
    new_text = Column(Text, nullable=False)
    old_speaker = Column(String(20), nullable=True)
    new_speaker = Column(String(20), nullable=True)
    editor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=False)
