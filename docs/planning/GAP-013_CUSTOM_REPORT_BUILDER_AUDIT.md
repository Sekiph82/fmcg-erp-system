# GAP-013 Custom Report Builder Depth Audit

## Summary

GAP-013 is not starting from zero. The repository already has a custom report-builder module with ORM models, schemas, a backend service, an API endpoint, an Alembic migration, frontend pages, a data-source catalog, saved reports, report execution, CSV export, schedules, dashboard widgets, row-level security policy screens, AI recommendation helpers, and an executive summary page.

The current implementation is useful as a foundation, but it is not yet enterprise-grade for an ERP/MES report engine. The most important risks are missing authentication and permission dependencies on most report-builder endpoints, weak module ownership, no dedicated report-builder permission contract, incomplete row-level security enforcement, raw SQL execution without database-level filter pushdown, partial export/schedule behavior, frontend direct `fetch` usage, and lack of focused tests.

## Business Importance

ERP users expect reports to be controlled operational artifacts, not just ad hoc queries. A factory reporting layer needs:

- role and scope-aware access to sensitive finance, HR, payroll, quality, production, sales, procurement, and inventory data
- reusable report definitions and templates
- safe query generation from whitelisted data sources and fields
- scheduled report delivery
- export governance
- dashboard widgets and drill-down
- auditability around report creation, execution, export, and sharing
- reliable KPI definitions that managers can use for real decisions

Without deeper hardening, the current report builder can expose broad operational data and allow high-impact report actions without the permission discipline used elsewhere in the ERP.

## Files Inspected

Backend files inspected:

- `backend/app/api/v1/endpoints/report_builder.py`
- `backend/app/services/report_builder_service.py`
- `backend/app/models/report_builder.py`
- `backend/app/schemas/report_builder.py`
- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/api/v1/endpoints/dashboard.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/f8a9b0c1d2e3_custom_report_builder.py`
- `backend/tests/*` search results for report-builder coverage

Frontend files inspected:

- `frontend/src/lib/report_builder.ts`
- `frontend/src/app/dashboard/report-builder/page.tsx`
- `frontend/src/app/dashboard/report-builder/builder/page.tsx`
- `frontend/src/app/dashboard/report-builder/catalog/page.tsx`
- `frontend/src/app/dashboard/report-builder/saved/page.tsx`
- `frontend/src/app/dashboard/report-builder/viewer/page.tsx`
- `frontend/src/app/dashboard/report-builder/dashboards/page.tsx`
- `frontend/src/app/dashboard/report-builder/schedules/page.tsx`
- `frontend/src/app/dashboard/report-builder/rls/page.tsx`
- `frontend/src/app/dashboard/report-builder/ai/page.tsx`
- `frontend/src/app/dashboard/report-builder/executive/page.tsx`
- `frontend/src/components/nav-config.tsx`

Planning/tracker files inspected:

- `TASKS.md`
- `CODEX_PROGRESS.md`
- `docs/planning/ERP_ROADMAP_AND_MANUAL_PLAN.md`
- `docs/planning/ERP_ROADMAP_IMPLEMENTATION_PLAN.md`
- `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md`

## Existing Backend Coverage

The report-builder backend route is registered as:

- `/api/v1/reports-builder`
- endpoint file: `backend/app/api/v1/endpoints/report_builder.py`

Implemented endpoint groups include:

- data catalog:
  - `GET /catalog`
  - `GET /catalog/{data_source}`
- report definitions:
  - create, list, detail, patch, delete, clone
  - seed template reports
- execution/export:
  - run report
  - CSV export
  - preview data source
- schedules:
  - create, list, deactivate
- dashboards/widgets:
  - create/list/detail dashboard
  - add/delete widget
- AI recommendations:
  - builder assistant
  - insight generator
  - performance optimizer
  - list and acknowledge recommendations
- executive summary:
  - cross-module KPI summary
- RLS policy CRUD:
  - create/list/update/delete row-level security policies

The service defines a static `DATA_SOURCES` catalog for sales orders, customers, products, stock, invoices, purchase orders, expenses, timesheets, appraisals, CRM records, kanban cards, training assignments, certifications, notifications, and skill matrix data.

The query runner uses a whitelist of data-source table names and allowed field paths. It constructs simple `SELECT` and `COUNT` SQL from catalog metadata and applies filters in Python after retrieving rows.

## Existing Model and Migration Coverage

Existing ORM model file:

- `backend/app/models/report_builder.py`

Existing models:

- `ReportDefinition`
- `ReportField`
- `ReportFilter`
- `ReportCalculatedField`
- `ReportSchedule`
- `ReportDashboard`
- `DashboardWidget`
- `RBAIRecommendation`
- `RLSPolicy`

Existing enums:

- `ReportVisibility`
- `AggregationType`
- `FilterOperator`
- `LogicalOperator`
- `SortDirection`
- `ChartType`
- `ScheduleFrequency`
- `ExportFormat`
- `RBAIAgentType`
- `RBAIRecStatus`
- `RLSPolicyScope`

Existing migration:

- `backend/alembic/versions/f8a9b0c1d2e3_custom_report_builder.py`

The migration creates the main report-builder tables and several enum types. It does not appear to create the `rb_rls_policies` table even though the ORM and endpoint now use `RLSPolicy`. It also does not define all foreign keys reflected by the ORM relationships, such as report-to-field/filter/schedule relationships and dashboard widget report references. GAP-013B/C should reconcile this carefully rather than assuming the schema is complete.

## Existing Frontend Coverage

The frontend has a substantial report-builder route group:

- `/dashboard/report-builder`
- `/dashboard/report-builder/builder`
- `/dashboard/report-builder/catalog`
- `/dashboard/report-builder/saved`
- `/dashboard/report-builder/viewer`
- `/dashboard/report-builder/dashboards`
- `/dashboard/report-builder/schedules`
- `/dashboard/report-builder/rls`
- `/dashboard/report-builder/ai`
- `/dashboard/report-builder/executive`

Implemented UI behavior includes:

- report-builder home with KPI cards and quick navigation
- template seeding button
- data catalog browser and preview
- report builder form for data source, fields, aggregation, sort, filters, and visibility
- saved reports list with clone/delete/export links
- report viewer with run/export behavior
- dashboard and widget management
- schedule creation/deactivation
- RLS policy management
- AI recommendation generation and acknowledgement
- executive KPI cards

The navigation section exists under `analytics.view`, and all report-builder child pages currently use `analytics.view` for visibility.

## Existing Permissions / Roles / Scopes

Current permission facts:

- Seed permissions include `analytics.view` and `analytics.export`.
- The sidebar report-builder section is guarded by `analytics.view`.
- `backend/app/core/module_registry.py` registers `report_builder` as a loose `EndpointRouteDefinition`, not as a full module definition.
- There is no dedicated `report_builder.*` permission family in seed data.
- Most report-builder API endpoints do not depend on `get_current_user` or `require_permission`.
- RLS policy endpoints use `get_current_user`, but not a dedicated admin/configure permission.

This is the largest security gap in the current slice. The report builder can reach sensitive source tables across modules, so API protection must be stronger than generic navigation visibility.

## Existing Analytics / Dashboard Context

The separate analytics endpoint already uses module-specific permissions for many operational BI surfaces. For example, the inspected analytics endpoint imports `require_permission` and applies module permissions such as inventory view for inventory analytics.

The dashboard summary endpoint uses authenticated-user dependency but not a broad analytics permission dependency. It is separate from the report builder but relevant because the report-builder executive summary performs similar cross-module aggregation directly inside `report_builder.py`.

## Missing Pieces

- Dedicated module definition for `report_builder`.
- Dedicated permission contract, likely:
  - `report_builder.view`
  - `report_builder.create`
  - `report_builder.edit`
  - `report_builder.delete`
  - `report_builder.run`
  - `report_builder.export`
  - `report_builder.schedule`
  - `report_builder.dashboard`
  - `report_builder.rls_admin`
  - `report_builder.ai`
  - `report_builder.manage_templates`
- Permission dependencies on catalog, report CRUD, run, export, preview, schedules, dashboards, AI, executive summary, and RLS endpoints.
- Role grants that do not make every analytics viewer a report admin.
- Schema/migration reconciliation for `rb_rls_policies`.
- Foreign key/index reconciliation for report builder child tables and dashboard widgets.
- Execution-time module permission checks for underlying data sources.
- Enforcement of saved report visibility (`private`, `team`, `global`).
- Actual RLS policy application inside `_execute_query` or a dedicated query planning service.
- Export permission separation and auditability.
- Schedule runner/delivery implementation; current schedules are stored but not executed by a worker.
- XLSX/PDF export support; current export is CSV only despite enum support for more formats.
- Pivot-table support.
- Drill-down dashboard behavior.
- Calculated-field execution. Calculated fields are stored but not used by the run engine.
- Aggregation/group-by execution. Aggregation fields are stored but the current SQL path selects raw columns.
- Runtime filter validation beyond simple request shape.
- Query limits and guardrails for expensive reports beyond the passed limit.
- Frontend permission/action gating beyond navigation.
- Shared API client usage. `frontend/src/lib/report_builder.ts`, RLS page, and executive page use direct `fetch`.
- Focused backend tests for permissions, query safety, RLS, export, schedule, and schema ownership.
- Focused frontend tests for page guards and action visibility.

## Partial Pieces

- SQL safety is partially addressed by static data-source and field whitelists, but filters are applied after the database query and RLS is not enforced in the query path.
- Templates exist and can be seeded, but template management is not permission-protected.
- Schedules exist in schema/service/API, but no execution worker or delivery flow was found in this audit.
- Dashboards and widgets exist, but no clear drill-down contract or widget-level permission filtering was found.
- AI recommendations are rule-based helpers, not true predictive AI. This is acceptable if documented, but the UI should not imply deeper AI capability than implemented.
- Export exists as CSV, but it is not protected by `analytics.export` or a dedicated report export permission.
- The frontend route group is broad and useful, but it lacks page-level guards and action-level permission gating.

## Risks

- Unauthenticated callers may be able to create, list, run, export, schedule, and delete reports because most report-builder endpoints lack auth dependencies.
- Analytics viewers can see the report-builder navigation, but backend routes are not protected consistently by equivalent permissions.
- Sensitive finance, HR, payroll, customer, supplier, quality, and inventory data can become visible through generic report execution unless data-source permissions and scopes are enforced.
- Row-level security policies can be managed through authenticated-only endpoints and are not applied to report execution.
- CSV export can return up to 10,000 rows without explicit export permission.
- Schedule definitions could be created without permission if endpoint auth remains absent.
- Missing migration ownership for RLS policies can cause runtime failures in a fresh database.
- Report field/filter child rows may not be fully protected by database constraints if foreign keys remain incomplete in migration history.
- Frontend direct `fetch` calls may bypass shared API client auth/error conventions.
- Source files contain garbled separator/comment glyphs in report-builder code and client files, which is cosmetic but should be cleaned when files are touched.

## Recommended GAP-013B Design Direction

GAP-013B should design a hardening slice rather than replacing the report builder.

Recommended direction:

- Promote `report_builder` into `MODULE_DEFINITIONS`.
- Keep `/api/v1/reports-builder` and `/dashboard/report-builder/*` routes stable.
- Add dedicated report-builder permission keys and seed role grants.
- Reconcile migration ownership for `rb_rls_policies`, child-table foreign keys, indexes, and enum duplicate-safety.
- Move permission and execution guard logic into a report-builder access/query service.
- Require both report-builder permission and underlying data-source module permission before catalog/run/export access.
- Enforce report visibility:
  - private: owner/admin only
  - team: owner/team/role policy
  - global: users with view/run and underlying data-source permission
- Apply RLS policies during query planning before data is returned.
- Keep SQL generation whitelist-based; avoid arbitrary SQL entry.
- Push safe filters into SQL where possible instead of filtering only after limited row retrieval.
- Separate `run`, `export`, `schedule`, `dashboard`, `rls_admin`, `ai`, and template-management permissions.
- Standardize frontend calls on the shared API client and add page/action guards.
- Add focused contract tests before expanding advanced features.

## Acceptance Criteria for GAP-013 Completion

GAP-013 should be considered complete only when:

- `report_builder` is module-owned and exposed in the registry/manifest consistently.
- Dedicated report-builder permissions are seeded idempotently.
- Report-builder routes require authentication and appropriate permissions.
- Run/export operations require both report-builder permission and underlying module visibility.
- RLS policies are schema-owned and applied to report execution.
- Saved report visibility is enforced.
- Dangerous actions such as delete, export, schedule, template seeding, AI generation, and RLS management are not available to normal analytics viewers by default.
- Frontend nav/pages/actions use dedicated permissions and shared API client conventions.
- Migration ownership is deterministic for all report-builder tables used by the ORM.
- Focused backend tests cover permission contracts, query safety, RLS enforcement, export gating, and route imports.
- Frontend type-check/lint pass after report-builder UI changes.
- Documentation explains current report-builder behavior, limitations, permissions, RLS, export, schedule, and follow-up boundaries.
