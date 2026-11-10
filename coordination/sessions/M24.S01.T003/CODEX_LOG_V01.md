# M24.S01.T003 — Staging area/location semantics

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` is authoritative. The location interpretation is recorded in `coordination/milestones/M24/EXECUTION_PLAN_V01.md`.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/012 and the transactional, warehouse-scope, rollback, and direct-observability requirements in `coordination/AUDIT_POLICY.md`.

## Starting synchronization and preserved work

- Verified repository root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Starting local `HEAD` and fetched `origin/main`: `0db8dc68c971661dbda55f6992f3b4e70e4da84d`; ahead/behind `0/0`.
- At task start, 261 changed paths outside the excluded private `.hiveai` path were present. They were left untouched and unstaged; no reset, clean, stash, or overwrite was used.
- Root `TASKS.md` was read and not manually edited by this implementation.

## Implementation

- Added nullable source and staging location references to reservation lines with `ON DELETE SET NULL`; existing rows are not backfilled because their historical location is not known.
- Source location is copied from the stock row actually allocated. A configured source must be active, unblocked, in an active zone of the order's source warehouse, and in a raw-material or staging zone. Missing source location remains unassigned; the service does not guess a location.
- Staging selection is limited to active, unblocked locations in active staging zones in the source warehouse. A single configured location is selected automatically, none remains unassigned, and multiple choices require an explicit location. A foreign/invalid selection is rejected before inventory mutation.
- The generated pick list groups by source and staging location and includes their codes. The frontend displays both, offers valid staging locations, clears a previous choice when the warehouse changes, and explains the no-guess behavior.
- Extended the disposable PostgreSQL suite for selected/default location persistence, pick-list reporting without stock mutation, multi-location explicit selection, foreign-warehouse rejection, and the unconfigured-staging case.

## Checks performed

- `python -m py_compile` on the changed model, schema, service, migration, and M24 integration test: passed.
- `python -m ruff check tests/test_m24_s01_t001_material_reservation_db.py`: passed.
- `npm exec -- eslint src/app/dashboard/material-flow/reservations/page.tsx src/lib/materialFlow.ts`: exited 0.
- `git diff --check` on the tracked changed files: passed.
- SQLAlchemy `configure_mappers()` smoke check for material-flow and WMS models: passed.
- `python -m alembic heads`: one head, `20261108_0013`.
- PostgreSQL tests and migration application were not run; they remain in the consolidated M24 validation campaign. No test PASS is claimed.

## Changed files for this task

- `backend/alembic/versions/20261108_0013_m24_reservation_location_semantics.py`
- `backend/app/models/material_flow.py`
- `backend/app/schemas/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s01_t001_material_reservation_db.py`
- `frontend/src/app/dashboard/material-flow/reservations/page.tsx`
- `frontend/src/lib/materialFlow.ts`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `coordination/sessions/M24.S01.T003/CODEX_LOG_V01.md`

## Pending acceptance

The migration has not been applied to a database. PostgreSQL behavior, API authorization, cross-warehouse isolation, rollback, concurrency, frontend type/build checks, and consolidated independent code/security review remain unverified until M24 milestone acceptance.
