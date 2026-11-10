# M29.S03.T002 — Reason-code hierarchy

## Implementation status

Implemented; pending consolidated M29.S04 acceptance. Historical downtime descriptions were not classified or backfilled. The migration adds shared taxonomy reference rows and nullable foreign-key links only.

## Changes

- Added a two-level active reason taxonomy seeded from the existing `DowntimeClass` values.
- Linked maintenance breakdowns, production downtime events, and machine-operator downtime records to the same code table.
- Added leaf-code validation and read endpoints; maintenance reads retain the existing `maintenance.view` permission guard.
- Added grouped reason-code selectors to the three downtime screens. New maintenance and production UI entries require a selected code; the API fields remain nullable for legacy-client compatibility.
- Returned an HTTP 422 for a machine-operator reason/class mismatch instead of allowing it to surface as an internal server error.
- Kept existing incident reason text and historical rows unchanged.

## Lightweight evidence

- `python -m py_compile` for touched backend models, schemas, endpoints, service, and migration: PASS.
- SQLAlchemy model import and `configure_mappers()`: PASS.
- Focused imports of maintenance, production-advanced, and machine-operator endpoints: PASS.
- `python -m alembic heads`: one head, `20261108_0025`.
- Scoped ESLint for the three downtime screens and their three API clients: PASS.
- Scoped tracked `git diff --check`: PASS.
- No database migration execution, automated tests, full frontend checks, or milestone code/security audit were run. Those remain for M29.S04 consolidated acceptance.

## Inputs reviewed

- `TASKS.md` M29.S03 task rows.
- `coordination/milestones/M29/EXECUTION_PLAN_V01.md`.
- The M29 plan's referenced GAP-007, GAP-022, and GAP-023 audits; these informed integration surfaces and compatibility constraints, not additional acceptance requirements.

