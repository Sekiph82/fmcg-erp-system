# M26.S02.T004 — Shift/team comparisons

## Status

Implemented; pending consolidated M26 milestone verification and acceptance.

## Change summary

- Added an authenticated, production-view-protected comparison endpoint and team-page date filters/tables for team and shift comparisons.
- Team assignment comes only from `team_id` recorded on labor/runtime logs. Shift assignment uses the latest recorded work-order assignment at or before the log start and requires matching recorded resource identifiers; missing, ambiguous, or mismatched evidence is shown as unassigned.
- Reports approved and unapproved labor counts, approved labor hours, runtime by recorded activity, completed work-order output allocated by approved lifetime labor minutes, and source IDs. Output with missing quantity/UOM/labor basis and open/invalid runtime intervals remain explicitly unavailable.
- No live employee, factory, or shift data was seeded; no OEE/utilization inference is made from overlapping runtime intervals.

## Focused evidence

- `python -m pytest tests/test_m26_s02_t004_shift_team_comparisons.py -q`: **1 passed**. The first run exposed an overly strict match for labor logs without a machine ID; the match now compares only identifiers present on both the log and its effective assignment, and still requires at least one matching recorded resource.
- `python -m compileall -q app/schemas/machine_operator.py app/services/machine_operator_service.py app/api/v1/endpoints/machine_operator.py`: passed.
- API route/service import check: passed.
- Focused ESLint on `src/app/dashboard/machine-ops/teams/page.tsx` and `src/lib/machineOperator.ts`: passed.
- `git diff --check`: passed (Git emitted existing line-ending normalization warnings for unrelated dirty files).

## Acceptance boundary

Milestone-level PostgreSQL, frontend type/lint, API/RBAC, regression/E2E validation, and consolidated independent code/security review remain pending. This task is not marked DONE.
