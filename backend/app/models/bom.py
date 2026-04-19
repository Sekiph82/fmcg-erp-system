"""
Advanced Multi-Level BOM / Formula / Packaging BOM — Data Models
──────────────────────────────────────────────────────────────────
Enterprise FMCG BOM engine: single-level, multi-level, formula,
intermediate, packaging, phantom, co-product/by-product, rework.

Models:
  1. AdvancedBOM            — BOM header with full lifecycle control
  2. AdvancedBOMLine        — BOM lines with FMCG-specific fields
  3. BOMSubstituteGroup     — approved substitute groups
  4. BOMSubstitute          — ranked substitute materials
  5. BOMConversionProfile   — bulk-to-pack conversion logic
  6. BOMYieldConfig         — yield/loss category configuration
  7. BOMAIRec               — AI agent recommendations
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer, Float,
    ForeignKey, Enum as SAEnum, DateTime, Date, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class BOMType(str, enum.Enum):
    FORMULA      = "FORMULA"       # raw materials → bulk/intermediate
    INTERMEDIATE = "INTERMEDIATE"  # intermediate → next stage
    PACKAGING    = "PACKAGING"     # bulk → packaged SKU
    MULTILEVEL   = "MULTILEVEL"    # full recursive tree
    PHANTOM      = "PHANTOM"       # logical grouping, not separately stocked
    REWORK       = "REWORK"        # rework / recovery process
    COPRODUCT    = "COPRODUCT"     # one process → multiple outputs

class BOMLifecycle(str, enum.Enum):
    DRAFT        = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    RELEASED     = "RELEASED"
    SUPERSEDED   = "SUPERSEDED"
    ARCHIVED     = "ARCHIVED"

class ComponentType(str, enum.Enum):
    RAW            = "RAW"
    INTERMEDIATE   = "INTERMEDIATE"
    PACKAGING      = "PACKAGING"
    SERVICE        = "SERVICE"
    CO_PRODUCT     = "CO_PRODUCT"
    BY_PRODUCT     = "BY_PRODUCT"
    UTILITY        = "UTILITY"
    REWORK         = "REWORK"

class BasisType(str, enum.Enum):
    PER_BATCH   = "PER_BATCH"
    PER_UNIT    = "PER_UNIT"
    PER_100KG   = "PER_100KG"
    PER_1000L   = "PER_1000L"
    PERCENTAGE  = "PERCENTAGE"
    FIXED       = "FIXED"

class SubstitutionPolicy(str, enum.Enum):
    NO_SUB           = "NO_SUB"
    PLANNER_APPROVAL = "PLANNER_APPROVAL"
    QA_APPROVAL      = "QA_APPROVAL"
    BOTH_REQUIRED    = "BOTH_REQUIRED"
    SHORTAGE_ONLY    = "SHORTAGE_ONLY"
    EMERGENCY_ONLY   = "EMERGENCY_ONLY"

class ItemLinkType(str, enum.Enum):
    PRODUCT  = "PRODUCT"
    MATERIAL = "MATERIAL"

class LossCategory(str, enum.Enum):
    PROCESS_LOSS    = "PROCESS_LOSS"
    EVAPORATION     = "EVAPORATION"
    TRANSFER        = "TRANSFER"
    STARTUP         = "STARTUP"
    SHUTDOWN        = "SHUTDOWN"
    FILLING         = "FILLING"
    PACKAGING_REJECT= "PACKAGING_REJECT"
    QC_REJECTION    = "QC_REJECTION"
    LINE_PURGE      = "LINE_PURGE"

class BOMAgentType(str, enum.Enum):
    FORMULA_ANALYZER    = "FORMULA_ANALYZER"
    PACKAGING_OPTIMIZER = "PACKAGING_OPTIMIZER"
    COMPLIANCE_CHECKER  = "COMPLIANCE_CHECKER"

class BOMRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ── 1. AdvancedBOM (Header) ────────────────────────────────────────────────────

class AdvancedBOM(Base, TimestampMixin):
    __tablename__ = "advanced_boms"
    __table_args__ = (
        UniqueConstraint("bom_code", name="uq_advanced_bom_code"),
    )

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_code      = Column(String(80), nullable=False, unique=True, index=True)
    bom_name      = Column(String(255), nullable=False)
    bom_type      = Column(SAEnum(BOMType), nullable=False, default=BOMType.FORMULA, index=True)

    # product linkage
    product_id    = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True)
    product_name  = Column(String(255), nullable=True)  # cached

    # base qty — what qty this BOM is defined for
    base_qty      = Column(Numeric(14, 4), nullable=False, default=1000)
    base_uom      = Column(String(20), nullable=False, default="KG")

    # version control
    version_no    = Column(String(20), nullable=False, default="1.0")
    revision_no   = Column(String(20), nullable=False, default="0")
    is_default    = Column(Boolean, nullable=False, default=False)
    lifecycle     = Column(SAEnum(BOMLifecycle), nullable=False, default=BOMLifecycle.DRAFT, index=True)

    # effectivity
    effective_from = Column(Date, nullable=True)
    effective_to   = Column(Date, nullable=True)

    # users
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # linked artifacts
    linked_routing_id         = Column(UUID(as_uuid=True), nullable=True)
    linked_quality_spec_id    = Column(UUID(as_uuid=True), nullable=True)
    linked_label_profile_id   = Column(UUID(as_uuid=True), nullable=True)
    linked_compliance_profile_id = Column(UUID(as_uuid=True), nullable=True)

    # KPIs computed on demand
    standard_batch_cost    = Column(Numeric(16, 4), nullable=True)
    standard_cost_per_uom  = Column(Numeric(16, 4), nullable=True)
    total_raw_cost         = Column(Numeric(16, 4), nullable=True)
    total_packaging_cost   = Column(Numeric(16, 4), nullable=True)
    by_product_credit      = Column(Numeric(16, 4), nullable=True)
    costing_updated_at     = Column(DateTime(timezone=True), nullable=True)

    # allergen flags (computed roll-up)
    allergen_flags         = Column(JSON, nullable=True)   # {"dairy": true, "gluten": false, ...}
    nutrition_per_100g     = Column(JSON, nullable=True)   # {"calories": 250, "protein": 12, ...}

    notes                  = Column(Text, nullable=True)

    # relationships
    product       = relationship("Product", foreign_keys=[product_id])
    created_by    = relationship("User", foreign_keys=[created_by_id])
    reviewed_by   = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by   = relationship("User", foreign_keys=[approved_by_id])
    released_by   = relationship("User", foreign_keys=[released_by_id])
    lines         = relationship(
        "AdvancedBOMLine",
        back_populates="bom",
        cascade="all, delete-orphan",
        foreign_keys="AdvancedBOMLine.bom_id",
        order_by="AdvancedBOMLine.line_no",
    )
    yield_configs = relationship("BOMYieldConfig", back_populates="bom", cascade="all, delete-orphan")
    ai_recs       = relationship("BOMAIRec", back_populates="bom", cascade="all, delete-orphan")


# ── 2. AdvancedBOMLine ─────────────────────────────────────────────────────────

class AdvancedBOMLine(Base, TimestampMixin):
    __tablename__ = "advanced_bom_lines"
    __table_args__ = (
        UniqueConstraint("bom_id", "line_no", name="uq_adv_bom_line_no"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id         = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no        = Column(Integer, nullable=False)

    # component
    component_type = Column(SAEnum(ComponentType), nullable=False, default=ComponentType.RAW)
    item_type      = Column(SAEnum(ItemLinkType), nullable=False, default=ItemLinkType.MATERIAL)
    item_id        = Column(UUID(as_uuid=True), nullable=True)      # FK to product or material
    item_name      = Column(String(255), nullable=True)             # cached
    item_code      = Column(String(100), nullable=True)             # cached

    # child BOM link (for multi-level / phantom)
    child_bom_id   = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="SET NULL"), nullable=True)

    # quantities
    required_qty   = Column(Numeric(14, 4), nullable=False, default=0)
    required_uom   = Column(String(20), nullable=False, default="KG")
    basis_type     = Column(SAEnum(BasisType), nullable=False, default=BasisType.PER_BATCH)
    concentration_pct = Column(Numeric(6, 3), nullable=True)        # active ingredient %

    # yield & loss
    wastage_pct      = Column(Numeric(6, 3), nullable=False, default=0)
    process_loss_pct = Column(Numeric(6, 3), nullable=False, default=0)
    yield_contribution_pct = Column(Numeric(6, 3), nullable=True)   # this line's share of total yield

    # flags
    fixed_consumption  = Column(Boolean, nullable=False, default=False)
    is_optional        = Column(Boolean, nullable=False, default=False)
    qc_required        = Column(Boolean, nullable=False, default=False)
    allergen_flag      = Column(Boolean, nullable=False, default=False)
    nutrition_relevant = Column(Boolean, nullable=False, default=False)
    critical_component = Column(Boolean, nullable=False, default=False)

    # substitution
    substitute_group_id = Column(UUID(as_uuid=True), ForeignKey("bom_substitute_groups.id", ondelete="SET NULL"), nullable=True)
    substitution_policy = Column(SAEnum(SubstitutionPolicy), nullable=False, default=SubstitutionPolicy.NO_SUB)

    # staging
    consumption_stage  = Column(String(100), nullable=True)   # e.g. "Initial Mix", "Final Addition"
    issue_stage        = Column(String(100), nullable=True)

    # allergen attributes (on this line item)
    allergen_types     = Column(JSON, nullable=True)           # ["dairy", "gluten"]
    traceability_level = Column(String(50), nullable=True)     # FULL / BATCH / LOT

    # nutritional data per 100g of this component
    nutrition_data     = Column(JSON, nullable=True)

    # cost (cached per line)
    unit_cost          = Column(Numeric(14, 4), nullable=True)
    extended_cost      = Column(Numeric(16, 4), nullable=True)

    notes              = Column(Text, nullable=True)

    # relationships
    bom              = relationship("AdvancedBOM", back_populates="lines", foreign_keys="AdvancedBOMLine.bom_id")
    child_bom        = relationship("AdvancedBOM", foreign_keys="AdvancedBOMLine.child_bom_id")
    substitute_group = relationship("BOMSubstituteGroup", back_populates="bom_lines")


# ── 3. BOMSubstituteGroup ─────────────────────────────────────────────────────

class BOMSubstituteGroup(Base, TimestampMixin):
    __tablename__ = "bom_substitute_groups"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_code  = Column(String(50), nullable=False, unique=True, index=True)
    group_name  = Column(String(255), nullable=False)
    policy      = Column(SAEnum(SubstitutionPolicy), nullable=False, default=SubstitutionPolicy.PLANNER_APPROVAL)
    notes       = Column(Text, nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)

    bom_lines   = relationship("AdvancedBOMLine", back_populates="substitute_group")
    substitutes = relationship("BOMSubstitute", back_populates="group", cascade="all, delete-orphan",
                               order_by="BOMSubstitute.priority")


# ── 4. BOMSubstitute ──────────────────────────────────────────────────────────

class BOMSubstitute(Base, TimestampMixin):
    __tablename__ = "bom_substitutes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id        = Column(UUID(as_uuid=True), ForeignKey("bom_substitute_groups.id", ondelete="CASCADE"), nullable=False)
    item_type       = Column(SAEnum(ItemLinkType), nullable=False, default=ItemLinkType.MATERIAL)
    item_id         = Column(UUID(as_uuid=True), nullable=True)
    item_name       = Column(String(255), nullable=True)
    item_code       = Column(String(100), nullable=True)
    priority        = Column(Integer, nullable=False, default=1)
    qty_ratio       = Column(Numeric(8, 4), nullable=False, default=1.0)   # substitution ratio vs primary
    cost_impact_pct = Column(Numeric(6, 2), nullable=True)
    quality_impact  = Column(String(50), nullable=True)   # NONE / MINOR / MAJOR
    allergen_impact = Column(String(255), nullable=True)
    compliance_impact = Column(String(255), nullable=True)
    notes           = Column(Text, nullable=True)
    is_active       = Column(Boolean, nullable=False, default=True)

    group = relationship("BOMSubstituteGroup", back_populates="substitutes")


# ── 5. BOMConversionProfile ───────────────────────────────────────────────────

class BOMConversionProfile(Base, TimestampMixin):
    __tablename__ = "bom_conversion_profiles"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_code         = Column(String(80), nullable=False, unique=True, index=True)
    profile_name         = Column(String(255), nullable=False)

    # source / target
    source_product_id    = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    source_product_name  = Column(String(255), nullable=True)
    target_product_id    = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    target_product_name  = Column(String(255), nullable=True)

    # conversion params
    theoretical_conversion_ratio = Column(Numeric(10, 6), nullable=False, default=1.0)
    standard_fill_volume  = Column(Numeric(14, 4), nullable=True)    # per unit (ml, g, etc.)
    fill_volume_uom       = Column(String(20), nullable=True)
    fill_tolerance_pct    = Column(Numeric(5, 3), nullable=False, default=1.0)
    density_g_per_ml      = Column(Numeric(8, 4), nullable=True)     # for volume↔weight

    # loss parameters
    startup_loss_pct      = Column(Numeric(6, 3), nullable=False, default=0.5)
    shutdown_loss_pct     = Column(Numeric(6, 3), nullable=False, default=0.3)
    packaging_reject_pct  = Column(Numeric(6, 3), nullable=False, default=0.5)
    residual_bulk_pct     = Column(Numeric(6, 3), nullable=False, default=0.2)
    line_purge_loss_pct   = Column(Numeric(6, 3), nullable=False, default=0.1)

    # expected yields
    standard_expected_units   = Column(Numeric(14, 0), nullable=True)
    realistic_expected_units  = Column(Numeric(14, 0), nullable=True)

    linked_packaging_bom_id = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="SET NULL"), nullable=True)
    is_active               = Column(Boolean, nullable=False, default=True)
    notes                   = Column(Text, nullable=True)

    source_product  = relationship("Product", foreign_keys=[source_product_id])
    target_product  = relationship("Product", foreign_keys=[target_product_id])
    packaging_bom   = relationship("AdvancedBOM", foreign_keys=[linked_packaging_bom_id])


# ── 6. BOMYieldConfig ─────────────────────────────────────────────────────────

class BOMYieldConfig(Base, TimestampMixin):
    __tablename__ = "bom_yield_configs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id          = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="CASCADE"), nullable=False)
    loss_category   = Column(SAEnum(LossCategory), nullable=False)
    description     = Column(String(255), nullable=True)
    basis           = Column(String(50), nullable=False, default="PCT_OF_INPUT")
    standard_pct    = Column(Numeric(6, 3), nullable=False, default=0)
    max_allowable_pct = Column(Numeric(6, 3), nullable=True)
    cost_impact_flag = Column(Boolean, nullable=False, default=True)
    notes           = Column(Text, nullable=True)

    bom = relationship("AdvancedBOM", back_populates="yield_configs")


# ── 7. BOMAIRec ───────────────────────────────────────────────────────────────

class BOMAIRec(Base, TimestampMixin):
    __tablename__ = "bom_ai_recs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id         = Column(UUID(as_uuid=True), ForeignKey("advanced_boms.id", ondelete="CASCADE"), nullable=False)
    agent_type     = Column(SAEnum(BOMAgentType), nullable=False)
    status         = Column(SAEnum(BOMRecStatus), nullable=False, default=BOMRecStatus.PENDING)
    title          = Column(String(255), nullable=False)
    explanation    = Column(Text, nullable=True)
    impact_summary = Column(Text, nullable=True)
    confidence_score = Column(Numeric(4, 2), nullable=True)
    payload        = Column(JSON, nullable=True)
    actioned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actioned_at    = Column(DateTime(timezone=True), nullable=True)

    bom         = relationship("AdvancedBOM", back_populates="ai_recs")
    actioned_by = relationship("User", foreign_keys=[actioned_by_id])
