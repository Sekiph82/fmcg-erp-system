"""IoT / Real-Time Machine Data Streaming endpoints.

Prefix: /api/v1/iot
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models.iot import (
    SensorDataPoint, MachineStateEvent, IoTAlertThreshold, IoTAlert,
    IoTDevice, IoTChannel,
    MachineState, AlertSeverity, AlertStatus,
)

from app.services.iot_ingest import (
    SensorBatchIn, SensorIn, StateIn, ingest_reading, record_machine_state,
)

router = APIRouter()


# ── Request Schemas ───────────────────────────────────────────────────────────

class ThresholdIn(BaseModel):
    machine_id: str
    metric_name: str
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    description: Optional[str] = None


# ── Sensor Data Ingest ────────────────────────────────────────────────────────

@router.post("/ingest", status_code=201)
async def ingest_sensor(
    payload: SensorIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "ingest")),
):
    """Ingest single sensor reading. Requires iot.ingest permission."""
    recorded = await ingest_reading(db, payload)
    await db.commit()
    return {"machine_id": payload.machine_id, "metric": payload.metric_name, "value": payload.value, "recorded_at": recorded.isoformat()}


@router.post("/ingest/batch", status_code=201)
async def ingest_batch(
    payload: SensorBatchIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "ingest")),
):
    """Batch ingest up to 1000 sensor readings. Requires iot.ingest permission."""
    if len(payload.readings) > 1000:
        raise HTTPException(400, "Max 1000 readings per batch")
    for r in payload.readings:  # same path as single readings, so thresholds raise alerts here too
        await ingest_reading(db, r)
    await db.commit()
    return {"ingested": len(payload.readings)}


@router.get("/bridge/status")
async def mqtt_bridge_status(_=Depends(require_permission("iot", "view"))):
    """MQTT bridge state for this API worker (no credentials)."""
    from app.services.mqtt_bridge import STATUS

    return dict(STATUS)


@router.get("/sensors/latest")
async def latest_readings(
    machine_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """Latest N sensor readings."""
    q = select(SensorDataPoint).where(SensorDataPoint.quality_flag == True)
    if machine_id:
        q = q.where(SensorDataPoint.machine_id == machine_id)
    if metric_name:
        q = q.where(SensorDataPoint.metric_name == metric_name)
    q = q.order_by(desc(SensorDataPoint.recorded_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "machine_id": r.machine_id, "machine_name": r.machine_name,
         "metric_name": r.metric_name, "value": float(r.value), "unit": r.unit,
         "source": r.source, "recorded_at": r.recorded_at.isoformat() if r.recorded_at else ""}
        for r in rows
    ]


@router.get("/sensors/summary")
async def sensor_summary(
    hours: int = Query(1, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """Avg/min/max per machine+metric over last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    r = await db.execute(
        select(
            SensorDataPoint.machine_id,
            SensorDataPoint.machine_name,
            SensorDataPoint.metric_name,
            SensorDataPoint.unit,
            func.avg(SensorDataPoint.value).label("avg_val"),
            func.min(SensorDataPoint.value).label("min_val"),
            func.max(SensorDataPoint.value).label("max_val"),
            func.count().label("readings"),
        )
        .where(SensorDataPoint.recorded_at >= cutoff, SensorDataPoint.quality_flag == True)
        .group_by(SensorDataPoint.machine_id, SensorDataPoint.machine_name,
                  SensorDataPoint.metric_name, SensorDataPoint.unit)
        .order_by(SensorDataPoint.machine_id, SensorDataPoint.metric_name)
    )
    return [
        {"machine_id": row.machine_id, "machine_name": row.machine_name,
         "metric_name": row.metric_name, "unit": row.unit,
         "avg": round(float(row.avg_val), 4), "min": round(float(row.min_val), 4),
         "max": round(float(row.max_val), 4), "readings": row.readings}
        for row in r.all()
    ]


# ── Machine State ─────────────────────────────────────────────────────────────

@router.post("/machines/state", status_code=201)
async def record_state(
    payload: StateIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "ingest")),
):
    """Record machine state change. Requires iot.ingest permission."""
    result = await record_machine_state(db, payload)
    await db.commit()
    return result


@router.get("/machines/current-states")
async def current_machine_states(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """Current state per machine (latest state event per machine_id)."""
    latest_r = await db.execute(
        select(MachineStateEvent.machine_id, func.max(MachineStateEvent.changed_at).label("latest"))
        .group_by(MachineStateEvent.machine_id)
    )
    machine_latest = {row.machine_id: row.latest for row in latest_r.all()}

    states = []
    for machine_id, latest_ts in machine_latest.items():
        row_r = await db.execute(
            select(MachineStateEvent)
            .where(MachineStateEvent.machine_id == machine_id,
                   MachineStateEvent.changed_at == latest_ts)
            .limit(1)
        )
        row = row_r.scalar_one_or_none()
        if row:
            states.append({
                "machine_id": row.machine_id,
                "machine_name": row.machine_name,
                "state": row.state,
                "changed_at": row.changed_at.isoformat() if row.changed_at else "",
                "minutes_in_state": int((datetime.utcnow() - row.changed_at).total_seconds() / 60) if row.changed_at else None,
            })
    return states


@router.get("/machines/state-history")
async def state_history(
    machine_id: str,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    q = select(MachineStateEvent).where(MachineStateEvent.machine_id == machine_id)
    q = q.order_by(desc(MachineStateEvent.changed_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"state": r.state, "previous_state": r.previous_state,
         "changed_at": r.changed_at.isoformat() if r.changed_at else "",
         "duration_seconds": r.duration_seconds, "trigger_source": r.trigger_source}
        for r in rows
    ]


# ── Alert Thresholds ──────────────────────────────────────────────────────────

@router.post("/thresholds", status_code=201)
async def create_threshold(
    payload: ThresholdIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "configure")),
):
    t = IoTAlertThreshold(**payload.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": str(t.id), "machine_id": t.machine_id, "metric_name": t.metric_name,
            "min_threshold": float(t.min_threshold) if t.min_threshold else None,
            "max_threshold": float(t.max_threshold) if t.max_threshold else None,
            "severity": t.severity}


@router.get("/thresholds")
async def list_thresholds(
    machine_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    q = select(IoTAlertThreshold).where(IoTAlertThreshold.is_active == True)
    if machine_id:
        q = q.where(IoTAlertThreshold.machine_id == machine_id)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "machine_id": r.machine_id, "metric_name": r.metric_name,
         "min_threshold": float(r.min_threshold) if r.min_threshold else None,
         "max_threshold": float(r.max_threshold) if r.max_threshold else None,
         "severity": r.severity, "description": r.description}
        for r in rows
    ]


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    machine_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    q = select(IoTAlert)
    if status:
        q = q.where(IoTAlert.status == status)
    if severity:
        q = q.where(IoTAlert.severity == severity)
    if machine_id:
        q = q.where(IoTAlert.machine_id == machine_id)
    q = q.order_by(desc(IoTAlert.triggered_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "machine_id": r.machine_id, "machine_name": r.machine_name,
         "metric_name": r.metric_name, "triggered_value": float(r.triggered_value),
         "severity": r.severity, "status": r.status,
         "triggered_at": r.triggered_at.isoformat() if r.triggered_at else "",
         "acknowledged_by": r.acknowledged_by}
        for r in rows
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "acknowledge")),
):
    r = await db.execute(select(IoTAlert).where(IoTAlert.id == uuid.UUID(alert_id)))
    alert = r.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    return {"alert_id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_by": acknowledged_by}


# ── Device Registry (read-only) ───────────────────────────────────────────────

@router.get("/devices")
async def list_devices(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """List registered IoT devices."""
    q = select(IoTDevice)
    if status:
        q = q.where(IoTDevice.status == status)
    q = q.order_by(IoTDevice.name).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "device_code": r.device_code, "name": r.name,
         "protocol": r.protocol, "device_type": r.device_type, "status": r.status,
         "machine_id": r.machine_id, "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None}
        for r in rows
    ]


@router.get("/devices/{device_id}/channels")
async def list_device_channels(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """List channels for a registered IoT device."""
    q = select(IoTChannel).where(
        IoTChannel.device_id == uuid.UUID(device_id),
        IoTChannel.is_active == True,
    ).order_by(IoTChannel.metric_name)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "channel_code": r.channel_code, "metric_name": r.metric_name,
         "unit": r.unit, "value_type": r.value_type,
         "min_valid_value": float(r.min_valid_value) if r.min_valid_value is not None else None,
         "max_valid_value": float(r.max_valid_value) if r.max_valid_value is not None else None}
        for r in rows
    ]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def iot_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("iot", "view")),
):
    """IoT system overview."""
    cutoff_1h = datetime.utcnow() - timedelta(hours=1)
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    readings_1h_r = await db.execute(
        select(func.count()).select_from(SensorDataPoint)
        .where(SensorDataPoint.recorded_at >= cutoff_1h)
    )
    open_alerts_r = await db.execute(
        select(func.count()).select_from(IoTAlert)
        .where(IoTAlert.status == AlertStatus.OPEN)
    )
    critical_r = await db.execute(
        select(func.count()).select_from(IoTAlert)
        .where(IoTAlert.status == AlertStatus.OPEN, IoTAlert.severity == AlertSeverity.CRITICAL)
    )
    machines_r = await db.execute(
        select(func.count(func.distinct(SensorDataPoint.machine_id)))
        .where(SensorDataPoint.recorded_at >= cutoff_24h)
    )
    devices_r = await db.execute(
        select(func.count()).select_from(IoTDevice)
        .where(IoTDevice.status == "ACTIVE")
    )

    return {
        "readings_last_1h": readings_1h_r.scalar() or 0,
        "open_alerts": open_alerts_r.scalar() or 0,
        "critical_alerts": critical_r.scalar() or 0,
        "active_machines_24h": machines_r.scalar() or 0,
        "registered_devices": devices_r.scalar() or 0,
    }
