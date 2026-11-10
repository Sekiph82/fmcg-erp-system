# M24.S04.T002 implementation log

**Status:** IMPLEMENTED; pending consolidated M24 acceptance in S04.T004.  
**Task authority:** root `TASKS.md`, exact task `M24.S04.T002 — Genealogy event creation`.  
**Acceptance material:** `coordination/milestones/M24/EXECUTION_PLAN_V01.md`, S04 genealogy assumptions, `docs/planning/GAP-020_CONSUMER_COMPLAINT_RECALL_AUDIT.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, and the repository audit policy. No task-specific acceptance matrix or audit was present.  
**Starting Git state:** fetched `origin/main`; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d` (0/0 divergence). Existing local changes were preserved; no reset, clean, stash, broad staging, commit, or push was performed.

## Implementation

- Production completion now loads exact posted reservation-based `RAW_ISSUE` and `PKG_ISSUE` lines for the order and their actual `ProductionConsumption` events.
- Finished-goods transformation genealogy uses actual consumed quantities and references the exact issue line and consumption event. Raw tracked lots create `intermediate_from` edges; packaging tracked lots create `packed_from` edges. Trace lines preserve the issue source location and material lot identity. Untracked inputs stay in the trace event without fabricated lot links.
- Production completion does not run the legacy BOM stock issue again for any material already issued by the M24 reservation workflow. Legacy BOM consumption remains for materials with no such issue history.
- Independent review found that partial reservations could leave unused stock marked reserved after production completion. Completion now releases only unissued reservation balances in the same transaction as WIP/finished-goods/genealogy/order completion. On-hand stock does not change during release. Failures remain within the same rollback boundary. This closes the orphan-reservation case uncovered while validating the task scenario.
- Added a guarded disposable-PostgreSQL case for exact raw issue-to-consumption-to-finished-lot genealogy, no duplicate BOM stock issue, and reservation balance release. It is authored but not run; the M24 plan defers comprehensive integration tests to S04.T004.
- Updated the M24 execution assumptions with these synthetic-only lineage and reservation-close rules. No real production, factory, staff, or material activity is claimed.

## Changed files for this task

- `backend/app/services/production_service.py`
- `backend/tests/test_m24_s04_t002_genealogy_db.py` (new)
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `coordination/sessions/M24.S04.T002/CODEX_LOG_V01.md` (new)

## Checks and review

- `python -m py_compile` for the changed production service and guarded database acceptance file — passed.
- Ruff for those files — passed.
- FastAPI OpenAPI generation confirmed the production completion route remains present; existing warnings from other endpoints were emitted.
- `git diff --check` — passed with existing Windows LF-to-CRLF notices.
- One independent read-only review first identified the partial-reservation leak. The implementation was updated and re-reviewed: completion already held the order lock, then releases active/partially-issued reservation balances and locks stock in deterministic order; only unused reserved quantity is returned to available, with no on-hand change. Updated scenario assertions match this behavior. No remaining critical finding. Reviewer did not edit files or run tests.
- No database/API/frontend/E2E suites were run, following the M24 consolidated-validation plan. No approval, merge, commit, or push is claimed.

## Queue state

At the task boundary, `--apply-answers` found no unanswered exact matches. The queue marked M24.S04.T002 as `[v]` IMPLEMENTED pending consolidated verification and selected M24.S04.T003 — Reversal/correction controls as its explicit dependency-ready successor. The tracker validator and queue check passed after the transition. M24 integration, security, migration, frontend and E2E acceptance remains at S04.T004.