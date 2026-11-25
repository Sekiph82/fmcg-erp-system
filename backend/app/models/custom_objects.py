"""M45.S01.T015 admin-defined custom objects, their records and many-to-many associations."""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class CustomObjectType(Base):
    __tablename__ = "co_types"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key           = Column(String(40), nullable=False, unique=True)      # e.g. "freezer", "shelf_space"
    label         = Column(String(80), nullable=False)
    label_plural  = Column(String(80), nullable=False)
    fields        = Column(JSON, nullable=False)       # [{key, label, type, required, unique, options}]
    display_field = Column(String(40), nullable=False)
    view_roles    = Column(JSON, nullable=False, default=list)   # role names; empty = everyone with custom_objects.view
    edit_roles    = Column(JSON, nullable=False, default=list)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CustomObjectRecord(Base):
    __tablename__ = "co_records"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_id    = Column(UUID(as_uuid=True), ForeignKey("co_types.id", ondelete="CASCADE"), nullable=False, index=True)
    data       = Column(JSONB, nullable=False)
    display    = Column(String(255), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CustomObjectAssociation(Base):
    __tablename__ = "co_associations"
    __table_args__ = (UniqueConstraint("record_id", "target_type", "target_id", "label", name="uq_co_association"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id   = Column(UUID(as_uuid=True), ForeignKey("co_records.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False)        # customer | crm_record | product | sales_order | co_record
    target_id   = Column(UUID(as_uuid=True), nullable=False, index=True)
    label       = Column(String(40), nullable=False, default="related")
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
