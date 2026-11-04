# M22.S02.T003 — Partial completion/backorder semantics

## Scope and acceptance basis

- Canonical task: root `TASKS.md`, exact row `M22.S02.T003 — Partial completion/backorder semantics`.
- No task-specific prompt, acceptance matrix, or M22.S02.T003 audit was present in the repository. The implementation follows the task row, the M22 domain decision in `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`, and the M22.S02.T001/T002 contracts.
- The domain decision makes `ProductionOrder` the canonical order of record, requires partial quantities/batch identity/genealogy preservation and transactional parent/operation reconciliation, and explicitly keeps the active `exec_*` model family separate. No `exec_*` writes were added.
- `coordination/AUDIT_POLICY.md` and `coordination/AUDIT_INDEX.md` were reviewed. The latest general strict audit available is M20 V06; it is an M20 verdict, not M22 task acceptance. Its synthetic virtual-factory decision confirms that this software scope does not require real factory or employee data.

## Synchronization and preserved work

- Canonical Git root verified as `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Starting `HEAD` and fetched `origin/main`: `2bd812bcb4aab6f46fddf81ff7dfaaa830b6623c`; divergence was 0 ahead / 0 behind.
- The unrelated tracked owner change in `frontend/next-env.d.ts` and all unrelated untracked artifacts were left unstaged and unchanged. No dashboard or FormuLab files were used.

## Implementation

- Added database-backed quantity bounds for canonical production-order actuals/backordered quantity and work-order actuals. Migration `20261104_0006` preflights legacy quantity violations and stops rather than rewriting existing records; downgrade refuses to erase established backorder lineage.
- Canonical work-order completion now validates finite, positive quantities at the database precision, caps actual output at that operation's plan, records `COMPLETED_PARTIALLY` when appropriate, and preserves the actor-attributed immutable transition event.
- Parent completion validates the actual quantity against the original order plan and, when routed/manual work orders exist, requires it to equal the completed output from the final operation. Cancelled split/merge source operations do not prevent closure; active incomplete operations do.
- Completing below plan posts material consumption and finished goods only for the actual quantity, then creates a linked `PLANNED` child backorder for the exact remainder in the same database transaction. The child preserves product, recipe, plan-line, batch, UOM and warehouse context, receives a future schedule window, has no approval attribution, and therefore remains subject to existing approval/release gates. Parent and child transition events are written transactionally; repeat child creation is rejected.
- Production report, analytics, dashboard KPI and historical forecast denominators now use original planned quantity minus transferred backorder quantity. MRP/MPS open-order queries already exclude completed parents and include the new planned child, so their supply projection does not count the remainder twice.
- Added detail API/UI fields and links to navigate between source and child orders, plus a guarded disposable-PostgreSQL regression module. It covers quantity guardrails, final-operation reconciliation, partial inventory postings and linked planned backorder lineage.

## Independent source review

- An independent read-only reviewer found and reported a `daily_kpis()` scope error in the initial analytics change. The expression is now defined locally inside `daily_kpis()`; the reviewer rechecked the fix and the final scoped diff and reported no remaining concrete blocker.
- Reviewer did not edit files or run tests.

## Verification and limits

- `git diff --check`: passed for the scoped working diff; only Git line-ending notices were emitted.
- `python -m alembic heads`: migration `20261104_0006` is the sole head.
- PostgreSQL tests, migration upgrade/downgrade, frontend type-check/build, and runtime acceptance were not run in this task, per the requested milestone-batched test cadence. The regression test is added but has no execution receipt yet. No test PASS or deployed behavior is claimed.
- The backorder scheduling convention is a software assumption: schedule one source-duration window beginning at the later of the source scheduled end or current UTC time. It does not represent a real factory schedule.
