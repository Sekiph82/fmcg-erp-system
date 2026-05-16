/**
 * ERP Navigation Configuration — Workspace-based flat hierarchy
 * 33 workspace entries in 9 cluster groups.
 * Child functions live inside workspace tabs, not in the sidebar.
 *
 * How to add a module without creating route sprawl:
 *   1. Add a ws() entry in the correct cluster below.
 *   2. Create /dashboard/<slug>/page.tsx using ModuleWorkspace.
 *   3. Add old-route redirects in routeRedirectMap.ts + middleware.ts.
 *   Never add child items/sections here — those become sidebar links.
 */
import React from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface NavChild {
  label: string;
  href: string;
  permission?: string;
}

export interface NavSection {
  type: "section";
  id: string;
  label: string;
  icon: React.ReactNode;
  permission?: string;
  items: NavChild[];
}

export interface NavStandaloneLink {
  type: "link";
  id: string;
  label: string;
  href: string;
  icon: React.ReactNode;
  permission?: string;
}

export interface NavWorkspaceLink {
  type: "workspace";
  id: string;
  label: string;
  href: string;
  icon: React.ReactNode;
  permission?: string;
  searchHints?: Array<{ label: string; tab: string }>;
}

export interface NavClusterHeader {
  type: "cluster-header";
  id: string;
  label: string;
}

export type NavEntry = NavStandaloneLink | NavSection | NavWorkspaceLink | NavClusterHeader;

// ── Helpers ───────────────────────────────────────────────────────────────────

function I(size: "md" | "sm", ...ds: string[]): React.ReactNode {
  const dim = size === "md" ? "h-[17px] w-[17px]" : "h-[14px] w-[14px]";
  return (
    <svg className={`${dim} shrink-0`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {ds.map((d, i) => (
        <path key={i} strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d={d} />
      ))}
    </svg>
  );
}

const md = (...ds: string[]) => I("md", ...ds);

const cluster = (id: string, label: string): NavClusterHeader => ({
  type: "cluster-header",
  id,
  label,
});

function ws(
  id: string,
  label: string,
  href: string,
  icon: React.ReactNode,
  opts?: { permission?: string; searchHints?: Array<{ label: string; tab: string }> }
): NavWorkspaceLink {
  return { type: "workspace", id, label, href, icon, ...opts };
}

// ── Navigation config ─────────────────────────────────────────────────────────

export const NAV_CONFIG: NavEntry[] = [

  // Dashboard
  {
    type: "link",
    id: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: md("M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"),
  },

  // ── Supply Chain ────────────────────────────────────────────────────────────
  cluster("cluster-supply-chain", "Supply Chain"),

  ws("products",    "Products",        "/dashboard/products",
    md("M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"),
    { permission: "products.view" }),

  ws("materials",   "Materials",       "/dashboard/materials",
    md("M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"),
    { permission: "products.view" }),

  ws("suppliers",   "Suppliers",       "/dashboard/suppliers",
    md("M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"),
    { permission: "procurement.view" }),

  ws("inventory",   "Inventory",       "/dashboard/inventory",
    md("M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"),
    { permission: "inventory.view", searchHints: [
      { label: "Cycle Count",         tab: "cycle-count" },
      { label: "Shelf Life / FEFO",   tab: "shelf-life" },
      { label: "Lot Traceability",    tab: "traceability" },
      { label: "Serial / Batch",      tab: "serials" },
      { label: "Stock Movements",     tab: "movements" },
    ]}),

  ws("warehouses",  "Warehouses & WMS","/dashboard/warehouses",
    md("M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"),
    { permission: "inventory.view", searchHints: [
      { label: "WMS / Picking",       tab: "wms" },
      { label: "Putaway",             tab: "wms" },
      { label: "Bin Replenishment",   tab: "wms" },
    ]}),

  ws("procurement", "Procurement",     "/dashboard/procurement",
    md("M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"),
    { permission: "procurement.view", searchHints: [
      { label: "Subcontracting",      tab: "subcontracting" },
      { label: "Landed Cost",         tab: "landed-cost" },
      { label: "Supplier Portal",     tab: "supplier-portal" },
      { label: "AI Suggestions",      tab: "suggestions" },
    ]}),

  // ── Manufacturing ───────────────────────────────────────────────────────────
  cluster("cluster-manufacturing", "Manufacturing"),

  ws("production",  "Production",      "/dashboard/production",
    md("M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"),
    { permission: "production.view", searchHints: [
      { label: "Production Execution",tab: "execution" },
      { label: "Machine Operators",   tab: "machine-ops" },
      { label: "Material Flow",       tab: "material-flow" },
      { label: "OEE Records",         tab: "oee" },
      { label: "Batch / Lots",        tab: "batch-lots" },
    ]}),

  ws("planning",    "Planning",        "/dashboard/planning",
    md("M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"),
    { permission: "production.view", searchHints: [
      { label: "MRP",                 tab: "mrp" },
      { label: "MPS",                 tab: "mps" },
      { label: "Kanban",              tab: "kanban" },
      { label: "Capacity Board",      tab: "advanced" },
      { label: "Simulation",          tab: "advanced" },
    ]}),

  ws("npd",         "NPD",             "/dashboard/npd",
    md("M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"),
    { permission: "npd.view" }),

  ws("bom",         "BOM & Formula",   "/dashboard/bom",
    md("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"),
    { permission: "bom.view", searchHints: [
      { label: "Formula Versions",    tab: "list" },
      { label: "Substitutes",         tab: "substitutes" },
      { label: "BOM Compare",         tab: "compare" },
    ]}),

  ws("recipes",     "Recipes",         "/dashboard/recipes",
    md("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"),
    { permission: "recipe.view" }),

  ws("quality",     "Quality",         "/dashboard/quality",
    md("M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"),
    { permission: "quality.view", searchHints: [
      { label: "QMS & HACCP",         tab: "qms" },
      { label: "Allergen Matrix",     tab: "allergen" },
      { label: "Consumer Complaints", tab: "consumer-complaints" },
      { label: "CAPA",                tab: "qms" },
      { label: "COA",                 tab: "qms" },
    ]}),

  ws("compliance",  "Compliance",      "/dashboard/compliance",
    md("M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"),
    { permission: "gs1.view", searchHints: [
      { label: "GS1 Labels",          tab: "gs1" },
      { label: "Barcode Generator",   tab: "gs1" },
      { label: "Print Queue",         tab: "gs1" },
      { label: "Regulatory Certs",    tab: "regulatory-certs" },
    ]}),

  ws("shop-floor",  "Shop Floor",      "/dashboard/shop-floor",
    md("M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"),
    { permission: "production.view", searchHints: [
      { label: "Operator Terminal",   tab: "terminal" },
      { label: "Supervisor Console",  tab: "supervisor" },
      { label: "Queue Board",         tab: "queue" },
    ]}),

  // ── Commercial ──────────────────────────────────────────────────────────────
  cluster("cluster-commercial", "Commercial"),

  ws("sales",       "Sales",           "/dashboard/sales",
    md("M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"),
    { permission: "sales.view", searchHints: [
      { label: "Price Lists",         tab: "price-lists" },
      { label: "Van Sales",           tab: "van-sales" },
      { label: "Secondary Sales",     tab: "secondary" },
      { label: "Commissions",         tab: "commissions" },
      { label: "Recurring Orders",    tab: "recurring" },
      { label: "Customer Portal",     tab: "portal" },
      { label: "Dynamic Pricing",     tab: "dynamic-pricing" },
    ]}),

  ws("crm",         "CRM",             "/dashboard/crm",
    md("M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"),
    { permission: "sales.view", searchHints: [
      { label: "Pipeline Board",      tab: "pipeline" },
      { label: "Loyalty Program",     tab: "loyalty" },
      { label: "NPS Tracking",        tab: "nps" },
      { label: "Surveys",             tab: "surveys" },
    ]}),

  ws("marketing",   "Marketing",       "/dashboard/marketing",
    md("M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z", "M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"),
    { permission: "marketing.view", searchHints: [
      { label: "TPM",                 tab: "tpm" },
      { label: "Trade Spend",         tab: "tpm" },
      { label: "Promotions",          tab: "promotions-schemes" },
      { label: "Market Intelligence", tab: "market-intel" },
      { label: "E-commerce",          tab: "ecommerce" },
    ]}),

  ws("pos",         "POS",             "/dashboard/pos",
    md("M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"),
    { permission: "sales.view" }),

  // ── Finance ─────────────────────────────────────────────────────────────────
  cluster("cluster-finance", "Finance"),

  ws("finance",     "Finance",         "/dashboard/finance",
    md("M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"),
    { permission: "finance.view", searchHints: [
      { label: "Bank Reconciliation", tab: "bank-recon" },
      { label: "Invoice Match",       tab: "invoice-match" },
      { label: "Fixed Assets",        tab: "fixed-assets" },
      { label: "Dimensions",          tab: "dimensions" },
      { label: "Dunning",             tab: "dunning" },
      { label: "Tax",                 tab: "tax" },
      { label: "Journal Entries",     tab: "accounting" },
      { label: "eTIMS / e-Invoice",   tab: "tax" },
    ]}),

  // ── Factory Operations ──────────────────────────────────────────────────────
  cluster("cluster-factory", "Factory Operations"),

  ws("maintenance", "Maintenance",     "/dashboard/maintenance",
    md("M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z", "M15 12a3 3 0 11-6 0 3 3 0 016 0z"),
    { permission: "maintenance.view" }),

  ws("utility-management", "Utilities","/dashboard/utility-management",
    md("M13 10V3L4 14h7v7l9-11h-7z"),
    { permission: "utility_management.view", searchHints: [
      { label: "Electricity",         tab: "electricity" },
      { label: "Water",               tab: "water" },
      { label: "ESG",                 tab: "esg" },
      { label: "IoT",                 tab: "iot" },
      { label: "Alarms",              tab: "alarms" },
      { label: "KPI Center",          tab: "kpi" },
    ]}),

  // ── Logistics ───────────────────────────────────────────────────────────────
  cluster("cluster-logistics", "Logistics"),

  ws("logistics",   "Logistics",       "/dashboard/logistics",
    md("M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"),
    { permission: "logistics.view", searchHints: [
      { label: "Fleet",               tab: "fleet" },
      { label: "Containers",          tab: "containers" },
      { label: "Shipments",           tab: "shipments" },
    ]}),

  // ── HR & Payroll ────────────────────────────────────────────────────────────
  cluster("cluster-hr", "HR & Payroll"),

  ws("hr",          "HR",              "/dashboard/hr",
    md("M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"),
    { permission: "hr.view", searchHints: [
      { label: "Recruitment",         tab: "recruitment" },
      { label: "Appraisals",          tab: "appraisals" },
      { label: "Timesheets",          tab: "timesheets" },
      { label: "ESS",                 tab: "ess" },
      { label: "Training",            tab: "training" },
      { label: "Expenses",            tab: "expenses" },
    ]}),

  ws("payroll",     "Kenya Payroll",   "/dashboard/payroll",
    md("M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"),
    { permission: "payroll_ke.view" }),

  // ── Documents & Communication ────────────────────────────────────────────────
  cluster("cluster-comms", "Documents & Communication"),

  ws("documents",   "Documents",       "/dashboard/documents",
    md("M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"),
    { permission: "documents.view", searchHints: [
      { label: "Knowledge Base",      tab: "knowledge-base" },
      { label: "E-Signatures",        tab: "esign" },
      { label: "Contracts",           tab: "contracts" },
    ]}),

  ws("communication","Communication",  "/dashboard/communication",
    md("M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"),
    { searchHints: [
      { label: "Chatter",             tab: "chatter" },
      { label: "Calendar",            tab: "calendar" },
      { label: "Notifications",       tab: "notifications" },
      { label: "WhatsApp",            tab: "whatsapp" },
    ]}),

  ws("helpdesk",    "Helpdesk",        "/dashboard/helpdesk",
    md("M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"),
    { permission: "quality.view" }),

  // ── Intelligence ─────────────────────────────────────────────────────────────
  cluster("cluster-intelligence", "Intelligence"),

  ws("ai",          "AI",              "/dashboard/ai",
    md("M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"),
    { permission: "ai.view", searchHints: [
      { label: "AI Chat / Copilot",   tab: "chat" },
      { label: "Predictions",         tab: "predictions" },
      { label: "Formulations",        tab: "formulations" },
      { label: "Scenarios",           tab: "scenarios" },
    ]}),

  ws("analytics",   "Analytics",       "/dashboard/analytics",
    md("M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"),
    { permission: "analytics.view", searchHints: [
      { label: "Report Builder",      tab: "report-builder" },
      { label: "Saved Reports",       tab: "reports" },
      { label: "Market Intelligence", tab: "market-intel" },
    ]}),

  // ── Administration ───────────────────────────────────────────────────────────
  cluster("cluster-admin", "Administration"),

  ws("admin",       "Admin",           "/dashboard/admin",
    md("M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z", "M15 12a3 3 0 11-6 0 3 3 0 016 0z"),
    { permission: "users.view", searchHints: [
      { label: "Users",               tab: "users" },
      { label: "Roles",               tab: "roles" },
      { label: "Security",            tab: "security" },
      { label: "Custom Fields",       tab: "custom-fields" },
      { label: "System Config",       tab: "system-config" },
      { label: "Audit Logs",          tab: "logs" },
    ]}),

  ws("integrations","Integrations",    "/dashboard/integrations",
    md("M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"),
    { permission: "integrations.view", searchHints: [
      { label: "Webhooks",            tab: "webhooks" },
      { label: "Developer Portal",    tab: "developer" },
      { label: "API Keys",            tab: "developer" },
      { label: "M-Pesa",              tab: "mpesa" },
    ]}),

];

// ── Active path helpers ───────────────────────────────────────────────────────

export function isItemActive(href: string, pathname: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(href + "/");
}

export function getSectionIdForPath(pathname: string): string | null {
  for (const entry of NAV_CONFIG) {
    if (entry.type === "workspace" || entry.type === "link") {
      if (isItemActive(entry.href, pathname)) return entry.id;
    }
    // Legacy section support
    if (entry.type === "section") {
      if (entry.items.some((item) => isItemActive(item.href, pathname))) {
        return entry.id;
      }
    }
  }
  return null;
}
