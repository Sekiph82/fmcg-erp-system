# GAP-023 ML-Based Predictive Maintenance Audit

## Summary

GAP-023 covers ML/rule-based predictive maintenance. The implementation is substantially complete: models, service logic, endpoints, schemas, and frontend pages all exist. The primary gaps are missing permission guards on all endpoints, no dedicated predictive/review permission actions, missing migration ownership for maintenance tables, no focused predictive maintenance tests, and no implementation documentation.

## Files Inspected

- `backend/app/models/maintenance.py`
- `backend/app/services/maintenance_service.py`
- `backend/app/api/v1/endpoints/maintenance.py`
- `backend/app/schemas/maintenance.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `frontend/src/app/dashboard/maintenance/page.tsx`
- `frontend/src/app/dashboard/maintenance/predictive/page.tsx`
- `frontend/src/app/dashboard/maintenance/assets/page.tsx`
- `frontend/src/app/dashboard/maintenance/breakdowns/page.tsx`
- `frontend/src/app/dashboard/maintenance/plans/page.tsx`
- `backend/alembic/versions/*`

## Existing Model Coverage

`backend/app/models/maintenance.py` defines:

- `Asset` — asset register (asset_no, name, type, line, manufacturer, install_date, warranty, status)
- `PMPlan` — preventive maintenance plan (frequency, interval_days, checklist, next_due_date)
- `PMWorkOrder` — PM work order (scheduled, started, completed, technician)
- `BreakdownRecord` — breakdown event (start/end time, downtime_minutes, severity, status, root_cause)
- `SparePart` — spare part master linked to Material
- `SparePartUsage` — spare part consumption against breakdown or PM WO
- `MaintenancePrediction` — rule-based failure prediction (predicted_failure_date, confidence, risk_level, failure_mode, recommended_action, evidence_summary, source_metrics, status lifecycle)

Enums: `AssetStatus`, `PMFrequency`, `PMStatus`, `BreakdownSeverity`, `BreakdownStatus`, `MaintenancePredictionRisk`, `MaintenancePredictionStatus`.

## Existing Service Coverage

`backend/app/services/maintenance_service.py` implements:

- `compute_mtbf_mttr` — MTBF/MTTR per asset from breakdown records
- `compute_downtime_by_machine` — aggregated downtime including MES downtime logs
- `overdue_pm_list` — overdue PM plans by next_due_date
- `generate_maintenance_predictions` — rule-based prediction using:
  - IoT sensor trend analysis (vibration, temperature, current, pressure)
  - Machine state events (DOWN, FAULT events in window)
  - Critical IoT alerts in window
  - Recent breakdown history (90-day window)
  - Score-to-risk mapping (LOW/MEDIUM/HIGH/CRITICAL)
  - Evidence summary and source_metrics JSON for explainability
  - Upsert logic — updates existing OPEN/REVIEWED predictions rather than duplicating
- `list_maintenance_predictions`, `get_maintenance_prediction`, `review_maintenance_prediction`

The algorithm is explicitly rule-based and explainable — not a black-box ML model. Confidence and risk are computed from weighted signal scores.

## Existing Endpoint Coverage

`backend/app/api/v1/endpoints/maintenance.py` exposes:

- Assets: `GET /assets/`, `POST /assets/`, `GET /assets/{id}`, `PATCH /assets/{id}`
- PM Plans: `GET /pm-plans/`, `POST /pm-plans/`, `PATCH /pm-plans/{id}`
- PM Work Orders: `GET /work-orders/`, `POST /work-orders/`, `PATCH /work-orders/{id}`
- Breakdowns: `GET /breakdowns/`, `POST /breakdowns/`, `PATCH /breakdowns/{id}`
- Spare Parts: `GET /spare-parts/`, `POST /spare-parts/`, `PATCH /spare-parts/{id}`
- Spare Part Usages: `POST /spare-part-usages/`, `GET /spare-part-usages/{asset_id}`
- Predictions: `POST /predictions/generate`, `GET /predictions`, `PATCH /predictions/{id}/review`
- Reports: `GET /reports/mtbf-mttr`, `GET /reports/downtime-by-machine`, `GET /reports/overdue-pm`

## Existing Schema Coverage

`backend/app/schemas/maintenance.py` has full Pydantic schemas:
- `AssetCreate`, `AssetUpdate`, `AssetRead`
- `PMPlanCreate`, `PMPlanUpdate`, `PMPlanRead`
- `PMWorkOrderCreate`, `PMWorkOrderUpdate`, `PMWorkOrderRead`
- `BreakdownCreate`, `BreakdownUpdate`, `BreakdownRead`
- `SparePartCreate`, `SparePartUpdate`, `SparePartRead`
- `SparePartUsageCreate`, `SparePartUsageRead`
- `MaintenancePredictionRead`, `MaintenancePredictionReview`
- Analytics schemas: `MtbfMttrRow`, `DowntimeByMachineRow`, `OverduePMRow`

## Existing Frontend Coverage

- `frontend/src/app/dashboard/maintenance/page.tsx` — maintenance dashboard with asset health tiles, overdue PM list, high-risk prediction summary
- `frontend/src/app/dashboard/maintenance/predictive/page.tsx` — predictive maintenance page with generate button, risk filters, prediction cards with evidence
- `frontend/src/app/dashboard/maintenance/assets/page.tsx` — asset register
- `frontend/src/app/dashboard/maintenance/breakdowns/page.tsx` — breakdown records
- `frontend/src/app/dashboard/maintenance/plans/page.tsx` — PM plans
- `frontend/src/app/dashboard/maintenance/spares/page.tsx` — spare parts
- `frontend/src/app/dashboard/maintenance/reports/page.tsx` — MTBF/MTTR and downtime reports

Frontend uses `@tanstack/react-query` and the `maintenanceApi` client from `frontend/src/lib/maintenance.ts`.

## Permission Gaps

- All maintenance endpoints use only `get_current_user` — no dedicated `maintenance.*` permission checks.
- `maintenance` module has `DEFAULT_ACTIONS` (view, create, edit, delete) in `module_registry.py` — no `predict` or `review_prediction` actions.
- Seed has `maintenance.view`, `maintenance.create`, `maintenance.edit` only.
- No `maintenance.predict` permission exists for running predictions.
- No `maintenance.review_prediction` or `maintenance.export` permission exists.

## Migration Ownership Gaps

- Alembic search found no migration that creates `assets`, `pm_plans`, `pm_work_orders`, `breakdown_records`, `spare_parts`, `spare_part_usages`, or `maintenance_predictions` tables.
- These tables likely exist from `create_all` or a base migration not found in search scope.
- GAP-023C should add an idempotent reconciliation migration for maintenance tables.

## Test Gaps

- No focused predictive maintenance tests exist in `backend/tests/`.
- Existing maintenance test coverage is unclear.

## Risks

- Unauthenticated access to breakdown and spare part mutations — any logged-in user can create/edit breakdown records and consume spare parts.
- `POST /predictions/generate` can be triggered by any logged-in user — should require a dedicated permission.
- `PATCH /predictions/{id}/review` can be actioned by any logged-in user.
- String `machine_id` in predictions matches `asset.asset_no` — drift between these values would break prediction generation.
- Frontend pages have no permission guards — visible to all authenticated users.

## Acceptance Criteria for GAP-023

GAP-023 is complete when:
- All maintenance endpoints use dedicated `maintenance.*` permission guards.
- `predict` and `review_prediction` permission actions exist and are seeded.
- Reconciliation migration covers maintenance tables.
- Frontend maintenance pages have page-level permission guards.
- Focused tests cover module registry, permission tuples, endpoint guards, and model imports.
- Implementation notes document the rule-based algorithm.
