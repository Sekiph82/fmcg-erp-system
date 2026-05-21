# Visible Action Target Inventory

**Date:** 2026-05-21
**Total targets found:** 487
**Working:** 54
**Broken:** 433 (353 unique)

## By Module

| Module | Working | Broken | Total |
|--------|---------|--------|-------|
| Administration | 0 | 17 | 17 |
| Other | 12 | 2 | 14 |
| Intelligence / Analytics | 11 | 15 | 26 |
| Documents & Communication | 2 | 28 | 30 |
| Commercial / CRM | 2 | 13 | 15 |
| Finance | 0 | 64 | 64 |
| HR & Payroll | 0 | 42 | 42 |
| Administration / Integrations | 2 | 9 | 11 |
| Supply Chain / Inventory | 0 | 25 | 25 |
| Logistics | 0 | 7 | 7 |
| Commercial / Marketing | 0 | 38 | 38 |
| Manufacturing / Planning | 10 | 11 | 21 |
| Supply Chain / Procurement | 0 | 24 | 24 |
| Manufacturing / Production | 0 | 25 | 25 |
| Factory Operations / Quality | 0 | 16 | 16 |
| Commercial / Sales | 0 | 42 | 42 |
| Factory Operations / Utilities | 15 | 55 | 70 |

## All Broken Targets (first 50)

| Source File | Visible Via | Target | Reason |
|------------|-------------|--------|--------|
| `users/page.tsx` | /dashboard/admin?tab=UsersPage | `/dashboard/users/${r.id` | middleware_redirect |
| `roles/page.tsx` | /dashboard/admin?tab=RolesPage | `/dashboard/roles/${r.id` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/new-field` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/fields` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/form-builder` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/workflow-rules` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/values` | middleware_redirect |
| `custom-fields/page.tsx` | /dashboard/admin?tab=CustomFieldsPage | `/dashboard/custom-fields/ai` | middleware_redirect |
| `mobile/page.tsx` | /dashboard/admin?tab=MobilePage | `/dashboard/mobile/approvals` | middleware_redirect |
| `mobile/page.tsx` | /dashboard/admin?tab=MobilePage | `/dashboard/mobile/devices` | middleware_redirect |
| `mobile/page.tsx` | /dashboard/admin?tab=MobilePage | `/dashboard/approvals` | middleware_redirect |
| `mobile/page.tsx` | /dashboard/admin?tab=MobilePage | `/dashboard/notification-center` | middleware_redirect |
| `ai/compliance/page.tsx` | /dashboard/ai?tab=AICompliancePage | `/dashboard/tax` | middleware_redirect |
| `ai/compliance/page.tsx` | /dashboard/ai?tab=AICompliancePage | `/dashboard/production/quality` | no_route_file |
| `analytics/production/page.tsx` | /dashboard/analytics?tab=AnalyticsProductionPage | `/dashboard/production/orders` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/inventory` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/production` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/procurement` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/sales` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/finance` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/payments` | middleware_redirect |
| `reports/page.tsx` | /dashboard/analytics?tab=ReportsPage | `/dashboard/reports/marketing` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/catalog` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/builder` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/saved` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/viewer` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/dashboards` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/schedules` | middleware_redirect |
| `report-builder/page.tsx` | /dashboard/analytics?tab=ReportBuilderPage | `/dashboard/report-builder/ai` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/feed` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/search` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/reports` | middleware_redirect |
| `chatter/page.tsx` | /dashboard/communication?tab=ChatterPage | `/dashboard/chatter/ai` | middleware_redirect |
| `calendar/page.tsx` | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/view` | middleware_redirect |
| `calendar/page.tsx` | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/new-event` | middleware_redirect |
| `calendar/page.tsx` | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/resources` | middleware_redirect |
| `calendar/page.tsx` | /dashboard/communication?tab=CalendarPage | `/dashboard/calendar/availability` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/list` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/preferences` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/templates` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/schedules` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/reports` | middleware_redirect |
| `notification-center/page.tsx` | /dashboard/communication?tab=NotifPage | `/dashboard/notification-center/ai` | middleware_redirect |
| `crm/pipeline/page.tsx` | /dashboard/crm?tab=CRMPipelinePage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/leads/page.tsx` | /dashboard/crm?tab=CRMLeadsPage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/opportunities/page.tsx` | /dashboard/crm?tab=CRMOppsPage | `/dashboard/crm/records/${rec.id` | middleware_redirect |
| `crm/activities/page.tsx` | /dashboard/crm?tab=CRMActivitiesPage | `/dashboard/crm/records/${act.crm_record_id` | middleware_redirect |
| `nps/page.tsx` | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | middleware_redirect |
| `surveys/page.tsx` | /dashboard/crm?tab=SurveysPage | `/dashboard/surveys/new` | middleware_redirect |
