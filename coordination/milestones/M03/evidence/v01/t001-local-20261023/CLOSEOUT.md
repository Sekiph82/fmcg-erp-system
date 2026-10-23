# M03.S02.T001 — Standardize duplicate detection across masters

**Result:** Shared database-key duplicate checks and focused local verification are complete. The implementation follows the existing declared unique constraints; it does not add fuzzy matching or change key definitions.

## Delivered

- Added shared detection that reads single-column and composite unique keys from SQLAlchemy model metadata, skips nullable key values, and returns the matching field names without exposing stored key values.
- Applied the same matching rules to Product, Material, Supplier, Warehouse, Company, Branch, and Recipe create/update paths. Direct duplicate requests receive a consistent HTTP 409 `duplicate_master_record` response.
- Routed Product, Material, Supplier, and Warehouse bulk-import duplicate checks through the model's declared unique constraints. Product imports now check both SKU and barcode.
- Corrected CSV batch handling so a rejected row does not reserve one of its other keys and incorrectly reject a later valid row. This covers both CSV duplicate rejection and database duplicate rejection.
- Kept equality semantics aligned with the database constraints. No name, tax identifier, email, phone, case-folding, or fuzzy similarity rule was invented.

## Verification evidence

- Focused run: `python -m pytest -q tests/test_m03_master_duplicate_detection.py tests/test_gap025_multi_company_branch.py` — **26 passed**.
- The task integration test exercised Product CRUD duplicate rejection, Product CSV duplicate detection, detection of a database-existing barcode, key self-exclusion, and synthetic unique-key checks for Product, Material, Supplier, Warehouse, Company, and Branch.
- The CSV regression tests include rejected rows followed by valid rows that reuse an otherwise unused key, covering both in-file duplicate and existing-database rejection paths.
- Tests ran only against loopback PostgreSQL database `fmcg_m03_t001_a17e48cc09bb4c3f8a12620d` in task-labeled container `fmcg-m03-s02-t001-a17e48cc09bb4c3f8a12620d` (`codex.task=M03.S02.T001`). Migrations completed through `20261023_0014`. Only synthetic records were created.
- Python compilation of all changed Python modules and tests — passed.
- `git diff --check` — passed.
- Independent read-only review found and helped correct two CSV key-reservation false positives. The final review confirmed both paths are fixed and no concrete blocker remains.

## Scope and limits

- The TASKS.md row had no linked M03 acceptance file, and the repository had no M03-specific duplicate-detection audit. The implementation therefore uses the existing database unique constraints as the business-key source of truth, consistent with the active audit policy requiring reconciliation with existing capabilities.
- Similar names or contact details are not automatically treated as duplicates. The task does not change migrations or existing database key definitions.
- The runtime suite does not exercise every individual HTTP route, every import adapter, or concurrent insert races. Existing database constraints remain the final protection against concurrent duplicate writes.
- No GitHub Actions, production deployment, external audit, or owner acceptance was performed.
