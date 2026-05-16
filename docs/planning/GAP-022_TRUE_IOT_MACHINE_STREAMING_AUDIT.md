# GAP-022 True IoT / Machine Streaming Audit

## Summary

GAP-022 is partially implemented, but the current implementation is closer to HTTP-based IoT ingestion plus machine-operation dashboards than true streaming infrastructure. The repository already has useful foundations for sensor readings, machine state events, alert thresholds, integration event capture, machine master/runtime/OEE, and utility meters/sensors.

The main missing pieces are production-grade device identity, signed ingestion, MQTT/OPC-UA/SCADA bridge workers, streaming transport, idempotency, normalized device registry linkage, high-volume time-series strategy, module ownership, dedicated permissions, and a single coherent model between the `/iot` endpoint and the integrations IoT placeholder.

## Business Importance

True IoT and machine streaming is a future-facing but important ERP/MES capability. In a factory setting it should support real-time line health, machine state transitions, utility consumption, downtime detection, predictive maintenance, quality condition monitoring, production-order correlation, and alert escalation.

The current code gives a useful operator-facing prototype. It is not yet enough for trusted plant-floor streaming because unauthenticated ingest paths and placeholder bridge comments need to become controlled device-facing interfaces.

## Files Inspected

- `backend/app/models/iot.py`
- `backend/app/api/v1/endpoints/iot.py`
- `backend/app/services/iot_service.py`
- `backend/app/models/integrations.py`
- `backend/app/api/v1/endpoints/integrations.py`
- `backend/app/core/integration_capabilities.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/app/models/machine_operator.py`
- `backend/app/api/v1/endpoints/machine_operator.py`
- `backend/app/services/machine_operator_service.py`
- `backend/app/models/utility_management.py`
- `backend/app/api/v1/endpoints/utility_management.py`
- `backend/app/api/v1/endpoints/utility_integration.py`
- `backend/alembic/versions/*` search results for IoT and machine tables
- `frontend/src/app/dashboard/iot/page.tsx`
- `frontend/src/lib/integrations.ts`
- `frontend/src/app/dashboard/machine-ops/*`
- `frontend/src/components/nav-config.tsx`
- `backend/tests/test_gap006_integration_capabilities.py`

## Existing Dedicated IoT Coverage

`backend/app/models/iot.py` defines:

- `SensorDataPoint`
- `MachineStateEvent`
- `IoTAlertThreshold`
- `IoTAlert`
- `MachineState`
- `AlertSeverity`
- `AlertStatus`

These models cover basic time-stamped sensor values, machine state transitions, threshold configuration, and triggered alerts.

`backend/app/api/v1/endpoints/iot.py` exposes:

- `POST /ingest`
- `POST /ingest/batch`
- `GET /sensors/latest`
- `GET /sensors/summary`
- `POST /machines/state`
- `GET /machines/current-states`
- `GET /machines/state-history`
- `POST /thresholds`
- `GET /thresholds`
- `GET /alerts`
- `POST /alerts/{alert_id}/acknowledge`
- `GET /dashboard`

The endpoint supports manual or HTTP-based sensor ingestion, batch ingestion, latest readings, summary aggregation, state recording, current state lookup, state history, threshold creation/listing, alert listing, alert acknowledgment, and dashboard KPIs.

## Existing Integrations IoT Placeholder

There is a separate IoT path inside the integrations module.

`backend/app/models/integrations.py` defines `MachineEvent` on `machine_events`.

`backend/app/services/iot_service.py` is explicitly labeled as a placeholder service. It records machine events and provides recent event and machine status summaries.

`backend/app/api/v1/endpoints/integrations.py` exposes:

- `POST /integrations/iot/events`
- `GET /integrations/iot/events`
- `GET /integrations/iot/machines`

This path stores generic machine events separately from `iot_sensor_data` and `iot_machine_states`.

`backend/app/core/integration_capabilities.py` marks provider `IOT` as `STUB_ONLY`, simulation-supported, and notes that the current service is a placeholder for a future MQTT/streaming bridge.

## Existing Machine Operations Coverage

`backend/app/models/machine_operator.py` provides a much richer MES-adjacent machine and operator model:

- `Machine`
- `OperatorProfile`
- `ProductionTeam`
- `TeamMember`
- `OperatorSkillCert`
- `WorkOrderAssignment`
- `AssignmentHistory`
- `MachineRuntimeLog`
- `LaborTimeLog`
- `MachinePerformanceSnapshot`
- `DowntimeIntelligence`
- `SupervisorReview`
- `MOAIRecommendation`

The frontend under `frontend/src/app/dashboard/machine-ops/*` covers machine master, operators, teams, runtime logs, performance, downtime, costing, certifications, and assignment board.

This is operationally useful but separate from the dedicated `iot` models. Machine master IDs are UUIDs in machine-ops, while IoT readings currently use string `machine_id` fields.

## Existing Utility Sensor and Meter Coverage

Utility Management already has a serious meter/sensor foundation.

`backend/app/models/utility_management.py` includes device and reading concepts such as `UtilityDevice`, `UtilityReading`, `SourceMethod.IOT`, `ReadingSource.IOT`, related machine fields, utility transactions with IOT reference type, and sensor-like utility records for electricity, water, compressed air, steam, solar, wastewater, and treatment.

The frontend has utility pages for meters/sensors, readings, alarm center, KPI center, machine utility, integration hub, and the IoT dashboard link.

This means GAP-022 should not invent a new isolated plant device registry. It should connect IoT devices to the existing utility and machine foundations.

## Frontend Coverage

`frontend/src/app/dashboard/iot/page.tsx` provides an IoT dashboard with:

- dashboard KPIs
- current machine states
- open alerts
- sensor summaries
- manual sensor ingest
- threshold creation
- refresh behavior
- guidance text for HTTP, MQTT bridge, and OPC-UA bridge approaches

The page uses direct `fetch` calls rather than a typed frontend API library.

Navigation exposes `IoT Machine Data` under Utility Management and currently gates it with `utility_management.view`.

Machine operations pages provide a broader MES dashboard and refetch some data periodically, but they are not wired to true IoT streams.

## Current Permission and Security Findings

The dedicated `/iot` endpoint has mixed protection:

- `POST /iot/ingest` has no auth.
- `POST /iot/ingest/batch` has no auth.
- `POST /iot/machines/state` has no auth.
- read/dashboard/threshold/alert endpoints use `get_current_user`, not dedicated `iot.*` permissions.

The integrations IoT event ingest path also has no auth and comments that machine credentials are a placeholder.

Seed data currently has only `iot.manage`; no full `iot.view`, `iot.ingest`, `iot.configure`, `iot.acknowledge`, `iot.export`, or `iot.admin` permission family exists.

`module_registry.py` lists `iot` as an `EndpointRouteDefinition`, not a `ModuleDefinition`.

Machine-ops endpoints appear to have no auth or permission dependencies at all, despite exposing machine master, runtime, labor, costing, downtime, AI, and assignment mutation endpoints.

## Migration Ownership Findings

Searches found references to utility IOT enums and machine utility tables in migrations.

Searches did not find clear Alembic ownership for these dedicated IoT tables:

- `iot_sensor_data`
- `iot_machine_states`
- `iot_alert_thresholds`
- `iot_alerts`

Searches found the `machine_events` model, but no clear migration ownership for that table in the inspected search output.

Machine-ops tables should also be verified in GAP-022C or a related hardening gap because the model is substantial and may have migration ownership gaps.

## Current Architecture Mismatches

- Dedicated IoT readings live in `iot_sensor_data`; integrations IoT events live in `machine_events`.
- Machine master in machine-ops uses UUID `machines.id`; IoT readings use string `machine_id`.
- Utility devices and readings already support IOT/SCADA concepts, but `/iot` readings are not directly linked to `utility_devices`.
- Thresholds are per string machine/metric, not per registered device/sensor/channel.
- Alerts stay inside IoT and are not yet escalated into maintenance work orders or utility alarm events.
- Frontend IoT page can manually ingest data without a clear permission boundary.
- Integration capability status correctly says `STUB_ONLY`, but the `/iot` page presents bridge guidance that may look more production-ready than the backend actually is.

## Missing Pieces

- Device registry for PLC/SCADA/MQTT/HTTP devices with identity, credential hash, protocol, tenant/company scope, and active/disabled state.
- Signed or credential-authenticated device ingest.
- Replay protection and idempotency keys for telemetry messages.
- MQTT bridge worker or documented bridge contract.
- OPC-UA/SCADA bridge worker or documented bridge contract.
- WebSocket/SSE or broker-backed real-time push to dashboards.
- High-volume time-series storage strategy, retention policy, and rollups.
- Link from IoT sensor channels to machine master, utility devices, production lines, work centers, and production orders.
- Dedicated `iot` module ownership and permission family.
- Alert escalation into maintenance, quality, utility alarms, and production downtime.
- Validation for metric names, units, value ranges, and bad-quality data handling.
- Backpressure/batch-size controls beyond a simple batch limit.
- Import/export/reporting and audit trail for IoT configuration changes.

## Recommended GAP-022B Design Direction

GAP-022B should design a narrow production-safe IoT foundation rather than a full streaming platform rewrite.

Recommended first slice:

- promote `iot` into a `ModuleDefinition`
- add dedicated permissions such as `iot.view`, `iot.ingest`, `iot.configure`, `iot.acknowledge`, `iot.export`, and `iot.admin`
- preserve existing `/iot` dashboard routes
- add a device/channel registry that can link to machine-ops `machines`, utility devices, lines, and work centers
- add secure device-ingest authentication without exposing user credentials to machines
- reconcile the dedicated `/iot` model with the integrations `machine_events` placeholder
- keep MQTT/OPC-UA bridge implementation as a later worker unless the migration/service foundation is ready
- verify migration ownership before changing models

## Risks

- Current unauthenticated ingest paths can be abused if exposed beyond a trusted internal network.
- String machine identifiers can drift away from machine master records.
- Duplicate event models can cause conflicting dashboards and future migrations.
- Lack of retention/rollup strategy can make sensor tables grow without bounds.
- Alerts are not yet connected to maintenance or production downtime workflows.
- Machine-ops mutation endpoints appear under-protected and should not be treated as production-safe.

## Acceptance Criteria for GAP-022 Completion

GAP-022 should be considered complete only when:

- IoT module ownership and permissions are explicit.
- Device ingest is authenticated or otherwise securely constrained.
- Current HTTP ingest remains backward compatible or has a documented migration path.
- Sensor data, machine events, utility devices, and machine master records have a coherent linkage strategy.
- Migration ownership for IoT and machine event tables is verified or reconciled.
- Read and mutation endpoints use dedicated permissions.
- Frontend IoT and machine views use dedicated guards.
- Tests cover registry permissions, ingest security contract, endpoint imports, and frontend nav/page guards.
