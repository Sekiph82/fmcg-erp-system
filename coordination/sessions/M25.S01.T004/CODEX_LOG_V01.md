# M25.S01.T004 — Kenya receipt closure

## Scope and operating assumptions

Implemented an in-system warehouse receipt closure for synthetic Kenya shipment data. A shipment can close only after it reaches `OUT_FOR_DELIVERY`, and the closure must cite one or more unused, `POSTED` GRNs whose purchase orders are linked to that shipment. Partial receipts remain partial; this closure does not assert that the complete purchase order has been received. The recorded delivery date is the latest selected GRN receipt date. The closure records its actor/time and selected GRN/date snapshots as append-only evidence.

This is a software workflow using synthetic organizations, operators, shipments, purchase orders, GRNs, and warehouses. It does not claim real KRA validation, customs clearance, physical delivery, or live supplier/warehouse operations.

## Implementation

- Added shipment receipt closure and closure-line models plus revision `20261029_0037`.
- Guarded migration adoption against incompatible tables, columns, defaults, indexes, functions, and unowned triggers. The squashed baseline creates current model tables before revision 0037; the migration only adopts an unmarked baseline-shaped table when it is empty and trigger-free, then records ownership markers.
- Added scoped API reads and receipt closure, rejected direct delivery-date/GRN edits and direct shipment status changes to `DELIVERED`, and serialized PO-link add/remove operations against the shipment row lock. PO links cannot change after closure.
- Added a read-only arrival delivery date, GRN selection and immutable closure history to logistics UI, with receipt API methods and mocked Playwright coverage.
- Updated the logistics user manual with the synthetic receipt workflow and its limits.

## Verification evidence

- `postgres-test-run-07.log`: task-owned, disposable PostgreSQL 16 database; all migrations through `20261029_0037` applied; integration test **1 passed**. Database data was synthetic, the published port was bound to loopback, no volume was mounted, and the task runner verified and removed its labeled container.
- `playwright-mocked-01.log`: targeted mocked Chromium UI suite **2 passed** (successful receipt closure and view-only access).
- Captured command logs have trailing horizontal whitespace removed only; test output content and results are unchanged.
- `frontend/npm run type-check`: passed.
- Targeted ESLint for the changed arrival/shipments/API/e2e files: passed.
- Python `compileall` for changed backend, migration, and integration-test files: passed.
- `git diff --check`: passed; Git reported only the existing `TASKS.md` LF-to-CRLF normalization warning.
- Independent read-only review: final pass; no remaining route, test, locking, or migration-guard blocker.

## Corrections recorded

Earlier task-owned PostgreSQL attempts exposed and led to fixes for PostgreSQL `FOR UPDATE` with `DISTINCT`, a nested Pydantic response type/import, an expired ORM identifier in the test, and migration ownership handling for baseline-created tables. An early mocked Playwright run exposed a missing label/input association; the accessible delivery-date field was corrected. Only the final passing test runs are included as evidence above; the failed attempts are not reported as passing evidence.
