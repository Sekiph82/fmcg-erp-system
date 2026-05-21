# Visible Broken Action Targets

**Date:** 2026-05-21
**Total:** 353

## Statistics

| Metric | Count |
|--------|-------|
| Critical | 26 |
| High | 272 |
| Medium | 55 |
| Git: real page found | 305 |
| Recommendation: RESTORE FROM GIT | 305 |
| Recommendation: CONVERT TO SUBVIEW | 38 |
| Recommendation: CREATE NEW PAGE | 10 |

## Administration (13)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0001 | users/page.tsx | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0002 | roles/page.tsx | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0003 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/new-field` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0004 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/fields` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0005 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0006 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/form-builder` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0007 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/workflow-rules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0008 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/values` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0009 | custom-fields/page.tsx | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0010 | mobile/page.tsx | /dashboard/admin?tab=MobilePage | `/dashboard/mobile/approvals` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0011 | mobile/page.tsx | /dashboard/admin?tab=MobilePage | `/dashboard/mobile/devices` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0012 | mobile/page.tsx | /dashboard/admin?tab=MobilePage | `/dashboard/approvals` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0013 | mobile/page.tsx | /dashboard/admin?tab=MobilePage | `/dashboard/notification-center` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Other (2)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0014 | ai/compliance/page.tsx | /dashboard/ai?tab=AICompliancePage | `/dashboard/tax` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0015 | ai/compliance/page.tsx | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |

## Intelligence / Analytics (15)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0016 | analytics/production/page.tsx | /dashboard/analytics?tab=AnalyticsProductionPage | `/dashboard/production/orders` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0017 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/inventory` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0018 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/production` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0019 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/procurement` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0020 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/sales` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0021 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/finance` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0022 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/payments` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0023 | reports/page.tsx | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/marketing` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0024 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/catalog` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0025 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/builder` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0026 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/saved` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0027 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/viewer` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0028 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/dashboards` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0029 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/schedules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0030 | report-builder/page.tsx | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Documents & Communication (22)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0031 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/feed` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0032 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/search` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0033 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0034 | chatter/page.tsx | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0035 | calendar/page.tsx | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/view` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0036 | calendar/page.tsx | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/new-event` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0037 | calendar/page.tsx | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/resources` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0038 | calendar/page.tsx | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/availability` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0039 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/list` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0040 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/preferences` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0041 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/templates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0042 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/schedules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0043 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0044 | notification-center/page.tsx | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0052 | documents/compliance/page.tsx | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/documents/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0053 | documents/compliance/page.tsx | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0054 | documents/compliance/page.tsx | /dashboard/documents?tab=DocsCompliancePage | `/dashboard/esign` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0055 | documents/expiring/page.tsx | /dashboard/documents?tab=DocsExpiringPage | `/dashboard/documents/${d.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0056 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0057 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0058 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/articles` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0059 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/articles/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Commercial / CRM (7)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0045 | crm/pipeline/page.tsx | /dashboard/crm?tab=CRMPipelinePage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0046 | crm/leads/page.tsx | /dashboard/crm?tab=CRMLeadsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0047 | crm/opportunities/page.tsx | /dashboard/crm?tab=CRMOppsPage | `/dashboard/crm/records/${rec.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0048 | crm/activities/page.tsx | /dashboard/crm?tab=CRMActivitiesPage | `/dashboard/crm/records/${act.crm_record_id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0049 | nps/page.tsx | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0050 | surveys/page.tsx | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0051 | surveys/page.tsx | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Finance (57)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0060 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/customers-ledger` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0061 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/suppliers-ledger` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0062 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/sales-invoices` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0063 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/purchase-invoices` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0064 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/payments` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0065 | finance/accounting/page.tsx | /dashboard/finance?tab=FinanceAccountingPage | `/dashboard/finance/accounting/controls` | high | STUB | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0066 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/import` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0067 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0068 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/open-items` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0069 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/balance` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0070 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/rules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0071 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0072 | bank-reconciliation/page.tsx | /dashboard/finance?tab=BankReconPage | `/dashboard/bank-reconciliation/statements/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0073 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/review-queue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0074 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/matches` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0075 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/blocked` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0076 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/duplicates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0077 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0078 | invoice-match/page.tsx | /dashboard/finance?tab=InvoiceMatchPage | `/dashboard/invoice-match/${m.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0079 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/assets` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0080 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/categories` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0081 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/depreciation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0082 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/posting` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0083 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/disposal` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0084 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/transfer` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0085 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/import` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0086 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0087 | fixed-assets/page.tsx | /dashboard/finance?tab=FixedAssetsPage | `/dashboard/fixed-assets/assets/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0088 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/types` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0089 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/values` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0090 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/cost-centers` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0091 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/allocations` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0092 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/allocation-run` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0093 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/validation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0094 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/defaults` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0095 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/reclassify` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0096 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/completeness` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0097 | dimensions/page.tsx | /dashboard/finance?tab=DimensionsPage | `/dashboard/dimensions/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0098 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/aging` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0099 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/workqueue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0100 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/credit-holds` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0101 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/policies` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0102 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0103 | dunning/page.tsx | /dashboard/finance?tab=DunningPage | `/dashboard/dunning/cases/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0104 | tax/page.tsx | /dashboard/finance?tab=TaxPage | `/dashboard/tax/rules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0105 | tax/page.tsx | /dashboard/finance?tab=TaxPage | `/dashboard/tax/regulatory` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0106 | tax/page.tsx | /dashboard/finance?tab=TaxPage | `/dashboard/tax/transactions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0107 | tax/page.tsx | /dashboard/finance?tab=TaxPage | `/dashboard/tax/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0108 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/claims` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0109 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/claims/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0110 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/approval` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0111 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/reimbursement` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0112 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/advances` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0113 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/categories` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0114 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/policies` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0115 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0116 | expenses/page.tsx | /dashboard/finance?tab=ExpensesPage | `/dashboard/expenses/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## HR & Payroll (41)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0117 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/requisitions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0118 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/requisitions/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0119 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/candidates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0120 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/pipeline` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0121 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/interviews` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0122 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/offers` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0123 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/stages` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0124 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0125 | recruitment/page.tsx | /dashboard/hr?tab=RecruitmentPage | `/dashboard/recruitment/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0126 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/profile` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0127 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/leave` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0128 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/attendance` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0129 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/documents` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0130 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/requests` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0131 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/notifications` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0132 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0133 | ess/page.tsx | /dashboard/hr?tab=ESSPage | `/dashboard/ess/admin` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0134 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/periods` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0135 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/templates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0136 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/records` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0137 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/records/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0138 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/self-review` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0139 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/manager-queue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0140 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/hr-review` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0141 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/development-plans` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0142 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0143 | appraisals/page.tsx | /dashboard/hr?tab=AppraisalsPage | `/dashboard/appraisals/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0144 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/programs` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0145 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/sessions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0146 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/skill-matrix` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0147 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/assignments` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0148 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/certifications` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0149 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/feedback` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0150 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0151 | training/page.tsx | /dashboard/hr?tab=TrainingPage | `/dashboard/training/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0152 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/my-timesheets` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0153 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/time-entry` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0154 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/weekly-view` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0155 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/approval-queue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0156 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0157 | timesheets/page.tsx | /dashboard/hr?tab=TimesheetsPage | `/dashboard/timesheets/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Administration / Integrations (9)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0158 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/definitions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0159 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/subscriptions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0160 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/deliveries` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0161 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/dead-letter` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0162 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/inbound` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0163 | webhooks/page.tsx | /dashboard/integrations?tab=WebhooksPage | `/dashboard/webhooks/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0164 | developer/page.tsx | /dashboard/integrations?tab=DeveloperPage | `/dashboard/developer/keys` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0165 | developer/page.tsx | /dashboard/integrations?tab=DeveloperPage | `/dashboard/developer/graphql` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0166 | developer/page.tsx | /dashboard/integrations?tab=DeveloperPage | `/dashboard/webhooks` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Supply Chain / Inventory (24)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0167 | cycle-count/page.tsx | /dashboard/inventory?tab=CycleCountPage | `/dashboard/cycle-count/plans` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0168 | cycle-count/page.tsx | /dashboard/inventory?tab=CycleCountPage | `/dashboard/cycle-count/tasks` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0169 | cycle-count/page.tsx | /dashboard/inventory?tab=CycleCountPage | `/dashboard/cycle-count/entries` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0170 | cycle-count/page.tsx | /dashboard/inventory?tab=CycleCountPage | `/dashboard/cycle-count/variances` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0171 | cycle-count/page.tsx | /dashboard/inventory?tab=CycleCountPage | `/dashboard/cycle-count/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0172 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/fefo-config` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0173 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/lot-aging` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0174 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/near-expiry` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0175 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/expired` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0176 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/retest-queue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0177 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/shipment-validation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0178 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/production-validation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0179 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/compliance` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0180 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/disposition` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0181 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/customer-rules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0182 | shelf-life/page.tsx | /dashboard/inventory?tab=ShelfLifePage | `/dashboard/shelf-life/bulk-hold-monitor` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0183 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0184 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/recalls/${r.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0185 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/search` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0186 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/backward` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0187 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/forward` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0188 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/genealogy` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0189 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/mock-recall` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0190 | traceability/page.tsx | /dashboard/inventory?tab=TraceabilityPage | `/dashboard/traceability/regulatory` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Logistics (7)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0191 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/vehicles` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0192 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/drivers` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0193 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/trips` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0194 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/fuel` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0195 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/maintenance` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0196 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/incidents` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0197 | fleet/page.tsx | /dashboard/logistics?tab=FleetPage | `/dashboard/fleet/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Commercial / Marketing (30)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0198 | marketing/campaigns/page.tsx | /dashboard/marketing?tab=MarketingCampaignsPage | `/dashboard/marketing/campaigns/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0199 | marketing/campaigns/page.tsx | /dashboard/marketing?tab=MarketingCampaignsPage | `/dashboard/marketing/campaigns/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0200 | marketing/promotions/page.tsx | /dashboard/marketing?tab=MarketingPromotionsPage | `/dashboard/marketing/promotions/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0201 | marketing/promotions/page.tsx | /dashboard/marketing?tab=MarketingPromotionsPage | `/dashboard/marketing/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0202 | marketing/trade-spend/page.tsx | /dashboard/marketing?tab=MarketingTradeSpendPage | `/dashboard/marketing/trade-spend/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0203 | marketing/trade-spend/page.tsx | /dashboard/marketing?tab=MarketingTradeSpendPage | `/dashboard/marketing/trade-spend/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0204 | marketing/ads/page.tsx | /dashboard/marketing?tab=MarketingAdsPage | `/dashboard/marketing/ads/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0205 | marketing/ads/page.tsx | /dashboard/marketing?tab=MarketingAdsPage | `/dashboard/marketing/ads/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0206 | marketing/social-media/page.tsx | /dashboard/marketing?tab=MarketingSocialPage | `/dashboard/marketing/social-media/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0207 | marketing/social-media/page.tsx | /dashboard/marketing?tab=MarketingSocialPage | `/dashboard/marketing/social-media/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0208 | marketing/segments/page.tsx | /dashboard/marketing?tab=MarketingSegmentsPage | `/dashboard/marketing/segments/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0209 | marketing/segments/page.tsx | /dashboard/marketing?tab=MarketingSegmentsPage | `/dashboard/marketing/segments/${s.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0210 | marketing/influencers/page.tsx | /dashboard/marketing?tab=MarketingInfluencersPage | `/dashboard/marketing/influencers/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0211 | marketing/influencers/page.tsx | /dashboard/marketing?tab=MarketingInfluencersPage | `/dashboard/marketing/influencers/${i.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0212 | marketing/ecommerce/page.tsx | /dashboard/marketing?tab=MarketingEcommercePage | `/dashboard/marketing/ecommerce/stores` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0213 | marketing/visits/page.tsx | /dashboard/marketing?tab=MarketingVisitsPage | `/dashboard/marketing/visits/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0214 | marketing/visits/page.tsx | /dashboard/marketing?tab=MarketingVisitsPage | `/dashboard/marketing/visits/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0215 | marketing/brand-spend/page.tsx | /dashboard/marketing?tab=MarketingBrandSpendPage | `/dashboard/marketing/brand-spend/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0216 | marketing/brand-spend/page.tsx | /dashboard/marketing?tab=MarketingBrandSpendPage | `/dashboard/marketing/brand-spend/${b.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0217 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/plans/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0218 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0219 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0220 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/promotions/${p.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0221 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/calendar` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0222 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/budget` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0223 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/claims` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0224 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/roi` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0225 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/settlement` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0226 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/plans` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0227 | tpm/page.tsx | /dashboard/marketing?tab=TPMPage | `/dashboard/tpm/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Manufacturing / Planning (8)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0228 | mrp/page.tsx | /dashboard/planning?tab=MRPPage | `/dashboard/mrp/forecast` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0229 | mrp/page.tsx | /dashboard/planning?tab=MRPPage | `/dashboard/mrp/suggestions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0230 | mrp/page.tsx | /dashboard/planning?tab=MRPPage | `/dashboard/mrp/run` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0231 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/boards` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0232 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/view` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0233 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/cards` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0234 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0235 | kanban/page.tsx | /dashboard/planning?tab=KanbanPage | `/dashboard/kanban/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |

## Supply Chain / Procurement (17)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0236 | procurement/orders/page.tsx | /dashboard/procurement?tab=ProcurementOrdersPage | `/dashboard/procurement/orders/${p.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0237 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${a.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0238 | procurement/deliveries/page.tsx | /dashboard/procurement?tab=ProcurementDeliveriesPage | `/dashboard/procurement/orders/${r.po_id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0239 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=SuggestionsPage | `/dashboard/procurement-suggestion/suggestions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0240 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=SuggestionsPage | `/dashboard/procurement-suggestion/groups` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0241 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=SuggestionsPage | `/dashboard/procurement-suggestion/supplier-prices` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0242 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=SuggestionsPage | `/dashboard/procurement-suggestion/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0243 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/locations` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0244 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/orders` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0245 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/stock` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0246 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/yield` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0247 | subcontracting/page.tsx | /dashboard/procurement?tab=SubcontractingPage | `/dashboard/subcontracting/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0248 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0249 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0250 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/documents` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0251 | landed-cost/page.tsx | /dashboard/procurement?tab=LandedCostPage | `/dashboard/landed-cost/${doc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0252 | supplier-portal/page.tsx | /dashboard/procurement?tab=SupplierPortalPage | `/dashboard/supplier-portal/accounts/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Manufacturing / Production (22)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0253 | production/orders/page.tsx | /dashboard/production?tab=ProductionOrdersPage | `/dashboard/production/orders/${o.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0254 | production-execution/page.tsx | /dashboard/production?tab=ExecutionPage | `/dashboard/production-execution/work-orders` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0255 | production-execution/page.tsx | /dashboard/production?tab=ExecutionPage | `/dashboard/production-execution/${o.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0256 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/machines` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0257 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/operators` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0258 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/teams` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0259 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/runtime` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0260 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/performance` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0261 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/downtime` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0262 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/costing` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0263 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/certs` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0264 | machine-ops/page.tsx | /dashboard/production?tab=MachineOpsPage | `/dashboard/machine-ops/assignment` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0265 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/issue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0266 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/wip-transfer` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0267 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/bulk-transfer` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0268 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/fg-receipt` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0269 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/reservations` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0270 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/tanks` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0271 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/returns` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0272 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/reconciliation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0273 | material-flow/page.tsx | /dashboard/production?tab=MaterialFlowPage | `/dashboard/material-flow/history` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0274 | projects/page.tsx | /dashboard/production?tab=ProjectsPage | `/dashboard/projects/${p.id}` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Quality (15)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0275 | quality/reports/page.tsx | /dashboard/quality?tab=QualityReportsPage | `/dashboard/quality/${i.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0276 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/inspections` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0277 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/templates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0278 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/haccp` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0279 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/ccp` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0280 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/deviations` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0281 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/corrective-actions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0282 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/quarantine` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0283 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/allergen` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0284 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0285 | qms/page.tsx | /dashboard/quality?tab=QMSPage | `/dashboard/qms/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0286 | allergen/page.tsx | /dashboard/quality?tab=AllergenPage | `/dashboard/allergen/material-profiles` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0287 | allergen/page.tsx | /dashboard/quality?tab=AllergenPage | `/dashboard/allergen/product-allergens` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0288 | allergen/page.tsx | /dashboard/quality?tab=AllergenPage | `/dashboard/allergen/change-logs` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0289 | brand-assets/page.tsx | /dashboard/quality?tab=BrandAssetsPage | `/dashboard/brand-assets/${a.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Sales (39)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0290 | sales/orders/page.tsx | /dashboard/sales?tab=SalesOrdersPage | `/dashboard/sales/orders/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0291 | sales/invoices/page.tsx | /dashboard/sales?tab=SalesInvoicesPage | `/dashboard/sales/invoices/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0292 | sales/shipments/page.tsx | /dashboard/sales?tab=SalesShipmentsPage | `/dashboard/sales/shipments/${r.id}` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0293 | price-lists/page.tsx | /dashboard/sales?tab=PriceListsPage | `/dashboard/price-lists/approval-queue` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0294 | price-lists/page.tsx | /dashboard/sales?tab=PriceListsPage | `/dashboard/price-lists/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0295 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0296 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/list` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0297 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/list/${c.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0298 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/expiring` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0299 | contracts/page.tsx | /dashboard/sales?tab=ContractsPage | `/dashboard/contracts/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0300 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0301 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0302 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/templates/${t.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0303 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0304 | recurring-orders/page.tsx | /dashboard/sales?tab=RecurringOrdersPage | `/dashboard/recurring-orders/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0305 | commissions/page.tsx | /dashboard/sales?tab=CommissionsPage | `/dashboard/commissions/rules` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0306 | commissions/page.tsx | /dashboard/sales?tab=CommissionsPage | `/dashboard/commissions/transactions` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0307 | commissions/page.tsx | /dashboard/sales?tab=CommissionsPage | `/dashboard/commissions/payouts` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0308 | commissions/page.tsx | /dashboard/sales?tab=CommissionsPage | `/dashboard/commissions/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0309 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/analysis` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0310 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/inventory` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0311 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/upload` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0312 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0313 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans/new` | critical | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0314 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/route` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0315 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/pos` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0316 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/stock` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0317 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/reconciliation` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0318 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0319 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/vans/${v.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0320 | van-sales/page.tsx | /dashboard/sales?tab=VanSalesPage | `/dashboard/van-sales/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0321 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/accounts` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0322 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/drafts` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0323 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/claims` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0324 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/users` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0325 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/activity` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0326 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/ai` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0327 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0328 | portal/page.tsx | /dashboard/sales?tab=PortalPage | `/dashboard/portal/accounts/${acc.id` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Utilities (25)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0329 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/electricity` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0330 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/water` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0331 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/soft-water` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0332 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/boiler` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0333 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/compressor` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0334 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/solar` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0335 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/chemicals` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0336 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/wastewater` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0337 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/utility-cost` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0338 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=KPICenterPage | `/dashboard/utility-management/kpi-center/machine-utility` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0339 | utility-management/alarm-center/page.tsx | /dashboard/utility-management?tab=AlarmCenterPage | `/dashboard/utility-management/kpi-center` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0340 | utility-management/alarm-rules/page.tsx | /dashboard/utility-management?tab=AlarmRulesPage | `/dashboard/utility-management/kpi-center` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0341 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/daily-consumption` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0342 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/equipment-efficiency` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0343 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/treatment` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0344 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/cost-allocation` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0345 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/load-analysis` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0346 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/anomalies` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0347 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=UtilReportsPage | `/dashboard/utility-management/reports/sustainability` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0348 | utility-management/integration/page.tsx | /dashboard/utility-management?tab=UtilIntegrationPage | `/dashboard/utility-management/kpi-center` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0349 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/activities` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0350 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/factors` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0351 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/targets` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0352 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/reports` | medium | REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0353 | esg/page.tsx | /dashboard/utility-management?tab=ESGPage | `/dashboard/esg/intelligence` | high | REAL | RESTORE_OLD_PAGE_FROM_GIT |

