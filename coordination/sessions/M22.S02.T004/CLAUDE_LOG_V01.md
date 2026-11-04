# M22.S02.T004 — Rework/reprocess flows

## Task basis

- Canonical task: root `TASKS.md`, `M22.S02.T004` (Required Actor: CODEX).
- The task row contains no separate prompt or acceptance link. No M22.S02.T004-specific audit was present when this task was inspected.
- Applied the M22 responsibility decision in `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`: canonical `WorkOrder` remains a child operation of `ProductionOrder`; the separate `exec_*` subsystem remains active and untouched; execution facts retain actor and genealogy lineage.
- Assumption: rework is a quantity-preserving repair of output from an already completed operation, under its still-open, approved parent order. Rework is restricted to the terminal routed operation, or one unambiguous manual operation group, until explicit downstream reprocessing/dependency semantics exist. A completed parent order remains immutable. The rework result returns through the same parent and batch context; it does not independently post finished goods.

## Implementation

- Added canonical WorkOrder rework quantity, source link and reason, database constraints, genealogy action and migration `20261104_0007`.
- Added an authenticated API that requires both edit and create permission, an approved `IN_PROGRESS` parent, a completed source operation, a positive milliquantity within the remaining unreworked actual quantity, and a specific reason. Parent/source rows are locked before quantity allocation.
- Created a planned result operation under the same parent, routing/work center/operator and batch context; recorded actor-attributed transitions and immutable `REWORK` genealogy.
- Reconciled parent output as source actual quantity less assigned rework plus completed rework output, avoiding duplicate finished-goods quantity. Parent close remains blocked while any active rework operation is incomplete.
- Added UI/API-client support and eligibility messaging. The UI hides unsupported mixed routed/manual cases; backend checks remain authoritative.
- Added guarded disposable-PostgreSQL coverage for exact DB isolation, quantity conservation, incomplete rework closure, terminal-operation eligibility, mixed route/manual rejection, excessive rework and immutable completed parents.
- No `exec_*` files or live factory/employee data were changed.

## Verification status

- `git diff --check`: passed.
- `python -m alembic heads`: the sole migration head is `20261104_0007`.
- Independent read-only review found no blockers in quantity accounting, locking, authorization, model/migration alignment, or the added routed/manual regression case. The reviewer ran no tests, builds or migrations.
- Functional tests, migration execution and frontend type/build checks were not run. Per owner preference, they are batched for the M22 milestone verification rather than run for every task. No test PASS or database acceptance is claimed.
