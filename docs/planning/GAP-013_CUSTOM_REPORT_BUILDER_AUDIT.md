# GAP-013 Custom Report Builder Depth Audit

## Summary

A custom report builder exists with database models, Pydantic schemas, a service layer, and API endpoints covering report CRUD, execution, CSV export, schedules, dashboards/widgets, RLS policy management, AI recommendations, and an executive summary. The frontend has domain-specific report pages (sales, procurement, finance, etc.) that are independent of the builder API.

**Critical finding:** Almost all report builder endpoints lack authentication and permission guards. The route is registered as a loose `ENDPOINT_ROUTE_DEFINITIONS` entry — not a `MODULE_DEFINITIONS` module — so no `require_permission` dependency is generated for it. Every endpoint beyond the execution layer is effectively unauthenticated.

---

## Business Importance

Custom reporting depth is a Phase 4 / Tier 3 priority. Allows finance, operations, and management users to slice ERP data without developer involvement. The executive summary and AI recommendations elevate it toward a BI-light capability. However, the security and completeness gaps identified below must be closed before this feature can be used safely in production.

---

## Files Inspected

| Path | Purpose |
|---|---|
| `backend/app/api/v1/endpoints/report_builder.py` | API endpoints |
| `backend/app/services/report_builder_service.py` | Business logic, query engine, AI agents |
| `backend/app/models/report_builder.py` | ORM models (9 tables) |
| `backend/app/schemas/report_builder.py` | Pydantic schemas |
| `backend/alembic/versions/f8a9b0c1d2e3_custom_report_builder.py` | Migration |
| `backend/app/core/module_registry.py` | Route/module registration |
| `backend/app/api/v1/endpoints/utilities_reports.py` | Pre-built utility reports (separate surface) |
| `backend/app/services/utilities_reports_service.py` | Utility reports logic |
| `frontend/src/lib/report_builder.ts` | Frontend API client |
| `frontend/src/app/dashboard/reports/` | 8 domain-specific report pages |
| `backend/tests/` | Test file search |

---

## Existing Backend Coverage

### Models (`backend/app/models/report_builder.py`)

9 tables fully defined:

| Model | Table | Key fields |
|---|---|---|
| `ReportDefinition` | `rb_report_definitions` | report_code, report_name, visibility, data_source, query_definition (JSON), is_template, run_count, last_run_at |
| `ReportField` | `rb_report_fields` | report_id, field_path, aggregation, is_group_by, sort_direction, position, visible |
| `ReportFilter` | `rb_report_filters` | report_id, field_path, operator, value, value_to, logical_op, position |
| `ReportCalculatedField` | `rb_calculated_fields` | report_id, expression, alias, data_type |
| `ReportSchedule` | `rb_report_schedules` | report_id, frequency, run_time, recipients (JSON), export_format, active_flag, last_run_at, next_run_at |
| `ReportDashboard` | `rb_dashboards` | dashboard_code, dashboard_name, visibility, owner_user_id |
| `DashboardWidget` | `rb_dashboard_widgets` | dashboard_id, report_id, chart_type, position, width/height, x/y/color axis fields |
| `RBAIRecommendation` | `rb_ai_recommendations` | agent_type, title, body, report_id, score, status, actioned_by, actioned_at |
| `RLSPolicy` | `rb_rls_policies` | report_id, policy_scope (user/role), scope_id, field_path, operator, value |

Enums: `ReportVisibility`, `AggregationType`, `FilterOperator`, `LogicalOperator`, `SortDirection`, `ChartType`, `ScheduleFrequency`, `ExportFormat`, `RBAIAgentType`, `RBAIRecStatus`, `RLSPolicyScope`.

### Schemas (`backend/app/schemas/report_builder.py`)

Full schema coverage: Create/Update/Out for reports, fields, filters, calculated fields, schedules, dashboards, widgets, AI recommendations. `RunRequest` and `RunResult` (columns/rows/metadata). `RBAIRecAck` for status updates.

### Service (`backend/app/services/report_builder_service.py`)

| Function | Reality |
|---|---|
| `_execute_query()` | Executes real SQL (`text(SELECT ...)`) against the DB; fields whitelisted to `DATA_SOURCES` catalog; filters applied post-DB in Python |
| `create_report / get / update / delete / clone / list` | Full DB CRUD against `rb_report_definitions` + child tables |
| `run_report()` | Real execution; increments `run_count`; returns paginated rows |
| `export_report_csv()` | Real CSV generation from query results |
| `seed_templates()` | Inserts seed report definitions from `DATA_SOURCES` |
| `create_schedule / list_schedules / deactivate_schedule` | DB CRUD only; **no background execution** — schedules are stored but never triggered |
| `create_dashboard / list / get / add_widget / delete_widget` | Full DB CRUD |
| `run_builder_assistant()` | Heuristic only — flags reports with `run_count == 0`; not LLM-backed |
| `run_insight_generator()` | Heuristic only — flags high-usage reports (run_count > 5) |
| `run_performance_optimizer()` | Heuristic only — flags reports with no filters |
| `ack_ai_rec()` | DB status update |

### Data Source Catalog

Hardcoded in `DATA_SOURCES` dict (not DB-driven). 10+ sources covering: `sales_orders`, `customers`, `products`, `stock`, `invoices`, `purchase_orders`, and others. Each source maps to a single DB table with a flat field list (no joins, no related fields).

### API Endpoints (`backend/app/api/v1/endpoints/report_builder.py`)

30+ endpoints registered under `/reports-builder` prefix. **Critical issue: no `require_permission` dependencies on any endpoint.** `get_current_user` is imported but not used. `get_db` is the only dependency on most routes.

Specific gaps:
- `GET /catalog` — public (no auth at all)
- `GET /catalog/{data_source}` — public
- `POST /reports`, `GET /reports`, `GET /reports/{id}` — no auth
- `POST /reports/{id}/run`, `GET /reports/{id}/export` — no auth (anyone can run/export any report)
- `POST /ai/run-*` — no auth (anyone can trigger AI agent runs)
- `POST /rls`, `PATCH /rls/{id}`, `DELETE /rls/{id}` — no auth (anyone can create/modify RLS policies)
- `GET /executive-summary` — no auth (exposes cross-module KPIs)

### Module Registry

`report_builder` registered as `ENDPOINT_ROUTE_DEFINITIONS` (loose route), **not** `MODULE_DEFINITIONS`. This means:
- No permission actions defined for the report builder module
- No `require_permission("reports", "view")` is generated anywhere
- No seed permissions exist for report builder
- No role-based access control path for report builder

### Utilities Reports

`utilities_reports.py` registered as a separate `ENDPOINT_ROUTE_DEFINITIONS` entry. 15 pre-built utility monitoring reports. These also lack `require_permission` guards based on inspection of the registry entry (loose route, not module-owned).

### Migration

`f8a9b0c1d2e3_custom_report_builder.py` — creates all 9 `rb_*` tables. Migration revision ID is not in the `20260515_*` date-prefixed sequence. Needs verification that it is in the Alembic chain and that the head reflects it.

---

## Existing Frontend Coverage

### Frontend API Client (`frontend/src/lib/report_builder.ts`)

Complete client covering all backend surfaces: catalog, CRUD, run/export, schedules, dashboards, widgets, AI recommendations. Uses `apiClient` (auth-aware).

### Frontend Report Pages (`frontend/src/app/dashboard/reports/`)

8 domain-specific pages: finance, inventory, marketing, payments, procurement, production, sales, and a main reports index. These pages appear to be standalone domain report views, **not connected to the custom report builder API**. They likely call domain-specific endpoints (e.g., `/api/v1/sales/orders`) directly rather than using `report_builder.ts`.

There is **no dedicated report builder UI** — no drag-and-drop field selection, no builder canvas, no filter construction UI, no dashboard editor. The `report_builder.ts` client exists but no frontend page consumes it.

---

## Existing Permissions / Roles / Scopes

**None.** The report builder has no entries in `MODULE_DEFINITIONS`, no permission actions, and no seed permission codes. RLS policies are defined at the data level (field-level row filtering) but there is no role-based access control at the API surface level.

---

## Existing Migrations

- `f8a9b0c1d2e3_custom_report_builder.py` — creates `rb_*` tables. Not in the `20260515_*` date-prefixed sequence; relationship to current head unknown without running `alembic heads`.

---

## Existing Tests

**None** for the report builder. No test file in `backend/tests/` covers `report_builder` functionality. The 5 test files that exist cover security hardening, attack simulation, GAP-006 integrations, and GAP-011 HR/payroll.

---

## Existing Documentation

No implementation notes file exists for GAP-013 prior to this audit.

---

## Key Finding 1: No Authentication or Permission Guards

Every endpoint in `report_builder.py` is effectively public. An unauthenticated or unpermissioned user can:
- Browse all report definitions
- Run any report and see its data
- Export full CSV datasets
- Create, modify, and delete reports and dashboards
- Create and delete RLS policies
- Trigger AI agent runs
- View the executive summary with cross-module KPIs

This is a **critical security gap** for any production deployment.

## Key Finding 2: Route Registered as Loose ENDPOINT_ROUTE_DEFINITION

`report_builder` is not in `MODULE_DEFINITIONS`. It has no permission actions, no seed codes, no role assignments. Upgrading to `MODULE_DEFINITIONS` would require defining permission actions (e.g., view, create, edit, run, export, admin), adding seed codes, and assigning roles.

## Key Finding 3: Query Engine Has Significant Limitations

The `_execute_query()` function executes real SQL but:
- **No JOINs** — each report queries exactly one table; no cross-table or multi-source queries
- **No SQL-level aggregation** — `AggregationType` fields (SUM, AVG, COUNT, etc.) are defined in the model/schema but ignored in `_execute_query()`; it always does `SELECT col1, col2 FROM table LIMIT N OFFSET M`
- **Filters applied in Python post-fetch** — not pushed into SQL `WHERE`; for large tables this fetches all rows then filters in memory
- **No GROUP BY** — `is_group_by` field defined but not implemented
- **Calculated fields ignored** — `ReportCalculatedField.expression` is stored but never evaluated during query execution
- **No LIMIT enforcement on aggregation** — if a report has aggregation-type fields, execution silently returns raw rows as if it were a non-aggregated query

## Key Finding 4: RLS Policies Not Enforced During Execution

`rb_rls_policies` table exists and CRUD endpoints allow creating `user`/`role`-scope policies with field-level filtering. However, `_execute_query()` does not consult `RLSPolicy` records at all during execution. RLS policies are stored but never applied.

## Key Finding 5: Schedules Not Executed

`rb_report_schedules` records are created with `frequency`, `run_time`, and `next_run_at` but no background scheduler (Celery, APScheduler, Cron) reads these records and triggers report execution. Schedules are a stub — they describe intent but do nothing.

## Key Finding 6: AI Features Are Heuristic Stubs

The three AI agents (`builder_assistant`, `insight_generator`, `performance_optimizer`) produce recommendations based on simple DB queries (unused reports, high-run-count reports, reports without filters). They do not invoke any LLM or ML model. The `RBAIAgentType` enum and recommendation structure are designed for LLM integration but the implementation is fully heuristic.

## Key Finding 7: Frontend Report Builder UI Missing

The `report_builder.ts` client is fully implemented, but no frontend page uses it. The existing `/dashboard/reports/*` pages are domain-specific views that do not connect to the report builder API. A builder canvas (field picker, filter editor, aggregation config, chart type selector, dashboard editor) would need to be created.

## Key Finding 8: Migration Revision ID Is Not Date-Prefixed

The migration uses revision `f8a9b0c1d2e3` (a hash-style ID), unlike the rest of the migration chain which uses `YYYYMMDD_NNNN` prefixes. Its position in the Alembic chain needs to be verified.

---

## Missing Pieces

- Permission guards on all report builder endpoints
- `MODULE_DEFINITIONS` registration with permission actions and seed codes
- Role assignments for report builder permissions
- SQL-level aggregation (GROUP BY + aggregate functions)
- SQL-level filter pushdown (WHERE clause generation)
- Calculated field evaluation at query time
- RLS policy enforcement in query execution
- Schedule background execution (Celery task or APScheduler job)
- Frontend report builder UI (field picker, filter builder, chart config, dashboard editor)
- Tests for report CRUD, execution, export, and permission checks
- Verification that migration `f8a9b0c1d2e3` is in the active Alembic chain

---

## Partial Pieces

- Data source catalog — defined but static/hardcoded, not DB-driven
- AI recommendations — data layer complete, recommendation logic is heuristic stubs
- RLS — data layer complete, enforcement logic missing
- Schedules — data layer complete, execution trigger missing
- Executive summary — works for cross-module KPI read but unauthenticated
- Frontend API client — complete implementation, no UI consuming it
- Aggregation fields — defined in model/schema, not implemented in query engine

---

## Risks

| Risk | Severity |
|---|---|
| Unauthenticated access to all report data and export | Critical |
| No role-based gating on executive summary | High |
| RLS policies stored but not enforced — false sense of data isolation | High |
| Python-level filter on full table fetch — performance risk on large tables | Medium |
| Aggregation/GROUP BY not implemented — users expect SUM/COUNT but get raw rows | Medium |
| Schedules stored but never triggered — scheduled delivery silently does nothing | Medium |
| No tests — any regression invisible | Medium |

---

## Recommended GAP-013B Design Direction

1. **Promote to MODULE_DEFINITIONS** — add permission actions: `view`, `create`, `edit`, `run`, `export`, `admin`. Add seed codes. Assign to admin and analyst roles.
2. **Add `require_permission` to all endpoints** — minimum `reports.view` on GET routes, `reports.run` on execution, `reports.export` on export, `reports.admin` on RLS/seed.
3. **SQL aggregation** — implement GROUP BY + aggregate function translation in `_execute_query()` based on `ReportField.aggregation` and `is_group_by` flags.
4. **SQL filter pushdown** — generate `WHERE` clause from `ReportFilter` records instead of Python post-filtering.
5. **RLS enforcement** — consult `RLSPolicy` for the current user/role before executing any query.
6. **Migration verification** — confirm `f8a9b0c1d2e3` is in the Alembic chain and run `alembic heads` to verify.
7. **Tests** — add focused tests for permission enforcement, data source validation, and execution output.

Frontend builder UI is deferred — that is a significant UI effort beyond this roadmap slice.

---

## Acceptance Criteria for GAP-013 Completion

| Item | Status |
|---|---|
| All report builder endpoints gated by `require_permission` | TODO |
| `MODULE_DEFINITIONS` registration with permission actions and seed codes | TODO |
| SQL-level filters and aggregation in query engine | TODO |
| RLS policies enforced during execution | TODO |
| Migration `f8a9b0c1d2e3` verified in Alembic chain | TODO |
| Tests for permission enforcement and execution behavior | TODO |
| Audit doc (this file) | DONE |
