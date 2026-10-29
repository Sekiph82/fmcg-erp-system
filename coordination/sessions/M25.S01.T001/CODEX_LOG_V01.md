# M25.S01.T001 — Purchase→shipment→container linkage

Status: implementation complete; independently reviewed.

## Delivered

- Added a shipment-level purchase-order/container management view to the existing logistics shipment page. Eligible orders are APPROVED, ORDERED, or PARTIALLY_RECEIVED; the API independently enforces the same rule.
- Added server checks for missing shipment/PO references and duplicate PO links. A unique database constraint prevents concurrent duplicate links; the migration aborts on pre-existing duplicates rather than deleting owner data.
- Purchase-order links expose supplier, PO number, and correctly rounded order-line totals including tax.
- Protected link/container reads with `logistics.view`, creation with `logistics.create`, and unlink/container updates with `logistics.edit`. The UI hides mutation controls for view-only users.
- Added a task-scoped PostgreSQL integration test and mocked browser coverage.

## Evidence

- `coordination/sessions/M25.S01.T001/M25_S01_T001_TEST_RUN_V03.log`: fresh `postgres:16-alpine` database, Alembic upgrade through `20261029_0034`, 1 passed. The integration test exercised permission denials, allowed create/edit, missing records, PO status and duplicate guards, taxed multi-line totals, persisted linkage/counts, and the database uniqueness constraint.
- `coordination/sessions/M25.S01.T001/M25_S01_T001_FRONTEND_TEST_RUN_V01.log`: TypeScript check and targeted ESLint passed; mocked Chromium E2E passed 2/2.
- Independent read-only review: no actionable blocker found after the final auth/test/migration changes; the narrow linkage claim is supported by V03 and the mocked E2E evidence.
- The runner bound only to loopback, used synthetic data, no password and no volume mount, and verified its labeled temporary database container was removed. No production ERP data, factory system, external carrier, customs, or provider was used.
- `M25_S01_T001_TEST_RUN_INITIAL_FAILED_V01.log` preserves an early failed attempt caused by a lazy-loaded PO relationship; the API now eagerly loads PO lines. `M25_S01_T001_TEST_RUN_V02.log` preserves a later failed attempt where the test harness used the authorized actor for a denial assertion. Both issues were corrected and V03 passed.

## Limits

This closes only the M25.S01.T001 software linkage scope. It does not claim live-factory acceptance, external shipping/carrier integration, customs clearance, landed-cost accounting, or production deployment approval. The first broad Playwright invocation stopped at the repository's protected login-state guard; the focused mocked tests then ran with `--no-deps` and an isolated empty state file.
