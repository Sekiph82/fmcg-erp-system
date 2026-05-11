# GAP-002 Posting Integration Audit

## Task

`GAP-002A: Audit current implementation: Accounting-to-Inventory-to-Manufacturing Posting Integration`

This is an audit-only checkpoint. No business logic was changed for GAP-002A.

## Planning Requirement

The ERP needs accounting-to-inventory-to-manufacturing posting integration. In practical terms, operational events should create auditable, idempotent accounting impact:

- supplier goods receipt should update inventory and create GRNI/inventory accounting impact
- supplier invoice should clear GRNI to AP and tax accounts
- material issue to production should move inventory value to WIP
- finished goods receipt should move WIP to finished goods inventory
- production variances, scrap, waste, and adjustments should post to configured variance accounts
- landed cost should update inventory valuation and GL
- inventory adjustments, write-offs, returns, transfers, and cycle counts should be traceable to accounting where relevant
- every posting should be period-aware, permission-protected, idempotent, and reversible by accounting entry rather than direct mutation

## Current Implementation Summary

| Area | Current Status | Evidence | Notes |
|---|---|---|---|
| Inventory stock ledger | Existing | `backend/app/models/inventory.py`, `backend/app/services/inventory_service.py` | `Stock` and `StockMovement` exist. Stock entry/issue/transfer/adjust/delete logic updates balances and movement rows. Missing direct GL posting linkage on stock movements. |
| Procurement GRN posting | Partial | `backend/app/services/procurement_service.py::post_grn` | Posted GRNs create `StockMovement` rows and update `Stock`. GRN lines store `stock_movement_id`. Missing GRNI/inventory/AP/tax GL posting and idempotent accounting batch linkage. |
| Production material issue | Partial | `backend/app/services/production_service.py::_issue_material` | Production consumes material stock and creates material `StockMovement` issue rows. Missing WIP debit / raw material inventory credit GL posting. |
| Finished goods receipt | Partial | `backend/app/services/production_service.py::_receipt_finished_goods` | Production receives finished goods into stock and creates product `StockMovement` receipt rows. Missing finished goods debit / WIP credit GL posting. |
| Production costing | Partial | `backend/app/services/finance_service.py::rollup_production_order_costs`, `ProductionCostEntry`, `ProductCost` | Cost rollups exist for materials and product costs. Missing automatic GL posting from WIP, FG, variance, scrap, and overhead allocations. |
| Landed cost | Partial | `backend/app/services/landed_cost_service.py::post_landed_cost` | Landed cost creates `LCInventoryAdjustment` rows and marks allocations posted. Missing reliable stock value update evidence and GL posting to inventory/clearing/AP accounts. |
| Inventory valuation | Partial | `StockMovement.unit_cost`, `StockMovement.total_cost`, `StockLayer`/FIFO helpers in inventory models/services | Some cost fields and FIFO layer consumption exist. Missing central valuation policy used by all posting events and accounting integration. |
| Accounting posting foundation | Partial / newly improved | `AccountingPostingBatch`, `AccountingPostingRule`, journal helpers from GAP-001 | The new GAP-001 foundation provides idempotent posting-batch structures and journal validation helpers. GAP-002 still needs to connect real operational events to that engine. |
| Period close enforcement | Partial / newly improved | `assert_posting_period_open` in `finance_service.py` | Posting helper exists but inventory/procurement/production event services do not yet call it. |
| Reversals/corrections | Partial | `StockMovement` delete/reversal-ish service logic and GAP-001 journal reversal helper | Inventory delete/reverse logic exists for some flows, but no unified accounting reversal trail for operational postings. |
| Audit linkage | Partial | Movement IDs, GRN line `stock_movement_id`, production consumption/receipt records | Operational records link to movements, but GL journal links are mostly missing. |

## Files Audited

| File | What It Contains |
|---|---|
| `backend/app/models/inventory.py` | `Stock`, `Lot`, `StockMovement`, FIFO/serial layer models and movement metadata. |
| `backend/app/services/inventory_service.py` | Stock entry, issue, transfer, adjustment, delete/reverse, FIFO consumption, summary and detail logic. |
| `backend/app/api/v1/endpoints/inventory.py` | Inventory endpoints that call inventory service functions. |
| `backend/app/models/procurement.py` | Purchase orders, GRNs, GRN lines, supplier payments, import shipment landed cost fields. |
| `backend/app/services/procurement_service.py` | PO workflow and `post_grn` stock receipt logic. |
| `backend/app/api/v1/endpoints/procurement.py` | GRN posting route. |
| `backend/app/models/production.py` | Production order, material consumption, finished goods receipt, downtime models. |
| `backend/app/services/production_service.py` | Production lifecycle, material issue, finished goods receipt, reports. |
| `backend/app/api/v1/endpoints/production.py` | Production order lifecycle endpoints. |
| `backend/app/models/finance.py` | GL, journal lines, accounting posting batches/rules, production cost entries, product costs. |
| `backend/app/services/finance_service.py` | GAP-001 accounting helpers and production cost rollups. |
| `backend/app/models/landed_cost.py` | Landed cost header, lines, allocation lines, inventory adjustments. |
| `backend/app/services/landed_cost_service.py` | Landed cost validation/allocation/posting logic. |
| `backend/app/services/cycle_count_service.py` | Cycle count variance stock adjustment posting logic. |
| `backend/app/services/utility_integration_service.py` | Example cross-module finance/production integration patterns for later reference. |

## Existing Integration Strengths

- Operational stock movements are real rows, not UI-only placeholders.
- GRN posting updates stock and stores a movement ID back on the GRN line.
- Production material issue and finished goods receipt reuse the stock ledger.
- Cost rollup logic already computes production cost entries from material consumption.
- Landed cost has allocation and inventory-adjustment records.
- GAP-001 created the right accounting foundation for idempotent posting batches and posting rules.

## Critical Gaps To Design Next

| Gap | Why It Matters | Suggested Design Direction |
|---|---|---|
| No central operational posting engine | Each operational module mutates stock independently without a shared GL posting contract. | Add service-layer posting functions that accept source module/event/source ID and create idempotent journal entries through `AccountingPostingBatch`. |
| Stock movements lack journal linkage | Inventory cannot be reconciled to GL by movement. | Add nullable `journal_entry_id` and `posting_batch_id` to `stock_movements` or an association table if a movement can generate multiple journals. |
| GRN lacks GRNI accounting | Received-not-invoiced liability is not modeled in GL. | On GRN post: debit raw material/finished goods inventory, credit GRNI/receipts clearing. |
| Supplier invoice does not clear GRNI | AP invoice accounting can drift from received inventory. | On invoice post: debit GRNI and tax recoverable, credit AP. Match invoice lines to GRN/PO lines where available. |
| Material issue lacks WIP posting | Production consumption changes stock but not accounting WIP. | On material consumption: debit WIP, credit raw material inventory using actual layer/standard/weighted cost. |
| Finished goods receipt lacks FG/WIP posting | Finished goods stock increases without accounting completion. | On receipt: debit finished goods inventory, credit WIP. |
| Landed cost lacks GL/inventory valuation integration | Landed cost allocations are not reliably reflected in inventory value and GL. | Post landed cost to inventory value and clearing/AP accounts with allocation line links. |
| Costing policy not centralized | Different flows can use different cost assumptions. | Define valuation policy per item/category: standard, weighted average, FIFO. Use it in inventory and accounting posting. |
| Period close not enforced in operations | Closed accounting periods can still receive operational stock/accounting impact. | Call `assert_posting_period_open` in GRN, production issue/receipt, landed cost, adjustments, and invoice posting. |
| Reversal strategy incomplete | Operational corrections can reverse stock without reversing accounting. | Use journal reversal helper and idempotent reversal batches tied to source documents. |

## Design Constraints For GAP-002B

- Reuse the GAP-001 `AccountingPostingBatch` and `AccountingPostingRule` foundation.
- Do not bypass `StockMovement`; accounting should follow the operational movement ledger.
- Keep operational services responsible for inventory state and finance service responsible for journal creation/validation.
- Do not post directly from frontend.
- Add nullable linkage fields first; backfill and strict constraints can come later.
- Keep idempotency mandatory for every source document event.
- Do not make destructive schema changes to stock, GRN, production, or finance tables.

## Acceptance Criteria Result

`GAP-002A` is complete: current posting integration strengths, missing GL integration points, relevant files, and next schema/service design direction are documented.

No schema, model, service, API, frontend, or seed behavior was changed in this audit step.
