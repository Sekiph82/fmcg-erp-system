# M25.S03.T001 — Inventory valuation posting

## Scope and authority

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Exact task: `M25.S03.T001 — Inventory valuation posting` from root `TASKS.md`; the task row did not link a separate acceptance file.
- Baseline: `6610f1ac86ba817bfdd481c1a167bed58e0a0f47`; `origin/main` was fetched and confirmed at the same revision before work.
- Read before implementation: `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_SCHEMA_DESIGN.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_IMPLEMENTATION_NOTES.md`, `docs/planning/GAP-001_ACCOUNTING_CORE_AUDIT.md`, `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md`, and predecessor acceptance `coordination/sessions/M13.S03.T001/CHATGPT_AUDIT_CRITERIA_V01.md`.
- GAP-002 identified missing inventory/GRNI posting for GRN receipt and no central valuation policy. This task reuses `StockMovement`, `CostLayer`, `InventoryAccountMapping`, and existing finance posting event, batch, journal, and period controls. No migration was needed.

## Simulated ERP assumptions

- Inventory receipts are only posted when the inventory mapping, accounts, currency conversion, and open finance period are configured. This avoids inventing accounts, rates, or carrying values.
- A new physical GRN post creates stock, the applicable cost layer, a balanced journal, and the posting links in one database transaction. The route requires both finance posting authorization and procurement record access; the UI makes that requirement visible.
- PO-line price and its saved exchange-rate snapshot supply actual cost. Matching PO/company base currencies use rate 1; a foreign-currency PO with the default rate is rejected. Unit values use the same four-decimal monetary scale stored on stock movements, so layer, movement, and GL totals reconcile.
- FIFO and WEIGHTED_AVG store the converted receipt cost in the receipt layer. STANDARD uses the item's configured base-currency standard cost; a difference posts through the configured variance expense account.
- A separately posted legacy GRN may be valued only when no outbound movement occurred after its receipt. A possibly consumed unvalued receipt fails closed for manual inventory/accounting reconciliation.
- No real supplier, factory, user, exchange rate, or production data was used. This task does not claim live-provider behavior or cover landed-cost capitalization, material-consumption/WIP posting, reversal, supplier-invoice tax, or live finance setup.

## Implementation

- Added `post_grn_inventory_valuation` with PO-then-GRN lock ordering, company/warehouse/PO-line/movement identity checks, scoped active mapping checks, open-period enforcement, saved-rate conversion, FIFO/weighted-average/standard valuation, balanced inventory/GRNI/variance journal, cost layer, event/batch/journal links, and verified idempotent replay.
- Integrated valuation into physical `post_grn` so stock and GL cannot commit separately. Any finance configuration or posting failure rolls back the GRN, stock, PO counters, movement, cost layer, and accounting records together.
- Kept the finance-protected legacy valuation route for untouched older receipts; it rejects any later outbound issue, transfer, negative adjustment, or write-off.
- Added valuation status to GRN responses and updated the PO detail UI with a combined stock-and-valuation action plus finance-permission messaging.
- Updated M05/M06 integration fixtures and posting expectations to include synthetic finance setup required by the new receipt invariant.

## Verification

- Task-owned disposable PostgreSQL runner: `coordination/sessions/M25.S03.T001/run_inventory_valuation_tests.ps1`.
- PostgreSQL image: `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Final task database: `fmcg_m25_s03_t001_5551c3cb3cd7496b8ce2`; random task-specific name, loopback-only port, local trust authentication, no password or volume. Container was removed by the runner.
- Fresh Alembic migration reached `20261029_0040 (head)`; M25 task-owned PostgreSQL suite: **16 passed**. Coverage includes FIFO, WEIGHTED_AVG, STANDARD variance both directions, atomic physical receipt/valuation success and rollback, permission denial/grant, currency conversion and four-decimal FX reconciliation, duplicate replay, tampered posting links, delayed legacy valuation after outbound movement, wrong movement, company mismatch, missing mapping, closed period, and invalid foreign default rate.
- Isolated disposable PostgreSQL regressions: M05.S03.T002 **7 passed**, M05.S03.T003 **5 passed**, M06.S03.T001 **5 passed**. Each used its exact task-name database prefix, synthetic records only, loopback-only networking, and exact container cleanup. Runner/transcripts: `coordination/sessions/M25.S03.T001/run_receipt_regressions.ps1` and `receipt-regressions-final.log`.
- Posting integration unit/helper suites: **7 passed**, **11 skipped** because those cases require their separate M13 task-owned disposable database; no skip is reported as a pass.
- Frontend `npm run type-check`: passed. Targeted ESLint for the PO detail page and procurement API types: passed. Backend `py_compile`: passed. `git diff --check`: passed.

## Independent review

- Independent read-only reviewer initially identified separate-transaction consumption risk, inverse lock order, a stale legacy valuation path, and unit-cost rounding drift. Those were fixed and covered by tests.
- Final read-only review: **no blocking findings**. Reviewer did not run commands, edit files, or access a database.
