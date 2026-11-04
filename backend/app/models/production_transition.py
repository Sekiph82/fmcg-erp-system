import uuid

from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Identity, Index,
    String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class ProductionTransitionEvent(Base):
    """Append-only status and approval history for production orders and operations."""

    __tablename__ = "production_transition_events"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('PRODUCTION_ORDER', 'WORK_ORDER', 'EXEC_PRODUCTION_ORDER', 'EXEC_WORK_ORDER')",
            name="ck_production_transition_entity_type",
        ),
        CheckConstraint(
            "parent_entity_type IN ('PRODUCTION_ORDER', 'EXEC_PRODUCTION_ORDER')",
            name="ck_production_transition_parent_type",
        ),
        CheckConstraint("length(trim(action)) > 0", name="ck_production_transition_action_nonempty"),
        CheckConstraint(
            "(actor_id IS NOT NULL) <> (actor_session_id IS NOT NULL)",
            name="ck_production_transition_single_actor",
        ),
        UniqueConstraint("event_seq", name="uq_production_transition_events_event_seq"),
        Index("ix_production_transition_entity_seq", "entity_type", "entity_id", "event_seq"),
        Index("ix_production_transition_parent_seq", "parent_entity_type", "parent_entity_id", "event_seq"),
        Index("ix_production_transition_actor_created", "actor_id", "created_at"),
        Index("ix_production_transition_session_created", "actor_session_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_seq = Column(BigInteger, Identity(always=True), nullable=False)
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    parent_entity_type = Column(String(40), nullable=False)
    parent_entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(40), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_production_transition_actor_users"),
        nullable=True,
    )
    actor_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sf_sessions.id", ondelete="RESTRICT", name="fk_production_transition_actor_session"),
        nullable=True,
    )
    actor_label = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
