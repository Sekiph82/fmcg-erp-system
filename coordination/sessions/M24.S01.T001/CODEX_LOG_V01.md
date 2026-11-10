# M24.S01.T001 — Material reservation against released orders

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file exists; root `TASKS.md` is authoritative. M24 execution assumptions are recorded in `coordination/milestones/M24/EXECUTION_PLAN_V01.md`.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-003/004/010/012 and `coordination/AUDIT_POLICY.md` transactional integrity requirements; the M22 production-order responsibility decision in `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` identifies `ProductionOrder` as the order of record.

## Implementation

- Reservation creation now requires a released or in-progress canonical production order and its active source warehouse. It validates material identity, active status, UOM conversion, requested lot, stock balance arithmetic, lot expiry/quarantine, and released quality status.
- It locks stock rows in deterministic identity order, allocates only available quantity, and writes reservation lines with the exact allocated lot and quantity while updating `quantity_reserved` and `quantity_available` in the same transaction.
- Reservation create/read/cancel API routes require an authenticated user and warehouse-scoped inventory access. Cancellation releases only the unissued balance; cancelling a production order releases its outstanding reservations inside the order transaction.
- FEFO policy remains with M24.S01.T004; this implementation uses stable stock-row identity order until that task defines the lot recommendation behavior.
- Added a disposable-PostgreSQL-gated integration suite covering unreleased-order rejection, reservation/cancel balance arithmetic, and shortage atomicity. It has not yet been run.

## Checks performed

- `python -m py_compile` on the changed backend service, endpoint, lifecycle service, and new gated integration test: passed.
- Ruff on the new integration test: passed. A broader Ruff invocation reported existing findings across the legacy material-flow and production-service modules; inspection of the touched ranges and the new file found no new Ruff diagnostics.
- `git diff --check` on the changed backend files and task tracker: passed.
- No PostgreSQL, API, or E2E test was run for this task; comprehensive tests and independent reviews are batched for M24.S04.T004.

## Scope limits

No real stock, physical pick, factory execution, employee action, valuation posting, or live ERP acceptance is claimed. No migration was needed for the existing reservation schema.
