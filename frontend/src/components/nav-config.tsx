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
      { label: "Production Plans",  href: "/dashboard/production",         permission: "production.view" },
      { label: "Production Orders", href: "/dashboard/production/orders",  permission: "production.view" },
      { label: "MES Reports",       href: "/dashboard/production/reports", permission: "production.view" },
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
