"""
Production Execution System — Production Orders + Work Orders + Genealogy.
Tables: exec_production_orders, exec_work_orders, exec_order_materials,
        exec_batch_genealogy, exec_split_merge_log, exec_ai_recs
"""
import uuid
from enum import Enum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class ProdExecStatus(str, Enum):
    DRAFT       = "DRAFT"
    PLANNED     = "PLANNED"
    RELEASED    = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED      = "PAUSED"
    COMPLETED   = "COMPLETED"
    CLOSED      = "CLOSED"
    CANCELLED   = "CANCELLED"

class WOExecStatus(str, Enum):
    PENDING     = "PENDING"
    READY       = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED      = "PAUSED"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"

class ExecSourceType(str, Enum):
    MRP                = "MRP"
    MPS                = "MPS"
    MANUAL             = "MANUAL"
    SALES              = "SALES"
    SUBCONTRACT_RETURN = "SUBCONTRACT_RETURN"

class ExecMatStatus(str, Enum):
    RESERVED = "RESERVED"
    ISSUED   = "ISSUED"
    CONSUMED = "CONSUMED"
    RETURNED = "RETURNED"
    SCRAPPED = "SCRAPPED"

class ExecScrapCategory(str, Enum):
    PROCESS  = "PROCESS"
    QUALITY  = "QUALITY"
    DAMAGE   = "DAMAGE"
    HANDLING = "HANDLING"

class ExecSplitMergeType(str, Enum):
    SPLIT = "SPLIT"
    MERGE = "MERGE"

class ExecAIAgentType(str, Enum):
    EXECUTION_ANALYZER = "EXECUTION_ANALYZER"
    DEVIATION_DETECTOR = "DEVIATION_DETECTOR"

class ExecAIRecStatus(str, Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ── Models ─────────────────────────────────────────────────────────────────────

class ProdExecOrder(Base):
    """Production Order — batch-level execution record."""
    __tablename__ = "exec_production_orders"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no = Column(String(60), unique=True, nullable=False, index=True)

    # Product / BOM links
    product_id  = Column(UUID(as_uuid=True), ForeignKey("products.id",       ondelete="SET NULL"), nullable=True)
    bom_id      = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id",  ondelete="SET NULL"), nullable=True)
    routing_id  = Column(UUID(as_uuid=True), ForeignKey("routings.id",       ondelete="SET NULL"), nullable=True)

    # Denormalised names for fast list queries
    product_name = Column(String(200), nullable=True)
    bom_code     = Column(String(50),  nullable=True)

    # Quantities
    planned_qty   = Column(Numeric(14, 4), nullable=False)
    completed_qty = Column(Numeric(14, 4), default=0)
    scrap_qty     = Column(Numeric(14, 4), default=0)
    rework_qty    = Column(Numeric(14, 4), default=0)
    uom           = Column(String(20),     nullable=False, default="KG")
    batch_no      = Column(String(100),    nullable=True, index=True)  # output lot/batch

    # Source
    source_type        = Column(String(30), default="MANUAL")
    source_document_id = Column(UUID(as_uuid=True), nullable=True)
    priority           = Column(Integer, default=5)

    # Scheduling
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_end   = Column(DateTime(timezone=True), nullable=True)
    actual_start  = Column(DateTime(timezone=True), nullable=True)
    actual_end    = Column(DateTime(timezone=True), nullable=True)

    # Location
    plant_id           = Column(String(50), nullable=True)
    section_id         = Column(String(50), nullable=True)
    line_id            = Column(String(50), nullable=True)
    preferred_machine_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    status = Column(String(20), default="DRAFT", index=True)

    # Costing
    planned_material_cost = Column(Numeric(16, 2), default=0)
    actual_material_cost  = Column(Numeric(16, 2), default=0)
    planned_labor_cost    = Column(Numeric(16, 2), default=0)
    actual_labor_cost     = Column(Numeric(16, 2), default=0)
    overhead_cost         = Column(Numeric(16, 2), default=0)
    total_actual_cost     = Column(Numeric(16, 2), default=0)
    cost_per_uom          = Column(Numeric(14, 4), nullable=True)

    # Genealogy
    parent_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="SET NULL"), nullable=True)
    is_rework       = Column(Boolean, default=False)
    is_split        = Column(Boolean, default=False)
    rework_reason   = Column(Text,    nullable=True)

    # Meta
    remarks     = Column(Text, nullable=True)
    created_by  = Column(UUID(as_uuid=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    work_orders = relationship(
        "ExecWorkOrder",
        back_populates="production_order",
        cascade="all, delete-orphan",
        order_by="ExecWorkOrder.step_sequence",
    )
    materials = relationship(
        "ExecOrderMaterial",
        back_populates="production_order",
        cascade="all, delete-orphan",
    )
    genealogy_links = relationship(
        "BatchGenealogy",
        back_populates="production_order",
        cascade="all, delete-orphan",
    )
    ai_recs = relationship(
        "ExecAIRec",
        back_populates="production_order",
        cascade="all, delete-orphan",
    )


class ExecWorkOrder(Base):
    """Work Order — single routing step execution within a production order."""
    __tablename__ = "exec_work_orders"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id  = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_code       = Column(String(50),  nullable=True)
    step_sequence        = Column(Integer,     nullable=False)
    step_name            = Column(String(200), nullable=False)

    # Resources
    work_center_id      = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    section_id          = Column(String(50),  nullable=True)
    line_id             = Column(String(50),  nullable=True)
    machine_id          = Column(UUID(as_uuid=True), nullable=True)
    assigned_operator_id = Column(UUID(as_uuid=True), nullable=True)

    # Quantities
    planned_qty   = Column(Numeric(14, 4), nullable=False)
    completed_qty = Column(Numeric(14, 4), default=0)
    scrap_qty     = Column(Numeric(14, 4), default=0)
    rework_qty    = Column(Numeric(14, 4), default=0)

    # Time (minutes)
    setup_time_planned   = Column(Numeric(8, 2), default=0)
    run_time_planned     = Column(Numeric(8, 2), default=0)
    cleanup_time_planned = Column(Numeric(8, 2), default=0)
    setup_time_actual    = Column(Numeric(8, 2), nullable=True)
    run_time_actual      = Column(Numeric(8, 2), nullable=True)
    cleanup_time_actual  = Column(Numeric(8, 2), nullable=True)

    # Dependency
    dependency_work_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id", ondelete="SET NULL"), nullable=True)

    # QC
    qc_required_flag = Column(Boolean, default=False)
    qc_passed        = Column(Boolean, nullable=True)  # None=not checked

    # Scrap
    scrap_category = Column(String(20), nullable=True)
    scrap_reason   = Column(Text,       nullable=True)

    # Status
    status       = Column(String(20), default="PENDING", index=True)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    production_order = relationship("ProdExecOrder", back_populates="work_orders")


class ExecOrderMaterial(Base):
    """Material consumption tracking per production order."""
    __tablename__ = "exec_order_materials"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("exec_work_orders.id",       ondelete="SET NULL"), nullable=True)

    # Item
    item_type  = Column(String(20), default="MATERIAL")  # MATERIAL or PRODUCT
    item_id    = Column(UUID(as_uuid=True), nullable=True)
    item_name  = Column(String(200), nullable=True)
    item_code  = Column(String(80),  nullable=True)

    # Quantities
    required_qty  = Column(Numeric(14, 4), nullable=False)
    reserved_qty  = Column(Numeric(14, 4), default=0)
    issued_qty    = Column(Numeric(14, 4), default=0)
    consumed_qty  = Column(Numeric(14, 4), default=0)
    returned_qty  = Column(Numeric(14, 4), default=0)
    scrapped_qty  = Column(Numeric(14, 4), default=0)
    uom           = Column(String(20), nullable=False)

    # Status & costing
    status        = Column(String(20), default="RESERVED")
    lot_numbers   = Column(JSONB, nullable=True)   # list of lot numbers used
    unit_cost     = Column(Numeric(14, 4), nullable=True)
    extended_cost = Column(Numeric(16, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    production_order = relationship("ProdExecOrder", back_populates="materials")


class BatchGenealogy(Base):
    """Input lot → output batch traceability link per production order."""
    __tablename__ = "exec_batch_genealogy"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Input lot
    input_lot_no   = Column(String(100), nullable=True, index=True)
    input_item_name = Column(String(200), nullable=True)
    input_item_id  = Column(UUID(as_uuid=True), nullable=True)
    input_qty      = Column(Numeric(14, 4), nullable=True)
    input_uom      = Column(String(20), nullable=True)
    input_supplier = Column(String(200), nullable=True)

    # Output lot
    output_lot_no   = Column(String(100), nullable=True, index=True)
    output_item_name = Column(String(200), nullable=True)
    output_item_id  = Column(UUID(as_uuid=True), nullable=True)
    output_qty      = Column(Numeric(14, 4), nullable=True)
    output_uom      = Column(String(20), nullable=True)

    link_type  = Column(String(30), default="INPUT_OUTPUT")  # INPUT_OUTPUT, REWORK, SPLIT, MERGE
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    production_order = relationship("ProdExecOrder", back_populates="genealogy_links")


class ExecSplitMergeLog(Base):
    """Audit log of split and merge operations."""
    __tablename__ = "exec_split_merge_log"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_type  = Column(String(10), nullable=False)  # SPLIT or MERGE
    source_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    result_order_ids = Column(JSONB, nullable=False)  # list of UUIDs
    source_qty      = Column(Numeric(14, 4), nullable=False)
    result_qtys     = Column(JSONB, nullable=False)   # list of qty
    reason          = Column(Text, nullable=True)
    performed_by    = Column(UUID(as_uuid=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class ExecAIRec(Base):
    """AI recommendation for a production order."""
    __tablename__ = "exec_ai_recs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("exec_production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_type          = Column(String(30), nullable=False)
    status              = Column(String(20), default="PENDING")
    title               = Column(String(300), nullable=False)
    explanation         = Column(Text, nullable=True)
    impact_summary      = Column(Text, nullable=True)
    confidence_score    = Column(Numeric(4, 3), nullable=True)
    actioned_at         = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    production_order = relationship("ProdExecOrder", back_populates="ai_recs")
