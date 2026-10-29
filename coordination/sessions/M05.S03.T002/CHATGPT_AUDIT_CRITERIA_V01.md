# M05.S03.T002 — Cross-module transaction integrity V01

## Authority and reviewed basis

The only selected implementation scope is `M05.S03.T002 — Validate transaction integrity across production/procurement/sales` from root `TASKS.md`. The user has authorized Codex to maintain the tracker and complete unblocked tasks autonomously. Use synthetic virtual ERP records only; no real factory, staff, supplier, customer, or operational data is implied.

Read before implementation:

- `coordination/AUDIT_INDEX.md`: ERP-AL-003/004/010/011/012 (authenticated actor, enforced states, critical transaction evidence, negative-test sensitivity, and cross-module side effects).
- `coordination/AUDIT_POLICY.md`: critical inventory/production/procurement workflows require direct transaction, rollback, repeat-posting, and downstream-effect evidence; tests must fail for the intended reason.
- `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`: current GRN, production material issue, and finished-goods receipt update stock movements/balances; operational GL integration is documented as a known future gap.
- `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md` and `docs/planning/GAP-010_CRM_SALES_PIPELINE_AUDIT.md`: existing stock-ledger and dispatch lifecycle context.
- Prior task evidence `coordination/sessions/M05.S03.T001/CHATGPT_AUDIT_CRITERIA_V01.md` and `CODEX_LOG_V01.md`: synthetic PostgreSQL guard, stock ledger conventions, and no-production-acceptance boundary.
- Current services, endpoints, models, session dependency, and related tests for procurement GRN posting, production order completion, and sales shipment dispatch.

## Acceptance criteria

1. Trace the selected live mutations end-to-end: authenticated GRN post (`procurement.py` → `procurement_service.post_grn`), production order complete (`production.py` → `production_service.complete_order`), and shipment dispatch (`sales.py` → `sales_service.dispatch_shipment`). Record each service's mutations, route commit point, exception rollback path, actor provenance, and downstream stock/movement/document effects.
2. Add a focused task-owned integration test module guarded to run only when both `M05_S03_T002_DISPOSABLE_TEST_DATABASE=1` and an exact `fmcg_m05_s03_t002_<hex>` database name match a passwordless PostgreSQL URL bound to loopback. Use only unique synthetic records. Never connect to or write a normal development, owner, staging, or production database.
3. On real PostgreSQL, prove one successful posting in each flow persists a coherent set of source-state, stock, and stock-movement effects in one transaction: accepted GRN quantity updates stock, GRN line movement linkage, PO received quantity/status; production material issue, consumption, finished-goods receipt, output stock, and completed order; shipment dispatch, stock deduction, shipment-line movement linkage, shipped quantity, and order/shipment status.
4. For each flow, force a failure after the service has staged its business mutations but before commit, roll back, and use a fresh session to prove every affected source row, stock balance, movement, consumption/receipt, and order/procurement progress value remains at its original persisted value. The test must detect an accidental commit inside the service.
5. Prove duplicate/repeated posting attempts for a posted GRN, completed production order, and dispatched shipment are rejected without creating duplicate movements/receipts/consumptions or changing balances. Arrange valid unrelated preconditions so the intended lifecycle guard is the observed cause.
6. Assert synthetic actor attribution where the models expose it. Verify no unintended finance journal/batch or unrelated module side effects are created by these operational transitions; explicitly retain GAP-002's documented absence of automatic GL posting as known scope, not as an implemented finance feature.
7. If evidence reveals a clear transaction-integrity defect in the selected flows, make only the smallest correction that preserves existing business policies and add a sensitive regression test. Do not redesign accounting, costing, inventory valuation, approvals, permission policy, or schema. Concurrency/race safeguards are the following task M05.S03.T003 and should not be absorbed here unless necessary to make a directly observed T002 invariant hold.
8. Run focused tests on a fresh empty task-owned PostgreSQL database migrated to the single current Alembic head. Record exact commands/results, failures/corrections, hashes, changed paths, transaction findings, containment/cleanup, and an independent read-only code review in `CODEX_LOG_V01.md`.
9. Do not claim physical factory, live credentials, production deployment, real-company acceptance, accounting integration, or GitHub Actions evidence.

## Stop conditions

If the selected flows cannot be exercised without owner data/credentials, an unapproved business-policy choice, a destructive schema change, or affecting a non-disposable database, stop only the dependent correction and explain the exact blocker in Turkish. Do not fabricate a passing result.
