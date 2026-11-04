# M22.S04.T002 — Split/merge/rework tests

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical scope: root `TASKS.md`, exact row `M22.S04.T002 — Split/merge/rework tests`.
- Domain authority: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` preserves canonical parent/operation ownership and the separate `exec_*` boundary. Relevant implementation evidence is in `coordination/sessions/M22.S02.T002/CLAUDE_LOG_V01.md` and `coordination/sessions/M22.S02.T004/CLAUDE_LOG_V01.md`.
- Latest applicable audit/governance reviewed: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`. V06 is historical bounded evidence, not an M22 verdict. No M22.S04.T002-specific audit matrix or prompt was present.

## Coverage mapped to current M22 implementation

- `backend/tests/test_m22_s02_t002_work_order_split_merge_db.py` is guarded to an exact task-named, loopback, passwordless disposable PostgreSQL database. It rejects unbalanced split quantity without changing the source, verifies split/merge conservation and terminal source statuses, checks per-source merge genealogy and total transferred quantity, and confirms genealogy rows reject mutation.
- `backend/tests/test_m22_s02_t004_work_order_rework_db.py` has the same database isolation pattern. It covers mixed routed/manual and nonterminal rework rejection, quantity-limited rework creation under the same parent/operation, actor-attributed rework lineage and transition events, parent-close blocking until the rework operation completes, reconciled parent output, over-allocation rejection, and completed-parent immutability.
- These task-specific PostgreSQL suites already provide the requested regression coverage; this task adds a versioned coverage map rather than duplicating fixtures or broadening implementation scope.

## Validation and review status

- `python -m py_compile backend/tests/test_m22_s02_t002_work_order_split_merge_db.py backend/tests/test_m22_s02_t004_work_order_rework_db.py` passed.
- The PostgreSQL integration cases and comprehensive M22 regressions were not run here; they remain in the consolidated M22 milestone validation campaign. No database/test PASS or runtime acceptance is claimed.
- Consolidated independent source/security review remains pending until milestone acceptance.

## Synchronization and preserved work

- Before claiming M22.S04.T002, fetched `origin/main`; local `HEAD` and `origin/main` both resolved to `cc6610ea123e1d7285f0e7d4f5678925e1f70ef5` (0/0 divergence).
- The unrelated tracked owner edit `frontend/next-env.d.ts` and unrelated untracked files were not modified or staged.
- FormuLab and other checkouts were not modified.
