# M34.S02.T003 — Release/call-off orders

## Delivered

- Linked each blanket-agreement release purchase order to its source BPA and added a migration with schema adoption, ownership tracking, guarded downgrade, and preserved existing schema objects.
- Added scoped BPA release-order listing and creation. A release creates one DRAFT PO line from the BPA item, inherits supplier, company/branch/cost-center/department scope, currency, payment terms, and effective all-units price-break pricing. Existing PO approval and ordering remain required.
- Serialized commitment reservations by locking the BPA row. Reservations account for non-cancelled release POs and subtract received quantities; consumed quantity is tracked separately.
- Added release audit events, exact-one-item agreement validation, duplicate PO-number conflict handling, BPA/PO commercial-term protections, and price-break locking while a non-cancelled release is open.
- Added BPA release UI and API client support, with release history and the DRAFT/normal-approval behavior shown in the flow.

## Verification

- Disposable PostgreSQL V10: 3/3 focused tests passed; Alembic reached `20261030_0010`, downgraded to `20261030_0009`, returned to `20261030_0010`, and verified task-container cleanup. Full hashes and database evidence: [disposable-postgres-verification-V10.md](disposable-postgres-verification-V10.md).
- Python compilation passed for the changed backend modules and T003 test.
- Frontend `npm run type-check` passed; targeted ESLint passed for the BPA page and procurement API client.
- `git diff --check` passed for the task-scoped changes.
- Independent read-only review initially found two P2 issues (price-break mutation during an open release and a concurrent duplicate PO number). Both were fixed and the focused re-review reported no remaining findings. The final V10 run covers both cases.

## Test history note

V08 failed because the test expected HTTP 409 for a quantity that exceeded the agreement's remaining consumed commitment and the application correctly returned HTTP 422. V09 corrected that expectation and passed the original three-test scope. V10 is the final test evidence after the independent review fixes.
