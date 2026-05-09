"""IoT / Real-Time Machine Data Streaming models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class MachineState(str, PyEnum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    DOWN = "DOWN"
    FAULT = "FAULT"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class AlertSeverity(str, PyEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, PyEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class SensorDataPoint(Base):
    """Time-series sensor reading from IoT device / PLC / SCADA."""
    __tablename__ = "iot_sensor_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_name = Column(String(200), nullable=True)
    sensor_id = Column(String(100), nullable=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)  # temperature | pressure | rpm | vibration | current
    value = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(30), nullable=True)                       # °C | bar | rpm | mm/s | A
    quality_flag = Column(Boolean, default=True, nullable=False)   # False = bad data quality
    source = Column(String(50), nullable=True)                     # MQTT | OPC-UA | HTTP | MANUAL
    production_order_id = Column(String(100), nullable=True, index=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MachineStateEvent(Base):
    """State transition event for a machine (RUNNING → IDLE → DOWN)."""
    __tablename__ = "iot_machine_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_name = Column(String(200), nullable=True)
    state = Column(Enum(MachineState), nullable=False)
    previous_state = Column(Enum(MachineState), nullable=True)
    trigger_value = Column(Numeric(18, 6), nullable=True)
    trigger_metric = Column(String(100), nullable=True)
    trigger_source = Column(String(100), nullable=True)   # auto | manual | alarm
    duration_seconds = Column(Integer, nullable=True)     # duration in previous state
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IoTAlertThreshold(Base):
    """Configurable alert threshold per machine + metric."""
    __tablename__ = "iot_alert_thresholds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    min_threshold = Column(Numeric(18, 6), nullable=True)
    max_threshold = Column(Numeric(18, 6), nullable=True)
    severity = Column(Enum(AlertSeverity, name="iot_alertseverity"), nullable=False, default=AlertSeverity.WARNING)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IoTAlert(Base):
    """Alert triggered when sensor value crosses threshold."""
    __tablename__ = "iot_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    threshold_id = Column(UUID(as_uuid=True), ForeignKey("iot_alert_thresholds.id", ondelete="SET NULL"), nullable=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_name = Column(String(200), nullable=True)
    metric_name = Column(String(100), nullable=False)
    triggered_value = Column(Numeric(18, 6), nullable=False)
    threshold_min = Column(Numeric(18, 6), nullable=True)
    threshold_max = Column(Numeric(18, 6), nullable=True)
    severity = Column(Enum(AlertSeverity, name="iot_alertseverity"), nullable=False, default=AlertSeverity.WARNING)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.OPEN, index=True)
    acknowledged_by = Column(String(200), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    threshold = relationship("IoTAlertThreshold", foreign_keys=[threshold_id])
