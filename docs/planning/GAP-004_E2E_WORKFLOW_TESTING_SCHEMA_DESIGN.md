# GAP-004 End-to-End Workflow Testing Schema Design

## Task

`GAP-004B: Design data model/schema: End-to-End Workflow Completion Testing`

## Design Decision

No application database migration is required for GAP-004.

End-to-end workflow testing should use deterministic test fixtures, API/browser harnesses, and isolated test database setup. It should not add new ERP business tables only to make tests easier.

## Test Architecture

Use two complementary layers:

| Layer | Purpose | Tooling |
|---|---|---|
| Backend API workflow tests | Exercise real FastAPI routes, auth, DB state, permissions, and workflow transitions. | `pytest`, `httpx`/FastAPI async client, PostgreSQL test database, Redis where needed. |
| Browser workflow tests | Exercise login, route guards, sidebar visibility, page load, and critical form/action UX. | Playwright under `frontend`, separate from manual screenshot capture. |

Screenshot automation remains for user manual assets only. It should not be treated as a pass/fail E2E suite.

## Fixture Data Contract

Create reusable deterministic fixture builders in test code, not production code.

Recommended fixture entities:

| Fixture | Minimum Fields |
|---|---|
| Company | `id`, `name`, active status |
| Branch | `id`, `company_id`, `name` |
| Warehouse | `id`, `branch_id`, `name` |
| Product/SKU | `id`, `sku`, `name`, `category`, UOM |
| Supplier | `id`, `name`, active status |
| Customer | `id`, `name`, `region`, active status |
| User/Role | role permissions, access scopes, active status |
| Stock | product, warehouse, quantity, batch/lot if supported |
| Purchase Request / PO | department/company/branch scope, status |
| Production Order | warehouse/factory-ready scope, product, quantity, status |
| QC Inspection | warehouse/product-category scope, status, result readiness |
| Journal Entry | company/branch/cost-center scope, balanced lines, posting status |

## Workflow Contracts

Initial workflow tests should be small and deterministic:

| Workflow ID | Contract |
|---|---|
| `E2E-AUTH-001` | Bad login returns `401`; valid login sets cookie; `/auth/me` returns user/effective access; logout clears auth. |
| `E2E-RBAC-001` | Admin sees admin modules; scoped manager sees allowed modules; unauthorized direct URL/API returns safe denial. |
| `E2E-INVENTORY-001` | Stock movement creates movement history and respects warehouse scope. |
| `E2E-PROC-001` | Purchase request can move through submit/approve/convert readiness with department/company scope checks. |
| `E2E-PROD-001` | Production order lifecycle rejects unauthorized release and locked-status edits. |
| `E2E-QA-001` | QC release/hold actions require matching quality permission and scope. |
| `E2E-FIN-001` | Journal validation/post/reversal uses balanced lines, scope checks, and locked-status rules. |
| `E2E-UI-001` | Login, dashboard, Permission Matrix, Inventory, Production, Quality, Finance, and Admin pages render without fatal errors for a permitted user. |

## Files To Add Later

No files are added in this design task except this document.

Likely implementation files for later GAP-004 subtasks:

- `backend/tests/e2e/conftest.py`
- `backend/tests/e2e/test_auth_rbac_workflow.py`
- `backend/tests/e2e/test_inventory_finance_workflow.py`
- `backend/tests/e2e/test_production_quality_workflow.py`
- `frontend/playwright.config.ts`
- `frontend/e2e/auth-rbac.spec.ts`
- `frontend/e2e/critical-pages.spec.ts`
- optional `docs/testing/E2E_WORKFLOWS.md`

## Skip Decisions

`GAP-004C`, `GAP-004D`, and `GAP-004E` should be marked `SKIPPED` for the current slice.

Reason:

- no new ERP database migration is needed
- no new production ORM model is needed
- no new production API schema is needed

The next meaningful implementation work is test harness/service-layer setup: fixture builders, authenticated client helpers, and workflow assertions.

## Acceptance Criteria Result

`GAP-004B` is complete when this design is recorded and the queue moves to the next meaningful implementation task after the skipped schema/model subtasks.

