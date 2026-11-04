# M34.S04.T004 verification

- Database: `fmcg_m34_s04_t004_4cb09e6007014ee79f0b6176` (disposable; PostgreSQL 16.6; passwordless trust; loopback-only host port).
- Schema: Alembic head `20261104_0001`.
- Guarded test command: `python -m pytest -q tests/test_m34_s04_t004_purchase_invoice_posting_db.py` with `M34_S04_T004_DISPOSABLE_TEST_DATABASE=1` and the matching disposable database name.
- Result: **9 passed, 12 warnings in 11.26s**. The warnings are existing `datetime.utcnow()` deprecations in `invoice_match_service.py`.
- Container cleanup: `container-cleanup-V12.log` records removal and `verified_absent=True`; a separate exact-name `docker ps -a` query also returned no container.
- Static checks: relevant Python files compiled; Ruff passed for the new test and F821 on changed backend modules; targeted frontend ESLint and TypeScript checks passed; `git diff --check` passed.
- Independent final review: no remaining actionable findings.
