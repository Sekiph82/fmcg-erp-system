# PAGE CONSOLIDATION PLAN
Version: 1.0 | Date: 2026-05-16 | Status: Approved for Implementation

## Problem Statement

755 page.tsx files across 103 top-level modules create:
- Sidebar with 72 expandable sections under 14 clusters
- Each section expands to 5–20 child links → effective visible nav items = hundreds
- Code duplication across near-identical list/create/edit pages
- RBAC complexity multiplied across fragments
- Hard to onboard new developers

## Target State

| Metric | Current | Target |
|--------|---------|--------|
| page.tsx files | 755 | 755 (preserved) |
| Sidebar top-level items | 72 sections | 40–48 workspaces |
| Visible nav child links | 300+ | 0 (moved to tabs) |
| Workspace components | 0 | ~15 reusable |
| Route redirects | 0 | ~650 |

> **Key insight:** We do NOT delete pages. We eliminate sidebar child link exposure and convert functional screens into tabs/drawers within workspace pages. Old URLs redirect.

---

## Target Workspace Architecture

### Sidebar Structure (target: 40–48 items)

```
Dashboard                          → /dashboard

── Supply Chain ─────────────────────
Products                           → /dashboard/products
Materials                          → /dashboard/materials
Suppliers                          → /dashboard/suppliers
Inventory                          → /dashboard/inventory
Warehouses & WMS                   → /dashboard/warehouses
Procurement                        → /dashboard/procurement

── Manufacturing ────────────────────
Production                         → /dashboard/production
Planning                           → /dashboard/planning
NPD                                → /dashboard/npd
BOM & Formula                      → /dashboard/bom
Recipes                            → /dashboard/recipes
Quality                            → /dashboard/quality
Compliance                         → /dashboard/compliance

── Commercial ───────────────────────
Sales                              → /dashboard/sales
CRM                                → /dashboard/crm
Marketing                          → /dashboard/marketing
POS                                → /dashboard/pos

── Finance ──────────────────────────
Finance                            → /dashboard/finance

── Factory Operations ───────────────
Maintenance                        → /dashboard/maintenance
Utilities                          → /dashboard/utility-management
Shop Floor                         → /dashboard/shop-floor

── Logistics ────────────────────────
Logistics                          → /dashboard/logistics

── HR & Payroll ─────────────────────
HR                                 → /dashboard/hr
Kenya Payroll                      → /dashboard/payroll

── Documents & Communication ────────
Documents                          → /dashboard/documents
Communication                      → /dashboard/communication
Helpdesk                           → /dashboard/helpdesk

── Intelligence ─────────────────────
AI                                 → /dashboard/ai
Analytics                          → /dashboard/analytics

── Administration ───────────────────
Admin                              → /dashboard/admin
Integrations                       → /dashboard/integrations
```

**Total: 33 sidebar entries** (plus cluster headers) — well within 35–55 target.

---

## Workspace Tab Definitions

### /dashboard/products
Tabs: List | Categories | Pricing | Import/Export | History | Reports | AI

### /dashboard/materials
Tabs: List | Categories | Specs | Import/Export | Reports

### /dashboard/suppliers
Tabs: List | Contacts | Pricing | Performance | Documents | Import/Export

### /dashboard/inventory
Tabs: Stock | Movements | Tracking (Serials/Batch) | Valuation | Cycle Count | Shelf-Life | Traceability | Import/Export | Reports

### /dashboard/warehouses
Tabs: Warehouses | WMS | Putaway | Picking | Replenishment | Containers | Reports

### /dashboard/procurement
Tabs: Dashboard | Requests | Orders | RFQ | Blanket | Reorder | Deliveries | Supplier Scorecard | Suggestions | Subcontracting | Landed Cost | Supplier Portal | Invoice Match | Reports

### /dashboard/production
Tabs: Dashboard | Orders | Work Orders | Work Centers | Scheduling | Execution | Machine Ops | Material Flow | OEE | Waste & Yield | Batch/Lots | WIP | Costing | Variance | Labor | Time Tracking | Projects | Advanced | AI | Reports

### /dashboard/planning
Tabs: MRP | MPS | Advanced Planning | Kanban | Capacity | Bottlenecks | Simulation

### /dashboard/npd
Tabs: Projects | Stage Gates | Pilot Batches | Readiness | Approvals | Reports | AI

### /dashboard/bom
Tabs: BOM List | Formula Lines | Costing | Compare | Conversion | Substitutes | AI

### /dashboard/recipes
Tabs: List | Ingredients | Process | Approval | Import/Export | Reports

### /dashboard/quality
Tabs: Inspections | Parameters | QMS | HACCP | CCP | Deviations | CAPA | Calibration | AQL | COA | Allergen | Nutrition | Brand Assets | Complaints | Certificates | Traceability | Reports | AI

### /dashboard/compliance
Tabs: GS1 | Labels | Barcodes | Print Queue | SSCC | Regulatory Certs | Audit | Reports | AI

### /dashboard/sales
Tabs: Dashboard | Quotes | Orders | Invoices | Delivery | Shipments | Returns | Collections | Field Sales | Distributors | Van Sales | Secondary | Recurring | Price Lists | Dynamic Pricing | Contracts | Commissions | Portal | NPS | Loyalty | Reports

### /dashboard/crm
Tabs: Dashboard | Leads | Opportunities | Pipeline | Activities | Qualify | Forecast | Win-Loss | Overdue | Segments | Surveys | Territory | AI

### /dashboard/marketing
Tabs: Dashboard | Campaigns | Promotions | Schemes | TPM | Trade Spend | Brand Spend | Segments | Visits | Influencers | Social Media | E-commerce | Ads | Market Intel | Surveys | AI Optimizer | Analytics | Reports

### /dashboard/finance
Tabs: Overview | Cashbook | Receivables | Accounting | Journal | COA | GL | Trial Balance | P&L | Balance Sheet | Period Closing | Budgets | Product Costing | Bank Recon | Invoice Match | Fixed Assets | Dimensions | Dunning | Tax | eTIMS | VAT | Expenses | Receipt OCR | Bank API | Exchange Rates | M-Pesa | Reports

### /dashboard/maintenance
Tabs: Dashboard | Assets | PM Plans | Work Orders | Breakdowns | Predictive | Spare Parts | Reports

### /dashboard/utility-management
Tabs: Dashboard | Assets | Devices | Readings | Electricity | Water | Soft Water | Steam | Compressor | Solar | Chemical | Wastewater | Machine Utility | Billing | Alarms | KPI Center | ESG | IoT | Reports | Integration

### /dashboard/shop-floor
Tabs: Dashboard | Terminal | Supervisor | Queue | Downtime | Handover

### /dashboard/logistics
Tabs: Overview | Shipments | Arrivals | Customs | Containers | Fleet | Drivers | Trips | Fuel | Incidents | Reports

### /dashboard/hr
Tabs: Overview | Employees | Shifts | Attendance | Leave | Payroll | Recruitment | ESS | Appraisals | Training | Timesheets | Expenses | Reports

### /dashboard/payroll (Kenya)
Tabs: Dashboard | Runs | Profiles | Reports | Statutory

### /dashboard/documents
Tabs: Repository | Knowledge Base | E-Signatures | Contracts | Compliance | Expiring | Reports

### /dashboard/communication
Tabs: Messages | Email | WhatsApp | Calls | Meetings | Calendar | Chatter | Notifications | Reports

### /dashboard/helpdesk
Tabs: Dashboard | All Tickets | Open | Escalated | SLA | Reports

### /dashboard/ai
Tabs: Dashboard | Chat | NL Command | Predictions | Recommendations | Scenarios | Formulations | Compliance | Governance | Logs

### /dashboard/analytics
Tabs: BI Hub | Report Builder | Saved Reports | Schedules | Market Intel | Inventory | Sales | Finance | Production | Procurement | Marketing | AI Insights

### /dashboard/admin
Tabs: Users | Roles | Permissions | Companies | Security | Approvals | Custom Fields | Mobile | Import History | System Logs | System Config | Kanban

### /dashboard/integrations
Tabs: Overview | Marketplace | Webhooks | Developer | API Keys | GraphQL | M-Pesa | Barcode | Email | WhatsApp | Marketing Sync | Logs

---

## URL / Query Parameter Standard

```
Main tab:       ?tab=<tab-key>
Sub-tab:        ?subtab=<subtab-key>
Drawer open:    ?drawer=create | edit | detail | import
Entity ID:      ?id=<uuid>
Named entity:   ?productId=<id> | ?orderId=<id> | ?journalId=<id>
```

Examples:
```
/dashboard/products?tab=list
/dashboard/products?tab=pricing
/dashboard/products?drawer=create
/dashboard/products?id=abc123&drawer=edit
/dashboard/finance?tab=bank-recon
/dashboard/finance?tab=invoice-match&id=xyz&drawer=detail
/dashboard/inventory?tab=shelf-life
/dashboard/production?tab=execution
/dashboard/utilities?tab=electricity
```

Rules:
- Tab keys: lowercase kebab-case, stable (never rename)
- `tab` is the primary tab key
- `subtab` for sub-navigation inside a tab
- `drawer` controls which panel/modal opens
- `id` is the entity being viewed/edited
- Browser back/forward must work (URL-driven state)

---

## Implementation Phases

### Phase 1 — Infrastructure (CURRENT)
- [x] Audit document (docs/PAGE_CONSOLIDATION_AUDIT.md)
- [x] Plan document (docs/PAGE_CONSOLIDATION_PLAN.md)
- [ ] Reusable workspace components (frontend/src/components/workspace/)
- [ ] Route redirect map (frontend/src/lib/routeRedirectMap.ts)
- [ ] Redirect middleware (frontend/src/middleware.ts)
- [ ] Simplified nav-config.tsx (40–48 workspace entries)
- [ ] Audit script (scripts/audit-page-count.mjs)

### Phase 2 — Supply Chain Modules
- [ ] /products workspace (with existing page as tabs)
- [ ] /materials workspace
- [ ] /suppliers workspace
- [ ] /inventory workspace (absorb: cycle-count, shelf-life, traceability)
- [ ] /warehouses workspace (absorb: wms, putaway, containers)
- [ ] Sidebar rebuilt with Phase 2 workspaces
- [ ] Redirect tests pass

### Phase 3 — Transactional Core
- [ ] /procurement workspace (absorb: subcontracting, landed-cost, suggestions, supplier-portal, copacking)
- [ ] /sales workspace (absorb: price-lists, dynamic-pricing, contracts, recurring-orders, commissions, secondary-sales, van-sales, portal)
- [ ] /crm workspace (absorb: loyalty, nps, surveys)
- [ ] /finance workspace (absorb: bank-recon, invoice-match, fixed-assets, dimensions, dunning, tax, bank-api, expenses)

### Phase 4 — Manufacturing
- [ ] /production workspace (absorb: production-execution, machine-ops, material-flow, projects)
- [ ] /planning workspace (absorb: mrp, mps, kanban, planning)
- [ ] /npd workspace
- [ ] /bom workspace
- [ ] /recipes workspace
- [ ] /quality workspace (absorb: qms, allergen, brand-assets, traceability)
- [ ] /compliance workspace (absorb: gs1)

### Phase 5 — Factory & Ops
- [ ] /maintenance workspace
- [ ] /utility-management workspace (absorb: esg, iot)
- [ ] /shop-floor workspace
- [ ] /logistics workspace (absorb: fleet, containers)

### Phase 6 — Business & Admin
- [ ] /hr workspace (absorb: recruitment, ess, appraisals, training, timesheets, expenses)
- [ ] /payroll workspace (Kenya)
- [ ] /marketing workspace (absorb: tpm, promotions, market-intelligence)
- [ ] /documents workspace (absorb: knowledge-base, esign)
- [ ] /communication workspace (absorb: chatter, calendar, messages, email, whatsapp, calls, meetings, notifications)
- [ ] /helpdesk workspace
- [ ] /ai workspace
- [ ] /analytics workspace (absorb: report-builder, reports)
- [ ] /admin workspace (absorb: users, roles, permissions, companies, security, custom-fields, utilities, mobile, logs, import-history, kanban)
- [ ] /integrations workspace (absorb: webhooks, developer, portal)

---

## Workspace Component Architecture

```
frontend/src/components/workspace/
├── ModuleWorkspace.tsx          — root layout wrapper
├── WorkspaceHeader.tsx          — title + description + primary action
├── WorkspaceTabs.tsx            — URL-driven tab bar
├── WorkspaceContent.tsx         — tab content area with permission gate
├── WorkspaceDrawer.tsx          — slide-in panel for create/edit/detail
├── WorkspaceEmptyState.tsx      — empty state component
└── index.ts                     — re-exports
```

### ModuleWorkspace Props
```typescript
interface ModuleWorkspaceProps {
  title: string
  description?: string
  permission?: string
  primaryAction?: { label: string; onClick: () => void; permission?: string }
  tabs: WorkspaceTab[]
  children?: React.ReactNode // fallback content
}

interface WorkspaceTab {
  key: string
  label: string
  permission?: string
  content: React.ReactNode
}
```

### WorkspaceTabs Behavior
- Reads `?tab=` from URL search params
- Defaults to first visible tab
- Updates URL on tab change (replaceState, preserves other params)
- Hides tabs user lacks permission for
- Responsive: collapses to dropdown on mobile

### WorkspaceDrawer Behavior
- Opens when `?drawer=create|edit|detail|import` present in URL
- Closes by removing drawer param (preserves other params)
- Supports back button to close
- Width: 600px on desktop, full-width on mobile

---

## Permission Architecture

### Frontend (UI gating)
- `ModuleWorkspace`: hide entire page if no module permission
- `WorkspaceTabs`: hide tab if no tab permission
- Action buttons: hide/disable based on write permission
- Drawers: same permission as the tab they open from

### Backend (enforcement)
- Backend remains the authority
- Frontend gates are UX convenience only
- All mutations go through permission-checked API endpoints

### Permission Defaults (when permission unknown)
- View tabs: show (optimistic)
- Create/Edit/Delete actions: hide (conservative)
- Import/Export: hide (conservative)
- Destructive actions: require explicit permission + confirmation

---

## Navigation Architecture Changes

### Before (72 expandable sections):
```
Master Data ▾
  Products
  Materials
  Suppliers
  Warehouses
  Customers
  Recipes / BOM

Planning ▾
  New Product Development
    NPD Projects

  MRP & Forecasting
    MRP Dashboard
    Planner Workbench
    ...7 items

  Master Production Schedule
    ...5 items

  Advanced Planning Suite
    ...6 items
  ...etc
```

### After (33 flat workspace links):
```
Dashboard

── Supply Chain ─────────────────
Products
Materials
Suppliers
Inventory
Warehouses & WMS
Procurement

── Manufacturing ─────────────────
Production
Planning
NPD
BOM & Formula
Recipes
Quality
Compliance

── Commercial ────────────────────
Sales
CRM
Marketing
POS

── Finance ───────────────────────
Finance

── Factory Ops ───────────────────
Maintenance
Utilities
Shop Floor

── Logistics ─────────────────────
Logistics

── HR & Payroll ──────────────────
HR
Kenya Payroll

── Docs & Comms ──────────────────
Documents
Communication
Helpdesk

── Intelligence ──────────────────
AI
Analytics

── Admin ─────────────────────────
Admin
Integrations
```

### Sidebar Search
- Must still search child tabs/functions
- Result shows: "Products › Pricing" → routes to /dashboard/products?tab=pricing
- No UI change to search results beyond routing target

---

## Redirect Map Summary

Old routes redirect to new workspace tabs. Full list in `frontend/src/lib/routeRedirectMap.ts`.

Key redirects:
```
/dashboard/cycle-count          → /dashboard/inventory?tab=cycle-count
/dashboard/shelf-life           → /dashboard/inventory?tab=shelf-life
/dashboard/traceability         → /dashboard/inventory?tab=traceability
/dashboard/movements            → /dashboard/inventory?tab=movements
/dashboard/wms                  → /dashboard/warehouses?tab=wms
/dashboard/putaway              → /dashboard/warehouses?tab=wms
/dashboard/containers           → /dashboard/logistics?tab=containers
/dashboard/subcontracting       → /dashboard/procurement?tab=subcontracting
/dashboard/landed-cost          → /dashboard/procurement?tab=landed-cost
/dashboard/procurement-suggestion → /dashboard/procurement?tab=suggestions
/dashboard/supplier-portal      → /dashboard/procurement?tab=supplier-portal
/dashboard/copacking            → /dashboard/procurement?tab=subcontracting
/dashboard/price-lists          → /dashboard/sales?tab=price-lists
/dashboard/dynamic-pricing      → /dashboard/sales?tab=dynamic-pricing
/dashboard/contracts            → /dashboard/sales?tab=contracts
/dashboard/recurring-orders     → /dashboard/sales?tab=recurring
/dashboard/commissions          → /dashboard/sales?tab=commissions
/dashboard/secondary-sales      → /dashboard/sales?tab=secondary
/dashboard/van-sales            → /dashboard/sales?tab=van-sales
/dashboard/portal               → /dashboard/sales?tab=portal
/dashboard/loyalty              → /dashboard/crm?tab=loyalty
/dashboard/nps                  → /dashboard/crm?tab=nps
/dashboard/surveys              → /dashboard/crm?tab=surveys
/dashboard/tpm                  → /dashboard/marketing?tab=tpm
/dashboard/promotions           → /dashboard/marketing?tab=promotions-schemes
/dashboard/market-intelligence  → /dashboard/marketing?tab=market-intel
/dashboard/bank-reconciliation  → /dashboard/finance?tab=bank-recon
/dashboard/invoice-match        → /dashboard/finance?tab=invoice-match
/dashboard/fixed-assets         → /dashboard/finance?tab=fixed-assets
/dashboard/dimensions           → /dashboard/finance?tab=dimensions
/dashboard/dunning              → /dashboard/finance?tab=dunning
/dashboard/tax                  → /dashboard/finance?tab=tax
/dashboard/bank-api             → /dashboard/finance?tab=bank-api
/dashboard/machine-ops          → /dashboard/production?tab=machine-ops
/dashboard/material-flow        → /dashboard/production?tab=material-flow
/dashboard/production-execution → /dashboard/production?tab=execution
/dashboard/projects             → /dashboard/production?tab=projects
/dashboard/mrp                  → /dashboard/planning?tab=mrp
/dashboard/mps                  → /dashboard/planning?tab=mps
/dashboard/planning             → /dashboard/planning?tab=advanced
/dashboard/kanban               → /dashboard/planning?tab=kanban
/dashboard/qms                  → /dashboard/quality?tab=qms
/dashboard/allergen             → /dashboard/quality?tab=allergen
/dashboard/brand-assets         → /dashboard/quality?tab=brand-assets
/dashboard/gs1                  → /dashboard/compliance?tab=gs1
/dashboard/quality/consumer-complaints → /dashboard/quality?tab=complaints
/dashboard/maintenance/...      → /dashboard/maintenance?tab=...
/dashboard/utility-management   → /dashboard/utility-management (stays)
/dashboard/iot                  → /dashboard/utility-management?tab=iot
/dashboard/esg                  → /dashboard/utility-management?tab=esg
/dashboard/fleet                → /dashboard/logistics?tab=fleet
/dashboard/logistics/containers → /dashboard/logistics?tab=containers
/dashboard/recruitment          → /dashboard/hr?tab=recruitment
/dashboard/ess                  → /dashboard/hr?tab=ess
/dashboard/appraisals           → /dashboard/hr?tab=appraisals
/dashboard/training             → /dashboard/hr?tab=training
/dashboard/timesheets           → /dashboard/hr?tab=timesheets
/dashboard/expenses             → /dashboard/hr?tab=expenses
/dashboard/knowledge-base       → /dashboard/documents?tab=knowledge-base
/dashboard/esign                → /dashboard/documents?tab=esign
/dashboard/chatter              → /dashboard/communication?tab=chatter
/dashboard/calendar             → /dashboard/communication?tab=calendar
/dashboard/messages             → /dashboard/communication?tab=messages
/dashboard/email                → /dashboard/communication?tab=email
/dashboard/whatsapp             → /dashboard/communication?tab=whatsapp
/dashboard/calls                → /dashboard/communication?tab=calls
/dashboard/meetings             → /dashboard/communication?tab=meetings
/dashboard/notification-center  → /dashboard/communication?tab=notifications
/dashboard/report-builder       → /dashboard/analytics?tab=report-builder
/dashboard/reports              → /dashboard/analytics?tab=reports
/dashboard/market-intelligence  → /dashboard/analytics?tab=market-intel
/dashboard/users                → /dashboard/admin?tab=users
/dashboard/roles                → /dashboard/admin?tab=roles
/dashboard/permissions          → /dashboard/admin?tab=permissions
/dashboard/companies            → /dashboard/admin?tab=companies
/dashboard/security             → /dashboard/admin?tab=security
/dashboard/custom-fields        → /dashboard/admin?tab=custom-fields
/dashboard/utilities            → /dashboard/admin?tab=system-config
/dashboard/mobile               → /dashboard/admin?tab=mobile
/dashboard/logs                 → /dashboard/admin?tab=logs
/dashboard/import-history       → /dashboard/admin?tab=import-history
/dashboard/approvals            → /dashboard/admin?tab=approvals
/dashboard/webhooks             → /dashboard/integrations?tab=webhooks
/dashboard/developer            → /dashboard/integrations?tab=developer
```

---

## Adding New Modules (Anti-sprawl Guide)

### DO:
1. Add a tab to an existing workspace if the feature belongs there
2. Create a new workspace ONLY if the module has 5+ distinct views and its own permission
3. Use WorkspaceTabs + WorkspaceDrawer pattern
4. Register the route in routeRedirectMap if any old links exist
5. Add permission to the workspace and tab level
6. Update nav-config.tsx with the workspace entry (not child pages)

### DON'T:
1. Create a new top-level sidebar section for a sub-feature
2. Create separate pages for create/edit/detail — use WorkspaceDrawer
3. Create separate pages for import/export — use a tab panel
4. Create separate pages for reports — use a Reports tab
5. Hard-code routes in components — use the workspace pattern

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| Existing deep links break | routeRedirectMap + middleware redirect |
| Permission checks bypass | Backend remains authoritative |
| Large workspaces load slowly | Tab-level lazy loading |
| Mobile sidebar overflow | Dropdown collapse on narrow screens |
| Drawer state lost on navigation | URL-persisted drawer state |
