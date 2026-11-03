# M34.S04.T001 — implementation log

## Scope

Hardened the existing PO/receipt/invoice match path and its review boundary. This task does not add accounting postings or change the approved tolerance policy.

## Changes

- Enforced authenticated finance permissions across invoice-match reads, matching, review, duplicate resolution, AI actions, and tolerance configuration. Review decisions take the actor from the authenticated account; the client can no longer author the reviewer identity.
- Made tolerance-rule reads reachable by placing the dynamic match-ID route after the static route.
- Serialized matching and review against invoice, PO, and match-header rows; rejected stale review versions and force reruns of reviewed/approved matches.
- Hardened matching against cancelled POs, currency and UOM mismatches, ambiguous PO-line selection, zero invoice quantity, and concurrent invoices that would overbill accepted receipt quantity. Kept the configured tolerance values and conversion policy unchanged.
- Corrected tax variance classification so a nonzero in-tolerance variance is not described as an exact match. Explicitly delete GRN-link children before replacing match lines on rerun.
- Added focused permission/status tests and disposable PostgreSQL concurrency, rerun, stale-review, and matching-invariant regressions.

## Verification

- `python -m pytest tests/test_m34_s04_t001_invoice_match_hardening.py -q`: **7 passed**, including view-only denial for review and tolerance configuration.
- Fresh task-owned PostgreSQL 16.6 database; Alembic upgraded to `20261104_0001 (head)`; `python -m pytest tests/test_m34_s04_t001_invoice_match_db.py -q`: **5 passed**. Disposable container cleanup verified. See `disposable-postgres-V05.log`, `pytest-postgres-V05.log`, and `alembic-upgrade-V05.log`.
- `python -m py_compile` for the changed backend endpoint, service, schema, and both task test files: passed.
- Ruff on the changed endpoint, schema, and both task test files: passed. Ruff on the whole service reports 15 issues also present in `HEAD` before this task; none were introduced by this diff.
- Frontend `npm run type-check` and targeted ESLint for the changed invoice-match files: passed.
- `git diff --check`: passed before evidence files were added; rerun before publication.
- Independent read-only review of the final expected-run-version flow: no remaining findings.

## Evidence limits

All database cases use generated synthetic records in the disposable task database. The implementation does not claim AP/GL posting, production-data validation, or a real human approval workflow.
