# GAP-008 Warehouse Management Depth Implementation Notes

## Status

GAP-008A through GAP-008K are complete as of 2026-05-14.

This is a controlled WMS depth slice. It does not replace the existing inventory/WMS architecture. It extends the current warehouse zones, storage locations, stock, movements, putaway, count, picking, packing, and replenishment foundation with handling-unit, pick-wave, location-aware movement, access-hint, and scoped-action support.

## Implemented Scope

### Migration

Added `backend/alembic/versions/20260514_0020_wms_depth_reconciliation.py`.

The migration reconciles WMS depth schema ownership by adding or verifying:

- `wms_handling_units`
- `wms_handling_unit_items`
- `wms_pick_waves`
- `wms_picking_tasks`
- `wms_packing_records`
- `wms_replenishment_tasks`
- `wms_picking_tasks.wave_id`
- `stock_movements.source_location_id`
- `stock_movements.destination_location_id`
- `stock_movements.source_handling_unit_id`
- `stock_movements.destination_handling_unit_id`

Live development PostgreSQL verification succeeded. Alembic current is `20260514_0020 (head)`.

### Backend Models

Updated:

- `backend/app/models/wms.py`
- `backend/app/models/inventory.py`

Added WMS ORM support for:

- handling units
- handling-unit items
- pick waves
- picking-task wave ownership
- stock movement source/destination locations
- stock movement source/destination handling units

### Schemas

Updated:

- `backend/app/schemas/wms.py`
- `backend/app/schemas/inventory.py`

Added request/response support for:

- `WMSAccessHint`
- handling units
- handling-unit items
- pick waves
- picking-task wave fields
- inventory movement location/HU fields
- stock and WMS response access hints

### Services

Updated `backend/app/services/wms_service.py`.

Added:

- `build_wms_access_hint`
- `ensure_wms_action_allowed`
- `can_change_wms_status`
- handling-unit create/update helpers
- pick-wave create/update helpers
- location and warehouse validation helpers

The service preserves the ERP-wide access-control model from GAP-SEC-001: broad view is separate from mutation scope. Warehouse mutation remains controlled through inventory warehouse-scoped permissions such as `inventory.receive_own_scope`, `inventory.dispatch_own_scope`, `inventory.transfer_own_scope`, `inventory.adjust_own_scope`, and `inventory.edit_own_scope`.

### API

Updated `backend/app/api/v1/endpoints/wms.py`.

Added endpoints:

- `GET /api/v1/wms/handling-units`
- `POST /api/v1/wms/handling-units`
- `GET /api/v1/wms/handling-units/{handling_unit_id}`
- `PATCH /api/v1/wms/handling-units/{handling_unit_id}`
- `GET /api/v1/wms/pick-waves`
- `POST /api/v1/wms/pick-waves`
- `GET /api/v1/wms/pick-waves/{wave_id}`
- `PATCH /api/v1/wms/pick-waves/{wave_id}`

Also threaded access hints and scoped guards through WMS execution surfaces:

- zones
- storage locations
- putaway
- quarantine/release
- FEFO suggestions
- stock counts
- picking tasks
- packing records
- replenishment tasks

### Frontend

Updated:

- `frontend/src/lib/wms.ts`
- `frontend/src/app/dashboard/wms/page.tsx`

Added:

- WMS access-hint types
- handling-unit types and API client methods
- pick-wave types and API client methods
- WMS dashboard tabs for handling units and pick waves
- visible `View Only` / `Editable` access badges based on backend access hints

### Roles And Permissions

Updated `backend/app/db/seed.py`.

Added `wms.view` to the Warehouse Manager role. This lets warehouse managers see WMS navigation while mutation remains constrained by assigned warehouse scopes through inventory permissions.

No broad edit permission was added to the Warehouse Manager role.

## Verification

Commands run:

- `cd backend; .\venv\Scripts\python.exe -m py_compile alembic\versions\20260514_0020_wms_depth_reconciliation.py`
- `cd backend; .\venv\Scripts\python.exe -m alembic heads`
- `cd backend; .\venv\Scripts\python.exe -m alembic history -r 20260514_0010:20260514_0020`
- `cd backend; .\venv\Scripts\python.exe -m alembic upgrade 20260514_0010:20260514_0020 --sql`
- `docker compose --env-file .env.development exec -T backend python -m alembic upgrade head`
- `docker compose --env-file .env.development exec -T backend python -m alembic current`
- live async SQLAlchemy schema verification for WMS tables and movement columns
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\models\wms.py app\models\inventory.py`
- SQLAlchemy mapper smoke check for WMS/inventory models
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\schemas\wms.py app\schemas\inventory.py`
- Pydantic smoke check for WMS and inventory schemas
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\services\wms_service.py tests\test_gap008_wms_service.py`
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\api\v1\endpoints\wms.py app\services\wms_service.py app\schemas\wms.py`
- `cd backend; .\venv\Scripts\python.exe -c "import app.api.v1.endpoints.wms; print('wms endpoint import ok')"`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap008_wms_service.py -q`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap008_wms_service.py tests\test_gap_sec001_access_control.py -q`
- `cd frontend; npm.cmd run type-check`
- `cd frontend; npm.cmd run lint`

## Remaining Follow-Ups

These are not marked complete by this slice:

- mobile/scanner-optimized WMS flows
- offline scanner mode
- wave release UI actions beyond list visibility
- handling-unit create/edit UI
- license-plate label printing
- advanced labor productivity dashboards
- deeper FEFO allocation against pick waves
- full end-to-end browser tests using seeded WMS records

## Operational Notes

Backend authorization remains the source of truth. The frontend access badges are UX hints only. Direct API calls still pass through scoped guards and status-lock checks.
