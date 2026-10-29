# M05.S03.T003 — Negative-stock and concurrency safeguards V01

## Scope and synchronized baseline

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Exact selected task: `M05.S03.T003 — Validate negative-stock/concurrency safeguards` from root `TASKS.md`.
- Starting `HEAD == origin/main`: `5638c637589f6b8e783d7641d4cdb085c36e0609` (task claim and acceptance material).
- The exact canonical local root was verified and fetched before implementation. Existing unrelated owner modifications/untracked content were preserved and not staged.
- Read this task's generated prompt and criteria, `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012, `coordination/AUDIT_POLICY.md`, GAP-002/GAP-008 audit material, T001/T002 evidence, and the current inventory/procurement/production services, API callers, session dependency, models, and tests.

## Defects proven and narrow corrections

1. **Duplicate GRN posting.** PostgreSQL concurrency test with a stale draft GRN showed two concurrent post requests could both commit. The service checked the caller's stale status and had no source-receipt serialization; both calls could add movements/stock and increment PO received quantity. `post_grn` now locks the owning PO first (serializing partial receipts), then locks and refreshes the GRN before checking its state. Stock and PO-line rows are refreshed under their locks, and the PO-line aggregate is refreshed after updates. Existing PO/GRN business states remain unchanged.
2. **Duplicate production completion.** Two concurrent requests carrying the same stale IN_PROGRESS order could both consume materials and receive finished goods. `complete_order` now locks and refreshes the production-order row before checking its transition. The losing request sees the persisted COMPLETED state and cannot duplicate material consumption or finished-goods output.
3. **Locked stock identity freshness.** Inventory issue, production material issue/finished-goods receipt, and procurement stock upsert now refresh already-present ORM identity-map rows after acquiring `FOR UPDATE`. This ensures the guard and arithmetic use the database row version obtained under lock, not a cached value.

The corrections are limited to transaction locking/refresh and state revalidation. No schema migration, production policy, accounting integration, allocation rule, valuation rule, or public API contract changed. T001 sales allocation/dispatch and T002 transaction behavior were retained.

## Direct PostgreSQL acceptance evidence

- Added `backend/tests/test_m05_s03_t003_stock_concurrency_db.py` with an exact name/engine/host/no-password guard. Every actor, order, item, stock row, receipt, and reference is synthetic and uniquely suffixed.
- The suite directly verifies an inventory issue above available quantity raises `INSUFFICIENT_STOCK` and leaves stock/movement records unchanged.
- Duplicate GRN race: the first service call holds the transaction after posting; a second request has already loaded the stale DRAFT object. The test records its backend PID, confirms a real PostgreSQL lock wait in `pg_stat_activity`, releases the first transaction, and verifies the second receives the already-posted guard. One GRN movement, one PO receipt increment, and the exact stock total persist.
- Duplicate production-completion race uses the same method with a stale IN_PROGRESS object. A real PostgreSQL lock wait is observed; the second call is rejected after the first commits. Exactly one material consumption, finished-goods receipt, issue/receipt pair, and output-stock increment remain.
- Competing production orders start with only six units of shared synthetic material and each require four. The test waits until both worker backends are queued on the stock row, observes both PostgreSQL lock waits, then releases the blocker. Exactly one order completes, one reports `INSUFFICIENT_MATERIAL`, material stock remains nonnegative at two units, and only the winner has movement/consumption/finished-goods records.

## Disposable PostgreSQL and commands

Final isolated environment:

- PostgreSQL image `postgres:16.6-alpine`; exact DB `fmcg_m05_s03_t003_98e370077c0a4d8faddc`; passwordless `postgres` user; host bound only to `127.0.0.1:61335`; no mounts; only a 512 MiB tmpfs at `/var/lib/postgresql/data`; task/disposable labels; restart policy `no`.
- Fresh `python -m alembic upgrade head` passed. `python -m alembic heads` and `python -m alembic current` both report the single head `20261029_0025`.
- `M05_S03_T003_DISPOSABLE_TEST_DATABASE=1`, exact matching `M05_S03_T003_DISPOSABLE_TEST_DATABASE_NAME`, and `DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:61335/fmcg_m05_s03_t003_98e370077c0a4d8faddc` were set only for this DB.
- `python -m pytest -q tests/test_m05_s03_t003_stock_concurrency_db.py --tb=short` — **5 passed, 1 existing Starlette deprecation warning** on the final fresh database; `postgres-tests-final.log`.
- `python -m pytest -q tests/test_gap009_procurement_maturity.py tests/test_production_cost_yield_variance.py tests/test_gap010_crm_sales_commercial_access.py tests/test_moto_sales_mpesa_delegation.py --tb=short` — **23 passed, 1 existing Starlette deprecation warning**; `related-regressions-final.log`.
- `python -m py_compile app/services/inventory_service.py app/services/procurement_service.py app/services/production_service.py tests/test_m05_s03_t003_stock_concurrency_db.py` — passed.
- `git diff --check` — passed before commit.

## Attempts, review, and cleanup

- Initial disposable run before service corrections produced **2 intended failures**: duplicate GRN and duplicate production completion both committed; the insufficient-stock and competing-stock tests passed. This directly exposed the two workflow races.
- The first rerun after code correction still reported the same two failures because the test's blocker held a row but did not execute/commit the first business operation. The concurrency harness was corrected to post/complete in the blocker transaction while the second request held its preloaded stale entity. Both tests now prove a real lock wait against a committed first transaction and fail for duplicate side effects if serialization is removed.
- Corrected attempt run: **5 passed, 1 warning** (`postgres-tests-attempt03.log`). Final clean-database run independently reports **5 passed**.
- Independent read-only reviewer inspected the three service diffs, API callers, and test suite; found no remaining material issues. Reviewer did not edit, run tests, or access the database. This is source review, distinct from test evidence.
- Final and attempt containers were inspected by exact name, task labels, restart policy, mounts/tmpfs and loopback binding before removal. Both were removed; exact `docker inspect` absence was verified. Metadata is recorded in `container-attempt01-cleanup.json` and `container-final-cleanup.json`.
- No real factory, employee, supplier/customer data, live credential, normal development/staging/production database, external service, application process, or GitHub Actions was used. This does not establish physical-factory or production acceptance.
- Root `TASKS.md` was read and is authorized for queue updates; T003 is now `COMPLETE`, and dependency-ready successor `M06.S03.T001 — Verify three-way-match transaction chain` is selected explicitly.

## Evidence hashes

`artifact-hashes-final.json` records SHA-256 values for criteria, prompt, task tests, changed services, migration/head/current output, final focused/related test output, and final cleanup metadata. The hash table excludes itself and this log.
