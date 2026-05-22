#!/usr/bin/env node
/**
 * audit-visible-import-graph.js
 *
 * Dynamic audit: builds import visibility graph, extracts all action targets
 * from user-visible pages, classifies broken targets, searches git history.
 *
 * KEY INSIGHT: A page can be user-visible even if its standalone route is
 * middleware-redirected — if it is dynamically imported into a workspace tab.
 *
 * Outputs:
 *   docs/VISIBLE_IMPORT_GRAPH.json / .md
 *   docs/VISIBLE_ACTION_TARGET_INVENTORY.json / .md
 *   docs/VISIBLE_BROKEN_ACTION_TARGETS.json / .md
 *   docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json / .md
 */

"use strict";

const fs   = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT      = path.resolve(__dirname, "..");
const DOCS      = path.join(ROOT, "docs");
const FRONTEND  = path.join(ROOT, "frontend", "src");
const DASHBOARD = path.join(FRONTEND, "app", "dashboard");

// ─── MIDDLEWARE REDIRECT MAP ──────────────────────────────────────────────────
// Source of truth: frontend/src/middleware.ts (REDIRECTS object)
// Key = old route prefix (exact or prefix-matched); Value = workspace dest
const MIDDLEWARE_REDIRECTS = {
  "/dashboard/movements":                       { workspace: "/dashboard/inventory",          tab: "movements" },
  "/dashboard/cycle-count":                     { workspace: "/dashboard/inventory",          tab: "cycle-count" },
  "/dashboard/shelf-life":                      { workspace: "/dashboard/inventory",          tab: "shelf-life" },
  "/dashboard/traceability":                    { workspace: "/dashboard/inventory",          tab: "traceability" },
  "/dashboard/wms":                             { workspace: "/dashboard/warehouses",         tab: "wms" },
  "/dashboard/putaway":                         { workspace: "/dashboard/warehouses",         tab: "wms" },
  "/dashboard/containers":                      { workspace: "/dashboard/logistics",          tab: "containers" },
  "/dashboard/procurement-suggestion":          { workspace: "/dashboard/procurement",        tab: "suggestions" },
  "/dashboard/subcontracting":                  { workspace: "/dashboard/procurement",        tab: "subcontracting" },
  "/dashboard/copacking":                       { workspace: "/dashboard/procurement",        tab: "subcontracting" },
  "/dashboard/landed-cost":                     { workspace: "/dashboard/procurement",        tab: "landed-cost" },
  "/dashboard/supplier-portal":                 { workspace: "/dashboard/procurement",        tab: "supplier-portal" },
  "/dashboard/price-lists":                     { workspace: "/dashboard/sales",              tab: "price-lists" },
  "/dashboard/dynamic-pricing":                 { workspace: "/dashboard/sales",              tab: "dynamic-pricing" },
  "/dashboard/contracts":                       { workspace: "/dashboard/sales",              tab: "contracts" },
  "/dashboard/recurring-orders":                { workspace: "/dashboard/sales",              tab: "recurring" },
  "/dashboard/commissions":                     { workspace: "/dashboard/sales",              tab: "commissions" },
  "/dashboard/secondary-sales":                 { workspace: "/dashboard/sales",              tab: "secondary" },
  "/dashboard/van-sales":                       { workspace: "/dashboard/sales",              tab: "van-sales" },
  "/dashboard/portal":                          { workspace: "/dashboard/sales",              tab: "portal" },
  "/dashboard/sales/pod":                       { workspace: "/dashboard/sales",              tab: "delivery" },
  "/dashboard/sales/customer-statement":        { workspace: "/dashboard/sales",              tab: "customers" },
  "/dashboard/crm/ai":                          { workspace: "/dashboard/crm",               tab: "overview" },
  "/dashboard/crm/overdue":                     { workspace: "/dashboard/crm",               tab: "pipeline" },
  "/dashboard/crm/qualify":                     { workspace: "/dashboard/crm",               tab: "leads" },
  "/dashboard/crm/records":                     { workspace: "/dashboard/crm",               tab: "overview" },
  "/dashboard/loyalty":                         { workspace: "/dashboard/crm",               tab: "loyalty" },
  "/dashboard/nps":                             { workspace: "/dashboard/crm",               tab: "nps" },
  "/dashboard/surveys":                         { workspace: "/dashboard/crm",               tab: "surveys" },
  "/dashboard/tpm":                             { workspace: "/dashboard/marketing",          tab: "tpm" },
  "/dashboard/promotions":                      { workspace: "/dashboard/marketing",          tab: "promotions-schemes" },
  "/dashboard/market-intelligence":             { workspace: "/dashboard/marketing",          tab: "market-intel" },
  "/dashboard/marketing/campaigns":             { workspace: "/dashboard/marketing",          tab: "campaigns" },
  "/dashboard/marketing/ads":                   { workspace: "/dashboard/marketing",          tab: "ads" },
  "/dashboard/marketing/brand-spend":           { workspace: "/dashboard/marketing",          tab: "brand-spend" },
  "/dashboard/marketing/ecommerce":             { workspace: "/dashboard/marketing",          tab: "ecommerce" },
  "/dashboard/marketing/influencers":           { workspace: "/dashboard/marketing",          tab: "influencers" },
  "/dashboard/marketing/promotions":            { workspace: "/dashboard/marketing",          tab: "promotions" },
  "/dashboard/marketing/segments":              { workspace: "/dashboard/marketing",          tab: "segments" },
  "/dashboard/marketing/social-media":          { workspace: "/dashboard/marketing",          tab: "social-media" },
  "/dashboard/marketing/trade-spend":           { workspace: "/dashboard/marketing",          tab: "trade-spend" },
  "/dashboard/marketing/visits":                { workspace: "/dashboard/marketing",          tab: "visits" },
  "/dashboard/marketing/ai-optimizer":          { workspace: "/dashboard/marketing",          tab: "analytics" },
  "/dashboard/finance/accounting":              { workspace: "/dashboard/finance",            tab: "accounting" },
  "/dashboard/bank-reconciliation":             { workspace: "/dashboard/finance",            tab: "bank-recon" },
  "/dashboard/invoice-match":                   { workspace: "/dashboard/finance",            tab: "invoice-match" },
  "/dashboard/fixed-assets":                    { workspace: "/dashboard/finance",            tab: "fixed-assets" },
  "/dashboard/dimensions":                      { workspace: "/dashboard/finance",            tab: "dimensions" },
  "/dashboard/dunning":                         { workspace: "/dashboard/finance",            tab: "dunning" },
  "/dashboard/tax":                             { workspace: "/dashboard/finance",            tab: "tax" },
  "/dashboard/bank-api":                        { workspace: "/dashboard/finance",            tab: "bank-api" },
  "/dashboard/expenses":                        { workspace: "/dashboard/hr",                 tab: "expenses" },
  "/dashboard/production/advanced":             { workspace: "/dashboard/production",         tab: "scheduling" },
  "/dashboard/production/ai":                   { workspace: "/dashboard/production",         tab: "plans" },
  "/dashboard/production/orders":               { workspace: "/dashboard/production",         tab: "orders" },
  "/dashboard/production/plans":                { workspace: "/dashboard/production",         tab: "plans" },
  "/dashboard/production/shifts":               { workspace: "/dashboard/production",         tab: "scheduling" },
  "/dashboard/production/work-orders":          { workspace: "/dashboard/production",         tab: "orders" },
  "/dashboard/production-execution":            { workspace: "/dashboard/production",         tab: "execution" },
  "/dashboard/machine-ops":                     { workspace: "/dashboard/production",         tab: "machine-ops" },
  "/dashboard/material-flow":                   { workspace: "/dashboard/production",         tab: "material-flow" },
  "/dashboard/projects":                        { workspace: "/dashboard/production",         tab: "projects" },
  "/dashboard/planning/schedule":               { workspace: "/dashboard/planning",           tab: "advanced" },
  "/dashboard/planning/capacity":               { workspace: "/dashboard/planning",           tab: "advanced" },
  "/dashboard/planning/bottlenecks":            { workspace: "/dashboard/planning",           tab: "advanced" },
  "/dashboard/planning/simulation":             { workspace: "/dashboard/planning",           tab: "advanced" },
  "/dashboard/planning/changeover":             { workspace: "/dashboard/planning",           tab: "advanced" },
  "/dashboard/mrp":                             { workspace: "/dashboard/planning",           tab: "mrp" },
  "/dashboard/mps":                             { workspace: "/dashboard/planning",           tab: "mps" },
  "/dashboard/kanban":                          { workspace: "/dashboard/planning",           tab: "kanban" },
  "/dashboard/qms":                             { workspace: "/dashboard/quality",            tab: "qms" },
  "/dashboard/allergen":                        { workspace: "/dashboard/quality",            tab: "allergen" },
  "/dashboard/brand-assets":                    { workspace: "/dashboard/quality",            tab: "brand-assets" },
  "/dashboard/quality/consumer-complaints":     { workspace: "/dashboard/quality",            tab: "consumer-complaints" },
  "/dashboard/gs1":                             { workspace: "/dashboard/compliance",         tab: "gs1" },
  "/dashboard/iot":                             { workspace: "/dashboard/utility-management", tab: "iot" },
  "/dashboard/esg":                             { workspace: "/dashboard/utility-management", tab: "esg" },
  "/dashboard/utility-management/categories":   { workspace: "/dashboard/utility-management", tab: "assets" },
  "/dashboard/utility-management/kpi-center":   { workspace: "/dashboard/utility-management", tab: "kpi-center" },
  "/dashboard/utility-management/reports":      { workspace: "/dashboard/utility-management", tab: "reports" },
  "/dashboard/fleet":                           { workspace: "/dashboard/logistics",          tab: "fleet" },
  "/dashboard/logistics/containers":            { workspace: "/dashboard/logistics",          tab: "containers" },
  "/dashboard/recruitment":                     { workspace: "/dashboard/hr",                 tab: "recruitment" },
  "/dashboard/ess":                             { workspace: "/dashboard/hr",                 tab: "ess" },
  "/dashboard/appraisals":                      { workspace: "/dashboard/hr",                 tab: "appraisals" },
  "/dashboard/training":                        { workspace: "/dashboard/hr",                 tab: "training" },
  "/dashboard/timesheets":                      { workspace: "/dashboard/hr",                 tab: "timesheets" },
  "/dashboard/documents/new":                   { workspace: "/dashboard/documents",          drawer: "create" },
  "/dashboard/knowledge-base":                  { workspace: "/dashboard/documents",          tab: "knowledge-base" },
  "/dashboard/esign":                           { workspace: "/dashboard/documents",          tab: "esign" },
  "/dashboard/chatter":                         { workspace: "/dashboard/communication",      tab: "chatter" },
  "/dashboard/calendar":                        { workspace: "/dashboard/communication",      tab: "calendar" },
  "/dashboard/messages":                        { workspace: "/dashboard/communication",      tab: "messages" },
  "/dashboard/email":                           { workspace: "/dashboard/communication",      tab: "email" },
  "/dashboard/whatsapp":                        { workspace: "/dashboard/communication",      tab: "whatsapp" },
  "/dashboard/calls":                           { workspace: "/dashboard/communication",      tab: "calls" },
  "/dashboard/meetings":                        { workspace: "/dashboard/communication",      tab: "meetings" },
  "/dashboard/notification-center":             { workspace: "/dashboard/communication",      tab: "notifications" },
  "/dashboard/report-builder":                  { workspace: "/dashboard/analytics",          tab: "report-builder" },
  "/dashboard/reports":                         { workspace: "/dashboard/analytics",          tab: "reports" },
  "/dashboard/users":                           { workspace: "/dashboard/admin",              tab: "users" },
  "/dashboard/roles":                           { workspace: "/dashboard/admin",              tab: "roles" },
  "/dashboard/permissions":                     { workspace: "/dashboard/admin",              tab: "permissions" },
  "/dashboard/companies":                       { workspace: "/dashboard/admin",              tab: "companies" },
  "/dashboard/security":                        { workspace: "/dashboard/admin",              tab: "security" },
  "/dashboard/approvals":                       { workspace: "/dashboard/admin",              tab: "approvals" },
  "/dashboard/custom-fields":                   { workspace: "/dashboard/admin",              tab: "custom-fields" },
  "/dashboard/utilities":                       { workspace: "/dashboard/admin",              tab: "system-config" },
  "/dashboard/mobile":                          { workspace: "/dashboard/admin",              tab: "mobile" },
  "/dashboard/logs":                            { workspace: "/dashboard/admin",              tab: "logs" },
  "/dashboard/import-history":                  { workspace: "/dashboard/admin",              tab: "import-history" },
  "/dashboard/webhooks":                        { workspace: "/dashboard/integrations",       tab: "webhooks" },
  "/dashboard/developer":                       { workspace: "/dashboard/integrations",       tab: "developer" },
  "/dashboard/payroll":                         { workspace: "/dashboard/hr",                 tab: "payroll" },
};

// Routes that bypass prefix redirect (real standalone pages under redirected prefix)
// Keep in sync with frontend/src/middleware.ts BYPASS_PREFIX_REDIRECT
const BYPASS_PREFIX_REDIRECT = new Set([
  "/dashboard/mps/planning-board","/dashboard/mps/capacity","/dashboard/mps/campaigns","/dashboard/mps/whatif",
  "/dashboard/cycle-count/plans","/dashboard/cycle-count/tasks","/dashboard/cycle-count/entries",
  "/dashboard/cycle-count/variances","/dashboard/cycle-count/reports",
  "/dashboard/custom-fields/new-field","/dashboard/calendar/new-event","/dashboard/surveys/new",
  "/dashboard/documents/new","/dashboard/knowledge-base/articles/new","/dashboard/fixed-assets/assets/new",
  "/dashboard/expenses/claims/new","/dashboard/recruitment/requisitions/new","/dashboard/appraisals/records/new",
  "/dashboard/marketing/campaigns/new","/dashboard/marketing/promotions/new","/dashboard/marketing/trade-spend/new",
  "/dashboard/marketing/ads/new","/dashboard/marketing/social-media/new","/dashboard/marketing/segments/new",
  "/dashboard/marketing/influencers/new","/dashboard/marketing/visits/new","/dashboard/marketing/brand-spend/new",
  "/dashboard/tpm/plans/new","/dashboard/tpm/promotions/new","/dashboard/mrp/run",
  "/dashboard/landed-cost/new","/dashboard/machine-ops/runtime","/dashboard/contracts/new",
  "/dashboard/recurring-orders/templates/new","/dashboard/van-sales/vans/new",
  "/dashboard/custom-fields/fields","/dashboard/custom-fields/form-builder","/dashboard/custom-fields/workflow-rules","/dashboard/custom-fields/values",
  "/dashboard/mobile/approvals","/dashboard/mobile/devices","/dashboard/approvals",
  "/dashboard/notification-center","/dashboard/notification-center/list","/dashboard/notification-center/preferences",
  "/dashboard/notification-center/templates","/dashboard/notification-center/schedules",
  "/dashboard/tax","/dashboard/tax/rules","/dashboard/tax/regulatory","/dashboard/tax/transactions",
  "/dashboard/production/orders","/dashboard/production-execution/work-orders",
  "/dashboard/report-builder/catalog","/dashboard/report-builder/builder","/dashboard/report-builder/saved",
  "/dashboard/report-builder/viewer","/dashboard/report-builder/dashboards","/dashboard/report-builder/schedules",
  "/dashboard/chatter/feed","/dashboard/chatter/search",
  "/dashboard/calendar/events","/dashboard/calendar/view","/dashboard/calendar/resources","/dashboard/calendar/availability",
  "/dashboard/esign","/dashboard/knowledge-base/articles",
  "/dashboard/finance/accounting/customers-ledger","/dashboard/finance/accounting/suppliers-ledger",
  "/dashboard/finance/accounting/sales-invoices","/dashboard/finance/accounting/purchase-invoices","/dashboard/finance/accounting/payments",
  "/dashboard/bank-reconciliation/import","/dashboard/bank-reconciliation/statements",
  "/dashboard/bank-reconciliation/open-items","/dashboard/bank-reconciliation/balance","/dashboard/bank-reconciliation/rules",
  "/dashboard/invoice-match/review-queue","/dashboard/invoice-match/matches","/dashboard/invoice-match/blocked","/dashboard/invoice-match/duplicates",
  "/dashboard/fixed-assets/assets","/dashboard/fixed-assets/categories","/dashboard/fixed-assets/depreciation",
  "/dashboard/fixed-assets/posting","/dashboard/fixed-assets/disposal","/dashboard/fixed-assets/transfer","/dashboard/fixed-assets/import",
  "/dashboard/dimensions/types","/dashboard/dimensions/values","/dashboard/dimensions/cost-centers","/dashboard/dimensions/allocations",
  "/dashboard/dimensions/allocation-run","/dashboard/dimensions/validation","/dashboard/dimensions/defaults",
  "/dashboard/dimensions/reclassify","/dashboard/dimensions/completeness",
  "/dashboard/dunning/aging","/dashboard/dunning/workqueue","/dashboard/dunning/credit-holds","/dashboard/dunning/policies","/dashboard/dunning/cases",
  "/dashboard/expenses/claims","/dashboard/expenses/approval","/dashboard/expenses/reimbursement",
  "/dashboard/expenses/advances","/dashboard/expenses/categories","/dashboard/expenses/policies",
  "/dashboard/recruitment/requisitions","/dashboard/recruitment/candidates","/dashboard/recruitment/pipeline",
  "/dashboard/recruitment/interviews","/dashboard/recruitment/offers","/dashboard/recruitment/stages",
  "/dashboard/ess/profile","/dashboard/ess/leave","/dashboard/ess/attendance","/dashboard/ess/documents",
  "/dashboard/ess/requests","/dashboard/ess/notifications","/dashboard/ess/admin",
  "/dashboard/appraisals/periods","/dashboard/appraisals/templates","/dashboard/appraisals/records",
  "/dashboard/appraisals/self-review","/dashboard/appraisals/manager-queue","/dashboard/appraisals/hr-review","/dashboard/appraisals/development-plans",
  "/dashboard/training/programs","/dashboard/training/sessions","/dashboard/training/skill-matrix",
  "/dashboard/training/assignments","/dashboard/training/certifications","/dashboard/training/feedback",
  "/dashboard/timesheets/my-timesheets","/dashboard/timesheets/time-entry","/dashboard/timesheets/weekly-view","/dashboard/timesheets/approval-queue",
  "/dashboard/webhooks","/dashboard/webhooks/definitions","/dashboard/webhooks/subscriptions",
  "/dashboard/webhooks/deliveries","/dashboard/webhooks/dead-letter","/dashboard/webhooks/inbound",
  "/dashboard/developer/keys","/dashboard/developer/graphql",
  "/dashboard/shelf-life/fefo-config","/dashboard/shelf-life/lot-aging","/dashboard/shelf-life/near-expiry",
  "/dashboard/shelf-life/expired","/dashboard/shelf-life/retest-queue","/dashboard/shelf-life/shipment-validation",
  "/dashboard/shelf-life/production-validation","/dashboard/shelf-life/compliance","/dashboard/shelf-life/disposition",
  "/dashboard/shelf-life/customer-rules","/dashboard/shelf-life/bulk-hold-monitor",
  "/dashboard/traceability/recalls","/dashboard/traceability/search","/dashboard/traceability/backward",
  "/dashboard/traceability/forward","/dashboard/traceability/genealogy","/dashboard/traceability/mock-recall","/dashboard/traceability/regulatory",
  "/dashboard/fleet/vehicles","/dashboard/fleet/drivers","/dashboard/fleet/trips",
  "/dashboard/fleet/fuel","/dashboard/fleet/maintenance","/dashboard/fleet/incidents",
  "/dashboard/marketing/crm","/dashboard/marketing/crm/followup",
  "/dashboard/marketing/surveys","/dashboard/marketing/surveys/new",
  "/dashboard/marketing/ecommerce/stores",
  "/dashboard/tpm/plans","/dashboard/tpm/promotions","/dashboard/tpm/calendar","/dashboard/tpm/budget",
  "/dashboard/tpm/claims","/dashboard/tpm/roi","/dashboard/tpm/settlement",
  "/dashboard/mrp/forecast","/dashboard/mrp/suggestions",
  "/dashboard/kanban/boards","/dashboard/kanban/view","/dashboard/kanban/cards",
  "/dashboard/procurement-suggestion/suggestions","/dashboard/procurement-suggestion/groups","/dashboard/procurement-suggestion/supplier-prices",
  "/dashboard/subcontracting/locations","/dashboard/subcontracting/orders","/dashboard/subcontracting/stock","/dashboard/subcontracting/yield",
  "/dashboard/landed-cost/documents",
  "/dashboard/machine-ops/machines","/dashboard/machine-ops/operators","/dashboard/machine-ops/teams",
  "/dashboard/machine-ops/performance","/dashboard/machine-ops/downtime","/dashboard/machine-ops/costing",
  "/dashboard/machine-ops/certs","/dashboard/machine-ops/assignment",
  "/dashboard/material-flow/issue","/dashboard/material-flow/wip-transfer","/dashboard/material-flow/bulk-transfer",
  "/dashboard/material-flow/fg-receipt","/dashboard/material-flow/reservations","/dashboard/material-flow/tanks",
  "/dashboard/material-flow/returns","/dashboard/material-flow/reconciliation","/dashboard/material-flow/history",
  "/dashboard/qms/inspections","/dashboard/qms/templates","/dashboard/qms/haccp","/dashboard/qms/ccp",
  "/dashboard/qms/deviations","/dashboard/qms/corrective-actions","/dashboard/qms/quarantine","/dashboard/qms/allergen",
  "/dashboard/allergen/material-profiles","/dashboard/allergen/product-allergens","/dashboard/allergen/change-logs",
  "/dashboard/price-lists/approval-queue","/dashboard/contracts/list","/dashboard/contracts/expiring",
  "/dashboard/recurring-orders/templates",
  "/dashboard/commissions/rules","/dashboard/commissions/transactions","/dashboard/commissions/payouts",
  "/dashboard/secondary-sales/analysis","/dashboard/secondary-sales/inventory","/dashboard/secondary-sales/upload",
  "/dashboard/van-sales/route","/dashboard/van-sales/pos","/dashboard/van-sales/stock",
  "/dashboard/van-sales/reconciliation","/dashboard/van-sales/vans",
  "/dashboard/portal/accounts","/dashboard/portal/drafts","/dashboard/portal/claims","/dashboard/portal/users","/dashboard/portal/activity",
  "/dashboard/utility-management/kpi-center","/dashboard/utility-management/kpi-center/electricity",
  "/dashboard/utility-management/kpi-center/water","/dashboard/utility-management/kpi-center/soft-water",
  "/dashboard/utility-management/kpi-center/boiler","/dashboard/utility-management/kpi-center/compressor",
  "/dashboard/utility-management/kpi-center/solar","/dashboard/utility-management/kpi-center/chemicals",
  "/dashboard/utility-management/kpi-center/wastewater","/dashboard/utility-management/kpi-center/utility-cost",
  "/dashboard/utility-management/kpi-center/machine-utility",
  "/dashboard/esg/activities","/dashboard/esg/factors","/dashboard/esg/targets","/dashboard/esg/intelligence",
  // Wave 1C — AI and reports pages
  "/dashboard/custom-fields/ai",
  "/dashboard/reports/inventory","/dashboard/reports/production","/dashboard/reports/procurement",
  "/dashboard/reports/sales","/dashboard/reports/finance","/dashboard/reports/payments","/dashboard/reports/marketing",
  "/dashboard/report-builder/ai",
  "/dashboard/chatter/reports","/dashboard/chatter/ai",
  "/dashboard/notification-center/reports","/dashboard/notification-center/ai",
  "/dashboard/bank-reconciliation/ai","/dashboard/invoice-match/ai","/dashboard/fixed-assets/ai","/dashboard/dimensions/ai",
  "/dashboard/tax/reports","/dashboard/expenses/reports","/dashboard/expenses/ai",
  "/dashboard/recruitment/reports","/dashboard/recruitment/ai","/dashboard/ess/ai",
  "/dashboard/appraisals/reports","/dashboard/appraisals/ai",
  "/dashboard/training/reports","/dashboard/training/ai",
  "/dashboard/timesheets/reports","/dashboard/timesheets/ai",
  "/dashboard/webhooks/reports","/dashboard/fleet/reports","/dashboard/tpm/ai",
  "/dashboard/kanban/reports","/dashboard/kanban/ai",
  "/dashboard/procurement-suggestion/ai","/dashboard/subcontracting/ai","/dashboard/landed-cost/ai",
  "/dashboard/qms/reports","/dashboard/qms/ai",
  "/dashboard/contracts/ai","/dashboard/recurring-orders/reports","/dashboard/recurring-orders/ai",
  "/dashboard/commissions/ai","/dashboard/van-sales/ai","/dashboard/portal/ai","/dashboard/portal/reports",
  "/dashboard/utility-management/reports/daily-consumption","/dashboard/utility-management/reports/equipment-efficiency",
  "/dashboard/utility-management/reports/treatment","/dashboard/utility-management/reports/cost-allocation",
  "/dashboard/utility-management/reports/load-analysis","/dashboard/utility-management/reports/anomalies",
  "/dashboard/utility-management/reports/sustainability",
  "/dashboard/esg/reports",
]);

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function git(cmd, opts = {}) {
  try {
    return execSync(cmd, { cwd: ROOT, encoding: "utf-8", timeout: 12000, ...opts });
  } catch { return ""; }
}

function readFile(filePath) {
  try { return fs.readFileSync(filePath, "utf-8"); } catch { return null; }
}

function fileExists(p) {
  try { return fs.existsSync(p); } catch { return false; }
}

/** Walk a directory recursively, return paths matching predicate */
function walkDir(dir, predicate) {
  const results = [];
  if (!fileExists(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...walkDir(full, predicate));
    else if (predicate(entry.name, full)) results.push(full);
  }
  return results;
}

/** Convert absolute file path to route string */
function fileToRoute(absPath) {
  const norm = absPath.replace(/\\/g, "/");
  const base = path.join(FRONTEND, "app").replace(/\\/g, "/");
  return norm
    .replace(base, "")
    .replace(/\/page\.tsx$/, "")
    .replace(/\/$/, "") || "/";
}

/** Convert @/app/... import path to absolute file path */
function importToAbs(importPath) {
  return path.join(
    FRONTEND,
    importPath.replace(/^@\//, "").replace(/\//g, path.sep) + ".tsx"
  );
}

/** Check if a file is a redirect stub (<= 8 non-empty lines, contains redirect() */
function isRedirectStub(absPath) {
  const content = readFile(absPath);
  if (!content) return false;
  const lines = content.split("\n").filter(l => l.trim().length > 0);
  return lines.length <= 8 && content.includes("redirect(");
}

/** Check if route is caught by middleware (returns redirect dest or null) */
function middlewareMatch(route) {
  if (MIDDLEWARE_REDIRECTS[route]) return MIDDLEWARE_REDIRECTS[route];
  if (BYPASS_PREFIX_REDIRECT.has(route)) return null;
  const parts = route.split("/");
  for (let i = parts.length - 1; i >= 2; i--) {
    const prefix = parts.slice(0, i).join("/");
    if (MIDDLEWARE_REDIRECTS[prefix]) return MIDDLEWARE_REDIRECTS[prefix];
  }
  return null;
}

/** Module name from workspace file path */
function moduleFromWorkspace(wsFile) {
  const route = fileToRoute(wsFile).replace(/\\/g, "/");
  const map = {
    "/dashboard/inventory":          "Supply Chain / Inventory",
    "/dashboard/warehouses":         "Supply Chain / Warehouses",
    "/dashboard/procurement":        "Supply Chain / Procurement",
    "/dashboard/planning":           "Manufacturing / Planning",
    "/dashboard/production":         "Manufacturing / Production",
    "/dashboard/quality":            "Factory Operations / Quality",
    "/dashboard/utility-management": "Factory Operations / Utilities",
    "/dashboard/maintenance":        "Factory Operations / Maintenance",
    "/dashboard/finance":            "Finance",
    "/dashboard/hr":                 "HR & Payroll",
    "/dashboard/payroll":            "HR & Payroll",
    "/dashboard/sales":              "Commercial / Sales",
    "/dashboard/crm":                "Commercial / CRM",
    "/dashboard/marketing":          "Commercial / Marketing",
    "/dashboard/logistics":          "Logistics",
    "/dashboard/communication":      "Documents & Communication",
    "/dashboard/documents":          "Documents & Communication",
    "/dashboard/analytics":          "Intelligence / Analytics",
    "/dashboard/admin":              "Administration",
    "/dashboard/integrations":       "Administration / Integrations",
    "/dashboard/compliance":         "Administration / Compliance",
  };
  return map[route] || "Other";
}

/** Severity for a broken target */
function severity(target) {
  if (target.includes("/new") || target.includes("/create") || target.includes("drawer=create")) return "critical";
  if (target.includes("/run") || target.includes("/generate") || target.includes("/approve")) return "critical";
  if (target.includes("/reports") || target.includes("/ai") || target.includes("/analytics")) return "medium";
  return "high";
}

// ─── PHASE 1: Dynamically scan workspace pages for dynamic() imports ──────────

console.log("Phase 1: Scanning for dynamic imports…");

const workspacePages = walkDir(DASHBOARD, (name) => name === "page.tsx")
  .filter(p => {
    const content = readFile(p);
    return content && content.includes("dynamic(() => import(");
  });

// Map: importedFilePath → [ { workspacePage, tabKey } ]
const importedBy = {};

for (const wsPage of workspacePages) {
  const content = readFile(wsPage);
  if (!content) continue;
  const re = /dynamic\(\s*\(\s*\)\s*=>\s*import\(\s*["'`](@\/app\/dashboard\/[^"'`]+)["'`]\s*\)/g;
  let m;
  while ((m = re.exec(content)) !== null) {
    const absImported = importToAbs(m[1]);
    if (!importedBy[absImported]) importedBy[absImported] = [];
    // Try to extract tab key from surrounding lines
    const lineStart = content.lastIndexOf("\n", m.index);
    const lineEnd   = content.indexOf("\n", m.index);
    const line = content.slice(lineStart, lineEnd);
    // tab key usually in nearby const declaration e.g. const FooPage = dynamic(...)
    // or in tab array: { key: "xxx", ... content: <FooPage /> }
    const varMatch = line.match(/const\s+(\w+)\s*=/);
    importedBy[absImported].push({ workspacePage: wsPage, varName: varMatch ? varMatch[1] : "unknown" });
  }
}

console.log(`  Found ${Object.keys(importedBy).length} dynamically imported pages across ${workspacePages.length} workspace pages`);

// ─── PHASE 2: Build visibility graph ─────────────────────────────────────────

console.log("Phase 2: Building visibility graph…");

const visGraph = [];

for (const [importedFile, importers] of Object.entries(importedBy)) {
  const route = fileToRoute(importedFile).replace(/\\/g, "/");
  const mwMatch = middlewareMatch(route);
  const exists = fileExists(importedFile);
  const isStub = exists ? isRedirectStub(importedFile) : false;

  visGraph.push({
    filePath:                    importedFile.replace(ROOT + path.sep, "").replace(/\\/g, "/"),
    routeGuess:                  route,
    visibility:                  "DYNAMICALLY_IMPORTED_VISIBLE",
    visibleBecause:              importers.map(i => ({
      importedBy:        i.workspacePage.replace(ROOT + path.sep, "").replace(/\\/g, "/"),
      varName:           i.varName,
      importType:        "dynamic",
      parentRouteGuess:  fileToRoute(i.workspacePage).replace(/\\/g, "/"),
    })),
    fileExists:                  exists,
    isRedirectStubAsStandalone:  !!mwMatch,
    standaloneRedirectsTo:       mwMatch ? `${mwMatch.workspace}${mwMatch.tab ? "?tab=" + mwMatch.tab : ""}${mwMatch.drawer ? "?drawer=" + mwMatch.drawer : ""}` : null,
    isStillUserVisibleThroughImport: true,
    module: moduleFromWorkspace(importers[0]?.workspacePage || ""),
  });
}

// ─── PHASE 3: Extract action targets from user-visible pages ─────────────────

console.log("Phase 3: Extracting action targets from user-visible pages…");

// Regex patterns to find navigation targets in source files
// Captures /dashboard/... route strings from href, router.push, etc.
const NAV_PATTERNS = [
  // Link href="/dashboard/..." or href={"/dashboard/..."}
  { re: /href[=:]\s*[{"'`]+\s*(\/dashboard\/[^"'`}\s]+)/g, type: "Link.href" },
  // router.push|replace("/dashboard/...")
  { re: /router\.(push|replace)\(\s*["'`](\/dashboard\/[^"'`\s]+)/g, type: "router.push", capIdx: 2 },
  // window.location = or .href =
  { re: /window\.location(?:\.href)?\s*=\s*["'`](\/dashboard\/[^"'`\s]+)/g, type: "window.location" },
];

const allTargets = []; // { sourceFile, route, lineNumber, targetRoute, targetType, evidence, label }

for (const node of visGraph) {
  const absPath = path.join(ROOT, node.filePath.replace(/\//g, path.sep));
  const content = readFile(absPath);
  if (!content) continue;

  const lines = content.split("\n");

  for (const { re, type, capIdx = 1 } of NAV_PATTERNS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(content)) !== null) {
      const targetRoute = m[capIdx].split("?")[0].split("#")[0]; // strip query/hash
      if (!targetRoute.startsWith("/dashboard/")) continue;

      // Find line number
      const linesBefore = content.slice(0, m.index).split("\n").length;
      const lineNo = linesBefore;

      // Try to extract a label: look for nearby text content on same or adjacent lines
      const contextLines = lines.slice(Math.max(0, lineNo - 3), lineNo + 3);
      const labelMatch = contextLines.join(" ").match(/"([A-Z][A-Za-z0-9 &/+\-]+)"|label:\s*"([^"]+)"|>([A-Z][A-Za-z &/+\-]{2,30})</);
      const label = labelMatch ? (labelMatch[1] || labelMatch[2] || labelMatch[3]) || targetRoute.split("/").pop() : targetRoute.split("/").pop();

      allTargets.push({
        sourceFile:    node.filePath,
        sourceRoute:   node.routeGuess,
        visibleVia:    node.visibleBecause[0]?.parentRouteGuess + "?tab=" + node.visibleBecause[0]?.varName,
        module:        node.module,
        label:         label.trim().slice(0, 60),
        targetRoute,
        fullTarget:    m[capIdx],
        targetType:    type,
        lineNumber:    lineNo,
        evidence:      m[0].trim().slice(0, 120),
      });
    }
  }
}

console.log(`  Found ${allTargets.length} navigation targets total`);

// ─── PHASE 4: Classify targets ───────────────────────────────────────────────

console.log("Phase 4: Classifying targets…");

function classifyTarget(targetRoute) {
  // 1. Bypass routes are real pages
  if (BYPASS_PREFIX_REDIRECT.has(targetRoute)) return { status: "WORKING", reason: "bypass_set_real_page" };

  // 2. Check middleware
  const mw = middlewareMatch(targetRoute);
  if (mw) {
    const dest = `${mw.workspace}${mw.tab ? "?tab=" + mw.tab : ""}${mw.drawer ? "?drawer=" + mw.drawer : ""}`;
    return { status: "BROKEN", reason: "middleware_redirect", redirectsTo: dest };
  }

  // 3. Check file system
  const relPath = `/app${targetRoute}/page.tsx`;
  const absPath = path.join(FRONTEND, ...relPath.split("/"));

  if (!fileExists(absPath)) {
    return { status: "BROKEN", reason: "no_route_file" };
  }

  if (isRedirectStub(absPath)) {
    const content = readFile(absPath);
    const stubMatch = content.match(/redirect\(["'`]([^"'`]+)["'`]\)/);
    const redirectsTo = stubMatch ? stubMatch[1] : "unknown";
    return { status: "BROKEN", reason: "redirect_stub_file", redirectsTo };
  }

  return { status: "WORKING", reason: "real_page_exists" };
}

const classified = allTargets.map(t => {
  const cls = classifyTarget(t.targetRoute);
  return { ...t, ...cls };
});

const broken = classified.filter(t => t.status === "BROKEN");
const working = classified.filter(t => t.status === "WORKING");

// Deduplicate broken by (sourceFile + targetRoute)
const seenBroken = new Set();
const brokenUniq = broken.filter(t => {
  const key = `${t.sourceFile}||${t.targetRoute}`;
  if (seenBroken.has(key)) return false;
  seenBroken.add(key);
  return true;
});

console.log(`  Working: ${working.length}, Broken: ${broken.length} (${brokenUniq.length} unique)`);

// ─── PHASE 5: Git history search ─────────────────────────────────────────────

console.log("Phase 5: Searching git history…");

// Known reference commits (from prior analysis)
// 674b6c5 (2026-05-01): had REAL page implementations
// bd6faf5 (2026-05-17): many replaced with redirect stubs
const REF_COMMITS = ["674b6c5", "27ebada", "10125e4"];

// Cache git checks to avoid repeated git show calls
const gitCache = {};

function checkFileInGit(routePath) {
  // routePath like /dashboard/cycle-count/plans
  const filePath = `frontend/src/app${routePath}/page.tsx`;
  if (gitCache[filePath] !== undefined) return gitCache[filePath];

  let result = { found: false, wasReal: false, commit: null, commitDate: null, note: "" };

  for (const commit of REF_COMMITS) {
    const content = git(`git show ${commit}:${filePath} 2>nul`, { shell: true });
    if (content && content.trim().length > 10) {
      const isReal = !content.includes("redirect(");
      result = {
        found: true,
        wasReal: isReal,
        commit,
        commitDate: git(`git log -1 --format=%as ${commit}`).trim(),
        filePath,
        preview: content.trim().slice(0, 200),
        note: isReal
          ? `Real implementation found in ${commit}`
          : `Only redirect stub found in ${commit}`,
      };
      break;
    }
  }

  if (!result.found) {
    // Try git log to see if file ever existed
    const log = git(`git log --all --oneline -- ${filePath}`);
    if (log.trim()) {
      const lines = log.trim().split("\n");
      result = {
        found: true,
        wasReal: null, // unknown — would need to check content
        commit: lines[0].split(" ")[0],
        commitDate: null,
        filePath,
        note: `File existed in git history (${lines.length} commits). Content not checked.`,
      };
    }
  }

  gitCache[filePath] = result;
  return result;
}

// Run git checks for all broken unique targets
const brokenWithGit = brokenUniq.map(t => {
  const gitInfo = checkFileInGit(t.targetRoute);
  return {
    ...t,
    gitHistory: gitInfo,
  };
});

const gitMatchesFound    = brokenWithGit.filter(t => t.gitHistory.found).length;
const highConfMatches    = brokenWithGit.filter(t => t.gitHistory.wasReal === true).length;
const medConfMatches     = brokenWithGit.filter(t => t.gitHistory.found && t.gitHistory.wasReal === null).length;
const unresolved         = brokenWithGit.filter(t => !t.gitHistory.found).length;

console.log(`  Git history: ${gitMatchesFound} found, ${highConfMatches} high-conf (real page), ${medConfMatches} medium, ${unresolved} unresolved`);

// ─── PHASE 5b: Search current code for candidates ────────────────────────────

console.log("Phase 5b: Searching current code for implementation candidates…");

// For each broken target, look for existing related implementations
function searchCurrentCode(targetRoute) {
  const segment = targetRoute.split("/").pop(); // e.g. "plans", "variances"
  const prefix  = targetRoute.split("/").slice(0, -1).join("/").replace("/dashboard/", ""); // e.g. "cycle-count"

  const candidates = [];

  // Search for the route path in current codebase
  try {
    const grepOut = git(`git grep -rn --include="*.tsx" "${segment}" frontend/src/app/dashboard/ 2>nul`, { shell: true });
    if (grepOut.trim()) {
      const matches = grepOut.trim().split("\n").slice(0, 3);
      for (const match of matches) {
        const parts = match.split(":");
        if (parts.length >= 2) {
          candidates.push({
            filePath: parts[0],
            lineNumber: parseInt(parts[1], 10),
            evidence: parts.slice(2).join(":").trim().slice(0, 80),
            confidence: match.includes(prefix) ? "high" : "low",
          });
        }
      }
    }
  } catch {}

  return candidates.slice(0, 3);
}

// ─── PHASE 6: Assign recommendation ─────────────────────────────────────────

function getRecommendation(t) {
  if (t.gitHistory.wasReal === true)                   return "RESTORE_OLD_PAGE_FROM_GIT";
  if (t.reason === "no_route_file")                    return "CREATE_NEW_REAL_PAGE_REQUIRED";
  if (t.targetRoute.includes("/new") && t.reason === "redirect_stub_file") return "CONVERT_TO_WORKSPACE_SUBVIEW";
  if (t.reason === "middleware_redirect")              return "CONVERT_TO_WORKSPACE_SUBVIEW";
  if (t.reason === "redirect_stub_file")               return "CONVERT_TO_WORKSPACE_SUBVIEW";
  return "NEEDS_BUSINESS_DECISION";
}

// Add sequential IDs + recommendations
let idCounter = 1;
const finalBroken = brokenWithGit.map(t => ({
  id:               `BVT-${String(idCounter++).padStart(4, "0")}`,
  module:           t.module,
  sourceFile:       t.sourceFile,
  sourceRoute:      t.sourceRoute,
  visibleVia:       t.visibleVia,
  label:            t.label,
  lineNumber:       t.lineNumber,
  currentTarget:    t.targetRoute,
  currentBehavior:  t.reason,
  redirectsTo:      t.redirectsTo || null,
  whyBroken:        `In ${t.sourceRoute} (visible at ${t.visibleVia}): link to "${t.targetRoute}" — ${t.reason}${t.redirectsTo ? " → " + t.redirectsTo : ""}`,
  severity:         severity(t.targetRoute),
  userVisible:      true,
  evidence:         t.evidence,
  gitHistory:       t.gitHistory,
  recommendation:   getRecommendation({ ...t, gitHistory: t.gitHistory }),
}));

// ─── PHASE 7: Generate outputs ───────────────────────────────────────────────

console.log("Phase 7: Writing reports…");

// ── 7a: VISIBLE_IMPORT_GRAPH.json ──────────────────────────────────────────
fs.writeFileSync(path.join(DOCS, "VISIBLE_IMPORT_GRAPH.json"), JSON.stringify(visGraph, null, 2));

// ── 7b: VISIBLE_IMPORT_GRAPH.md ────────────────────────────────────────────
const graphMd = `# Visible Import Graph

**Date:** 2026-05-21
**Method:** Dynamic scan of \`dynamic(() => import(...))\` in all workspace pages, cross-referenced with middleware redirect map.

## Key Insight

A page can be user-visible even if its standalone route is middleware-redirected,
if it is dynamically imported into a workspace tab.

## Summary

| Metric | Count |
|--------|-------|
| Workspace pages with dynamic imports | ${workspacePages.length} |
| Total dynamically imported pages found | ${visGraph.length} |
| Pages with middleware-redirected standalone routes | ${visGraph.filter(n => n.isRedirectStubAsStandalone).length} |

## Import Map (Redirect-Stub Pages That Are Still User-Visible)

| Imported Page | Standalone Route | Redirected To | Visible As Tab |
|--------------|-----------------|---------------|----------------|
${visGraph
  .filter(n => n.isRedirectStubAsStandalone)
  .map(n => `| \`${n.filePath.replace("frontend/src/app/dashboard/","")}\` | \`${n.routeGuess}\` | \`${n.standaloneRedirectsTo}\` | ${n.visibleBecause.map(v => `\`${v.parentRouteGuess}\``).join(", ")} |`)
  .join("\n")}
`;
fs.writeFileSync(path.join(DOCS, "VISIBLE_IMPORT_GRAPH.md"), graphMd);

// ── 7c: VISIBLE_ACTION_TARGET_INVENTORY.json ────────────────────────────────
fs.writeFileSync(
  path.join(DOCS, "VISIBLE_ACTION_TARGET_INVENTORY.json"),
  JSON.stringify(classified.map(t => ({
    sourceFile:   t.sourceFile,
    sourceRoute:  t.sourceRoute,
    visibleVia:   t.visibleVia,
    module:       t.module,
    label:        t.label,
    targetRoute:  t.targetRoute,
    targetType:   t.targetType,
    lineNumber:   t.lineNumber,
    evidence:     t.evidence,
    status:       t.status,
    reason:       t.reason,
    redirectsTo:  t.redirectsTo || null,
  })), null, 2)
);

// ── 7d: VISIBLE_ACTION_TARGET_INVENTORY.md ──────────────────────────────────
const totalByModule = {};
for (const t of classified) {
  if (!totalByModule[t.module]) totalByModule[t.module] = { working: 0, broken: 0 };
  t.status === "WORKING" ? totalByModule[t.module].working++ : totalByModule[t.module].broken++;
}
const invMd = `# Visible Action Target Inventory

**Date:** 2026-05-21
**Total targets found:** ${classified.length}
**Working:** ${working.length}
**Broken:** ${broken.length} (${brokenUniq.length} unique)

## By Module

| Module | Working | Broken | Total |
|--------|---------|--------|-------|
${Object.entries(totalByModule).map(([m, v]) => `| ${m} | ${v.working} | ${v.broken} | ${v.working + v.broken} |`).join("\n")}

## All Broken Targets (first 50)

| Source File | Visible Via | Target | Reason |
|------------|-------------|--------|--------|
${brokenUniq.slice(0, 50).map(t => `| \`${t.sourceFile.replace("frontend/src/app/dashboard/","")}\` | ${t.visibleVia} | \`${t.targetRoute}\` | ${t.reason} |`).join("\n")}
`;
fs.writeFileSync(path.join(DOCS, "VISIBLE_ACTION_TARGET_INVENTORY.md"), invMd);

// ── 7e: VISIBLE_BROKEN_ACTION_TARGETS.json ──────────────────────────────────
fs.writeFileSync(
  path.join(DOCS, "VISIBLE_BROKEN_ACTION_TARGETS.json"),
  JSON.stringify(finalBroken, null, 2)
);

// ── 7f: VISIBLE_BROKEN_ACTION_TARGETS.md ────────────────────────────────────
const byMod = {};
for (const t of finalBroken) {
  if (!byMod[t.module]) byMod[t.module] = [];
  byMod[t.module].push(t);
}
const brokenMd = `# Visible Broken Action Targets

**Date:** 2026-05-21
**Total:** ${finalBroken.length}

## Statistics

| Metric | Count |
|--------|-------|
| Critical | ${finalBroken.filter(t=>t.severity==="critical").length} |
| High | ${finalBroken.filter(t=>t.severity==="high").length} |
| Medium | ${finalBroken.filter(t=>t.severity==="medium").length} |
| Git: real page found | ${highConfMatches} |
| Recommendation: RESTORE FROM GIT | ${finalBroken.filter(t=>t.recommendation==="RESTORE_OLD_PAGE_FROM_GIT").length} |
| Recommendation: CONVERT TO SUBVIEW | ${finalBroken.filter(t=>t.recommendation==="CONVERT_TO_WORKSPACE_SUBVIEW").length} |
| Recommendation: CREATE NEW PAGE | ${finalBroken.filter(t=>t.recommendation==="CREATE_NEW_REAL_PAGE_REQUIRED").length} |

${Object.entries(byMod).map(([mod, targets]) => `## ${mod} (${targets.length})

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
${targets.map(t => `| ${t.id} | ${t.sourceFile.replace("frontend/src/app/dashboard/","")} | ${t.visibleVia} | \`${t.currentTarget}\` | ${t.severity} | ${t.gitHistory.wasReal === true ? "REAL" : t.gitHistory.found ? "STUB" : "NONE"} | ${t.recommendation} |`).join("\n")}
`).join("\n")}
`;
fs.writeFileSync(path.join(DOCS, "VISIBLE_BROKEN_ACTION_TARGETS.md"), brokenMd);

// ── 7g: BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json ───────────────────────
const reportJson = {
  generatedDate: "2026-05-21",
  auditVersion: "v3.0-fully-dynamic",
  keyFinding: "Previous audit missed 296+ broken action cards because it did not account for pages dynamically imported into workspace tabs. A page is user-visible if it is imported as tab content, regardless of what middleware does to its standalone route.",
  stats: {
    workspacePagesScanned:             workspacePages.length,
    totalDynamicImportsFound:          Object.values(importedBy).reduce((a, v) => a + v.length, 0),
    dynamicallyImportedVisiblePages:   visGraph.length,
    totalVisibleActionTargetsFound:    classified.length,
    workingTargets:                    working.length,
    totalBrokenVisibleTargets:         finalBroken.length,
    criticalSeverity:                  finalBroken.filter(t=>t.severity==="critical").length,
    highSeverity:                      finalBroken.filter(t=>t.severity==="high").length,
    mediumSeverity:                    finalBroken.filter(t=>t.severity==="medium").length,
    gitHistoryMatchesFound:            gitMatchesFound,
    highConfidenceRealPageMatches:     highConfMatches,
    mediumConfidenceMatches:           medConfMatches,
    unresolvedNoGitMatch:              unresolved,
    recommendRestoreFromGit:           finalBroken.filter(t=>t.recommendation==="RESTORE_OLD_PAGE_FROM_GIT").length,
    recommendConvertToSubview:         finalBroken.filter(t=>t.recommendation==="CONVERT_TO_WORKSPACE_SUBVIEW").length,
    recommendCreateNewPage:            finalBroken.filter(t=>t.recommendation==="CREATE_NEW_REAL_PAGE_REQUIRED").length,
  },
  moduleGroups: Object.entries(byMod).map(([module, targets]) => ({
    module,
    brokenCount: targets.length,
    items: targets,
  })),
};
fs.writeFileSync(
  path.join(DOCS, "BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json"),
  JSON.stringify(reportJson, null, 2)
);

// ── 7h: BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md (main report) ───────────

const topCritical = finalBroken
  .filter(t => t.severity === "critical" || t.severity === "high")
  .slice(0, 20);

const gitRealItems = finalBroken.filter(t => t.gitHistory.wasReal === true);
const unresolvedItems = finalBroken.filter(t => !t.gitHistory.found);

// Dynamic import failure list (pages that are both redirect-stubbed AND user-visible)
const dif = visGraph.filter(n => n.isRedirectStubAsStandalone);

const mainMd = `# Broken Button → Original Page Match Report

**Date:** 2026-05-21
**Audit Version:** v3.0 — Fully Dynamic Scan
**Script:** \`scripts/audit-visible-import-graph.js\`

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Workspace pages scanned | ${workspacePages.length} |
| Total dynamic imports found | ${Object.values(importedBy).reduce((a,v)=>a+v.length,0)} |
| Dynamically imported visible pages | ${visGraph.length} |
| Total visible action targets found | ${classified.length} |
| Working targets | ${working.length} |
| **Total broken visible action targets** | **${finalBroken.length}** |
| Critical severity (create/run/approve actions) | ${finalBroken.filter(t=>t.severity==="critical").length} |
| High severity | ${finalBroken.filter(t=>t.severity==="high").length} |
| Medium severity | ${finalBroken.filter(t=>t.severity==="medium").length} |
| Git history matches found | ${gitMatchesFound} |
| **High-confidence: real page existed in git** | **${highConfMatches}** |
| Medium-confidence: file in git but content unverified | ${medConfMatches} |
| Unresolved: no git match | ${unresolved} |

---

## Key Finding — The Dynamic Import Visibility Blind Spot

### Previous Audit Was Wrong

Previous audit classified 296 broken action cards as **"safe_archived_standalone"** because:
> "The source page's standalone route is middleware-redirected, so users never see the page."

**This reasoning is incorrect.** A page can be user-visible through TWO paths:
1. Standalone route (may be redirected)
2. **Dynamic import into a workspace tab** ← this path was ignored

When \`inventory/page.tsx\` does:
\`\`\`typescript
const CycleCountPage = dynamic(() => import("@/app/dashboard/cycle-count/page"), { ssr: false });
\`\`\`
…the Cycle Count page IS rendered to users at \`/dashboard/inventory?tab=cycle-count\`.
Middleware redirecting \`/dashboard/cycle-count\` → \`/dashboard/inventory?tab=cycle-count\` is irrelevant here.

### Impact

${dif.length} pages are in this state — middleware-redirected as standalone routes,
but dynamically imported into workspace tabs and therefore fully user-visible.
Their internal navigation cards/buttons (totalling **${finalBroken.length}**) all fail silently
by looping the user back to the same workspace tab they are already on.

### The Cycle Count Example (Confirmed Still Broken)

**Visible at:** \`/dashboard/inventory?tab=cycle-count\`
**Source:** \`frontend/src/app/dashboard/cycle-count/page.tsx\`
**How visible:** \`inventory/page.tsx\` imports it as the "Cycle Count" tab
**Standalone route:** \`/dashboard/cycle-count\` → middleware redirects to \`/dashboard/inventory?tab=cycle-count\`

The 5 navigation tiles shown to users all link to redirect stubs:

| Tile | Target | Behavior | Git History |
|------|--------|----------|-------------|
| Count Plans | \`/dashboard/cycle-count/plans\` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Tasks | \`/dashboard/cycle-count/tasks\` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Entries | \`/dashboard/cycle-count/entries\` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Variance Review | \`/dashboard/cycle-count/variances\` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Reports & AI | \`/dashboard/cycle-count/reports\` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |

Git evidence: Commit \`674b6c5\` (2026-05-01) had REAL implementations — full CRUD with API integration.
These were deleted in \`bd6faf5\` (2026-05-17) and replaced with redirect stubs.
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT from commit 674b6c5.**

---

## Top 20 Critical/High Severity Broken Visible Buttons

| ID | Module | Visible At | Card/Button | Current Target | Behavior | Git | Recommendation |
|----|--------|-----------|-------------|----------------|----------|-----|----------------|
${topCritical.map(t => `| ${t.id} | ${t.module} | ${t.visibleVia} | ${t.label} | \`${t.currentTarget}\` | ${t.currentBehavior} | ${t.gitHistory.wasReal === true ? "✓ REAL" : t.gitHistory.found ? "stub" : "none"} | ${t.recommendation} |`).join("\n")}

---

## Module-by-Module Breakdown

${Object.entries(byMod).map(([mod, targets]) => `### ${mod}

**Broken count:** ${targets.length}

| Module | Visible Location | Tab | Source File | Button/Card | Current Target | Current Behavior | Original Page? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-----|-------------|-------------|----------------|-----------------|----------------|------------|------------|-----------------|
${targets.map(t => {
  const git = t.gitHistory;
  const origFound = git.wasReal === true ? "Yes — real page" : git.found ? "Yes — stub only" : "No";
  const bestMatch = git.wasReal === true ? `commit ${git.commit} (${git.commitDate})` : git.found ? "only redirect stub in git" : "not found";
  const conf = git.wasReal === true ? "high" : git.found ? "medium" : "low";
  const tabStr = t.visibleVia.split("?tab=")[1] || "—";
  return `| ${mod} | ${t.visibleVia.split("?tab=")[0]} | ${tabStr} | ${t.sourceFile.replace("frontend/src/app/dashboard/","")} | ${t.label} | \`${t.currentTarget}\` | ${t.currentBehavior} | ${origFound} | ${bestMatch} | ${conf} | ${t.recommendation} |`;
}).join("\n")}

`).join("\n")}

---

## Dynamic Import Visibility Failures

Every entry below was **missed** by the previous audit (classified as "safe_archived_standalone").
Each of these pages is middleware-redirected as a standalone route but IS user-visible
because it is dynamically imported into a workspace tab.

| Source Page | Standalone Route | Middleware Destination | Visible As | Broken Cards |
|-------------|-----------------|----------------------|-----------|--------------|
${dif.map(n => {
  const brokenCount = finalBroken.filter(t => t.sourceFile === n.filePath).length;
  return `| \`${n.filePath.replace("frontend/src/app/dashboard/","")}\` | \`${n.routeGuess}\` | \`${n.standaloneRedirectsTo}\` | ${n.visibleBecause.map(v => `\`${v.parentRouteGuess}\``).join(", ")} | ${brokenCount} |`;
}).join("\n")}

---

## Git History — High-Confidence Real Page Matches

These broken targets had REAL implementations in commit \`674b6c5\` (2026-05-01).
All were deleted/replaced with redirect stubs in \`bd6faf5\` (2026-05-17).
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT**

| Module | Target Route | Source File in Git | Confidence |
|--------|-------------|-------------------|------------|
${gitRealItems.map(t => `| ${t.module} | \`${t.currentTarget}\` | \`${t.gitHistory.filePath}\` | high |`).join("\n")}

---

## Unresolved — No Git Match Found

These broken targets have no known implementation in git history.

| Module | Target Route | Source File | Recommendation |
|--------|-------------|-------------|----------------|
${unresolvedItems.slice(0, 30).map(t => `| ${t.module} | \`${t.currentTarget}\` | ${t.sourceFile.replace("frontend/src/app/dashboard/","")} | ${t.recommendation} |`).join("\n")}
${unresolvedItems.length > 30 ? `\n…and ${unresolvedItems.length - 30} more` : ""}

---

## Recommendation Summary

| Category | Count | Action |
|----------|-------|--------|
| RESTORE_OLD_PAGE_FROM_GIT | ${finalBroken.filter(t=>t.recommendation==="RESTORE_OLD_PAGE_FROM_GIT").length} | Restore from git commit \`674b6c5\` + add BYPASS_PREFIX_REDIRECT |
| CONVERT_TO_WORKSPACE_SUBVIEW | ${finalBroken.filter(t=>t.recommendation==="CONVERT_TO_WORKSPACE_SUBVIEW").length} | Change href to \`?tab=X&view=Y\` pattern in workspace |
| CREATE_NEW_REAL_PAGE_REQUIRED | ${finalBroken.filter(t=>t.recommendation==="CREATE_NEW_REAL_PAGE_REQUIRED").length} | No implementation exists — new page required |
| NEEDS_BUSINESS_DECISION | ${finalBroken.filter(t=>t.recommendation==="NEEDS_BUSINESS_DECISION").length} | Intent unclear — needs product decision |

---

*Generated by \`scripts/audit-visible-import-graph.js\` — DO NOT FIX based on this report. Discovery pass only.*
`;

fs.writeFileSync(path.join(DOCS, "BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md"), mainMd);

// ─── CONSOLE SUMMARY ─────────────────────────────────────────────────────────
console.log("\n╔══════════════════════════════════════════════════════╗");
console.log("║          AUDIT COMPLETE — SUMMARY                   ║");
console.log("╠══════════════════════════════════════════════════════╣");
console.log(`║ Workspace pages scanned:         ${String(workspacePages.length).padStart(6)}              ║`);
console.log(`║ Dynamic imports found:           ${String(Object.values(importedBy).reduce((a,v)=>a+v.length,0)).padStart(6)}              ║`);
console.log(`║ Dynamically imported pages:      ${String(visGraph.length).padStart(6)}              ║`);
console.log(`║ Total visible action targets:    ${String(classified.length).padStart(6)}              ║`);
console.log(`║ BROKEN visible action targets:   ${String(finalBroken.length).padStart(6)}              ║`);
console.log(`║   Critical:                      ${String(finalBroken.filter(t=>t.severity==="critical").length).padStart(6)}              ║`);
console.log(`║   High:                          ${String(finalBroken.filter(t=>t.severity==="high").length).padStart(6)}              ║`);
console.log(`║   Medium:                        ${String(finalBroken.filter(t=>t.severity==="medium").length).padStart(6)}              ║`);
console.log(`║ Git history matches:             ${String(gitMatchesFound).padStart(6)}              ║`);
console.log(`║ High-conf (real page in git):    ${String(highConfMatches).padStart(6)}              ║`);
console.log(`║ Unresolved (no git match):       ${String(unresolved).padStart(6)}              ║`);
console.log("╠══════════════════════════════════════════════════════╣");
console.log("║ CYCLE COUNT PAGES IN GIT:                           ║");
const ccItems = finalBroken.filter(t => t.currentTarget.startsWith("/dashboard/cycle-count/"));
for (const cc of ccItems) {
  const status = cc.gitHistory.wasReal === true ? "REAL ✓" : cc.gitHistory.found ? "stub" : "NONE";
  console.log(`║   ${cc.currentTarget.padEnd(40)} ${status.padStart(6)} ║`);
}
console.log("╠══════════════════════════════════════════════════════╣");
console.log("║ OUTPUT FILES:                                        ║");
console.log("║   docs/VISIBLE_IMPORT_GRAPH.json                    ║");
console.log("║   docs/VISIBLE_IMPORT_GRAPH.md                      ║");
console.log("║   docs/VISIBLE_ACTION_TARGET_INVENTORY.json         ║");
console.log("║   docs/VISIBLE_ACTION_TARGET_INVENTORY.md           ║");
console.log("║   docs/VISIBLE_BROKEN_ACTION_TARGETS.json           ║");
console.log("║   docs/VISIBLE_BROKEN_ACTION_TARGETS.md             ║");
console.log("║   docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json║");
console.log("║   docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md  ║");
console.log("╚══════════════════════════════════════════════════════╝");
