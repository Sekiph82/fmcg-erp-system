# M22.S01.T002 — Harden state machine and transition guards

Date: 2026-11-04
Actor: CODEX

## Scope and implementation

Implemented the M22.S01.T001 responsibility decision without merging the canonical `ProductionOrder` / advanced `WorkOrder` tables with the active parallel `exec_production_orders` / `exec_work_orders` subsystem.

- Added explicit allowed-transition maps for each production-order state model and routed the existing guarded actions through them. The generic execution `advance` action now delegates release, start and close to their dedicated service guards, rejects completion without completion quantities, and only performs the safe DRAFT-to-PLANNED status-only edge.
- Canonical advanced work-order create, edit and delete now lock the parent first and are limited to a PLANNED parent and PLANNED child. Start and completion lock parent then child and require an IN_PROGRESS parent; lifecycle status, timestamps and actual quantity cannot be set through create/update payloads.
- Canonical production-order completion is rejected while any linked advanced work order is unfinished. Orders with no linked work orders retain their prior completion path.
- Applied the same parent-first locking and completion gate to the separate `exec_*` order/work-order family. The shop-floor service now uses the same lock order, requires an active parent for work-order actions, and checks predecessor completion before starting a dependent operation. Existing separate IDs and persistence remain intact.
- Added a guarded parent resume endpoint and matching API/detail-page control for the existing PAUSED state. Removed the list-page generic “Complete” action because completion requires quantities and must use its dedicated endpoint.
- Restricted work-order CSV import to planned operations under PLANNED parents, rejected lifecycle/status/actual fields, and rechecked the parent state while holding its row lock before inserting.

No schema migration, data rewrite, crosswalk, dual-write or live-factory/employee assumption was introduced.

## Review and verification

- Independent read-only review: no blocking findings. The review covered parent-first lock ordering, duplicate route paths, status payload/import bypasses, separation of the two model families and the resume control. No files were changed by the reviewer.
- `git diff --check`: passed (exit code 0).
- Automated tests were not run; no test result is claimed.

## Evidence limits

This records source-level transition guards and independent read-only review only. It does not claim runtime database acceptance, approval of lifecycle policy, production deployment, or live-factory behavior.
