# GAP-SEC-001 ERP-wide Permission + Scope-Based Access Control Audit

## Task

`GAP-SEC-001A: Audit current implementation: ERP-wide permission + scope-based access control`

This audit records the existing security foundation before adding the ERP-wide scope layer.

## Required Access-Control Direction

The ERP must separate broad visibility from scoped mutation:

- a user may view global or company-wide data when they have a broad view permission
- create, edit, delete, approve, post, release, receive, dispatch, adjust, import, and export actions must be restricted by permission plus operational scope
- workflow status must also lock protected records when appropriate
- backend checks are authoritative; frontend checks improve UX only
- super admin bypass must remain explicit
- deny by default for mutation when no matching scope exists

## Current Implementation Summary

| Area | Current Status | Evidence | Notes |
|---|---|---|---|
| Cookie authentication | Existing | `backend/app/core/deps.py::get_current_user` | Reads only the auth cookie, rejects blocklisted tokens, validates active users. |
| Role-based permissions | Existing | `backend/app/models/role.py`, `backend/app/core/deps.py::require_permission` | Permissions use `module.action` strings. Superusers bypass. |
| User-role assignment | Existing | `backend/app/models/user.py::user_role` | Many-to-many user-role table is already in place. |
| Role-permission assignment | Existing | `backend/app/models/role.py::role_permission` | Many-to-many role-permission table is already in place. |
| Permission active flag | Missing | `Permission` model | Role active state exists, but individual permission activation is not modeled. Existing checks only filter active roles. |
| Generic operational scopes | Missing | No `AccessScope` model found | `UserCompanyAccess` exists for company access, but it is not a generic mutation/view scope system. |
| Company and branch models | Existing | `backend/app/models/company.py` | Company/branch records exist and can be used by scope resolution. |
| Warehouse model | Existing | `backend/app/models/master.py::Warehouse` | Warehouses exist but are not linked to the current RBAC system. |
| Frontend auth permissions | Existing / simple | `frontend/src/context/AuthContext.tsx` | Exposes `hasPermission(code)` only; no scope helpers yet. |
| `/auth/me` payload | Existing / limited | `backend/app/api/v1/endpoints/auth.py` | Returns `UserRead` with roles and computed `permission_codes`; no effective scopes/modules/feature flags. |
| Sidebar filtering | Existing / permission-only | `frontend/src/components/Sidebar.tsx` | Hides entries by permission string but cannot distinguish broad view from scoped mutation. |

## Existing Model Notes

### Permission

Current fields:

- `id`
- `code`
- `name`
- `description`
- `module`
- `action`
- `is_mobile_visible`

The current `code` field can support the requested `module.action.scope_level` format without a destructive schema change. For example:

- `inventory.view_all`
- `inventory.view_own_scope`
- `inventory.edit_all`
- `inventory.edit_own_scope`

The matching `module` remains `inventory`; the `action` should store the full action segment such as `view_all` or `edit_own_scope`.

### Role

Current fields:

- `id`
- `name`
- `description`
- `is_active`
- `permissions`
- `users`

The model is suitable for scope extension through a related generic `AccessScope` table.

### User

Current fields:

- `id`
- `email`
- `username`
- `full_name`
- `hashed_password`
- `is_active`
- `is_superuser`
- `must_change_password`
- `roles`

The model is suitable for user-specific scope overrides through a related generic `AccessScope` table.

### Existing Company Access

`UserCompanyAccess` grants company access with a simple company role. It should not be removed. It can coexist as an older company-access feature while GAP-SEC-001 introduces the generic cross-module scope layer.

## Gaps To Close

| Gap | Why It Matters | GAP-SEC-001 Response |
|---|---|---|
| No generic access scope model | Cannot express "view all but edit Nairobi warehouse only" in current RBAC. | Add `AccessScope` with role-owned and user-owned scopes plus action booleans. |
| No scope-aware auth payload | Frontend cannot decide view-only row UX or scoped buttons. | Extend `/auth/me` response with effective scopes, modules, and feature flags while preserving `permission_codes`. |
| Permission helper is binary | `require_permission("inventory", "edit")` cannot check warehouse/branch/factory scope. | Add central access-control helpers and keep existing `require_permission` compatibility. |
| No record scope resolver | Endpoints would duplicate logic for warehouse/company/factory fields. | Add central resolver definitions per module/record shape. |
| No workflow status lock helper | Posted/closed/released records can be inconsistently protected. | Add `can_modify_by_status(module, action, status)`. |
| Frontend has permission-only helpers | UI cannot show row-level "View only" or scoped mutation buttons. | Add scope helpers to auth context after backend payload exists. |

## Implementation Slice Order

1. Add generic `AccessScope` migration and ORM relationships.
2. Add access schemas for `/auth/me` and future admin APIs.
3. Add centralized backend helper/service layer.
4. Extend `/auth/me` with effective permissions/scopes/modules.
5. Add focused tests for permission and scope behavior.
6. Apply enforcement to critical modules in small follow-up slices.
7. Update frontend helpers and sidebar/action UX.
8. Add seed permissions/roles/scopes and admin UI.

## GAP-SEC-001A Result

The existing system has a solid role/permission base but lacks the generic ERP-wide operational scope layer. The next implementation step is an additive schema design and migration for `AccessScope`; no current auth behavior should be broken.
