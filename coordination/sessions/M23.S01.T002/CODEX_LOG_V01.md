# M23.S01.T002 — Start/pause/resume/complete operation actions

## Acceptance basis

- Canonical task scope: root `TASKS.md`, `M23.S01.T002 — Start/pause/resume/complete operation actions`.
- Workflow context: `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md` and the M23.S01.T001 terminal hardening log.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` keeps the active `exec_*` execution aggregate distinct; this task does not infer or create a crosswalk to canonical `ProductionOrder`/`WorkOrder` rows or dual-write execution events.

## Existing lifecycle and change

- The shop-floor API already exposes start, pause, resume, and finish operations. The service locks the operation/parent context, requires the parent execution order to be in progress, validates operation state transitions, enforces predecessor completion before start, records transition/activity history, and commits the operation change with downstream readiness updates.
- Added server-side completion validation before any database access: good, scrap, and rework quantities, plus optional actual runtime, must be finite and non-negative. The terminal's finish action is already protected by operator entry, valid quantities, queue availability, pending-action locks, and clear completion feedback from T001.
- Added parameterized regression cases for negative and non-finite completion values. These cases are scheduled for the consolidated M23 verification run.

## Verification state

- `git diff --check` is the only executed check for this task; full and focused test suites are deferred to M23.S04 per the owner-requested milestone cadence.
- No live factory, real employee, or production-data result is represented. Start/pause/resume/finish remain synthetic virtual-workspace actions; role-specific authorization is scoped to M23.S01.T004.
