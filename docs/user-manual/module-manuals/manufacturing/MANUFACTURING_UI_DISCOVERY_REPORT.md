# Manufacturing UI Discovery Report

**Discovery method:** Source code inspection of all Manufacturing frontend page components  
**Date:** 2026-05-19  
**Scope:** Manufacturing module only (Supply Chain excluded)

---

## Routes Scanned

| Route | Page | Component File |
|---|---|---|
| /dashboard/production | Production | production/page.tsx |
| /dashboard/planning | Planning | planning/page.tsx |
| /dashboard/npd | NPD | npd/page.tsx |
| /dashboard/bom | BOM & Formula | bom/page.tsx |
| /dashboard/recipes | Recipes | recipes/page.tsx |
| /dashboard/quality | Quality | quality/page.tsx |
| /dashboard/compliance | Compliance | compliance/page.tsx |
| /dashboard/shop-floor | Shop Floor | shop-floor/page.tsx |

---

## Page Summary

| Page | Route | Tabs Found | Buttons Found | Dropdowns Found | Modals/Forms Found | Imports Found |
|---|---|---:|---:|---:|---:|---:|
| Production | /dashboard/production | 20 | 2 | 2 | 2 | 0 |
| Planning | /dashboard/planning | 9 | 1 | 1 | 1 | 0 |
| NPD | /dashboard/npd | 1 | 1 | 1 | 1 (inline form) | 0 |
| BOM & Formula | /dashboard/bom | 4 | 2 | 2 | 2 | 0 |
| Recipes | /dashboard/recipes | 1 | 2 | 1 | 2 (+ 3-tab import) | 1 |
| Quality | /dashboard/quality | 8 | 1 | 2 | 1 | 0 |
| Compliance | /dashboard/compliance | 2 | 3 | 2 | 1 (inline form) | 0 |
| Shop Floor | /dashboard/shop-floor | 6 | 2 | 0 | 0 | 0 |
| **TOTAL** | | **51** | **14** | **11** | **10** | **1** |

---

## Production — All 20 Tabs

| # | Tab Label | URL Key | Route | Has Modal/Button | Tab Key Confirmed |
|---|---|---|---|---|---|
| 1 | Plans | plans | /dashboard/production | + New Plan modal | ✓ (default tab) |
| 2 | Work Orders | orders | /dashboard/production?tab=orders | + New Work Order modal | ✓ |
| 3 | Scheduling | scheduling | /dashboard/production?tab=scheduling | — | ✓ |
| 4 | Work Centers | work-centers | /dashboard/production?tab=work-centers | — | ✓ |
| 5 | Routing | routing | /dashboard/production?tab=routing | — | ✓ |
| 6 | Batch / Lots | batch-lots | /dashboard/production?tab=batch-lots | — | ✓ |
| 7 | QC | quality-control | /dashboard/production?tab=quality-control | — | ✓ |
| 8 | Labor | labor | /dashboard/production?tab=labor | — | ✓ |
| 9 | Time Tracking | time-tracking | /dashboard/production?tab=time-tracking | — | ✓ |
| 10 | OEE | oee | /dashboard/production?tab=oee | — | ✓ |
| 11 | Downtime | downtime | /dashboard/production?tab=downtime | — | ✓ |
| 12 | Waste & Yield | waste-yield | /dashboard/production?tab=waste-yield | — | ✓ |
| 13 | WIP | wip | /dashboard/production?tab=wip | — | ✓ |
| 14 | Costing | costing | /dashboard/production?tab=costing | — | ✓ |
| 15 | Variance | variance | /dashboard/production?tab=variance | — | ✓ |
| 16 | Reports | reports | /dashboard/production?tab=reports | — | ✓ |
| 17 | Execution | execution | /dashboard/production?tab=execution | — | ✓ (loads production-execution/page) |
| 18 | Machine Ops | machine-ops | /dashboard/production?tab=machine-ops | — | ✓ (loads machine-ops/page) |
| 19 | Material Flow | material-flow | /dashboard/production?tab=material-flow | — | ✓ (loads material-flow/page) |
| 20 | Projects | projects | /dashboard/production?tab=projects | — | ✓ (loads projects/page) |

**Production total: 20 tabs.** All tabs confirmed from source in `frontend/src/app/dashboard/production/page.tsx`.  
**Note on tab row:** The tab row may be horizontally scrollable at smaller viewports. Capture spec uses 1600×900 viewport so all tabs should be visible without scrolling.

---

## Planning — 9 Tabs

| # | Tab Label | URL Key | Has Modal |
|---|---|---|---|
| 1 | Dashboard | advanced | + New Scenario modal |
| 2 | Schedule | schedule | — |
| 3 | Capacity | capacity | — |
| 4 | Simulation | simulation | — |
| 5 | Bottlenecks | bottlenecks | — |
| 6 | Changeover | changeover | — |
| 7 | MRP | mrp | — |
| 8 | MPS | mps | — |
| 9 | Kanban | kanban | — |

**New Scenario modal fields:** scenario_name, mode (FINITE/INFINITE dropdown), description.

---

## NPD — 1 Tab

| Tab | Actions | Filters |
|---|---|---|
| New Products | + New Project (inline form) | Stage filter pills (All, IDEA, CONCEPT, DEVELOPMENT, PILOT, LAUNCH, LAUNCHED, CANCELLED) |

**New Project form fields:** Product Name*, Category (NEW_PRODUCT/LINE_EXTENSION/REFORMULATION/PACK_SIZE_CHANGE/COST_REDUCTION), Brand, Target Launch Date, Est. COGS/Unit (KES), Description.

---

## BOM & Formula — 4 Tabs

| # | Tab Label | URL Key | Buttons | Dropdowns | Modals |
|---|---|---|---|---|---|
| 1 | BOM / Formula | list | + New BOM | Type (FORMULA/INTERMEDIATE/PACKAGING/MULTILEVEL/PHANTOM/REWORK/COPRODUCT), Status (DRAFT/UNDER_REVIEW/APPROVED/RELEASED/SUPERSEDED/ARCHIVED) | New BOM modal |
| 2 | Substitutes | substitutes | + New Group | — | New Substitute Group modal |
| 3 | Compare | compare | — | — | — |
| 4 | Conversion | conversion | — | — | — |

**New BOM modal fields:** BOM Name*, BOM Type (dropdown), Base Qty, UOM (KG/L/UNIT/MT/G/ML), Version.  
**New Substitute Group modal fields:** group_name, policy (NO_SUB/PLANNER_APPROVAL/QA_APPROVAL/BOTH_REQUIRED/SHORTAGE_ONLY/EMERGENCY_ONLY), notes.

---

## Recipes — 1 Tab

| Tab | Buttons | Dropdowns | Modals/Imports |
|---|---|---|---|
| Recipes | Import Recipes / BOM, + New Recipe | Status (All/DRAFT/APPROVED/OBSOLETE) | New Recipe modal, Import dialog (3 tabs) |

**Import dialog tabs:**
1. Recipe Headers — fields: *product_sku, *version, *name, description, is_active, valid_from, valid_to
2. BOM Items — fields: *product_sku, *version, *line_no, *material_code, *quantity, *unit, loss_percent, optional, alternative_group, notes
3. Process Steps — fields: *product_sku, *version, *step_no, *step_name, temperature_c, target_ph, viscosity_cp, mix_time_min, rpm, notes

**New Recipe modal fields:** Product* (dropdown), Recipe Name*, Version*, Description, Valid From, Valid To.

---

## Quality — 8 Tabs

| # | Tab Label | URL Key | Buttons | Dropdowns | Modals |
|---|---|---|---|---|---|
| 1 | Inspections | inspections | + New Inspection | Type (INCOMING/IN_PROCESS/FINISHED_GOODS), Status (PENDING/IN_PROGRESS/PASSED/FAILED/CONDITIONAL_RELEASE/CANCELLED) | New Inspection modal |
| 2 | Certificates | certificates | + Add Certificate (inline form) | Authority, Status, Entity Type | — |
| 3 | Parameters | parameters | — | — | — |
| 4 | Consumer Complaints | consumer-complaints | — | — | — |
| 5 | Reports | reports | — | — | — |
| 6 | QMS | qms | — | — | — |
| 7 | Allergen | allergen | — | — | — |
| 8 | Brand Assets | brand-assets | — | — | — |

**New Inspection modal fields:** Inspection No*, QC Type*, Inspection Date*, Lot Number, Batch No, Supplier (if INCOMING), Material (if INCOMING), Warehouse, Sample Size, Sample Unit, Notes.

---

## Compliance — 2 Tabs

| Tab | Buttons | Dropdowns | Notes |
|---|---|---|---|
| GS1 & Labels | Run Label Validator, Packaging Optimizer | — | Both buttons trigger AI agent runs |
| Regulatory Certs | + Add Certificate | Status (ACTIVE/PENDING_RENEWAL/EXPIRED/SUSPENDED/REVOKED/PENDING_INITIAL), Entity Type (PRODUCT/PLANT/SUPPLIER/COMPANY) | Authority filter is pill buttons, not dropdown |

---

## Shop Floor — 6 Tabs

| # | Tab Label | URL Key | Buttons |
|---|---|---|---|
| 1 | Overview | overview | Run AI Agents, Operator Terminal (link), Supervisor Console (link) |
| 2 | Terminal | terminal | — |
| 3 | Supervisor | supervisor | — |
| 4 | Queue | queue | — |
| 5 | Downtime | downtime | — |
| 6 | Handover | handover | — |

---

## Selector Strategy

| Item Type | Preferred Selector |
|---|---|
| Tab navigation | URL params — `/dashboard/page?tab=key` |
| Primary action buttons | `getByRole('button', { name })` |
| TestId buttons | `getByTestId('testid')` |
| Text-based buttons | `getByText('text', { exact: false })` |
| Modal trigger then content | Click button → waitFor dialog text |
| Select dropdowns | `page.locator('select:near(:text("label"))')` |
| Import dialog tabs | `getByText('tab label')` after modal open |

---

## Hidden/Off-Screen Tab Handling

All Manufacturing pages use `ModuleWorkspace` which renders tabs via URL params (`?tab=key`). The tab bar may be horizontally scrollable on narrow viewports but all tabs are present in the DOM regardless.

**Capture approach:** Navigate directly to `?tab=key` — no horizontal scrolling needed. The active tab is set via URL, not by clicking a visible tab button. This is confirmed by `WorkspaceTabs.tsx` using `useSearchParams().get("tab")`.

---

## Items Classified as Not Needing Capture

| ID | Reason |
|---|---|
| compliance-gs1-btn-label-validator | Both GS1 buttons are visible in the `compliance-tab-gs1` screenshot header row |
| compliance-gs1-btn-packaging-optimizer | Same — captured in parent screen |

---

## Manifest Total

- **Total manifest items:** 67
- **Items requiring capture:** 64 (3 pre-classified)
- **Required for PDF:** 55
- **Priority 1:** 58
- **Priority 2:** 6
- **Priority 3:** 3
