# M20.S02.T003 — MPS BOM/material feasibility closeout

## Scope and implementation

Material feasibility now chooses one approved, effective default BOM or approved recipe for each planned line date. Overlapping effective approved versions fail closed with an explicit ambiguity diagnostic. BOM explosion retains batch basis, required yield/waste, optional-line behavior, and nested BOM lifecycle/effectivity checks. `BOMYieldConfig` entries with `PCT_OF_INPUT` basis are aggregated as input loss and gross up required output; duplicate categories, unsupported bases, invalid/max-exceeding percentages, and total loss at or above 100% fail closed.

Material requirements, PO quantities, and finished-product/BOM output quantities use configured UOM conversions. Requirements are normalized to four decimal places in the material's UOM. Active inventory rows must reconcile on-hand, reserved, and available quantities before they are used. Open PO supply is counted only when company and branch/warehouse scope is unambiguous and the expected date is no later than the line's required date. Lines consume supply in planned-start-date order, so later receipts cannot cover earlier requirements. Shortage diagnostics include material UOM, lead time, latest order date, excluded receipt reasons, and the BOM's substitution policy/group. The evaluator never consumes unapproved substitutes to make a line appear feasible.

## Verification

- A fresh task-owned PostgreSQL 16 Docker container used a unique `fmcg_m20_t003_<20-32 hex>` database name, a loopback-only published port, and a `tmpfs` data directory. Alembic reached head before tests. The generated database password was not recorded or reported; environment values were cleared and the exact container/database were removed after each run.
- `python -m pytest tests/test_m20_v03_acceptance.py -q` on the disposable database — **12 passed, 67 warnings**. Warnings are existing Pydantic v2 deprecations; they were not suppressed or counted as failures.
- `python -m pytest tests/test_m20_remaining_engine.py -q` — **30 passed**.
- Focused PostgreSQL MPS material cases — **3 passed**, covering effective BOM feasibility, UOM normalization, configured yield loss, ambiguous company-only PO destination, duplicate active UOM conversions, overlapping approved BOMs, lead-time dates, and chronological allocation within a shared period.
- `python -m py_compile app/services/mps_advanced_service.py app/services/mps_engine.py tests/test_m20_v03_acceptance.py tests/test_m20_remaining_engine.py` — passed.
- `git diff --check` — passed.
- An initial integration assertion exposed excess decimal precision after UOM conversion. Quantizing normalized material needs to four decimal places fixed the discrepancy; the final integration and acceptance runs above passed.

## Independent review and limits

An independent read-only reviewer checked date ordering, yield configuration, duplicate UOM handling, company/warehouse PO scope, substitution policy, effective BOM/recipe selection, inventory reconciliation, and diagnostic quantities/dates. The final review reported no concrete remaining defects and did not run tests or access a database.

Only synthetic task fixtures and the disposable database were used. GitHub Actions were not run, consistent with the M20 CI hold through 2026-10-30. The milestone-wide owner-data, CI, and visual-acceptance gates recorded in the latest M20 audit remain separate from this task's closeout.
