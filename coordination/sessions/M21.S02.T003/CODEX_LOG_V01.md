# M21.S02.T003 — Separate standard vs actual yield/loss

## Owner decision and behavior

Owner answer Q-M21-S02-T003-YIELD-SOURCE: B — recipe-item loss percentages are the standard source.

Each new waste record snapshots the quantity-weighted recipe item loss percentage for the production order's recipe, matching the same material and UOM. Repeated recipe rows for the same material and UOM are weighted by their recipe quantities; no values are combined across different UOMs. Matching by material code is resolved to the master material before lookup. If the order, material, UOM, or matching recipe rows do not provide a sound standard, the standard stays null.

Actual loss remains calculated from the record's expected and actual quantities. The UI shows actual loss, recipe standard loss, and actual-minus-standard variance in percentage points. Updating actual quantities preserves the standard snapshot. Historical records are not backfilled.

## Verification evidence

- Disposable PostgreSQL 16 runner passed all 10 focused tests against database fmcg_m21_s02_t003_bd03cdbfff5842fa8fd582d8; Alembic reached 20261028_0021.
- Disposable image: postgres:16-alpine, image ID sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229.
- Test container was loopback-bound, had no volume mounts, used synthetic schema checks only, and the task-labelled container was removed by the runner.
- Focused Python suite: 9 passed, including weighted aggregation, no-match behavior, material-code resolution, creation snapshot, and update preservation.
- Frontend type-check passed.
- Python compilation passed for changed backend modules and migration.
- git diff --check passed.
- Independent read-only review found no blocker after confirming snapshot persistence and update preservation coverage.

## Scope limits

Standards are only compared for the same material and UOM. This task does not aggregate unlike material units into a single order-level yield percentage and does not backfill historical standards.