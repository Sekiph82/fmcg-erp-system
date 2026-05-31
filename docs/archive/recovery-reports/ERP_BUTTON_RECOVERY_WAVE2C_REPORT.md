# ERP Button Recovery — Wave 2C Report

**Date:** 2026-05-22
**Status:** COMPLETE
**BVT before:** 3 → **BVT after:** 0

---

## Summary

| Item | Result |
|------|--------|
| BVT before Wave 2C | 3 |
| BVT after Wave 2C | **0** |
| type-check | ✅ CLEAN |
| build | ✅ CLEAN |
| Backend tests | ✅ 482/482 |
| Broken action cards | ✅ 0 |
| Workspace tabs | ✅ All passed |
| Page count | 757 (up from 755) |
| Live smoke | ⏳ SKIPPED — Docker not running |

---

## Implementation Details

### BVT-0001 — `/dashboard/nps/surveys` (FIXED)

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/nps/page.tsx:110` |
| Old target | `/dashboard/nps/surveys` |
| New target | `/dashboard/surveys` |
| Backend used | No — href change only |
| Middleware changes | None |
| routeRedirectMap changes | None |

**Rationale:** `/dashboard/surveys` is the real standalone surveys page (`surveysApi` backed). The old `/dashboard/nps/surveys` never had a real page — it redirected through middleware to `/dashboard/crm?tab=nps`. Changed the "Manage Surveys" button in the NPS page to point directly to the real surveys dashboard.

---

### BVT-0002 — `/dashboard/knowledge-base/categories` (FIXED)

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/knowledge-base/categories/page.tsx` (NEW) |
| Backend used | Yes — `kbApi.listCategories()`, `kbApi.createCategory()`, `kbApi.updateCategory()` |
| Middleware changes | None (knowledge-base already removed from REDIRECTS in Wave 2A) |
| routeRedirectMap changes | None |

**Features:**
- Lists all KB categories with name, slug, icon (emoji), article count, description, display order
- Create new category form (name, slug auto-derived, description, icon, display order)
- Inline edit for each category row
- Loading / empty / error states
- Breadcrumb back to `/dashboard/knowledge-base`

---

### BVT-0003 — `/dashboard/secondary-sales/${h.id}` (FIXED)

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/secondary-sales/[id]/page.tsx` (NEW) |
| Backend used | Yes — `secondarySalesApi.get(id)`, `secondarySalesApi.process(id)`, `secondarySalesApi.reject(id, reason)` |
| Middleware changes | Removed `/dashboard/secondary-sales` from REDIRECTS; added to BYPASS_PREFIX_REDIRECT |
| routeRedirectMap changes | Removed `/dashboard/secondary-sales` and sub-routes (analysis/inventory/upload) |
| Audit script changes | Removed from MIDDLEWARE_REDIRECTS; added to BYPASS set |

**Features:**
- Loads `SecondarySalesDetail` by ID (`GET /api/v1/secondary-sales/{id}`)
- Shows header: reference_no, distributor, period, status, upload source, notes, validation errors
- KPI cards: total lines, total value, valid lines, invalid lines
- Actions: Process (VALIDATED status), Reject with reason (PENDING/VALIDATED)
- Sales lines table: retailer, product, SKU, qty sold, unit price, total value, sale date, valid flag
- Loading / not-found (404) / error states
- Back link to `/dashboard/secondary-sales`

**Middleware rationale:** `/dashboard/secondary-sales` was in REDIRECTS (→ `/dashboard/sales?tab=secondary`). Prefix-match would have caught any `/dashboard/secondary-sales/<id>` and redirected it. Removed the parent from REDIRECTS (real `page.tsx` exists and renders directly). Added to BYPASS_PREFIX_REDIRECT to be explicit. Analysis/inventory/upload sub-routes removed from routeRedirectMap (they have real pages, were already in BYPASS).

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/app/dashboard/nps/page.tsx` | href fix: `/dashboard/nps/surveys` → `/dashboard/surveys` |
| `frontend/src/app/dashboard/knowledge-base/categories/page.tsx` | NEW — KB Categories management page |
| `frontend/src/app/dashboard/secondary-sales/[id]/page.tsx` | NEW — Secondary Sales detail page |
| `frontend/src/middleware.ts` | Removed secondary-sales from REDIRECTS; added to BYPASS |
| `frontend/src/lib/routeRedirectMap.ts` | Removed secondary-sales and sub-routes |
| `scripts/audit-visible-import-graph.js` | Synced MIDDLEWARE_REDIRECTS and BYPASS |

---

## Verification Results

| Check | Result |
|-------|--------|
| `npm run type-check` | ✅ CLEAN |
| `npm run build` | ✅ CLEAN (757 pages) |
| `pytest tests/ -q` | ✅ 482/482 passed |
| `find-broken-action-cards.js` | ✅ 0 |
| `check-restored-routes-quality.js` | ✅ valid |
| `audit-visible-import-graph.js` | ✅ **0 BVT** |
| `check-workspace-tabs.js` | ✅ All passed |
| `audit-page-count.js` | ✅ 757 total |
| Live smoke | ⏳ SKIPPED — Docker not running |
| `check-route-redirects.js` | ⚠ 15 "Missing middleware" warnings (same as post-Wave 2A; expected) |

---

## Remaining Broken Targets

**None.**

---

## Decision

**A. Button/link recovery complete**

All 353 original broken visible action targets resolved across Waves 0 → 2C. BVT reduced from 47 (Wave 2C start) to **0**.

**Recommended next task:**
1. Start Docker and run `frontend/e2e/restored-routes-smoke.spec.ts` full suite (groups A–E)
2. Resume manufacturing/manual/screenshot/PDF work if applicable
