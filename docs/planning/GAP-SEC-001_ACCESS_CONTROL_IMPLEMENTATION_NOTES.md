# GAP-SEC-001 ERP-wide Permission + Scope-Based Access Control Implementation Notes

## Implemented Foundation

This checkpoint implements the first backend/frontend foundation for ERP-wide scoped access control.

Completed:

- Added additive Alembic migration `20260511_0030_access_scopes`.
- Added `AccessScope` ORM model with role-owned and user-owned scopes.
- Added `Permission.is_active` and `Role.is_system_role`.
- Loaded role/user scopes in `get_current_user`.
- Centralized permission/scope logic in `backend/app/core/access_control.py`.
- Kept existing `require_permission(module, action)` compatibility and routed it through the new helper.
- Extended `/api/v1/auth/me` to include:
  - `modules`
  - `scopes`
  - `feature_flags`
  - existing `permission_codes`
- Added backend schemas for access scope assignment and read payloads.
- Added role scope APIs:
  - `GET /api/v1/roles/{role_id}/scopes`
  - `PUT /api/v1/roles/{role_id}/scopes`
- Added user scope APIs:
  - `GET /api/v1/users/{user_id}/scopes`
  - `PUT /api/v1/users/{user_id}/scopes`
- Added audit event constants for role/user scope assignment/removal.
- Added frontend auth helpers:
  - `hasAnyPermission`
  - `hasModule`
  - `canPerformInScope`
  - `canViewScope`
  - `canEditScope`
  - `canViewRecord`
  - `canEditRecord`
  - `getFirstAllowedRoute`
- Added frontend API helpers for assigning/listing role and user scopes.
- Added scope-aware permission seed definitions and conservative role templates.
- Added focused tests for broad view vs scoped mutation, user override precedence, status locks, admin bypass, and seed contracts.
- Applied first-pass backend scoped enforcement to critical module slices:
  - inventory/WMS stock summaries, stock adjustments, stock deletion, movements, entry, issue, and transfers
  - production order list/detail and lifecycle actions using warehouse scope until factory/line IDs exist on the order model
  - sales customer/order list/detail and mutation paths using customer region scope
  - procurement PR/PO list/detail and mutation paths using department scope
  - quality inspection list/detail, result edits, decisions, quarantine release, and QC creation using warehouse/product-category-ready scopes
  - finance journal list/detail, creation, posting, and reversal using nullable company/branch/cost-center scope fields
- Added additive Alembic migration `20260511_0040_finance_journal_scopes`.
- Updated frontend permission matching so base permissions such as `inventory.view` are satisfied by scoped variants such as `inventory.view_all` and `inventory.view_own_scope`.
- Updated frontend record-scope resolution for `target_warehouse_id`, `from_warehouse_id`, `to_warehouse_id`, `region`, and `department`.
- Updated the inventory page to show row-level `View only` badges and disable warehouse mutation buttons when the user lacks the relevant action scope.
- Added user-detail and role-detail scope management panels backed by the existing user/role scope assignment APIs.

## Security Semantics

The implemented helper layer supports the required rule:

- view permissions and mutation permissions are evaluated separately
- `*_view_all` can allow broad visibility
- `*_edit_own_scope`, `*_post_own_scope`, `*_release_own_scope`, etc. require matching active scopes
- user-owned scope rows override role-owned rows for the same scope
- mutation is denied by default when no matching scope exists
- superuser bypass is explicit
- workflow status locking blocks standard mutation for locked states such as `POSTED`, `CLOSED`, `COMPLETED`, `RELEASED`, `REVERSED`, and `CANCELLED`

## Conservative Seed Behavior

The seed adds scope-aware permission codes and default role templates.

Important:

- `owner` and `admin` receive explicit `global:ALL` role scopes.
- Operational roles receive broad view and own-scope mutation permission codes.
- Operational roles do not receive fake global edit scopes.
- Real mutation access for warehouse/factory/company/region/etc. must be granted by assigning `AccessScope` rows.

This prevents broad view permissions from silently becoming broad edit permissions.

## Current Limitations

This is a first-pass ERP-wide enforcement rollout across the highest-risk operational slices. It is not yet exhaustive coverage of every endpoint in every module.

Still required:

- Add row-level access hints to high-value list APIs such as stock, production orders, QC lots, invoices, purchase orders, sales orders, employees, and assets.
- Improve the initial JSON-based scope assignment UI into a friendlier form-driven scope picker and add the permission debugger.
- Add deeper endpoint-level tests for inventory/WMS, production, quality, finance, sales, procurement, HR, maintenance, and utilities.
- Extend scoped enforcement beyond the first-pass routes into remaining secondary endpoints, reports, and analytics pages.
- Rerun live `alembic upgrade head` when PostgreSQL is accepting connections.

## Checks Run

Passed:

- Backend py_compile for changed models, schemas, routers, seed, and access-control helper.
- Frontend type-check with `npm.cmd run type-check`.
- Alembic `heads`.
- Alembic offline SQL for `20260511_0020:head`.
- Focused GAP-SEC-001 pytest.
- Regression suite: GAP-001, GAP-002, GAP-SEC-001, hardening, and RBAC attack-simulation tests.
- Alembic offline SQL for `20260511_0030:head` after adding finance journal scope fields.
- Frontend type-check after scoped auth/sidebar/inventory action UX changes.

Blocked:

- Live `alembic upgrade head` still fails because local PostgreSQL refuses the connection.

Known unrelated import warnings/errors observed during a broad app route smoke:

- missing local optional package `pyotp` for 2FA imports
- missing local optional package `dateutil` for fixed assets imports
- existing SQLAlchemy overlap warnings in unrelated models

The scope routes themselves registered successfully in that smoke.
