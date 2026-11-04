# Work Orders & Scheduling

**Route:** `/dashboard/production?tab=orders` (and related tabs)  
**Permission required:** `production.view`

---

## Production orders and work-order operations

**Production-order route:** `/dashboard/production/orders`
**Compatibility route:** `/dashboard/production/work-orders` redirects to the production-order tab.

The production-order page lists and creates top-level `ProductionOrder` records. Its “New Production Order” form captures the order number, product, approved recipe, planned quantity/UOM, target warehouse and schedule. This is the parent manufacturing commitment; the older screenshot description and “New Work Order” wording on this page were incorrect.

A **work order** is an operation under a production order: for example, pre-mixing, pasteurisation, filling or labelling at a routed work center. It carries operation sequence, resource assignment, operation progress and actual time/labor/QC details. It does not replace the parent order or independently post finished goods.

### Current implementation boundary

The ERP currently contains two separate persisted execution families: `production_orders` with routed `work_orders`, and the active `production-execution` module with `exec_production_orders` and `exec_work_orders`. They have no automatic ID crosswalk or synchronization. Do not assume that similarly named or numbered records are the same order. M22 is reconciling these structures through an explicit, non-destructive migration/compatibility plan; no existing rows are claimed migrated or removed. See [M22 responsibility decision](../../../../coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md).

### Key concepts

- A production plan/line is a planning proposal; the production order is the order-level commitment created from it or through the explicit production-order workflow.
- A production order can have multiple routed work-order operations.
- Routing determines operation sequence and work-center assignment; actual work-order time/labor and QC remain attributable to the parent order.
- Order-level material and finished-goods postings, overall status and finalized production cost belong to the parent production order.

---

## Scheduling Tab

**Tab key:** `scheduling`  
**Route:** `/dashboard/production/scheduling`




The current scheduling page lists production-order schedule entries in a table and supports creating or deleting entries. It does not provide a Gantt board or an edit action. These rows schedule a parent production order at a work center and optional shift; they are not routing-step work orders.

For advanced finite-capacity scheduling with AI optimisation, use **Advanced Planning** (`/dashboard/planning`).

---

## Work Centers Tab

**Tab key:** `work-centers`  
**Route:** `/dashboard/production/work-centers/page`

![Production — Work Centers tab](../../../screenshots/captured/module-ui/manufacturing/production/work-centers-tab.png)
*Work Centers tab showing capacity, shifts, and cost rates for each production station.*

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

![Production — Routing tab](../../../screenshots/captured/module-ui/manufacturing/production/routing-tab.png)
*Routing tab defining operation sequences and work center assignments per product.*

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

![Production — Labor tab](../../../screenshots/captured/module-ui/manufacturing/production/labor-tab.png)
*Labor tab showing operator assignments per work order and shift.*

Labour assignments link operators to specific work orders and shifts. This feeds into:
- Labour costing per work order
- Time and attendance reconciliation
- OEE workforce efficiency metrics

---

## Time Tracking Tab

**Tab key:** `time-tracking`  
**Route:** `/dashboard/production/time-tracking/page`

![Production — Time Tracking tab](../../../screenshots/captured/module-ui/manufacturing/production/time-tracking-tab.png)
*Time Tracking tab with operator time entries against work orders.*

Operators log their productive time against work orders. Time tracking data feeds into:
- Labour cost actuals
- Work order completion progress
- Efficiency benchmarks vs. standard routing times

---

## WIP Tab

**Tab key:** `wip`  
**Route:** `/dashboard/production/wip/page`

![Production — WIP tab](../../../screenshots/captured/module-ui/manufacturing/production/wip-tab.png)
*WIP tab showing materials issued to production and unconverted quantities.*

Work-in-Progress (WIP) tracks materials that have been issued to production but not yet converted into finished goods. WIP values are used in:
- Balance sheet inventory valuation
- Production cost control
- Period-end closing

---

## Costing Tab

**Tab key:** `costing`  
**Route:** `/dashboard/production/costing`

![Production — Costing tab](../../../screenshots/captured/module-ui/manufacturing/production/costing-tab.png)
*Costing tab showing the production-order cost breakdown.*

Production-order costing currently aggregates:
- Material costs from issued quantities and material standard cost
- Labour costs from labor logs attached through routed work orders and work-center labor rates
- Machine costs from work-order actual duration and work-center machine rates
- Energy costs from utility transactions matched by the parent batch number

The computed breakdown is finalized on the `ProductionOrder`; work-order labor/time records provide operation-level inputs. Yield-loss variance is reported separately from booked production cost.

---

## Variance Tab

**Tab key:** `variance`  
**Route:** `/dashboard/production/variance/page`

![Production — Variance tab](../../../screenshots/captured/module-ui/manufacturing/production/variance-tab.png)
*Variance tab comparing standard vs. actual cost with material, labour, and overhead breakdown.*

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

![Production — Execution tab](../../../screenshots/captured/module-ui/manufacturing/production/execution-tab.png)
*Execution tab showing real-time work order progress, percentages, and exception alerts.*

Production execution provides a manager-level real-time view of all active work orders, their progress percentages, and exception alerts. It complements the Shop Floor Supervisor console.

---

## Machine Ops Tab

**Tab key:** `machine-ops`  
**Route:** `/dashboard/machine-ops/page`

![Production — Machine Ops tab](../../../screenshots/captured/module-ui/manufacturing/production/machine-ops-tab.png)
*Machine Ops tab with maintenance schedules, checklists, and breakdown reports.*

Machine operations management covers:
- Machine maintenance schedules
- Preventive maintenance checklists
- Breakdown reporting
- Integration with downtime events in OEE

---

## Material Flow Tab

**Tab key:** `material-flow`  
**Route:** `/dashboard/material-flow/page`

![Production — Material Flow tab](../../../screenshots/captured/module-ui/manufacturing/production/material-flow-tab.png)
*Material Flow tab tracking goods issue from warehouse to production and goods receipt back to stock.*

Material flow tracks the movement of materials through the production process:
- Goods Issue (materials from warehouse to production)
- Goods Receipt (finished goods from production to warehouse)
- Transfer orders between production stages

---

## Projects Tab

**Tab key:** `projects`  
**Route:** `/dashboard/projects/page`

![Production — Projects tab](../../../screenshots/captured/module-ui/manufacturing/production/projects-tab.png)
*Projects tab showing production project campaigns with timelines and work order counts.*

Production projects manage multi-work-order production campaigns (e.g. a seasonal promotion requiring co-ordinated runs across multiple lines). Projects group plans and work orders with shared timelines and budgets.
