# ERP Action Card Recovery Report

**Date:** 2026-05-20
**Pass:** Round 15 — ERP-wide strict action card / button recovery audit
**Method:** Static code analysis (find-broken-action-cards.js) + manual verification + route checks

---

## Summary

| Metric | Count |
|--------|-------|
| Source files scanned | 63 |
| Redirect stubs found (total) | 491 |
| Total broken card references found | 314 (pre-fix) |
| **User-visible broken cards** | **18** |
| User-visible broken cards fixed | **18** |
| User-visible broken cards remaining | **0** |
| Old-standalone-page broken cards (never user-visible) | 296 (safe — pages themselves redirect) |
| Middleware prefix traps found | 1 (MPS — fixed in Round 13/14) |
| Command palette (actionRegistry.ts) entries fixed | 16 |
| Workspace page hrefs fixed | 5 |
| Pages/stubs restored | 0 (all broken cards were fixable by updating hrefs) |
| Frontend type-check | CLEAN |
| Frontend build | CLEAN |

---

## MPS Case (Rounds 13–14, Prerequisite)

**Source:** `frontend/src/app/dashboard/mps/page.tsx` (MPS tab inside Planning workspace)

| Card | Old Target | Old Behavior | Fix | Status |
|------|-----------|-------------|-----|--------|
| Production Planning Board | `/dashboard/mps/planning-board` | Redirect stub → `/dashboard/planning?tab=mps` | Restored real page | FIXED |
| Capacity Heatmap | `/dashboard/mps/capacity` | Redirect stub → `/dashboard/planning?tab=mps` | Restored real page | FIXED |
| Campaign Planning | `/dashboard/mps/campaigns` | Redirect stub → `/dashboard/planning?tab=mps` | Restored real page | FIXED |
| What-If Simulation | `/dashboard/mps/whatif` | Redirect stub → `/dashboard/planning?tab=mps` | Restored real page | FIXED |

**Middleware prefix trap:** `/dashboard/mps` prefix redirect caught all sub-routes before pages rendered.  
**Fix:** Added `BYPASS_PREFIX_REDIRECT` set in `middleware.ts` for the 4 real MPS sub-routes.  
**Redirect type changed:** 308 → 302 for all dashboard consolidation redirects (browser cache issue).

---

## Round 15 — ERP-Wide Findings

### A. Command Palette — actionRegistry.ts (16 entries fixed)

The Ctrl+K command palette had 16 entries pointing to redirect stub routes.
When clicked, users would hit an extra 302 redirect before landing in the right workspace.
All fixed to point directly to the correct workspace `?tab=` URLs.

| Entry | Old href | New href | Issue |
|-------|---------|---------|-------|
| New Contract | `/dashboard/contracts/new` | `/dashboard/sales?tab=contracts&drawer=create` | Stub → sales workspace |
| New Expense Claim | `/dashboard/expenses/claims/new` | `/dashboard/hr?tab=expenses&drawer=create` | Stub → HR workspace |
| New Job Requisition | `/dashboard/recruitment/requisitions` | `/dashboard/hr?tab=recruitment` | Stub sub-route |
| New Kanban Card | `/dashboard/kanban/cards` | `/dashboard/planning?tab=kanban` | Stub sub-route |
| Start Van Route | `/dashboard/van-sales/route` | `/dashboard/sales?tab=van-sales` | Stub sub-route |
| Import Bank Statement | `/dashboard/bank-reconciliation/import` | `/dashboard/finance?tab=bank-recon` | Stub sub-route |
| Run MRP | `/dashboard/mrp/run` | `/dashboard/planning?tab=mrp` | Stub sub-route |
| Run Procurement AI | `/dashboard/procurement-suggestion/ai` | `/dashboard/procurement?tab=suggestions` | Stub sub-route |
| Run Bank Reconciliation | `/dashboard/bank-reconciliation` | `/dashboard/finance?tab=bank-recon` | Middleware redirect |
| Run Invoice Matching | `/dashboard/invoice-match` | `/dashboard/finance?tab=invoice-match` | Middleware redirect |
| Run Kenya Payroll | `/dashboard/payroll` | `/dashboard/hr?tab=payroll` | Middleware redirect |
| Run Production AI | `/dashboard/production/ai` | `/dashboard/production?tab=plans` | Stub sub-route |
| Aging Report | `/dashboard/dunning/aging` | `/dashboard/finance?tab=dunning` | Stub sub-route |
| Build Custom Report | `/dashboard/report-builder/builder` | `/dashboard/analytics?tab=report-builder` | Stub sub-route |
| ESG Reports | `/dashboard/esg/reports` | `/dashboard/utility-management?tab=esg` | Stub sub-route |
| Rider Performance | `/dashboard/van-sales/performance` | `/dashboard/sales?tab=van-sales` | Stub sub-route |

**File changed:** `frontend/src/lib/actionRegistry.ts`

---

### B. Marketing Workspace — marketing/page.tsx (2 buttons fixed)

"+ New Campaign" and "+ New Promotion" buttons in the marketing overview linked to redirect stub routes.
The middleware caught these via prefix match and stripped the `drawer=create` param — so the create drawer never opened.

| Button | Old href | New href | Issue |
|--------|---------|---------|-------|
| + New Campaign | `/dashboard/marketing/campaigns/new` | `/dashboard/marketing?tab=campaigns&drawer=create` | Middleware stripped drawer param |
| + New Promotion | `/dashboard/marketing/promotions/new` | `/dashboard/marketing?tab=promotions&drawer=create` | Middleware stripped drawer param |

**Root cause:** `/dashboard/marketing/campaigns/new` had a stub page that correctly redirected with `drawer=create`.
But middleware's prefix match on `/dashboard/marketing/campaigns` fired first and redirected WITHOUT the drawer param.
Stub page was never reached.

**File changed:** `frontend/src/app/dashboard/marketing/page.tsx`

---

### C. CRM Workspace — crm/page.tsx (2 links fixed)

Quick navigation links in the CRM dashboard overview linked to redirect stub sub-routes.

| Link | Old href | New href | Issue |
|------|---------|---------|-------|
| Overdue Queue | `/dashboard/crm/overdue` | `/dashboard/crm?tab=pipeline` | Stub → crm?tab=pipeline via redirect |
| AI Agents | `/dashboard/crm/ai` | `/dashboard/crm?tab=overview` | Stub → crm?tab=overview via redirect |

**Note:** Most CRM sub-routes (`crm/leads`, `crm/opportunities`, `crm/pipeline`, `crm/activities`, `crm/forecast`, `crm/win-loss`, `crm/stages`) are REAL standalone pages (100–190 lines), not stubs. Only `crm/overdue` and `crm/ai` were redirect stubs.

**File changed:** `frontend/src/app/dashboard/crm/page.tsx`

---

### D. Documents Workspace — documents/page.tsx (1 button fixed)

"+ New Document" button used `router.push("/dashboard/documents/new")` which goes through a redirect stub.
Changed to use the direct URL `router.push("/dashboard/documents?drawer=create")`.

| Button | Old push | New push | Issue |
|--------|---------|---------|-------|
| + New Document | `/dashboard/documents/new` | `/dashboard/documents?drawer=create` | Unnecessary redirect stub hop |

**File changed:** `frontend/src/app/dashboard/documents/page.tsx`

---

## Old Standalone Pages (296 broken cards — NOT fixed, not user-visible)

The `find-broken-action-cards.js` script found 296 additional broken cards in OLD STANDALONE PAGES.
These pages are themselves redirected by middleware (e.g., `/dashboard/allergen` → `/dashboard/quality?tab=allergen`).
Users who visit the old routes are redirected before the old page renders — they never see the old page's navigation cards.

**Why not fixed:** Fixing these would require either:
1. Rebuilding all old standalone page UIs (not justified — they're archived, not broken)
2. Deleting them (not safe without audit of any edge-case navigation paths)

**Classified as:** `safe_archived_standalone` — present in codebase but never user-visible due to middleware consolidation redirects.

**If old standalone pages need to be user-accessible again:** Use `BYPASS_PREFIX_REDIRECT` in middleware.ts (same pattern as MPS recovery).

---

## Prefix Redirect Trap Analysis

Prefix redirect traps occur when a parent route redirect in middleware catches child routes before real pages render.

| Parent Route | Redirects To | Child Route | Child Status | Bypass Needed? |
|-------------|-------------|------------|-------------|----------------|
| `/dashboard/mps` | `planning?tab=mps` | `/dashboard/mps/planning-board` | Real page | **FIXED** (Round 13) |
| `/dashboard/mps` | `planning?tab=mps` | `/dashboard/mps/capacity` | Real page | **FIXED** (Round 13) |
| `/dashboard/mps` | `planning?tab=mps` | `/dashboard/mps/campaigns` | Real page | **FIXED** (Round 13) |
| `/dashboard/mps` | `planning?tab=mps` | `/dashboard/mps/whatif` | Real page | **FIXED** (Round 13) |
| `/dashboard/marketing/campaigns` | `marketing?tab=campaigns` | `/dashboard/marketing/campaigns/new` | Stub (now bypassed by href fix) | FIXED via href change |

**Rule:** When creating real pages under a route prefix that has a middleware redirect, add the route to `BYPASS_PREFIX_REDIRECT` in `middleware.ts`.

---

## Remaining Needs Review

| Item | Route | Reason | Recommendation |
|------|-------|--------|---------------|
| CRM Records | `/dashboard/crm/records` | No page.tsx file, route handled by middleware redirect to overview | Safe — no UI broken |
| Van Sales sub-features | `/dashboard/van-sales/route`, `/dashboard/van-sales/performance` | Consolidated into single van-sales tab, no sub-view distinction | Low priority |
| MRP Run sub-action | `/dashboard/mrp/run` | Now points to MRP tab; no specific "Run MRP" dialog in workspace | Needs MRP tab UI review |

---

## ERP-Wide Module Status

| Module | Action Cards Status | Broken Fixed | Notes |
|--------|-------------------|-------------|-------|
| Manufacturing / Production | ✅ Clean | 0 | All workspace cards use ?tab= |
| Supply Chain / Inventory | ✅ Clean | 0 | All workspace cards use ?tab= |
| Sales / Commercial | ✅ Clean | 0 | actionRegistry entries fixed |
| Finance | ✅ Clean | 0 | actionRegistry entries fixed |
| HR / Payroll | ✅ Clean | 0 | actionRegistry entries fixed |
| Planning / MPS / MRP | ✅ Clean | 4 (MPS, prior) | MPS pages restored, bypass added |
| Marketing | ✅ Clean | 2 | New Campaign / New Promotion fixed |
| CRM | ✅ Clean | 2 | Overdue Queue / AI Agents fixed |
| Documents | ✅ Clean | 1 | New Document button fixed |
| Quality | ✅ Clean | 0 | All workspace cards use ?tab= |
| Logistics | ✅ Clean | 0 (fixed Round 13) | All workspace cards use ?tab= |
| Maintenance | ✅ Clean | 0 (fixed Round 13) | All workspace cards use ?tab= |
| Command Palette | ✅ Clean | 16 | All actionRegistry hrefs fixed |

---

## Verification Results

| Check | Result |
|-------|--------|
| User-visible broken cards after fix | 0 |
| Redirect stub refs in user-visible files | 0 |
| Frontend type-check | CLEAN |
| Frontend build | CLEAN |
| MPS regression (4 pages) | PASS |
| Middleware redirects remain 302 | YES |
