# M25.S02.T004 — Currency/exchange-rate handling

## Scope and controls

- Exact task selected from the root `TASKS.md` handoff: `M25.S02.T004`.
- The task row had no separate acceptance-document link. Read the canonical task row, `docs/planning/GAP-001_ACCOUNTING_CORE_AUDIT.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, and `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md` before editing.
- GAP-001 records Finance exchange rates against KES and calls the conversion/revaluation path partial. GAP-002 says landed-cost inventory valuation and GL links remain partial. This task records rate provenance and produces consistent converted cost amounts; it does not claim a new GL posting, inventory valuation policy, live rate provider, or supplier-payment flow.
- Assumption used for this simulation: each landed-cost line may retain its invoice currency; the document currency is the reporting currency for header foreign-currency totals; all converted/base values use the repository's KES base.
- Finance `ExchangeRate` rows are the only accepted source for non-KES rates. Resolve the latest rate on or before the bill date; if no bill date exists, use today's date as the cutoff. KES is exactly 1:1. Missing rates fail closed. No stale-rate age limit or manual override was invented.
- Persist the applied numeric rate, source date, source label, and optional exact Finance rate row ID on each header and line. Later edits to a Finance rate do not recalculate saved landed-cost amounts. Legacy rows retain their existing numeric amounts/rates and have NULL provenance because the historical source date cannot be reconstructed.

## Implementation

- Added Alembic revision `20261029_0040` with nullable, provenance-marked Finance rate snapshot columns and `ON DELETE SET NULL` rate links. Upgrade adopts only the exact expected nullable schema and comments. Downgrade refuses to discard saved rate links or source snapshots.
- Landed-cost create/add-line resolves Finance rates using the bill date, stores the rate snapshot, converts line amounts to KES, and sums those base values. Header foreign-currency totals are the base sum converted back at the header currency's saved rate, so mixed-currency line amounts are never added together directly.
- Changing the draft document currency or bill date re-resolves and snapshots the header and line rates, recalculates base values, and recomputes totals in the same transaction. Other header-only edits do not rewrite legacy rate snapshots.
- API schemas normalize three-letter currency codes, reject untracked manual landed-cost rates, and reject Finance exchange rates that are non-positive, non-finite, or cannot remain positive within `NUMERIC(18,6)` storage.
- New landed-cost entry defaults to KES and no longer asks staff to type a rate. The saved document view shows each line's rate, source and effective date, and explains the header-total currency conversion.
- Existing actual-cost comparisons continue to use each line's stored rate. Posted allocations/journals are not rewritten by this task.

## Verification

- Disposable PostgreSQL runner: `coordination/sessions/M25.S02.T004/run_currency_rate_tests.ps1`; transcript: `coordination/sessions/M25.S02.T004/postgres-test-run-final.log`.
- `postgres:16-alpine`, image `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`; database/container names were task-labeled, randomly suffixed, and temporary. The port was bound only to `127.0.0.1`; there was no password or volume mount. Only synthetic data was used, and the exact task-owned container was removed after the run.
- PostgreSQL exercised a full fresh migration, clean downgrade, schema adoption with exact pre-existing ORM-style columns/FKs/comments, an old legacy landed-cost row with unknown provenance, re-upgrade, dated USD/XTS/KES conversion, date-change recalculation, and a guarded downgrade after saved rate links existed. Result: **8 passed**; expected downgrade refusal was confirmed; final Alembic head was `20261029_0040`.
- Focused M25.S02 landed-cost and M13 posting tests: **45 passed, 13 skipped**; the T004 database test is run separately by the disposable runner.
- Backend Python compile check: PASS.
- Frontend `npm run type-check`: PASS. Targeted ESLint for the landed-cost detail/new pages and API types: PASS.
- Independent read-only review found and prompted correction of the no-bill-date future-rate cutoff and invalid legacy header-rate guard; both are fixed and covered. The reviewer confirmed no remaining blocker. The no-bill-date test also asserts the cutoff bind value equals today's date.

## Limits

- Exchange-rate creation remains manual or uses the pre-existing Finance rate-source enum; this task did not integrate a live CBK/ECB connector or verify source authenticity.
- Existing historical rows whose rate provenance was not stored remain explicitly unknown. No fabricated backfill was applied.
- This task does not add accounting postings, adjust posted inventory, revalue foreign-currency balances, define a maximum stale-rate age, or claim production/business approval.
