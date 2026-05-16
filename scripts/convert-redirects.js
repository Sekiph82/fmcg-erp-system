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
