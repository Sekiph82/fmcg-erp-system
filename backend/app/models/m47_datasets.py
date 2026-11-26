"""M47.S01.T011 report-builder datasets: an uploaded table, optionally blended (left join) with a catalog source."""
import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ReportDataset(Base):
    __tablename__ = "rb_datasets"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key           = Column(String(40), nullable=False, unique=True)
    name          = Column(String(150), nullable=False)
    columns       = Column(JSON, nullable=False)            # [{path, label, type: string|number}]
    rows          = Column(JSON, nullable=False)            # list of dicts (capped)
    row_count     = Column(Integer, nullable=False, default=0)
    join_source   = Column(String(60), nullable=True)       # a report-builder source key, e.g. "customers"
    join_local    = Column(String(60), nullable=True)       # dataset column
    join_remote   = Column(String(60), nullable=True)       # source field path
    created_by    = Column(String(100), nullable=False)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
