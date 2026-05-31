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
| Pages with middleware-redirected standalone routes | 66 |

## Import Map (Redirect-Stub Pages That Are Still User-Visible)

| Imported Page | Standalone Route | Redirected To | Visible As Tab |
|--------------|-----------------|---------------|----------------|
| `permissions/page.tsx` | `/dashboard/permissions` | `/dashboard/admin?tab=permissions` | `/dashboard/admin` |
| `companies/page.tsx` | `/dashboard/companies` | `/dashboard/admin?tab=companies` | `/dashboard/admin` |
| `security/page.tsx` | `/dashboard/security` | `/dashboard/admin?tab=security` | `/dashboard/admin` |
| `approvals/page.tsx` | `/dashboard/approvals` | `/dashboard/admin?tab=approvals` | `/dashboard/admin` |
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
| `esign/page.tsx` | `/dashboard/esign` | `/dashboard/documents?tab=esign` | `/dashboard/documents` |
| `finance/accounting/page.tsx` | `/dashboard/finance/accounting` | `/dashboard/finance?tab=accounting` | `/dashboard/finance` |
| `fixed-assets/page.tsx` | `/dashboard/fixed-assets` | `/dashboard/finance?tab=fixed-assets` | `/dashboard/finance` |
| `dimensions/page.tsx` | `/dashboard/dimensions` | `/dashboard/finance?tab=dimensions` | `/dashboard/finance` |
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
| `logistics/containers/page.tsx` | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` | `/dashboard/logistics` |
| `fleet/page.tsx` | `/dashboard/fleet` | `/dashboard/logistics?tab=fleet` | `/dashboard/logistics` |
| `marketing/ecommerce/page.tsx` | `/dashboard/marketing/ecommerce` | `/dashboard/marketing?tab=ecommerce` | `/dashboard/marketing` |
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
| `machine-ops/page.tsx` | `/dashboard/machine-ops` | `/dashboard/production?tab=machine-ops` | `/dashboard/production` |
| `material-flow/page.tsx` | `/dashboard/material-flow` | `/dashboard/production?tab=material-flow` | `/dashboard/production` |
| `quality/consumer-complaints/page.tsx` | `/dashboard/quality/consumer-complaints` | `/dashboard/quality?tab=consumer-complaints` | `/dashboard/quality` |
| `qms/page.tsx` | `/dashboard/qms` | `/dashboard/quality?tab=qms` | `/dashboard/quality` |
| `allergen/page.tsx` | `/dashboard/allergen` | `/dashboard/quality?tab=allergen` | `/dashboard/quality` |
| `dynamic-pricing/page.tsx` | `/dashboard/dynamic-pricing` | `/dashboard/sales?tab=dynamic-pricing` | `/dashboard/sales` |
| `commissions/page.tsx` | `/dashboard/commissions` | `/dashboard/sales?tab=commissions` | `/dashboard/sales` |
| `utility-management/kpi-center/page.tsx` | `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management?tab=kpi-center` | `/dashboard/utility-management` |
| `utility-management/reports/page.tsx` | `/dashboard/utility-management/reports` | `/dashboard/utility-management?tab=reports` | `/dashboard/utility-management` |
| `iot/page.tsx` | `/dashboard/iot` | `/dashboard/utility-management?tab=iot` | `/dashboard/utility-management` |
| `esg/page.tsx` | `/dashboard/esg` | `/dashboard/utility-management?tab=esg` | `/dashboard/utility-management` |
| `wms/page.tsx` | `/dashboard/wms` | `/dashboard/warehouses?tab=wms` | `/dashboard/warehouses` |
