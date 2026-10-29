# M05.S03.T002 — Cross-module transaction integrity V01

## Scope and synchronized baseline

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Exact selected task: `M05.S03.T002 — Validate transaction integrity across production/procurement/sales` from root `TASKS.md`.
- Starting commit and fetched `origin/main`: `ce2b5e94af9687b37ba90bfa585774f641b50f08` (task claim and criteria/prompt).
- The exact local checkout was verified before task work; `git fetch origin main` reported no divergence. Pre-existing modified `frontend/next-env.d.ts`, untracked owner files, M20 evidence, dashboard files, and all other unrelated content were left untouched and unstaged.
- Read task criteria/prompt, `coordination/AUDIT_INDEX.md` (ERP-AL-003/004/010/011/012), `coordination/AUDIT_POLICY.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, GAP-008 and GAP-010, the preceding M05.S03.T001 criteria/log, and the actual models, services, endpoints, DB session dependency, and related tests.

## Transaction paths reviewed

- Procurement route `backend/app/api/v1/endpoints/procurement.py::post_grn` authenticates and checks scoped action permission, calls `procurement_service.post_grn`, then commits. The service stages receipt movements, stock balances, GRN line linkage, received PO-line quantity, GRN status, and PO status in the shared session. Uncaught request errors reach `get_db`, which rolls back.
- Production route `backend/app/api/v1/endpoints/production.py::complete_order` authenticates and checks the close action, calls `production_service.complete_order`, then commits. The service stages material issues and consumption rows, finished-goods movement/receipt/stock, and order completion in the same session. Uncaught request errors reach `get_db`, which rolls back.
- Sales route `backend/app/api/v1/endpoints/sales.py::dispatch_shipment` authenticates, runs its prepaid-payment guard, calls `sales_service.dispatch_shipment`, then commits. The service stages stock deductions, issue movements, shipment-line linkage, shipped quantity, and shipment/order state in the same session. Uncaught request errors reach `get_db`, which rolls back.
- Existing GAP-002 audit explicitly says operational GL posting is a known follow-on gap. These tests assert this scope truthfully; they do not add accounting behavior.

## Implementation and direct evidence

- No service/API code defect was proven within the selected transaction-integrity scope, so no production-code changes were made.
- Added `backend/tests/test_m05_s03_t002_transaction_integrity_db.py`. It refuses writes unless explicitly enabled for a passwordless PostgreSQL URL bound to loopback and the exact task-prefixed database name. Its records are synthetic and uniquely suffixed.
- Successful PostgreSQL scenarios verify coherent persisted source state, stock, stock movements, source-to-movement links, order/PO progress, and synthetic actor attribution for each of the three flows. Repeated GRN, production completion, and shipment dispatch calls verify the expected lifecycle guard and no duplicate persisted movement/receipt/consumption or stock change. Tests compare before/after journal-entry and posting-batch totals, and inspect the related operational accounting-link fields.
- Each flow is also executed inside a real PostgreSQL transaction followed by an injected failure after the service returns and before commit. Fresh verification sessions prove source state, stock balances, movements, consumption/receipt rows, and procurement/sales progress were rolled back.
- These checks establish service-level transaction participation and current audited side effects with synthetic data; they do not constitute authenticated HTTP end-to-end testing, concurrency proof, GL integration, or production acceptance.

## Disposable PostgreSQL and commands

Final isolated environment:

- PostgreSQL image `postgres:16.6-alpine`; exact DB `fmcg_m05_s03_t002_099cc2bdead04010b854`; passwordless `postgres` user; host binding `127.0.0.1:51700`; no data volume mounts; only a 512 MiB tmpfs for the database; task/disposable labels; restart policy `no`.
- Fresh migration: `python -m alembic upgrade head` — passed. `python -m alembic heads` and `python -m alembic current` both report the single head `20261029_0025`.
- `M05_S03_T002_DISPOSABLE_TEST_DATABASE=1`, exact matching `M05_S03_T002_DISPOSABLE_TEST_DATABASE_NAME`, and `DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:51700/fmcg_m05_s03_t002_099cc2bdead04010b854` were used only for this task database.
- `python -m pytest -q tests/test_m05_s03_t002_transaction_integrity_db.py --tb=short` — **7 passed** on the final fresh database; `postgres-tests-final.log`.
- `python -m pytest -q tests/test_gap009_procurement_maturity.py tests/test_production_cost_yield_variance.py tests/test_gap010_crm_sales_commercial_access.py tests/test_moto_sales_mpesa_delegation.py --tb=short` — **23 passed, 1 existing Starlette deprecation warning**; `related-regressions.log`.
- `python -m py_compile app/services/procurement_service.py app/services/production_service.py app/services/sales_service.py tests/test_m05_s03_t002_transaction_integrity_db.py` — passed.
- `git diff --check` — passed before commit.

## Attempts, review, and cleanup

- Initial disposable-DB test attempt had two test-harness failures: accessing an expired ORM movement attribute after rollback, and asserting a production order using a stock ID. The subsequent attempt exposed another expired ORM ID access and a guard-string expectation that did not account for SQLAlchemy's enum representation. These were corrected; all failures remain recorded in `postgres-tests-attempt01.log` and `postgres-tests-attempt02.log`.
- `postgres-tests-attempt03.log` reports 7 passed after corrections. Final clean run independently reports 7 passed.
- Independent read-only reviewer identified missing before/after journal/batch counts and weak repeat-guard assertions. Both findings were corrected. Re-review found no remaining material findings; reviewer did not run tests or access the database. This is source review, separate from test evidence.
- The exact final task container identity, labels, no-mount/tmpfs configuration, loopback binding, and task DB name are recorded in `container-final-cleanup.json`; `docker rm --force` succeeded and a subsequent exact `docker inspect` confirmed absence. The earlier attempt container was also removed and its absence confirmed.
- No real records, factory, employees, provider, normal development DB, staging DB, production DB, application server, external HTTP integration, or GitHub Actions were used.
- Root `TASKS.md` was read and is authorized for this queue; it currently marks T002 `IN_PROGRESS`. Final completion evidence and next exact task selection will be recorded only after this log and checks are reviewed.

## Evidence hashes

`artifact-hashes-final.json` records SHA-256 values for the criteria, prompt, integration test, final migration/current/head logs, final focused/related test logs, and cleanup metadata. The hash table does not hash itself or this log.
