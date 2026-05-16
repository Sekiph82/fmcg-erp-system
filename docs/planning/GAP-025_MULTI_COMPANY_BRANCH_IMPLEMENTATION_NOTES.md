# GAP-025 Multi-Company / Multi-Branch / Franchise Scaling — Implementation Notes

## Summary

GAP-025 hardened the existing multi-company / multi-branch implementation with proper permission guards,
module promotion, warehouse multi-tenancy columns, and contract tests.
The core Company/Branch/UserCompanyAccess models and CRUD were already feature-complete.

## Changes Made

### GAP-025A — Audit
- Inspected company models, endpoints, module registry, seed, frontend, and cross-module multi-tenancy.
- Key gaps: bare get_current_user guards, wrong module in require_permission, no company.view/create/edit/delete/export permissions, Warehouse missing company_id/branch_id, no frontend page guard.
- Output: `GAP-025_MULTI_COMPANY_BRANCH_AUDIT.md`

### GAP-025B — Schema Design
- Designed permission family: view, create, edit, delete, export, manage.
- Defined module promotion from EndpointRouteDefinition to ModuleDefinition.
- Confirmed Warehouse multi-tenancy via nullable company_id/branch_id columns.
- Output: `GAP-025_MULTI_COMPANY_BRANCH_SCHEMA_DESIGN.md`

### GAP-025C — Migration
- Created `20260516_0050_multi_company_warehouse_reconciliation.py`.
- Adds `company_id` (UUID FK → companies, nullable) and `branch_id` (UUID FK → branches, nullable) to `warehouses`.
- Uses `_has_column()` guard — idempotent.
- Creates index `ix_warehouses_company_id`.
- Single Alembic head: `20260516_0050`.

### GAP-025D — ORM Update
- Added `company_id` and `branch_id` columns to `Warehouse` model in `backend/app/models/master.py`.
- Both nullable FKs with SET NULL on delete.
- `company_id` indexed.

### GAP-025E — Schema Update
- Added `company_id: Optional[uuid.UUID] = None` and `branch_id: Optional[uuid.UUID] = None` to `WarehouseBase` in `backend/app/schemas/master.py`.
- Propagates to `WarehouseCreate` and `WarehouseRead` via inheritance.

### GAP-025G — Module Registry and Endpoint Guards

**Module Registry:**
- Added `company` as `ModuleDefinition` with `permission_actions=("view", "create", "edit", "delete", "export", "manage")`.
- Removed `company` `EndpointRouteDefinition` (replaced with comment).
- `sidebar_group="Administration"`, `icon_key="building"`, `critical=True`.

**Endpoint rewrite (`backend/app/api/v1/endpoints/company.py`):**
- Added `_check_company_access(db, user, company_id)` helper — raises 403 if user has no `UserCompanyAccess` row and is not superuser.
- All 12 endpoints updated with company-specific permission guards:
  - Read endpoints: `require_permission("company", "view")` + `_check_company_access` on company-scoped routes
  - Write endpoints (company/branch): `require_permission("company", "create")` / `require_permission("company", "edit")`
  - User access management: `require_permission("company", "manage")` (all user grant/revoke/list)
  - Removed all `require_permission("admin", "manage")` uses
  - Removed all bare `Depends(get_current_user)` in route signatures

### GAP-025H — Frontend Guard
- Added `import { RequirePermission } from "@/components/PermissionGuard"` to `frontend/src/app/dashboard/companies/page.tsx`.
- Wrapped main `CompaniesPage` return with `<RequirePermission permission="company.view">`.

### GAP-025I — Seed Permissions and Role Grants
- Replaced single `company.manage` tuple with 6 explicit tuples: view (public=True), create, edit, delete, export, manage.
- Role grants:
  - `admin`: full company access (view, create, edit, delete, export, manage)
  - `company_admin`: view, edit, export, manage (existing manage kept; view/edit/export added)
  - `ceo`: view, export
  - `coo`: view
  - `cto`: view

### GAP-025J — Tests
- Created `backend/tests/test_gap025_multi_company_branch.py` with 22 contract tests:
  - Module registry: company is ModuleDefinition, not in EndpointRouteDefinition
  - Permission seeds: all 6 tuples present
  - Registry permission codes
  - Role grants: admin, company_admin, ceo, coo, cto
  - Endpoint source: require_permission present, view/manage/edit guards present, _check_company_access present, no bare get_current_user, no admin.manage
  - ORM: Company/Branch/UserCompanyAccess importable, Warehouse has company_id/branch_id
  - Schema: WarehouseBase has company_id/branch_id
  - Migration: file exists, company_id/branch_id/warehouses in source
  - Frontend: companies page has RequirePermission + company.view

## Limitations

- Docker not available — migration not executed live. Verified via compile and Alembic SQL.
- Warehouse `company_id`/`branch_id` are nullable — existing warehouses remain unassigned. Application must populate on new warehouse creation.
- Franchise support is out of scope for this GAP — no franchise model added. A future Franchise model would require business requirements defining franchise-specific fields (royalty rates, territory, etc.).
- Cross-company data isolation (product catalog, supplier list) remains at application layer — no database-level row security.
