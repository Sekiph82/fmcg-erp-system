# GAP-003 Permission And Security Hardening Schema Design

## Task

`GAP-003B: Design data model/schema: Permission and Security Hardening Across All New Modules`

## Context

`GAP-SEC-001` was inserted before this task as the foundational ERP-wide access-control implementation. That work added the schema and helper layer needed for broad view access plus scoped mutation access:

- `Permission.is_active`
- `Role.is_system_role`
- `AccessScope`
- role-owned and user-owned scope assignments
- effective permissions/modules/scopes in `/api/v1/auth/me`
- centralized helpers in `backend/app/core/access_control.py`
- first-pass scoped enforcement in inventory, production, sales, procurement, quality, finance journals, and admin scope APIs

Therefore `GAP-003` must not create a second permission architecture. It should harden coverage, validation, tests, and UX on top of the existing `Permission`, `Role`, `AccessScope`, module registry, and auth context foundations.

## Schema Decision

No additional database migration is required for `GAP-003`.

The active schema foundation is sufficient for the remaining hardening slice:

| Requirement | Existing Foundation | Decision |
|---|---|---|
| Active/inactive permissions | `Permission.is_active` | Reuse. |
| System role marker | `Role.is_system_role` | Reuse. |
| User-specific access overrides | `AccessScope.user_id` | Reuse. |
| Role default scopes | `AccessScope.role_id` | Reuse. |
| View vs mutation scope flags | `AccessScope.can_view`, `can_edit`, `can_approve`, `can_post`, `can_release`, etc. | Reuse. |
| Effective access payload | `/api/v1/auth/me` modules/scopes/feature flags | Reuse and test. |
| Module permission source of truth | `backend/app/core/module_registry.py` plus seed permissions | Extend metadata and validation, not schema. |
| Frontend role-aware navigation | local nav config plus backend manifest integration | Validate and migrate incrementally, not schema. |

## Remaining Hardening Design

The next implementation tasks should focus on non-schema hardening:

1. Add route-permission audit tests for high-risk routers.
2. Validate frontend nav permissions against backend registry and seeded permission codes.
3. Expand backend module registry coverage for high-risk endpoint groups before migrating the full sidebar.
4. Preserve cookie-only auth and test logout/cookie revocation behavior.
5. Add consistent forbidden response expectations for protected mutation routes.
6. Extend action-level frontend checks where buttons/forms still assume module-level access.
7. Document remaining endpoint groups that need scoped enforcement after the first-pass `GAP-SEC-001` rollout.

## Migration Decision

`GAP-003C` should be marked `SKIPPED`.

Reason: database changes for this security hardening gap were already implemented by `GAP-SEC-001C` and `20260511_0040_finance_journal_scopes`. Adding another migration now would duplicate architecture rather than improve coverage.

## Model Decision

`GAP-003D` should be marked `SKIPPED`.

Reason: ORM model changes were already implemented by `GAP-SEC-001D` and the finance journal scope model update. Remaining GAP-003 work is validation, endpoint coverage, frontend behavior, tests, and docs.

## Schema/Payload Decision

`GAP-003E` should be marked `SKIPPED` unless a later route-specific payload gap is discovered.

Reason: the effective access payload and scope assignment schemas already exist. GAP-003 should add tests around those schemas rather than introduce new response contracts.

## Acceptance Criteria Result

`GAP-003B` is complete when this design is recorded and the task queue points to the next meaningful implementation task: `GAP-003F`, service/helper hardening and route-permission validation logic.

