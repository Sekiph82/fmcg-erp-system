# GAP-008 - Warehouse Management Depth Audit

## Status
GAP-008A audit is complete.

This audit inspects the current warehouse, WMS, inventory, and cycle-count implementation before any schema or feature changes. The repository already has a meaningful WMS foundation, but the depth is uneven: stock ledger operations are relatively mature, while warehouse execution workflows need stronger permission/scope enforcement, migration ownership review, workflow hardening, and frontend parity.

## Planning Requirement
The roadmap item for Warehouse Management Depth calls for:

- putaway strategies
- bin/location hierarchy
- wave picking / batch picking
- FEFO enforced during picking
- pallet/license plate tracking
- mobile scanner workflow
- offline warehouse mode
- cycle count reconciliation approvals
- damaged/quarantine stock movement
- warehouse productivity metrics

## Files Inspected

Backend models:

- `backend/app/models/master.py`
- `backend/app/models/inventory.py`
- `backend/app/models/wms.py`
- `backend/app/models/cycle_count.py`

Backend schemas:

- `backend/app/schemas/inventory.py`
- `backend/app/schemas/wms.py`
- `backend/app/schemas/cycle_count.py`

Backend API endpoints:

- `backend/app/api/v1/endpoints/warehouses.py`
- `backend/app/api/v1/endpoints/inventory.py`
- `backend/app/api/v1/endpoints/wms.py`
- `backend/app/api/v1/endpoints/cycle_count.py`

Backend services and CRUD:

- `backend/app/services/inventory_service.py`
- `backend/app/services/wms_service.py`
- `backend/app/services/cycle_count_service.py`
- `backend/app/crud/inventory.py`
- `backend/app/crud/wms.py`

Frontend:

- `frontend/src/lib/inventory.ts`
- `frontend/src/lib/wms.ts`
- `frontend/src/lib/warehouses.ts`
- `frontend/src/lib/cycleCount.ts`
- `frontend/src/app/dashboard/inventory/page.tsx`
- `frontend/src/app/dashboard/inventory/serials/page.tsx`
- `frontend/src/app/dashboard/inventory/valuation/page.tsx`
- `frontend/src/app/dashboard/warehouses/page.tsx`
- `frontend/src/app/dashboard/wms/page.tsx`
- `frontend/src/app/dashboard/wms/counts/page.tsx`
- `frontend/src/app/dashboard/wms/counts/[id]/page.tsx`
- `frontend/src/app/dashboard/wms/picking/page.tsx`
- `frontend/src/app/dashboard/wms/replenishment/page.tsx`
- `frontend/src/app/dashboard/wms/reports/page.tsx`
- `frontend/src/components/nav-config.tsx`

Migrations and docs:

- `backend/alembic/versions/a5b6c7d8e9f0_cycle_count.py`
- `backend/alembic/versions/b6c7d8e9f0a1_putaway_rules.py`
- `backend/alembic/versions/20260511_0020_operational_posting_integration.py`
- `docs/planning/ERP_ROADMAP_AND_MANUAL_PLAN.md`
- `docs/user-manual/MANUAL_AUDIT.md`

## Existing Implementation

### Warehouse Master Data

`Warehouse` exists in `backend/app/models/master.py` with code, name, type, address/city/country, capacity area, active flag, and relationships to stock and stock movements.

`backend/app/api/v1/endpoints/warehouses.py` exposes list, create, detail, update, and delete routes.

Current limitations:

- Warehouse master does not include branch/company ownership, temperature class, storage restrictions, dock/staging metadata, operating calendar, or responsible manager.
- The API mostly checks authentication only. It does not consistently require `warehouses.view`, `warehouses.create`, `warehouses.edit`, or `warehouses.delete`.
- Deletion appears hard-delete oriented through CRUD. A production WMS should prefer archive/deactivate when warehouses are referenced by stock, movements, zones, locations, counts, or logistics records.

### Inventory Stock Ledger

`backend/app/models/inventory.py` has:

- `Stock` for current on-hand, reserved, available, blocked, warehouse, lot, and location state.
- `Lot` for batch/lot tracking with manufacture date, expiry date, quarantine flag, product/material/supplier references.
- `StockMovement` as an immutable-style quantity ledger with receipt, issue, transfer, adjustment, return, and write-off movement types.
- `SerialNumber` and `SerialMovement` for per-unit tracking.
- `CostLayer` for FIFO / weighted-average / standard-cost valuation support.

`backend/app/services/inventory_service.py` has real stock operation helpers for:

- stock entry
- stock issue
- warehouse transfer
- stock adjustment by balancing movement
- stock delete guards
- movement delete reversal logic
- stock summary
- movement detail
- FIFO cost layers and valuation / aging reports

This is the strongest warehouse-adjacent foundation in the current code.

Current limitations:

- `Stock` has only one `location_id`; there is no dedicated inventory balance table by product/material, lot, warehouse, location, status, license plate, and handling unit.
- `quantity_reserved` exists but reservation workflow is not clearly tied to sales orders, production orders, picking waves, or allocation rules.
- `StockRead` does not expose `is_blocked`, `location_id`, or access hints even though the model has them.
- Lot uniqueness is not scoped by product/material/supplier. Duplicate lot numbers may be ambiguous in real FMCG operations.
- Inventory movements have source/destination warehouse IDs but no source/destination location IDs, pallet/license plate IDs, reason code table, approval status, or device/scanner metadata.

### WMS Bin / Location Foundation

`backend/app/models/wms.py` defines:

- `WarehouseZone`
- `StorageLocation`
- `PutawayRule`
- `PutawayTask`
- `PutawayExecution`
- `StockCount`
- `StockCountLine`
- `PickingTask`
- `PackingRecord`
- `ReplenishmentTask`

This is a meaningful WMS surface. It includes zones, bins, barcode on locations, location capacity fields, location blocked flag, min/max quantities, putaway rule types, putaway task/execution, stock-count lifecycle, picking task statuses, packing records, and replenishment statuses.

`backend/app/api/v1/endpoints/wms.py` exposes endpoints for:

- zones and locations
- scan location / lot / product
- putaway
- quarantine and release
- FEFO suggestions
- stock counts
- near-expiry, low-stock, aging, lot trace, and movement ledger reports
- putaway rules and tasks
- putaway AI helper summaries
- picking tasks
- packing records
- replenishment tasks

Current limitations:

- Most WMS endpoints use `get_current_user` only. They do not consistently require `wms.view`, `wms.create`, `wms.edit`, `wms.approve`, or warehouse-scoped mutation checks.
- WMS routes currently do not use the central GAP-SEC-001 access helpers the way `inventory.py` does.
- Scan endpoints can reveal stock positions across warehouses without warehouse view-scope filtering.
- Quarantine/release are important operational controls but currently require only authentication. They should require scoped quality/WMS/inventory hold/release permissions.
- Putaway rule/task create/update/execute does not verify warehouse scope or status transitions beyond service checks.
- Picking, packing, and replenishment endpoints are CRUD-style and do not enforce enough workflow rules for real warehouse execution.
- There is no wave picking, batch picking, cartonization, load staging, dock assignment, route/load linkage, mobile device session, or offline sync queue.
- There is no pallet/license plate/handling-unit model.
- Location utilization is stored as `current_utilization_pct` but not consistently recalculated from stock weight/volume.

### Cycle Count

`backend/app/models/cycle_count.py` defines:

- count plans
- count tasks
- count entries
- count adjustments
- ABC classifications

`backend/app/services/cycle_count_service.py` supports:

- plan/task CRUD
- task generation from ABC/location/item logic
- count entry capture
- adjustment approval/rejection
- ABC classification
- dashboard and report summaries
- AI-style variance/count-frequency helper summaries

Current limitations:

- `backend/app/api/v1/endpoints/cycle_count.py` has several routes that do not require `get_current_user` or explicit permissions at all, including dashboard/list/detail/update/report surfaces.
- Approval/rejection routes authenticate but do not clearly require `cycle_count.approve` or warehouse scope.
- `_post_stock_adjustment` creates stock movements but the movement source/destination warehouse fields are null in the observed implementation area, which weakens downstream stock-ledger traceability unless compensated elsewhere.
- Cycle count and WMS stock-count models coexist. The roadmap design should decide whether both stay, whether one becomes the enterprise count engine, or whether one wraps the other.

### Frontend

Frontend WMS coverage exists:

- `/dashboard/inventory`
- `/dashboard/inventory/serials`
- `/dashboard/inventory/valuation`
- `/dashboard/warehouses`
- `/dashboard/wms`
- `/dashboard/wms/counts`
- `/dashboard/wms/counts/[id]`
- `/dashboard/wms/picking`
- `/dashboard/wms/replenishment`
- `/dashboard/wms/reports`
- putaway routes under `/dashboard/putaway`

The inventory page has recent scope-aware UX:

- uses `useAuth`
- uses `canPerformInScope`
- shows `View only` badges
- hides/disables stock adjust/delete actions based on warehouse action scope

WMS-specific pages are less hardened:

- WMS pages generally render action buttons without permission/scope checks.
- WMS rows do not expose per-row access hints.
- Picking/replenishment pages look closer to operational scaffolding than mature execution screens.
- Manual audit already marks some WMS/putaway pages as partial or not clearly discoverable.

### Permissions And Registry

The module registry owns `inventory` as a core module with default actions.

`wms`, `warehouses`, and `cycle_count` appear in seed permissions and navigation, but WMS and cycle-count routes are still registered via endpoint-route definitions rather than a fully metadata-owned module definition.

Seed permissions include:

- `warehouses.view/create/edit`
- `wms.view/create/edit`
- `cycle_count.view/create/approve`
- `inventory.view_all`, `inventory.edit_own_scope`, `inventory.adjust_own_scope`, `inventory.receive_own_scope`, `inventory.dispatch_own_scope`
- `cycle_count.perform_own_scope`

Current limitations:

- No consistent scope-aware permission set exists for all WMS actions yet. Examples needed: `wms.view_all`, `wms.view_own_scope`, `wms.putaway_own_scope`, `wms.pick_own_scope`, `wms.pack_own_scope`, `wms.replenish_own_scope`, `wms.quarantine_own_scope`, `wms.release_own_scope`, `cycle_count.approve_own_scope`.
- Navigation uses `wms.view` and `warehouses.view`, while backend endpoints often only check authentication.
- The permission vocabulary overlaps `inventory` and `wms`; GAP-008B should define a clean boundary.

## Migration Ownership Findings

Existing Alembic migrations cover parts of WMS:

- Cycle-count tables are owned by `a5b6c7d8e9f0_cycle_count.py`.
- Putaway rules/tasks/executions and storage-location capacity fields are owned by `b6c7d8e9f0a1_putaway_rules.py`.
- Operational posting integration owns accounting fields on `stock_movements`.

Potential migration gap:

- No migration was clearly found for `wms_picking_tasks`, `wms_packing_records`, or `wms_replenishment_tasks`.
- If those tables currently exist only because of previous `Base.metadata.create_all` behavior, GAP-008C must add additive/reconciliation migration ownership before relying on them in production.
- The audit command did not clearly find migration ownership for base `stocks`, `stock_movements`, `lots`, `serial_numbers`, `cost_layers`, `warehouse_zones`, or `storage_locations`; GAP-008B/C should verify live schema history and avoid duplicate creation.

## Gap Analysis Against Roadmap

| Requirement | Current Status | Notes |
|---|---|---|
| Putaway strategies | Partial | Rule model and suggestion service exist, but scope/status hardening and frontend depth are limited. |
| Bin/location hierarchy | Partial | Zones and locations exist; no aisle/rack/level/bin hierarchy beyond zone/location. |
| Wave picking / batch picking | Missing | Picking task model exists, but no wave/batch picking orchestration. |
| FEFO enforced during picking | Partial | FEFO suggestion endpoint exists; picking task has `fefo_enforced`, but enforcement is not clearly applied in picking creation/update. |
| Pallet/license plate tracking | Missing | No handling unit/license plate model found. |
| Mobile scanner workflow | Partial | Scan endpoints and location barcodes exist; no mobile session/device/offline workflow. |
| Offline warehouse mode | Missing | No offline sync queue or conflict-resolution model found. |
| Cycle count reconciliation approvals | Partial | WMS stock counts and cycle-count adjustment approvals exist, but permissions/scope and stock-ledger traceability need hardening. |
| Damaged/quarantine stock movement | Partial | Quarantine/release changes blocked stock and creates movements, but permission/scope and reason-code workflow need hardening. |
| Warehouse productivity metrics | Partial | Putaway AI/efficiency summaries and reports exist, but picker productivity, task SLA, dock/load throughput, and labor metrics are missing. |

## Recommended GAP-008B Design Direction

Do not create a second WMS architecture.

Reuse:

- `Warehouse`
- `Stock`
- `Lot`
- `StockMovement`
- `WarehouseZone`
- `StorageLocation`
- `PutawayRule`
- `PutawayTask`
- `StockCount`
- `PickingTask`
- `PackingRecord`
- `ReplenishmentTask`
- central GAP-SEC-001 access helpers

Design should focus on:

1. Migration reconciliation for existing WMS models that are not clearly Alembic-owned.
2. Permission/scope model for WMS actions and cycle-count actions.
3. A handling-unit/license-plate model if required for pallet tracking.
4. Wave picking and picking-line models instead of overloading single picking tasks.
5. Optional scanner/offline sync tables only if the frontend/backend workflow will use them in this phase.
6. Status rules for putaway, counts, picking, packing, replenishment, quarantine/release, and stock movement reversal.
7. API response access hints for operational WMS lists.

## Immediate Risks

- Some WMS tables may be missing in a fresh Alembic-only database if they were historically created by automatic metadata creation.
- WMS mutating endpoints are not consistently permission/scope protected.
- Broad scan/report endpoints may expose cross-warehouse stock details without view-scope filtering.
- FEFO exists as suggestion logic but is not enforced consistently in picking execution.
- Two count systems exist (`stock_counts` and `cc_*`) and need a clear product decision before deeper implementation.

## GAP-008B Acceptance Focus

The next task should produce a schema/design document that answers:

- Which current WMS models remain authoritative?
- Which missing migrations are required?
- Which new tables are essential now versus later?
- How `inventory` and `wms` permission boundaries work.
- How warehouse scope checks apply to zones, locations, putaway, picking, packing, replenishment, counts, quarantine, and scan/report APIs.
- Which workflows are locked by status and which require approval.

