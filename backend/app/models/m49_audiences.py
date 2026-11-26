"""M49.S01.T011 audience lifecycle (provider sync state, hashed members, suppression list) and M49.S01.T006 ad edits.

Only SHA-256 hashes of identifiers are stored here (never the raw e-mail or phone); the raw address stays in the
consented CRM tables. SIMULATED and LIVE are separate values of `mode`."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AudienceSync(Base):
    """One audience on one ad account of one provider (a customer list, or a Meta lookalike made from one).
    status: DRAFT | SYNCING | PROCESSING | READY | SIMULATED | FAILED | UNKNOWN | DELETED.
    READY only when the provider's own status says so; SIMULATED = nothing was sent (offline simulation)."""
    __tablename__ = "m49_audience_syncs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audience_id     = Column(UUID(as_uuid=True), ForeignKey("mkt_audiences.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider        = Column(String(10), nullable=False)
    kind            = Column(String(10), nullable=False, default="CUSTOM")      # CUSTOM | LOOKALIKE
    origin_sync_id  = Column(UUID(as_uuid=True), nullable=True)                 # lookalike seed
    spec            = Column(JSON, nullable=False, default=dict)                # e.g. {"ratio": 0.01}
    name            = Column(String(200), nullable=False)
    external_id     = Column(String(200), nullable=True)
    status          = Column(String(12), nullable=False, default="DRAFT")
    mode            = Column(String(10), nullable=False, default="SIMULATED")   # SIMULATED | LIVE
    provider_status = Column(String(120), nullable=True)
    provider_size   = Column(Integer, nullable=True)
    last_job_id     = Column(String(160), nullable=True)
    approval_status = Column(String(10), nullable=False, default="NONE")        # NONE | PENDING | APPROVED | REJECTED
    approval_hash   = Column(String(64), nullable=True)
    requested_by    = Column(String(100), nullable=True)
    approved_by     = Column(String(100), nullable=True)
    last_sync_at    = Column(DateTime(timezone=True), nullable=True)
    last_error      = Column(String(500), nullable=True)
    created_by      = Column(String(100), nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AudienceSyncMember(Base):
    """What this sync has sent (hashes only). state: PENDING_ADD | IN_SYNC | PENDING_REMOVE | REMOVED."""
    __tablename__ = "m49_audience_sync_members"

    sync_id        = Column(UUID(as_uuid=True), ForeignKey("m49_audience_syncs.id", ondelete="CASCADE"), primary_key=True)
    email_sha256   = Column(String(64), primary_key=True)
    phone_sha256   = Column(String(64), nullable=True)      # E.164 with "+" (Google, TikTok)
    phone_sha256_np = Column(String(64), nullable=True)     # digits only (Meta)
    state          = Column(String(14), nullable=False, default="PENDING_ADD")
    updated_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AudienceSuppression(Base):
    """Hashed e-mails that must never be sent to an ad platform again (consent withdrawn)."""
    __tablename__ = "m49_audience_suppressions"

    email_sha256 = Column(String(64), primary_key=True)
    reason       = Column(String(30), nullable=False, default="CONSENT_WITHDRAWN")
    created_by   = Column(String(100), nullable=False)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdNodeEdit(Base):
    """Edit of documented updatable fields of a created ad object, approved by a second person, sent through the
    M48 mutation ledger (operation EDIT, key <edit id>:EDIT).
    status: PENDING_APPROVAL | APPROVED | REJECTED | APPLIED | SIMULATED | FAILED | UNKNOWN."""
    __tablename__ = "m49_ad_edits"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    root_id      = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id      = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    fields       = Column(JSON, nullable=False, default=dict)       # {"name": ..., "start_date": ..., "end_date": ...}
    status       = Column(String(18), nullable=False, default="PENDING_APPROVAL")
    payload_hash = Column(String(64), nullable=False)
    mode         = Column(String(10), nullable=True)
    read_back    = Column(JSON, nullable=True)                      # what the provider reported after the edit
    last_error   = Column(String(500), nullable=True)
    attempts     = Column(Integer, nullable=False, default=0)
    requested_by = Column(String(100), nullable=False)
    decided_by   = Column(String(100), nullable=True)
    decided_at   = Column(DateTime(timezone=True), nullable=True)
    applied_at   = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
