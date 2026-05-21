# Visible Import Graph

**Date:** 2026-05-21
**Method:** Static analysis of dynamic() imports in workspace pages cross-referenced with middleware redirect map.

## Key Finding: Dynamic Import Visibility Blind Spot

The previous audit incorrectly classified ~296 broken action cards as "safe" because their source pages
were middleware-redirected as standalone routes. This is wrong when those pages are ALSO dynamically
imported into workspace tabs.

**Rule:** A page is user-visible if it is dynamically imported into a workspace, regardless of what
middleware does to its standalone route.

## Summary

| Metric | Count |
|--------|-------|
| Total dynamically imported pages | 188 |
| Pages with broken action cards | 59 |
| Pages that are BOTH redirect stubs AND have broken cards | 58 |
| Total broken visible action targets | 296 |

## Pages with Broken Action Cards (User-Visible Through Dynamic Import)

### frontend/src/app/dashboard/cycle-count/page.tsx

- **Route (standalone):** `/dashboard/cycle-count`
- **Standalone redirected:** YES → /dashboard/inventory?tab=cycle-count
- **Visible via:** `/dashboard/inventory?tab=cycle-count`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/cycle-count/entries`, `/dashboard/cycle-count/plans`, `/dashboard/cycle-count/reports`, `/dashboard/cycle-count/tasks`, `/dashboard/cycle-count/variances`

### frontend/src/app/dashboard/shelf-life/page.tsx

- **Route (standalone):** `/dashboard/shelf-life`
- **Standalone redirected:** YES → /dashboard/inventory?tab=shelf-life
- **Visible via:** `/dashboard/inventory?tab=shelf-life`
- **Broken card count:** 11
- **Broken targets:** `/dashboard/shelf-life/bulk-hold-monitor`, `/dashboard/shelf-life/compliance`, `/dashboard/shelf-life/customer-rules`, `/dashboard/shelf-life/disposition`, `/dashboard/shelf-life/expired`, `/dashboard/shelf-life/fefo-config`, `/dashboard/shelf-life/lot-aging`, `/dashboard/shelf-life/near-expiry`, `/dashboard/shelf-life/production-validation`, `/dashboard/shelf-life/retest-queue`, `/dashboard/shelf-life/shipment-validation`

### frontend/src/app/dashboard/traceability/page.tsx

- **Route (standalone):** `/dashboard/traceability`
- **Standalone redirected:** YES → /dashboard/inventory?tab=traceability
- **Visible via:** `/dashboard/inventory?tab=traceability`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/traceability/backward`, `/dashboard/traceability/forward`, `/dashboard/traceability/genealogy`, `/dashboard/traceability/mock-recall`, `/dashboard/traceability/recalls`, `/dashboard/traceability/regulatory`, `/dashboard/traceability/search`

### frontend/src/app/dashboard/mrp/page.tsx

- **Route (standalone):** `/dashboard/mrp`
- **Standalone redirected:** YES → /dashboard/planning?tab=mrp
- **Visible via:** `/dashboard/planning?tab=mrp`
- **Broken card count:** 3
- **Broken targets:** `/dashboard/mrp/forecast`, `/dashboard/mrp/run`, `/dashboard/mrp/suggestions`

### frontend/src/app/dashboard/kanban/page.tsx

- **Route (standalone):** `/dashboard/kanban`
- **Standalone redirected:** YES → /dashboard/planning?tab=kanban
- **Visible via:** `/dashboard/planning?tab=kanban`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/kanban/ai`, `/dashboard/kanban/boards`, `/dashboard/kanban/cards`, `/dashboard/kanban/reports`, `/dashboard/kanban/view`

### frontend/src/app/dashboard/production-execution/page.tsx

- **Route (standalone):** `/dashboard/production-execution`
- **Standalone redirected:** YES → /dashboard/production?tab=execution
- **Visible via:** `/dashboard/production?tab=execution`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/production-execution/work-orders`

### frontend/src/app/dashboard/machine-ops/page.tsx

- **Route (standalone):** `/dashboard/machine-ops`
- **Standalone redirected:** YES → /dashboard/production?tab=machine-ops
- **Visible via:** `/dashboard/production?tab=machine-ops`
- **Broken card count:** 9
- **Broken targets:** `/dashboard/machine-ops/assignment`, `/dashboard/machine-ops/certs`, `/dashboard/machine-ops/costing`, `/dashboard/machine-ops/downtime`, `/dashboard/machine-ops/machines`, `/dashboard/machine-ops/operators`, `/dashboard/machine-ops/performance`, `/dashboard/machine-ops/runtime`, `/dashboard/machine-ops/teams`

### frontend/src/app/dashboard/material-flow/page.tsx

- **Route (standalone):** `/dashboard/material-flow`
- **Standalone redirected:** YES → /dashboard/production?tab=material-flow
- **Visible via:** `/dashboard/production?tab=material-flow`
- **Broken card count:** 9
- **Broken targets:** `/dashboard/material-flow/bulk-transfer`, `/dashboard/material-flow/fg-receipt`, `/dashboard/material-flow/history`, `/dashboard/material-flow/issue`, `/dashboard/material-flow/reconciliation`, `/dashboard/material-flow/reservations`, `/dashboard/material-flow/returns`, `/dashboard/material-flow/tanks`, `/dashboard/material-flow/wip-transfer`

### frontend/src/app/dashboard/finance/accounting/page.tsx

- **Route (standalone):** `/dashboard/finance/accounting`
- **Standalone redirected:** YES → /dashboard/finance?tab=accounting
- **Visible via:** `/dashboard/finance?tab=accounting`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/finance/accounting/controls`, `/dashboard/finance/accounting/customers-ledger`, `/dashboard/finance/accounting/payments`, `/dashboard/finance/accounting/purchase-invoices`, `/dashboard/finance/accounting/sales-invoices`, `/dashboard/finance/accounting/suppliers-ledger`

### frontend/src/app/dashboard/bank-reconciliation/page.tsx

- **Route (standalone):** `/dashboard/bank-reconciliation`
- **Standalone redirected:** YES → /dashboard/finance?tab=bank-recon
- **Visible via:** `/dashboard/finance?tab=bank-recon`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/bank-reconciliation/ai`, `/dashboard/bank-reconciliation/balance`, `/dashboard/bank-reconciliation/import`, `/dashboard/bank-reconciliation/open-items`, `/dashboard/bank-reconciliation/rules`, `/dashboard/bank-reconciliation/statements`

### frontend/src/app/dashboard/invoice-match/page.tsx

- **Route (standalone):** `/dashboard/invoice-match`
- **Standalone redirected:** YES → /dashboard/finance?tab=invoice-match
- **Visible via:** `/dashboard/finance?tab=invoice-match`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/invoice-match/ai`, `/dashboard/invoice-match/blocked`, `/dashboard/invoice-match/duplicates`, `/dashboard/invoice-match/matches`, `/dashboard/invoice-match/review-queue`

### frontend/src/app/dashboard/fixed-assets/page.tsx

- **Route (standalone):** `/dashboard/fixed-assets`
- **Standalone redirected:** YES → /dashboard/finance?tab=fixed-assets
- **Visible via:** `/dashboard/finance?tab=fixed-assets`
- **Broken card count:** 9
- **Broken targets:** `/dashboard/fixed-assets/ai`, `/dashboard/fixed-assets/assets/new`, `/dashboard/fixed-assets/assets`, `/dashboard/fixed-assets/categories`, `/dashboard/fixed-assets/depreciation`, `/dashboard/fixed-assets/disposal`, `/dashboard/fixed-assets/import`, `/dashboard/fixed-assets/posting`, `/dashboard/fixed-assets/transfer`

### frontend/src/app/dashboard/dimensions/page.tsx

- **Route (standalone):** `/dashboard/dimensions`
- **Standalone redirected:** YES → /dashboard/finance?tab=dimensions
- **Visible via:** `/dashboard/finance?tab=dimensions`
- **Broken card count:** 10
- **Broken targets:** `/dashboard/dimensions/ai`, `/dashboard/dimensions/allocation-run`, `/dashboard/dimensions/allocations`, `/dashboard/dimensions/completeness`, `/dashboard/dimensions/cost-centers`, `/dashboard/dimensions/defaults`, `/dashboard/dimensions/reclassify`, `/dashboard/dimensions/types`, `/dashboard/dimensions/validation`, `/dashboard/dimensions/values`

### frontend/src/app/dashboard/dunning/page.tsx

- **Route (standalone):** `/dashboard/dunning`
- **Standalone redirected:** YES → /dashboard/finance?tab=dunning
- **Visible via:** `/dashboard/finance?tab=dunning`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/dunning/aging`, `/dashboard/dunning/cases`, `/dashboard/dunning/credit-holds`, `/dashboard/dunning/policies`, `/dashboard/dunning/workqueue`

### frontend/src/app/dashboard/tax/page.tsx

- **Route (standalone):** `/dashboard/tax`
- **Standalone redirected:** YES → /dashboard/finance?tab=tax
- **Visible via:** `/dashboard/finance?tab=tax`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/tax/regulatory`, `/dashboard/tax/reports`, `/dashboard/tax/rules`, `/dashboard/tax/transactions`

### frontend/src/app/dashboard/expenses/page.tsx

- **Route (standalone):** `/dashboard/expenses`
- **Standalone redirected:** YES → /dashboard/hr?tab=expenses
- **Visible via:** `/dashboard/finance?tab=expenses`, `/dashboard/hr?tab=expenses`
- **Broken card count:** 9
- **Broken targets:** `/dashboard/expenses/advances`, `/dashboard/expenses/ai`, `/dashboard/expenses/approval`, `/dashboard/expenses/categories`, `/dashboard/expenses/claims/new`, `/dashboard/expenses/claims`, `/dashboard/expenses/policies`, `/dashboard/expenses/reimbursement`, `/dashboard/expenses/reports`

### frontend/src/app/dashboard/recruitment/page.tsx

- **Route (standalone):** `/dashboard/recruitment`
- **Standalone redirected:** YES → /dashboard/hr?tab=recruitment
- **Visible via:** `/dashboard/hr?tab=recruitment`
- **Broken card count:** 9
- **Broken targets:** `/dashboard/recruitment/ai`, `/dashboard/recruitment/candidates`, `/dashboard/recruitment/interviews`, `/dashboard/recruitment/offers`, `/dashboard/recruitment/pipeline`, `/dashboard/recruitment/reports`, `/dashboard/recruitment/requisitions/new`, `/dashboard/recruitment/requisitions`, `/dashboard/recruitment/stages`

### frontend/src/app/dashboard/ess/page.tsx

- **Route (standalone):** `/dashboard/ess`
- **Standalone redirected:** YES → /dashboard/hr?tab=ess
- **Visible via:** `/dashboard/hr?tab=ess`
- **Broken card count:** 8
- **Broken targets:** `/dashboard/ess/admin`, `/dashboard/ess/ai`, `/dashboard/ess/attendance`, `/dashboard/ess/documents`, `/dashboard/ess/leave`, `/dashboard/ess/notifications`, `/dashboard/ess/profile`, `/dashboard/ess/requests`

### frontend/src/app/dashboard/appraisals/page.tsx

- **Route (standalone):** `/dashboard/appraisals`
- **Standalone redirected:** YES → /dashboard/hr?tab=appraisals
- **Visible via:** `/dashboard/hr?tab=appraisals`
- **Broken card count:** 10
- **Broken targets:** `/dashboard/appraisals/ai`, `/dashboard/appraisals/development-plans`, `/dashboard/appraisals/hr-review`, `/dashboard/appraisals/manager-queue`, `/dashboard/appraisals/periods`, `/dashboard/appraisals/records/new`, `/dashboard/appraisals/records`, `/dashboard/appraisals/reports`, `/dashboard/appraisals/self-review`, `/dashboard/appraisals/templates`

### frontend/src/app/dashboard/training/page.tsx

- **Route (standalone):** `/dashboard/training`
- **Standalone redirected:** YES → /dashboard/hr?tab=training
- **Visible via:** `/dashboard/hr?tab=training`
- **Broken card count:** 8
- **Broken targets:** `/dashboard/training/ai`, `/dashboard/training/assignments`, `/dashboard/training/certifications`, `/dashboard/training/feedback`, `/dashboard/training/programs`, `/dashboard/training/reports`, `/dashboard/training/sessions`, `/dashboard/training/skill-matrix`

### frontend/src/app/dashboard/timesheets/page.tsx

- **Route (standalone):** `/dashboard/timesheets`
- **Standalone redirected:** YES → /dashboard/hr?tab=timesheets
- **Visible via:** `/dashboard/hr?tab=timesheets`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/timesheets/ai`, `/dashboard/timesheets/approval-queue`, `/dashboard/timesheets/my-timesheets`, `/dashboard/timesheets/reports`, `/dashboard/timesheets/time-entry`, `/dashboard/timesheets/weekly-view`

### frontend/src/app/dashboard/price-lists/page.tsx

- **Route (standalone):** `/dashboard/price-lists`
- **Standalone redirected:** YES → /dashboard/sales?tab=price-lists
- **Visible via:** `/dashboard/sales?tab=price-lists`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/price-lists/approval-queue`

### frontend/src/app/dashboard/contracts/page.tsx

- **Route (standalone):** `/dashboard/contracts`
- **Standalone redirected:** YES → /dashboard/sales?tab=contracts
- **Visible via:** `/dashboard/sales?tab=contracts`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/contracts/ai`, `/dashboard/contracts/expiring`, `/dashboard/contracts/list`, `/dashboard/contracts/new`

### frontend/src/app/dashboard/recurring-orders/page.tsx

- **Route (standalone):** `/dashboard/recurring-orders`
- **Standalone redirected:** YES → /dashboard/sales?tab=recurring
- **Visible via:** `/dashboard/sales?tab=recurring`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/recurring-orders/ai`, `/dashboard/recurring-orders/reports`, `/dashboard/recurring-orders/templates/new`, `/dashboard/recurring-orders/templates`

### frontend/src/app/dashboard/commissions/page.tsx

- **Route (standalone):** `/dashboard/commissions`
- **Standalone redirected:** YES → /dashboard/sales?tab=commissions
- **Visible via:** `/dashboard/sales?tab=commissions`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/commissions/ai`, `/dashboard/commissions/payouts`, `/dashboard/commissions/rules`, `/dashboard/commissions/transactions`

### frontend/src/app/dashboard/secondary-sales/page.tsx

- **Route (standalone):** `/dashboard/secondary-sales`
- **Standalone redirected:** YES → /dashboard/sales?tab=secondary
- **Visible via:** `/dashboard/sales?tab=secondary`
- **Broken card count:** 3
- **Broken targets:** `/dashboard/secondary-sales/analysis`, `/dashboard/secondary-sales/inventory`, `/dashboard/secondary-sales/upload`

### frontend/src/app/dashboard/van-sales/page.tsx

- **Route (standalone):** `/dashboard/van-sales`
- **Standalone redirected:** YES → /dashboard/sales?tab=van-sales
- **Visible via:** `/dashboard/sales?tab=van-sales`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/van-sales/ai`, `/dashboard/van-sales/pos`, `/dashboard/van-sales/reconciliation`, `/dashboard/van-sales/route`, `/dashboard/van-sales/stock`, `/dashboard/van-sales/vans/new`, `/dashboard/van-sales/vans`

### frontend/src/app/dashboard/portal/page.tsx

- **Route (standalone):** `/dashboard/portal`
- **Standalone redirected:** YES → /dashboard/sales?tab=portal
- **Visible via:** `/dashboard/sales?tab=portal`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/portal/accounts`, `/dashboard/portal/activity`, `/dashboard/portal/ai`, `/dashboard/portal/claims`, `/dashboard/portal/drafts`, `/dashboard/portal/reports`, `/dashboard/portal/users`

### frontend/src/app/dashboard/procurement-suggestion/page.tsx

- **Route (standalone):** `/dashboard/procurement-suggestion`
- **Standalone redirected:** YES → /dashboard/procurement?tab=suggestions
- **Visible via:** `/dashboard/procurement?tab=suggestions`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/procurement-suggestion/ai`, `/dashboard/procurement-suggestion/groups`, `/dashboard/procurement-suggestion/suggestions`, `/dashboard/procurement-suggestion/supplier-prices`

### frontend/src/app/dashboard/subcontracting/page.tsx

- **Route (standalone):** `/dashboard/subcontracting`
- **Standalone redirected:** YES → /dashboard/procurement?tab=subcontracting
- **Visible via:** `/dashboard/procurement?tab=subcontracting`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/subcontracting/ai`, `/dashboard/subcontracting/locations`, `/dashboard/subcontracting/orders`, `/dashboard/subcontracting/stock`, `/dashboard/subcontracting/yield`

### frontend/src/app/dashboard/landed-cost/page.tsx

- **Route (standalone):** `/dashboard/landed-cost`
- **Standalone redirected:** YES → /dashboard/procurement?tab=landed-cost
- **Visible via:** `/dashboard/procurement?tab=landed-cost`
- **Broken card count:** 3
- **Broken targets:** `/dashboard/landed-cost/ai`, `/dashboard/landed-cost/documents`, `/dashboard/landed-cost/new`

### frontend/src/app/dashboard/qms/page.tsx

- **Route (standalone):** `/dashboard/qms`
- **Standalone redirected:** YES → /dashboard/quality?tab=qms
- **Visible via:** `/dashboard/quality?tab=qms`
- **Broken card count:** 10
- **Broken targets:** `/dashboard/qms/ai`, `/dashboard/qms/allergen`, `/dashboard/qms/ccp`, `/dashboard/qms/corrective-actions`, `/dashboard/qms/deviations`, `/dashboard/qms/haccp`, `/dashboard/qms/inspections`, `/dashboard/qms/quarantine`, `/dashboard/qms/reports`, `/dashboard/qms/templates`

### frontend/src/app/dashboard/allergen/page.tsx

- **Route (standalone):** `/dashboard/allergen`
- **Standalone redirected:** YES → /dashboard/quality?tab=allergen
- **Visible via:** `/dashboard/quality?tab=allergen`
- **Broken card count:** 3
- **Broken targets:** `/dashboard/allergen/change-logs`, `/dashboard/allergen/material-profiles`, `/dashboard/allergen/product-allergens`

### frontend/src/app/dashboard/fleet/page.tsx

- **Route (standalone):** `/dashboard/fleet`
- **Standalone redirected:** YES → /dashboard/logistics?tab=fleet
- **Visible via:** `/dashboard/logistics?tab=fleet`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/fleet/drivers`, `/dashboard/fleet/fuel`, `/dashboard/fleet/incidents`, `/dashboard/fleet/maintenance`, `/dashboard/fleet/reports`, `/dashboard/fleet/trips`, `/dashboard/fleet/vehicles`

### frontend/src/app/dashboard/chatter/page.tsx

- **Route (standalone):** `/dashboard/chatter`
- **Standalone redirected:** YES → /dashboard/communication?tab=chatter
- **Visible via:** `/dashboard/communication?tab=chatter`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/chatter/ai`, `/dashboard/chatter/feed`, `/dashboard/chatter/reports`, `/dashboard/chatter/search`

### frontend/src/app/dashboard/calendar/page.tsx

- **Route (standalone):** `/dashboard/calendar`
- **Standalone redirected:** YES → /dashboard/communication?tab=calendar
- **Visible via:** `/dashboard/communication?tab=calendar`
- **Broken card count:** 4
- **Broken targets:** `/dashboard/calendar/availability`, `/dashboard/calendar/new-event`, `/dashboard/calendar/resources`, `/dashboard/calendar/view`

### frontend/src/app/dashboard/notification-center/page.tsx

- **Route (standalone):** `/dashboard/notification-center`
- **Standalone redirected:** YES → /dashboard/communication?tab=notifications
- **Visible via:** `/dashboard/communication?tab=notifications`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/notification-center/ai`, `/dashboard/notification-center/list`, `/dashboard/notification-center/preferences`, `/dashboard/notification-center/reports`, `/dashboard/notification-center/schedules`, `/dashboard/notification-center/templates`

### frontend/src/app/dashboard/reports/page.tsx

- **Route (standalone):** `/dashboard/reports`
- **Standalone redirected:** YES → /dashboard/analytics?tab=reports
- **Visible via:** `/dashboard/analytics?tab=reports`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/reports/finance`, `/dashboard/reports/inventory`, `/dashboard/reports/marketing`, `/dashboard/reports/payments`, `/dashboard/reports/procurement`, `/dashboard/reports/production`, `/dashboard/reports/sales`

### frontend/src/app/dashboard/report-builder/page.tsx

- **Route (standalone):** `/dashboard/report-builder`
- **Standalone redirected:** YES → /dashboard/analytics?tab=report-builder
- **Visible via:** `/dashboard/analytics?tab=report-builder`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/report-builder/ai`, `/dashboard/report-builder/builder`, `/dashboard/report-builder/catalog`, `/dashboard/report-builder/dashboards`, `/dashboard/report-builder/saved`, `/dashboard/report-builder/schedules`, `/dashboard/report-builder/viewer`

### frontend/src/app/dashboard/custom-fields/page.tsx

- **Route (standalone):** `/dashboard/custom-fields`
- **Standalone redirected:** YES → /dashboard/admin?tab=custom-fields
- **Visible via:** `/dashboard/admin?tab=custom-fields`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/custom-fields/ai`, `/dashboard/custom-fields/fields`, `/dashboard/custom-fields/form-builder`, `/dashboard/custom-fields/new-field`, `/dashboard/custom-fields/values`, `/dashboard/custom-fields/workflow-rules`

### frontend/src/app/dashboard/mobile/page.tsx

- **Route (standalone):** `/dashboard/mobile`
- **Standalone redirected:** YES → /dashboard/admin?tab=mobile
- **Visible via:** `/dashboard/admin?tab=mobile`
- **Broken card count:** 2
- **Broken targets:** `/dashboard/mobile/approvals`, `/dashboard/mobile/devices`

### frontend/src/app/dashboard/marketing/campaigns/page.tsx

- **Route (standalone):** `/dashboard/marketing/campaigns`
- **Standalone redirected:** YES → /dashboard/marketing?tab=campaigns
- **Visible via:** `/dashboard/marketing?tab=campaigns`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/campaigns/new`

### frontend/src/app/dashboard/marketing/promotions/page.tsx

- **Route (standalone):** `/dashboard/marketing/promotions`
- **Standalone redirected:** YES → /dashboard/marketing?tab=promotions
- **Visible via:** `/dashboard/marketing?tab=promotions`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/promotions/new`

### frontend/src/app/dashboard/marketing/trade-spend/page.tsx

- **Route (standalone):** `/dashboard/marketing/trade-spend`
- **Standalone redirected:** YES → /dashboard/marketing?tab=trade-spend
- **Visible via:** `/dashboard/marketing?tab=trade-spend`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/trade-spend/new`

### frontend/src/app/dashboard/marketing/ads/page.tsx

- **Route (standalone):** `/dashboard/marketing/ads`
- **Standalone redirected:** YES → /dashboard/marketing?tab=ads
- **Visible via:** `/dashboard/marketing?tab=ads`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/ads/new`

### frontend/src/app/dashboard/marketing/social-media/page.tsx

- **Route (standalone):** `/dashboard/marketing/social-media`
- **Standalone redirected:** YES → /dashboard/marketing?tab=social-media
- **Visible via:** `/dashboard/marketing?tab=social-media`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/social-media/new`

### frontend/src/app/dashboard/marketing/segments/page.tsx

- **Route (standalone):** `/dashboard/marketing/segments`
- **Standalone redirected:** YES → /dashboard/marketing?tab=segments
- **Visible via:** `/dashboard/marketing?tab=segments`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/segments/new`

### frontend/src/app/dashboard/marketing/influencers/page.tsx

- **Route (standalone):** `/dashboard/marketing/influencers`
- **Standalone redirected:** YES → /dashboard/marketing?tab=influencers
- **Visible via:** `/dashboard/marketing?tab=influencers`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/influencers/new`

### frontend/src/app/dashboard/marketing/visits/page.tsx

- **Route (standalone):** `/dashboard/marketing/visits`
- **Standalone redirected:** YES → /dashboard/marketing?tab=visits
- **Visible via:** `/dashboard/marketing?tab=visits`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/visits/new`

### frontend/src/app/dashboard/marketing/brand-spend/page.tsx

- **Route (standalone):** `/dashboard/marketing/brand-spend`
- **Standalone redirected:** YES → /dashboard/marketing?tab=brand-spend
- **Visible via:** `/dashboard/marketing?tab=brand-spend`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/marketing/brand-spend/new`

### frontend/src/app/dashboard/tpm/page.tsx

- **Route (standalone):** `/dashboard/tpm`
- **Standalone redirected:** YES → /dashboard/marketing?tab=tpm
- **Visible via:** `/dashboard/marketing?tab=tpm`
- **Broken card count:** 10
- **Broken targets:** `/dashboard/tpm/ai`, `/dashboard/tpm/budget`, `/dashboard/tpm/calendar`, `/dashboard/tpm/claims`, `/dashboard/tpm/plans/new`, `/dashboard/tpm/plans`, `/dashboard/tpm/promotions/new`, `/dashboard/tpm/promotions`, `/dashboard/tpm/roi`, `/dashboard/tpm/settlement`

### frontend/src/app/dashboard/surveys/page.tsx

- **Route (standalone):** `/dashboard/surveys`
- **Standalone redirected:** YES → /dashboard/crm?tab=surveys
- **Visible via:** `/dashboard/crm?tab=surveys`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/surveys/new`

### frontend/src/app/dashboard/documents/compliance/page.tsx

- **Route (standalone):** `/dashboard/documents/compliance`
- **Standalone redirected:** NO
- **Visible via:** `/dashboard/documents?tab=compliance`
- **Broken card count:** 1
- **Broken targets:** `/dashboard/documents/new`

### frontend/src/app/dashboard/knowledge-base/page.tsx

- **Route (standalone):** `/dashboard/knowledge-base`
- **Standalone redirected:** YES → /dashboard/documents?tab=knowledge-base
- **Visible via:** `/dashboard/documents?tab=knowledge-base`
- **Broken card count:** 2
- **Broken targets:** `/dashboard/knowledge-base/articles/new`, `/dashboard/knowledge-base/articles`

### frontend/src/app/dashboard/webhooks/page.tsx

- **Route (standalone):** `/dashboard/webhooks`
- **Standalone redirected:** YES → /dashboard/integrations?tab=webhooks
- **Visible via:** `/dashboard/integrations?tab=webhooks`
- **Broken card count:** 6
- **Broken targets:** `/dashboard/webhooks/dead-letter`, `/dashboard/webhooks/definitions`, `/dashboard/webhooks/deliveries`, `/dashboard/webhooks/inbound`, `/dashboard/webhooks/reports`, `/dashboard/webhooks/subscriptions`

### frontend/src/app/dashboard/developer/page.tsx

- **Route (standalone):** `/dashboard/developer`
- **Standalone redirected:** YES → /dashboard/integrations?tab=developer
- **Visible via:** `/dashboard/integrations?tab=developer`
- **Broken card count:** 2
- **Broken targets:** `/dashboard/developer/graphql`, `/dashboard/developer/keys`

### frontend/src/app/dashboard/utility-management/kpi-center/page.tsx

- **Route (standalone):** `/dashboard/utility-management/kpi-center`
- **Standalone redirected:** YES → /dashboard/utility-management?tab=kpi-center
- **Visible via:** `/dashboard/utility-management?tab=kpi-center`
- **Broken card count:** 10
- **Broken targets:** `/dashboard/utility-management/kpi-center/boiler`, `/dashboard/utility-management/kpi-center/chemicals`, `/dashboard/utility-management/kpi-center/compressor`, `/dashboard/utility-management/kpi-center/electricity`, `/dashboard/utility-management/kpi-center/machine-utility`, `/dashboard/utility-management/kpi-center/soft-water`, `/dashboard/utility-management/kpi-center/solar`, `/dashboard/utility-management/kpi-center/utility-cost`, `/dashboard/utility-management/kpi-center/wastewater`, `/dashboard/utility-management/kpi-center/water`

### frontend/src/app/dashboard/utility-management/reports/page.tsx

- **Route (standalone):** `/dashboard/utility-management/reports`
- **Standalone redirected:** YES → /dashboard/utility-management?tab=reports
- **Visible via:** `/dashboard/utility-management?tab=reports`
- **Broken card count:** 7
- **Broken targets:** `/dashboard/utility-management/reports/anomalies`, `/dashboard/utility-management/reports/cost-allocation`, `/dashboard/utility-management/reports/daily-consumption`, `/dashboard/utility-management/reports/equipment-efficiency`, `/dashboard/utility-management/reports/load-analysis`, `/dashboard/utility-management/reports/sustainability`, `/dashboard/utility-management/reports/treatment`

### frontend/src/app/dashboard/esg/page.tsx

- **Route (standalone):** `/dashboard/esg`
- **Standalone redirected:** YES → /dashboard/utility-management?tab=esg
- **Visible via:** `/dashboard/utility-management?tab=esg`
- **Broken card count:** 5
- **Broken targets:** `/dashboard/esg/activities`, `/dashboard/esg/factors`, `/dashboard/esg/intelligence`, `/dashboard/esg/reports`, `/dashboard/esg/targets`

