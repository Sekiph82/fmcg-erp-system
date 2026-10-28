# M21.S01.T003 — Package component quantities by SKU/size

## Scope and acceptance context

The canonical `TASKS.md` row asks for package component quantities by SKU/size and has no separate acceptance checklist. The applicable `GAP-021` audit and implementation notes describe the existing `BOMConversionProfile` target-product and linked-packaging-BOM fields, plus the existing Advanced BOM line quantity/UOM/loss contract. They recommend extending those existing structures instead of introducing a parallel BOM model.

## Changes

- Added a read-only package-component calculation for a conversion profile's exact target product/SKU and linked packaging BOM.
- The route requires a positive finite target quantity, verifies the linked BOM is `PACKAGING` and belongs to that same target product, normalizes the requested target UOM to the BOM base UOM with the existing conversion utility, and returns only `PACKAGING` component lines with scaled and adjusted quantities.
- The caller supplies the explicit target SKU quantity. This operation does not infer a gross-versus-good quantity from conversion yield percentages.
- Added unit and disposable PostgreSQL integration coverage. No new production schema or migration was needed.

## Verification evidence

- `coordination/sessions/M21.S01.T003/run_disposable_package_component_tests.ps1` — **PASS: 8 passed**, including the package-component unit tests, PostgreSQL integration test, and T001 profile contract test.
- The runner used local `postgres:16-alpine`, image `sha256:16bc17d64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`, disposable database `fmcg_m21_s01_t003_37a2272e4ba54b7f9bfd6420`, and Alembic revision `20261028_0017`.
- Integration coverage verified a synthetic 500 ml target SKU's packaging BOM, packaging-only component filtering, per-unit quantities, component wastage, and a configured `2 CARTON` → `24 PCS` request conversion. Test data was synthetic and rolled back in the test transaction.
- The runner used no volume mounts and published its port on `127.0.0.1` only. It restored environment overrides and stopped the exact task-labelled container; a post-run query found no remaining `M21.S01.T003` container.
- `py_compile` for the changed service, endpoint, schema, and tests — passed.
- `git diff --check` — passed.
- Independent read-only review found no remaining blocker. It confirmed the explicit target quantity avoids choosing a yield basis, and checked SKU/BOM matching, UOM normalization, packaging-only filtering, test rollback, and disposable container cleanup.

## Limits

This is local evidence against a fresh disposable database, not production-data or live-environment verification. Each target SKU/size still needs an accurately configured target product, linked packaging BOM, component quantities, and UOM conversion factors where the product and BOM base units differ.
