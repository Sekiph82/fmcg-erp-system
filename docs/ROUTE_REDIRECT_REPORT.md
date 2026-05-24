# Route Redirect Report

Generated: 2026-05-24

## Summary

| Check | Count |
|-------|-------|
| routeRedirectMap top-level keys | 84 |
| middleware redirect keys        | 82 |
| In routeRedirectMap NOT middleware | 17 |
| In middleware NOT routeRedirectMap | 0 |
| Duplicate keys in routeRedirectMap | 0 |
| Duplicate keys in middleware        | 0 |
| Redirect loops                      | 0 |
| Missing redirect targets            | 0 |
| Intra-workspace routes not in MW    | 0 |
| **Total issues**                    | **17** |

## In routeRedirectMap top-level keys but NOT in middleware

These routes are documented in routeRedirectMap.ts but have no middleware redirect.
Users who navigate directly will NOT be redirected.

- `/dashboard/bank-reconciliation` → `/dashboard/finance?tab=bank-recon`
- `/dashboard/contracts` → `/dashboard/sales?tab=contracts`
- `/dashboard/custom-fields` → `/dashboard/admin?tab=custom-fields`
- `/dashboard/dunning` → `/dashboard/finance?tab=dunning`
- `/dashboard/invoice-match` → `/dashboard/finance?tab=invoice-match`
- `/dashboard/knowledge-base` → `/dashboard/documents?tab=knowledge-base`
- `/dashboard/landed-cost` → `/dashboard/procurement?tab=landed-cost`
- `/dashboard/portal` → `/dashboard/sales?tab=portal`
- `/dashboard/price-lists` → `/dashboard/sales?tab=price-lists`
- `/dashboard/production-execution` → `/dashboard/production?tab=execution`
- `/dashboard/projects` → `/dashboard/production?tab=projects`
- `/dashboard/recurring-orders` → `/dashboard/sales?tab=recurring`
- `/dashboard/supplier-portal` → `/dashboard/procurement?tab=supplier-portal`
- `/dashboard/surveys` → `/dashboard/crm?tab=surveys`
- `/dashboard/tpm` → `/dashboard/marketing?tab=tpm`
- `/dashboard/traceability` → `/dashboard/inventory?tab=traceability`
- `/dashboard/van-sales` → `/dashboard/sales?tab=van-sales`

## Full Middleware Redirect Table

| Source | Target | Tab |
|--------|--------|-----|
| `/dashboard/allergen` | `/dashboard/quality` | allergen |
| `/dashboard/appraisals` | `/dashboard/hr` | appraisals |
| `/dashboard/approvals` | `/dashboard/admin` | approvals |
| `/dashboard/bank-api` | `/dashboard/finance` | bank-api |
| `/dashboard/calendar` | `/dashboard/communication` | calendar |
| `/dashboard/calls` | `/dashboard/communication` | calls |
| `/dashboard/chatter` | `/dashboard/communication` | chatter |
| `/dashboard/commissions` | `/dashboard/sales` | commissions |
| `/dashboard/companies` | `/dashboard/admin` | companies |
| `/dashboard/containers` | `/dashboard/logistics` | containers |
| `/dashboard/copacking` | `/dashboard/procurement` | subcontracting |
| `/dashboard/crm/ai` | `/dashboard/crm` | overview |
| `/dashboard/crm/overdue` | `/dashboard/crm` | pipeline |
| `/dashboard/crm/qualify` | `/dashboard/crm` | leads |
| `/dashboard/cycle-count` | `/dashboard/inventory` | cycle-count |
| `/dashboard/developer` | `/dashboard/integrations` | developer |
| `/dashboard/dimensions` | `/dashboard/finance` | dimensions |
| `/dashboard/documents/new` | `/dashboard/documents` | — |
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
| `/dashboard/iot` | `/dashboard/utility-management` | iot |
| `/dashboard/kanban` | `/dashboard/planning` | kanban |
| `/dashboard/logistics/containers` | `/dashboard/logistics` | containers |
| `/dashboard/logs` | `/dashboard/admin` | logs |
| `/dashboard/loyalty` | `/dashboard/crm` | loyalty |
| `/dashboard/machine-ops` | `/dashboard/production` | machine-ops |
| `/dashboard/market-intelligence` | `/dashboard/marketing` | market-intel |
| `/dashboard/marketing/ai-optimizer` | `/dashboard/marketing` | analytics |
| `/dashboard/marketing/ecommerce` | `/dashboard/marketing` | ecommerce |
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
| `/dashboard/procurement-suggestion` | `/dashboard/procurement` | suggestions |
| `/dashboard/production/advanced` | `/dashboard/production` | scheduling |
| `/dashboard/production/ai` | `/dashboard/production` | plans |
| `/dashboard/production/plans` | `/dashboard/production` | plans |
| `/dashboard/production/shifts` | `/dashboard/production` | scheduling |
| `/dashboard/production/work-orders` | `/dashboard/production` | orders |
| `/dashboard/promotions` | `/dashboard/marketing` | promotions-schemes |
| `/dashboard/putaway` | `/dashboard/warehouses` | wms |
| `/dashboard/qms` | `/dashboard/quality` | qms |
| `/dashboard/quality/consumer-complaints` | `/dashboard/quality` | consumer-complaints |
| `/dashboard/recruitment` | `/dashboard/hr` | recruitment |
| `/dashboard/report-builder` | `/dashboard/analytics` | report-builder |
| `/dashboard/reports` | `/dashboard/analytics` | reports |
| `/dashboard/sales/customer-statement` | `/dashboard/sales` | customers |
| `/dashboard/sales/pod` | `/dashboard/sales` | delivery |
| `/dashboard/security` | `/dashboard/admin` | security |
| `/dashboard/shelf-life` | `/dashboard/inventory` | shelf-life |
| `/dashboard/subcontracting` | `/dashboard/procurement` | subcontracting |
| `/dashboard/tax` | `/dashboard/finance` | tax |
| `/dashboard/timesheets` | `/dashboard/hr` | timesheets |
| `/dashboard/training` | `/dashboard/hr` | training |
| `/dashboard/utilities` | `/dashboard/admin` | system-config |
| `/dashboard/utility-management/categories` | `/dashboard/utility-management` | assets |
| `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management` | kpi-center |
| `/dashboard/utility-management/reports` | `/dashboard/utility-management` | reports |
| `/dashboard/webhooks` | `/dashboard/integrations` | webhooks |
| `/dashboard/whatsapp` | `/dashboard/communication` | whatsapp |
| `/dashboard/wms` | `/dashboard/warehouses` | wms |