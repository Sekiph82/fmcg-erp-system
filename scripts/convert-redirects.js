/**
 * Converts FULL_DUPLICATE_UI pages to redirect-only pages.
 * Run: node scripts/convert-redirects.js
 */
const fs = require("fs");
const path = require("path");

const APP = path.join(__dirname, "../frontend/src/app/dashboard");

/**
 * Static redirect: no params
 */
function staticRedirect(target) {
  return `import { redirect } from "next/navigation";

export default function Page() {
  redirect("${target}");
}
`;
}

/**
 * Dynamic redirect: one [id] param
 */
function dynamicRedirect(target, paramName = "id") {
  return `import { redirect } from "next/navigation";

export default function Page({ params }: { params: { ${paramName}: string } }) {
  redirect(\`${target.replace("{id}", `\${encodeURIComponent(params.${paramName})}`)}\`);
}
`;
}

const redirects = [
  // ── Marketing ──────────────────────────────────────────────────────────────
  // ads
  { file: "marketing/ads/[id]/page.tsx",         content: dynamicRedirect("/dashboard/marketing?tab=ads&id={id}&drawer=detail") },
  { file: "marketing/ads/new/page.tsx",           content: staticRedirect("/dashboard/marketing?tab=ads&drawer=create") },
  // ai-optimizer
  { file: "marketing/ai-optimizer/page.tsx",      content: staticRedirect("/dashboard/marketing?tab=analytics") },
  // brand-spend
  { file: "marketing/brand-spend/[id]/page.tsx",  content: dynamicRedirect("/dashboard/marketing?tab=brand-spend&id={id}&drawer=detail") },
  { file: "marketing/brand-spend/new/page.tsx",   content: staticRedirect("/dashboard/marketing?tab=brand-spend&drawer=create") },
  // campaigns
  { file: "marketing/campaigns/[id]/page.tsx",    content: dynamicRedirect("/dashboard/marketing?tab=campaigns&id={id}&drawer=detail") },
  { file: "marketing/campaigns/new/page.tsx",     content: staticRedirect("/dashboard/marketing?tab=campaigns&drawer=create") },
  // crm (no crm tab in marketing — use overview)
  { file: "marketing/crm/[id]/page.tsx",          content: dynamicRedirect("/dashboard/marketing?tab=overview&id={id}") },
  { file: "marketing/crm/followup/page.tsx",      content: staticRedirect("/dashboard/marketing?tab=overview") },
  { file: "marketing/crm/page.tsx",               content: staticRedirect("/dashboard/marketing?tab=overview") },
  // ecommerce
  { file: "marketing/ecommerce/analytics/page.tsx",            content: staticRedirect("/dashboard/marketing?tab=ecommerce") },
  { file: "marketing/ecommerce/performance/[id]/page.tsx",     content: dynamicRedirect("/dashboard/marketing?tab=ecommerce&id={id}&drawer=detail") },
  { file: "marketing/ecommerce/performance/new/page.tsx",      content: staticRedirect("/dashboard/marketing?tab=ecommerce&drawer=create") },
  { file: "marketing/ecommerce/performance/page.tsx",          content: staticRedirect("/dashboard/marketing?tab=ecommerce") },
  { file: "marketing/ecommerce/products/[id]/page.tsx",        content: dynamicRedirect("/dashboard/marketing?tab=ecommerce&id={id}&drawer=detail") },
  { file: "marketing/ecommerce/products/new/page.tsx",         content: staticRedirect("/dashboard/marketing?tab=ecommerce&drawer=create") },
  { file: "marketing/ecommerce/products/page.tsx",             content: staticRedirect("/dashboard/marketing?tab=ecommerce") },
  { file: "marketing/ecommerce/returns/page.tsx",              content: staticRedirect("/dashboard/marketing?tab=ecommerce") },
  { file: "marketing/ecommerce/stores/[id]/page.tsx",          content: dynamicRedirect("/dashboard/marketing?tab=ecommerce&id={id}&drawer=detail") },
  { file: "marketing/ecommerce/stores/new/page.tsx",           content: staticRedirect("/dashboard/marketing?tab=ecommerce&drawer=create") },
  { file: "marketing/ecommerce/stores/page.tsx",               content: staticRedirect("/dashboard/marketing?tab=ecommerce") },
  // influencers
  { file: "marketing/influencers/[id]/page.tsx",  content: dynamicRedirect("/dashboard/marketing?tab=influencers&id={id}&drawer=detail") },
  { file: "marketing/influencers/new/page.tsx",   content: staticRedirect("/dashboard/marketing?tab=influencers&drawer=create") },
  // promotions (marketing sub — not the /dashboard/promotions module)
  { file: "marketing/promotions/[id]/page.tsx",   content: dynamicRedirect("/dashboard/marketing?tab=promotions&id={id}&drawer=detail") },
  { file: "marketing/promotions/new/page.tsx",    content: staticRedirect("/dashboard/marketing?tab=promotions&drawer=create") },
  // segments
  { file: "marketing/segments/[id]/page.tsx",     content: dynamicRedirect("/dashboard/marketing?tab=segments&id={id}&drawer=detail") },
  { file: "marketing/segments/new/page.tsx",      content: staticRedirect("/dashboard/marketing?tab=segments&drawer=create") },
  // social-media
  { file: "marketing/social-media/[id]/page.tsx", content: dynamicRedirect("/dashboard/marketing?tab=social-media&id={id}&drawer=detail") },
  { file: "marketing/social-media/new/page.tsx",  content: staticRedirect("/dashboard/marketing?tab=social-media&drawer=create") },
  // surveys (no surveys tab in marketing)
  { file: "marketing/surveys/[id]/page.tsx",      content: dynamicRedirect("/dashboard/marketing?tab=overview&id={id}") },
  { file: "marketing/surveys/new/page.tsx",       content: staticRedirect("/dashboard/marketing?tab=overview&drawer=create") },
  { file: "marketing/surveys/page.tsx",           content: staticRedirect("/dashboard/marketing?tab=overview") },
  // trade-spend
  { file: "marketing/trade-spend/[id]/page.tsx",  content: dynamicRedirect("/dashboard/marketing?tab=trade-spend&id={id}&drawer=detail") },
  { file: "marketing/trade-spend/new/page.tsx",   content: staticRedirect("/dashboard/marketing?tab=trade-spend&drawer=create") },
  // visits
  { file: "marketing/visits/[id]/page.tsx",       content: dynamicRedirect("/dashboard/marketing?tab=visits&id={id}&drawer=detail") },
  { file: "marketing/visits/new/page.tsx",        content: staticRedirect("/dashboard/marketing?tab=visits&drawer=create") },

  // ── Finance / accounting sub-pages ─────────────────────────────────────────
  { file: "finance/accounting/balance-sheet/page.tsx",       content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/chart-of-accounts/page.tsx",   content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/controls/page.tsx",            content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/customers-ledger/page.tsx",    content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/general-ledger/page.tsx",      content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/journal/page.tsx",             content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/payments/page.tsx",            content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/period-closing/page.tsx",      content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/profit-loss/page.tsx",         content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/purchase-invoices/page.tsx",   content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/sales-invoices/page.tsx",      content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/suppliers-ledger/page.tsx",    content: staticRedirect("/dashboard/finance?tab=accounting") },
  { file: "finance/accounting/trial-balance/page.tsx",       content: staticRedirect("/dashboard/finance?tab=accounting") },

  // ── Production child pages ─────────────────────────────────────────────────
  { file: "production/advanced/page.tsx",         content: staticRedirect("/dashboard/production?tab=scheduling") },
  { file: "production/ai/page.tsx",               content: staticRedirect("/dashboard/production?tab=plans") },
  { file: "production/orders/[id]/page.tsx",      content: dynamicRedirect("/dashboard/production?tab=orders&id={id}&drawer=detail") },
  { file: "production/plans/[id]/page.tsx",       content: dynamicRedirect("/dashboard/production?tab=plans&id={id}&drawer=detail") },
  { file: "production/shifts/page.tsx",           content: staticRedirect("/dashboard/production?tab=scheduling") },
  { file: "production/work-orders/page.tsx",      content: staticRedirect("/dashboard/production?tab=orders") },

  // ── Utility-management child pages ─────────────────────────────────────────
  { file: "utility-management/categories/page.tsx",                          content: staticRedirect("/dashboard/utility-management?tab=assets") },
  { file: "utility-management/kpi-center/boiler/page.tsx",                   content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/chemicals/page.tsx",                content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/compressor/page.tsx",               content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/electricity/page.tsx",              content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/machine-utility/page.tsx",          content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/soft-water/page.tsx",               content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/solar/page.tsx",                    content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/utility-cost/page.tsx",             content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/wastewater/page.tsx",               content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/kpi-center/water/page.tsx",                    content: staticRedirect("/dashboard/utility-management?tab=kpi-center") },
  { file: "utility-management/reports/anomalies/page.tsx",                   content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/cost-allocation/page.tsx",             content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/daily-consumption/page.tsx",           content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/equipment-efficiency/page.tsx",        content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/load-analysis/page.tsx",               content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/sustainability/page.tsx",              content: staticRedirect("/dashboard/utility-management?tab=reports") },
  { file: "utility-management/reports/treatment/page.tsx",                   content: staticRedirect("/dashboard/utility-management?tab=reports") },

  // ── Van Sales (→ /dashboard/sales?tab=van-sales) ───────────────────────────
  { file: "van-sales/ai/page.tsx",             content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/field-rep/page.tsx",      content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/fraud/page.tsx",          content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/mpesa/page.tsx",          content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/performance/page.tsx",    content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/pos/page.tsx",            content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/reconciliation/page.tsx", content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/reports/page.tsx",        content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/returns/page.tsx",        content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/route/page.tsx",          content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/route-optimizer/page.tsx",content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/stock/page.tsx",          content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/vans/new/page.tsx",       content: staticRedirect("/dashboard/sales?tab=van-sales&drawer=create") },
  { file: "van-sales/vans/page.tsx",           content: staticRedirect("/dashboard/sales?tab=van-sales") },
  { file: "van-sales/vans/[id]/page.tsx",      content: dynamicRedirect("/dashboard/sales?tab=van-sales&id={id}&drawer=detail") },
  { file: "van-sales/visits/page.tsx",         content: staticRedirect("/dashboard/sales?tab=van-sales") },

  // ── QMS (→ /dashboard/quality?tab=qms or specific tab) ─────────────────────
  { file: "qms/ai/page.tsx",                   content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/allergen/page.tsx",             content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "qms/aql/page.tsx",                  content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/audit-checklists/page.tsx",     content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/calibration/page.tsx",          content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/ccp/page.tsx",                  content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/coa/page.tsx",                  content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/corrective-actions/page.tsx",   content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/deviations/page.tsx",           content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/haccp/page.tsx",                content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/inspections/page.tsx",          content: staticRedirect("/dashboard/quality?tab=inspections") },
  { file: "qms/quarantine/page.tsx",           content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/reports/page.tsx",              content: staticRedirect("/dashboard/quality?tab=reports") },
  { file: "qms/supplier-safety/page.tsx",      content: staticRedirect("/dashboard/quality?tab=qms") },
  { file: "qms/templates/page.tsx",            content: staticRedirect("/dashboard/quality?tab=qms") },

  // ── Recruitment (→ /dashboard/hr?tab=recruitment) ──────────────────────────
  { file: "recruitment/ai/page.tsx",                    content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/candidates/new/page.tsx",        content: staticRedirect("/dashboard/hr?tab=recruitment&drawer=create") },
  { file: "recruitment/candidates/page.tsx",            content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/candidates/[id]/page.tsx",       content: dynamicRedirect("/dashboard/hr?tab=recruitment&id={id}&drawer=detail") },
  { file: "recruitment/interviews/page.tsx",            content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/offers/page.tsx",                content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/pipeline/page.tsx",              content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/reports/page.tsx",               content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/requisitions/new/page.tsx",      content: staticRedirect("/dashboard/hr?tab=recruitment&drawer=create") },
  { file: "recruitment/requisitions/page.tsx",          content: staticRedirect("/dashboard/hr?tab=recruitment") },
  { file: "recruitment/requisitions/[id]/page.tsx",     content: dynamicRedirect("/dashboard/hr?tab=recruitment&id={id}&drawer=detail") },
  { file: "recruitment/stages/page.tsx",                content: staticRedirect("/dashboard/hr?tab=recruitment") },

  // ── Allergen (→ /dashboard/quality?tab=allergen) ────────────────────────────
  { file: "allergen/ai/page.tsx",                content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/allergens/page.tsx",          content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/change-logs/page.tsx",        content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/cleaning/page.tsx",           content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/label-readiness/page.tsx",    content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/material-profiles/page.tsx",  content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/nutrition/page.tsx",          content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/product-allergens/page.tsx",  content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/product-nutrition/page.tsx",  content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/reports/page.tsx",            content: staticRedirect("/dashboard/quality?tab=allergen") },
  { file: "allergen/rollup/page.tsx",             content: staticRedirect("/dashboard/quality?tab=allergen") },

  // ── Expenses (→ /dashboard/hr?tab=expenses) ─────────────────────────────────
  { file: "expenses/advances/page.tsx",          content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/ai/page.tsx",                content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/approval/page.tsx",          content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/categories/page.tsx",        content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/claims/new/page.tsx",        content: staticRedirect("/dashboard/hr?tab=expenses&drawer=create") },
  { file: "expenses/claims/page.tsx",            content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/claims/[id]/page.tsx",       content: dynamicRedirect("/dashboard/hr?tab=expenses&id={id}&drawer=detail") },
  { file: "expenses/policies/page.tsx",          content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/receipt-ocr/page.tsx",       content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/reimbursement/page.tsx",     content: staticRedirect("/dashboard/hr?tab=expenses") },
  { file: "expenses/reports/page.tsx",           content: staticRedirect("/dashboard/hr?tab=expenses") },

  // ── Fixed Assets (→ /dashboard/finance?tab=fixed-assets) ───────────────────
  { file: "fixed-assets/ai/page.tsx",                         content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/assets/new/page.tsx",                 content: staticRedirect("/dashboard/finance?tab=fixed-assets&drawer=create") },
  { file: "fixed-assets/assets/page.tsx",                     content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/assets/[id]/page.tsx",                content: dynamicRedirect("/dashboard/finance?tab=fixed-assets&id={id}&drawer=detail") },
  { file: "fixed-assets/assets/[id]/add-component/page.tsx",  content: dynamicRedirect("/dashboard/finance?tab=fixed-assets&id={id}&drawer=add-component") },
  { file: "fixed-assets/categories/page.tsx",                 content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/depreciation/page.tsx",               content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/disposal/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/import/page.tsx",                     content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/posting/page.tsx",                    content: staticRedirect("/dashboard/finance?tab=fixed-assets") },
  { file: "fixed-assets/transfer/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=fixed-assets") },

  // ── CRM child routes (→ /dashboard/crm) ────────────────────────────────────
  { file: "crm/ai/page.tsx",                   content: staticRedirect("/dashboard/crm?tab=overview") },
  { file: "crm/overdue/page.tsx",              content: staticRedirect("/dashboard/crm?tab=pipeline") },
  { file: "crm/qualify/page.tsx",              content: staticRedirect("/dashboard/crm?tab=leads") },
  { file: "crm/records/[id]/page.tsx",         content: dynamicRedirect("/dashboard/crm?tab=overview&id={id}&drawer=detail") },

  // ── Sales child dynamic routes (ID preserved) ───────────────────────────────
  { file: "sales/orders/[id]/page.tsx",        content: dynamicRedirect("/dashboard/sales?tab=orders&id={id}&drawer=detail") },
  { file: "sales/invoices/[id]/page.tsx",      content: dynamicRedirect("/dashboard/sales?tab=invoices&id={id}&drawer=detail") },
  { file: "sales/shipments/[id]/page.tsx",     content: dynamicRedirect("/dashboard/sales?tab=shipments&id={id}&drawer=detail") },
  { file: "sales/pod/page.tsx",                content: staticRedirect("/dashboard/sales?tab=delivery") },
  { file: "sales/customer-statement/page.tsx", content: staticRedirect("/dashboard/sales?tab=customers") },

  // ── Procurement child dynamic routes (ID preserved) ─────────────────────────
  { file: "procurement/[id]/page.tsx",         content: dynamicRedirect("/dashboard/procurement?tab=purchase-requests&id={id}&drawer=detail") },
  { file: "procurement/orders/[id]/page.tsx",  content: dynamicRedirect("/dashboard/procurement?tab=orders&id={id}&drawer=detail") },

  // ── Documents child routes ──────────────────────────────────────────────────
  { file: "documents/new/page.tsx",            content: staticRedirect("/dashboard/documents?drawer=create") },
  { file: "documents/[id]/page.tsx",           content: dynamicRedirect("/dashboard/documents?id={id}&drawer=detail") },

  // ── Utilities (→ /dashboard/admin?tab=system-config) — clears UNKNOWN ───────
  { file: "utilities/currencies/page.tsx",     content: staticRedirect("/dashboard/admin?tab=system-config") },
  { file: "utilities/series/page.tsx",         content: staticRedirect("/dashboard/admin?tab=system-config") },
  { file: "utilities/uom/page.tsx",            content: staticRedirect("/dashboard/admin?tab=system-config") },

  // ══════════════════════════════════════════════════════════════════════════════
  // PASS 5 — Bulk conversion of all remaining FULL_DUPLICATE_UI clusters
  // ══════════════════════════════════════════════════════════════════════════════

  // ── material-flow (→ /dashboard/production?tab=material-flow) ───────────────
  { file: "material-flow/bulk-transfer/page.tsx",        content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/fg-receipt/page.tsx",           content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/history/page.tsx",              content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/issue/page.tsx",                content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/packaging/page.tsx",            content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/reconciliation/page.tsx",       content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/reservations/page.tsx",         content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/returns/page.tsx",              content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/stages/page.tsx",               content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/tanks/page.tsx",                content: staticRedirect("/dashboard/production?tab=material-flow") },
  { file: "material-flow/wip-transfer/page.tsx",         content: staticRedirect("/dashboard/production?tab=material-flow") },

  // ── portal (→ /dashboard/sales?tab=portal) ──────────────────────────────────
  { file: "portal/accounts/[id]/page.tsx",               content: dynamicRedirect("/dashboard/sales?tab=portal&id={id}&drawer=detail") },
  { file: "portal/accounts/[id]/view/page.tsx",          content: dynamicRedirect("/dashboard/sales?tab=portal&id={id}&drawer=detail") },
  { file: "portal/accounts/page.tsx",                    content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/activity/page.tsx",                    content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/ai/page.tsx",                          content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/claims/page.tsx",                      content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/drafts/page.tsx",                      content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/order-tracking/page.tsx",              content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/reports/page.tsx",                     content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/sell-through/page.tsx",                content: staticRedirect("/dashboard/sales?tab=portal") },
  { file: "portal/users/page.tsx",                       content: staticRedirect("/dashboard/sales?tab=portal") },

  // ── shelf-life (→ /dashboard/inventory?tab=shelf-life) ──────────────────────
  { file: "shelf-life/bulk-hold-monitor/page.tsx",       content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/compliance/page.tsx",              content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/customer-rules/page.tsx",          content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/disposition/page.tsx",             content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/expired/page.tsx",                 content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/fefo-config/page.tsx",             content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/lot-aging/page.tsx",               content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/near-expiry/page.tsx",             content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/production-validation/page.tsx",   content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/retest-queue/page.tsx",            content: staticRedirect("/dashboard/inventory?tab=shelf-life") },
  { file: "shelf-life/shipment-validation/page.tsx",     content: staticRedirect("/dashboard/inventory?tab=shelf-life") },

  // ── supplier-portal (→ /dashboard/procurement?tab=supplier-portal) ───────────
  { file: "supplier-portal/accounts/[id]/page.tsx",                   content: dynamicRedirect("/dashboard/procurement?tab=supplier-portal&id={id}&drawer=detail") },
  { file: "supplier-portal/accounts/[id]/purchase-orders/page.tsx",   content: dynamicRedirect("/dashboard/procurement?tab=supplier-portal&id={id}&drawer=detail") },
  { file: "supplier-portal/accounts/page.tsx",                        content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/activity/page.tsx",                        content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/ai/page.tsx",                              content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/documents/page.tsx",                       content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/eta/page.tsx",                             content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/invoices/page.tsx",                        content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/payment/page.tsx",                         content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/reports/page.tsx",                         content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },
  { file: "supplier-portal/users/page.tsx",                           content: staticRedirect("/dashboard/procurement?tab=supplier-portal") },

  // ── tpm (→ /dashboard/marketing?tab=tpm) ────────────────────────────────────
  { file: "tpm/ai/page.tsx",                             content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/budget/page.tsx",                         content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/calendar/page.tsx",                       content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/claims/page.tsx",                         content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/plans/new/page.tsx",                      content: staticRedirect("/dashboard/marketing?tab=tpm&drawer=create") },
  { file: "tpm/plans/page.tsx",                          content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/promotions/[id]/page.tsx",                content: dynamicRedirect("/dashboard/marketing?tab=tpm&id={id}&drawer=detail") },
  { file: "tpm/promotions/new/page.tsx",                 content: staticRedirect("/dashboard/marketing?tab=tpm&drawer=create") },
  { file: "tpm/promotions/page.tsx",                     content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/roi/page.tsx",                            content: staticRedirect("/dashboard/marketing?tab=tpm") },
  { file: "tpm/settlement/page.tsx",                     content: staticRedirect("/dashboard/marketing?tab=tpm") },

  // ── appraisals (→ /dashboard/hr?tab=appraisals) ─────────────────────────────
  { file: "appraisals/ai/page.tsx",                      content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/development-plans/page.tsx",       content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/hr-review/page.tsx",               content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/manager-queue/page.tsx",           content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/periods/page.tsx",                 content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/records/new/page.tsx",             content: staticRedirect("/dashboard/hr?tab=appraisals&drawer=create") },
  { file: "appraisals/records/page.tsx",                 content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/reports/page.tsx",                 content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/self-review/page.tsx",             content: staticRedirect("/dashboard/hr?tab=appraisals") },
  { file: "appraisals/templates/page.tsx",               content: staticRedirect("/dashboard/hr?tab=appraisals") },

  // ── bank-reconciliation (→ /dashboard/finance?tab=bank-recon) ───────────────
  { file: "bank-reconciliation/accounts/page.tsx",       content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/ai/page.tsx",             content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/balance/page.tsx",        content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/import/page.tsx",         content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/mpesa/page.tsx",          content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/open-items/page.tsx",     content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/reports/page.tsx",        content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/rules/page.tsx",          content: staticRedirect("/dashboard/finance?tab=bank-recon") },
  { file: "bank-reconciliation/statements/[id]/page.tsx",content: dynamicRedirect("/dashboard/finance?tab=bank-recon&id={id}&drawer=detail") },
  { file: "bank-reconciliation/statements/page.tsx",     content: staticRedirect("/dashboard/finance?tab=bank-recon") },

  // ── dimensions (→ /dashboard/finance?tab=dimensions) ───────────────────────
  { file: "dimensions/ai/page.tsx",                      content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/allocation-run/page.tsx",          content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/allocations/page.tsx",             content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/completeness/page.tsx",            content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/cost-centers/page.tsx",            content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/defaults/page.tsx",                content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/reclassify/page.tsx",              content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/types/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/validation/page.tsx",              content: staticRedirect("/dashboard/finance?tab=dimensions") },
  { file: "dimensions/values/page.tsx",                  content: staticRedirect("/dashboard/finance?tab=dimensions") },

  // ── recurring-orders (→ /dashboard/sales?tab=recurring) ─────────────────────
  { file: "recurring-orders/ai/page.tsx",                content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/billing/page.tsx",           content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/generation-log/page.tsx",    content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/pause-skip/page.tsx",        content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/reports/page.tsx",           content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/schedule/page.tsx",          content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/templates/[id]/page.tsx",    content: dynamicRedirect("/dashboard/sales?tab=recurring&id={id}&drawer=detail") },
  { file: "recurring-orders/templates/new/page.tsx",     content: staticRedirect("/dashboard/sales?tab=recurring&drawer=create") },
  { file: "recurring-orders/templates/page.tsx",         content: staticRedirect("/dashboard/sales?tab=recurring") },
  { file: "recurring-orders/upcoming-demand/page.tsx",   content: staticRedirect("/dashboard/sales?tab=recurring") },

  // ── calendar (→ /dashboard/communication?tab=calendar) ──────────────────────
  { file: "calendar/ai/page.tsx",                        content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/availability/page.tsx",              content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/bookings/page.tsx",                  content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/events/page.tsx",                    content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/new-event/page.tsx",                 content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/reports/page.tsx",                   content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/resources/page.tsx",                 content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/shifts/page.tsx",                    content: staticRedirect("/dashboard/communication?tab=calendar") },
  { file: "calendar/view/page.tsx",                      content: staticRedirect("/dashboard/communication?tab=calendar") },

  // ── dunning (→ /dashboard/finance?tab=dunning) ──────────────────────────────
  { file: "dunning/aging/page.tsx",                      content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/ai/page.tsx",                         content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/cases/[id]/page.tsx",                 content: dynamicRedirect("/dashboard/finance?tab=dunning&id={id}&drawer=detail") },
  { file: "dunning/cases/page.tsx",                      content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/credit-holds/page.tsx",               content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/policies/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/reports/page.tsx",                    content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/templates/page.tsx",                  content: staticRedirect("/dashboard/finance?tab=dunning") },
  { file: "dunning/workqueue/page.tsx",                  content: staticRedirect("/dashboard/finance?tab=dunning") },

  // ── machine-ops (→ /dashboard/production?tab=machine-ops) ───────────────────
  { file: "machine-ops/assignment/page.tsx",             content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/certs/page.tsx",                  content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/costing/page.tsx",                content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/downtime/page.tsx",               content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/machines/page.tsx",               content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/operators/page.tsx",              content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/performance/page.tsx",            content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/runtime/page.tsx",                content: staticRedirect("/dashboard/production?tab=machine-ops") },
  { file: "machine-ops/teams/page.tsx",                  content: staticRedirect("/dashboard/production?tab=machine-ops") },

  // ── report-builder (→ /dashboard/analytics?tab=report-builder) ──────────────
  { file: "report-builder/ai/page.tsx",                  content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/builder/page.tsx",             content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/catalog/page.tsx",             content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/dashboards/page.tsx",          content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/executive/page.tsx",           content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/rls/page.tsx",                 content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/saved/page.tsx",               content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/schedules/page.tsx",           content: staticRedirect("/dashboard/analytics?tab=report-builder") },
  { file: "report-builder/viewer/page.tsx",              content: staticRedirect("/dashboard/analytics?tab=report-builder") },

  // ── traceability (→ /dashboard/inventory?tab=traceability) ──────────────────
  { file: "traceability/backward/page.tsx",              content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/forward/page.tsx",               content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/genealogy/page.tsx",             content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/mock-recall/page.tsx",           content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/recalls/[id]/page.tsx",          content: dynamicRedirect("/dashboard/inventory?tab=traceability&id={id}&drawer=detail") },
  { file: "traceability/recalls/page.tsx",               content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/regulatory/page.tsx",            content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/search/page.tsx",                content: staticRedirect("/dashboard/inventory?tab=traceability") },
  { file: "traceability/templates/page.tsx",             content: staticRedirect("/dashboard/inventory?tab=traceability") },

  // ── custom-fields (→ /dashboard/admin?tab=custom-fields) ────────────────────
  { file: "custom-fields/[id]/page.tsx",                 content: dynamicRedirect("/dashboard/admin?tab=custom-fields&id={id}&drawer=detail") },
  { file: "custom-fields/ai/page.tsx",                   content: staticRedirect("/dashboard/admin?tab=custom-fields") },
  { file: "custom-fields/fields/page.tsx",               content: staticRedirect("/dashboard/admin?tab=custom-fields") },
  { file: "custom-fields/form-builder/page.tsx",         content: staticRedirect("/dashboard/admin?tab=custom-fields") },
  { file: "custom-fields/new-field/page.tsx",            content: staticRedirect("/dashboard/admin?tab=custom-fields&drawer=create") },
  { file: "custom-fields/reports/page.tsx",              content: staticRedirect("/dashboard/admin?tab=custom-fields") },
  { file: "custom-fields/values/page.tsx",               content: staticRedirect("/dashboard/admin?tab=custom-fields") },
  { file: "custom-fields/workflow-rules/page.tsx",       content: staticRedirect("/dashboard/admin?tab=custom-fields") },

  // ── ess (→ /dashboard/hr?tab=ess) ───────────────────────────────────────────
  { file: "ess/admin/page.tsx",                          content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/ai/page.tsx",                             content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/attendance/page.tsx",                     content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/documents/page.tsx",                      content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/leave/page.tsx",                          content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/notifications/page.tsx",                  content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/profile/page.tsx",                        content: staticRedirect("/dashboard/hr?tab=ess") },
  { file: "ess/requests/page.tsx",                       content: staticRedirect("/dashboard/hr?tab=ess") },

  // ── gs1 (→ /dashboard/compliance?tab=gs1) ───────────────────────────────────
  { file: "gs1/ai/page.tsx",                             content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/barcodes/page.tsx",                       content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/config/page.tsx",                         content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/labels/page.tsx",                         content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/print-queue/page.tsx",                    content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/reports/page.tsx",                        content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/scan/page.tsx",                           content: staticRedirect("/dashboard/compliance?tab=gs1") },
  { file: "gs1/sscc/page.tsx",                           content: staticRedirect("/dashboard/compliance?tab=gs1") },

  // ── invoice-match (→ /dashboard/finance?tab=invoice-match) ──────────────────
  { file: "invoice-match/[id]/page.tsx",                 content: dynamicRedirect("/dashboard/finance?tab=invoice-match&id={id}&drawer=detail") },
  { file: "invoice-match/ai/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/blocked/page.tsx",              content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/duplicates/page.tsx",           content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/matches/page.tsx",              content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/reports/page.tsx",              content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/review-queue/page.tsx",         content: staticRedirect("/dashboard/finance?tab=invoice-match") },
  { file: "invoice-match/tolerance-rules/page.tsx",      content: staticRedirect("/dashboard/finance?tab=invoice-match") },

  // ── price-lists (→ /dashboard/sales?tab=price-lists) ────────────────────────
  { file: "price-lists/[id]/page.tsx",                   content: dynamicRedirect("/dashboard/sales?tab=price-lists&id={id}&drawer=detail") },
  { file: "price-lists/ai/page.tsx",                     content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/approval-queue/page.tsx",         content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/compare/page.tsx",                content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/discount-rules/page.tsx",         content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/import/page.tsx",                 content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/margin/page.tsx",                 content: staticRedirect("/dashboard/sales?tab=price-lists") },
  { file: "price-lists/reports/page.tsx",                content: staticRedirect("/dashboard/sales?tab=price-lists") },

  // ── promotions (→ /dashboard/marketing?tab=promotions-schemes) ──────────────
  { file: "promotions/ai/page.tsx",                      content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },
  { file: "promotions/analytics/page.tsx",               content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },
  { file: "promotions/overrides/page.tsx",               content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },
  { file: "promotions/page.tsx",                         content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },
  { file: "promotions/schemes/[id]/page.tsx",            content: dynamicRedirect("/dashboard/marketing?tab=promotions-schemes&id={id}&drawer=detail") },
  { file: "promotions/schemes/new/page.tsx",             content: staticRedirect("/dashboard/marketing?tab=promotions-schemes&drawer=create") },
  { file: "promotions/schemes/page.tsx",                 content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },
  { file: "promotions/simulate/page.tsx",                content: staticRedirect("/dashboard/marketing?tab=promotions-schemes") },

  // ── training (→ /dashboard/hr?tab=training) ──────────────────────────────────
  { file: "training/ai/page.tsx",                        content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/assignments/page.tsx",               content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/certifications/page.tsx",            content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/feedback/page.tsx",                  content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/programs/page.tsx",                  content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/reports/page.tsx",                   content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/sessions/page.tsx",                  content: staticRedirect("/dashboard/hr?tab=training") },
  { file: "training/skill-matrix/page.tsx",              content: staticRedirect("/dashboard/hr?tab=training") },

  // ── contracts (→ /dashboard/sales?tab=contracts) ────────────────────────────
  { file: "contracts/ai/page.tsx",                       content: staticRedirect("/dashboard/sales?tab=contracts") },
  { file: "contracts/expiring/page.tsx",                 content: staticRedirect("/dashboard/sales?tab=contracts") },
  { file: "contracts/list/[id]/page.tsx",                content: dynamicRedirect("/dashboard/sales?tab=contracts&id={id}&drawer=detail") },
  { file: "contracts/list/page.tsx",                     content: staticRedirect("/dashboard/sales?tab=contracts") },
  { file: "contracts/new/page.tsx",                      content: staticRedirect("/dashboard/sales?tab=contracts&drawer=create") },
  { file: "contracts/performance/page.tsx",              content: staticRedirect("/dashboard/sales?tab=contracts") },
  { file: "contracts/reports/page.tsx",                  content: staticRedirect("/dashboard/sales?tab=contracts") },

  // ── fleet (→ /dashboard/logistics?tab=fleet) ────────────────────────────────
  { file: "fleet/drivers/page.tsx",                      content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/fuel/page.tsx",                         content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/incidents/page.tsx",                    content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/maintenance/page.tsx",                  content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/reports/page.tsx",                      content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/trips/page.tsx",                        content: staticRedirect("/dashboard/logistics?tab=fleet") },
  { file: "fleet/vehicles/page.tsx",                     content: staticRedirect("/dashboard/logistics?tab=fleet") },

  // ── reports (→ /dashboard/analytics?tab=reports) ────────────────────────────
  { file: "reports/finance/page.tsx",                    content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/inventory/page.tsx",                  content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/marketing/page.tsx",                  content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/payments/page.tsx",                   content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/procurement/page.tsx",                content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/production/page.tsx",                 content: staticRedirect("/dashboard/analytics?tab=reports") },
  { file: "reports/sales/page.tsx",                      content: staticRedirect("/dashboard/analytics?tab=reports") },

  // ── commissions (→ /dashboard/sales?tab=commissions) ────────────────────────
  { file: "commissions/ai/page.tsx",                     content: staticRedirect("/dashboard/sales?tab=commissions") },
  { file: "commissions/payouts/page.tsx",                content: staticRedirect("/dashboard/sales?tab=commissions") },
  { file: "commissions/reports/page.tsx",                content: staticRedirect("/dashboard/sales?tab=commissions") },
  { file: "commissions/rules/page.tsx",                  content: staticRedirect("/dashboard/sales?tab=commissions") },
  { file: "commissions/targets/page.tsx",                content: staticRedirect("/dashboard/sales?tab=commissions") },
  { file: "commissions/transactions/page.tsx",           content: staticRedirect("/dashboard/sales?tab=commissions") },

  // ── esg (→ /dashboard/utility-management?tab=esg) ───────────────────────────
  { file: "esg/activities/page.tsx",                     content: staticRedirect("/dashboard/utility-management?tab=esg") },
  { file: "esg/carbon/page.tsx",                         content: staticRedirect("/dashboard/utility-management?tab=esg") },
  { file: "esg/factors/page.tsx",                        content: staticRedirect("/dashboard/utility-management?tab=esg") },
  { file: "esg/intelligence/page.tsx",                   content: staticRedirect("/dashboard/utility-management?tab=esg") },
  { file: "esg/reports/page.tsx",                        content: staticRedirect("/dashboard/utility-management?tab=esg") },
  { file: "esg/targets/page.tsx",                        content: staticRedirect("/dashboard/utility-management?tab=esg") },

  // ── mrp (→ /dashboard/planning?tab=mrp) ─────────────────────────────────────
  { file: "mrp/forecast/accuracy/page.tsx",              content: staticRedirect("/dashboard/planning?tab=mrp") },
  { file: "mrp/forecast/correlation/page.tsx",           content: staticRedirect("/dashboard/planning?tab=mrp") },
  { file: "mrp/forecast/page.tsx",                       content: staticRedirect("/dashboard/planning?tab=mrp") },
  { file: "mrp/run/page.tsx",                            content: staticRedirect("/dashboard/planning?tab=mrp") },
  { file: "mrp/suggestions/page.tsx",                    content: staticRedirect("/dashboard/planning?tab=mrp") },
  { file: "mrp/workbench/page.tsx",                      content: staticRedirect("/dashboard/planning?tab=mrp") },

  // ── notification-center (→ /dashboard/communication?tab=notifications) ───────
  { file: "notification-center/ai/page.tsx",             content: staticRedirect("/dashboard/communication?tab=notifications") },
  { file: "notification-center/list/page.tsx",           content: staticRedirect("/dashboard/communication?tab=notifications") },
  { file: "notification-center/preferences/page.tsx",    content: staticRedirect("/dashboard/communication?tab=notifications") },
  { file: "notification-center/reports/page.tsx",        content: staticRedirect("/dashboard/communication?tab=notifications") },
  { file: "notification-center/schedules/page.tsx",      content: staticRedirect("/dashboard/communication?tab=notifications") },
  { file: "notification-center/templates/page.tsx",      content: staticRedirect("/dashboard/communication?tab=notifications") },

  // ── procurement-suggestion (→ /dashboard/procurement?tab=suggestions) ────────
  { file: "procurement-suggestion/ai/page.tsx",           content: staticRedirect("/dashboard/procurement?tab=suggestions") },
  { file: "procurement-suggestion/groups/page.tsx",       content: staticRedirect("/dashboard/procurement?tab=suggestions") },
  { file: "procurement-suggestion/reports/page.tsx",      content: staticRedirect("/dashboard/procurement?tab=suggestions") },
  { file: "procurement-suggestion/suggestions/page.tsx",  content: staticRedirect("/dashboard/procurement?tab=suggestions") },
  { file: "procurement-suggestion/supplier-compare/page.tsx", content: staticRedirect("/dashboard/procurement?tab=suggestions") },
  { file: "procurement-suggestion/supplier-prices/page.tsx",  content: staticRedirect("/dashboard/procurement?tab=suggestions") },

  // ── subcontracting (→ /dashboard/procurement?tab=subcontracting) ─────────────
  { file: "subcontracting/ai/page.tsx",                  content: staticRedirect("/dashboard/procurement?tab=subcontracting") },
  { file: "subcontracting/locations/page.tsx",           content: staticRedirect("/dashboard/procurement?tab=subcontracting") },
  { file: "subcontracting/orders/page.tsx",              content: staticRedirect("/dashboard/procurement?tab=subcontracting") },
  { file: "subcontracting/performance/page.tsx",         content: staticRedirect("/dashboard/procurement?tab=subcontracting") },
  { file: "subcontracting/stock/page.tsx",               content: staticRedirect("/dashboard/procurement?tab=subcontracting") },
  { file: "subcontracting/yield/page.tsx",               content: staticRedirect("/dashboard/procurement?tab=subcontracting") },

  // ── timesheets (→ /dashboard/hr?tab=timesheets) ──────────────────────────────
  { file: "timesheets/ai/page.tsx",                      content: staticRedirect("/dashboard/hr?tab=timesheets") },
  { file: "timesheets/approval-queue/page.tsx",          content: staticRedirect("/dashboard/hr?tab=timesheets") },
  { file: "timesheets/my-timesheets/page.tsx",           content: staticRedirect("/dashboard/hr?tab=timesheets") },
  { file: "timesheets/reports/page.tsx",                 content: staticRedirect("/dashboard/hr?tab=timesheets") },
  { file: "timesheets/time-entry/page.tsx",              content: staticRedirect("/dashboard/hr?tab=timesheets") },
  { file: "timesheets/weekly-view/page.tsx",             content: staticRedirect("/dashboard/hr?tab=timesheets") },

  // ── webhooks (→ /dashboard/integrations?tab=webhooks) ───────────────────────
  { file: "webhooks/dead-letter/page.tsx",               content: staticRedirect("/dashboard/integrations?tab=webhooks") },
  { file: "webhooks/definitions/page.tsx",               content: staticRedirect("/dashboard/integrations?tab=webhooks") },
  { file: "webhooks/deliveries/page.tsx",                content: staticRedirect("/dashboard/integrations?tab=webhooks") },
  { file: "webhooks/inbound/page.tsx",                   content: staticRedirect("/dashboard/integrations?tab=webhooks") },
  { file: "webhooks/reports/page.tsx",                   content: staticRedirect("/dashboard/integrations?tab=webhooks") },
  { file: "webhooks/subscriptions/page.tsx",             content: staticRedirect("/dashboard/integrations?tab=webhooks") },

  // ── chatter (→ /dashboard/communication?tab=chatter) ────────────────────────
  { file: "chatter/ai/page.tsx",                         content: staticRedirect("/dashboard/communication?tab=chatter") },
  { file: "chatter/feed/page.tsx",                       content: staticRedirect("/dashboard/communication?tab=chatter") },
  { file: "chatter/reports/page.tsx",                    content: staticRedirect("/dashboard/communication?tab=chatter") },
  { file: "chatter/search/page.tsx",                     content: staticRedirect("/dashboard/communication?tab=chatter") },
  { file: "chatter/threads/page.tsx",                    content: staticRedirect("/dashboard/communication?tab=chatter") },

  // ── cycle-count (→ /dashboard/inventory?tab=cycle-count) ────────────────────
  { file: "cycle-count/entries/page.tsx",                content: staticRedirect("/dashboard/inventory?tab=cycle-count") },
  { file: "cycle-count/plans/page.tsx",                  content: staticRedirect("/dashboard/inventory?tab=cycle-count") },
  { file: "cycle-count/reports/page.tsx",                content: staticRedirect("/dashboard/inventory?tab=cycle-count") },
  { file: "cycle-count/tasks/page.tsx",                  content: staticRedirect("/dashboard/inventory?tab=cycle-count") },
  { file: "cycle-count/variances/page.tsx",              content: staticRedirect("/dashboard/inventory?tab=cycle-count") },

  // ── kanban (→ /dashboard/planning?tab=kanban) ────────────────────────────────
  { file: "kanban/ai/page.tsx",                          content: staticRedirect("/dashboard/planning?tab=kanban") },
  { file: "kanban/boards/page.tsx",                      content: staticRedirect("/dashboard/planning?tab=kanban") },
  { file: "kanban/cards/page.tsx",                       content: staticRedirect("/dashboard/planning?tab=kanban") },
  { file: "kanban/reports/page.tsx",                     content: staticRedirect("/dashboard/planning?tab=kanban") },
  { file: "kanban/view/page.tsx",                        content: staticRedirect("/dashboard/planning?tab=kanban") },

  // ── landed-cost (→ /dashboard/procurement?tab=landed-cost) ──────────────────
  { file: "landed-cost/[id]/page.tsx",                   content: dynamicRedirect("/dashboard/procurement?tab=landed-cost&id={id}&drawer=detail") },
  { file: "landed-cost/ai/page.tsx",                     content: staticRedirect("/dashboard/procurement?tab=landed-cost") },
  { file: "landed-cost/documents/page.tsx",              content: staticRedirect("/dashboard/procurement?tab=landed-cost") },
  { file: "landed-cost/new/page.tsx",                    content: staticRedirect("/dashboard/procurement?tab=landed-cost&drawer=create") },
  { file: "landed-cost/reports/page.tsx",                content: staticRedirect("/dashboard/procurement?tab=landed-cost") },

  // ── wms sub-pages (→ /dashboard/warehouses?tab=wms) ─────────────────────────
  { file: "wms/counts/[id]/page.tsx",                    content: dynamicRedirect("/dashboard/warehouses?tab=wms&id={id}&drawer=detail") },
  { file: "wms/counts/page.tsx",                         content: staticRedirect("/dashboard/warehouses?tab=wms") },
  { file: "wms/picking/page.tsx",                        content: staticRedirect("/dashboard/warehouses?tab=wms") },
  { file: "wms/replenishment/page.tsx",                  content: staticRedirect("/dashboard/warehouses?tab=wms") },
  { file: "wms/reports/page.tsx",                        content: staticRedirect("/dashboard/warehouses?tab=wms") },

  // ── mps (→ /dashboard/planning?tab=mps) ─────────────────────────────────────
  { file: "mps/campaigns/page.tsx",                      content: staticRedirect("/dashboard/planning?tab=mps") },
  { file: "mps/capacity/page.tsx",                       content: staticRedirect("/dashboard/planning?tab=mps") },
  { file: "mps/planning-board/page.tsx",                 content: staticRedirect("/dashboard/planning?tab=mps") },
  { file: "mps/whatif/page.tsx",                         content: staticRedirect("/dashboard/planning?tab=mps") },

  // ── surveys (→ /dashboard/crm?tab=surveys) ───────────────────────────────────
  { file: "surveys/[id]/page.tsx",                       content: dynamicRedirect("/dashboard/crm?tab=surveys&id={id}&drawer=detail") },
  { file: "surveys/[id]/respond/page.tsx",               content: dynamicRedirect("/dashboard/crm?tab=surveys&id={id}&drawer=detail") },
  { file: "surveys/[id]/results/page.tsx",               content: dynamicRedirect("/dashboard/crm?tab=surveys&id={id}&drawer=detail") },
  { file: "surveys/new/page.tsx",                        content: staticRedirect("/dashboard/crm?tab=surveys&drawer=create") },

  // ── tax (→ /dashboard/finance?tab=tax) ──────────────────────────────────────
  { file: "tax/regulatory/page.tsx",                     content: staticRedirect("/dashboard/finance?tab=tax") },
  { file: "tax/reports/page.tsx",                        content: staticRedirect("/dashboard/finance?tab=tax") },
  { file: "tax/rules/page.tsx",                          content: staticRedirect("/dashboard/finance?tab=tax") },
  { file: "tax/transactions/page.tsx",                   content: staticRedirect("/dashboard/finance?tab=tax") },

  // ── knowledge-base (→ /dashboard/documents?tab=knowledge-base) ──────────────
  { file: "knowledge-base/[id]/page.tsx",                content: dynamicRedirect("/dashboard/documents?tab=knowledge-base&id={id}&drawer=detail") },
  { file: "knowledge-base/articles/new/page.tsx",        content: staticRedirect("/dashboard/documents?tab=knowledge-base&drawer=create") },
  { file: "knowledge-base/articles/page.tsx",            content: staticRedirect("/dashboard/documents?tab=knowledge-base") },

  // ── production-execution (→ /dashboard/production?tab=execution) ─────────────
  { file: "production-execution/[id]/genealogy/page.tsx",content: dynamicRedirect("/dashboard/production?tab=execution&id={id}&drawer=detail") },
  { file: "production-execution/[id]/page.tsx",          content: dynamicRedirect("/dashboard/production?tab=execution&id={id}&drawer=detail") },
  { file: "production-execution/work-orders/page.tsx",   content: staticRedirect("/dashboard/production?tab=execution") },

  // ── putaway (→ /dashboard/warehouses?tab=wms) ───────────────────────────────
  { file: "putaway/execute/[id]/page.tsx",               content: dynamicRedirect("/dashboard/warehouses?tab=wms&id={id}&drawer=detail") },
  { file: "putaway/page.tsx",                            content: staticRedirect("/dashboard/warehouses?tab=wms") },
  { file: "putaway/rules/page.tsx",                      content: staticRedirect("/dashboard/warehouses?tab=wms") },

  // ── secondary-sales (→ /dashboard/sales?tab=secondary) ──────────────────────
  { file: "secondary-sales/analysis/page.tsx",           content: staticRedirect("/dashboard/sales?tab=secondary") },
  { file: "secondary-sales/inventory/page.tsx",          content: staticRedirect("/dashboard/sales?tab=secondary") },
  { file: "secondary-sales/upload/page.tsx",             content: staticRedirect("/dashboard/sales?tab=secondary") },

  // ── containers (→ /dashboard/logistics?tab=containers) ──────────────────────
  { file: "containers/outstanding/page.tsx",             content: staticRedirect("/dashboard/logistics?tab=containers") },
  { file: "containers/page.tsx",                         content: staticRedirect("/dashboard/logistics?tab=containers") },

  // ── developer (→ /dashboard/integrations?tab=developer) ─────────────────────
  { file: "developer/graphql/page.tsx",                  content: staticRedirect("/dashboard/integrations?tab=developer") },
  { file: "developer/keys/page.tsx",                     content: staticRedirect("/dashboard/integrations?tab=developer") },

  // ── logs (→ /dashboard/admin?tab=logs) ──────────────────────────────────────
  { file: "logs/compliance/page.tsx",                    content: staticRedirect("/dashboard/admin?tab=logs") },
  { file: "logs/retention/page.tsx",                     content: staticRedirect("/dashboard/admin?tab=logs") },

  // ── mobile (→ /dashboard/admin?tab=mobile) ───────────────────────────────────
  { file: "mobile/approvals/page.tsx",                   content: staticRedirect("/dashboard/admin?tab=mobile") },
  { file: "mobile/devices/page.tsx",                     content: staticRedirect("/dashboard/admin?tab=mobile") },

  // ── projects (→ /dashboard/production?tab=projects) ─────────────────────────
  { file: "projects/[id]/page.tsx",                      content: dynamicRedirect("/dashboard/production?tab=projects&id={id}&drawer=detail") },
  { file: "projects/dashboard/page.tsx",                 content: staticRedirect("/dashboard/production?tab=projects") },

  // ── brand-assets (→ /dashboard/quality?tab=brand-assets) ────────────────────
  { file: "brand-assets/[id]/page.tsx",                  content: dynamicRedirect("/dashboard/quality?tab=brand-assets&id={id}&drawer=detail") },

  // ── copacking (→ /dashboard/procurement?tab=subcontracting) ─────────────────
  { file: "copacking/page.tsx",                          content: staticRedirect("/dashboard/procurement?tab=subcontracting") },

  // ── payroll (→ /dashboard/hr?tab=payroll) — file-level + MW entry needed ─────
  { file: "payroll/runs/[id]/page.tsx",                  content: dynamicRedirect("/dashboard/hr?tab=payroll&id={id}&drawer=detail") },

  // ── quality [id] (→ /dashboard/quality?tab=qms) — file-level only ────────────
  { file: "quality/[id]/page.tsx",                       content: dynamicRedirect("/dashboard/quality?tab=qms&id={id}&drawer=detail") },

  // ── roles [id] (→ /dashboard/admin?tab=roles) ───────────────────────────────
  { file: "roles/[id]/page.tsx",                         content: dynamicRedirect("/dashboard/admin?tab=roles&id={id}&drawer=detail") },

  // ── security (→ /dashboard/admin?tab=security) ──────────────────────────────
  { file: "security/monitor/page.tsx",                   content: staticRedirect("/dashboard/admin?tab=security") },

  // ── users [id] (→ /dashboard/admin?tab=users) ───────────────────────────────
  { file: "users/[id]/page.tsx",                         content: dynamicRedirect("/dashboard/admin?tab=users&id={id}&drawer=detail") },
];

let written = 0;
let skipped = 0;
let errors = 0;

for (const { file, content } of redirects) {
  const fullPath = path.join(APP, file);
  if (!fs.existsSync(fullPath)) {
    console.warn(`SKIP (not found): ${file}`);
    skipped++;
    continue;
  }
  try {
    fs.writeFileSync(fullPath, content, "utf8");
    console.log(`OK: ${file}`);
    written++;
  } catch (e) {
    console.error(`ERROR: ${file} — ${e.message}`);
    errors++;
  }
}

console.log(`\nDone. Written=${written} Skipped=${skipped} Errors=${errors}`);
