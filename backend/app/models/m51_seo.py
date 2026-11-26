"""M51.S01.T003/T004/T005/T009 state: Search Console snapshots, technical SEO crawls, keyword imports, AEO measurement
and secure visitor e-mail verification. Tokens, codes and addresses are never stored in clear except the pending
address of an unconsumed verification (wiped on use) and the local outbox body (deleted on use/expiry)."""
import uuid

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
                        func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def _id():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ── T003 Google Search Console ──────────────────────────────────────────────────────────────────

class M51GscSnapshot(Base):
    """One stored Search Analytics answer. ``source`` keeps simulator data apart from live provider data."""
    __tablename__ = "m51_gsc_snapshots"

    id          = _id()
    site_url    = Column(String(300), nullable=False, index=True)
    params_hash = Column(String(64), nullable=False, index=True)
    params      = Column(JSON, nullable=False)
    rows        = Column(JSON, nullable=False)
    row_count   = Column(Integer, nullable=False, default=0)
    data_state  = Column(String(12), nullable=False, default="final")
    source      = Column(String(20), nullable=False)          # LIVE | LOCAL_SIMULATOR
    metadata_   = Column("metadata", JSON, nullable=True)     # provider metadata (first_incomplete_date)
    created_by  = Column(String(100), nullable=True)
    fetched_at  = _now()


class M51GscSubmission(Base):
    """Sitemap submission: provider mutation, so a second person approves before the PUT is sent."""
    __tablename__ = "m51_gsc_submissions"

    id           = _id()
    site_url     = Column(String(300), nullable=False)
    feedpath     = Column(String(1000), nullable=False)
    status       = Column(String(12), nullable=False, default="PENDING")   # PENDING | SUBMITTED | FAILED | REJECTED
    requested_by = Column(String(100), nullable=False)
    decided_by   = Column(String(100), nullable=True)
    result       = Column(String(500), nullable=True)
    source       = Column(String(20), nullable=True)
    created_at   = _now()
    decided_at   = Column(DateTime(timezone=True), nullable=True)


# ── T004 technical SEO ──────────────────────────────────────────────────────────────────────────

class M51SeoSite(Base):
    """Allow-list: the crawler and the lab/field vitals touch only these origins."""
    __tablename__ = "m51_seo_sites"

    id         = _id()
    origin     = Column(String(300), nullable=False, unique=True)
    kind       = Column(String(20), nullable=False)           # OWN | AUTHORIZED_SOURCE
    note       = Column(String(500), nullable=True)           # who authorised it (required for AUTHORIZED_SOURCE)
    created_by = Column(String(100), nullable=True)
    created_at = _now()


class M51SeoCrawl(Base):
    __tablename__ = "m51_seo_crawls"

    id          = _id()
    origin      = Column(String(300), nullable=False, index=True)
    status      = Column(String(12), nullable=False, default="RUNNING")   # RUNNING | DONE | FAILED
    config      = Column(JSON, nullable=False)
    summary     = Column(JSON, nullable=True)
    error       = Column(String(500), nullable=True)
    created_by  = Column(String(100), nullable=True)
    created_at  = _now()
    finished_at = Column(DateTime(timezone=True), nullable=True)


class M51SeoPage(Base):
    __tablename__ = "m51_seo_pages"

    id       = _id()
    crawl_id = Column(UUID(as_uuid=True), ForeignKey("m51_seo_crawls.id", ondelete="CASCADE"), nullable=False, index=True)
    url      = Column(String(1000), nullable=False)
    status   = Column(Integer, nullable=True)
    data     = Column(JSON, nullable=False)


class M51SeoIssue(Base):
    __tablename__ = "m51_seo_issues"

    id       = _id()
    crawl_id = Column(UUID(as_uuid=True), ForeignKey("m51_seo_crawls.id", ondelete="CASCADE"), nullable=False, index=True)
    url      = Column(String(1000), nullable=False)
    code     = Column(String(40), nullable=False)
    severity = Column(String(8), nullable=False)               # ERROR | WARN | INFO
    detail   = Column(String(500), nullable=True)


class M51Keyword(Base):
    __tablename__ = "m51_keywords"
    __table_args__ = (UniqueConstraint("keyword", "locale", "source", name="uq_m51_keyword"),)

    id         = _id()
    keyword    = Column(String(200), nullable=False, index=True)
    locale     = Column(String(8), nullable=False, default="en")
    volume     = Column(Integer, nullable=True)
    difficulty = Column(Float, nullable=True)
    cpc        = Column(Float, nullable=True)
    intent     = Column(String(20), nullable=True)
    source     = Column(String(60), nullable=False)            # name of the supplier of the CSV
    batch_id   = Column(UUID(as_uuid=True), nullable=False)
    imported_by = Column(String(100), nullable=True)
    created_at = _now()


# ── T005 AEO measurement ────────────────────────────────────────────────────────────────────────

class M51AeoPromptSet(Base):
    __tablename__ = "m51_aeo_prompt_sets"

    id                 = _id()
    name               = Column(String(120), nullable=False)
    locale             = Column(String(2), nullable=False)      # en | sw | tr
    prompts            = Column(JSON, nullable=False)
    brand_terms        = Column(JSON, nullable=False)
    brand_domains      = Column(JSON, nullable=False, default=list)
    competitor_terms   = Column(JSON, nullable=False, default=list)
    provider           = Column(String(20), nullable=False, default="")   # "" | ai_provider | simulator
    samples_per_prompt = Column(Integer, nullable=False, default=3)
    max_calls_per_run  = Column(Integer, nullable=False, default=30)
    consent_confirmed  = Column(Boolean, nullable=False, default=False)  # owner accepts provider terms and cost
    archived           = Column(Boolean, nullable=False, default=False)
    created_by         = Column(String(100), nullable=True)
    created_at         = _now()


class M51AeoRun(Base):
    __tablename__ = "m51_aeo_runs"

    id            = _id()
    set_id        = Column(UUID(as_uuid=True), ForeignKey("m51_aeo_prompt_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    provider      = Column(String(30), nullable=False)
    model         = Column(String(120), nullable=True)
    model_version = Column(String(120), nullable=True)
    source        = Column(String(12), nullable=False)          # LIVE | SIMULATED
    status        = Column(String(10), nullable=False)          # DONE | PARTIAL | FAILED
    calls         = Column(Integer, nullable=False, default=0)
    summary       = Column(JSON, nullable=True)
    error         = Column(String(500), nullable=True)
    created_by    = Column(String(100), nullable=True)
    created_at    = _now()


class M51AeoAnswer(Base):
    __tablename__ = "m51_aeo_answers"

    id          = _id()
    run_id      = Column(UUID(as_uuid=True), ForeignKey("m51_aeo_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt      = Column(String(400), nullable=False)
    sample      = Column(Integer, nullable=False)
    answer      = Column(Text, nullable=True)
    brand       = Column(Boolean, nullable=False, default=False)
    brand_cited = Column(Boolean, nullable=False, default=False)
    competitors = Column(JSON, nullable=False, default=list)
    citations   = Column(JSON, nullable=False, default=list)    # [{url, host, position}]
    asked_at    = _now()


# ── T009 visitor e-mail verification ────────────────────────────────────────────────────────────

class M51VisitorVerification(Base):
    __tablename__ = "m51_visitor_verifications"

    id           = _id()
    visitor_hash = Column(String(64), nullable=False, index=True)
    session_hash = Column(String(64), nullable=False)
    email_hash   = Column(String(64), nullable=False, index=True)
    email        = Column(String(254), nullable=True)           # pending address only; NULL once used or revoked
    ip_hash      = Column(String(64), nullable=False, index=True)
    token_hash   = Column(String(64), nullable=False, unique=True)
    code_hash    = Column(String(64), nullable=False)
    attempts     = Column(Integer, nullable=False, default=0)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    expires_at   = Column(DateTime(timezone=True), nullable=False)
    consumed_at  = Column(DateTime(timezone=True), nullable=True)
    revoked_at   = Column(DateTime(timezone=True), nullable=True)


class M51VisitorMailOutbox(Base):
    """Local outbox: the only place a verification message goes unless Mailpit mode is switched on."""
    __tablename__ = "m51_visitor_mail_outbox"

    id              = _id()
    verification_id = Column(UUID(as_uuid=True), ForeignKey("m51_visitor_verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    to_email        = Column(String(254), nullable=False)
    subject         = Column(String(200), nullable=False)
    body            = Column(Text, nullable=False)
    channel         = Column(String(10), nullable=False)        # OUTBOX | MAILPIT
    created_at      = _now()
