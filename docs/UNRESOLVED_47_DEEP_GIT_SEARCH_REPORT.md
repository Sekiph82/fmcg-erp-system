# Unresolved 47 BVT Targets — Deep Git Search Report

**Date:** 2026-05-22  
**Branch:** main  
**Previous shallow search result:** 47/47 "found: false"  
**Deep search result:** 43/47 FOUND, 4 NOT_FOUND

---

## Executive Summary

The previous audit marked all 47 BVT items as unresolved with no git match. This deep search used 6 strategies including bulk directory scans of commit `674b6c5` and targeted `git log -S` / `git grep` passes. Result: **91% of BVT items (43/47) have real pages in git history** and can be restored. Only 4 items are genuinely new design work.

| Metric | Count |
|--------|-------|
| BVT items searched | 47 |
| FOUND in git | 43 |
| NOT FOUND (new design needed) | 4 |
| Unique routes to restore | 37 |
| Estimated BVT after Wave 2A+2B | 4 |
| Estimated BVT after Wave 2C | 0 |

---

## Search Strategies Used

1. `git show 674b6c5:frontend/src/app/dashboard/<route>/[id]/page.tsx` — direct path check
2. `git log --all --full-history -- 'frontend/src/app/dashboard/<segment>/[id]/page.tsx'`
3. `git show 674b6c5:frontend/src/app/dashboard/<route>/` — directory listing
4. `git grep -l '<label text>' <commit>` — UI label text search
5. `git log -S '<component name>'` — code string search
6. `git log --all --name-only -- '*/[id]/page.tsx'` — all dynamic id pages ever committed

---

## Root Cause: Middleware Prefix Matching

All 43 "found" items share the same root cause: **middleware prefix matching intercepts dynamic [id] sub-routes**.

`matchRedirect()` in `middleware.ts` uses a longest-prefix loop. If `/dashboard/crm/records` is in the `REDIRECTS` map, then `/dashboard/crm/records/abc123` is caught and redirected — even though `BYPASS_PREFIX_REDIRECT` contains `/dashboard/crm/records` (BYPASS is exact-match only, not prefix).

Fix pattern per case type:

**Type A — middleware_redirect** (31 unique routes, 37 BVT items):
1. Remove parent prefix from `REDIRECTS` map in `middleware.ts`
2. Remove same entry from `routeRedirectMap.ts`
3. Remove from audit-visible-import-graph.js redirect section; add [id] path to its BYPASS section
4. Restore `[id]/page.tsx` from git history via `git checkout <commit> -- <path>`

**Type B — no_route_file** (6 unique routes, 6 BVT items):
1. Parent is NOT in REDIRECTS (it's in BYPASS from earlier wave) → no middleware change needed
2. Restore `[id]/page.tsx` from git history
3. Add `[id]` path to BYPASS_PREFIX_REDIRECT and audit script BYPASS section

---

## Classification Table (All 47 Items)

| ID | Module | Target | Result | Git Commit | Fix Type |
|----|--------|--------|--------|------------|----------|
| BVT-0001 | Administration | `users/${r.id}` | FOUND | 674b6c5 | Type A |
| BVT-0002 | Administration | `roles/${r.id}` | FOUND | 674b6c5 | Type A |
| BVT-0003 | Administration | `custom-fields/${f.id}` | FOUND | 674b6c5 | Type A |
| BVT-0004 | Other | `production/quality` | NOT_FOUND | — | LINK_TO_EXISTING |
| BVT-0005 | CRM | `crm/records/${rec.id}` | FOUND | 674b6c5 | Type A |
| BVT-0006 | CRM | `crm/records/${rec.id}` | FOUND | 674b6c5 | Type A (dup) |
| BVT-0007 | CRM | `crm/records/${rec.id}` | FOUND | 674b6c5 | Type A (dup) |
| BVT-0008 | CRM | `crm/records/${act.id}` | FOUND | 674b6c5 | Type A (dup) |
| BVT-0009 | CRM | `nps/surveys` | NOT_FOUND | — | NEW_DESIGN |
| BVT-0010 | CRM | `surveys/${s.id}` | FOUND | 2b50ec0 | Type A |
| BVT-0011 | Documents | `documents/${d.id}` | FOUND | 674b6c5 | Type B |
| BVT-0012 | Documents | `documents/${d.id}` | FOUND | 674b6c5 | Type B (dup) |
| BVT-0013 | Documents | `knowledge-base/${a.id}` | FOUND | 7faccdf | Type A |
| BVT-0014 | Documents | `knowledge-base/categories` | NOT_FOUND | — | NEW_DESIGN |
| BVT-0015 | Finance | `bank-reconciliation/statements/${s.id}` | FOUND | 674b6c5 | Type A |
| BVT-0016 | Finance | `invoice-match/${m.id}` | FOUND | 674b6c5 | Type A |
| BVT-0017 | Finance | `dunning/cases/${c.id}` | FOUND | 674b6c5 | Type A |
| BVT-0018 | Inventory | `traceability/recalls/${r.id}` | FOUND | 674b6c5 | Type A |
| BVT-0019 | Marketing | `marketing/campaigns/${c.id}` | FOUND | 674b6c5 | Type A |
| BVT-0020 | Marketing | `marketing/promotions/${p.id}` | FOUND | 674b6c5 | Type A |
| BVT-0021 | Marketing | `marketing/trade-spend/${t.id}` | FOUND | 674b6c5 | Type A |
| BVT-0022 | Marketing | `marketing/ads/${a.id}` | FOUND | 674b6c5 | Type A |
| BVT-0023 | Marketing | `marketing/social-media/${a.id}` | FOUND | 674b6c5 | Type A |
| BVT-0024 | Marketing | `marketing/segments/${s.id}` | FOUND | 674b6c5 | Type A |
| BVT-0025 | Marketing | `marketing/influencers/${i.id}` | FOUND | 674b6c5 | Type A |
| BVT-0026 | Marketing | `marketing/visits/${v.id}` | FOUND | 674b6c5 | Type A |
| BVT-0027 | Marketing | `marketing/brand-spend/${b.id}` | FOUND | 674b6c5 | Type A |
| BVT-0028 | Marketing | `tpm/promotions/${p.id}` | FOUND | 674b6c5 | Type A |
| BVT-0029 | Procurement | `procurement/orders/${p.id}` | FOUND | 674b6c5 | Type B |
| BVT-0030 | Procurement | `procurement/orders/${a.po_id}` | FOUND | 674b6c5 | Type B (dup) |
| BVT-0031 | Procurement | `procurement/orders/${r.po_id}` | FOUND | 674b6c5 | Type B (dup) |
| BVT-0032 | Procurement | `landed-cost/${doc.id}` | FOUND | 674b6c5 | Type A |
| BVT-0033 | Procurement | `supplier-portal/accounts/${a.id}` | FOUND | 674b6c5 | Type A |
| BVT-0034 | Production | `production/orders/${o.id}` | FOUND | 674b6c5 | Type A |
| BVT-0035 | Production | `production-execution/${o.id}` | FOUND | 674b6c5 | Type A |
| BVT-0036 | Production | `projects/${p.id}` | FOUND | 8e21ed6 | Type A |
| BVT-0037 | Quality | `quality/${i.id}` | FOUND | 674b6c5 | Type B |
| BVT-0038 | Quality | `brand-assets/${a.id}` | FOUND | de74736 | Type A |
| BVT-0039 | Sales | `sales/orders/${r.id}` | FOUND | 674b6c5 | Type B |
| BVT-0040 | Sales | `sales/invoices/${r.id}` | FOUND | 674b6c5 | Type B |
| BVT-0041 | Sales | `sales/shipments/${r.id}` | FOUND | 674b6c5 | Type B |
| BVT-0042 | Sales | `price-lists/${h.id}` | FOUND | 674b6c5 | Type A |
| BVT-0043 | Sales | `contracts/list/${c.id}` | FOUND | 674b6c5 | Type A |
| BVT-0044 | Sales | `recurring-orders/templates/${t.id}` | FOUND | 674b6c5 | Type A |
| BVT-0045 | Sales | `secondary-sales/${h.id}` | NOT_FOUND | — | NEW_DESIGN |
| BVT-0046 | Sales | `van-sales/vans/${v.id}` | FOUND | 674b6c5 | Type A |
| BVT-0047 | Sales | `portal/accounts/${acc.id}` | FOUND | 674b6c5 | Type A |

---

## Not Found Items Analysis

### BVT-0004 — `/dashboard/production/quality`
- **Source:** `frontend/src/app/dashboard/ai/compliance/page.tsx`
- **Finding:** Href typo. The route `production/quality` never existed. The real page is `production/quality-control` (exists in `674b6c5` and current tree).
- **Fix:** Update href in source file. No middleware change. No new page needed.

### BVT-0009 — `/dashboard/nps/surveys`
- **Source:** `frontend/src/app/dashboard/nps/page.tsx`
- **Finding:** Never created in any commit. Backend `nps.py` with survey endpoints exists.
- **Options:** A) Build real `nps/surveys` list page using nps.py API. B) Change link to `/dashboard/marketing?tab=surveys` (reuses existing surveys workspace).
- **Recommended:** Option B (lower effort, surveys workspace already exists).

### BVT-0014 — `/dashboard/knowledge-base/categories`
- **Source:** `frontend/src/app/dashboard/knowledge-base/page.tsx`
- **Finding:** Never created in any commit. Backend `knowledge_base.py` has category endpoints.
- **Options:** A) Add "Categories" tab to existing knowledge-base workspace (subview). B) Build standalone categories page.
- **Recommended:** Option A (workspace subview is consistent with app patterns).

### BVT-0045 — `/dashboard/secondary-sales/${h.id}`
- **Source:** `frontend/src/app/dashboard/secondary-sales/page.tsx`
- **Finding:** Detail page never created in any commit. Backend `secondary_sales.py` exists.
- **Options:** A) Build `secondary-sales/[id]/page.tsx` using secondary_sales.py. B) Open row data in a side drawer instead.
- **Recommended:** Option A (consistent with all other [id] detail pages in this codebase).
