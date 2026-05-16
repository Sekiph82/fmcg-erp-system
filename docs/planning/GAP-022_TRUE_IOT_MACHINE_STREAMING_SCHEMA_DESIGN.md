# GAP-022 True IoT / Machine Streaming Schema Design

## Summary

GAP-022 should evolve the current HTTP-ingest IoT prototype into a controlled factory telemetry foundation without replacing machine-ops or utility-management. The correct next implementation slice is to reconcile ownership, permissions, migration coverage, and device identity before adding live MQTT/OPC-UA workers.

## Design Goals

- Preserve existing `/iot` API and `/dashboard/iot` page paths.
- Preserve existing machine-ops and utility-management models.
- Add secure device/channel identity rather than letting arbitrary strings be the long-term integration key.
- Keep HTTP ingest backward compatible while preparing for MQTT, OPC-UA, SCADA, and edge gateway bridges.
- Connect telemetry to machines, utility devices, production lines, work centers, production orders, and maintenance/utility alarms.
- Avoid introducing a separate streaming stack until the schema and security contracts are clear.

## Current Model Baseline

The current dedicated IoT model has:

- `SensorDataPoint`
- `MachineStateEvent`
- `IoTAlertThreshold`
- `IoTAlert`

The integrations model separately has:

- `MachineEvent`

Machine operations has:

- `Machine`
- `MachineRuntimeLog`
- `MachinePerformanceSnapshot`
- `DowntimeIntelligence`
- related operator, assignment, labor, review, and AI recommendation tables

Utility management has:

- `UtilityDevice`
- `UtilityReading`
- `UtilityTransaction`
- utility alarm and KPI structures
- IOT and SCADA source concepts

These should be reused.

## Module Ownership Design

Promote `iot` from loose endpoint-route ownership to a module-owned route:

| Module Key | Label | Route Prefix | Import Path |
|---|---|---|---|
| `iot` | IoT / Machine Streaming | `/iot` | `app.api.v1.endpoints.iot` |

Keep `machine_operator` and `utility_management` as their own existing surfaces. GAP-022 should not collapse those modules into `iot`.

## Permission Design

Recommended permissions:

- `iot.view` for dashboards, latest readings, summaries, states, thresholds, alerts, and histories
- `iot.ingest` for internal bridge or device-gateway ingestion contracts
- `iot.configure` for thresholds, device/channel configuration, and bridge configuration
- `iot.acknowledge` for alert acknowledgment and operational response
- `iot.export` for telemetry/report exports
- `iot.admin` for device credential lifecycle and dangerous configuration

Do not protect IoT with broad `utility_management.view` or generic `get_current_user` alone.

Machine-ops permissions should be handled in its own hardening slice or as part of GAP-022 if the implementation touches those endpoints. At minimum, machine-ops should not remain unauthenticated for machine master, runtime, labor, downtime, costing, assignment, and AI mutations.

## Proposed Device and Channel Registry

Add a small registry before adding bridge workers:

### `iot_devices`

Recommended fields:

- `id`
- `device_code`
- `name`
- `protocol`
- `device_type`
- `status`
- `gateway_id`
- `machine_id`
- `utility_device_id`
- `work_center_id`
- `line_id`
- `department`
- `company_id`
- `branch_id`
- `credential_hash`
- `last_seen_at`
- `last_message_id`
- `metadata_json`
- `created_at`
- `updated_at`

Recommended enums:

- protocol: `HTTP`, `MQTT`, `OPC_UA`, `SCADA`, `MODBUS`, `MANUAL`, `API`
- device type: `PLC`, `SENSOR`, `METER`, `GATEWAY`, `EDGE_AGENT`, `SCADA_TAG`, `OTHER`
- status: `ACTIVE`, `DISABLED`, `MAINTENANCE`, `RETIRED`

### `iot_channels`

Recommended fields:

- `id`
- `device_id`
- `channel_code`
- `metric_name`
- `unit`
- `value_type`
- `min_valid_value`
- `max_valid_value`
- `normal_min_value`
- `normal_max_value`
- `sampling_interval_seconds`
- `aggregation_method`
- `machine_id`
- `utility_device_id`
- `production_order_link_mode`
- `is_active`
- `metadata_json`
- `created_at`
- `updated_at`

This keeps metric/unit/range validation out of ad hoc endpoint code.

### `iot_ingest_messages`

Recommended as a lightweight idempotency/audit table:

- `id`
- `device_id`
- `message_id`
- `source`
- `received_at`
- `record_count`
- `status`
- `error_message`
- `raw_payload_hash`

Use a uniqueness constraint on `(device_id, message_id)` where `message_id` is present.

## Existing Table Reconciliation

Keep these tables:

- `iot_sensor_data`
- `iot_machine_states`
- `iot_alert_thresholds`
- `iot_alerts`

Add nullable FKs or soft links only after migration ownership is verified:

- `iot_sensor_data.device_id`
- `iot_sensor_data.channel_id`
- `iot_sensor_data.utility_device_id`
- `iot_sensor_data.machine_uuid`
- `iot_machine_states.device_id`
- `iot_alert_thresholds.channel_id`
- `iot_alerts.device_id`
- `iot_alerts.channel_id`

Retain string `machine_id` initially for backward compatibility with existing dashboard data and manual ingest.

## Integration Event Reconciliation

The integrations `MachineEvent` path and the dedicated `/iot` path overlap.

Recommended first decision:

- Keep `MachineEvent` as a generic integration event log.
- Treat `iot_sensor_data` and `iot_machine_states` as normalized telemetry/state facts.
- For future bridge workers, write raw event metadata to `machine_events` only when useful, and write normalized facts to `iot_*` tables.

Do not create a third telemetry model.

## API Design

Keep current read endpoints and add permission dependencies:

- dashboard/latest/summary/current states/state history/alerts/threshold list: `iot.view`
- threshold create/update/deactivate: `iot.configure`
- alert acknowledge/resolve: `iot.acknowledge`
- data export: `iot.export`

Device ingestion should not depend on a human user session. Instead:

- accept device credentials or signed gateway requests
- verify active device/channel status
- validate metric names, units, ranges, and timestamps
- support idempotency by message id
- reject oversized batches consistently
- preserve the existing `/iot/ingest` and `/iot/ingest/batch` paths where possible

## Frontend Design

Keep `/dashboard/iot` as the first screen. Add guards:

- page view: `iot.view`
- manual ingest/testing panel: `iot.ingest` or `iot.configure`
- threshold creation: `iot.configure`
- alert acknowledgment: `iot.acknowledge`

Keep the IoT nav under Utility Management for now or move it to an Operations/Factory Intelligence group only if the project has an established placement. The guard should become `iot.view`.

## Streaming and Bridge Design

Do not add an MQTT broker, OPC-UA worker, or WebSocket stream in GAP-022C unless the repo already has a worker framework ready.

Recommended future worker sequence:

- HTTP gateway ingest first
- MQTT subscriber bridge as a background worker
- OPC-UA polling/subscription bridge
- dashboard polling optimization
- SSE/WebSocket push after data contracts stabilize

## Retention and Rollup Design

High-volume telemetry needs a retention decision before production use.

Recommended first slice:

- keep raw readings for a configurable period
- add hourly/daily rollup tables later if dashboard queries become heavy
- avoid deleting data in migrations
- document future retention jobs rather than implementing destructive purges now

## Migration Strategy for GAP-022C

GAP-022C should first inspect Alembic ownership for:

- `iot_sensor_data`
- `iot_machine_states`
- `iot_alert_thresholds`
- `iot_alerts`
- `machine_events`
- `machines`
- `machine_runtime_logs`
- `machine_performance_snapshots`
- `utility_devices`
- `utility_readings`

If IoT tables are missing from Alembic ownership, add an additive reconciliation migration.

If the core IoT tables already exist in migrations, add only the smallest safe registry tables and nullable linkage fields needed for secure ingest.

## Test Strategy

GAP-022J should cover:

- `iot` module registry ownership
- seed permission tuples and conservative role grants
- endpoint source permissions for view/configure/acknowledge
- ingest route security contract
- nav/page guard using `iot.view`
- migration ownership of IoT/device registry tables
- endpoint import smoke

## Acceptance Criteria for GAP-022B

GAP-022B is complete when this design documents module ownership, permission families, device/channel registry direction, existing-table reconciliation, integration event boundary, API/ingest security, frontend guard direction, streaming bridge boundaries, retention strategy, migration strategy, and test strategy.
