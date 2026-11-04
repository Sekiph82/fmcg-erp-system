# M22.S03.T001 — Subcontract operation linkage

## Task basis

- Canonical task: root `TASKS.md`, `M22.S03.T001` (Required Actor: CODEX).
- The task row has no linked task prompt or task-specific acceptance/audit file. Applied the latest applicable M22 responsibility decision at `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`.
- That decision makes `ProductionOrder` the canonical business order and `WorkOrder` its operation child; it keeps `exec_*` as a separate active subsystem and requires execution facts to retain stable order/operation identity. No existing `exec_*` data is automatically cross-linked.

## Bounded implementation assumptions

- Add an optional, explicit FK from a subcontracting order header to one canonical WorkOrder. One order per work order keeps a single vendor receipt stream; partial deliveries remain supported by the subcontract receipt flow.
- New links are accepted only for a planned work order under a nonterminal production order. Product output lines, when present, must match the parent production product. Existing subcontract orders remain null/unlinked and are not backfilled by guessed IDs.
- Accepted product receipts for a linked operation are held as operation evidence rather than posted as a second finished-goods stock receipt. Completing the subcontract order requires accepted output; completing its WorkOrder must use exactly that accepted quantity. Parent close remains the single finished-goods stock posting point.

## Implementation

- Added nullable `SubcontractOrder.work_order_id` with RESTRICT FK/unique index and a downgrade preflight that refuses to discard existing links.
- Added create/read API schema exposure, locked parent/work-order validation in the service, and preloading for linked order reads.
- Added receipt and WorkOrder completion reconciliation so accepted linked output cannot be double-posted or disagree with the operation actual quantity.
- Receipt, subcontract completion, and WorkOrder completion lock the parent order, WorkOrder, and subcontract order in the same order before committing output/status changes.
- Added UI operation selection from planned canonical WorkOrders and link visibility in both order list and detail.
- Added a guarded disposable-PostgreSQL regression for linked and legacy-unlinked orders, deferred product-stock posting, and accepted-quantity matching.

## Verification status

- `git diff --check`: passed; `python -m alembic heads`: sole head `20261104_0008`.
- Tests, migration execution and frontend type/build checks were not run; they are batched for the M22 milestone verification per owner preference. No test PASS or data migration is claimed.
- Independent read-only review found and prompted fixes for duplicate finished-goods posting and concurrent receipt/completion races. Linked output now defers stock posting to parent close, requires exact accepted-receipt/WorkOrder quantity reconciliation, and uses a consistent parent→WorkOrder→subcontract-order row lock order. Follow-up review confirmed the stock and concurrency blockers are resolved; no tests/builds/migrations were run by the reviewer.
