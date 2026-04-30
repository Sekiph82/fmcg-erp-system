/**
 * ERP Navigation Configuration
 * Data-driven. Add a section, item, or cluster header here — sidebar renders automatically.
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

/** Non-interactive cluster label — visually separates groups of sections */
export interface NavClusterHeader {
  type: "cluster-header";
  id: string;
  label: string;
}

export type NavEntry = NavStandaloneLink | NavSection | NavClusterHeader;

// ── Icon helper ───────────────────────────────────────────────────────────────

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

// ── Cluster header helper ─────────────────────────────────────────────────────

const cluster = (id: string, label: string): NavClusterHeader => ({
  type: "cluster-header",
  id,
  label,
});

// ── Navigation config ─────────────────────────────────────────────────────────

export const NAV_CONFIG: NavEntry[] = [

  // ── Dashboard ────────────────────────────────────────────────────────────────
  {
    type: "link",
    id: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: md(
      "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
    ),
  },

  // ╔══════════════════════════════╗
  // ║       OPERATIONS             ║
  // ╚══════════════════════════════╝
  cluster("cluster-operations", "Operations"),

  {
    type: "section",
    id: "master",
    label: "Master Data",
    icon: md(
      "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
    ),
    items: [
      { label: "Products",      href: "/dashboard/products",        permission: "products.view" },
      { label: "Materials",     href: "/dashboard/materials",       permission: "products.view" },
      { label: "Suppliers",     href: "/dashboard/suppliers",       permission: "procurement.view" },
      { label: "Warehouses",    href: "/dashboard/warehouses",      permission: "warehouses.view" },
      { label: "Customers",     href: "/dashboard/sales/customers", permission: "sales.view" },
      { label: "Recipes / BOM", href: "/dashboard/recipes",         permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "production",
    label: "Production / MES",
    permission: "production.view",
    icon: md(
      "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
    ),
    items: [
      { label: "Production Plans",  href: "/dashboard/production",                 permission: "production.view" },
      { label: "Production Orders", href: "/dashboard/production/orders",          permission: "production.view" },
      { label: "Work Centers",      href: "/dashboard/production/work-centers",    permission: "production.view" },
      { label: "Scheduling",        href: "/dashboard/production/scheduling",      permission: "production.view" },
      { label: "OEE Records",       href: "/dashboard/production/oee",             permission: "production.view" },
      { label: "Waste & Yield",     href: "/dashboard/production/waste-yield",     permission: "production.view" },
      { label: "Batch / Lots",      href: "/dashboard/production/batch-lots",      permission: "production.view" },
      { label: "Costing",           href: "/dashboard/production/costing",         permission: "production.view" },
      { label: "AI Intelligence",   href: "/dashboard/production/ai",              permission: "production.view" },
      { label: "MES Reports",       href: "/dashboard/production/reports",         permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "warehouse",
    label: "Warehouse & Inventory",
    icon: md("M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"),
    items: [
      { label: "Inventory",       href: "/dashboard/inventory",   permission: "inventory.view" },
      { label: "Stock Movements", href: "/dashboard/movements",   permission: "inventory.view" },
      { label: "WMS / Zones",     href: "/dashboard/wms",         permission: "wms.view" },
      { label: "Stock Counts",    href: "/dashboard/wms/counts",  permission: "wms.view" },
      { label: "WMS Reports",     href: "/dashboard/wms/reports", permission: "wms.view" },
    ],
  },

  {
    type: "section",
    id: "procurement",
    label: "Procurement",
    permission: "procurement.view",
    icon: md(
      "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
    ),
    items: [
      { label: "Purchase Requests",  href: "/dashboard/procurement",            permission: "procurement.view" },
      { label: "Purchase Orders",    href: "/dashboard/procurement/orders",     permission: "procurement.view" },
      { label: "Delivery Planning",  href: "/dashboard/procurement/deliveries", permission: "procurement.view" },
      { label: "Supplier Scorecard", href: "/dashboard/procurement/suppliers",  permission: "procurement.view" },
    ],
  },

  {
    type: "section",
    id: "subcontracting",
    label: "Subcontracting",
    permission: "procurement.view",
    icon: md(
      "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
    ),
    items: [
      { label: "SC Dashboard",        href: "/dashboard/subcontracting",              permission: "procurement.view" },
      { label: "Orders",              href: "/dashboard/subcontracting/orders",        permission: "procurement.view" },
      { label: "SC Locations",        href: "/dashboard/subcontracting/locations",     permission: "procurement.view" },
      { label: "Subcontractor Stock", href: "/dashboard/subcontracting/stock",         permission: "procurement.view" },
      { label: "Yield Analysis",      href: "/dashboard/subcontracting/yield",         permission: "procurement.view" },
      { label: "Performance",         href: "/dashboard/subcontracting/performance",   permission: "procurement.view" },
      { label: "AI Agents",           href: "/dashboard/subcontracting/ai",            permission: "procurement.view" },
    ],
  },

  {
    type: "section",
    id: "invoice-match",
    label: "3-Way Invoice Matching",
    permission: "finance.view",
    icon: md(
      "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
    ),
    items: [
      { label: "Match Dashboard",   href: "/dashboard/invoice-match",                permission: "finance.view" },
      { label: "All Matches",       href: "/dashboard/invoice-match/matches",         permission: "finance.view" },
      { label: "Review Queue",      href: "/dashboard/invoice-match/review-queue",    permission: "finance.view" },
      { label: "Blocked Invoices",  href: "/dashboard/invoice-match/blocked",         permission: "finance.view" },
      { label: "Duplicate Review",  href: "/dashboard/invoice-match/duplicates",      permission: "finance.view" },
      { label: "Tolerance Rules",   href: "/dashboard/invoice-match/tolerance-rules", permission: "finance.view" },
      { label: "Reports",           href: "/dashboard/invoice-match/reports",         permission: "finance.view" },
      { label: "AI Agents",         href: "/dashboard/invoice-match/ai",              permission: "finance.view" },
    ],
  },

  {
    type: "section",
    id: "bank-reconciliation",
    label: "Bank Reconciliation",
    permission: "finance.view",
    icon: md(
      "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
    ),
    items: [
      { label: "Dashboard",         href: "/dashboard/bank-reconciliation",              permission: "finance.view" },
      { label: "Import Statement",  href: "/dashboard/bank-reconciliation/import",       permission: "finance.view" },
      { label: "All Statements",    href: "/dashboard/bank-reconciliation/statements",   permission: "finance.view" },
      { label: "Bank Accounts",     href: "/dashboard/bank-reconciliation/accounts",     permission: "finance.view" },
      { label: "Open Items Aging",  href: "/dashboard/bank-reconciliation/open-items",   permission: "finance.view" },
      { label: "Matching Rules",    href: "/dashboard/bank-reconciliation/rules",        permission: "finance.view" },
      { label: "Bank vs Ledger",    href: "/dashboard/bank-reconciliation/balance",      permission: "finance.view" },
      { label: "M-Pesa Recon",      href: "/dashboard/bank-reconciliation/mpesa",        permission: "finance.view" },
      { label: "Reports",           href: "/dashboard/bank-reconciliation/reports",      permission: "finance.view" },
      { label: "AI Agents",         href: "/dashboard/bank-reconciliation/ai",           permission: "finance.view" },
    ],
  },

  {
    type: "section",
    id: "fixed-assets",
    label: "Fixed Assets",
    permission: "finance.view",
    icon: md(
      "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
    ),
    items: [
      { label: "Dashboard",      href: "/dashboard/fixed-assets",              permission: "finance.view" },
      { label: "Asset Register", href: "/dashboard/fixed-assets/assets",       permission: "finance.view" },
      { label: "New Asset",      href: "/dashboard/fixed-assets/assets/new",   permission: "finance.view" },
      { label: "Categories",     href: "/dashboard/fixed-assets/categories",   permission: "finance.view" },
      { label: "Depreciation",   href: "/dashboard/fixed-assets/depreciation", permission: "finance.view" },
      { label: "Posting Run",    href: "/dashboard/fixed-assets/posting",      permission: "finance.view" },
      { label: "Disposals",      href: "/dashboard/fixed-assets/disposal",     permission: "finance.view" },
      { label: "Transfers",      href: "/dashboard/fixed-assets/transfer",     permission: "finance.view" },
      { label: "Legacy Import",  href: "/dashboard/fixed-assets/import",       permission: "finance.view" },
      { label: "AI Agents",      href: "/dashboard/fixed-assets/ai",           permission: "finance.view" },
    ],
  },

  {
    type: "section",
    id: "dimensions",
    label: "Accounting Dimensions",
    permission: "finance.view",
    icon: md(
      "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
    ),
    items: [
      { label: "Dashboard",        href: "/dashboard/dimensions",              permission: "finance.view" },
      { label: "Dimension Types",  href: "/dashboard/dimensions/types",        permission: "finance.view" },
      { label: "Dim Values",       href: "/dashboard/dimensions/values",       permission: "finance.view" },
      { label: "Cost Centers",     href: "/dashboard/dimensions/cost-centers", permission: "finance.view" },
      { label: "Allocation Rules", href: "/dashboard/dimensions/allocations",  permission: "finance.view" },
      { label: "Allocation Run",   href: "/dashboard/dimensions/allocation-run", permission: "finance.view" },
      { label: "Validation Rules", href: "/dashboard/dimensions/validation",   permission: "finance.view" },
      { label: "Default Rules",    href: "/dashboard/dimensions/defaults",     permission: "finance.view" },
      { label: "Reclassify",       href: "/dashboard/dimensions/reclassify",   permission: "finance.view" },
      { label: "Completeness",     href: "/dashboard/dimensions/completeness", permission: "finance.view" },
      { label: "AI Agents",        href: "/dashboard/dimensions/ai",           permission: "finance.view" },
    ],
  },

  {
    type: "section",
    id: "landed-cost",
    label: "Landed Cost Allocation",
    permission: "procurement.view",
    icon: md(
      "M3 10h18M3 14h18M10 3v18M14 3v18M3 6a3 3 0 013-3h12a3 3 0 013 3v12a3 3 0 01-3 3H6a3 3 0 01-3-3V6z"
    ),
    items: [
      { label: "LC Dashboard",    href: "/dashboard/landed-cost",              permission: "procurement.view" },
      { label: "Documents",       href: "/dashboard/landed-cost/documents",    permission: "procurement.view" },
      { label: "New Document",    href: "/dashboard/landed-cost/new",          permission: "procurement.view" },
      { label: "Reports",         href: "/dashboard/landed-cost/reports",      permission: "procurement.view" },
      { label: "AI Agents",       href: "/dashboard/landed-cost/ai",           permission: "procurement.view" },
    ],
  },

  {
    type: "section",
    id: "procurement-suggestion",
    label: "Procurement Suggestion Engine",
    permission: "procurement.view",
    icon: md(
      "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    ),
    items: [
      { label: "PS Dashboard",       href: "/dashboard/procurement-suggestion",                  permission: "procurement.view" },
      { label: "Suggestions",        href: "/dashboard/procurement-suggestion/suggestions",       permission: "procurement.view" },
      { label: "Grouped Orders",     href: "/dashboard/procurement-suggestion/groups",            permission: "procurement.view" },
      { label: "Supplier Prices",    href: "/dashboard/procurement-suggestion/supplier-prices",   permission: "procurement.view" },
      { label: "Supplier Compare",   href: "/dashboard/procurement-suggestion/supplier-compare",  permission: "procurement.view" },
      { label: "Shortage Report",    href: "/dashboard/procurement-suggestion/reports",           permission: "procurement.view" },
      { label: "AI Agents",          href: "/dashboard/procurement-suggestion/ai",                permission: "procurement.view" },
    ],
  },

  {
    type: "section",
    id: "quality",
    label: "Quality",
    permission: "quality.view",
    icon: md(
      "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
    ),
    items: [
      { label: "QC Inspections", href: "/dashboard/quality",            permission: "quality.view" },
      { label: "QC Parameters",  href: "/dashboard/quality/parameters", permission: "quality.view" },
      { label: "QC Reports",     href: "/dashboard/quality/reports",    permission: "quality.view" },
    ],
  },

  {
    type: "section",
    id: "qms",
    label: "QMS & HACCP",
    permission: "quality.view",
    icon: md(
      "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
    ),
    items: [
      { label: "QMS Dashboard",        href: "/dashboard/qms",                        permission: "quality.view" },
      { label: "QC Inspections",        href: "/dashboard/qms/inspections",            permission: "quality.view" },
      { label: "QC Templates",          href: "/dashboard/qms/templates",              permission: "quality.view" },
      { label: "HACCP Analysis",        href: "/dashboard/qms/haccp",                  permission: "quality.view" },
      { label: "CCP Monitoring",        href: "/dashboard/qms/ccp",                    permission: "quality.view" },
      { label: "Deviations",            href: "/dashboard/qms/deviations",             permission: "quality.view" },
      { label: "Corrective Actions",    href: "/dashboard/qms/corrective-actions",     permission: "quality.view" },
      { label: "Quarantine / Hold",     href: "/dashboard/qms/quarantine",             permission: "quality.view" },
      { label: "Allergen Validation",   href: "/dashboard/qms/allergen",               permission: "quality.view" },
      { label: "QMS Reports",           href: "/dashboard/qms/reports",                permission: "quality.view" },
      { label: "AI Quality Agents",     href: "/dashboard/qms/ai",                     permission: "quality.view" },
    ],
  },

  {
    type: "section",
    id: "allergen",
    label: "Allergen & Nutrition",
    permission: "quality.view",
    icon: md(
      "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
    ),
    items: [
      { label: "AN Dashboard",       href: "/dashboard/allergen",                   permission: "quality.view" },
      { label: "Allergen Master",     href: "/dashboard/allergen/allergens",         permission: "quality.view" },
      { label: "Material Profiles",   href: "/dashboard/allergen/material-profiles", permission: "quality.view" },
      { label: "Nutrition Profiles",  href: "/dashboard/allergen/nutrition",         permission: "quality.view" },
      { label: "Product Allergens",   href: "/dashboard/allergen/product-allergens", permission: "quality.view" },
      { label: "Product Nutrition",   href: "/dashboard/allergen/product-nutrition", permission: "quality.view" },
      { label: "Roll-Up Viewer",      href: "/dashboard/allergen/rollup",            permission: "quality.view" },
      { label: "Label Readiness",     href: "/dashboard/allergen/label-readiness",   permission: "quality.view" },
      { label: "Change Logs",         href: "/dashboard/allergen/change-logs",       permission: "quality.view" },
      { label: "Reports",             href: "/dashboard/allergen/reports",           permission: "quality.view" },
      { label: "AI Agents",           href: "/dashboard/allergen/ai",                permission: "quality.view" },
    ],
  },

  {
    type: "section",
    id: "gs1",
    label: "GS1 & Label Printing",
    permission: "quality.view",
    icon: md(
      "M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
    ),
    items: [
      { label: "GS1 Dashboard",      href: "/dashboard/gs1",             permission: "quality.view" },
      { label: "GS1 Configuration",  href: "/dashboard/gs1/config",      permission: "quality.view" },
      { label: "Barcode Generator",  href: "/dashboard/gs1/barcodes",    permission: "quality.view" },
      { label: "Label Templates",    href: "/dashboard/gs1/labels",      permission: "quality.view" },
      { label: "Print Queue",        href: "/dashboard/gs1/print-queue", permission: "quality.view" },
      { label: "SSCC Pallets",       href: "/dashboard/gs1/sscc",        permission: "quality.view" },
      { label: "Scan Debug",         href: "/dashboard/gs1/scan",        permission: "quality.view" },
      { label: "GS1 Reports",        href: "/dashboard/gs1/reports",     permission: "quality.view" },
      { label: "AI Agents",          href: "/dashboard/gs1/ai",          permission: "quality.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║       COMMERCIAL             ║
  // ╚══════════════════════════════╝
  cluster("cluster-commercial", "Commercial"),

  {
    type: "section",
    id: "sales",
    label: "Sales & Distribution",
    permission: "sales.view",
    icon: md("M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"),
    items: [
      { label: "Sales Orders",      href: "/dashboard/sales/orders",       permission: "sales.view" },
      { label: "Field Sales",       href: "/dashboard/sales/field-sales",  permission: "sales.view" },
      { label: "Distributors",      href: "/dashboard/sales/distributors", permission: "sales.view" },
      { label: "Pricing & Promos",  href: "/dashboard/sales/pricing",      permission: "sales.view" },
      { label: "Delivery",          href: "/dashboard/sales/delivery",     permission: "sales.view" },
      { label: "Shipments",         href: "/dashboard/sales/shipments",    permission: "sales.view" },
      { label: "Proof of Delivery", href: "/dashboard/sales/pod",          permission: "sales.view" },
      { label: "Collections",       href: "/dashboard/sales/collections",  permission: "sales.view" },
      { label: "Returns",           href: "/dashboard/sales/returns",      permission: "sales.view" },
      { label: "Invoices",          href: "/dashboard/sales/invoices",     permission: "sales.view" },
      { label: "Sales Reports",     href: "/dashboard/sales/reports",      permission: "sales.view" },
    ],
  },

  {
    type: "section",
    id: "marketing",
    label: "Marketing",
    permission: "marketing.view",
    icon: md(
      "M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z",
      "M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"
    ),
    items: [
      { label: "Dashboard",            href: "/dashboard/marketing",                        permission: "marketing.view" },
      { label: "Campaigns",            href: "/dashboard/marketing/campaigns",              permission: "campaigns.view" },
      { label: "Promotions",           href: "/dashboard/marketing/promotions",             permission: "promotions.view" },
      { label: "Customer Segments",    href: "/dashboard/marketing/segments",               permission: "segments.view" },
      { label: "CRM",                  href: "/dashboard/marketing/crm",                   permission: "crm.view" },
      { label: "Field Visits",         href: "/dashboard/marketing/visits",                 permission: "customer_visits.view" },
      { label: "Trade Spend",          href: "/dashboard/marketing/trade-spend",            permission: "trade_spend.view" },
      { label: "Brand Spend",          href: "/dashboard/marketing/brand-spend",            permission: "brand_spend.view" },
      { label: "Surveys",              href: "/dashboard/marketing/surveys",                permission: "surveys.view" },
      { label: "Influencers",          href: "/dashboard/marketing/influencers",            permission: "influencers.view" },
      { label: "Social Media",         href: "/dashboard/marketing/social-media",           permission: "social_media.view" },
      { label: "E-commerce Stores",    href: "/dashboard/marketing/ecommerce/stores",       permission: "ecommerce.view" },
      { label: "Store Performance",    href: "/dashboard/marketing/ecommerce/performance",  permission: "ecommerce.view" },
      { label: "Product Performance",  href: "/dashboard/marketing/ecommerce/products",     permission: "ecommerce.view" },
      { label: "E-comm Analytics",     href: "/dashboard/marketing/ecommerce/analytics",    permission: "ecommerce.view" },
      { label: "Returns",              href: "/dashboard/marketing/ecommerce/returns",      permission: "ecommerce.view" },
      { label: "Ads Performance",      href: "/dashboard/marketing/ads",                   permission: "ad_performance.view" },
      { label: "AI Optimizer",         href: "/dashboard/marketing/ai-optimizer",           permission: "ai_optimizer.view" },
      { label: "Analytics",            href: "/dashboard/marketing/analytics",              permission: "marketing_analytics.view" },
    ],
  },

  {
    type: "section",
    id: "price-lists",
    label: "Price Lists & Discounts",
    permission: "sales.view",
    icon: md(
      "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
    ),
    items: [
      { label: "Dashboard",         href: "/dashboard/price-lists",                  permission: "sales.view" },
      { label: "Approval Queue",    href: "/dashboard/price-lists/approval-queue",   permission: "sales.view" },
      { label: "Discount Rules",    href: "/dashboard/price-lists/discount-rules",   permission: "sales.view" },
      { label: "Margin Guardrails", href: "/dashboard/price-lists/margin",           permission: "sales.view" },
      { label: "Version Compare",   href: "/dashboard/price-lists/compare",          permission: "sales.view" },
      { label: "Bulk Import",       href: "/dashboard/price-lists/import",           permission: "sales.view" },
      { label: "Reports",           href: "/dashboard/price-lists/reports",          permission: "sales.view" },
      { label: "AI Agents",         href: "/dashboard/price-lists/ai",               permission: "sales.view" },
    ],
  },

  {
    type: "section",
    id: "dunning",
    label: "Dunning & Collections",
    permission: "finance.view",
    icon: md(
      "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Dashboard",          href: "/dashboard/dunning",                permission: "finance.view" },
      { label: "Aging Report",       href: "/dashboard/dunning/aging",          permission: "finance.view" },
      { label: "Dunning Cases",      href: "/dashboard/dunning/cases",          permission: "finance.view" },
      { label: "Collector Queue",    href: "/dashboard/dunning/workqueue",      permission: "finance.view" },
      { label: "Credit Holds",       href: "/dashboard/dunning/credit-holds",   permission: "finance.view" },
      { label: "Policies",           href: "/dashboard/dunning/policies",       permission: "finance.view" },
      { label: "Templates",          href: "/dashboard/dunning/templates",      permission: "finance.view" },
      { label: "Reports",            href: "/dashboard/dunning/reports",        permission: "finance.view" },
      { label: "AI Agents",          href: "/dashboard/dunning/ai",             permission: "finance.view" },
    ],
  },

  {
    type: "section",
    id: "supplier-portal",
    label: "Supplier Portal",
    permission: "procurement.view",
    icon: md(
      "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
    ),
    items: [
      { label: "Portal Admin",       href: "/dashboard/supplier-portal",                  permission: "procurement.view" },
      { label: "Purchase Orders",    href: "/dashboard/supplier-portal/accounts",         permission: "procurement.view" },
      { label: "ETA Management",     href: "/dashboard/supplier-portal/eta",              permission: "procurement.view" },
      { label: "Documents",          href: "/dashboard/supplier-portal/documents",        permission: "procurement.view" },
      { label: "Invoice Submission", href: "/dashboard/supplier-portal/invoices",         permission: "procurement.view" },
      { label: "Payment Status",     href: "/dashboard/supplier-portal/payment",          permission: "procurement.view" },
      { label: "Portal Users",       href: "/dashboard/supplier-portal/users",            permission: "procurement.view" },
      { label: "Activity Log",       href: "/dashboard/supplier-portal/activity",         permission: "procurement.view" },
      { label: "Reports",            href: "/dashboard/supplier-portal/reports",          permission: "procurement.view" },
      { label: "AI Agents",          href: "/dashboard/supplier-portal/ai",               permission: "procurement.view" },
    ],
  },

  {
    type: "section",
    id: "customer-portal",
    label: "Customer / Distributor Portal",
    permission: "sales.view",
    icon: md(
      "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
    ),
    items: [
      { label: "Portal Admin",     href: "/dashboard/portal",              permission: "sales.view" },
      { label: "Portal Accounts",  href: "/dashboard/portal/accounts",     permission: "sales.view" },
      { label: "Draft Order Queue", href: "/dashboard/portal/drafts",      permission: "sales.view" },
      { label: "Claims Review",    href: "/dashboard/portal/claims",       permission: "sales.view" },
      { label: "Portal Users",     href: "/dashboard/portal/users",        permission: "sales.view" },
      { label: "Activity Log",     href: "/dashboard/portal/activity",     permission: "sales.view" },
      { label: "Reports",          href: "/dashboard/portal/reports",      permission: "sales.view" },
      { label: "AI Agents",        href: "/dashboard/portal/ai",           permission: "sales.view" },
    ],
  },

  {
    type: "section",
    id: "crm-pipeline",
    label: "CRM Pipeline",
    permission: "sales.view",
    icon: md(
      "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
    ),
    items: [
      { label: "CRM Dashboard",      href: "/dashboard/crm",              permission: "sales.view" },
      { label: "Leads",              href: "/dashboard/crm/leads",        permission: "sales.view" },
      { label: "Opportunities",      href: "/dashboard/crm/opportunities", permission: "sales.view" },
      { label: "Pipeline Board",     href: "/dashboard/crm/pipeline",     permission: "sales.view" },
      { label: "Activity Timeline",  href: "/dashboard/crm/activities",   permission: "sales.view" },
      { label: "Lead Qualification", href: "/dashboard/crm/qualify",      permission: "sales.view" },
      { label: "Forecast",           href: "/dashboard/crm/forecast",     permission: "sales.view" },
      { label: "Win/Loss Analysis",  href: "/dashboard/crm/win-loss",     permission: "sales.view" },
      { label: "Overdue Queue",      href: "/dashboard/crm/overdue",      permission: "sales.view" },
      { label: "Stage Config",       href: "/dashboard/crm/stages",       permission: "sales.view" },
      { label: "AI Agents",          href: "/dashboard/crm/ai",           permission: "sales.view" },
    ],
  },

  {
    type: "section",
    id: "tpm",
    label: "Trade Promotion Mgmt",
    permission: "promotions.view",
    icon: md(
      "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
    ),
    items: [
      { label: "TPM Dashboard",      href: "/dashboard/tpm",              permission: "promotions.view" },
      { label: "Promotion Calendar", href: "/dashboard/tpm/calendar",     permission: "promotions.view" },
      { label: "Plans",              href: "/dashboard/tpm/plans",        permission: "promotions.view" },
      { label: "Trade Promotions",   href: "/dashboard/tpm/promotions",   permission: "promotions.view" },
      { label: "Budget Monitor",     href: "/dashboard/tpm/budget",       permission: "promotions.view" },
      { label: "Claims Queue",       href: "/dashboard/tpm/claims",       permission: "promotions.view" },
      { label: "Settlement Tracker", href: "/dashboard/tpm/settlement",   permission: "promotions.view" },
      { label: "ROI Analysis",       href: "/dashboard/tpm/roi",          permission: "promotions.view" },
      { label: "AI Agents",          href: "/dashboard/tpm/ai",           permission: "promotions.view" },
    ],
  },

  {
    type: "section",
    id: "promotions",
    label: "Promotional Schemes",
    permission: "promotions.view",
    icon: md(
      "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
    ),
    items: [
      { label: "Dashboard",        href: "/dashboard/promotions",             permission: "promotions.view" },
      { label: "Schemes",          href: "/dashboard/promotions/schemes",     permission: "promotions.view" },
      { label: "New Scheme",       href: "/dashboard/promotions/schemes/new", permission: "promotions.view" },
      { label: "Simulator",        href: "/dashboard/promotions/simulate",    permission: "promotions.view" },
      { label: "Override Queue",   href: "/dashboard/promotions/overrides",   permission: "promotions.view" },
      { label: "Cost Analytics",   href: "/dashboard/promotions/analytics",   permission: "promotions.view" },
      { label: "AI Agents",        href: "/dashboard/promotions/ai",          permission: "promotions.view" },
    ],
  },

  {
    type: "section",
    id: "finance",
    label: "Finance",
    permission: "finance.view",
    icon: md(
      "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Overview",         href: "/dashboard/finance",            permission: "finance.view" },
      { label: "Cashbook",         href: "/dashboard/finance/cashbook",   permission: "finance.view" },
      { label: "Receivables",      href: "/dashboard/finance/receivables",permission: "finance.view" },
      { label: "Product Costing",  href: "/dashboard/finance/costing",    permission: "finance.view" },
      { label: "Budgets",          href: "/dashboard/finance/budget",     permission: "finance.view" },
      { label: "M-Pesa Recon.",    href: "/dashboard/finance/mpesa",      permission: "mpesa.view_transactions" },
    ],
  },

  {
    type: "section",
    id: "accounting",
    label: "Finance & Accounting",
    permission: "finance.view",
    icon: md(
      "M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
    ),
    items: [
      { label: "Dashboard",         href: "/dashboard/finance/accounting",                    permission: "finance.view" },
      { label: "Customers Ledger",  href: "/dashboard/finance/accounting/customers-ledger",   permission: "finance.view" },
      { label: "Suppliers Ledger",  href: "/dashboard/finance/accounting/suppliers-ledger",   permission: "finance.view" },
      { label: "Sales Invoices",    href: "/dashboard/finance/accounting/sales-invoices",     permission: "finance.view" },
      { label: "Purchase Invoices", href: "/dashboard/finance/accounting/purchase-invoices",  permission: "finance.view" },
      { label: "Payments",          href: "/dashboard/finance/accounting/payments",           permission: "finance.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║       FIELD OPERATIONS       ║
  // ╚══════════════════════════════╝
  cluster("cluster-field", "Field Operations"),

  {
    type: "section",
    id: "utility-management",
    label: "Utility Management",
    permission: "utility_management.view",
    icon: md(
      "M13 10V3L4 14h7v7l9-11h-7z"
    ),
    items: [
      { label: "Asset Categories",   href: "/dashboard/utility-management/categories",    permission: "utility_management.view" },
      { label: "Utility Assets",     href: "/dashboard/utility-management/assets",        permission: "utility_management.view" },
      { label: "Meters & Sensors",   href: "/dashboard/utility-management/devices",       permission: "utility_management.view" },
      { label: "Readings",           href: "/dashboard/utility-management/readings",      permission: "utility_management.view" },
      { label: "Transactions",       href: "/dashboard/utility-management/transactions",  permission: "utility_management.view" },
      { label: "Electricity",        href: "/dashboard/utility-management/electricity",   permission: "utility_management.view" },
      { label: "Water",             href: "/dashboard/utility-management/water",          permission: "utility_management.view" },
      { label: "Soft Water",        href: "/dashboard/utility-management/soft-water",     permission: "utility_management.view" },
      { label: "Steam & Boiler",    href: "/dashboard/utility-management/steam",           permission: "utility_management.view" },
      { label: "Compressed Air",   href: "/dashboard/utility-management/compressor",           permission: "utility_management.view" },
      { label: "Solar Energy",     href: "/dashboard/utility-management/solar",                permission: "utility_management.view" },
      { label: "Chemical Treatment", href: "/dashboard/utility-management/chemical-treatment",  permission: "utility_management.view" },
      { label: "Alarm Center",       href: "/dashboard/utility-management/alarm-center",         permission: "utility_management.view" },
      { label: "KPI Center",         href: "/dashboard/utility-management/kpi-center",           permission: "utility_management.view" },
      { label: "Reports & Analytics", href: "/dashboard/utility-management/reports",             permission: "utility_management.view" },
      { label: "Integration Hub",    href: "/dashboard/utility-management/integration",          permission: "utility_management.view" },
    ],
  },

  {
    type: "section",
    id: "maintenance",
    label: "Maintenance",
    permission: "maintenance.view",
    icon: md(
      "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
      "M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    ),
    items: [
      { label: "Overview",    href: "/dashboard/maintenance",             permission: "maintenance.view" },
      { label: "Assets",      href: "/dashboard/maintenance/assets",      permission: "maintenance.view" },
      { label: "PM Plans",    href: "/dashboard/maintenance/plans",       permission: "maintenance.view" },
      { label: "Breakdowns",  href: "/dashboard/maintenance/breakdowns",  permission: "maintenance.view" },
      { label: "Spare Parts", href: "/dashboard/maintenance/spares",      permission: "maintenance.view" },
      { label: "Reports",     href: "/dashboard/maintenance/reports",     permission: "maintenance.view" },
    ],
  },

  {
    type: "section",
    id: "logistics",
    label: "Logistics",
    permission: "logistics.view",
    icon: md(
      "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Overview",           href: "/dashboard/logistics",             permission: "logistics.view" },
      { label: "Shipments",          href: "/dashboard/logistics/shipments",   permission: "logistics.view" },
      { label: "Containers",         href: "/dashboard/logistics/containers",  permission: "logistics.view" },
      { label: "Customs Documents",  href: "/dashboard/logistics/documents",   permission: "logistics.view" },
      { label: "Arrivals & Clearance",href: "/dashboard/logistics/arrivals",   permission: "logistics.view" },
    ],
  },

  {
    type: "section",
    id: "tax",
    label: "Tax & Regulatory",
    permission: "tax.view",
    icon: md(
      "M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"
    ),
    items: [
      { label: "Overview",           href: "/dashboard/tax",              permission: "tax.view" },
      { label: "Tax Rules",          href: "/dashboard/tax/rules",        permission: "tax.view" },
      { label: "Regulatory Flags",   href: "/dashboard/tax/regulatory",   permission: "tax.view" },
      { label: "Transaction Taxes",  href: "/dashboard/tax/transactions", permission: "tax.view" },
      { label: "Tax Reports",        href: "/dashboard/tax/reports",      permission: "tax.view" },
    ],
  },

  {
    type: "section",
    id: "integrations",
    label: "Integrations",
    permission: "integrations.view",
    icon: md(
      "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
    ),
    items: [
      { label: "Overview",        href: "/dashboard/integrations",                  permission: "integrations.view" },
      { label: "M-Pesa",          href: "/dashboard/integrations/mpesa",            permission: "mpesa.view_transactions" },
      { label: "Int. Logs",       href: "/dashboard/integrations/logs",             permission: "integrations.view" },
      { label: "Barcode",         href: "/dashboard/integrations/barcode",          permission: "integrations.view" },
      { label: "Sync Status",     href: "/dashboard/integrations/sync",             permission: "integrations.view" },
      { label: "Marketing Sync",  href: "/dashboard/integrations/marketing-sync",   permission: "integrations.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║       AI & INTELLIGENCE      ║
  // ╚══════════════════════════════╝
  cluster("cluster-ai", "AI & Intelligence"),

  {
    type: "section",
    id: "ai",
    label: "AI & Intelligence",
    permission: "ai.view",
    icon: md(
      "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    ),
    items: [
      { label: "AI Dashboard",         href: "/dashboard/ai",                    permission: "ai.view" },
      { label: "Predictions",          href: "/dashboard/ai/predictions",        permission: "ai.view" },
      { label: "Recommendations",      href: "/dashboard/ai/recommendations",    permission: "ai.view" },
      { label: "Scenario Simulator",   href: "/dashboard/ai/scenarios",          permission: "ai.view" },
      { label: "Formulation Engine",   href: "/dashboard/ai/formulations",       permission: "ai.view" },
      { label: "Compliance & Docs",    href: "/dashboard/ai/compliance",         permission: "ai.view" },
      { label: "AI Logs",              href: "/dashboard/ai/logs",               permission: "ai.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║       ANALYTICS              ║
  // ╚══════════════════════════════╝
  cluster("cluster-analytics", "Analytics"),

  {
    type: "section",
    id: "analytics",
    label: "Analytics / BI",
    permission: "analytics.view",
    icon: md(
      "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
    ),
    items: [
      { label: "BI Hub",           href: "/dashboard/analytics",               permission: "analytics.view" },
      { label: "Inventory BI",     href: "/dashboard/analytics/inventory",     permission: "inventory.view" },
      { label: "Production BI",    href: "/dashboard/analytics/production",    permission: "production.view" },
      { label: "Procurement BI",   href: "/dashboard/analytics/procurement",   permission: "procurement.view" },
      { label: "Sales BI",         href: "/dashboard/analytics/sales",         permission: "sales.view" },
      { label: "Finance BI",       href: "/dashboard/analytics/finance",       permission: "finance.view" },
      { label: "Payments / M-Pesa",href: "/dashboard/analytics/payments",      permission: "mpesa.view_transactions" },
      { label: "Marketing BI",     href: "/dashboard/reports/marketing",       permission: "marketing_analytics.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║   PLANNING & INTELLIGENCE        ║
  // ╚══════════════════════════════════╝
  cluster("cluster-planning", "Planning & Intelligence"),

  {
    type: "section",
    id: "mrp",
    label: "MRP & Forecasting",
    permission: "production.view",
    icon: md(
      "M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
    ),
    items: [
      { label: "MRP Dashboard",      href: "/dashboard/mrp",              permission: "production.view" },
      { label: "MRP Runs",           href: "/dashboard/mrp/run",          permission: "production.view" },
      { label: "Suggestions",        href: "/dashboard/mrp/suggestions",  permission: "production.view" },
      { label: "Demand Forecasting", href: "/dashboard/mrp/forecast",     permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "mps",
    label: "Master Production Scheduling",
    permission: "production.view",
    icon: md(
      "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
    ),
    items: [
      { label: "MPS Dashboard",   href: "/dashboard/mps",                 permission: "production.view" },
      { label: "Planning Board",  href: "/dashboard/mps/planning-board",  permission: "production.view" },
      { label: "Capacity Heatmap",href: "/dashboard/mps/capacity",        permission: "production.view" },
      { label: "Campaign View",   href: "/dashboard/mps/campaigns",       permission: "production.view" },
      { label: "What-If Simulator", href: "/dashboard/mps/whatif",        permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "planning",
    label: "Advanced Planning Suite",
    permission: "production.view",
    icon: md(
      "M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"
    ),
    items: [
      { label: "Planning Dashboard",   href: "/dashboard/planning",                permission: "production.view" },
      { label: "Schedule Board",       href: "/dashboard/planning/schedule",       permission: "production.view" },
      { label: "Capacity Board",       href: "/dashboard/planning/capacity",       permission: "production.view" },
      { label: "Bottleneck Explorer",  href: "/dashboard/planning/bottlenecks",    permission: "production.view" },
      { label: "Simulation Sandbox",   href: "/dashboard/planning/simulation",     permission: "production.view" },
      { label: "Changeover Matrix",    href: "/dashboard/planning/changeover",     permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "production-execution",
    label: "Production Execution",
    permission: "production.view",
    icon: md(
      "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
    ),
    items: [
      { label: "Order Dashboard",     href: "/dashboard/production-execution",                permission: "production.view" },
      { label: "Work Order Queue",     href: "/dashboard/production-execution/work-orders",    permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "bom",
    label: "BOM & Formula",
    permission: "production.view",
    icon: md(
      "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
    ),
    items: [
      { label: "BOM Master",             href: "/dashboard/bom",                    permission: "production.view" },
      { label: "Conversion Profiles",    href: "/dashboard/bom/conversion",         permission: "production.view" },
      { label: "Substitute Manager",     href: "/dashboard/bom/substitutes",        permission: "production.view" },
      { label: "Version Compare",        href: "/dashboard/bom/compare",            permission: "production.view" },
    ],
  },

  {
    type: "section",
    id: "shop-floor",
    label: "Shop Floor",
    permission: "production.view",
    icon: md(
      "M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"
    ),
    items: [
      { label: "SF Dashboard",      href: "/dashboard/shop-floor",             permission: "production.view" },
      { label: "Operator Terminal", href: "/dashboard/shop-floor/terminal",   permission: "production.view" },
      { label: "Supervisor Console",href: "/dashboard/shop-floor/supervisor", permission: "production.view" },
      { label: "Queue Board",       href: "/dashboard/shop-floor/queue",      permission: "production.view" },
      { label: "Downtime Board",    href: "/dashboard/shop-floor/downtime",   permission: "production.view" },
      { label: "Shift Handover",    href: "/dashboard/shop-floor/handover",   permission: "production.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║  MACHINE + OPERATOR INTELLIGENCE ║
  // ╚══════════════════════════════════╝
  cluster("cluster-machine-ops", "Machine & Operator"),

  {
    type: "section",
    id: "machine-ops",
    label: "Machine + Operator Intelligence",
    permission: "production.view",
    icon: md(
      "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
    ),
    items: [
      { label: "MO Dashboard",       href: "/dashboard/machine-ops",                permission: "production.view" },
      { label: "Machine Master",     href: "/dashboard/machine-ops/machines",        permission: "production.view" },
      { label: "Operators",          href: "/dashboard/machine-ops/operators",       permission: "production.view" },
      { label: "Teams",              href: "/dashboard/machine-ops/teams",           permission: "production.view" },
      { label: "Runtime Logs",       href: "/dashboard/machine-ops/runtime",         permission: "production.view" },
      { label: "OEE / Performance",  href: "/dashboard/machine-ops/performance",     permission: "production.view" },
      { label: "Downtime Board",     href: "/dashboard/machine-ops/downtime",        permission: "production.view" },
      { label: "Cost Contribution",  href: "/dashboard/machine-ops/costing",         permission: "production.view" },
      { label: "Cert Monitor",       href: "/dashboard/machine-ops/certs",           permission: "production.view" },
      { label: "Assignment Board",   href: "/dashboard/machine-ops/assignment",      permission: "production.view" },
    ],
  },

  // ╔══════════════════════════════════════════╗
  // ║  LOT TRACEABILITY + RECALL MANAGEMENT   ║
  // ╚══════════════════════════════════════════╝
  cluster("cluster-traceability", "Traceability & Recall"),

  {
    type: "section",
    id: "traceability",
    label: "Lot Traceability + Recall",
    permission: "production.view",
    icon: md(
      "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
    ),
    items: [
      { label: "Trace Dashboard",      href: "/dashboard/traceability",                    permission: "production.view" },
      { label: "Trace Search",         href: "/dashboard/traceability/search",             permission: "production.view" },
      { label: "Backward Trace",       href: "/dashboard/traceability/backward",           permission: "production.view" },
      { label: "Forward Trace",        href: "/dashboard/traceability/forward",            permission: "production.view" },
      { label: "Genealogy Graph",      href: "/dashboard/traceability/genealogy",          permission: "production.view" },
      { label: "Recall List",          href: "/dashboard/traceability/recalls",            permission: "production.view" },
      { label: "Mock Recall Drill",    href: "/dashboard/traceability/mock-recall",        permission: "production.view" },
      { label: "Regulatory Reports",   href: "/dashboard/traceability/regulatory",         permission: "production.view" },
    ],
  },

  // ╔══════════════════════════════════════╗
  // ║   FEFO + SHELF-LIFE CONTROL          ║
  // ╚══════════════════════════════════════╝
  cluster("cluster-shelf-life", "FEFO & Shelf-Life"),

  {
    type: "section",
    id: "shelf-life",
    label: "FEFO + Shelf-Life Control",
    permission: "production.view",
    icon: md(
      "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
    ),
    items: [
      { label: "SL Dashboard",          href: "/dashboard/shelf-life",                       permission: "production.view" },
      { label: "FEFO Config",            href: "/dashboard/shelf-life/fefo-config",           permission: "production.view" },
      { label: "Lot Aging Explorer",     href: "/dashboard/shelf-life/lot-aging",             permission: "production.view" },
      { label: "Near-Expiry Board",      href: "/dashboard/shelf-life/near-expiry",           permission: "production.view" },
      { label: "Expired Stock Board",    href: "/dashboard/shelf-life/expired",               permission: "production.view" },
      { label: "Retest Queue",           href: "/dashboard/shelf-life/retest-queue",          permission: "production.view" },
      { label: "Shipment Validation",    href: "/dashboard/shelf-life/shipment-validation",   permission: "production.view" },
      { label: "Production Validation",  href: "/dashboard/shelf-life/production-validation", permission: "production.view" },
      { label: "FEFO Compliance Audit",  href: "/dashboard/shelf-life/compliance",            permission: "production.view" },
      { label: "Disposition Console",    href: "/dashboard/shelf-life/disposition",           permission: "production.view" },
      { label: "Customer SL Rules",      href: "/dashboard/shelf-life/customer-rules",        permission: "production.view" },
      { label: "Bulk Hold Monitor",      href: "/dashboard/shelf-life/bulk-hold-monitor",     permission: "production.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║     MATERIAL FLOW ENGINE     ║
  // ╚══════════════════════════════╝
  cluster("cluster-material-flow", "Material Flow"),

  {
    type: "section",
    id: "material-flow",
    label: "Material Flow Engine",
    permission: "production.view",
    icon: md(
      "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
    ),
    items: [
      { label: "MF Dashboard",        href: "/dashboard/material-flow",                  permission: "production.view" },
      { label: "Issue to Production", href: "/dashboard/material-flow/issue",             permission: "production.view" },
      { label: "Reservations",        href: "/dashboard/material-flow/reservations",      permission: "production.view" },
      { label: "WIP / Stage Transfer",href: "/dashboard/material-flow/wip-transfer",     permission: "production.view" },
      { label: "Bulk Transfer",       href: "/dashboard/material-flow/bulk-transfer",     permission: "production.view" },
      { label: "Packaging Issue",     href: "/dashboard/material-flow/packaging",         permission: "production.view" },
      { label: "FG Receipt",          href: "/dashboard/material-flow/fg-receipt",        permission: "production.view" },
      { label: "Returns & Reversals", href: "/dashboard/material-flow/returns",           permission: "production.view" },
      { label: "Tank Occupancy",      href: "/dashboard/material-flow/tanks",             permission: "production.view" },
      { label: "Flow History",        href: "/dashboard/material-flow/history",           permission: "production.view" },
      { label: "Reconciliation",      href: "/dashboard/material-flow/reconciliation",    permission: "production.view" },
      { label: "Stage Config",        href: "/dashboard/material-flow/stages",            permission: "production.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║    SALES COMMISSION TRACKING     ║
  // ╚══════════════════════════════════╝
  cluster("cluster-commissions", "Commissions"),

  {
    type: "section",
    id: "commissions",
    label: "Sales Commissions",
    permission: "sales.view",
    icon: md(
      "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Dashboard",     href: "/dashboard/commissions",               permission: "sales.view" },
      { label: "Rules",         href: "/dashboard/commissions/rules",          permission: "sales.view" },
      { label: "Transactions",  href: "/dashboard/commissions/transactions",   permission: "sales.view" },
      { label: "Targets",       href: "/dashboard/commissions/targets",        permission: "sales.view" },
      { label: "Payouts",       href: "/dashboard/commissions/payouts",        permission: "sales.view" },
      { label: "Reports",       href: "/dashboard/commissions/reports",        permission: "sales.view" },
      { label: "AI Insights",   href: "/dashboard/commissions/ai",             permission: "sales.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║     EMPLOYEE SELF-SERVICE        ║
  // ╚══════════════════════════════════╝
  cluster("cluster-ess", "Employee Self-Service"),

  {
    type: "section",
    id: "ess",
    label: "Employee Self-Service",
    permission: "hr.view",
    icon: md(
      "M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "ESS Dashboard",    href: "/dashboard/ess",               permission: "hr.view" },
      { label: "My Profile",       href: "/dashboard/ess/profile",        permission: "hr.view" },
      { label: "Leave",            href: "/dashboard/ess/leave",          permission: "hr.view" },
      { label: "Attendance",       href: "/dashboard/ess/attendance",     permission: "hr.view" },
      { label: "Documents",        href: "/dashboard/ess/documents",      permission: "hr.view" },
      { label: "My Requests",      href: "/dashboard/ess/requests",       permission: "hr.view" },
      { label: "Notifications",    href: "/dashboard/ess/notifications",  permission: "hr.view" },
      { label: "HR Admin",         href: "/dashboard/ess/admin",          permission: "hr.view" },
      { label: "AI Insights",      href: "/dashboard/ess/ai",             permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║       RECRUITMENT / ATS          ║
  // ╚══════════════════════════════════╝
  cluster("cluster-recruitment", "Recruitment"),

  {
    type: "section",
    id: "recruitment",
    label: "Recruitment / ATS",
    permission: "hr.view",
    icon: md(
      "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
    ),
    items: [
      { label: "Dashboard",       href: "/dashboard/recruitment",                      permission: "hr.view" },
      { label: "Requisitions",    href: "/dashboard/recruitment/requisitions",          permission: "hr.view" },
      { label: "Candidates",      href: "/dashboard/recruitment/candidates",            permission: "hr.view" },
      { label: "Pipeline Board",  href: "/dashboard/recruitment/pipeline",              permission: "hr.view" },
      { label: "Interviews",      href: "/dashboard/recruitment/interviews",            permission: "hr.view" },
      { label: "Offers",          href: "/dashboard/recruitment/offers",                permission: "hr.view" },
      { label: "Pipeline Stages", href: "/dashboard/recruitment/stages",               permission: "hr.view" },
      { label: "Reports",         href: "/dashboard/recruitment/reports",              permission: "hr.view" },
      { label: "AI Insights",     href: "/dashboard/recruitment/ai",                   permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║   TIMESHEET APPROVAL WORKFLOW    ║
  // ╚══════════════════════════════════╝
  cluster("cluster-timesheets", "Timesheets"),

  {
    type: "section",
    id: "timesheets",
    label: "Timesheet Management",
    permission: "hr.view",
    icon: md(
      "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Dashboard",       href: "/dashboard/timesheets",                    permission: "hr.view" },
      { label: "My Timesheets",   href: "/dashboard/timesheets/my-timesheets",      permission: "hr.view" },
      { label: "New Time Entry",  href: "/dashboard/timesheets/time-entry",         permission: "hr.view" },
      { label: "Weekly View",     href: "/dashboard/timesheets/weekly-view",        permission: "hr.view" },
      { label: "Approval Queue",  href: "/dashboard/timesheets/approval-queue",     permission: "hr.view" },
      { label: "Reports",         href: "/dashboard/timesheets/reports",            permission: "hr.view" },
      { label: "AI Insights",     href: "/dashboard/timesheets/ai",                 permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║   TRAINING & SKILLS MANAGEMENT   ║
  // ╚══════════════════════════════════╝
  cluster("cluster-training", "Training & Skills"),

  {
    type: "section",
    id: "training",
    label: "Training & Skills",
    permission: "hr.view",
    icon: md(
      "M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5l4-2.222"
    ),
    items: [
      { label: "Dashboard",           href: "/dashboard/training",                      permission: "hr.view" },
      { label: "Training Programs",   href: "/dashboard/training/programs",             permission: "hr.view" },
      { label: "Sessions / Calendar", href: "/dashboard/training/sessions",             permission: "hr.view" },
      { label: "Skill Matrix",        href: "/dashboard/training/skill-matrix",         permission: "hr.view" },
      { label: "Assignments",         href: "/dashboard/training/assignments",          permission: "hr.view" },
      { label: "Certifications",      href: "/dashboard/training/certifications",       permission: "hr.view" },
      { label: "Feedback",            href: "/dashboard/training/feedback",             permission: "hr.view" },
      { label: "Reports",             href: "/dashboard/training/reports",              permission: "hr.view" },
      { label: "AI Insights",         href: "/dashboard/training/ai",                   permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║     PERFORMANCE APPRAISALS       ║
  // ╚══════════════════════════════════╝
  cluster("cluster-appraisals", "Performance Appraisals"),

  {
    type: "section",
    id: "appraisals",
    label: "Performance Appraisals",
    permission: "hr.view",
    icon: md(
      "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
    ),
    items: [
      { label: "Dashboard",          href: "/dashboard/appraisals",                       permission: "hr.view" },
      { label: "Periods",            href: "/dashboard/appraisals/periods",               permission: "hr.view" },
      { label: "Templates",          href: "/dashboard/appraisals/templates",             permission: "hr.view" },
      { label: "All Records",        href: "/dashboard/appraisals/records",               permission: "hr.view" },
      { label: "New Appraisal",      href: "/dashboard/appraisals/records/new",          permission: "hr.view" },
      { label: "Self Review",        href: "/dashboard/appraisals/self-review",          permission: "hr.view" },
      { label: "Manager Queue",      href: "/dashboard/appraisals/manager-queue",        permission: "hr.view" },
      { label: "HR Review",          href: "/dashboard/appraisals/hr-review",            permission: "hr.view" },
      { label: "Development Plans",  href: "/dashboard/appraisals/development-plans",    permission: "hr.view" },
      { label: "Reports",            href: "/dashboard/appraisals/reports",              permission: "hr.view" },
      { label: "AI Insights",        href: "/dashboard/appraisals/ai",                   permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║         EXPENSE CLAIMS           ║
  // ╚══════════════════════════════════╝
  cluster("cluster-expenses", "Expense Claims"),

  {
    type: "section",
    id: "expenses",
    label: "Expense Claims",
    permission: "hr.view",
    icon: md(
      "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"
    ),
    items: [
      { label: "Dashboard",       href: "/dashboard/expenses",                  permission: "hr.view" },
      { label: "My Claims",       href: "/dashboard/expenses/claims",           permission: "hr.view" },
      { label: "New Claim",       href: "/dashboard/expenses/claims/new",       permission: "hr.view" },
      { label: "Approval Queue",  href: "/dashboard/expenses/approval",         permission: "hr.view" },
      { label: "Reimbursement",   href: "/dashboard/expenses/reimbursement",    permission: "hr.view" },
      { label: "Advances",        href: "/dashboard/expenses/advances",         permission: "hr.view" },
      { label: "Categories",      href: "/dashboard/expenses/categories",       permission: "hr.view" },
      { label: "Policies",        href: "/dashboard/expenses/policies",         permission: "hr.view" },
      { label: "Reports",         href: "/dashboard/expenses/reports",          permission: "hr.view" },
      { label: "AI Insights",     href: "/dashboard/expenses/ai",               permission: "hr.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║       CONTRACT MANAGEMENT        ║
  // ╚══════════════════════════════════╝
  cluster("cluster-contracts", "Contracts"),

  {
    type: "section",
    id: "contracts",
    label: "Contract Management",
    permission: "sales.view",
    icon: md(
      "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
    ),
    items: [
      { label: "Dashboard",      href: "/dashboard/contracts",            permission: "sales.view" },
      { label: "All Contracts",  href: "/dashboard/contracts/list",       permission: "sales.view" },
      { label: "New Contract",   href: "/dashboard/contracts/new",        permission: "sales.view" },
      { label: "Expiring Soon",  href: "/dashboard/contracts/expiring",   permission: "sales.view" },
      { label: "Reports",        href: "/dashboard/contracts/reports",    permission: "sales.view" },
      { label: "AI Insights",    href: "/dashboard/contracts/ai",         permission: "sales.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║     VAN SALES / MOBILE POS       ║
  // ╚══════════════════════════════════╝
  cluster("cluster-van-sales", "Van Sales"),

  {
    type: "section",
    id: "van-sales",
    label: "Van Sales / Mobile POS",
    permission: "sales.view",
    icon: md(
      "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
    ),
    items: [
      { label: "Dashboard",        href: "/dashboard/van-sales",                   permission: "sales.view" },
      { label: "Vans",             href: "/dashboard/van-sales/vans",              permission: "sales.view" },
      { label: "Route Execution",  href: "/dashboard/van-sales/route",             permission: "sales.view" },
      { label: "Mobile POS",       href: "/dashboard/van-sales/pos",               permission: "sales.view" },
      { label: "Van Stock",        href: "/dashboard/van-sales/stock",             permission: "sales.view" },
      { label: "Reconciliation",   href: "/dashboard/van-sales/reconciliation",    permission: "sales.view" },
      { label: "Reports",          href: "/dashboard/van-sales/reports",           permission: "sales.view" },
      { label: "AI Intelligence",  href: "/dashboard/van-sales/ai",                permission: "sales.view" },
      { label: "Fraud Alerts",     href: "/dashboard/van-sales/fraud",             permission: "sales.view" },
      { label: "Rider Performance",href: "/dashboard/van-sales/performance",       permission: "sales.view" },
      { label: "M-Pesa Payments",  href: "/dashboard/van-sales/mpesa",             permission: "sales.view" },
    ],
  },

  // ╔══════════════════════════════════╗
  // ║   SUBSCRIPTION / RECURRING       ║
  // ╚══════════════════════════════════╝
  cluster("cluster-recurring", "Recurring Orders"),

  {
    type: "section",
    id: "recurring-orders",
    label: "Recurring Orders",
    permission: "sales.view",
    icon: md(
      "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
    ),
    items: [
      { label: "Dashboard",          href: "/dashboard/recurring-orders",                   permission: "sales.view" },
      { label: "Templates",          href: "/dashboard/recurring-orders/templates",          permission: "sales.view" },
      { label: "Generation Calendar",href: "/dashboard/recurring-orders/schedule",          permission: "sales.view" },
      { label: "Upcoming Demand",    href: "/dashboard/recurring-orders/upcoming-demand",   permission: "sales.view" },
      { label: "Reports",            href: "/dashboard/recurring-orders/reports",           permission: "sales.view" },
      { label: "AI Insights",        href: "/dashboard/recurring-orders/ai",                permission: "sales.view" },
    ],
  },

  // ╔══════════════════════════════╗
  // ║       PEOPLE & ADMIN         ║
  // ╚══════════════════════════════╝
  cluster("cluster-admin", "People & Admin"),

  {
    type: "section",
    id: "hr",
    label: "Human Resources",
    permission: "hr.view",
    icon: md(
      "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
    ),
    items: [
      { label: "Overview",         href: "/dashboard/hr",            permission: "hr.view" },
      { label: "Employees",        href: "/dashboard/hr/employees",  permission: "hr.view" },
      { label: "Shifts",           href: "/dashboard/hr/shifts",     permission: "hr.view" },
      { label: "Attendance",       href: "/dashboard/hr/attendance", permission: "hr.view" },
      { label: "Leave Management", href: "/dashboard/hr/leave",      permission: "hr.view" },
      { label: "Payroll",          href: "/dashboard/hr/payroll",    permission: "hr.view" },
    ],
  },

  {
    type: "section",
    id: "admin",
    label: "Admin & Support",
    icon: md(
      "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
      "M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    ),
    items: [
      { label: "Users",           href: "/dashboard/users",         permission: "users.view" },
      { label: "Roles",           href: "/dashboard/roles",         permission: "roles.view" },
      { label: "Permissions",     href: "/dashboard/permissions",   permission: "roles.view" },
      { label: "Documents",       href: "/dashboard/documents",     permission: "documents.view" },
      { label: "Import History",  href: "/dashboard/import-history",permission: "audit.view" },
      { label: "System Logs",     href: "/dashboard/logs",          permission: "audit.view" },
    ],
  },

  {
    type: "section",
    id: "utilities",
    label: "Utilities",
    permission: "utilities.view",
    icon: md(
      "M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
    ),
    items: [
      { label: "System Configs",   href: "/dashboard/utilities",               permission: "utilities.view" },
      { label: "UOM Conversions",  href: "/dashboard/utilities?tab=uom",       permission: "utilities.view" },
      { label: "Number Series",    href: "/dashboard/utilities?tab=series",    permission: "utilities.view" },
      { label: "Currencies",       href: "/dashboard/utilities?tab=currencies",permission: "utilities.view" },
    ],
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

export function isItemActive(href: string, pathname: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(href + "/");
}

export function getSectionIdForPath(pathname: string): string | null {
  for (const entry of NAV_CONFIG) {
    if (entry.type === "section") {
      if (entry.items.some((item) => isItemActive(item.href, pathname))) {
        return entry.id;
      }
    } else if (entry.type === "link") {
      if (isItemActive(entry.href, pathname)) return entry.id;
    }
  }
  return null;
}
