# Visible Broken Action Targets

**Date:** 2026-05-21
**Total:** 48

## Statistics

| Metric | Count |
|--------|-------|
| Critical | 0 |
| High | 48 |
| Medium | 0 |
| Git: real page found | 0 |
| Recommendation: RESTORE FROM GIT | 0 |
| Recommendation: CONVERT TO SUBVIEW | 38 |
| Recommendation: CREATE NEW PAGE | 10 |

## Administration (3)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0001 | users/page.tsx | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0002 | roles/page.tsx | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0003 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Other (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0004 | ai/compliance/page.tsx | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |

## Commercial / CRM (6)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0005 | crm/pipeline/page.tsx | /dashboard/crm?tab=CRMPipelinePage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0006 | crm/leads/page.tsx | /dashboard/crm?tab=CRMLeadsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0007 | crm/opportunities/page.tsx | /dashboard/crm?tab=CRMOppsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0008 | crm/activities/page.tsx | /dashboard/crm?tab=CRMActivitiesPage | `/dashboard/crm/records/${act.crm_record_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0009 | nps/page.tsx | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0010 | surveys/page.tsx | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Documents & Communication (4)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0011 | documents/compliance/page.tsx | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0012 | documents/expiring/page.tsx | /dashboard/documents?tab=DocsExpiringPage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0013 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0014 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Finance (4)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0015 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/controls` | high | STUB | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0016 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0017 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/${m.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0018 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Supply Chain / Inventory (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0019 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Marketing (10)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0020 | marketing/campaigns/page.tsx | /dashboard/marketing?tab=MarketingCampaignsPage | `/dashboard/marketing/campaigns/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0021 | marketing/promotions/page.tsx | /dashboard/marketing?tab=MarketingPromotionsPage | `/dashboard/marketing/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0022 | marketing/trade-spend/page.tsx | /dashboard/marketing?tab=MarketingTradeSpendPage | `/dashboard/marketing/trade-spend/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0023 | marketing/ads/page.tsx | /dashboard/marketing?tab=MarketingAdsPage | `/dashboard/marketing/ads/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0024 | marketing/social-media/page.tsx | /dashboard/marketing?tab=MarketingSocialPage | `/dashboard/marketing/social-media/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0025 | marketing/segments/page.tsx | /dashboard/marketing?tab=MarketingSegmentsPage | `/dashboard/marketing/segments/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0026 | marketing/influencers/page.tsx | /dashboard/marketing?tab=MarketingInfluencersPage | `/dashboard/marketing/influencers/${i.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0027 | marketing/visits/page.tsx | /dashboard/marketing?tab=MarketingVisitsPage | `/dashboard/marketing/visits/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0028 | marketing/brand-spend/page.tsx | /dashboard/marketing?tab=MarketingBrandSpendPage | `/dashboard/marketing/brand-spend/${b.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0029 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Supply Chain / Procurement (5)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0030 | procurement/orders/page.tsx | /dashboard/procurement?tab=ProcurementOrdersPage | `/dashboard/procurement/orders/${p.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0031 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${a.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0032 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${r.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0033 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/${doc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0034 | supplier-portal/page.tsx | /dashboard/procurement?tab=SupplierPortalPage | `/dashboard/supplier-portal/accounts/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Manufacturing / Production (3)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0035 | production/orders/page.tsx | /dashboard/production?tab=ProductionOrdersPage | `/dashboard/production/orders/${o.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0036 | production-execution/page.tsx | /dashboard/production?tab=ExecutionPage | `/dashboard/production-execution/${o.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0037 | projects/page.tsx | /dashboard/production?tab=ProjectsPage | `/dashboard/projects/${p.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Quality (2)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0038 | quality/reports/page.tsx | /dashboard/quality?tab=QualityReportsPage | `/dashboard/quality/${i.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0039 | brand-assets/page.tsx | /dashboard/quality?tab=BrandAssetsPage | `/dashboard/brand-assets/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Sales (9)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0040 | sales/orders/page.tsx | /dashboard/sales?tab=SalesOrdersPage | `/dashboard/sales/orders/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0041 | sales/invoices/page.tsx | /dashboard/sales?tab=SalesInvoicesPage | `/dashboard/sales/invoices/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0042 | sales/shipments/page.tsx | /dashboard/sales?tab=SalesShipmentsPage | `/dashboard/sales/shipments/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0043 | price-lists/page.tsx | /dashboard/sales?tab=PriceListsPage | `/dashboard/price-lists/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0044 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/list/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0045 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0046 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0047 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0048 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/accounts/${acc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

