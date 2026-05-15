# GAP-013 Custom Report Builder Depth Schema Design

## Summary

GAP-013A found that the report builder's 9 DB tables (`rb_*`) are already well-structured. The critical gaps are in code, not schema: no permission guards, no SQL-level filter/aggregation, no RLS enforcement at query time, no schedule execution. This design document records what schema changes are needed (minimal), what code changes each GAP-013 task will make, and why.

---

## Design Goals

1. **Security first** — add `require_permission` to all endpoints; promote to MODULE_DEFINITIONS.
2. **Query correctness** — push filters into SQL `WHERE`, implement GROUP BY + aggregations in SQL.
3. **RLS enforcement** — consult `rb_rls_policies` on every query execution.
4. **Schedule tracking** — add a run-log table so schedule execution history is auditable.
5. **Migration ownership** — verify and document `f8a9b0c1d2e3` chain position; GAP-013C migration adds only the schedule run log table.
6. **No DB reset** — all changes are additive; existing data is preserved.

---

## Current Model Baseline

All 9 `rb_*` tables already exist and are well-designed (see GAP-013A for full field list). Key baseline facts:

| Table | Status |
|---|---|
| `rb_report_definitions` | Complete. Has `owner_user_id`, `visibility`, `run_count`, `last_run_at`. |
| `rb_report_fields` | Complete. Has `aggregation`, `is_group_by`, `sort_direction`. Aggregation logic not wired. |
| `rb_report_filters` | Complete. Has `operator`, `value`, `value_to`, `logical_op`. Filter pushdown not wired. |
| `rb_calculated_fields` | Complete. `expression` stored but not evaluated. No change needed at schema level. |
| `rb_report_schedules` | Complete. Has `frequency`, `next_run_at`, `last_run_at`. No run log table exists. |
| `rb_dashboards` | Complete. |
| `rb_dashboard_widgets` | Complete. |
| `rb_ai_recommendations` | Complete. |
| `rb_rls_policies` | Complete. Has `data_source`, `scope`, `principal`, `filter_field`, `operator`, `filter_value`. Not consulted at query time. |

Migration `f8a9b0c1d2e3` creates all 9 tables. Alembic history confirms it is the parent of `20260515_0030` (current head) — it is in the active chain.

---

## Required Schema Changes

### Only One New Table: `rb_schedule_run_log`

The existing `rb_report_schedules` table records intent but no execution history. A run log is needed for:
- Auditing when a schedule actually ran
- Detecting stuck/failed scheduled runs
- Showing last execution status in the UI

**New table: `rb_schedule_run_log`**

```
rb_schedule_run_log
───────────────────
run_id          UUID PK default uuid4
schedule_id     UUID FK→rb_report_schedules(schedule_id) ON DELETE CASCADE
report_id       UUID FK→rb_report_definitions(report_id) ON DELETE CASCADE
started_at      TIMESTAMP NOT NULL
completed_at    TIMESTAMP nullable
status          VARCHAR(20) NOT NULL default 'running'  -- running/success/failed/skipped
row_count       INTEGER nullable
export_format   VARCHAR(10) nullable
recipients_sent TEXT nullable  -- JSON list of email addresses notified
error_message   TEXT nullable
```

No other new tables needed. All other improvements are code-only.

### No Changes to Existing Tables

The existing `rb_*` tables do not need new columns for:
- Permission enforcement — handled via service/endpoint code
- SQL aggregation — handled in `_execute_query()` logic
- RLS enforcement — handled in service code reading `rb_rls_policies`
- Calculated field evaluation — deferred; no schema change needed

---

## Module Registry and Permission Design

### Promote from ENDPOINT_ROUTE_DEFINITIONS to MODULE_DEFINITIONS

**Current (must change):**
```python
EndpointRouteDefinition(
    key="report_builder",
    route_prefix="/reports-builder",
    import_path="app.api.v1.endpoints.report_builder",
    tags=('report-builder',),
)
```

**Target:**
```python
ModuleDefinition(
    key="reports",
    label="Report Builder",
    route_prefix="/reports-builder",
    import_path="app.api.v1.endpoints.report_builder",
    permission_actions=("view", "create", "edit", "run", "export", "admin"),
    sidebar_group="Analytics",
    icon_key="bar-chart",
    ai_mode=AIMode.RULE_BASED,
    critical=False,
)
```

### Permission Action Definitions

| Permission Code | What it gates |
|---|---|
| `reports.view` | GET /catalog, GET /reports, GET /reports/{id}, GET /dashboards, GET /ai/recommendations |
| `reports.create` | POST /reports, POST /dashboards, POST /reports/{id}/schedule |
| `reports.edit` | PATCH /reports/{id}, PATCH /rls/{id} |
| `reports.run` | POST /reports/{id}/run, POST /preview |
| `reports.export` | GET /reports/{id}/export |
| `reports.admin` | POST /reports/seed-templates, POST /rls, DELETE /rls/{id}, POST /ai/run-*, GET /executive-summary |

### Seed Role Assignments

| Role | Permissions |
|---|---|
| admin | All 6 permission codes |
| analyst (if exists) | view, create, edit, run, export |
| viewer / readonly | view, run |

`utilities_reports` remains a loose `ENDPOINT_ROUTE_DEFINITIONS` entry for now — it is a monitoring surface, not a builder. Permission guard is a separate follow-up.

---

## Query Engine Design

No schema changes needed. All improvements are in `_execute_query()` in `report_builder_service.py`.

### SQL Filter Pushdown (GAP-013G)

Currently filters are applied post-fetch in Python. Target: generate `WHERE` clause.

Design approach:
- Map `FilterOperator` to SQL operators.
- Build parameterized conditions using `sqlalchemy.text` with bound parameters — never string interpolation.
- Handle `logical_op` as `AND`/`OR` grouping.
- Apply only to fields in `allowed_fields` (whitelist already exists).

Operator mapping:
```
eq          → col = :val
neq         → col != :val
gt          → col > :val
lt          → col < :val
gte         → col >= :val
lte         → col <= :val
between     → col BETWEEN :val AND :val_to
in          → col IN (:val)  (comma-split value string)
like        → col ILIKE :val
is_null     → col IS NULL
is_not_null → col IS NOT NULL
```

### SQL Aggregation and GROUP BY (GAP-013G)

Currently all queries do `SELECT col1, col2 FROM table`. Target: detect group-by intent and emit proper SQL.

Design approach:
- If ANY `ReportField` has `is_group_by=True` or `aggregation != NONE`:
  - GROUP BY fields: emit as plain columns in SELECT + GROUP BY clause.
  - Aggregated fields: wrap in aggregate function (`SUM("col")`, `COUNT("col")`, etc.).
  - `COUNT_DISTINCT` → `COUNT(DISTINCT "col")`.
- If no group-by fields, fall back to flat SELECT (current behavior).
- Only fields in `allowed_fields` can appear in the query (whitelist enforced).

### RLS Enforcement (GAP-013G)

Design approach:
- Before executing any query, load active `RLSPolicy` records for the current user:
  - `scope=USER` → match `principal == str(user.id)`
  - `scope=ROLE` → match `principal in [role.name for role in user.roles]`
- Filter policies by `data_source == current_data_source`.
- Translate each active RLS policy into an additional `WHERE` condition using the same operator mapping as filter pushdown.
- Append RLS conditions to the query using `AND` (most restrictive).
- This requires passing `user` into `_execute_query()` and `run_report()`.

---

## Schedule Execution Design (Deferred to Later GAP)

`rb_schedule_run_log` table (defined above) is the schema foundation. Actual background job execution (Celery task, APScheduler, or cron) is deferred beyond GAP-013 — it requires a task runner infrastructure decision. GAP-013C adds the table only. The background trigger is a follow-up.

---

## Migration Scope for GAP-013C

Single additive migration:

```
revision: 20260515_0040
parent:   20260515_0030
message:  report_builder_schedule_run_log
```

DDL:
```sql
CREATE TABLE rb_schedule_run_log (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES rb_report_schedules(schedule_id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES rb_report_definitions(report_id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    row_count INTEGER,
    export_format VARCHAR(10),
    recipients_sent TEXT,
    error_message TEXT
);
CREATE INDEX ix_rb_schedule_run_log_schedule_id ON rb_schedule_run_log(schedule_id);
CREATE INDEX ix_rb_schedule_run_log_started_at ON rb_schedule_run_log(started_at);
```

Migration uses `_has_table` guard (offline-safe pattern from GAP-012C).

---

## Schema and API Compatibility

- All existing `rb_*` tables unchanged — no column renames, no type changes.
- Existing report definitions, fields, filters, schedules, dashboards, widgets, and AI recommendations are unaffected.
- Migration `f8a9b0c1d2e3` confirmed in chain (parent of `20260515_0030`). No re-creation needed.
- Module registry change: removing `report_builder` from `ENDPOINT_ROUTE_DEFINITIONS` and adding `reports` to `MODULE_DEFINITIONS` changes the route registration logic. Routes remain at `/reports-builder`. Permission codes `reports.*` are new; no existing codes are removed.

---

## Service Layer Design

### `report_builder_service.py` Changes (GAP-013F/G)

1. `_execute_query(db, data_source, fields, filters, limit, offset, user=None)` — add `user` parameter for RLS.
2. `_build_where_clause(filters, allowed_fields)` — new helper; returns SQLAlchemy `WHERE` fragment.
3. `_build_rls_conditions(db, user, data_source, allowed_fields)` — new helper; queries `RLSPolicy` and returns conditions.
4. `_build_select_columns(fields, allowed_fields)` — new helper; detects aggregation intent, returns SELECT expressions and GROUP BY fields.
5. `run_report(db, report_id, req, user)` — add `user` parameter; pass to `_execute_query`.

All changes are additive to existing functions; no existing public API surface removed.

---

## Frontend Design Implications (Not in GAP-013 Scope)

The frontend `report_builder.ts` client is complete and correct. No frontend changes are in scope for GAP-013B through GAP-013L. A dedicated frontend builder UI (field picker, filter editor, chart config, dashboard editor) is a future Phase 4+ deliverable.

---

## Test Strategy

GAP-013J will add focused tests:
- Permission enforcement: unauthenticated request → 401/403; correct permission → 200.
- Data source validation: unknown data source → 400.
- SQL filter pushdown: filter on a known field reduces rows; filter on unknown field is rejected.
- RLS enforcement: user with RLS policy sees fewer rows than admin with no policy.
- Aggregation: report with SUM field returns aggregated rows, not raw rows.

---

## Acceptance Criteria for GAP-013B

| Item | Status |
|---|---|
| Migration scope defined (`rb_schedule_run_log`) | DONE |
| Permission action set defined | DONE |
| Module registry promotion plan documented | DONE |
| SQL filter pushdown design documented | DONE |
| SQL aggregation design documented | DONE |
| RLS enforcement design documented | DONE |
| Backward compatibility confirmed | DONE |
| `f8a9b0c1d2e3` chain position verified | DONE (parent of 20260515_0030) |
