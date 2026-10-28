# M21.S01.T002 — Density and UOM conversion rules

## Scope and acceptance context

The root `TASKS.md` row requests density/UOM conversion rules and has no separate acceptance checklist. I reviewed the latest applicable materials, `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_AUDIT.md` and `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_IMPLEMENTATION_NOTES.md`. They document the existing Advanced BOM conversion profile and caution against adding a parallel formula/BOM architecture. T001 confirmed the existing profile model; SKU/package component quantities and profile version/effective dates remain in T003 and T004.

## Changes

- Conversion now normalizes an input quantity to the linked source product's canonical UOM. Without a linked source product, callers must provide a source UOM, which is used as the ratio basis.
- Standard `G`/`KG` and `ML`/`L` conversions are handled directly. Mass/volume conversions use the profile's density in g/mL; missing, non-positive, NaN, or infinite density is rejected with HTTP 422.
- Other units use the existing configured UOM conversion service, including direct and inverse factors. Results retain the submitted input UOM and identify normalized quantity/UOM in the calculation notes.
- Added focused unit tests and a disposable PostgreSQL integration test. No production schema or migration change was needed.

## Verification evidence

- `coordination/sessions/M21.S01.T002/run_disposable_density_uom_tests.ps1` — **PASS: 18 passed**. This includes the density/UOM unit tests, synthetic PostgreSQL integration test, and the T001 profile contract test.
- The runner used local `postgres:16-alpine`, image `sha256:16bc17d64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`, and disposable database `fmcg_m21_s01_t002_98e59ec9c1534b0795cd17a8`. Alembic reached `20261028_0017`.
- The PostgreSQL container had no volume mounts and published its port on `127.0.0.1` only. Test records were synthetic products, conversion profiles, and UOM factors. The runner restored its environment overrides and stopped the exact task-labelled container; a post-run query found no remaining `M21.S01.T002` container.
- `py_compile` for the changed service, endpoint, and tests — passed.
- `git diff --check` — passed.
- An independent read-only review found and reported a non-finite-density edge case. The implementation and parametrized tests were updated for NaN and both infinities; the reviewer confirmed the blocker resolved. No other blocker was reported in the scoped review.

## Limits

This is local test evidence against a fresh disposable database, not a production-data or live-environment verification. For a profile without a linked source product, the explicit source UOM is necessarily treated as its conversion-ratio basis.
