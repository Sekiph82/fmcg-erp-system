# GAP-023 ML-Based Predictive Maintenance Schema Design

## Summary

GAP-023 does not require new models or schema changes. All necessary tables, ORM classes, Pydantic schemas, service logic, and endpoint routes already exist. The work is permission hardening, migration ownership reconciliation, frontend guards, and test coverage.

## No New Models Required

Existing models cover the predictive maintenance domain:

- `Asset` — asset register
- `PMPlan`, `PMWorkOrder` — preventive maintenance lifecycle
- `BreakdownRecord`, `SparePartUsage` — corrective maintenance history
- `MaintenancePrediction` — rule-based failure prediction with full lifecycle and evidence fields

## Permission Design

Expand `maintenance` module from `DEFAULT_ACTIONS` to an explicit set:

| Permission | Description |
|---|---|
| `maintenance.view` | View assets, PM plans, breakdowns, spare parts, predictions, reports |
| `maintenance.create` | Create assets, PM plans, PM work orders, breakdown records |
| `maintenance.edit` | Edit assets, PM plans, work orders, breakdown records, spare parts |
| `maintenance.delete` | Delete assets or decommission |
| `maintenance.predict` | Generate ML/rule-based predictive maintenance analysis |
| `maintenance.review_prediction` | Review, dismiss, or escalate predictive maintenance results |
| `maintenance.export` | Export MTBF/MTTR and downtime reports |

Role grants:

| Role | Permissions |
|---|---|
| `owner` | wildcard — all |
| `admin` | full maintenance access |
| `coo` | view, predict, review_prediction, export |
| `cto` | view, export |
| `factory_manager` | view, create, edit, predict, review_prediction |
| `maintenance_technician` | view, create, edit |
| `production_manager` | view, export |

## Migration Strategy

GAP-023C should create an idempotent reconciliation migration for:

- `assets`
- `pm_plans`
- `pm_work_orders`
- `breakdown_records`
- `spare_parts`
- `spare_part_usages`
- `maintenance_predictions`

Use the same `_has_table` / `context.is_offline_mode()` guard pattern from GAP-022C to avoid destructive actions.

## Algorithm Design (Existing — No Change)

The existing rule-based prediction algorithm in `maintenance_service.py` is appropriate for GAP-023. It is explainable, uses only existing data (IoT sensor trends, machine state events, critical alerts, breakdown history), and stores evidence summaries and source metrics for audit. No change to the algorithm is required.

## Acceptance Criteria for GAP-023B

GAP-023B is complete when this document defines the permission family, role grant strategy, migration scope, and algorithm boundary for GAP-023 implementation.
