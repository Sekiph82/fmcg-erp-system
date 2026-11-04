# M34.S04.T004 — Finance posting/reconciliation

## Delivered

- Added idempotent, period-aware posting for PO-linked supplier invoices. Posting requires the saved three-way match and revalidates invoice and receipt snapshots, supplier/currency consistency, remaining accepted quantities, configured account mappings, and the open accounting period.
- Posts accepted receipt value to configured GRNI, recoverable tax to its configured asset account, approved price differences to the configured variance expense account, and the payable to AP. Missing or ambiguous accounting configuration fails closed.
- Added a scoped finance API action and a purchase-invoice UI action. PO-linked payments require the invoice's posted GL event.
- Locked invoices during payment creation and enforced scoped permission, payable lifecycle, finite positive amount, and outstanding-balance limits. Added an invoice-filtered posting-event query for the 300-row page so old invoices do not disappear behind a global 500-event cap.
- Corrected Optional Decimal constraints in blanket-agreement schemas using `Annotated`; the repository's installed Pydantic version rejected constraints attached to `Optional[Decimal]` at application import time.

## Verification

- Final disposable PostgreSQL 16.6 run: `coordination/sessions/M34.S04.T004/disposable-postgres-run-V12.log`; cleanup proof: `container-cleanup-V12.log`. A unique passwordless trust database was published only on loopback, migrated to Alembic head `20261104_0001`, and ran the task-guarded integration module: **9 passed**. The database and container were removed; the exact-name Docker listing was empty.
- Covered GRNI/tax/AP posting and idempotent replay, configured price variance, unpayable invoices, edits after matching, payment-before-post rejection, scope and lifecycle guards, excessive/concurrent payments, NaN rejection, and source-ID event filtering/bounds.
- Python compileall passed. Ruff passed for the new integration test and F821 on affected endpoint/service/schema modules. Targeted frontend ESLint and `tsc --noEmit` passed. `git diff --check` passed.
- Independent read-only review: no remaining actionable findings.
- The 12 reported deprecation warnings come from the existing three-way-match service's `datetime.utcnow()` calls; this task did not change that service.

No live company, supplier, invoice, posting rule, or production accounting data was used or modified.
