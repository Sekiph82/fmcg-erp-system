# M23.S01.T003 — Operator/shift/machine context capture

## Acceptance basis

- Canonical task scope: root `TASKS.md`, `M23.S01.T003 — Operator/shift/machine context capture`.
- Existing workflow: `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md` and the M23.S01.T001 terminal log.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`; this implementation preserves the separate active `exec_*` execution model and does not invent crosswalks to canonical production-order records.

## Implemented

- The terminal can start an operator session with a typed virtual name or an existing active operator profile, plus optional line, configured work center, machine, and active shift selections. No employees, machines, shifts, or other owner data are seeded or fabricated.
- The active session is displayed in the terminal and its ID is retained in browser `sessionStorage`; a reload restores the session, while an ended/stale session is discarded. Session creation stays disabled until restoration finishes, and users can explicitly end the session.
- Shop-floor work-order activity snapshots operator/profile, team, machine, line, and shift from the referenced active session. Downtime records and their paired activity events take the same values from the session, ignoring conflicting client-supplied identity/context fields. New records reject missing or inactive session references; closing an existing downtime record preserves its original session snapshot.
- Added nullable session/shift context columns and `SET NULL` foreign keys for activity/downtime history, plus API/schema and frontend type support. The manufacturing manual explains that a typed virtual operator name is context, not proof of identity or authentication.

## Verification state

- `git diff --check` passed for changed tracked sources. An independent read-only review accepted the context snapshot rules, reload restoration, and migration/model alignment after follow-up corrections.
- Regression cases cover activity and downtime context consistency under conflicting client values and rejection of logged-out sessions. They are deferred to consolidated M23.S04 verification; no tests were run for this task.
- No live employee, factory, device, or production acceptance is claimed. Authentication and role-specific action permissions remain the scope of M23.S01.T004.
