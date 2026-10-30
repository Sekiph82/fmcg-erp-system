# M34.S01.T002 — Supplier invitation/bid workflow

## Scope and baseline

- Task: issue supplier invitations against the existing RFQ aggregate and capture controlled, attributed supplier quotations.
- Baseline: `609cca7dde06e51dce48ab5e8f03cda8c29add6b` (`HEAD` and `origin/main` matched at the task boundary; divergence `0 0`).
- Acceptance context: root `TASKS.md`, `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md`, and the supply-chain RFQ manual. The implementation extends existing RFQ/response and supplier models rather than adding another procurement architecture.
- Data: local disposable test suppliers and RFQs are synthetic. Existing supplier or owner data was not altered.

## Changes

- Added migration `20261030_0006` and RFQ response invitation/submission status, issue and submit timestamps, actor references, unique RFQ/supplier response enforcement, and finite positive price/nonnegative lead-time constraints.
- Added a permission/scoped invitation-issue endpoint. It requires a draft RFQ with active selected suppliers, records the internal issuing actor, and cannot be repeated implicitly.
- Bid entry is limited to an invited active supplier on an issued, open RFQ before its deadline. Submitted bids are immutable, attributed to the authenticated procurement user, and cannot be spoofed through generic status updates. Generic RFQ edits lock the row, issued terms are immutable, cancellation is constrained, and the existing single-supplier award patch now requires and records a submitted bid.
- Updated the existing RFQ UI to choose active suppliers, issue invitations, record bids only for invited suppliers, and distinguish invitations from submitted bids. The UI explicitly states that this local flow records invitations in ERP but does not send external email.
- Added task-guarded tests for payload validation, invitation lifecycle, deadline and supplier eligibility, duplicate/uninvited bids, bid attribution, award persistence, status-spoof prevention, repeat issuance, and RFQ row-lock concurrency.
- Added a task-scoped disposable PostgreSQL runner with unique passwordless loopback-only database/container names, migration round trip, focused regressions, and exact container cleanup verification.

## Verification evidence

- `coordination/sessions/M34.S01.T002/disposable-postgres-run-V05.log` and `disposable-postgres-command-output-V05.log`: fresh PostgreSQL task database; Alembic upgrade to head, downgrade one revision, re-upgrade; invitation/bid and GAP-009 suites **9 passed**; final revision `20261030_0006 (head)`; exact task container removal verified.
- No-database focused suite: `tests/test_m34_s01_t002_rfq_bids.py` — **2 passed, 1 skipped** (the PostgreSQL workflow test is database-guarded).
- Python compilation passed for changed backend API, model, schema, migration, and task test files.
- Frontend `npm run type-check` and targeted ESLint for the RFQ page and procurement client passed.
- `git diff --check` passed; `python -m alembic heads` reports the single head `20261030_0006`.
- Independent read-only review: no remaining actionable findings; confirmed invitation state, bid guards, lifecycle locks, award persistence, migration round trip, cleanup, and transparent no-email UI wording.

## Failed attempts and retained evidence

- V01/V02 are retained as failed attempts. V01 exposed an incorrectly quoted enum server default during migration. V02 exposed an ORM timestamp serialization issue (`MissingGreenlet`) in the invitation route; neither is passing evidence.
- V03 passed the initial bid-flow suite; subsequent independent review identified a lifecycle race, award persistence assertion, and timing-sensitive concurrency test. These were fixed, and V05 is the final evidence run with the concurrency handshake and award assertion.

## Limits

- This is local synthetic software acceptance, not live supplier, email delivery, legal, payment, or production acceptance.
- No message was sent to suppliers. No GitHub Actions were run or dispatched.
