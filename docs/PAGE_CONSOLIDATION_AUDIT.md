# PAGE CONSOLIDATION AUDIT
Generated: 2026-05-16 | Status: Phase 1 — Audit Complete

## Summary

| Metric | Count |
|--------|-------|
| Total page.tsx files | 755 |
| Top-level dashboard modules | 103 |
| Current sidebar sections | 72 |
| Current sidebar cluster groups | 14 |
| Target sidebar workspaces | 40–50 |
| Routes needing redirect | ~650 |
| Routes staying standalone | ~50–60 |

---

## Route Inventory by Business Domain

Routes are prefixed `/dashboard/` throughout. Shown without that prefix for brevity.

---

### A. AI & Intelligence

| Route | File | Type | Page Type | Proposed Workspace | Tab/Section |
|-------|------|------|-----------|-------------------|-------------|
| ai | dashboard/ai/page.tsx | standalone | dashboard | /ai | overview |
| ai/chat | dashboard/ai/chat/page.tsx | child | tool | /ai | chat |
| ai/compliance | dashboard/ai/compliance/page.tsx | child | report | /ai | compliance |
| ai/formulations | dashboard/ai/formulations/page.tsx | child | tool | /ai | formulations |
| ai/governance | dashboard/ai/governance/page.tsx | child | settings | /ai | governance |
| ai/logs | dashboard/ai/logs/page.tsx | child | report | /ai | logs |
| ai/nl-command | dashboard/ai/nl-command/page.tsx | child | tool | /ai | nl-command |
| ai/predictions | dashboard/ai/predictions/page.tsx | child | dashboard | /ai | predictions |
| ai/recommendations | dashboard/ai/recommendations/page.tsx | child | list | /ai | recommendations |
| ai/scenarios | dashboard/ai/scenarios/page.tsx | child | tool | /ai | scenarios |

---

### B. Allergen & Nutrition

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| allergen | dashboard | /quality | allergen |
| allergen/ai | AI | /quality | allergen (ai panel) |
| allergen/allergens | list | /quality | allergen |
| allergen/change-logs | list | /quality | allergen |
| allergen/cleaning | list | /quality | allergen |
| allergen/label-readiness | list | /quality | allergen |
| allergen/material-profiles | list | /quality | allergen |
| allergen/nutrition | list | /quality | allergen |
| allergen/product-allergens | list | /quality | allergen |
| allergen/product-nutrition | list | /quality | allergen |
| allergen/reports | report | /quality | allergen |
| allergen/rollup | list | /quality | allergen |

---

### C. Analytics & Reports

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| analytics | dashboard | /analytics | overview |
| analytics/finance | report | /analytics | finance |
| analytics/inventory | report | /analytics | inventory |
| analytics/payments | report | /analytics | payments |
| analytics/procurement | report | /analytics | procurement |
| analytics/production | report | /analytics | production |
| analytics/sales | report | /analytics | sales |
| report-builder | dashboard | /analytics | report-builder |
| report-builder/ai | AI | /analytics | report-builder |
| report-builder/builder | tool | /analytics | report-builder |
| report-builder/catalog | list | /analytics | report-builder |
| report-builder/dashboards | list | /analytics | report-builder |
| report-builder/executive | dashboard | /analytics | report-builder |
| report-builder/rls | settings | /analytics | report-builder |
| report-builder/saved | list | /analytics | report-builder |
| report-builder/schedules | settings | /analytics | report-builder |
| report-builder/viewer | tool | /analytics | report-builder |
| reports | list | /analytics | reports |
| reports/finance | report | /analytics | reports |
| reports/inventory | report | /analytics | reports |
| reports/marketing | report | /analytics | reports |
| reports/payments | report | /analytics | reports |
| reports/procurement | report | /analytics | reports |
| reports/production | report | /analytics | reports |
| reports/sales | report | /analytics | reports |
| market-intelligence | dashboard | /analytics | market-intel |

---

### D. Appraisals

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| appraisals | dashboard | /hr | appraisals |
| appraisals/ai | AI | /hr | appraisals |
| appraisals/development-plans | list | /hr | appraisals |
| appraisals/hr-review | list | /hr | appraisals |
| appraisals/manager-queue | list | /hr | appraisals |
| appraisals/periods | settings | /hr | appraisals |
| appraisals/records | list | /hr | appraisals |
| appraisals/records/new | create | /hr | appraisals (drawer) |
| appraisals/reports | report | /hr | appraisals |
| appraisals/self-review | tool | /hr | appraisals |
| appraisals/templates | settings | /hr | appraisals |

---

### E. Approvals

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| approvals | list | /admin | approvals |

---

### F. Bank API & Reconciliation

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| bank-api | settings | /finance | bank-api |
| bank-reconciliation | dashboard | /finance | bank-recon |
| bank-reconciliation/accounts | list | /finance | bank-recon |
| bank-reconciliation/ai | AI | /finance | bank-recon |
| bank-reconciliation/balance | report | /finance | bank-recon |
| bank-reconciliation/import | import | /finance | bank-recon |
| bank-reconciliation/mpesa | list | /finance | bank-recon |
| bank-reconciliation/open-items | list | /finance | bank-recon |
| bank-reconciliation/reports | report | /finance | bank-recon |
| bank-reconciliation/rules | settings | /finance | bank-recon |
| bank-reconciliation/statements | list | /finance | bank-recon |
| bank-reconciliation/statements/[id] | detail | /finance | bank-recon (drawer) |

---

### G. BOM & Formula

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| bom | list | /bom | list |
| bom/[id] | detail | /bom | detail (drawer/page) |
| bom/[id]/compliance | detail | /bom | detail |
| bom/[id]/costing | detail | /bom | detail |
| bom/[id]/explode | detail | /bom | detail |
| bom/compare | tool | /bom | compare |
| bom/conversion | settings | /bom | conversion |
| bom/substitutes | list | /bom | substitutes |

---

### H. Brand Assets

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| brand-assets | list | /quality | brand-assets |
| brand-assets/[id] | detail | /quality | brand-assets (drawer) |

---

### I. Calendar & Scheduling

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| calendar | dashboard | /communication | calendar |
| calendar/ai | AI | /communication | calendar |
| calendar/availability | list | /communication | calendar |
| calendar/bookings | list | /communication | calendar |
| calendar/events | list | /communication | calendar |
| calendar/new-event | create | /communication | calendar (drawer) |
| calendar/reports | report | /communication | calendar |
| calendar/resources | settings | /communication | calendar |
| calendar/shifts | list | /communication | calendar |
| calendar/view | tool | /communication | calendar |

---

### J. Calls, Messages, Chatter, Communication

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| calls | list | /communication | calls |
| chatter | dashboard | /communication | chatter |
| chatter/ai | AI | /communication | chatter |
| chatter/feed | list | /communication | chatter |
| chatter/reports | report | /communication | chatter |
| chatter/search | tool | /communication | chatter |
| chatter/threads | list | /communication | chatter |
| email | tool | /communication | email |
| messages | list | /communication | messages |
| meetings | list | /communication | meetings |
| notification-center | dashboard | /communication | notifications |
| notification-center/ai | AI | /communication | notifications |
| notification-center/list | list | /communication | notifications |
| notification-center/preferences | settings | /communication | notifications |
| notification-center/reports | report | /communication | notifications |
| notification-center/schedules | settings | /communication | notifications |
| notification-center/templates | settings | /communication | notifications |
| whatsapp | tool | /communication | whatsapp |

---

### K. Commissions

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| commissions | dashboard | /sales | commissions |
| commissions/ai | AI | /sales | commissions |
| commissions/payouts | list | /sales | commissions |
| commissions/reports | report | /sales | commissions |
| commissions/rules | settings | /sales | commissions |
| commissions/targets | list | /sales | commissions |
| commissions/transactions | list | /sales | commissions |

---

### L. Companies / Admin

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| companies | list | /admin | companies |
| users | list | /admin | users |
| users/[id] | detail | /admin | users (drawer) |
| roles | list | /admin | roles |
| roles/[id] | detail | /admin | roles (drawer) |
| permissions | list | /admin | permissions |
| security | settings | /admin | security |
| security/monitor | dashboard | /admin | security |
| import-history | list | /admin | import-history |
| logs | list | /admin | logs |
| logs/compliance | list | /admin | logs |
| logs/retention | settings | /admin | logs |
| custom-fields | dashboard | /admin | custom-fields |
| custom-fields/[id] | detail | /admin | custom-fields (drawer) |
| custom-fields/ai | AI | /admin | custom-fields |
| custom-fields/fields | list | /admin | custom-fields |
| custom-fields/form-builder | tool | /admin | custom-fields |
| custom-fields/new-field | create | /admin | custom-fields (drawer) |
| custom-fields/reports | report | /admin | custom-fields |
| custom-fields/values | list | /admin | custom-fields |
| custom-fields/workflow-rules | settings | /admin | custom-fields |
| utilities | settings | /admin | system-config |
| utilities/currencies | settings | /admin | system-config |
| utilities/series | settings | /admin | system-config |
| utilities/uom | settings | /admin | system-config |
| approvals | list | /admin | approvals |
| mobile | settings | /admin | mobile |
| mobile/approvals | list | /admin | mobile |
| mobile/devices | list | /admin | mobile |

---

### M. Containers

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| containers | list | /logistics | containers |
| containers/outstanding | list | /logistics | containers |

---

### N. Contracts

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| contracts | dashboard | /sales | contracts |
| contracts/ai | AI | /sales | contracts |
| contracts/expiring | list | /sales | contracts |
| contracts/list | list | /sales | contracts |
| contracts/list/[id] | detail | /sales | contracts (drawer) |
| contracts/new | create | /sales | contracts (drawer) |
| contracts/performance | report | /sales | contracts |
| contracts/reports | report | /sales | contracts |

---

### O. Co-Packing

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| copacking | list | /procurement | subcontracting (co-packing tab) |

---

### P. CRM

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| crm | dashboard | /crm | overview |
| crm/activities | list | /crm | activities |
| crm/ai | AI | /crm | ai |
| crm/forecast | report | /crm | forecast |
| crm/leads | list | /crm | leads |
| crm/opportunities | list | /crm | opportunities |
| crm/overdue | list | /crm | pipeline |
| crm/pipeline | kanban | /crm | pipeline |
| crm/qualify | tool | /crm | leads |
| crm/records/[id] | detail | /crm | detail (drawer) |
| crm/stages | settings | /crm | settings |
| crm/territory | settings | /crm | settings |
| crm/win-loss | report | /crm | reports |

---

### Q. Cycle Count

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| cycle-count | dashboard | /inventory | cycle-count |
| cycle-count/entries | list | /inventory | cycle-count |
| cycle-count/plans | list | /inventory | cycle-count |
| cycle-count/reports | report | /inventory | cycle-count |
| cycle-count/tasks | list | /inventory | cycle-count |
| cycle-count/variances | list | /inventory | cycle-count |

---

### R. Developer & Webhooks & Integrations

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| developer | settings | /integrations | developer |
| developer/graphql | tool | /integrations | developer |
| developer/keys | settings | /integrations | developer |
| integrations | dashboard | /integrations | overview |
| integrations/barcode | settings | /integrations | barcode |
| integrations/logs | list | /integrations | logs |
| integrations/marketing-sync | settings | /integrations | marketing-sync |
| integrations/marketplace | list | /integrations | marketplace |
| integrations/mpesa | settings | /integrations | mpesa |
| integrations/sync | list | /integrations | logs |
| webhooks | dashboard | /integrations | webhooks |
| webhooks/dead-letter | list | /integrations | webhooks |
| webhooks/definitions | list | /integrations | webhooks |
| webhooks/deliveries | list | /integrations | webhooks |
| webhooks/inbound | list | /integrations | webhooks |
| webhooks/reports | report | /integrations | webhooks |
| webhooks/subscriptions | list | /integrations | webhooks |
| portal | dashboard | /sales | portal |
| portal/accounts | list | /sales | portal |
| portal/accounts/[id] | detail | /sales | portal (drawer) |
| portal/accounts/[id]/view | detail | /sales | portal (drawer) |
| portal/activity | list | /sales | portal |
| portal/ai | AI | /sales | portal |
| portal/claims | list | /sales | portal |
| portal/drafts | list | /sales | portal |
| portal/order-tracking | list | /sales | portal |
| portal/reports | report | /sales | portal |
| portal/sell-through | tool | /sales | portal |
| portal/users | list | /sales | portal |
| supplier-portal | dashboard | /procurement | supplier-portal |
| supplier-portal/accounts | list | /procurement | supplier-portal |
| supplier-portal/accounts/[id] | detail | /procurement | supplier-portal (drawer) |
| supplier-portal/accounts/[id]/purchase-orders | list | /procurement | supplier-portal |
| supplier-portal/activity | list | /procurement | supplier-portal |
| supplier-portal/ai | AI | /procurement | supplier-portal |
| supplier-portal/documents | list | /procurement | supplier-portal |
| supplier-portal/eta | list | /procurement | supplier-portal |
| supplier-portal/invoices | list | /procurement | supplier-portal |
| supplier-portal/payment | list | /procurement | supplier-portal |
| supplier-portal/reports | report | /procurement | supplier-portal |
| supplier-portal/users | list | /procurement | supplier-portal |

---

### S. Dimensions

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| dimensions | dashboard | /finance | dimensions |
| dimensions/ai | AI | /finance | dimensions |
| dimensions/allocation-run | tool | /finance | dimensions |
| dimensions/allocations | list | /finance | dimensions |
| dimensions/completeness | report | /finance | dimensions |
| dimensions/cost-centers | list | /finance | dimensions |
| dimensions/defaults | settings | /finance | dimensions |
| dimensions/reclassify | tool | /finance | dimensions |
| dimensions/types | settings | /finance | dimensions |
| dimensions/validation | settings | /finance | dimensions |
| dimensions/values | list | /finance | dimensions |

---

### T. Documents & Knowledge Base

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| documents | list | /documents | repository |
| documents/[id] | detail | /documents | repository (drawer) |
| documents/compliance | list | /documents | compliance |
| documents/expiring | list | /documents | expiring |
| documents/new | create | /documents | repository (drawer) |
| knowledge-base | list | /documents | knowledge-base |
| knowledge-base/[id] | detail | /documents | knowledge-base (drawer) |
| knowledge-base/articles | list | /documents | knowledge-base |
| knowledge-base/articles/new | create | /documents | knowledge-base (drawer) |
| esign | list | /documents | esign |
| contracts | dashboard | /documents | contracts (also /sales) |

---

### U. Dunning

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| dunning | dashboard | /finance | dunning |
| dunning/aging | report | /finance | dunning |
| dunning/ai | AI | /finance | dunning |
| dunning/cases | list | /finance | dunning |
| dunning/cases/[id] | detail | /finance | dunning (drawer) |
| dunning/credit-holds | list | /finance | dunning |
| dunning/policies | settings | /finance | dunning |
| dunning/reports | report | /finance | dunning |
| dunning/templates | settings | /finance | dunning |
| dunning/workqueue | list | /finance | dunning |

---

### V. Dynamic Pricing

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| dynamic-pricing | tool | /sales | pricing |

---

### W. ESG

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| esg | dashboard | /utilities | esg |
| esg/activities | list | /utilities | esg |
| esg/carbon | report | /utilities | esg |
| esg/factors | settings | /utilities | esg |
| esg/intelligence | AI | /utilities | esg |
| esg/reports | report | /utilities | esg |
| esg/targets | list | /utilities | esg |

---

### X. ESS (Employee Self-Service)

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| ess | dashboard | /hr | ess |
| ess/admin | settings | /hr | ess |
| ess/ai | AI | /hr | ess |
| ess/attendance | list | /hr | ess |
| ess/documents | list | /hr | ess |
| ess/leave | list | /hr | ess |
| ess/notifications | list | /hr | ess |
| ess/profile | settings | /hr | ess |
| ess/requests | list | /hr | ess |

---

### Y. Expenses

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| expenses | dashboard | /hr | expenses |
| expenses/advances | list | /hr | expenses |
| expenses/ai | AI | /hr | expenses |
| expenses/approval | list | /hr | expenses |
| expenses/categories | settings | /hr | expenses |
| expenses/claims | list | /hr | expenses |
| expenses/claims/[id] | detail | /hr | expenses (drawer) |
| expenses/claims/new | create | /hr | expenses (drawer) |
| expenses/policies | settings | /hr | expenses |
| expenses/receipt-ocr | tool | /hr | expenses |
| expenses/reimbursement | list | /hr | expenses |
| expenses/reports | report | /hr | expenses |

---

### Z. Finance & Accounting

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| finance | dashboard | /finance | overview |
| finance/accounting | dashboard | /finance | accounting |
| finance/accounting/balance-sheet | report | /finance | accounting |
| finance/accounting/chart-of-accounts | list | /finance | accounting |
| finance/accounting/controls | settings | /finance | accounting |
| finance/accounting/customers-ledger | list | /finance | accounting |
| finance/accounting/general-ledger | list | /finance | accounting |
| finance/accounting/journal | list | /finance | accounting |
| finance/accounting/payments | list | /finance | accounting |
| finance/accounting/period-closing | tool | /finance | accounting |
| finance/accounting/profit-loss | report | /finance | accounting |
| finance/accounting/purchase-invoices | list | /finance | accounting |
| finance/accounting/sales-invoices | list | /finance | accounting |
| finance/accounting/suppliers-ledger | list | /finance | accounting |
| finance/accounting/trial-balance | report | /finance | accounting |
| finance/budget | list | /finance | budgets |
| finance/cashbook | list | /finance | cashbook |
| finance/costing | list | /finance | costing |
| finance/etims | tool | /finance | tax |
| finance/exchange-rates | settings | /finance | settings |
| finance/mpesa | list | /finance | mpesa |
| finance/receivables | list | /finance | receivables |
| finance/vat-returns | report | /finance | tax |
| fixed-assets | dashboard | /finance | fixed-assets |
| fixed-assets/ai | AI | /finance | fixed-assets |
| fixed-assets/assets | list | /finance | fixed-assets |
| fixed-assets/assets/[id] | detail | /finance | fixed-assets (drawer) |
| fixed-assets/assets/[id]/add-component | create | /finance | fixed-assets (drawer) |
| fixed-assets/assets/new | create | /finance | fixed-assets (drawer) |
| fixed-assets/categories | settings | /finance | fixed-assets |
| fixed-assets/depreciation | list | /finance | fixed-assets |
| fixed-assets/disposal | list | /finance | fixed-assets |
| fixed-assets/import | import | /finance | fixed-assets |
| fixed-assets/posting | tool | /finance | fixed-assets |
| fixed-assets/transfer | tool | /finance | fixed-assets |
| invoice-match | dashboard | /finance | invoice-match |
| invoice-match/[id] | detail | /finance | invoice-match (drawer) |
| invoice-match/ai | AI | /finance | invoice-match |
| invoice-match/blocked | list | /finance | invoice-match |
| invoice-match/duplicates | list | /finance | invoice-match |
| invoice-match/matches | list | /finance | invoice-match |
| invoice-match/reports | report | /finance | invoice-match |
| invoice-match/review-queue | list | /finance | invoice-match |
| invoice-match/tolerance-rules | settings | /finance | invoice-match |
| tax | dashboard | /finance | tax |
| tax/regulatory | list | /finance | tax |
| tax/reports | report | /finance | tax |
| tax/rules | settings | /finance | tax |
| tax/transactions | list | /finance | tax |

---

### AA. Fixed Assets → merged into Finance above

---

### BB. Fleet

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| fleet | dashboard | /logistics | fleet |
| fleet/drivers | list | /logistics | fleet |
| fleet/fuel | list | /logistics | fleet |
| fleet/incidents | list | /logistics | fleet |
| fleet/maintenance | list | /logistics | fleet |
| fleet/reports | report | /logistics | fleet |
| fleet/trips | list | /logistics | fleet |
| fleet/vehicles | list | /logistics | fleet |

---

### CC. GS1 / Labels

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| gs1 | dashboard | /compliance | gs1 |
| gs1/ai | AI | /compliance | gs1 |
| gs1/barcodes | tool | /compliance | gs1 |
| gs1/config | settings | /compliance | gs1 |
| gs1/labels | list | /compliance | gs1 |
| gs1/print-queue | list | /compliance | gs1 |
| gs1/reports | report | /compliance | gs1 |
| gs1/scan | tool | /compliance | gs1 |
| gs1/sscc | list | /compliance | gs1 |

---

### DD. Helpdesk

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| helpdesk | dashboard | /helpdesk | overview |
| helpdesk/escalated | list | /helpdesk | escalated |
| helpdesk/open | list | /helpdesk | open |
| helpdesk/sla | list | /helpdesk | sla |
| helpdesk/tickets | list | /helpdesk | all-tickets |

---

### EE. HR & Payroll

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| hr | dashboard | /hr | overview |
| hr/attendance | list | /hr | attendance |
| hr/employees | list | /hr | employees |
| hr/leave | list | /hr | leave |
| hr/payroll | list | /hr | payroll |
| hr/shifts | settings | /hr | shifts |
| payroll | dashboard | /payroll-ke | overview |
| payroll/profiles | settings | /payroll-ke | profiles |
| payroll/reports | report | /payroll-ke | reports |
| payroll/runs/[id] | detail | /payroll-ke | runs (drawer) |
| timesheets | dashboard | /hr | timesheets |
| timesheets/ai | AI | /hr | timesheets |
| timesheets/approval-queue | list | /hr | timesheets |
| timesheets/my-timesheets | list | /hr | timesheets |
| timesheets/reports | report | /hr | timesheets |
| timesheets/time-entry | tool | /hr | timesheets (drawer) |
| timesheets/weekly-view | tool | /hr | timesheets |

---

### FF. Inventory

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| inventory | dashboard | /inventory | stock |
| inventory/serials | list | /inventory | tracking |
| inventory/valuation | list | /inventory | valuation |
| movements | list | /inventory | movements |
| shelf-life | dashboard | /inventory | shelf-life |
| shelf-life/bulk-hold-monitor | list | /inventory | shelf-life |
| shelf-life/compliance | report | /inventory | shelf-life |
| shelf-life/customer-rules | settings | /inventory | shelf-life |
| shelf-life/disposition | tool | /inventory | shelf-life |
| shelf-life/expired | list | /inventory | shelf-life |
| shelf-life/fefo-config | settings | /inventory | shelf-life |
| shelf-life/lot-aging | list | /inventory | shelf-life |
| shelf-life/near-expiry | list | /inventory | shelf-life |
| shelf-life/production-validation | tool | /inventory | shelf-life |
| shelf-life/retest-queue | list | /inventory | shelf-life |
| shelf-life/shipment-validation | tool | /inventory | shelf-life |
| traceability | dashboard | /inventory | traceability |
| traceability/backward | tool | /inventory | traceability |
| traceability/forward | tool | /inventory | traceability |
| traceability/genealogy | tool | /inventory | traceability |
| traceability/mock-recall | tool | /inventory | traceability |
| traceability/recalls | list | /inventory | traceability |
| traceability/recalls/[id] | detail | /inventory | traceability (drawer) |
| traceability/regulatory | report | /inventory | traceability |
| traceability/search | tool | /inventory | traceability |
| traceability/templates | settings | /inventory | traceability |
| cycle-count | dashboard | /inventory | cycle-count |
| cycle-count/entries | list | /inventory | cycle-count |
| cycle-count/plans | list | /inventory | cycle-count |
| cycle-count/reports | report | /inventory | cycle-count |
| cycle-count/tasks | list | /inventory | cycle-count |
| cycle-count/variances | list | /inventory | cycle-count |

---

### GG. IoT

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| iot | dashboard | /utilities | iot |

---

### HH. Kanban

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| kanban | dashboard | /planning | kanban |
| kanban/ai | AI | /planning | kanban |
| kanban/boards | list | /planning | kanban |
| kanban/cards | list | /planning | kanban |
| kanban/reports | report | /planning | kanban |
| kanban/view | tool | /planning | kanban |

---

### II. Landed Cost

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| landed-cost | dashboard | /procurement | landed-cost |
| landed-cost/[id] | detail | /procurement | landed-cost (drawer) |
| landed-cost/ai | AI | /procurement | landed-cost |
| landed-cost/documents | list | /procurement | landed-cost |
| landed-cost/new | create | /procurement | landed-cost (drawer) |
| landed-cost/reports | report | /procurement | landed-cost |

---

### JJ. Logistics

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| logistics | dashboard | /logistics | overview |
| logistics/arrivals | list | /logistics | arrivals |
| logistics/containers | list | /logistics | containers |
| logistics/documents | list | /logistics | documents |
| logistics/shipments | list | /logistics | shipments |
| containers | list | /logistics | containers |
| containers/outstanding | list | /logistics | containers |

---

### KK. Loyalty / NPS

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| loyalty | dashboard | /crm | loyalty |
| nps | dashboard | /crm | nps |

---

### LL. Machine Ops

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| machine-ops | dashboard | /production | machine-ops |
| machine-ops/assignment | list | /production | machine-ops |
| machine-ops/certs | list | /production | machine-ops |
| machine-ops/costing | report | /production | machine-ops |
| machine-ops/downtime | list | /production | machine-ops |
| machine-ops/machines | list | /production | machine-ops |
| machine-ops/operators | list | /production | machine-ops |
| machine-ops/performance | report | /production | machine-ops |
| machine-ops/runtime | list | /production | machine-ops |
| machine-ops/teams | list | /production | machine-ops |

---

### MM. Maintenance

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| maintenance | dashboard | /maintenance | overview |
| maintenance/assets | list | /maintenance | assets |
| maintenance/breakdowns | list | /maintenance | breakdowns |
| maintenance/plans | list | /maintenance | plans |
| maintenance/predictive | list | /maintenance | predictive |
| maintenance/reports | report | /maintenance | reports |
| maintenance/spares | list | /maintenance | spares |

---

### NN. Marketing

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| marketing | dashboard | /marketing | overview |
| marketing/ads | list | /marketing | ads |
| marketing/ads/[id] | detail | /marketing | ads (drawer) |
| marketing/ads/new | create | /marketing | ads (drawer) |
| marketing/ai-optimizer | AI | /marketing | ai-optimizer |
| marketing/analytics | dashboard | /marketing | analytics |
| marketing/brand-spend | list | /marketing | brand-spend |
| marketing/brand-spend/[id] | detail | /marketing | brand-spend (drawer) |
| marketing/brand-spend/new | create | /marketing | brand-spend (drawer) |
| marketing/campaigns | list | /marketing | campaigns |
| marketing/campaigns/[id] | detail | /marketing | campaigns (drawer) |
| marketing/campaigns/new | create | /marketing | campaigns (drawer) |
| marketing/crm | list | /marketing | crm |
| marketing/crm/[id] | detail | /marketing | crm (drawer) |
| marketing/crm/followup | list | /marketing | crm |
| marketing/ecommerce | dashboard | /marketing | ecommerce |
| marketing/ecommerce/analytics | report | /marketing | ecommerce |
| marketing/ecommerce/performance | list | /marketing | ecommerce |
| marketing/ecommerce/performance/[id] | detail | /marketing | ecommerce (drawer) |
| marketing/ecommerce/performance/new | create | /marketing | ecommerce (drawer) |
| marketing/ecommerce/products | list | /marketing | ecommerce |
| marketing/ecommerce/products/[id] | detail | /marketing | ecommerce (drawer) |
| marketing/ecommerce/products/new | create | /marketing | ecommerce (drawer) |
| marketing/ecommerce/returns | list | /marketing | ecommerce |
| marketing/ecommerce/stores | list | /marketing | ecommerce |
| marketing/ecommerce/stores/[id] | detail | /marketing | ecommerce (drawer) |
| marketing/ecommerce/stores/new | create | /marketing | ecommerce (drawer) |
| marketing/influencers | list | /marketing | influencers |
| marketing/influencers/[id] | detail | /marketing | influencers (drawer) |
| marketing/influencers/new | create | /marketing | influencers (drawer) |
| marketing/promotions | list | /marketing | promotions |
| marketing/promotions/[id] | detail | /marketing | promotions (drawer) |
| marketing/promotions/new | create | /marketing | promotions (drawer) |
| marketing/segments | list | /marketing | segments |
| marketing/segments/[id] | detail | /marketing | segments (drawer) |
| marketing/segments/new | create | /marketing | segments (drawer) |
| marketing/social-media | list | /marketing | social-media |
| marketing/social-media/[id] | detail | /marketing | social-media (drawer) |
| marketing/social-media/new | create | /marketing | social-media (drawer) |
| marketing/surveys | list | /marketing | surveys |
| marketing/surveys/[id] | detail | /marketing | surveys (drawer) |
| marketing/surveys/new | create | /marketing | surveys (drawer) |
| marketing/trade-spend | list | /marketing | trade-spend |
| marketing/trade-spend/[id] | detail | /marketing | trade-spend (drawer) |
| marketing/trade-spend/new | create | /marketing | trade-spend (drawer) |
| marketing/visits | list | /marketing | visits |
| marketing/visits/[id] | detail | /marketing | visits (drawer) |
| marketing/visits/new | create | /marketing | visits (drawer) |
| market-intelligence | dashboard | /marketing | market-intel |
| tpm | dashboard | /marketing | tpm |
| tpm/ai | AI | /marketing | tpm |
| tpm/budget | list | /marketing | tpm |
| tpm/calendar | list | /marketing | tpm |
| tpm/claims | list | /marketing | tpm |
| tpm/plans | list | /marketing | tpm |
| tpm/plans/new | create | /marketing | tpm (drawer) |
| tpm/promotions | list | /marketing | tpm |
| tpm/promotions/[id] | detail | /marketing | tpm (drawer) |
| tpm/promotions/new | create | /marketing | tpm (drawer) |
| tpm/roi | report | /marketing | tpm |
| tpm/settlement | list | /marketing | tpm |
| promotions | dashboard | /marketing | promotions-schemes |
| promotions/ai | AI | /marketing | promotions-schemes |
| promotions/analytics | report | /marketing | promotions-schemes |
| promotions/overrides | list | /marketing | promotions-schemes |
| promotions/schemes | list | /marketing | promotions-schemes |
| promotions/schemes/[id] | detail | /marketing | promotions-schemes (drawer) |
| promotions/schemes/new | create | /marketing | promotions-schemes (drawer) |
| promotions/simulate | tool | /marketing | promotions-schemes |

---

### OO. Material Flow

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| material-flow | dashboard | /production | material-flow |
| material-flow/bulk-transfer | tool | /production | material-flow |
| material-flow/fg-receipt | tool | /production | material-flow |
| material-flow/history | list | /production | material-flow |
| material-flow/issue | tool | /production | material-flow |
| material-flow/packaging | tool | /production | material-flow |
| material-flow/reconciliation | tool | /production | material-flow |
| material-flow/reservations | list | /production | material-flow |
| material-flow/returns | list | /production | material-flow |
| material-flow/stages | settings | /production | material-flow |
| material-flow/tanks | list | /production | material-flow |
| material-flow/wip-transfer | tool | /production | material-flow |

---

### PP. Materials

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| materials | list | /materials | list |

---

### QQ. MPS & MRP & Planning

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| mrp | dashboard | /planning | mrp |
| mrp/forecast | list | /planning | mrp |
| mrp/forecast/accuracy | report | /planning | mrp |
| mrp/forecast/correlation | report | /planning | mrp |
| mrp/run | tool | /planning | mrp |
| mrp/suggestions | list | /planning | mrp |
| mrp/workbench | tool | /planning | mrp |
| mps | dashboard | /planning | mps |
| mps/campaigns | list | /planning | mps |
| mps/capacity | list | /planning | mps |
| mps/planning-board | tool | /planning | mps |
| mps/whatif | tool | /planning | mps |
| planning | dashboard | /planning | advanced |
| planning/bottlenecks | report | /planning | advanced |
| planning/capacity | list | /planning | advanced |
| planning/changeover | settings | /planning | advanced |
| planning/schedule | tool | /planning | advanced |
| planning/simulation | tool | /planning | advanced |
| kanban | dashboard | /planning | kanban |
| procurement-suggestion | dashboard | /procurement | suggestions |
| procurement-suggestion/ai | AI | /procurement | suggestions |
| procurement-suggestion/groups | list | /procurement | suggestions |
| procurement-suggestion/reports | report | /procurement | suggestions |
| procurement-suggestion/suggestions | list | /procurement | suggestions |
| procurement-suggestion/supplier-compare | tool | /procurement | suggestions |
| procurement-suggestion/supplier-prices | list | /procurement | suggestions |

---

### RR. NPD

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| npd | list | /npd | projects |
| npd/[id] | detail | /npd | detail (drawer/page) |

---

### SS. Procurement

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| procurement | dashboard | /procurement | overview |
| procurement/[id] | detail | /procurement | requests (drawer) |
| procurement/blanket-agreements | list | /procurement | blanket |
| procurement/deliveries | list | /procurement | deliveries |
| procurement/orders | list | /procurement | orders |
| procurement/orders/[id] | detail | /procurement | orders (drawer) |
| procurement/reorder-policies | settings | /procurement | reorder |
| procurement/rfq | list | /procurement | rfq |
| procurement/suppliers | list | /procurement | supplier-scorecard |
| subcontracting | dashboard | /procurement | subcontracting |
| subcontracting/ai | AI | /procurement | subcontracting |
| subcontracting/locations | list | /procurement | subcontracting |
| subcontracting/orders | list | /procurement | subcontracting |
| subcontracting/performance | report | /procurement | subcontracting |
| subcontracting/stock | list | /procurement | subcontracting |
| subcontracting/yield | report | /procurement | subcontracting |
| copacking | list | /procurement | subcontracting |

---

### TT. Production & Manufacturing

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| production | dashboard | /production | overview |
| production/advanced | list | /production | advanced |
| production/ai | AI | /production | ai |
| production/batch-lots | list | /production | batch-lots |
| production/costing | list | /production | costing |
| production/downtime | list | /production | downtime |
| production/labor | list | /production | labor |
| production/oee | list | /production | oee |
| production/orders | list | /production | orders |
| production/orders/[id] | detail | /production | orders (drawer) |
| production/plans/[id] | detail | /production | overview (drawer) |
| production/quality-control | list | /production | quality-control |
| production/reports | report | /production | reports |
| production/routing | settings | /production | routing |
| production/scheduling | tool | /production | scheduling |
| production/shifts | settings | /production | shifts |
| production/time-tracking | list | /production | time-tracking |
| production/variance | report | /production | variance |
| production/waste-yield | list | /production | waste-yield |
| production/wip | list | /production | wip |
| production/work-centers | list | /production | work-centers |
| production/work-orders | list | /production | work-orders |
| production-execution | dashboard | /production | execution |
| production-execution/[id] | detail | /production | execution (drawer) |
| production-execution/[id]/genealogy | detail | /production | execution |
| production-execution/work-orders | list | /production | execution |
| shop-floor | dashboard | /shop-floor | overview |
| shop-floor/downtime | list | /shop-floor | downtime |
| shop-floor/handover | tool | /shop-floor | handover |
| shop-floor/queue | list | /shop-floor | queue |
| shop-floor/supervisor | dashboard | /shop-floor | supervisor |
| shop-floor/terminal | tool | /shop-floor | terminal |

---

### UU. Products

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| products | list | /products | list |

---

### VV. Projects

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| projects | list | /production | projects |
| projects/[id] | detail | /production | projects (drawer) |
| projects/dashboard | dashboard | /production | projects |

---

### WW. Quality & Compliance

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| quality | list | /quality | inspections |
| quality/[id] | detail | /quality | inspections (drawer) |
| quality/certificates | list | /quality | certificates |
| quality/consumer-complaints | list | /quality | complaints |
| quality/parameters | settings | /quality | parameters |
| quality/reports | report | /quality | reports |
| qms | dashboard | /quality | qms |
| qms/ai | AI | /quality | qms |
| qms/allergen | list | /quality | allergen |
| qms/aql | settings | /quality | qms |
| qms/audit-checklists | list | /quality | qms |
| qms/calibration | list | /quality | qms |
| qms/ccp | list | /quality | qms |
| qms/coa | list | /quality | qms |
| qms/corrective-actions | list | /quality | qms |
| qms/deviations | list | /quality | qms |
| qms/haccp | list | /quality | qms |
| qms/inspections | list | /quality | inspections |
| qms/quarantine | list | /quality | qms |
| qms/reports | report | /quality | reports |
| qms/supplier-safety | list | /quality | qms |
| qms/templates | settings | /quality | qms |

---

### XX. Recipes

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| recipes | list | /recipes | list |
| recipes/[id] | detail | /recipes | detail (drawer) |

---

### YY. Recruitment

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| recruitment | dashboard | /hr | recruitment |
| recruitment/ai | AI | /hr | recruitment |
| recruitment/candidates | list | /hr | recruitment |
| recruitment/candidates/[id] | detail | /hr | recruitment (drawer) |
| recruitment/candidates/new | create | /hr | recruitment (drawer) |
| recruitment/interviews | list | /hr | recruitment |
| recruitment/offers | list | /hr | recruitment |
| recruitment/pipeline | kanban | /hr | recruitment |
| recruitment/reports | report | /hr | recruitment |
| recruitment/requisitions | list | /hr | recruitment |
| recruitment/requisitions/[id] | detail | /hr | recruitment (drawer) |
| recruitment/requisitions/new | create | /hr | recruitment (drawer) |
| recruitment/stages | settings | /hr | recruitment |

---

### ZZ. Recurring Orders

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| recurring-orders | dashboard | /sales | recurring |
| recurring-orders/ai | AI | /sales | recurring |
| recurring-orders/billing | list | /sales | recurring |
| recurring-orders/generation-log | list | /sales | recurring |
| recurring-orders/pause-skip | tool | /sales | recurring |
| recurring-orders/reports | report | /sales | recurring |
| recurring-orders/schedule | list | /sales | recurring |
| recurring-orders/templates | list | /sales | recurring |
| recurring-orders/templates/[id] | detail | /sales | recurring (drawer) |
| recurring-orders/templates/new | create | /sales | recurring (drawer) |
| recurring-orders/upcoming-demand | list | /sales | recurring |

---

### AAA. Sales

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| sales | dashboard | /sales | overview |
| sales/collections | list | /sales | collections |
| sales/customers | list | /sales | customers |
| sales/customer-statement | list | /sales | customers |
| sales/delivery | list | /sales | delivery |
| sales/distributors | list | /sales | distributors |
| sales/field-sales | list | /sales | field-sales |
| sales/invoices | list | /sales | invoices |
| sales/invoices/[id] | detail | /sales | invoices (drawer) |
| sales/margin | report | /sales | reports |
| sales/orders | list | /sales | orders |
| sales/orders/[id] | detail | /sales | orders (drawer) |
| sales/pod | list | /sales | delivery |
| sales/pricing | list | /sales | pricing |
| sales/quotes | list | /sales | quotes |
| sales/reports | report | /sales | reports |
| sales/returns | list | /sales | returns |
| sales/shipments | list | /sales | shipments |
| sales/shipments/[id] | detail | /sales | shipments (drawer) |
| price-lists | dashboard | /sales | price-lists |
| price-lists/[id] | detail | /sales | price-lists (drawer) |
| price-lists/ai | AI | /sales | price-lists |
| price-lists/approval-queue | list | /sales | price-lists |
| price-lists/compare | tool | /sales | price-lists |
| price-lists/discount-rules | settings | /sales | price-lists |
| price-lists/import | import | /sales | price-lists |
| price-lists/margin | report | /sales | price-lists |
| price-lists/reports | report | /sales | price-lists |
| dynamic-pricing | tool | /sales | dynamic-pricing |
| secondary-sales | dashboard | /sales | secondary |
| secondary-sales/analysis | report | /sales | secondary |
| secondary-sales/inventory | list | /sales | secondary |
| secondary-sales/upload | import | /sales | secondary |
| van-sales | dashboard | /sales | van-sales |
| van-sales/ai | AI | /sales | van-sales |
| van-sales/field-rep | list | /sales | van-sales |
| van-sales/fraud | list | /sales | van-sales |
| van-sales/mpesa | list | /sales | van-sales |
| van-sales/performance | report | /sales | van-sales |
| van-sales/pos | tool | /sales | van-sales |
| van-sales/reconciliation | tool | /sales | van-sales |
| van-sales/reports | report | /sales | van-sales |
| van-sales/returns | list | /sales | van-sales |
| van-sales/route | list | /sales | van-sales |
| van-sales/route-optimizer | tool | /sales | van-sales |
| van-sales/stock | list | /sales | van-sales |
| van-sales/vans | list | /sales | van-sales |
| van-sales/vans/[id] | detail | /sales | van-sales (drawer) |
| van-sales/vans/new | create | /sales | van-sales (drawer) |
| van-sales/visits | list | /sales | van-sales |

---

### BBB. Surveys

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| surveys | list | /crm | surveys |
| surveys/[id] | detail | /crm | surveys (drawer) |
| surveys/[id]/respond | tool | /crm | surveys |
| surveys/[id]/results | report | /crm | surveys |
| surveys/new | create | /crm | surveys (drawer) |

---

### CCC. Suppliers

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| suppliers | list | /suppliers | list |

---

### DDD. Training

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| training | dashboard | /hr | training |
| training/ai | AI | /hr | training |
| training/assignments | list | /hr | training |
| training/certifications | list | /hr | training |
| training/feedback | list | /hr | training |
| training/programs | list | /hr | training |
| training/reports | report | /hr | training |
| training/sessions | list | /hr | training |
| training/skill-matrix | tool | /hr | training |

---

### EEE. Utility Management

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| utility-management | dashboard | /utilities | overview |
| utility-management/alarm-center | list | /utilities | alarms |
| utility-management/alarm-rules | settings | /utilities | alarms |
| utility-management/assets | list | /utilities | assets |
| utility-management/billing | list | /utilities | billing |
| utility-management/categories | settings | /utilities | assets |
| utility-management/chemical-treatment | list | /utilities | chemical |
| utility-management/compressor | list | /utilities | compressor |
| utility-management/devices | list | /utilities | devices |
| utility-management/electricity | list | /utilities | electricity |
| utility-management/integration | settings | /utilities | integration |
| utility-management/kpi-center | dashboard | /utilities | kpi |
| utility-management/kpi-center/boiler | report | /utilities | kpi |
| utility-management/kpi-center/chemicals | report | /utilities | kpi |
| utility-management/kpi-center/compressor | report | /utilities | kpi |
| utility-management/kpi-center/electricity | report | /utilities | kpi |
| utility-management/kpi-center/machine-utility | report | /utilities | kpi |
| utility-management/kpi-center/soft-water | report | /utilities | kpi |
| utility-management/kpi-center/solar | report | /utilities | kpi |
| utility-management/kpi-center/utility-cost | report | /utilities | kpi |
| utility-management/kpi-center/wastewater | report | /utilities | kpi |
| utility-management/kpi-center/water | report | /utilities | kpi |
| utility-management/machine-utility | list | /utilities | machine-utility |
| utility-management/readings | list | /utilities | readings |
| utility-management/reports | report | /utilities | reports |
| utility-management/reports/anomalies | report | /utilities | reports |
| utility-management/reports/cost-allocation | report | /utilities | reports |
| utility-management/reports/daily-consumption | report | /utilities | reports |
| utility-management/reports/equipment-efficiency | report | /utilities | reports |
| utility-management/reports/load-analysis | report | /utilities | reports |
| utility-management/reports/sustainability | report | /utilities | reports |
| utility-management/reports/treatment | report | /utilities | reports |
| utility-management/soft-water | list | /utilities | soft-water |
| utility-management/solar | list | /utilities | solar |
| utility-management/steam | list | /utilities | steam |
| utility-management/transactions | list | /utilities | transactions |
| utility-management/wastewater | list | /utilities | wastewater |
| utility-management/water | list | /utilities | water |
| iot | dashboard | /utilities | iot |
| esg | dashboard | /utilities | esg |
| esg/activities | list | /utilities | esg |
| esg/carbon | report | /utilities | esg |
| esg/factors | settings | /utilities | esg |
| esg/intelligence | AI | /utilities | esg |
| esg/reports | report | /utilities | esg |
| esg/targets | list | /utilities | esg |

---

### FFF. Warehouses & WMS

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| warehouses | list | /warehouses | list |
| wms | dashboard | /warehouses | wms |
| wms/counts | list | /warehouses | wms |
| wms/counts/[id] | detail | /warehouses | wms (drawer) |
| wms/picking | list | /warehouses | wms |
| wms/replenishment | list | /warehouses | wms |
| wms/reports | report | /warehouses | wms |
| putaway | list | /warehouses | wms |
| putaway/execute/[id] | tool | /warehouses | wms |
| putaway/rules | settings | /warehouses | wms |

---

### GGG. POS

| Route | Type | Proposed Workspace | Tab |
|-------|------|--------------------|-----|
| pos | tool | /pos | terminal |
| pos/sales | list | /pos | sales |
| pos/sessions | list | /pos | sessions |

---

## Duplicate / Near-Duplicate Routes

| Duplication | Routes | Resolution |
|------------|--------|------------|
| Marketing CRM vs CRM Pipeline | marketing/crm + crm/* | Keep /crm as main; /marketing/crm links to /crm |
| Marketing Promotions vs Promotions | marketing/promotions + promotions/* | Merge into /marketing?tab=promotions-schemes |
| Marketing Surveys vs Surveys | marketing/surveys + surveys/* | surveys kept in /crm; cross-link from /marketing |
| Quality Allergen vs QMS Allergen | qms/allergen + allergen/* | allergen/* is canonical; qms/allergen links there |
| Reports module vs module-specific reports | reports/* vs finance/accounting/* | reports/* kept as cross-module roll-up |
| Containers in logistics vs containers/* | logistics/containers + containers/* | merge into /logistics?tab=containers |

---

## Orphan Pages (not in sidebar nav-config)

Based on file scan vs nav-config items. Unlinked routes:
- `dashboard/page.tsx` (the root dashboard — IS linked as Dashboard standalone)
- `dashboard/approvals/page.tsx` — linked but buried in Admin section
- `dashboard/movements/page.tsx` — linked in Warehouse section

No fully orphaned pages detected. All directories appear linked in nav-config.

---

## Placeholder / Stub Pages

To be verified during Phase 2 implementation. Suspected stubs based on single-item modules:
- `bank-api` (one page only)
- `loyalty` (one page only)
- `nps` (one page only)
- `dynamic-pricing` (one page only)
- `email` (one page only)
- `whatsapp` (one page only)
- `calls` (one page only)
- `meetings` (one page only)
- `iot` (one page only)
- `messages` (one page only)

These are prime candidates for becoming tabs rather than routes.

---

## Pages That Should Become Drawers

All `/new`, `/edit`, `/create` routes and detail `/[id]` routes:
- ~95 create/new routes → drawers
- ~60 edit routes → drawers
- ~75 detail/[id] routes → drawers

---

## Pages That Should Become Tabs/Panels

- All import-only routes → Import tab/panel
- All report-only routes → Reports tab
- All settings-only routes → Settings tab
- All AI-only routes → AI panel

---

## Permission Requirements

| Workspace | Permission |
|-----------|-----------|
| /products | products.view |
| /materials | products.view |
| /suppliers | procurement.view |
| /warehouses | inventory.view + wms.view |
| /inventory | inventory.view |
| /procurement | procurement.view |
| /sales | sales.view |
| /crm | sales.view |
| /marketing | marketing.view |
| /finance | finance.view |
| /production | production.view |
| /planning | planning.view |
| /npd | npd.view |
| /bom | bom.view |
| /recipes | recipe.view |
| /quality | quality.view |
| /compliance | gs1.view |
| /maintenance | maintenance.view |
| /utilities | utility_management.view |
| /logistics | logistics.view |
| /hr | hr.view |
| /payroll-ke | payroll_ke.view |
| /documents | documents.view |
| /communication | hr.view |
| /helpdesk | quality.view |
| /ai | ai.view |
| /analytics | analytics.view |
| /pos | sales.view |
| /shop-floor | production.view |
| /integrations | integrations.view |
| /admin | users.view |
