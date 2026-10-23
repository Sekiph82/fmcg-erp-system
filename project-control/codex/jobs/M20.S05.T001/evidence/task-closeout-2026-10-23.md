# M20.S05.T001 — Backend MPS regression tests

## Result

The backend regression suite passed on a newly created task-owned PostgreSQL 16 container bound to loopback. The database was named with the required `fmcg_m20_t001_<32 hex>` pattern, guarded with `M20_DISPOSABLE_TEST_DATABASE=1` and the exact database-name variable, upgraded with Alembic, and removed after the run. No production or owner database was used.

Command scope:

- `python -m alembic upgrade head`
- `python -m pytest -q` over `test_m20_auth_transaction_boundary.py`, `test_m20_remaining_engine.py`, `test_m20_postgres_scenario_savepoint.py`, `test_m20_s01_t001_mps_hardening.py`, `test_m20_v03_acceptance.py`, `test_m20_s01_t001_v02_mps_remediation.py`, `test_m20_s01_t001_v03_mps_remediation.py`, `test_m20_s01_t002_mps_preservation.py`, `test_m20_strict_findings.py`, and `test_mps_sequences.py`

**Result: 111 passed, 0 failed, 0 skipped; 70 warnings.** Warnings are existing dependency deprecations, including Pydantic schema/config deprecations and the Starlette/httpx test-client warning.

## Coverage and fixes

- Added PostgreSQL-backed ASGI coverage for what-if scenario create, invalid-input rollback, list/detail, comparison serialization, cross-plan rejection, warehouse scope, and missing permissions.
- Scenario creation now requires both the route's `mps.simulate` permission and edit access to the plan's source warehouse. The test verifies scoped success, missing scope denial, and missing simulate permission denial.
- Fixed a pytest event-loop connection reuse issue by disposing the async engine before the PostgreSQL savepoint scenario test.
- Updated sequence-service tests to submit a valid line update and to reject a released plan before looking up its line.

## Independent review and deferred evidence

An independent read-only review found no remaining concrete issue in the final changes. GitHub Actions/remote CI were not run; they remain deferred under the M20 quota restriction through 2026-10-30. This is local task evidence only and does not approve or close the M20 milestone.

Changed-file Ruff checks report 18 findings, and the same 18 are present in the fetched `origin/main` versions of those files; this task introduced no new Ruff findings. `git diff --check` passed.
