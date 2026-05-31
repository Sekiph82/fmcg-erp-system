# Action Card Health Audit
**Date:** 2026-05-19  
**Scope:** ERP-wide navigation tiles, action cards, workflow cards  
**Method:** Code inspection across all dashboard pages + targeted Playwright tests

---

## Summary

| Metric | Count |
|--------|-------|
| Routes scanned | 23 |
| Tabs examined | 30+ |
| Cards / tiles discovered | 120+ |
| **Working** | 110+ |
| **Broken (dead-click)** | 0 |
| **Wrong context (UX bug)** | 2 pages fixed |
| **Static OK** | ~40 metric/KPI cards |
| **Needs Review** | 2 (fleet sub-nav, cycle-count cross-context) |
| **Fixed in this pass** | 2 pages |

---

## Known Example — Inventory → Cycle Count

**Route:** `/dashboard/inventory?tab=cycle-count`

| Card | Route Target | Handler | Status |
|------|-------------|---------|--------|
| Count Plans | `/dashboard/cycle-count/plans` | `<Link href>` | ✅ WORKING |
| Count Tasks | `/dashboard/cycle-count/tasks` | `<Link href>` | ✅ WORKING |
| Count Entries | `/dashboard/cycle-count/entries` | `<Link href>` | ✅ WORKING |
| Variance Review | `/dashboard/cycle-count/variances` | `<Link href>` | ✅ WORKING |
| Reports & AI | `/dashboard/cycle-count/reports` | `<Link href>` | ✅ WORKING |

**Finding:** All 5 cards use Next.js `<Link>` components pointing to real routes that exist. Cards work. The user may have observed that clicking navigates away from the Inventory context to the cycle-count standalone module — this is correct behavior (cycle-count is a standalone module with its own sub-pages).

---

## Fixes Applied

### Fix 1: Logistics Overview Tab — Wrong navigation context
**Route:** `frontend/src/app/dashboard/logistics/page.tsx`  
**Problem:** KPI tiles and quick nav cards in the Overview tab used `router.push("/dashboard/logistics/shipments")` which navigated to the STANDALONE route, leaving the Logistics ModuleWorkspace context.  
**Fix:** Changed all navigation targets to use `?tab=` format so navigation stays within the workspace.

| Card | Before | After |
|------|--------|-------|
| Active Shipments KPI | `/dashboard/logistics/shipments` | `/dashboard/logistics?tab=shipments` |
| In Transit KPI | `/dashboard/logistics/shipments` | `/dashboard/logistics?tab=shipments` |
| At Port / Clearing KPI | `/dashboard/logistics/arrivals` | `/dashboard/logistics?tab=arrivals` |
| Overdue Documents KPI | `/dashboard/logistics/documents` | `/dashboard/logistics?tab=documents` |
| ETA "View" button | `/dashboard/logistics/arrivals` | `/dashboard/logistics?tab=arrivals` |
| "Manage all" shipments | `/dashboard/logistics/shipments` | `/dashboard/logistics?tab=shipments` |
| Shipment row click | `/dashboard/logistics/shipments` | `/dashboard/logistics?tab=shipments` |
| Shipment Planning card | `/dashboard/logistics/shipments` | `/dashboard/logistics?tab=shipments` |
| Container Tracking card | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` |
| Customs Documents card | `/dashboard/logistics/documents` | `/dashboard/logistics?tab=documents` |
| Arrival & Clearance card | `/dashboard/logistics/arrivals` | `/dashboard/logistics?tab=arrivals` |

**Files changed:** `frontend/src/app/dashboard/logistics/page.tsx`

---

### Fix 2: Maintenance Overview Tab — Wrong navigation context
**Route:** `frontend/src/app/dashboard/maintenance/page.tsx`  
**Problem:** KPI tiles, "View all" buttons, table row clicks, and quick nav cards in the Overview tab navigated to standalone routes (`/dashboard/maintenance/assets` etc.) instead of switching tabs within the Maintenance ModuleWorkspace.  
**Fix:** Changed all navigation targets to `?tab=` format.

| Card | Before | After |
|------|--------|-------|
| Total Assets KPI | `/dashboard/maintenance/assets` | `/dashboard/maintenance?tab=assets` |
| Open Breakdowns KPI | `/dashboard/maintenance/breakdowns` | `/dashboard/maintenance?tab=breakdowns` |
| Overdue PMs KPI | `/dashboard/maintenance/plans` | `/dashboard/maintenance?tab=plans` |
| Low Stock Spares KPI | `/dashboard/maintenance/spares` | `/dashboard/maintenance?tab=spares` |
| "View all" breakdowns | `/dashboard/maintenance/breakdowns` | `/dashboard/maintenance?tab=breakdowns` |
| Breakdown row click | `/dashboard/maintenance/breakdowns` | `/dashboard/maintenance?tab=breakdowns` |
| "View all" PMs | `/dashboard/maintenance/plans` | `/dashboard/maintenance?tab=plans` |
| PM row click | `/dashboard/maintenance/plans` | `/dashboard/maintenance?tab=plans` |
| Asset Register card | `/dashboard/maintenance/assets` | `/dashboard/maintenance?tab=assets` |
| PM Plans & Work Orders | `/dashboard/maintenance/plans` | `/dashboard/maintenance?tab=plans` |
| Breakdown Records card | `/dashboard/maintenance/breakdowns` | `/dashboard/maintenance?tab=breakdowns` |
| Predictive Maintenance | `/dashboard/maintenance/predictive` | `/dashboard/maintenance?tab=predictive` |
| Spare Parts card | `/dashboard/maintenance/spares` | `/dashboard/maintenance?tab=spares` |
| Maintenance Reports card | `/dashboard/maintenance/reports` | `/dashboard/maintenance?tab=reports` |

**Files changed:** `frontend/src/app/dashboard/maintenance/page.tsx`

---

## ERP-Wide Card Inventory (Code-Reviewed)

### Module Hub Pages — All Working

| Module | Pattern | Cards Found | Status |
|--------|---------|-------------|--------|
| HR | KPI tiles + section cards | 8 | ✅ All working — router.push to real routes |
| Finance | KPI tiles + quick links | 10 | ✅ All working |
| Sales | KPI tiles + quick links | 10 | ✅ All working |
| Production | Table rows + plans | — | ✅ All working |
| Quality | KPI cards | 4 | ✅ Static OK (no handler needed) |
| Procurement | Table rows | — | ✅ All working |
| Reports | Module cards | 7 | ✅ All working |
| Allergen | Action cards + quick nav | 13 | ✅ All working — uses `<a href>` |
| Traceability | KPIs + quick nav | 10 | ✅ All working |
| Shelf Life | KPIs + quick nav | 14 | ✅ All working |
| Timesheets | KPIs + quick nav | 9 | ✅ All working |
| Training | KPIs + quick nav | 11 | ✅ All working |
| Kanban | KPIs + quick nav | 8 | ✅ All working |
| Report Builder | KPIs + quick nav | 10 | ✅ All working |
| Mobile | KPIs + quick nav | 7 | ✅ All working |
| Notification Center | KPIs + quick nav | 9 | ✅ All working |
| Appraisals | KPIs + quick nav | 13 | ✅ All working |

### ModuleWorkspace Embedded Pages

| Module | Tab | Cards Found | Status |
|--------|-----|-------------|--------|
| Inventory → Cycle Count | cycle-count | 5 nav cards | ✅ Working (navigate to standalone cycle-count sub-pages) |
| Logistics → Overview | overview | 11 cards | ✅ FIXED — now navigate via `?tab=` |
| Maintenance → Overview | overview | 14 cards | ✅ FIXED — now navigate via `?tab=` |

---

## Needs Review

### 1. Fleet Dashboard (embedded in Logistics → Fleet tab)
**Route when embedded:** `/dashboard/logistics?tab=fleet`  
**Status:** NEEDS_REVIEW  
**Issue:** Fleet dashboard uses `<Link>` to navigate to `/dashboard/fleet/vehicles`, `/dashboard/fleet/drivers`, etc. When embedded in the Logistics workspace, clicking navigates to standalone fleet sub-pages, leaving the logistics context.  
**Reason not fixed:** Fleet is a large standalone module with 7 sub-pages. Embedding all of them as sub-tabs inside the Logistics workspace would be overly complex. The standalone fleet routes exist and work correctly. The fleet module has its own coherent module context at `/dashboard/fleet`.  
**Recommended next step:** Consider adding "Fleet" as a top-level sidebar nav item separately from Logistics, or adding a "Back to Logistics" breadcrumb in fleet sub-pages.

### 2. Cycle Count (embedded in Inventory → Cycle Count tab)
**Route when embedded:** `/dashboard/inventory?tab=cycle-count`  
**Status:** NEEDS_REVIEW (but WORKING)  
**Issue:** Same pattern as Fleet — Cycle Count nav cards navigate to standalone sub-pages, leaving the Inventory workspace context.  
**Reason not fixed:** Cycle Count is a standalone module (`/dashboard/cycle-count/`) with 5 real sub-pages. All routes exist and work correctly. Cards use proper `<Link>` components. The navigation is functional.  
**Recommended next step:** Consider adding a "Back to Inventory" breadcrumb in cycle-count sub-pages for context continuity.

---

## Rules — Working vs Broken vs Static

| Rule | Definition |
|------|-----------|
| WORKING | Click changes route, opens modal, switches tab, triggers API, or filters content |
| BROKEN | Looks clickable (hover/cursor/button), click produces no observable change |
| STATIC_OK | Metric/KPI display card — no hover/cursor/button styling, no interaction expected |
| NEEDS_REVIEW | Navigates but changes context unexpectedly, or is a known architectural trade-off |

---

## Audit Infrastructure Added

| File | Purpose |
|------|---------|
| `frontend/e2e/audit-action-cards.spec.ts` | Full ERP audit script — visits routes, discovers cards, tests clicks |
| `frontend/e2e/action-card-health.spec.ts` | Targeted health tests for known card patterns |

### Run Instructions

```bash
# Run targeted health tests
cd frontend
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/action-card-health.spec.ts --project=chromium --workers=1 --reporter=list

# Run full audit (generates docs/ACTION_CARD_HEALTH_AUDIT.json)
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/audit-action-cards.spec.ts --project=chromium --workers=1 --reporter=list
```

---

## Zero Dead-Click Cards Found

After complete code inspection of all dashboard pages, **zero cards/tiles were found that look clickable but do absolutely nothing** (no `onClick`, no `href`, no navigation). All interactive-looking cards either:
1. Have a working `router.push()` or `<Link>` handler
2. Are static metric/KPI display cards with no misleading interactive styling

The two fixes applied were **UX context bugs** (navigated correctly but to standalone routes instead of staying in the ModuleWorkspace tab context), not dead-click bugs.
