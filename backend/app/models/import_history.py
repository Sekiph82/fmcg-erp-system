"""Import history – audit trail for every bulk import run."""
import uuid
import enum

from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ImportStatus(str, enum.Enum):
    COMPLETED  = "completed"
    PARTIAL    = "partial"
    FAILED     = "failed"
    VALIDATED  = "validated"   # validate_only run


class ImportHistory(Base, TimestampMixin):
    """One row per import run (including validate-only runs)."""
    __tablename__ = "import_history"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username     = Column(String(100), nullable=True)          # denormalised – survives user deletion
    user_roles   = Column(String(500), nullable=True)          # comma-joined role names at import time
    module       = Column(String(50),  nullable=False, index=True)
    file_name    = Column(String(255), nullable=True)
    import_mode  = Column(String(50),  nullable=False)         # validate_only | import_valid_only | strict
    total_rows   = Column(Integer, default=0, nullable=False)
    success_count= Column(Integer, default=0, nullable=False)
    failure_count= Column(Integer, default=0, nullable=False)
    status       = Column(String(30), nullable=False, default=ImportStatus.COMPLETED)
    errors_json  = Column(JSONB, nullable=True)                # list[{row, field, message}] – capped at 500

    user = relationship("User", foreign_keys=[user_id], lazy="select")
