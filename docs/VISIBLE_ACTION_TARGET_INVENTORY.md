# Visible Action Target Inventory

**Date:** 2026-05-21
**Total targets found:** 487
**Working:** 484
**Broken:** 3 (3 unique)

## By Module

| Module | Working | Broken | Total |
|--------|---------|--------|-------|
| Administration | 17 | 0 | 17 |
| Other | 14 | 0 | 14 |
| Intelligence / Analytics | 26 | 0 | 26 |
| Documents & Communication | 29 | 1 | 30 |
| Commercial / CRM | 14 | 1 | 15 |
| Finance | 64 | 0 | 64 |
| HR & Payroll | 42 | 0 | 42 |
| Administration / Integrations | 11 | 0 | 11 |
| Supply Chain / Inventory | 25 | 0 | 25 |
| Logistics | 7 | 0 | 7 |
| Commercial / Marketing | 38 | 0 | 38 |
| Manufacturing / Planning | 21 | 0 | 21 |
| Supply Chain / Procurement | 24 | 0 | 24 |
| Manufacturing / Production | 25 | 0 | 25 |
| Factory Operations / Quality | 16 | 0 | 16 |
| Commercial / Sales | 41 | 1 | 42 |
| Factory Operations / Utilities | 70 | 0 | 70 |

## All Broken Targets (first 50)

| Source File | Visible Via | Target | Reason |
|------------|-------------|--------|--------|
| `nps/page.tsx` | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | middleware_redirect |
| `knowledge-base/page.tsx` | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | no_route_file |
| `secondary-sales/page.tsx` | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | no_route_file |
