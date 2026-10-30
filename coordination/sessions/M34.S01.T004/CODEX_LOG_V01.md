# M34.S01.T004 — Award/split-award approval

## Scope and decisions

- Reused the existing RFQ, supplier-response, and configurable `ProcurementApprovalRule` records; did not invent approval thresholds or approver identities.
- Award proposals require at least one matching active RFQ approval rule and fail closed when the configured rules do not resolve to eligible approvers.
- Split awards allocate the complete requested quantity by RFQ line (or the single legacy RFQ quantity), compute totals from submitted line quotes, and preserve the selected currency.
- Existing baseline migrations create ORM metadata before the incremental Alembic chain. The new migration therefore validates and adopts exact compatible award tables, and rejects incompatible schema shapes rather than assuming the tables are absent.

## Changes

- Added itemized RFQ bid quotes, award proposals and line/supplier allocations, decision snapshots, configured multi-level approval, rejection history, and terminal bid states.
- Blocked direct RFQ status changes to `AWARDED`; only final approval can award an RFQ. A finalized split award leaves the header supplier unset, marks allocated submitted bids `AWARDED`, and other submitted bids `REJECTED`.
- Scoped approval actions in the UI to the assigned user and the currently active approval level. The API independently enforces assignment, scope, and sequence.
- Added a task-owned, passwordless loopback PostgreSQL runner. It generates a unique disposable database/container name, sets `M34_S01_T004_DISPOSABLE_TEST_DATABASE=1`, and removes the container in `finally`.

## Verification

- `run_disposable_postgres.ps1 -RunVersion V03`: PostgreSQL 16 disposable container; full Alembic upgrade to `20261030_0008`, downgrade/re-upgrade, incompatible weak-check rejection, restoration/re-upgrade, then focused T004/T002/T003 tests. Result: **8 passed, 2 skipped**. The two skips are retained as skips; no pass is claimed for them.
- V03 confirmed `20261030_0008 (head)` after the test suite and `TASK_CONTAINER_CLEANUP=verified_absent` for the unique task container.
- `python -m compileall -q app tests/test_m34_s01_t004_rfq_award_approval.py tests/test_m34_s01_t002_rfq_bids.py`: passed.
- `npm run type-check`: passed.
- `npx eslint src/app/dashboard/procurement/rfq/page.tsx src/lib/procurement.ts`: passed.
- Independent read-only review: three findings were fixed (unallocated bids remain submitted, unassigned approvers saw actions, and later approval levels showed actions early). Follow-up review found no remaining findings; reviewer did not execute tests.
- The first disposable runner attempt exposed the baseline `Base.metadata.create_all` behavior and failed its incorrect “table absent” assumption. The runner was corrected to test incompatible schema adoption; V03 then passed the complete flow above.

## Evidence files

- `disposable-postgres-run-V01.log` and `disposable-postgres-command-output-V01.log` — initial runner discovery/failure.
- `disposable-postgres-run-V02.log` and `disposable-postgres-command-output-V02.log` — first corrected migration adoption and test run.
- `disposable-postgres-run-V03.log` and `disposable-postgres-command-output-V03.log` — final verification and cleanup.
