"""iot machine streaming reconciliation

Revision ID: 20260516_0020
Revises: 20260516_0010
Create Date: 2026-05-16 07:25:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260516_0020"
down_revision = "20260516_0010"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def _create_enum(name: str, *values: str) -> None:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)


def _enum(name: str, *values: str):
    return postgresql.ENUM(*values, name=name, create_type=False)


def _drop_enum(name: str) -> None:
    op.execute(f"DROP TYPE IF EXISTS {name}")


def _timestamps(timezone: bool = False) -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=timezone), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=timezone), server_default=sa.func.now(), nullable=True),
    ]


def _create_enums() -> None:
    _create_enum("machinestate", "RUNNING", "IDLE", "DOWN", "FAULT", "MAINTENANCE", "OFFLINE")
    _create_enum("iot_alertseverity", "INFO", "WARNING", "CRITICAL")
    _create_enum("alertstatus", "OPEN", "ACKNOWLEDGED", "RESOLVED")
    _create_enum("iotdeviceprotocol", "HTTP", "MQTT", "OPC_UA", "SCADA", "MODBUS", "MANUAL", "API")
    _create_enum("iotdevicetype", "PLC", "SENSOR", "METER", "GATEWAY", "EDGE_AGENT", "SCADA_TAG", "OTHER")
    _create_enum("iotdevicestatus", "ACTIVE", "DISABLED", "MAINTENANCE", "RETIRED")
    _create_enum("iotchannelvaluetype", "NUMERIC", "BOOLEAN", "STRING", "STATE")
    _create_enum("iotaggregationmethod", "AVG", "MIN", "MAX", "SUM", "LAST", "COUNT")
    _create_enum("iotingeststatus", "ACCEPTED", "DUPLICATE", "REJECTED", "PARTIAL")


def _create_registry_tables() -> None:
    if context.is_offline_mode() or not _has_table("iot_devices"):
        op.create_table(
            "iot_devices",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_code", sa.String(100), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("protocol", _enum("iotdeviceprotocol", "HTTP", "MQTT", "OPC_UA", "SCADA", "MODBUS", "MANUAL", "API"), nullable=False, server_default="HTTP"),
            sa.Column("device_type", _enum("iotdevicetype", "PLC", "SENSOR", "METER", "GATEWAY", "EDGE_AGENT", "SCADA_TAG", "OTHER"), nullable=False, server_default="OTHER"),
            sa.Column("status", _enum("iotdevicestatus", "ACTIVE", "DISABLED", "MAINTENANCE", "RETIRED"), nullable=False, server_default="ACTIVE"),
            sa.Column("gateway_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=True),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("utility_device_id", UUID, nullable=True),
            sa.Column("work_center_id", UUID, nullable=True),
            sa.Column("line_id", sa.String(100), nullable=True),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("company_id", UUID, nullable=True),
            sa.Column("branch_id", UUID, nullable=True),
            sa.Column("credential_hash", sa.String(255), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_message_id", sa.String(255), nullable=True),
            sa.Column("metadata_json", JSONB, nullable=True),
            *_timestamps(timezone=True),
            sa.UniqueConstraint("device_code", name="uq_iot_devices_device_code"),
        )

    _create_index_once("ix_iot_devices_device_code", "iot_devices", ["device_code"])
    _create_index_once("ix_iot_devices_machine_id", "iot_devices", ["machine_id"])
    _create_index_once("ix_iot_devices_machine_uuid", "iot_devices", ["machine_uuid"])
    _create_index_once("ix_iot_devices_utility_device_id", "iot_devices", ["utility_device_id"])
    _create_index_once("ix_iot_devices_status", "iot_devices", ["status"])

    if context.is_offline_mode() or not _has_table("iot_channels"):
        op.create_table(
            "iot_channels",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_id", UUID, nullable=False),
            sa.Column("channel_code", sa.String(120), nullable=False),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("unit", sa.String(30), nullable=True),
            sa.Column("value_type", _enum("iotchannelvaluetype", "NUMERIC", "BOOLEAN", "STRING", "STATE"), nullable=False, server_default="NUMERIC"),
            sa.Column("min_valid_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("max_valid_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("normal_min_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("normal_max_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("sampling_interval_seconds", sa.Integer(), nullable=True),
            sa.Column("aggregation_method", _enum("iotaggregationmethod", "AVG", "MIN", "MAX", "SUM", "LAST", "COUNT"), nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=True),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("utility_device_id", UUID, nullable=True),
            sa.Column("production_order_link_mode", sa.String(50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata_json", JSONB, nullable=True),
            *_timestamps(timezone=True),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("device_id", "channel_code", name="uq_iot_channels_device_channel"),
        )

    _create_index_once("ix_iot_channels_device_id", "iot_channels", ["device_id"])
    _create_index_once("ix_iot_channels_metric_name", "iot_channels", ["metric_name"])
    _create_index_once("ix_iot_channels_machine_id", "iot_channels", ["machine_id"])
    _create_index_once("ix_iot_channels_utility_device_id", "iot_channels", ["utility_device_id"])

    if context.is_offline_mode() or not _has_table("iot_ingest_messages"):
        op.create_table(
            "iot_ingest_messages",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_id", UUID, nullable=True),
            sa.Column("message_id", sa.String(255), nullable=True),
            sa.Column("source", sa.String(50), nullable=True),
            sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", _enum("iotingeststatus", "ACCEPTED", "DUPLICATE", "REJECTED", "PARTIAL"), nullable=False, server_default="ACCEPTED"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("raw_payload_hash", sa.String(128), nullable=True),
            *_timestamps(timezone=True),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("device_id", "message_id", name="uq_iot_ingest_device_message"),
        )

    _create_index_once("ix_iot_ingest_messages_device_id", "iot_ingest_messages", ["device_id"])
    _create_index_once("ix_iot_ingest_messages_message_id", "iot_ingest_messages", ["message_id"])
    _create_index_once("ix_iot_ingest_messages_received_at", "iot_ingest_messages", ["received_at"])


def _create_iot_fact_tables() -> None:
    if context.is_offline_mode() or not _has_table("iot_sensor_data"):
        op.create_table(
            "iot_sensor_data",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_id", UUID, nullable=True),
            sa.Column("channel_id", UUID, nullable=True),
            sa.Column("ingest_message_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("machine_name", sa.String(200), nullable=True),
            sa.Column("utility_device_id", UUID, nullable=True),
            sa.Column("sensor_id", sa.String(100), nullable=True),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("value", sa.Numeric(18, 6), nullable=False),
            sa.Column("unit", sa.String(30), nullable=True),
            sa.Column("quality_flag", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source", sa.String(50), nullable=True),
            sa.Column("production_order_id", sa.String(100), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["channel_id"], ["iot_channels.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["ingest_message_id"], ["iot_ingest_messages.id"], ondelete="SET NULL"),
        )
    else:
        _add_column_once("iot_sensor_data", sa.Column("device_id", UUID, nullable=True))
        _add_column_once("iot_sensor_data", sa.Column("channel_id", UUID, nullable=True))
        _add_column_once("iot_sensor_data", sa.Column("ingest_message_id", UUID, nullable=True))
        _add_column_once("iot_sensor_data", sa.Column("machine_uuid", UUID, nullable=True))
        _add_column_once("iot_sensor_data", sa.Column("utility_device_id", UUID, nullable=True))

    _create_index_once("ix_iot_sensor_data_machine_id", "iot_sensor_data", ["machine_id"])
    _create_index_once("ix_iot_sensor_data_sensor_id", "iot_sensor_data", ["sensor_id"])
    _create_index_once("ix_iot_sensor_data_metric_name", "iot_sensor_data", ["metric_name"])
    _create_index_once("ix_iot_sensor_data_production_order_id", "iot_sensor_data", ["production_order_id"])
    _create_index_once("ix_iot_sensor_data_recorded_at", "iot_sensor_data", ["recorded_at"])
    _create_index_once("ix_iot_sensor_data_device_id", "iot_sensor_data", ["device_id"])
    _create_index_once("ix_iot_sensor_data_channel_id", "iot_sensor_data", ["channel_id"])
    _create_index_once("ix_iot_sensor_data_machine_metric_time", "iot_sensor_data", ["machine_id", "metric_name", "recorded_at"])

    if context.is_offline_mode() or not _has_table("iot_machine_states"):
        op.create_table(
            "iot_machine_states",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("machine_name", sa.String(200), nullable=True),
            sa.Column("state", _enum("machinestate", "RUNNING", "IDLE", "DOWN", "FAULT", "MAINTENANCE", "OFFLINE"), nullable=False),
            sa.Column("previous_state", _enum("machinestate", "RUNNING", "IDLE", "DOWN", "FAULT", "MAINTENANCE", "OFFLINE"), nullable=True),
            sa.Column("trigger_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("trigger_metric", sa.String(100), nullable=True),
            sa.Column("trigger_source", sa.String(100), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("changed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="SET NULL"),
        )
    else:
        _add_column_once("iot_machine_states", sa.Column("device_id", UUID, nullable=True))
        _add_column_once("iot_machine_states", sa.Column("machine_uuid", UUID, nullable=True))

    _create_index_once("ix_iot_machine_states_machine_id", "iot_machine_states", ["machine_id"])
    _create_index_once("ix_iot_machine_states_changed_at", "iot_machine_states", ["changed_at"])
    _create_index_once("ix_iot_machine_states_device_id", "iot_machine_states", ["device_id"])

    if context.is_offline_mode() or not _has_table("iot_alert_thresholds"):
        op.create_table(
            "iot_alert_thresholds",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("device_id", UUID, nullable=True),
            sa.Column("channel_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("min_threshold", sa.Numeric(18, 6), nullable=True),
            sa.Column("max_threshold", sa.Numeric(18, 6), nullable=True),
            sa.Column("severity", _enum("iot_alertseverity", "INFO", "WARNING", "CRITICAL"), nullable=False, server_default="WARNING"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["channel_id"], ["iot_channels.id"], ondelete="SET NULL"),
        )
    else:
        _add_column_once("iot_alert_thresholds", sa.Column("device_id", UUID, nullable=True))
        _add_column_once("iot_alert_thresholds", sa.Column("channel_id", UUID, nullable=True))
        _add_column_once("iot_alert_thresholds", sa.Column("machine_uuid", UUID, nullable=True))

    _create_index_once("ix_iot_alert_thresholds_machine_id", "iot_alert_thresholds", ["machine_id"])
    _create_index_once("ix_iot_alert_thresholds_device_id", "iot_alert_thresholds", ["device_id"])
    _create_index_once("ix_iot_alert_thresholds_channel_id", "iot_alert_thresholds", ["channel_id"])

    if context.is_offline_mode() or not _has_table("iot_alerts"):
        op.create_table(
            "iot_alerts",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("threshold_id", UUID, nullable=True),
            sa.Column("device_id", UUID, nullable=True),
            sa.Column("channel_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_uuid", UUID, nullable=True),
            sa.Column("machine_name", sa.String(200), nullable=True),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("triggered_value", sa.Numeric(18, 6), nullable=False),
            sa.Column("threshold_min", sa.Numeric(18, 6), nullable=True),
            sa.Column("threshold_max", sa.Numeric(18, 6), nullable=True),
            sa.Column("severity", _enum("iot_alertseverity", "INFO", "WARNING", "CRITICAL"), nullable=False, server_default="WARNING"),
            sa.Column("status", _enum("alertstatus", "OPEN", "ACKNOWLEDGED", "RESOLVED"), nullable=False, server_default="OPEN"),
            sa.Column("acknowledged_by", sa.String(200), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("triggered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["threshold_id"], ["iot_alert_thresholds.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["channel_id"], ["iot_channels.id"], ondelete="SET NULL"),
        )
    else:
        _add_column_once("iot_alerts", sa.Column("device_id", UUID, nullable=True))
        _add_column_once("iot_alerts", sa.Column("channel_id", UUID, nullable=True))
        _add_column_once("iot_alerts", sa.Column("machine_uuid", UUID, nullable=True))

    _create_index_once("ix_iot_alerts_machine_id", "iot_alerts", ["machine_id"])
    _create_index_once("ix_iot_alerts_status", "iot_alerts", ["status"])
    _create_index_once("ix_iot_alerts_triggered_at", "iot_alerts", ["triggered_at"])
    _create_index_once("ix_iot_alerts_device_id", "iot_alerts", ["device_id"])
    _create_index_once("ix_iot_alerts_channel_id", "iot_alerts", ["channel_id"])


def _create_machine_events() -> None:
    if context.is_offline_mode() or not _has_table("machine_events"):
        op.create_table(
            "machine_events",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_name", sa.String(255), nullable=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("value_str", sa.String(200), nullable=True),
            sa.Column("value_numeric", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("production_order_id", UUID, nullable=True),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw_payload", sa.Text(), nullable=True),
            *_timestamps(timezone=True),
            sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"], ondelete="SET NULL"),
        )

    _create_index_once("ix_machine_events_machine_id", "machine_events", ["machine_id"])
    _create_index_once("ix_machine_events_production_order_id", "machine_events", ["production_order_id"])
    _create_index_once("ix_machine_events_received_at", "machine_events", ["received_at"])
    _create_index_once("ix_machine_events_machine_type_time", "machine_events", ["machine_id", "event_type", "received_at"])


def upgrade() -> None:
    _create_enums()
    _create_registry_tables()
    _create_iot_fact_tables()
    _create_machine_events()


def downgrade() -> None:
    for table_name in (
        "machine_events",
        "iot_alerts",
        "iot_alert_thresholds",
        "iot_machine_states",
        "iot_sensor_data",
        "iot_ingest_messages",
        "iot_channels",
        "iot_devices",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)

    for enum_name in (
        "iotingeststatus",
        "iotaggregationmethod",
        "iotchannelvaluetype",
        "iotdevicestatus",
        "iotdevicetype",
        "iotdeviceprotocol",
        "alertstatus",
        "iot_alertseverity",
        "machinestate",
    ):
        _drop_enum(enum_name)
