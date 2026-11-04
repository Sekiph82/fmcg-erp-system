# M22.S04.T001 — Lifecycle/state tests

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical scope: root `TASKS.md`, exact row `M22.S04.T001 — Lifecycle/state tests`.
- Domain authority: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` places lifecycle ownership on `ProductionOrder` and treats canonical `WorkOrder` rows as child operations. M22.S01.T003 and T004 implementation records define approval/release actor semantics and the append-only transition ledger.
- Relevant prior audit/governance: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and the latest MPS/production strict audit `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`. V06 is bounded historical M20 evidence, not an M22 acceptance verdict. No M22.S04.T001-specific prompt or audit matrix was present.
- Existing state coverage was inspected in `backend/tests/test_m08_s03_t001_transition_guards_db.py` and the M22.S02/S03 disposable-PostgreSQL task suites; this task adds direct M22 proof for current parent approval/release history.

## Implementation

- Added `backend/tests/test_m22_s04_t001_lifecycle_state_db.py`, protected by an exact loopback, passwordless, task-named disposable-database guard.
- The new database scenario rejects creator self-approval and repeated approval, approves and releases a planned canonical order, then verifies ordered transition actions, parent identity, actor ID/label and from/to states. PostgreSQL trigger checks reject both update and delete attempts against recorded transition events.
- Existing M08 transition-guard database cases and M22 task-specific suites remain part of the consolidated M22 acceptance campaign; this task did not duplicate or alter their earlier coverage.

## Validation and review status

- The integration test was syntax-checked with `python -m py_compile`; no PostgreSQL test was run during this implementation task.
- Comprehensive M22 database/regression validation and consolidated independent source/security review remain pending until milestone acceptance. No test PASS or runtime/database acceptance is claimed.

## Synchronization and preserved work

- Before claiming M22.S04.T001, fetched `origin/main`; local `HEAD` and `origin/main` both resolved to `cc6610ea123e1d7285f0e7d4f5678925e1f70ef5` (0/0 divergence).
- The unrelated tracked owner edit `frontend/next-env.d.ts` and unrelated untracked files were not modified or staged.
- FormuLab and other checkouts were not modified.
