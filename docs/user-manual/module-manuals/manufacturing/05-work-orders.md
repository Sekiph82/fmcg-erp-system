# Work Orders & Scheduling

**Route:** `/dashboard/production?tab=orders` (and related tabs)  
**Permission required:** `production.view`

---

## Work Orders Tab

**Tab key:** `orders`  
**Route:** `/dashboard/production/orders/page`

![Production — Orders tab](../../../screenshots/captured/tabs/production-orders.png)
*Production Orders tab listing work orders with status, plan reference, and target quantities.*

Work orders are the execution units of manufacturing. Each work order references a production plan, a product (or BOM), a target quantity, and a work center. Work orders progress through status stages from DRAFT to COMPLETED.

### Key Concepts

- A work order is always linked to a **Production Plan**. The plan must be `CONFIRMED` before work orders can start.
- Work orders reference a **BOM** (the RELEASED formulation) and a **Routing** (the sequence of operations across work centers).
- Batch and lot numbers are assigned when a work order is released.
- Labour, time tracking, and OEE data are linked at the work order level.

---

## Scheduling Tab

**Tab key:** `scheduling`  
**Route:** `/dashboard/production/scheduling/page`

The scheduling tab provides a visual Gantt-style board for sequencing work orders across work centers and shifts. Use this when you need to manually adjust planned start/end times or resolve conflicts.

For advanced finite-capacity scheduling with AI optimisation, use **Advanced Planning** (`/dashboard/planning`).

---

## Work Centers Tab

**Tab key:** `work-centers`  
**Route:** `/dashboard/production/work-centers/page`

Work centers represent physical production stations (e.g. Blending Line 1, Filling Line 3, Pasteuriser). Each work center has:
- A capacity (units per hour or KG per shift)
- Operating shifts
- A cost rate (used for costing work orders)
- Downtime tracking linkage

Work centers are also managed from the Shop Floor module for real-time status.

---

## Routing Tab

**Tab key:** `routing`  
**Route:** `/dashboard/production/routing/page`

A routing defines the sequence of operations (and the work center for each) required to produce a product. Example routing for a juice product:

| Step | Operation | Work Center |
|------|-----------|-------------|
| 10 | Pre-mixing | Blending Line 1 |
| 20 | Pasteurisation | Pasteuriser A |
| 30 | Filling | Filling Line 2 |
| 40 | Labelling | Labelling Machine 1 |

Routings are linked to products (or BOMs). When a work order is created, the routing determines which work centers are scheduled and in what sequence.

---

## Labor Tab

**Tab key:** `labor`  
**Route:** `/dashboard/production/labor/page`

Labour assignments link operators to specific work orders and shifts. This feeds into:
- Labour costing per work order
- Time and attendance reconciliation
- OEE workforce efficiency metrics

---

## Time Tracking Tab

**Tab key:** `time-tracking`  
**Route:** `/dashboard/production/time-tracking/page`

Operators log their productive time against work orders. Time tracking data feeds into:
- Labour cost actuals
- Work order completion progress
- Efficiency benchmarks vs. standard routing times

---

## WIP Tab

**Tab key:** `wip`  
**Route:** `/dashboard/production/wip/page`

Work-in-Progress (WIP) tracks materials that have been issued to production but not yet converted into finished goods. WIP values are used in:
- Balance sheet inventory valuation
- Production cost control
- Period-end closing

---

## Costing Tab

**Tab key:** `costing`  
**Route:** `/dashboard/production/costing/page`

![Production — Costing tab](../../../screenshots/captured/tabs/production-costing.png)
*Costing tab showing standard vs. actual cost breakdown per work order.*

Production costing aggregates:
- Material costs (actual quantities issued × material cost)
- Labour costs (logged hours × labour rate)
- Overhead absorption (machine hours × overhead rate)

Costing is performed per work order and rolled up to the production plan level.

---

## Variance Tab

**Tab key:** `variance`  
**Route:** `/dashboard/production/variance/page`

Variance analysis compares:
- Standard cost (from BOM + Routing) vs. Actual cost (from work order)
- Material usage variance
- Labour efficiency variance
- Overhead absorption variance

Significant variances are flagged for investigation.

---

## Execution Tab

**Tab key:** `execution`  
**Route:** `/dashboard/production-execution/page`

![Production — Execution tab](../../../screenshots/captured/tabs/production-execution.png)
*Execution tab showing real-time work order progress, percentages, and exception alerts.*

Production execution provides a manager-level real-time view of all active work orders, their progress percentages, and exception alerts. It complements the Shop Floor Supervisor console.

---

## Machine Ops Tab

**Tab key:** `machine-ops`  
**Route:** `/dashboard/machine-ops/page`

Machine operations management covers:
- Machine maintenance schedules
- Preventive maintenance checklists
- Breakdown reporting
- Integration with downtime events in OEE

---

## Material Flow Tab

**Tab key:** `material-flow`  
**Route:** `/dashboard/material-flow/page`

![Production — Material Flow tab](../../../screenshots/captured/tabs/production-material-flow.png)
*Material Flow tab tracking goods issue from warehouse to production and goods receipt back to stock.*

Material flow tracks the movement of materials through the production process:
- Goods Issue (materials from warehouse to production)
- Goods Receipt (finished goods from production to warehouse)
- Transfer orders between production stages

---

## Projects Tab

**Tab key:** `projects`  
**Route:** `/dashboard/projects/page`

Production projects manage multi-work-order production campaigns (e.g. a seasonal promotion requiring co-ordinated runs across multiple lines). Projects group plans and work orders with shared timelines and budgets.
