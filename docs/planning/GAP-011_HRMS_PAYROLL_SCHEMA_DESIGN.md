# GAP-011 HRMS / Payroll Schema Design

Status: GAP-011B design complete
Phase: Phase 3 - High-importance operational modules
Business priority: High
Technical area: HR / Payroll

## Summary

GAP-011 should harden the existing HR/payroll domain through additive reconciliation. The repository already has core HR, Kenya payroll, timesheets, ESS, recruitment, appraisals, training, and expenses. The design should not replace these modules. It should make migration ownership deterministic, define a canonical employee identity, split payroll privacy from generic HR access, add operational scope fields, and prepare consistent workflow locks.

The first implementation slice should focus on the security and schema foundations that later service/API/frontend tasks can enforce safely:

- own or reconcile core HR tables in Alembic;
- add company, branch, department, cost center, manager, and employee-self scope fields where missing;
- make Kenya payroll the canonical statutory payroll surface;
- preserve lightweight HR payroll as compatibility/summary data;
- add response/access-hint fields later through schemas, not through duplicate tables;
- keep all migration work additive and idempotent.

## Design Inputs From GAP-011A

The audit found:

- core HR exists in `backend/app/models/hr.py`;
- Kenya payroll exists in `backend/app/models/payroll_ke.py` and `backend/app/services/payroll_ke_service.py`;
- timesheets, ESS, recruitment, appraisals, training, and expenses exist;
- core HR table migration ownership is not clearly discoverable;
- Kenya payroll and lightweight HR payroll are duplicate payroll surfaces;
- many HR-adjacent endpoints need explicit auth, permission, and scope checks;
- frontend navigation uses coarse `hr.view` for sensitive payroll and HR-adjacent pages;
- ESS and timesheets rely on caller-supplied employee identifiers without enough central ownership checks.

## HR / Payroll Ownership Boundaries

### Canonical Employee Master

`hr_employees` remains the canonical employee master table.

Design rules:

- every HR/payroll/ESS/timesheet/appraisal/training/expense employee reference should resolve to `hr_employees.id` where practical;
- existing string employee IDs should be preserved during transition, but new normalized UUID fields should be added when needed;
- the `Employee.user_id` link remains the bridge to central auth users for employees who can log in;
- ESS account/profile data should reference the canonical employee, not act as an independent employee master.

### Canonical Statutory Payroll

Kenya payroll (`ke_payroll_profiles`, `ke_payroll_runs`, `ke_payroll_lines`, `ke_payslips`) should be treated as the canonical statutory payroll surface.

Lightweight HR payroll (`hr_payroll_periods`, `hr_payroll_lines`) should remain as a compatibility or summary layer until the product can safely retire or repurpose it. GAP-011 should not remove this surface.

### HR-Adjacent Modules

Timesheets, ESS, recruitment, appraisals, training, and expenses are related to HR but should keep their current module ownership. GAP-011 should add canonical employee and scope bridge fields first, then later endpoints can enforce ownership and permissions consistently.

## Employee Master Ownership

Additive fields recommended for `hr_employees`:

| Field | Type | Purpose |
|---|---|---|
| `company_id` | UUID nullable FK to `companies.id` | Company scope for HR/payroll visibility and mutation. |
| `branch_id` | UUID nullable FK to `branches.id` | Branch scope for HR/payroll visibility and mutation. |
| `department_id` | String nullable | Department or employee-department scope. Kept string because existing HR stores department as text. |
| `cost_center_id` | UUID nullable FK to `cost_centers.id` | Finance/payroll allocation scope. |
| `manager_employee_id` | UUID nullable FK to `hr_employees.id` | Manager/self-service and timesheet approval boundary. |
| `terminated_at` | Date nullable | Lifecycle timestamp without deleting history. |
| `archived_at` | DateTime nullable | Soft archive marker. |
| `archived_by_id` | UUID nullable FK to `users.id` | Auditability for archive action. |

Existing `department` should not be removed. It can continue serving legacy display/import behavior while `department_id` becomes the scope key.

## Department / Branch / Company Scope Model

Use GAP-SEC-001 `AccessScope` as the authorization source of truth.

Scope types for HR/payroll:

- `company`
- `branch`
- `department`
- `employee_department`
- `cost_center`
- `employee`

Mutation rules:

- HR view can be broad (`hr.view_all`) or scoped (`hr.view_own_scope`).
- HR mutation must require `hr.edit_all` or `hr.edit_own_scope`.
- Payroll view must require payroll-specific permissions, not generic HR view.
- Payroll mutation must require `payroll.manage_all`, `payroll.manage_own_scope`, `payroll.approve_all`, or `payroll.approve_own_scope` depending on action.
- ESS self-service should use `employee` scope derived from the authenticated user/employee link.

## Payroll Period Model

Kenya payroll run should be the operational statutory period object.

Recommended additive fields for `ke_payroll_runs`:

| Field | Type | Purpose |
|---|---|---|
| `company_id` | UUID nullable FK | Company scope for run visibility and approval. |
| `branch_id` | UUID nullable FK | Branch scope for branch payroll runs. |
| `department_id` | String nullable | Department-scoped runs where needed. |
| `cost_center_id` | UUID nullable FK | Cost allocation and scope. |
| `locked_at` | DateTime nullable | Locks run after approval/payment. |
| `locked_by_id` | UUID nullable FK to users | Auditability for lock. |

The existing unique constraint on `period_month` and `period_year` is too global for multi-company payroll. In a later safe migration, add a scoped uniqueness rule for company/branch-aware runs. Do not drop the old uniqueness constraint until data and rollout are reviewed.

## Payslip Model

`ke_payslips` should remain the statutory payslip table.

Recommended additive fields:

| Field | Type | Purpose |
|---|---|---|
| `company_id` | UUID nullable FK | Scope inherited from run/employee. |
| `branch_id` | UUID nullable FK | Scope inherited from run/employee. |
| `department_id` | String nullable | Scope inherited from employee. |
| `viewed_at` | DateTime nullable | ESS visibility audit. |
| `sent_at` | DateTime nullable | Distribution audit. |
| `sent_by_id` | UUID nullable FK to users | Distribution actor. |

Do not expose payslip amounts through generic HR schemas or frontend screens. Payslip fields should be returned only through payroll-authorized endpoints or self-service owner endpoints.

## Payroll Run Model

`PayrollRunStatus` currently supports `DRAFT`, `CALCULATED`, `APPROVED`, `PAID`, and `CANCELLED`.

Workflow lock design:

- `DRAFT`: editable by payroll managers in scope.
- `CALCULATED`: recalculation allowed only by payroll managers in scope.
- `APPROVED`: no line/profile edits; payment/export actions only.
- `PAID`: immutable except reversal/correction workflow.
- `CANCELLED`: immutable.

Service helpers should later expose:

- `can_modify_payroll_run(status, action)`;
- `ensure_payroll_run_scope(user, run, action)`;
- `build_payroll_access_hint(user, record)`.

## Deductions / Allowances / Tax Rules

Existing Kenya payroll uses:

- `KeTaxBand`
- `KeStatutoryRate`
- `KeNhifTier`
- `SHIFTier`
- JSON allowance/deduction payloads on profile/line records

Recommended additive fields for statutory configuration:

| Table | Field | Purpose |
|---|---|---|
| `ke_tax_bands` | `effective_from`, `effective_to` | Period-specific rate governance. |
| `ke_statutory_rates` | `effective_from`, `effective_to` | Period-specific statutory governance. |
| `ke_nhif_tiers` | `effective_from`, `effective_to` | Period-specific tier governance. |
| `ke_shif_tiers` | already has `effective_date`; add `effective_to` later if needed | Versioned SHIF governance. |

Do not normalize all allowance/deduction components into new tables in this slice. The existing JSON structure can remain until payroll component management becomes its own feature.

## Timesheet To Payroll Relationship

`timesheet_headers.employee_id` is currently a string. Additive bridge fields recommended:

| Field | Type | Purpose |
|---|---|---|
| `hr_employee_id` | UUID nullable FK to `hr_employees.id` | Canonical employee link. |
| `company_id` | UUID nullable FK | Scope inherited from employee. |
| `branch_id` | UUID nullable FK | Scope inherited from employee. |
| `department_id` | String nullable | Department scope. |
| `manager_employee_id` | UUID nullable FK to `hr_employees.id` | Approval boundary. |
| `payroll_run_id` | UUID nullable FK to `ke_payroll_runs.id` | Trace which payroll run consumed the timesheet. |
| `finalized_by_id` | UUID nullable FK to users | Auditability for finalization. |

The existing string fields should remain during migration. Services can gradually populate the canonical fields from `hr_employees`.

## Expense Reimbursement To Payroll Relationship

Expense claims already have their own accounting/reimbursement surface. GAP-011 should not force all expenses into payroll, but should define bridge fields if missing:

- canonical `hr_employee_id`;
- company/branch/department/cost-center scope fields;
- optional `payroll_run_id` for reimbursements included in payroll;
- reimbursement status lock rules.

If expense models already have equivalent fields, later tasks should reuse them instead of adding duplicates.

## ESS Boundaries

ESS currently has separate accounts and profiles. Preserve these tables for compatibility, but add central-auth and canonical employee bridges:

| Table | Field | Purpose |
|---|---|---|
| `ess_accounts` | `user_id` UUID nullable FK to `users.id` | Bind ESS to central auth where possible. |
| `ess_accounts` | `hr_employee_id` UUID nullable FK to `hr_employees.id` | Canonical employee ownership. |
| `ess_employee_profiles` | `hr_employee_id` UUID nullable FK to `hr_employees.id` | Canonical profile ownership. |

Service/API design:

- authenticated central user can access ESS only for their linked employee unless an HR/payroll permission grants broader access;
- caller-supplied employee IDs must be resolved and compared to the authenticated user's employee link;
- ESS payroll/payslip routes must never expose other employees' payroll data.

## Recruitment / Appraisal / Training Relations

These modules can remain separate but should bridge to `hr_employees`:

- candidate-to-employee conversion should create or link an `hr_employees` record;
- appraisal records should store canonical `hr_employee_id`, reviewer/manager employee ID, and department scope;
- training assignments/certifications should store canonical `hr_employee_id` and department/company scope.

GAP-011 should document and prepare these bridges, but endpoint hardening can start with the HR/payroll/timesheet/ESS surfaces before touching every HR-adjacent feature.

## Permissions And Scopes

Recommended permission model:

| Permission | Meaning |
|---|---|
| `hr.view_all` | View all HR employee/non-payroll records subject to tenant/company rules. |
| `hr.view_own_scope` | View HR records in assigned company/branch/department/employee scopes. |
| `hr.edit_all` | Edit all HR records. Admin-level only. |
| `hr.edit_own_scope` | Edit HR records only inside assigned scopes. |
| `employees.view_own_scope` | View employee directory records in assigned scope. |
| `employees.self_view` | View own employee profile. |
| `employees.self_update` | Submit own profile update requests. |
| `payroll.view_all` | View payroll profiles, runs, lines, and payslips across scopes. Highly restricted. |
| `payroll.view_own_scope` | View payroll records inside assigned scope. |
| `payroll.manage_all` | Create/calculate/update payroll across scopes. Highly restricted. |
| `payroll.manage_own_scope` | Manage payroll inside assigned company/branch/department scope. |
| `payroll.approve_all` | Approve payroll across scopes. Highly restricted. |
| `payroll.approve_own_scope` | Approve payroll inside assigned scope. |
| `payroll.export_all` | Export payroll reports across scopes. |
| `payroll.export_own_scope` | Export payroll reports inside assigned scope. |
| `timesheets.view_own_scope` | View assigned team/department timesheets. |
| `timesheets.approve_own_scope` | Approve assigned team/department timesheets. |
| `ess.self_service` | Use employee self-service for own employee record only. |

Keep `payroll_ke.*` permissions for compatibility, but map them in services/routes toward the canonical `payroll.*` action model.

## Audit Logging

Later service/API tasks should audit:

- employee create/update/archive/termination;
- HR scope assignment changes;
- payroll profile create/update;
- payroll run calculate/approve/pay/cancel;
- payslip generation/send/view through ESS;
- timesheet approval/finalization;
- ESS denied access to another employee;
- payroll export.

Audit entries should include user ID, action, module, entity type, entity ID, scope fields, request ID if available, and before/after payload when practical.

## Migration Strategy

GAP-011C should add one safe reconciliation migration.

Migration rules:

- additive only;
- idempotent helper style matching recent GAP migrations;
- no table drops;
- no column drops;
- no destructive changes to existing constraints;
- create missing core HR tables only if absent;
- add columns only if absent;
- add indexes/FKs only if absent;
- preserve legacy string employee ID fields.

Recommended migration content:

1. Reconcile core HR table ownership by creating missing `hr_*` tables only if absent.
2. Add HR scope/lifecycle columns to `hr_employees`.
3. Add scope columns to `hr_shift_templates`, `hr_attendance`, `hr_leave_requests`, `hr_leave_balances`, `hr_payroll_periods`, and `hr_payroll_lines` where useful.
4. Add payroll scope/lock columns to `ke_payroll_profiles`, `ke_payroll_runs`, `ke_payroll_lines`, and `ke_payslips`.
5. Add effective-date fields to statutory rate tables where missing.
6. Add canonical employee/scope bridge fields to `timesheet_headers`.
7. Add central auth/canonical employee bridge fields to `ess_accounts` and `ess_employee_profiles`.

## Backward Compatibility

Backward compatibility requirements:

- keep existing API paths;
- keep existing HR payroll tables;
- keep existing Kenya payroll routes;
- keep existing ESS account/profile tables;
- preserve legacy string employee ID fields;
- make new fields nullable at first;
- populate scopes opportunistically in services rather than requiring immediate historical backfill.

## GAP-011C Migration Scope

GAP-011C should implement only the schema foundation needed for later tasks. It should not yet refactor every endpoint.

Expected migration name:

- `20260515_0020_hrms_payroll_reconciliation.py`

Expected checks:

- `python -m py_compile backend/alembic/versions/20260515_0020_hrms_payroll_reconciliation.py`
- `cd backend; alembic heads`
- `cd backend; alembic history -r 20260515_0010:20260515_0020`
- `cd backend; alembic upgrade 20260515_0010:20260515_0020 --sql`
- live `alembic upgrade head` only if the local development DB is running and safe.

## GAP-011D And Later Direction

GAP-011D should update ORM models to match the migration.

GAP-011E should add request/response schema fields and sensitive payroll response separation.

GAP-011F should add HR/payroll service helpers for:

- scope resolution;
- access hints;
- payroll privacy checks;
- employee self-service ownership;
- workflow locks.

GAP-011G should apply helpers to core HR, Kenya payroll, timesheets, and ESS first. Recruitment, appraisal, training, and expense hardening can follow if the slice remains safe.

GAP-011H should update frontend route visibility and view-only/sensitive-data behavior.

GAP-011I should register/seed missing module-owned HR/payroll/timesheet/ESS permissions conservatively.

GAP-011J should add focused privacy/scope/status tests.

## Acceptance Criteria For GAP-011B

GAP-011B is complete when:

- schema decisions are documented against actual HR/payroll models;
- HR/payroll ownership boundaries are defined;
- duplicate payroll surface handling is documented;
- canonical employee identity design is documented;
- scope fields and permissions are specified;
- payroll period, run, line, payslip, allowance/deduction, timesheet, expense, ESS, recruitment, appraisal, and training relationships are addressed;
- migration strategy is additive and backward-compatible;
- next implementation tasks have clear migration/model/schema direction.
