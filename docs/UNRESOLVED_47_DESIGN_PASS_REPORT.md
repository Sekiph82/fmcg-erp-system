# Unresolved 47 BVT Targets — Design Pass Report

**Date:** 2026-05-22  
**Branch:** main  
**Status:** Pending user approval for Wave 2C (3 items). Waves 2A and 2B ready to implement.

---

## Executive Summary

Deep git search found real implementations for 43 of 47 BVT items. These can be restored from git history using the same proven pattern from Waves 1A/1B/1C. Only 3 items require new design work (Wave 2C).

| Wave | Name | BVT Items Fixed | Design Approval Needed |
|------|------|-----------------|------------------------|
| **2A** | Restore from git | 43 | No — git history confirmed |
| **2B** | Fix href typo | 1 | No — trivial fix |
| **2C** | New design | 3 | **Yes** |
| **Total** | | **47** | — |

**BVT projection:**
- Current: 47
- After Wave 2A: 4
- After Wave 2B: 3
- After Wave 2C: **0**

---

## Wave 2A — Restore from Git (43 BVT items, 37 unique routes)

All items have real page implementations in git history. Two sub-patterns based on current middleware state:

### Wave 2A Type-A: Remove redirect + restore page (31 routes, 37 BVT items)

Parent route is in `REDIRECTS` map. Middleware prefix-matching catches all `/{id}` sub-routes.

**Per-route work:**
1. `git checkout <commit> -- <path>` to restore `[id]/page.tsx`
2. Remove parent prefix entry from `middleware.ts` REDIRECTS map
3. Remove same entry from `routeRedirectMap.ts`
4. Remove from audit-visible-import-graph.js redirects section; add `[id]` path to BYPASS section
5. Update BYPASS count in status docs

| Route (relative to /dashboard/) | Parent to Remove | Git Commit | BVT IDs |
|----------------------------------|-----------------|------------|---------|
| `users/[id]` | `/dashboard/users` | 674b6c5 | BVT-0001 |
| `roles/[id]` | `/dashboard/roles` | 674b6c5 | BVT-0002 |
| `custom-fields/[id]` | `/dashboard/custom-fields` | 674b6c5 | BVT-0003 |
| `crm/records/[id]` | `/dashboard/crm/records` | 674b6c5 | BVT-0005/0006/0007/0008 |
| `surveys/[id]` | `/dashboard/surveys` | 2b50ec0 | BVT-0010 |
| `knowledge-base/[id]` | `/dashboard/knowledge-base` | 7faccdf | BVT-0013 |
| `bank-reconciliation/statements/[id]` | `/dashboard/bank-reconciliation` | 674b6c5 | BVT-0015 |
| `invoice-match/[id]` | `/dashboard/invoice-match` | 674b6c5 | BVT-0016 |
| `dunning/cases/[id]` | `/dashboard/dunning` | 674b6c5 | BVT-0017 |
| `traceability/recalls/[id]` | `/dashboard/traceability` | 674b6c5 | BVT-0018 |
| `marketing/campaigns/[id]` | `/dashboard/marketing/campaigns` | 674b6c5 | BVT-0019 |
| `marketing/promotions/[id]` | `/dashboard/marketing/promotions` | 674b6c5 | BVT-0020 |
| `marketing/trade-spend/[id]` | `/dashboard/marketing/trade-spend` | 674b6c5 | BVT-0021 |
| `marketing/ads/[id]` | `/dashboard/marketing/ads` | 674b6c5 | BVT-0022 |
| `marketing/social-media/[id]` | `/dashboard/marketing/social-media` | 674b6c5 | BVT-0023 |
| `marketing/segments/[id]` | `/dashboard/marketing/segments` | 674b6c5 | BVT-0024 |
| `marketing/influencers/[id]` | `/dashboard/marketing/influencers` | 674b6c5 | BVT-0025 |
| `marketing/visits/[id]` | `/dashboard/marketing/visits` | 674b6c5 | BVT-0026 |
| `marketing/brand-spend/[id]` | `/dashboard/marketing/brand-spend` | 674b6c5 | BVT-0027 |
| `tpm/promotions/[id]` | `/dashboard/tpm` | 674b6c5 | BVT-0028 |
| `landed-cost/[id]` | `/dashboard/landed-cost` | 674b6c5 | BVT-0032 |
| `supplier-portal/accounts/[id]` | `/dashboard/supplier-portal` | 674b6c5 | BVT-0033 |
| `production/orders/[id]` | `/dashboard/production/orders` | 674b6c5 | BVT-0034 |
| `production-execution/[id]` | `/dashboard/production-execution` | 674b6c5 | BVT-0035 |
| `projects/[id]` | `/dashboard/projects` | 8e21ed6 | BVT-0036 |
| `brand-assets/[id]` | `/dashboard/brand-assets` | de74736 | BVT-0038 |
| `price-lists/[id]` | `/dashboard/price-lists` | 674b6c5 | BVT-0042 |
| `contracts/list/[id]` | `/dashboard/contracts` | 674b6c5 | BVT-0043 |
| `recurring-orders/templates/[id]` | `/dashboard/recurring-orders` | 674b6c5 | BVT-0044 |
| `van-sales/vans/[id]` | `/dashboard/van-sales` | 674b6c5 | BVT-0046 |
| `portal/accounts/[id]` | `/dashboard/portal` | 674b6c5 | BVT-0047 |

### Wave 2A Type-B: Restore page only — no middleware change (6 routes, 6 BVT items)

Parent route is NOT in `REDIRECTS` (already in BYPASS from earlier wave). No prefix-redirect problem. Just restore the missing [id]/page.tsx and add path to BYPASS.

| Route (relative to /dashboard/) | Git Commit | BVT IDs |
|----------------------------------|------------|---------|
| `documents/[id]` | 674b6c5 | BVT-0011, BVT-0012 |
| `procurement/orders/[id]` | 674b6c5 | BVT-0029, BVT-0030, BVT-0031 |
| `quality/[id]` | 674b6c5 | BVT-0037 |
| `sales/orders/[id]` | 674b6c5 | BVT-0039 |
| `sales/invoices/[id]` | 674b6c5 | BVT-0040 |
| `sales/shipments/[id]` | 674b6c5 | BVT-0041 |

---

## Wave 2B — Link to Existing Page (1 item)

**BVT-0004** — trivial href typo fix.

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/ai/compliance/page.tsx` |
| Wrong href | `/dashboard/production/quality` |
| Correct href | `/dashboard/production/quality-control` |
| Why | `production/quality-control/page.tsx` exists in `674b6c5` and current tree. `production/quality` never existed. |
| Work | One-line edit. No middleware, no new files. |

---

## Wave 2C — New Design Required (3 items, needs approval)

These routes never existed in any git commit. User approval required before implementation.

---

### BVT-0009 — `/dashboard/nps/surveys`

**Source file:** `frontend/src/app/dashboard/nps/page.tsx`  
**Context:** NPS workspace page has a "surveys" tab/button linking to `/dashboard/nps/surveys`. No such route was ever committed.  
**Backend:** `nps.py` has survey-related endpoints.

| Option | Effort | Consistency |
|--------|--------|-------------|
| **A (recommended):** Change link to `/dashboard/marketing?tab=surveys` | Trivial (1-line edit) | Good — reuses existing surveys workspace |
| B: Build real `nps/surveys` list page from `nps.py` | Medium (new page + BYPASS) | Best — dedicated NPS surveys view |

**Recommendation:** Option A unless NPS surveys are a distinct dataset from marketing surveys.

---

### BVT-0014 — `/dashboard/knowledge-base/categories`

**Source file:** `frontend/src/app/dashboard/knowledge-base/page.tsx`  
**Context:** Knowledge base workspace has a "Categories" link. No categories sub-route was ever committed.  
**Backend:** `knowledge_base.py` has category CRUD endpoints.

| Option | Effort | Consistency |
|--------|--------|-------------|
| **A (recommended):** Add "Categories" tab/subview to existing knowledge-base workspace | Low (add tab to existing page) | Best — consistent with workspace subview pattern |
| B: Build standalone `knowledge-base/categories/page.tsx` | Medium (new page) | Adds nav depth |

**Recommendation:** Option A — subview tab consistent with how all other workspace sub-features are handled.

---

### BVT-0045 — `/dashboard/secondary-sales/${h.id}`

**Source file:** `frontend/src/app/dashboard/secondary-sales/page.tsx`  
**Context:** Secondary sales list page has row links pointing to `secondary-sales/${h.id}`. Detail page never created.  
**Backend:** `secondary_sales.py` has full CRUD including GET by ID.

| Option | Effort | Consistency |
|--------|--------|-------------|
| **A (recommended):** Build `secondary-sales/[id]/page.tsx` from `secondary_sales.py` | Medium (new page) | Best — consistent with all other [id] detail pages |
| B: Replace href with side drawer on row click | Low (modify list page) | Inconsistent — every other module uses [id] pages |

**Recommendation:** Option A — all 37 other "restore from git" items are [id] detail pages. Drawer would be an outlier.

---

## Middleware Impact Summary (Wave 2A)

Wave 2A-TypeA removes 31 parent entries from `REDIRECTS` + `routeRedirectMap.ts`. After Wave 2A, the REDIRECTS map will be significantly smaller (currently ~253 entries from Wave 1A+1B minus the 6 removed in Task 2). This is expected and correct: as [id] detail pages are restored, their parent redirect entries become unnecessary because the parent pages are already in BYPASS.

**Current BYPASS count:** 312  
**Estimated BYPASS after Wave 2A-TypeA:** 312 + 31 (new [id] paths) = ~343  
**Estimated BYPASS after Wave 2A-TypeB:** ~343 + 6 = ~349  
**REDIRECTS map shrinks by:** 31 entries (removed parents)
