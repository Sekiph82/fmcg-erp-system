# Manufacturing Module — Overview

**Manual:** FMCG ERP Manufacturing Module Manual  
**Audience:** Production Managers, Quality Officers, Planning Managers, Shop Floor Supervisors, NPD Teams  
**Scope:** All manufacturing-related screens, workflows, and import formats

---

## What This Module Covers

The Manufacturing module in the FMCG ERP spans eight linked subsystems:

| Subsystem | Route | Purpose |
|-----------|-------|---------|
| Recipes | `/dashboard/recipes` | Formulation management — ingredients, process parameters, lifecycle |
| BOM & Formula | `/dashboard/bom` | Bill of materials, formula versions, cost explosion |
| Production | `/dashboard/production` | Plans, work orders, scheduling, OEE, costing |
| Advanced Planning | `/dashboard/planning` | Finite capacity scheduling, MRP, MPS, Kanban |
| Shop Floor | `/dashboard/shop-floor` | Real-time terminal, supervisor console, downtime, handover |
| NPD | `/dashboard/npd` | New product development stage-gate pipeline |
| Quality | `/dashboard/quality` | QC inspections, certificates, allergen, complaints |
| Compliance | `/dashboard/compliance` | GS1 labels, barcodes, regulatory certificates |

---

## Navigation

Access Manufacturing modules via the left sidebar under the **Production** and **Quality** clusters. All modules require authentication. Tab-level access is controlled by permissions (see below).

Quick navigation paths:
- New Recipe: **Sidebar → Recipes → New Recipe**
- Production Plan: **Sidebar → Production → Plans tab → New Plan**
- QC Inspection: **Sidebar → Quality → Inspections tab → New Inspection**
- Shop Floor: **Sidebar → Shop Floor → Terminal tab**
- NPD Project: **Sidebar → NPD → New Project**

---

## Permission Map

| Permission | Grants Access To |
|------------|-----------------|
| `recipe.view` | Recipe list and detail pages |
| `recipe.create` | Create new recipes |
| `recipe.delete` | Delete DRAFT recipes |
| `bom.view` | BOM list and detail pages |
| `bom.create` | Create new BOMs |
| `production.view` | All production tabs (plans, orders, scheduling, OEE, etc.) |
| `planning.view` | All planning tabs (scenarios, schedule, MRP, MPS, etc.) |
| `npd.view` | NPD project list |
| `npd.create` | Create new NPD projects |
| `quality.view` | QC inspection list and detail |
| `gs1.view` | Compliance → GS1 & Labels tab |

Users see only the tabs and buttons their permissions allow. Missing permissions show a "No access" message rather than an error.

---

## Chapters in This Manual

1. [Recipes](./01-recipes.md) — Header, BOM items, process parameters, status workflow
2. [Recipe Bulk Import](./02-recipes-import.md) — CSV format, 3-tab import, validation
3. [BOM & Formula](./03-bom-formula.md) — BOM types, lifecycle, formula editing
4. [Production Plans](./04-production-plans.md) — Plan creation, status, confirmation
5. [Work Orders & Scheduling](./05-work-orders.md) — Orders, scheduling, work centers, routing
6. [Batch & Lots](./06-batch-lots.md) — Batch tracking, lot numbers, traceability
7. [QC Inspections](./07-quality-control.md) — Inspection types, test results, decisions
8. [Shop Floor Operations](./08-shop-floor.md) — Terminal, supervisor, queue, downtime, handover
9. [Advanced Planning & MRP](./09-planning-scheduling.md) — Scenarios, capacity, MRP, MPS
10. [New Product Development](./10-npd.md) — Stage-gate pipeline, project management
11. [OEE, Downtime & Yield](./11-oee-reporting.md) — OEE KPIs, downtime categories, waste
12. [Compliance & Labelling](./12-compliance.md) — GS1, barcodes, regulatory certificates
