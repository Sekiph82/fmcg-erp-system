"""Fleet Management endpoints."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.fleet import DriverStatus, IncidentStatus, TripStatus, VehicleStatus
from app.schemas.fleet import (
    DriverCreate, DriverOut, DriverUpdate,
    FleetDashboard,
    FuelLogCreate, FuelLogOut,
    IncidentCreate, IncidentOut, IncidentUpdate,
    MaintenanceCreate, MaintenanceOut, MaintenanceUpdate,
    TripCreate, TripOut, TripUpdate,
    VehicleCreate, VehicleOut, VehicleUpdate,
)
import app.services.fleet_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=FleetDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Vehicles ──────────────────────────────────────────────────────────────────

@router.get("/vehicles", response_model=List[VehicleOut])
async def list_vehicles(
    status: Optional[VehicleStatus] = None,
    vehicle_type: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_vehicles(db, status=status, vehicle_type=vehicle_type, skip=skip, limit=limit)


@router.post("/vehicles", response_model=VehicleOut, status_code=201)
async def create_vehicle(data: VehicleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_vehicle(db, data)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(vehicle_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_vehicle(db, vehicle_id)
    if not obj:
        raise HTTPException(404, "Vehicle not found")
    return obj


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(vehicle_id: UUID, data: VehicleUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_vehicle(db, vehicle_id, data)
    if not obj:
        raise HTTPException(404, "Vehicle not found")
    return obj


@router.get("/vehicles/{vehicle_id}/availability")
async def check_availability(
    vehicle_id: UUID,
    check_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    check = check_date or date.today()
    return await svc.check_vehicle_availability(db, vehicle_id, check)


# ── Drivers ───────────────────────────────────────────────────────────────────

@router.get("/drivers", response_model=List[DriverOut])
async def list_drivers(
    status: Optional[DriverStatus] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_drivers(db, status=status, skip=skip, limit=limit)


@router.post("/drivers", response_model=DriverOut, status_code=201)
async def create_driver(data: DriverCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_driver(db, data)


@router.get("/drivers/{driver_id}", response_model=DriverOut)
async def get_driver(driver_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_driver(db, driver_id)
    if not obj:
        raise HTTPException(404, "Driver not found")
    return obj


@router.patch("/drivers/{driver_id}", response_model=DriverOut)
async def update_driver(driver_id: UUID, data: DriverUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_driver(db, driver_id, data)
    if not obj:
        raise HTTPException(404, "Driver not found")
    return obj


# ── Trips ─────────────────────────────────────────────────────────────────────

@router.get("/trips", response_model=List[TripOut])
async def list_trips(
    vehicle_id: Optional[UUID] = None,
    driver_id: Optional[UUID] = None,
    status: Optional[TripStatus] = None,
    trip_date: Optional[date] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_trips(
        db, vehicle_id=vehicle_id, driver_id=driver_id,
        status=status, trip_date=trip_date, skip=skip, limit=limit,
    )


@router.post("/trips", response_model=TripOut, status_code=201)
async def create_trip(data: TripCreate, db: AsyncSession = Depends(get_db)):
    avail = await svc.check_vehicle_availability(db, data.vehicle_id, data.trip_date)
    if not avail["available"]:
        raise HTTPException(409, f"Vehicle not available: {avail['reason']}")
    return await svc.create_trip(db, data)


@router.get("/trips/{trip_id}", response_model=TripOut)
async def get_trip(trip_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_trip(db, trip_id)
    if not obj:
        raise HTTPException(404, "Trip not found")
    return obj


@router.patch("/trips/{trip_id}", response_model=TripOut)
async def update_trip(trip_id: UUID, data: TripUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_trip(db, trip_id, data)
    if not obj:
        raise HTTPException(404, "Trip not found")
    return obj


# ── Fuel Logs ─────────────────────────────────────────────────────────────────

@router.get("/fuel", response_model=List[FuelLogOut])
async def list_fuel_logs(
    vehicle_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_fuel_logs(db, vehicle_id=vehicle_id, skip=skip, limit=limit)


@router.post("/fuel", response_model=FuelLogOut, status_code=201)
async def create_fuel_log(data: FuelLogCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_fuel_log(db, data)


# ── Maintenance ───────────────────────────────────────────────────────────────

@router.get("/maintenance", response_model=List[MaintenanceOut])
async def list_maintenance(
    vehicle_id: Optional[UUID] = None,
    completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_maintenance(db, vehicle_id=vehicle_id, completed=completed, skip=skip, limit=limit)


@router.post("/maintenance", response_model=MaintenanceOut, status_code=201)
async def create_maintenance(data: MaintenanceCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_maintenance(db, data)


@router.patch("/maintenance/{record_id}", response_model=MaintenanceOut)
async def update_maintenance(record_id: UUID, data: MaintenanceUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_maintenance(db, record_id, data)
    if not obj:
        raise HTTPException(404, "Maintenance record not found")
    return obj


# ── Incidents ─────────────────────────────────────────────────────────────────

@router.get("/incidents", response_model=List[IncidentOut])
async def list_incidents(
    vehicle_id: Optional[UUID] = None,
    status: Optional[IncidentStatus] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_incidents(db, vehicle_id=vehicle_id, status=status, skip=skip, limit=limit)


@router.post("/incidents", response_model=IncidentOut, status_code=201)
async def create_incident(data: IncidentCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_incident(db, data)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
async def update_incident(incident_id: UUID, data: IncidentUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_incident(db, incident_id, data)
    if not obj:
        raise HTTPException(404, "Incident not found")
    return obj


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/utilization")
async def utilization_report(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_utilization_report(db, days=days)


@router.get("/reports/fuel")
async def fuel_report(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_fuel_report(db, days=days)


@router.get("/reports/maintenance")
async def maintenance_report(
    days: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_maintenance_report(db, days=days)


@router.get("/reports/drivers")
async def driver_report(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_driver_report(db, days=days)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/ai/route-efficiency")
async def ai_route_efficiency(db: AsyncSession = Depends(get_db)):
    return await svc.ai_route_efficiency(db)


@router.get("/ai/fuel-anomaly")
async def ai_fuel_anomaly(db: AsyncSession = Depends(get_db)):
    return await svc.ai_fuel_anomaly(db)


@router.get("/ai/maintenance-predictor")
async def ai_maintenance_predictor(db: AsyncSession = Depends(get_db)):
    return await svc.ai_maintenance_predictor(db)
