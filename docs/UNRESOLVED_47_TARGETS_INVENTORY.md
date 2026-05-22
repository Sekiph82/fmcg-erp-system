# Unresolved 47 BVT Targets — Full Inventory

**Date:** 2026-05-22  
**Branch:** main  
**Status:** Deep git search complete. 43/47 found in git history. 4 not found (need design decisions).

---

## Summary

| Result | BVT Items | Unique Routes |
|--------|-----------|---------------|
| FOUND_REAL_PAGE_HIGH_CONFIDENCE | 43 | 37 |
| NOT_FOUND_AFTER_DEEP_SEARCH | 4 | 4 |
| **Total** | **47** | **41** |

---

## Administration (3 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0001 | User row link (dynamic id) | `/dashboard/users/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/users/[id]/page.tsx` |
| BVT-0002 | Role row link (dynamic id) | `/dashboard/roles/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/roles/[id]/page.tsx` |
| BVT-0003 | Custom field row (dynamic id) | `/dashboard/custom-fields/${f.custom_field_id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/custom-fields/[id]/page.tsx` |

---

## Other (1 item)

| ID | Label | Target | Deep Search | Notes |
|----|-------|--------|-------------|-------|
| BVT-0004 | Quality Module (action card) | `/dashboard/production/quality` | NOT_FOUND | Typo. Real page: `production/quality-control`. Fix: update href. |

---

## Commercial / CRM (6 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0005 | View (pipeline record) | `/dashboard/crm/records/${rec.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/crm/records/[id]/page.tsx` |
| BVT-0006 | View (lead) | `/dashboard/crm/records/${rec.id}` | FOUND | 674b6c5 | same as BVT-0005 |
| BVT-0007 | View (opportunity) | `/dashboard/crm/records/${rec.id}` | FOUND | 674b6c5 | same as BVT-0005 |
| BVT-0008 | CRM record link (activity) | `/dashboard/crm/records/${act.crm_record_id}` | FOUND | 674b6c5 | same as BVT-0005 |
| BVT-0009 | surveys | `/dashboard/nps/surveys` | NOT_FOUND | Never existed. Backend nps.py present. |
| BVT-0010 | Survey row link (dynamic id) | `/dashboard/surveys/${s.id}` | FOUND | 2b50ec0 | `frontend/src/app/dashboard/surveys/[id]/page.tsx` |

---

## Documents & Communication (4 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0011 | Document row link (compliance) | `/dashboard/documents/${d.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/documents/[id]/page.tsx` |
| BVT-0012 | Document row link (expiring) | `/dashboard/documents/${d.id}` | FOUND | 674b6c5 | same as BVT-0011 |
| BVT-0013 | Article row link (dynamic id) | `/dashboard/knowledge-base/${a.id}` | FOUND | 7faccdf | `frontend/src/app/dashboard/knowledge-base/[id]/page.tsx` |
| BVT-0014 | Categories | `/dashboard/knowledge-base/categories` | NOT_FOUND | Never existed. Backend has category endpoints. |

---

## Finance (3 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0015 | Statement row link (dynamic id) | `/dashboard/bank-reconciliation/statements/${s.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/bank-reconciliation/statements/[id]/page.tsx` |
| BVT-0016 | View (invoice match) | `/dashboard/invoice-match/${m.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/invoice-match/[id]/page.tsx` |
| BVT-0017 | Dunning case row (dynamic id) | `/dashboard/dunning/cases/${c.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/dunning/cases/[id]/page.tsx` |

---

## Supply Chain / Inventory (1 item)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0018 | Recall row link (dynamic id) | `/dashboard/traceability/recalls/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx` |

---

## Commercial / Marketing (10 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0019 | Campaign row link (dynamic id) | `/dashboard/marketing/campaigns/${c.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/campaigns/[id]/page.tsx` |
| BVT-0020 | Promotion row link (dynamic id) | `/dashboard/marketing/promotions/${p.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/promotions/[id]/page.tsx` |
| BVT-0021 | Trade spend row link (dynamic id) | `/dashboard/marketing/trade-spend/${t.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/trade-spend/[id]/page.tsx` |
| BVT-0022 | Ad row link (dynamic id) | `/dashboard/marketing/ads/${a.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/ads/[id]/page.tsx` |
| BVT-0023 | Social post row link (dynamic id) | `/dashboard/marketing/social-media/${a.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/social-media/[id]/page.tsx` |
| BVT-0024 | Segment row link (dynamic id) | `/dashboard/marketing/segments/${s.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/segments/[id]/page.tsx` |
| BVT-0025 | Influencer row link (dynamic id) | `/dashboard/marketing/influencers/${i.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/influencers/[id]/page.tsx` |
| BVT-0026 | Visit row link (dynamic id) | `/dashboard/marketing/visits/${v.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/visits/[id]/page.tsx` |
| BVT-0027 | Brand spend row link (dynamic id) | `/dashboard/marketing/brand-spend/${b.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/marketing/brand-spend/[id]/page.tsx` |
| BVT-0028 | TPM promotion row link (dynamic id) | `/dashboard/tpm/promotions/${p.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/tpm/promotions/[id]/page.tsx` |

---

## Supply Chain / Procurement (5 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0029 | PO No (order list) | `/dashboard/procurement/orders/${p.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/procurement/orders/[id]/page.tsx` |
| BVT-0030 | PO No (deliveries, po_id) | `/dashboard/procurement/orders/${a.po_id}` | FOUND | 674b6c5 | same as BVT-0029 |
| BVT-0031 | PO No (deliveries receipt, po_id) | `/dashboard/procurement/orders/${r.po_id}` | FOUND | 674b6c5 | same as BVT-0029 |
| BVT-0032 | Landed cost row link (dynamic id) | `/dashboard/landed-cost/${doc.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/landed-cost/[id]/page.tsx` |
| BVT-0033 | View (supplier account) | `/dashboard/supplier-portal/accounts/${a.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/supplier-portal/accounts/[id]/page.tsx` |

---

## Manufacturing / Production (3 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0034 | Production order row (dynamic id) | `/dashboard/production/orders/${o.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/production/orders/[id]/page.tsx` |
| BVT-0035 | Execution order row (dynamic id) | `/dashboard/production-execution/${o.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/production-execution/[id]/page.tsx` |
| BVT-0036 | Project row link (dynamic id) | `/dashboard/projects/${p.id}` | FOUND | 8e21ed6 | `frontend/src/app/dashboard/projects/[id]/page.tsx` |

---

## Factory Operations / Quality (2 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0037 | Inspection No (quality report row) | `/dashboard/quality/${i.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/quality/[id]/page.tsx` |
| BVT-0038 | Brand asset row link (dynamic id) | `/dashboard/brand-assets/${a.id}` | FOUND | de74736 | `frontend/src/app/dashboard/brand-assets/[id]/page.tsx` |

---

## Commercial / Sales (9 items)

| ID | Label | Target | Deep Search | Git Commit | Git Path |
|----|-------|--------|-------------|------------|----------|
| BVT-0039 | Order No | `/dashboard/sales/orders/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/sales/orders/[id]/page.tsx` |
| BVT-0040 | Invoice No | `/dashboard/sales/invoices/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/sales/invoices/[id]/page.tsx` |
| BVT-0041 | Shipment No | `/dashboard/sales/shipments/${r.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/sales/shipments/[id]/page.tsx` |
| BVT-0042 | Price list row link (dynamic id) | `/dashboard/price-lists/${h.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/price-lists/[id]/page.tsx` |
| BVT-0043 | Contract row link (dynamic id) | `/dashboard/contracts/list/${c.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/contracts/list/[id]/page.tsx` |
| BVT-0044 | Template row link (dynamic id) | `/dashboard/recurring-orders/templates/${t.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/recurring-orders/templates/[id]/page.tsx` |
| BVT-0045 | Secondary sales row link (dynamic id) | `/dashboard/secondary-sales/${h.id}` | NOT_FOUND | Never existed. Backend secondary_sales.py present. |
| BVT-0046 | Van row link (dynamic id) | `/dashboard/van-sales/vans/${v.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/van-sales/vans/[id]/page.tsx` |
| BVT-0047 | Manage (portal account) | `/dashboard/portal/accounts/${acc.id}` | FOUND | 674b6c5 | `frontend/src/app/dashboard/portal/accounts/[id]/page.tsx` |

---

## Not Found Items Detail

| ID | Target | Why Not Found | Proposed Fix |
|----|--------|---------------|--------------|
| BVT-0004 | `/dashboard/production/quality` | Typo — real page is `production/quality-control` | LINK_TO_EXISTING_PAGE — update href |
| BVT-0009 | `/dashboard/nps/surveys` | Never existed in any commit | NEW_DESIGN — real nps/surveys page OR link to `/dashboard/marketing?tab=surveys` |
| BVT-0014 | `/dashboard/knowledge-base/categories` | Never existed in any commit | NEW_DESIGN — workspace subview tab OR new categories page |
| BVT-0045 | `/dashboard/secondary-sales/${h.id}` | Never existed in any commit | NEW_DESIGN — drawer detail OR new [id] page using secondary_sales.py backend |
