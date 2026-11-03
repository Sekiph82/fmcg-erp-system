# M34.S02.T004 — Contract consumption tracking

## Delivered

- A BPA's `consumed_quantity` now increases atomically when linked goods receipts are posted, using accepted quantity only. Rejected units remain outside consumption and unreceived PO quantities remain reserved through the release-order calculation.
- BPA receipts must have finite, non-negative quantities; accepted plus rejected must equal received. Positive accepted quantities must reference a matching line and unit on the linked release PO, and cannot exceed the PO quantity or BPA commitment.
- Receipt posts lock the release PO and BPA rows, preventing lost consumption updates across concurrent receipts from separate POs under one agreement.
- Each consumption increment writes an audit event with before/after totals and the source GRN, PO, line IDs, accepted quantity, and unit.
- The existing BPA screen already displays consumed and remaining quantities, so this task required no additional UI or schema migration.

## Verification

- Disposable PostgreSQL V03: 2/2 task-focused tests passed on PostgreSQL 16 at Alembic head `20261030_0010`; verified cleanup. Details and hashes: [disposable-postgres-verification-V03.md](disposable-postgres-verification-V03.md).
- Python compilation passed for the changed audit/service modules and T004 test.
- Related M34.S02 T001-T003 regression suite: 6 passed, 3 skipped. The skipped tests are explicitly task-database-gated and are not counted as passes.
- `git diff --check` passed for task-scoped changes.
- Independent read-only review initially found quantity-split validation and missing cross-PO concurrency coverage. Both were added; the final review found no remaining findings and ran no tests.

## Iteration history

V01 failed due to a test fixture reading an expired ORM object after rollback. V02 passed the first corrected flow. V03 is the final run after adding finite/split validation and concurrent receipts against separate PO rows.
