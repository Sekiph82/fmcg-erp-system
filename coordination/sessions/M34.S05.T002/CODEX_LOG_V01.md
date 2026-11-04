# M34.S05.T002 — CODEX Work Log

## Task

Supplier scorecard tests, as the exact current `TASKS.md` task.

## Work completed

- Added a task-specific PostgreSQL database integration test for the supplier dashboard's real FastAPI route and authenticated user dependency.
- Added synthetic PO/posted-GRN data for rolling OTIF; branch-scoped supplier evaluations for dimension averages; active, future, and archived ESG records; and linked QMS food-safety records for current, expired, and unknown-validity states.
- Verified that same-name QMS data linked to a different supplier ID is not joined, and that a branch-scoped viewer sees only accessible PO/evaluation metrics without supplier-wide ESG or food-safety details.
- Added a disposable runner with an exact task database guard, unique PostgreSQL 16.6 container/database, 127.0.0.1-only publication, migrations to head, environment cleanup, and container-removal verification.
- All inserted records are synthetic and cleaned up. No production service or schema was changed.

## Verification

See `verification-V01.md`, `disposable-postgres-run-V03.log`, and `container-cleanup-V03.log`.

## Review and boundaries

The independent read-only reviewer found no substantive findings. This verifies authenticated API scorecard behavior using signed test cookies; it does not verify the password login or 2FA challenge journey. The run is disposable implementation evidence, not production data or owner approval.
