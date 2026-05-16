# GAP-022 True IoT / Machine Streaming — Implementation Notes

## Summary

GAP-022 promoted the IoT module from a loose endpoint route into a fully owned `ModuleDefinition`, added a complete `iot.*` permission family, hardened all IoT API endpoints with dedicated permission guards, added a device registry ORM layer, aligned the IoT frontend page with permission guards, and reconciled migration ownership for all IoT and machine event tables.

## Changes Made

### GAP-022C: Migration

- Added `backend/alembic/versions/20260516_0020_iot_machine_streaming_reconciliation.py`.
- Migration creates (additive, idempotent):
  - `iot_devices` — device registry (PLC, sensor, meter, gateway, SCADA tag)
  - `iot_channels` — per-device metric channel registry
  - `iot_ingest_messages` — idempotency/audit log per ingest message
  - `iot_sensor_data` — adds nullable FK columns `device_id`, `channel_id`, `ingest_message_id`, `machine_uuid`, `utility_device_id` if table already exists
  - `iot_machine_states` — adds nullable FK columns `device_id`, `machine_uuid` if table already exists
  - `iot_alert_thresholds` — adds nullable FK columns `device_id`, `channel_id`, `machine_uuid` if table already exists
  - `iot_alerts` — adds nullable FK columns `device_id`, `channel_id`, `machine_uuid` if table already exists
  - `machine_events` — generic integration machine event log (idempotent create)
- Alembic single head after migration: `20260516_0020`.

### GAP-022D: ORM Models

- Updated `backend/app/models/iot.py` with new classes:
  - `IoTDevice` → `iot_devices`
  - `IoTChannel` → `iot_channels`
  - `IoTIngestMessage` → `iot_ingest_messages`
  - Updated `SensorDataPoint`, `MachineStateEvent`, `IoTAlertThreshold`, `IoTAlert` with new FK columns matching migration.
- Added enum classes: `IoTDeviceProtocol`, `IoTDeviceType`, `IoTDeviceStatus`, `IoTChannelValueType`, `IoTAggregationMethod`, `IoTIngestStatus`.
- `MachineEvent` in `backend/app/models/integrations.py` unchanged — still maps to `machine_events`.

### GAP-022G: API Endpoints

- Hardened all endpoints in `backend/app/api/v1/endpoints/iot.py` with `require_permission`:
  - `POST /ingest` → `iot.ingest`
  - `POST /ingest/batch` → `iot.ingest`
  - `GET /sensors/latest` → `iot.view`
  - `GET /sensors/summary` → `iot.view`
  - `POST /machines/state` → `iot.ingest`
  - `GET /machines/current-states` → `iot.view`
  - `GET /machines/state-history` → `iot.view`
  - `POST /thresholds` → `iot.configure`
  - `GET /thresholds` → `iot.view`
  - `GET /alerts` → `iot.view`
  - `POST /alerts/{id}/acknowledge` → `iot.acknowledge`
  - `GET /devices` → `iot.view` (new — device registry list)
  - `GET /devices/{id}/channels` → `iot.view` (new — channel list)
  - `GET /dashboard` → `iot.view` (adds `registered_devices` count)

### GAP-022H: Frontend

- Added `RequirePermission permission="iot.view"` wrapper to `frontend/src/app/dashboard/iot/page.tsx`.
- Added `PermissionGuard permission="iot.ingest"` around manual sensor ingest panel.
- Added `PermissionGuard permission="iot.configure"` around alert threshold creation panel.
- Updated `frontend/src/components/nav-config.tsx`: changed IoT nav entry guard from `utility_management.view` to `iot.view`.

### GAP-022I: Permissions and Roles

- Promoted `iot` from `EndpointRouteDefinition` to `ModuleDefinition` in `backend/app/core/module_registry.py`.
- Permission actions: `view`, `ingest`, `configure`, `acknowledge`, `export`, `admin`.
- Replaced single `iot.manage` seed tuple with full family in `backend/app/db/seed.py`:
  - `iot.view` — visible to all authorized users on mobile
  - `iot.ingest` — for bridge/gateway ingest
  - `iot.configure` — threshold and device configuration
  - `iot.acknowledge` — alert acknowledgment
  - `iot.export` — telemetry/report exports
  - `iot.admin` — device credential lifecycle
- Role grants:
  - `owner`: wildcard (all permissions auto-included)
  - `admin`: full IoT access (`view`, `ingest`, `configure`, `acknowledge`, `export`, `admin`)
  - `cto`: `view`, `configure`, `acknowledge`, `export`, `admin`
  - `coo`: `view`, `acknowledge`, `export`
  - `factory_manager`: `view`, `acknowledge`
  - `maintenance_technician`: `view`

### GAP-022J: Tests

- Added `backend/tests/test_gap022_iot_machine_streaming.py` with 20 focused contract tests covering:
  - Module registry promotion
  - Permission tuple seeds
  - Role grant contracts
  - Endpoint source permission guards
  - Frontend guard presence
  - Nav guard correctness
  - Migration file existence and content
  - ORM model imports and table name contracts

## Limitations and Deferred Work

- **Live DB migration not run**: Docker daemon unavailable. Offline SQL rendering was used for verification in GAP-022C.
- **MQTT / OPC-UA / SCADA bridge workers**: Not implemented. These require a background worker framework and are deferred to a future GAP.
- **Device credential authentication**: `credential_hash` column exists in `iot_devices` ORM and migration. Actual hash verification at ingest time is deferred — `iot.ingest` permission is the current ingest gate.
- **Idempotency key enforcement**: `iot_ingest_messages` table exists but is not yet used in the ingest endpoint logic. Deferred.
- **Alert escalation to maintenance/quality**: IoT alerts are not yet forwarded to maintenance work orders or utility alarms. Deferred.
- **Time-series retention and rollup**: Raw sensor data in `iot_sensor_data` has no automated retention policy. Deferred.
- **Machine-ops endpoint hardening**: Machine-ops endpoints remain without dedicated permissions. This was identified as a risk in the audit but was out of scope for GAP-022.

## Checks Run

- `py_compile app/models/iot.py` — passed
- `configure_mappers` for iot models — passed (unrelated pre-existing SA warnings present)
- `py_compile app/api/v1/endpoints/iot.py` — see GAP-022L
- `py_compile app/core/module_registry.py app/db/seed.py` — see GAP-022L
- `alembic heads` — single head `20260516_0020`
- Frontend type-check — see GAP-022L
- 20 focused pytest tests — see GAP-022L
