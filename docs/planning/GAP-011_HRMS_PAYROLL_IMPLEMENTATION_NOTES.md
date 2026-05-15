# GAP-011 HRMS / Payroll Implementation Notes

Status: GAP-011K documentation in progress
Phase: Phase 3 - High-importance operational modules
Business priority: High
Technical area: HR / Payroll

## Summary

GAP-011 reconciles the existing HRMS and payroll surfaces without replacing the current architecture. The repository already had core HR, Kenya payroll, timesheets, ESS, recruitment, appraisals, training, and expenses. This implementation slice keeps those modules intact and hardens the foundations that were inconsistent: schema ownership, canonical employee references, payroll privacy, permissions, scopes, workflow locks, and frontend visibility.

The current canonical employee master remains `hr_employees`. Kenya statutory payroll remains the canonical localized payroll surface under `/api/v1/payroll-ke`. The older HR payroll period/line surface remains for compatibility and lightweight operational summaries.

## Canonical HR / Payroll Architecture

- Core employee master: `backend/app/models/hr.py` via `Employee`.
- Kenya payroll profile/run/line/payslip: `backend/app/models/payroll_ke.py`.
- Timesheets bridge to HR employees: `backend/app/models/timesheets.py`.
- ESS account/profile bridge to central users and HR employees: `backend/app/models/ess.py`.
- Central HR/payroll access behavior: `backend/app/services/hr_payroll_access_service.py`.
- Frontend HR client: `frontend/src/lib/hr.ts`.
- Frontend Kenya payroll client: `frontend/src/lib/payrollKe.ts`.

## Kenya Payroll Surface

Kenya payroll remains separate from generic HR. The backend route is `/api/v1/payroll-ke`, and the frontend route group is `/dashboard/payroll`.

The Kenya payroll frontend pages are now guarded by `payroll_ke.view`:

- `/dashboard/payroll`
- `/dashboard/payroll/profiles`
- `/dashboard/payroll/reports`
- `/dashboard/payroll/runs/[id]`

Payroll mutation controls are permission-aware:

- payroll run creation and statutory rate seeding require `payroll_ke.create`
- payroll profile creation/edit affordances require `payroll_ke.create`
- payroll run calculation requires `payroll_ke.create`
- payroll approval requires `payroll_ke.approve`
- statutory report CSV export requires `payroll_ke.export`

## Permissions and Scopes

The backend module registry now owns both HR and Kenya payroll:

- `hr`: `view`, `create`, `edit`, `approve`, `export`
- `payroll_ke`: `view`, `create`, `approve`, `export`

The route paths are unchanged. `hr` and `payroll_ke` were moved out of loose endpoint-route ownership and into `MODULE_DEFINITIONS`, so manifest, route registration, and permission contract checks have a clearer source.

Scoped HR/payroll helpers support:

- company scope
- branch scope
- department scope
- cost center scope
- employee self-ownership checks

Generic HR visibility does not imply Kenya payroll visibility. `hr.view` alone must not expose statutory payroll pages or payroll API data.

## Admin / Role / Seed Setup

Seed permissions already define the generic HR and Kenya payroll permission families. GAP-011 verified those contracts and kept Kenya payroll explicit:

- `hr_manager` has HR permissions and explicit `payroll_ke.*` grants.
- `scoped_hr_manager` keeps scoped HR and generic scoped payroll authority, but does not receive broad `payroll_ke.create` or `payroll_ke.approve`.
- payroll-specific access remains opt-in rather than inherited from all HR roles.

The registry/seed contract is covered by `backend/tests/test_gap011_hrms_payroll_access.py`.

## Migration and Schema Changes

Migration file:

- `backend/alembic/versions/20260515_0020_hrms_payroll_reconciliation.py`

The migration is additive and reconciliation-oriented. It adds missing scope and bridge fields without dropping existing payroll or HR surfaces.

Main schema additions include:

- employee company, branch, department, cost center, manager, lifecycle, and archive fields
- HR shift, attendance, leave, payroll period, and payroll line scope fields
- Kenya payroll profile/run/line/payslip scope fields
- payroll run lock metadata
- payslip viewed/sent metadata
- statutory effective dates
- timesheet canonical HR employee, manager, payroll run, and finalization fields
- ESS central user and HR employee bridge fields

Live DB migration was not run in this session because Docker was unavailable when GAP-011C was executed. Alembic head/history/offline SQL checks passed. Live upgrade must be run when the local development stack is available.

## Backend Service Behavior

`backend/app/services/hr_payroll_access_service.py` centralizes the first HR/payroll access slice:

- `inherit_hr_scope(target, source)` copies company, branch, department, and cost center references.
- `can_change_hr_status(record, action)` blocks mutations when workflow state does not allow them.
- `can_view_hr_record(user, module, record)` checks view behavior for HR and payroll compatibility modules.
- `can_modify_hr_record(user, module, action, record)` separates broad view from scoped mutation.
- `user_owns_employee(user, employee_or_id)` supports ESS ownership checks.
- `build_hr_access_hint(...)` returns view-only/action hints for frontend-safe UX.
- `ensure_hr_action_allowed(...)` raises clear 403/422 failures.

A test caught and fixed a scoped payroll management bug: `payroll.manage_own_scope` now works with assigned edit-capable department/company scopes instead of incorrectly requiring `payroll.edit_own_scope`.

## API Endpoint Behavior

GAP-011G hardened these endpoint files with existing permission dependencies while preserving paths:

- `backend/app/api/v1/endpoints/payroll_ke.py`
- `backend/app/api/v1/endpoints/timesheets.py`
- `backend/app/api/v1/endpoints/ess.py`

ESS login remains public. Non-login ESS account/profile/request/document/notification/dashboard/activity routes now require HR permissions. Kenya payroll list/detail/report routes require payroll visibility, and mutation routes require create/approve-style payroll permissions.

Core HR endpoints already had coarse permission guards. Deeper record-level filtering for every core HR list/detail/mutation remains a follow-up.

## Frontend Screens

Frontend type contracts now include the new backend fields:

- `frontend/src/lib/hr.ts`: HR scope fields, employee lifecycle/archive fields, payroll scope fields.
- `frontend/src/lib/payrollKe.ts`: payroll scope fields, payroll locks, payslip distribution fields, statutory effective dates.

Navigation now uses `payroll_ke.view` for Kenya payroll pages, while the lightweight HR payroll page remains under `hr.view`.

Frontend UX now reflects payroll privacy:

- users without payroll create permission do not see New Payroll Run or Seed Rates controls
- users without payroll create permission see payroll profiles as view-only
- users without payroll approve permission do not see payroll approval controls
- users without payroll export permission see export as restricted

## Tests and Checks

Focused tests added:

- `backend/tests/test_gap011_hrms_payroll_access.py`

Coverage includes:

- HR broad view with scoped employee edit
- payroll visibility separate from generic HR visibility
- scoped payroll management limited to assigned department scope
- payroll status locks and superuser bypass
- HR scope inheritance and employee self-ownership
- HR/payroll registry and seed contracts
- frontend payroll guards, action permissions, view-only labels, and type contracts

Commands run:

- `cd backend; .\venv\Scripts\python.exe -m py_compile tests\test_gap011_hrms_payroll_access.py app\services\hr_payroll_access_service.py app\core\module_registry.py app\db\seed.py`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap011_hrms_payroll_access.py -q`
- `cd frontend; npm.cmd run type-check`

Result:

- 7 focused GAP-011 tests passed.
- Frontend type-check passed.

## Known Limitations and Follow-Up

- Live Alembic upgrade for `20260515_0020` still needs verification when Docker/PostgreSQL is available.
- Core HR endpoints still need deeper record-level scope filtering beyond coarse permission guards.
- Recruitment, appraisals, training, and expenses were audited but not fully scope-hardened in this slice.
- Kenya payroll routes still rely primarily on permission gates; per-record company/branch/department filtering should be expanded in a later endpoint-hardening pass.
- Duplicate payroll surfaces remain intentionally documented rather than destructively removed. Kenya payroll is canonical for localized statutory payroll; HR payroll remains a compatibility summary surface.

## Acceptance Criteria Snapshot

- HR/payroll ownership boundaries documented: done.
- Additive schema reconciliation implemented: done.
- ORM and schema contracts updated: done.
- Shared HR/payroll access service added: done.
- Kenya payroll, timesheets, and ESS endpoint permission hardening started: done.
- Frontend payroll privacy and type contracts updated: done.
- Registry and seed contracts verified: done.
- Focused tests added and passing: done.
- Live DB migration verification: pending local Docker/PostgreSQL availability.
