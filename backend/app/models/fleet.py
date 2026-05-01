from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, Numeric, Date, DateTime,
    Text, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class VehicleType(str, PyEnum):
    TRUCK = "truck"
    VAN = "van"
    MOTORCYCLE = "motorcycle"
    PICKUP = "pickup"
    THIRD_PARTY = "third_party"


class VehicleStatus(str, PyEnum):
    ACTIVE = "active"
    IN_SERVICE = "in_service"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class FuelType(str, PyEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"


class TripStatus(str, PyEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceType(str, PyEnum):
    SERVICE = "service"
    REPAIR = "repair"
    INSPECTION = "inspection"
    TYRE = "tyre"
    OTHER = "other"


class IncidentType(str, PyEnum):
    ACCIDENT = "accident"
    DAMAGE = "damage"
    THEFT = "theft"
    BREAKDOWN = "breakdown"
    OTHER = "other"


class IncidentStatus(str, PyEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DriverStatus(str, PyEnum):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"
    OFF_DUTY = "off_duty"
    INACTIVE = "inactive"


class Vehicle(Base, TimestampMixin):
    __tablename__ = "fleet_vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_code = Column(String(50), unique=True, nullable=False, index=True)
    plate_number = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    capacity_weight_kg = Column(Numeric(10, 2), nullable=True)
    capacity_volume_m3 = Column(Numeric(10, 2), nullable=True)
    fuel_type = Column(Enum(FuelType), default=FuelType.DIESEL, nullable=False)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.ACTIVE, nullable=False, index=True)
    purchase_date = Column(Date, nullable=True)
    odometer_km = Column(Numeric(12, 1), nullable=True)         # last known odometer
    gps_device_id = Column(String(100), nullable=True)          # telematics-ready
    assigned_driver_id = Column(UUID(as_uuid=True), ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True)
    default_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    assigned_driver = relationship("FleetDriver", foreign_keys=[assigned_driver_id])
    trips = relationship("FleetTrip", back_populates="vehicle", foreign_keys="FleetTrip.vehicle_id")
    fuel_logs = relationship("FuelLog", back_populates="vehicle", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="vehicle", cascade="all, delete-orphan")
    incidents = relationship("IncidentLog", back_populates="vehicle", cascade="all, delete-orphan")


class FleetDriver(Base, TimestampMixin):
    __tablename__ = "fleet_drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_code = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    license_number = Column(String(100), nullable=False)
    license_class = Column(String(20), nullable=True)           # A, B, CE, etc.
    license_expiry = Column(Date, nullable=True)
    status = Column(Enum(DriverStatus), default=DriverStatus.AVAILABLE, nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id])
    trips = relationship("FleetTrip", back_populates="driver", foreign_keys="FleetTrip.driver_id")
    incidents = relationship("IncidentLog", back_populates="driver")


class FleetTrip(Base, TimestampMixin):
    __tablename__ = "fleet_trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_no = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("fleet_vehicles.id", ondelete="RESTRICT"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_date = Column(Date, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    start_location = Column(String(255), nullable=True)
    end_location = Column(String(255), nullable=True)
    planned_distance_km = Column(Numeric(10, 2), nullable=True)
    actual_distance_km = Column(Numeric(10, 2), nullable=True)
    start_odometer = Column(Numeric(12, 1), nullable=True)
    end_odometer = Column(Numeric(12, 1), nullable=True)
    status = Column(Enum(TripStatus), default=TripStatus.PLANNED, nullable=False, index=True)
    purpose = Column(String(255), nullable=True)                # delivery / van_sales / transfer
    delivery_trip_id = Column(UUID(as_uuid=True), ForeignKey("delivery_trips.id", ondelete="SET NULL"), nullable=True)
    cargo_weight_kg = Column(Numeric(10, 2), nullable=True)
    fuel_used_liters = Column(Numeric(10, 3), nullable=True)    # captured at end of trip
    trip_cost = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="trips", foreign_keys=[vehicle_id])
    driver = relationship("FleetDriver", back_populates="trips", foreign_keys=[driver_id])


class FuelLog(Base, TimestampMixin):
    __tablename__ = "fleet_fuel_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("fleet_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("fleet_trips.id", ondelete="SET NULL"), nullable=True)
    fuel_date = Column(Date, nullable=False)
    fuel_quantity_liters = Column(Numeric(10, 3), nullable=False)
    fuel_cost = Column(Numeric(12, 2), nullable=False)
    cost_per_liter = Column(Numeric(10, 4), nullable=True)
    odometer_reading = Column(Numeric(12, 1), nullable=True)
    fuel_station = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="fuel_logs")
    trip = relationship("FleetTrip")


class MaintenanceRecord(Base, TimestampMixin):
    __tablename__ = "fleet_maintenance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("fleet_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_type = Column(Enum(MaintenanceType), nullable=False)
    maintenance_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)
    odometer_at_service = Column(Numeric(12, 1), nullable=True)
    next_due_date = Column(Date, nullable=True)
    next_due_odometer = Column(Numeric(12, 1), nullable=True)
    vendor = Column(String(255), nullable=True)
    downtime_days = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="maintenance_records")


class IncidentLog(Base, TimestampMixin):
    __tablename__ = "fleet_incident_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("fleet_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True)
    incident_date = Column(Date, nullable=False)
    incident_type = Column(Enum(IncidentType), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    cost_estimate = Column(Numeric(12, 2), nullable=True)
    insurance_claim_no = Column(String(100), nullable=True)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False)
    resolved_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="incidents")
    driver = relationship("FleetDriver", back_populates="incidents")
