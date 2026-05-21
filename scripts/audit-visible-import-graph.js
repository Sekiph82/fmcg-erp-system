#!/usr/bin/env node
/**
 * Audit Script: Build Import Visibility Graph + Broken Action Target Report
 *
 * PURPOSE: Find all dashboard pages that are user-visible through dynamic import
 * into workspace pages, even when their standalone route is middleware-redirected.
 *
 * KEY INSIGHT: The previous audit classified pages as "safe" if middleware redirected
 * their standalone route. This is WRONG if the page is also dynamically imported
 * into a workspace tab. Users see the page content (and its broken action cards)
 * regardless of what middleware does to the standalone route.
 *
 * OUTPUT:
 *   docs/VISIBLE_IMPORT_GRAPH.json
 *   docs/VISIBLE_IMPORT_GRAPH.md
 *   docs/VISIBLE_BROKEN_ACTION_TARGETS.json
 *   docs/VISIBLE_BROKEN_ACTION_TARGETS.md
 *   docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json
 *   docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md
 */

const fs = require("fs");
const path = require("path");

// ─── CONSTANTS ───────────────────────────────────────────────────────────────

const ROOT = path.resolve(__dirname, "..");
const DOCS = path.join(ROOT, "docs");
const FRONTEND = path.join(ROOT, "frontend", "src", "app", "dashboard");

// ─── MIDDLEWARE REDIRECT MAP (from middleware.ts) ─────────────────────────────
// Key = middleware-redirected prefix/exact route; Value = workspace dest
const MIDDLEWARE_REDIRECTS = {
  "/dashboard/movements":                       { workspace: "/dashboard/inventory", tab: "movements" },
  "/dashboard/cycle-count":                     { workspace: "/dashboard/inventory", tab: "cycle-count" },
  "/dashboard/shelf-life":                      { workspace: "/dashboard/inventory", tab: "shelf-life" },
  "/dashboard/traceability":                    { workspace: "/dashboard/inventory", tab: "traceability" },
  "/dashboard/wms":                             { workspace: "/dashboard/warehouses", tab: "wms" },
  "/dashboard/putaway":                         { workspace: "/dashboard/warehouses", tab: "wms" },
  "/dashboard/containers":                      { workspace: "/dashboard/logistics", tab: "containers" },
  "/dashboard/procurement-suggestion":          { workspace: "/dashboard/procurement", tab: "suggestions" },
  "/dashboard/subcontracting":                  { workspace: "/dashboard/procurement", tab: "subcontracting" },
  "/dashboard/copacking":                       { workspace: "/dashboard/procurement", tab: "subcontracting" },
  "/dashboard/landed-cost":                     { workspace: "/dashboard/procurement", tab: "landed-cost" },
  "/dashboard/supplier-portal":                 { workspace: "/dashboard/procurement", tab: "supplier-portal" },
  "/dashboard/price-lists":                     { workspace: "/dashboard/sales", tab: "price-lists" },
  "/dashboard/dynamic-pricing":                 { workspace: "/dashboard/sales", tab: "dynamic-pricing" },
  "/dashboard/contracts":                       { workspace: "/dashboard/sales", tab: "contracts" },
  "/dashboard/recurring-orders":                { workspace: "/dashboard/sales", tab: "recurring" },
  "/dashboard/commissions":                     { workspace: "/dashboard/sales", tab: "commissions" },
  "/dashboard/secondary-sales":                 { workspace: "/dashboard/sales", tab: "secondary" },
  "/dashboard/van-sales":                       { workspace: "/dashboard/sales", tab: "van-sales" },
  "/dashboard/portal":                          { workspace: "/dashboard/sales", tab: "portal" },
  "/dashboard/sales/pod":                       { workspace: "/dashboard/sales", tab: "delivery" },
  "/dashboard/sales/customer-statement":        { workspace: "/dashboard/sales", tab: "customers" },
  "/dashboard/crm/ai":                          { workspace: "/dashboard/crm", tab: "overview" },
  "/dashboard/crm/overdue":                     { workspace: "/dashboard/crm", tab: "pipeline" },
  "/dashboard/crm/qualify":                     { workspace: "/dashboard/crm", tab: "leads" },
  "/dashboard/crm/records":                     { workspace: "/dashboard/crm", tab: "overview" },
  "/dashboard/loyalty":                         { workspace: "/dashboard/crm", tab: "loyalty" },
  "/dashboard/nps":                             { workspace: "/dashboard/crm", tab: "nps" },
  "/dashboard/surveys":                         { workspace: "/dashboard/crm", tab: "surveys" },
  "/dashboard/tpm":                             { workspace: "/dashboard/marketing", tab: "tpm" },
  "/dashboard/promotions":                      { workspace: "/dashboard/marketing", tab: "promotions-schemes" },
  "/dashboard/market-intelligence":             { workspace: "/dashboard/marketing", tab: "market-intel" },
  "/dashboard/marketing/campaigns":             { workspace: "/dashboard/marketing", tab: "campaigns" },
  "/dashboard/marketing/ads":                   { workspace: "/dashboard/marketing", tab: "ads" },
  "/dashboard/marketing/brand-spend":           { workspace: "/dashboard/marketing", tab: "brand-spend" },
  "/dashboard/marketing/crm":                   { workspace: "/dashboard/marketing", tab: "overview" },
  "/dashboard/marketing/ecommerce":             { workspace: "/dashboard/marketing", tab: "ecommerce" },
  "/dashboard/marketing/influencers":           { workspace: "/dashboard/marketing", tab: "influencers" },
  "/dashboard/marketing/promotions":            { workspace: "/dashboard/marketing", tab: "promotions" },
  "/dashboard/marketing/segments":              { workspace: "/dashboard/marketing", tab: "segments" },
  "/dashboard/marketing/social-media":          { workspace: "/dashboard/marketing", tab: "social-media" },
  "/dashboard/marketing/surveys":               { workspace: "/dashboard/marketing", tab: "overview" },
  "/dashboard/marketing/trade-spend":           { workspace: "/dashboard/marketing", tab: "trade-spend" },
  "/dashboard/marketing/visits":                { workspace: "/dashboard/marketing", tab: "visits" },
  "/dashboard/marketing/ai-optimizer":          { workspace: "/dashboard/marketing", tab: "analytics" },
  "/dashboard/finance/accounting":              { workspace: "/dashboard/finance", tab: "accounting" },
  "/dashboard/bank-reconciliation":             { workspace: "/dashboard/finance", tab: "bank-recon" },
  "/dashboard/invoice-match":                   { workspace: "/dashboard/finance", tab: "invoice-match" },
  "/dashboard/fixed-assets":                    { workspace: "/dashboard/finance", tab: "fixed-assets" },
  "/dashboard/dimensions":                      { workspace: "/dashboard/finance", tab: "dimensions" },
  "/dashboard/dunning":                         { workspace: "/dashboard/finance", tab: "dunning" },
  "/dashboard/tax":                             { workspace: "/dashboard/finance", tab: "tax" },
  "/dashboard/bank-api":                        { workspace: "/dashboard/finance", tab: "bank-api" },
  "/dashboard/expenses":                        { workspace: "/dashboard/hr", tab: "expenses" },
  "/dashboard/production/advanced":             { workspace: "/dashboard/production", tab: "scheduling" },
  "/dashboard/production/ai":                   { workspace: "/dashboard/production", tab: "plans" },
  "/dashboard/production/orders":               { workspace: "/dashboard/production", tab: "orders" },
  "/dashboard/production/plans":                { workspace: "/dashboard/production", tab: "plans" },
  "/dashboard/production/shifts":               { workspace: "/dashboard/production", tab: "scheduling" },
  "/dashboard/production/work-orders":          { workspace: "/dashboard/production", tab: "orders" },
  "/dashboard/production-execution":            { workspace: "/dashboard/production", tab: "execution" },
  "/dashboard/machine-ops":                     { workspace: "/dashboard/production", tab: "machine-ops" },
  "/dashboard/material-flow":                   { workspace: "/dashboard/production", tab: "material-flow" },
  "/dashboard/projects":                        { workspace: "/dashboard/production", tab: "projects" },
  "/dashboard/planning/schedule":               { workspace: "/dashboard/planning", tab: "advanced" },
  "/dashboard/planning/capacity":               { workspace: "/dashboard/planning", tab: "advanced" },
  "/dashboard/planning/bottlenecks":            { workspace: "/dashboard/planning", tab: "advanced" },
  "/dashboard/planning/simulation":             { workspace: "/dashboard/planning", tab: "advanced" },
  "/dashboard/planning/changeover":             { workspace: "/dashboard/planning", tab: "advanced" },
  "/dashboard/mrp":                             { workspace: "/dashboard/planning", tab: "mrp" },
  "/dashboard/mps":                             { workspace: "/dashboard/planning", tab: "mps" },
  "/dashboard/kanban":                          { workspace: "/dashboard/planning", tab: "kanban" },
  "/dashboard/qms":                             { workspace: "/dashboard/quality", tab: "qms" },
  "/dashboard/allergen":                        { workspace: "/dashboard/quality", tab: "allergen" },
  "/dashboard/brand-assets":                    { workspace: "/dashboard/quality", tab: "brand-assets" },
  "/dashboard/quality/consumer-complaints":     { workspace: "/dashboard/quality", tab: "consumer-complaints" },
  "/dashboard/gs1":                             { workspace: "/dashboard/compliance", tab: "gs1" },
  "/dashboard/iot":                             { workspace: "/dashboard/utility-management", tab: "iot" },
  "/dashboard/esg":                             { workspace: "/dashboard/utility-management", tab: "esg" },
  "/dashboard/utility-management/categories":   { workspace: "/dashboard/utility-management", tab: "assets" },
  "/dashboard/utility-management/kpi-center":   { workspace: "/dashboard/utility-management", tab: "kpi-center" },
  "/dashboard/utility-management/reports":      { workspace: "/dashboard/utility-management", tab: "reports" },
  "/dashboard/fleet":                           { workspace: "/dashboard/logistics", tab: "fleet" },
  "/dashboard/logistics/containers":            { workspace: "/dashboard/logistics", tab: "containers" },
  "/dashboard/recruitment":                     { workspace: "/dashboard/hr", tab: "recruitment" },
  "/dashboard/ess":                             { workspace: "/dashboard/hr", tab: "ess" },
  "/dashboard/appraisals":                      { workspace: "/dashboard/hr", tab: "appraisals" },
  "/dashboard/training":                        { workspace: "/dashboard/hr", tab: "training" },
  "/dashboard/timesheets":                      { workspace: "/dashboard/hr", tab: "timesheets" },
  "/dashboard/documents/new":                   { workspace: "/dashboard/documents", drawer: "create" },
  "/dashboard/knowledge-base":                  { workspace: "/dashboard/documents", tab: "knowledge-base" },
  "/dashboard/esign":                           { workspace: "/dashboard/documents", tab: "esign" },
  "/dashboard/chatter":                         { workspace: "/dashboard/communication", tab: "chatter" },
  "/dashboard/calendar":                        { workspace: "/dashboard/communication", tab: "calendar" },
  "/dashboard/messages":                        { workspace: "/dashboard/communication", tab: "messages" },
  "/dashboard/email":                           { workspace: "/dashboard/communication", tab: "email" },
  "/dashboard/whatsapp":                        { workspace: "/dashboard/communication", tab: "whatsapp" },
  "/dashboard/calls":                           { workspace: "/dashboard/communication", tab: "calls" },
  "/dashboard/meetings":                        { workspace: "/dashboard/communication", tab: "meetings" },
  "/dashboard/notification-center":             { workspace: "/dashboard/communication", tab: "notifications" },
  "/dashboard/report-builder":                  { workspace: "/dashboard/analytics", tab: "report-builder" },
  "/dashboard/reports":                         { workspace: "/dashboard/analytics", tab: "reports" },
  "/dashboard/users":                           { workspace: "/dashboard/admin", tab: "users" },
  "/dashboard/roles":                           { workspace: "/dashboard/admin", tab: "roles" },
  "/dashboard/permissions":                     { workspace: "/dashboard/admin", tab: "permissions" },
  "/dashboard/companies":                       { workspace: "/dashboard/admin", tab: "companies" },
  "/dashboard/security":                        { workspace: "/dashboard/admin", tab: "security" },
  "/dashboard/approvals":                       { workspace: "/dashboard/admin", tab: "approvals" },
  "/dashboard/custom-fields":                   { workspace: "/dashboard/admin", tab: "custom-fields" },
  "/dashboard/utilities":                       { workspace: "/dashboard/admin", tab: "system-config" },
  "/dashboard/mobile":                          { workspace: "/dashboard/admin", tab: "mobile" },
  "/dashboard/logs":                            { workspace: "/dashboard/admin", tab: "logs" },
  "/dashboard/import-history":                  { workspace: "/dashboard/admin", tab: "import-history" },
  "/dashboard/webhooks":                        { workspace: "/dashboard/integrations", tab: "webhooks" },
  "/dashboard/developer":                       { workspace: "/dashboard/integrations", tab: "developer" },
  "/dashboard/payroll":                         { workspace: "/dashboard/hr", tab: "payroll" },
};

// Pages bypassed from middleware prefix redirect (real standalone pages)
const BYPASS_PREFIX_REDIRECT = new Set([
  "/dashboard/mps/planning-board",
  "/dashboard/mps/capacity",
  "/dashboard/mps/campaigns",
  "/dashboard/mps/whatif",
]);

// ─── DYNAMIC IMPORT MAP (from grep of workspace pages) ────────────────────────
// workspacePage → array of dynamically imported module paths (relative to @/app/...)
const DYNAMIC_IMPORTS = {
  "frontend/src/app/dashboard/inventory/page.tsx": [
    { importPath: "@/app/dashboard/movements/page", tabKey: "movements" },
    { importPath: "@/app/dashboard/cycle-count/page", tabKey: "cycle-count" },
    { importPath: "@/app/dashboard/shelf-life/page", tabKey: "shelf-life" },
    { importPath: "@/app/dashboard/traceability/page", tabKey: "traceability" },
    { importPath: "@/app/dashboard/inventory/serials/page", tabKey: "serials" },
    { importPath: "@/app/dashboard/inventory/valuation/page", tabKey: "valuation" },
  ],
  "frontend/src/app/dashboard/planning/page.tsx": [
    { importPath: "@/app/dashboard/planning/schedule/page", tabKey: "advanced" },
    { importPath: "@/app/dashboard/planning/capacity/page", tabKey: "advanced" },
    { importPath: "@/app/dashboard/planning/simulation/page", tabKey: "advanced" },
    { importPath: "@/app/dashboard/planning/bottlenecks/page", tabKey: "advanced" },
    { importPath: "@/app/dashboard/planning/changeover/page", tabKey: "advanced" },
    { importPath: "@/app/dashboard/mrp/page", tabKey: "mrp" },
    { importPath: "@/app/dashboard/mps/page", tabKey: "mps" },
    { importPath: "@/app/dashboard/kanban/page", tabKey: "kanban" },
  ],
  "frontend/src/app/dashboard/production/page.tsx": [
    { importPath: "@/app/dashboard/production/orders/page", tabKey: "orders" },
    { importPath: "@/app/dashboard/production/scheduling/page", tabKey: "scheduling" },
    { importPath: "@/app/dashboard/production/work-centers/page", tabKey: "work-centers" },
    { importPath: "@/app/dashboard/production/batch-lots/page", tabKey: "batch-lots" },
    { importPath: "@/app/dashboard/production/quality-control/page", tabKey: "quality-control" },
    { importPath: "@/app/dashboard/production/labor/page", tabKey: "labor" },
    { importPath: "@/app/dashboard/production/oee/page", tabKey: "oee" },
    { importPath: "@/app/dashboard/production/downtime/page", tabKey: "downtime" },
    { importPath: "@/app/dashboard/production/waste-yield/page", tabKey: "waste-yield" },
    { importPath: "@/app/dashboard/production/wip/page", tabKey: "wip" },
    { importPath: "@/app/dashboard/production/costing/page", tabKey: "costing" },
    { importPath: "@/app/dashboard/production/variance/page", tabKey: "variance" },
    { importPath: "@/app/dashboard/production/reports/page", tabKey: "reports" },
    { importPath: "@/app/dashboard/production/routing/page", tabKey: "routing" },
    { importPath: "@/app/dashboard/production/time-tracking/page", tabKey: "time-tracking" },
    { importPath: "@/app/dashboard/production-execution/page", tabKey: "execution" },
    { importPath: "@/app/dashboard/machine-ops/page", tabKey: "machine-ops" },
    { importPath: "@/app/dashboard/material-flow/page", tabKey: "material-flow" },
    { importPath: "@/app/dashboard/projects/page", tabKey: "projects" },
  ],
  "frontend/src/app/dashboard/finance/page.tsx": [
    { importPath: "@/app/dashboard/finance/accounting/page", tabKey: "accounting" },
    { importPath: "@/app/dashboard/finance/cashbook/page", tabKey: "cashbook" },
    { importPath: "@/app/dashboard/finance/receivables/page", tabKey: "receivables" },
    { importPath: "@/app/dashboard/finance/budget/page", tabKey: "budget" },
    { importPath: "@/app/dashboard/finance/mpesa/page", tabKey: "mpesa" },
    { importPath: "@/app/dashboard/finance/costing/page", tabKey: "costing" },
    { importPath: "@/app/dashboard/finance/exchange-rates/page", tabKey: "exchange-rates" },
    { importPath: "@/app/dashboard/finance/etims/page", tabKey: "etims" },
    { importPath: "@/app/dashboard/finance/vat-returns/page", tabKey: "vat-returns" },
    { importPath: "@/app/dashboard/bank-reconciliation/page", tabKey: "bank-recon" },
    { importPath: "@/app/dashboard/invoice-match/page", tabKey: "invoice-match" },
    { importPath: "@/app/dashboard/fixed-assets/page", tabKey: "fixed-assets" },
    { importPath: "@/app/dashboard/dimensions/page", tabKey: "dimensions" },
    { importPath: "@/app/dashboard/dunning/page", tabKey: "dunning" },
    { importPath: "@/app/dashboard/tax/page", tabKey: "tax" },
    { importPath: "@/app/dashboard/bank-api/page", tabKey: "bank-api" },
    { importPath: "@/app/dashboard/expenses/page", tabKey: "expenses" },
  ],
  "frontend/src/app/dashboard/hr/page.tsx": [
    { importPath: "@/app/dashboard/hr/employees/page", tabKey: "employees" },
    { importPath: "@/app/dashboard/hr/attendance/page", tabKey: "attendance" },
    { importPath: "@/app/dashboard/hr/leave/page", tabKey: "leave" },
    { importPath: "@/app/dashboard/hr/payroll/page", tabKey: "payroll" },
    { importPath: "@/app/dashboard/hr/shifts/page", tabKey: "shifts" },
    { importPath: "@/app/dashboard/recruitment/page", tabKey: "recruitment" },
    { importPath: "@/app/dashboard/ess/page", tabKey: "ess" },
    { importPath: "@/app/dashboard/appraisals/page", tabKey: "appraisals" },
    { importPath: "@/app/dashboard/training/page", tabKey: "training" },
    { importPath: "@/app/dashboard/timesheets/page", tabKey: "timesheets" },
    { importPath: "@/app/dashboard/expenses/page", tabKey: "expenses" },
  ],
  "frontend/src/app/dashboard/sales/page.tsx": [
    { importPath: "@/app/dashboard/sales/orders/page", tabKey: "orders" },
    { importPath: "@/app/dashboard/sales/invoices/page", tabKey: "invoices" },
    { importPath: "@/app/dashboard/sales/customers/page", tabKey: "customers" },
    { importPath: "@/app/dashboard/sales/quotes/page", tabKey: "quotes" },
    { importPath: "@/app/dashboard/sales/shipments/page", tabKey: "shipments" },
    { importPath: "@/app/dashboard/sales/delivery/page", tabKey: "delivery" },
    { importPath: "@/app/dashboard/sales/collections/page", tabKey: "collections" },
    { importPath: "@/app/dashboard/sales/returns/page", tabKey: "returns" },
    { importPath: "@/app/dashboard/sales/pricing/page", tabKey: "pricing" },
    { importPath: "@/app/dashboard/sales/margin/page", tabKey: "margin" },
    { importPath: "@/app/dashboard/sales/distributors/page", tabKey: "distributors" },
    { importPath: "@/app/dashboard/sales/field-sales/page", tabKey: "field-sales" },
    { importPath: "@/app/dashboard/sales/reports/page", tabKey: "reports" },
    { importPath: "@/app/dashboard/price-lists/page", tabKey: "price-lists" },
    { importPath: "@/app/dashboard/dynamic-pricing/page", tabKey: "dynamic-pricing" },
    { importPath: "@/app/dashboard/contracts/page", tabKey: "contracts" },
    { importPath: "@/app/dashboard/recurring-orders/page", tabKey: "recurring" },
    { importPath: "@/app/dashboard/commissions/page", tabKey: "commissions" },
    { importPath: "@/app/dashboard/secondary-sales/page", tabKey: "secondary" },
    { importPath: "@/app/dashboard/van-sales/page", tabKey: "van-sales" },
    { importPath: "@/app/dashboard/portal/page", tabKey: "portal" },
  ],
  "frontend/src/app/dashboard/procurement/page.tsx": [
    { importPath: "@/app/dashboard/procurement/orders/page", tabKey: "orders" },
    { importPath: "@/app/dashboard/procurement/rfq/page", tabKey: "rfq" },
    { importPath: "@/app/dashboard/procurement/deliveries/page", tabKey: "deliveries" },
    { importPath: "@/app/dashboard/procurement/suppliers/page", tabKey: "suppliers" },
    { importPath: "@/app/dashboard/procurement/blanket-agreements/page", tabKey: "blanket-agreements" },
    { importPath: "@/app/dashboard/procurement/reorder-policies/page", tabKey: "reorder-policies" },
    { importPath: "@/app/dashboard/procurement-suggestion/page", tabKey: "suggestions" },
    { importPath: "@/app/dashboard/subcontracting/page", tabKey: "subcontracting" },
    { importPath: "@/app/dashboard/landed-cost/page", tabKey: "landed-cost" },
    { importPath: "@/app/dashboard/supplier-portal/page", tabKey: "supplier-portal" },
  ],
  "frontend/src/app/dashboard/quality/page.tsx": [
    { importPath: "@/app/dashboard/quality/certificates/page", tabKey: "certificates" },
    { importPath: "@/app/dashboard/quality/parameters/page", tabKey: "parameters" },
    { importPath: "@/app/dashboard/quality/consumer-complaints/page", tabKey: "consumer-complaints" },
    { importPath: "@/app/dashboard/quality/reports/page", tabKey: "reports" },
    { importPath: "@/app/dashboard/qms/page", tabKey: "qms" },
    { importPath: "@/app/dashboard/allergen/page", tabKey: "allergen" },
    { importPath: "@/app/dashboard/brand-assets/page", tabKey: "brand-assets" },
  ],
  "frontend/src/app/dashboard/logistics/page.tsx": [
    { importPath: "@/app/dashboard/logistics/containers/page", tabKey: "containers" },
    { importPath: "@/app/dashboard/logistics/arrivals/page", tabKey: "arrivals" },
    { importPath: "@/app/dashboard/logistics/documents/page", tabKey: "documents" },
    { importPath: "@/app/dashboard/logistics/shipments/page", tabKey: "shipments" },
    { importPath: "@/app/dashboard/fleet/page", tabKey: "fleet" },
  ],
  "frontend/src/app/dashboard/warehouses/page.tsx": [
    { importPath: "@/app/dashboard/wms/page", tabKey: "wms" },
  ],
  "frontend/src/app/dashboard/communication/page.tsx": [
    { importPath: "@/app/dashboard/chatter/page", tabKey: "chatter" },
    { importPath: "@/app/dashboard/calendar/page", tabKey: "calendar" },
    { importPath: "@/app/dashboard/messages/page", tabKey: "messages" },
    { importPath: "@/app/dashboard/email/page", tabKey: "email" },
    { importPath: "@/app/dashboard/whatsapp/page", tabKey: "whatsapp" },
    { importPath: "@/app/dashboard/calls/page", tabKey: "calls" },
    { importPath: "@/app/dashboard/meetings/page", tabKey: "meetings" },
    { importPath: "@/app/dashboard/notification-center/page", tabKey: "notifications" },
  ],
  "frontend/src/app/dashboard/analytics/page.tsx": [
    { importPath: "@/app/dashboard/analytics/inventory/page", tabKey: "inventory" },
    { importPath: "@/app/dashboard/analytics/sales/page", tabKey: "sales" },
    { importPath: "@/app/dashboard/analytics/production/page", tabKey: "production" },
    { importPath: "@/app/dashboard/analytics/procurement/page", tabKey: "procurement" },
    { importPath: "@/app/dashboard/analytics/finance/page", tabKey: "finance" },
    { importPath: "@/app/dashboard/analytics/payments/page", tabKey: "payments" },
    { importPath: "@/app/dashboard/reports/page", tabKey: "reports" },
    { importPath: "@/app/dashboard/report-builder/page", tabKey: "report-builder" },
  ],
  "frontend/src/app/dashboard/admin/page.tsx": [
    { importPath: "@/app/dashboard/users/page", tabKey: "users" },
    { importPath: "@/app/dashboard/roles/page", tabKey: "roles" },
    { importPath: "@/app/dashboard/permissions/page", tabKey: "permissions" },
    { importPath: "@/app/dashboard/companies/page", tabKey: "companies" },
    { importPath: "@/app/dashboard/security/page", tabKey: "security" },
    { importPath: "@/app/dashboard/approvals/page", tabKey: "approvals" },
    { importPath: "@/app/dashboard/custom-fields/page", tabKey: "custom-fields" },
    { importPath: "@/app/dashboard/utilities/page", tabKey: "system-config" },
    { importPath: "@/app/dashboard/mobile/page", tabKey: "mobile" },
    { importPath: "@/app/dashboard/logs/page", tabKey: "logs" },
    { importPath: "@/app/dashboard/import-history/page", tabKey: "import-history" },
  ],
  "frontend/src/app/dashboard/marketing/page.tsx": [
    { importPath: "@/app/dashboard/marketing/campaigns/page", tabKey: "campaigns" },
    { importPath: "@/app/dashboard/marketing/promotions/page", tabKey: "promotions" },
    { importPath: "@/app/dashboard/marketing/trade-spend/page", tabKey: "trade-spend" },
    { importPath: "@/app/dashboard/marketing/ads/page", tabKey: "ads" },
    { importPath: "@/app/dashboard/marketing/social-media/page", tabKey: "social-media" },
    { importPath: "@/app/dashboard/marketing/segments/page", tabKey: "segments" },
    { importPath: "@/app/dashboard/marketing/influencers/page", tabKey: "influencers" },
    { importPath: "@/app/dashboard/marketing/ecommerce/page", tabKey: "ecommerce" },
    { importPath: "@/app/dashboard/marketing/analytics/page", tabKey: "analytics" },
    { importPath: "@/app/dashboard/marketing/visits/page", tabKey: "visits" },
    { importPath: "@/app/dashboard/marketing/brand-spend/page", tabKey: "brand-spend" },
    { importPath: "@/app/dashboard/tpm/page", tabKey: "tpm" },
    { importPath: "@/app/dashboard/market-intelligence/page", tabKey: "market-intel" },
  ],
  "frontend/src/app/dashboard/crm/page.tsx": [
    { importPath: "@/app/dashboard/crm/pipeline/page", tabKey: "pipeline" },
    { importPath: "@/app/dashboard/crm/leads/page", tabKey: "leads" },
    { importPath: "@/app/dashboard/crm/opportunities/page", tabKey: "opportunities" },
    { importPath: "@/app/dashboard/crm/activities/page", tabKey: "activities" },
    { importPath: "@/app/dashboard/crm/forecast/page", tabKey: "forecast" },
    { importPath: "@/app/dashboard/crm/territory/page", tabKey: "territory" },
    { importPath: "@/app/dashboard/crm/stages/page", tabKey: "stages" },
    { importPath: "@/app/dashboard/crm/win-loss/page", tabKey: "win-loss" },
    { importPath: "@/app/dashboard/loyalty/page", tabKey: "loyalty" },
    { importPath: "@/app/dashboard/nps/page", tabKey: "nps" },
    { importPath: "@/app/dashboard/surveys/page", tabKey: "surveys" },
  ],
  "frontend/src/app/dashboard/documents/page.tsx": [
    { importPath: "@/app/dashboard/documents/compliance/page", tabKey: "compliance" },
    { importPath: "@/app/dashboard/documents/expiring/page", tabKey: "expiring" },
    { importPath: "@/app/dashboard/knowledge-base/page", tabKey: "knowledge-base" },
    { importPath: "@/app/dashboard/esign/page", tabKey: "esign" },
  ],
  "frontend/src/app/dashboard/integrations/page.tsx": [
    { importPath: "@/app/dashboard/integrations/mpesa/page", tabKey: "mpesa" },
    { importPath: "@/app/dashboard/integrations/sync/page", tabKey: "sync" },
    { importPath: "@/app/dashboard/integrations/marketplace/page", tabKey: "marketplace" },
    { importPath: "@/app/dashboard/integrations/barcode/page", tabKey: "barcode" },
    { importPath: "@/app/dashboard/integrations/marketing-sync/page", tabKey: "marketing-sync" },
    { importPath: "@/app/dashboard/integrations/logs/page", tabKey: "logs" },
    { importPath: "@/app/dashboard/webhooks/page", tabKey: "webhooks" },
    { importPath: "@/app/dashboard/developer/page", tabKey: "developer" },
  ],
  "frontend/src/app/dashboard/utility-management/page.tsx": [
    { importPath: "@/app/dashboard/utility-management/assets/page", tabKey: "assets" },
    { importPath: "@/app/dashboard/utility-management/electricity/page", tabKey: "electricity" },
    { importPath: "@/app/dashboard/utility-management/water/page", tabKey: "water" },
    { importPath: "@/app/dashboard/utility-management/solar/page", tabKey: "solar" },
    { importPath: "@/app/dashboard/utility-management/steam/page", tabKey: "steam" },
    { importPath: "@/app/dashboard/utility-management/wastewater/page", tabKey: "wastewater" },
    { importPath: "@/app/dashboard/utility-management/soft-water/page", tabKey: "soft-water" },
    { importPath: "@/app/dashboard/utility-management/compressor/page", tabKey: "compressor" },
    { importPath: "@/app/dashboard/utility-management/chemical-treatment/page", tabKey: "chemical-treatment" },
    { importPath: "@/app/dashboard/utility-management/machine-utility/page", tabKey: "machine-utility" },
    { importPath: "@/app/dashboard/utility-management/readings/page", tabKey: "readings" },
    { importPath: "@/app/dashboard/utility-management/devices/page", tabKey: "devices" },
    { importPath: "@/app/dashboard/utility-management/kpi-center/page", tabKey: "kpi-center" },
    { importPath: "@/app/dashboard/utility-management/alarm-center/page", tabKey: "alarm-center" },
    { importPath: "@/app/dashboard/utility-management/alarm-rules/page", tabKey: "alarm-rules" },
    { importPath: "@/app/dashboard/utility-management/billing/page", tabKey: "billing" },
    { importPath: "@/app/dashboard/utility-management/transactions/page", tabKey: "transactions" },
    { importPath: "@/app/dashboard/utility-management/reports/page", tabKey: "reports" },
    { importPath: "@/app/dashboard/utility-management/integration/page", tabKey: "integration" },
    { importPath: "@/app/dashboard/iot/page", tabKey: "iot" },
    { importPath: "@/app/dashboard/esg/page", tabKey: "esg" },
  ],
};

// ─── GIT HISTORY FINDINGS (from git show + git log commands) ─────────────────
// Evidence of real pages that existed before consolidation
const GIT_HISTORY = {
  // Cycle Count - REAL pages existed in commit 674b6c5 (2026-05-01)
  "/dashboard/cycle-count/plans":     { commit: "674b6c5", date: "2026-05-01", wasReal: true,  deletedIn: "bd6faf5", deletedDate: "2026-05-17", note: "Full CRUD: listPlans, createPlan, generateTasks, updatePlan" },
  "/dashboard/cycle-count/tasks":     { commit: "674b6c5", date: "2026-05-01", wasReal: true,  deletedIn: "bd6faf5", deletedDate: "2026-05-17", note: "Task queue with status management" },
  "/dashboard/cycle-count/entries":   { commit: "674b6c5", date: "2026-05-01", wasReal: true,  deletedIn: "bd6faf5", deletedDate: "2026-05-17", note: "Physical count entry recording" },
  "/dashboard/cycle-count/variances": { commit: "674b6c5", date: "2026-05-01", wasReal: true,  deletedIn: "bd6faf5", deletedDate: "2026-05-17", note: "Full approve/reject variance workflow with bulk selection" },
  "/dashboard/cycle-count/reports":   { commit: "674b6c5", date: "2026-05-01", wasReal: true,  deletedIn: "bd6faf5", deletedDate: "2026-05-17", note: "Accuracy, variance, AI insights reporting" },
  // Shelf Life - REAL pages existed in commit bd6faf5 (may have been redirect stubs)
  "/dashboard/shelf-life/bulk-hold-monitor":    { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub in latest known commit" },
  "/dashboard/shelf-life/compliance":           { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/customer-rules":       { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/disposition":          { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/expired":              { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/fefo-config":          { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/lot-aging":            { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/near-expiry":          { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/production-validation":{ commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/shelf-life/retest-queue":         { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  // Traceability - REAL pages existed in commit bd6faf5
  "/dashboard/traceability/backward":   { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/traceability/forward":    { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/traceability/genealogy":  { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/traceability/mock-recall":{ commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/traceability/recalls":    { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Stub + recalls/[id]/page.tsx existed as dynamic route" },
  "/dashboard/traceability/regulatory": { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
  "/dashboard/traceability/search":     { commit: "bd6faf5", date: "2026-05-17", wasReal: false, note: "Exists as redirect stub" },
};

// ─── BROKEN ACTION CARDS DATA (from BROKEN_ACTION_CARDS.json) ────────────────
// Grouped by source file for lookup
const brokenCardsRaw = JSON.parse(
  fs.readFileSync(path.join(DOCS, "BROKEN_ACTION_CARDS.json"), "utf-8")
);

// Build lookup: sourceFile → array of broken stubs
const brokenBySource = {};
for (const entry of brokenCardsRaw) {
  const key = entry.sourceFile;
  if (!brokenBySource[key]) brokenBySource[key] = [];
  brokenBySource[key].push(entry);
}

// ─── HELPER: importPath → relative file path ──────────────────────────────────
function importPathToFile(importPath) {
  // "@/app/dashboard/X/page" → "frontend/src/app/dashboard/X/page.tsx"
  return importPath.replace("@/", "frontend/src/") + ".tsx";
}

// ─── HELPER: file path → route guess ─────────────────────────────────────────
function fileToRoute(filePath) {
  // "frontend/src/app/dashboard/X/page.tsx" → "/dashboard/X"
  return filePath
    .replace("frontend/src/app", "")
    .replace(/\/page\.tsx$/, "")
    .replace(/\/$/, "") || "/";
}

// ─── HELPER: check if route is middleware-redirected ─────────────────────────
function isMiddlewareRedirected(route) {
  // Exact match
  if (MIDDLEWARE_REDIRECTS[route]) return MIDDLEWARE_REDIRECTS[route];
  // Prefix match
  const parts = route.split("/");
  for (let i = parts.length - 1; i >= 2; i--) {
    const prefix = parts.slice(0, i).join("/");
    if (MIDDLEWARE_REDIRECTS[prefix] && !BYPASS_PREFIX_REDIRECT.has(route)) {
      return MIDDLEWARE_REDIRECTS[prefix];
    }
  }
  return null;
}

// ─── BUILD VISIBILITY GRAPH ──────────────────────────────────────────────────

const visibilityGraph = [];
const workspacePages = Object.keys(DYNAMIC_IMPORTS);

// Build reverse map: imported file → workspace pages that import it
const importedByWorkspace = {};
for (const [workspacePage, imports] of Object.entries(DYNAMIC_IMPORTS)) {
  for (const imp of imports) {
    const file = importPathToFile(imp.importPath);
    if (!importedByWorkspace[file]) importedByWorkspace[file] = [];
    importedByWorkspace[file].push({ workspacePage, tabKey: imp.tabKey });
  }
}

// Process each imported file
for (const [filePath, importers] of Object.entries(importedByWorkspace)) {
  const routeGuess = fileToRoute(filePath);
  const middlewareRedirect = isMiddlewareRedirected(routeGuess);
  const isRedirectStubAsStandalone = !!middlewareRedirect;
  const hasBrokenCards = !!brokenBySource[filePath];
  const brokenCards = brokenBySource[filePath] || [];

  visibilityGraph.push({
    filePath,
    routeGuess,
    visibility: "DYNAMICALLY_IMPORTED_VISIBLE",
    visibleBecause: importers.map((imp) => ({
      importedBy: imp.workspacePage,
      importType: "dynamic",
      tabKey: imp.tabKey,
      parentRouteGuess: fileToRoute(imp.workspacePage),
      parentVisibility: "DIRECT_WORKSPACE_VISIBLE",
      evidence: `dynamic(() => import("${filePath.replace("frontend/src/", "@/")}"))`,
    })),
    isRedirectStubAsStandalone,
    standaloneRedirectsTo: isRedirectStubAsStandalone
      ? `${middlewareRedirect.workspace}${middlewareRedirect.tab ? `?tab=${middlewareRedirect.tab}` : ""}${middlewareRedirect.drawer ? `?drawer=${middlewareRedirect.drawer}` : ""}`
      : null,
    isStillUserVisibleThroughImport: true,
    hasBrokenActionCards: hasBrokenCards,
    brokenCardCount: brokenCards.length,
    brokenCardRoutes: brokenCards.map((c) => c.stubRoute),
  });
}

// ─── BUILD BROKEN VISIBLE TARGETS ────────────────────────────────────────────

const brokenVisibleTargets = [];
let idCounter = 1;

// Module classification by workspace
function classifyModule(workspacePage) {
  const route = fileToRoute(workspacePage);
  const moduleMap = {
    "/dashboard/inventory": "Supply Chain / Inventory",
    "/dashboard/warehouses": "Supply Chain / Warehouses",
    "/dashboard/planning": "Manufacturing / Planning",
    "/dashboard/production": "Manufacturing / Production",
    "/dashboard/finance": "Finance",
    "/dashboard/hr": "HR & Payroll",
    "/dashboard/sales": "Commercial / Sales",
    "/dashboard/procurement": "Supply Chain / Procurement",
    "/dashboard/quality": "Factory Operations / Quality",
    "/dashboard/logistics": "Logistics",
    "/dashboard/communication": "Documents & Communication",
    "/dashboard/analytics": "Intelligence / Analytics",
    "/dashboard/admin": "Administration",
    "/dashboard/marketing": "Commercial / Marketing",
    "/dashboard/crm": "Commercial / CRM",
    "/dashboard/documents": "Documents & Communication",
    "/dashboard/integrations": "Administration / Integrations",
    "/dashboard/utility-management": "Factory Operations / Utilities",
  };
  return moduleMap[route] || "Unknown";
}

function getRecommendation(stubRoute, gitInfo) {
  if (gitInfo && gitInfo.wasReal) return "RESTORE_OLD_PAGE_FROM_GIT";
  if (gitInfo && !gitInfo.wasReal) return "CONVERT_TO_WORKSPACE_SUBVIEW";
  // Default: check if it's a same-workspace redirect
  return "CONVERT_TO_WORKSPACE_SUBVIEW";
}

for (const node of visibilityGraph) {
  if (!node.hasBrokenActionCards) continue;

  const brokenCards = brokenBySource[node.filePath] || [];

  for (const card of brokenCards) {
    const stubRoute = card.stubRoute;
    const gitInfo = GIT_HISTORY[stubRoute];
    const importers = node.visibleBecause;
    const parentWorkspace = importers[0]?.parentRouteGuess || "unknown";

    // Determine severity
    let severity = "high";
    if (stubRoute.includes("/new") || stubRoute.includes("/create")) severity = "critical";
    else if (stubRoute.includes("/reports") || stubRoute.includes("/ai")) severity = "medium";

    brokenVisibleTargets.push({
      id: `BVT-${String(idCounter++).padStart(4, "0")}`,
      module: classifyModule(importers[0]?.importedBy || ""),
      sourceFile: node.filePath,
      sourceRouteContext: node.routeGuess,
      visibleVia: `${parentWorkspace}?tab=${importers[0]?.tabKey || "?"}`,
      label: card.stubRoute.split("/").pop() || "unknown",
      currentTarget: card.stubRoute,
      currentBehavior: "redirect_stub",
      redirectsTo: card.redirectTarget,
      whyBroken: `Card in ${node.routeGuess} (user-visible as ${parentWorkspace}?tab=${importers[0]?.tabKey}) links to ${stubRoute} which is a redirect stub → ${card.redirectTarget}. User clicks card → lands on same workspace tab they're already on. Action has no effect.`,
      severity,
      userVisible: true,
      isRedirectStubAsStandalone: node.isRedirectStubAsStandalone,
      evidence: card.matches ? card.matches[0] : "href in source",
      gitHistoryCandidates: gitInfo ? [
        {
          commit: gitInfo.commit,
          commitDate: gitInfo.date,
          filePath: `frontend/src/app${stubRoute}/page.tsx`,
          route: stubRoute,
          wasRealImplementation: gitInfo.wasReal,
          deletedIn: gitInfo.deletedIn || null,
          deletedDate: gitInfo.deletedDate || null,
          evidence: gitInfo.note,
          confidence: gitInfo.wasReal ? "high" : "medium",
          restoreComplexity: gitInfo.wasReal ? "easy" : "medium",
          likelyOriginalTarget: gitInfo.wasReal,
        }
      ] : [],
      recommendation: getRecommendation(stubRoute, gitInfo),
    });
  }
}

// ─── STATISTICS ──────────────────────────────────────────────────────────────

const stats = {
  totalDynamicallyImportedPages: visibilityGraph.length,
  pagesWithBrokenCards: visibilityGraph.filter((n) => n.hasBrokenActionCards).length,
  pagesWithRedirectStubAndBrokenCards: visibilityGraph.filter((n) => n.isRedirectStubAsStandalone && n.hasBrokenActionCards).length,
  totalBrokenVisibleTargets: brokenVisibleTargets.length,
  criticalSeverity: brokenVisibleTargets.filter((t) => t.severity === "critical").length,
  highSeverity: brokenVisibleTargets.filter((t) => t.severity === "high").length,
  mediumSeverity: brokenVisibleTargets.filter((t) => t.severity === "medium").length,
  gitHistoryMatchesFound: brokenVisibleTargets.filter((t) => t.gitHistoryCandidates.length > 0).length,
  highConfidenceMatches: brokenVisibleTargets.filter((t) => t.gitHistoryCandidates.some((g) => g.confidence === "high")).length,
  restoreFromGitRecommendation: brokenVisibleTargets.filter((t) => t.recommendation === "RESTORE_OLD_PAGE_FROM_GIT").length,
  convertToSubviewRecommendation: brokenVisibleTargets.filter((t) => t.recommendation === "CONVERT_TO_WORKSPACE_SUBVIEW").length,
};

// Group by module
const byModule = {};
for (const target of brokenVisibleTargets) {
  if (!byModule[target.module]) byModule[target.module] = [];
  byModule[target.module].push(target);
}

// ─── WRITE OUTPUTS ────────────────────────────────────────────────────────────

// 1. VISIBLE_IMPORT_GRAPH.json
fs.writeFileSync(
  path.join(DOCS, "VISIBLE_IMPORT_GRAPH.json"),
  JSON.stringify(visibilityGraph, null, 2)
);

// 2. VISIBLE_BROKEN_ACTION_TARGETS.json
fs.writeFileSync(
  path.join(DOCS, "VISIBLE_BROKEN_ACTION_TARGETS.json"),
  JSON.stringify(brokenVisibleTargets, null, 2)
);

// 3. VISIBLE_IMPORT_GRAPH.md
const graphMd = `# Visible Import Graph

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
| Total dynamically imported pages | ${stats.totalDynamicallyImportedPages} |
| Pages with broken action cards | ${stats.pagesWithBrokenCards} |
| Pages that are BOTH redirect stubs AND have broken cards | ${stats.pagesWithRedirectStubAndBrokenCards} |
| Total broken visible action targets | ${stats.totalBrokenVisibleTargets} |

## Pages with Broken Action Cards (User-Visible Through Dynamic Import)

${visibilityGraph
  .filter((n) => n.hasBrokenActionCards)
  .map((n) => `### ${n.filePath}

- **Route (standalone):** \`${n.routeGuess}\`
- **Standalone redirected:** ${n.isRedirectStubAsStandalone ? `YES → ${n.standaloneRedirectsTo}` : "NO"}
- **Visible via:** ${n.visibleBecause.map((v) => `\`${v.parentRouteGuess}?tab=${v.tabKey}\``).join(", ")}
- **Broken card count:** ${n.brokenCardCount}
- **Broken targets:** ${n.brokenCardRoutes.map((r) => `\`${r}\``).join(", ")}
`)
  .join("\n")}
`;
fs.writeFileSync(path.join(DOCS, "VISIBLE_IMPORT_GRAPH.md"), graphMd);

// 4. VISIBLE_BROKEN_ACTION_TARGETS.md
const brokenMd = `# Visible Broken Action Targets

**Date:** 2026-05-21
**Total broken visible buttons/cards/tiles:** ${stats.totalBrokenVisibleTargets}

## Statistics

| Metric | Count |
|--------|-------|
| Critical severity | ${stats.criticalSeverity} |
| High severity | ${stats.highSeverity} |
| Medium severity | ${stats.mediumSeverity} |
| Git history matches found | ${stats.gitHistoryMatchesFound} |
| High-confidence original page found | ${stats.highConfidenceMatches} |
| Recommendation: RESTORE FROM GIT | ${stats.restoreFromGitRecommendation} |
| Recommendation: CONVERT TO SUBVIEW | ${stats.convertToSubviewRecommendation} |

${Object.entries(byModule).map(([module, targets]) => `## ${module}

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
${targets.map((t) => `| ${t.id} | ${t.sourceFile.replace("frontend/src/app/dashboard/", "")} | ${t.visibleVia} | \`${t.currentTarget}\` | ${t.severity} | ${t.recommendation} |`).join("\n")}
`).join("\n")}
`;
fs.writeFileSync(path.join(DOCS, "VISIBLE_BROKEN_ACTION_TARGETS.md"), brokenMd);

// 5. BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json
const matchReport = {
  generatedDate: "2026-05-21",
  auditVersion: "v2.0-dynamic-import-aware",
  keyFinding: "Previous audit blind spot: pages dynamically imported into workspace tabs were incorrectly classified as 'safe' because their standalone routes were middleware-redirected. These pages ARE user-visible and their broken action cards ARE encountered by users.",
  stats,
  moduleGroups: Object.entries(byModule).map(([module, targets]) => ({
    module,
    brokenCount: targets.length,
    targets: targets.map((t) => ({
      id: t.id,
      module: t.module,
      visibleLocation: t.visibleVia,
      buttonLabel: t.currentTarget.split("/").pop(),
      currentTarget: t.currentTarget,
      currentBehavior: t.currentBehavior,
      redirectsTo: t.redirectsTo,
      whyBroken: t.whyBroken,
      severity: t.severity,
      gitHistoryFound: t.gitHistoryCandidates.length > 0,
      gitHistoryWasRealPage: t.gitHistoryCandidates.some((g) => g.wasRealImplementation),
      bestMatchOriginalPage: t.gitHistoryCandidates.length > 0 ? t.gitHistoryCandidates[0] : null,
      recommendation: t.recommendation,
    })),
  })),
};
fs.writeFileSync(
  path.join(DOCS, "BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json"),
  JSON.stringify(matchReport, null, 2)
);

// 6. BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md
const top20 = brokenVisibleTargets
  .filter((t) => t.severity === "critical" || t.severity === "high")
  .slice(0, 20);

const matchMd = `# Broken Button → Original Page Match Report

**Date:** 2026-05-21
**Audit Version:** v2.0 — Dynamic Import Aware

---

## THE AUDIT BLIND SPOT: Dynamic Import Visibility

### Why Previous Reports Were Wrong

Previous audit logic:
> "If a standalone route is middleware-redirected, all action cards in that page are invisible to users."

**This is incorrect.** A page is user-visible if ANY of these are true:
1. It is directly reachable from sidebar/nav
2. It is dynamically imported by a workspace page as tab content

### The Cycle Count Example (Still Broken)

**Visible location:** \`/dashboard/inventory?tab=cycle-count\`
**Source component:** \`frontend/src/app/dashboard/cycle-count/page.tsx\`
**How it becomes visible:** \`inventory/page.tsx\` dynamically imports \`cycle-count/page\`
**Standalone route redirect:** \`/dashboard/cycle-count\` → \`/dashboard/inventory?tab=cycle-count\` (middleware)
**Result:** User sees Cycle Count dashboard with 5 navigation tiles — ALL broken.

| Card | Target | Current Behavior | Git History | Recommendation |
|------|--------|------------------|-------------|----------------|
| Count Plans | \`/dashboard/cycle-count/plans\` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Count Tasks | \`/dashboard/cycle-count/tasks\` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Count Entries | \`/dashboard/cycle-count/entries\` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Variance Review | \`/dashboard/cycle-count/variances\` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Reports & AI | \`/dashboard/cycle-count/reports\` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |

**Git evidence:** Commit \`674b6c5\` (2026-05-01) contained REAL implementations:
- \`cycle-count/plans/page.tsx\`: Full CRUD — listPlans, createPlan, generateTasks, updatePlan
- \`cycle-count/variances/page.tsx\`: Full approve/reject workflow with bulk selection
- \`cycle-count/tasks/page.tsx\`: Task queue management
- \`cycle-count/entries/page.tsx\`: Physical count entry recording
- \`cycle-count/reports/page.tsx\`: Accuracy and variance reporting

These were deleted in \`bd6faf5\` (2026-05-17) and replaced with redirect stubs.

---

## Statistics

| Metric | Count |
|--------|-------|
| Dynamically imported pages analyzed | ${stats.totalDynamicallyImportedPages} |
| Pages with broken cards (user-visible) | ${stats.pagesWithBrokenCards} |
| Pages: BOTH redirect stub AND has broken cards | ${stats.pagesWithRedirectStubAndBrokenCards} |
| **Total broken visible action targets** | **${stats.totalBrokenVisibleTargets}** |
| Critical severity | ${stats.criticalSeverity} |
| High severity | ${stats.highSeverity} |
| Medium severity | ${stats.mediumSeverity} |
| Git history matches found | ${stats.gitHistoryMatchesFound} |
| High-confidence original page found | ${stats.highConfidenceMatches} |

---

## Recommendation Categories

| Category | Count | Description |
|----------|-------|-------------|
| RESTORE_OLD_PAGE_FROM_GIT | ${stats.restoreFromGitRecommendation} | Real page existed in git — restore from commit 674b6c5 |
| CONVERT_TO_WORKSPACE_SUBVIEW | ${stats.convertToSubviewRecommendation} | No prior real page — implement as ?view= or ?subtab= |

---

## Top 20 Critical/High Severity Broken Visible Buttons

| ID | Module | Visible At | Card Target | Why Broken | Git Found | Recommendation |
|----|--------|-----------|-------------|------------|-----------|----------------|
${top20.map((t) => `| ${t.id} | ${t.module} | ${t.visibleVia} | \`${t.currentTarget}\` | Redirect stub → ${t.redirectsTo} | ${t.gitHistoryCandidates.length > 0 ? (t.gitHistoryCandidates[0].wasRealImplementation ? "YES (real page)" : "YES (stub)") : "NO"} | ${t.recommendation} |`).join("\n")}

---

## Full Breakdown by Module

${Object.entries(byModule).map(([module, targets]) => `### ${module}

**Broken count:** ${targets.length}

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
${targets.map((t) => {
  const git = t.gitHistoryCandidates[0];
  const gitFound = git ? (git.wasRealImplementation ? `Yes — real page commit ${git.commit} (${git.commitDate})` : `Yes — redirect stub commit ${git.commit}`) : "No";
  const bestMatch = git ? (git.wasRealImplementation ? git.filePath : "Needs new implementation") : "Unknown";
  const conf = git ? git.confidence : "low";
  return `| ${module} | ${t.visibleVia} | \`${t.currentTarget.split("/").pop()}\` | \`${t.currentTarget}\` | redirect_stub → ${t.redirectsTo} | ${gitFound} | ${bestMatch} | ${conf} | ${t.recommendation} |`;
}).join("\n")}

`).join("\n")}

---

## Dynamic Import Visibility Failures

These cases were MISSED by the previous audit because it treated middleware-redirected pages
as "invisible to users" without checking if they are dynamically imported into workspace tabs.

${visibilityGraph
  .filter((n) => n.isRedirectStubAsStandalone && n.hasBrokenActionCards)
  .map((n) => `### ${n.routeGuess} (${n.brokenCardCount} broken cards)

- **Standalone route:** \`${n.routeGuess}\` → middleware redirects to \`${n.standaloneRedirectsTo}\`
- **Also visible as:** Tab content in ${n.visibleBecause.map((v) => `\`${v.parentRouteGuess}?tab=${v.tabKey}\``).join(", ")}
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** ${n.brokenCardRoutes.map((r) => `\`${r}\``).join(", ")}
`)
  .join("\n")}

---

## Do Not Fix

This report is READ-ONLY. No code was modified.
Recommendations are provided for future fix passes only.
`;

fs.writeFileSync(
  path.join(DOCS, "BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md"),
  matchMd
);

// ─── CONSOLE OUTPUT ───────────────────────────────────────────────────────────
console.log("\n=== AUDIT COMPLETE ===\n");
console.log(`Total dynamically imported pages scanned:     ${stats.totalDynamicallyImportedPages}`);
console.log(`Pages with broken action cards:               ${stats.pagesWithBrokenCards}`);
console.log(`Pages: redirect stub + broken cards (missed): ${stats.pagesWithRedirectStubAndBrokenCards}`);
console.log(`TOTAL BROKEN VISIBLE ACTION TARGETS:          ${stats.totalBrokenVisibleTargets}`);
console.log(`  Critical:                                   ${stats.criticalSeverity}`);
console.log(`  High:                                       ${stats.highSeverity}`);
console.log(`  Medium:                                     ${stats.mediumSeverity}`);
console.log(`Git history matches found:                    ${stats.gitHistoryMatchesFound}`);
console.log(`High-confidence original page matches:        ${stats.highConfidenceMatches}`);
console.log(`\nOutputs:`);
console.log(`  docs/VISIBLE_IMPORT_GRAPH.json`);
console.log(`  docs/VISIBLE_IMPORT_GRAPH.md`);
console.log(`  docs/VISIBLE_BROKEN_ACTION_TARGETS.json`);
console.log(`  docs/VISIBLE_BROKEN_ACTION_TARGETS.md`);
console.log(`  docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.json`);
console.log(`  docs/BROKEN_BUTTON_ORIGINAL_PAGE_MATCH_REPORT.md`);
