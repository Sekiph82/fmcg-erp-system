"""M45 customer data hub: authorized data sources, prospect corpus (T001), research facts and enrichment proposals
(T002/T003), verified fields, merges (T010)."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DataSource(Base):
    """An authorized source of business data: a local import (CSV/JSON the company may use) or a provider adapter."""
    __tablename__ = "cd_sources"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(150), nullable=False)
    kind         = Column(String(15), nullable=False, default="LOCAL_IMPORT")   # LOCAL_IMPORT | PROVIDER
    license_note = Column(String(500), nullable=False)          # why we may use it (e.g. "own trade-fair list 2026")
    rows         = Column(Integer, nullable=False, default=0)
    expires_at   = Column(DateTime(timezone=True), nullable=False)   # retention: rows are deleted after this
    imported_by  = Column(String(100), nullable=True)
    imported_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProspectRecord(Base):
    __tablename__ = "cd_prospects"
    __table_args__ = (UniqueConstraint("source_id", "row_no", name="uq_cd_prospect_row"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id    = Column(UUID(as_uuid=True), ForeignKey("cd_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    row_no       = Column(Integer, nullable=False)
    company_name = Column(String(255), nullable=False)
    norm_name    = Column(String(255), nullable=False, index=True)
    city         = Column(String(100), nullable=True)
    region       = Column(String(100), nullable=True)
    channel      = Column(String(50), nullable=True)
    segment      = Column(String(100), nullable=True)
    size_band    = Column(String(5), nullable=True)            # S | M | L
    email        = Column(String(254), nullable=True)
    phone        = Column(String(50), nullable=True)
    website      = Column(String(300), nullable=True)
    tax_id       = Column(String(50), nullable=True)
    notes        = Column(Text, nullable=True)


class ResearchFact(Base):
    """One sourced value for one field of a customer/prospect, with citation and freshness. Proposals become customer
    data only when a person approves them; a verified value is never replaced silently."""
    __tablename__ = "cd_facts"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type = Column(String(12), nullable=False)           # customer | prospect
    subject_id   = Column(UUID(as_uuid=True), nullable=False, index=True)
    field        = Column(String(40), nullable=False)
    value        = Column(String(500), nullable=False)
    source_id    = Column(UUID(as_uuid=True), ForeignKey("cd_sources.id", ondelete="CASCADE"), nullable=True)
    citation     = Column(String(300), nullable=False)          # e.g. "Trade fair list 2026, row 12, column phone"
    confidence   = Column(Float, nullable=False, default=0.5)
    status       = Column(String(10), nullable=False, default="PROPOSED")   # PROPOSED | APPLIED | REJECTED
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_by   = Column(String(100), nullable=True)
    decided_at   = Column(DateTime(timezone=True), nullable=True)


class VerifiedField(Base):
    __tablename__ = "cd_verified_fields"
    __table_args__ = (UniqueConstraint("customer_id", "field", name="uq_cd_verified_field"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    field       = Column(String(40), nullable=False)
    verified_by = Column(String(100), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProspectRun(Base):
    """A prospecting search: criteria, ranked results with evidence; outreach goes through AI requests (approval)."""
    __tablename__ = "cd_prospect_runs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    criteria    = Column(JSON, nullable=False)
    results     = Column(JSON, nullable=False)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MergeLog(Base):
    """A customer/contact merge (T010): survivor, merged record snapshot and every moved reference, for audit and undo."""
    __tablename__ = "cd_merges"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity      = Column(String(10), nullable=False)            # customer | contact
    survivor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    merged_id   = Column(UUID(as_uuid=True), nullable=False)
    snapshot    = Column(JSON, nullable=False)                  # the merged row as it was
    moved       = Column(JSON, nullable=False)                  # [{"table", "column", "ids"}]
    field_changes = Column(JSON, nullable=False)                # survivor fields filled from the merged row
    reason      = Column(String(300), nullable=True)
    merged_by   = Column(String(100), nullable=False)
    merged_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    undone_by   = Column(String(100), nullable=True)
    undone_at   = Column(DateTime(timezone=True), nullable=True)


class DuplicateDismissal(Base):
    """A candidate pair a person marked "not a duplicate"; it is not suggested again."""
    __tablename__ = "cd_dup_dismissals"
    __table_args__ = (UniqueConstraint("entity", "a_id", "b_id", name="uq_cd_dup_dismissal"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity       = Column(String(10), nullable=False)
    a_id         = Column(UUID(as_uuid=True), nullable=False)       # smaller id first
    b_id         = Column(UUID(as_uuid=True), nullable=False)
    dismissed_by = Column(String(100), nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SensitiveField(Base):
    """A field classified as sensitive (T017): masked for users without data.view_sensitive; reveals are audited.
    Custom fields use cf_definitions.sensitive_flag instead."""
    __tablename__ = "cd_sensitive_fields"
    __table_args__ = (UniqueConstraint("entity", "field", name="uq_cd_sensitive_field"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity         = Column(String(20), nullable=False)          # customer | contact
    field          = Column(String(40), nullable=False)
    enabled        = Column(Boolean, nullable=False, default=True)
    retention_days = Column(Integer, nullable=True)              # clear the value this long after the record became inactive
    updated_by     = Column(String(100), nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
