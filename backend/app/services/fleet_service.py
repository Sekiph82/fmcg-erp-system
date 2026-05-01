"""Fleet Management service — vehicles, drivers, trips, fuel, maintenance, incidents."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import (
    DriverStatus, FleetDriver, FleetTrip, FuelLog, IncidentLog,
    IncidentStatus, MaintenanceRecord, MaintenanceType,
    TripStatus, Vehicle, VehicleStatus,
)
from app.schemas.fleet import (
    DriverCreate, DriverUpdate, FuelLogCreate, IncidentCreate, IncidentUpdate,
    MaintenanceCreate, MaintenanceUpdate, TripCreate, TripUpdate,
    VehicleCreate, VehicleUpdate,
)


# ── Sequence helper ───────────────────────────────────────────────────────────

async def _next_trip_no(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(FleetTrip))
    n = (result.scalar_one() or 0) + 1
    return f"TRIP-{n:05d}"


async def _next_driver_code(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(FleetDriver))
    n = (result.scalar_one() or 0) + 1
    return f"DRV-{n:04d}"


# ── Vehicle CRUD ──────────────────────────────────────────────────────────────

async def list_vehicles(
    db: AsyncSession,
    status: Optional[VehicleStatus] = None,
    vehicle_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Vehicle]:
    q = select(Vehicle).order_by(Vehicle.vehicle_code)
    if status:
        q = q.where(Vehicle.status == status)
    if vehicle_type:
        q = q.where(Vehicle.vehicle_type == vehicle_type)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_vehicle(db: AsyncSession, vehicle_id: UUID) -> Optional[Vehicle]:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    return result.scalar_one_or_none()


async def create_vehicle(db: AsyncSession, data: VehicleCreate) -> Vehicle:
    vehicle = Vehicle(**data.model_dump())
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def update_vehicle(db: AsyncSession, vehicle_id: UUID, data: VehicleUpdate) -> Optional[Vehicle]:
    vehicle = await get_vehicle(db, vehicle_id)
    if not vehicle:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, val)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def check_vehicle_availability(
    db: AsyncSession, vehicle_id: UUID, trip_date: date
) -> Dict[str, Any]:
    """Check if vehicle is available on a given date."""
    vehicle = await get_vehicle(db, vehicle_id)
    if not vehicle:
        return {"available": False, "reason": "Vehicle not found"}

    if vehicle.status == VehicleStatus.MAINTENANCE:
        return {"available": False, "reason": "Vehicle is in maintenance"}
    if vehicle.status == VehicleStatus.INACTIVE:
        return {"available": False, "reason": "Vehicle is inactive"}

    # Check for conflicting trips on that date
    existing = await db.execute(
        select(FleetTrip).where(
            and_(
                FleetTrip.vehicle_id == vehicle_id,
                FleetTrip.trip_date == trip_date,
                FleetTrip.status.in_([TripStatus.PLANNED, TripStatus.IN_PROGRESS]),
            )
        )
    )
    conflict = existing.scalar_one_or_none()
    if conflict:
        return {"available": False, "reason": f"Already assigned to trip {conflict.trip_no}"}

    # Check for maintenance on that date
    maint = await db.execute(
        select(MaintenanceRecord).where(
            and_(
                MaintenanceRecord.vehicle_id == vehicle_id,
                MaintenanceRecord.maintenance_date == trip_date,
                MaintenanceRecord.completed == False,  # noqa: E712
            )
        )
    )
    if maint.scalar_one_or_none():
        return {"available": False, "reason": "Maintenance scheduled on this date"}

    return {"available": True, "reason": None}


# ── Driver CRUD ───────────────────────────────────────────────────────────────

async def list_drivers(
    db: AsyncSession,
    status: Optional[DriverStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[FleetDriver]:
    q = select(FleetDriver).order_by(FleetDriver.full_name)
    if status:
        q = q.where(FleetDriver.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_driver(db: AsyncSession, driver_id: UUID) -> Optional[FleetDriver]:
    result = await db.execute(select(FleetDriver).where(FleetDriver.id == driver_id))
    return result.scalar_one_or_none()


async def create_driver(db: AsyncSession, data: DriverCreate) -> FleetDriver:
    if not data.driver_code:
        data = data.model_copy(update={"driver_code": await _next_driver_code(db)})
    driver = FleetDriver(**data.model_dump())
    db.add(driver)
    await db.commit()
    await db.refresh(driver)
    return driver


async def update_driver(db: AsyncSession, driver_id: UUID, data: DriverUpdate) -> Optional[FleetDriver]:
    driver = await get_driver(db, driver_id)
    if not driver:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(driver, field, val)
    await db.commit()
    await db.refresh(driver)
    return driver


# ── Trip CRUD ─────────────────────────────────────────────────────────────────

async def list_trips(
    db: AsyncSession,
    vehicle_id: Optional[UUID] = None,
    driver_id: Optional[UUID] = None,
    status: Optional[TripStatus] = None,
    trip_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[FleetTrip]:
    q = select(FleetTrip).order_by(desc(FleetTrip.trip_date), desc(FleetTrip.created_at))
    if vehicle_id:
        q = q.where(FleetTrip.vehicle_id == vehicle_id)
    if driver_id:
        q = q.where(FleetTrip.driver_id == driver_id)
    if status:
        q = q.where(FleetTrip.status == status)
    if trip_date:
        q = q.where(FleetTrip.trip_date == trip_date)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_trip(db: AsyncSession, trip_id: UUID) -> Optional[FleetTrip]:
    result = await db.execute(select(FleetTrip).where(FleetTrip.id == trip_id))
    return result.scalar_one_or_none()


async def create_trip(db: AsyncSession, data: TripCreate) -> FleetTrip:
    trip = FleetTrip(
        trip_no=await _next_trip_no(db),
        **data.model_dump(),
    )
    db.add(trip)

    # Mark vehicle as in_service if trip starts now
    if data.start_time and data.start_time.date() == date.today():
        vehicle = await get_vehicle(db, data.vehicle_id)
        if vehicle and vehicle.status == VehicleStatus.ACTIVE:
            vehicle.status = VehicleStatus.IN_SERVICE

    # Mark driver as on_trip
    if data.driver_id:
        driver = await get_driver(db, data.driver_id)
        if driver:
            driver.status = DriverStatus.ON_TRIP

    await db.commit()
    await db.refresh(trip)
    return trip


async def update_trip(db: AsyncSession, trip_id: UUID, data: TripUpdate) -> Optional[FleetTrip]:
    trip = await get_trip(db, trip_id)
    if not trip:
        return None

    updates = data.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(trip, field, val)

    # Compute actual distance from odometer if both set
    if trip.start_odometer and trip.end_odometer and not trip.actual_distance_km:
        trip.actual_distance_km = trip.end_odometer - trip.start_odometer

    # On complete: free vehicle and driver
    if updates.get("status") == TripStatus.COMPLETED:
        vehicle = await get_vehicle(db, trip.vehicle_id)
        if vehicle:
            vehicle.status = VehicleStatus.ACTIVE
            if trip.end_odometer:
                vehicle.odometer_km = trip.end_odometer
        if trip.driver_id:
            driver = await get_driver(db, trip.driver_id)
            if driver:
                driver.status = DriverStatus.AVAILABLE

    await db.commit()
    await db.refresh(trip)
    return trip


# ── Fuel Log ──────────────────────────────────────────────────────────────────

async def list_fuel_logs(
    db: AsyncSession,
    vehicle_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[FuelLog]:
    q = select(FuelLog).order_by(desc(FuelLog.fuel_date))
    if vehicle_id:
        q = q.where(FuelLog.vehicle_id == vehicle_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_fuel_log(db: AsyncSession, data: FuelLogCreate) -> FuelLog:
    cost_per_liter = data.cost_per_liter
    if not cost_per_liter and data.fuel_quantity_liters and data.fuel_cost:
        cost_per_liter = data.fuel_cost / data.fuel_quantity_liters

    log = FuelLog(**data.model_dump(exclude={"cost_per_liter"}), cost_per_liter=cost_per_liter)
    db.add(log)

    # Update vehicle odometer
    if data.odometer_reading:
        vehicle = await get_vehicle(db, data.vehicle_id)
        if vehicle:
            vehicle.odometer_km = data.odometer_reading

    await db.commit()
    await db.refresh(log)
    return log


# ── Maintenance CRUD ──────────────────────────────────────────────────────────

async def list_maintenance(
    db: AsyncSession,
    vehicle_id: Optional[UUID] = None,
    completed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[MaintenanceRecord]:
    q = select(MaintenanceRecord).order_by(desc(MaintenanceRecord.maintenance_date))
    if vehicle_id:
        q = q.where(MaintenanceRecord.vehicle_id == vehicle_id)
    if completed is not None:
        q = q.where(MaintenanceRecord.completed == completed)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_maintenance(db: AsyncSession, data: MaintenanceCreate) -> MaintenanceRecord:
    record = MaintenanceRecord(**data.model_dump())
    db.add(record)

    # Put vehicle into maintenance status
    vehicle = await get_vehicle(db, data.vehicle_id)
    if vehicle and not data.maintenance_date > date.today():
        vehicle.status = VehicleStatus.MAINTENANCE

    await db.commit()
    await db.refresh(record)
    return record


async def update_maintenance(
    db: AsyncSession, record_id: UUID, data: MaintenanceUpdate
) -> Optional[MaintenanceRecord]:
    result = await db.execute(select(MaintenanceRecord).where(MaintenanceRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        return None
    updates = data.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(record, field, val)
    # If completed, free vehicle
    if updates.get("completed") is True:
        vehicle = await get_vehicle(db, record.vehicle_id)
        if vehicle and vehicle.status == VehicleStatus.MAINTENANCE:
            vehicle.status = VehicleStatus.ACTIVE
    await db.commit()
    await db.refresh(record)
    return record


# ── Incident CRUD ─────────────────────────────────────────────────────────────

async def list_incidents(
    db: AsyncSession,
    vehicle_id: Optional[UUID] = None,
    status: Optional[IncidentStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[IncidentLog]:
    q = select(IncidentLog).order_by(desc(IncidentLog.incident_date))
    if vehicle_id:
        q = q.where(IncidentLog.vehicle_id == vehicle_id)
    if status:
        q = q.where(IncidentLog.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_incident(db: AsyncSession, data: IncidentCreate) -> IncidentLog:
    incident = IncidentLog(**data.model_dump())
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


async def update_incident(
    db: AsyncSession, incident_id: UUID, data: IncidentUpdate
) -> Optional[IncidentLog]:
    result = await db.execute(select(IncidentLog).where(IncidentLog.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(incident, field, val)
    await db.commit()
    await db.refresh(incident)
    return incident


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    today = date.today()
    month_start = today.replace(day=1)

    total_v_r = await db.execute(select(func.count()).select_from(Vehicle))
    total_vehicles = total_v_r.scalar_one()

    active_v_r = await db.execute(
        select(func.count()).where(Vehicle.status == VehicleStatus.ACTIVE)
    )
    active_vehicles = active_v_r.scalar_one()

    maint_v_r = await db.execute(
        select(func.count()).where(Vehicle.status == VehicleStatus.MAINTENANCE)
    )
    in_maintenance = maint_v_r.scalar_one()

    trips_today_r = await db.execute(
        select(func.count()).where(FleetTrip.trip_date == today)
    )
    trips_today = trips_today_r.scalar_one()

    trips_ip_r = await db.execute(
        select(func.count()).where(FleetTrip.status == TripStatus.IN_PROGRESS)
    )
    trips_in_progress = trips_ip_r.scalar_one()

    fuel_r = await db.execute(
        select(func.sum(FuelLog.fuel_cost)).where(FuelLog.fuel_date >= month_start)
    )
    fuel_cost_month = float(fuel_r.scalar_one() or 0)

    maint_r = await db.execute(
        select(func.sum(MaintenanceRecord.cost)).where(MaintenanceRecord.maintenance_date >= month_start)
    )
    maint_cost_month = float(maint_r.scalar_one() or 0)

    incidents_r = await db.execute(
        select(func.count()).where(IncidentLog.status == IncidentStatus.OPEN)
    )
    open_incidents = incidents_r.scalar_one()

    drivers_r = await db.execute(
        select(func.count()).where(FleetDriver.status == DriverStatus.AVAILABLE)
    )
    available_drivers = drivers_r.scalar_one()

    # Upcoming maintenance (next 14 days)
    upcoming_r = await db.execute(
        select(MaintenanceRecord, Vehicle.vehicle_code, Vehicle.plate_number)
        .join(Vehicle, Vehicle.id == MaintenanceRecord.vehicle_id)
        .where(
            and_(
                MaintenanceRecord.completed == False,  # noqa: E712
                MaintenanceRecord.next_due_date.isnot(None),
                MaintenanceRecord.next_due_date <= today + timedelta(days=14),
                MaintenanceRecord.next_due_date >= today,
            )
        )
        .order_by(MaintenanceRecord.next_due_date)
        .limit(10)
    )
    upcoming_maintenance = [
        {
            "vehicle_code": row[1],
            "plate_number": row[2],
            "maintenance_type": row[0].maintenance_type.value,
            "next_due_date": str(row[0].next_due_date),
            "days_until": (row[0].next_due_date - today).days,
        }
        for row in upcoming_r.all()
    ]

    recent_trips_r = await db.execute(
        select(FleetTrip)
        .order_by(desc(FleetTrip.created_at))
        .limit(5)
    )
    recent_trips = [
        {
            "trip_no": t.trip_no,
            "trip_date": str(t.trip_date),
            "status": t.status.value,
            "purpose": t.purpose,
        }
        for t in recent_trips_r.scalars().all()
    ]

    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "in_maintenance": in_maintenance,
        "trips_today": trips_today,
        "trips_in_progress": trips_in_progress,
        "fuel_cost_this_month": fuel_cost_month,
        "maintenance_cost_this_month": maint_cost_month,
        "open_incidents": open_incidents,
        "available_drivers": available_drivers,
        "upcoming_maintenance": upcoming_maintenance,
        "recent_trips": recent_trips,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_utilization_report(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            Vehicle.vehicle_code,
            Vehicle.plate_number,
            Vehicle.vehicle_type,
            func.count(FleetTrip.id).label("trip_count"),
            func.sum(FleetTrip.actual_distance_km).label("total_km"),
            func.sum(FleetTrip.trip_cost).label("total_cost"),
        )
        .outerjoin(FleetTrip, and_(FleetTrip.vehicle_id == Vehicle.id, FleetTrip.trip_date >= since))
        .group_by(Vehicle.id, Vehicle.vehicle_code, Vehicle.plate_number, Vehicle.vehicle_type)
        .order_by(desc("trip_count"))
    )
    return [
        {
            "vehicle_code": r[0],
            "plate_number": r[1],
            "vehicle_type": r[2],
            "trip_count": r[3] or 0,
            "total_km": float(r[4] or 0),
            "total_cost": float(r[5] or 0),
            "utilization_pct": min(round((r[3] or 0) / max(days, 1) * 100, 1), 100),
        }
        for r in result.all()
    ]


async def get_fuel_report(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            Vehicle.vehicle_code,
            Vehicle.plate_number,
            func.sum(FuelLog.fuel_quantity_liters).label("total_liters"),
            func.sum(FuelLog.fuel_cost).label("total_cost"),
            func.avg(FuelLog.cost_per_liter).label("avg_cost_per_liter"),
        )
        .join(Vehicle, Vehicle.id == FuelLog.vehicle_id)
        .where(FuelLog.fuel_date >= since)
        .group_by(Vehicle.id, Vehicle.vehicle_code, Vehicle.plate_number)
        .order_by(desc("total_cost"))
    )
    rows = result.all()

    # Compute km/L using trip distance data
    report = []
    for r in rows:
        report.append({
            "vehicle_code": r[0],
            "plate_number": r[1],
            "total_liters": float(r[2] or 0),
            "total_fuel_cost": float(r[3] or 0),
            "avg_cost_per_liter": float(r[4] or 0),
        })
    return report


async def get_maintenance_report(db: AsyncSession, days: int = 90) -> List[Dict[str, Any]]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            Vehicle.vehicle_code,
            Vehicle.plate_number,
            MaintenanceRecord.maintenance_type,
            func.count(MaintenanceRecord.id).label("count"),
            func.sum(MaintenanceRecord.cost).label("total_cost"),
            func.sum(MaintenanceRecord.downtime_days).label("total_downtime"),
        )
        .join(Vehicle, Vehicle.id == MaintenanceRecord.vehicle_id)
        .where(MaintenanceRecord.maintenance_date >= since)
        .group_by(
            Vehicle.id, Vehicle.vehicle_code, Vehicle.plate_number,
            MaintenanceRecord.maintenance_type,
        )
        .order_by(desc("total_cost"))
    )
    return [
        {
            "vehicle_code": r[0],
            "plate_number": r[1],
            "maintenance_type": r[2],
            "count": r[3] or 0,
            "total_cost": float(r[4] or 0),
            "total_downtime_days": r[5] or 0,
        }
        for r in result.all()
    ]


async def get_driver_report(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            FleetDriver.full_name,
            FleetDriver.driver_code,
            func.count(FleetTrip.id).label("trip_count"),
            func.sum(FleetTrip.actual_distance_km).label("total_km"),
        )
        .outerjoin(FleetTrip, and_(FleetTrip.driver_id == FleetDriver.id, FleetTrip.trip_date >= since))
        .group_by(FleetDriver.id, FleetDriver.full_name, FleetDriver.driver_code)
        .order_by(desc("trip_count"))
    )
    return [
        {
            "driver_code": r[1],
            "full_name": r[0],
            "trip_count": r[2] or 0,
            "total_km": float(r[3] or 0),
        }
        for r in result.all()
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def ai_route_efficiency(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 1: Route efficiency optimizer."""
    since = date.today() - timedelta(days=30)
    result = await db.execute(
        select(
            Vehicle.vehicle_code,
            Vehicle.plate_number,
            Vehicle.capacity_weight_kg,
            func.count(FleetTrip.id).label("trips"),
            func.avg(FleetTrip.actual_distance_km).label("avg_km"),
            func.avg(FleetTrip.cargo_weight_kg).label("avg_cargo"),
        )
        .outerjoin(FleetTrip, and_(FleetTrip.vehicle_id == Vehicle.id, FleetTrip.trip_date >= since))
        .where(Vehicle.status != VehicleStatus.INACTIVE)
        .group_by(Vehicle.id, Vehicle.vehicle_code, Vehicle.plate_number, Vehicle.capacity_weight_kg)
    )

    recommendations = []
    for r in result.all():
        trips, avg_km, avg_cargo, capacity = r[3], r[4], r[5], r[2]
        if trips == 0:
            recommendations.append({
                "vehicle_code": r[0],
                "plate_number": r[1],
                "issue": "No trips in last 30 days",
                "recommendation": "Review if vehicle is needed or reassign to busier routes",
                "priority": "MEDIUM",
            })
        elif capacity and avg_cargo and float(avg_cargo) < float(capacity) * 0.4:
            utilization_pct = round(float(avg_cargo) / float(capacity) * 100, 1)
            recommendations.append({
                "vehicle_code": r[0],
                "plate_number": r[1],
                "issue": f"Low cargo utilization: {utilization_pct}% of capacity",
                "recommendation": "Consolidate loads or pair with smaller vehicle",
                "priority": "HIGH" if utilization_pct < 20 else "MEDIUM",
            })

    return {
        "agent": "Route Efficiency Optimizer",
        "analysis_period_days": 30,
        "recommendations": recommendations,
        "summary": f"{len(recommendations)} vehicle(s) flagged for route optimization.",
    }


async def ai_fuel_anomaly(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 2: Detect abnormal fuel consumption."""
    since = date.today() - timedelta(days=30)
    result = await db.execute(
        select(
            Vehicle.vehicle_code,
            Vehicle.plate_number,
            func.avg(FuelLog.fuel_quantity_liters).label("avg_fill"),
            func.max(FuelLog.fuel_quantity_liters).label("max_fill"),
            func.count(FuelLog.id).label("fill_count"),
        )
        .join(Vehicle, Vehicle.id == FuelLog.vehicle_id)
        .where(FuelLog.fuel_date >= since)
        .group_by(Vehicle.id, Vehicle.vehicle_code, Vehicle.plate_number)
    )

    anomalies = []
    for r in result.all():
        avg_fill = float(r[2] or 0)
        max_fill = float(r[3] or 0)
        if avg_fill > 0 and max_fill > avg_fill * 2:
            anomalies.append({
                "vehicle_code": r[0],
                "plate_number": r[1],
                "avg_fill_liters": round(avg_fill, 1),
                "max_fill_liters": round(max_fill, 1),
                "anomaly": "Single fill-up exceeded 2× average — possible tank manipulation or data entry error",
                "severity": "HIGH",
            })

    return {
        "agent": "Fuel Anomaly Detector",
        "period_days": 30,
        "anomalies": anomalies,
        "note": "Anomalies are flagged for human review only — no automatic action taken.",
    }


async def ai_maintenance_predictor(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 3: Predict upcoming maintenance needs."""
    today = date.today()
    predictions = []

    result = await db.execute(
        select(Vehicle, MaintenanceRecord)
        .outerjoin(MaintenanceRecord, and_(
            MaintenanceRecord.vehicle_id == Vehicle.id,
            MaintenanceRecord.completed == False,  # noqa: E712
            MaintenanceRecord.next_due_date.isnot(None),
        ))
        .where(Vehicle.status != VehicleStatus.INACTIVE)
    )

    seen: set = set()
    for vehicle, maint in result.all():
        if vehicle.id in seen:
            continue
        seen.add(vehicle.id)

        issues = []

        # Check next maintenance
        if maint and maint.next_due_date:
            days_until = (maint.next_due_date - today).days
            if days_until <= 30:
                issues.append({
                    "type": maint.maintenance_type.value,
                    "due_date": str(maint.next_due_date),
                    "days_remaining": days_until,
                    "urgency": "CRITICAL" if days_until <= 7 else ("HIGH" if days_until <= 14 else "MEDIUM"),
                })

        # Check odometer-based service (every 10,000 km — configurable)
        if vehicle.odometer_km and maint and maint.next_due_odometer:
            km_remaining = float(maint.next_due_odometer) - float(vehicle.odometer_km)
            if km_remaining <= 1000:
                issues.append({
                    "type": "odometer_service",
                    "current_odometer": float(vehicle.odometer_km),
                    "due_at_odometer": float(maint.next_due_odometer),
                    "km_remaining": round(km_remaining, 0),
                    "urgency": "CRITICAL" if km_remaining <= 200 else "HIGH",
                })

        if issues:
            predictions.append({
                "vehicle_code": vehicle.vehicle_code,
                "plate_number": vehicle.plate_number,
                "predicted_issues": issues,
            })

    return {
        "agent": "Maintenance Predictor",
        "vehicles_analyzed": len(seen),
        "vehicles_requiring_attention": len(predictions),
        "predictions": predictions,
        "disclaimer": "Predictions based on due dates and odometer data. Consult workshop before acting.",
    }
