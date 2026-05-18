# Old Route Compatibility

**Date:** 2026-05-18

This chapter documents old URL routes that have been consolidated into workspace tabs. Bookmarks or links using these old URLs will automatically redirect to the correct workspace.

**Do NOT capture screenshots for these old routes.** They redirect immediately — there is no unique content to document. Instead, document the destination workspace and tab.

---

## How Redirects Work

Old routes redirect via Next.js middleware (308 Permanent Redirect). The browser follows the redirect immediately. The user lands on the correct workspace with the correct tab active.

Source: `frontend/src/lib/routeRedirectMap.ts` and `frontend/src/middleware.ts`.

---

## Old Route → New Workspace Mapping

### Sales & Distribution

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/van-sales | /dashboard/sales | tab=van-sales |
| /dashboard/sales/orders/[id] | /dashboard/sales | — |
| /dashboard/portal | /dashboard/sales | tab=portal |
| /dashboard/customers | /dashboard/sales | tab=customers |
| /dashboard/contracts | /dashboard/sales | tab=contracts |
| /dashboard/price-list | /dashboard/sales | tab=price-lists |
| /dashboard/dynamic-pricing | /dashboard/sales | tab=dynamic-pricing |
| /dashboard/commissions | /dashboard/sales | tab=commissions |
| /dashboard/field-sales | /dashboard/sales | tab=field-sales |
| /dashboard/secondary-sales | /dashboard/sales | tab=secondary |
| /dashboard/distributors | /dashboard/sales | tab=distributors |
| /dashboard/returns | /dashboard/sales | tab=returns |
| /dashboard/delivery | /dashboard/logistics | tab=shipments |

### Finance

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/fixed-assets | /dashboard/finance | tab=fixed-assets |
| /dashboard/bank-reconciliation | /dashboard/finance | tab=bank-recon |
| /dashboard/invoice-match | /dashboard/finance | tab=invoice-match |
| /dashboard/tax | /dashboard/finance | tab=tax |
| /dashboard/expenses (finance) | /dashboard/finance | tab=expenses |
| /dashboard/dunning | /dashboard/finance | tab=dunning |
| /dashboard/dimensions | /dashboard/finance | tab=dimensions |
| /dashboard/finance/accounting | /dashboard/finance | — |

### Quality

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/qms | /dashboard/quality | tab=qms |
| /dashboard/allergen | /dashboard/quality | tab=allergen |
| /dashboard/shelf-life | /dashboard/inventory | tab=shelf-life |
| /dashboard/traceability | /dashboard/inventory | tab=traceability |
| /dashboard/consumer-complaints | /dashboard/quality | tab=consumer-complaints |
| /dashboard/gs1 | /dashboard/compliance | tab=gs1 |
| /dashboard/regulatory-certs | /dashboard/compliance | tab=regulatory-certs |

### HR

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/recruitment | /dashboard/hr | tab=recruitment |
| /dashboard/appraisals | /dashboard/hr | tab=appraisals |
| /dashboard/timesheets | /dashboard/hr | tab=timesheets |
| /dashboard/training | /dashboard/hr | tab=training |
| /dashboard/ess | /dashboard/hr | tab=ess |
| /dashboard/payroll/runs/[id] | /dashboard/hr | tab=payroll |

### Production

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/production/orders | /dashboard/production | — |
| /dashboard/production/orders/[id] | /dashboard/production | — |
| /dashboard/production/costing | /dashboard/production | tab=costing |
| /dashboard/copacking | /dashboard/production | — |
| /dashboard/mrp | /dashboard/planning | tab=mrp |
| /dashboard/mps | /dashboard/planning | tab=mps |
| /dashboard/planning/schedule | /dashboard/planning | tab=schedule |

### Inventory

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/cycle-count | /dashboard/inventory | tab=cycle-count |
| /dashboard/serial-tracking | /dashboard/inventory | tab=serials |
| /dashboard/inventory/stock | /dashboard/inventory | tab=stock |
| /dashboard/inventory/movements | /dashboard/inventory | tab=movements |
| /dashboard/wms (picking) | /dashboard/warehouses | tab=wms |

### Procurement

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/procurement/orders/[id] | /dashboard/procurement | — |
| /dashboard/procurement/purchase-orders | /dashboard/procurement | tab=orders |
| /dashboard/procurement/rfq | /dashboard/procurement | tab=rfq |
| /dashboard/subcontracting | /dashboard/procurement | tab=subcontracting |
| /dashboard/landed-cost | /dashboard/procurement | tab=landed-cost |
| /dashboard/supplier-portal | /dashboard/procurement | tab=supplier-portal |

### Admin

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/users | /dashboard/admin | tab=users |
| /dashboard/users/[id] | /dashboard/admin | tab=users |
| /dashboard/roles | /dashboard/admin | tab=roles |
| /dashboard/audit-logs | /dashboard/admin | tab=logs |
| /dashboard/company | /dashboard/admin | tab=companies |
| /dashboard/custom-fields | /dashboard/admin | tab=custom-fields |
| /dashboard/approvals (admin) | /dashboard/admin | tab=approvals |

### Analytics & Reports

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/reports | /dashboard/analytics | tab=reports |
| /dashboard/report-builder | /dashboard/analytics | tab=report-builder |
| /dashboard/market-intelligence | /dashboard/marketing | tab=market-intel |

### CRM & Marketing

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/crm/records/[id] | /dashboard/crm | — |
| /dashboard/loyalty | /dashboard/crm | tab=loyalty |
| /dashboard/nps | /dashboard/crm | tab=nps |
| /dashboard/surveys | /dashboard/crm | tab=surveys |
| /dashboard/promotions | /dashboard/marketing | tab=promotions-schemes |
| /dashboard/tpm | /dashboard/marketing | tab=tpm |
| /dashboard/brand-assets | /dashboard/quality | tab=brand-assets |

### Finance (Additional)

| Old Route | Redirects To | Tab |
|---|---|---|
| /dashboard/payroll-ke | /dashboard/payroll | — |
| /dashboard/knowledge-base | /dashboard/documents | tab=knowledge-base |
| /dashboard/esign | /dashboard/documents | tab=esign |
| /dashboard/meetings | /dashboard/communication | tab=meetings |
| /dashboard/calendar | /dashboard/communication | tab=calendar |
| /dashboard/whatsapp | /dashboard/communication | tab=whatsapp |

---

## Notes for Manual Authors

When writing manual text about an old route:

> "If you previously bookmarked `/dashboard/van-sales`, it now automatically redirects to the Sales workspace Van Sales tab (`/dashboard/sales?tab=van-sales`). Update your bookmark."

Do NOT create a manual chapter for an old redirect-only route. Link to the destination workspace chapter instead.
