# M24.S02.T002 — Actual consumption transaction

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` and the M24 interpretation in `coordination/milestones/M24/EXECUTION_PLAN_V01.md` define the scope.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012/013 and `coordination/AUDIT_POLICY.md` critical production-consumption, actor/scope, repeat-request, linked-history, migration, and rollback requirements.

## Starting synchronization and preserved work

- Verified canonical Git root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Fetched `origin/main` before starting. Local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`, ahead/behind `0/0`.
- The worktree contains unrelated owner/project changes, including generated frontend build output. All were preserved; no reset, clean, stash, or broad staging was used.
- Root `TASKS.md` explicitly selected `M24.S02.T002` after T001 implementation; no matching unanswered owner decisions were present.

## Implementation

- Actual consumption now requires an exact posted RAW_ISSUE line from the same in-progress production order. Material, lot, issued quantity, and UOM are taken from that line.
- Added an idempotency key and unique database index for consumption events. A repeat with identical actor/request returns the existing row; mismatched key reuse is rejected.
- Cumulative consumption/return/scrap linked to an issue line cannot exceed its issued quantity. Unlinked legacy consumption of the same order/material blocks new linked consumption rather than inventing an allocation.
- Authenticated production-warehouse edit/view scope is required for create/list. Optional work-order attribution must belong to the order, be in progress, and match any issue-line work order.
- Consumption creates an attributable `ProductionConsumption` event and a variance snapshot without decrementing inventory again; the prior issue movement remains the inventory event. Returns and scrap remain separate task scopes.
- Added a migration and task-owned disposable-PostgreSQL acceptance cases for database targeting, exact issue-line linkage, no second stock mutation, idempotent retry, key reuse, and over-consumption.

## Checks performed

- `python -m py_compile` on changed backend modules and the new acceptance module: passed.
- Ruff on the changed material-flow backend and new acceptance module: passed.
- Targeted frontend ESLint on material-flow types: passed.
- `alembic heads`: one head, `20261108_0015`.
- Targeted `git diff --check`: exited 0.
- PostgreSQL tests, migration application, API tests, and full frontend build were not run; they remain in the consolidated M24 milestone acceptance campaign. No database-test PASS is claimed.

## Changed files for this task

- `backend/alembic/versions/20261108_0015_m24_consumption_idempotency.py`
- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/models/material_flow.py`
- `backend/app/schemas/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s02_t002_actual_consumption_db.py`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `frontend/src/lib/materialFlow.ts`

## Pending acceptance

Disposable-PostgreSQL migration and behavior checks, API authorization tests, rollback/concurrency and legacy-history cases, frontend build, and consolidated independent code/security reviews remain pending until M24 milestone acceptance.
