# M22.S01.T004 — Codex implementation log V01

## Scope and acceptance material

- Root task: `TASKS.md`, current task `M22.S01.T004 — Immutable audit history for critical transitions`.
- Acceptance: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`, whose follow-up implications require append-only, attributable order and operation transition history across the canonical and active parallel model families.
- Applicable governance: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and the latest available M20 strict-audit records. No M22.S01.T004-specific prompt, criteria, or audit file existed when implementation began.
- Starting synchronized state: `HEAD=37d603eea6dd44376944747a5bd5cd4f6d8f5cd9` on `main`; this is the T003 commit whose post-push fetch was recorded as equal to `origin/main` before T004 was claimed.

## Implementation

- Added a production transition-event model and Alembic revision `20261104_0003`, linked after T003 revision `20261104_0002`.
- Events carry a monotonic database sequence, immutable timestamp, parent/entity identities, action, before/after status, and exactly one attributable actor: an authenticated user (restricted FK) or an active shop-floor operator session (restricted FK with an immutable operator-name snapshot).
- PostgreSQL UPDATE, DELETE, and TRUNCATE triggers reject mutation. No history was fabricated or backfilled for events that predate this migration.
- Recorded creation, approval, release, lifecycle, cancellation, split/merge/rework, operation creation/deletion/start/completion, shop-floor state changes, and imported operation creation in the same database transaction as their business changes.
- Added the authenticated actor to direct MRP/MPS production-order creation paths. Canonical advanced work-order create/delete/start/complete routes check production permission and the locked parent order's warehouse scope before mutation.
- Added scoped read endpoints and timelines to canonical and parallel production-order detail screens. The timeline states that prior events are not backfilled.
- Updated existing guarded-transition database/service test call sites to supply actor IDs now required by the audited service contract; these tests have not been run during this task.

## Changed implementation files

- `backend/alembic/versions/20261104_0003_m22_production_transition_history.py`
- `backend/app/api/v1/endpoints/bulk_import.py`
- `backend/app/api/v1/endpoints/production.py`
- `backend/app/api/v1/endpoints/production_advanced.py`
- `backend/app/api/v1/endpoints/production_execution.py`
- `backend/app/crud/production.py`
- `backend/app/crud/production_advanced.py`
- `backend/app/models/__init__.py`
- `backend/app/models/production_transition.py`
- `backend/app/schemas/production_transition.py`
- `backend/app/services/import_engine.py`
- `backend/app/services/mrp_service.py`
- `backend/app/services/mps_service.py`
- `backend/app/services/production_execution_service.py`
- `backend/app/services/production_service.py`
- `backend/app/services/production_transition_history.py`
- `backend/app/services/shop_floor_service.py`
- `backend/tests/test_m08_s03_t001_transition_guards_db.py`
- `backend/tests/test_m27_s02_t002_production_gate.py`
- `backend/tests/test_m27_s02_t002_production_gate_db.py`
- `frontend/src/app/dashboard/production-execution/[id]/page.tsx`
- `frontend/src/app/dashboard/production/orders/[id]/page.tsx`
- `frontend/src/lib/production.ts`
- `frontend/src/lib/productionExecution.ts`

## Checks and limitations

- Repository root was verified as `C:\Users\sekip\Desktop\fmcg-erp-system`.
- `node scripts/codex/validate-task-state.mjs`: passed at task start; tracker reported T004 `IN_PROGRESS`, 362/545 complete.
- `node scripts/codex/task-queue.mjs --check`: passed at task start and selected T004 as the explicit current task with `Required Actor=CODEX`.
- `git diff --check`: passed after implementation edits.
- Automated tests, typecheck/build, PostgreSQL migration execution, and runtime acceptance have not been run. The owner requested batching milestone tests instead of running them after each task; M22 test evidence remains pending.
- Independent read-only review identified and drove fixes for three blockers: missing warehouse-scope authorization on canonical work-order transitions, missing MRP/MPS create events, and stale actorless service-call sites. The reviewer then confirmed no remaining blocker; no tests were run by the reviewer.
- Task status closure is maintained separately in root `TASKS.md`; this log does not claim migration/runtime acceptance or a passing test suite.
