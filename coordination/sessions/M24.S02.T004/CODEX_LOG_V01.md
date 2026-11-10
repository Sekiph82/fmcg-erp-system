# M24.S02.T004 — Scrap/spillage material accounting

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` and the M24 interpretation in `coordination/milestones/M24/EXECUTION_PLAN_V01.md` define the scope.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012/013 and `coordination/AUDIT_POLICY.md` critical inventory, actor/scope, idempotency, linked-history, reconciliation, and reversal controls.

## Starting synchronization and preserved work

- Verified canonical Git root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Fetched `origin/main` before starting; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`, ahead/behind `0/0`.
- Existing local owner/project changes, including generated frontend output, were preserved; no reset, clean, stash, or broad staging was used.
- Root `TASKS.md` explicitly selected `M24.S02.T004`; no matching unanswered owner decisions were present.

## Implementation

- Added an authenticated, idempotent scrap/spillage endpoint tied to a posted reservation-based material issue line and an in-progress production order.
- The request requires a finite positive quantity at 0.001 precision, one explicit reason code (spillage, contamination, damage, process loss, or other), and a nonblank explanation. Cumulative consumption, returns, and scrap cannot exceed the exact issued line.
- Each posting creates a POSTED SCRAP transaction/line linked to the issue line, plus an attributable `ProductionConsumption` scrap event with reason, actor, and remaining variance. The event and flow line commit in one transaction.
- Scrap does not add a second warehouse stock movement or reduce stock again: the issue transaction already removed the quantity from warehouse inventory. This avoids double-counting and leaves unit-cost/financial loss unknown where no verified cost exists.
- Generic material SCRAP drafts cannot be posted or reversed as a substitute; the linked task path is the only route. M24.S04.T003 retains correction/reversal scope.
- Added guarded disposable-PostgreSQL cases for exact database targeting, issue-line linkage, no second stock movement/balance mutation, reconciliation totals, idempotency, key reuse, reason, and quantity ceiling.
- Added migration `20261108_0017` for scrap flow-line lineage and reason code.

## Checks performed

- `python -m py_compile` on changed backend modules and the new acceptance module: passed.
- Ruff on changed material-flow backend modules and the new acceptance module: passed.
- Targeted frontend ESLint on the material issue page and material-flow types: passed.
- SQLAlchemy model import/metadata smoke check: passed.
- `alembic heads`: one head, `20261108_0017`.
- Targeted `git diff --check`: exited 0; Git reported LF-to-CRLF normalization for the changed frontend page.
- PostgreSQL tests, migration application, API tests, and full frontend build were not run; they remain in the consolidated M24 milestone acceptance campaign. No database-test PASS is claimed.

## Changed files for this task

- `backend/alembic/versions/20261108_0017_m24_material_scrap_lineage.py`
- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/models/material_flow.py`
- `backend/app/schemas/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s02_t004_material_scrap_db.py`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `frontend/src/app/dashboard/material-flow/issue/page.tsx`
- `frontend/src/lib/materialFlow.ts`

## Pending acceptance

Disposable-PostgreSQL migration and behavior checks, authorization/warehouse-isolation, rollback/concurrency, frontend build/E2E, reconciliation and correction coverage, and consolidated independent code/security reviews remain pending until M24 milestone acceptance.
