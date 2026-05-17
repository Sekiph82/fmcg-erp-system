import { NextRequest, NextResponse } from "next/server";

/**
 * Redirect map: old dashboard route → new workspace + query params.
 * Kept inline here (not imported) so this file works cleanly at Edge Runtime.
 * Source of truth is routeRedirectMap.ts — keep in sync when updating.
 */
const REDIRECTS: Record<string, { p: string; t?: string; d?: string }> = {
  // Inventory
  "/dashboard/movements":                       { p: "/dashboard/inventory", t: "movements" },
  "/dashboard/cycle-count":                     { p: "/dashboard/inventory", t: "cycle-count" },
  "/dashboard/shelf-life":                      { p: "/dashboard/inventory", t: "shelf-life" },
  "/dashboard/traceability":                    { p: "/dashboard/inventory", t: "traceability" },
  // Warehouses
  "/dashboard/wms":                             { p: "/dashboard/warehouses", t: "wms" },
  "/dashboard/putaway":                         { p: "/dashboard/warehouses", t: "wms" },
  "/dashboard/containers":                      { p: "/dashboard/logistics", t: "containers" },
  // Procurement
  "/dashboard/procurement-suggestion":          { p: "/dashboard/procurement", t: "suggestions" },
  "/dashboard/subcontracting":                  { p: "/dashboard/procurement", t: "subcontracting" },
  "/dashboard/copacking":                       { p: "/dashboard/procurement", t: "subcontracting" },
  "/dashboard/landed-cost":                     { p: "/dashboard/procurement", t: "landed-cost" },
  "/dashboard/supplier-portal":                 { p: "/dashboard/procurement", t: "supplier-portal" },
  // Sales
  "/dashboard/price-lists":                     { p: "/dashboard/sales", t: "price-lists" },
  "/dashboard/dynamic-pricing":                 { p: "/dashboard/sales", t: "dynamic-pricing" },
  "/dashboard/contracts":                       { p: "/dashboard/sales", t: "contracts" },
  "/dashboard/recurring-orders":                { p: "/dashboard/sales", t: "recurring" },
  "/dashboard/commissions":                     { p: "/dashboard/sales", t: "commissions" },
  "/dashboard/secondary-sales":                 { p: "/dashboard/sales", t: "secondary" },
  "/dashboard/van-sales":                       { p: "/dashboard/sales", t: "van-sales" },
  "/dashboard/portal":                          { p: "/dashboard/sales", t: "portal" },
  // Sales child routes (static; dynamic [id] handled by file-level redirect to preserve ID)
  "/dashboard/sales/pod":                       { p: "/dashboard/sales", t: "delivery" },
  "/dashboard/sales/customer-statement":        { p: "/dashboard/sales", t: "customers" },
  // CRM child routes (static + prefix for records/[id])
  "/dashboard/crm/ai":                          { p: "/dashboard/crm", t: "overview" },
  "/dashboard/crm/overdue":                     { p: "/dashboard/crm", t: "pipeline" },
  "/dashboard/crm/qualify":                     { p: "/dashboard/crm", t: "leads" },
  "/dashboard/crm/records":                     { p: "/dashboard/crm", t: "overview" },
  // CRM alias modules
  "/dashboard/loyalty":                         { p: "/dashboard/crm", t: "loyalty" },
  "/dashboard/nps":                             { p: "/dashboard/crm", t: "nps" },
  "/dashboard/surveys":                         { p: "/dashboard/crm", t: "surveys" },
  // Marketing
  "/dashboard/tpm":                             { p: "/dashboard/marketing", t: "tpm" },
  "/dashboard/promotions":                      { p: "/dashboard/marketing", t: "promotions-schemes" },
  "/dashboard/market-intelligence":             { p: "/dashboard/marketing", t: "market-intel" },
  // Marketing workspace child routes (prefix match covers /[id], /new, etc.)
  "/dashboard/marketing/campaigns":             { p: "/dashboard/marketing", t: "campaigns" },
  "/dashboard/marketing/ads":                   { p: "/dashboard/marketing", t: "ads" },
  "/dashboard/marketing/brand-spend":           { p: "/dashboard/marketing", t: "brand-spend" },
  "/dashboard/marketing/crm":                   { p: "/dashboard/marketing", t: "overview" },
  "/dashboard/marketing/ecommerce":             { p: "/dashboard/marketing", t: "ecommerce" },
  "/dashboard/marketing/influencers":           { p: "/dashboard/marketing", t: "influencers" },
  "/dashboard/marketing/promotions":            { p: "/dashboard/marketing", t: "promotions" },
  "/dashboard/marketing/segments":              { p: "/dashboard/marketing", t: "segments" },
  "/dashboard/marketing/social-media":          { p: "/dashboard/marketing", t: "social-media" },
  "/dashboard/marketing/surveys":               { p: "/dashboard/marketing", t: "overview" },
  "/dashboard/marketing/trade-spend":           { p: "/dashboard/marketing", t: "trade-spend" },
  "/dashboard/marketing/visits":                { p: "/dashboard/marketing", t: "visits" },
  "/dashboard/marketing/ai-optimizer":          { p: "/dashboard/marketing", t: "analytics" },
  // Finance
  "/dashboard/finance/accounting":              { p: "/dashboard/finance", t: "accounting" },
  "/dashboard/bank-reconciliation":             { p: "/dashboard/finance", t: "bank-recon" },
  "/dashboard/invoice-match":                   { p: "/dashboard/finance", t: "invoice-match" },
  "/dashboard/fixed-assets":                    { p: "/dashboard/finance", t: "fixed-assets" },
  "/dashboard/dimensions":                      { p: "/dashboard/finance", t: "dimensions" },
  "/dashboard/dunning":                         { p: "/dashboard/finance", t: "dunning" },
  "/dashboard/tax":                             { p: "/dashboard/finance", t: "tax" },
  "/dashboard/bank-api":                        { p: "/dashboard/finance", t: "bank-api" },
  "/dashboard/expenses":                        { p: "/dashboard/hr", t: "expenses" },
  // Production workspace child routes
  "/dashboard/production/advanced":             { p: "/dashboard/production", t: "scheduling" },
  "/dashboard/production/ai":                   { p: "/dashboard/production", t: "plans" },
  "/dashboard/production/orders":               { p: "/dashboard/production", t: "orders" },
  "/dashboard/production/plans":                { p: "/dashboard/production", t: "plans" },
  "/dashboard/production/shifts":               { p: "/dashboard/production", t: "scheduling" },
  "/dashboard/production/work-orders":          { p: "/dashboard/production", t: "orders" },
  // Production sub-modules
  "/dashboard/production-execution":            { p: "/dashboard/production", t: "execution" },
  "/dashboard/machine-ops":                     { p: "/dashboard/production", t: "machine-ops" },
  "/dashboard/material-flow":                   { p: "/dashboard/production", t: "material-flow" },
  "/dashboard/projects":                        { p: "/dashboard/production", t: "projects" },
  // Planning (no /dashboard/planning entry — it IS the workspace, would cause a loop)
  // Child pages of the planning workspace redirect to specific tabs:
  "/dashboard/planning/schedule":               { p: "/dashboard/planning", t: "advanced" },
  "/dashboard/planning/capacity":               { p: "/dashboard/planning", t: "advanced" },
  "/dashboard/planning/bottlenecks":            { p: "/dashboard/planning", t: "advanced" },
  "/dashboard/planning/simulation":             { p: "/dashboard/planning", t: "advanced" },
  "/dashboard/planning/changeover":             { p: "/dashboard/planning", t: "advanced" },
  "/dashboard/mrp":                             { p: "/dashboard/planning", t: "mrp" },
  "/dashboard/mps":                             { p: "/dashboard/planning", t: "mps" },
  "/dashboard/kanban":                          { p: "/dashboard/planning", t: "kanban" },
  // Quality
  "/dashboard/qms":                             { p: "/dashboard/quality", t: "qms" },
  "/dashboard/allergen":                        { p: "/dashboard/quality", t: "allergen" },
  "/dashboard/brand-assets":                    { p: "/dashboard/quality", t: "brand-assets" },
  "/dashboard/quality/consumer-complaints":     { p: "/dashboard/quality", t: "consumer-complaints" },
  // Compliance
  "/dashboard/gs1":                             { p: "/dashboard/compliance", t: "gs1" },
  // Utilities
  "/dashboard/iot":                             { p: "/dashboard/utility-management", t: "iot" },
  "/dashboard/esg":                             { p: "/dashboard/utility-management", t: "esg" },
  // Utility-management workspace child routes
  "/dashboard/utility-management/categories":   { p: "/dashboard/utility-management", t: "assets" },
  "/dashboard/utility-management/kpi-center":   { p: "/dashboard/utility-management", t: "kpi-center" },
  "/dashboard/utility-management/reports":      { p: "/dashboard/utility-management", t: "reports" },
  // Logistics
  "/dashboard/fleet":                           { p: "/dashboard/logistics", t: "fleet" },
  "/dashboard/logistics/containers":            { p: "/dashboard/logistics", t: "containers" },
  // HR
  "/dashboard/recruitment":                     { p: "/dashboard/hr", t: "recruitment" },
  "/dashboard/ess":                             { p: "/dashboard/hr", t: "ess" },
  "/dashboard/appraisals":                      { p: "/dashboard/hr", t: "appraisals" },
  "/dashboard/training":                        { p: "/dashboard/hr", t: "training" },
  "/dashboard/timesheets":                      { p: "/dashboard/hr", t: "timesheets" },
  // Documents child routes
  "/dashboard/documents/new":                   { p: "/dashboard/documents", d: "create" },
  // Documents alias modules
  "/dashboard/knowledge-base":                  { p: "/dashboard/documents", t: "knowledge-base" },
  "/dashboard/esign":                           { p: "/dashboard/documents", t: "esign" },
  // Communication
  "/dashboard/chatter":                         { p: "/dashboard/communication", t: "chatter" },
  "/dashboard/calendar":                        { p: "/dashboard/communication", t: "calendar" },
  "/dashboard/messages":                        { p: "/dashboard/communication", t: "messages" },
  "/dashboard/email":                           { p: "/dashboard/communication", t: "email" },
  "/dashboard/whatsapp":                        { p: "/dashboard/communication", t: "whatsapp" },
  "/dashboard/calls":                           { p: "/dashboard/communication", t: "calls" },
  "/dashboard/meetings":                        { p: "/dashboard/communication", t: "meetings" },
  "/dashboard/notification-center":             { p: "/dashboard/communication", t: "notifications" },
  // Analytics
  "/dashboard/report-builder":                  { p: "/dashboard/analytics", t: "report-builder" },
  "/dashboard/reports":                         { p: "/dashboard/analytics", t: "reports" },
  // Admin
  "/dashboard/users":                           { p: "/dashboard/admin", t: "users" },
  "/dashboard/roles":                           { p: "/dashboard/admin", t: "roles" },
  "/dashboard/permissions":                     { p: "/dashboard/admin", t: "permissions" },
  "/dashboard/companies":                       { p: "/dashboard/admin", t: "companies" },
  "/dashboard/security":                        { p: "/dashboard/admin", t: "security" },
  "/dashboard/approvals":                       { p: "/dashboard/admin", t: "approvals" },
  "/dashboard/custom-fields":                   { p: "/dashboard/admin", t: "custom-fields" },
  "/dashboard/utilities":                       { p: "/dashboard/admin", t: "system-config" },
  "/dashboard/mobile":                          { p: "/dashboard/admin", t: "mobile" },
  "/dashboard/logs":                            { p: "/dashboard/admin", t: "logs" },
  "/dashboard/import-history":                  { p: "/dashboard/admin", t: "import-history" },
  // Integrations
  "/dashboard/webhooks":                        { p: "/dashboard/integrations", t: "webhooks" },
  "/dashboard/developer":                       { p: "/dashboard/integrations", t: "developer" },
  // Payroll (top-level alias → HR payroll tab)
  "/dashboard/payroll":                         { p: "/dashboard/hr", t: "payroll" },
};

function matchRedirect(pathname: string): { p: string; t?: string; d?: string } | null {
  // Exact match
  if (REDIRECTS[pathname]) return REDIRECTS[pathname];

  // Prefix match — longest prefix wins
  const parts = pathname.split("/");
  for (let i = parts.length - 1; i >= 2; i--) {
    const prefix = parts.slice(0, i).join("/");
    if (REDIRECTS[prefix]) return REDIRECTS[prefix];
  }
  return null;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  const match = matchRedirect(pathname);
  if (!match) return NextResponse.next();

  const params = new URLSearchParams(search);
  if (match.t) params.set("tab", match.t);
  if (match.d) params.set("drawer", match.d);

  const qs = params.toString();
  const dest = qs ? `${match.p}?${qs}` : match.p;

  return NextResponse.redirect(new URL(dest, request.url), { status: 308 });
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
