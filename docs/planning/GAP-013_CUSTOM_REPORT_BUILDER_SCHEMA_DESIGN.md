# GAP-013 Custom Report Builder Schema Design

## Summary

GAP-013 should harden the existing report builder rather than replace it. The repository already has a report-builder model set, service, endpoint, frontend route group, and an older migration. The next implementation slice should reconcile missing schema ownership, add explicit module permissions, enforce report visibility and data-source access, and make row-level security real during report execution.

The correct approach is additive:

- keep `/api/v1/reports-builder`
- keep `/dashboard/report-builder/*`
- keep existing `rb_*` table names where practical
- add only missing columns/tables/indexes/constraints
- avoid deleting existing report definitions, schedules, dashboards, or templates
- move security and execution decisions into services before adding advanced features

## Current Schema Baseline

Existing ORM models:

- `ReportDefinition`
- `ReportField`
- `ReportFilter`
- `ReportCalculatedField`
- `ReportSchedule`
- `ReportDashboard`
- `DashboardWidget`
- `RBAIRecommendation`
- `RLSPolicy`

Existing migration:

- `backend/alembic/versions/f8a9b0c1d2e3_custom_report_builder.py`

Known migration ownership gap:

- `rb_rls_policies` exists in ORM usage but was not found in the inspected migration.
- Some ORM child relationships are not fully reflected by explicit migration foreign keys.
- Existing migration is not reconciliation-style and may not be duplicate-safe against dirty development databases.

## Design Goals

- Make report-builder schema deterministic under Alembic.
- Preserve existing report definitions and dashboards.
- Add explicit security metadata for ownership, visibility, execution, export, and scheduling.
- Apply ERP permission/scope rules before data leaves the backend.
- Keep SQL generation metadata-driven and whitelist-based.
- Avoid arbitrary user-written SQL in this slice.
- Support CSV now while preparing cleanly for XLSX/PDF later.
- Support schedules as auditable definitions even if worker delivery remains a later task.

## Module Ownership Design

Promote `report_builder` into `MODULE_DEFINITIONS`.

Module route:

- route prefix: `/reports-builder`
- import path: `app.api.v1.endpoints.report_builder`
- frontend base: `/dashboard/report-builder`

Recommended module actions:

- `view`
- `create`
- `edit`
- `delete`
- `run`
- `export`
- `schedule`
- `dashboard`
- `rls_admin`
- `ai`
- `manage_templates`

Keep `analytics.view` as a compatibility navigation fallback only if needed, but backend report-builder access should use `report_builder.*` permissions.

## Permission Design

Recommended permission keys:

- `report_builder.view`: view report-builder catalog and permitted report metadata
- `report_builder.create`: create saved reports
- `report_builder.edit`: edit owned or permitted reports
- `report_builder.delete`: deactivate saved reports
- `report_builder.run`: execute permitted reports
- `report_builder.export`: export permitted report results
- `report_builder.schedule`: create/deactivate report schedules
- `report_builder.dashboard`: create dashboards and dashboard widgets
- `report_builder.rls_admin`: manage report row-level security policies
- `report_builder.ai`: run rule-based report-builder recommendations
- `report_builder.manage_templates`: seed and maintain template reports

Role grants should be conservative:

- Admin / Owner / Super Admin: full report-builder permission set
- CFO / Finance Manager / Data Manager / Auditor: view, run, export, and dashboard where appropriate
- Functional managers: view/run reports only when they also have underlying module access
- Normal analytics viewers: view/run limited reports, not delete, RLS admin, template seeding, or broad export

## Underlying Data-Source Access Design

A user should need two layers of access to use a report data source:

1. report-builder action permission
2. underlying module permission for the data source

Examples:

- `sales_orders` requires `report_builder.run` plus `sales.view` or a scoped sales view permission.
- `purchase_orders` requires `report_builder.run` plus procurement visibility.
- `timesheets` requires `report_builder.run` plus timesheet/HR visibility according to the module convention.
- payroll or finance sources should require their specific module permissions and should not be exposed through generic analytics access alone.

Add a source access helper in service code:

- `report_data_source_module(data_source)`
- `can_view_report_data_source(user, data_source)`
- `ensure_report_builder_action(user, action, report_or_source)`

The static catalog should remain the source-owned whitelist for tables and fields, but each source entry should define:

- `module`
- `view_permission`
- `export_permission` where different
- optional `scope_type`
- optional `sensitive` flag
- optional `default_date_field`

## Report Visibility Design

Existing visibility values should remain:

- `private`
- `team`
- `global`

Recommended behavior:

- private: owner, admin, or explicit share can view/run
- team: owner, team/role share, or admin can view/run
- global: users with report-builder permission and underlying data-source permission can view/run

Additive schema options:

- keep `owner_user_id`
- add `owner_role_id` nullable where role/team ownership is needed
- add `shared_role_ids` JSONB nullable for a lightweight first slice
- add `shared_user_ids` JSONB nullable only if current project patterns favor JSON list sharing

Preferred first slice:

- avoid a full report-sharing join table unless immediate UI use needs it
- add only `owner_role_id` and `shared_role_ids` if team visibility must become enforceable now
- enforce owner/global behavior first, document team sharing as role-based follow-up if needed

## RLS Schema Design

`RLSPolicy` should be schema-owned with table:

- `rb_rls_policies`

Columns:

- `policy_id` UUID primary key
- `policy_name` string required
- `data_source` string required
- `scope` enum/string: `user`, `role`
- `principal` string required
- `filter_field` string required
- `operator` enum/string using existing filter operators
- `filter_value` text required
- `active_flag` boolean required default true
- `description` text nullable
- `created_by` string nullable
- `created_at` datetime
- `updated_at` datetime

Recommended indexes:

- `(data_source, active_flag)`
- `(scope, principal)`
- `(data_source, scope, principal, active_flag)`

Recommended constraints:

- `policy_name` not empty where project migration helpers support it
- `filter_field` should be validated in service against the data-source catalog
- `operator` should be validated against allowed operators

RLS execution rule:

- RLS policies are not just administrative records; they must be appended to the query plan before data retrieval.
- If a source is sensitive and no applicable RLS exists, default should be deny or require broad all-scope permission.
- RLS filters must be validated against the source catalog before use.

## Migration Reconciliation Scope for GAP-013C

GAP-013C should add a new additive reconciliation migration.

Suggested migration name:

- `20260515_0070_report_builder_hardening.py`

The migration should:

1. Create `rb_rls_policies` if missing.
2. Add missing foreign keys where safe:
   - `rb_report_fields.report_id -> rb_report_definitions.report_id`
   - `rb_report_filters.report_id -> rb_report_definitions.report_id`
   - `rb_calculated_fields.report_id -> rb_report_definitions.report_id`
   - `rb_report_schedules.report_id -> rb_report_definitions.report_id`
   - `rb_dashboard_widgets.dashboard_id -> rb_dashboards.dashboard_id`
   - `rb_dashboard_widgets.report_id -> rb_report_definitions.report_id`
3. Add missing indexes for common lookups:
   - report `data_source`
   - report `owner_user_id`
   - report `visibility`
   - active report definitions
   - schedule active/next-run fields
   - dashboard owner/visibility
   - AI recommendation status/type
   - RLS data-source/principal fields
4. Add optional additive columns where the service needs them:
   - `owner_role_id`
   - `shared_role_ids`
   - `last_exported_at`
   - `last_exported_by`
   - `last_scheduled_run_at`
   - `last_scheduled_status`
   - `last_error`
5. Avoid dropping or renaming existing report-builder tables.
6. Avoid changing enum storage destructively.
7. Use `table_exists`, `column_exists`, `index_exists`, and `foreign_key_exists` helpers to support dirty dev DBs.

Do not implement an advanced schedule worker or binary export table in GAP-013C unless later tasks require it.

## Model Design

Keep existing models and extend them only as needed.

Recommended first-slice model additions:

`ReportDefinition`:

- `owner_role_id`
- `shared_role_ids`
- `last_exported_at`
- `last_exported_by`

`ReportSchedule`:

- `last_scheduled_run_at`
- `last_scheduled_status`
- `last_error`

`RLSPolicy`:

- ensure ORM matches the migration exactly

Avoid adding a full report execution history table in this slice unless the team wants audit logging now. Existing audit infrastructure can be used later for export/run event logging.

## Schema/API Contract Design

Add or extend schemas to expose:

- report access hints:
  - `can_view`
  - `can_edit`
  - `can_delete`
  - `can_run`
  - `can_export`
  - `can_schedule`
  - `view_only`
  - `reason`
- catalog source access:
  - `module`
  - `view_permission`
  - `can_use`
  - `can_export`
  - `sensitive`
- RLS policy create/read/update schemas in `backend/app/schemas/report_builder.py`
- export format validation
- schedule recipient validation where possible
- limit/offset bounds on run requests

Recommended `RunRequest` bounds:

- `limit`: minimum 1, maximum 1000 for UI runs
- export can use a larger service-controlled cap, such as 10000, only with export permission
- `offset`: minimum 0

## Service Design

Add or extend service helpers rather than growing `report_builder.py`.

Recommended services:

- keep `backend/app/services/report_builder_service.py`
- add `backend/app/services/report_builder_access_service.py` if separation keeps the file readable

Core helper responsibilities:

- action permission checks
- report visibility checks
- data-source module permission checks
- RLS policy lookup and validation
- safe query plan creation
- export gating
- schedule gating
- access hint generation

The query runner should:

- validate data source
- validate selected fields
- validate filters
- merge saved filters, runtime filters, and RLS filters
- push safe filters into SQL where possible
- cap limit/offset
- return clear errors instead of swallowing every exception into an empty result

Arbitrary SQL input should remain out of scope.

## API Endpoint Design

Apply permission dependencies consistently:

- catalog:
  - `report_builder.view`
  - filter sources by underlying module permission
- create report:
  - `report_builder.create`
- list/detail:
  - `report_builder.view`
  - service enforces report visibility
- update:
  - `report_builder.edit`
  - service enforces owner/admin/visibility rules
- delete:
  - `report_builder.delete`
- clone:
  - `report_builder.create` plus source report visibility
- seed templates:
  - `report_builder.manage_templates`
- run:
  - `report_builder.run` plus underlying source permission and RLS
- export:
  - `report_builder.export` plus run permission and underlying source permission
- preview:
  - `report_builder.view` plus underlying source permission
- schedules:
  - `report_builder.schedule`
- dashboards/widgets:
  - `report_builder.dashboard`
- AI recommendations:
  - `report_builder.ai`
- executive summary:
  - either `report_builder.view` plus relevant underlying module permissions or keep as analytics-owned with explicit analytics permission
- RLS:
  - `report_builder.rls_admin`

Endpoint response paths should remain stable.

## Frontend Design Implications

GAP-013H should:

- keep the existing report-builder page group
- replace direct `fetch` in `frontend/src/lib/report_builder.ts` with shared API client conventions
- move RLS and executive-summary calls into `report_builder.ts`
- guard pages with dedicated report-builder permissions
- hide/disable actions based on permission:
  - create report
  - delete report
  - clone report
  - run report
  - export
  - schedule
  - dashboard/widget management
  - seed templates
  - RLS management
  - AI generation
- show view-only state for reports returned with limited access
- keep current table/list layout unless deeper UX work is explicitly required

## Test Strategy

GAP-013J should add focused tests for:

- registry includes `report_builder` as a module-owned route
- seed permissions include all required report-builder actions
- report-builder endpoint imports cleanly
- catalog/run/export endpoints declare dedicated permission dependencies
- RLS table/model/migration ownership exists
- source access helper denies use of a data source when underlying module view is absent
- export requires export permission
- template seeding requires manage-template permission
- normal analytics viewer does not get `rls_admin`, `delete`, or `manage_templates`
- frontend nav/page source uses dedicated report-builder permissions instead of only `analytics.view`

Prefer pure contract/service tests first so no live PostgreSQL is required.

## Documentation Requirements

GAP-013K should document:

- report builder permission model
- data-source catalog rules
- report visibility rules
- RLS behavior and limits
- run/export behavior
- schedule behavior and current worker limitations
- dashboard/widget behavior
- AI recommendation behavior as rule-based
- commands and checks run
- known limitations and follow-ups

## Acceptance Criteria for GAP-013B

GAP-013B is complete when:

- Current schema baseline is documented.
- Additive migration scope is clear.
- Permission and module ownership design is explicit.
- Report visibility and source-access rules are defined.
- RLS ownership and execution design are defined.
- Service/API/frontend implications are documented.
- Test strategy is ready for implementation tasks.
- No production DB or destructive schema action has been run.
