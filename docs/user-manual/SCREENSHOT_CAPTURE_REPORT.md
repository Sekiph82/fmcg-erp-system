# Screenshot Capture Report

**Date:** 2026-05-19  
**Status:** COMPLETE — 140/140 routes captured

---

## Run History

### Run 1 (2026-05-18) — PARTIAL
- Tool: `frontend/e2e/manual-screenshots.spec.ts` (v1)
- Viewport: 1440×900, Docker frontend: 1G memory
- Result: **73/140 captured**, 67 failed
- Root cause: Next.js dev server OOM at route 38 (production workspace). ERR_EMPTY_RESPONSE.
- Recovery: Server restarted, captured analytics/docs/maintenance/CRM/marketing/AI clusters (routes 109–140)

### Run 2 (2026-05-19) — COMPLETE
- Tool: `frontend/e2e/manual-screenshots.spec.ts` (v2 — failed-only mode)
- Viewport: 1440×900, Docker frontend: **2G memory** (increased from 1G)
- Command: `MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots`
- Result: **67/67 failed routes recaptured successfully, 0 failures**
- Total after merge: **140/140 captured**
- Duration: 8.5 minutes (2.0m setup/warmup + 6.4m capture)

---

## Final Results

| Metric | Count |
|--------|-------|
| Total routes (capture=true) | 140 |
| Captured | **140** |
| Failed | 0 |
| capture=false (skipped) | 1 (`/dashboard/admin?tab=security` — covered by `admin-security`) |
| PNG files | 140 |
| Total size | ~70 MB (gitignored — regenerate locally) |

---

## Captured Modules (All)

| Module | Routes | Status |
|--------|--------|--------|
| Login | 1 | ✅ Captured |
| Dashboard | 1 | ✅ Captured |
| Admin (all 8 tabs) | 9 | ✅ Captured |
| Products / Materials / Suppliers | 3 | ✅ Captured |
| Warehouses (2 tabs) | 2 | ✅ Captured |
| Inventory (8 tabs) | 8 | ✅ Captured |
| WMS (4 tabs) | 4 | ✅ Captured |
| Procurement (8 tabs) | 8 | ✅ Captured |
| Production (12 tabs) | 12 | ✅ Captured |
| Shop-floor (3 tabs) | 3 | ✅ Captured |
| BOM (4 tabs) | 4 | ✅ Captured |
| Recipes | 1 | ✅ Captured |
| Planning (4 tabs) | 4 | ✅ Captured |
| Quality (7 tabs) | 7 | ✅ Captured |
| Compliance (3 tabs) | 3 | ✅ Captured |
| **Sales (11 tabs)** | 11 | ✅ Captured |
| Logistics (4 tabs) | 4 | ✅ Captured |
| **Finance (10 tabs)** | 10 | ✅ Captured |
| **HR (9 tabs)** | 9 | ✅ Captured |
| **Payroll (3 tabs)** | 3 | ✅ Captured |
| Analytics (6 tabs) | 6 | ✅ Captured |
| Documents (3 tabs) | 3 | ✅ Captured |
| NPD | 1 | ✅ Captured |
| Maintenance (3 tabs) | 3 | ✅ Captured |
| Utility Management (3 tabs) | 3 | ✅ Captured |
| CRM (3 tabs) | 3 | ✅ Captured |
| Marketing (3 tabs) | 3 | ✅ Captured |
| AI (2 tabs) | 2 | ✅ Captured |
| Integrations (2 tabs) | 2 | ✅ Captured |
| Approvals | 1 | ✅ Captured |
| Audit Logs (2 tabs) | 2 | ✅ Captured |
| POS | 1 | ✅ Captured |
| Communication | 1 | ✅ Captured |
| Helpdesk | 1 | ✅ Captured |

---

## Kenya-Critical Route Status

All critical routes captured:

| Route | PNG |
|-------|-----|
| /dashboard/sales | 072_sales.png |
| /dashboard/sales?tab=orders | 073_sales-orders.png |
| /dashboard/sales?tab=van-sales | 077_sales-van-sales.png |
| /dashboard/sales?tab=collections | 079_sales-collections.png |
| /dashboard/finance | 087_finance.png |
| /dashboard/finance?tab=mpesa | 094_finance-mpesa.png |
| /dashboard/finance?tab=tax | 095_finance-tax.png |
| /dashboard/hr | 097_hr.png |
| /dashboard/hr?tab=payroll | 100_hr-payroll.png |
| /dashboard/payroll | 106_payroll.png |
| /dashboard/payroll?tab=profiles | 107_payroll-profiles.png |
| /dashboard/payroll?tab=reports | 108_payroll-reports.png |

---

## How to Regenerate Screenshots

PNGs are gitignored (~70 MB). Regenerate locally:

```bash
# Full capture (all routes)
cd frontend
E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots

# Failed-only recapture
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots

# Specific module
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ROLE=sales npm run test:manual-screenshots

# Batch mode
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_BATCH_SIZE=15 MANUAL_CAPTURE_BATCH_INDEX=0 MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots

# Validate routes.json first
npm run manual:validate-routes
```

**Requirements:**
- Docker stack running (`docker compose up -d`)
- Frontend container: 2G memory (set in docker-compose.yml)
- Auth state present (auto-created by setup project)
