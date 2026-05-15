# GAP-008 - Warehouse Management Depth Schema Design

## Status
GAP-008B design is complete.

This design extends the existing warehouse, inventory, WMS, and cycle-count foundation. It must not create a second warehouse system. The goal is to reconcile existing model/migration ownership first, then add only the schema needed for deeper WMS execution.

## Design Principles

- Keep `Warehouse` in `backend/app/models/master.py` as the warehouse master.
- Keep `Stock`, `Lot`, `StockMovement`, `SerialNumber`, and `CostLayer` in `backend/app/models/inventory.py` as the stock ledger foundation.
- Keep `WarehouseZone`, `StorageLocation`, putaway, stock-count, picking, packing, and replenishment models in `backend/app/models/wms.py`.
- Keep `CycleCount*` models in `backend/app/models/cycle_count.py`; do not merge them into `StockCount` in this slice.
- Use GAP-SEC-001 access scopes for warehouse mutation control.
- Prefer additive migrations and backward-compatible nullable fields.
- Avoid creating destructive warehouse resets, duplicate stock-balance tables, or parallel lot/batch tables.

## Current Authoritative Models

| Area | Authoritative Existing Model(s) | Decision |
|---|---|---|
| Warehouse master | `Warehouse` | Reuse. Add no duplicate warehouse table. |
| Zones and bins | `WarehouseZone`, `StorageLocation` | Reuse. Add migration reconciliation if missing fields/tables are not owned. |
| Current stock | `Stock` | Reuse. Do not create a second stock balance table in this slice. |
| Stock ledger | `StockMovement` | Reuse. Add optional source/destination location and handling-unit references. |
| Lots/batches | `Lot` | Reuse. Future improvement can add scoped uniqueness; keep additive now. |
| Serials | `SerialNumber`, `SerialMovement` | Reuse. Do not expand unless tied to handling units later. |
| Putaway | `PutawayRule`, `PutawayTask`, `PutawayExecution` | Reuse. Migration ownership exists for these tables. |
| WMS counts | `StockCount`, `StockCountLine` | Reuse for warehouse stock-count execution. |
| Cycle count planning | `CycleCountPlan`, `CycleCountTask`, `CountEntry`, `CountAdjustment`, `ABCClassification` | Reuse for ABC/count-planning. Permission/scope hardening is still required. |
| Picking | `PickingTask` | Reuse, but add wave ownership and location/handling-unit links. |
| Packing | `PackingRecord` | Reuse, but add migration ownership if missing. |
| Replenishment | `ReplenishmentTask` | Reuse, but add migration ownership if missing. |

## Required Migration Reconciliation

GAP-008C should create one additive/reconciliation Alembic migration after `20260514_0010`.

The migration should:

1. Create missing enums with `checkfirst=True`:
   - `pickingtaskstatus`
   - `packingstatus`
   - `replenishmentstatus`
   - new `wms_handling_unit_status`
   - new `wms_handling_unit_type`
   - new `wms_pick_wave_status`
2. Create missing existing-model tables if not present:
   - `wms_picking_tasks`
   - `wms_packing_records`
   - `wms_replenishment_tasks`
3. Add missing indexes for those existing-model tables.
4. Add optional location columns to `stock_movements`:
   - `source_location_id`
   - `destination_location_id`
5. Add optional handling-unit references to `stock_movements`:
   - `source_handling_unit_id`
   - `destination_handling_unit_id`
6. Create handling-unit/license-plate tables:
   - `wms_handling_units`
   - `wms_handling_unit_items`
7. Create wave-picking table:
   - `wms_pick_waves`
8. Add nullable `wave_id` to `wms_picking_tasks`.

Because older development databases may already contain some tables from historical automatic metadata creation, the migration should inspect the database before creating existing-model tables. It must be safe on both fresh Alembic-only databases and existing development databases.

## New Tables

### `wms_handling_units`

Purpose: pallet/license plate tracking for FMCG warehouse operations.

Recommended columns:

- `id` UUID primary key
- `license_plate` string, unique, indexed
- `warehouse_id` FK to `warehouses.id`, required
- `location_id` FK to `storage_locations.id`, nullable
- `parent_hu_id` FK to `wms_handling_units.id`, nullable
- `hu_type` enum: `PALLET`, `CARTON`, `TOTE`, `CRATE`, `CONTAINER`
- `status` enum: `OPEN`, `CLOSED`, `ON_HOLD`, `SHIPPED`, `CONSUMED`, `VOID`
- `gross_weight_kg` numeric nullable
- `net_weight_kg` numeric nullable
- `volume_m3` numeric nullable
- `created_by_id` FK to `users.id`, nullable
- `closed_at` timestamp nullable
- `notes` text nullable
- `created_at`, `updated_at`

Indexes/constraints:

- unique `license_plate`
- index `warehouse_id`
- index `location_id`
- index `status`
- index `parent_hu_id`

### `wms_handling_unit_items`

Purpose: item/lot quantities contained in each license plate.

Recommended columns:

- `id` UUID primary key
- `handling_unit_id` FK to `wms_handling_units.id`, required, cascade delete
- `stock_type` enum compatible with existing `StockType`
- `product_id` FK nullable
- `material_id` FK nullable
- `lot_id` FK nullable
- `quantity` numeric required
- `unit` string required
- `created_at`, `updated_at`

Constraints:

- Check that product/material matches `stock_type`.
- Index `handling_unit_id`.
- Index `product_id`.
- Index `material_id`.
- Index `lot_id`.

### `wms_pick_waves`

Purpose: wave/batch picking orchestration.

Recommended columns:

- `id` UUID primary key
- `wave_no` string unique indexed
- `warehouse_id` FK to `warehouses.id`, required
- `status` enum: `DRAFT`, `RELEASED`, `IN_PROGRESS`, `PICKED`, `CANCELLED`, `CLOSED`
- `priority` integer default 100
- `planned_start_at` timestamp nullable
- `planned_end_at` timestamp nullable
- `released_by_id` FK to `users.id`, nullable
- `released_at` timestamp nullable
- `closed_at` timestamp nullable
- `notes` text nullable
- `created_at`, `updated_at`

Indexes:

- `warehouse_id`
- `status`
- `planned_start_at`

`wms_picking_tasks.wave_id` should be nullable and point to `wms_pick_waves.id`.

## Existing Table Extensions

### `stock_movements`

Add nullable fields:

- `source_location_id`
- `destination_location_id`
- `source_handling_unit_id`
- `destination_handling_unit_id`

Rationale:

- WMS execution must know where stock moved within a warehouse.
- Putaway, picking, replenishment, and quarantine should leave a location-aware stock ledger trail.
- Fields are nullable to preserve existing movement rows and non-location transactions.

### `wms_picking_tasks`

Add nullable fields if the table already exists:

- `wave_id`
- optional `source_handling_unit_id` later if needed, but this can wait until handling-unit service logic exists.

Rationale:

- Wave picking should group existing picking tasks without replacing them.

## Permission And Scope Boundary

Keep the existing split:

- `inventory.*` controls stock ledger operations and stock quantities.
- `wms.*` controls warehouse execution operations.
- `warehouses.*` controls warehouse master data.
- `cycle_count.*` controls count planning and adjustment approvals.

Recommended permissions for GAP-008I:

- `wms.view_all`
- `wms.view_own_scope`
- `wms.create_own_scope`
- `wms.edit_own_scope`
- `wms.putaway_own_scope`
- `wms.pick_own_scope`
- `wms.pack_own_scope`
- `wms.replenish_own_scope`
- `wms.quarantine_own_scope`
- `wms.release_own_scope`
- `wms.wave_manage_own_scope`
- `wms.export_own_scope`
- `warehouses.view_all`
- `warehouses.view_own_scope`
- `warehouses.edit_own_scope`
- `cycle_count.perform_own_scope`
- `cycle_count.approve_own_scope`

Admin/global variants can use `_all` or base permission forms consistent with the current access helper behavior.

## Endpoint Scope Rules

GAP-008G should apply central access helpers to the following groups:

| Endpoint Group | View Rule | Mutation Rule |
|---|---|---|
| Warehouses | `warehouses.view_all` or assigned warehouse view scope | Create/edit/delete requires warehouse/company admin permission; delete should be strongly restricted. |
| Zones / locations | `wms.view_all` or warehouse view scope | Create/edit requires `wms.edit_all` or `wms.edit_own_scope` for the warehouse. |
| Scan location/lot/product | View only by allowed warehouse scopes | No mutation. Scan results should filter unauthorized stock positions. |
| Putaway rules/tasks | View by warehouse scope | Create/execute requires `wms.putaway_*` or `wms.edit_*` and matching warehouse scope. |
| Quarantine/release | View by warehouse scope | Quarantine requires `wms.quarantine_*`; release requires `wms.release_*` or quality release permission if later integrated. |
| FEFO suggestions | View by warehouse scope | No mutation; picking execution still needs pick scope. |
| Stock counts | View by warehouse scope | Start/record/submit requires count/perform scope; approve requires approve scope. |
| Picking | View by warehouse scope | Create/update/release/pick requires `wms.pick_*`; FEFO enforcement must be checked during create/update. |
| Packing | View by warehouse scope | Create/update/close requires `wms.pack_*`. |
| Replenishment | View by warehouse/location scope | Create/update/complete requires `wms.replenish_*`. |
| Reports | View by warehouse scope | Export requires export permission. |

## Workflow Status Rules

Recommended status locks:

- Putaway task `PENDING` and `IN_PROGRESS` can be updated by scoped users.
- Putaway task `COMPLETED` and `CANCELLED` are locked except notes by privileged users.
- Stock count `DRAFT` can be edited/started.
- Stock count `IN_PROGRESS` accepts count lines and submit.
- Stock count `PENDING_APPROVAL` requires approval permission.
- Stock count `APPROVED` is locked.
- Picking task `PENDING` can be assigned and released.
- Picking task `IN_PROGRESS` can accept picked quantity.
- Picking task `PICKED` can be packed.
- Picking task `PACKED` is locked except controlled reversal.
- Packing record `OPEN` can be edited.
- Packing record `CLOSED` is locked.
- Replenishment task `PENDING` and `IN_PROGRESS` can be updated.
- Replenishment task `COMPLETED` and `CANCELLED` are locked.
- Handling unit `OPEN` can be changed.
- Handling unit `CLOSED`, `SHIPPED`, `CONSUMED`, and `VOID` are locked except controlled transitions.

## API Response UX

Important WMS list responses should eventually include access hints:

```json
{
  "access": {
    "can_view": true,
    "can_edit": false,
    "can_putaway": false,
    "can_pick": true,
    "can_quarantine": false,
    "can_release": false
  }
}
```

Apply selectively to:

- stock summary
- zones/locations
- putaway tasks
- picking tasks
- packing records
- replenishment tasks
- stock counts
- cycle-count tasks/adjustments

## Frontend Design Impact

GAP-008H should preserve the current UI style and extend existing pages:

- Show WMS action buttons only when permission/scope allows the action.
- Add `View only` badges for rows outside mutation scope.
- Add stable `data-testid` selectors for WMS rows/actions.
- Keep broad view support: a user may see all warehouses if allowed but mutate only assigned warehouses.
- Do not hide backend errors; show the existing toast/error pattern.

## What Not To Do

- Do not create a second stock balance table.
- Do not delete or replace the existing cycle-count implementation.
- Do not make WMS an isolated island outside inventory stock movements.
- Do not bypass existing `StockMovement` ledger logic.
- Do not implement mobile/offline mode with fake local-only behavior.
- Do not mark FEFO as enforced unless picking creation/update actually validates it.

## GAP-008C Migration Scope

Recommended first migration name:

- `20260514_0020_wms_depth_reconciliation.py`

Migration should be additive and safe:

- create missing execution tables if absent
- add handling-unit/license-plate tables
- add wave-picking table
- add nullable location/handling-unit movement fields
- add nullable `wave_id` to `wms_picking_tasks`
- create indexes and FK constraints

Live database verification should include:

- `alembic heads`
- `alembic history -r 20260514_0010:20260514_0020`
- offline SQL generation
- live `alembic upgrade head` if local dev PostgreSQL is running
- schema checks for all new tables/columns

## Follow-Up Implementation Order

1. GAP-008C: Add the reconciliation/additive migration.
2. GAP-008D: Add ORM models for handling units and pick waves; extend stock movement and picking task relationships.
3. GAP-008E: Add schemas for handling units, waves, access hints, and extended movement/location data.
4. GAP-008F: Add service helpers for handling-unit lifecycle, wave creation/release, FEFO validation, and status locks.
5. GAP-008G: Harden WMS/warehouse/cycle-count endpoints with permissions and scopes.
6. GAP-008H: Update WMS frontend rows/actions with scoped UX.
7. GAP-008I: Register/seed WMS scope-aware permissions and role grants.
8. GAP-008J: Add focused tests.
9. GAP-008K: Document operational behavior.
10. GAP-008L: Run final checks and record results.

