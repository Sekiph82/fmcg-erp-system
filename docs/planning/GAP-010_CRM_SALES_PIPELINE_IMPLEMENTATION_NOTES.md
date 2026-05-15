# GAP-010 - CRM and Sales Pipeline Depth Implementation Notes

Status: GAP-010K documentation complete  
Phase: Phase 3 - High-importance operational modules  
Business priority: High  
Technical area: CRM / Sales

## Summary

GAP-010 hardens the existing Sales, Quotation, and CRM pipeline foundation. The repo already had customer, sales order, quotation, CRM record, CRM territory, pipeline stage, activity, competitor, win/loss, and AI recommendation surfaces. This slice reconciles commercial scope fields, adds row-level access hints, applies backend permission/scope guards to the primary commercial flows, and makes the frontend show view-only commercial records instead of pretending every visible record is editable.

The core rule implemented here is:

- Broad commercial visibility can be granted with `sales.view_all` or `crm.view_all`.
- Mutation remains restricted by action permission, commercial scope, and workflow status.
- Backend checks are the source of truth. Frontend badges and disabled actions are UX only.

## Implemented Scope

### Migration

Added `backend/alembic/versions/20260515_0010_crm_sales_scope_reconciliation.py`.

The migration is additive and reconciliation-oriented:

- Adds commercial scope columns to:
  - `customers`
  - `sales_orders`
  - `quotations`
  - `crm_records`
  - `crm_territories`
- Adds approval and discount-governance fields to:
  - `sales_orders`
  - `quotations`
- Adds `crm_record_id` linkage on quotations.
- Adds `territory_id` and `assigned_customer_id` linkage on CRM records.
- Adds indexes and foreign keys where safe.
- Does not drop existing records, reset CRM data, or recreate Sales/CRM tables.

Live local development verification was completed:

- `alembic upgrade head` succeeded after fixing CRM territory column/index ordering.
- `alembic current` reports `20260515_0010 (head)`.
- Live schema verification confirmed the required CRM/Sales commercial scope columns and Alembic version.

### Backend Models

Updated:

- `backend/app/models/sales.py`
- `backend/app/models/quotation.py`
- `backend/app/models/crm.py`

Key model additions:

- commercial scope fields:
  - `company_id`
  - `branch_id`
  - `sales_region_id`
  - `sales_team_id`
  - `customer_group_id`
- sales order and quotation approval fields:
  - `approval_status`
  - `discount_approval_required`
  - `discount_approved_by_id`
  - `discount_approved_at`
- quotation-to-CRM linkage:
  - `crm_record_id`
- CRM record scope/linkage fields:
  - `territory_id`
  - `assigned_customer_id`

### Backend Schemas

Updated:

- `backend/app/schemas/sales.py`
- `backend/app/schemas/quotation.py`
- `backend/app/schemas/crm.py`

Added reusable commercial payload contracts:

- `CommercialScopeFields`
- `CommercialAccessHint`

Important read schemas now support row-level access hints through `access`, allowing frontend pages to show view-only commercial rows and suppress unsafe actions.

### Service Helpers

Added:

- `backend/app/services/commercial_access_service.py`

Helper behavior includes:

- `inherit_commercial_scope`
- `commercial_document_key`
- `commercial_module_key`
- `can_change_commercial_status`
- `build_commercial_access_hint`
- `ensure_commercial_action_allowed`

Status locking currently covers:

- customers: edit only when active
- sales orders: edit only when draft; approve/cancel limited by status
- quotations: edit only draft; convert only accepted; delete only draft
- CRM records: edit/cancel/convert only open or on-hold according to action
- CRM territories: edit only active

### API Endpoints

Updated:

- `backend/app/api/v1/endpoints/sales.py`
- `backend/app/api/v1/endpoints/quotation.py`
- `backend/app/api/v1/endpoints/crm_pipeline.py`

Key behavior:

- Customer and sales order list/detail responses include commercial access hints where relevant.
- Customer and sales order create/update paths call commercial scoped action guards.
- Quotation list/detail/create/update/status/convert paths use commercial access helpers.
- Quotation conversion copies commercial scope from the quote to the generated sales order.
- CRM record and territory list/detail/create/update paths use authentication, permission dependencies, scoped filtering, scoped action guards, and access hints.
- CRM is now registered as a module-owned route through the backend module registry.

The deeper CRM child resources, including activities, interest lines, competitors, reports, and AI recommendation actions, remain a known follow-up for inherited record-scope guards.

### Frontend

Updated:

- `frontend/src/lib/sales.ts`
- `frontend/src/lib/quotations.ts`
- `frontend/src/lib/crm_pipeline.ts`
- `frontend/src/app/dashboard/sales/customers/page.tsx`
- `frontend/src/app/dashboard/sales/orders/page.tsx`
- `frontend/src/app/dashboard/sales/quotes/page.tsx`
- `frontend/src/app/dashboard/crm/pipeline/page.tsx`

Frontend behavior:

- Sales, quotation, and CRM types include commercial scope and access-hint fields.
- The CRM Axios client uses `withCredentials: true` to match cookie-auth behavior.
- Sales customer rows show a `View only` badge and disable edit when `access.can_edit === false`.
- Sales order rows show a `View only` badge when returned access hints say the row is not actionable.
- Quotation actions are hidden/suppressed based on `access.can_edit`, `access.can_convert`, and related action flags.
- CRM pipeline cards show `View only`, reduce drag affordance, and prevent drag changes when `access.can_edit === false`.

## Permissions And Roles

Updated:

- `backend/app/core/access_control.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`

Access-control action mappings now include:

- `convert` mapped to `can_create`
- `discount_approve` mapped to `can_approve`

Sales module actions now include:

- `view`
- `create`
- `edit`
- `approve`
- `cancel`
- `convert`
- `export`
- `import`

CRM is now a first-class module registry entry with:

- route prefix `/crm`
- import path `app.api.v1.endpoints.crm_pipeline`
- actions `view`, `create`, `edit`, `delete`, `approve`, `cancel`, `convert`, `export`, `import`

New or expanded scope-aware commercial permissions include:

- `sales.create_all`
- `sales.create_own_region`
- `sales.edit_all`
- `sales.edit_own_region`
- `sales.approve_all`
- `sales.approve_own_region`
- `sales.cancel_all`
- `sales.cancel_own_region`
- `sales.convert_all`
- `sales.convert_own_region`
- `crm.create_all`
- `crm.create_own_region`
- `crm.edit_all`
- `crm.edit_own_region`
- `crm.cancel_all`
- `crm.cancel_own_region`
- `crm.convert_all`
- `crm.convert_own_region`

Role seed changes are conservative:

- `regional_sales_manager` and `sales_manager` receive broad view plus scoped create/edit/approve/cancel/convert grants.
- `cmo` receives broad CRM/Sales mutation grants as an executive role.
- Normal commercial roles do not receive `sales.edit_all` or `crm.edit_all`.
- Actual scoped mutation still requires matching `AccessScope` rows.

## Admin Setup Notes

For a regional sales or CRM manager:

1. Assign broad view permission if needed:
   - `sales.view_all`
   - `crm.view_all`
2. Assign scoped mutation permissions:
   - `sales.create_own_region`
   - `sales.edit_own_region`
   - `sales.approve_own_region`
   - `sales.cancel_own_region`
   - `sales.convert_own_region`
   - `crm.create_own_region`
   - `crm.edit_own_region`
   - `crm.cancel_own_region`
   - `crm.convert_own_region`
3. Assign `AccessScope` rows for the operational commercial scopes:
   - `sales_region`
   - `sales_team`
   - `customer_group`
   - optionally `company` and `branch`
4. Use `can_create`, `can_edit`, `can_approve`, and `can_cancel` flags intentionally. Broad view does not imply mutation.

## Tests And Checks

Added:

- `backend/tests/test_gap010_crm_sales_commercial_access.py`

Focused tests cover:

- broad Sales view without out-of-region edit
- row-level view-only access hints
- commercial scope inheritance
- sales order status locks
- quotation conversion status, permission, and scope gates
- CRM scoped edit and superuser bypass
- module registry and seed permission contracts
- frontend view-only/action suppression contracts

Commands run:

- `cd backend; .\venv\Scripts\python.exe -m py_compile tests\test_gap010_crm_sales_commercial_access.py`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap010_crm_sales_commercial_access.py -q`
- earlier GAP-010 compile, frontend type-check, Alembic, live migration, and live schema verification commands recorded in `CODEX_PROGRESS.md`

Known test warnings:

- Existing SQLAlchemy relationship overlap warnings appear for dimension/project models. They are unrelated to GAP-010.

## Known Limitations And Follow-Ups

This is a production-hardening slice, not the final CRM/Sales implementation. Remaining work includes:

- Add inherited scoped guards for CRM activities, interest lines, competitors, win/loss records, reports, and AI recommendation actions.
- Add richer frontend scope selection in create/edit forms where commercial users need to choose target region/team/group explicitly.
- Backfill commercial scope fields for legacy customers, sales orders, quotations, CRM records, and territories where currently null.
- Add endpoint-level integration tests once safe non-destructive fixtures exist for authenticated CRM/Sales users.
- Extend quote and sales order discount approval flows into a full approval workflow if the business rules require multi-step approval.
- Add richer UI for CRM territory and commercial scope administration.

## Acceptance Criteria Snapshot

GAP-010 is considered complete for the current roadmap slice when:

- migration, live schema verification, ORM models, schemas, service helpers, endpoint guards, frontend UX, permissions/roles, tests, documentation, and final checks are complete;
- broad view and scoped mutation remain separate;
- frontend view-only behavior reflects backend access hints;
- known deeper CRM child-resource follow-ups are recorded honestly.
