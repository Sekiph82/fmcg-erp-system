# GAP-004 End-to-End Workflow Completion Testing Audit

## Task

`GAP-004A: Audit current implementation: End-to-End Workflow Completion Testing`

This is an audit-only checkpoint. No application behavior was changed for GAP-004A.

## Planning Requirement

The ERP needs end-to-end workflow tests for real business journeys, not only isolated unit checks.

Critical journeys should cover:

- login and authenticated `/auth/me`
- role-based navigation visibility
- inventory stock movement flows
- procurement request to purchase order flow
- goods receipt / stock impact readiness
- production order lifecycle
- quality inspection and lot release/hold readiness
- finance/accounting posting controls
- cross-module posting integration readiness
- unauthorized direct URL/API access
- startup smoke from Docker Compose

## Current Coverage Summary

| Area | Current Status | Evidence | Notes |
|---|---|---|---|
| Backend unit/security tests | Existing | `backend/tests/test_security.py`, `backend/tests/test_attack_simulation.py`, `backend/tests/test_hardening.py` | Good coverage for password policy, login limiter, blocklist, sanitization, business guards, RBAC controls, cookies, production config, AI validation, and module metadata. |
| GAP-focused backend tests | Existing | `test_gap001_accounting_core.py`, `test_gap002_posting_integration.py`, `test_gap_sec001_access_control.py` | Strong focused tests for accounting foundation, posting integration helpers, and scoped access-control helpers. |
| Load/performance simulation | Existing | `backend/tests/test_load_simulation.py` | Covers limiter/blocklist/sanitizer/AI guard throughput, but not full ERP user journeys. |
| Frontend type checking | Existing | `frontend/package.json` `type-check` | TypeScript compile coverage exists. No React component/unit test runner was discovered. |
| Browser screenshot automation | Partial | `frontend/scripts/capture-user-manual-screenshots.mjs`, `docs/user-manual/screenshots/routes.json` | Can log in and capture pages when credentials and live services exist. It is not an assertion-based E2E test suite. |
| Local smoke docs | Existing | `README.md` smoke checks | Documents backend import, health, login page, and bad-login `401` checks. |
| Docker health checks | Existing | `docker-compose.yml` | Backend, frontend, DB, and Redis health checks exist. |
| CI backend checks | Existing | `.github/workflows/ci.yml` | Runs compile, import, Alembic upgrade, and pytest against PostgreSQL/Redis services. |
| CI frontend checks | Existing | `.github/workflows/ci.yml` | Runs npm audit, type-check, and production build. |
| CI browser E2E | Missing | `.github/workflows/ci.yml` | No Playwright/Cypress workflow was found for actual ERP journeys. |
| API workflow integration tests | Partial / missing | `backend/tests` | Existing tests are mostly unit/service/security contracts. No full request chain through FastAPI + DB for procurement to stock to finance posting was found. |
| Seeded E2E fixtures | Missing | `demo-data`, backend fixtures | Test payload helpers exist, but no stable end-to-end fixture package for cross-module workflows was found. |

## Files Audited

| File or Folder | What Was Checked |
|---|---|
| `backend/tests` | Available pytest coverage and test categories. |
| `backend/tests/fixtures.py` | Existing payload helpers and assertion helpers. |
| `frontend/package.json` | Available frontend scripts and Playwright dependency. |
| `frontend/scripts/capture-user-manual-screenshots.mjs` | Whether screenshot automation can act as E2E coverage. |
| `docs/user-manual/screenshots/routes.json` | Manual route manifest coverage. |
| `.github/workflows/ci.yml` | CI coverage for backend, frontend, Docker config, DB, and Redis. |
| `README.md` | Local startup and smoke-check instructions. |
| `docker-compose.yml` | Service health checks. |
| `start-dev.bat` | Local startup readiness behavior. |

## Strengths

- CI already has PostgreSQL and Redis services for backend checks.
- Alembic upgrade runs in CI.
- Backend compile/import and pytest run in CI.
- Frontend type-check and build run in CI.
- Docker Compose has health checks.
- Manual screenshot automation has a route manifest and login flow.
- Recent security/access-control work has focused helper and regression tests.

## Gaps And Risks

| Gap | Risk | Recommended Next Step |
|---|---|---|
| No browser E2E suite | Frontend pages can compile but fail at runtime after login or route navigation. | Add Playwright assertion tests for login, dashboard, sidebar visibility, and a few high-risk module pages. |
| No cross-module API workflow tests | Procurement, inventory, production, quality, and finance can regress independently. | Add backend integration tests using FastAPI client + test DB fixtures for representative workflows. |
| Screenshot automation is not assertion-based | Screenshots can be captured even if business behavior is broken. | Keep screenshots for manuals, add separate Playwright E2E assertions. |
| No stable E2E fixture pack | Tests may be brittle or hard to repeat. | Create deterministic seed/fixture helpers for company, branch, warehouse, product, supplier, customer, production order, QC lot, and journal scenarios. |
| Role-based UI not fully tested in browser | Sidebar/action hiding can drift from `/auth/me` permissions. | Add Playwright tests for admin, scoped manager, and read-only auditor personas. |
| Startup smoke checks are documented but not CI-executed against Compose | Local startup can regress without CI noticing full service readiness. | Add a CI/manual script for `docker compose config` plus optional health smoke when feasible. |
| Cross-module posting remains foundation-only | Automatic operational posting paths are not yet wired end to end. | Design tests now as pending workflow contracts, then enable as modules are wired. |

## Recommended E2E Workflow Set

Minimum useful set for the next design step:

| Workflow ID | Journey | Test Layer |
|---|---|---|
| E2E-AUTH-001 | Login, `/auth/me`, logout, bad login `401` | API + browser |
| E2E-RBAC-001 | Admin sees admin nav; scoped manager sees only allowed modules | Browser |
| E2E-INVENTORY-001 | Create stock movement and verify stock balance/movement history | API integration |
| E2E-PROC-001 | Purchase request to purchase order lifecycle | API integration |
| E2E-PROD-001 | Production order create, release, start, complete, stock impact readiness | API integration |
| E2E-QA-001 | QC inspection create, result entry, approval/release denial outside scope | API integration |
| E2E-FIN-001 | Journal validation/post/reversal with locked-status rules | API integration |
| E2E-POSTING-001 | Operational posting event/link idempotency contract | API integration |
| E2E-UI-001 | Critical dashboard pages load without fatal console/API errors | Browser |

## Acceptance Criteria Result

`GAP-004A` is complete when this audit is recorded and the next design task can define the E2E test architecture without changing application behavior.

