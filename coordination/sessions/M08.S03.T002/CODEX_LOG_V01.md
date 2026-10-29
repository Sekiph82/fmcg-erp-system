# M08.S03.T002 — Verify production/inventory transaction atomicity

**Status:** COMPLETE
**Actor:** CODEX
**Date:** 2026-10-29
**Canonical checkout:** `C:\Users\sekip\Desktop\fmcg-erp-system`

## Scope and references

The canonical task row was the exact scope. It had no linked task-specific acceptance artifact. I used the queue-generated M08.S03.T002 prompt, `coordination/AUDIT_POLICY.md`, applicable ERP/MES rules ERP-AL-010 and ERP-AL-012 from `coordination/AUDIT_INDEX.md`, and the existing production/inventory transaction tests as context. The existing service already used one session/commit boundary for material consumption, finished-goods receipt, and order completion, with rollback on propagated exceptions. Synthetic tests were added for this exact task.

## Changes

- Added shared, deterministic, transaction-scoped PostgreSQL advisory locks for logical lot and stock keys. A row-level `FOR UPDATE` cannot protect a stock or lot row that does not exist yet.
- Applied the same lot/stock keys across production receipts, inventory stock entry/transfer, procurement GRN receipt, generic stock-movement upserts, bulk stock import, and subcontract material-stock updates. Protected lot creation with a duplicate check. Stock-key queries now distinguish an explicit null lot from lot-managed rows.
- Acquired transfer keys and row locks in stable order; production recipes now lock material rows in stable material order.
- Added a barrier-controlled test for production receipt racing with stock entry for the same new lot/stock key. It observes the second PostgreSQL backend waiting specifically on an advisory lock before releasing the first transaction, for both lot-managed and no-lot identities.
- Added direct tests for production completion success/retry rejection and rollback after a forced late failure that occurs after material issue.

No schema migration was required. Advisory locks are acquired only on PostgreSQL; other dialects retain existing behavior.

## Verification evidence

- Fresh isolated PostgreSQL 16.6 Alpine container, random loopback port, `tmpfs` data directory, no persistent volume, passwordless local connection, and exact task-prefixed synthetic database name.
- `alembic upgrade head` succeeded; `alembic heads` and `alembic current` both reported the single revision `20261029_0025`.
- `pytest tests/test_m08_s03_t002_production_inventory_atomicity_db.py -q`: **6 passed**. This includes successful atomic production/inventory posting, repeat rejection without duplicate effects, full rollback after an injected late failure, same-order concurrent completion, and deterministic cross-writer advisory-lock tests for both lot-managed and null-lot stock keys.
- Additional focused regression command covering M08 transition/auth, M08 atomicity guard, procurement maturity, production costing, and scoped-access tests: **32 passed, 21 skipped**. The skipped cases require their own task-specific disposable database environment.
- `py_compile` succeeded for all changed Python files; `git diff --check` succeeded.
- The disposable PostgreSQL container was removed and verified absent. No password was created or shared.
- Independent read-only review confirmed consistent identity keys across the inspected stock upsert paths, stable transfer lock ordering, and test sensitivity. No concrete P1/P2 issue was reported; the reviewer did not run tests or edit files.

## Limitations

- This is focused evidence, not a full repository suite or production deployment acceptance.
- Direct database writers outside the inspected application paths do not participate in the advisory-lock protocol. No GitHub Actions were dispatched, and no live production data was used.
