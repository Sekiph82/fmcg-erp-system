# Route Redirect Report

Generated: 2026-05-18

## Summary

| Check | Count |
|-------|-------|
| routeRedirectMap top-level keys | 88 |
| middleware redirect keys        | 116 |
| In routeRedirectMap NOT middleware | 0 |
| In middleware NOT routeRedirectMap | 0 |
| Duplicate keys in routeRedirectMap | 0 |
| Duplicate keys in middleware        | 0 |
| Redirect loops                      | 0 |
| Missing redirect targets            | 0 |
| Intra-workspace routes not in MW    | 0 |
| **Total issues**                    | **0** |

## All checks passed

routeRedirectMap.ts and middleware.ts are in sync. No issues found.

## Full Middleware Redirect Table

| Source | Target | Tab |
|--------|--------|-----|
| `/dashboard/allergen` | `/dashboard/quality` | allergen |
| `/dashboard/appraisals` | `/dashboard/hr` | appraisals |
| `/dashboard/approvals` | `/dashboard/admin` | approvals |
| `/dashboard/bank-api` | `/dashboard/finance` | bank-api |
| `/dashboard/bank-reconciliation` | `/dashboard/finance` | bank-recon |
| `/dashboard/brand-assets` | `/dashboard/quality` | brand-assets |
| `/dashboard/calendar` | `/dashboard/communication` | calendar |
| `/dashboard/calls` | `/dashboard/communication` | calls |
| `/dashboard/chatter` | `/dashboard/communication` | chatter |
| `/dashboard/commissions` | `/dashboard/sales` | commissions |
| `/dashboard/companies` | `/dashboard/admin` | companies |
| `/dashboard/containers` | `/dashboard/logistics` | containers |
| `/dashboard/contracts` | `/dashboard/sales` | contracts |
| `/dashboard/copacking` | `/dashboard/procurement` | subcontracting |
| `/dashboard/crm/ai` | `/dashboard/crm` | overview |
| `/dashboard/crm/overdue` | `/dashboard/crm` | pipeline |
| `/dashboard/crm/qualify` | `/dashboard/crm` | leads |
| `/dashboard/crm/records` | `/dashboard/crm` | overview |
| `/dashboard/custom-fields` | `/dashboard/admin` | custom-fields |
| `/dashboard/cycle-count` | `/dashboard/inventory` | cycle-count |
| `/dashboard/developer` | `/dashboard/integrations` | developer |
| `/dashboard/dimensions` | `/dashboard/finance` | dimensions |
| `/dashboard/documents/new` | `/dashboard/documents` | — |
| `/dashboard/dunning` | `/dashboard/finance` | dunning |
| `/dashboard/dynamic-pricing` | `/dashboard/sales` | dynamic-pricing |
| `/dashboard/email` | `/dashboard/communication` | email |
| `/dashboard/esg` | `/dashboard/utility-management` | esg |
| `/dashboard/esign` | `/dashboard/documents` | esign |
| `/dashboard/ess` | `/dashboard/hr` | ess |
| `/dashboard/expenses` | `/dashboard/hr` | expenses |
| `/dashboard/finance/accounting` | `/dashboard/finance` | accounting |
| `/dashboard/fixed-assets` | `/dashboard/finance` | fixed-assets |
| `/dashboard/fleet` | `/dashboard/logistics` | fleet |
| `/dashboard/gs1` | `/dashboard/compliance` | gs1 |
| `/dashboard/import-history` | `/dashboard/admin` | import-history |
| `/dashboard/invoice-match` | `/dashboard/finance` | invoice-match |
| `/dashboard/iot` | `/dashboard/utility-management` | iot |
| `/dashboard/kanban` | `/dashboard/planning` | kanban |
| `/dashboard/knowledge-base` | `/dashboard/documents` | knowledge-base |
| `/dashboard/landed-cost` | `/dashboard/procurement` | landed-cost |
| `/dashboard/logistics/containers` | `/dashboard/logistics` | containers |
| `/dashboard/logs` | `/dashboard/admin` | logs |
| `/dashboard/loyalty` | `/dashboard/crm` | loyalty |
| `/dashboard/machine-ops` | `/dashboard/production` | machine-ops |
| `/dashboard/market-intelligence` | `/dashboard/marketing` | market-intel |
| `/dashboard/marketing/ads` | `/dashboard/marketing` | ads |
| `/dashboard/marketing/ai-optimizer` | `/dashboard/marketing` | analytics |
| `/dashboard/marketing/brand-spend` | `/dashboard/marketing` | brand-spend |
| `/dashboard/marketing/campaigns` | `/dashboard/marketing` | campaigns |
| `/dashboard/marketing/crm` | `/dashboard/marketing` | overview |
| `/dashboard/marketing/ecommerce` | `/dashboard/marketing` | ecommerce |
| `/dashboard/marketing/influencers` | `/dashboard/marketing` | influencers |
| `/dashboard/marketing/promotions` | `/dashboard/marketing` | promotions |
| `/dashboard/marketing/segments` | `/dashboard/marketing` | segments |
| `/dashboard/marketing/social-media` | `/dashboard/marketing` | social-media |
| `/dashboard/marketing/surveys` | `/dashboard/marketing` | overview |
| `/dashboard/marketing/trade-spend` | `/dashboard/marketing` | trade-spend |
| `/dashboard/marketing/visits` | `/dashboard/marketing` | visits |
| `/dashboard/material-flow` | `/dashboard/production` | material-flow |
| `/dashboard/meetings` | `/dashboard/communication` | meetings |
| `/dashboard/messages` | `/dashboard/communication` | messages |
| `/dashboard/mobile` | `/dashboard/admin` | mobile |
| `/dashboard/movements` | `/dashboard/inventory` | movements |
| `/dashboard/mps` | `/dashboard/planning` | mps |
| `/dashboard/mrp` | `/dashboard/planning` | mrp |
| `/dashboard/notification-center` | `/dashboard/communication` | notifications |
| `/dashboard/nps` | `/dashboard/crm` | nps |
| `/dashboard/payroll` | `/dashboard/hr` | payroll |
| `/dashboard/permissions` | `/dashboard/admin` | permissions |
| `/dashboard/planning/bottlenecks` | `/dashboard/planning` | advanced |
| `/dashboard/planning/capacity` | `/dashboard/planning` | advanced |
| `/dashboard/planning/changeover` | `/dashboard/planning` | advanced |
| `/dashboard/planning/schedule` | `/dashboard/planning` | advanced |
| `/dashboard/planning/simulation` | `/dashboard/planning` | advanced |
| `/dashboard/portal` | `/dashboard/sales` | portal |
| `/dashboard/price-lists` | `/dashboard/sales` | price-lists |
| `/dashboard/procurement-suggestion` | `/dashboard/procurement` | suggestions |
| `/dashboard/production-execution` | `/dashboard/production` | execution |
| `/dashboard/production/advanced` | `/dashboard/production` | scheduling |
| `/dashboard/production/ai` | `/dashboard/production` | plans |
| `/dashboard/production/orders` | `/dashboard/production` | orders |
| `/dashboard/production/plans` | `/dashboard/production` | plans |
| `/dashboard/production/shifts` | `/dashboard/production` | scheduling |
| `/dashboard/production/work-orders` | `/dashboard/production` | orders |
| `/dashboard/projects` | `/dashboard/production` | projects |
| `/dashboard/promotions` | `/dashboard/marketing` | promotions-schemes |
| `/dashboard/putaway` | `/dashboard/warehouses` | wms |
| `/dashboard/qms` | `/dashboard/quality` | qms |
| `/dashboard/quality/consumer-complaints` | `/dashboard/quality` | consumer-complaints |
| `/dashboard/recruitment` | `/dashboard/hr` | recruitment |
| `/dashboard/recurring-orders` | `/dashboard/sales` | recurring |
| `/dashboard/report-builder` | `/dashboard/analytics` | report-builder |
| `/dashboard/reports` | `/dashboard/analytics` | reports |
| `/dashboard/roles` | `/dashboard/admin` | roles |
| `/dashboard/sales/customer-statement` | `/dashboard/sales` | customers |
| `/dashboard/sales/pod` | `/dashboard/sales` | delivery |
| `/dashboard/secondary-sales` | `/dashboard/sales` | secondary |
| `/dashboard/security` | `/dashboard/admin` | security |
| `/dashboard/shelf-life` | `/dashboard/inventory` | shelf-life |
| `/dashboard/subcontracting` | `/dashboard/procurement` | subcontracting |
| `/dashboard/supplier-portal` | `/dashboard/procurement` | supplier-portal |
| `/dashboard/surveys` | `/dashboard/crm` | surveys |
| `/dashboard/tax` | `/dashboard/finance` | tax |
| `/dashboard/timesheets` | `/dashboard/hr` | timesheets |
| `/dashboard/tpm` | `/dashboard/marketing` | tpm |
| `/dashboard/traceability` | `/dashboard/inventory` | traceability |
| `/dashboard/training` | `/dashboard/hr` | training |
| `/dashboard/users` | `/dashboard/admin` | users |
| `/dashboard/utilities` | `/dashboard/admin` | system-config |
| `/dashboard/utility-management/categories` | `/dashboard/utility-management` | assets |
| `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management` | kpi-center |
| `/dashboard/utility-management/reports` | `/dashboard/utility-management` | reports |
| `/dashboard/van-sales` | `/dashboard/sales` | van-sales |
| `/dashboard/webhooks` | `/dashboard/integrations` | webhooks |
| `/dashboard/whatsapp` | `/dashboard/communication` | whatsapp |
| `/dashboard/wms` | `/dashboard/warehouses` | wms |