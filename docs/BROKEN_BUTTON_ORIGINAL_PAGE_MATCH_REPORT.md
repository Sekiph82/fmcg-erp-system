# Broken Button → Original Page Match Report

**Date:** 2026-05-21
**Audit Version:** v3.0 — Fully Dynamic Scan
**Script:** `scripts/audit-visible-import-graph.js`

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Workspace pages scanned | 26 |
| Total dynamic imports found | 222 |
| Dynamically imported visible pages | 220 |
| Total visible action targets found | 487 |
| Working targets | 54 |
| **Total broken visible action targets** | **353** |
| Critical severity (create/run/approve actions) | 26 |
| High severity | 272 |
| Medium severity | 55 |
| Git history matches found | 306 |
| **High-confidence: real page existed in git** | **305** |
| Medium-confidence: file in git but content unverified | 1 |
| Unresolved: no git match | 47 |

---

## Key Finding — The Dynamic Import Visibility Blind Spot

### Previous Audit Was Wrong

Previous audit classified 296 broken action cards as **"safe_archived_standalone"** because:
> "The source page's standalone route is middleware-redirected, so users never see the page."

**This reasoning is incorrect.** A page can be user-visible through TWO paths:
1. Standalone route (may be redirected)
2. **Dynamic import into a workspace tab** ← this path was ignored

When `inventory/page.tsx` does:
```typescript
const CycleCountPage = dynamic(() => import("@/app/dashboard/cycle-count/page"), { ssr: false });
```
…the Cycle Count page IS rendered to users at `/dashboard/inventory?tab=cycle-count`.
Middleware redirecting `/dashboard/cycle-count` → `/dashboard/inventory?tab=cycle-count` is irrelevant here.

### Impact

97 pages are in this state — middleware-redirected as standalone routes,
but dynamically imported into workspace tabs and therefore fully user-visible.
Their internal navigation cards/buttons (totalling **353**) all fail silently
by looping the user back to the same workspace tab they are already on.

### The Cycle Count Example (Confirmed Still Broken)

**Visible at:** `/dashboard/inventory?tab=cycle-count`
**Source:** `frontend/src/app/dashboard/cycle-count/page.tsx`
**How visible:** `inventory/page.tsx` imports it as the "Cycle Count" tab
**Standalone route:** `/dashboard/cycle-count` → middleware redirects to `/dashboard/inventory?tab=cycle-count`

The 5 navigation tiles shown to users all link to redirect stubs:

| Tile | Target | Behavior | Git History |
|------|--------|----------|-------------|
| Count Plans | `/dashboard/cycle-count/plans` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Tasks | `/dashboard/cycle-count/tasks` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Entries | `/dashboard/cycle-count/entries` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Variance Review | `/dashboard/cycle-count/variances` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Reports & AI | `/dashboard/cycle-count/reports` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |

Git evidence: Commit `674b6c5` (2026-05-01) had REAL implementations — full CRUD with API integration.
These were deleted in `bd6faf5` (2026-05-17) and replaced with redirect stubs.
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT from commit 674b6c5.**

---

## Top 20 Critical/High Severity Broken Visible Buttons

| ID | Module | Visible At | Card/Button | Current Target | Behavior | Git | Recommendation |
|----|--------|-----------|-------------|----------------|----------|-----|----------------|
| BVT-0001 | Administration | /dashboard/admin?tab=UsersPage | ${r.id | `/dashboard/users/${r.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0002 | Administration | /dashboard/admin?tab=RolesPage | ${r.id | `/dashboard/roles/${r.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0003 | Administration | /dashboard/admin?tab=CustomFieldsPage | Custom Fields | `/dashboard/custom-fields/new-field` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0004 | Administration | /dashboard/admin?tab=CustomFieldsPage | Recent Fields | `/dashboard/custom-fields/fields` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0005 | Administration | /dashboard/admin?tab=CustomFieldsPage | ${f.custom_field_id | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0006 | Administration | /dashboard/admin?tab=CustomFieldsPage | Field Manager | `/dashboard/custom-fields/form-builder` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0007 | Administration | /dashboard/admin?tab=CustomFieldsPage | Field Manager | `/dashboard/custom-fields/workflow-rules` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0008 | Administration | /dashboard/admin?tab=CustomFieldsPage | Workflow Rules | `/dashboard/custom-fields/values` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0010 | Administration | /dashboard/admin?tab=MobilePage | Approval Inbox | `/dashboard/mobile/approvals` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0011 | Administration | /dashboard/admin?tab=MobilePage | Approval Inbox | `/dashboard/mobile/devices` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0012 | Administration | /dashboard/admin?tab=MobilePage | Approval Inbox | `/dashboard/approvals` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0013 | Administration | /dashboard/admin?tab=MobilePage | Device Manager | `/dashboard/notification-center` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0014 | Other | /dashboard/ai?tab=AICompliancePage | Tax Module | `/dashboard/tax` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0015 | Other | /dashboard/ai?tab=AICompliancePage | Quality Module | `/dashboard/production/quality` | no_route_file | none | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0016 | Intelligence / Analytics | /dashboard/analytics?tab=AnalyticsProductionPage | Past scheduled end | `/dashboard/production/orders` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0024 | Intelligence / Analytics | /dashboard/analytics?tab=ReportBuilderPage | Data Catalog | `/dashboard/report-builder/catalog` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0025 | Intelligence / Analytics | /dashboard/analytics?tab=ReportBuilderPage | Data Catalog | `/dashboard/report-builder/builder` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0026 | Intelligence / Analytics | /dashboard/analytics?tab=ReportBuilderPage | Data Catalog | `/dashboard/report-builder/saved` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0027 | Intelligence / Analytics | /dashboard/analytics?tab=ReportBuilderPage | Build Report | `/dashboard/report-builder/viewer` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0028 | Intelligence / Analytics | /dashboard/analytics?tab=ReportBuilderPage | Saved Reports | `/dashboard/report-builder/dashboards` | middleware_redirect | ✓ REAL | RESTORE_OLD_PAGE_FROM_GIT |

---

## Module-by-Module Breakdown

### Administration

**Broken count:** 13

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Administration | /dashboard/admin | UsersPage | users/page.tsx | ${r.id | `/dashboard/users/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin | RolesPage | roles/page.tsx | ${r.id | `/dashboard/roles/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | Custom Fields | `/dashboard/custom-fields/new-field` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | Recent Fields | `/dashboard/custom-fields/fields` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | ${f.custom_field_id | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | Field Manager | `/dashboard/custom-fields/form-builder` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | Field Manager | `/dashboard/custom-fields/workflow-rules` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | Workflow Rules | `/dashboard/custom-fields/values` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | New Field | `/dashboard/custom-fields/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | MobilePage | mobile/page.tsx | Approval Inbox | `/dashboard/mobile/approvals` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | MobilePage | mobile/page.tsx | Approval Inbox | `/dashboard/mobile/devices` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | MobilePage | mobile/page.tsx | Approval Inbox | `/dashboard/approvals` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration | /dashboard/admin | MobilePage | mobile/page.tsx | Device Manager | `/dashboard/notification-center` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Other

**Broken count:** 2

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Other | /dashboard/ai | AICompliancePage | ai/compliance/page.tsx | Tax Module | `/dashboard/tax` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Other | /dashboard/ai | AICompliancePage | ai/compliance/page.tsx | Quality Module | `/dashboard/production/quality` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |


### Intelligence / Analytics

**Broken count:** 15

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Intelligence / Analytics | /dashboard/analytics | AnalyticsProductionPage | analytics/production/page.tsx | Past scheduled end | `/dashboard/production/orders` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Inventory | `/dashboard/reports/inventory` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Production / MES | `/dashboard/reports/production` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Procurement | `/dashboard/reports/procurement` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Sales & Revenue | `/dashboard/reports/sales` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Finance | `/dashboard/reports/finance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | M-Pesa Payments | `/dashboard/reports/payments` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportsPage | reports/page.tsx | Marketing BI | `/dashboard/reports/marketing` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Data Catalog | `/dashboard/report-builder/catalog` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Data Catalog | `/dashboard/report-builder/builder` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Data Catalog | `/dashboard/report-builder/saved` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Build Report | `/dashboard/report-builder/viewer` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Saved Reports | `/dashboard/report-builder/dashboards` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Report Viewer | `/dashboard/report-builder/schedules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Intelligence / Analytics | /dashboard/analytics | ReportBuilderPage | report-builder/page.tsx | Dashboards | `/dashboard/report-builder/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Documents & Communication

**Broken count:** 22

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Documents & Communication | /dashboard/communication | ChatterPage | chatter/page.tsx | Recent Activity Feed | `/dashboard/chatter/feed` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | ChatterPage | chatter/page.tsx | My Feed | `/dashboard/chatter/search` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | ChatterPage | chatter/page.tsx | My Feed | `/dashboard/chatter/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | ChatterPage | chatter/page.tsx | Search | `/dashboard/chatter/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | CalendarPage | calendar/page.tsx | Calendar View | `/dashboard/calendar/view` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | CalendarPage | calendar/page.tsx | Calendar View | `/dashboard/calendar/new-event` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | CalendarPage | calendar/page.tsx | Calendar View | `/dashboard/calendar/resources` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | CalendarPage | calendar/page.tsx | New Event | `/dashboard/calendar/availability` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | All Notifications | `/dashboard/notification-center/list` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | All Notifications | `/dashboard/notification-center/preferences` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | All Notifications | `/dashboard/notification-center/templates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | Preferences | `/dashboard/notification-center/schedules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | Templates | `/dashboard/notification-center/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/communication | NotifPage | notification-center/page.tsx | Schedules | `/dashboard/notification-center/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/documents | DocsCompliancePage | documents/compliance/page.tsx | new | `/dashboard/documents/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/documents | DocsCompliancePage | documents/compliance/page.tsx | ${d.id | `/dashboard/documents/${d.id` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | /dashboard/documents | DocsCompliancePage | documents/compliance/page.tsx | Expiry Tracker | `/dashboard/esign` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/documents | DocsExpiringPage | documents/expiring/page.tsx | ${d.id | `/dashboard/documents/${d.id` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | ${a.id | `/dashboard/knowledge-base/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | Categories | `/dashboard/knowledge-base/categories` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | articles | `/dashboard/knowledge-base/articles` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | View all | `/dashboard/knowledge-base/articles/new` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Commercial / CRM

**Broken count:** 7

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / CRM | /dashboard/crm | CRMPipelinePage | crm/pipeline/page.tsx | ${rec.id | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMLeadsPage | crm/leads/page.tsx | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMOppsPage | crm/opportunities/page.tsx | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMActivitiesPage | crm/activities/page.tsx | ${act.crm_record_id | `/dashboard/crm/records/${act.crm_record_id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | NPSPage | nps/page.tsx | surveys | `/dashboard/nps/surveys` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | SurveysPage | surveys/page.tsx | new | `/dashboard/surveys/new` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / CRM | /dashboard/crm | SurveysPage | surveys/page.tsx | ${s.id | `/dashboard/surveys/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Finance

**Broken count:** 57

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Customers Ledger | `/dashboard/finance/accounting/customers-ledger` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Customers Ledger | `/dashboard/finance/accounting/suppliers-ledger` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Customers Ledger | `/dashboard/finance/accounting/sales-invoices` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Suppliers Ledger | `/dashboard/finance/accounting/purchase-invoices` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Sales Invoices | `/dashboard/finance/accounting/payments` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FinanceAccountingPage | finance/accounting/page.tsx | Purchase Invoices | `/dashboard/finance/accounting/controls` | middleware_redirect | Yes — stub only | only redirect stub in git | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | Bank Reconciliation | `/dashboard/bank-reconciliation/import` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | statements | `/dashboard/bank-reconciliation/statements` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | Open Items Aging | `/dashboard/bank-reconciliation/open-items` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | Open Items Aging | `/dashboard/bank-reconciliation/balance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | Open Items Aging | `/dashboard/bank-reconciliation/rules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | Bank vs Ledger | `/dashboard/bank-reconciliation/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | ${s.id | `/dashboard/bank-reconciliation/statements/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | review-queue | `/dashboard/invoice-match/review-queue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | matches | `/dashboard/invoice-match/matches` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | On Hold | `/dashboard/invoice-match/blocked` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | Quick Links | `/dashboard/invoice-match/duplicates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | Blocked Invoices | `/dashboard/invoice-match/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | View | `/dashboard/invoice-match/${m.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Asset Register | `/dashboard/fixed-assets/assets` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Asset Register | `/dashboard/fixed-assets/categories` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Asset Register | `/dashboard/fixed-assets/depreciation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Asset Categories | `/dashboard/fixed-assets/posting` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Depreciation Schedules | `/dashboard/fixed-assets/disposal` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Posting Run | `/dashboard/fixed-assets/transfer` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Disposals | `/dashboard/fixed-assets/import` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | Transfers | `/dashboard/fixed-assets/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | FixedAssetsPage | fixed-assets/page.tsx | new | `/dashboard/fixed-assets/assets/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Dimension Types | `/dashboard/dimensions/types` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Dimension Types | `/dashboard/dimensions/values` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Dimension Types | `/dashboard/dimensions/cost-centers` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Dimension Values | `/dashboard/dimensions/allocations` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Cost Centers | `/dashboard/dimensions/allocation-run` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Allocation Rules | `/dashboard/dimensions/validation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Allocation Run | `/dashboard/dimensions/defaults` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Validation Rules | `/dashboard/dimensions/reclassify` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Default Rules | `/dashboard/dimensions/completeness` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DimensionsPage | dimensions/page.tsx | Reclassify | `/dashboard/dimensions/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | Aging Report | `/dashboard/dunning/aging` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | Aging Report | `/dashboard/dunning/workqueue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | Aging Report | `/dashboard/dunning/credit-holds` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | Collector Queue | `/dashboard/dunning/policies` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | Top Priority Cases | `/dashboard/dunning/cases` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | ${c.id | `/dashboard/dunning/cases/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | TaxPage | tax/page.tsx | Tax Rules & Categories | `/dashboard/tax/rules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | TaxPage | tax/page.tsx | Tax Rules & Categories | `/dashboard/tax/regulatory` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | TaxPage | tax/page.tsx | Tax Rules & Categories | `/dashboard/tax/transactions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | TaxPage | tax/page.tsx | Regulatory Flags | `/dashboard/tax/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | My Claims | `/dashboard/expenses/claims` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | My Claims | `/dashboard/expenses/claims/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | My Claims | `/dashboard/expenses/approval` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | New Claim | `/dashboard/expenses/reimbursement` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | Approval Queue | `/dashboard/expenses/advances` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | Reimbursement | `/dashboard/expenses/categories` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | Advances | `/dashboard/expenses/policies` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | Categories | `/dashboard/expenses/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Finance | /dashboard/finance | ExpensesPage | expenses/page.tsx | Policies | `/dashboard/expenses/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### HR & Payroll

**Broken count:** 41

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Requisitions | `/dashboard/recruitment/requisitions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Requisitions | `/dashboard/recruitment/requisitions/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Requisitions | `/dashboard/recruitment/candidates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | New Requisition | `/dashboard/recruitment/pipeline` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Candidates | `/dashboard/recruitment/interviews` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Pipeline Board | `/dashboard/recruitment/offers` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Interviews | `/dashboard/recruitment/stages` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Offers | `/dashboard/recruitment/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | RecruitmentPage | recruitment/page.tsx | Pipeline Stages | `/dashboard/recruitment/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | My Profile | `/dashboard/ess/profile` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | My Profile | `/dashboard/ess/leave` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | My Profile | `/dashboard/ess/attendance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | Leave | `/dashboard/ess/documents` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | Attendance | `/dashboard/ess/requests` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | Documents | `/dashboard/ess/notifications` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | My Requests | `/dashboard/ess/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | ESSPage | ess/page.tsx | Notifications | `/dashboard/ess/admin` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Appraisal Periods | `/dashboard/appraisals/periods` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Appraisal Periods | `/dashboard/appraisals/templates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Appraisal Periods | `/dashboard/appraisals/records` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Templates | `/dashboard/appraisals/records/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | All Records | `/dashboard/appraisals/self-review` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | New Appraisal | `/dashboard/appraisals/manager-queue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Self Review | `/dashboard/appraisals/hr-review` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Manager Queue | `/dashboard/appraisals/development-plans` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | HR Review | `/dashboard/appraisals/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | AppraisalsPage | appraisals/page.tsx | Development Plans | `/dashboard/appraisals/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Training Programs | `/dashboard/training/programs` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Training Programs | `/dashboard/training/sessions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Training Programs | `/dashboard/training/skill-matrix` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Sessions / Calendar | `/dashboard/training/assignments` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Skill Matrix | `/dashboard/training/certifications` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Assignments | `/dashboard/training/feedback` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Certifications | `/dashboard/training/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TrainingPage | training/page.tsx | Feedback | `/dashboard/training/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | My Timesheets | `/dashboard/timesheets/my-timesheets` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | My Timesheets | `/dashboard/timesheets/time-entry` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | My Timesheets | `/dashboard/timesheets/weekly-view` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | New Time Entry | `/dashboard/timesheets/approval-queue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | Weekly View | `/dashboard/timesheets/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| HR & Payroll | /dashboard/hr | TimesheetsPage | timesheets/page.tsx | Approval Queue | `/dashboard/timesheets/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Administration / Integrations

**Broken count:** 9

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Event Definitions | `/dashboard/webhooks/definitions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Event Definitions | `/dashboard/webhooks/subscriptions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Event Definitions | `/dashboard/webhooks/deliveries` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Subscriptions | `/dashboard/webhooks/dead-letter` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Deliveries | `/dashboard/webhooks/inbound` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | WebhooksPage | webhooks/page.tsx | Dead-Letter Queue | `/dashboard/webhooks/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | DeveloperPage | developer/page.tsx | API Keys | `/dashboard/developer/keys` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | DeveloperPage | developer/page.tsx | API Keys | `/dashboard/developer/graphql` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Administration / Integrations | /dashboard/integrations | DeveloperPage | developer/page.tsx | OpenAPI Docs | `/dashboard/webhooks` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Supply Chain / Inventory

**Broken count:** 24

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Supply Chain / Inventory | /dashboard/inventory | CycleCountPage | cycle-count/page.tsx | Count Plans | `/dashboard/cycle-count/plans` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | CycleCountPage | cycle-count/page.tsx | Count Plans | `/dashboard/cycle-count/tasks` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | CycleCountPage | cycle-count/page.tsx | Count Plans | `/dashboard/cycle-count/entries` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | CycleCountPage | cycle-count/page.tsx | Count Tasks | `/dashboard/cycle-count/variances` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | CycleCountPage | cycle-count/page.tsx | Count Entries | `/dashboard/cycle-count/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | FEFO Config | `/dashboard/shelf-life/fefo-config` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | FEFO Config | `/dashboard/shelf-life/lot-aging` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | FEFO Config | `/dashboard/shelf-life/near-expiry` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Lot Aging | `/dashboard/shelf-life/expired` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Near-Expiry Board | `/dashboard/shelf-life/retest-queue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Expired Board | `/dashboard/shelf-life/shipment-validation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Retest Queue | `/dashboard/shelf-life/production-validation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Shipment Validation | `/dashboard/shelf-life/compliance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Production Validation | `/dashboard/shelf-life/disposition` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Compliance Audit | `/dashboard/shelf-life/customer-rules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | ShelfLifePage | shelf-life/page.tsx | Disposition Console | `/dashboard/shelf-life/bulk-hold-monitor` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Recent Recalls | `/dashboard/traceability/recalls` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | ${r.id | `/dashboard/traceability/recalls/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Trace Search | `/dashboard/traceability/search` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Trace Search | `/dashboard/traceability/backward` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Trace Search | `/dashboard/traceability/forward` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Backward Trace | `/dashboard/traceability/genealogy` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Genealogy Graph | `/dashboard/traceability/mock-recall` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | Recall List | `/dashboard/traceability/regulatory` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Logistics

**Broken count:** 7

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Vehicles | `/dashboard/fleet/vehicles` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Vehicles | `/dashboard/fleet/drivers` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Vehicles | `/dashboard/fleet/trips` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Drivers | `/dashboard/fleet/fuel` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Trips | `/dashboard/fleet/maintenance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Fuel Log | `/dashboard/fleet/incidents` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Logistics | /dashboard/logistics | FleetPage | fleet/page.tsx | Maintenance | `/dashboard/fleet/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Commercial / Marketing

**Broken count:** 30

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / Marketing | /dashboard/marketing | MarketingCampaignsPage | marketing/campaigns/page.tsx | new | `/dashboard/marketing/campaigns/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingCampaignsPage | marketing/campaigns/page.tsx | ${c.id | `/dashboard/marketing/campaigns/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingPromotionsPage | marketing/promotions/page.tsx | new | `/dashboard/marketing/promotions/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingPromotionsPage | marketing/promotions/page.tsx | ${p.id | `/dashboard/marketing/promotions/${p.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingTradeSpendPage | marketing/trade-spend/page.tsx | new | `/dashboard/marketing/trade-spend/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingTradeSpendPage | marketing/trade-spend/page.tsx | ${t.id | `/dashboard/marketing/trade-spend/${t.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingAdsPage | marketing/ads/page.tsx | new | `/dashboard/marketing/ads/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingAdsPage | marketing/ads/page.tsx | ${a.id | `/dashboard/marketing/ads/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingSocialPage | marketing/social-media/page.tsx | new | `/dashboard/marketing/social-media/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingSocialPage | marketing/social-media/page.tsx | ${a.id | `/dashboard/marketing/social-media/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingSegmentsPage | marketing/segments/page.tsx | new | `/dashboard/marketing/segments/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingSegmentsPage | marketing/segments/page.tsx | ${s.id | `/dashboard/marketing/segments/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingInfluencersPage | marketing/influencers/page.tsx | new | `/dashboard/marketing/influencers/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingInfluencersPage | marketing/influencers/page.tsx | ${i.id | `/dashboard/marketing/influencers/${i.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingEcommercePage | marketing/ecommerce/page.tsx | stores | `/dashboard/marketing/ecommerce/stores` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingVisitsPage | marketing/visits/page.tsx | new | `/dashboard/marketing/visits/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingVisitsPage | marketing/visits/page.tsx | ${v.id | `/dashboard/marketing/visits/${v.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingBrandSpendPage | marketing/brand-spend/page.tsx | new | `/dashboard/marketing/brand-spend/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | MarketingBrandSpendPage | marketing/brand-spend/page.tsx | ${b.id | `/dashboard/marketing/brand-spend/${b.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | new | `/dashboard/tpm/plans/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | new | `/dashboard/tpm/promotions/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Recent Promotions | `/dashboard/tpm/promotions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | ${p.id | `/dashboard/tpm/promotions/${p.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Promotion Calendar | `/dashboard/tpm/calendar` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Promotion Calendar | `/dashboard/tpm/budget` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Promotion Calendar | `/dashboard/tpm/claims` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Budget Monitor | `/dashboard/tpm/roi` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Claims Queue | `/dashboard/tpm/settlement` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | ROI Analysis | `/dashboard/tpm/plans` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | Plans Master | `/dashboard/tpm/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Manufacturing / Planning

**Broken count:** 8

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Manufacturing / Planning | /dashboard/planning | MRPPage | mrp/page.tsx | forecast | `/dashboard/mrp/forecast` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | MRPPage | mrp/page.tsx | suggestions | `/dashboard/mrp/suggestions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | MRPPage | mrp/page.tsx | run | `/dashboard/mrp/run` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | KanbanPage | kanban/page.tsx | All Boards | `/dashboard/kanban/boards` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | KanbanPage | kanban/page.tsx | All Boards | `/dashboard/kanban/view` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | KanbanPage | kanban/page.tsx | All Boards | `/dashboard/kanban/cards` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | KanbanPage | kanban/page.tsx | Board View | `/dashboard/kanban/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Planning | /dashboard/planning | KanbanPage | kanban/page.tsx | All Cards | `/dashboard/kanban/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |


### Supply Chain / Procurement

**Broken count:** 17

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Supply Chain / Procurement | /dashboard/procurement | ProcurementOrdersPage | procurement/orders/page.tsx | PO No | `/dashboard/procurement/orders/${p.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | ProcurementDeliveriesPage | procurement/deliveries/page.tsx | ${a.po_id} | `/dashboard/procurement/orders/${a.po_id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | ProcurementDeliveriesPage | procurement/deliveries/page.tsx | PO No | `/dashboard/procurement/orders/${r.po_id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | SuggestionsPage | procurement-suggestion/page.tsx | suggestions | `/dashboard/procurement-suggestion/suggestions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SuggestionsPage | procurement-suggestion/page.tsx | Suggestion List | `/dashboard/procurement-suggestion/groups` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SuggestionsPage | procurement-suggestion/page.tsx | Suggestion List | `/dashboard/procurement-suggestion/supplier-prices` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SuggestionsPage | procurement-suggestion/page.tsx | Grouped Orders | `/dashboard/procurement-suggestion/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SubcontractingPage | subcontracting/page.tsx | locations | `/dashboard/subcontracting/locations` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SubcontractingPage | subcontracting/page.tsx | Run AI Agents | `/dashboard/subcontracting/orders` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SubcontractingPage | subcontracting/page.tsx | Orders | `/dashboard/subcontracting/stock` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SubcontractingPage | subcontracting/page.tsx | Orders | `/dashboard/subcontracting/yield` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | SubcontractingPage | subcontracting/page.tsx | Subcontractor Stock | `/dashboard/subcontracting/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | LandedCostPage | landed-cost/page.tsx | Landed Cost Allocation | `/dashboard/landed-cost/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | LandedCostPage | landed-cost/page.tsx | ai | `/dashboard/landed-cost/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | LandedCostPage | landed-cost/page.tsx | Recent Documents | `/dashboard/landed-cost/documents` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Procurement | /dashboard/procurement | LandedCostPage | landed-cost/page.tsx | ${doc.id | `/dashboard/landed-cost/${doc.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement | SupplierPortalPage | supplier-portal/page.tsx | View | `/dashboard/supplier-portal/accounts/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Manufacturing / Production

**Broken count:** 22

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Manufacturing / Production | /dashboard/production | ProductionOrdersPage | production/orders/page.tsx | ${o.id} | `/dashboard/production/orders/${o.id}` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production | ExecutionPage | production-execution/page.tsx | work-orders | `/dashboard/production-execution/work-orders` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | ExecutionPage | production-execution/page.tsx | ${o.id | `/dashboard/production-execution/${o.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Machine Master | `/dashboard/machine-ops/machines` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Machine Master | `/dashboard/machine-ops/operators` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Machine Master | `/dashboard/machine-ops/teams` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Operators | `/dashboard/machine-ops/runtime` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Teams | `/dashboard/machine-ops/performance` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Runtime Logs | `/dashboard/machine-ops/downtime` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Performance | `/dashboard/machine-ops/costing` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Downtime Board | `/dashboard/machine-ops/certs` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MachineOpsPage | machine-ops/page.tsx | Cost Contribution | `/dashboard/machine-ops/assignment` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Issue to Production | `/dashboard/material-flow/issue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Issue to Production | `/dashboard/material-flow/wip-transfer` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Issue to Production | `/dashboard/material-flow/bulk-transfer` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Stage Transfer | `/dashboard/material-flow/fg-receipt` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Bulk Transfer | `/dashboard/material-flow/reservations` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | FG Receipt | `/dashboard/material-flow/tanks` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Reservations | `/dashboard/material-flow/returns` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Tank Occupancy | `/dashboard/material-flow/reconciliation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | MaterialFlowPage | material-flow/page.tsx | Recent Flows | `/dashboard/material-flow/history` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Manufacturing / Production | /dashboard/production | ProjectsPage | projects/page.tsx | ${p.id} | `/dashboard/projects/${p.id}` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Factory Operations / Quality

**Broken count:** 15

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Factory Operations / Quality | /dashboard/quality | QualityReportsPage | quality/reports/page.tsx | Inspection No | `/dashboard/quality/${i.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | QC Inspections | `/dashboard/qms/inspections` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | QC Inspections | `/dashboard/qms/templates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | QC Inspections | `/dashboard/qms/haccp` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | QC Templates | `/dashboard/qms/ccp` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | HACCP Analysis | `/dashboard/qms/deviations` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | CCP Monitoring | `/dashboard/qms/corrective-actions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | Deviations | `/dashboard/qms/quarantine` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | Corrective Actions | `/dashboard/qms/allergen` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | Quarantine / Hold | `/dashboard/qms/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | QMSPage | qms/page.tsx | Allergen Validation | `/dashboard/qms/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | AllergenPage | allergen/page.tsx | Missing allergen profiles | `/dashboard/allergen/material-profiles` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | AllergenPage | allergen/page.tsx | Missing allergen profiles | `/dashboard/allergen/product-allergens` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | AllergenPage | allergen/page.tsx | Missing allergen profiles | `/dashboard/allergen/change-logs` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Quality | /dashboard/quality | BrandAssetsPage | brand-assets/page.tsx | ${a.id | `/dashboard/brand-assets/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / Sales

**Broken count:** 39

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / Sales | /dashboard/sales | SalesOrdersPage | sales/orders/page.tsx | Order No | `/dashboard/sales/orders/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | SalesInvoicesPage | sales/invoices/page.tsx | Invoice No | `/dashboard/sales/invoices/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | SalesShipmentsPage | sales/shipments/page.tsx | Shipment No | `/dashboard/sales/shipments/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | PriceListsPage | price-lists/page.tsx | approval-queue | `/dashboard/price-lists/approval-queue` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PriceListsPage | price-lists/page.tsx | ${h.id | `/dashboard/price-lists/${h.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | Run AI | `/dashboard/contracts/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | Recent Contracts | `/dashboard/contracts/list` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | ${c.id | `/dashboard/contracts/list/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | View all | `/dashboard/contracts/expiring` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | AI Alerts | `/dashboard/contracts/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | new | `/dashboard/recurring-orders/templates/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | Recent Templates | `/dashboard/recurring-orders/templates` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | ${t.id | `/dashboard/recurring-orders/templates/${t.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | Reports | `/dashboard/recurring-orders/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | AI Insights | `/dashboard/recurring-orders/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | CommissionsPage | commissions/page.tsx | Run AI | `/dashboard/commissions/rules` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | CommissionsPage | commissions/page.tsx | Pending Approval | `/dashboard/commissions/transactions` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | CommissionsPage | commissions/page.tsx | Draft Payouts | `/dashboard/commissions/payouts` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | CommissionsPage | commissions/page.tsx | AI Insights | `/dashboard/commissions/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | SecondarySalesPage | secondary-sales/page.tsx | analysis | `/dashboard/secondary-sales/analysis` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | SecondarySalesPage | secondary-sales/page.tsx | inventory | `/dashboard/secondary-sales/inventory` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | SecondarySalesPage | secondary-sales/page.tsx | upload | `/dashboard/secondary-sales/upload` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | SecondarySalesPage | secondary-sales/page.tsx | ${h.id | `/dashboard/secondary-sales/${h.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Run AI Agents | `/dashboard/van-sales/vans/new` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Route Execution | `/dashboard/van-sales/route` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Route Execution | `/dashboard/van-sales/pos` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Route Execution | `/dashboard/van-sales/stock` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Mobile POS | `/dashboard/van-sales/reconciliation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | Vans | `/dashboard/van-sales/vans` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | ${v.id | `/dashboard/van-sales/vans/${v.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | AI Alerts | `/dashboard/van-sales/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | All Accounts | `/dashboard/portal/accounts` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | All Accounts | `/dashboard/portal/drafts` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | All Accounts | `/dashboard/portal/claims` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Draft Orders Queue | `/dashboard/portal/users` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Claims Review | `/dashboard/portal/activity` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Portal Users | `/dashboard/portal/ai` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Activity Log | `/dashboard/portal/reports` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Manage | `/dashboard/portal/accounts/${acc.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Factory Operations / Utilities

**Broken count:** 25

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Electricity | `/dashboard/utility-management/kpi-center/electricity` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Electricity | `/dashboard/utility-management/kpi-center/water` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Electricity | `/dashboard/utility-management/kpi-center/soft-water` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Water | `/dashboard/utility-management/kpi-center/boiler` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Soft Water | `/dashboard/utility-management/kpi-center/compressor` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Boiler / Steam | `/dashboard/utility-management/kpi-center/solar` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Compressed Air | `/dashboard/utility-management/kpi-center/chemicals` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Solar | `/dashboard/utility-management/kpi-center/wastewater` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Chemicals | `/dashboard/utility-management/kpi-center/utility-cost` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | KPICenterPage | utility-management/kpi-center/page.tsx | Wastewater | `/dashboard/utility-management/kpi-center/machine-utility` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | AlarmCenterPage | utility-management/alarm-center/page.tsx | kpi-center | `/dashboard/utility-management/kpi-center` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | AlarmRulesPage | utility-management/alarm-rules/page.tsx | KPI Center | `/dashboard/utility-management/kpi-center` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Daily Consumption | `/dashboard/utility-management/reports/daily-consumption` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Boiler & Steam | `/dashboard/utility-management/reports/equipment-efficiency` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Chemical Treatment | `/dashboard/utility-management/reports/treatment` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Cost Allocation | `/dashboard/utility-management/reports/cost-allocation` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Base Load Analysis | `/dashboard/utility-management/reports/load-analysis` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Alarm Trend Report | `/dashboard/utility-management/reports/anomalies` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilReportsPage | utility-management/reports/page.tsx | Sustainability Summary | `/dashboard/utility-management/reports/sustainability` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | UtilIntegrationPage | utility-management/integration/page.tsx | kpi-center | `/dashboard/utility-management/kpi-center` | middleware_redirect | Yes — real page | commit 674b6c5 (2026-05-01) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | ESGPage | esg/page.tsx | activities | `/dashboard/esg/activities` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | ESGPage | esg/page.tsx | factors | `/dashboard/esg/factors` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | ESGPage | esg/page.tsx | targets | `/dashboard/esg/targets` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | ESGPage | esg/page.tsx | reports | `/dashboard/esg/reports` | middleware_redirect | Yes — real page | commit 27ebada (2026-05-02) | high | RESTORE_OLD_PAGE_FROM_GIT |
| Factory Operations / Utilities | /dashboard/utility-management | ESGPage | esg/page.tsx | intelligence | `/dashboard/esg/intelligence` | middleware_redirect | Yes — real page | commit 10125e4 (2026-05-10) | high | RESTORE_OLD_PAGE_FROM_GIT |



---

## Dynamic Import Visibility Failures

Every entry below was **missed** by the previous audit (classified as "safe_archived_standalone").
Each of these pages is middleware-redirected as a standalone route but IS user-visible
because it is dynamically imported into a workspace tab.

| Source Page | Standalone Route | Middleware Destination | Visible As | Broken Cards |
|-------------|-----------------|----------------------|-----------|--------------|
| `users/page.tsx` | `/dashboard/users` | `/dashboard/admin?tab=users` | `/dashboard/admin` | 1 |
| `roles/page.tsx` | `/dashboard/roles` | `/dashboard/admin?tab=roles` | `/dashboard/admin` | 1 |
| `permissions/page.tsx` | `/dashboard/permissions` | `/dashboard/admin?tab=permissions` | `/dashboard/admin` | 0 |
| `companies/page.tsx` | `/dashboard/companies` | `/dashboard/admin?tab=companies` | `/dashboard/admin` | 0 |
| `security/page.tsx` | `/dashboard/security` | `/dashboard/admin?tab=security` | `/dashboard/admin` | 0 |
| `approvals/page.tsx` | `/dashboard/approvals` | `/dashboard/admin?tab=approvals` | `/dashboard/admin` | 0 |
| `custom-fields/page.tsx` | `/dashboard/custom-fields` | `/dashboard/admin?tab=custom-fields` | `/dashboard/admin` | 7 |
| `utilities/page.tsx` | `/dashboard/utilities` | `/dashboard/admin?tab=system-config` | `/dashboard/admin` | 0 |
| `mobile/page.tsx` | `/dashboard/mobile` | `/dashboard/admin?tab=mobile` | `/dashboard/admin` | 4 |
| `logs/page.tsx` | `/dashboard/logs` | `/dashboard/admin?tab=logs` | `/dashboard/admin` | 0 |
| `import-history/page.tsx` | `/dashboard/import-history` | `/dashboard/admin?tab=import-history` | `/dashboard/admin` | 0 |
| `reports/page.tsx` | `/dashboard/reports` | `/dashboard/analytics?tab=reports` | `/dashboard/analytics` | 7 |
| `report-builder/page.tsx` | `/dashboard/report-builder` | `/dashboard/analytics?tab=report-builder` | `/dashboard/analytics` | 7 |
| `chatter/page.tsx` | `/dashboard/chatter` | `/dashboard/communication?tab=chatter` | `/dashboard/communication` | 4 |
| `calendar/page.tsx` | `/dashboard/calendar` | `/dashboard/communication?tab=calendar` | `/dashboard/communication` | 4 |
| `messages/page.tsx` | `/dashboard/messages` | `/dashboard/communication?tab=messages` | `/dashboard/communication` | 0 |
| `email/page.tsx` | `/dashboard/email` | `/dashboard/communication?tab=email` | `/dashboard/communication` | 0 |
| `whatsapp/page.tsx` | `/dashboard/whatsapp` | `/dashboard/communication?tab=whatsapp` | `/dashboard/communication` | 0 |
| `calls/page.tsx` | `/dashboard/calls` | `/dashboard/communication?tab=calls` | `/dashboard/communication` | 0 |
| `meetings/page.tsx` | `/dashboard/meetings` | `/dashboard/communication?tab=meetings` | `/dashboard/communication` | 0 |
| `notification-center/page.tsx` | `/dashboard/notification-center` | `/dashboard/communication?tab=notifications` | `/dashboard/communication` | 6 |
| `gs1/page.tsx` | `/dashboard/gs1` | `/dashboard/compliance?tab=gs1` | `/dashboard/compliance` | 0 |
| `loyalty/page.tsx` | `/dashboard/loyalty` | `/dashboard/crm?tab=loyalty` | `/dashboard/crm` | 0 |
| `nps/page.tsx` | `/dashboard/nps` | `/dashboard/crm?tab=nps` | `/dashboard/crm` | 1 |
| `surveys/page.tsx` | `/dashboard/surveys` | `/dashboard/crm?tab=surveys` | `/dashboard/crm` | 2 |
| `knowledge-base/page.tsx` | `/dashboard/knowledge-base` | `/dashboard/documents?tab=knowledge-base` | `/dashboard/documents` | 4 |
| `esign/page.tsx` | `/dashboard/esign` | `/dashboard/documents?tab=esign` | `/dashboard/documents` | 0 |
| `finance/accounting/page.tsx` | `/dashboard/finance/accounting` | `/dashboard/finance?tab=accounting` | `/dashboard/finance` | 6 |
| `bank-reconciliation/page.tsx` | `/dashboard/bank-reconciliation` | `/dashboard/finance?tab=bank-recon` | `/dashboard/finance` | 7 |
| `invoice-match/page.tsx` | `/dashboard/invoice-match` | `/dashboard/finance?tab=invoice-match` | `/dashboard/finance` | 6 |
| `fixed-assets/page.tsx` | `/dashboard/fixed-assets` | `/dashboard/finance?tab=fixed-assets` | `/dashboard/finance` | 9 |
| `dimensions/page.tsx` | `/dashboard/dimensions` | `/dashboard/finance?tab=dimensions` | `/dashboard/finance` | 10 |
| `dunning/page.tsx` | `/dashboard/dunning` | `/dashboard/finance?tab=dunning` | `/dashboard/finance` | 6 |
| `tax/page.tsx` | `/dashboard/tax` | `/dashboard/finance?tab=tax` | `/dashboard/finance` | 4 |
| `bank-api/page.tsx` | `/dashboard/bank-api` | `/dashboard/finance?tab=bank-api` | `/dashboard/finance` | 0 |
| `expenses/page.tsx` | `/dashboard/expenses` | `/dashboard/hr?tab=expenses` | `/dashboard/finance`, `/dashboard/hr` | 9 |
| `recruitment/page.tsx` | `/dashboard/recruitment` | `/dashboard/hr?tab=recruitment` | `/dashboard/hr` | 9 |
| `ess/page.tsx` | `/dashboard/ess` | `/dashboard/hr?tab=ess` | `/dashboard/hr` | 8 |
| `appraisals/page.tsx` | `/dashboard/appraisals` | `/dashboard/hr?tab=appraisals` | `/dashboard/hr` | 10 |
| `training/page.tsx` | `/dashboard/training` | `/dashboard/hr?tab=training` | `/dashboard/hr` | 8 |
| `timesheets/page.tsx` | `/dashboard/timesheets` | `/dashboard/hr?tab=timesheets` | `/dashboard/hr` | 6 |
| `webhooks/page.tsx` | `/dashboard/webhooks` | `/dashboard/integrations?tab=webhooks` | `/dashboard/integrations` | 6 |
| `developer/page.tsx` | `/dashboard/developer` | `/dashboard/integrations?tab=developer` | `/dashboard/integrations` | 3 |
| `movements/page.tsx` | `/dashboard/movements` | `/dashboard/inventory?tab=movements` | `/dashboard/inventory` | 0 |
| `cycle-count/page.tsx` | `/dashboard/cycle-count` | `/dashboard/inventory?tab=cycle-count` | `/dashboard/inventory` | 5 |
| `shelf-life/page.tsx` | `/dashboard/shelf-life` | `/dashboard/inventory?tab=shelf-life` | `/dashboard/inventory` | 11 |
| `traceability/page.tsx` | `/dashboard/traceability` | `/dashboard/inventory?tab=traceability` | `/dashboard/inventory` | 8 |
| `logistics/containers/page.tsx` | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` | `/dashboard/logistics` | 0 |
| `fleet/page.tsx` | `/dashboard/fleet` | `/dashboard/logistics?tab=fleet` | `/dashboard/logistics` | 7 |
| `marketing/campaigns/page.tsx` | `/dashboard/marketing/campaigns` | `/dashboard/marketing?tab=campaigns` | `/dashboard/marketing` | 2 |
| `marketing/promotions/page.tsx` | `/dashboard/marketing/promotions` | `/dashboard/marketing?tab=promotions` | `/dashboard/marketing` | 2 |
| `marketing/trade-spend/page.tsx` | `/dashboard/marketing/trade-spend` | `/dashboard/marketing?tab=trade-spend` | `/dashboard/marketing` | 2 |
| `marketing/ads/page.tsx` | `/dashboard/marketing/ads` | `/dashboard/marketing?tab=ads` | `/dashboard/marketing` | 2 |
| `marketing/social-media/page.tsx` | `/dashboard/marketing/social-media` | `/dashboard/marketing?tab=social-media` | `/dashboard/marketing` | 2 |
| `marketing/segments/page.tsx` | `/dashboard/marketing/segments` | `/dashboard/marketing?tab=segments` | `/dashboard/marketing` | 2 |
| `marketing/influencers/page.tsx` | `/dashboard/marketing/influencers` | `/dashboard/marketing?tab=influencers` | `/dashboard/marketing` | 2 |
| `marketing/ecommerce/page.tsx` | `/dashboard/marketing/ecommerce` | `/dashboard/marketing?tab=ecommerce` | `/dashboard/marketing` | 1 |
| `marketing/visits/page.tsx` | `/dashboard/marketing/visits` | `/dashboard/marketing?tab=visits` | `/dashboard/marketing` | 2 |
| `marketing/brand-spend/page.tsx` | `/dashboard/marketing/brand-spend` | `/dashboard/marketing?tab=brand-spend` | `/dashboard/marketing` | 2 |
| `tpm/page.tsx` | `/dashboard/tpm` | `/dashboard/marketing?tab=tpm` | `/dashboard/marketing` | 11 |
| `market-intelligence/page.tsx` | `/dashboard/market-intelligence` | `/dashboard/marketing?tab=market-intel` | `/dashboard/marketing` | 0 |
| `payroll/profiles/page.tsx` | `/dashboard/payroll/profiles` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `payroll/reports/page.tsx` | `/dashboard/payroll/reports` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `planning/schedule/page.tsx` | `/dashboard/planning/schedule` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/capacity/page.tsx` | `/dashboard/planning/capacity` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/simulation/page.tsx` | `/dashboard/planning/simulation` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/bottlenecks/page.tsx` | `/dashboard/planning/bottlenecks` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/changeover/page.tsx` | `/dashboard/planning/changeover` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `mrp/page.tsx` | `/dashboard/mrp` | `/dashboard/planning?tab=mrp` | `/dashboard/planning` | 3 |
| `mps/page.tsx` | `/dashboard/mps` | `/dashboard/planning?tab=mps` | `/dashboard/planning` | 0 |
| `kanban/page.tsx` | `/dashboard/kanban` | `/dashboard/planning?tab=kanban` | `/dashboard/planning` | 5 |
| `procurement-suggestion/page.tsx` | `/dashboard/procurement-suggestion` | `/dashboard/procurement?tab=suggestions` | `/dashboard/procurement` | 4 |
| `subcontracting/page.tsx` | `/dashboard/subcontracting` | `/dashboard/procurement?tab=subcontracting` | `/dashboard/procurement` | 5 |
| `landed-cost/page.tsx` | `/dashboard/landed-cost` | `/dashboard/procurement?tab=landed-cost` | `/dashboard/procurement` | 4 |
| `supplier-portal/page.tsx` | `/dashboard/supplier-portal` | `/dashboard/procurement?tab=supplier-portal` | `/dashboard/procurement` | 1 |
| `production/orders/page.tsx` | `/dashboard/production/orders` | `/dashboard/production?tab=orders` | `/dashboard/production` | 1 |
| `production-execution/page.tsx` | `/dashboard/production-execution` | `/dashboard/production?tab=execution` | `/dashboard/production` | 2 |
| `machine-ops/page.tsx` | `/dashboard/machine-ops` | `/dashboard/production?tab=machine-ops` | `/dashboard/production` | 9 |
| `material-flow/page.tsx` | `/dashboard/material-flow` | `/dashboard/production?tab=material-flow` | `/dashboard/production` | 9 |
| `projects/page.tsx` | `/dashboard/projects` | `/dashboard/production?tab=projects` | `/dashboard/production` | 1 |
| `quality/consumer-complaints/page.tsx` | `/dashboard/quality/consumer-complaints` | `/dashboard/quality?tab=consumer-complaints` | `/dashboard/quality` | 0 |
| `qms/page.tsx` | `/dashboard/qms` | `/dashboard/quality?tab=qms` | `/dashboard/quality` | 10 |
| `allergen/page.tsx` | `/dashboard/allergen` | `/dashboard/quality?tab=allergen` | `/dashboard/quality` | 3 |
| `brand-assets/page.tsx` | `/dashboard/brand-assets` | `/dashboard/quality?tab=brand-assets` | `/dashboard/quality` | 1 |
| `price-lists/page.tsx` | `/dashboard/price-lists` | `/dashboard/sales?tab=price-lists` | `/dashboard/sales` | 2 |
| `dynamic-pricing/page.tsx` | `/dashboard/dynamic-pricing` | `/dashboard/sales?tab=dynamic-pricing` | `/dashboard/sales` | 0 |
| `contracts/page.tsx` | `/dashboard/contracts` | `/dashboard/sales?tab=contracts` | `/dashboard/sales` | 5 |
| `recurring-orders/page.tsx` | `/dashboard/recurring-orders` | `/dashboard/sales?tab=recurring` | `/dashboard/sales` | 5 |
| `commissions/page.tsx` | `/dashboard/commissions` | `/dashboard/sales?tab=commissions` | `/dashboard/sales` | 4 |
| `secondary-sales/page.tsx` | `/dashboard/secondary-sales` | `/dashboard/sales?tab=secondary` | `/dashboard/sales` | 4 |
| `van-sales/page.tsx` | `/dashboard/van-sales` | `/dashboard/sales?tab=van-sales` | `/dashboard/sales` | 8 |
| `portal/page.tsx` | `/dashboard/portal` | `/dashboard/sales?tab=portal` | `/dashboard/sales` | 8 |
| `utility-management/kpi-center/page.tsx` | `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management?tab=kpi-center` | `/dashboard/utility-management` | 10 |
| `utility-management/reports/page.tsx` | `/dashboard/utility-management/reports` | `/dashboard/utility-management?tab=reports` | `/dashboard/utility-management` | 7 |
| `iot/page.tsx` | `/dashboard/iot` | `/dashboard/utility-management?tab=iot` | `/dashboard/utility-management` | 0 |
| `esg/page.tsx` | `/dashboard/esg` | `/dashboard/utility-management?tab=esg` | `/dashboard/utility-management` | 5 |
| `wms/page.tsx` | `/dashboard/wms` | `/dashboard/warehouses?tab=wms` | `/dashboard/warehouses` | 0 |

---

## Git History — High-Confidence Real Page Matches

These broken targets had REAL implementations in commit `674b6c5` (2026-05-01).
All were deleted/replaced with redirect stubs in `bd6faf5` (2026-05-17).
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT**

| Module | Target Route | Source File in Git | Confidence |
|--------|-------------|-------------------|------------|
| Administration | `/dashboard/custom-fields/new-field` | `frontend/src/app/dashboard/custom-fields/new-field/page.tsx` | high |
| Administration | `/dashboard/custom-fields/fields` | `frontend/src/app/dashboard/custom-fields/fields/page.tsx` | high |
| Administration | `/dashboard/custom-fields/form-builder` | `frontend/src/app/dashboard/custom-fields/form-builder/page.tsx` | high |
| Administration | `/dashboard/custom-fields/workflow-rules` | `frontend/src/app/dashboard/custom-fields/workflow-rules/page.tsx` | high |
| Administration | `/dashboard/custom-fields/values` | `frontend/src/app/dashboard/custom-fields/values/page.tsx` | high |
| Administration | `/dashboard/custom-fields/ai` | `frontend/src/app/dashboard/custom-fields/ai/page.tsx` | high |
| Administration | `/dashboard/mobile/approvals` | `frontend/src/app/dashboard/mobile/approvals/page.tsx` | high |
| Administration | `/dashboard/mobile/devices` | `frontend/src/app/dashboard/mobile/devices/page.tsx` | high |
| Administration | `/dashboard/approvals` | `frontend/src/app/dashboard/approvals/page.tsx` | high |
| Administration | `/dashboard/notification-center` | `frontend/src/app/dashboard/notification-center/page.tsx` | high |
| Other | `/dashboard/tax` | `frontend/src/app/dashboard/tax/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/production/orders` | `frontend/src/app/dashboard/production/orders/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/inventory` | `frontend/src/app/dashboard/reports/inventory/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/production` | `frontend/src/app/dashboard/reports/production/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/procurement` | `frontend/src/app/dashboard/reports/procurement/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/sales` | `frontend/src/app/dashboard/reports/sales/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/finance` | `frontend/src/app/dashboard/reports/finance/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/payments` | `frontend/src/app/dashboard/reports/payments/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/reports/marketing` | `frontend/src/app/dashboard/reports/marketing/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/catalog` | `frontend/src/app/dashboard/report-builder/catalog/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/builder` | `frontend/src/app/dashboard/report-builder/builder/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/saved` | `frontend/src/app/dashboard/report-builder/saved/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/viewer` | `frontend/src/app/dashboard/report-builder/viewer/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/dashboards` | `frontend/src/app/dashboard/report-builder/dashboards/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/schedules` | `frontend/src/app/dashboard/report-builder/schedules/page.tsx` | high |
| Intelligence / Analytics | `/dashboard/report-builder/ai` | `frontend/src/app/dashboard/report-builder/ai/page.tsx` | high |
| Documents & Communication | `/dashboard/chatter/feed` | `frontend/src/app/dashboard/chatter/feed/page.tsx` | high |
| Documents & Communication | `/dashboard/chatter/search` | `frontend/src/app/dashboard/chatter/search/page.tsx` | high |
| Documents & Communication | `/dashboard/chatter/reports` | `frontend/src/app/dashboard/chatter/reports/page.tsx` | high |
| Documents & Communication | `/dashboard/chatter/ai` | `frontend/src/app/dashboard/chatter/ai/page.tsx` | high |
| Documents & Communication | `/dashboard/calendar/view` | `frontend/src/app/dashboard/calendar/view/page.tsx` | high |
| Documents & Communication | `/dashboard/calendar/new-event` | `frontend/src/app/dashboard/calendar/new-event/page.tsx` | high |
| Documents & Communication | `/dashboard/calendar/resources` | `frontend/src/app/dashboard/calendar/resources/page.tsx` | high |
| Documents & Communication | `/dashboard/calendar/availability` | `frontend/src/app/dashboard/calendar/availability/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/list` | `frontend/src/app/dashboard/notification-center/list/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/preferences` | `frontend/src/app/dashboard/notification-center/preferences/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/templates` | `frontend/src/app/dashboard/notification-center/templates/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/schedules` | `frontend/src/app/dashboard/notification-center/schedules/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/reports` | `frontend/src/app/dashboard/notification-center/reports/page.tsx` | high |
| Documents & Communication | `/dashboard/notification-center/ai` | `frontend/src/app/dashboard/notification-center/ai/page.tsx` | high |
| Commercial / CRM | `/dashboard/surveys/new` | `frontend/src/app/dashboard/surveys/new/page.tsx` | high |
| Documents & Communication | `/dashboard/documents/new` | `frontend/src/app/dashboard/documents/new/page.tsx` | high |
| Documents & Communication | `/dashboard/esign` | `frontend/src/app/dashboard/esign/page.tsx` | high |
| Documents & Communication | `/dashboard/knowledge-base/articles` | `frontend/src/app/dashboard/knowledge-base/articles/page.tsx` | high |
| Documents & Communication | `/dashboard/knowledge-base/articles/new` | `frontend/src/app/dashboard/knowledge-base/articles/new/page.tsx` | high |
| Finance | `/dashboard/finance/accounting/customers-ledger` | `frontend/src/app/dashboard/finance/accounting/customers-ledger/page.tsx` | high |
| Finance | `/dashboard/finance/accounting/suppliers-ledger` | `frontend/src/app/dashboard/finance/accounting/suppliers-ledger/page.tsx` | high |
| Finance | `/dashboard/finance/accounting/sales-invoices` | `frontend/src/app/dashboard/finance/accounting/sales-invoices/page.tsx` | high |
| Finance | `/dashboard/finance/accounting/purchase-invoices` | `frontend/src/app/dashboard/finance/accounting/purchase-invoices/page.tsx` | high |
| Finance | `/dashboard/finance/accounting/payments` | `frontend/src/app/dashboard/finance/accounting/payments/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/import` | `frontend/src/app/dashboard/bank-reconciliation/import/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/statements` | `frontend/src/app/dashboard/bank-reconciliation/statements/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/open-items` | `frontend/src/app/dashboard/bank-reconciliation/open-items/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/balance` | `frontend/src/app/dashboard/bank-reconciliation/balance/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/rules` | `frontend/src/app/dashboard/bank-reconciliation/rules/page.tsx` | high |
| Finance | `/dashboard/bank-reconciliation/ai` | `frontend/src/app/dashboard/bank-reconciliation/ai/page.tsx` | high |
| Finance | `/dashboard/invoice-match/review-queue` | `frontend/src/app/dashboard/invoice-match/review-queue/page.tsx` | high |
| Finance | `/dashboard/invoice-match/matches` | `frontend/src/app/dashboard/invoice-match/matches/page.tsx` | high |
| Finance | `/dashboard/invoice-match/blocked` | `frontend/src/app/dashboard/invoice-match/blocked/page.tsx` | high |
| Finance | `/dashboard/invoice-match/duplicates` | `frontend/src/app/dashboard/invoice-match/duplicates/page.tsx` | high |
| Finance | `/dashboard/invoice-match/ai` | `frontend/src/app/dashboard/invoice-match/ai/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/assets` | `frontend/src/app/dashboard/fixed-assets/assets/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/categories` | `frontend/src/app/dashboard/fixed-assets/categories/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/depreciation` | `frontend/src/app/dashboard/fixed-assets/depreciation/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/posting` | `frontend/src/app/dashboard/fixed-assets/posting/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/disposal` | `frontend/src/app/dashboard/fixed-assets/disposal/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/transfer` | `frontend/src/app/dashboard/fixed-assets/transfer/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/import` | `frontend/src/app/dashboard/fixed-assets/import/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/ai` | `frontend/src/app/dashboard/fixed-assets/ai/page.tsx` | high |
| Finance | `/dashboard/fixed-assets/assets/new` | `frontend/src/app/dashboard/fixed-assets/assets/new/page.tsx` | high |
| Finance | `/dashboard/dimensions/types` | `frontend/src/app/dashboard/dimensions/types/page.tsx` | high |
| Finance | `/dashboard/dimensions/values` | `frontend/src/app/dashboard/dimensions/values/page.tsx` | high |
| Finance | `/dashboard/dimensions/cost-centers` | `frontend/src/app/dashboard/dimensions/cost-centers/page.tsx` | high |
| Finance | `/dashboard/dimensions/allocations` | `frontend/src/app/dashboard/dimensions/allocations/page.tsx` | high |
| Finance | `/dashboard/dimensions/allocation-run` | `frontend/src/app/dashboard/dimensions/allocation-run/page.tsx` | high |
| Finance | `/dashboard/dimensions/validation` | `frontend/src/app/dashboard/dimensions/validation/page.tsx` | high |
| Finance | `/dashboard/dimensions/defaults` | `frontend/src/app/dashboard/dimensions/defaults/page.tsx` | high |
| Finance | `/dashboard/dimensions/reclassify` | `frontend/src/app/dashboard/dimensions/reclassify/page.tsx` | high |
| Finance | `/dashboard/dimensions/completeness` | `frontend/src/app/dashboard/dimensions/completeness/page.tsx` | high |
| Finance | `/dashboard/dimensions/ai` | `frontend/src/app/dashboard/dimensions/ai/page.tsx` | high |
| Finance | `/dashboard/dunning/aging` | `frontend/src/app/dashboard/dunning/aging/page.tsx` | high |
| Finance | `/dashboard/dunning/workqueue` | `frontend/src/app/dashboard/dunning/workqueue/page.tsx` | high |
| Finance | `/dashboard/dunning/credit-holds` | `frontend/src/app/dashboard/dunning/credit-holds/page.tsx` | high |
| Finance | `/dashboard/dunning/policies` | `frontend/src/app/dashboard/dunning/policies/page.tsx` | high |
| Finance | `/dashboard/dunning/cases` | `frontend/src/app/dashboard/dunning/cases/page.tsx` | high |
| Finance | `/dashboard/tax/rules` | `frontend/src/app/dashboard/tax/rules/page.tsx` | high |
| Finance | `/dashboard/tax/regulatory` | `frontend/src/app/dashboard/tax/regulatory/page.tsx` | high |
| Finance | `/dashboard/tax/transactions` | `frontend/src/app/dashboard/tax/transactions/page.tsx` | high |
| Finance | `/dashboard/tax/reports` | `frontend/src/app/dashboard/tax/reports/page.tsx` | high |
| Finance | `/dashboard/expenses/claims` | `frontend/src/app/dashboard/expenses/claims/page.tsx` | high |
| Finance | `/dashboard/expenses/claims/new` | `frontend/src/app/dashboard/expenses/claims/new/page.tsx` | high |
| Finance | `/dashboard/expenses/approval` | `frontend/src/app/dashboard/expenses/approval/page.tsx` | high |
| Finance | `/dashboard/expenses/reimbursement` | `frontend/src/app/dashboard/expenses/reimbursement/page.tsx` | high |
| Finance | `/dashboard/expenses/advances` | `frontend/src/app/dashboard/expenses/advances/page.tsx` | high |
| Finance | `/dashboard/expenses/categories` | `frontend/src/app/dashboard/expenses/categories/page.tsx` | high |
| Finance | `/dashboard/expenses/policies` | `frontend/src/app/dashboard/expenses/policies/page.tsx` | high |
| Finance | `/dashboard/expenses/reports` | `frontend/src/app/dashboard/expenses/reports/page.tsx` | high |
| Finance | `/dashboard/expenses/ai` | `frontend/src/app/dashboard/expenses/ai/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/requisitions` | `frontend/src/app/dashboard/recruitment/requisitions/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/requisitions/new` | `frontend/src/app/dashboard/recruitment/requisitions/new/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/candidates` | `frontend/src/app/dashboard/recruitment/candidates/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/pipeline` | `frontend/src/app/dashboard/recruitment/pipeline/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/interviews` | `frontend/src/app/dashboard/recruitment/interviews/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/offers` | `frontend/src/app/dashboard/recruitment/offers/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/stages` | `frontend/src/app/dashboard/recruitment/stages/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/reports` | `frontend/src/app/dashboard/recruitment/reports/page.tsx` | high |
| HR & Payroll | `/dashboard/recruitment/ai` | `frontend/src/app/dashboard/recruitment/ai/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/profile` | `frontend/src/app/dashboard/ess/profile/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/leave` | `frontend/src/app/dashboard/ess/leave/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/attendance` | `frontend/src/app/dashboard/ess/attendance/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/documents` | `frontend/src/app/dashboard/ess/documents/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/requests` | `frontend/src/app/dashboard/ess/requests/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/notifications` | `frontend/src/app/dashboard/ess/notifications/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/ai` | `frontend/src/app/dashboard/ess/ai/page.tsx` | high |
| HR & Payroll | `/dashboard/ess/admin` | `frontend/src/app/dashboard/ess/admin/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/periods` | `frontend/src/app/dashboard/appraisals/periods/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/templates` | `frontend/src/app/dashboard/appraisals/templates/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/records` | `frontend/src/app/dashboard/appraisals/records/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/records/new` | `frontend/src/app/dashboard/appraisals/records/new/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/self-review` | `frontend/src/app/dashboard/appraisals/self-review/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/manager-queue` | `frontend/src/app/dashboard/appraisals/manager-queue/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/hr-review` | `frontend/src/app/dashboard/appraisals/hr-review/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/development-plans` | `frontend/src/app/dashboard/appraisals/development-plans/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/reports` | `frontend/src/app/dashboard/appraisals/reports/page.tsx` | high |
| HR & Payroll | `/dashboard/appraisals/ai` | `frontend/src/app/dashboard/appraisals/ai/page.tsx` | high |
| HR & Payroll | `/dashboard/training/programs` | `frontend/src/app/dashboard/training/programs/page.tsx` | high |
| HR & Payroll | `/dashboard/training/sessions` | `frontend/src/app/dashboard/training/sessions/page.tsx` | high |
| HR & Payroll | `/dashboard/training/skill-matrix` | `frontend/src/app/dashboard/training/skill-matrix/page.tsx` | high |
| HR & Payroll | `/dashboard/training/assignments` | `frontend/src/app/dashboard/training/assignments/page.tsx` | high |
| HR & Payroll | `/dashboard/training/certifications` | `frontend/src/app/dashboard/training/certifications/page.tsx` | high |
| HR & Payroll | `/dashboard/training/feedback` | `frontend/src/app/dashboard/training/feedback/page.tsx` | high |
| HR & Payroll | `/dashboard/training/reports` | `frontend/src/app/dashboard/training/reports/page.tsx` | high |
| HR & Payroll | `/dashboard/training/ai` | `frontend/src/app/dashboard/training/ai/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/my-timesheets` | `frontend/src/app/dashboard/timesheets/my-timesheets/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/time-entry` | `frontend/src/app/dashboard/timesheets/time-entry/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/weekly-view` | `frontend/src/app/dashboard/timesheets/weekly-view/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/approval-queue` | `frontend/src/app/dashboard/timesheets/approval-queue/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/reports` | `frontend/src/app/dashboard/timesheets/reports/page.tsx` | high |
| HR & Payroll | `/dashboard/timesheets/ai` | `frontend/src/app/dashboard/timesheets/ai/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/definitions` | `frontend/src/app/dashboard/webhooks/definitions/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/subscriptions` | `frontend/src/app/dashboard/webhooks/subscriptions/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/deliveries` | `frontend/src/app/dashboard/webhooks/deliveries/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/dead-letter` | `frontend/src/app/dashboard/webhooks/dead-letter/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/inbound` | `frontend/src/app/dashboard/webhooks/inbound/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks/reports` | `frontend/src/app/dashboard/webhooks/reports/page.tsx` | high |
| Administration / Integrations | `/dashboard/developer/keys` | `frontend/src/app/dashboard/developer/keys/page.tsx` | high |
| Administration / Integrations | `/dashboard/developer/graphql` | `frontend/src/app/dashboard/developer/graphql/page.tsx` | high |
| Administration / Integrations | `/dashboard/webhooks` | `frontend/src/app/dashboard/webhooks/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/cycle-count/plans` | `frontend/src/app/dashboard/cycle-count/plans/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/cycle-count/tasks` | `frontend/src/app/dashboard/cycle-count/tasks/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/cycle-count/entries` | `frontend/src/app/dashboard/cycle-count/entries/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/cycle-count/variances` | `frontend/src/app/dashboard/cycle-count/variances/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/cycle-count/reports` | `frontend/src/app/dashboard/cycle-count/reports/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/fefo-config` | `frontend/src/app/dashboard/shelf-life/fefo-config/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/lot-aging` | `frontend/src/app/dashboard/shelf-life/lot-aging/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/near-expiry` | `frontend/src/app/dashboard/shelf-life/near-expiry/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/expired` | `frontend/src/app/dashboard/shelf-life/expired/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/retest-queue` | `frontend/src/app/dashboard/shelf-life/retest-queue/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/shipment-validation` | `frontend/src/app/dashboard/shelf-life/shipment-validation/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/production-validation` | `frontend/src/app/dashboard/shelf-life/production-validation/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/compliance` | `frontend/src/app/dashboard/shelf-life/compliance/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/disposition` | `frontend/src/app/dashboard/shelf-life/disposition/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/customer-rules` | `frontend/src/app/dashboard/shelf-life/customer-rules/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/shelf-life/bulk-hold-monitor` | `frontend/src/app/dashboard/shelf-life/bulk-hold-monitor/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/recalls` | `frontend/src/app/dashboard/traceability/recalls/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/search` | `frontend/src/app/dashboard/traceability/search/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/backward` | `frontend/src/app/dashboard/traceability/backward/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/forward` | `frontend/src/app/dashboard/traceability/forward/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/genealogy` | `frontend/src/app/dashboard/traceability/genealogy/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/mock-recall` | `frontend/src/app/dashboard/traceability/mock-recall/page.tsx` | high |
| Supply Chain / Inventory | `/dashboard/traceability/regulatory` | `frontend/src/app/dashboard/traceability/regulatory/page.tsx` | high |
| Logistics | `/dashboard/fleet/vehicles` | `frontend/src/app/dashboard/fleet/vehicles/page.tsx` | high |
| Logistics | `/dashboard/fleet/drivers` | `frontend/src/app/dashboard/fleet/drivers/page.tsx` | high |
| Logistics | `/dashboard/fleet/trips` | `frontend/src/app/dashboard/fleet/trips/page.tsx` | high |
| Logistics | `/dashboard/fleet/fuel` | `frontend/src/app/dashboard/fleet/fuel/page.tsx` | high |
| Logistics | `/dashboard/fleet/maintenance` | `frontend/src/app/dashboard/fleet/maintenance/page.tsx` | high |
| Logistics | `/dashboard/fleet/incidents` | `frontend/src/app/dashboard/fleet/incidents/page.tsx` | high |
| Logistics | `/dashboard/fleet/reports` | `frontend/src/app/dashboard/fleet/reports/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/campaigns/new` | `frontend/src/app/dashboard/marketing/campaigns/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/promotions/new` | `frontend/src/app/dashboard/marketing/promotions/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/trade-spend/new` | `frontend/src/app/dashboard/marketing/trade-spend/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/ads/new` | `frontend/src/app/dashboard/marketing/ads/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/social-media/new` | `frontend/src/app/dashboard/marketing/social-media/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/segments/new` | `frontend/src/app/dashboard/marketing/segments/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/influencers/new` | `frontend/src/app/dashboard/marketing/influencers/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/ecommerce/stores` | `frontend/src/app/dashboard/marketing/ecommerce/stores/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/visits/new` | `frontend/src/app/dashboard/marketing/visits/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/marketing/brand-spend/new` | `frontend/src/app/dashboard/marketing/brand-spend/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/plans/new` | `frontend/src/app/dashboard/tpm/plans/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/promotions/new` | `frontend/src/app/dashboard/tpm/promotions/new/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/promotions` | `frontend/src/app/dashboard/tpm/promotions/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/calendar` | `frontend/src/app/dashboard/tpm/calendar/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/budget` | `frontend/src/app/dashboard/tpm/budget/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/claims` | `frontend/src/app/dashboard/tpm/claims/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/roi` | `frontend/src/app/dashboard/tpm/roi/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/settlement` | `frontend/src/app/dashboard/tpm/settlement/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/plans` | `frontend/src/app/dashboard/tpm/plans/page.tsx` | high |
| Commercial / Marketing | `/dashboard/tpm/ai` | `frontend/src/app/dashboard/tpm/ai/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/mrp/forecast` | `frontend/src/app/dashboard/mrp/forecast/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/mrp/suggestions` | `frontend/src/app/dashboard/mrp/suggestions/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/mrp/run` | `frontend/src/app/dashboard/mrp/run/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/kanban/boards` | `frontend/src/app/dashboard/kanban/boards/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/kanban/view` | `frontend/src/app/dashboard/kanban/view/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/kanban/cards` | `frontend/src/app/dashboard/kanban/cards/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/kanban/reports` | `frontend/src/app/dashboard/kanban/reports/page.tsx` | high |
| Manufacturing / Planning | `/dashboard/kanban/ai` | `frontend/src/app/dashboard/kanban/ai/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/procurement-suggestion/suggestions` | `frontend/src/app/dashboard/procurement-suggestion/suggestions/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/procurement-suggestion/groups` | `frontend/src/app/dashboard/procurement-suggestion/groups/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/procurement-suggestion/supplier-prices` | `frontend/src/app/dashboard/procurement-suggestion/supplier-prices/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/procurement-suggestion/ai` | `frontend/src/app/dashboard/procurement-suggestion/ai/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/subcontracting/locations` | `frontend/src/app/dashboard/subcontracting/locations/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/subcontracting/orders` | `frontend/src/app/dashboard/subcontracting/orders/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/subcontracting/stock` | `frontend/src/app/dashboard/subcontracting/stock/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/subcontracting/yield` | `frontend/src/app/dashboard/subcontracting/yield/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/subcontracting/ai` | `frontend/src/app/dashboard/subcontracting/ai/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/landed-cost/new` | `frontend/src/app/dashboard/landed-cost/new/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/landed-cost/ai` | `frontend/src/app/dashboard/landed-cost/ai/page.tsx` | high |
| Supply Chain / Procurement | `/dashboard/landed-cost/documents` | `frontend/src/app/dashboard/landed-cost/documents/page.tsx` | high |
| Manufacturing / Production | `/dashboard/production-execution/work-orders` | `frontend/src/app/dashboard/production-execution/work-orders/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/machines` | `frontend/src/app/dashboard/machine-ops/machines/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/operators` | `frontend/src/app/dashboard/machine-ops/operators/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/teams` | `frontend/src/app/dashboard/machine-ops/teams/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/runtime` | `frontend/src/app/dashboard/machine-ops/runtime/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/performance` | `frontend/src/app/dashboard/machine-ops/performance/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/downtime` | `frontend/src/app/dashboard/machine-ops/downtime/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/costing` | `frontend/src/app/dashboard/machine-ops/costing/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/certs` | `frontend/src/app/dashboard/machine-ops/certs/page.tsx` | high |
| Manufacturing / Production | `/dashboard/machine-ops/assignment` | `frontend/src/app/dashboard/machine-ops/assignment/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/issue` | `frontend/src/app/dashboard/material-flow/issue/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/wip-transfer` | `frontend/src/app/dashboard/material-flow/wip-transfer/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/bulk-transfer` | `frontend/src/app/dashboard/material-flow/bulk-transfer/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/fg-receipt` | `frontend/src/app/dashboard/material-flow/fg-receipt/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/reservations` | `frontend/src/app/dashboard/material-flow/reservations/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/tanks` | `frontend/src/app/dashboard/material-flow/tanks/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/returns` | `frontend/src/app/dashboard/material-flow/returns/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/reconciliation` | `frontend/src/app/dashboard/material-flow/reconciliation/page.tsx` | high |
| Manufacturing / Production | `/dashboard/material-flow/history` | `frontend/src/app/dashboard/material-flow/history/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/inspections` | `frontend/src/app/dashboard/qms/inspections/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/templates` | `frontend/src/app/dashboard/qms/templates/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/haccp` | `frontend/src/app/dashboard/qms/haccp/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/ccp` | `frontend/src/app/dashboard/qms/ccp/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/deviations` | `frontend/src/app/dashboard/qms/deviations/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/corrective-actions` | `frontend/src/app/dashboard/qms/corrective-actions/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/quarantine` | `frontend/src/app/dashboard/qms/quarantine/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/allergen` | `frontend/src/app/dashboard/qms/allergen/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/reports` | `frontend/src/app/dashboard/qms/reports/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/qms/ai` | `frontend/src/app/dashboard/qms/ai/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/allergen/material-profiles` | `frontend/src/app/dashboard/allergen/material-profiles/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/allergen/product-allergens` | `frontend/src/app/dashboard/allergen/product-allergens/page.tsx` | high |
| Factory Operations / Quality | `/dashboard/allergen/change-logs` | `frontend/src/app/dashboard/allergen/change-logs/page.tsx` | high |
| Commercial / Sales | `/dashboard/price-lists/approval-queue` | `frontend/src/app/dashboard/price-lists/approval-queue/page.tsx` | high |
| Commercial / Sales | `/dashboard/contracts/new` | `frontend/src/app/dashboard/contracts/new/page.tsx` | high |
| Commercial / Sales | `/dashboard/contracts/list` | `frontend/src/app/dashboard/contracts/list/page.tsx` | high |
| Commercial / Sales | `/dashboard/contracts/expiring` | `frontend/src/app/dashboard/contracts/expiring/page.tsx` | high |
| Commercial / Sales | `/dashboard/contracts/ai` | `frontend/src/app/dashboard/contracts/ai/page.tsx` | high |
| Commercial / Sales | `/dashboard/recurring-orders/templates/new` | `frontend/src/app/dashboard/recurring-orders/templates/new/page.tsx` | high |
| Commercial / Sales | `/dashboard/recurring-orders/templates` | `frontend/src/app/dashboard/recurring-orders/templates/page.tsx` | high |
| Commercial / Sales | `/dashboard/recurring-orders/reports` | `frontend/src/app/dashboard/recurring-orders/reports/page.tsx` | high |
| Commercial / Sales | `/dashboard/recurring-orders/ai` | `frontend/src/app/dashboard/recurring-orders/ai/page.tsx` | high |
| Commercial / Sales | `/dashboard/commissions/rules` | `frontend/src/app/dashboard/commissions/rules/page.tsx` | high |
| Commercial / Sales | `/dashboard/commissions/transactions` | `frontend/src/app/dashboard/commissions/transactions/page.tsx` | high |
| Commercial / Sales | `/dashboard/commissions/payouts` | `frontend/src/app/dashboard/commissions/payouts/page.tsx` | high |
| Commercial / Sales | `/dashboard/commissions/ai` | `frontend/src/app/dashboard/commissions/ai/page.tsx` | high |
| Commercial / Sales | `/dashboard/secondary-sales/analysis` | `frontend/src/app/dashboard/secondary-sales/analysis/page.tsx` | high |
| Commercial / Sales | `/dashboard/secondary-sales/inventory` | `frontend/src/app/dashboard/secondary-sales/inventory/page.tsx` | high |
| Commercial / Sales | `/dashboard/secondary-sales/upload` | `frontend/src/app/dashboard/secondary-sales/upload/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/vans/new` | `frontend/src/app/dashboard/van-sales/vans/new/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/route` | `frontend/src/app/dashboard/van-sales/route/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/pos` | `frontend/src/app/dashboard/van-sales/pos/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/stock` | `frontend/src/app/dashboard/van-sales/stock/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/reconciliation` | `frontend/src/app/dashboard/van-sales/reconciliation/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/vans` | `frontend/src/app/dashboard/van-sales/vans/page.tsx` | high |
| Commercial / Sales | `/dashboard/van-sales/ai` | `frontend/src/app/dashboard/van-sales/ai/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/accounts` | `frontend/src/app/dashboard/portal/accounts/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/drafts` | `frontend/src/app/dashboard/portal/drafts/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/claims` | `frontend/src/app/dashboard/portal/claims/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/users` | `frontend/src/app/dashboard/portal/users/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/activity` | `frontend/src/app/dashboard/portal/activity/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/ai` | `frontend/src/app/dashboard/portal/ai/page.tsx` | high |
| Commercial / Sales | `/dashboard/portal/reports` | `frontend/src/app/dashboard/portal/reports/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/electricity` | `frontend/src/app/dashboard/utility-management/kpi-center/electricity/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/water` | `frontend/src/app/dashboard/utility-management/kpi-center/water/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/soft-water` | `frontend/src/app/dashboard/utility-management/kpi-center/soft-water/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/boiler` | `frontend/src/app/dashboard/utility-management/kpi-center/boiler/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/compressor` | `frontend/src/app/dashboard/utility-management/kpi-center/compressor/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/solar` | `frontend/src/app/dashboard/utility-management/kpi-center/solar/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/chemicals` | `frontend/src/app/dashboard/utility-management/kpi-center/chemicals/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/wastewater` | `frontend/src/app/dashboard/utility-management/kpi-center/wastewater/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/utility-cost` | `frontend/src/app/dashboard/utility-management/kpi-center/utility-cost/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center/machine-utility` | `frontend/src/app/dashboard/utility-management/kpi-center/machine-utility/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center` | `frontend/src/app/dashboard/utility-management/kpi-center/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center` | `frontend/src/app/dashboard/utility-management/kpi-center/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/daily-consumption` | `frontend/src/app/dashboard/utility-management/reports/daily-consumption/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/equipment-efficiency` | `frontend/src/app/dashboard/utility-management/reports/equipment-efficiency/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/treatment` | `frontend/src/app/dashboard/utility-management/reports/treatment/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/cost-allocation` | `frontend/src/app/dashboard/utility-management/reports/cost-allocation/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/load-analysis` | `frontend/src/app/dashboard/utility-management/reports/load-analysis/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/anomalies` | `frontend/src/app/dashboard/utility-management/reports/anomalies/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/reports/sustainability` | `frontend/src/app/dashboard/utility-management/reports/sustainability/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/utility-management/kpi-center` | `frontend/src/app/dashboard/utility-management/kpi-center/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/esg/activities` | `frontend/src/app/dashboard/esg/activities/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/esg/factors` | `frontend/src/app/dashboard/esg/factors/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/esg/targets` | `frontend/src/app/dashboard/esg/targets/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/esg/reports` | `frontend/src/app/dashboard/esg/reports/page.tsx` | high |
| Factory Operations / Utilities | `/dashboard/esg/intelligence` | `frontend/src/app/dashboard/esg/intelligence/page.tsx` | high |

---

## Unresolved — No Git Match Found

These broken targets have no known implementation in git history.

| Module | Target Route | Source File | Recommendation |
|--------|-------------|-------------|----------------|
| Administration | `/dashboard/users/${r.id` | users/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | `/dashboard/roles/${r.id` | roles/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | `/dashboard/custom-fields/${f.custom_field_id` | custom-fields/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Other | `/dashboard/production/quality` | ai/compliance/page.tsx | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / CRM | `/dashboard/crm/records/${rec.id` | crm/pipeline/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | `/dashboard/crm/records/${rec.id` | crm/leads/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | `/dashboard/crm/records/${rec.id` | crm/opportunities/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | `/dashboard/crm/records/${act.crm_record_id` | crm/activities/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | `/dashboard/nps/surveys` | nps/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | `/dashboard/surveys/${s.id` | surveys/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | `/dashboard/documents/${d.id` | documents/compliance/page.tsx | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | `/dashboard/documents/${d.id` | documents/expiring/page.tsx | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | `/dashboard/knowledge-base/${a.id` | knowledge-base/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | `/dashboard/knowledge-base/categories` | knowledge-base/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | `/dashboard/bank-reconciliation/statements/${s.id` | bank-reconciliation/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | `/dashboard/invoice-match/${m.id` | invoice-match/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | `/dashboard/dunning/cases/${c.id` | dunning/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | `/dashboard/traceability/recalls/${r.id` | traceability/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/campaigns/${c.id` | marketing/campaigns/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/promotions/${p.id` | marketing/promotions/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/trade-spend/${t.id` | marketing/trade-spend/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/ads/${a.id` | marketing/ads/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/social-media/${a.id` | marketing/social-media/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/segments/${s.id` | marketing/segments/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/influencers/${i.id` | marketing/influencers/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/visits/${v.id` | marketing/visits/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/marketing/brand-spend/${b.id` | marketing/brand-spend/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | `/dashboard/tpm/promotions/${p.id` | tpm/page.tsx | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | `/dashboard/procurement/orders/${p.id}` | procurement/orders/page.tsx | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | `/dashboard/procurement/orders/${a.po_id}` | procurement/deliveries/page.tsx | CREATE_NEW_REAL_PAGE_REQUIRED |

…and 17 more

---

## Recommendation Summary

| Category | Count | Action |
|----------|-------|--------|
| RESTORE_OLD_PAGE_FROM_GIT | 305 | Restore from git commit `674b6c5` + add BYPASS_PREFIX_REDIRECT |
| CONVERT_TO_WORKSPACE_SUBVIEW | 38 | Change href to `?tab=X&view=Y` pattern in workspace |
| CREATE_NEW_REAL_PAGE_REQUIRED | 10 | No implementation exists — new page required |
| NEEDS_BUSINESS_DECISION | 0 | Intent unclear — needs product decision |

---

*Generated by `scripts/audit-visible-import-graph.js` — DO NOT FIX based on this report. Discovery pass only.*
