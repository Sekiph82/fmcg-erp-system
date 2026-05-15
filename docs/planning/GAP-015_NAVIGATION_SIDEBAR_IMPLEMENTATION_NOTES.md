# GAP-015 UI/UX Navigation and Sidebar Implementation Notes

## Summary

GAP-015 fixed four surgical issues in the nav configuration that were identified during the audit: the warehouse section had no section-level permission guard, the admin section had no section-level permission guard, the report-builder section used the wrong permission domain (`analytics.view` instead of `reports.*`), and two tax section items bled into the finance domain. No backend changes were made.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Migration/Models/Schemas/Services/Endpoints/Permissions | All SKIPPED — navigation is frontend config only |
| Frontend nav-config | 4 surgical fixes in `nav-config.tsx` |
| Tests | Added `backend/tests/test_gap015_navigation_registry.py` (registry consistency); frontend type-check re-run |

---

## Changes Made

### `frontend/src/components/nav-config.tsx`

| Fix | Detail |
|---|---|
| Warehouse section | Added `permission: "inventory.view"` at section level — was missing entirely |
| Tax section | Changed 2 items (`eTIMS / e-Invoice`, `VAT Returns (VAT3)`) from `permission: "finance.view"` to `permission: "tax.view"` |
| Report-builder section | Changed section guard from `analytics.view` to `reports.view`; changed all 10 item permissions from `analytics.view` to appropriate `reports.*` codes (view/create/admin) |
| Admin section | Added `permission: "users.view"` at section level — was missing entirely |

---

## Tests

### `backend/tests/test_gap015_navigation_registry.py`

5 focused tests; no DB required.

| Test | Checks |
|---|---|
| `test_all_nav_permission_keys_exist_in_registry` | All MODULE_DEFINITIONS-sourced nav permission codes exist in `registry_permission_codes()` |
| `test_module_definitions_have_sidebar_groups` | Every module has a non-empty `sidebar_group` |
| `test_module_definitions_have_route_prefixes` | Every module route prefix starts with `/` |
| `test_no_duplicate_module_keys` | No two modules share the same key |
| `test_no_duplicate_route_prefixes` | No two modules share the same route prefix |

All 5 passed. Frontend type-check passed.

---

## Known Limitations / Out of Scope

| Area | Detail |
|---|---|
| 35+ still-orphaned routes | Routes like `approvals`, `portal`, `iot`, `shelf-life` etc. have no nav entry. Adding them would require creating new nav sections or expanding existing ones — a larger UX design decision beyond a surgical fix. |
| Marketing section fragmentation | 15 unique permission codes across marketing items. Consolidating would require a backend permission redesign. |
| `wms.view` / `audit.view` not in registry | These permissions are used in nav-config but their modules (`wms`, `audit`) are still in `ENDPOINT_ROUTE_DEFINITIONS` not `MODULE_DEFINITIONS`. They work because they're in `seed.py`, but they are not registered via `registry_permission_codes()`. These modules should be promoted in a future GAP. |
| Backend module ≠ nav section alignment | 20 MODULE_DEFINITIONS vs 68 nav sections. The nav is intentionally finer-grained. |
