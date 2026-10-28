# M21.S02.T004 — Feed variances into costing/reporting

## Behavior

Costing and variance responses now expose informational recipe-standard yield-loss cost variance per order and product. The calculation is `(actual loss quantity - expected quantity × standard loss percentage / 100) × material standard cost`, using the standard-loss snapshot recorded on each waste row.

The amount is returned only when every standard-bearing row has a non-negative material standard cost and matching waste/material UOM. Missing standards are not counted; rows with a standard but no usable cost or matching UOM are counted as unpriced and withhold the aggregate amount. Priced, unpriced, and standard-bearing counts accompany each result.

This exposure is kept separate from finalized component costs, total cost, cost per unit, total variance, and variance percentage. Existing cost finalization does not persist or book the informational amount.

## Verification evidence

- Focused Python tests: 8 passed, covering matching and mismatching UOM, missing cost/standard, incomplete aggregation, product report aggregation, and GET/finalize API response serialization.
- Frontend `npm.cmd run type-check` passed.
- Python compilation passed for the changed costing service, schema, and endpoint modules.
- `git diff --check` passed.
- Independent read-only review found no remaining blocker after confirming GET and finalize responses include the computed fields.

## Scope limits

This task reports yield-loss exposure; it does not change booked or finalized cost totals, historical rows, or standard-cost policy. No production database data was modified.
