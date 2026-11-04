# M34.S05.T002 Verification

## Scope

The database-backed test calls the supplier dashboard through FastAPI/ASGI with authenticated synthetic users. It verifies rolling OTIF from posted GRN line quantities and dates; recorded supplier evaluation dimensions and date ordering; latest ended active ESG selection; and per-type QMS food-safety status/current/expiry handling. It also verifies a branch-scoped user sees only in-scope procurement counts/evaluations and receives no supplier-wide ESG or food-safety signals.

All suppliers, users, roles, scopes, POs, receipts, evaluations, ESG records, and food-safety rows are synthetic and removed during test cleanup. The test mints signed test cookies and exercises `get_current_user`; it does not exercise password login or the interactive 2FA challenge.

## Evidence

- `disposable-postgres-run-V03.log`: unique task-owned `postgres:16.6` database and container, loopback-only host binding, no password, Alembic upgrade through `20261104_0001`, guarded T002 database test module: **2 passed, 69 warnings**.
- `container-cleanup-V03.log`: removed the task container and verified it is absent.
- Existing scorecard unit regression: `python -m pytest -q tests/test_m34_s03_t002_supplier_scorecard.py`: **2 passed**.
- `git diff --check`: passed.
- Independent read-only review: no substantive findings on score calculations, OTIF source linkage, time/status filters, scoped privacy, auth fixtures, cleanup, or task scope.

Warnings are Pydantic configuration/deprecation warnings from existing application imports; test assertions passed.
