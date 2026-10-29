# M08.S03.T001 — Harden state-transition invariants

**Status:** COMPLETE
**Actor:** CODEX
**Date:** 2026-10-29
**Canonical checkout:** `C:\Users\sekip\Desktop\fmcg-erp-system`

## Scope and references

Implemented the exact `M08.S03.T001` scope from the canonical task queue prompt: harden production-order and execution work-order state transitions. No task-specific acceptance artifact was linked from the task row, so the repository's applicable audit policy/index, M08/M05 planning audit material, and existing production services/tests were used to constrain the implementation. No business-policy decision or real factory data was needed; tests use synthetic records.

## Changes

- Restrict direct order and work-order edits to explicit editable-field allowlists; lifecycle state, quantities, and timestamps remain owned by transition services.
- Serialize lifecycle changes with fresh row locks. Lock production parent before work-order rows, and require production to be running before work steps can start or complete.
- Enforce work-step predecessor completion, same-order/earlier-step dependencies, and reject cycles even when an edit changes step order. Prevent work-order edits after production starts and prevent repeat terminal transitions.
- Validate split and merge inputs; reject repeated cancellation and unsupported terminal-state cancellation. Close and persist an active downtime interval when an in-progress production order is cancelled.
- Require authenticated production-execution API access, check scope permissions for reads and writes, and use the authenticated user's ID for audit ownership instead of generating a random ID.

## Verification evidence

- Fresh isolated PostgreSQL 16.6 Alpine container, bound only to a random `127.0.0.1` port, in-memory `tmpfs`, no persistent volume, passwordless local connection, task-specific synthetic database name.
- `alembic upgrade head` succeeded; `alembic heads` and `alembic current` both reported the single revision `20261029_0025`.
- Focused task suite: `20 passed` (`test_m08_s03_t001_transition_guards_db.py` and `test_m08_s03_t001_auth_guard.py`).
- Additional local regression suite: `18 passed, 15 skipped` (the database-guarded cases were skipped without the task database environment).
- `py_compile` for the three changed Python modules and both task test files succeeded; `git diff --check` succeeded.
- The disposable PostgreSQL container was removed after the run and verified absent. No password was created or shared.
- Independent read-only review checked lock ordering, the GET versus transition-lock behavior, and the sequence-change cycle regression. No concrete issue was reported; the reviewer did not run tests or edit files.

## Limitations

- This evidence covers the targeted transition and authentication regressions, not the full repository suite or production deployment.
- No GitHub Actions were dispatched. No live production database or real factory data was used.
