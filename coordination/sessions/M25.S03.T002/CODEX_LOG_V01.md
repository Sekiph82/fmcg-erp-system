# M25.S03.T002 — Variance/accrual posting

## Scope and operating assumption

Implement a separate accounting adjustment for an actual landed-cost amount recorded after the estimate has already posted. Preserve the original landed-cost line, allocation, initial journal, and inventory-adjustment record. Translate the actual through the line's saved exchange-rate snapshot and adjust the configured landed-cost clearing accrual. For capitalized costs, split the adjustment between remaining FIFO inventory value and consumed-cost expense using the source layer's current remaining quantity. For non-capitalizable costs, post the delta to the configured expense account. A zero delta is finalized as not required without creating a journal. A closed or locked accounting period blocks posting without partial writes.

This is a synthetic ERP workflow. The entered source reference is provenance only; it is not invoice authentication and does not create supplier AP, tax, or payment records.

## Implementation

- Added an immutable variance-posting record per original allocation, linked to its operational posting batch and journal entry. The actual record stores base-currency actual/variance values, state, and posting timestamp.
- Added a finance-protected `POST .../lines/{line_id}/actual/post` endpoint. It locks the header, line, actual, accounting period, allocations, and FIFO layers; verifies original posting links; uses idempotent operational events; and commits all variance entries and inventory valuation changes atomically.
- Positive and negative variances use signed, balanced journal lines. Inventory reductions cannot take a FIFO layer below zero, and unit-cost precision that cannot reconcile fails closed.
- Added a guarded `20261029_0041` migration with historical actual backfill and full schema checks before adopting the posting table. Kept the T003 actual-recording behavior unchanged and made the earlier actual-table shape check accept only the specifically marked T0041 fields that can be present from the metadata-created fresh baseline.
- Added the detail-page action and posting state display for finance users.

## Verification

- Fresh disposable PostgreSQL migration and integration run: **8 passed**, final Alembic revision `20261029_0041 (head)`. Database name matched the exact `fmcg_m25_s03_t002_<20 hex>` task prefix, loopback only, random host port, no password, no volume, synthetic data only. The task-owned container was stopped and removed by the runner.
- Related landed-cost actuals, FX, and inventory-valuation regression suites: **11 passed, 17 skipped**. Database-gated skips belonged to other exact task-owned suites and were not bypassed.
- Frontend type-check and targeted ESLint passed.
- Python compileall, targeted Ruff, and `git diff --check` passed.
- Independent read-only review found no remaining blockers after migration timestamp and strict schema-adoption checks were corrected.

## Evidence files

- `coordination/sessions/M25.S03.T002/run_variance_posting_tests.ps1`
- `coordination/sessions/M25.S03.T002/postgres-test-run.log`
- `coordination/sessions/M25.S03.T002/pytest-output.log`

## Limits

- No live supplier invoice, AP/tax, payment, external FX provider, or real-company data was used.
- Adjustments require an open period for the landed-cost bill date and configured account mappings; unsupported or inconsistent source records remain pending for manual reconciliation.
