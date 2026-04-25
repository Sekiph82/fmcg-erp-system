"""Accounting Dimensions / Cost Centers models."""
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class DimensionScope(str, enum.Enum):
    FINANCIAL   = "FINANCIAL"
    OPERATIONAL = "OPERATIONAL"
    BOTH        = "BOTH"


class CostCenterType(str, enum.Enum):
    PRODUCTION  = "PRODUCTION"
    WAREHOUSE   = "WAREHOUSE"
    ADMIN       = "ADMIN"
    SALES       = "SALES"
    UTILITIES   = "UTILITIES"
    MAINTENANCE = "MAINTENANCE"
    CORPORATE   = "CORPORATE"
    PROJECT     = "PROJECT"
    OTHER       = "OTHER"


class DimSourceType(str, enum.Enum):
    MANUAL           = "MANUAL"
    DEFAULT          = "DEFAULT"
    INHERITED        = "INHERITED"
    RULE_BASED       = "RULE_BASED"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"


class AllocationBasis(str, enum.Enum):
    FIXED_PCT      = "FIXED_PCT"
    HEADCOUNT      = "HEADCOUNT"
    FLOOR_AREA     = "FLOOR_AREA"
    MACHINE_HOURS  = "MACHINE_HOURS"
    LABOR_HOURS    = "LABOR_HOURS"
    REVENUE        = "REVENUE"
    QTY            = "QTY"
    MANUAL         = "MANUAL"
    CUSTOM_FORMULA = "CUSTOM_FORMULA"


class AllocationFrequency(str, enum.Enum):
    MONTHLY   = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    MANUAL    = "MANUAL"


class AllocationRunStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    PREVIEWED = "PREVIEWED"
    POSTED   = "POSTED"
    REVERSED = "REVERSED"


class ValidationSeverity(str, enum.Enum):
    WARN  = "WARN"
    BLOCK = "BLOCK"


class DimAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


class DimAIAgentType(str, enum.Enum):
    COMPLETENESS_MONITOR = "COMPLETENESS_MONITOR"
    ALLOCATION_OPTIMIZER = "ALLOCATION_OPTIMIZER"
    PROFITABILITY_LENS   = "PROFITABILITY_LENS"


# ── Dimension Type Master ──────────────────────────────────────────────────────

class DimType(Base, TimestampMixin):
    __tablename__ = "dim_types"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_code             = Column(String(50), unique=True, nullable=False)
    type_name             = Column(String(120), nullable=False)
    dimension_scope       = Column(Enum(DimensionScope), nullable=False, default=DimensionScope.BOTH)
    hierarchy_enabled     = Column(Boolean, default=True)
    is_mandatory          = Column(Boolean, default=False)
    active                = Column(Boolean, default=True)
    notes                 = Column(Text)

    values = relationship("DimValue", back_populates="dim_type", cascade="all, delete-orphan")
    validation_rules = relationship("DimValidationRule", back_populates="dim_type")


# ── Dimension Value Master ─────────────────────────────────────────────────────

class DimValue(Base, TimestampMixin):
    __tablename__ = "dim_values"
    __table_args__ = (UniqueConstraint("dim_type_id", "dim_code"),)

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    dim_code              = Column(String(50), nullable=False)
    dim_name              = Column(String(180), nullable=False)
    parent_id             = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=True)
    level_no              = Column(Integer, default=1)
    responsible_user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    active                = Column(Boolean, default=True)
    start_date            = Column(Date)
    end_date              = Column(Date)
    notes                 = Column(Text)

    dim_type  = relationship("DimType", back_populates="values")
    parent    = relationship("DimValue", remote_side="DimValue.id", foreign_keys=[parent_id])
    children  = relationship("DimValue", foreign_keys=[parent_id])


# ── Cost Center Master ─────────────────────────────────────────────────────────

class CostCenter(Base, TimestampMixin):
    __tablename__ = "cost_centers"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_center_code      = Column(String(50), unique=True, nullable=False)
    cost_center_name      = Column(String(180), nullable=False)
    parent_id             = Column(UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True)
    cost_center_type      = Column(Enum(CostCenterType), nullable=False, default=CostCenterType.ADMIN)
    plant_id              = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    manager_employee_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    department            = Column(String(100))
    active                = Column(Boolean, default=True)
    start_date            = Column(Date)
    end_date              = Column(Date)
    notes                 = Column(Text)

    parent   = relationship("CostCenter", remote_side="CostCenter.id", foreign_keys=[parent_id])
    children = relationship("CostCenter", foreign_keys=[parent_id])


# ── Transaction Dimension Link ─────────────────────────────────────────────────

class TransactionDimension(Base, TimestampMixin):
    __tablename__ = "transaction_dimensions"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_type      = Column(String(80), nullable=False)
    transaction_id        = Column(String(80), nullable=False)
    line_id               = Column(String(80))
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    dim_value_id          = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    source_type           = Column(Enum(DimSourceType), default=DimSourceType.MANUAL)
    locked                = Column(Boolean, default=False)
    notes                 = Column(Text)

    dim_type  = relationship("DimType")
    dim_value = relationship("DimValue")


# ── Dimension Validation Rule ──────────────────────────────────────────────────

class DimValidationRule(Base, TimestampMixin):
    __tablename__ = "dim_validation_rules"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name             = Column(String(180), nullable=False)
    transaction_type      = Column(String(80))
    gl_account_pattern    = Column(String(100))
    module                = Column(String(80))
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    severity              = Column(Enum(ValidationSeverity), default=ValidationSeverity.WARN)
    active                = Column(Boolean, default=True)
    effective_date        = Column(Date)
    notes                 = Column(Text)

    dim_type = relationship("DimType", back_populates="validation_rules")


# ── Allocation Rule Master ─────────────────────────────────────────────────────

class AllocationRule(Base, TimestampMixin):
    __tablename__ = "allocation_rules"

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code                   = Column(String(50), unique=True, nullable=False)
    rule_name                   = Column(String(180), nullable=False)
    source_dim_type_id          = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    source_dim_value_id         = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    target_dim_type_id          = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    allocation_basis            = Column(Enum(AllocationBasis), nullable=False, default=AllocationBasis.FIXED_PCT)
    frequency                   = Column(Enum(AllocationFrequency), default=AllocationFrequency.MONTHLY)
    gl_account_cost_pool        = Column(String(50))
    gl_account_allocation_dr    = Column(String(50))
    gl_account_allocation_cr    = Column(String(50))
    active                      = Column(Boolean, default=True)
    notes                       = Column(Text)

    source_dim_type  = relationship("DimType", foreign_keys=[source_dim_type_id])
    source_dim_value = relationship("DimValue", foreign_keys=[source_dim_value_id])
    target_dim_type  = relationship("DimType", foreign_keys=[target_dim_type_id])
    lines            = relationship("AllocationRuleLine", back_populates="rule", cascade="all, delete-orphan")
    runs             = relationship("AllocationRun", back_populates="rule")


# ── Allocation Rule Lines ──────────────────────────────────────────────────────

class AllocationRuleLine(Base, TimestampMixin):
    __tablename__ = "allocation_rule_lines"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id               = Column(UUID(as_uuid=True), ForeignKey("allocation_rules.id"), nullable=False)
    target_dim_value_id   = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    fixed_pct             = Column(Numeric(8, 4))
    weight_value          = Column(Numeric(18, 4))
    active                = Column(Boolean, default=True)
    notes                 = Column(Text)

    rule             = relationship("AllocationRule", back_populates="lines")
    target_dim_value = relationship("DimValue")


# ── Allocation Run ─────────────────────────────────────────────────────────────

class AllocationRun(Base, TimestampMixin):
    __tablename__ = "allocation_runs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id               = Column(UUID(as_uuid=True), ForeignKey("allocation_rules.id"), nullable=False)
    period_start          = Column(Date, nullable=False)
    period_end            = Column(Date, nullable=False)
    dry_run               = Column(Boolean, default=True)
    status                = Column(Enum(AllocationRunStatus), default=AllocationRunStatus.DRAFT)
    source_pool_amount    = Column(Numeric(18, 4), default=0)
    total_allocated       = Column(Numeric(18, 4), default=0)
    run_notes             = Column(Text)
    posted_by_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    rule      = relationship("AllocationRule", back_populates="runs")
    lines     = relationship("AllocationRunLine", back_populates="run", cascade="all, delete-orphan")


# ── Allocation Run Lines ───────────────────────────────────────────────────────

class AllocationRunLine(Base, TimestampMixin):
    __tablename__ = "allocation_run_lines"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id                = Column(UUID(as_uuid=True), ForeignKey("allocation_runs.id"), nullable=False)
    target_dim_value_id   = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    pct_applied           = Column(Numeric(8, 4))
    allocated_amount      = Column(Numeric(18, 4))
    journal_entry_id      = Column(String(80))

    run              = relationship("AllocationRun", back_populates="lines")
    target_dim_value = relationship("DimValue")


# ── Dimension Default Rule ─────────────────────────────────────────────────────

class DimDefaultRule(Base, TimestampMixin):
    __tablename__ = "dim_default_rules"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name             = Column(String(180), nullable=False)
    transaction_type      = Column(String(80), nullable=False)
    source_field          = Column(String(100))
    source_field_value    = Column(String(200))
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    dim_value_id          = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    priority              = Column(Integer, default=10)
    active                = Column(Boolean, default=True)

    dim_type  = relationship("DimType")
    dim_value = relationship("DimValue")


# ── Reclassification Record ────────────────────────────────────────────────────

class DimReclassification(Base, TimestampMixin):
    __tablename__ = "dim_reclassifications"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_type      = Column(String(80), nullable=False)
    transaction_id        = Column(String(80), nullable=False)
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=False)
    old_dim_value_id      = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=True)
    new_dim_value_id      = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=False)
    reason                = Column(Text, nullable=False)
    journal_entry_ref     = Column(String(80))
    reclassified_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    dim_type      = relationship("DimType")
    old_dim_value = relationship("DimValue", foreign_keys=[old_dim_value_id])
    new_dim_value = relationship("DimValue", foreign_keys=[new_dim_value_id])


# ── AI Recommendations ────────────────────────────────────────────────────────

class DimAIRecommendation(Base, TimestampMixin):
    __tablename__ = "dim_ai_recommendations"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type            = Column(Enum(DimAIAgentType), nullable=False)
    title                 = Column(String(300), nullable=False)
    detail                = Column(Text)
    severity              = Column(String(20), default="info")
    status                = Column(Enum(DimAIRecStatus), default=DimAIRecStatus.PENDING)
    dim_type_id           = Column(UUID(as_uuid=True), ForeignKey("dim_types.id"), nullable=True)
    dim_value_id          = Column(UUID(as_uuid=True), ForeignKey("dim_values.id"), nullable=True)
    allocation_rule_id    = Column(UUID(as_uuid=True), ForeignKey("allocation_rules.id"), nullable=True)
