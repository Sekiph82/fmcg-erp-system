# Page Count Report

Generated: 2026-05-22

## Summary

| Classification            | Code | Count |
|---------------------------|------|-------|
| WORKSPACE_PAGE            | A    | 31   |
| REDIRECT_ONLY             | B    | 191   |
| LIGHTWEIGHT_WRAPPER       | C    | 213   |
| FULL_DUPLICATE_UI         | D    | 301   |
| STANDALONE_OPERATIONAL    | E    | 19   |
| UNKNOWN                   | F    | 0   |
| **Total**                 |      | **755** |

## Definitions

- **A WORKSPACE_PAGE** — renders `<ModuleWorkspace tabs={...}>` — these are the destination pages.
- **B REDIRECT_ONLY** — page body only calls `redirect()` / `permanentRedirect()` — no UI.
- **C LIGHTWEIGHT_WRAPPER** — dynamically imported as a tab by a workspace page. Stays as-is.
- **D FULL_DUPLICATE_UI** — has own API calls/state/forms and is NOT used as a workspace tab.
  These are the pages to migrate or convert to redirect-only.
- **E STANDALONE_OPERATIONAL** — full-screen tool that must remain standalone (POS, shop-floor).
- **F UNKNOWN** — could not classify from content heuristics.

## FULL_DUPLICATE_UI pages by module

### utility-management (17 pages)

- `/dashboard/utility-management/kpi-center/boiler` ✅ MW
- `/dashboard/utility-management/kpi-center/chemicals` ✅ MW
- `/dashboard/utility-management/kpi-center/compressor` ✅ MW
- `/dashboard/utility-management/kpi-center/electricity` ✅ MW
- `/dashboard/utility-management/kpi-center/machine-utility` ✅ MW
- `/dashboard/utility-management/kpi-center/soft-water` ✅ MW
- `/dashboard/utility-management/kpi-center/solar` ✅ MW
- `/dashboard/utility-management/kpi-center/utility-cost` ✅ MW
- `/dashboard/utility-management/kpi-center/wastewater` ✅ MW
- `/dashboard/utility-management/kpi-center/water` ✅ MW
- `/dashboard/utility-management/reports/anomalies` ✅ MW
- `/dashboard/utility-management/reports/cost-allocation` ✅ MW
- `/dashboard/utility-management/reports/daily-consumption` ✅ MW
- `/dashboard/utility-management/reports/equipment-efficiency` ✅ MW
- `/dashboard/utility-management/reports/load-analysis` ✅ MW
- `/dashboard/utility-management/reports/sustainability` ✅ MW
- `/dashboard/utility-management/reports/treatment` ✅ MW

### marketing (14 pages)

- `/dashboard/marketing/ads/new` ✅ MW
- `/dashboard/marketing/brand-spend/new` ✅ MW
- `/dashboard/marketing/campaigns/new` ✅ MW
- `/dashboard/marketing/crm/followup` ❌ MW
- `/dashboard/marketing/crm` ❌ MW
- `/dashboard/marketing/ecommerce/stores` ✅ MW
- `/dashboard/marketing/influencers/new` ✅ MW
- `/dashboard/marketing/promotions/new` ✅ MW
- `/dashboard/marketing/segments/new` ✅ MW
- `/dashboard/marketing/social-media/new` ✅ MW
- `/dashboard/marketing/surveys/new` ❌ MW
- `/dashboard/marketing/surveys` ❌ MW
- `/dashboard/marketing/trade-spend/new` ✅ MW
- `/dashboard/marketing/visits/new` ✅ MW

### shelf-life (11 pages)

- `/dashboard/shelf-life/bulk-hold-monitor` ✅ MW
- `/dashboard/shelf-life/compliance` ✅ MW
- `/dashboard/shelf-life/customer-rules` ✅ MW
- `/dashboard/shelf-life/disposition` ✅ MW
- `/dashboard/shelf-life/expired` ✅ MW
- `/dashboard/shelf-life/fefo-config` ✅ MW
- `/dashboard/shelf-life/lot-aging` ✅ MW
- `/dashboard/shelf-life/near-expiry` ✅ MW
- `/dashboard/shelf-life/production-validation` ✅ MW
- `/dashboard/shelf-life/retest-queue` ✅ MW
- `/dashboard/shelf-life/shipment-validation` ✅ MW

### appraisals (10 pages)

- `/dashboard/appraisals/ai` ✅ MW
- `/dashboard/appraisals/development-plans` ✅ MW
- `/dashboard/appraisals/hr-review` ✅ MW
- `/dashboard/appraisals/manager-queue` ✅ MW
- `/dashboard/appraisals/periods` ✅ MW
- `/dashboard/appraisals/records/new` ✅ MW
- `/dashboard/appraisals/records` ✅ MW
- `/dashboard/appraisals/reports` ✅ MW
- `/dashboard/appraisals/self-review` ✅ MW
- `/dashboard/appraisals/templates` ✅ MW

### dimensions (10 pages)

- `/dashboard/dimensions/ai` ✅ MW
- `/dashboard/dimensions/allocation-run` ✅ MW
- `/dashboard/dimensions/allocations` ✅ MW
- `/dashboard/dimensions/completeness` ✅ MW
- `/dashboard/dimensions/cost-centers` ✅ MW
- `/dashboard/dimensions/defaults` ✅ MW
- `/dashboard/dimensions/reclassify` ✅ MW
- `/dashboard/dimensions/types` ✅ MW
- `/dashboard/dimensions/validation` ✅ MW
- `/dashboard/dimensions/values` ✅ MW

### qms (10 pages)

- `/dashboard/qms/ai` ✅ MW
- `/dashboard/qms/allergen` ✅ MW
- `/dashboard/qms/ccp` ✅ MW
- `/dashboard/qms/corrective-actions` ✅ MW
- `/dashboard/qms/deviations` ✅ MW
- `/dashboard/qms/haccp` ✅ MW
- `/dashboard/qms/inspections` ✅ MW
- `/dashboard/qms/quarantine` ✅ MW
- `/dashboard/qms/reports` ✅ MW
- `/dashboard/qms/templates` ✅ MW

### tpm (10 pages)

- `/dashboard/tpm/ai` ✅ MW
- `/dashboard/tpm/budget` ✅ MW
- `/dashboard/tpm/calendar` ✅ MW
- `/dashboard/tpm/claims` ✅ MW
- `/dashboard/tpm/plans/new` ✅ MW
- `/dashboard/tpm/plans` ✅ MW
- `/dashboard/tpm/promotions/new` ✅ MW
- `/dashboard/tpm/promotions` ✅ MW
- `/dashboard/tpm/roi` ✅ MW
- `/dashboard/tpm/settlement` ✅ MW

### expenses (9 pages)

- `/dashboard/expenses/advances` ✅ MW
- `/dashboard/expenses/ai` ✅ MW
- `/dashboard/expenses/approval` ✅ MW
- `/dashboard/expenses/categories` ✅ MW
- `/dashboard/expenses/claims/new` ✅ MW
- `/dashboard/expenses/claims` ✅ MW
- `/dashboard/expenses/policies` ✅ MW
- `/dashboard/expenses/reimbursement` ✅ MW
- `/dashboard/expenses/reports` ✅ MW

### fixed-assets (9 pages)

- `/dashboard/fixed-assets/ai` ✅ MW
- `/dashboard/fixed-assets/assets/new` ✅ MW
- `/dashboard/fixed-assets/assets` ✅ MW
- `/dashboard/fixed-assets/categories` ✅ MW
- `/dashboard/fixed-assets/depreciation` ✅ MW
- `/dashboard/fixed-assets/disposal` ✅ MW
- `/dashboard/fixed-assets/import` ✅ MW
- `/dashboard/fixed-assets/posting` ✅ MW
- `/dashboard/fixed-assets/transfer` ✅ MW

### machine-ops (9 pages)

- `/dashboard/machine-ops/assignment` ✅ MW
- `/dashboard/machine-ops/certs` ✅ MW
- `/dashboard/machine-ops/costing` ✅ MW
- `/dashboard/machine-ops/downtime` ✅ MW
- `/dashboard/machine-ops/machines` ✅ MW
- `/dashboard/machine-ops/operators` ✅ MW
- `/dashboard/machine-ops/performance` ✅ MW
- `/dashboard/machine-ops/runtime` ✅ MW
- `/dashboard/machine-ops/teams` ✅ MW

### material-flow (9 pages)

- `/dashboard/material-flow/bulk-transfer` ✅ MW
- `/dashboard/material-flow/fg-receipt` ✅ MW
- `/dashboard/material-flow/history` ✅ MW
- `/dashboard/material-flow/issue` ✅ MW
- `/dashboard/material-flow/reconciliation` ✅ MW
- `/dashboard/material-flow/reservations` ✅ MW
- `/dashboard/material-flow/returns` ✅ MW
- `/dashboard/material-flow/tanks` ✅ MW
- `/dashboard/material-flow/wip-transfer` ✅ MW

### recruitment (9 pages)

- `/dashboard/recruitment/ai` ✅ MW
- `/dashboard/recruitment/candidates` ✅ MW
- `/dashboard/recruitment/interviews` ✅ MW
- `/dashboard/recruitment/offers` ✅ MW
- `/dashboard/recruitment/pipeline` ✅ MW
- `/dashboard/recruitment/reports` ✅ MW
- `/dashboard/recruitment/requisitions/new` ✅ MW
- `/dashboard/recruitment/requisitions` ✅ MW
- `/dashboard/recruitment/stages` ✅ MW

### ess (8 pages)

- `/dashboard/ess/admin` ✅ MW
- `/dashboard/ess/ai` ✅ MW
- `/dashboard/ess/attendance` ✅ MW
- `/dashboard/ess/documents` ✅ MW
- `/dashboard/ess/leave` ✅ MW
- `/dashboard/ess/notifications` ✅ MW
- `/dashboard/ess/profile` ✅ MW
- `/dashboard/ess/requests` ✅ MW

### training (8 pages)

- `/dashboard/training/ai` ✅ MW
- `/dashboard/training/assignments` ✅ MW
- `/dashboard/training/certifications` ✅ MW
- `/dashboard/training/feedback` ✅ MW
- `/dashboard/training/programs` ✅ MW
- `/dashboard/training/reports` ✅ MW
- `/dashboard/training/sessions` ✅ MW
- `/dashboard/training/skill-matrix` ✅ MW

### fleet (7 pages)

- `/dashboard/fleet/drivers` ✅ MW
- `/dashboard/fleet/fuel` ✅ MW
- `/dashboard/fleet/incidents` ✅ MW
- `/dashboard/fleet/maintenance` ✅ MW
- `/dashboard/fleet/reports` ✅ MW
- `/dashboard/fleet/trips` ✅ MW
- `/dashboard/fleet/vehicles` ✅ MW

### portal (7 pages)

- `/dashboard/portal/accounts` ✅ MW
- `/dashboard/portal/activity` ✅ MW
- `/dashboard/portal/ai` ✅ MW
- `/dashboard/portal/claims` ✅ MW
- `/dashboard/portal/drafts` ✅ MW
- `/dashboard/portal/reports` ✅ MW
- `/dashboard/portal/users` ✅ MW

### report-builder (7 pages)

- `/dashboard/report-builder/ai` ✅ MW
- `/dashboard/report-builder/builder` ✅ MW
- `/dashboard/report-builder/catalog` ✅ MW
- `/dashboard/report-builder/dashboards` ✅ MW
- `/dashboard/report-builder/saved` ✅ MW
- `/dashboard/report-builder/schedules` ✅ MW
- `/dashboard/report-builder/viewer` ✅ MW

### reports (7 pages)

- `/dashboard/reports/finance` ✅ MW
- `/dashboard/reports/inventory` ✅ MW
- `/dashboard/reports/marketing` ✅ MW
- `/dashboard/reports/payments` ✅ MW
- `/dashboard/reports/procurement` ✅ MW
- `/dashboard/reports/production` ✅ MW
- `/dashboard/reports/sales` ✅ MW

### traceability (7 pages)

- `/dashboard/traceability/backward` ✅ MW
- `/dashboard/traceability/forward` ✅ MW
- `/dashboard/traceability/genealogy` ✅ MW
- `/dashboard/traceability/mock-recall` ✅ MW
- `/dashboard/traceability/recalls` ✅ MW
- `/dashboard/traceability/regulatory` ✅ MW
- `/dashboard/traceability/search` ✅ MW

### van-sales (7 pages)

- `/dashboard/van-sales/ai` ✅ MW
- `/dashboard/van-sales/pos` ✅ MW
- `/dashboard/van-sales/reconciliation` ✅ MW
- `/dashboard/van-sales/route` ✅ MW
- `/dashboard/van-sales/stock` ✅ MW
- `/dashboard/van-sales/vans/new` ✅ MW
- `/dashboard/van-sales/vans` ✅ MW

### bank-reconciliation (6 pages)

- `/dashboard/bank-reconciliation/ai` ✅ MW
- `/dashboard/bank-reconciliation/balance` ✅ MW
- `/dashboard/bank-reconciliation/import` ✅ MW
- `/dashboard/bank-reconciliation/open-items` ✅ MW
- `/dashboard/bank-reconciliation/rules` ✅ MW
- `/dashboard/bank-reconciliation/statements` ✅ MW

### custom-fields (6 pages)

- `/dashboard/custom-fields/ai` ✅ MW
- `/dashboard/custom-fields/fields` ✅ MW
- `/dashboard/custom-fields/form-builder` ✅ MW
- `/dashboard/custom-fields/new-field` ✅ MW
- `/dashboard/custom-fields/values` ✅ MW
- `/dashboard/custom-fields/workflow-rules` ✅ MW

### notification-center (6 pages)

- `/dashboard/notification-center/ai` ✅ MW
- `/dashboard/notification-center/list` ✅ MW
- `/dashboard/notification-center/preferences` ✅ MW
- `/dashboard/notification-center/reports` ✅ MW
- `/dashboard/notification-center/schedules` ✅ MW
- `/dashboard/notification-center/templates` ✅ MW

### timesheets (6 pages)

- `/dashboard/timesheets/ai` ✅ MW
- `/dashboard/timesheets/approval-queue` ✅ MW
- `/dashboard/timesheets/my-timesheets` ✅ MW
- `/dashboard/timesheets/reports` ✅ MW
- `/dashboard/timesheets/time-entry` ✅ MW
- `/dashboard/timesheets/weekly-view` ✅ MW

### webhooks (6 pages)

- `/dashboard/webhooks/dead-letter` ✅ MW
- `/dashboard/webhooks/definitions` ✅ MW
- `/dashboard/webhooks/deliveries` ✅ MW
- `/dashboard/webhooks/inbound` ✅ MW
- `/dashboard/webhooks/reports` ✅ MW
- `/dashboard/webhooks/subscriptions` ✅ MW

### calendar (5 pages)

- `/dashboard/calendar/availability` ✅ MW
- `/dashboard/calendar/events` ✅ MW
- `/dashboard/calendar/new-event` ✅ MW
- `/dashboard/calendar/resources` ✅ MW
- `/dashboard/calendar/view` ✅ MW

### cycle-count (5 pages)

- `/dashboard/cycle-count/entries` ✅ MW
- `/dashboard/cycle-count/plans` ✅ MW
- `/dashboard/cycle-count/reports` ✅ MW
- `/dashboard/cycle-count/tasks` ✅ MW
- `/dashboard/cycle-count/variances` ✅ MW

### dunning (5 pages)

- `/dashboard/dunning/aging` ✅ MW
- `/dashboard/dunning/cases` ✅ MW
- `/dashboard/dunning/credit-holds` ✅ MW
- `/dashboard/dunning/policies` ✅ MW
- `/dashboard/dunning/workqueue` ✅ MW

### esg (5 pages)

- `/dashboard/esg/activities` ✅ MW
- `/dashboard/esg/factors` ✅ MW
- `/dashboard/esg/intelligence` ✅ MW
- `/dashboard/esg/reports` ✅ MW
- `/dashboard/esg/targets` ✅ MW

### finance (5 pages)

- `/dashboard/finance/accounting/customers-ledger` ✅ MW
- `/dashboard/finance/accounting/payments` ✅ MW
- `/dashboard/finance/accounting/purchase-invoices` ✅ MW
- `/dashboard/finance/accounting/sales-invoices` ✅ MW
- `/dashboard/finance/accounting/suppliers-ledger` ✅ MW

### invoice-match (5 pages)

- `/dashboard/invoice-match/ai` ✅ MW
- `/dashboard/invoice-match/blocked` ✅ MW
- `/dashboard/invoice-match/duplicates` ✅ MW
- `/dashboard/invoice-match/matches` ✅ MW
- `/dashboard/invoice-match/review-queue` ✅ MW

### kanban (5 pages)

- `/dashboard/kanban/ai` ✅ MW
- `/dashboard/kanban/boards` ✅ MW
- `/dashboard/kanban/cards` ✅ MW
- `/dashboard/kanban/reports` ✅ MW
- `/dashboard/kanban/view` ✅ MW

### subcontracting (5 pages)

- `/dashboard/subcontracting/ai` ✅ MW
- `/dashboard/subcontracting/locations` ✅ MW
- `/dashboard/subcontracting/orders` ✅ MW
- `/dashboard/subcontracting/stock` ✅ MW
- `/dashboard/subcontracting/yield` ✅ MW

### chatter (4 pages)

- `/dashboard/chatter/ai` ✅ MW
- `/dashboard/chatter/feed` ✅ MW
- `/dashboard/chatter/reports` ✅ MW
- `/dashboard/chatter/search` ✅ MW

### commissions (4 pages)

- `/dashboard/commissions/ai` ✅ MW
- `/dashboard/commissions/payouts` ✅ MW
- `/dashboard/commissions/rules` ✅ MW
- `/dashboard/commissions/transactions` ✅ MW

### contracts (4 pages)

- `/dashboard/contracts/ai` ✅ MW
- `/dashboard/contracts/expiring` ✅ MW
- `/dashboard/contracts/list` ✅ MW
- `/dashboard/contracts/new` ✅ MW

### procurement-suggestion (4 pages)

- `/dashboard/procurement-suggestion/ai` ✅ MW
- `/dashboard/procurement-suggestion/groups` ✅ MW
- `/dashboard/procurement-suggestion/suggestions` ✅ MW
- `/dashboard/procurement-suggestion/supplier-prices` ✅ MW

### recurring-orders (4 pages)

- `/dashboard/recurring-orders/ai` ✅ MW
- `/dashboard/recurring-orders/reports` ✅ MW
- `/dashboard/recurring-orders/templates/new` ✅ MW
- `/dashboard/recurring-orders/templates` ✅ MW

### tax (4 pages)

- `/dashboard/tax/regulatory` ✅ MW
- `/dashboard/tax/reports` ✅ MW
- `/dashboard/tax/rules` ✅ MW
- `/dashboard/tax/transactions` ✅ MW

### allergen (3 pages)

- `/dashboard/allergen/change-logs` ✅ MW
- `/dashboard/allergen/material-profiles` ✅ MW
- `/dashboard/allergen/product-allergens` ✅ MW

### landed-cost (3 pages)

- `/dashboard/landed-cost/ai` ✅ MW
- `/dashboard/landed-cost/documents` ✅ MW
- `/dashboard/landed-cost/new` ✅ MW

### mrp (3 pages)

- `/dashboard/mrp/forecast` ✅ MW
- `/dashboard/mrp/run` ✅ MW
- `/dashboard/mrp/suggestions` ✅ MW

### secondary-sales (3 pages)

- `/dashboard/secondary-sales/analysis` ✅ MW
- `/dashboard/secondary-sales/inventory` ✅ MW
- `/dashboard/secondary-sales/upload` ✅ MW

### developer (2 pages)

- `/dashboard/developer/graphql` ✅ MW
- `/dashboard/developer/keys` ✅ MW

### knowledge-base (2 pages)

- `/dashboard/knowledge-base/articles/new` ✅ MW
- `/dashboard/knowledge-base/articles` ✅ MW

### mobile (2 pages)

- `/dashboard/mobile/approvals` ✅ MW
- `/dashboard/mobile/devices` ✅ MW

### documents (1 pages)

- `/dashboard/documents/new` ✅ MW

### price-lists (1 pages)

- `/dashboard/price-lists/approval-queue` ✅ MW

### production-execution (1 pages)

- `/dashboard/production-execution/work-orders` ✅ MW

### surveys (1 pages)

- `/dashboard/surveys/new` ✅ MW
