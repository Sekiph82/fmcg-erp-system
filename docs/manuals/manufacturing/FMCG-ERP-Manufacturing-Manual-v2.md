# FMCG ERP — Manufacturing Module Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Production Managers, Quality Officers, Planning Managers, Shop Floor Supervisors, NPD Teams  
**Modules Covered:** Recipes · BOM & Formula · Production · Planning · Shop Floor · NPD · Quality · Compliance

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Recipes](#2-recipes)
3. [Recipe Bulk Import](#3-recipe-bulk-import)
4. [BOM & Formula](#4-bom--formula)
5. [Production](#5-production)
6. [Advanced Planning & MRP](#6-advanced-planning--mrp)
7. [Shop Floor Operations](#7-shop-floor-operations)
8. [New Product Development (NPD)](#8-new-product-development-npd)
9. [Quality Control](#9-quality-control)
10. [Compliance & Labelling](#10-compliance--labelling)
11. [Common Mistakes & Troubleshooting](#11-common-mistakes--troubleshooting)
12. [Related Modules](#12-related-modules)

---

## 1. Module Overview

**What it does:** The Manufacturing module manages the full production lifecycle — from product formulation through to shop floor execution, quality control, and regulatory compliance.

**Who uses it:**
- Production Manager — creates production plans and work orders
- Quality Officer — logs inspections, manages certificates and complaints
- Planning Manager — runs MRP/MPS and capacity planning
- Shop Floor Supervisor — monitors execution, records downtime and handovers
- NPD Manager — manages new product development stage-gates

**When to use it:**
- When setting up a new product formulation (Recipes → BOM)
- When planning a production run (Production Plans → Work Orders)
- When executing a production order on the factory floor (Shop Floor)
- When performing quality checks on finished goods or in-process batches
- When tracking OEE, downtime, and yield

**Modules at a glance:**

| Module | Route | Purpose |
|--------|-------|---------|
| Recipes | `/dashboard/recipes` | Formulation management |
| BOM | `/dashboard/bom` | Bill of materials and formula |
| Production | `/dashboard/production` | Plans, orders, scheduling, OEE |
| Planning | `/dashboard/planning` | MRP, MPS, capacity scheduling |
| Shop Floor | `/dashboard/shop-floor` | Real-time terminal and supervisor |
| NPD | `/dashboard/npd` | New product stage-gate |
| Quality | `/dashboard/quality` | QC, certificates, complaints |
| Compliance | `/dashboard/compliance` | GS1 labels, regulatory certs |

![Manufacturing Production Overview](../../user-manual/screenshots/captured/038_production.png)
*Production module main view.*

---

## 2. Recipes

**Route:** `/dashboard/recipes`  
**Required permission:** `recipe.view`

### What it does
Manages product formulations — the ingredients (BOM items) and process parameters (temperature, pH, mixing time) for each product version. A recipe must be **Approved** before it can be used in production.

![Recipes List](../../user-manual/screenshots/captured/module-ui/manufacturing/recipes/recipes-tab.png)
*Recipes list page with search, status filter, Import, and New Recipe buttons.*

### Tabs and Sections

The Recipes page is a single list (no workspace tabs). Each recipe row links to a detail page.

### Every Button Explained

| Button | Where | What it does |
|--------|-------|--------------|
| **+ New Recipe** | Top right | Opens New Recipe modal |
| **Import Recipes / BOM** | Top right | Opens 3-tab CSV import modal |
| **Delete** (trash icon) | Row action | Deletes DRAFT recipe only |

### Search and Filters

- **Search bar** — filters live across: recipe name, product SKU, product name, version number
- **Status filter** — filter by DRAFT / APPROVED / OBSOLETE

### Status Values

| Status | Meaning |
|--------|---------|
| DRAFT | Under development; editable and deletable |
| APPROVED | Approved for production; no edits allowed |
| OBSOLETE | Retired; no longer active |

Status flow: `DRAFT → APPROVED → OBSOLETE` (no reverse)

### Creating a Recipe

1. Click **+ New Recipe**
2. Fill in the modal:

| Field | Required | Notes |
|-------|----------|-------|
| Product | Yes | Select from products master |
| Recipe Name | Yes | Free text |
| Version | Yes | Default "1.0" |
| Description | No | Not shown in list |
| Valid From / Valid To | No | Validity window |

3. Click **Create** — recipe created as DRAFT

![New Recipe Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/recipes/new-recipe-modal.png)
*New Recipe modal. Product, Name, and Version are required.*

### Recipe Detail Page

**Route:** `/dashboard/recipes/{recipe_id}`

Two sub-sections on detail page:

**BOM Items (Ingredients)**

| Field | Description |
|-------|-------------|
| Material | Link to materials master |
| Line No | Ordering sequence (must be unique) |
| Quantity | Amount per batch |
| Unit | KG, L, G, ML, etc. |
| Loss % | Expected process loss (default 0) |
| Optional | Marks non-mandatory ingredients |
| Alt Group | Groups substitutable items |
| Notes | Free text per line |

**Process Parameters (Steps)**

| Field | Description |
|-------|-------------|
| Step No | Sequence (must be unique) |
| Step Name | e.g. Blending, Pasteurisation |
| Temp (°C) | Target process temperature |
| pH | Target pH value |
| Viscosity (cP) | Target viscosity |
| Mix Time (min) | Mixing duration |
| RPM | Agitator speed |
| Notes | Free text |

> **DRAFT-only rule:** BOM items and process parameters can only be added/edited/deleted while status is DRAFT.

### Required Data Before Starting
- Products must exist in the Products master
- Materials must exist in the Materials master
- At minimum one BOM item needed before recipe can be approved

### What Happens After Save
- Recipe created as DRAFT — visible in list
- Detail page opens automatically
- Add BOM items and process parameters before approving

### Common Mistakes
- Trying to edit an APPROVED recipe → blocked by API (HTTP 422)
- Forgetting to set version (defaults to "1.0" — acceptable but not distinguishable from other v1 recipes)
- Deleting an APPROVED recipe → delete button not shown for APPROVED/OBSOLETE

---

## 3. Recipe Bulk Import

**Button:** Import Recipes / BOM on the Recipes page

### When to Use
When migrating recipes from Excel or another system. Faster than creating one by one.

### Import Modal — 3 Tabs

![Import Modal — Headers](../../user-manual/screenshots/captured/module-ui/manufacturing/recipes/import-modal-headers-tab.png)
*Tab 1: Recipe Headers. Upload the CSV with one row per recipe.*

![Import Modal — BOM Items](../../user-manual/screenshots/captured/module-ui/manufacturing/recipes/import-modal-bom-items-tab.png)
*Tab 2: BOM Items. Upload BOM lines keyed by recipe name or ID.*

![Import Modal — Process Steps](../../user-manual/screenshots/captured/module-ui/manufacturing/recipes/import-modal-process-steps-tab.png)
*Tab 3: Process Steps. Upload process parameter rows.*

### Import Steps (in order)

1. **Tab 1 — Recipe Headers:** Upload CSV with columns: `name, product_sku, version, description, valid_from, valid_to`
2. **Tab 2 — BOM Items:** Upload CSV with columns: `recipe_name, material_code, line_no, quantity, unit, loss_percentage, is_optional, alternative_group, notes`
3. **Tab 3 — Process Steps:** Upload CSV with columns: `recipe_name, step_no, step_name, target_temperature, target_ph, target_viscosity, mixing_time_minutes, rpm, notes`

> **Order matters:** Import headers first. BOM and process steps reference recipe names created in Tab 1.

### Validation Rules
- All referenced products (by SKU) must exist in the system
- All referenced materials (by code) must exist in the system
- Duplicate recipe name + version combinations are rejected
- Numeric fields (quantity, temperature, pH) must be valid numbers

### What Happens After Import
- New recipes created as DRAFT
- Validation errors shown inline per row
- Successful rows imported; failed rows shown with error message

---

## 4. BOM & Formula

**Route:** `/dashboard/bom`  
**Required permission:** `bom.view`

### What it does
Manages Bills of Materials — the formal list of components required to produce a finished good. BOM is the production-facing view; Recipe is the formulation-facing view.

### Tabs

![BOM List](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/bom-list-tab.png)
*BOM List tab showing all BOMs with product, version, and status columns.*

| Tab | Purpose |
|-----|---------|
| BOM List | All BOMs, searchable and filterable |
| Substitutes | Substitute groups and alternative components |
| Compare | Side-by-side BOM version comparison |
| Conversion | Unit conversion factors |

### Creating a BOM

Click **+ New BOM** (requires `bom.create`).

![New BOM Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/new-bom-modal.png)
*New BOM modal with product, version, and effective date fields.*

| Field | Required | Notes |
|-------|----------|-------|
| Product | Yes | Select from products |
| BOM Type | Yes | Manufacturing / Kit / Service |
| Version | Yes | e.g. "1.0" |
| Effective Date | No | Date from which BOM is active |

### BOM Substitutes Tab

![Substitutes Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/substitutes-tab.png)
*Substitute Groups — define alternative materials that can replace a primary component.*

Click **+ New Substitute Group** to create a group:

![New Substitute Group Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/new-substitute-group-modal.png)

### BOM Compare Tab

![BOM Compare](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/compare-tab.png)
*Side-by-side comparison of two BOM versions. Highlights additions, removals, and quantity changes.*

Select two BOMs from the dropdowns and click **Compare**.

### BOM Conversion Tab

![Conversion Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/bom/conversion-tab.png)
*Unit conversion factors used when BOM quantities differ from inventory units.*

### Common Mistakes
- Creating BOM before the product exists in the system
- Leaving version blank (causes duplicate-detection failures)
- Not setting Effective Date when multiple BOM versions exist for same product

---

## 5. Production

**Route:** `/dashboard/production`  
**Required permission:** `production.view`

### What it does
Central hub for production execution: create plans, raise work orders, schedule operations, track OEE, record costing and variance.

### Tabs (20 total)

![Production Overview](../../user-manual/screenshots/captured/038_production.png)

| Tab | Purpose |
|-----|---------|
| Plans | Production plans (multi-order groupings) |
| Work Orders | Individual production orders |
| Scheduling | Gantt-style scheduling and sequencing |
| Work Centers | Machine and labor centers configuration |
| Routing | Operation sequences per product |
| Batch/Lots | Batch tracking and lot numbers |
| QC | In-process quality checks |
| Labor | Labor entries and time allocation |
| Time Tracking | Clock-in/out and operation time |
| OEE | Overall Equipment Effectiveness dashboard |
| Downtime | Downtime event log |
| Waste/Yield | Scrap, waste, and yield recording |
| WIP | Work-in-process inventory |
| Costing | Actual vs. standard cost per order |
| Variance | Cost and yield variance reports |
| Reports | Production summary reports |
| Execution | Real-time execution status |
| Machine Ops | Machine operation parameters |
| Material Flow | Material consumption vs. plan |
| Projects | Production project groupings |

### Production Plans Tab

![Plans Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/plans-tab.png)
*Plans tab with plan list, status filter, and New Plan button.*

**Creating a Plan:**
1. Click **+ New Plan**
2. Fill modal:

![New Plan Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/production/new-plan-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Plan Name | Yes | Free text |
| Start Date | Yes | Planned start |
| End Date | Yes | Planned completion |
| Product | No | Filter for product-specific plan |
| Notes | No | Free text |

3. Plan created as DRAFT — add work orders from the Work Orders tab referencing this plan

**Plan Status Flow:** `DRAFT → CONFIRMED → IN_PROGRESS → COMPLETED`

### Work Orders Tab

![Work Orders Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/work-orders-tab.png)
*Work Orders tab showing all orders with status, product, quantity, and scheduled dates.*

**Creating a Work Order:**
1. Click **+ New Work Order**

![New Work Order Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/production/new-work-order-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Product | Yes | Finished good to produce |
| Quantity | Yes | Planned quantity |
| Unit | Yes | UOM |
| BOM | Yes | Select approved BOM version |
| Recipe | No | Link to recipe for process params |
| Work Center | No | Primary work center |
| Planned Start | Yes | Scheduled start date/time |
| Planned End | Yes | Scheduled end date/time |
| Production Plan | No | Parent plan reference |

**Work Order Status Flow:** `DRAFT → CONFIRMED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED`

### Scheduling Tab

![Scheduling Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/scheduling-tab.png)
*Gantt chart view of all work orders by work center and date.*

Drag-and-drop rescheduling. Click any bar to open work order detail.

### OEE Tab

![OEE Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/oee-tab.png)
*OEE dashboard showing Availability, Performance, Quality KPIs and trend charts.*

OEE = Availability × Performance × Quality

| KPI | Calculation |
|-----|-------------|
| Availability | (Planned - Downtime) / Planned |
| Performance | Actual Output / Theoretical Max Output |
| Quality | Good Units / Total Units Produced |

### Downtime Tab

![Downtime Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/downtime-tab.png)
*Downtime log with machine, category, duration, and reason columns.*

Log downtime events: select machine, category (Mechanical, Electrical, Changeover, Break, etc.), start/end time, root cause notes.

### Waste/Yield Tab

![Waste/Yield Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/waste-yield-tab.png)
*Waste and yield recording per work order and material.*

Record actual yield vs. planned yield. Waste entries create inventory adjustments automatically.

### Costing Tab

![Costing Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/production/costing-tab.png)
*Actual vs. standard cost breakdown by material, labor, and overhead.*

### Required Data Before Starting Production
- Products and materials in master data
- Approved BOM version for each product
- Work centers configured
- Routing defined (optional but needed for scheduling)

### What Happens After Completing a Work Order
- Finished goods inventory increases by produced quantity
- Material consumption reduces raw material inventory
- Costing records are created (actual vs. standard)
- Batch/lot numbers assigned if batch tracking enabled

---

## 6. Advanced Planning & MRP

**Route:** `/dashboard/planning`  
**Required permission:** `planning.view`

### What it does
Finite capacity scheduling, Material Requirements Planning (MRP), Master Production Scheduling (MPS), and what-if scenario simulation.

### Tabs

| Tab | Purpose |
|-----|---------|
| Dashboard | Planning KPI summary |
| Schedule | Finite capacity schedule |
| Capacity | Work center capacity profiles |
| Simulation | What-if scenario planning |
| Bottlenecks | Bottleneck identification |
| Changeover | Changeover time matrix |
| MRP | Material requirements planning run |
| MPS | Master production schedule |
| Kanban | Kanban card management |

![Planning Dashboard](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/dashboard-tab.png)
*Planning module dashboard with KPI cards and schedule overview.*

### MRP Tab

![MRP Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/mrp-tab.png)
*MRP run results — shows recommended purchase orders and production orders per material.*

**Running MRP:**
1. Go to Planning → MRP tab
2. Set horizon (default 30 days)
3. Click **Run MRP**
4. Review recommendations — approve to convert to purchase requisitions or work orders

### MPS Tab

![MPS Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/mps-tab.png)
*MPS showing demand vs. supply balance per period.*

### Capacity Tab

![Capacity Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/capacity-tab.png)
*Work center capacity — planned load vs. available capacity by period.*

### Simulation Tab

![Simulation Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/simulation-tab.png)
*Create what-if scenarios to test schedule changes without affecting live data.*

Click **+ New Scenario** to create a simulation:

![New Scenario Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/new-scenario-modal.png)

Scenarios are sandbox copies — changes here do not affect production plans until promoted.

### Schedule Tab

![Schedule Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/schedule-tab.png)
*Finite capacity schedule — operations sequenced across work centers.*

### Bottlenecks Tab

![Bottlenecks Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/bottlenecks-tab.png)
*Identifies over-loaded work centers and suggests rebalancing.*

### Changeover Tab

![Changeover Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/changeover-tab.png)
*Changeover time matrix — time to switch between product families on each work center.*

### Kanban Tab

![Kanban Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/planning/kanban-tab.png)
*Kanban board view of production work orders by stage.*

---

## 7. Shop Floor Operations

**Route:** `/dashboard/shop-floor`  
**Required permission:** `production.view`

### What it does
Real-time shop floor management — operator terminal, supervisor console, work queue, downtime logging, and shift handover.

### Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Summary dashboard of all active work orders |
| Terminal | Operator clock-in/out and work execution |
| Supervisor | Supervisor override and monitoring console |
| Queue | Work order queue by work center |
| Downtime | Shop-floor downtime log |
| Handover | Shift handover notes |

![Shop Floor Overview](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/overview-tab.png)
*Shop Floor overview — active orders by status and work center.*

### Terminal Tab

![Terminal Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/terminal-tab.png)
*Operator terminal — scan/select work order, start/pause/complete operations.*

**Operator workflow:**
1. Select or scan work order barcode
2. Click **Start** to begin operation
3. Record quantities at checkpoints
4. Click **Pause** to suspend (auto-creates time entry)
5. Click **Complete** when operation finished

### Supervisor Tab

![Supervisor Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/supervisor-tab.png)
*Supervisor console — override decisions, approve exceptions, view operator activity.*

### Queue Tab

![Queue Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/queue-tab.png)
*Work order queue per work center — prioritized list of pending operations.*

### Downtime Tab (Shop Floor)

![Shop Floor Downtime](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/downtime-tab.png)
*Log downtime events directly from shop floor with machine and reason code.*

### Handover Tab

![Handover Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/shop-floor/handover-tab.png)
*Shift handover — outgoing supervisor records open issues, pending tasks, and notes for incoming shift.*

**Handover workflow:**
1. Open Handover tab at end of shift
2. System auto-populates open work orders and unresolved downtimes
3. Supervisor adds freetext notes
4. Click **Submit Handover** — creates timestamped record
5. Incoming shift supervisor reviews and acknowledges

---

## 8. New Product Development (NPD)

**Route:** `/dashboard/npd`  
**Required permission:** `npd.view`

### What it does
Manages the new product development pipeline using a stage-gate model. From initial concept through trials and commercial launch.

### Tabs

![NPD New Products Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/npd/new-products-tab.png)
*NPD project list with stage, owner, and target launch date.*

### Creating an NPD Project

Click **+ New Project**:

![NPD New Project Form](../../user-manual/screenshots/captured/module-ui/manufacturing/npd/new-project-form.png)
*New NPD project form with project name, product category, owner, target dates, and stage gate.*

| Field | Required | Notes |
|-------|----------|-------|
| Project Name | Yes | Descriptive name |
| Product Category | Yes | Select from categories |
| Project Owner | Yes | Responsible manager |
| Target Launch Date | Yes | Commercial target date |
| Current Stage | Yes | Concept / Development / Trials / Launch |
| Budget | No | Estimated development budget |
| Description | No | Free text |

### Stage Gate Stages

| Stage | Meaning |
|-------|---------|
| Concept | Initial idea and feasibility |
| Development | Recipe development and lab trials |
| Trials | Pilot production and consumer testing |
| Launch | Commercial production approved |
| On Hold | Paused |
| Cancelled | Discontinued |

### What Happens After Creating a Project
- Project appears in NPD list with CONCEPT stage
- Team members can be assigned
- Linked to Recipe (when trial recipe created) and BOM
- Stage advances when gate criteria met and approved

---

## 9. Quality Control

**Route:** `/dashboard/quality`  
**Required permission:** `quality.view`

### What it does
Manages QC inspections, quality certificates, allergen declarations, consumer complaints, quality parameters, QMS documents, and brand assets.

### Tabs

| Tab | Purpose |
|-----|---------|
| Inspections | QC inspection records |
| Certificates | Quality certificates per product/batch |
| Parameters | Quality test parameters configuration |
| Consumer Complaints | Customer complaint log and tracking |
| Reports | QC summary and trend reports |
| QMS | Quality management system documents |
| Allergen | Allergen declaration matrix |
| Brand Assets | Brand standards and packaging |

![Quality Inspections Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/inspections-tab.png)
*Inspections list with type, product, batch, result, and status columns.*

### Creating an Inspection

Click **+ New Inspection**:

![New Inspection Modal](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/new-inspection-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Inspection Type | Yes | Incoming / In-Process / Final / Outgoing |
| Product | Yes | Product being inspected |
| Batch/Lot | No | Link to batch if applicable |
| Work Order | No | Link to production work order |
| Inspector | Yes | User performing inspection |
| Scheduled Date | Yes | Planned inspection date |

After creation, add test results against the configured parameters.

### Inspection Results — Decision

| Decision | Meaning |
|----------|---------|
| PASS | Product meets all specifications |
| FAIL | Product outside specification — triggers NCMR |
| CONDITIONAL | Passes with deviations noted |
| PENDING | Results not yet complete |

### Certificates Tab

![Certificates Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/certificates-tab.png)
*Quality certificates — COA (Certificates of Analysis) per product and batch.*

### Parameters Tab

![Parameters Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/parameters-tab.png)
*Quality test parameters — define specs (min/max/target) for each product-test combination.*

### Consumer Complaints Tab

![Consumer Complaints Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/consumer-complaints-tab.png)
*Consumer complaint register — log, categorize, investigate, and close complaints.*

### Allergen Tab

![Allergen Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/allergen-tab.png)
*Allergen matrix — cross-reference products with allergen presence and contamination risk.*

### QMS Tab

![QMS Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/qms-tab.png)
*QMS document library — SOPs, work instructions, and quality procedures.*

### Reports Tab

![Quality Reports Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/quality/reports-tab.png)
*QC trend charts and summary statistics by product, line, and period.*

---

## 10. Compliance & Labelling

**Route:** `/dashboard/compliance`  
**Required permission:** `gs1.view`

### What it does
Manages GS1 barcode label generation and regulatory certificate tracking for export and local market compliance.

### Tabs

| Tab | Purpose |
|-----|---------|
| GS1 Labels | Generate and print GS1-compliant barcodes |
| Regulatory Certs | Track regulatory permits and certificates |

### GS1 Labels Tab

![GS1 Labels Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/compliance/gs1-labels-tab.png)
*GS1 label generation — select product, batch, and label template to generate barcodes.*

### Regulatory Certs Tab

![Regulatory Certs Tab](../../user-manual/screenshots/captured/module-ui/manufacturing/compliance/regulatory-certs-tab.png)
*Regulatory certificates register — status, expiry tracking, and renewal alerts.*

**Status filter:**

![Status Dropdown](../../user-manual/screenshots/captured/module-ui/manufacturing/compliance/regulatory-certs-status-dropdown.png)
*Filter by: Active / Expired / Expiring Soon / Pending*

**Entity type filter:**

![Entity Type Dropdown](../../user-manual/screenshots/captured/module-ui/manufacturing/compliance/regulatory-certs-entity-type-dropdown.png)
*Filter by entity: Product / Facility / Ingredient / Process*

### Adding a Certificate

![Add Certificate Form](../../user-manual/screenshots/captured/module-ui/manufacturing/compliance/add-certificate-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Certificate Name | Yes | e.g. "KEBS Approval — Tomato Sauce" |
| Issuing Authority | Yes | e.g. KEBS, KEPHIS, HISA |
| Entity Type | Yes | Product / Facility / Ingredient |
| Reference No | Yes | Official certificate/permit number |
| Issue Date | Yes | Date issued |
| Expiry Date | Yes | Renewal required before this date |
| Status | Yes | Active / Expired / Pending |
| Product / Facility | No | Link to relevant entity |
| Document | No | Upload PDF/scan of certificate |

### Expiry Alerts
System flags certificates expiring within 90 days in the KPI strip at top of Regulatory Certs tab.

---

## 11. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Can't edit recipe | Status is APPROVED | Create new version as DRAFT; cannot reverse APPROVED |
| Work order won't confirm | No approved BOM linked | Approve BOM first; then link to work order |
| MRP recommends nothing | Demand horizon too short or no open sales orders | Extend horizon; check sales order backlog |
| OEE shows 0% | No work orders in COMPLETED status | Complete work orders; ensure times entered |
| QC inspection missing parameters | No parameters configured for this product | Add parameters in Quality → Parameters tab |
| Shop Floor terminal shows empty queue | Work orders not RELEASED | Release work orders from Production → Work Orders tab |
| Regulatory cert not showing | Certificate expired filter active | Clear status filter or update status to Active |

---

## 12. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Recipe → production use | Production → Work Orders (BOM + Recipe linked) |
| Work Order completion | Inventory → Stock (FG increase + RM consumption) |
| MRP recommendations | Procurement → Purchase Requisitions |
| QC Fail → NCMR | Quality → Consumer Complaints or Inventory → Quarantine |
| NPD to commercial | Recipes → BOM → Production Plan |
| Allergen declarations | Compliance → Regulatory Certs (certificate links to allergen certs) |
| Batch tracking | Inventory → Traceability and Serials modules |

---

*End of Manufacturing Manual v2*
