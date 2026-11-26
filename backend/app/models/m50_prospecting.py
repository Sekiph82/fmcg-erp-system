"""M50.S01.T001-T004 AI prospecting agent, research adapter, enrichment and buyer-intent feed state.

Provider API keys are never stored here (they come from settings); only non-secret provider settings are.
"""
import uuid

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
                        func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class M50ProviderSetting(Base):
    """One row per external data area: SEARCH | ENRICHMENT | INTENT. Nothing runs until enabled AND licensed."""
    __tablename__ = "m50_provider_settings"

    kind           = Column(String(12), primary_key=True)
    provider       = Column(String(30), nullable=False, default="")
    enabled        = Column(Boolean, nullable=False, default=False)
    licensed       = Column(Boolean, nullable=False, default=False)      # owner confirmed a licence/subscription exists
    license_note   = Column(String(500), nullable=True)
    retention_days = Column(Integer, nullable=False, default=30)
    config         = Column(JSON, nullable=False, default=dict)          # non-secret: country, language, half-life, mapping
    updated_by     = Column(String(100), nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M50Icp(Base):
    __tablename__ = "m50_icp_profiles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(150), nullable=False)
    criteria    = Column(JSON, nullable=False)       # city/region/channel/segment/size_bands/keywords
    competitors = Column(JSON, nullable=False, default=list)
    use_search  = Column(Boolean, nullable=False, default=False)
    archived    = Column(Boolean, nullable=False, default=False)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M50AgentRun(Base):
    __tablename__ = "m50_agent_runs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    icp_id      = Column(UUID(as_uuid=True), ForeignKey("m50_icp_profiles.id", ondelete="SET NULL"), nullable=True)
    criteria    = Column(JSON, nullable=False)
    llm_mode    = Column(String(15), nullable=False)     # LLM | DETERMINISTIC
    llm_model   = Column(String(80), nullable=True)
    search_state = Column(String(20), nullable=False)    # OFF | NOT_CONFIGURED | OK | ERROR
    steps       = Column(JSON, nullable=False)           # ordered step log with counts and unknowns
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M50Candidate(Base):
    __tablename__ = "m50_candidates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id           = Column(UUID(as_uuid=True), ForeignKey("m50_agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind             = Column(String(10), nullable=False)       # lead | prospect | web
    ref_id           = Column(String(60), nullable=True)
    company_name     = Column(String(255), nullable=False)
    norm_name        = Column(String(255), nullable=False, index=True)
    email            = Column(String(254), nullable=True)
    score            = Column(Float, nullable=False)
    confidence       = Column(Float, nullable=False)
    evidence         = Column(JSON, nullable=False)             # [{criterion, value, citation}]
    citations        = Column(JSON, nullable=False)             # web citations [{url, title, snippet, retrieved_at, age}]
    unknowns         = Column(JSON, nullable=False)
    territory        = Column(JSON, nullable=False)
    competitor       = Column(JSON, nullable=False)
    rationale        = Column(Text, nullable=True)
    crm_record_id    = Column(UUID(as_uuid=True), nullable=True)
    crm_association  = Column(String(20), nullable=False, default="NONE")   # NONE | EXISTING_LEAD
    evidence_age_days = Column(Integer, nullable=True)
    status           = Column(String(20), nullable=False, default="RANKED")  # RANKED | OUTREACH_PROPOSED | DISMISSED
    approval_request_id = Column(UUID(as_uuid=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M50ResearchQuery(Base):
    __tablename__ = "m50_research_queries"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider       = Column(String(30), nullable=False)
    query          = Column(String(400), nullable=False)
    country        = Column(String(2), nullable=True)
    search_lang    = Column(String(10), nullable=True)
    page           = Column(Integer, nullable=False, default=0)
    more_available = Column(Boolean, nullable=False, default=False)
    results        = Column(JSON, nullable=False)               # [{title, url, description, rank}]
    status         = Column(String(12), nullable=False)         # OK | ERROR
    error          = Column(String(300), nullable=True)
    created_by     = Column(String(100), nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at     = Column(DateTime(timezone=True), nullable=False)


class M50ResearchDoc(Base):
    """A page fetched through the SSRF-safe fetcher, with the facts extracted from it and their provenance."""
    __tablename__ = "m50_research_docs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id     = Column(UUID(as_uuid=True), ForeignKey("m50_research_queries.id", ondelete="SET NULL"), nullable=True)
    url          = Column(String(1000), nullable=False)
    final_url    = Column(String(1000), nullable=True)
    status       = Column(String(10), nullable=False)           # FETCHED | BLOCKED | FAILED
    reason       = Column(String(300), nullable=True)
    content_type = Column(String(80), nullable=True)
    size_bytes   = Column(Integer, nullable=True)
    title        = Column(String(300), nullable=True)
    facts        = Column(JSON, nullable=False)                 # [{field, value, snippet}]
    created_by   = Column(String(100), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at   = Column(DateTime(timezone=True), nullable=False)


class M50EnrichmentProposal(Base):
    __tablename__ = "m50_enrichment_proposals"
    __table_args__ = (UniqueConstraint("customer_id", "provider", "field", "value", name="uq_m50_enrich_prop"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id   = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    provider      = Column(String(30), nullable=False)
    field         = Column(String(40), nullable=False)
    value         = Column(String(500), nullable=False)
    source_ref    = Column(String(300), nullable=False)        # provider + request + record reference
    confidence    = Column(Float, nullable=False)
    consent_basis = Column(String(300), nullable=False)
    status        = Column(String(10), nullable=False, default="PROPOSED")   # PROPOSED | APPLIED | REJECTED | REVOKED
    retrieved_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at    = Column(DateTime(timezone=True), nullable=False)
    decided_by    = Column(String(100), nullable=True)
    decided_at    = Column(DateTime(timezone=True), nullable=True)
    applied_old   = Column(String(500), nullable=True)          # value before apply, for revoke


class M50IntentEvent(Base):
    """Third-party buyer-intent signal about a COMPANY (never a person). First-party scores live in ci_*."""
    __tablename__ = "m50_intent_events"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dedup_key        = Column(String(64), nullable=False, unique=True)
    feed             = Column(String(100), nullable=False)
    company_name     = Column(String(255), nullable=False)
    domain           = Column(String(255), nullable=True)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    match_method     = Column(String(12), nullable=False)       # DOMAIN | NAME | NONE
    match_confidence = Column(Float, nullable=False)
    topic            = Column(String(100), nullable=False)
    strength         = Column(Float, nullable=False)            # 0..1 from the feed
    observed_at      = Column(DateTime(timezone=True), nullable=False)
    received_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at       = Column(DateTime(timezone=True), nullable=False)
    consent_basis    = Column(String(300), nullable=False)
    status           = Column(String(10), nullable=False, default="ACTIVE")   # ACTIVE | WITHDRAWN
    imported_by      = Column(String(100), nullable=True)


class M50IntentAlert(Base):
    __tablename__ = "m50_intent_alerts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    score           = Column(Float, nullable=False)
    reasons         = Column(JSON, nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
