# Visible Import Graph

**Date:** 2026-05-21
**Method:** Dynamic scan of `dynamic(() => import(...))` in all workspace pages, cross-referenced with middleware redirect map.

## Key Insight

A page can be user-visible even if its standalone route is middleware-redirected,
if it is dynamically imported into a workspace tab.

## Summary

| Metric | Count |
|--------|-------|
| Workspace pages with dynamic imports | 26 |
| Total dynamically imported pages found | 220 |
| Pages with middleware-redirected standalone routes | 97 |

## Import Map (Redirect-Stub Pages That Are Still User-Visible)

| Imported Page | Standalone Route | Redirected To | Visible As Tab |
|--------------|-----------------|---------------|----------------|
| `users/page.tsx` | `/dashboard/users` | `/dashboard/admin?tab=users` | `/dashboard/admin` |
| `roles/page.tsx` | `/dashboard/roles` | `/dashboard/admin?tab=roles` | `/dashboard/admin` |
| `permissions/page.tsx` | `/dashboard/permissions` | `/dashboard/admin?tab=permissions` | `/dashboard/admin` |
| `companies/page.tsx` | `/dashboard/companies` | `/dashboard/admin?tab=companies` | `/dashboard/admin` |
| `security/page.tsx` | `/dashboard/security` | `/dashboard/admin?tab=security` | `/dashboard/admin` |
| `approvals/page.tsx` | `/dashboard/approvals` | `/dashboard/admin?tab=approvals` | `/dashboard/admin` |
| `custom-fields/page.tsx` | `/dashboard/custom-fields` | `/dashboard/admin?tab=custom-fields` | `/dashboard/admin` |
| `utilities/page.tsx` | `/dashboard/utilities` | `/dashboard/admin?tab=system-config` | `/dashboard/admin` |
| `mobile/page.tsx` | `/dashboard/mobile` | `/dashboard/admin?tab=mobile` | `/dashboard/admin` |
| `logs/page.tsx` | `/dashboard/logs` | `/dashboard/admin?tab=logs` | `/dashboard/admin` |
| `import-history/page.tsx` | `/dashboard/import-history` | `/dashboard/admin?tab=import-history` | `/dashboard/admin` |
| `reports/page.tsx` | `/dashboard/reports` | `/dashboard/analytics?tab=reports` | `/dashboard/analytics` |
| `report-builder/page.tsx` | `/dashboard/report-builder` | `/dashboard/analytics?tab=report-builder` | `/dashboard/analytics` |
| `chatter/page.tsx` | `/dashboard/chatter` | `/dashboard/communication?tab=chatter` | `/dashboard/communication` |
| `calendar/page.tsx` | `/dashboard/calendar` | `/dashboard/communication?tab=calendar` | `/dashboard/communication` |
| `messages/page.tsx` | `/dashboard/messages` | `/dashboard/communication?tab=messages` | `/dashboard/communication` |
| `email/page.tsx` | `/dashboard/email` | `/dashboard/communication?tab=email` | `/dashboard/communication` |
| `whatsapp/page.tsx` | `/dashboard/whatsapp` | `/dashboard/communication?tab=whatsapp` | `/dashboard/communication` |
| `calls/page.tsx` | `/dashboard/calls` | `/dashboard/communication?tab=calls` | `/dashboard/communication` |
| `meetings/page.tsx` | `/dashboard/meetings` | `/dashboard/communication?tab=meetings` | `/dashboard/communication` |
| `notification-center/page.tsx` | `/dashboard/notification-center` | `/dashboard/communication?tab=notifications` | `/dashboard/communication` |
| `gs1/page.tsx` | `/dashboard/gs1` | `/dashboard/compliance?tab=gs1` | `/dashboard/compliance` |
| `loyalty/page.tsx` | `/dashboard/loyalty` | `/dashboard/crm?tab=loyalty` | `/dashboard/crm` |
| `nps/page.tsx` | `/dashboard/nps` | `/dashboard/crm?tab=nps` | `/dashboard/crm` |
| `surveys/page.tsx` | `/dashboard/surveys` | `/dashboard/crm?tab=surveys` | `/dashboard/crm` |
| `knowledge-base/page.tsx` | `/dashboard/knowledge-base` | `/dashboard/documents?tab=knowledge-base` | `/dashboard/documents` |
| `esign/page.tsx` | `/dashboard/esign` | `/dashboard/documents?tab=esign` | `/dashboard/documents` |
| `finance/accounting/page.tsx` | `/dashboard/finance/accounting` | `/dashboard/finance?tab=accounting` | `/dashboard/finance` |
| `bank-reconciliation/page.tsx` | `/dashboard/bank-reconciliation` | `/dashboard/finance?tab=bank-recon` | `/dashboard/finance` |
| `invoice-match/page.tsx` | `/dashboard/invoice-match` | `/dashboard/finance?tab=invoice-match` | `/dashboard/finance` |
| `fixed-assets/page.tsx` | `/dashboard/fixed-assets` | `/dashboard/finance?tab=fixed-assets` | `/dashboard/finance` |
| `dimensions/page.tsx` | `/dashboard/dimensions` | `/dashboard/finance?tab=dimensions` | `/dashboard/finance` |
| `dunning/page.tsx` | `/dashboard/dunning` | `/dashboard/finance?tab=dunning` | `/dashboard/finance` |
| `tax/page.tsx` | `/dashboard/tax` | `/dashboard/finance?tab=tax` | `/dashboard/finance` |
| `bank-api/page.tsx` | `/dashboard/bank-api` | `/dashboard/finance?tab=bank-api` | `/dashboard/finance` |
| `expenses/page.tsx` | `/dashboard/expenses` | `/dashboard/hr?tab=expenses` | `/dashboard/finance`, `/dashboard/hr` |
| `recruitment/page.tsx` | `/dashboard/recruitment` | `/dashboard/hr?tab=recruitment` | `/dashboard/hr` |
| `ess/page.tsx` | `/dashboard/ess` | `/dashboard/hr?tab=ess` | `/dashboard/hr` |
| `appraisals/page.tsx` | `/dashboard/appraisals` | `/dashboard/hr?tab=appraisals` | `/dashboard/hr` |
| `training/page.tsx` | `/dashboard/training` | `/dashboard/hr?tab=training` | `/dashboard/hr` |
| `timesheets/page.tsx` | `/dashboard/timesheets` | `/dashboard/hr?tab=timesheets` | `/dashboard/hr` |
| `webhooks/page.tsx` | `/dashboard/webhooks` | `/dashboard/integrations?tab=webhooks` | `/dashboard/integrations` |
| `developer/page.tsx` | `/dashboard/developer` | `/dashboard/integrations?tab=developer` | `/dashboard/integrations` |
| `movements/page.tsx` | `/dashboard/movements` | `/dashboard/inventory?tab=movements` | `/dashboard/inventory` |
| `cycle-count/page.tsx` | `/dashboard/cycle-count` | `/dashboard/inventory?tab=cycle-count` | `/dashboard/inventory` |
| `shelf-life/page.tsx` | `/dashboard/shelf-life` | `/dashboard/inventory?tab=shelf-life` | `/dashboard/inventory` |
| `traceability/page.tsx` | `/dashboard/traceability` | `/dashboard/inventory?tab=traceability` | `/dashboard/inventory` |
| `logistics/containers/page.tsx` | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` | `/dashboard/logistics` |
| `fleet/page.tsx` | `/dashboard/fleet` | `/dashboard/logistics?tab=fleet` | `/dashboard/logistics` |
| `marketing/campaigns/page.tsx` | `/dashboard/marketing/campaigns` | `/dashboard/marketing?tab=campaigns` | `/dashboard/marketing` |
| `marketing/promotions/page.tsx` | `/dashboard/marketing/promotions` | `/dashboard/marketing?tab=promotions` | `/dashboard/marketing` |
| `marketing/trade-spend/page.tsx` | `/dashboard/marketing/trade-spend` | `/dashboard/marketing?tab=trade-spend` | `/dashboard/marketing` |
| `marketing/ads/page.tsx` | `/dashboard/marketing/ads` | `/dashboard/marketing?tab=ads` | `/dashboard/marketing` |
| `marketing/social-media/page.tsx` | `/dashboard/marketing/social-media` | `/dashboard/marketing?tab=social-media` | `/dashboard/marketing` |
| `marketing/segments/page.tsx` | `/dashboard/marketing/segments` | `/dashboard/marketing?tab=segments` | `/dashboard/marketing` |
| `marketing/influencers/page.tsx` | `/dashboard/marketing/influencers` | `/dashboard/marketing?tab=influencers` | `/dashboard/marketing` |
| `marketing/ecommerce/page.tsx` | `/dashboard/marketing/ecommerce` | `/dashboard/marketing?tab=ecommerce` | `/dashboard/marketing` |
| `marketing/visits/page.tsx` | `/dashboard/marketing/visits` | `/dashboard/marketing?tab=visits` | `/dashboard/marketing` |
| `marketing/brand-spend/page.tsx` | `/dashboard/marketing/brand-spend` | `/dashboard/marketing?tab=brand-spend` | `/dashboard/marketing` |
| `tpm/page.tsx` | `/dashboard/tpm` | `/dashboard/marketing?tab=tpm` | `/dashboard/marketing` |
| `market-intelligence/page.tsx` | `/dashboard/market-intelligence` | `/dashboard/marketing?tab=market-intel` | `/dashboard/marketing` |
| `payroll/profiles/page.tsx` | `/dashboard/payroll/profiles` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` |
| `payroll/reports/page.tsx` | `/dashboard/payroll/reports` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` |
| `planning/schedule/page.tsx` | `/dashboard/planning/schedule` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` |
| `planning/capacity/page.tsx` | `/dashboard/planning/capacity` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` |
| `planning/simulation/page.tsx` | `/dashboard/planning/simulation` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` |
| `planning/bottlenecks/page.tsx` | `/dashboard/planning/bottlenecks` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` |
| `planning/changeover/page.tsx` | `/dashboard/planning/changeover` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` |
| `mrp/page.tsx` | `/dashboard/mrp` | `/dashboard/planning?tab=mrp` | `/dashboard/planning` |
| `mps/page.tsx` | `/dashboard/mps` | `/dashboard/planning?tab=mps` | `/dashboard/planning` |
| `kanban/page.tsx` | `/dashboard/kanban` | `/dashboard/planning?tab=kanban` | `/dashboard/planning` |
| `procurement-suggestion/page.tsx` | `/dashboard/procurement-suggestion` | `/dashboard/procurement?tab=suggestions` | `/dashboard/procurement` |
| `subcontracting/page.tsx` | `/dashboard/subcontracting` | `/dashboard/procurement?tab=subcontracting` | `/dashboard/procurement` |
| `landed-cost/page.tsx` | `/dashboard/landed-cost` | `/dashboard/procurement?tab=landed-cost` | `/dashboard/procurement` |
| `supplier-portal/page.tsx` | `/dashboard/supplier-portal` | `/dashboard/procurement?tab=supplier-portal` | `/dashboard/procurement` |
| `production/orders/page.tsx` | `/dashboard/production/orders` | `/dashboard/production?tab=orders` | `/dashboard/production` |
| `production-execution/page.tsx` | `/dashboard/production-execution` | `/dashboard/production?tab=execution` | `/dashboard/production` |
| `machine-ops/page.tsx` | `/dashboard/machine-ops` | `/dashboard/production?tab=machine-ops` | `/dashboard/production` |
| `material-flow/page.tsx` | `/dashboard/material-flow` | `/dashboard/production?tab=material-flow` | `/dashboard/production` |
| `projects/page.tsx` | `/dashboard/projects` | `/dashboard/production?tab=projects` | `/dashboard/production` |
| `quality/consumer-complaints/page.tsx` | `/dashboard/quality/consumer-complaints` | `/dashboard/quality?tab=consumer-complaints` | `/dashboard/quality` |
| `qms/page.tsx` | `/dashboard/qms` | `/dashboard/quality?tab=qms` | `/dashboard/quality` |
| `allergen/page.tsx` | `/dashboard/allergen` | `/dashboard/quality?tab=allergen` | `/dashboard/quality` |
| `brand-assets/page.tsx` | `/dashboard/brand-assets` | `/dashboard/quality?tab=brand-assets` | `/dashboard/quality` |
| `price-lists/page.tsx` | `/dashboard/price-lists` | `/dashboard/sales?tab=price-lists` | `/dashboard/sales` |
| `dynamic-pricing/page.tsx` | `/dashboard/dynamic-pricing` | `/dashboard/sales?tab=dynamic-pricing` | `/dashboard/sales` |
| `contracts/page.tsx` | `/dashboard/contracts` | `/dashboard/sales?tab=contracts` | `/dashboard/sales` |
| `recurring-orders/page.tsx` | `/dashboard/recurring-orders` | `/dashboard/sales?tab=recurring` | `/dashboard/sales` |
| `commissions/page.tsx` | `/dashboard/commissions` | `/dashboard/sales?tab=commissions` | `/dashboard/sales` |
| `secondary-sales/page.tsx` | `/dashboard/secondary-sales` | `/dashboard/sales?tab=secondary` | `/dashboard/sales` |
| `van-sales/page.tsx` | `/dashboard/van-sales` | `/dashboard/sales?tab=van-sales` | `/dashboard/sales` |
| `portal/page.tsx` | `/dashboard/portal` | `/dashboard/sales?tab=portal` | `/dashboard/sales` |
| `utility-management/kpi-center/page.tsx` | `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management?tab=kpi-center` | `/dashboard/utility-management` |
| `utility-management/reports/page.tsx` | `/dashboard/utility-management/reports` | `/dashboard/utility-management?tab=reports` | `/dashboard/utility-management` |
| `iot/page.tsx` | `/dashboard/iot` | `/dashboard/utility-management?tab=iot` | `/dashboard/utility-management` |
| `esg/page.tsx` | `/dashboard/esg` | `/dashboard/utility-management?tab=esg` | `/dashboard/utility-management` |
| `wms/page.tsx` | `/dashboard/wms` | `/dashboard/warehouses?tab=wms` | `/dashboard/warehouses` |
