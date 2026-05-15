# GAP-011 HR / Payroll Audit

Status: GAP-011A audit complete
Phase: Phase 3 - High-importance operational modules
Business priority: High
Technical area: HR / Payroll

## Summary

The repository already has a broad HR/payroll surface. It includes backend models, schemas, endpoints, services, migrations, and frontend pages for employee master data, shifts, attendance, leave, lightweight HR payroll, Kenya payroll localization, timesheets, employee self-service, recruitment, appraisals, training, and expenses.

The main issue is consistency, not absence. Core HR uses one table and permission surface, Kenya payroll uses another route/model surface, ESS has a separate employee/account model, and HR-adjacent modules use their own employee identifiers and workflow patterns. Several routes also have weak or missing auth/permission enforcement. GAP-011 should therefore reconcile HR/payroll ownership, permissions, scopes, and workflow locks before expanding features.

## Business Importance

HR and payroll contain sensitive employee, salary, statutory, bank, attendance, leave, appraisal, and expense data. In an FMCG ERP/MES, this domain must support factory staffing, department and branch-scoped HR access, attendance and shift records, payroll calculations, payslips, employee self-service, statutory reports, and auditability.

Production readiness requires a clear privacy boundary: broad HR visibility must not automatically expose payroll or salary fields, and self-service users must never access other employees' records by changing IDs.

## Files Inspected

Backend files:

- `backend/app/models/hr.py`
- `backend/app/models/payroll_ke.py`
- `backend/app/models/timesheets.py`
- `backend/app/models/ess.py`
- `backend/app/models/recruitment.py`
- `backend/app/models/appraisals.py`
- `backend/app/models/training.py`
- `backend/app/models/expenses.py`
- `backend/app/schemas/hr.py`
- `backend/app/schemas/payroll_ke.py`
- `backend/app/api/v1/endpoints/hr.py`
- `backend/app/api/v1/endpoints/payroll_ke.py`
- `backend/app/api/v1/endpoints/timesheets.py`
- `backend/app/api/v1/endpoints/ess.py`
- `backend/app/api/v1/endpoints/recruitment.py`
- `backend/app/api/v1/endpoints/appraisals.py`
- `backend/app/api/v1/endpoints/training.py`
- `backend/app/api/v1/endpoints/expenses.py`
- `backend/app/services/payroll_ke_service.py`
- `backend/app/services/timesheets_service.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/e9f0a1b2c3d4_payroll_ke.py`
- `backend/alembic/versions/c5d6e7f8b0a9_timesheet_approval_workflow.py`
- `backend/alembic/versions/f2a3b4c5d6e7_employee_self_service.py`
- `backend/alembic/versions/e1f2a3b4c5d6_recruitment_ats.py`
- `backend/alembic/versions/b4c5d6e7a8f9_training_skills_management.py`
- `backend/alembic/versions/d0e1f2a3b4c5_expense_claims.py`

Frontend files:

- `frontend/src/lib/hr.ts`
- `frontend/src/lib/payrollKe.ts`
- `frontend/src/lib/timesheets.ts`
- `frontend/src/components/nav-config.tsx`
- `frontend/src/app/dashboard/hr/page.tsx`
- `frontend/src/app/dashboard/hr/employees/page.tsx`
- `frontend/src/app/dashboard/hr/shifts/page.tsx`
- `frontend/src/app/dashboard/hr/attendance/page.tsx`
- `frontend/src/app/dashboard/hr/leave/page.tsx`
- `frontend/src/app/dashboard/hr/payroll/page.tsx`
- `frontend/src/app/dashboard/payroll/page.tsx`
- `frontend/src/app/dashboard/payroll/profiles/page.tsx`
- `frontend/src/app/dashboard/payroll/reports/page.tsx`
- `frontend/src/app/dashboard/payroll/runs/[id]/page.tsx`
- `frontend/src/app/dashboard/timesheets/*`
- `frontend/src/app/dashboard/ess/*`

Planning and tracker files:

- `TASKS.md`
- `CODEX_PROGRESS.md`
- `docs/planning/ERP_ROADMAP_IMPLEMENTATION_PLAN.md`
- `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md`

## Existing Backend Coverage

Core HR coverage found:

- employee master records;
- shift templates;
- employee shift assignments;
- attendance records;
- leave requests;
- leave balances;
- lightweight payroll periods and payroll lines;
- payroll period approval and export;
- marketing field-team summary.

Kenya payroll coverage found:

- employee payroll profiles;
- PAYE tax bands;
- statutory rates;
- NHIF tiers;
- SHIF tiers;
- payroll runs;
- payroll line calculation;
- payslips;
- statutory payroll reports;
- basic payroll AI insights;
- KRA eTIMS invoice record stub.

Timesheets coverage found:

- timesheet headers and lines;
- submit, approve, reject, and finalize workflow;
- approval logs;
- payroll input report;
- utilization, overtime, project, and activity reports;
- AI recommendations.

ESS and HR-adjacent coverage found:

- ESS accounts, profiles, leave, attendance, requests, documents, notifications, activity logs, and recommendations;
- recruitment stages, requisitions, postings, candidates, interviews, offers, reports, and AI recommendations;
- appraisal periods, templates, records, KPI/competency lines, development plans, reports, and AI recommendations;
- training skills, employee skill profiles, programs, sessions, assignments, certifications, feedback, reports, and AI recommendations;
- expense categories, policies, claims, advances, approvals, reimbursements, accounting entries, reports, and AI recommendations.

## Existing Frontend Coverage

Frontend pages and API clients exist for:

- HR dashboard and employee management;
- shifts, attendance, leave, and HR payroll;
- Kenya payroll landing, profiles, reports, and payroll-run detail pages;
- timesheets;
- ESS;
- recruitment, appraisals, training, and expenses through dashboard navigation.

The frontend is broad enough for review, but route permissions are too coarse. Many HR-adjacent areas reuse `hr.view`, including areas that should be protected by payroll-specific, ESS-specific, or workflow-specific permissions.

## Existing Permissions / Roles / Scopes

Seeded permissions include:

- `hr.view`
- `hr.create`
- `hr.edit`
- `hr.approve`
- `hr.export`
- `hr.import`
- `hr.import_template`
- `payroll_ke.view`
- `payroll_ke.create`
- `payroll_ke.approve`
- `payroll_ke.export`
- `hr.view_own_scope`
- `hr.edit_own_scope`
- `employees.view_own_scope`
- `payroll.view`
- `payroll.manage_own_scope`

Roles found:

- `hr_manager` with broad `hr.*` and `payroll_ke.*` grants;
- `scoped_hr_manager` with scoped HR and payroll grants;
- executive and company admin roles with HR visibility.

Scope and permission gaps:

- `hr` is registered as an endpoint route rather than a first-class module definition.
- `payroll_ke` is registered as an endpoint route rather than a first-class module definition.
- payroll routes do not consistently enforce `payroll_ke.*` or `payroll.*` permissions.
- scoped HR permissions exist in seed data, but route-level scope enforcement is inconsistent.
- frontend navigation mostly uses `hr.view` for HR, payroll, ESS, recruitment, appraisals, training, timesheets, and expenses.

## Existing Migrations

Found HR/payroll-adjacent migrations:

- `backend/alembic/versions/e9f0a1b2c3d4_payroll_ke.py`
- `backend/alembic/versions/c5d6e7f8b0a9_timesheet_approval_workflow.py`
- `backend/alembic/versions/f2a3b4c5d6e7_employee_self_service.py`
- `backend/alembic/versions/e1f2a3b4c5d6_recruitment_ats.py`
- `backend/alembic/versions/b4c5d6e7a8f9_training_skills_management.py`
- `backend/alembic/versions/d0e1f2a3b4c5_expense_claims.py`

Important migration risk: Alembic ownership for core HR tables such as `hr_employees`, `hr_shift_templates`, `hr_attendance`, `hr_leave_requests`, `hr_leave_balances`, `hr_payroll_periods`, and `hr_payroll_lines` was not found by search, even though later migrations reference `hr_employees`.

## Existing Tests

No focused GAP-011 HR/payroll test file was found.

Related tests found:

- `backend/tests/test_security.py` includes a payroll statutory completeness guard.
- `backend/tests/test_attack_simulation.py` checks payroll statutory completeness and confirms `payroll_ke.*` permissions exist.

Coverage gaps:

- HR employee CRUD permission and scope tests;
- payroll profile and payslip privacy tests;
- Kenya payroll calculation regression fixtures;
- timesheet authentication and approval-boundary tests;
- ESS self-only access tests;
- leave approval and balance tests;
- payroll run lifecycle/status-lock tests.

## Existing Documentation

No GAP-011-specific audit, design, or implementation documentation existed before this audit.

Related planning files are present:

- `TASKS.md`
- `CODEX_PROGRESS.md`
- `docs/planning/ERP_ROADMAP_IMPLEMENTATION_PLAN.md`
- `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md`

## Key Finding 1: HR Module Exists but Needs Hardening

Core HR is implemented with meaningful employee, shift, attendance, leave, and lightweight payroll models and endpoints. The main HR routes use `require_permission("hr", action)`, which is better than open access.

The hardening gaps are company/branch/department scope enforcement, employee status lifecycle rules, payroll privacy separation, and safer delete behavior. Current employee delete behavior is a hard delete, which is risky for audit, payroll, attendance, and historical records.

## Key Finding 2: Kenya Payroll Exists but Needs Ownership Cleanup

Kenya payroll is not fake. It includes real statutory calculation service code and models for tax bands, statutory rates, payroll runs, payroll lines, payslips, and reports.

The ownership problem is that Kenya payroll lives alongside lightweight HR payroll without a clear canonical boundary. Payroll routes inspected generally require authentication but not consistent payroll-specific permission and scope checks. Salary, payroll profile, and payslip access should be isolated from generic HR access.

## Key Finding 3: Duplicate Payroll Surfaces / Route Conflicts

Two payroll surfaces exist:

- core HR payroll under `/api/v1/hr/payroll/*` and `frontend/src/app/dashboard/hr/payroll/page.tsx`;
- Kenya payroll under `/api/v1/payroll-ke/*` and `frontend/src/app/dashboard/payroll/*`.

Both surfaces may be useful, but the product needs a documented ownership model. GAP-011 should avoid destructive cleanup and instead define Kenya payroll as the canonical statutory payroll surface while preserving compatibility for existing lightweight HR payroll screens where they are still used.

## Key Finding 4: Auth and Permission Enforcement Gaps

Core HR has coarse permission dependencies. Kenya payroll mostly uses authentication without consistent explicit payroll permission checks. Timesheets, ESS, recruitment, appraisals, training, and expenses endpoint files inspected largely expose route handlers without explicit central auth or permission dependencies.

This is a high-priority security issue because HR-adjacent endpoints contain sensitive employee, performance, attendance, payroll, expense, and applicant data.

## Key Finding 5: Scope Enforcement Gaps

Scope-aware permissions exist in seed data, but HR/payroll routes do not consistently enforce company, branch, department, employee-department, manager, or employee-self scopes.

Risk examples:

- HR users with view access may be able to mutate employee records outside their department.
- Payroll users may access salary data outside their company/branch scope.
- ESS users may be able to act on caller-supplied employee IDs.
- Timesheet approvals may not be constrained to the assigned manager or department.

## Key Finding 6: Migration Ownership and Schema Consistency Risks

Later migrations reference `hr_employees`, but a creation migration for the core HR tables was not clearly discoverable. This creates fresh-database risk if the current dev database relies on historical `create_all` behavior or non-versioned setup.

Schema consistency is also fragmented across modules. ESS, Kenya payroll, timesheets, appraisals, training, and expenses have their own employee references. GAP-011 should define a canonical employee identity approach and then reconcile each module incrementally.

## Missing Pieces

- Deterministic Alembic ownership for core HR tables.
- Central HR/payroll access helper aligned with GAP-SEC-001 scopes.
- Payroll-specific privacy permissions and response-shaping rules.
- Explicit auth/permission dependencies on all HR-adjacent endpoints.
- Employee self-service ownership checks.
- Department/company/branch/manager scope fields and indexes where missing.
- Payroll run lifecycle/status locks.
- Non-destructive employee archive/termination behavior.
- One canonical employee ID strategy across HR, ESS, payroll, timesheets, appraisals, training, and expenses.
- Frontend route and action controls that separate HR view from payroll/salary access.

## Partial Pieces

- Core HR CRUD exists but is lightweight and not fully scoped.
- Leave management exists but entitlement accrual and balance initialization are thin.
- Attendance exists but device/biometric/import validation and shift-derived expected hours are not complete.
- Kenya payroll calculations exist but statutory rates need effective-date/versioned governance.
- Payslips exist but employee access and distribution privacy need hardening.
- Timesheets have workflow states but weak endpoint auth and ownership boundaries.
- ESS is feature-rich but appears to be parallel to central auth/RBAC.
- Recruitment, appraisals, training, and expenses are broad but need consistent auth and scope enforcement.

## Risks

| Risk | Impact |
|---|---|
| Missing core HR migration ownership | Fresh databases may fail when payroll migrations reference `hr_employees`, or HR tables may depend on runtime `create_all` history. |
| Payroll endpoints authenticated but not permission-gated | Any authenticated user may access or mutate salary/payroll data if routes are reachable. |
| HR-adjacent endpoints without auth dependencies | Sensitive HR data and workflows may be exposed or mutable without proper authorization. |
| Generic `hr.view` used for payroll and ESS navigation | Users with HR visibility may see payroll/salary/ESS surfaces they should not access. |
| Caller-supplied employee IDs in ESS/timesheets | Users may read or mutate other employees' records unless ownership is enforced server-side. |
| Hard delete for employees | Audit, payroll, attendance, leave, and timesheet relationships can be damaged. |
| Two payroll implementations | Operators may not know whether `/hr/payroll/*` or `/payroll-ke/*` owns the statutory process. |

## Recommended GAP-011B Design Direction

Design GAP-011 as an additive reconciliation, not a rewrite:

- establish deterministic migration ownership for core HR tables;
- document Kenya payroll as the canonical statutory payroll surface;
- preserve the lightweight HR payroll surface as a compatibility/summary surface until safely retired;
- add company, branch, department, employee-department, cost-center, manager, and employee-self scope fields where needed;
- define a canonical employee ID relationship across HR, ESS, payroll, timesheets, appraisals, training, and expenses;
- separate `hr.*` visibility from `payroll.*` salary and payslip permissions;
- add workflow status locks for payroll runs, payslips, leave, timesheets, appraisals, expenses, and employee lifecycle state;
- add central HR/payroll access helpers so endpoint code stays thin;
- update frontend navigation and actions to honor HR/payroll privacy and view-only states.

## Acceptance Criteria for GAP-011 Completion

GAP-011 should be considered complete only when:

- core HR table migration ownership is deterministic;
- HR/payroll/ESS/timesheet routes require authentication and correct permissions;
- broad HR visibility and scoped mutation are separate;
- payroll salary, payslip, and profile data are permission-gated separately from HR view;
- ESS cannot access another employee's records by changing IDs;
- employee records are not hard-deleted in normal workflows;
- payroll, leave, timesheet, appraisal, and expense statuses enforce workflow locks where implemented;
- frontend navigation and action controls reflect backend permissions;
- focused tests cover critical HR/payroll privacy, scope, and workflow rules.
