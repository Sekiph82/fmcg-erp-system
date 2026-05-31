# Page Consolidation History

Completed 2026-05-17. All 5 passes executed across two sessions (2026-05-16 and 2026-05-17).

## Final Counts (post Pass 6 closeout)

| Classification          | Count |
|-------------------------|-------|
| A WORKSPACE_PAGE        | 31    |
| B REDIRECT_ONLY         | 496   |
| C LIGHTWEIGHT_WRAPPER   | 213   |
| D FULL_DUPLICATE_UI     | 0     |
| E STANDALONE_OPERATIONAL| 14    |
| F UNKNOWN               | 0     |
| **Total**               | **754** |

## Pass 1 — Infrastructure (2026-05-16)

**Route Redirect Drift — Fixed**
- Added 13 marketing child-route prefix entries to middleware.ts + routeRedirectMap.ts
- Added finance/accounting prefix entry
- Added 6 production child-route prefix entries
- Added 3 utility-management child-route prefix entries
- check-route-redirects.js: 0 issues (was 7)

**Sidebar Search Hints — Fixed**
- nav-config.tsx: `alarms` → `alarm-center`, `kpi` → `kpi-center`
- Removed `contracts` hint from documents workspace (no such tab)
- Removed `market-intel` hint from analytics workspace (tab is in marketing)
- check-workspace-tabs.js: 0 issues (was 12)

## Pass 2 — Theme + First Wave (2026-05-16)

**Theme Preservation**
- docs/UI_THEME_AUDIT.md created (NEON LIQUID GLASS design audit)
- frontend/src/lib/ui-theme.ts created (reusable theme constants)

**Pages Converted (73)**
- marketing: 36 pages → redirect-only
- finance/accounting: 13 pages
- production: 6 pages
- utility-management: 18 pages
- FULL_DUPLICATE_UI: 500 → 427

## Pass 3 — HR + Quality (2026-05-16)

**Pages Converted (76)**
- van-sales: 16 → /dashboard/sales?tab=van-sales
- qms: 15 → /dashboard/quality?tab=qms
- recruitment: 12 → /dashboard/hr?tab=recruitment
- allergen: 11 → /dashboard/quality?tab=allergen
- expenses: 11 → /dashboard/hr?tab=expenses
- fixed-assets: 11 → /dashboard/finance?tab=fixed-assets
- FULL_DUPLICATE_UI: 427 → 351

**Checks post-Pass 3:** B=149, D=351, build PASS

## Pass 4 — CRM/Sales/Docs + UNKNOWN clearance (2026-05-17)

**UNKNOWN pages classified (3 → 0)**
- utilities/currencies, utilities/series, utilities/uom → B REDIRECT_ONLY

**Pages Converted (16)**
- CRM child: crm/ai, crm/overdue, crm/qualify, crm/records/[id]
- Sales child: orders/[id], invoices/[id], shipments/[id], pod, customer-statement
- Procurement child: [id], orders/[id]
- Documents child: new, [id]
- Utilities child: currencies, series, uom

**Middleware additions:**
- CRM child routes (prefix for records/[id])
- Sales static child routes
- Documents drawer entry

**BOM [id] pages documented:** rich formula editor → STANDALONE_OPERATIONAL (no workspace drawer)

**Checks post-Pass 4:** B=165, D=338, UNKNOWN=0, build PASS

## Pass 5 — Mass Conversion (2026-05-17)

**Pages Converted (331 new entries in convert-redirects.js)**

All clusters had existing MW prefix coverage:

| Cluster | Count | Target |
|---------|-------|--------|
| material-flow | 11 | /dashboard/production?tab=material-flow |
| portal | 11 | /dashboard/sales?tab=portal |
| shelf-life | 11 | /dashboard/inventory?tab=shelf-life |
| supplier-portal | 11 | /dashboard/procurement?tab=supplier-portal |
| tpm | 11 | /dashboard/marketing?tab=tpm |
| appraisals | 10 | /dashboard/hr?tab=appraisals |
| bank-reconciliation | 10 | /dashboard/finance?tab=bank-recon |
| dimensions | 10 | /dashboard/finance?tab=dimensions |
| recurring-orders | 10 | /dashboard/sales?tab=recurring |
| calendar | 9 | /dashboard/communication?tab=calendar |
| dunning | 9 | /dashboard/finance?tab=dunning |
| machine-ops | 9 | /dashboard/production?tab=machine-ops |
| report-builder | 9 | /dashboard/analytics?tab=report-builder |
| traceability | 9 | /dashboard/inventory?tab=traceability |
| custom-fields | 8 | /dashboard/admin?tab=custom-fields |
| ess | 8 | /dashboard/hr?tab=ess |
| gs1 | 8 | /dashboard/compliance?tab=gs1 |
| invoice-match | 8 | /dashboard/finance?tab=invoice-match |
| price-lists | 8 | /dashboard/sales?tab=price-lists |
| promotions | 8 | /dashboard/marketing?tab=promotions-schemes |
| training | 8 | /dashboard/hr?tab=training |
| contracts | 7 | /dashboard/sales?tab=contracts |
| fleet | 7 | /dashboard/logistics?tab=fleet |
| reports | 7 | /dashboard/analytics?tab=reports |
| commissions | 6 | /dashboard/sales?tab=commissions |
| esg | 6 | /dashboard/utility-management?tab=esg |
| mrp | 6 | /dashboard/planning?tab=mrp |
| notification-center | 6 | /dashboard/communication?tab=notifications |
| procurement-suggestion | 6 | /dashboard/procurement?tab=suggestions |
| subcontracting | 6 | /dashboard/procurement?tab=subcontracting |
| timesheets | 6 | /dashboard/hr?tab=timesheets |
| webhooks | 6 | /dashboard/integrations?tab=webhooks |
| chatter | 5 | /dashboard/communication?tab=chatter |
| cycle-count | 5 | /dashboard/inventory?tab=cycle-count |
| kanban | 5 | /dashboard/planning?tab=kanban |
| landed-cost | 5 | /dashboard/procurement?tab=landed-cost |
| wms sub-pages | 5 | /dashboard/warehouses?tab=wms |
| mps | 4 | /dashboard/planning?tab=mps |
| surveys | 4 | /dashboard/crm?tab=surveys |
| tax | 4 | /dashboard/finance?tab=tax |
| knowledge-base | 3 | /dashboard/documents?tab=knowledge-base |
| production-execution | 3 | /dashboard/production?tab=execution |
| putaway | 3 | /dashboard/warehouses?tab=wms |
| secondary-sales | 3 | /dashboard/sales?tab=secondary |
| containers | 2 | /dashboard/logistics?tab=containers |
| developer | 2 | /dashboard/integrations?tab=developer |
| logs | 2 | /dashboard/admin?tab=logs |
| mobile | 2 | /dashboard/admin?tab=mobile |
| projects | 2 | /dashboard/production?tab=projects |
| brand-assets/[id] | 1 | /dashboard/quality?tab=brand-assets |
| copacking | 1 | /dashboard/procurement?tab=subcontracting |
| payroll/runs/[id] | 1 | /dashboard/hr?tab=payroll |
| quality/[id] | 1 | /dashboard/quality?tab=qms (file-level only) |
| roles/[id] | 1 | /dashboard/admin?tab=roles |
| security/monitor | 1 | /dashboard/admin?tab=security |
| users/[id] | 1 | /dashboard/admin?tab=users |

**Middleware addition:**
- `/dashboard/payroll` → `{ p: "/dashboard/hr", t: "payroll" }` (was missing)

**STANDALONE_DIRS additions:**
- "npd" (npd/[id] — NPD project detail, stage gates, rich editor)
- "recipes" (recipes/[id] — recipe editor with items and process parameters)

**Checks post-Pass 5:** A=31, B=496, C=213, D=5, E=9, F=0, build PASS

## Pass 6 — Closeout (2026-05-17)

**Remaining D=5 classified:**

| Route | Decision | Reason |
|-------|----------|--------|
| `/dashboard/bom/[id]` | STANDALONE_OPERATIONAL | Full formula editor: formula lines, yield configs, AI recs, batch scaling, lifecycle CRUD |
| `/dashboard/bom/[id]/compliance` | STANDALONE_OPERATIONAL | BOM allergen/compliance sub-view, useQuery per [id] |
| `/dashboard/bom/[id]/costing` | STANDALONE_OPERATIONAL | BOM cost roll-up sub-view, useQuery per [id] |
| `/dashboard/bom/[id]/explode` | STANDALONE_OPERATIONAL | Multi-level BOM explosion tree, useState + useQuery |
| `/dashboard/` (root) | STANDALONE_OPERATIONAL | Executive Dashboard — primary landing page, useQuery KPIs, auto-refresh |

**Audit script change (audit-page-count.js):**
Added path-specific rules in `classify()` before the STANDALONE_DIRS check:
- Root page (`parts.length === 1 && parts[0] === "page.tsx"`) → E
- bom/[id] and sub-pages (`topDir === "bom" && parts[1] === "[id]"`) → E

Cannot add "bom" to STANDALONE_DIRS because `bom/compare`, `bom/substitutes`, `bom/conversion` are C=LIGHTWEIGHT_WRAPPER (dynamically imported by `bom/page.tsx`). Adding "bom" to STANDALONE_DIRS would catch them before the C check.

**Final checks:**
- audit-page-count → A=31, B=496, C=213, D=0, E=14, F=0, Total=754
- check-route-redirects → 0 drift
- check-workspace-tabs → 0 mismatches
- tsc --noEmit → PASS
- npm run build → PASS (exit 0, 697 static pages generated)
- erp-health-audit.py → 0 HIGH
