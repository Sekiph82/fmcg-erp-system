"""IoT / Real-Time Machine Data Streaming models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class IoTDeviceProtocol(str, PyEnum):
    HTTP = "HTTP"
    MQTT = "MQTT"
    OPC_UA = "OPC_UA"
    SCADA = "SCADA"
    MODBUS = "MODBUS"
    MANUAL = "MANUAL"
    API = "API"


class IoTDeviceType(str, PyEnum):
    PLC = "PLC"
    SENSOR = "SENSOR"
    METER = "METER"
    GATEWAY = "GATEWAY"
    EDGE_AGENT = "EDGE_AGENT"
    SCADA_TAG = "SCADA_TAG"
    OTHER = "OTHER"


class IoTDeviceStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class IoTChannelValueType(str, PyEnum):
    NUMERIC = "NUMERIC"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    STATE = "STATE"


class IoTAggregationMethod(str, PyEnum):
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    SUM = "SUM"
    LAST = "LAST"
    COUNT = "COUNT"


class IoTIngestStatus(str, PyEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"


class IoTDevice(Base):
    """Registered IoT/SCADA/PLC source device or gateway."""
    __tablename__ = "iot_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    protocol = Column(Enum(IoTDeviceProtocol), nullable=False, default=IoTDeviceProtocol.HTTP)
    device_type = Column(Enum(IoTDeviceType), nullable=False, default=IoTDeviceType.OTHER)
    status = Column(Enum(IoTDeviceStatus), nullable=False, default=IoTDeviceStatus.ACTIVE, index=True)
    gateway_id = Column(UUID(as_uuid=True), nullable=True)
    machine_id = Column(String(100), nullable=True, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True, index=True)
    utility_device_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    work_center_id = Column(UUID(as_uuid=True), nullable=True)
    line_id = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    company_id = Column(UUID(as_uuid=True), nullable=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    credential_hash = Column(String(255), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_message_id = Column(String(255), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    channels = relationship("IoTChannel", back_populates="device", cascade="all, delete-orphan")


class IoTChannel(Base):
    """Metric channel exposed by a registered IoT device."""
    __tablename__ = "iot_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_code = Column(String(120), nullable=False)
    metric_name = Column(String(100), nullable=False, index=True)
    unit = Column(String(30), nullable=True)
    value_type = Column(Enum(IoTChannelValueType), nullable=False, default=IoTChannelValueType.NUMERIC)
    min_valid_value = Column(Numeric(18, 6), nullable=True)
    max_valid_value = Column(Numeric(18, 6), nullable=True)
    normal_min_value = Column(Numeric(18, 6), nullable=True)
    normal_max_value = Column(Numeric(18, 6), nullable=True)
    sampling_interval_seconds = Column(Integer, nullable=True)
    aggregation_method = Column(Enum(IoTAggregationMethod), nullable=True)
    machine_id = Column(String(100), nullable=True, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True)
    utility_device_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    production_order_link_mode = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    device = relationship("IoTDevice", back_populates="channels")


class IoTIngestMessage(Base):
    """Idempotency and audit record for a device/gateway ingest message."""
    __tablename__ = "iot_ingest_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(String(255), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    record_count = Column(Integer, nullable=False, default=0)
    status = Column(Enum(IoTIngestStatus), nullable=False, default=IoTIngestStatus.ACCEPTED)
    error_message = Column(Text, nullable=True)
    raw_payload_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    device = relationship("IoTDevice")


class SensorDataPoint(Base):
    """Time-series sensor reading from IoT device / PLC / SCADA."""
    __tablename__ = "iot_sensor_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("iot_channels.id", ondelete="SET NULL"), nullable=True, index=True)
    ingest_message_id = Column(UUID(as_uuid=True), ForeignKey("iot_ingest_messages.id", ondelete="SET NULL"), nullable=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True)
    machine_name = Column(String(200), nullable=True)
    utility_device_id = Column(UUID(as_uuid=True), nullable=True)
    sensor_id = Column(String(100), nullable=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)  # temperature | pressure | rpm | vibration | current
    value = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(30), nullable=True)                       # °C | bar | rpm | mm/s | A
    quality_flag = Column(Boolean, default=True, nullable=False)   # False = bad data quality
    source = Column(String(50), nullable=True)                     # MQTT | OPC-UA | HTTP | MANUAL
    production_order_id = Column(String(100), nullable=True, index=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("IoTDevice")
    channel = relationship("IoTChannel")
    ingest_message = relationship("IoTIngestMessage")


class MachineStateEvent(Base):
    """State transition event for a machine (RUNNING → IDLE → DOWN)."""
    __tablename__ = "iot_machine_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True)
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

    device = relationship("IoTDevice")


class IoTAlertThreshold(Base):
    """Configurable alert threshold per machine + metric."""
    __tablename__ = "iot_alert_thresholds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("iot_channels.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True)
    metric_name = Column(String(100), nullable=False)
    min_threshold = Column(Numeric(18, 6), nullable=True)
    max_threshold = Column(Numeric(18, 6), nullable=True)
    severity = Column(Enum(AlertSeverity, name="iot_alertseverity"), nullable=False, default=AlertSeverity.WARNING)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("IoTDevice")
    channel = relationship("IoTChannel")


class IoTAlert(Base):
    """Alert triggered when sensor value crosses threshold."""
    __tablename__ = "iot_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    threshold_id = Column(UUID(as_uuid=True), ForeignKey("iot_alert_thresholds.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("iot_channels.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_uuid = Column(UUID(as_uuid=True), nullable=True)
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
    device = relationship("IoTDevice")
    channel = relationship("IoTChannel")
