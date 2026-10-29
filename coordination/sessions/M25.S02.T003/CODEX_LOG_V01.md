# M25.S02.T003 — Estimated vs actual landed cost

## Scope and controls

- Exact task: `M25.S02.T003`, selected in root `TASKS.md`; implementation stayed in the canonical FMCG ERP checkout.
- Acceptance context read: root task row and landed-cost module manual. Applicable reviews read: `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md` and `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`.
- The finance/inventory audit says landed-cost allocation and accounting linkage remain partial. This change therefore records comparison data and does not claim new inventory or GL posting behavior.
- All test records were synthetic. No factory, employees, live supplier invoices, or external accounting records were represented as real.

## Implementation

- New cost lines retain an explicit estimated foreign-currency amount; legacy `amount_fc` inputs continue to work and are copied into the estimate field.
- Migration `20261029_0039` backfills existing line estimates from the previously used amount, adds an immutable one-per-line actual-source record with amount, source reference, actor, and timestamp, and safely handles both a fresh baseline-created table and a legacy schema without the new objects.
- Actual amounts recorded before posting become the current allocation amount, clear stale unposted allocations, reset VALIDATED documents to DRAFT, and recalculate header totals in the same transaction. An inconsistent document with posted allocations fails closed.
- Actuals entered after posting are comparison-only; the posted cost, allocation, and journal remain unchanged. A second actual/correction is rejected and requires a separate adjustment workflow.
- The API requires `finance.post` for actual entry. The detail page shows estimate, actual, variance in foreign and base currency, source reference, and timestamp. New document entry labels the amount as estimated.
- Downgrade refuses to discard actual records or estimates that differ from the operative amount. Historical estimates backfilled equal to their prior amount remain safe to downgrade.

## Verification

- `coordination/sessions/M25.S02.T003/run_actual_cost_tests.ps1`: PASS on disposable `postgres:16-alpine` image `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`, bound only to `127.0.0.1`, with no volume mount or password. The runner exercised fresh-baseline adoption, simulated the pre-T003 schema with a legacy landed-cost line, reapplied the migration, and ran the database-backed service/migration checks: **4 passed**. Container `codex-m25-s02-t003-99899bafadf249b4b325` and its synthetic database were task-labeled and removed by the runner. Transcript: `coordination/sessions/M25.S02.T003/postgres-test-run-final.log`.
- Backend compile check for changed Python and migration files: PASS.
- Focused M25.S02 T001/T002/T003 unit checks: **37 passed, 1 skipped**. The skipped T003 database case is run by the disposable PostgreSQL script above.
- Frontend `npm run type-check`: PASS.
- Targeted ESLint for the landed-cost detail page, new-document page, and API types: PASS.
- `git diff --check`: PASS.
- Independent read-only review found no blockers after fixes for anomalous posted allocations, baseline-table primary key/timezone checks, and `NUMERIC(14,4)` overflow including legacy amount inputs.

## Limits

- The user-entered source reference is recorded as provenance; this workflow does not verify invoice authenticity.
- Recording an actual amount on an already-posted document reports variance only. Posting an accounting/inventory adjustment remains in the later M25 accounting/valuation task scope.
