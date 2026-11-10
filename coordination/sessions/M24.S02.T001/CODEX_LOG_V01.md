# M24.S02.T001 — Material issue transaction

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` and the M24 interpretation in `coordination/milestones/M24/EXECUTION_PLAN_V01.md` define the scope.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012/013 and `coordination/AUDIT_POLICY.md` inventory transaction, identity, authorization, locking, ledger, and rollback controls. GAP-019's WMS product/shipment pick coordination remains separate from this production material reservation flow.

## Starting synchronization and preserved work

- Verified canonical Git root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Fetched `origin/main`; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`, ahead/behind `0/0` at task start.
- The worktree contained unrelated owner/project changes. They were preserved; no reset, clean, stash, or broad staging was used.
- Root `TASKS.md` selected `M24.S02.T001` with `Required Actor: CODEX`; task state was claimed through the queue script.

## Implementation

- Added a reservation issue request with a required idempotency key and reservation-line quantities. Each request is checked for precision, duplicates, ownership by the chosen reservation, and available unissued quantity.
- Reservation lines now preserve their exact source-stock row. Rows created before this linkage exists are rejected if they cannot be issued unambiguously.
- Added an atomic posting path that records the flow header and lines, append-only ISSUE stock movements with the authenticated actor, stock balance reductions, issued quantities, and partial/full reservation status.
- Added a transaction-scoped idempotency lock. A matching retry returns the original posted flow; a key reused by another actor, reservation, or quantity set is rejected.
- Rechecked production-order state, reservation expiry/status, exact stock identity and arithmetic, active source location/zone, and lot expiry/quality/hold/FEFO eligibility before mutation.
- Required authentication and warehouse edit/view scope on material-flow transaction create/read/reverse paths. Generic RAW_ISSUE creation/confirmation is rejected; generic reversal of a posted material issue is blocked until an inventory-aware reversal path exists.
- The issue page now posts reservation quantities through the dedicated endpoint and shows the resulting posted issue history. Actual consumption remains S02.T002 scope.
- Added a guarded PostgreSQL acceptance module for exact database targeting, partial/final issue, matching idempotent retry, key reuse, overdraw, wrong reservation line, ledger actor, and no-mutation rejection cases.
- Added migration `20261108_0014` for source-stock linkage, reservation-line flow linkage, and unique idempotency key storage.

## Checks performed

- `python -m py_compile` on the changed backend modules and new acceptance module: passed.
- Ruff on the changed material-flow API/model/schema/service and new acceptance module: passed.
- Targeted frontend ESLint on the issue page and material-flow API types: passed.
- SQLAlchemy model import/metadata smoke check: passed.
- `alembic heads`: one head, `20261108_0014`.
- Targeted `git diff --check`: exited 0; Git reported LF-to-CRLF normalization for the changed frontend page.
- PostgreSQL acceptance tests, migration application, API tests, and frontend production build were not run; they remain in the consolidated M24 milestone acceptance campaign. No database-test PASS is claimed.

## Changed files for this task

- `backend/alembic/versions/20261108_0014_m24_material_issue_reservation_linkage.py`
- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/models/material_flow.py`
- `backend/app/schemas/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s02_t001_material_issue_db.py`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `frontend/src/app/dashboard/material-flow/issue/page.tsx`
- `frontend/src/lib/materialFlow.ts`

## Pending acceptance

Disposable-PostgreSQL migration and behavior checks, API authorization and warehouse-isolation tests, rollback/concurrency tests, frontend build/E2E checks, and consolidated independent code/security reviews remain pending until M24 milestone acceptance.
