"""M50.S01.T009-T011 tables: sync proposals/conflicts/options, SAML config + replay stores, OCR card drafts and add-in
OAuth grants. Evidence tables (proposals, conflicts, SAML assertions, OCR drafts, add-in grants) are archived on downgrade."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SyncOptions(Base):
    """Per-sync extras the M45 table has no column for (custom object type, association kind)."""
    __tablename__ = "m50_sync_options"

    sync_id = Column(UUID(as_uuid=True), ForeignKey("ds_syncs.id", ondelete="CASCADE"), primary_key=True)
    options = Column(JSON, nullable=False, default=dict)


class SyncProposal(Base):
    """A transactional row (sales/purchase order) staged by a sync; it becomes a DRAFT document only after a second
    person with the domain's create right approves it."""
    __tablename__ = "m50_sync_proposals"
    __table_args__ = (UniqueConstraint("sync_id", "key", name="uq_m50_sync_proposal_key"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_id     = Column(UUID(as_uuid=True), ForeignKey("ds_syncs.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id      = Column(UUID(as_uuid=True), ForeignKey("ds_runs.id", ondelete="SET NULL"), nullable=True)
    target      = Column(String(20), nullable=False)
    key         = Column(String(255), nullable=False)
    payload     = Column(JSON, nullable=False)
    status      = Column(String(12), nullable=False, default="PENDING")   # PENDING | APPLIED | REJECTED | FAILED
    proposed_by = Column(String(100), nullable=True)
    decided_by  = Column(String(100), nullable=True)
    decided_at  = Column(DateTime(timezone=True), nullable=True)
    applied_ref = Column(String(64), nullable=True)                       # id of the DRAFT document created
    error       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SyncConflict(Base):
    """A field where the source and the ERP disagree and the sync's rule kept the ERP value; an owner may resolve it."""
    __tablename__ = "m50_sync_conflicts"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_id      = Column(UUID(as_uuid=True), ForeignKey("ds_syncs.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id       = Column(UUID(as_uuid=True), ForeignKey("ds_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    key          = Column(String(255), nullable=False)
    field        = Column(String(60), nullable=False)
    source_value = Column(Text, nullable=True)
    erp_value    = Column(Text, nullable=True)
    resolution   = Column(String(8), nullable=True)                       # NULL (open) | SOURCE | ERP
    resolved_by  = Column(String(100), nullable=True)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SamlConfig(Base):
    __tablename__ = "m50_saml_configs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name              = Column(String(100), nullable=False)
    idp_entity_id     = Column(String(300), nullable=False)
    idp_sso_url       = Column(String(500), nullable=False)
    idp_x509_cert     = Column(Text, nullable=False)                      # public certificate (PEM or base64)
    sp_entity_id      = Column(String(300), nullable=False)
    email_attribute   = Column(String(100), nullable=False, default="email")
    groups_attribute  = Column(String(100), nullable=False, default="groups")
    role_mapping      = Column(JSON, nullable=False, default=dict)
    clock_skew_seconds = Column(Integer, nullable=False, default=60)
    active            = Column(Boolean, nullable=False, default=False)
    updated_by        = Column(String(100), nullable=True)
    updated_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SamlRequest(Base):
    """AuthnRequest ids we issued: a response must answer one of them, once (InResponseTo)."""
    __tablename__ = "m50_saml_requests"

    request_id  = Column(String(80), primary_key=True)
    config_id   = Column(UUID(as_uuid=True), ForeignKey("m50_saml_configs.id", ondelete="CASCADE"), nullable=False)
    redirect_to = Column(String(300), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    used_at     = Column(DateTime(timezone=True), nullable=True)


class SamlAssertionSeen(Base):
    """Assertion ids already accepted: a second presentation of the same assertion is a replay."""
    __tablename__ = "m50_saml_assertions"

    assertion_id     = Column(String(200), primary_key=True)
    config_id        = Column(UUID(as_uuid=True), ForeignKey("m50_saml_configs.id", ondelete="CASCADE"), nullable=False)
    not_on_or_after  = Column(DateTime(timezone=True), nullable=True)
    seen_at          = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OcrCardDraft(Base):
    """Text read from a business-card picture. The picture itself is never stored. Nothing becomes a contact until the
    user reviews the fields and confirms they may keep the person's details."""
    __tablename__ = "m50_ocr_card_drafts"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by  = Column(String(100), nullable=False)
    engine      = Column(String(40), nullable=False)
    text        = Column(Text, nullable=False)
    fields      = Column(JSON, nullable=False)
    status      = Column(String(10), nullable=False, default="DRAFT")    # DRAFT | CONFIRMED | DISCARDED
    consent_at  = Column(DateTime(timezone=True), nullable=True)
    contact_id  = Column(UUID(as_uuid=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AddinGrant(Base):
    """Add-in sign-in: a one-time code (PKCE S256), then a short-lived access token and a rotating refresh token.
    Only hashes are stored. Bound to a host (gmail | outlook) and the origin that started the flow."""
    __tablename__ = "m50_addin_grants"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    host            = Column(String(10), nullable=False)
    origin          = Column(String(200), nullable=False)
    scopes          = Column(JSON, nullable=False)
    code_hash       = Column(String(64), nullable=True, index=True)
    code_challenge  = Column(String(64), nullable=True)
    code_expires_at = Column(DateTime(timezone=True), nullable=True)
    access_hash     = Column(String(64), nullable=True, index=True)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    refresh_hash    = Column(String(64), nullable=True, index=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)
    prev_refresh_hash = Column(String(64), nullable=True, index=True)      # last rotated-out refresh token (reuse detection)
    revoked_at      = Column(DateTime(timezone=True), nullable=True)
    revoked_reason  = Column(String(40), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at    = Column(DateTime(timezone=True), nullable=True)
