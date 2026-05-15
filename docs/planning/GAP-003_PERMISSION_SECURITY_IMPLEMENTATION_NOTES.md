# GAP-003 Permission And Security Hardening Implementation Notes

## Task

`GAP-003K: Add or update documentation: Permission and Security Hardening Across All New Modules`

## Implemented Scope

This checkpoint hardens permission and module visibility behavior on top of the `GAP-SEC-001` access-control foundation.

Completed:

- Added `docs/planning/GAP-003_PERMISSION_SECURITY_SCHEMA_DESIGN.md`.
- Confirmed no new GAP-003 database migration is required.
- Skipped GAP-003C through GAP-003E because the schema/model/payload foundation already exists from GAP-SEC-001.
- Added backend scoped permission coverage helpers in `backend/app/core/module_registry.py`.
- Updated `/api/v1/modules/manifest` so scoped permissions such as `inventory.view_all` satisfy base module visibility such as `inventory.view`.
- Added protected admin coverage endpoint:
  - `GET /api/v1/modules/permissions/coverage`
  - permission: `roles.view`
- Added typed frontend client support in `frontend/src/lib/modules.ts`.
- Added registry coverage/drift summary to `frontend/src/app/dashboard/permissions/page.tsx`.
- Verified no new permission seed is needed because the coverage endpoint and Permission Matrix page already use `roles.view`.
- Added focused backend tests for scoped manifest visibility and permission coverage reporting.

## Security Behavior

The module manifest now uses the same principle as the frontend auth helpers:

- exact permission grants satisfy exact requirements
- scoped all/own grants can satisfy base visibility requirements
- broad view does not imply broad mutation
- mutation still depends on backend route checks and AccessScope rules

Example:

- A user with `inventory.view_all` can see the Inventory module in the backend manifest.
- That same user still cannot adjust stock unless they also have an appropriate mutation permission and matching warehouse scope.

## Admin Permission Coverage Endpoint

`GET /api/v1/modules/permissions/coverage` returns:

- `registry_permission_count`
- `database_permission_count`
- `covered_registry_permissions`
- `missing_registry_permissions`
- `database_only_permissions`

Use this endpoint to identify registry/database permission drift before migrating more frontend navigation to backend-owned module metadata.

## Frontend Behavior

The Permission Matrix page now shows:

- registry permission count
- database permission count
- registry permissions covered by exact/scoped grants
- missing registry permissions
- database-only permissions

This is intentionally an admin review surface, not a permission editor rewrite.

## Checks Run

Passed:

- Backend py_compile:
  - `app/core/module_registry.py`
  - `app/api/v1/endpoints/modules.py`
- Focused backend tests:
  - module manifest registry consistency
  - user permission filtering
  - scoped permission visibility
  - permission coverage report
  - permission coverage endpoint
- GAP-SEC-001 access-control regression tests.
- RBAC attack-simulation regression tests.
- Frontend type-check with `npm.cmd run type-check`.

## Remaining Follow-Up

Still required in later hardening slices:

- Expand backend module registry coverage beyond the current core modules.
- Add automated frontend nav permission extraction/validation against backend-known permission codes.
- Add route-dependency audit tests for more high-risk routers.
- Migrate more sidebar/nav behavior to backend-owned module manifest metadata.
- Add a friendlier permission debugger for admins.
- Add row-level permission hints to more operational list APIs.

## Acceptance Result

`GAP-003K` is complete when this documentation is recorded and `TASKS.md` points to `GAP-003L` for final checks and checkpoint recording.

