import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class QCType(str, enum.Enum):
    INCOMING = "INCOMING"
    IN_PROCESS = "IN_PROCESS"
    FINISHED_GOODS = "FINISHED_GOODS"


class QCStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CONDITIONAL_RELEASE = "CONDITIONAL_RELEASE"
    CANCELLED = "CANCELLED"


class QCDecision(str, enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONDITIONAL_RELEASE = "CONDITIONAL_RELEASE"
    REWORK = "REWORK"


class ParameterType(str, enum.Enum):
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    PASS_FAIL = "PASS_FAIL"


class QCParameter(Base, TimestampMixin):
    """Reusable test parameter template (pH, viscosity, temperature, etc.)."""
    __tablename__ = "qc_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parameter_type = Column(Enum(ParameterType), nullable=False, default=ParameterType.NUMERIC)
    unit = Column(String(30), nullable=True)
    min_value = Column(Numeric(14, 4), nullable=True)
    max_value = Column(Numeric(14, 4), nullable=True)
    expected_value = Column(String(200), nullable=True)   # free-text for text/bool params
    is_critical = Column(Boolean, default=False, nullable=False)
    applicable_types = Column(String(100), nullable=False, default="ALL")  # "ALL" or "INCOMING,IN_PROCESS"
    is_active = Column(Boolean, default=True, nullable=False)


class QCInspection(Base, TimestampMixin):
    """Single QC inspection event (incoming, in-process, or finished goods)."""
    __tablename__ = "qc_inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_no = Column(String(50), unique=True, nullable=False, index=True)
    qc_type = Column(Enum(QCType), nullable=False)
    status = Column(Enum(QCStatus), nullable=False, default=QCStatus.PENDING)

    # Linked entities (one or more may be set depending on type)
    grn_id = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True)
    grn_line_id = Column(UUID(as_uuid=True), ForeignKey("grn_lines.id", ondelete="SET NULL"), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)

    # Item identification (denormalized for easy querying)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    lot_number = Column(String(100), nullable=True)
    batch_no = Column(String(100), nullable=True)
    sample_size = Column(Numeric(10, 3), nullable=True)
    sample_unit = Column(String(20), nullable=True)

    inspection_date = Column(Date, nullable=False)
    inspector_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    # Decision
    decision = Column(Enum(QCDecision), nullable=True)
    decided_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_notes = Column(Text, nullable=True)
    rework_candidate = Column(Boolean, default=False, nullable=False)
    quarantine_applied = Column(Boolean, default=False, nullable=False)

    # Relationships
    inspector = relationship("User", foreign_keys=[inspector_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    supplier = relationship("Supplier")
    material = relationship("Material")
    product = relationship("Product")
    lot = relationship("Lot")
    production_order = relationship("ProductionOrder")
    test_results = relationship("QCTestResult", back_populates="inspection",
                                cascade="all, delete-orphan", order_by="QCTestResult.created_at")


class QCTestResult(Base, TimestampMixin):
    """Individual test result within an inspection."""
    __tablename__ = "qc_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("qc_parameters.id", ondelete="SET NULL"), nullable=True)

    # Denormalized snapshot of parameter at test time
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(Enum(ParameterType), nullable=False)
    unit = Column(String(30), nullable=True)

    # Result values (one used depending on type)
    numeric_value = Column(Numeric(14, 4), nullable=True)
    text_value = Column(Text, nullable=True)
    boolean_value = Column(Boolean, nullable=True)

    # Spec limits at time of test
    min_spec = Column(Numeric(14, 4), nullable=True)
    max_spec = Column(Numeric(14, 4), nullable=True)
    expected_text = Column(String(200), nullable=True)

    is_passed = Column(Boolean, nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    tested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    inspection = relationship("QCInspection", back_populates="test_results")
    parameter = relationship("QCParameter")
    tested_by = relationship("User")
