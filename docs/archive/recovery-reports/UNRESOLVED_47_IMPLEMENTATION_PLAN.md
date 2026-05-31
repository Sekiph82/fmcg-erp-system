# Unresolved 47 BVT Targets — Implementation Plan

**Date:** 2026-05-22  
**Status:** Wave 2A and 2B ready. Wave 2C pending design approval.  
**Goal:** BVT count 47 → 0

---

## Overview

| Wave | Items | Approach | Approval | Estimated BVT After |
|------|-------|----------|----------|---------------------|
| 2A-TypeA | 37 BVT (31 routes) | Restore from git + remove parent from REDIRECTS | Not needed | 10 |
| 2A-TypeB | 6 BVT (6 routes) | Restore from git only | Not needed | 4 |
| 2B | 1 BVT | Fix href typo | Not needed | 3 |
| 2C | 3 BVT | New design (pending approval) | **Required** | 0 |

---

## Pre-Implementation Checklist

Before starting any wave:
- [ ] `git status` clean
- [ ] `npm run type-check` passes
- [ ] `node scripts/find-broken-action-cards.js` = 0
- [ ] `node scripts/audit-visible-import-graph.js` = 47 BVT (baseline)

---

## Wave 2A-TypeA: Remove Redirect + Restore Page

**Git commits needed:** 674b6c5 (main), 2b50ec0 (surveys), 7faccdf (knowledge-base), 8e21ed6 (projects), de74736 (brand-assets)

**Per-route steps (repeat for each of the 31 routes):**

```
git checkout <gitCommit> -- <gitPath>
```

Then for each parent in REDIRECTS, remove from:
1. `frontend/src/middleware.ts` — REDIRECTS map entry
2. `frontend/src/lib/routeRedirectMap.ts` — matching entry
3. `scripts/audit-visible-import-graph.js` — remove from redirects section; add [id] path to BYPASS section

**Critical:** `middleware.ts` and `routeRedirectMap.ts` must always stay in sync. `check-route-redirects.js` will warn if they diverge.

### Ordered restore list (674b6c5)

```bash
git checkout 674b6c5 -- frontend/src/app/dashboard/users/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/roles/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/custom-fields/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/crm/records/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/bank-reconciliation/statements/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/invoice-match/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/dunning/cases/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/campaigns/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/promotions/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/trade-spend/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/ads/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/social-media/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/segments/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/influencers/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/visits/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/marketing/brand-spend/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/tpm/promotions/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/landed-cost/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/supplier-portal/accounts/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/production/orders/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/production-execution/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/price-lists/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/contracts/list/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/recurring-orders/templates/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/van-sales/vans/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/portal/accounts/[id]/page.tsx
```

```bash
git checkout 2b50ec0 -- frontend/src/app/dashboard/surveys/[id]/page.tsx
git checkout 7faccdf -- frontend/src/app/dashboard/knowledge-base/[id]/page.tsx
git checkout 8e21ed6 -- frontend/src/app/dashboard/projects/[id]/page.tsx
git checkout de74736 -- frontend/src/app/dashboard/brand-assets/[id]/page.tsx
```

### REDIRECTS entries to remove (Type-A parents)

Remove these from `middleware.ts` REDIRECTS map AND `routeRedirectMap.ts`:

| Entry to remove | Currently redirects to |
|-----------------|------------------------|
| `/dashboard/users` | `/dashboard/admin?tab=users` |
| `/dashboard/roles` | `/dashboard/admin?tab=roles` |
| `/dashboard/custom-fields` | `/dashboard/admin?tab=custom-fields` |
| `/dashboard/crm/records` | `/dashboard/crm?tab=overview` |
| `/dashboard/surveys` | `/dashboard/crm?tab=surveys` |
| `/dashboard/knowledge-base` | `/dashboard/documents?tab=knowledge-base` |
| `/dashboard/bank-reconciliation` | `/dashboard/finance?tab=bank-recon` |
| `/dashboard/invoice-match` | `/dashboard/finance?tab=invoice-match` |
| `/dashboard/dunning` | `/dashboard/finance?tab=dunning` |
| `/dashboard/traceability` | `/dashboard/inventory?tab=traceability` |
| `/dashboard/marketing/campaigns` | `/dashboard/marketing?tab=campaigns` |
| `/dashboard/marketing/promotions` | `/dashboard/marketing?tab=promotions` |
| `/dashboard/marketing/trade-spend` | `/dashboard/marketing?tab=trade-spend` |
| `/dashboard/marketing/ads` | `/dashboard/marketing?tab=ads` |
| `/dashboard/marketing/social-media` | `/dashboard/marketing?tab=social-media` |
| `/dashboard/marketing/segments` | `/dashboard/marketing?tab=segments` |
| `/dashboard/marketing/influencers` | `/dashboard/marketing?tab=influencers` |
| `/dashboard/marketing/visits` | `/dashboard/marketing?tab=visits` |
| `/dashboard/marketing/brand-spend` | `/dashboard/marketing?tab=brand-spend` |
| `/dashboard/tpm` | `/dashboard/marketing?tab=tpm` |
| `/dashboard/landed-cost` | `/dashboard/procurement?tab=landed-cost` |
| `/dashboard/supplier-portal` | `/dashboard/procurement?tab=supplier-portal` |
| `/dashboard/production/orders` | `/dashboard/production?tab=orders` |
| `/dashboard/production-execution` | `/dashboard/production?tab=execution` |
| `/dashboard/projects` | `/dashboard/production?tab=projects` |
| `/dashboard/brand-assets` | `/dashboard/quality?tab=brand-assets` |
| `/dashboard/price-lists` | `/dashboard/sales?tab=price-lists` |
| `/dashboard/contracts` | `/dashboard/sales?tab=contracts` |
| `/dashboard/recurring-orders` | `/dashboard/sales?tab=recurring` |
| `/dashboard/van-sales` | `/dashboard/sales?tab=van-sales` |
| `/dashboard/portal` | `/dashboard/sales?tab=portal` |

**Note:** Removing these from REDIRECTS is safe because all parent pages are already in BYPASS_PREFIX_REDIRECT (added in earlier waves). Parent pages remain accessible.

---

## Wave 2A-TypeB: Restore Page Only

No REDIRECTS changes. Parent routes NOT in REDIRECTS (in BYPASS). Just restore [id] files and add to BYPASS.

```bash
git checkout 674b6c5 -- frontend/src/app/dashboard/documents/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/procurement/orders/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/quality/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/sales/orders/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/sales/invoices/[id]/page.tsx
git checkout 674b6c5 -- frontend/src/app/dashboard/sales/shipments/[id]/page.tsx
```

Add to `BYPASS_PREFIX_REDIRECT` in `middleware.ts`:
- `/dashboard/documents/`  (or rely on /dashboard/documents being absent from REDIRECTS)
- `/dashboard/procurement/orders/`
- `/dashboard/quality/`  
- `/dashboard/sales/orders/`
- `/dashboard/sales/invoices/`
- `/dashboard/sales/shipments/`

Also update `audit-visible-import-graph.js` BYPASS section for these.

---

## Wave 2B: Fix Href Typo

**File:** `frontend/src/app/dashboard/ai/compliance/page.tsx`

Find and replace: `"/dashboard/production/quality"` → `"/dashboard/production/quality-control"`

No middleware changes. No new files. Verify `production/quality-control/page.tsx` exists in current tree first.

---

## Wave 2C: New Design (Needs Approval)

**Do not implement until user approves design choices.**

### BVT-0009 — nps/surveys

**If Option A approved (recommended):**
- Edit `frontend/src/app/dashboard/nps/page.tsx`
- Change href/link: `/dashboard/nps/surveys` → `/dashboard/marketing?tab=surveys`
- No new file, no middleware change

**If Option B approved (build nps/surveys page):**
- Create `frontend/src/app/dashboard/nps/surveys/page.tsx` using nps.py survey endpoints
- Add `/dashboard/nps/surveys` to BYPASS_PREFIX_REDIRECT
- Add to audit-visible-import-graph.js BYPASS section

### BVT-0014 — knowledge-base/categories

**If Option A approved (recommended — subview tab):**
- Edit `frontend/src/app/dashboard/knowledge-base/page.tsx`
- Add "Categories" tab/subview that fetches from knowledge_base.py category endpoints
- Change href from `/dashboard/knowledge-base/categories` to internal tab switch or remove link

**If Option B approved (standalone page):**
- Create `frontend/src/app/dashboard/knowledge-base/categories/page.tsx`
- Add to BYPASS (parent `/dashboard/knowledge-base` already not in REDIRECTS after Wave 2A-TypeA)

### BVT-0045 — secondary-sales/[id]

**If Option A approved (recommended — detail page):**
- Create `frontend/src/app/dashboard/secondary-sales/[id]/page.tsx`
- Use `secondary_sales.py` GET by ID endpoint
- Add `/dashboard/secondary-sales/` to BYPASS (if parent still in REDIRECTS)
- Follow same pattern as other [id] detail pages restored in Wave 2A

**If Option B approved (drawer):**
- Edit `frontend/src/app/dashboard/secondary-sales/page.tsx`
- Replace `href="/dashboard/secondary-sales/${h.id}"` with onClick that opens side drawer with row data
- No new files, no middleware changes

---

## Verification Steps (After Each Wave)

```bash
# After Wave 2A:
node scripts/audit-visible-import-graph.js   # expect 4 BVT
node scripts/check-route-redirects.js         # expect 0 warnings
node scripts/check-workspace-tabs.js          # expect 0 issues
node scripts/check-restored-routes-quality.js # all valid
npm run type-check                             # CLEAN
npm run build                                 # CLEAN
node scripts/find-broken-action-cards.js      # expect 0

# After Wave 2B:
node scripts/audit-visible-import-graph.js   # expect 3 BVT
node scripts/find-broken-action-cards.js      # expect 0

# After Wave 2C:
node scripts/audit-visible-import-graph.js   # expect 0 BVT
```

---

## Commit Strategy

| Wave | Commit Message |
|------|---------------|
| 2A-TypeA (674b6c5 batch) | `fix(ui): restore [id] detail pages from 674b6c5 — remove middleware prefix redirects` |
| 2A-TypeA (earlier commits) | `fix(ui): restore surveys/kb/projects/brand-assets [id] pages from git history` |
| 2A-TypeB | `fix(ui): restore detail pages with no-route-file pattern (docs/procurement/quality/sales)` |
| 2B | `fix(ui): correct production/quality typo in ai compliance action card` |
| 2C | `fix(ui): resolve final 3 unresolved BVT targets — Wave 2C new design` |

**All commits must pass:** type-check CLEAN, build CLEAN, find-broken-action-cards = 0.
