# M34.S01.T001 — Tender/sourcing event model

## Scope and baseline

- Task: add a multi-line tender/sourcing event to the existing RFQ model and API, retain compatibility with existing single-item RFQs, and expose event lines in the current procurement UI.
- Baseline: `609cca7dde06e51dce48ab5e8f03cda8c29add6b` (`main` and `origin/main` matched at task start and before task close; divergence `0 0`).
- Existing procurement is governed by `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md`; implementation extends the existing `RFQRequest` aggregate and does not create a parallel procurement workflow.
- Fixtures use synthetic data only. No supplier, factory, employee, or owner procurement data was invented or changed.

## Changes

- Added `RFQLine` sourcing-event lines and Alembic revision `20261030_0005`; existing single-item RFQs remain supported while new events can contain multiple identified lines.
- Added finite, positive, representable `NUMERIC(14,3)` quantity validation in API schemas and database constraints, including NaN/infinity rejection.
- Made migration adoption validate table shape and quantity type, replace weaker same-named checks and incorrect FK delete actions, and retain guarded downgrade behavior that refuses destructive data loss.
- Extended the existing RFQ API responses and frontend procurement view with ordered line details and line counts.
- Added task-scoped database guard, API persistence/compatibility checks, direct database constraint checks, and an adoption regression with intentionally weak checks and `RESTRICT`/incorrect cascade FK actions.
- Added `run_disposable_postgres.ps1`, which creates a unique passwordless loopback-only PostgreSQL container/database, runs the migration round trip and focused tests, then verifies exact container removal.

## Verification evidence

- `coordination/sessions/M34.S01.T001/disposable-postgres-run-V06.log` and `disposable-postgres-command-output-V06.log`: fresh PostgreSQL 16 task database; Alembic empty-to-head upgrade, downgrade one revision, re-upgrade; task and GAP-009 focused suites **17 passed**; final Alembic head `20261030_0005`; exact task container removal verified.
- No-database focused suite: `tests/test_m34_s01_t001_sourcing_event.py` — **9 passed, 2 skipped** (the two guarded PostgreSQL tests require the task database).
- Python compilation passed for the changed API, model, schema, migration, and test modules.
- Frontend `npm run type-check` and targeted ESLint for the RFQ page and procurement client passed.
- `git diff --check` passed; `python -m alembic heads` reports the single head `20261030_0005`.
- Independent read-only review: no remaining actionable findings after migration adoption checks, weak-constraint/FK replacement, and V06 evidence were reviewed.

## Failed attempts and retained evidence

- V01–V03 logs are retained. V03 was stopped by Windows PowerShell treating Alembic stderr as a terminating native-command error; its tests did not run.
- V04 reached the suite but exposed two test expectation issues: PostgreSQL rejects infinity at the `NUMERIC(14,3)` type boundary, and renders check expressions with casts. The implementation was retained; tests were corrected and V05/V06 were run with complete command output.
- V05 passed 17 tests. V06 additionally exercises replacement of incorrect pre-existing FK delete actions and is the final evidence run.

## Limits

- This is local synthetic integration evidence only. It is not production, live supplier, legal, payment, or factory acceptance.
- No GitHub Actions were run or dispatched.
