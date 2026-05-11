# GAP-003 Permission And Security Hardening Audit

## Task

`GAP-003A: Audit current implementation: Permission and Security Hardening Across All New Modules`

This is an audit-only checkpoint. No security behavior was changed for GAP-003A.

## Planning Requirement

New and existing modules must be protected consistently:

- backend routes must enforce permissions for privileged actions
- frontend navigation and action buttons should hide inaccessible areas
- role templates must include required permissions without over-granting risky actions
- module registry permissions should be the source of truth where practical
- authentication must remain cookie-based and production-safe
- newly added finance/accounting controls must not expose unsafe automatic posting

## Current Implementation Summary

| Area | Current Status | Evidence | Notes |
|---|---|---|---|
| Authentication dependency | Existing | `backend/app/core/deps.py::get_current_user` | Reads `settings.AUTH_COOKIE_NAME` from HttpOnly cookie path and rejects blocklisted tokens. No bearer fallback is present in the inspected dependency. |
| RBAC dependency | Existing | `backend/app/core/deps.py::require_permission` | Superusers pass; non-superusers need `{module}.{action}` from active role permissions. |
| Core module registry | Partial | `backend/app/core/module_registry.py` | Registry defines core modules and permission actions, including `finance.configure`. It does not yet cover the full large endpoint surface. |
| Endpoint route registry | Partial | `ENDPOINT_ROUTE_DEFINITIONS` in `module_registry.py` | Many routes are registered as endpoints without corresponding `ModuleDefinition` permission actions. This is useful for startup but not yet a full permission source of truth. |
| Seed permissions and roles | Partial / strong for core finance | `backend/app/db/seed.py` | `finance.configure` exists and CFO/finance manager roles include it. Many non-core module permissions still appear manually maintained. |
| Frontend sidebar visibility | Existing / local | `frontend/src/components/Sidebar.tsx`, `frontend/src/components/nav-config.tsx` | Sidebar filters entries by local permission strings. It is role-aware, but still frontend-owned rather than fully backend-manifest-owned. |
| Backend-owned module manifest | Partial | module registry and modules endpoint from previous hardening work | Manifest foundation exists, but frontend navigation still has many permissions not fully represented by backend `ModuleDefinition` entries. |
| GAP-001 finance controls | Existing | Finance endpoints and Accounting Controls UI | Uses `finance.view`, `finance.create`, `finance.approve`, and `finance.configure`. |
| GAP-002 posting integration controls | Existing / safe | Finance endpoints added in GAP-002 | Audit reads use `finance.view`; account mapping writes use `finance.configure`; no unsafe execute endpoint was added. |

## Files Audited

| File | What Was Checked |
|---|---|
| `backend/app/core/deps.py` | Cookie auth, token blocklist, active user check, RBAC permission dependency. |
| `backend/app/core/module_registry.py` | Core module definitions, permission action lists, endpoint route definitions, finance `configure` permission. |
| `backend/app/db/seed.py` | Permission definitions and role templates for CFO and finance manager. |
| `backend/app/api/v1/endpoints/finance.py` | Recently added GAP-001/GAP-002 endpoint permissions. |
| `frontend/src/components/Sidebar.tsx` | Permission filtering for sections/items. |
| `frontend/src/components/nav-config.tsx` | Frontend-owned permission strings and nav structure. |
| `frontend/src/lib/modules.ts` | Backend manifest integration surface. |

## Strengths

- Backend permission checks are centralized through `require_permission`.
- Superuser bypass is explicit and simple.
- Role permissions are loaded with users through relationships in the auth dependency.
- Cookie auth is currently enforced by `get_current_user`.
- Sidebar entries are filtered before rendering, so users do not see every item if their role lacks the permission.
- Finance configuration permissions already protect fiscal years, posting rules, and GAP-002 inventory account mapping writes.
- GAP-002 avoided adding a high-risk "execute posting now" endpoint.

## Risks And Gaps

| Gap | Risk | Recommended Next Step |
|---|---|---|
| Registry does not cover full endpoint surface | New module routes can exist without registry-owned permission metadata. | Expand registry coverage or add automated route-permission audit tests. |
| Frontend nav is still locally owned | Frontend permission strings can drift from backend registry/seed permissions. | Validate every nav permission against backend permissions, then migrate to `/api/v1/modules/manifest`. |
| Seed role matrix remains manually maintained | Roles can become over-broad or miss new actions. | Generate core permission templates from registry, with explicit overrides for special modules. |
| Endpoint permission coverage is not automatically audited | A route can be added without `require_permission`. | Add tests that inspect route dependencies for selected high-risk routers. |
| Non-core endpoints outnumber module definitions | Many endpoint routes are startup-registered but not module-permission-defined. | Add `ModuleDefinition` or permission metadata for high-risk endpoint groups first. |
| Frontend action buttons may not all be permission-aware | Sidebar hiding does not guarantee create/edit/delete button hiding. | Audit common action components and module pages for action-level permission checks. |
| Cookie auth requires broad test coverage | Cookie-only auth is good, but regressions would lock users out or weaken auth. | Expand auth tests around cookie success/failure/logout and revoked tokens. |

## GAP-001/GAP-002 Permission Review

| Surface | Current Permission | Result |
|---|---|---|
| Fiscal year creation | `finance.configure` | Appropriate. |
| Posting rule creation | `finance.configure` | Appropriate. |
| Posting batch list | `finance.view` | Appropriate. |
| Operational posting event list/detail | `finance.view` | Appropriate for audit reads. |
| Inventory account mapping list | `finance.view` | Appropriate. |
| Inventory account mapping create/update | `finance.configure` | Appropriate. |
| Automatic GL posting execution | Not exposed | Appropriate for current foundation stage. |

## Acceptance Criteria Result

`GAP-003A` is complete when this audit is recorded and the next design task can use it to decide what to implement.

No code, schema, service, API, frontend, or seed behavior was changed in this audit step.

