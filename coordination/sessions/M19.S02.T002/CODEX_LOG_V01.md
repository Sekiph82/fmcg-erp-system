# M19.S02.T002 — Tenant/company isolation verification

## Result

The company summary endpoint and a focused two-company production-ASGI integration check were corrected and verified on a task-owned disposable PostgreSQL database. No production database, owner data, deployed environment, or GitHub Actions were used.

## Change

- Scoped warehouse, open purchase-order, and open sales-order summary counts to the requested `company_id`.
- Replaced stale purchase-order status names with the existing `APPROVED`, `ORDERED`, and `PARTIALLY_RECEIVED` enum values. The previous query raised an `AttributeError` and returned HTTP 500.
- Kept active product count global because the Product model has no company ownership field; this is shared catalog data under the current schema.
- Added `backend/tests/test_m19_s02_t002_company_isolation.py`. It exercises the production ASGI app with a synthetic company viewer, two companies, company-owned and unassigned warehouses/orders, and asserts own-company counts and HTTP 403 for the other company.
- Added `run_disposable_company_summary_test.ps1`, which creates a unique task-labeled PostgreSQL container, binds its ephemeral port to loopback only, uses no volumes, migrates to head, sets the exact M19 test gate, runs the focused test, and stops/removes the container.

## Verification evidence

| Check | Result |
|---|---|
| `run_disposable_company_summary_test.ps1` | **PASS** — focused test `1 passed`; migration state `20261028_0017`; PostgreSQL `postgres:16-alpine`, local image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229` |
| Disposable database | `fmcg_m19_s02_t002_8ac6fd23db7b4c96bc4f0fc3`; synthetic records only; runner confirmed loopback binding and no volume mounts |
| Exact task container after run | No matching container remained in `docker container ls -a` |
| `tests/test_gap_sec001_access_control.py tests/test_gap025_multi_company_branch.py` | **PASS** — 35 passed in 3.29s |
| Independent read-only review | No blocker found. Reviewer confirmed company filters, valid enum members, authorization assertions, global Product schema semantics, and runner isolation. |
| Whitespace checks (`git diff --check` plus all task files) | **PASS** |

The first focused run failed because the old summary query referenced nonexistent PO enum members. That defect was fixed, and the rerun passed. The passing run emitted 71 existing library/application warnings, including short configured test JWT-key and Pydantic deprecation warnings; no warning caused a test failure.

## Limits

- This proves behavior in local synthetic PostgreSQL and the production ASGI application wiring only. It is not evidence for a deployed environment or an external penetration test.
- `M19_DISPOSABLE_TEST_DATABASE` and the exact database-name check are a fail-closed convention, not cryptographic proof of container ownership. Run this test through the task runner only.
- If Docker becomes unavailable during cleanup, the runner fails loudly but cannot guarantee container removal.
