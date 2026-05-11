# GAP-SEC-001 ERP-wide Access-Control Schema Design

## Task

`GAP-SEC-001B: Design data model/schema: ERP-wide permission + scope-based access control`

## Design Principle

Keep the current RBAC model and add one generic scope layer.

Existing:

- `User`
- `Role`
- `Permission`
- `user_role`
- `role_permission`

New:

- `AccessScope`
- centralized scope evaluation helpers
- effective access payload in `/auth/me`

This preserves existing login, cookie auth, current API paths, and existing `module.action` permission behavior while enabling the new `module.action.scope_level` permission format.

## Permission Code Format

No destructive permission-table change is required.

Use the existing `Permission.code` field for scope-aware permissions:

| Permission Code | Module | Action |
|---|---|---|
| `inventory.view_all` | `inventory` | `view_all` |
| `inventory.view_own_scope` | `inventory` | `view_own_scope` |
| `inventory.edit_all` | `inventory` | `edit_all` |
| `inventory.edit_own_scope` | `inventory` | `edit_own_scope` |
| `finance.post_all` | `finance` | `post_all` |
| `finance.post_own_company` | `finance` | `post_own_company` |
| `users.manage` | `users` | `manage` |
| `roles.manage` | `roles` | `manage` |

Legacy permissions such as `inventory.view` and `finance.configure` remain valid during migration.

## AccessScope Model

Table: `access_scopes`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Generated UUID. |
| `user_id` | UUID nullable FK to users | User-specific override owner. |
| `role_id` | UUID nullable FK to roles | Role default scope owner. |
| `scope_type` | string | Examples: `company`, `branch`, `warehouse`, `factory`, `production_line`, `department`, `sales_region`, `customer_group`, `supplier_category`, `product_category`, `cost_center`, `project`, `employee_department`, `machine`, `utility_area`, `global`. |
| `scope_id` | string | Related record id as string, or `ALL` for explicit global scope. |
| `scope_name` | string nullable | Optional cached display label for `/auth/me` and admin screens. |
| `can_view` | bool | View inside this scope. |
| `can_create` | bool | Create inside this scope. |
| `can_edit` | bool | Edit inside this scope. |
| `can_delete` | bool | Delete/archive inside this scope. |
| `can_approve` | bool | Approve/reject inside this scope. |
| `can_post` | bool | Post finance/accounting documents inside this scope. |
| `can_release` | bool | Release production/QC/etc. inside this scope. |
| `can_cancel` | bool | Cancel inside this scope. |
| `can_export` | bool | Export inside this scope. |
| `can_import` | bool | Import inside this scope. |
| `can_transfer` | bool | Transfer stock/assets/etc. inside this scope. |
| `can_adjust` | bool | Adjust stock/operational quantities inside this scope. |
| `can_receive` | bool | Receive into this scope. |
| `can_dispatch` | bool | Dispatch from this scope. |
| `is_active` | bool | Inactive scopes do not apply. |

Constraints:

- exactly one owner is required: either `user_id` or `role_id`, not both
- `scope_type` and `scope_id` are required
- unique owner/scope pair:
  - `(user_id, scope_type, scope_id)` for user scopes
  - `(role_id, scope_type, scope_id)` for role scopes

Indexes:

- `user_id`
- `role_id`
- `(scope_type, scope_id)`
- `(user_id, scope_type)`
- `(role_id, scope_type)`

## Effective Access Priority

1. `User.is_superuser` is full access.
2. A `*` permission or explicit all-level permission grants full permission for that action.
3. User-specific active `AccessScope` rows override role scopes for the same `scope_type` and `scope_id`.
4. Active role scopes apply when no user-specific override exists.
5. If no scope grants a mutation action, deny by default.
6. View permissions and mutation permissions are evaluated separately.

Important nuance:

- A user may have `inventory.view_all` and `inventory.edit_own_scope`.
- That means list/search may show all inventory records, but edit/adjust/receive/dispatch must pass the matching scope action.

## Backend Helper API

Create `backend/app/core/access_control.py` with pure and dependency-oriented helpers:

- `permission_code(module, action)`
- `get_effective_permission_codes(user)`
- `has_permission(user, permission)`
- `has_any_permission(user, permissions)`
- `get_effective_scopes(user, scope_type=None)`
- `can_perform_in_scope(user, scope_type, scope_id, action)`
- `can_view_scope(user, scope_type, scope_id)`
- `can_modify_scope(user, scope_type, scope_id, action)`
- `can_view_record(user, module, record)`
- `can_modify_record(user, module, action, record)`
- `require_any_permission(permissions)`
- `require_scoped_permission(permission_all, permission_scoped, scope_type, scope_id)`
- `require_record_access(module, action, record_loader)`
- `can_modify_by_status(module, action, status)`

Keep `backend/app/core/deps.py::require_permission` for existing endpoints, but delegate permission logic to the shared helper so behavior stays consistent.

## Record Scope Resolution

Create a central resolver map with conservative defaults. Initial mapping should support common fields without forcing every module to be refactored immediately.

| Module | Scope Resolution |
|---|---|
| `inventory` | `warehouse_id`, `source_warehouse_id`, `destination_warehouse_id`, then `branch_id`, `company_id`. |
| `warehouses` / `wms` | `warehouse_id`, `branch_id`, `company_id`. |
| `procurement` | `company_id`, `branch_id`, `department_id`, `supplier_category_id`, `product_category_id`. |
| `sales` / `crm` | `company_id`, `branch_id`, `sales_region_id`, `sales_team_id`, `customer_group_id`, `customer_id`. |
| `production` / `mrp` | `factory_id`, `production_line_id`, `branch_id`, `company_id`, `product_category_id`. |
| `quality` / `qms` | `factory_id`, `quality_lab_id`, `product_category_id`, `branch_id`, `company_id`. |
| `finance` | `company_id`, `branch_id`, `cost_center_id`. |
| `hr` / `payroll` | `company_id`, `branch_id`, `department_id`, `employee_department_id`. |
| `maintenance` / `utilities` / `iot` | `factory_id`, `machine_id`, `production_line_id`, `utility_area_id`, `branch_id`, `company_id`. |
| `admin` | `global`, `company_id`. |

If a record has no resolvable scope, mutation is denied unless the user has the corresponding `_all` permission or is superuser.

## Workflow Status Locking

Create `can_modify_by_status(module, action, status)` with a deny-by-default lock list:

- `POSTED`
- `CLOSED`
- `COMPLETED`
- `REVERSED`
- `CANCELLED`
- `LOCKED`

Module-specific rules can extend this:

- finance posted records cannot be edited directly
- production completed/closed orders are locked
- production released orders allow only limited non-core edits unless a special permission is added later
- quality released lots require controlled hold/reversal flows

## `/auth/me` Response

Preserve current fields and add optional effective access data:

```json
{
  "id": "...",
  "email": "user@example.com",
  "username": "user",
  "full_name": "User",
  "is_active": true,
  "is_superuser": false,
  "must_change_password": false,
  "roles": [],
  "permission_codes": [],
  "modules": [],
  "scopes": [],
  "feature_flags": {}
}
```

Scope item:

```json
{
  "scope_type": "warehouse",
  "scope_id": "...",
  "scope_name": "Nairobi Warehouse",
  "can_view": true,
  "can_edit": true,
  "can_adjust": true,
  "can_receive": true,
  "can_dispatch": true,
  "source": "role"
}
```

## Frontend Helper Direction

Extend `AuthContext` after backend payload exists:

- `hasPermission(permission)`
- `hasAnyPermission(permissions)`
- `hasModule(moduleKey)`
- `canViewScope(scopeType, scopeId)`
- `canEditScope(scopeType, scopeId)`
- `canPerformInScope(scopeType, scopeId, action)`
- `getFirstAllowedRoute()`

`localStorage` must not become the source of truth. The helpers should use the live `/auth/me` payload.

## Acceptance Result

This design supports the requested ERP-wide rule: broad view is separate from scoped mutation, with backend-authoritative checks and frontend UX helpers layered on top.
