# User Manual Screenshot Capture

This folder stores screenshot capture inputs and outputs for the FMCG ERP user manual.

## Start The ERP

From the repository root, start the local development environment:

```powershell
.\start-dev.bat
```

Or start services manually:

```powershell
docker compose --env-file .env.development up --build
```

Confirm these pages respond before running screenshots:

- `http://localhost:3000/login`
- `http://localhost:8000/health`

## Required Environment Variables

The screenshot crawler does not hardcode credentials.

```powershell
$env:MANUAL_TEST_BASE_URL = "http://localhost:3000"
$env:MANUAL_TEST_USERNAME = "<username>"
$env:MANUAL_TEST_PASSWORD = "<password>"
```

`MANUAL_TEST_BASE_URL` defaults to `http://localhost:3000` if omitted. Username and password are required.

## Run Screenshot Capture

```powershell
cd frontend
npm run manual:screenshots
```

The crawler logs in, visits routes from `routes.json`, captures full-page screenshots, extracts visible read-only action labels, and writes results to `screenshots-index.json`.

## Files

- `routes.json`: route manifest used by the crawler.
- `screenshots-index.json`: capture result index with `captured`, `failed`, or `skipped` status.
- `{module-slug}/{route-slug}.png`: screenshot files created by the crawler.

## Route Maintenance

`routes.json` is initially generated from `frontend/src/components/nav-config.tsx`. Add missing routes manually using this shape:

```json
{
  "id": "inventory-products",
  "title": "Products",
  "module": "Inventory",
  "path": "/dashboard/products",
  "priority": "core",
  "capture": true,
  "permission": "products.view"
}
```

Set `capture` to `false` for routes that are intentionally excluded or unsafe.

## Read-Only Safety Rules

The crawler must not create, edit, delete, approve, reject, submit, send, pay, recall, or mutate ERP data. It only opens pages, reads visible actions, and captures screenshots after login.

## Troubleshooting

- Missing credentials: set `MANUAL_TEST_USERNAME` and `MANUAL_TEST_PASSWORD`.
- Login fails: verify the user can sign in manually at `/login`.
- Frontend unavailable: run `start-dev.bat` and confirm `http://localhost:3000/login`.
- Backend unavailable: confirm `http://localhost:8000/health`.
- Individual route fails: review the route's `error` field in `screenshots-index.json`.
- Empty/detail pages: seed/demo data may be missing; do not create data from the crawler.

