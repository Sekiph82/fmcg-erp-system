# ERP Button Recovery — Wave 2A + Wave 2B Report

**Date:** 2026-05-22  
**Status:** COMPLETE  
**BVT reduction:** 47 → 3 (44 resolved)

---

## Summary

Wave 2A restored 37 `[id]` detail pages from git history and removed 31 parent redirect entries that were causing prefix-match hijacking. Wave 2B corrected one href typo. The audit script was also enhanced to correctly classify template-literal hrefs pointing to `[id]` pages.

---

## BVT Counts

| Wave | BVT Before | BVT After | Delta |
|------|-----------|-----------|-------|
| Baseline | 47 | — | — |
| Wave 2A-TypeA (31 routes) | 47 | — | — |
| Wave 2A-TypeB (6 routes) | — | — | — |
| Wave 2B (typo fix) | — | 3 | -44 |
| **Total** | **47** | **3** | **-44** |

Remaining 3 BVTs are Wave 2C (pending design approval):
- `BVT-0001`: `/dashboard/nps/surveys` — middleware redirect (nps → crm tab)
- `BVT-0002`: `/dashboard/knowledge-base/categories` — no page file
- `BVT-0003`: `/dashboard/secondary-sales/${h.id}` — no [id]/page.tsx

---

## Wave 2A-TypeA: 31 Routes Restored + Middleware Fixed

Removed parent from `REDIRECTS` in `middleware.ts`, matching entries from `routeRedirectMap.ts`, and `audit-visible-import-graph.js`. Parent pages already have `page.tsx` (render directly after redirect removed). Also removed nested sub-routes from `routeRedirectMap.ts` that would still catch `[id]` via prefix matching.

| Route | Git Source | Notes |
|-------|-----------|-------|
| `users/[id]` | 674b6c5 | Full user detail |
| `roles/[id]` | 674b6c5 | Permissions management |
| `custom-fields/[id]` | 674b6c5 | Field config |
| `crm/records/[id]` | 674b6c5 | CRM record detail |
| `bank-reconciliation/statements/[id]` | 674b6c5 | Statement detail |
| `invoice-match/[id]` | 674b6c5 | Match detail |
| `dunning/cases/[id]` | 674b6c5 | Dunning case |
| `surveys/[id]` | 2b50ec0 | Survey detail |
| `knowledge-base/[id]` | 7faccdf | KB article |
| `marketing/campaigns/[id]` | 674b6c5 | Campaign detail |
| `marketing/promotions/[id]` | 674b6c5 | Promotion detail |
| `marketing/trade-spend/[id]` | 674b6c5 | Trade spend detail |
| `marketing/ads/[id]` | 674b6c5 | Ad detail |
| `marketing/social-media/[id]` | 674b6c5 | Social post detail |
| `marketing/segments/[id]` | 674b6c5 | Segment detail |
| `marketing/influencers/[id]` | 674b6c5 | Influencer detail |
| `marketing/visits/[id]` | 674b6c5 | Visit detail |
| `marketing/brand-spend/[id]` | 674b6c5 | Brand spend detail |
| `tpm/promotions/[id]` | 674b6c5 | TPM promotion detail (1 TS fix) |
| `landed-cost/[id]` | 674b6c5 | Landed cost detail |
| `supplier-portal/accounts/[id]` | 674b6c5 | Supplier account detail |
| `production/orders/[id]` | 674b6c5 | Production order detail |
| `production-execution/[id]` | 674b6c5 | Execution detail |
| `price-lists/[id]` | 674b6c5 | Price list detail |
| `contracts/list/[id]` | 674b6c5 | Contract detail |
| `recurring-orders/templates/[id]` | 674b6c5 | Template detail |
| `van-sales/vans/[id]` | 674b6c5 | Van detail |
| `portal/accounts/[id]` | 674b6c5 | Portal account detail (5 TS fixes) |
| `projects/[id]` | 8e21ed6 | Gantt chart |
| `brand-assets/[id]` | de74736 | Brand asset detail |
| `traceability/recalls/[id]` | 674b6c5 | Recall detail |

---

## Wave 2A-TypeB: 6 Routes Restored (No Middleware Changes)

Parent routes were NOT in REDIRECTS — just needed `[id]` stubs overwritten with real pages.

| Route | Git Source |
|-------|-----------|
| `documents/[id]` | 674b6c5 |
| `procurement/orders/[id]` | 674b6c5 |
| `quality/[id]` | 674b6c5 |
| `sales/orders/[id]` | 674b6c5 |
| `sales/invoices/[id]` | 674b6c5 |
| `sales/shipments/[id]` | 674b6c5 |

---

## Wave 2B: Href Typo Fix

**File:** `frontend/src/app/dashboard/ai/compliance/page.tsx:49`  
**Change:** `/dashboard/production/quality` → `/dashboard/production/quality-control`

---

## Audit Script Enhancement

Added template-literal route handling to `classifyTarget()` in `scripts/audit-visible-import-graph.js`. Routes like `/dashboard/users/${r.id}` now correctly resolve by checking for `[id]/page.tsx` under the base path.

---

## TypeScript Fixes Applied

| File | Fix |
|------|-----|
| `tpm/promotions/[id]/page.tsx:231` | `c.status as keyof typeof CLAIM_STATUS_BADGE` |
| `portal/accounts/[id]/page.tsx:44` | `inviteForm as unknown as Parameters<typeof portalApi.inviteUser>[1]` |
| `portal/accounts/[id]/page.tsx:352,386,392,399` | `d as unknown as Record<string, unknown>[]` |
| `production-execution/[id]/page.tsx:358` | `&quot;Run AI&quot;` entity escape |
| `quality/[id]/page.tsx:234` | `&quot;Add Test Result&quot;` entity escape |
| `sales/orders/[id]/page.tsx:387` | `&apos;s` entity escape |
| `traceability/recalls/[id]/page.tsx:148,251,334` | `&quot;...&quot;` entity escapes |

---

## Verification Results

| Check | Result |
|-------|--------|
| `npm run type-check` | ✓ CLEAN |
| `npm run build` | ✓ 698 static pages |
| `pytest tests/ -q` | ✓ 482 passed |
| `find-broken-action-cards.js` | ✓ 0 broken |
| `audit-visible-import-graph.js` | ✓ 3 BVT (Wave 2C only) |
| `check-workspace-tabs.js` | ✓ All passed |
| `check-restored-routes-quality.js` | ✓ 0 stubs, 0 no-UI |
| `audit-page-count.js` | ✓ 755 total pages |

---

## Remaining: Wave 2C (Pending Design Approval)

| BVT | Route | Issue | Options |
|-----|-------|-------|---------|
| BVT-0001 | `/dashboard/nps/surveys` | middleware redirect (nps → crm) | A: Change href; B: Build page |
| BVT-0002 | `/dashboard/knowledge-base/categories` | no page file | A: Add tab; B: Build page |
| BVT-0003 | `/dashboard/secondary-sales/${h.id}` | no [id] page | A: Build detail page; B: Drawer |
