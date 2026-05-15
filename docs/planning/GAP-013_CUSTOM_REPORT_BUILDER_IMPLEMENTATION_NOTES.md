# GAP-013 Custom Report Builder Implementation Notes

## Summary

GAP-013 hardened the Custom Report Builder module that already existed in the codebase. The module had zero authentication on any endpoint, no permission codes registered in the module registry or seed, no schedule run audit trail, and no RLS enforcement at query time. This gap adds the `rb_schedule_run_log` table, the `ScheduleRunLog` ORM model and schema, promotes the `reports` module from a loose route definition to a full `ModuleDefinition`, adds `require_permission` guards to all 30+ endpoints, seeds 6 permission codes, and adds focused tests covering all contracts.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Migration | Added `rb_schedule_run_log` table (revision `20260515_0040`) |
| ORM model | Added `ScheduleRunStatus` enum and `ScheduleRunLog` model; added `run_logs` back-ref on `ReportSchedule` |
| Schema | Added `ScheduleRunLogRead` Pydantic schema |
| Endpoint auth | Added `require_permission` dependency to all 30+ report builder endpoints |
| Module registry | Promoted `reports` to `MODULE_DEFINITIONS`; removed `report_builder` from `ENDPOINT_ROUTE_DEFINITIONS` |
| Seed | Added 6 `reports.*` permission codes; added all 6 to admin role; added view/run/export to CEO/exec roles |
| Tests | Added `backend/tests/test_gap013_report_builder_access.py` with 20 focused unit tests |

---

## Migration

**File:** `backend/alembic/versions/20260515_0040_report_builder_schedule_run_log.py`

- **Revision:** `20260515_0040`
- **Parent:** `20260515_0030` (document/knowledge reconciliation)
- **Strategy:** Additive only. Uses `_has_table` guard; safe to run against a DB where the table already exists.
- **What it creates:** `rb_schedule_run_log` with columns:
  - `run_id` UUID PK
  - `schedule_id` UUID FK → `rb_report_schedules.schedule_id` ON DELETE CASCADE, indexed
  - `report_id` UUID FK → `rb_report_definitions.report_id` ON DELETE CASCADE
  - `started_at` TIMESTAMP NOT NULL
  - `completed_at` TIMESTAMP (nullable)
  - `status` VARCHAR(20) default `'running'` (running/success/failed/skipped)
  - `row_count` INTEGER (nullable)
  - `export_format` VARCHAR(10) (nullable)
  - `recipients_sent` TEXT (nullable)
  - `error_message` TEXT (nullable)
  - Index: `ix_rb_schedule_run_log_started_at`
- **Live DB migration:** Skipped — Docker daemon unavailable in this session. Alembic offline SQL generation passed. Run when Docker is available:
  ```
  docker compose --env-file .env.development exec -T backend python -m alembic upgrade head
  ```

---

## Backend Models

### `backend/app/models/report_builder.py`

| Addition | Detail |
|---|---|
| `ScheduleRunStatus` enum | `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED` |
| `ScheduleRunLog` model | Maps to `rb_schedule_run_log`; relationships: `schedule` → `ReportSchedule`, `report` → `ReportDefinition` |
| `ReportSchedule.run_logs` | Back-reference relationship with `cascade="all, delete-orphan"` |

Pre-existing models unchanged: `ReportDefinition`, `ReportField`, `ReportFilter`, `ReportCalculatedField`, `ReportSchedule`, `ReportDashboard`, `DashboardWidget`, `RBAIRecommendation`, `ReportRLS`.

---

## Schemas

### `backend/app/schemas/report_builder.py`

| Schema | Fields |
|---|---|
| `ScheduleRunLogRead` | `run_id`, `schedule_id`, `report_id`, `started_at`, `completed_at`, `status`, `row_count`, `export_format`, `recipients_sent`, `error_message` |

Added before the existing `ReportOut.model_rebuild()` call. Uses `class Config: from_attributes = True` to match the pre-existing schema style in this file.

---

## Services

### `backend/app/services/report_builder_service.py`

No changes in this gap. The service already contained:

- `DATA_SOURCES` catalog — maps source keys to table names and allowed field paths
- `_validate_field(data_source, field_path)` — whitelist check against `DATA_SOURCES`
- `_apply_filter_python(rows, field, op, value, value_to)` — Python-level row filter supporting `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `like`, `is_null`, `is_not_null`, `in`, `between`
- `_execute_query(db, data_source, fields, filters, limit, offset)` — builds parameterized SELECT with integer-cast LIMIT/OFFSET
- `SAFE_AGGREGATIONS` set — allowlist for aggregation functions

Known limitation carried forward from the existing implementation: filter application is Python-level post-fetch, not SQL-level WHERE clauses. RLS enforcement is not applied at query time. These are recorded in the audit doc (`GAP-013_CUSTOM_REPORT_BUILDER_AUDIT.md`) as future improvements.

---

## Endpoints

### `backend/app/api/v1/endpoints/report_builder.py`

All 30+ routes now carry `dependencies=[Depends(require_permission("reports", "<action>"))]`. Permission mapping:

| Permission | Routes |
|---|---|
| `reports.view` | GET catalog, GET catalog/{id}, GET/POST reports list, GET report/{id}, GET schedules, GET dashboards, GET dashboard/{id}, GET/PATCH AI recommendations |
| `reports.create` | POST reports, POST clone, POST schedule, POST dashboards |
| `reports.edit` | PATCH report/{id}, POST dashboard widget |
| `reports.run` | POST run, POST preview |
| `reports.export` | GET export |
| `reports.admin` | DELETE report, POST seed-templates, DELETE schedule, DELETE widget, POST AI agents (3), GET executive summary, POST/GET/PATCH/DELETE RLS rules |

---

## Module Registry

### `backend/app/core/module_registry.py`

| Change | Detail |
|---|---|
| Removed | `EndpointRouteDefinition(key="report_builder", ...)` |
| Added | `ModuleDefinition(key="reports", label="Report Builder", route_prefix="/reports-builder", import_path="app.api.v1.endpoints.report_builder", permission_actions=("view", "create", "edit", "run", "export", "admin"), sidebar_group="Analytics", icon_key="bar-chart", ai_mode=RULE_BASED, critical=False)` |

---

## Permissions and Seed

### `backend/app/db/seed.py`

Six permission codes added to `PERMISSIONS`:

| Code | Label |
|---|---|
| `reports.view` | View Reports |
| `reports.create` | Create Reports |
| `reports.edit` | Edit Reports |
| `reports.run` | Run Reports |
| `reports.export` | Export Reports |
| `reports.admin` | Admin Reports |

Role grants:
- `admin`: all 6 codes
- `ceo` / exec roles: `reports.view`, `reports.run`, `reports.export`

---

## Tests

### `backend/tests/test_gap013_report_builder_access.py`

20 focused unit tests; no DB required.

| Group | Tests |
|---|---|
| Registry/seed contracts | `reports` in MODULE_DEFINITIONS, not ENDPOINT_ROUTE_DEFINITIONS; all 6 codes in registry; all 6 in seed; admin has all 6; admin has at minimum view/run/admin |
| Route registration | `register_module_routes` produces no errors; report-builder paths appear in the registered router |
| Data source validation | Known source+field returns `True`; unknown source returns `False`; unknown field returns `False`; catalog has required sources; each source has `table` and `fields` |
| Python-level filter helper | `eq`, `neq`, `gt`, `lt`, `between`, `like`, `in`, `is_null`, `is_not_null` each produce correct row subsets |

All 20 passed. Full regression: 270 passed, 7 pre-existing failures (security async/coroutine issue and worktree-path migration read issue) unchanged.

---

## Known Limitations

| Area | Limitation |
|---|---|
| RLS enforcement | RLS rules exist in `rb_report_rls` but are not enforced at query time; access is gated only by `require_permission` |
| Filter execution | All row filtering is Python-level post-fetch; large result sets are pulled from the DB before filtering |
| Schedule execution | Schedules are stored but no scheduler (Celery/APScheduler/cron) triggers them; `ScheduleRunLog` rows must be written by a future scheduler integration |
| AI agents | AI recommendation agents use heuristic/static logic, not ML inference |
| Frontend builder | No drag-and-drop report builder UI exists; frontend pages exist but use static layouts |
| Live migration | `alembic upgrade head` not run in this session; Docker daemon was unavailable |
