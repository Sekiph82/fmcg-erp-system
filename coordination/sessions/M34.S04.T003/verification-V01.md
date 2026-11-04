# M34.S04.T003 verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Task-owned PostgreSQL integration | PASS — 5 passed | `postgres-run-V03.log`, `alembic-upgrade-V03.log`, `pytest-postgres-V03.log`, `container-cleanup-V03.log` |
| Alembic migration | PASS — `20261104_0001 (head)` | `alembic-upgrade-V03.log` |
| Existing allocation-basis regression | PASS — 18 passed | `python -m pytest tests/test_m25_s02_t002_allocation_basis.py -q` from `backend` |
| Targeted Ruff | PASS | Landed-cost service, endpoint, and T003 PostgreSQL regression module |
| Python compilation | PASS | Changed service, endpoint, and T003 regression module |
| Patch whitespace | PASS | `git diff --check` |
| Independent read-only review | PASS | No actionable findings on source identity checks, locking, allocation safety, or endpoint errors |

The disposable integration runner used `postgres:16.6`, a unique `fmcg_m34_s04_t003_<24 hex>` database, passwordless trust authentication bound only to loopback, and `M34_S04_T003_DISPOSABLE_TEST_DATABASE=1` with the exact expected database name. The container was removed in the runner's `finally` path and absence was verified.
