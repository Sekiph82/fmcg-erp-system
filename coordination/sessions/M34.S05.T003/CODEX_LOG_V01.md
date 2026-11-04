# M34.S05.T003 — Three-way-match/finance integration tests

## Scope and acceptance basis

The root `TASKS.md` row is the only task-specific scope; no separate acceptance file is linked. The generated queue spec selected this exact task. The applicable `GAP-004_E2E_WORKFLOW_TESTING_AUDIT.md` identifies the missing representative procurement→stock→finance request chain through FastAPI and a test database. `GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md` calls out consistent PO→GRN→invoice match status, PO/GRN-linked landed-cost lifecycle, finance-ledger payment links, and protection of posted documents. Existing M34.S04 tests cover component/service behavior; this task adds the cross-module API/DB check.

## Change

- Added `backend/tests/test_m34_s05_t003_three_way_finance_workflow_db.py` and its task-owned PostgreSQL runner.
- Test data uses the established synthetic PO/GRN fixture; authenticated FastAPI routes post the GRN, run/re-run three-way matching, and post the supplier invoice to finance.
- Asserts the draft-receipt hold, absence of premature ledger posting, accepted GRN link and quantity, inventory movement, balanced GRNI/tax/AP journal, unique posting event, and idempotent API replay.
- Runner refuses non-loopback, passworded, wrong-name, or non-PostgreSQL targets; it binds the disposable PostgreSQL port to loopback and verifies container removal.

## Verification

See `verification-V01.md` and the V04 runner/cleanup logs. Initial runs informed corrections: a signed API user also needs the synthetic TOTP enrollment row; and finance posting correctly leaves the operational invoice lifecycle at `RECEIVED` while its ledger event is posted. Independent review had no blocking findings and recommended a direct assertion for the draft-GRN hold reason; that assertion is present in the final passing run. Ruff was unavailable in the project virtual environment, so this is explicitly not reported as passed.

## Independent review

Independent read-only review completed with no blocking/actionable findings.
