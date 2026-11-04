"""Immutable lineage for canonical production work-order splits and merges."""
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProductionWorkOrderGenealogy(Base):
    """An append-only quantity edge from a superseded order to its replacement."""

    __tablename__ = "production_work_order_genealogy"
    __table_args__ = (
        CheckConstraint("action IN ('SPLIT', 'MERGE')", name="ck_work_order_genealogy_action"),
        CheckConstraint("source_work_order_id <> result_work_order_id", name="ck_work_order_genealogy_not_self"),
        CheckConstraint("transferred_quantity > 0", name="ck_work_order_genealogy_quantity_positive"),
        UniqueConstraint(
            "operation_id",
            "source_work_order_id",
            "result_work_order_id",
            name="uq_work_order_genealogy_operation_edge",
        ),
        Index("ix_work_order_genealogy_operation", "operation_id"),
        Index("ix_work_order_genealogy_source_created", "source_work_order_id", "created_at"),
        Index("ix_work_order_genealogy_result_created", "result_work_order_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    action = Column(String(10), nullable=False)
    source_work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="RESTRICT", name="fk_work_order_genealogy_source"),
        nullable=False,
    )
    result_work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="RESTRICT", name="fk_work_order_genealogy_result"),
        nullable=False,
    )
    transferred_quantity = Column(Numeric(14, 3), nullable=False)
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_work_order_genealogy_actor"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_work_order = relationship("WorkOrder", foreign_keys=[source_work_order_id], passive_deletes="all")
    result_work_order = relationship("WorkOrder", foreign_keys=[result_work_order_id], passive_deletes="all")
    actor = relationship("User", foreign_keys=[actor_id])
