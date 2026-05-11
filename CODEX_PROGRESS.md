# CODEX PROGRESS

## Last Updated
2026-05-11T12:34:30+03:00

## Last Completed Task
GAP-003A: Audited current permission and security hardening coverage across auth, RBAC, registry, seed roles, finance endpoints, and sidebar visibility.

## Current Working Task
None. Next task is GAP-003B: Design data model/schema: Permission and Security Hardening Across All New Modules.

## Files Changed in Last Run
- `frontend/src/lib/finance.ts`
- `frontend/src/app/dashboard/finance/accounting/controls/page.tsx`
- `backend/app/api/v1/endpoints/finance.py`
- `backend/app/services/finance_service.py`
- `backend/app/schemas/finance.py`
- `backend/app/schemas/inventory.py`
- `backend/app/schemas/procurement.py`
- `backend/app/schemas/production.py`
- `backend/app/schemas/landed_cost.py`
- `backend/app/models/finance.py`
- `backend/app/models/inventory.py`
- `backend/app/models/procurement.py`
- `backend/app/models/production.py`
- `backend/app/models/landed_cost.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/20260511_0020_operational_posting_integration.py`
- `docs/planning/GAP-002_POSTING_INTEGRATION_SCHEMA_DESIGN.md`
- `TASKS.md`
- `CODEX_PROGRESS.md`
- `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md`
- `docs/planning/ERP_ROADMAP_IMPLEMENTATION_PLAN.md`
- `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`
- Plus the GAP-001 files already listed in the previous checkpoint.

## Tests/Checks Run
- GAP-001 final backend compile/import, focused pytest, Alembic head/history/offline SQL, frontend type-check, and documentation checks: passed except live DB migration, which is blocked by Docker/PostgreSQL availability.
- GAP-002A audit content check for GRNI, WIP, `StockMovement`, `AccountingPostingBatch`, and `assert_posting_period_open`: passed.
- GAP-002A audit file-size sanity check: passed.
- GAP-002B design content check for `operational_posting_events`, `inventory_account_mappings`, `posting_batch_id`, `journal_entry_id`, `assert_posting_period_open`, key posting event examples, and idempotency: passed.
- GAP-002B design file-size sanity check: passed.
- GAP-002C migration py_compile: passed.
- GAP-002C Alembic heads: passed; head is `20260511_0020`.
- GAP-002C Alembic history from `20260511_0010` to `20260511_0020`: passed.
- GAP-002C offline SQL generation from `20260511_0010` to `head`: passed.
- GAP-002C live `alembic upgrade head`: blocked by PostgreSQL connection refusal (`ConnectionRefusedError [WinError 1225]`).
- GAP-002D model py_compile: passed.
- GAP-002D model import/table-column smoke check: passed.
- GAP-002D SQLAlchemy `configure_mappers()`: passed. Existing unrelated mapper overlap warnings were emitted for `DimValue`, `CostCenter`, and `TaskDependency`.
- GAP-002E schema py_compile: passed.
- GAP-002E Pydantic smoke validation: passed, including operational posting event creation, posting-link read enum parsing, and inventory account mapping scope validation.
- GAP-002F service py_compile: passed.
- GAP-002F service smoke check: passed for deterministic idempotency key construction, account-mapping specificity, and posting-link application. Existing unrelated mapper overlap warnings were emitted for `DimValue`, `CostCenter`, and `TaskDependency`.
- GAP-002G finance endpoint py_compile: passed.
- GAP-002G route smoke check: passed for operational posting events and inventory account mapping endpoints.
- GAP-002H frontend type-check: passed with `npm.cmd run type-check`.
- GAP-002I permission inspection: passed. Finance module registry includes `configure`; seed definitions include `finance.configure`; CFO and finance manager role templates include `finance.configure`.
- GAP-002J focused pytest: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_gap002_posting_integration.py -q` passed, 6 tests.
- GAP-002J regression pytest: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_gap001_accounting_core.py backend/tests/test_gap002_posting_integration.py -q` passed, 15 tests. Existing unrelated mapper overlap warnings remain.
- GAP-002K documentation content check: passed for implemented-scope warning, endpoints, permissions, test commands, and live DB blocker.
- GAP-002L backend compile: passed for changed models, schemas, service, endpoint, and migration files.
- GAP-002L regression pytest: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_gap001_accounting_core.py backend/tests/test_gap002_posting_integration.py -q` passed, 15 tests. Existing unrelated mapper overlap warnings remain.
- GAP-002L Alembic heads/history/offline SQL: passed; current head is `20260511_0020`.
- GAP-002L frontend type-check: `npm.cmd run type-check` passed.
- GAP-002L documentation content check: passed.
- GAP-002L live `alembic upgrade head`: blocked by PostgreSQL connection refusal (`ConnectionRefusedError [WinError 1225]`).
- GAP-003A audit content check: passed for `get_current_user`, `require_permission`, module registry, sidebar filtering, `finance.configure`, operational posting permissions, route-permission audit needs, manifest drift, and no-code-change statement.
- GAP-003A audit file-size sanity check: passed.

## Known Issues
- `GAP-028K` remains blocked because screenshots have not been captured.
- Live Alembic upgrade still needs to be rerun when Docker/PostgreSQL is available.
- GAP-002 foundation slice is complete, but automatic GL posting from live GRN/production/landed-cost workflows is intentionally not yet wired and remains documented follow-up work.
- GAP-003A found that auth/RBAC foundations exist, but full registry coverage, backend-owned sidebar manifest migration, route permission audit tests, and action-level frontend permission audits remain to be designed/implemented.

## Next Resume Point
Continue with GAP-003B. Design the smallest safe data/model/schema direction for permission and security hardening. Use `docs/planning/GAP-003_PERMISSION_SECURITY_AUDIT.md` as the starting point. Do not implement code until the design task is complete.

## User Action Needed
None for GAP-003B.
