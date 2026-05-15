# End-to-End Workflow Tests

## Purpose

The GAP-004 E2E suite verifies critical browser workflows for the FMCG ERP without adding test-only production endpoints or hardcoded credentials.

Current coverage starts with:

- public login page smoke checks
- unauthenticated protected-route redirect
- bad-login safe error behavior
- authenticated shell/sidebar smoke checks when credentials are provided
- critical module page smoke scaffolding for Inventory, Production, Quality, Finance, Procurement, and Sales
- scoped inventory UI markers when suitable stock data exists
- operational workflow controls for Production, Quality, Finance Accounting Controls, Procurement, and Sales Customers
- limited-role route-safety checks when limited E2E credentials are provided

The suite is designed to be safe for development databases. It must not reset data, delete records, or depend on production services.

## Local Prerequisites

Start the local development stack before running authenticated E2E tests:

```powershell
docker compose --env-file .env.development up -d db redis backend frontend
```

Public login-page checks can also run against a local frontend dev server:

```powershell
cd frontend
npm run dev
```

If the backend or frontend is already running, set `E2E_SKIP_WEBSERVER=1` before invoking Playwright so it does not start another frontend dev server.

## Environment Variables

| Variable | Purpose |
|---|---|
| `E2E_BASE_URL` | Frontend URL. Defaults to `http://localhost:3000`. |
| `E2E_API_URL` | Backend URL used by the Playwright web server env. Defaults to `http://localhost:8000`. |
| `NEXT_PUBLIC_API_URL` | Frontend API URL override. Defaults to `http://localhost:8000`. |
| `E2E_USERNAME` / `E2E_PASSWORD` | Default authenticated browser user. |
| `E2E_ADMIN_USERNAME` / `E2E_ADMIN_PASSWORD` | Admin-compatible user for full shell/module smoke checks. Falls back to `E2E_USERNAME` / `E2E_PASSWORD`. |
| `E2E_LIMITED_USERNAME` / `E2E_LIMITED_PASSWORD` | Limited role user for permission/scope browser smoke checks. |
| `E2E_SKIP_WEBSERVER` | Set to any value to prevent Playwright from starting `npm run dev`. |

Do not hardcode credentials in test files.

## Expected E2E Users

The current role contract is documented in `docs/planning/GAP-004_E2E_ROLE_EXPECTATIONS.md`.

Use these users when you want authenticated browser coverage:

- Admin-compatible user: `owner`, `admin`, or superuser-equivalent access with global scope.
- Limited warehouse user: `warehouse_manager` role with explicit editable scope for one warehouse and view-only scope for at least one other warehouse.
- Optional read-only auditor: `read_only_auditor` role with assigned view scopes and no mutation permissions.

If these users are not available, authenticated tests skip instead of guessing credentials or seeding unsafe users.

## Commands

From `frontend`:

```powershell
npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:ui
npm run test:e2e:report
```

List tests without launching a browser:

```powershell
npm run test:e2e -- --list
```

Run only public auth smoke:

```powershell
npm run test:e2e -- e2e/auth-public.spec.ts --project=chromium
```

Run the full suite without credentials:

```powershell
npm run test:e2e -- --project=chromium
```

Expected no-secret result is currently 3 passing public auth tests and the authenticated/data-dependent checks skipped.

Run the workflow-control tests with admin credentials:

```powershell
$env:E2E_ADMIN_USERNAME="..."
$env:E2E_ADMIN_PASSWORD="..."
npm run test:e2e -- e2e/workflow-controls.spec.ts --project=chromium
```

## Credential and Data Behavior

Tests that require login skip when the matching E2E credential variables are not set.

Data-dependent assertions do not reset or delete the development database. If suitable seeded data is missing, tests record a `missing-data` annotation instead of fabricating production records.

Credential-dependent tests currently cover:

- authenticated dashboard shell and sidebar rendering
- first allowed/admin route smoke checks
- inventory, production, quality, finance, procurement, and sales page-load checks
- inventory per-row action/view-only markers when stock rows exist
- limited-route safety for restricted users

## Stable Selectors

The E2E suite prefers semantic locators when they are stable. Minimal `data-testid` hooks are available for:

- `login-form`, `login-username`, `login-password`, `login-submit`, `login-error`
- `dashboard-shell`, `dashboard-main`
- `sidebar`, `sidebar-nav`, `sidebar-link-*`, `sidebar-section-*`, `sidebar-cluster-*`
- `access-denied`
- `inventory-page`, `inventory-stock-table`, `inventory-adjust-button`, `inventory-view-only-badge`
- `production-page`, `production-plan-list`, `production-create-plan-button`
- `quality-page`, `quality-inspection-list`, `quality-create-inspection-button`
- `finance-accounting-controls-page`, `finance-operational-posting-events`, `finance-create-*`
- `procurement-page`, `procurement-pr-list`, `procurement-create-pr-button`
- `sales-customers-page`, `sales-customers-list`, `sales-create-customer-button`

## Browser Installation

If Playwright reports that Chromium is missing:

```powershell
npx playwright install chromium
```

## Troubleshooting

### Backend Not Running

Start the dev stack:

```powershell
docker compose --env-file .env.development up -d db redis backend frontend
```

Then check:

```powershell
docker compose --env-file .env.development ps
```

### Frontend Not Running

From `frontend`, run:

```powershell
npm run dev
```

Or let Playwright start the dev server by leaving `E2E_SKIP_WEBSERVER` unset.

### Login Fails

Confirm the username/password are present in the environment and that the user is active. The app uses HttpOnly cookie auth, so tests should log in through the UI rather than injecting localStorage tokens.

### Authenticated Tests Skip

This is expected when `E2E_ADMIN_*`, `E2E_USERNAME`, or `E2E_LIMITED_*` variables are missing. Public tests should still run.

### Seed Data Missing

Data-dependent assertions should annotate missing data instead of failing. To increase coverage, create development users and records through normal admin flows or controlled development seed scripts.

### Browser Missing

Run:

```powershell
npx playwright install chromium
```

### Database Migration Missing

Run the live development migration flow before authenticated E2E checks:

```powershell
docker compose --env-file .env.development exec backend alembic upgrade head
```

Do not reset volumes or delete development data just to make E2E tests pass.
