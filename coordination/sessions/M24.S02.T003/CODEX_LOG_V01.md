# M24.S02.T003 — Excess material return

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` and the M24 interpretation in `coordination/milestones/M24/EXECUTION_PLAN_V01.md` define the scope.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012/013 and `coordination/AUDIT_POLICY.md` inventory ledger, authorization, linkage, idempotency, rollback, quality, and reversal controls.

## Starting synchronization and preserved work

- Verified canonical Git root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Fetched `origin/main` before starting; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`, ahead/behind `0/0`.
- The worktree contains unrelated owner/project changes, including generated frontend build output. They were preserved; no reset, clean, stash, or broad staging was used.
- Root `TASKS.md` explicitly selected `M24.S02.T003`; no matching unanswered owner decisions were present.

## Implementation

- Added an authenticated return endpoint tied to a posted issue line. It validates the same production order/source warehouse, exact original stock and location identity, usable source location, order state, and unused quantity after consumption/returns/scrap.
- The return posts a `RETURN` flow transaction and line referencing the original issue line; an append-only stock movement and production-consumption return event link the return line to the source issue.
- A return idempotency key prevents duplicate stock and event writes. Reusing a key for another actor, line, or quantity is rejected.
- Returned material is received at its original source location as a separate stock row with `is_blocked = true` and remains unavailable pending review. The reservation is not reopened and issued quantity is not rewritten.
- Generic material return drafts cannot be confirmed, and generic reversal cannot reverse the new material issue/return flows before the inventory-aware S04 correction path exists.
- Batch reconciliation now derives issued totals from posted issue flow lines instead of summing a repeated issued-quantity snapshot on every partial consumption row.
- Added a frontend return panel and history on the material issue page, plus guarded disposable-PostgreSQL acceptance cases for partial consumption/return lineage, blocked returned stock, idempotent retry, key reuse, and excessive return rejection.
- Added migration `20261108_0016` to link a production return event to its return flow line.

## Checks performed

- `python -m py_compile` on changed backend modules and the new acceptance module: passed.
- Ruff on changed material-flow backend modules and the new acceptance module: passed.
- Targeted frontend ESLint on the material issue page and material-flow types: passed.
- SQLAlchemy model import/metadata smoke check: passed.
- `alembic heads`: one head, `20261108_0016`.
- Targeted `git diff --check`: exited 0; Git reported LF-to-CRLF normalization for the changed frontend page.
- PostgreSQL tests, migration application, API tests, and full frontend build were not run; they remain in the consolidated M24 milestone acceptance campaign. No database-test PASS is claimed.

## Changed files for this task

- `backend/alembic/versions/20261108_0016_m24_consumption_return_lineage.py`
- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/models/material_flow.py`
- `backend/app/schemas/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s02_t003_material_return_db.py`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `frontend/src/app/dashboard/material-flow/issue/page.tsx`
- `frontend/src/lib/materialFlow.ts`

## Pending acceptance

Disposable-PostgreSQL migration and behavior checks, API authorization and warehouse-isolation tests, rollback/concurrency and reconciliation checks, frontend build/E2E checks, and consolidated independent code/security reviews remain pending until M24 milestone acceptance.
