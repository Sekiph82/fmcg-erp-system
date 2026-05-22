# Visible Action Target Inventory

**Date:** 2026-05-21
**Total targets found:** 487
**Working:** 420
**Broken:** 67 (47 unique)

## By Module

| Module | Working | Broken | Total |
|--------|---------|--------|-------|
| Administration | 12 | 5 | 17 |
| Other | 13 | 1 | 14 |
| Intelligence / Analytics | 26 | 0 | 26 |
| Documents & Communication | 24 | 6 | 30 |
| Commercial / CRM | 4 | 11 | 15 |
| Finance | 61 | 3 | 64 |
| HR & Payroll | 42 | 0 | 42 |
| Administration / Integrations | 11 | 0 | 11 |
| Supply Chain / Inventory | 24 | 1 | 25 |
| Logistics | 7 | 0 | 7 |
| Commercial / Marketing | 25 | 13 | 38 |
| Manufacturing / Planning | 21 | 0 | 21 |
| Supply Chain / Procurement | 17 | 7 | 24 |
| Manufacturing / Production | 20 | 5 | 25 |
| Factory Operations / Quality | 13 | 3 | 16 |
| Commercial / Sales | 30 | 12 | 42 |
| Factory Operations / Utilities | 70 | 0 | 70 |

## All Broken Targets (first 50)

| Source File | Visible Via | Target | Reason |
|------------|-------------|--------|--------|
| `users/page.tsx` | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | middleware_redirect |
| `roles/page.tsx` | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect |
| `ai/compliance/page.tsx` | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | no_route_file |
| `crm/pipeline/page.tsx` | /dashboard/crm?tab=CRMPipelinePage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/leads/page.tsx` | /dashboard/crm?tab=CRMLeadsPage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/opportunities/page.tsx` | /dashboard/crm?tab=CRMOppsPage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/activities/page.tsx` | /dashboard/crm?tab=CRMActivitiesPage | `/dashboard/crm/records/${act.crm_record_id` | middleware_redirect |
| `nps/page.tsx` | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | middleware_redirect |
| `surveys/page.tsx` | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/${s.id` | middleware_redirect |
| `documents/compliance/page.tsx` | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/documents/${d.id` | no_route_file |
| `documents/expiring/page.tsx` | /dashboard/documents?tab=DocsExpiringPage | `/dashboard/documents/${d.id` | no_route_file |
| `knowledge-base/page.tsx` | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/${a.id` | middleware_redirect |
| `knowledge-base/page.tsx` | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | middleware_redirect |
| `bank-reconciliation/page.tsx` | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements/${s.id` | middleware_redirect |
| `invoice-match/page.tsx` | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/${m.id` | middleware_redirect |
| `dunning/page.tsx` | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases/${c.id` | middleware_redirect |
| `traceability/page.tsx` | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls/${r.id` | middleware_redirect |
| `marketing/campaigns/page.tsx` | /dashboard/marketing?tab=MarketingCampaignsPage | `/dashboard/marketing/campaigns/${c.id` | middleware_redirect |
| `marketing/promotions/page.tsx` | /dashboard/marketing?tab=MarketingPromotionsPage | `/dashboard/marketing/promotions/${p.id` | middleware_redirect |
| `marketing/trade-spend/page.tsx` | /dashboard/marketing?tab=MarketingTradeSpendPage | `/dashboard/marketing/trade-spend/${t.id` | middleware_redirect |
| `marketing/ads/page.tsx` | /dashboard/marketing?tab=MarketingAdsPage | `/dashboard/marketing/ads/${a.id` | middleware_redirect |
| `marketing/social-media/page.tsx` | /dashboard/marketing?tab=MarketingSocialPage | `/dashboard/marketing/social-media/${a.id` | middleware_redirect |
| `marketing/segments/page.tsx` | /dashboard/marketing?tab=MarketingSegmentsPage | `/dashboard/marketing/segments/${s.id` | middleware_redirect |
| `marketing/influencers/page.tsx` | /dashboard/marketing?tab=MarketingInfluencersPage | `/dashboard/marketing/influencers/${i.id` | middleware_redirect |
| `marketing/visits/page.tsx` | /dashboard/marketing?tab=MarketingVisitsPage | `/dashboard/marketing/visits/${v.id` | middleware_redirect |
| `marketing/brand-spend/page.tsx` | /dashboard/marketing?tab=MarketingBrandSpendPage | `/dashboard/marketing/brand-spend/${b.id` | middleware_redirect |
| `tpm/page.tsx` | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions/${p.id` | middleware_redirect |
| `procurement/orders/page.tsx` | /dashboard/procurement?tab=ProcurementOrdersPage | `/dashboard/procurement/orders/${p.id}` | no_route_file |
| `procurement/deliveries/page.tsx` | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${a.po_id}` | no_route_file |
| `procurement/deliveries/page.tsx` | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${r.po_id}` | no_route_file |
| `landed-cost/page.tsx` | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/${doc.id` | middleware_redirect |
| `supplier-portal/page.tsx` | /dashboard/procurement?tab=SupplierPortalPage | `/dashboard/supplier-portal/accounts/${a.id` | middleware_redirect |
| `production/orders/page.tsx` | /dashboard/production?tab=ProductionOrdersPage | `/dashboard/production/orders/${o.id}` | middleware_redirect |
| `production-execution/page.tsx` | /dashboard/production?tab=ExecutionPage | `/dashboard/production-execution/${o.id` | middleware_redirect |
| `projects/page.tsx` | /dashboard/production?tab=ProjectsPage | `/dashboard/projects/${p.id}` | middleware_redirect |
| `quality/reports/page.tsx` | /dashboard/quality?tab=QualityReportsPage | `/dashboard/quality/${i.id}` | no_route_file |
| `brand-assets/page.tsx` | /dashboard/quality?tab=BrandAssetsPage | `/dashboard/brand-assets/${a.id` | middleware_redirect |
| `sales/orders/page.tsx` | /dashboard/sales?tab=SalesOrdersPage | `/dashboard/sales/orders/${r.id}` | no_route_file |
| `sales/invoices/page.tsx` | /dashboard/sales?tab=SalesInvoicesPage | `/dashboard/sales/invoices/${r.id}` | no_route_file |
| `sales/shipments/page.tsx` | /dashboard/sales?tab=SalesShipmentsPage | `/dashboard/sales/shipments/${r.id}` | no_route_file |
| `price-lists/page.tsx` | /dashboard/sales?tab=PriceListsPage | `/dashboard/price-lists/${h.id` | middleware_redirect |
| `contracts/page.tsx` | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/list/${c.id` | middleware_redirect |
| `recurring-orders/page.tsx` | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates/${t.id` | middleware_redirect |
| `secondary-sales/page.tsx` | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | middleware_redirect |
| `van-sales/page.tsx` | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans/${v.id` | middleware_redirect |
| `portal/page.tsx` | /dashboard/sales?tab=PortalPage | `/dashboard/portal/accounts/${acc.id` | middleware_redirect |
