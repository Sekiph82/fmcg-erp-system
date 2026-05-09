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

from app.core.deps import get_current_user, get_db
from app.models.iot import (
    SensorDataPoint, MachineStateEvent, IoTAlertThreshold, IoTAlert,
    MachineState, AlertSeverity, AlertStatus,
)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SensorIn(BaseModel):
    machine_id: str
    machine_name: Optional[str] = None
    sensor_id: Optional[str] = None
    metric_name: str
    value: float
    unit: Optional[str] = None
    quality_flag: bool = True
    source: str = "HTTP"
    production_order_id: Optional[str] = None
    recorded_at: Optional[str] = None


class SensorBatchIn(BaseModel):
    readings: List[SensorIn]


class StateIn(BaseModel):
    machine_id: str
    machine_name: Optional[str] = None
    state: MachineState
    trigger_value: Optional[float] = None
    trigger_metric: Optional[str] = None
    trigger_source: str = "manual"
    notes: Optional[str] = None


class ThresholdIn(BaseModel):
    machine_id: str
    metric_name: str
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    description: Optional[str] = None


# ── Sensor Data Ingest ────────────────────────────────────────────────────────

@router.post("/ingest", status_code=201)
async def ingest_sensor(payload: SensorIn, db: AsyncSession = Depends(get_db)):
    """Ingest single sensor reading. No auth required — designed for device push."""
    recorded = datetime.fromisoformat(payload.recorded_at) if payload.recorded_at else datetime.utcnow()
    dp = SensorDataPoint(
        machine_id=payload.machine_id,
        machine_name=payload.machine_name,
        sensor_id=payload.sensor_id,
        metric_name=payload.metric_name,
        value=payload.value,
        unit=payload.unit,
        quality_flag=payload.quality_flag,
        source=payload.source,
        production_order_id=payload.production_order_id,
        recorded_at=recorded,
    )
    db.add(dp)

    # Check thresholds → create alert if breached
    thresh_r = await db.execute(
        select(IoTAlertThreshold).where(
            IoTAlertThreshold.machine_id == payload.machine_id,
            IoTAlertThreshold.metric_name == payload.metric_name,
            IoTAlertThreshold.is_active == True,
        )
    )
    for threshold in thresh_r.scalars().all():
        breached = False
        if threshold.min_threshold is not None and payload.value < float(threshold.min_threshold):
            breached = True
        if threshold.max_threshold is not None and payload.value > float(threshold.max_threshold):
            breached = True
        if breached:
            alert = IoTAlert(
                threshold_id=threshold.id,
                machine_id=payload.machine_id,
                machine_name=payload.machine_name,
                metric_name=payload.metric_name,
                triggered_value=payload.value,
                threshold_min=threshold.min_threshold,
                threshold_max=threshold.max_threshold,
                severity=threshold.severity,
                triggered_at=recorded,
            )
            db.add(alert)

    await db.commit()
    return {"machine_id": payload.machine_id, "metric": payload.metric_name, "value": payload.value, "recorded_at": recorded.isoformat()}


@router.post("/ingest/batch", status_code=201)
async def ingest_batch(payload: SensorBatchIn, db: AsyncSession = Depends(get_db)):
    """Batch ingest up to 1000 sensor readings."""
    if len(payload.readings) > 1000:
        raise HTTPException(400, "Max 1000 readings per batch")
    ingested = 0
    for r in payload.readings:
        recorded = datetime.fromisoformat(r.recorded_at) if r.recorded_at else datetime.utcnow()
        db.add(SensorDataPoint(
            machine_id=r.machine_id, machine_name=r.machine_name,
            sensor_id=r.sensor_id, metric_name=r.metric_name,
            value=r.value, unit=r.unit, quality_flag=r.quality_flag,
            source=r.source, recorded_at=recorded,
        ))
        ingested += 1
    await db.commit()
    return {"ingested": ingested}


@router.get("/sensors/latest")
async def latest_readings(
    machine_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
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
    _=Depends(get_current_user),
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
async def record_state(payload: StateIn, db: AsyncSession = Depends(get_db)):
    """Record machine state change. Computes duration in previous state."""
    # Get last state for duration calc
    prev_r = await db.execute(
        select(MachineStateEvent)
        .where(MachineStateEvent.machine_id == payload.machine_id)
        .order_by(desc(MachineStateEvent.changed_at))
        .limit(1)
    )
    prev = prev_r.scalar_one_or_none()
    prev_state = prev.state if prev else None
    duration = int((datetime.utcnow() - prev.changed_at).total_seconds()) if prev else None

    evt = MachineStateEvent(
        machine_id=payload.machine_id,
        machine_name=payload.machine_name,
        state=payload.state,
        previous_state=prev_state,
        trigger_value=payload.trigger_value,
        trigger_metric=payload.trigger_metric,
        trigger_source=payload.trigger_source,
        duration_seconds=duration,
        notes=payload.notes,
    )
    db.add(evt)
    await db.commit()
    return {"machine_id": payload.machine_id, "state": payload.state,
            "previous_state": prev_state, "duration_seconds": duration}


@router.get("/machines/current-states")
async def current_machine_states(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Current state per machine (latest state event per machine_id)."""
    # Get max changed_at per machine
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
    _=Depends(get_current_user),
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
async def create_threshold(payload: ThresholdIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
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
    _=Depends(get_current_user),
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
    _=Depends(get_current_user),
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
    _=Depends(get_current_user),
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


@router.get("/dashboard")
async def iot_dashboard(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
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

    return {
        "readings_last_1h": readings_1h_r.scalar() or 0,
        "open_alerts": open_alerts_r.scalar() or 0,
        "critical_alerts": critical_r.scalar() or 0,
        "active_machines_24h": machines_r.scalar() or 0,
    }
