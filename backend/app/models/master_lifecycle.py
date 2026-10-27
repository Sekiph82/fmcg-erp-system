import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


MASTER_ENTITY_TYPES = (
    "product",
    "material",
    "supplier",
    "warehouse",
    "company",
    "branch",
    "recipe",
)


class MasterLifecycleEvent(Base):
    """Append-only lifecycle history for governed master-record changes."""

    __tablename__ = "master_lifecycle_events"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('product','material','supplier','warehouse','company','branch','recipe')",
            name="ck_master_lifecycle_entity_type",
        ),
        CheckConstraint(
            "event_type IN ('DEACTIVATED','MERGED')",
            name="ck_master_lifecycle_event_type",
        ),
        CheckConstraint(
            "(event_type = 'MERGED' AND merged_into_id IS NOT NULL AND merged_into_id <> record_id) "
            "OR (event_type = 'DEACTIVATED' AND merged_into_id IS NULL)",
            name="ck_master_lifecycle_merge_target",
        ),
        Index("ix_master_lifecycle_record_created", "entity_type", "record_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(32), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(16), nullable=False)
    merged_into_id = Column(UUID(as_uuid=True), nullable=True)
    # Keep the actor UUID as immutable historical evidence even if the user is removed.
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
