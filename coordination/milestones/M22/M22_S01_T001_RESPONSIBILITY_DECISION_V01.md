# M22.S01.T001 — Production-order and work-order responsibilities

**Decision type:** target domain boundary for M22 follow-up work
**State:** bounded architecture decision; reconciliation/migration is not complete
**Evidence reviewed:** root `TASKS.md`; `backend/app/models/production.py`; `backend/app/models/production_advanced.py`; `backend/app/models/production_execution.py`; production, production-advanced and production-execution services/routes; manufacturing work-order manual; independent read-only model/consumer review.

## Current model map

| Concept | Current storage and links | Current responsibility/evidence |
|---|---|---|
| Production planning | `production_plans`, `production_plan_lines` | Demand/capacity proposal and its product/quantity/date lines. A plan is not itself an execution operation. |
| Business production order | `ProductionOrder` → `production_orders` | Order number, optional plan-line link, product/recipe, planned/actual quantity and UOM, batch, order status, warehouses, schedule/actual dates and finalized order cost. Material consumption, finished-goods receipt, downtime, finance, quality, MRP/MPS and reporting code already references this table. |
| Routed operation | advanced `WorkOrder` → `work_orders` | Required FK to `production_orders` with `RESTRICT`, routing step, work center, operation, operation quantities/status/times, plus time and labor records. This is structurally a child operation. |
| Parallel execution aggregate | `ProdExecOrder` → `exec_production_orders` | Separate order number and UUID, optional product/BOM/routing, planned/completed/scrap/rework quantities, batch, independent status/cost, split/rework genealogy. It has no FK to `production_orders`. Its API/service and shop-floor consumers are active. |
| Parallel execution operation | `ExecWorkOrder` → `exec_work_orders` | Child of `exec_production_orders`, with sequence, resources, actual quantities/times, dependencies, QC and scrap fields. Materials, genealogy, split/merge, AI recommendation and shop-floor records also reference the parallel aggregate. |

The production manual and UI currently use “work order” inconsistently: the standard production-order screen creates a `ProductionOrder`, while the production-execution screen operates on the distinct `exec_*` aggregate. The current `production/work-orders` page redirects to the order tab. These routes and persisted records are not automatically cross-linked.

## Target responsibility boundary

1. **`ProductionOrder` is the designated canonical business/order-of-record target.** It owns the committed product and production-definition reference, planned quantity/UOM, source and target locations, schedule envelope, overall lifecycle, order-level material/finished-goods postings and finalized cost. Today that definition is represented by `recipe_id`; a canonical BOM/version binding is a schema follow-up and must not be assumed to exist. It is the cross-module identity that MRP/MPS, inventory, finance, quality and reporting must resolve.
2. **A canonical `WorkOrder` is one executable routing operation under a `ProductionOrder`.** It owns operation sequence, work center/resource assignment, operation status, actual operation quantities/times, labor/time and operation-level QC. One parent can have multiple operations. A child operation cannot independently create a production commitment, release the parent, post finished goods, or finalize order costing.
3. **Planning remains separate.** A production plan/line proposes dated quantity and capacity. Creation/release of a production order is an explicit lifecycle transition; plan rows and work-order rows are not substitutes for that order.
4. **Execution facts remain attributable.** Material issues/returns, waste, QC, downtime, labor, batch/genealogy and cost entries must retain a stable relationship to the canonical order and, where operation-specific, its work order. Parent totals and child actuals must reconcile transactionally before completion/close.

## Reconciliation policy for the active parallel subsystem

`exec_production_orders` and `exec_work_orders` are **active parallel models**, not safe-to-drop legacy tables. This task does not rename or remove them and does not claim that their existing rows have been migrated. Until a later M22 migration/adapter establishes identity:

- Do not dual-write the same production event into both model families.
- Do not infer equivalence by matching `order_no`, batch text, product or timestamps; the UUIDs and existing dependent records have no FK bridge.
- Do not delete, merge or silently relink existing execution, material, genealogy, AI, split/merge, shop-floor or audit records.
- Later migration work must provide an explicit, auditable crosswalk for order and operation IDs, reconcile every dependent row, preserve stable API/history identifiers, and report ambiguous/unmatched records for explicit resolution. Expand/backfill/validate before switching reads/writes; contract/drop only after verified zero remaining consumers and rollback evidence.
- Existing execution routes remain an explicitly separate compatibility surface until those gates pass; no claim of unified current behavior is made.

## Follow-up acceptance implications

- M22.S01.T002 should harden one parent-order state machine and define how operation transitions are gated by it; duplicate routes must not bypass those guards.
- M22.S01.T003 should put release/approval/cancel/close authority on the parent and preserve actor/permission checks. Operation completion is not approval of the order.
- M22.S01.T004 should make order and operation transition history append-only and attributable.
- M22.S02 work must preserve partial quantities, batch identity, split/merge/rework genealogy and all dependent records through the explicit crosswalk; no “one row equals one order” assumption may erase them.

This is a target design for the virtual ERP implementation, not a live factory policy or completed data migration. It uses the existing schema relationships as evidence and requires no real factory, employee or owner data.
