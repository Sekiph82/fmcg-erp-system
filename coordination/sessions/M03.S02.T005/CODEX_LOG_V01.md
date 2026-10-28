# M03.S02.T005 — Implementation Log V01

## Scope and acceptance

The root `TASKS.md` row was the only T005 acceptance material; it contains the title “Validate referential integrity across master domains” and has no linked prompt or criteria file. Relevant prior material reviewed: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, the M03.S02.T001 closeout, and the T002 V01/V02 and T003 implementation logs. The M03 master models already had direct foreign keys for branch-to-company, warehouse-to-company/branch, material-to-supplier, recipe-to-product, and recipe-item-to-recipe/material references. The concrete gap was that the two individually valid warehouse scope references could point to different companies.

The enforced rule is limited to the schema's existing representation: when both `warehouses.company_id` and `warehouses.branch_id` are supplied, the branch must belong to that company. Company-only and branch-only warehouses remain valid. Existing records are not rewritten; adding the validated database constraint fails safely if a pre-existing mismatched pair exists.

## Changes

- Added the `uq_branches_id_company_id` unique target key and migration `20261028_0017`'s `fk_warehouses_branch_company` composite foreign key. PostgreSQL validates existing rows and enforces the pair for all database writers. The PostgreSQL-specific `ON DELETE SET NULL (branch_id)` action preserves the existing behavior of detaching a deleted branch while retaining the warehouse's company scope.
- The migration guards creation against the same named constraints already present through the squashed model-metadata baseline. Downgrade removes the composite FK and its supporting unique key.
- Added a warehouse CRUD preflight that reports a missing or company-mismatched branch as a structured 422. The database constraint remains authoritative for direct writes and races; the integrity error handler maps that exact FK conflict to a structured 409 without returning database details.
- Documented why the composite FK is migration-managed: SQLAlchemy's `ondelete` validator rejects PostgreSQL's column-specific `SET NULL` syntax. Alembic's `include_object` hook ignores only that exact reflected FK during autogenerate comparison.

## Starting state and ownership

- Starting `HEAD` and fetched `origin/main`: `e8e299ef2b96f92fad052cfa5cc89c40ea4fe966`, with no divergence before T005 was claimed.
- The existing owner edit `frontend/next-env.d.ts` and other unrelated local changes were left untouched and unstaged. No dashboard or private task state was used.
- T005 implementation and closure commits use `[skip ci]`; no GitHub Actions were dispatched.

## Changed files

- `backend/alembic/env.py`
- `backend/alembic/versions/20261028_0017_warehouse_branch_company_integrity.py`
- `backend/app/core/exception_handlers.py`
- `backend/app/crud/master.py`
- `backend/app/models/company.py`
- `backend/app/models/master.py`
- `backend/tests/test_m03_master_referential_integrity.py`
- `TASKS.md` (task tracking and evidence only)

## Verification

- `python -m compileall -q` on all changed Python source, migration, and test files — passed.
- `python -m alembic heads` from `backend` — one head, `20261028_0017`.
- A fresh PostgreSQL 18.6 instance bound to loopback only, using a task-owned database named `fmcg_m03_t005_c7728cfa64a14bfba60a4ac8` with trust authentication and no password:
  - `python -m alembic upgrade head` — passed through `20261028_0017`.
  - With `M03_DISPOSABLE_TEST_DATABASE=1` and `M03_DISPOSABLE_TEST_DATABASE_NAME=fmcg_m03_t005_c7728cfa64a14bfba60a4ac8`, `python -m pytest -q tests/test_m03_master_referential_integrity.py` — **2 passed**.
  - The integration test observed API mismatch rejection, direct database mismatch rejection by the named composite FK, rejection of moving a referenced branch to another company, acceptance of a branch-only warehouse, and preservation of company scope when a branch is deleted.
- `git diff --check` — passed.
- An early DB test run exposed that a composite FK with default delete behavior blocked the existing branch-detach behavior. A follow-up model compile also showed SQLAlchemy does not accept the column-specific `SET NULL` action. The final migration uses PostgreSQL's supported column-specific action, keeps only the needed unique key in ORM metadata, and documents the migration-managed FK. The clean full-migration rerun and both focused tests then passed.
- Independent read-only review found no remaining functional blocker. The reviewer did not edit files or run tests.
- The disposable PostgreSQL database, process, and temporary server files were removed after verification. No owner/production database or data was accessed; no password was used or shared.

## Limits

No production deployment, live owner-data audit, external audit verdict, or GitHub Actions result is claimed. Existing production data was not inspected; if it contains a warehouse/branch company mismatch, the new migration will fail rather than silently repair it.
