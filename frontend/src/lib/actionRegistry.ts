/**
 * Command Palette — Action Registry
 * Defines quick actions (create, run, navigate) available in Ctrl+K.
 */

export type ActionCategory =
  | "navigation"
  | "action"
  | "report"
  | "ai"
  | "record";

export interface PaletteAction {
  id: string;
  label: string;
  description?: string;
  category: ActionCategory;
  icon: string;          // emoji or icon key
  href?: string;         // navigate to route
  keywords?: string[];   // extra search terms
  permission?: string;   // permission code required
}

export const ACTION_REGISTRY: PaletteAction[] = [

  // ── Create actions ────────────────────────────────────────────────────────

  { id: "create_sales_order",       label: "New Sales Order",          description: "Create a new sales order",          category: "action", icon: "🛒", href: "/dashboard/sales/orders",              keywords: ["so", "order", "sell"], permission: "sales.view" },
  { id: "create_purchase_order",    label: "New Purchase Order",       description: "Create a new purchase order",       category: "action", icon: "📦", href: "/dashboard/procurement/orders",         keywords: ["po", "buy", "purchase"], permission: "procurement.view" },
  { id: "create_invoice",           label: "New Sales Invoice",        description: "Create a new invoice",              category: "action", icon: "📄", href: "/dashboard/sales/invoices",             keywords: ["invoice", "bill"], permission: "sales.view" },
  { id: "create_customer",          label: "New Customer",             description: "Add a new customer",                category: "action", icon: "👤", href: "/dashboard/sales/customers",            keywords: ["customer", "client"], permission: "sales.view" },
  { id: "create_product",           label: "New Product",              description: "Add a new product",                 category: "action", icon: "📦", href: "/dashboard/products",                   keywords: ["sku", "item"], permission: "products.view" },
  { id: "create_production_order",  label: "New Production Order",     description: "Create a production order",         category: "action", icon: "🏭", href: "/dashboard/production/orders",          keywords: ["batch", "manufacture"], permission: "production.view" },
  { id: "create_contract",          label: "New Contract",             description: "Create a new contract",             category: "action", icon: "📝", href: "/dashboard/contracts/new",              keywords: ["agreement"], permission: "sales.view" },
  { id: "create_expense_claim",     label: "New Expense Claim",        description: "Submit a new expense",              category: "action", icon: "💸", href: "/dashboard/expenses/claims/new",        keywords: ["expense", "claim", "reimburse"], permission: "hr.view" },
  { id: "create_job_requisition",   label: "New Job Requisition",      description: "Open a new hiring request",         category: "action", icon: "👥", href: "/dashboard/recruitment/requisitions",   keywords: ["hire", "recruit", "job"], permission: "hr.view" },
  { id: "create_kanban_card",       label: "New Kanban Card",          description: "Create a new task card",            category: "action", icon: "🗂️", href: "/dashboard/kanban/cards",               keywords: ["task", "card"], permission: "hr.view" },
  { id: "create_van_trip",          label: "Start Van Route",          description: "Begin van sales route",             category: "action", icon: "🚐", href: "/dashboard/van-sales/route",            keywords: ["van", "route", "mobile"], permission: "sales.view" },
  { id: "import_statement",         label: "Import Bank Statement",    description: "Import a bank statement CSV",       category: "action", icon: "🏦", href: "/dashboard/bank-reconciliation/import", keywords: ["bank", "recon", "statement"], permission: "finance.view" },

  // ── Run actions ───────────────────────────────────────────────────────────

  { id: "run_mrp",            label: "Run MRP",                  description: "Execute Material Requirements Planning", category: "action", icon: "⚙️",  href: "/dashboard/mrp/run",                  keywords: ["mrp", "planning", "materials"], permission: "production.view" },
  { id: "run_procurement_ai", label: "Run Procurement AI",       description: "Generate procurement suggestions",      category: "action", icon: "🤖",  href: "/dashboard/procurement-suggestion/ai",keywords: ["ai", "suggest", "buy"], permission: "procurement.view" },
  { id: "run_bank_recon",     label: "Run Bank Reconciliation",  description: "Auto-match bank transactions",          category: "action", icon: "🔄",  href: "/dashboard/bank-reconciliation",      keywords: ["bank", "match", "reconcile"], permission: "finance.view" },
  { id: "run_invoice_match",  label: "Run Invoice Matching",     description: "3-way PO/GRN/Invoice match",           category: "action", icon: "✅",  href: "/dashboard/invoice-match",            keywords: ["match", "invoice", "3way"], permission: "finance.view" },
  { id: "run_ai_predictions", label: "Generate AI Predictions",  description: "AI sales & risk forecast",             category: "action", icon: "📈",  href: "/dashboard/ai/predictions",           keywords: ["ai", "forecast", "predict"], permission: "ai.view" },
  { id: "run_ai_chat",        label: "ERP Copilot",              description: "Chat with the AI assistant",           category: "action", icon: "💬",  href: "/dashboard/ai/chat",                  keywords: ["chat", "ai", "copilot", "ask"], permission: "ai.view" },
  { id: "run_payroll",        label: "Run Kenya Payroll",        description: "Calculate payroll for this period",    category: "action", icon: "💰",  href: "/dashboard/payroll",                  keywords: ["payroll", "salary", "kenya"], permission: "hr.view" },
  { id: "run_production_ai",  label: "Run Production AI Agents", description: "Analyze production performance",       category: "action", icon: "🏭",  href: "/dashboard/production/ai",            keywords: ["production", "oee", "ai"], permission: "production.view" },

  // ── Report shortcuts ──────────────────────────────────────────────────────

  { id: "report_sales_bi",       label: "Sales Analytics",       description: "Open Sales BI dashboard",        category: "report", icon: "📊", href: "/dashboard/analytics/sales",         keywords: ["sales", "bi", "analytics"], permission: "sales.view" },
  { id: "report_finance_bi",     label: "Finance Analytics",     description: "Open Finance BI dashboard",      category: "report", icon: "📊", href: "/dashboard/analytics/finance",       keywords: ["finance", "bi", "analytics"], permission: "finance.view" },
  { id: "report_inventory_bi",   label: "Inventory Analytics",   description: "Open Inventory BI dashboard",    category: "report", icon: "📊", href: "/dashboard/analytics/inventory",     keywords: ["inventory", "stock", "bi"], permission: "inventory.view" },
  { id: "report_production_bi",  label: "Production Analytics",  description: "Open Production BI dashboard",   category: "report", icon: "📊", href: "/dashboard/analytics/production",    keywords: ["production", "oee", "bi"], permission: "production.view" },
  { id: "report_ai_logs",        label: "AI Audit Logs",         description: "View all AI request logs",       category: "report", icon: "📋", href: "/dashboard/ai/logs",                 keywords: ["ai", "logs", "audit"], permission: "ai.view" },
  { id: "report_dunning",        label: "Aging Report",          description: "Open accounts receivable aging",  category: "report", icon: "📊", href: "/dashboard/dunning/aging",           keywords: ["aging", "ar", "overdue"], permission: "finance.view" },
  { id: "report_custom_builder", label: "Build Custom Report",   description: "Open Report Builder",             category: "report", icon: "🛠️", href: "/dashboard/report-builder/builder",  keywords: ["report", "custom", "build"], permission: "analytics.view" },
  { id: "report_esg",            label: "ESG Reports",           description: "Sustainability & emissions",       category: "report", icon: "🌱", href: "/dashboard/esg/reports",             keywords: ["esg", "sustainability", "carbon"], permission: "hr.view" },

  // ── AI Commands (suggestions only — never auto-execute) ───────────────────

  { id: "ai_analyze_sales",      label: "Analyze Sales Trends",       description: "AI insight on recent sales",          category: "ai", icon: "🧠", href: "/dashboard/ai/chat?q=analyze+sales+trends",          keywords: ["analyze", "sales", "trend"] },
  { id: "ai_stock_risk",         label: "Stock Risk This Week",        description: "AI stock depletion risk",             category: "ai", icon: "🧠", href: "/dashboard/ai/predictions",                          keywords: ["stock", "risk", "deplete"] },
  { id: "ai_show_risks",         label: "Show Business Risks",         description: "AI risk recommendations",             category: "ai", icon: "🧠", href: "/dashboard/ai/recommendations",                      keywords: ["risk", "business", "alert"] },
  { id: "ai_unpaid_invoices",    label: "Find Unpaid Invoices",        description: "AI collections insight",             category: "ai", icon: "🧠", href: "/dashboard/ai/chat?q=show+unpaid+invoices",          keywords: ["unpaid", "invoice", "ar"] },
  { id: "ai_rider_performance",  label: "Rider Performance Analysis",  description: "AI field sales analysis",            category: "ai", icon: "🧠", href: "/dashboard/van-sales/performance",                    keywords: ["rider", "van", "performance"] },
  { id: "ai_formulate",          label: "Generate Product Formula",    description: "AI formulation engine",              category: "ai", icon: "🧪", href: "/dashboard/ai/formulations",                         keywords: ["formula", "formulation", "chemistry"] },
  { id: "ai_scenario",           label: "Run Business Scenario",       description: "What-if scenario simulation",        category: "ai", icon: "🎯", href: "/dashboard/ai/scenarios",                            keywords: ["scenario", "simulate", "whatif"] },
];

export function filterActions(
  actions: PaletteAction[],
  query: string,
  hasPermission: (code: string) => boolean,
): PaletteAction[] {
  const q = query.toLowerCase();
  return actions.filter((a) => {
    if (a.permission && !hasPermission(a.permission)) return false;
    if (!q) return true;
    return (
      a.label.toLowerCase().includes(q) ||
      (a.description ?? "").toLowerCase().includes(q) ||
      (a.keywords ?? []).some((k) => k.includes(q))
    );
  });
}
