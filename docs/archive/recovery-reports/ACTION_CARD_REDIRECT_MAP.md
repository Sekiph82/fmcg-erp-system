# Action Card Redirect Map

**Date:** 2026-05-20
**Status after Round 15 fixes:** 0 user-visible broken cards

---

## User-Visible Action Cards → Route Health

### Command Palette (actionRegistry.ts) — Ctrl+K

| Action | href | Route Reachable | Redirect? | Status |
|--------|------|----------------|-----------|--------|
| New Sales Order | `/dashboard/sales/orders` | YES (real page, 255 lines) | No | ✅ working |
| New Purchase Order | `/dashboard/procurement/orders` | YES (real page) | No | ✅ working |
| New Sales Invoice | `/dashboard/sales/invoices` | YES (real page) | No | ✅ working |
| New Customer | `/dashboard/sales/customers` | YES (real page) | No | ✅ working |
| New Product | `/dashboard/products` | YES (real page) | No | ✅ working |
| New Production Order | `/dashboard/production/orders` | Middleware redirect → production tab | 302 only | ✅ working |
| **New Contract** | `/dashboard/sales?tab=contracts&drawer=create` | YES (direct workspace URL) | No | ✅ **fixed** |
| **New Expense Claim** | `/dashboard/hr?tab=expenses&drawer=create` | YES (direct workspace URL) | No | ✅ **fixed** |
| **New Job Requisition** | `/dashboard/hr?tab=recruitment` | YES (direct workspace URL) | No | ✅ **fixed** |
| **New Kanban Card** | `/dashboard/planning?tab=kanban` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Start Van Route** | `/dashboard/sales?tab=van-sales` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Import Bank Statement** | `/dashboard/finance?tab=bank-recon` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Run MRP** | `/dashboard/planning?tab=mrp` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Run Procurement AI** | `/dashboard/procurement?tab=suggestions` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Run Bank Reconciliation** | `/dashboard/finance?tab=bank-recon` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Run Invoice Matching** | `/dashboard/finance?tab=invoice-match` | YES (direct workspace URL) | No | ✅ **fixed** |
| Generate AI Predictions | `/dashboard/ai/predictions` | YES (real page) | No | ✅ working |
| ERP Copilot | `/dashboard/ai/chat` | YES (real page) | No | ✅ working |
| **Run Kenya Payroll** | `/dashboard/hr?tab=payroll` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Run Production AI** | `/dashboard/production?tab=plans` | YES (direct workspace URL) | No | ✅ **fixed** |
| Sales Analytics | `/dashboard/analytics/sales` | YES (real page, 121 lines) | No | ✅ working |
| Finance Analytics | `/dashboard/analytics/finance` | YES (real page, 97 lines) | No | ✅ working |
| Inventory Analytics | `/dashboard/analytics/inventory` | YES (real page) | No | ✅ working |
| Production Analytics | `/dashboard/analytics/production` | YES (real page) | No | ✅ working |
| AI Audit Logs | `/dashboard/ai/logs` | YES (real page) | No | ✅ working |
| **Aging Report** | `/dashboard/finance?tab=dunning` | YES (direct workspace URL) | No | ✅ **fixed** |
| **Build Custom Report** | `/dashboard/analytics?tab=report-builder` | YES (direct workspace URL) | No | ✅ **fixed** |
| **ESG Reports** | `/dashboard/utility-management?tab=esg` | YES (direct workspace URL) | No | ✅ **fixed** |
| Analyze Sales Trends (AI) | `/dashboard/ai/chat?q=...` | YES (real page) | No | ✅ working |
| Stock Risk This Week (AI) | `/dashboard/ai/predictions` | YES (real page) | No | ✅ working |
| Show Business Risks (AI) | `/dashboard/ai/recommendations` | YES (real page) | No | ✅ working |
| Find Unpaid Invoices (AI) | `/dashboard/ai/chat?q=...` | YES (real page) | No | ✅ working |
| **Rider Performance (AI)** | `/dashboard/sales?tab=van-sales` | YES (direct workspace URL) | No | ✅ **fixed** |
| Generate Product Formula | `/dashboard/ai/formulations` | YES (real page) | No | ✅ working |
| Run Business Scenario | `/dashboard/ai/scenarios` | YES (real page) | No | ✅ working |

---

### Marketing Workspace — marketing/page.tsx

| Button | Old href | New href | Status |
|--------|---------|---------|--------|
| + New Campaign | `/dashboard/marketing/campaigns/new` (stub) | `/dashboard/marketing?tab=campaigns&drawer=create` | ✅ **fixed** |
| + New Promotion | `/dashboard/marketing/promotions/new` (stub) | `/dashboard/marketing?tab=promotions&drawer=create` | ✅ **fixed** |

---

### CRM Workspace — crm/page.tsx

| Link | Old href | New href | Status |
|------|---------|---------|--------|
| Lead List | `/dashboard/crm/leads` | unchanged | ✅ real page (170 lines) |
| Opportunities | `/dashboard/crm/opportunities` | unchanged | ✅ real page (187 lines) |
| Pipeline Board | `/dashboard/crm/pipeline` | unchanged | ✅ real page (155 lines) |
| Activity Timeline | `/dashboard/crm/activities` | unchanged | ✅ real page (123 lines) |
| Forecast | `/dashboard/crm/forecast` | unchanged | ✅ real page (132 lines) |
| Win/Loss Analysis | `/dashboard/crm/win-loss` | unchanged | ✅ real page (150 lines) |
| Overdue Queue | `/dashboard/crm/overdue` (stub) | `/dashboard/crm?tab=pipeline` | ✅ **fixed** |
| AI Agents | `/dashboard/crm/ai` (stub) | `/dashboard/crm?tab=overview` | ✅ **fixed** |
| Stage Config | `/dashboard/crm/stages` | unchanged | ✅ real page (145 lines) |

---

### Documents Workspace — documents/page.tsx

| Button | Old push | New push | Status |
|--------|---------|---------|--------|
| + New Document | `router.push("/dashboard/documents/new")` | `router.push("/dashboard/documents?drawer=create")` | ✅ **fixed** |

---

## Classification Reference

| Code | Meaning |
|------|---------|
| ✅ working | Direct route, real page, no redirect |
| ✅ **fixed** | Was broken stub/redirect, now direct workspace URL |
| ⚠️ middleware_redirect | Goes through 302 redirect but lands correctly |
| ❌ broken_redirect_stub | Points to redirect stub, may lose drawer/action params |
| ❌ broken_dead_route | Route does not exist (404) |
