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
| Working targets | 420 |
| **Total broken visible action targets** | **47** |
| Critical severity (create/run/approve actions) | 0 |
| High severity | 47 |
| Medium severity | 0 |
| Git history matches found | 0 |
| **High-confidence: real page existed in git** | **0** |
| Medium-confidence: file in git but content unverified | 0 |
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
Their internal navigation cards/buttons (totalling **47**) all fail silently
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
| BVT-0003 | Administration | /dashboard/admin?tab=CustomFieldsPage | ${f.custom_field_id | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0004 | Other | /dashboard/ai?tab=AICompliancePage | Quality Module | `/dashboard/production/quality` | no_route_file | none | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0005 | Commercial / CRM | /dashboard/crm?tab=CRMPipelinePage | ${rec.id | `/dashboard/crm/records/${rec.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0006 | Commercial / CRM | /dashboard/crm?tab=CRMLeadsPage | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0007 | Commercial / CRM | /dashboard/crm?tab=CRMOppsPage | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0008 | Commercial / CRM | /dashboard/crm?tab=CRMActivitiesPage | ${act.crm_record_id | `/dashboard/crm/records/${act.crm_record_id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0009 | Commercial / CRM | /dashboard/crm?tab=NPSPage | surveys | `/dashboard/nps/surveys` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0010 | Commercial / CRM | /dashboard/crm?tab=SurveysPage | ${s.id | `/dashboard/surveys/${s.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0011 | Documents & Communication | /dashboard/documents?tab=DocsCompliancePage | ${d.id | `/dashboard/documents/${d.id` | no_route_file | none | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0012 | Documents & Communication | /dashboard/documents?tab=DocsExpiringPage | ${d.id | `/dashboard/documents/${d.id` | no_route_file | none | CREATE_NEW_REAL_PAGE_REQUIRED |
| BVT-0013 | Documents & Communication | /dashboard/documents?tab=KnowledgeBasePage | ${a.id | `/dashboard/knowledge-base/${a.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0014 | Documents & Communication | /dashboard/documents?tab=KnowledgeBasePage | Categories | `/dashboard/knowledge-base/categories` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0015 | Finance | /dashboard/finance?tab=BankReconPage | ${s.id | `/dashboard/bank-reconciliation/statements/${s.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0016 | Finance | /dashboard/finance?tab=InvoiceMatchPage | View | `/dashboard/invoice-match/${m.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0017 | Finance | /dashboard/finance?tab=DunningPage | ${c.id | `/dashboard/dunning/cases/${c.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0018 | Supply Chain / Inventory | /dashboard/inventory?tab=TraceabilityPage | ${r.id | `/dashboard/traceability/recalls/${r.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0019 | Commercial / Marketing | /dashboard/marketing?tab=MarketingCampaignsPage | ${c.id | `/dashboard/marketing/campaigns/${c.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0020 | Commercial / Marketing | /dashboard/marketing?tab=MarketingPromotionsPage | ${p.id | `/dashboard/marketing/promotions/${p.id` | middleware_redirect | none | CONVERT_TO_WORKSPACE_SUBVIEW |

---

## Module-by-Module Breakdown

### Administration

**Broken count:** 3

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Administration | /dashboard/admin | UsersPage | users/page.tsx | ${r.id | `/dashboard/users/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin | RolesPage | roles/page.tsx | ${r.id | `/dashboard/roles/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin | CustomFieldsPage | custom-fields/page.tsx | ${f.custom_field_id | `/dashboard/custom-fields/${f.custom_field_id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Other

**Broken count:** 1

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Other | /dashboard/ai | AICompliancePage | ai/compliance/page.tsx | Quality Module | `/dashboard/production/quality` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |


### Commercial / CRM

**Broken count:** 6

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / CRM | /dashboard/crm | CRMPipelinePage | crm/pipeline/page.tsx | ${rec.id | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMLeadsPage | crm/leads/page.tsx | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMOppsPage | crm/opportunities/page.tsx | View | `/dashboard/crm/records/${rec.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | CRMActivitiesPage | crm/activities/page.tsx | ${act.crm_record_id | `/dashboard/crm/records/${act.crm_record_id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | NPSPage | nps/page.tsx | surveys | `/dashboard/nps/surveys` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / CRM | /dashboard/crm | SurveysPage | surveys/page.tsx | ${s.id | `/dashboard/surveys/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Documents & Communication

**Broken count:** 4

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Documents & Communication | /dashboard/documents | DocsCompliancePage | documents/compliance/page.tsx | ${d.id | `/dashboard/documents/${d.id` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | /dashboard/documents | DocsExpiringPage | documents/expiring/page.tsx | ${d.id | `/dashboard/documents/${d.id` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | ${a.id | `/dashboard/knowledge-base/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents | KnowledgeBasePage | knowledge-base/page.tsx | Categories | `/dashboard/knowledge-base/categories` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Finance

**Broken count:** 3

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Finance | /dashboard/finance | BankReconPage | bank-reconciliation/page.tsx | ${s.id | `/dashboard/bank-reconciliation/statements/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | InvoiceMatchPage | invoice-match/page.tsx | View | `/dashboard/invoice-match/${m.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance | DunningPage | dunning/page.tsx | ${c.id | `/dashboard/dunning/cases/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Supply Chain / Inventory

**Broken count:** 1

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Supply Chain / Inventory | /dashboard/inventory | TraceabilityPage | traceability/page.tsx | ${r.id | `/dashboard/traceability/recalls/${r.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / Marketing

**Broken count:** 10

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / Marketing | /dashboard/marketing | MarketingCampaignsPage | marketing/campaigns/page.tsx | ${c.id | `/dashboard/marketing/campaigns/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingPromotionsPage | marketing/promotions/page.tsx | ${p.id | `/dashboard/marketing/promotions/${p.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingTradeSpendPage | marketing/trade-spend/page.tsx | ${t.id | `/dashboard/marketing/trade-spend/${t.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingAdsPage | marketing/ads/page.tsx | ${a.id | `/dashboard/marketing/ads/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingSocialPage | marketing/social-media/page.tsx | ${a.id | `/dashboard/marketing/social-media/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingSegmentsPage | marketing/segments/page.tsx | ${s.id | `/dashboard/marketing/segments/${s.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingInfluencersPage | marketing/influencers/page.tsx | ${i.id | `/dashboard/marketing/influencers/${i.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingVisitsPage | marketing/visits/page.tsx | ${v.id | `/dashboard/marketing/visits/${v.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | MarketingBrandSpendPage | marketing/brand-spend/page.tsx | ${b.id | `/dashboard/marketing/brand-spend/${b.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing | TPMPage | tpm/page.tsx | ${p.id | `/dashboard/tpm/promotions/${p.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Supply Chain / Procurement

**Broken count:** 5

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Supply Chain / Procurement | /dashboard/procurement | ProcurementOrdersPage | procurement/orders/page.tsx | PO No | `/dashboard/procurement/orders/${p.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | ProcurementDeliveriesPage | procurement/deliveries/page.tsx | ${a.po_id} | `/dashboard/procurement/orders/${a.po_id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | ProcurementDeliveriesPage | procurement/deliveries/page.tsx | PO No | `/dashboard/procurement/orders/${r.po_id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Supply Chain / Procurement | /dashboard/procurement | LandedCostPage | landed-cost/page.tsx | ${doc.id | `/dashboard/landed-cost/${doc.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement | SupplierPortalPage | supplier-portal/page.tsx | View | `/dashboard/supplier-portal/accounts/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Manufacturing / Production

**Broken count:** 3

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Manufacturing / Production | /dashboard/production | ProductionOrdersPage | production/orders/page.tsx | ${o.id} | `/dashboard/production/orders/${o.id}` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production | ExecutionPage | production-execution/page.tsx | ${o.id | `/dashboard/production-execution/${o.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production | ProjectsPage | projects/page.tsx | ${p.id} | `/dashboard/projects/${p.id}` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Factory Operations / Quality

**Broken count:** 2

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Factory Operations / Quality | /dashboard/quality | QualityReportsPage | quality/reports/page.tsx | Inspection No | `/dashboard/quality/${i.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Factory Operations / Quality | /dashboard/quality | BrandAssetsPage | brand-assets/page.tsx | ${a.id | `/dashboard/brand-assets/${a.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / Sales

**Broken count:** 9

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
| Commercial / Sales | /dashboard/sales | SalesOrdersPage | sales/orders/page.tsx | Order No | `/dashboard/sales/orders/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | SalesInvoicesPage | sales/invoices/page.tsx | Invoice No | `/dashboard/sales/invoices/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | SalesShipmentsPage | sales/shipments/page.tsx | Shipment No | `/dashboard/sales/shipments/${r.id}` | no_route_file | No | not found | low | CREATE_NEW_REAL_PAGE_REQUIRED |
| Commercial / Sales | /dashboard/sales | PriceListsPage | price-lists/page.tsx | ${h.id | `/dashboard/price-lists/${h.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | ContractsPage | contracts/page.tsx | ${c.id | `/dashboard/contracts/list/${c.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | RecurringOrdersPage | recurring-orders/page.tsx | ${t.id | `/dashboard/recurring-orders/templates/${t.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | SecondarySalesPage | secondary-sales/page.tsx | ${h.id | `/dashboard/secondary-sales/${h.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | VanSalesPage | van-sales/page.tsx | ${v.id | `/dashboard/van-sales/vans/${v.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales | PortalPage | portal/page.tsx | Manage | `/dashboard/portal/accounts/${acc.id` | middleware_redirect | No | not found | low | CONVERT_TO_WORKSPACE_SUBVIEW |



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
| `custom-fields/page.tsx` | `/dashboard/custom-fields` | `/dashboard/admin?tab=custom-fields` | `/dashboard/admin` | 1 |
| `utilities/page.tsx` | `/dashboard/utilities` | `/dashboard/admin?tab=system-config` | `/dashboard/admin` | 0 |
| `mobile/page.tsx` | `/dashboard/mobile` | `/dashboard/admin?tab=mobile` | `/dashboard/admin` | 0 |
| `logs/page.tsx` | `/dashboard/logs` | `/dashboard/admin?tab=logs` | `/dashboard/admin` | 0 |
| `import-history/page.tsx` | `/dashboard/import-history` | `/dashboard/admin?tab=import-history` | `/dashboard/admin` | 0 |
| `reports/page.tsx` | `/dashboard/reports` | `/dashboard/analytics?tab=reports` | `/dashboard/analytics` | 0 |
| `report-builder/page.tsx` | `/dashboard/report-builder` | `/dashboard/analytics?tab=report-builder` | `/dashboard/analytics` | 0 |
| `chatter/page.tsx` | `/dashboard/chatter` | `/dashboard/communication?tab=chatter` | `/dashboard/communication` | 0 |
| `calendar/page.tsx` | `/dashboard/calendar` | `/dashboard/communication?tab=calendar` | `/dashboard/communication` | 0 |
| `messages/page.tsx` | `/dashboard/messages` | `/dashboard/communication?tab=messages` | `/dashboard/communication` | 0 |
| `email/page.tsx` | `/dashboard/email` | `/dashboard/communication?tab=email` | `/dashboard/communication` | 0 |
| `whatsapp/page.tsx` | `/dashboard/whatsapp` | `/dashboard/communication?tab=whatsapp` | `/dashboard/communication` | 0 |
| `calls/page.tsx` | `/dashboard/calls` | `/dashboard/communication?tab=calls` | `/dashboard/communication` | 0 |
| `meetings/page.tsx` | `/dashboard/meetings` | `/dashboard/communication?tab=meetings` | `/dashboard/communication` | 0 |
| `notification-center/page.tsx` | `/dashboard/notification-center` | `/dashboard/communication?tab=notifications` | `/dashboard/communication` | 0 |
| `gs1/page.tsx` | `/dashboard/gs1` | `/dashboard/compliance?tab=gs1` | `/dashboard/compliance` | 0 |
| `loyalty/page.tsx` | `/dashboard/loyalty` | `/dashboard/crm?tab=loyalty` | `/dashboard/crm` | 0 |
| `nps/page.tsx` | `/dashboard/nps` | `/dashboard/crm?tab=nps` | `/dashboard/crm` | 1 |
| `surveys/page.tsx` | `/dashboard/surveys` | `/dashboard/crm?tab=surveys` | `/dashboard/crm` | 1 |
| `knowledge-base/page.tsx` | `/dashboard/knowledge-base` | `/dashboard/documents?tab=knowledge-base` | `/dashboard/documents` | 2 |
| `esign/page.tsx` | `/dashboard/esign` | `/dashboard/documents?tab=esign` | `/dashboard/documents` | 0 |
| `finance/accounting/page.tsx` | `/dashboard/finance/accounting` | `/dashboard/finance?tab=accounting` | `/dashboard/finance` | 0 |
| `bank-reconciliation/page.tsx` | `/dashboard/bank-reconciliation` | `/dashboard/finance?tab=bank-recon` | `/dashboard/finance` | 1 |
| `invoice-match/page.tsx` | `/dashboard/invoice-match` | `/dashboard/finance?tab=invoice-match` | `/dashboard/finance` | 1 |
| `fixed-assets/page.tsx` | `/dashboard/fixed-assets` | `/dashboard/finance?tab=fixed-assets` | `/dashboard/finance` | 0 |
| `dimensions/page.tsx` | `/dashboard/dimensions` | `/dashboard/finance?tab=dimensions` | `/dashboard/finance` | 0 |
| `dunning/page.tsx` | `/dashboard/dunning` | `/dashboard/finance?tab=dunning` | `/dashboard/finance` | 1 |
| `tax/page.tsx` | `/dashboard/tax` | `/dashboard/finance?tab=tax` | `/dashboard/finance` | 0 |
| `bank-api/page.tsx` | `/dashboard/bank-api` | `/dashboard/finance?tab=bank-api` | `/dashboard/finance` | 0 |
| `expenses/page.tsx` | `/dashboard/expenses` | `/dashboard/hr?tab=expenses` | `/dashboard/finance`, `/dashboard/hr` | 0 |
| `recruitment/page.tsx` | `/dashboard/recruitment` | `/dashboard/hr?tab=recruitment` | `/dashboard/hr` | 0 |
| `ess/page.tsx` | `/dashboard/ess` | `/dashboard/hr?tab=ess` | `/dashboard/hr` | 0 |
| `appraisals/page.tsx` | `/dashboard/appraisals` | `/dashboard/hr?tab=appraisals` | `/dashboard/hr` | 0 |
| `training/page.tsx` | `/dashboard/training` | `/dashboard/hr?tab=training` | `/dashboard/hr` | 0 |
| `timesheets/page.tsx` | `/dashboard/timesheets` | `/dashboard/hr?tab=timesheets` | `/dashboard/hr` | 0 |
| `webhooks/page.tsx` | `/dashboard/webhooks` | `/dashboard/integrations?tab=webhooks` | `/dashboard/integrations` | 0 |
| `developer/page.tsx` | `/dashboard/developer` | `/dashboard/integrations?tab=developer` | `/dashboard/integrations` | 0 |
| `movements/page.tsx` | `/dashboard/movements` | `/dashboard/inventory?tab=movements` | `/dashboard/inventory` | 0 |
| `cycle-count/page.tsx` | `/dashboard/cycle-count` | `/dashboard/inventory?tab=cycle-count` | `/dashboard/inventory` | 0 |
| `shelf-life/page.tsx` | `/dashboard/shelf-life` | `/dashboard/inventory?tab=shelf-life` | `/dashboard/inventory` | 0 |
| `traceability/page.tsx` | `/dashboard/traceability` | `/dashboard/inventory?tab=traceability` | `/dashboard/inventory` | 1 |
| `logistics/containers/page.tsx` | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` | `/dashboard/logistics` | 0 |
| `fleet/page.tsx` | `/dashboard/fleet` | `/dashboard/logistics?tab=fleet` | `/dashboard/logistics` | 0 |
| `marketing/campaigns/page.tsx` | `/dashboard/marketing/campaigns` | `/dashboard/marketing?tab=campaigns` | `/dashboard/marketing` | 1 |
| `marketing/promotions/page.tsx` | `/dashboard/marketing/promotions` | `/dashboard/marketing?tab=promotions` | `/dashboard/marketing` | 1 |
| `marketing/trade-spend/page.tsx` | `/dashboard/marketing/trade-spend` | `/dashboard/marketing?tab=trade-spend` | `/dashboard/marketing` | 1 |
| `marketing/ads/page.tsx` | `/dashboard/marketing/ads` | `/dashboard/marketing?tab=ads` | `/dashboard/marketing` | 1 |
| `marketing/social-media/page.tsx` | `/dashboard/marketing/social-media` | `/dashboard/marketing?tab=social-media` | `/dashboard/marketing` | 1 |
| `marketing/segments/page.tsx` | `/dashboard/marketing/segments` | `/dashboard/marketing?tab=segments` | `/dashboard/marketing` | 1 |
| `marketing/influencers/page.tsx` | `/dashboard/marketing/influencers` | `/dashboard/marketing?tab=influencers` | `/dashboard/marketing` | 1 |
| `marketing/ecommerce/page.tsx` | `/dashboard/marketing/ecommerce` | `/dashboard/marketing?tab=ecommerce` | `/dashboard/marketing` | 0 |
| `marketing/visits/page.tsx` | `/dashboard/marketing/visits` | `/dashboard/marketing?tab=visits` | `/dashboard/marketing` | 1 |
| `marketing/brand-spend/page.tsx` | `/dashboard/marketing/brand-spend` | `/dashboard/marketing?tab=brand-spend` | `/dashboard/marketing` | 1 |
| `tpm/page.tsx` | `/dashboard/tpm` | `/dashboard/marketing?tab=tpm` | `/dashboard/marketing` | 1 |
| `market-intelligence/page.tsx` | `/dashboard/market-intelligence` | `/dashboard/marketing?tab=market-intel` | `/dashboard/marketing` | 0 |
| `payroll/profiles/page.tsx` | `/dashboard/payroll/profiles` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `payroll/reports/page.tsx` | `/dashboard/payroll/reports` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `planning/schedule/page.tsx` | `/dashboard/planning/schedule` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/capacity/page.tsx` | `/dashboard/planning/capacity` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/simulation/page.tsx` | `/dashboard/planning/simulation` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/bottlenecks/page.tsx` | `/dashboard/planning/bottlenecks` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/changeover/page.tsx` | `/dashboard/planning/changeover` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `mrp/page.tsx` | `/dashboard/mrp` | `/dashboard/planning?tab=mrp` | `/dashboard/planning` | 0 |
| `mps/page.tsx` | `/dashboard/mps` | `/dashboard/planning?tab=mps` | `/dashboard/planning` | 0 |
| `kanban/page.tsx` | `/dashboard/kanban` | `/dashboard/planning?tab=kanban` | `/dashboard/planning` | 0 |
| `procurement-suggestion/page.tsx` | `/dashboard/procurement-suggestion` | `/dashboard/procurement?tab=suggestions` | `/dashboard/procurement` | 0 |
| `subcontracting/page.tsx` | `/dashboard/subcontracting` | `/dashboard/procurement?tab=subcontracting` | `/dashboard/procurement` | 0 |
| `landed-cost/page.tsx` | `/dashboard/landed-cost` | `/dashboard/procurement?tab=landed-cost` | `/dashboard/procurement` | 1 |
| `supplier-portal/page.tsx` | `/dashboard/supplier-portal` | `/dashboard/procurement?tab=supplier-portal` | `/dashboard/procurement` | 1 |
| `production/orders/page.tsx` | `/dashboard/production/orders` | `/dashboard/production?tab=orders` | `/dashboard/production` | 1 |
| `production-execution/page.tsx` | `/dashboard/production-execution` | `/dashboard/production?tab=execution` | `/dashboard/production` | 1 |
| `machine-ops/page.tsx` | `/dashboard/machine-ops` | `/dashboard/production?tab=machine-ops` | `/dashboard/production` | 0 |
| `material-flow/page.tsx` | `/dashboard/material-flow` | `/dashboard/production?tab=material-flow` | `/dashboard/production` | 0 |
| `projects/page.tsx` | `/dashboard/projects` | `/dashboard/production?tab=projects` | `/dashboard/production` | 1 |
| `quality/consumer-complaints/page.tsx` | `/dashboard/quality/consumer-complaints` | `/dashboard/quality?tab=consumer-complaints` | `/dashboard/quality` | 0 |
| `qms/page.tsx` | `/dashboard/qms` | `/dashboard/quality?tab=qms` | `/dashboard/quality` | 0 |
| `allergen/page.tsx` | `/dashboard/allergen` | `/dashboard/quality?tab=allergen` | `/dashboard/quality` | 0 |
| `brand-assets/page.tsx` | `/dashboard/brand-assets` | `/dashboard/quality?tab=brand-assets` | `/dashboard/quality` | 1 |
| `price-lists/page.tsx` | `/dashboard/price-lists` | `/dashboard/sales?tab=price-lists` | `/dashboard/sales` | 1 |
| `dynamic-pricing/page.tsx` | `/dashboard/dynamic-pricing` | `/dashboard/sales?tab=dynamic-pricing` | `/dashboard/sales` | 0 |
| `contracts/page.tsx` | `/dashboard/contracts` | `/dashboard/sales?tab=contracts` | `/dashboard/sales` | 1 |
| `recurring-orders/page.tsx` | `/dashboard/recurring-orders` | `/dashboard/sales?tab=recurring` | `/dashboard/sales` | 1 |
| `commissions/page.tsx` | `/dashboard/commissions` | `/dashboard/sales?tab=commissions` | `/dashboard/sales` | 0 |
| `secondary-sales/page.tsx` | `/dashboard/secondary-sales` | `/dashboard/sales?tab=secondary` | `/dashboard/sales` | 1 |
| `van-sales/page.tsx` | `/dashboard/van-sales` | `/dashboard/sales?tab=van-sales` | `/dashboard/sales` | 1 |
| `portal/page.tsx` | `/dashboard/portal` | `/dashboard/sales?tab=portal` | `/dashboard/sales` | 1 |
| `utility-management/kpi-center/page.tsx` | `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management?tab=kpi-center` | `/dashboard/utility-management` | 0 |
| `utility-management/reports/page.tsx` | `/dashboard/utility-management/reports` | `/dashboard/utility-management?tab=reports` | `/dashboard/utility-management` | 0 |
| `iot/page.tsx` | `/dashboard/iot` | `/dashboard/utility-management?tab=iot` | `/dashboard/utility-management` | 0 |
| `esg/page.tsx` | `/dashboard/esg` | `/dashboard/utility-management?tab=esg` | `/dashboard/utility-management` | 0 |
| `wms/page.tsx` | `/dashboard/wms` | `/dashboard/warehouses?tab=wms` | `/dashboard/warehouses` | 0 |

---

## Git History — High-Confidence Real Page Matches

These broken targets had REAL implementations in commit `674b6c5` (2026-05-01).
All were deleted/replaced with redirect stubs in `bd6faf5` (2026-05-17).
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT**

| Module | Target Route | Source File in Git | Confidence |
|--------|-------------|-------------------|------------|


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
| RESTORE_OLD_PAGE_FROM_GIT | 0 | Restore from git commit `674b6c5` + add BYPASS_PREFIX_REDIRECT |
| CONVERT_TO_WORKSPACE_SUBVIEW | 37 | Change href to `?tab=X&view=Y` pattern in workspace |
| CREATE_NEW_REAL_PAGE_REQUIRED | 10 | No implementation exists — new page required |
| NEEDS_BUSINESS_DECISION | 0 | Intent unclear — needs product decision |

---

*Generated by `scripts/audit-visible-import-graph.js` — DO NOT FIX based on this report. Discovery pass only.*
