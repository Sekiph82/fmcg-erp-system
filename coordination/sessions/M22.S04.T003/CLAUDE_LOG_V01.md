# M22.S04.T003 — Cross-module transaction tests

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical scope: root `TASKS.md`, exact row `M22.S04.T003 — Cross-module transaction tests`.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` defines the canonical `ProductionOrder` as the link between planning, inventory, quality, and execution; the independent `exec_*` model family remains untouched.
- Applicable historical MPS and strict evidence: `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V06.md` and `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`; current M22 task-specific implementation evidence is recorded in the S03.T003 and S03.T004 logs. These are not a new M22 acceptance verdict. No M22.S04.T003-specific criteria/audit file was present.

## Implementation

- Added `backend/tests/test_m22_s04_t003_cross_module_transaction_db.py`, protected by an exact loopback, passwordless, task-named disposable PostgreSQL guard.
- The test follows a synthetic completed MRP run and approved MPS line into a linked ProductionOrder with source/target warehouse, schedule, and transition event; it then verifies idempotent MPS retry.
- It exercises the production release gate against a held raw-material lot at the exact recipe-plus-loss requirement. A blocked release must leave the ProductionOrder PLANNED, retain its prior approval and MPS link, preserve stock quantity, and preserve the committed MPS release audit. After the lot is explicitly released, retry must release the same order, append the actor-attributed transition, and leave stock unconsumed at the release boundary.
- All inputs are synthetic test fixtures. No live factory, employee, supplier, or owner data is used.

## Validation and review status

- The test module is syntax-checked with `python -m py_compile`; no PostgreSQL integration test was run during implementation.
- Comprehensive M22 tests, migration checks, and the consolidated independent source/security review remain pending for M22.S04.T004 acceptance. No test PASS, runtime acceptance, or independent verdict is claimed.

## Synchronization and preserved work

- Before claiming M22.S04.T003, local `HEAD` and `origin/main` were synchronized at `0db8dc68c971661dbda55f6992f3b4e70e4da84d` after the prior safe checkpoint push.
- The unrelated tracked owner edit `frontend/next-env.d.ts` and unrelated untracked files were not modified or staged.
- FormuLab and other checkouts were not modified.
