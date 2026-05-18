# Uncaptured Screenshots Report

**Date:** 2026-05-19  
**Status:** RECAPTURE IN PROGRESS

---

## Summary

| Metric | Count |
|--------|-------|
| Total routes in routes.json | 141 |
| Routes with capture=true | 140 |
| Routes with capture=false | 1 |
| Previously captured (run 1) | 73 |
| Previously failed (run 1) | 67 |
| Target for recapture | 67 |

### capture=false Routes (intentionally excluded)

| ID | Path | Reason |
|----|------|--------|
| security | /dashboard/admin?tab=security | Covered by admin workspace navigation; standalone page not needed |

---

## Kenya-Critical Route Status (Pre-Recapture)

| Module | Routes | Status | Critical for Kenya |
|--------|--------|--------|--------------------|
| Sales | 11 | FAILED | YES — van sales, M-Pesa collections |
| Finance | 10 | FAILED | YES — M-Pesa, eTIMS, tax |
| HR | 9 | FAILED | YES — Kenya payroll, PAYE/NHIF/NSSF |
| Payroll | 3 | FAILED | YES — payroll profiles, reports |
| Quality | 7 | FAILED | Important |
| Compliance | 3 | FAILED | Important |
| Production (partial) | 8 tabs | FAILED (4 captured) | Important |
| Planning | 4 | FAILED | Moderate |
| BOM | 4 | FAILED | Moderate |
| Shop-floor | 3 | FAILED | Moderate |
| Recipes | 1 | FAILED | Low |
| Logistics | 4 | FAILED | Moderate |

---

## Failed Routes — Full List

All 67 failures are classified as **dev-server-crash** (`net::ERR_EMPTY_RESPONSE`).

Root cause: Next.js dev server at 1G memory was overwhelmed after 37 consecutive rapid page navigations. Server was restarted with 2G memory for recapture.

### Production (8 routes)

| ID | Path | Error Class |
|----|------|-------------|
| production-costing | /dashboard/production?tab=costing | dev-server-crash |
| production-batch-lots | /dashboard/production?tab=batch-lots | dev-server-crash |
| production-quality-control | /dashboard/production?tab=quality-control | dev-server-crash |
| production-oee | /dashboard/production?tab=oee | dev-server-crash |
| production-downtime | /dashboard/production?tab=downtime | dev-server-crash |
| production-plans | /dashboard/production?tab=plans | dev-server-crash |
| production-scheduling | /dashboard/production?tab=scheduling | dev-server-crash |
| production-waste-yield | /dashboard/production?tab=waste-yield | dev-server-crash |

### Shop-floor (3 routes)

| ID | Path | Error Class |
|----|------|-------------|
| shop-floor | /dashboard/shop-floor | dev-server-crash |
| shop-floor-terminal | /dashboard/shop-floor?tab=terminal | dev-server-crash |
| shop-floor-supervisor | /dashboard/shop-floor?tab=supervisor | dev-server-crash |

### BOM (4 routes)

| ID | Path | Error Class |
|----|------|-------------|
| bom | /dashboard/bom | dev-server-crash |
| bom-list | /dashboard/bom?tab=list | dev-server-crash |
| bom-substitutes | /dashboard/bom?tab=substitutes | dev-server-crash |
| bom-compare | /dashboard/bom?tab=compare | dev-server-crash |

### Recipes (1 route)

| ID | Path | Error Class |
|----|------|-------------|
| recipes | /dashboard/recipes | dev-server-crash |

### Planning (4 routes)

| ID | Path | Error Class |
|----|------|-------------|
| planning | /dashboard/planning | dev-server-crash |
| planning-mrp | /dashboard/planning?tab=mrp | dev-server-crash |
| planning-mps | /dashboard/planning?tab=mps | dev-server-crash |
| planning-capacity | /dashboard/planning?tab=capacity | dev-server-crash |

### Quality (7 routes)

| ID | Path | Error Class |
|----|------|-------------|
| quality | /dashboard/quality | dev-server-crash |
| quality-inspections | /dashboard/quality?tab=inspections | dev-server-crash |
| quality-qms | /dashboard/quality?tab=qms | dev-server-crash |
| quality-allergen | /dashboard/quality?tab=allergen | dev-server-crash |
| quality-certificates | /dashboard/quality?tab=certificates | dev-server-crash |
| quality-consumer-complaints | /dashboard/quality?tab=consumer-complaints | dev-server-crash |
| quality-parameters | /dashboard/quality?tab=parameters | dev-server-crash |

### Compliance (3 routes)

| ID | Path | Error Class |
|----|------|-------------|
| compliance | /dashboard/compliance | dev-server-crash |
| compliance-gs1 | /dashboard/compliance?tab=gs1 | dev-server-crash |
| compliance-regulatory | /dashboard/compliance?tab=regulatory-certs | dev-server-crash |

### Sales (11 routes) — KENYA CRITICAL

| ID | Path | Error Class |
|----|------|-------------|
| sales | /dashboard/sales | dev-server-crash |
| sales-orders | /dashboard/sales?tab=orders | dev-server-crash |
| sales-invoices | /dashboard/sales?tab=invoices | dev-server-crash |
| sales-customers | /dashboard/sales?tab=customers | dev-server-crash |
| sales-shipments | /dashboard/sales?tab=shipments | dev-server-crash |
| sales-van-sales | /dashboard/sales?tab=van-sales | dev-server-crash |
| sales-quotes | /dashboard/sales?tab=quotes | dev-server-crash |
| sales-collections | /dashboard/sales?tab=collections | dev-server-crash |
| sales-price-lists | /dashboard/sales?tab=price-lists | dev-server-crash |
| sales-returns | /dashboard/sales?tab=returns | dev-server-crash |
| sales-field-sales | /dashboard/sales?tab=field-sales | dev-server-crash |

### Logistics (4 routes)

| ID | Path | Error Class |
|----|------|-------------|
| logistics | /dashboard/logistics | dev-server-crash |
| logistics-shipments | /dashboard/logistics?tab=shipments | dev-server-crash |
| logistics-fleet | /dashboard/logistics?tab=fleet | dev-server-crash |
| logistics-containers | /dashboard/logistics?tab=containers | dev-server-crash |

### Finance (10 routes) — KENYA CRITICAL

| ID | Path | Error Class |
|----|------|-------------|
| finance | /dashboard/finance | dev-server-crash |
| finance-accounting | /dashboard/finance?tab=accounting | dev-server-crash |
| finance-bank-recon | /dashboard/finance?tab=bank-recon | dev-server-crash |
| finance-fixed-assets | /dashboard/finance?tab=fixed-assets | dev-server-crash |
| finance-receivables | /dashboard/finance?tab=receivables | dev-server-crash |
| finance-cashbook | /dashboard/finance?tab=cashbook | dev-server-crash |
| finance-budget | /dashboard/finance?tab=budget | dev-server-crash |
| finance-mpesa | /dashboard/finance?tab=mpesa | dev-server-crash |
| finance-tax | /dashboard/finance?tab=tax | dev-server-crash |
| finance-expenses | /dashboard/finance?tab=expenses | dev-server-crash |

### HR (9 routes) — KENYA CRITICAL

| ID | Path | Error Class |
|----|------|-------------|
| hr | /dashboard/hr | dev-server-crash |
| hr-employees | /dashboard/hr?tab=employees | dev-server-crash |
| hr-attendance | /dashboard/hr?tab=attendance | dev-server-crash |
| hr-payroll | /dashboard/hr?tab=payroll | dev-server-crash |
| hr-recruitment | /dashboard/hr?tab=recruitment | dev-server-crash |
| hr-leave | /dashboard/hr?tab=leave | dev-server-crash |
| hr-appraisals | /dashboard/hr?tab=appraisals | dev-server-crash |
| hr-training | /dashboard/hr?tab=training | dev-server-crash |
| hr-expenses | /dashboard/hr?tab=expenses | dev-server-crash |

### Payroll (3 routes) — KENYA CRITICAL

| ID | Path | Error Class |
|----|------|-------------|
| payroll | /dashboard/payroll | dev-server-crash |
| payroll-profiles | /dashboard/payroll?tab=profiles | dev-server-crash |
| payroll-reports | /dashboard/payroll?tab=reports | dev-server-crash |

---

## Root Cause Analysis

All 67 failures share the same error: `net::ERR_EMPTY_RESPONSE`. This occurs when the Next.js dev server stops responding mid-run. Analysis:

1. **Memory pressure**: Dev server compiled 37+ heavy pages in rapid succession. At 1G, Node.js garbage collection cannot keep pace with compilation cache growth.
2. **Compiled page cache**: Next.js dev mode compiles each page on first visit and caches in memory. 140 pages = significant memory footprint.
3. **No breathing room**: Original script used 800ms between pages — not enough for GC when server is under memory pressure.

**Fix applied for recapture:**
- Frontend container memory increased from 1G → 2G
- Script improved: 4s retry delay, fresh browser context after crash, 800ms inter-route delay
- Failed-only mode: only retry the 67 failed routes

---

## How to Regenerate Screenshots

```bash
# Full recapture of all failed routes
cd frontend
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots

# Specific module
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ROLE=sales npm run test:manual-screenshots

# Specific IDs
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_IDS=sales,finance,hr npm run test:manual-screenshots

# Batch mode (15 routes per batch)
E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_BATCH_SIZE=15 MANUAL_CAPTURE_BATCH_INDEX=0 MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots
```

Screenshot PNGs are gitignored (too large). The index and scripts are committed.
