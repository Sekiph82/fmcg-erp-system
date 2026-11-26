"""M48.S01.T009 provider e-signature (DocuSign eSignature, Adobe Acrobat Sign): provider configuration with sealed
secrets, the envelope/agreement ledger (claimed before any provider call) and webhook replay protection.

The local signer-code evidence flow (signature_requests / signature_records) is separate and unchanged; it is local
evidence only and never labelled provider-certified.
"""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ESignProviderConfig(Base):
    __tablename__ = "esign_provider_configs"

    provider       = Column(String(20), primary_key=True)          # DOCUSIGN | ADOBE_SIGN
    settings       = Column(JSON, nullable=False, default=dict)     # non-secret: integration key, user id, base URLs
    secrets_sealed = Column(Text, nullable=True)                    # encrypted JSON (private key, HMAC key, client secret, refresh token)
    live_enabled   = Column(Boolean, nullable=False, default=False)  # owner activation; also needs ESIGN_LIVE_ENABLED
    updated_by     = Column(String(100), nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ESignEnvelope(Base):
    """One provider envelope (DocuSign) / agreement (Adobe Sign) for one immutable quotation or contract snapshot."""
    __tablename__ = "esign_envelopes"
    __table_args__ = (
        # at most one open request per source document
        Index("uq_esign_envelope_open_source", "source_type", "source_id", unique=True,
              postgresql_where=text("status IN ('CLAIMED','SENT','DELIVERED','UNKNOWN')")),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider            = Column(String(20), nullable=False)
    mode                = Column(String(10), nullable=False)        # SIMULATED | LIVE
    idempotency_key     = Column(String(80), nullable=False, unique=True)
    source_type         = Column(String(20), nullable=False)        # QUOTATION | CONTRACT
    source_id           = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_ref          = Column(String(80), nullable=False)        # quote_no vN / contract_code vN
    source_fingerprint  = Column(String(64), nullable=False)        # SHA-256 of the canonical approved content
    snapshot_pdf        = Column(LargeBinary, nullable=False)
    snapshot_sha256     = Column(String(64), nullable=False)
    signer_name         = Column(String(120), nullable=False)
    signer_email        = Column(String(254), nullable=False)
    expire_days         = Column(Integer, nullable=False, default=30)
    status              = Column(String(15), nullable=False, index=True)   # CLAIMED SENT DELIVERED COMPLETED DECLINED VOIDED CANCELLED EXPIRED UNKNOWN FAILED INVALIDATED
    provider_ref        = Column(String(100), nullable=True, index=True)   # envelopeId / agreementId
    provider_status     = Column(String(60), nullable=True)
    error               = Column(Text, nullable=True)
    timeline            = Column(JSON, nullable=False, default=list)
    signed_pdf          = Column(LargeBinary, nullable=True)
    signed_sha256       = Column(String(64), nullable=True)
    evidence_pdf        = Column(LargeBinary, nullable=True)        # certificate of completion / audit trail
    evidence_sha256     = Column(String(64), nullable=True)
    provider_certified  = Column(Boolean, nullable=False, default=False)   # LIVE provider completion only
    completed_at        = Column(DateTime(timezone=True), nullable=True)
    erp_applied         = Column(String(200), nullable=True)        # what the completion changed in the ERP
    created_by_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_checked_at     = Column(DateTime(timezone=True), nullable=True)


class ESignWebhookEvent(Base):
    """Replay protection: each provider notification is acted on once."""
    __tablename__ = "esign_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_key", name="uq_esign_webhook_event"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider    = Column(String(20), nullable=False)
    event_key   = Column(String(64), nullable=False)
    provider_ref = Column(String(100), nullable=True)
    event       = Column(String(80), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
