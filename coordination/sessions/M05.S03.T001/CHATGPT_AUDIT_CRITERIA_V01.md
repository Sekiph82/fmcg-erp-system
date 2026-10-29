# M05.S03.T001 — Reservation and Allocation Integrity V01

## Authority and audit basis

The exact selected task is `M05.S03.T001 — Validate reservation/allocation consistency` from root `TASKS.md`. Scope is validation of existing synthetic ERP behavior and only narrow corrective changes proven necessary by a failing invariant. No real factory, staff, customer, or stock records are assumed.

Latest applicable source audits and rules read before starting:

- `coordination/AUDIT_INDEX.md`: ERP-AL-003/004/011/012 require real authorization, enforced transitions, negative tests whose intended guard is the failure cause, and explicit upstream/downstream side-effect checks.
- `coordination/AUDIT_POLICY.md`: inventory reservations/movements are critical; transaction, rollback, idempotency, concurrency, and cross-module side effects need direct coverage.
- `docs/planning/GAP-010_CRM_SALES_PIPELINE_AUDIT.md`: sales orders have allocation, reservation release and shipment/dispatch flows; sales service includes these lifecycles.
- `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md`: `Stock.quantity_reserved` exists but reservation ownership/workflow linkage is limited; do not invent a new WMS architecture.
- `docs/migration/legacy-task-trackers/fmcg-erp-system-pre-M21.md`: stock-row locks protect against double allocation and must not be removed without a concurrency test.
- Current source: `backend/app/services/sales_service.py`; stock/order models under `backend/app/models/`.

## Acceptance criteria

1. Trace the live sales allocation, cancellation/release and dispatch code paths, transaction boundary, and tests before edits. Identify which fields are derived and which service owns each transition.
2. Use only unique, synthetic task data in an isolated disposable PostgreSQL database for behavior and concurrency evidence. Do not touch a normal development, owner, staging, or production DB; do not use real records or credentials.
3. Verify stock arithmetic (`available = on_hand - reserved`, no negative values), allocated quantity vs reservation deltas, and conservation across multiple stock rows and two synthetic sales orders competing for one SKU/warehouse.
4. Verify insufficient-stock behavior leaves persisted stock, order, and allocation state unchanged, with the intended insufficiency guard as the actual failure cause.
5. Verify cancellation releases only the cancelled order's reservation, preserves another order's reservation, and illegal/repeated lifecycle transitions do not release or allocate twice.
6. Verify shipment dispatch decreases on-hand and the corresponding reserved amount exactly once, creates the expected stock movement, and preserves remaining availability/reservations. Check for unintended finance/journal side effects where no posting transition is invoked.
7. Exercise true concurrent PostgreSQL transactions for competing allocations; demonstrate that final reservation does not exceed on-hand and order allocations match persisted reservations. Include same-order concurrency if current API/service paths allow concurrent invocation; record any unresolved race precisely.
8. If a test proves a defect, repair only the narrow, unambiguous data-integrity defect and add an adversarial regression test. Do not redesign reservation ownership/schema or change business allocation policy without an owner decision.
9. Record exact hashes, baseline/commit, database containment, commands and results, failures/corrections, changed paths, transaction and side-effect conclusions, cleanup, and an independent read-only review in `CODEX_LOG_V01.md`.
10. Keep external operations, production readiness, and real-company acceptance out of scope. All scenario data and actors are explicitly synthetic.

## Stop conditions

Stop only the dependent correction if a required reservation-policy choice, destructive schema change, production credential, or real operational fact is needed. Record the concrete blocker and continue no unrelated scope inside this task.