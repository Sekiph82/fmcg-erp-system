from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.fleet import (
    DriverStatus, FuelType, IncidentStatus, IncidentType,
    MaintenanceType, TripStatus, VehicleStatus, VehicleType,
)


# ── Vehicle ───────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vehicle_code: str
    plate_number: str
    vehicle_type: VehicleType
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity_weight_kg: Optional[Decimal] = None
    capacity_volume_m3: Optional[Decimal] = None
    fuel_type: FuelType = FuelType.DIESEL
    status: VehicleStatus = VehicleStatus.ACTIVE
    purchase_date: Optional[date] = None
    odometer_km: Optional[Decimal] = None
    gps_device_id: Optional[str] = None
    assigned_driver_id: Optional[UUID] = None
    default_warehouse_id: Optional[UUID] = None
    notes: Optional[str] = None


class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity_weight_kg: Optional[Decimal] = None
    capacity_volume_m3: Optional[Decimal] = None
    fuel_type: Optional[FuelType] = None
    status: Optional[VehicleStatus] = None
    odometer_km: Optional[Decimal] = None
    gps_device_id: Optional[str] = None
    assigned_driver_id: Optional[UUID] = None
    default_warehouse_id: Optional[UUID] = None
    notes: Optional[str] = None


class VehicleOut(BaseModel):
    id: UUID
    vehicle_code: str
    plate_number: str
    vehicle_type: VehicleType
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity_weight_kg: Optional[Decimal] = None
    capacity_volume_m3: Optional[Decimal] = None
    fuel_type: FuelType
    status: VehicleStatus
    purchase_date: Optional[date] = None
    odometer_km: Optional[Decimal] = None
    gps_device_id: Optional[str] = None
    assigned_driver_id: Optional[UUID] = None
    default_warehouse_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Driver ────────────────────────────────────────────────────────────────────

class DriverCreate(BaseModel):
    driver_code: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: str
    license_class: Optional[str] = None
    license_expiry: Optional[date] = None
    status: DriverStatus = DriverStatus.AVAILABLE
    employee_id: Optional[UUID] = None
    notes: Optional[str] = None


class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    license_class: Optional[str] = None
    license_expiry: Optional[date] = None
    status: Optional[DriverStatus] = None
    employee_id: Optional[UUID] = None
    notes: Optional[str] = None


class DriverOut(BaseModel):
    id: UUID
    driver_code: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: str
    license_class: Optional[str] = None
    license_expiry: Optional[date] = None
    status: DriverStatus
    employee_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Trip ──────────────────────────────────────────────────────────────────────

class TripCreate(BaseModel):
    vehicle_id: UUID
    driver_id: Optional[UUID] = None
    trip_date: date
    start_time: Optional[datetime] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    planned_distance_km: Optional[Decimal] = None
    purpose: Optional[str] = None
    delivery_trip_id: Optional[UUID] = None
    cargo_weight_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class TripUpdate(BaseModel):
    driver_id: Optional[UUID] = None
    end_time: Optional[datetime] = None
    end_location: Optional[str] = None
    actual_distance_km: Optional[Decimal] = None
    start_odometer: Optional[Decimal] = None
    end_odometer: Optional[Decimal] = None
    status: Optional[TripStatus] = None
    fuel_used_liters: Optional[Decimal] = None
    trip_cost: Optional[Decimal] = None
    cargo_weight_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class TripOut(BaseModel):
    id: UUID
    trip_no: str
    vehicle_id: UUID
    driver_id: Optional[UUID] = None
    trip_date: date
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    planned_distance_km: Optional[Decimal] = None
    actual_distance_km: Optional[Decimal] = None
    status: TripStatus
    purpose: Optional[str] = None
    cargo_weight_kg: Optional[Decimal] = None
    fuel_used_liters: Optional[Decimal] = None
    trip_cost: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Fuel Log ──────────────────────────────────────────────────────────────────

class FuelLogCreate(BaseModel):
    vehicle_id: UUID
    trip_id: Optional[UUID] = None
    fuel_date: date
    fuel_quantity_liters: Decimal
    fuel_cost: Decimal
    cost_per_liter: Optional[Decimal] = None
    odometer_reading: Optional[Decimal] = None
    fuel_station: Optional[str] = None
    notes: Optional[str] = None


class FuelLogOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    trip_id: Optional[UUID] = None
    fuel_date: date
    fuel_quantity_liters: Decimal
    fuel_cost: Decimal
    cost_per_liter: Optional[Decimal] = None
    odometer_reading: Optional[Decimal] = None
    fuel_station: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Maintenance ───────────────────────────────────────────────────────────────

class MaintenanceCreate(BaseModel):
    vehicle_id: UUID
    maintenance_type: MaintenanceType
    maintenance_date: date
    description: Optional[str] = None
    cost: Optional[Decimal] = None
    odometer_at_service: Optional[Decimal] = None
    next_due_date: Optional[date] = None
    next_due_odometer: Optional[Decimal] = None
    vendor: Optional[str] = None
    downtime_days: Optional[int] = None
    notes: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    description: Optional[str] = None
    cost: Optional[Decimal] = None
    next_due_date: Optional[date] = None
    next_due_odometer: Optional[Decimal] = None
    vendor: Optional[str] = None
    downtime_days: Optional[int] = None
    completed: Optional[bool] = None
    notes: Optional[str] = None


class MaintenanceOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    maintenance_type: MaintenanceType
    maintenance_date: date
    description: Optional[str] = None
    cost: Optional[Decimal] = None
    odometer_at_service: Optional[Decimal] = None
    next_due_date: Optional[date] = None
    next_due_odometer: Optional[Decimal] = None
    vendor: Optional[str] = None
    downtime_days: Optional[int] = None
    completed: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Incident ──────────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    vehicle_id: UUID
    driver_id: Optional[UUID] = None
    incident_date: date
    incident_type: IncidentType
    description: Optional[str] = None
    location: Optional[str] = None
    cost_estimate: Optional[Decimal] = None
    insurance_claim_no: Optional[str] = None
    notes: Optional[str] = None


class IncidentUpdate(BaseModel):
    description: Optional[str] = None
    cost_estimate: Optional[Decimal] = None
    insurance_claim_no: Optional[str] = None
    status: Optional[IncidentStatus] = None
    resolved_date: Optional[date] = None
    notes: Optional[str] = None


class IncidentOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    driver_id: Optional[UUID] = None
    incident_date: date
    incident_type: IncidentType
    description: Optional[str] = None
    location: Optional[str] = None
    cost_estimate: Optional[Decimal] = None
    insurance_claim_no: Optional[str] = None
    status: IncidentStatus
    resolved_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard / Reports ───────────────────────────────────────────────────────

class FleetDashboard(BaseModel):
    total_vehicles: int
    active_vehicles: int
    in_maintenance: int
    trips_today: int
    trips_in_progress: int
    fuel_cost_this_month: float
    maintenance_cost_this_month: float
    open_incidents: int
    available_drivers: int
    upcoming_maintenance: List[Dict[str, Any]]
    recent_trips: List[Dict[str, Any]]
