"""New Product Development (NPD) Workflow models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, Date, Numeric, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class NPDStage(str, PyEnum):
    IDEA = "IDEA"
    CONCEPT = "CONCEPT"
    DEVELOPMENT = "DEVELOPMENT"
    PILOT = "PILOT"
    LAUNCH = "LAUNCH"
    LAUNCHED = "LAUNCHED"
    CANCELLED = "CANCELLED"


class NPDCategory(str, PyEnum):
    NEW_PRODUCT = "NEW_PRODUCT"
    LINE_EXTENSION = "LINE_EXTENSION"
    REFORMULATION = "REFORMULATION"
    PACK_SIZE_CHANGE = "PACK_SIZE_CHANGE"
    COST_REDUCTION = "COST_REDUCTION"


class NPDProject(Base):
    """New Product Development project — tracks idea through launch."""
    __tablename__ = "npd_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    category = Column(Enum(NPDCategory), nullable=False, default=NPDCategory.NEW_PRODUCT)
    stage = Column(Enum(NPDStage), nullable=False, default=NPDStage.IDEA)
    description = Column(Text, nullable=True)
    target_launch_date = Column(Date, nullable=True)
    estimated_cogs = Column(Numeric(14, 4), nullable=True)   # KES per unit
    estimated_selling_price = Column(Numeric(14, 4), nullable=True)
    bom_recipe_id = Column(String(100), nullable=True)        # soft link to recipe/BOM
    regulatory_checklist = Column(JSONB, nullable=True)       # {allergen: bool, label: bool, kebs: bool, ...}
    launch_readiness_checklist = Column(JSONB, nullable=True) # {bom_approved: bool, label_approved: bool, ...}
    created_by = Column(String(200), nullable=True)
    brand = Column(String(200), nullable=True)
    target_market = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stage_gates = relationship("NPDStageGate", back_populates="project", cascade="all, delete-orphan")
    pilot_batches = relationship("NPDPilotBatch", back_populates="project", cascade="all, delete-orphan")


class NPDStageGate(Base):
    """Approval gate per stage per department."""
    __tablename__ = "npd_stage_gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("npd_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(Enum(NPDStage), nullable=False)
    department = Column(String(100), nullable=False)    # R&D | Marketing | Operations | Finance | Regulatory
    approved_flag = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("NPDProject", back_populates="stage_gates")


class NPDPilotBatchOutcome(str, PyEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    IN_PROGRESS = "IN_PROGRESS"


class NPDPilotBatch(Base):
    """Trial/pilot production batch for NPD project."""
    __tablename__ = "npd_pilot_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("npd_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_ref = Column(String(100), nullable=False)
    batch_no = Column(Integer, nullable=False, default=1)
    qty_produced = Column(Numeric(12, 3), nullable=True)
    uom = Column(String(20), default="KG", nullable=False)
    actual_cogs = Column(Numeric(14, 4), nullable=True)
    outcome = Column(Enum(NPDPilotBatchOutcome), default=NPDPilotBatchOutcome.IN_PROGRESS, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("NPDProject", back_populates="pilot_batches")
