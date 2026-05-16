# Page Count Report

Generated: 2026-05-16

## Summary

| Classification            | Code | Count |
|---------------------------|------|-------|
| WORKSPACE_PAGE            | A    | 31   |
| REDIRECT_ONLY             | B    | 149   |
| LIGHTWEIGHT_WRAPPER       | C    | 213   |
| FULL_DUPLICATE_UI         | D    | 351   |
| STANDALONE_OPERATIONAL    | E    | 7   |
| UNKNOWN                   | F    | 3   |
| **Total**                 |      | **754** |

## Definitions

- **A WORKSPACE_PAGE** — renders `<ModuleWorkspace tabs={...}>` — these are the destination pages.
- **B REDIRECT_ONLY** — page body only calls `redirect()` / `permanentRedirect()` — no UI.
- **C LIGHTWEIGHT_WRAPPER** — dynamically imported as a tab by a workspace page. Stays as-is.
- **D FULL_DUPLICATE_UI** — has own API calls/state/forms and is NOT used as a workspace tab.
  These are the pages to migrate or convert to redirect-only.
- **E STANDALONE_OPERATIONAL** — full-screen tool that must remain standalone (POS, shop-floor).
- **F UNKNOWN** — could not classify from content heuristics.

## FULL_DUPLICATE_UI pages by module

### material-flow (11 pages)

- `/dashboard/material-flow/bulk-transfer` ✅ MW
- `/dashboard/material-flow/fg-receipt` ✅ MW
- `/dashboard/material-flow/history` ✅ MW
- `/dashboard/material-flow/issue` ✅ MW
- `/dashboard/material-flow/packaging` ✅ MW
- `/dashboard/material-flow/reconciliation` ✅ MW
- `/dashboard/material-flow/reservations` ✅ MW
- `/dashboard/material-flow/returns` ✅ MW
- `/dashboard/material-flow/stages` ✅ MW
- `/dashboard/material-flow/tanks` ✅ MW
- `/dashboard/material-flow/wip-transfer` ✅ MW

### portal (11 pages)

- `/dashboard/portal/accounts/[id]` ✅ MW
- `/dashboard/portal/accounts/[id]/view` ✅ MW
- `/dashboard/portal/accounts` ✅ MW
- `/dashboard/portal/activity` ✅ MW
- `/dashboard/portal/ai` ✅ MW
- `/dashboard/portal/claims` ✅ MW
- `/dashboard/portal/drafts` ✅ MW
- `/dashboard/portal/order-tracking` ✅ MW
- `/dashboard/portal/reports` ✅ MW
- `/dashboard/portal/sell-through` ✅ MW
- `/dashboard/portal/users` ✅ MW

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

### supplier-portal (11 pages)

- `/dashboard/supplier-portal/accounts/[id]` ✅ MW
- `/dashboard/supplier-portal/accounts/[id]/purchase-orders` ✅ MW
- `/dashboard/supplier-portal/accounts` ✅ MW
- `/dashboard/supplier-portal/activity` ✅ MW
- `/dashboard/supplier-portal/ai` ✅ MW
- `/dashboard/supplier-portal/documents` ✅ MW
- `/dashboard/supplier-portal/eta` ✅ MW
- `/dashboard/supplier-portal/invoices` ✅ MW
- `/dashboard/supplier-portal/payment` ✅ MW
- `/dashboard/supplier-portal/reports` ✅ MW
- `/dashboard/supplier-portal/users` ✅ MW

### tpm (11 pages)

- `/dashboard/tpm/ai` ✅ MW
- `/dashboard/tpm/budget` ✅ MW
- `/dashboard/tpm/calendar` ✅ MW
- `/dashboard/tpm/claims` ✅ MW
- `/dashboard/tpm/plans/new` ✅ MW
- `/dashboard/tpm/plans` ✅ MW
- `/dashboard/tpm/promotions/[id]` ✅ MW
- `/dashboard/tpm/promotions/new` ✅ MW
- `/dashboard/tpm/promotions` ✅ MW
- `/dashboard/tpm/roi` ✅ MW
- `/dashboard/tpm/settlement` ✅ MW

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

### bank-reconciliation (10 pages)

- `/dashboard/bank-reconciliation/accounts` ✅ MW
- `/dashboard/bank-reconciliation/ai` ✅ MW
- `/dashboard/bank-reconciliation/balance` ✅ MW
- `/dashboard/bank-reconciliation/import` ✅ MW
- `/dashboard/bank-reconciliation/mpesa` ✅ MW
- `/dashboard/bank-reconciliation/open-items` ✅ MW
- `/dashboard/bank-reconciliation/reports` ✅ MW
- `/dashboard/bank-reconciliation/rules` ✅ MW
- `/dashboard/bank-reconciliation/statements/[id]` ✅ MW
- `/dashboard/bank-reconciliation/statements` ✅ MW

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

### recurring-orders (10 pages)

- `/dashboard/recurring-orders/ai` ✅ MW
- `/dashboard/recurring-orders/billing` ✅ MW
- `/dashboard/recurring-orders/generation-log` ✅ MW
- `/dashboard/recurring-orders/pause-skip` ✅ MW
- `/dashboard/recurring-orders/reports` ✅ MW
- `/dashboard/recurring-orders/schedule` ✅ MW
- `/dashboard/recurring-orders/templates/[id]` ✅ MW
- `/dashboard/recurring-orders/templates/new` ✅ MW
- `/dashboard/recurring-orders/templates` ✅ MW
- `/dashboard/recurring-orders/upcoming-demand` ✅ MW

### calendar (9 pages)

- `/dashboard/calendar/ai` ✅ MW
- `/dashboard/calendar/availability` ✅ MW
- `/dashboard/calendar/bookings` ✅ MW
- `/dashboard/calendar/events` ✅ MW
- `/dashboard/calendar/new-event` ✅ MW
- `/dashboard/calendar/reports` ✅ MW
- `/dashboard/calendar/resources` ✅ MW
- `/dashboard/calendar/shifts` ✅ MW
- `/dashboard/calendar/view` ✅ MW

### dunning (9 pages)

- `/dashboard/dunning/aging` ✅ MW
- `/dashboard/dunning/ai` ✅ MW
- `/dashboard/dunning/cases/[id]` ✅ MW
- `/dashboard/dunning/cases` ✅ MW
- `/dashboard/dunning/credit-holds` ✅ MW
- `/dashboard/dunning/policies` ✅ MW
- `/dashboard/dunning/reports` ✅ MW
- `/dashboard/dunning/templates` ✅ MW
- `/dashboard/dunning/workqueue` ✅ MW

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

### report-builder (9 pages)

- `/dashboard/report-builder/ai` ✅ MW
- `/dashboard/report-builder/builder` ✅ MW
- `/dashboard/report-builder/catalog` ✅ MW
- `/dashboard/report-builder/dashboards` ✅ MW
- `/dashboard/report-builder/executive` ✅ MW
- `/dashboard/report-builder/rls` ✅ MW
- `/dashboard/report-builder/saved` ✅ MW
- `/dashboard/report-builder/schedules` ✅ MW
- `/dashboard/report-builder/viewer` ✅ MW

### traceability (9 pages)

- `/dashboard/traceability/backward` ✅ MW
- `/dashboard/traceability/forward` ✅ MW
- `/dashboard/traceability/genealogy` ✅ MW
- `/dashboard/traceability/mock-recall` ✅ MW
- `/dashboard/traceability/recalls/[id]` ✅ MW
- `/dashboard/traceability/recalls` ✅ MW
- `/dashboard/traceability/regulatory` ✅ MW
- `/dashboard/traceability/search` ✅ MW
- `/dashboard/traceability/templates` ✅ MW

### custom-fields (8 pages)

- `/dashboard/custom-fields/[id]` ✅ MW
- `/dashboard/custom-fields/ai` ✅ MW
- `/dashboard/custom-fields/fields` ✅ MW
- `/dashboard/custom-fields/form-builder` ✅ MW
- `/dashboard/custom-fields/new-field` ✅ MW
- `/dashboard/custom-fields/reports` ✅ MW
- `/dashboard/custom-fields/values` ✅ MW
- `/dashboard/custom-fields/workflow-rules` ✅ MW

### ess (8 pages)

- `/dashboard/ess/admin` ✅ MW
- `/dashboard/ess/ai` ✅ MW
- `/dashboard/ess/attendance` ✅ MW
- `/dashboard/ess/documents` ✅ MW
- `/dashboard/ess/leave` ✅ MW
- `/dashboard/ess/notifications` ✅ MW
- `/dashboard/ess/profile` ✅ MW
- `/dashboard/ess/requests` ✅ MW

### gs1 (8 pages)

- `/dashboard/gs1/ai` ✅ MW
- `/dashboard/gs1/barcodes` ✅ MW
- `/dashboard/gs1/config` ✅ MW
- `/dashboard/gs1/labels` ✅ MW
- `/dashboard/gs1/print-queue` ✅ MW
- `/dashboard/gs1/reports` ✅ MW
- `/dashboard/gs1/scan` ✅ MW
- `/dashboard/gs1/sscc` ✅ MW

### invoice-match (8 pages)

- `/dashboard/invoice-match/[id]` ✅ MW
- `/dashboard/invoice-match/ai` ✅ MW
- `/dashboard/invoice-match/blocked` ✅ MW
- `/dashboard/invoice-match/duplicates` ✅ MW
- `/dashboard/invoice-match/matches` ✅ MW
- `/dashboard/invoice-match/reports` ✅ MW
- `/dashboard/invoice-match/review-queue` ✅ MW
- `/dashboard/invoice-match/tolerance-rules` ✅ MW

### price-lists (8 pages)

- `/dashboard/price-lists/[id]` ✅ MW
- `/dashboard/price-lists/ai` ✅ MW
- `/dashboard/price-lists/approval-queue` ✅ MW
- `/dashboard/price-lists/compare` ✅ MW
- `/dashboard/price-lists/discount-rules` ✅ MW
- `/dashboard/price-lists/import` ✅ MW
- `/dashboard/price-lists/margin` ✅ MW
- `/dashboard/price-lists/reports` ✅ MW

### promotions (8 pages)

- `/dashboard/promotions/ai` ✅ MW
- `/dashboard/promotions/analytics` ✅ MW
- `/dashboard/promotions/overrides` ✅ MW
- `/dashboard/promotions` ✅ MW
- `/dashboard/promotions/schemes/[id]` ✅ MW
- `/dashboard/promotions/schemes/new` ✅ MW
- `/dashboard/promotions/schemes` ✅ MW
- `/dashboard/promotions/simulate` ✅ MW

### training (8 pages)

- `/dashboard/training/ai` ✅ MW
- `/dashboard/training/assignments` ✅ MW
- `/dashboard/training/certifications` ✅ MW
- `/dashboard/training/feedback` ✅ MW
- `/dashboard/training/programs` ✅ MW
- `/dashboard/training/reports` ✅ MW
- `/dashboard/training/sessions` ✅ MW
- `/dashboard/training/skill-matrix` ✅ MW

### contracts (7 pages)

- `/dashboard/contracts/ai` ✅ MW
- `/dashboard/contracts/expiring` ✅ MW
- `/dashboard/contracts/list/[id]` ✅ MW
- `/dashboard/contracts/list` ✅ MW
- `/dashboard/contracts/new` ✅ MW
- `/dashboard/contracts/performance` ✅ MW
- `/dashboard/contracts/reports` ✅ MW

### fleet (7 pages)

- `/dashboard/fleet/drivers` ✅ MW
- `/dashboard/fleet/fuel` ✅ MW
- `/dashboard/fleet/incidents` ✅ MW
- `/dashboard/fleet/maintenance` ✅ MW
- `/dashboard/fleet/reports` ✅ MW
- `/dashboard/fleet/trips` ✅ MW
- `/dashboard/fleet/vehicles` ✅ MW

### reports (7 pages)

- `/dashboard/reports/finance` ✅ MW
- `/dashboard/reports/inventory` ✅ MW
- `/dashboard/reports/marketing` ✅ MW
- `/dashboard/reports/payments` ✅ MW
- `/dashboard/reports/procurement` ✅ MW
- `/dashboard/reports/production` ✅ MW
- `/dashboard/reports/sales` ✅ MW

### commissions (6 pages)

- `/dashboard/commissions/ai` ✅ MW
- `/dashboard/commissions/payouts` ✅ MW
- `/dashboard/commissions/reports` ✅ MW
- `/dashboard/commissions/rules` ✅ MW
- `/dashboard/commissions/targets` ✅ MW
- `/dashboard/commissions/transactions` ✅ MW

### esg (6 pages)

- `/dashboard/esg/activities` ✅ MW
- `/dashboard/esg/carbon` ✅ MW
- `/dashboard/esg/factors` ✅ MW
- `/dashboard/esg/intelligence` ✅ MW
- `/dashboard/esg/reports` ✅ MW
- `/dashboard/esg/targets` ✅ MW

### mrp (6 pages)

- `/dashboard/mrp/forecast/accuracy` ✅ MW
- `/dashboard/mrp/forecast/correlation` ✅ MW
- `/dashboard/mrp/forecast` ✅ MW
- `/dashboard/mrp/run` ✅ MW
- `/dashboard/mrp/suggestions` ✅ MW
- `/dashboard/mrp/workbench` ✅ MW

### notification-center (6 pages)

- `/dashboard/notification-center/ai` ✅ MW
- `/dashboard/notification-center/list` ✅ MW
- `/dashboard/notification-center/preferences` ✅ MW
- `/dashboard/notification-center/reports` ✅ MW
- `/dashboard/notification-center/schedules` ✅ MW
- `/dashboard/notification-center/templates` ✅ MW

### procurement-suggestion (6 pages)

- `/dashboard/procurement-suggestion/ai` ✅ MW
- `/dashboard/procurement-suggestion/groups` ✅ MW
- `/dashboard/procurement-suggestion/reports` ✅ MW
- `/dashboard/procurement-suggestion/suggestions` ✅ MW
- `/dashboard/procurement-suggestion/supplier-compare` ✅ MW
- `/dashboard/procurement-suggestion/supplier-prices` ✅ MW

### subcontracting (6 pages)

- `/dashboard/subcontracting/ai` ✅ MW
- `/dashboard/subcontracting/locations` ✅ MW
- `/dashboard/subcontracting/orders` ✅ MW
- `/dashboard/subcontracting/performance` ✅ MW
- `/dashboard/subcontracting/stock` ✅ MW
- `/dashboard/subcontracting/yield` ✅ MW

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

### chatter (5 pages)

- `/dashboard/chatter/ai` ✅ MW
- `/dashboard/chatter/feed` ✅ MW
- `/dashboard/chatter/reports` ✅ MW
- `/dashboard/chatter/search` ✅ MW
- `/dashboard/chatter/threads` ✅ MW

### cycle-count (5 pages)

- `/dashboard/cycle-count/entries` ✅ MW
- `/dashboard/cycle-count/plans` ✅ MW
- `/dashboard/cycle-count/reports` ✅ MW
- `/dashboard/cycle-count/tasks` ✅ MW
- `/dashboard/cycle-count/variances` ✅ MW

### kanban (5 pages)

- `/dashboard/kanban/ai` ✅ MW
- `/dashboard/kanban/boards` ✅ MW
- `/dashboard/kanban/cards` ✅ MW
- `/dashboard/kanban/reports` ✅ MW
- `/dashboard/kanban/view` ✅ MW

### landed-cost (5 pages)

- `/dashboard/landed-cost/[id]` ✅ MW
- `/dashboard/landed-cost/ai` ✅ MW
- `/dashboard/landed-cost/documents` ✅ MW
- `/dashboard/landed-cost/new` ✅ MW
- `/dashboard/landed-cost/reports` ✅ MW

### sales (5 pages)

- `/dashboard/sales/customer-statement` ❌ MW
- `/dashboard/sales/invoices/[id]` ❌ MW
- `/dashboard/sales/orders/[id]` ❌ MW
- `/dashboard/sales/pod` ❌ MW
- `/dashboard/sales/shipments/[id]` ❌ MW

### wms (5 pages)

- `/dashboard/wms/counts/[id]` ✅ MW
- `/dashboard/wms/counts` ✅ MW
- `/dashboard/wms/picking` ✅ MW
- `/dashboard/wms/replenishment` ✅ MW
- `/dashboard/wms/reports` ✅ MW

### bom (4 pages)

- `/dashboard/bom/[id]/compliance` ❌ MW
- `/dashboard/bom/[id]/costing` ❌ MW
- `/dashboard/bom/[id]/explode` ❌ MW
- `/dashboard/bom/[id]` ❌ MW

### crm (4 pages)

- `/dashboard/crm/ai` ❌ MW
- `/dashboard/crm/overdue` ❌ MW
- `/dashboard/crm/qualify` ❌ MW
- `/dashboard/crm/records/[id]` ❌ MW

### mps (4 pages)

- `/dashboard/mps/campaigns` ✅ MW
- `/dashboard/mps/capacity` ✅ MW
- `/dashboard/mps/planning-board` ✅ MW
- `/dashboard/mps/whatif` ✅ MW

### surveys (4 pages)

- `/dashboard/surveys/[id]` ✅ MW
- `/dashboard/surveys/[id]/respond` ✅ MW
- `/dashboard/surveys/[id]/results` ✅ MW
- `/dashboard/surveys/new` ✅ MW

### tax (4 pages)

- `/dashboard/tax/regulatory` ✅ MW
- `/dashboard/tax/reports` ✅ MW
- `/dashboard/tax/rules` ✅ MW
- `/dashboard/tax/transactions` ✅ MW

### knowledge-base (3 pages)

- `/dashboard/knowledge-base/[id]` ✅ MW
- `/dashboard/knowledge-base/articles/new` ✅ MW
- `/dashboard/knowledge-base/articles` ✅ MW

### production-execution (3 pages)

- `/dashboard/production-execution/[id]/genealogy` ✅ MW
- `/dashboard/production-execution/[id]` ✅ MW
- `/dashboard/production-execution/work-orders` ✅ MW

### putaway (3 pages)

- `/dashboard/putaway/execute/[id]` ✅ MW
- `/dashboard/putaway` ✅ MW
- `/dashboard/putaway/rules` ✅ MW

### secondary-sales (3 pages)

- `/dashboard/secondary-sales/analysis` ✅ MW
- `/dashboard/secondary-sales/inventory` ✅ MW
- `/dashboard/secondary-sales/upload` ✅ MW

### containers (2 pages)

- `/dashboard/containers/outstanding` ✅ MW
- `/dashboard/containers` ✅ MW

### developer (2 pages)

- `/dashboard/developer/graphql` ✅ MW
- `/dashboard/developer/keys` ✅ MW

### documents (2 pages)

- `/dashboard/documents/[id]` ❌ MW
- `/dashboard/documents/new` ❌ MW

### logs (2 pages)

- `/dashboard/logs/compliance` ✅ MW
- `/dashboard/logs/retention` ✅ MW

### mobile (2 pages)

- `/dashboard/mobile/approvals` ✅ MW
- `/dashboard/mobile/devices` ✅ MW

### procurement (2 pages)

- `/dashboard/procurement/[id]` ❌ MW
- `/dashboard/procurement/orders/[id]` ❌ MW

### projects (2 pages)

- `/dashboard/projects/[id]` ✅ MW
- `/dashboard/projects/dashboard` ✅ MW

### brand-assets (1 pages)

- `/dashboard/brand-assets/[id]` ✅ MW

### copacking (1 pages)

- `/dashboard/copacking` ✅ MW

### npd (1 pages)

- `/dashboard/npd/[id]` ❌ MW

### root (1 pages)

- `/dashboard/` ❌ MW

### payroll (1 pages)

- `/dashboard/payroll/runs/[id]` ❌ MW

### quality (1 pages)

- `/dashboard/quality/[id]` ❌ MW

### recipes (1 pages)

- `/dashboard/recipes/[id]` ❌ MW

### roles (1 pages)

- `/dashboard/roles/[id]` ✅ MW

### security (1 pages)

- `/dashboard/security/monitor` ✅ MW

### users (1 pages)

- `/dashboard/users/[id]` ✅ MW
