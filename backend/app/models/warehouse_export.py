"""M45.S01.T020 data warehouse export: targets, jobs (incremental watermark) and runs."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ExportTarget(Base):
    __tablename__ = "dw_targets"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(100), nullable=False, unique=True)
    kind       = Column(String(10), nullable=False)          # LOCAL_DIR | S3 | POSTGRES | SNOWFLAKE | BIGQUERY
    config     = Column(JSON, nullable=False)                # non-secret settings (dir, endpoint_url, bucket, prefix, schema)
    secret     = Column(Text, nullable=True)                 # encrypted: S3 secret key / PostgreSQL DSN / Snowflake key JSON / BigQuery SA JSON
    active     = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=True)
    secret_set_by = Column(String(100), nullable=True)           # who last stored the credential (cannot approve)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExportJob(Base):
    __tablename__ = "dw_jobs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id      = Column(UUID(as_uuid=True), ForeignKey("dw_targets.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset        = Column(String(40), nullable=False)
    file_format    = Column(String(10), nullable=False, default="csv")   # csv | jsonl | parquet (M50.S01.T010: widened from 6)
    every_minutes  = Column(Integer, nullable=True)
    watermark      = Column(DateTime(timezone=True), nullable=True)      # last updated_at fully exported
    watermark_id   = Column(String(64), nullable=True)                   # tie-breaker within the same timestamp
    known_ids      = Column(JSON, nullable=False, default=list)          # ids present at the last run (delete detection)
    schema_cols    = Column(JSON, nullable=False, default=list)          # columns exported last time (schema-change notice)
    next_run_at    = Column(DateTime(timezone=True), nullable=True)
    active         = Column(Boolean, nullable=False, default=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExportRun(Base):
    __tablename__ = "dw_runs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id      = Column(UUID(as_uuid=True), ForeignKey("dw_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status      = Column(String(10), nullable=False, default="RUNNING")  # RUNNING | DONE | FAILED
    rows        = Column(Integer, nullable=False, default=0)
    deleted     = Column(Integer, nullable=False, default=0)
    files       = Column(JSON, nullable=False, default=list)
    schema_change = Column(JSON, nullable=True)
    error       = Column(String(500), nullable=True)
    mode        = Column(String(10), nullable=True)                     # SIMULATED | LIVE (Snowflake/BigQuery runs)
    started_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
