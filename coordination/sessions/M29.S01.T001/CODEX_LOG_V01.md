# M29.S01.T001 — Couple PM windows to production schedule

## Scope implemented

- Added an optional asset-to-production-work-center link with UUID validation and explicit unlink support.
- Added optional timezone-aware PM work-order window start/end fields. The API requires both timestamps together and the database check constraint requires a positive interval.
- Added an advisory, read-only schedule-impact endpoint. It compares half-open PM and production intervals only when an asset has an explicit work-center link and the PM window is present. It includes planned, confirmed, and in-progress production schedules and requires both `maintenance.view` and `production.view`.
- Added asset work-center selection, PM window entry, and visible overlap results to the maintenance UI. Overlaps do not change or block production schedules.
- Added Alembic migration `20261108_0019` after `20261108_0018`.

## Evidence

- Python syntax compilation passed for the changed backend model/schema/CRUD/endpoint and migration modules.
- Maintenance endpoint/schema import check passed.
- Focused ESLint passed for the two modified maintenance pages and maintenance API client.
- `git diff --check` passed for the scoped task files.
- Independent read-only review found no blocker. Its note about differing `scheduled_date` and PM window dates was resolved: report filtering now includes either an in-range scheduled date or a PM interval overlapping the requested UTC date interval. The reviewer confirmed the correction.
- Automated tests and migration execution were not run; they are deferred to the M29 verification sprint per the requested milestone-level test batching.

## Boundaries and risks

- Schedule overlap is advisory and read-only; it does not perform APS rescheduling, reserve capacity, or block production.
- Only explicit work-center mappings and explicit PM windows are compared. Missing mappings/windows are returned as unavailable instead of fabricating a match.
- The impact endpoint is access-controlled by both maintenance and production view permissions.
- Migration/runtime database acceptance remains pending M29.S04.
