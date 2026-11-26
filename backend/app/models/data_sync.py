"""M45.S01.T011 no-code data sync: definitions (versioned mapping), per-key state, runs with diffs and rollback,
and daily data-quality snapshots."""
import uuid

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SyncDefinition(Base):
    __tablename__ = "ds_syncs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(100), nullable=False, unique=True)
    direction     = Column(String(3), nullable=False, default="IN")        # IN (source → ERP) | OUT (ERP → destination)
    source_kind   = Column(String(10), nullable=False)                     # UPLOAD | HTTP_JSON | WEBHOOK
    source_url    = Column(String(500), nullable=True)
    secret        = Column(Text, nullable=True)                            # encrypted bearer token / webhook token hash
    target        = Column(String(20), nullable=False)                     # customers | crm_contacts | products
    key_field     = Column(String(40), nullable=False)
    mapping       = Column(JSON, nullable=False)                           # [{"target": "...", "source": "...", "transforms": [...]}]
    conflict_rule = Column(String(12), nullable=False, default="source_wins")   # source_wins | target_wins | skip
    delete_mode   = Column(String(10), nullable=False, default="ignore")   # ignore | deactivate
    version       = Column(Integer, nullable=False, default=1)
    history       = Column(JSON, nullable=False, default=list)             # earlier mapping versions
    every_minutes = Column(Integer, nullable=True)
    next_run_at   = Column(DateTime(timezone=True), nullable=True)
    watermark     = Column(DateTime(timezone=True), nullable=True)         # OUT: last exported change
    active        = Column(Boolean, nullable=False, default=True)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SyncState(Base):
    """Hash of the last source row per key: unchanged rows are skipped, vanished keys are deletes."""
    __tablename__ = "ds_state"
    __table_args__ = (UniqueConstraint("sync_id", "key", name="uq_ds_state_key"),)

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_id = Column(UUID(as_uuid=True), ForeignKey("ds_syncs.id", ondelete="CASCADE"), nullable=False, index=True)
    key     = Column(String(255), nullable=False)
    hash    = Column(String(64), nullable=False)


class SyncRun(Base):
    __tablename__ = "ds_runs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_id     = Column(UUID(as_uuid=True), ForeignKey("ds_syncs.id", ondelete="CASCADE"), nullable=False, index=True)
    version     = Column(Integer, nullable=False)
    dry_run     = Column(Boolean, nullable=False, default=False)
    trigger     = Column(String(10), nullable=False, default="MANUAL")      # MANUAL | SCHEDULE | WEBHOOK | REPLAY
    status      = Column(String(12), nullable=False, default="RUNNING")     # RUNNING | DONE | FAILED | ROLLED_BACK
    counts      = Column(JSON, nullable=False, default=dict)
    diff        = Column(JSON, nullable=False, default=list)                # first 200 changes
    errors      = Column(JSON, nullable=False, default=list)
    before      = Column(JSON, nullable=False, default=list)                # rollback images
    input       = Column(JSON, nullable=True)                               # rows received (replay), capped
    attempts    = Column(Integer, nullable=False, default=1)
    run_by      = Column(String(100), nullable=True)
    started_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class DataQualitySnapshot(Base):
    __tablename__ = "dq_snapshots"
    __table_args__ = (UniqueConstraint("day", "entity", name="uq_dq_snapshot_day"),)

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day     = Column(Date, nullable=False)
    entity  = Column(String(20), nullable=False)
    metrics = Column(JSON, nullable=False)
