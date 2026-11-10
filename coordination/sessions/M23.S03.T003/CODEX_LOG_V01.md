# M23.S03.T003 — Add safe retry/idempotency for execution actions

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S03.T003`.
- Milestone plan: `coordination/milestones/M23/EXECUTION_PLAN_V01.md`.
- The M23.S03.T002 online-only policy requires a repeated submission after an ambiguous network outcome to reuse the same operation key; offline mutations are not queued or replayed.
- M23.S04 remains the consolidated milestone test, independent code review, and security review checkpoint.

## Implemented

- Added an `Idempotency-Key` contract to Shop Floor work-order execution mutations and downtime start/stop routes. The server fingerprints the canonical action, resource, authenticated actor, and request body; reusing a key for a different request returns HTTP 409.
- Persisted keys and fingerprints with execution activity rows and downtime records. Database constraints enforce key/fingerprint pairing and uniqueness for authenticated work-order actors and downtime creators.
- Serialized work-order retries under the existing parent/work-order locks. Exact retries return the original activity event or downtime record without repeating the execution mutation; PostgreSQL insert conflict arbitration covers concurrent downtime starts.
- Added frontend key reuse for the same path and request body. Failed requests retain their key for a safe retry; successful requests clear it. No offline mutation queue or automatic replay was added.
- Made migration `20261104_0012` tolerate constraints already created by the repository's fresh-database baseline as well as existing databases that need the constraints added.

## Verification

- Focused T003 unit and disposable-database tests: **8 passed**.
- A newly created task-owned PostgreSQL 16.6 container migrated from empty to Alembic head `20261104_0012`; the database guard confirmed the exact loopback database name, the retry test persisted one row and rejected changed-payload key reuse, and the task container was removed afterward.
- Focused authentication regression: **1 passed** (`tests/test_m23_s01_t004_shop_floor_permissions.py::test_shop_floor_api_requires_authentication_for_reads_and_mutations`).
- Python compile check, targeted frontend ESLint, and `git diff --check` passed.
- Ruff was attempted on the changed backend modules and reported seven unused-symbol findings. Each finding was verified in the corresponding `origin/main` version; these are pre-existing warnings and outside this task's changes.
- The first disposable migration attempt exposed the baseline-constraint collision described above. The migration was corrected, then the fresh-database migration and focused tests passed.

## Limits and publication

- The complete M23 suite, UI/E2E acceptance, consolidated independent review, and security review are deferred to M23.S04 as specified by the milestone plan.
- Evidence is synthetic and local. No live factory, real employee, production database, physical device, or deployment acceptance is claimed.
- The canonical checkout was fetched before the task checkpoint and `HEAD` matched `origin/main`. The worktree already contained 239 changed paths, including overlapping owner/local edits; no broad staging, commit, or push was attempted.
