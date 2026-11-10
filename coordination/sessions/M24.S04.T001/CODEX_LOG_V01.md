# M24.S04.T001 implementation log

**Status:** IMPLEMENTED; pending consolidated M24 acceptance in S04.T004.  
**Task authority:** root `TASKS.md`, exact task `M24.S04.T001 — Atomic stock/production transactions`.  
**Acceptance material:** `coordination/milestones/M24/EXECUTION_PLAN_V01.md`, S04 integrity/closure scope, plus `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md` and `coordination/AUDIT_POLICY.md`. No task-specific acceptance matrix or audit was present.  
**Starting Git state:** fetched `origin/main`; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d` (0/0 divergence). The working tree already contained owner and earlier task changes; they were preserved without reset, clean, stash, broad staging, commit, or push.

## Implementation

- Audited the M24 material issue transaction boundary. `issue_reserved_materials` writes and flushes the posted flow/lines, stock balance changes, reservation line/status and movements without committing. The authenticated endpoint commits the whole unit on success and rolls it back on exceptions. The existing production completion path similarly performs WIP receipt, finished-goods stock/lot, genealogy and quality writes in the session before the API commits.
- No runtime change was needed for this task after the transaction-boundary audit. Added a disposable-PostgreSQL rollback acceptance case for a reservation-based material issue. It verifies that a rollback restores on-hand/reserved/available stock and ACTIVE reservation state, resets issued quantity, and removes the posted issue and stock movement together.
- The new test is guarded to write only when the explicit M24.S04.T001 flag and exact loopback PostgreSQL database name are supplied, and rejects passwords, non-loopback hosts, other database names, and SQLite.

## Changed files for this task

- `backend/tests/test_m24_s04_t001_atomic_posting_db.py` (new)
- `coordination/sessions/M24.S04.T001/CODEX_LOG_V01.md` (new)

## Checks and review

- `python -m py_compile` for the new database acceptance file and related services — passed.
- Ruff for the new acceptance file and related services — passed.
- `git diff --check` — passed with existing Windows LF-to-CRLF notices.
- One independent read-only reviewer confirmed the unit-of-work transaction boundary and the exact loopback/passwordless database guard. The reviewer suggested also asserting the reservation status after rollback; that assertion was added and independently rechecked. Reviewer did not edit files or run tests.
- No database test was run, consistent with the M24 plan's consolidated validation at S04.T004. This is implementation evidence only, not database acceptance. No approval, merge, commit, or push is claimed.

## Queue state

At the task boundary, `--apply-answers` found no unanswered exact matches. The queue marked M24.S04.T001 as `[v]` IMPLEMENTED pending consolidated verification and selected M24.S04.T002 — Genealogy event creation as its explicit dependency-ready successor. The tracker validator and queue check passed after the transition. The remaining M24 test, migration, API, frontend and E2E validation stays at S04.T004.