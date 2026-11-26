"""M51.S01.T006/T007/T010 AI image drafts, media job queue and pluggable object storage state.

Secrets are never stored here (S3 and image-provider keys come from settings)."""
import uuid

from sqlalchemy import (JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _id():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _ts():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M51ImageJob(Base):
    """One image generation/edit request. The result is a DRAFT MARKETING_CREATIVE document; nothing uses it before approval."""
    __tablename__ = "m51_image_jobs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_m51_image_idem"),)

    id              = _id()
    operation       = Column(String(10), nullable=False)                 # GENERATE | EDIT
    provider        = Column(String(20), nullable=False)                 # simulator | openai | stability
    model           = Column(String(80), nullable=True)
    mode            = Column(String(10), nullable=False)                 # SIMULATED | LIVE
    status          = Column(String(12), nullable=False)                 # REJECTED | FAILED | GENERATED | APPROVED | DISCARDED
    title           = Column(String(200), nullable=False)
    prompt          = Column(Text, nullable=False)
    prompt_sha256   = Column(String(64), nullable=False)
    overlay_text    = Column(String(300), nullable=True)
    size            = Column(String(12), nullable=False, default="1024x1024")
    brand_key       = Column(String(40), nullable=True)
    source_document_id = Column(UUID(as_uuid=True), nullable=True)       # EDIT input (soft link to documents.id)
    document_id     = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    findings        = Column(JSON, nullable=False, default=list)         # moderation + claim findings
    provenance      = Column(JSON, nullable=False, default=dict)         # provider, model, prompt hash, time, request id
    cost_estimate   = Column(Numeric(10, 4), nullable=False, default=0)
    error           = Column(String(400), nullable=True)
    idempotency_key = Column(String(80), nullable=True)
    created_by      = Column(String(100), nullable=True)
    created_by_id   = Column(UUID(as_uuid=True), nullable=True)
    reviewed_by     = Column(String(100), nullable=True)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)
    review_note     = Column(String(300), nullable=True)
    created_at      = _ts()


class M51ImageUsage(Base):
    """Month budget ledger for image generation (reserve before the call, settle after)."""
    __tablename__ = "m51_image_usage"

    month = Column(String(7), primary_key=True)
    spent = Column(Numeric(12, 4), nullable=False, default=0)
    calls = Column(Integer, nullable=False, default=0)


class M51StorageObject(Base):
    """A stored media object (local or S3-compatible). Private by default; served only through signed, authorized URLs."""
    __tablename__ = "m51_storage_objects"

    id             = _id()
    backend        = Column(String(8), nullable=False)                    # local | s3
    key            = Column(String(80), nullable=False, unique=True)      # opaque random key
    owner_type     = Column(String(20), nullable=False, default="MEDIA")  # MEDIA | CMS_MEDIA | DOCUMENT | JOB_OUTPUT
    owner_id       = Column(String(64), nullable=True)
    file_name      = Column(String(200), nullable=False)
    mime           = Column(String(60), nullable=False)
    size           = Column(BigInteger, nullable=False, default=0)
    sha256         = Column(String(64), nullable=True)
    status         = Column(String(12), nullable=False)                    # UPLOADING | READY | QUARANTINED | DELETED
    scan_status    = Column(String(14), nullable=False, default="PENDING")  # PENDING | CLEAN | INFECTED | NOT_SCANNED | SCAN_ERROR
    approval       = Column(String(10), nullable=False, default="DRAFT")   # DRAFT | APPROVED (job outputs need a second person)
    access_version = Column(Integer, nullable=False, default=1)           # bump = every issued URL stops working
    retention_until = Column(DateTime(timezone=True), nullable=True)
    meta           = Column(JSON, nullable=False, default=dict)            # duration, dimensions, thumbnails, hooks queued
    created_by     = Column(String(100), nullable=True)
    approved_by    = Column(String(100), nullable=True)
    created_at     = _ts()
    deleted_at     = Column(DateTime(timezone=True), nullable=True)


class M51UploadSession(Base):
    """Multipart / resumable upload. Parts are PUT in order-free; the session survives restarts until it expires."""
    __tablename__ = "m51_upload_sessions"

    id          = _id()
    object_id   = Column(UUID(as_uuid=True), ForeignKey("m51_storage_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    backend_upload_id = Column(String(300), nullable=True)                # S3 UploadId
    part_size   = Column(Integer, nullable=False)
    total_size  = Column(BigInteger, nullable=False)
    parts       = Column(JSON, nullable=False, default=dict)               # {"1": {"size": n, "etag": "...", "sha256": "..."}}
    status      = Column(String(10), nullable=False, default="OPEN")      # OPEN | COMPLETED | ABORTED | EXPIRED
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_by  = Column(String(100), nullable=True)
    created_at  = _ts()


class M51StorageQuota(Base):
    """Byte quota per owner_type ('*' = all media). A missing row falls back to M51_STORAGE_QUOTA_BYTES."""
    __tablename__ = "m51_storage_quotas"

    scope      = Column(String(20), primary_key=True)
    max_bytes  = Column(BigInteger, nullable=False)
    updated_by = Column(String(100), nullable=True)


class M51StorageBackup(Base):
    """A backup run: copies of READY objects under a backup prefix plus a sha256 manifest."""
    __tablename__ = "m51_storage_backups"

    id           = _id()
    status       = Column(String(10), nullable=False)                      # RUNNING | COMPLETED | FAILED
    object_count = Column(Integer, nullable=False, default=0)
    total_bytes  = Column(BigInteger, nullable=False, default=0)
    manifest     = Column(JSON, nullable=False, default=list)              # [{id, key, sha256, size}]
    error        = Column(String(400), nullable=True)
    created_by   = Column(String(100), nullable=True)
    created_at   = _ts()
    restored_at  = Column(DateTime(timezone=True), nullable=True)


class M51MediaJob(Base):
    """Queued ffmpeg / TTS work with progress. Output is a DRAFT storage object until a second person approves it."""
    __tablename__ = "m51_media_jobs"

    id           = _id()
    kind         = Column(String(12), nullable=False)       # NARRATION | CAPTIONS | POSTER | TRIM | TRANSCODE
    status       = Column(String(12), nullable=False)       # QUEUED | RUNNING | SUCCEEDED | FAILED | TIMEOUT | CANCELLED | UNAVAILABLE
    progress     = Column(Float, nullable=False, default=0)  # 0..1
    params       = Column(JSON, nullable=False, default=dict)
    source_object_id = Column(UUID(as_uuid=True), ForeignKey("m51_storage_objects.id", ondelete="SET NULL"), nullable=True)
    output_object_id = Column(UUID(as_uuid=True), ForeignKey("m51_storage_objects.id", ondelete="SET NULL"), nullable=True)
    result       = Column(JSON, nullable=False, default=dict)   # engine, voice, language support, caption text...
    error        = Column(String(400), nullable=True)
    created_by   = Column(String(100), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    finished_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = _ts()
