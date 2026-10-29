# M25.S01.T003 — Customs/clearance milestone model

## Scope and assumptions

- Implemented an evidence-referenced status timeline using the clearance stages already listed in `docs/user-manual/module-manuals/logistics/03-arrivals-clearance.md`.
- The transition graph is explicit and sequential; a hold needs a reason, may resume at `UNDER_REVIEW`, and `CLEARED` is terminal.
- Each operator-entered milestone stores its source reference, system timestamp, actor, prior status, new status, and optional notes in an append-only record. These references are manually entered; there is no KRA connection, verified filing, or legal title assertion.
- Direct clearance status/date edits are rejected. Customs shipment states are changed through the milestone path, which also updates the existing arrival clearance date on `CLEARED`.
- GAP-009 flags uneven protection around import-shipment endpoints. The touched clearance read/create/edit/history routes now require the matching logistics permission. This task does not claim to resolve all GAP-009 access-scope gaps.
- Existing non-pending statuses are not backfilled as if they had verified milestone evidence. The UI identifies a current status that may predate history capture.

## Implementation

- Added `CustomsClearanceMilestone`, migration `20261029_0036`, append-only database triggers, retained actor/clearance foreign keys, and rollback safeguards that preserve history and existing baseline-owned immutability triggers.
- Added permissioned clearance milestone history and recording API; status changes lock the clearance and shipment rows and reload the exact inserted event by UUID.
- Updated the arrivals UI to show status history, record the next allowed milestone with source reference and optional/required hold reason, and keep the reference and notes in place if a save fails.
- Removed direct user editing of status-managed dates and status values. Added mocked UI coverage for successful recording and view-only access.

## Verification evidence

- Disposable PostgreSQL migration + API test passed: `1 passed` on each final V01, V02, and V03 run. The final V03 container/database were `codex-m25-s01-t003-9a1bb180f672492eb7c6` / `fmcg_m25_s01_t003_9a1bb180f672492eb7c6`; synthetic data only, PostgreSQL 16, loopback-only port, no volume, no password. The test covers permissions, invalid/skipped transitions, direct-edit bypasses, source/hold validation, actor attribution, ordered history, shipment synchronization, append-only protection, and deletion restrictions.
- Final mocked Playwright run on a task-owned Next dev server at port 3127: `2 passed` (timeline write and view-only screen). An initial run reused the pre-existing port-3000 dev server, whose stale page lacked the current accessible shipment label; rerunning against the current checkout on port 3127 passed.
- Frontend `npm run type-check`: passed.
- Targeted ESLint for the arrivals page, shipments page, logistics API client, and new E2E file: passed.
- Backend `compileall` and `git diff --check`: passed.
- Independent read-only review: no remaining blocker. The reviewer confirmed the row locking, permission gates, append-only actor/reference evidence, downgrade preservation, exact event response, and legacy-status wording.
- Cleanup check found no remaining task-labelled T003 Docker containers and no listener on the task-owned E2E port 3127.

## Limits

This is an internal workflow model with synthetic test data. It does not verify Kenyan tax rules, KRA decisions, actual customs documents, payment, or shipment ownership. Existing operational records require staff to enter a source reference and status; the system does not independently validate those claims.
