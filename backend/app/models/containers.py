"""Returnable Packaging / Container Management models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, Date, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ContainerCondition(str, PyEnum):
    GOOD = "GOOD"
    DAMAGED = "DAMAGED"
    LOST = "LOST"


class IssuanceStatus(str, PyEnum):
    OUTSTANDING = "OUTSTANDING"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    CLOSED = "CLOSED"
    WRITTEN_OFF = "WRITTEN_OFF"
    OVERDUE = "OVERDUE"


class ContainerType(Base):
    """Registry of returnable container types (crates, drums, pallets, bottles)."""
    __tablename__ = "container_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    deposit_amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(10), default="KES", nullable=False)
    material = Column(String(100), nullable=True)       # plastic | glass | metal | wood
    capacity_liters = Column(Numeric(8, 2), nullable=True)
    weight_kg = Column(Numeric(8, 3), nullable=True)
    active_flag = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    issuances = relationship("ContainerIssuance", back_populates="container_type")


class ContainerIssuance(Base):
    """Record of containers issued to a customer on a delivery."""
    __tablename__ = "container_issuances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issuance_ref = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    customer_name = Column(String(200), nullable=True)
    container_type_id = Column(UUID(as_uuid=True), ForeignKey("container_types.id", ondelete="RESTRICT"), nullable=False)
    delivery_ref = Column(String(100), nullable=True)        # link to delivery/shipment
    qty_issued = Column(Integer, nullable=False)
    qty_returned = Column(Integer, default=0, nullable=False)
    qty_outstanding = Column(Integer, nullable=False)         # computed: issued - returned
    deposit_charged = Column(Numeric(14, 2), nullable=True)
    deposit_refunded = Column(Numeric(14, 2), default=0)
    issued_at = Column(DateTime, default=datetime.utcnow)
    return_due_date = Column(Date, nullable=True)
    status = Column(Enum(IssuanceStatus), default=IssuanceStatus.OUTSTANDING, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    container_type = relationship("ContainerType", back_populates="issuances")
    returns = relationship("ContainerReturn", back_populates="issuance", cascade="all, delete-orphan")


class ContainerReturn(Base):
    """Record of containers returned by a customer."""
    __tablename__ = "container_returns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issuance_id = Column(UUID(as_uuid=True), ForeignKey("container_issuances.id", ondelete="CASCADE"), nullable=False, index=True)
    qty_returned = Column(Integer, nullable=False)
    condition = Column(Enum(ContainerCondition), default=ContainerCondition.GOOD, nullable=False)
    returned_at = Column(DateTime, default=datetime.utcnow)
    refund_amount = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    issuance = relationship("ContainerIssuance", back_populates="returns")
