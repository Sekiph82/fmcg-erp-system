# M05.S03.T003 — Negative-stock and concurrency safeguards V01

## Authority and reviewed basis

The only selected implementation scope is `M05.S03.T003 — Validate negative-stock/concurrency safeguards` from root `TASKS.md`, with the generated next-task prompt from `node scripts/codex/task-queue.mjs --spec`. The owner authorized synthetic virtual data and routine autonomous task/tracker updates. No physical factory, staff, or live operational data is presumed.

Read before implementation:

- `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/011/012 and `coordination/AUDIT_POLICY.md` critical-flow/concurrency/negative-test requirements.
- `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, and the M05.S03.T001/T002 criteria, prompts, logs, and direct tests.
- Current inventory issue, GRN post, production completion services and authenticated API callers, stock/production/procurement models, transaction/session rules, and tests.

T001 already verifies sales order allocation/dispatch reservation concurrency. T002 verifies transaction commit/rollback and repeated transitions for GRN, production completion, and shipment dispatch. Avoid duplicating their scope; this task targets negative stock and concurrent retries across inventory/procurement/production.

## Acceptance criteria

1. Trace exact stock-decreasing issue paths and the GRN/production state checks that protect stock-changing work. Record lock target, lock ordering, identity-map refresh behavior, the persisted state rechecked under lock, database transaction boundary, and ledger/source side effects.
2. Add a focused task-owned PostgreSQL test module that only writes when `M05_S03_T003_DISPOSABLE_TEST_DATABASE=1`, the URL is passwordless loopback PostgreSQL, and its database exactly matches `fmcg_m05_s03_t003_<hex>`. All rows/users/materials/products/orders are unique synthetic fixtures. Refuse other URLs/database names.
3. Directly prove inventory material/product issue cannot consume unavailable quantity; assert the intended insufficient-stock guard fires and persisted on-hand/available balances plus stock-movement count remain unchanged.
4. Exercise concurrent duplicate posting of one stale draft GRN using independent PostgreSQL sessions. At most one request may commit. The losing request must observe the persisted POSTED state after acquiring the source-row lock. Assert one stock movement, one accepted-quantity increment, and one stock increase.
5. Exercise concurrent completion retries for one stale IN_PROGRESS production order using independent PostgreSQL sessions. At most one request may commit. The loser must observe the persisted terminal state after acquiring the order lock. Assert one material consumption, one finished-goods receipt, one issue/receipt pair, and exact stock totals; no duplicate output or negative balance.
6. Exercise two independent production orders attempting to consume the same limited material stock concurrently. Assert stock/available never become negative, successful material movements equal the actual stock reduction, and the losing insufficient-material attempt leaves its order/receipt effects absent.
7. Tests must force and observe actual PostgreSQL lock waits for race cases (for example via `pg_stat_activity.wait_event_type='Lock'`) rather than relying on an unobserved `asyncio.gather` ordering. Negative tests must arrange other preconditions so the intended stock or state guard is the cause.
8. If evidence proves a defect, add only narrow service-level row-lock/refresh or guard correction necessary for these invariants; preserve existing business, allocation, receipt, costing, and accounting policies. Keep T001/T002 contracts intact. Do not add a new stock ownership schema, costing rule, accounting integration, retry policy, or public API.
9. Run the new task tests and relevant M05 sales plus inventory/procurement/production regression tests on a fresh disposable PostgreSQL database migrated to the current single Alembic head. Record exact commands/outcomes, failures/corrections, hashes, containment/cleanup, changed paths, review, and limitations in `CODEX_LOG_V01.md`.
10. No claim of real-factory use, production rollout, live credentials, external integration, or GitHub Actions evidence.

## Stop conditions

Stop only dependent changes if a required business choice, real operational credential/data, destructive schema change, or non-disposable database is required. Report the precise issue in Turkish; never fabricate a passing race or negative-stock result.
