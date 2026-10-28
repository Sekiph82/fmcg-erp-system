# M21.S02.T002 — Model filling/packaging loss and spillage

## Result

Filling and packaging-reject loss categories were already part of the BOM loss model. Added a distinct `SPILLAGE` category without reclassifying existing transfer or packaging records. Standard and max-allowable rates are now explicitly entered through the API/UI; the form no longer supplies a preset loss percentage. Negative and non-finite rate values are rejected by the API schema and database checks. No loss rates were fabricated.

## Verification evidence

- Disposable PostgreSQL 16 run: `8 passed in 3.95s`, including persistence of filling, packaging-reject, and spillage configs and direct database rejection of NaN in both rate columns.
- Migration state: `20261028_0020`, applied after `20261028_0019`.
- Disposable database: `fmcg_m21_s02_t002_411426ce2a6a45d3acb26632`; synthetic loss configurations only, loopback-bound ephemeral port, no volume mounts.
- Task-labelled disposable container cleanup: verified; no container remained for label `codex.task=M21.S02.T002`.
- Focused unit suite: `7 passed in 4.88s`, including category and rate validation contracts.
- Frontend: `npm.cmd run type-check` passed (`tsc --noEmit`).
- Python compilation: passed for the model, schema, migration, and tests.
- `git diff --check`: passed.
- Independent read-only review: confirmed model/migration checks match and direct DB writes cannot persist NaN; no blockers.

## Scope and limits

This task configures loss categories and rates. It does not calculate actual loss or combine stage percentages; those behaviors remain for later yield/variance tasks. No upper cap or cross-category aggregation formula was introduced. Downgrade removes the added checks but retains the PostgreSQL enum label because enum labels cannot be removed in place without rebuilding the type and risking stored loss data.
