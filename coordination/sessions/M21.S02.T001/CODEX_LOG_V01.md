# M21.S02.T001 — Model expected process yield

## Owner decision

Q-M21-S02-T001-YIELD-BASIS was answered in this conversation: expected process yield is stored as a percentage of BOM input quantity.

## Result

Added nullable `expected_process_yield_pct` to the BOM header. It is exposed by create/update/output schemas and BOM create/detail UI. New BOMs do not receive an invented yield; existing records remain `NULL`. Negative and non-finite percentages are rejected in the API schema, and PostgreSQL enforces nonnegative values. Cloned BOM versions preserve a configured percentage.

## Verification evidence

- Disposable PostgreSQL 16 run: `6 passed in 4.64s`, including the persistence test for a configured percentage and a legacy BOM with no value.
- Migration state: `20261028_0019`, applied after `20261028_0018`.
- Disposable database: `fmcg_m21_s02_t001_66ddb6691ced4dcc8e63a70e`; synthetic BOM rows only, loopback-bound ephemeral port, no volume mounts.
- Task-labelled disposable container cleanup: verified; no container remained for label `codex.task=M21.S02.T001`.
- Frontend: `npm.cmd run type-check` passed (`tsc --noEmit`).
- Python compilation: passed for modified BOM model/schema/service, migration, and tests.
- `git diff --check`: passed.
- Independent read-only review: no blockers; confirmed nullable behavior, no fabricated default or upper bound, API/UI consistency, clone behavior, and migration compatibility.

## Scope and limits

The field records the configured expected output/input percentage; it does not convert unlike UOMs or generate actual production yield. Existing loss categories remain separate for the following M21 yield/loss tasks. No production or owner data was used.
