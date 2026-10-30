# M34.S02.T002 — Price breaks/validity/commitments

## Delivery

Added dated, quantity-based blanket agreement price breaks, commitment-aware quote pricing, scoped API operations with schedule audit events, and an editable price-break schedule in the blanket agreements screen. The calculation uses an all-units rule: the highest eligible minimum quantity selects the unit price for the entire requested quantity; the BPA agreed unit price is the fallback. Currency and unit remain inherited from the parent BPA. This is an implementation default because the task's linked materials define no alternative tier interpretation; no real supplier values were introduced.

The resolver checks the BPA validity window and remaining commitment before pricing. Price-break records validate positive finite thresholds/prices and date windows. Schedule writes lock the parent agreement, enforce its scope and edit access, audit before/after state, and restrict edits after consumption or outside agreement validity. UI schedule controls use the existing access hints and disable mutation when permissions or loading state do not permit it.

Migration `20261030_0009` adds the price-break table while validating/adopting the existing schema ownership shape. Downgrade preserves pre-existing/adopted tables; migration-owned table removal takes an exclusive lock and refuses to drop populated records.

## Verification

- Disposable PostgreSQL 16 run V04: 3 focused tests passed.
- Alembic downgrade `20261030_0009 -> 20261030_0008` succeeded; `BPA_PRICE_BREAK_ROWS_AFTER_DOWNGRADE=3` confirmed all three schedule rows survived.
- Re-upgrade succeeded; head is `20261030_0009`.
- Disposable PostgreSQL container cleanup verified absent.
- Python compileall for changed backend/migration/test modules: passed.
- Frontend `npm run type-check`: passed.
- Targeted ESLint for the blanket-agreements page and procurement API client: passed.
- `git diff --check`: passed.
- Independent read-only review: earlier findings on downgrade locking, numeric NaN constraints, stale schedule state after load failure, and schema ownership validation were fixed; follow-up found no remaining actionable findings.

Immutable test output: `disposable-postgres-command-output-V04.log`. Downgrade-row preservation and container cleanup markers, with the SHA-256 of the full PowerShell transcript, are recorded in `disposable-postgres-verification-V04.md`. Earlier V02/V03 attempts are retained as failed iteration evidence in their command-output logs; V02 exposed a too-strict constraint-shape verifier, and V03 exposed a test assumption that PostgreSQL would raise `IntegrityError` for a precision-overflow Infinity value. The verifier and test were corrected, then V04 passed.
