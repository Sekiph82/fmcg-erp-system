import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date,
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
