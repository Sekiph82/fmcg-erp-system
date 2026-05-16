# GAP-023 ML-Based Predictive Maintenance — Implementation Notes

## Summary

GAP-023 hardened the existing predictive maintenance implementation with permission guards, migration ownership, and test coverage. No new models, algorithms, or service logic were required — the implementation was already feature-complete.

## Changes Made

### GAP-023A — Audit
- Inspected all maintenance models, service, endpoints, schemas, and frontend pages.
- Documented permission gaps (all endpoints used bare `get_current_user`), migration ownership gaps, and test gaps.
- Output: `GAP-023_ML_PREDICTIVE_MAINTENANCE_AUDIT.md`

### GAP-023B — Schema Design
- Defined explicit permission family for `maintenance` module: `view`, `create`, `edit`, `delete`, `predict`, `review_prediction`, `export`.
- Defined role grant strategy per role.
- Confirmed no new ORM models needed.
- Output: `GAP-023_ML_PREDICTIVE_MAINTENANCE_SCHEMA_DESIGN.md`

### GAP-023C — Migration
- Created `20260516_0030_maintenance_predictive_reconciliation.py`.
- Idempotently creates all 7 maintenance tables using `_has_table()` / `context.is_offline_mode()` guard pattern.
- Tables: `assets`, `pm_plans`, `pm_work_orders`, `breakdown_records`, `spare_parts`, `spare_part_usages`, `maintenance_predictions`.
- Enums: `assetstatus`, `pmfrequency`, `pmstatus`, `breakdownseverity`, `breakdownstatus`, `maintenancepredictionstatus`, `maintenancepredictionrisk`.

### GAP-023G — Endpoint Permission Guards
- Replaced all `Depends(get_current_user)` in `maintenance.py` with `Depends(require_permission(...))`.
- Removed `get_current_user` import (no longer needed).
- Permission mapping:
  - `GET /assets/`, `GET /assets/{id}`, `GET /pm-plans/`, `GET /work-orders/`, `GET /breakdowns/`, `GET /breakdowns/{id}`, `GET /spare-parts/`, `GET /spare-parts/{id}/usages`, `GET /breakdowns/{id}/spare-usages`, `GET /predictions`, `GET /reports/overdue-pm` → `maintenance.view`
  - `POST /assets/`, `POST /pm-plans/`, `POST /work-orders/`, `POST /breakdowns/`, `POST /spare-parts/`, `POST /spare-parts/usage` → `maintenance.create`
  - `PATCH /assets/{id}`, `PATCH /pm-plans/{id}`, `POST /work-orders/{id}/complete`, `PATCH /breakdowns/{id}/resolve`, `PATCH /breakdowns/{id}`, `PATCH /spare-parts/{id}` → `maintenance.edit`
  - `POST /predictions/generate` → `maintenance.predict`
  - `PATCH /predictions/{id}/review` → `maintenance.review_prediction`
  - `GET /reports/mtbf-mttr`, `GET /reports/downtime-by-machine` → `maintenance.export`

### GAP-023I — Module Registry and Seed
- Expanded `maintenance` `ModuleDefinition.permission_actions` from `DEFAULT_ACTIONS` to `("view", "create", "edit", "delete", "predict", "review_prediction", "export")`.
- Added 7 explicit maintenance permission tuples in `seed.py` PERMISSIONS list (replacing the previous 3).
- Role grants:
  - `admin`: full maintenance access (all 7 actions)
  - `coo`: view, create, edit, predict, review_prediction, export
  - `cto`: view, export
  - `factory_manager`: predict, review_prediction (view already granted via scoped maintenance permissions)
  - `maintenance_technician`: view, create, edit (unchanged)
  - `production_manager`: view, export

### GAP-023H — Frontend Permission Guards
- Added `RequirePermission` page-level guard to all 7 maintenance frontend pages:
  - `maintenance/page.tsx` → `maintenance.view`
  - `maintenance/assets/page.tsx` → `maintenance.view`
  - `maintenance/breakdowns/page.tsx` → `maintenance.view`
  - `maintenance/plans/page.tsx` → `maintenance.view`
  - `maintenance/spares/page.tsx` → `maintenance.view`
  - `maintenance/reports/page.tsx` → `maintenance.export`
  - `maintenance/predictive/page.tsx` → `maintenance.view` (page) + `PermissionGuard` for generate button (`maintenance.predict`) + review actions (`maintenance.review_prediction`)

### GAP-023J — Tests
- Created `backend/tests/test_gap023_ml_predictive_maintenance.py` with 25 contract tests:
  - Module registry: maintenance in MODULE_DEFINITIONS, correct permission_actions
  - Permission seeds: all 7 tuples present, predict/review_prediction/export explicitly checked
  - Registry permission codes
  - Role grants: admin, coo, cto, factory_manager, maintenance_technician, production_manager
  - Endpoint source guards: no bare get_current_user, predict/review_prediction/export guards present
  - Frontend guards: all 7 pages checked for RequirePermission
  - Migration: file exists, all 7 tables present in migration source
  - ORM: all 7 model classes importable with correct tablenames

## Rule-Based Prediction Algorithm

The algorithm in `maintenance_service.generate_maintenance_predictions()` is explicitly rule-based (not ML/black-box):

1. **IoT sensor trend analysis** — vibration, temperature, current, pressure sensor channels for each asset. If trend exceeds configurable thresholds, adds risk score.
2. **Machine state events** — DOWN and FAULT events in a rolling 7-day window. High event counts increase risk score.
3. **Critical IoT alerts** — unacknowledged critical alerts in window increase risk score.
4. **Breakdown history** — breakdowns in last 90 days increase score; recent/critical breakdowns add more weight.
5. **Score → risk mapping** — LOW (0–0.3), MEDIUM (0.3–0.6), HIGH (0.6–0.8), CRITICAL (0.8+).
6. **Evidence and source_metrics** — all signals stored in `evidence_summary` (text) and `source_metrics` (JSON) for full audit trail and explainability.
7. **Upsert logic** — existing OPEN/REVIEWED predictions for the same machine/failure_mode are updated rather than duplicated.

## Limitations

- Docker not available in development environment — migrations and seeds not executed during GAP-023.
- `machine_id` in `maintenance_predictions` maps to `asset.asset_no` — drift between these values would break prediction generation. The asset must be registered before predictions can link to it.
- Prediction generation requires IoT data, machine state events, or breakdown history to produce non-trivial results. Empty database will produce no predictions.
