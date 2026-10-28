# M21.S01.T001 — Define bulk-fluid→pack conversion profile model

## Scope and audit

The task row has no dedicated acceptance checklist. I reviewed the latest applicable repository materials available for this capability: `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_AUDIT.md` and `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_IMPLEMENTATION_NOTES.md`. They document an existing `BOMConversionProfile` model, service/API routes, UI, and migration ownership; they also explicitly caution against creating a parallel formula/BOM architecture. The root M21 milestone depends on the M09 and M20 foundations; M20 is complete, and M09's recipe/BOM model and CRUD foundation exists.

## Result

The requested profile model was already present. It links source and target products, carries a theoretical conversion ratio and target fill quantity/UOM, can reference a packaging BOM, and is registered in the model metadata. The reconciliation migration owns `bom_conversion_profiles` and its product/BOM foreign keys and unique profile code. No new production model or migration was needed.

Added a focused contract test to keep the existing model/schema surface aligned. Density/UOM conversion behavior belongs to M21.S01.T002, SKU/package-component quantities to T003, and profile version/effective-date behavior to T004; those were not pulled into this task.

## Verification

- `backend`: `python -m pytest -q tests/test_m21_s01_t001_conversion_profile_model.py` — **1 passed**.
- `backend`: `python -m py_compile app/models/bom.py app/schemas/bom.py app/services/bom_service.py app/services/bom_scaling_service.py app/api/v1/endpoints/bom.py` — passed.
- Read-only source review confirmed the test's core columns and links are present in both the SQLAlchemy model and the existing reconciliation migration.
- `git diff --check` passed.
- No production data, live database, or GitHub Actions were used.
