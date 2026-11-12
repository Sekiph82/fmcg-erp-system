"""Native IoT ingest shared by the REST endpoints and the MQTT bridge.

One reading is stored as a SensorDataPoint and checked against the machine's active alert
thresholds; a state change is stored as a MachineStateEvent with the previous state and how long
the machine stayed in it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iot import IoTAlert, IoTAlertThreshold, MachineState, MachineStateEvent, SensorDataPoint


class SensorIn(BaseModel):  # lengths and value range match the iot_sensor_data columns
    machine_id: str = Field(min_length=1, max_length=100)
    machine_name: Optional[str] = Field(None, max_length=200)
    sensor_id: Optional[str] = Field(None, max_length=100)
    metric_name: str = Field(min_length=1, max_length=100)
    value: float = Field(allow_inf_nan=False, gt=-1e12, lt=1e12)
    unit: Optional[str] = Field(None, max_length=30)
    quality_flag: bool = True
    source: str = Field("HTTP", max_length=50)
    production_order_id: Optional[str] = Field(None, max_length=100)
    recorded_at: Optional[str] = None


class SensorBatchIn(BaseModel):
    readings: List[SensorIn]


class StateIn(BaseModel):
    machine_id: str = Field(min_length=1, max_length=100)
    machine_name: Optional[str] = Field(None, max_length=200)
    state: MachineState
    trigger_value: Optional[float] = Field(None, allow_inf_nan=False, gt=-1e12, lt=1e12)
    trigger_metric: Optional[str] = Field(None, max_length=100)
    trigger_source: str = Field("manual", max_length=100)
    notes: Optional[str] = None
    changed_at: Optional[str] = None  # device time of the change; server time when omitted


def parse_recorded_at(value: Optional[str]) -> datetime:
    """Naive UTC for the timestamp-without-zone columns; device clocks often send '...Z'."""
    if not value:
        return datetime.utcnow()
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.astimezone(timezone.utc).replace(tzinfo=None) if moment.tzinfo else moment


async def ingest_reading(db: AsyncSession, payload: SensorIn, ingest_message_id: Optional[UUID] = None,
                         device_id: Optional[UUID] = None) -> datetime:
    """Store one reading and raise alerts for breached thresholds. Caller commits."""
    recorded = parse_recorded_at(payload.recorded_at)
    db.add(SensorDataPoint(
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
        ingest_message_id=ingest_message_id,
        device_id=device_id,
    ))
    thresholds = (await db.execute(select(IoTAlertThreshold).where(
        IoTAlertThreshold.machine_id == payload.machine_id,
        IoTAlertThreshold.metric_name == payload.metric_name,
        IoTAlertThreshold.is_active == True,  # noqa: E712
    ))).scalars().all()
    for threshold in thresholds:
        breached = (threshold.min_threshold is not None and payload.value < float(threshold.min_threshold)) or (
            threshold.max_threshold is not None and payload.value > float(threshold.max_threshold))
        if breached:
            db.add(IoTAlert(
                threshold_id=threshold.id,
                machine_id=payload.machine_id,
                machine_name=payload.machine_name,
                metric_name=payload.metric_name,
                triggered_value=payload.value,
                threshold_min=threshold.min_threshold,
                threshold_max=threshold.max_threshold,
                severity=threshold.severity,
                triggered_at=recorded,
            ))
    return recorded


async def record_machine_state(db: AsyncSession, payload: StateIn) -> dict:
    """Store a state change with the previous state and its duration. Caller commits."""
    prev = (await db.execute(
        select(MachineStateEvent)
        .where(MachineStateEvent.machine_id == payload.machine_id)
        .order_by(desc(MachineStateEvent.changed_at))
        .limit(1)
    )).scalar_one_or_none()
    prev_state = prev.state if prev else None
    changed = parse_recorded_at(payload.changed_at)
    duration = int((changed - prev.changed_at).total_seconds()) if prev else None
    db.add(MachineStateEvent(
        machine_id=payload.machine_id,
        machine_name=payload.machine_name,
        state=payload.state,
        previous_state=prev_state,
        trigger_value=payload.trigger_value,
        trigger_metric=payload.trigger_metric,
        trigger_source=payload.trigger_source,
        duration_seconds=duration,
        notes=payload.notes,
        changed_at=changed,
    ))
    return {"machine_id": payload.machine_id, "state": payload.state,
            "previous_state": prev_state, "duration_seconds": duration}
