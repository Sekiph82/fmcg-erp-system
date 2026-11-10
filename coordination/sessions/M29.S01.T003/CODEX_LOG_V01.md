# M29.S01.T003 — Maintenance priority/escalation rules

## Scope implemented

- Added a versioned, read-only breakdown priority assessment using existing recorded severity: CRITICAL/P1, HIGH/P2, MEDIUM/P3, LOW/P4.
- Added transparent virtual-demo review thresholds: critical immediately, high after 4 hours, medium after 24 hours, and low after 72 hours while still open or in repair.
- The assessment uses the recorded breakdown start time and one UTC report snapshot. Missing, naive, or inconsistent timestamps are flagged instead of being treated as valid elapsed time.
- Added a permission-gated report endpoint and exposed priority/escalation state in the maintenance breakdown UI.
- No alert, assignment, notification, staffing assumption, or write is performed.

## Evidence

- Python syntax compilation and maintenance service/endpoint import check passed.
- Focused ESLint passed for the modified breakdown page and maintenance API client.
- `git diff --check` passed for the scoped files.
- Independent read-only review found no blocker. It confirmed the virtual thresholds are clearly labeled as illustrative rather than approved site SLAs. The reviewer noted that the defaults are fixed in code rather than admin-configurable; this is documented and follows the owner’s instruction to use realistic virtual assumptions.
- Automated tests were not run; M29 regression and database tests remain batched for M29.S04.

## Boundaries

- Policy version: `virtual-demo-v1`.
- Review state is recalculated when requested; it is not persisted as a separate escalation event.
- The endpoint requires `maintenance.view` and sends no external action.
- No real plant response-time policy or operator assignment is claimed.
