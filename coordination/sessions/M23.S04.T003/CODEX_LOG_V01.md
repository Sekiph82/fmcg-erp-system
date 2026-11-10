# M23.S04.T003 — Production/QC/inventory integration tests

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S04.T003`.
- M23.S02 captures actual production quantities, issued-material consumption, and in-process QC; M23.S03 adds idempotent retries. M23.S04.T003 exercises these boundaries together on task-owned disposable PostgreSQL.
- Existing inventory issuance remains the prerequisite recorded in `ExecOrderMaterial.issued_qty`; this Shop Floor consumption test does not claim to post a second warehouse stock issue.

## Implemented

- Added a guarded PostgreSQL integration test that creates only synthetic user, production-order, work-order, operator-session, and already-issued-material rows.
- The test checks material-consumption retry keeps the issued-material consumption quantity at one application, a required QC checkpoint blocks finish until a passing result is recorded, an exact QC retry returns the original event, and a finish retry creates one completion history transition.
- Database writes are permitted only when the task-specific flag is enabled and `DATABASE_URL` names the exact loopback database pattern for M23.S04.T003.
- The test removes its task-owned synthetic rows in `finally`; the disposable database container is removed by the milestone runner.

## Verification and limits

- Python compile, targeted Ruff, and `git diff --check` passed for the new integration test.
- The database test has not been run yet. It belongs to the consolidated M23.S04 suite alongside the authored API and UI/E2E checks.
- Checkout sync check: `HEAD` and `origin/main` are both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`; no ahead/behind commits. The existing broad local worktree has 247 changed paths; no commit or push was attempted.
- All data is synthetic. No live inventory, production database, factory, or employee is represented.
