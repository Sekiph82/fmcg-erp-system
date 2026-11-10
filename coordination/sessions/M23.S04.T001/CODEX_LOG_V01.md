# M23.S04.T001 — Shop-floor API tests

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S04.T001`.
- M23 plan: `coordination/milestones/M23/EXECUTION_PLAN_V01.md`; API tests are the first part of one consolidated M23 acceptance checkpoint.
- The latest applicable Shop Floor boundary remains M27.S04.T004: acceptance is synthetic/local and must not imply live-factory or physical-device verification.

## Implemented

- Added HTTP-level API coverage for required idempotency headers, authenticated actor/key/fingerprint forwarding, stable response identity on repeated requests, and HTTP 409 mapping when a key is reused with a different payload.
- Added API coverage for downtime start actor attribution and stop-key conflicts.
- Tests use synthetic users and fake service/database dependencies; they do not write to a shared database.

## Verification and limits

- Python compile, targeted Ruff for the new API/idempotency test modules and migration, and `git diff --check` passed.
- The new M23.S04 API tests were not executed yet; the milestone plan batches test execution at M23.S04 acceptance after its API, UI/E2E, and production/QC/inventory coverage is assembled.
- No live factory, employee, production database, or deployed API acceptance is claimed.
