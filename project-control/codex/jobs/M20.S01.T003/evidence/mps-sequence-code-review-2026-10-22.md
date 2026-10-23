# M20.S01.T003 — independent code review

Date: 2026-10-22
Reviewer: independent read-only reviewer

Reviewed MPS sequence allocation and migration/backfill plus plan-line write and scenario snapshot paths in `mps_service.py`, `mps_whatif_service.py`, `mps_capacity_service.py`, `mps_campaign_service.py`, `endpoints/mps.py`, and focused tests.

Findings resolved: plan, line, and scenario numbers use atomic PostgreSQL sequences with existing formats preserved. Migration initialization handles empty, zero, and positive suffixes and locks all three source tables; rollout requires old MPS and what-if writers quiesced until sequence-backed code is active. Regeneration, manual line update, approval/release, demand/material planning, capacity scheduling, campaign grouping, and what-if snapshot paths use consistent parent-plan-first locking before inspecting or mutating relevant lines. Zero-demand regeneration retains source run lineage, deletes only unlocked stale lines, and refreshes counters for locked rows. Manual updates reject non-DRAFT plans before line lookup; the endpoint translates the business rejection to HTTP 400 inside its transaction.

Independent review confirmed the identified concurrency and stale-state findings are resolved and reported no remaining correctness finding in the inspected scope. PostgreSQL migration/runtime evidence remains pending because the local Docker Desktop Linux engine is unavailable.

## Follow-up review

The follow-up reviewed the DRAFT-only guards for both capacity schedulers, material-feasibility evaluation, and legacy campaign grouping. It confirmed they run after the parent plan is locked and before line reads/writes, and the API maps the business errors to HTTP 400. A test-coverage gap for APPROVED-plan campaign rejection was identified and then closed: the added test checks both legacy and validated campaign runners, verifies rejection before line lookup, and asserts the plan query uses `FOR UPDATE`. No remaining finding was reported in the reviewed scope. PostgreSQL execution evidence remains pending.

## V05 F14–F15 follow-up review

The reviewer confirmed same-day downtime now leaves SHIFT_ADD hours uncredited with an explicit unknown reason; the helper test covers that case. For structural scenarios, the reviewer confirmed MERGE independently validates quantity/batch-count consistency and sums different valid counts, while SPLIT derives counts for each batch-aligned part. Candidate `required_hours` is cleared for split and merged lines to avoid persisting stale values. No remaining concrete F14/F15 correctness finding was reported. The F16 real browser/backend roundtrip remains unverified and is pending PostgreSQL availability.

The source-linked MPSWhatIfScenario row in the invariant matrix was updated to match those checks. Independent review confirmed the row is accurate and clarified that SHIFT_ADD validates existing calendar-window consistency and the daily cap but does not infer a specific added-shift interval.

The broader source-linked matrix was then checked against current implementation. Review confirmed MPS approval/release readiness, demand/supply projection, material feasibility, validated capacity diagnostics, and validated campaign behavior are distinguished from legacy direct-service behavior. The Recipe-backed production release requirement is explicitly retained as a gap for BOM-only feasible lines. One stale SalesOrder warehouse/UOM counterexample was qualified to legacy/direct unscoped calls; active advanced projection behavior is described accurately.

## V05 F16 browser-test safety follow-up

The read-only reviewer confirmed the roundtrip test should require the exact opt-in `M20_DISPOSABLE_TEST_DATABASE=1` before login or API requests, keep the hardcoded `M20-OPS-PLAN-` prefix, and skip with a clear explanation otherwise. The test persists scenario history and has no cleanup, so the configured target still must be task-owned and disposable; the environment flag is an accidental-run guard, not proof of database identity. No E2E execution was performed.

## PostgreSQL roundtrip middleware follow-up

The independent read-only reviewer examined the `InputSanitizerMiddleware` fix after a fresh disposable-PostgreSQL E2E reproduced `RuntimeError: No response returned` on scenario POST. Starlette's `BaseHTTPMiddleware` replays the cached request body from `_body`, then uses the original receive channel to await a real disconnect. Replacing `_body` with sanitized bytes preserves that contract; overriding `_receive` did not replace the cache and incorrectly injected a disconnect. The reviewer found no correctness concern in the targeted fix. The follow-up E2E passed (1 browser test) against the task-owned PostgreSQL database; see `mps-sequence-checks-2026-10-22.md` and the retained post-reload screenshot.
