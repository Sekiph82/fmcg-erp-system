# M24.S01.T002 — Pick-list generation

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file exists; root `TASKS.md` is authoritative. The M24 interpretation is recorded in `coordination/milestones/M24/EXECUTION_PLAN_V01.md`.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-010/012 and `coordination/AUDIT_POLICY.md` require direct observation of inventory invariants and cross-module effects. M22's production-order responsibility decision keeps the pick list anchored to canonical `ProductionOrder` identity.

## Implementation

- Added a read-only generated pick-list API and reservation detail action. It is built from active/partially issued reservations, reports outstanding quantity by material and allocated lot, and includes the order, warehouse, expiry, and source-line identities.
- Generation does not create another reservation or mutate stock. It rejects cancelled/fully issued reservations, inactive orders, missing source identity, and malformed reservation references.
- Existing WMS `PickingTask` is product/shipment-specific (`product_id` is required), so this material pick-list preview reuses reservation lines as its source of truth instead of duplicating or mislinking WMS shipment tasks. S01.T003 will add location semantics; S01.T004 owns FEFO behavior.
- Added a disposable-PostgreSQL-gated case for outstanding quantities and read-only stock behavior. It has not yet been run.

## Checks performed

- `python -m py_compile` on changed backend schemas/services/endpoints and the M24 gated integration file: passed.
- Ruff on the M24 gated integration file: passed.
- Targeted ESLint on the reservation page and material-flow client: passed.
- `git diff --check`: passed.
- No PostgreSQL, API, or E2E test was run for this task; comprehensive M24 validation and independent review remain scheduled for S04.T004.

## Scope limits

The list is a virtual, read-only preparation view. It does not claim physical picking, staging, warehouse-device, or live stock acceptance.
