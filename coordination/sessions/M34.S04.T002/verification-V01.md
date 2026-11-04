# M34.S04.T002 verification evidence

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Focused unit/regression tests | PASS — 18 passed | `backend` working directory; `python -m pytest tests/test_m34_s04_t001_invoice_match_hardening.py tests/test_m34_s04_t002_tolerance_exception_approval.py -q` |
| Disposable PostgreSQL integration | PASS — 7 passed | `disposable-postgres-V03.log`, `alembic-upgrade-V03.log`, `pytest-postgres-V03.log`, `container-cleanup-V03.log` |
| Alembic schema | PASS — `20261104_0001 (head)` | `alembic-upgrade-V03.log` |
| Targeted Ruff (endpoint, schema, task tests) | PASS | Ruff check over the changed endpoint/schema and T001/T002 task tests |
| Service Ruff comparison | BASELINE — 15 existing findings | Current and `HEAD` service versions each report the same 15 pre-existing findings; no new service finding was introduced |
| Python compilation | PASS | `python -m compileall -q` over changed endpoint/schema/service and task tests |
| Patch whitespace | PASS | `git diff --check` |
| Independent read-only review | PASS after fix | Reviewer identified and rechecked subsequent-invoice quantity variance; no remaining actionable finding reported |

The disposable database used PostgreSQL 16.6, a unique task-prefixed database name, passwordless `trust` authentication bound only to loopback, and `M34_S04_T002_DISPOSABLE_TEST_DATABASE=1`. The container was removed in the runner's `finally` path and absence was verified. No live database was used.

## Known nonblocking warnings

The focused test output includes a Starlette `TestClient` deprecation warning. PostgreSQL tests include existing `datetime.utcnow()` deprecation warnings. These did not fail checks and are not changed in this task.
