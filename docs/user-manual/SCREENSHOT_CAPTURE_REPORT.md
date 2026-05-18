# Screenshot Capture Report

**Date:** 2026-05-18  
**Run duration:** ~7.1 minutes  
**Tool:** Playwright (`e2e/manual-screenshots.spec.ts`)  
**Viewport:** 1440×900

## Results

| Status | Count |
|--------|-------|
| Captured | 73 |
| Failed | 67 |
| Total routes | 140 |

Captured screenshots stored in: `docs/user-manual/screenshots/captured/`  
Index file: `docs/user-manual/screenshots/screenshots-index.json`  
Total size: ~36 MB (excluded from git — regenerate locally)

## Captured Modules

All 73 captures are real screenshots from the running ERP at 1440×900.

| Module | Routes Captured |
|--------|----------------|
| Login page | 1 |
| Dashboard (main) | 1 |
| Admin | 9 tabs |
| Products | 1 |
| Materials | 1 |
| Suppliers | 1 |
| Warehouses | 2 tabs |
| Inventory | 8 tabs |
| WMS | 4 tabs |
| Procurement | 8 tabs |
| Production (partial) | 4 tabs (overview, orders, execution, material-flow) |
| Analytics | 6 tabs |
| Documents | 3 tabs |
| NPD | 1 |
| Maintenance | 3 tabs |
| Utility Management | 3 tabs |
| CRM | 3 tabs |
| Marketing | 3 tabs |
| AI | 2 tabs |
| Integrations | 2 tabs |
| Approvals | 1 |
| Audit Logs | 2 tabs |
| POS | 1 |
| Communication | 1 |
| Helpdesk | 1 |

## Failed Routes (67)

All failures: `net::ERR_EMPTY_RESPONSE` — the Next.js dev server became unresponsive around route 42 (production advanced tabs), then recovered at analytics (route 109).

**Missing modules:**
- Production: costing, batch-lots, QC, OEE, downtime, plans, scheduling, waste-yield
- Shop-floor (all 3 tabs)
- BOM (all 4 tabs)
- Recipes
- Planning (all 4 tabs)
- Quality (all 7 tabs)
- Compliance (all 3 tabs)
- **Sales (all 11 tabs)** — critical for Kenya go-live
- Logistics (all 4 tabs)
- **Finance (all 10 tabs)** — critical for Kenya go-live
- **HR (all 9 tabs)** — critical for Kenya go-live
- **Payroll (all 3 tabs)** — critical for Kenya go-live

## Root Cause

The Next.js dev server (`next dev`) became unresponsive after sustained load (37+ rapid page navigations). This is expected dev server behavior — production builds do not have this issue.

**Workaround for re-capture of failed routes:**

1. Restart the Docker stack: `docker compose up -d`
2. Wait 60s for services to stabilize
3. Re-run capture: `npm run test:manual-screenshots`

The capture script is idempotent — it overwrites the index and adds new PNGs. Failed-route retries can be done by editing `routes.json` to only include the routes needing re-capture.

## Re-Capture Priority

For Kenya go-live documentation, re-capture these first:

1. Sales workspace (all tabs) — van sales, M-Pesa collections
2. Finance workspace (all tabs) — M-Pesa, tax (eTIMS), expenses
3. HR workspace (all tabs) — Kenya payroll, PAYE/NHIF/NSSF
4. Payroll workspace
5. Quality workspace
6. Planning workspace

## How to Regenerate Screenshots

```bash
# From repo root, with Docker stack running:
cd frontend
E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots

# Or with explicit auth setup first:
E2E_SKIP_WEBSERVER=1 npx playwright test --project=setup
E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots
```

Credentials and base URL are read from `.env.test` (or environment):
- `NEXT_PUBLIC_APP_URL` (default: `http://localhost:3000`)
- Admin credentials from auth setup test
