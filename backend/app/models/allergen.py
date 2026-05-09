"""Allergen + Nutrition Management System — data models."""
import uuid
import enum
from datetime import date, datetime

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class AllergenCategory(str, enum.Enum):
    MAJOR   = "MAJOR"    # EU/FDA top 14 / Big 9
    MINOR   = "MINOR"
    CUSTOM  = "CUSTOM"


class PresenceType(str, enum.Enum):
    CONTAINS                   = "CONTAINS"
    MAY_CONTAIN                = "MAY_CONTAIN"
    PRODUCED_IN_SAME_FACILITY  = "PRODUCED_IN_SAME_FACILITY"
    FREE_FROM                  = "FREE_FROM"
    UNKNOWN                    = "UNKNOWN"


class CrossContactRisk(str, enum.Enum):
    NONE     = "NONE"
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class NutrientBasis(str, enum.Enum):
    PER_100G   = "PER_100G"
    PER_100ML  = "PER_100ML"
    PER_SERVING = "PER_SERVING"
    PER_UNIT   = "PER_UNIT"


class NutrientSource(str, enum.Enum):
    SUPPLIER   = "SUPPLIER"
    LAB        = "LAB"
    MANUAL     = "MANUAL"
    CALCULATED = "CALCULATED"


class LabelBasisType(str, enum.Enum):
    PER_100G     = "PER_100G"
    PER_100ML    = "PER_100ML"
    PER_SERVING  = "PER_SERVING"
    BOTH         = "BOTH"


class AllergenChangeType(str, enum.Enum):
    ADDED                = "ADDED"
    REMOVED              = "REMOVED"
    SEVERITY_CHANGED     = "SEVERITY_CHANGED"
    DECLARATION_CHANGED  = "DECLARATION_CHANGED"
    MAY_CONTAIN_CHANGED  = "MAY_CONTAIN_CHANGED"


class ANAIAgentType(str, enum.Enum):
    ALLERGEN_RISK_MONITOR       = "ALLERGEN_RISK_MONITOR"
    NUTRITION_CHANGE_ANALYZER   = "NUTRITION_CHANGE_ANALYZER"
    LABEL_COMPLIANCE_ASSISTANT  = "LABEL_COMPLIANCE_ASSISTANT"


class ANAIRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    APPLIED  = "APPLIED"


# ── Allergen Master ───────────────────────────────────────────────────────────

class AllergenMaster(Base, TimestampMixin):
    __tablename__ = "allergen_masters"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allergen_code    = Column(String(50), nullable=False, unique=True, index=True)
    allergen_name    = Column(String(200), nullable=False)
    regulatory_name  = Column(String(300), nullable=True)
    category         = Column(Enum(AllergenCategory), nullable=False, default=AllergenCategory.MAJOR)
    is_active        = Column(Boolean, default=True, nullable=False)
    sort_order       = Column(Integer, default=0, nullable=False)
    notes            = Column(Text, nullable=True)

    profile_lines    = relationship("MaterialAllergenLine", back_populates="allergen")
    change_logs      = relationship("AllergenChangeLog", back_populates="allergen")


# ── Material Allergen Profile ─────────────────────────────────────────────────

class MaterialAllergenProfile(Base, TimestampMixin):
    __tablename__ = "material_allergen_profiles"
    __table_args__ = (UniqueConstraint("material_id", name="uq_mat_allergen_profile"),)

    id                           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id                  = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_present_flag        = Column(Boolean, default=False, nullable=False)
    allergen_may_contain_flag    = Column(Boolean, default=False, nullable=False)
    cross_contact_risk_level     = Column(Enum(CrossContactRisk), default=CrossContactRisk.NONE, nullable=False)
    supplier_allergen_statement_ref = Column(String(500), nullable=True)
    allergen_review_date         = Column(Date, nullable=True)
    approved_by                  = Column(String(200), nullable=True)
    is_active                    = Column(Boolean, default=True, nullable=False)
    notes                        = Column(Text, nullable=True)

    material = relationship("Material")
    lines    = relationship("MaterialAllergenLine", back_populates="profile", cascade="all, delete-orphan")


class MaterialAllergenLine(Base, TimestampMixin):
    __tablename__ = "material_allergen_lines"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id            = Column(UUID(as_uuid=True), ForeignKey("material_allergen_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_id           = Column(UUID(as_uuid=True), ForeignKey("allergen_masters.id", ondelete="RESTRICT"), nullable=False, index=True)
    presence_type         = Column(Enum(PresenceType), nullable=False, default=PresenceType.CONTAINS)
    concentration_note    = Column(String(500), nullable=True)
    declaration_required  = Column(Boolean, default=True, nullable=False)
    critical_flag         = Column(Boolean, default=False, nullable=False)
    notes                 = Column(Text, nullable=True)

    profile  = relationship("MaterialAllergenProfile", back_populates="lines")
    allergen = relationship("AllergenMaster", back_populates="profile_lines")


# ── Nutrition Profile ─────────────────────────────────────────────────────────

class NutritionProfile(Base, TimestampMixin):
    __tablename__ = "nutrition_profiles"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id    = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id     = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    basis_type     = Column(Enum(NutrientBasis), nullable=False, default=NutrientBasis.PER_100G)
    density_factor = Column(Numeric(8, 4), nullable=True)
    moisture_factor = Column(Numeric(8, 4), nullable=True)
    is_active      = Column(Boolean, default=True, nullable=False)
    notes          = Column(Text, nullable=True)

    material = relationship("Material")
    product  = relationship("Product")
    lines    = relationship("NutritionProfileLine", back_populates="profile", cascade="all, delete-orphan")


class NutritionProfileLine(Base, TimestampMixin):
    __tablename__ = "nutrition_profile_lines"
    __table_args__ = (UniqueConstraint("profile_id", "nutrient_code", name="uq_nutrition_line"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id     = Column(UUID(as_uuid=True), ForeignKey("nutrition_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    nutrient_code  = Column(String(50), nullable=False)
    nutrient_name  = Column(String(100), nullable=False)
    unit           = Column(String(20), nullable=False, default="g")
    value          = Column(Numeric(14, 6), nullable=False, default=0)
    source_type    = Column(Enum(NutrientSource), nullable=False, default=NutrientSource.MANUAL)
    approved_flag  = Column(Boolean, default=False, nullable=False)
    review_date    = Column(Date, nullable=True)
    notes          = Column(Text, nullable=True)

    profile = relationship("NutritionProfile", back_populates="lines")


# ── Product Allergen Summary (computed) ───────────────────────────────────────

class ProductAllergenSummary(Base, TimestampMixin):
    __tablename__ = "product_allergen_summaries"
    __table_args__ = (UniqueConstraint("product_id", name="uq_prod_allergen_summary"),)

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id              = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    bom_id                  = Column(UUID(as_uuid=True), nullable=True)
    bom_version             = Column(String(20), nullable=True)
    contains_allergens      = Column(JSON, nullable=True)    # list of allergen codes
    may_contain_allergens   = Column(JSON, nullable=True)
    declaration_required    = Column(JSON, nullable=True)    # list of {code, name}
    cross_contact_risk      = Column(Enum(CrossContactRisk), default=CrossContactRisk.NONE)
    label_statement         = Column(Text, nullable=True)
    may_contain_statement   = Column(Text, nullable=True)
    last_calculated_at      = Column(DateTime, nullable=True)
    calculation_source      = Column(String(50), nullable=True)  # "BOM" / "RECIPE" / "MANUAL"
    is_stale                = Column(Boolean, default=False, nullable=False)

    product = relationship("Product")


# ── Product Nutrition Summary (computed) ──────────────────────────────────────

class ProductNutritionSummary(Base, TimestampMixin):
    __tablename__ = "product_nutrition_summaries"
    __table_args__ = (UniqueConstraint("product_id", name="uq_prod_nutrition_summary"),)

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id            = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    bom_id                = Column(UUID(as_uuid=True), nullable=True)
    bom_version           = Column(String(20), nullable=True)
    serving_size_value    = Column(Numeric(10, 3), nullable=True)
    serving_size_uom      = Column(String(20), nullable=True, default="g")
    servings_per_pack     = Column(Numeric(8, 2), nullable=True)
    label_basis_type      = Column(Enum(LabelBasisType), default=LabelBasisType.PER_100G, nullable=False)
    nutrition_per_100g    = Column(JSON, nullable=True)    # {nutrient_code: value}
    nutrition_per_100ml   = Column(JSON, nullable=True)
    nutrition_per_serving = Column(JSON, nullable=True)
    nutrition_per_unit    = Column(JSON, nullable=True)
    last_calculated_at    = Column(DateTime, nullable=True)
    calculation_source    = Column(String(50), nullable=True)
    is_stale              = Column(Boolean, default=False, nullable=False)

    product = relationship("Product")


# ── Allergen Change Log ───────────────────────────────────────────────────────

class AllergenChangeLog(Base, TimestampMixin):
    __tablename__ = "allergen_change_logs"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id              = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    bom_id                  = Column(UUID(as_uuid=True), nullable=True)
    bom_version_from        = Column(String(20), nullable=True)
    bom_version_to          = Column(String(20), nullable=True)
    allergen_id             = Column(UUID(as_uuid=True), ForeignKey("allergen_masters.id", ondelete="SET NULL"), nullable=True)
    change_type             = Column(Enum(AllergenChangeType), nullable=False)
    old_value               = Column(String(200), nullable=True)
    new_value               = Column(String(200), nullable=True)
    detected_at             = Column(DateTime, nullable=True)
    requires_label_review   = Column(Boolean, default=True, nullable=False)
    requires_qc_review      = Column(Boolean, default=True, nullable=False)
    requires_haccp_review   = Column(Boolean, default=False, nullable=False)
    requires_cleaning_validation = Column(Boolean, default=False, nullable=False)
    label_review_done       = Column(Boolean, default=False, nullable=False)
    qc_review_done          = Column(Boolean, default=False, nullable=False)
    notes                   = Column(Text, nullable=True)

    product  = relationship("Product")
    allergen = relationship("AllergenMaster", back_populates="change_logs")


# ── Serving Size / Declaration Config ─────────────────────────────────────────

class ProductServingConfig(Base, TimestampMixin):
    __tablename__ = "product_serving_configs"
    __table_args__ = (UniqueConstraint("product_id", name="uq_prod_serving_config"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    serving_size_value  = Column(Numeric(10, 3), nullable=True)
    serving_size_uom    = Column(String(20), nullable=True, default="g")
    servings_per_pack   = Column(Numeric(8, 2), nullable=True)
    label_basis_type    = Column(Enum(LabelBasisType), default=LabelBasisType.PER_100G, nullable=False)
    market_profile      = Column(String(100), nullable=True)
    rounding_profile    = Column(String(100), nullable=True)
    notes               = Column(Text, nullable=True)

    product = relationship("Product")


# ── AI Recommendations ────────────────────────────────────────────────────────

class ANAIRecommendation(Base, TimestampMixin):
    __tablename__ = "an_ai_recommendations"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type           = Column(Enum(ANAIAgentType), nullable=False)
    title                = Column(String(500), nullable=False)
    description          = Column(Text, nullable=False)
    affected_entity_type = Column(String(100), nullable=True)
    affected_entity_id   = Column(String(100), nullable=True)
    recommendation       = Column(Text, nullable=False)
    severity             = Column(String(20), default="MEDIUM", nullable=False)
    status               = Column(Enum(ANAIRecStatus), default=ANAIRecStatus.PENDING, nullable=False)
    reviewed_by          = Column(String(200), nullable=True)
    reviewed_at          = Column(DateTime, nullable=True)
    agent_metadata       = Column(JSON, nullable=True)


# ── Cleaning Validation ───────────────────────────────────────────────────────

class CleaningValidationResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    PENDING = "PENDING"


class CleaningValidationLog(Base, TimestampMixin):
    """
    Records cleaning/sanitation validation between production runs to confirm
    allergen removal before switching to different allergen profile product.
    """
    __tablename__ = "allergen_cleaning_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_ref = Column(String(50), unique=True, nullable=False, index=True)
    line_id = Column(String(100), nullable=True, index=True)        # production line / equipment ID
    line_name = Column(String(200), nullable=True)
    previous_product = Column(String(300), nullable=True)           # product run before cleaning
    previous_allergens = Column(JSON, nullable=True)                # list of allergen names
    next_product = Column(String(300), nullable=True)               # product run after cleaning
    cleaning_method = Column(String(200), nullable=True)            # CIP | dry clean | wet clean | swab
    cleaning_agent = Column(String(200), nullable=True)
    cleaned_by = Column(String(200), nullable=True)
    cleaned_at = Column(DateTime, nullable=True)
    validated_by = Column(String(200), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    swab_test_result = Column(String(100), nullable=True)           # ATP reading or allergen swab result
    swab_threshold = Column(String(100), nullable=True)             # acceptable limit
    result = Column(Enum(CleaningValidationResult), nullable=False, default=CleaningValidationResult.PENDING)
    corrective_action = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
