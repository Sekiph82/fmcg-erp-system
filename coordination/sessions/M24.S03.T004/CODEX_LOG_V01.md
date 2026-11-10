# M24.S03.T004 implementation log

**Status:** IMPLEMENTED; pending consolidated M24 acceptance in S04.T004.  
**Task authority:** root `TASKS.md`, exact task `M24.S03.T004 — Packaging material consumption linkage`.  
**Acceptance material:** `coordination/milestones/M24/EXECUTION_PLAN_V01.md`, S03 batch scope, T004 assumptions, and the applicable material-flow posting audit/policy.  
**Starting Git state:** `HEAD` and `origin/main` were `0db8dc68c971661dbda55f6992f3b4e70e4da84d` at task start. Existing local changes were preserved; no reset, clean, stash, broad staging, commit, or push was performed.

## Implementation

- Added an authenticated packaging issue endpoint that posts `PKG_ISSUE` only from exact production reservation lines. The service validates each reserved material is typed as packaging, checks warehouse/order/reservation state and available quantity, and applies the existing stock, lot, actor, and idempotency controls.
- Kept generic transaction, issue, confirm, and reversal paths from bypassing the reservation-based packaging issue workflow. Return and scrap continue to reference the exact posted issue line and account for packaging issues.
- Allowed actual consumption events to reference posted packaging issue lines for the same in-progress order. Material type must match the issue type, and cumulative consumption, return, and scrap cannot exceed the exact issued line.
- Linked actual package consumption to the finished-goods trace event and lot at order completion. Tracked package lots receive a `packed_from` genealogy link; untracked packages retain issue-line and consumption-event trace lineage without inventing a lot.
- Prevented order completion from consuming a BOM packaging material a second time when that material already has a reserved packaging issue. Unissued packaging continues through the existing BOM completion path.
- Added UI for reservation-based packaging issues and actual package consumption. Consumption choices include only posted material issue lines. The idempotency key persists across failed retries and resets only when inputs change or the request succeeds.
- Added guarded disposable-PostgreSQL acceptance coverage for database-target safety, exact reservation/issue linkage, and quantity recording. These cases are authored but not run; the M24 plan batches comprehensive database/API/frontend/E2E validation at S04.T004.
- Recorded synthetic-only operating assumptions in the M24 execution plan; no real factory, staff, or material activity is claimed.

## Changed files for this task

- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/app/services/production_service.py`
- `backend/tests/test_m24_s03_t004_packaging_genealogy_db.py` (new)
- `frontend/src/app/dashboard/material-flow/issue/page.tsx`
- `frontend/src/lib/materialFlow.ts`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`

## Checks and review

- `python -m py_compile` for the changed backend modules and guarded acceptance file — passed.
- Ruff for the changed backend modules and guarded acceptance file — passed. The first broader invocation identified seven unused imports in `production_service.py`; those imports were removed and Ruff then passed.
- ESLint for the material-flow issue page and API client — passed.
- FastAPI OpenAPI generation — passed; the exact `/api/v1/material-flow/reservations/{res_id}/packaging-issue` route was present. Existing deprecation and duplicate-operation-ID warnings from other endpoints were emitted.
- `git diff --check` — passed with Windows LF-to-CRLF notices.
- One independent read-only review found a retry-idempotency issue in the UI. The key is now persisted across failed attempts and cleared when request inputs change or the request succeeds; posted-line filtering was added. Independent read-only re-review confirmed the finding was resolved and found no remaining critical issue. Reviewer did not edit files or run tests.
- No PostgreSQL/API integration/regression/frontend suite/E2E test was run, per the M24 consolidated validation plan. No approval, merge, commit, or push is claimed. Existing owner work in the dirty worktree was preserved.

## Queue state

At the task boundary, `--apply-answers` found no unanswered exact matches. The task queue marked M24.S03.T004 as `[v]` IMPLEMENTED pending milestone verification and selected M24.S04.T001 — Atomic stock/production transactions as its explicit dependency-ready successor. The tracker validator and queue check passed after the transition. Comprehensive M24 acceptance remains scheduled for S04.T004.