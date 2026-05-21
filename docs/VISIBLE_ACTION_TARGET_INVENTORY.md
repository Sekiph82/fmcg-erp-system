# Visible Action Target Inventory

**Date:** 2026-05-21
**Total targets found:** 487
**Working:** 357
**Broken:** 130 (102 unique)

## By Module

| Module | Working | Broken | Total |
|--------|---------|--------|-------|
| Administration | 11 | 6 | 17 |
| Other | 13 | 1 | 14 |
| Intelligence / Analytics | 18 | 8 | 26 |
| Documents & Communication | 20 | 10 | 30 |
| Commercial / CRM | 4 | 11 | 15 |
| Finance | 53 | 11 | 64 |
| HR & Payroll | 33 | 9 | 42 |
| Administration / Integrations | 10 | 1 | 11 |
| Supply Chain / Inventory | 24 | 1 | 25 |
| Logistics | 6 | 1 | 7 |
| Commercial / Marketing | 24 | 14 | 38 |
| Manufacturing / Planning | 19 | 2 | 21 |
| Supply Chain / Procurement | 13 | 11 | 24 |
| Manufacturing / Production | 20 | 5 | 25 |
| Factory Operations / Quality | 11 | 5 | 16 |
| Commercial / Sales | 23 | 19 | 42 |
| Factory Operations / Utilities | 55 | 15 | 70 |

## All Broken Targets (first 50)

| Source File | Visible Via | Target | Reason |
|------------|-------------|--------|--------|
| `users/page.tsx` | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | middleware_redirect |
| `roles/page.tsx` | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/ai` | middleware_redirect |
| `ai/compliance/page.tsx` | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | no_route_file |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/inventory` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/production` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/procurement` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/sales` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/finance` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/payments` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/marketing` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/ai` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/reports` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/ai` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/reports` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/ai` | middleware_redirect |
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
| `finance/accounting/page.tsx` | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/controls` | middleware_redirect |
| `bank-reconciliation/page.tsx` | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/ai` | middleware_redirect |
| `bank-reconciliation/page.tsx` | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements/${s.id` | middleware_redirect |
| `invoice-match/page.tsx` | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/ai` | middleware_redirect |
| `invoice-match/page.tsx` | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/${m.id` | middleware_redirect |
| `fixed-assets/page.tsx` | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/ai` | middleware_redirect |
| `dimensions/page.tsx` | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/ai` | middleware_redirect |
| `dunning/page.tsx` | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases/${c.id` | middleware_redirect |
| `tax/page.tsx` | /dashboard/finance?tab=TaxPage | `/dashboard/tax/reports` | middleware_redirect |
| `expenses/page.tsx` | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/reports` | middleware_redirect |
| `expenses/page.tsx` | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/ai` | middleware_redirect |
| `recruitment/page.tsx` | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/reports` | middleware_redirect |
| `recruitment/page.tsx` | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/ai` | middleware_redirect |
| `ess/page.tsx` | /dashboard/hr?tab=ESSPage | `/dashboard/ess/ai` | middleware_redirect |
| `appraisals/page.tsx` | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/reports` | middleware_redirect |
| `appraisals/page.tsx` | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/ai` | middleware_redirect |
| `training/page.tsx` | /dashboard/hr?tab=TrainingPage | `/dashboard/training/reports` | middleware_redirect |
| `training/page.tsx` | /dashboard/hr?tab=TrainingPage | `/dashboard/training/ai` | middleware_redirect |
| `timesheets/page.tsx` | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/reports` | middleware_redirect |
| `timesheets/page.tsx` | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/ai` | middleware_redirect |
| `webhooks/page.tsx` | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/reports` | middleware_redirect |
| `traceability/page.tsx` | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls/${r.id` | middleware_redirect |
| `fleet/page.tsx` | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/reports` | middleware_redirect |
