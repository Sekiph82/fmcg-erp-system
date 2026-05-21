# Visible Broken Action Targets

**Date:** 2026-05-21
**Total:** 102

## Statistics

| Metric | Count |
|--------|-------|
| Critical | 0 |
| High | 48 |
| Medium | 54 |
| Git: real page found | 54 |
| Recommendation: RESTORE FROM GIT | 54 |
| Recommendation: CONVERT TO SUBVIEW | 38 |
| Recommendation: CREATE NEW PAGE | 10 |

## Administration (4)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0001 | users/page.tsx | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0002 | roles/page.tsx | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0003 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0004 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Other (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0005 | ai/compliance/page.tsx | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |

## Intelligence / Analytics (8)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0006 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/inventory` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0007 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/production` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0008 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/procurement` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0009 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/sales` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0010 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/finance` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0011 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/payments` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0012 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/marketing` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0013 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Documents & Communication (8)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0014 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0015 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0016 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0017 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0024 | documents/compliance/page.tsx | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0025 | documents/expiring/page.tsx | /dashboard/documents?tab=DocsExpiringPage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0026 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0027 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / CRM (6)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0018 | crm/pipeline/page.tsx | /dashboard/crm?tab=CRMPipelinePage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0019 | crm/leads/page.tsx | /dashboard/crm?tab=CRMLeadsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0020 | crm/opportunities/page.tsx | /dashboard/crm?tab=CRMOppsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0021 | crm/activities/page.tsx | /dashboard/crm?tab=CRMActivitiesPage | `/dashboard/crm/records/${act.crm_record_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0022 | nps/page.tsx | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0023 | surveys/page.tsx | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Finance (11)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0028 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/controls` | high | STUB | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0029 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0030 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0031 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0032 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/${m.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0033 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0034 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0035 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0036 | tax/page.tsx | /dashboard/finance?tab=TaxPage | `/dashboard/tax/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0037 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0038 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## HR & Payroll (9)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0039 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0040 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0041 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0042 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0043 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0044 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0045 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0046 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0047 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Administration / Integrations (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0048 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Supply Chain / Inventory (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0049 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Logistics (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0050 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Commercial / Marketing (11)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0051 | marketing/campaigns/page.tsx | /dashboard/marketing?tab=MarketingCampaignsPage | `/dashboard/marketing/campaigns/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0052 | marketing/promotions/page.tsx | /dashboard/marketing?tab=MarketingPromotionsPage | `/dashboard/marketing/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0053 | marketing/trade-spend/page.tsx | /dashboard/marketing?tab=MarketingTradeSpendPage | `/dashboard/marketing/trade-spend/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0054 | marketing/ads/page.tsx | /dashboard/marketing?tab=MarketingAdsPage | `/dashboard/marketing/ads/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0055 | marketing/social-media/page.tsx | /dashboard/marketing?tab=MarketingSocialPage | `/dashboard/marketing/social-media/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0056 | marketing/segments/page.tsx | /dashboard/marketing?tab=MarketingSegmentsPage | `/dashboard/marketing/segments/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0057 | marketing/influencers/page.tsx | /dashboard/marketing?tab=MarketingInfluencersPage | `/dashboard/marketing/influencers/${i.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0058 | marketing/visits/page.tsx | /dashboard/marketing?tab=MarketingVisitsPage | `/dashboard/marketing/visits/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0059 | marketing/brand-spend/page.tsx | /dashboard/marketing?tab=MarketingBrandSpendPage | `/dashboard/marketing/brand-spend/${b.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0060 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0061 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Manufacturing / Planning (2)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0062 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0063 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Supply Chain / Procurement (8)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0064 | procurement/orders/page.tsx | /dashboard/procurement?tab=ProcurementOrdersPage | `/dashboard/procurement/orders/${p.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0065 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${a.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0066 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${r.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0067 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=SuggestionsPage | `/dashboard/procurement-suggestion/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0068 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0069 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0070 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/${doc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0071 | supplier-portal/page.tsx | /dashboard/procurement?tab=SupplierPortalPage | `/dashboard/supplier-portal/accounts/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Manufacturing / Production (3)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0072 | production/orders/page.tsx | /dashboard/production?tab=ProductionOrdersPage | `/dashboard/production/orders/${o.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0073 | production-execution/page.tsx | /dashboard/production?tab=ExecutionPage | `/dashboard/production-execution/${o.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0074 | projects/page.tsx | /dashboard/production?tab=ProjectsPage | `/dashboard/projects/${p.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Quality (4)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0075 | quality/reports/page.tsx | /dashboard/quality?tab=QualityReportsPage | `/dashboard/quality/${i.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0076 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0077 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0078 | brand-assets/page.tsx | /dashboard/quality?tab=BrandAssetsPage | `/dashboard/brand-assets/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Sales (16)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0079 | sales/orders/page.tsx | /dashboard/sales?tab=SalesOrdersPage | `/dashboard/sales/orders/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0080 | sales/invoices/page.tsx | /dashboard/sales?tab=SalesInvoicesPage | `/dashboard/sales/invoices/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0081 | sales/shipments/page.tsx | /dashboard/sales?tab=SalesShipmentsPage | `/dashboard/sales/shipments/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0082 | price-lists/page.tsx | /dashboard/sales?tab=PriceListsPage | `/dashboard/price-lists/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0083 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/list/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0084 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0085 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0086 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0087 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0088 | commissions/page.tsx | /dashboard/sales?tab=CommissionsPage | `/dashboard/commissions/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0089 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0090 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0091 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0092 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0093 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0094 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/accounts/${acc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Utilities (8)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0095 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/daily-consumption` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0096 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/equipment-efficiency` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0097 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/treatment` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0098 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/cost-allocation` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0099 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/load-analysis` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0100 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/anomalies` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0101 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/sustainability` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0102 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

