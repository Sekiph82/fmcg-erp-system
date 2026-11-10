# M26.S01.T004 — CODEX implementation log

## Implemented

- Enabled the existing `cert_override_flag` only for actors with `production.approve` or matching scoped approval permission and resource scope.
- Required a non-empty reason (trimmed and limited to 500 characters). A reason is rejected when the override flag is absent.
- Overrides apply only when qualification/certification checks block the assignment. Work-order, machine availability, and other non-qualification blockers remain non-overridable.
- Persisted the assignment with `cert_validation_passed=false`, override flag/reason, and assigning actor. Added an `AssignmentHistory` entry and a `SupervisorReview` (`CERT_OVERRIDE`) with reviewer actor and reason in the same database transaction.
- Added focused tests for approved override lineage, global approval permission, non-qualification blockers, required reason, reason/flag consistency, and scoped approver resource isolation.

## Checks performed

- Focused pytest: 6 passed. (Pydantic emitted existing class-based Config deprecation warnings.)
- Targeted Python compileall: passed.
- Focused Ruff `F821` check on touched M26 Python files: passed.
- `git diff --check` on touched M26 paths: passed.
- Independent read-only review: completed; scoped approver and whitespace-only reason findings were corrected, then reviewer found no remaining blocker.

## Pending

Fresh PostgreSQL migration, full M26 regression, frontend, E2E, and milestone-level security acceptance remain pending at M26.S03.T004.
