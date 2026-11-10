# M29.S02.T003 — Expiry blocking/quality linkage

## Implementation

- Linked CCP monitoring records to the calibration instrument used for each numeric reading. Numeric CCP entries now require a selected instrument; the API independently enforces this and checks the calibration record under a row lock.
- The software policy allows `CURRENT` and `DUE_SOON` instruments through the due date, inclusive. It rejects inactive instruments, missing calibration dates, records dated before the last calibration, overdue calibration, and `OUT_OF_SERVICE` instruments. The existing 30-day `DUE_SOON` window is a software default, not a regulatory or owner-approved standard.
- The API rejects invalid submissions without creating a monitoring record. Valid records retain the linked instrument, status at measurement time, and instrument code snapshot. The code and status remain visible in the historical log if the instrument link is later removed.
- The CCP screen requires a selectable eligible instrument, disables ineligible instruments, and shows the calibration link and status in the monitoring history. Existing records are not backfilled with invented instrument data.
- Added migration `20261108_0022` with nullable linkage and snapshot columns. Existing CCP logs remain unchanged and unlinked.

## Review and verification

- Independent read-only review checked API validation, due-date boundaries, permissions, persistence, migration, and the historical snapshot behavior; no blocker remained. The reviewer did not edit files or run tests.
- Python syntax and import check passed. Focused ESLint passed for the CCP page, calibration page, and QMS client. `alembic heads` reports `20261108_0022` as the single head. Scoped `git diff --check` reported no whitespace errors.
- No automated test suite or database migration was executed for this task. Comprehensive M29 verification and migration execution remain assigned to M29.S04.

## Queue status

Implementation is recorded as pending M29 milestone verification; this is not a claim that M29.S04 passed.
