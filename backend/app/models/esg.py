import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class SourceType(str, enum.Enum):
    FUEL_DIESEL = "FUEL_DIESEL"
    FUEL_PETROL = "FUEL_PETROL"
    FUEL_LPG = "FUEL_LPG"
    ELECTRICITY_GRID = "ELECTRICITY_GRID"
    ELECTRICITY_SOLAR = "ELECTRICITY_SOLAR"
    TRANSPORT_ROAD = "TRANSPORT_ROAD"
    TRANSPORT_AIR = "TRANSPORT_AIR"
    MATERIAL = "MATERIAL"
    WATER = "WATER"
    WASTE_GENERAL = "WASTE_GENERAL"
    WASTE_HAZARDOUS = "WASTE_HAZARDOUS"
    WASTE_RECYCLED = "WASTE_RECYCLED"


class EmissionScope(str, enum.Enum):
    SCOPE1 = "SCOPE1"
    SCOPE2 = "SCOPE2"
    SCOPE3 = "SCOPE3"


class ESGMetricType(str, enum.Enum):
    ENERGY = "ENERGY"
    WATER = "WATER"
    WASTE = "WASTE"
    RECYCLING = "RECYCLING"
    EMISSIONS = "EMISSIONS"


class SupplierSustainabilityRisk(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupplierSustainabilityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ARCHIVED = "ARCHIVED"


class ActivityData(Base, TimestampMixin):
    __tablename__ = "esg_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(Enum(SourceType), nullable=False, index=True)
    source_reference = Column(String(200), nullable=True)
    activity_date = Column(Date, nullable=False, index=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_auto_imported = Column(Boolean, default=False, nullable=False)

    location = relationship("Warehouse")
    supplier = relationship("Supplier")
    creator = relationship("User", foreign_keys=[created_by])
    emission_records = relationship("EmissionRecord", back_populates="activity", cascade="all, delete-orphan")


class EmissionFactor(Base, TimestampMixin):
    __tablename__ = "esg_emission_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factor_code = Column(String(50), unique=True, nullable=False, index=True)
    source_type = Column(Enum(SourceType), nullable=False, index=True)
    region = Column(String(10), nullable=False, default="KE")
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    factor_value = Column(Numeric(18, 8), nullable=False)
    unit = Column(String(50), nullable=False)
    scope = Column(Enum(EmissionScope), nullable=False)
    source_reference = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    emission_records = relationship("EmissionRecord", back_populates="factor")


class EmissionRecord(Base, TimestampMixin):
    __tablename__ = "esg_emission_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("esg_activities.id", ondelete="CASCADE"), nullable=False, index=True)
    factor_id = Column(UUID(as_uuid=True), ForeignKey("esg_emission_factors.id", ondelete="RESTRICT"), nullable=False)
    calculated_emission_kgco2e = Column(Numeric(18, 4), nullable=False)
    scope = Column(Enum(EmissionScope), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False)

    activity = relationship("ActivityData", back_populates="emission_records")
    factor = relationship("EmissionFactor", back_populates="emission_records")


class ResourceMetric(Base, TimestampMixin):
    __tablename__ = "esg_resource_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(Enum(ESGMetricType), nullable=False, index=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    period_from = Column(Date, nullable=False)
    period_to = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    location = relationship("Warehouse")


class ESGTarget(Base, TimestampMixin):
    __tablename__ = "esg_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(Enum(ESGMetricType), nullable=False)
    scope = Column(Enum(EmissionScope), nullable=True)
    baseline_year = Column(Integer, nullable=False)
    baseline_value = Column(Numeric(18, 4), nullable=False)
    target_value = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    target_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)


# ── Gap 64: Carbon Footprint Per Product / Batch ──────────────────────────────

# Gap 69: ESG Intelligence & Supplier Sustainability
class SupplierSustainabilityScore(Base, TimestampMixin):
    """
    Periodic supplier ESG scorecard used by procurement and sustainability teams.
    Keeps scored dimensions explicit so supplier risk can be audited and compared.
    """
    __tablename__ = "esg_supplier_sustainability_scores"
    __table_args__ = (
        Index("ix_esg_supplier_sustainability_period", "assessment_period_start", "assessment_period_end"),
        Index("ix_esg_supplier_sustainability_risk", "risk_level", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_name = Column(String(255), nullable=False)
    assessment_period_start = Column(Date, nullable=False)
    assessment_period_end = Column(Date, nullable=False)

    overall_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(Enum(SupplierSustainabilityRisk), nullable=False, default=SupplierSustainabilityRisk.MEDIUM)
    status = Column(Enum(SupplierSustainabilityStatus), nullable=False, default=SupplierSustainabilityStatus.ACTIVE)

    emissions_score = Column(Numeric(5, 2), nullable=True)
    energy_score = Column(Numeric(5, 2), nullable=True)
    water_score = Column(Numeric(5, 2), nullable=True)
    waste_score = Column(Numeric(5, 2), nullable=True)
    compliance_score = Column(Numeric(5, 2), nullable=True)
    labor_score = Column(Numeric(5, 2), nullable=True)

    renewable_energy_pct = Column(Numeric(6, 2), nullable=True)
    has_ghg_disclosure = Column(Boolean, default=False, nullable=False)
    has_science_based_target = Column(Boolean, default=False, nullable=False)
    iso14001_certified = Column(Boolean, default=False, nullable=False)
    wastewater_policy_verified = Column(Boolean, default=False, nullable=False)

    audit_findings = Column(Text, nullable=True)
    improvement_plan = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    assessed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    assessor = relationship("User", foreign_keys=[assessed_by])


# Gap 64: Carbon Footprint Per Product / Batch
class ProductCarbonFootprint(Base, TimestampMixin):
    """
    Granular carbon footprint per production batch and product.
    Scope 1: direct energy (combustion), Scope 2: purchased electricity,
    Scope 3: raw materials, transport, packaging.
    """
    __tablename__ = "esg_product_carbon_footprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String(300), nullable=True)
    production_batch_id = Column(String(100), nullable=True, index=True)  # soft FK to production batch
    batch_ref = Column(String(100), nullable=True)
    calculation_date = Column(Date, nullable=False)
    units_produced = Column(Numeric(14, 3), nullable=False)
    uom = Column(String(20), default="KG", nullable=False)

    # Scope emissions (kg CO2e)
    scope1_kg_co2e = Column(Numeric(14, 6), nullable=True)   # direct: gas, diesel used in production
    scope2_kg_co2e = Column(Numeric(14, 6), nullable=True)   # electricity consumption
    scope3_kg_co2e = Column(Numeric(14, 6), nullable=True)   # materials, transport, packaging
    total_kg_co2e = Column(Numeric(14, 6), nullable=False)
    co2e_per_unit = Column(Numeric(14, 6), nullable=True)    # total / units_produced

    # Breakdown inputs
    electricity_kwh = Column(Numeric(14, 4), nullable=True)
    electricity_emission_factor = Column(Numeric(10, 6), nullable=True)  # kg CO2e/kWh
    fuel_liters = Column(Numeric(14, 4), nullable=True)
    packaging_kg_co2e = Column(Numeric(14, 6), nullable=True)
    raw_material_kg_co2e = Column(Numeric(14, 6), nullable=True)
    transport_kg_co2e = Column(Numeric(14, 6), nullable=True)

    methodology = Column(String(200), nullable=True)  # GHG Protocol | ISO 14067 | custom
    verified = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    product = relationship("Product", foreign_keys=[product_id])
