# GAP-002 Posting Integration Schema Design

## Task

`GAP-002B: Design data model/schema: Accounting-to-Inventory-to-Manufacturing Posting Integration`

This is a design-only checkpoint. It does not change database schema, ORM models, services, API behavior, or frontend behavior. The next task, `GAP-002C`, should turn the accepted design into an additive Alembic migration.

## Design Goals

The current repo already has real operational ledgers:

- `StockMovement` for inventory movement
- `GoodsReceipt` and `GRNLine` for procurement receipts
- `MaterialConsumption` and `FinishedGoodsReceipt` for production execution
- `ProductionCostEntry` and `ProductCost` for costing rollups
- `LandedCostHeader`, allocation lines, and inventory adjustments
- GAP-001 `AccountingPostingBatch` and `AccountingPostingRule`

GAP-002 should connect those operational events to accounting without replacing the operational services.

The design should:

- add traceable links from operational events to accounting posting batches and journals
- keep posting idempotent by source module, source event, and source ID
- support reversals without deleting posted accounting evidence
- allow period-close checks before operational accounting impact
- support GRNI, WIP, finished goods, variance, landed cost, and adjustment posting
- stay additive and nullable first so existing development data remains safe

## Proposed New Enum Additions

| Enum | Values | Purpose |
|---|---|---|
| `OperationalPostingStatus` | `NOT_REQUIRED`, `PENDING`, `POSTED`, `FAILED`, `REVERSED` | Standard status for operational records that may create accounting impact. |
| `OperationalPostingEventType` | `GRN_POSTED`, `SUPPLIER_INVOICE_POSTED`, `MATERIAL_ISSUED`, `FG_RECEIVED`, `INVENTORY_ADJUSTED`, `LANDED_COST_POSTED`, `CYCLE_COUNT_VARIANCE_POSTED`, `PRODUCTION_VARIANCE_POSTED` | Source-event vocabulary for accounting posting batches. |
| `InventoryValuationSource` | `STANDARD`, `FIFO_LAYER`, `WEIGHTED_AVERAGE`, `MANUAL` | Records how movement accounting value was derived. |

These can live in `backend/app/models/finance.py` or in a new small integration model module if the migration grows too large. Prefer the smallest consistent extension.

## Proposed New Tables

### `operational_posting_links`

This table provides a generic cross-module audit link from source document/movement to posting batch and journal entry.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `source_module` | string | `inventory`, `procurement`, `production`, `landed_cost`, `cycle_count`, etc. |
| `source_event` | `OperationalPostingEventType` or string | Use enum if practical; string is more flexible for future modules. |
| `source_id` | string | Source record ID as text for cross-module flexibility. |
| `source_ref` | string, nullable | Human-readable reference like GRN number, production order number, movement reference. |
| `stock_movement_id` | FK `stock_movements.id`, nullable | Set when the source event is movement-based. |
| `posting_batch_id` | FK `accounting_posting_batches.id`, nullable | Links to GAP-001 idempotency/posting status. |
| `journal_entry_id` | FK `journal_entries.id`, nullable | Final GL entry created by the batch. |
| `status` | `OperationalPostingStatus` | Default `PENDING`. |
| `valuation_source` | `InventoryValuationSource`, nullable | How inventory value was calculated. |
| `posting_amount` | numeric, nullable | Amount posted in base currency. |
| `currency` | string | Default `KES`. |
| `error_message` | text, nullable | Last posting failure. |
| `posted_at` | datetime, nullable | Audit field. |
| `reversed_by_link_id` | FK self, nullable | Reversal trace. |
| `created_at`, `updated_at` | datetime | Standard timestamp mixin fields. |

Recommended constraints:

- Unique `(source_module, source_event, source_id)` for one-time posting events.
- Index `(stock_movement_id)`.
- Index `(posting_batch_id)`.
- Index `(journal_entry_id)`.

### `operational_posting_rule_defaults`

Optional table for factory defaults that sit above the generic `AccountingPostingRule`.

Use only if the code needs structured manufacturing-specific mappings that are awkward in `accounting_posting_rules`.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `event_type` | string | Example: `MATERIAL_ISSUED`. |
| `stock_type` | string, nullable | `MATERIAL` or `PRODUCT`. |
| `item_category` | string, nullable | Optional product/material category discriminator. |
| `inventory_account_id` | FK `chart_of_accounts.id`, nullable | Inventory account. |
| `wip_account_id` | FK `chart_of_accounts.id`, nullable | WIP account. |
| `grni_account_id` | FK `chart_of_accounts.id`, nullable | Received-not-invoiced clearing account. |
| `variance_account_id` | FK `chart_of_accounts.id`, nullable | Production or inventory variance account. |
| `scrap_account_id` | FK `chart_of_accounts.id`, nullable | Scrap/waste account. |
| `is_active` | boolean | Default true. |

Recommendation:

- Prefer using `accounting_posting_rules` first.
- Add this table only if GAP-002C/D needs more structure than the generic posting rules can support.

## Proposed Changes To Existing Tables

### `stock_movements`

Add nullable fields:

- `posting_status`
- `posting_batch_id` FK `accounting_posting_batches.id`
- `journal_entry_id` FK `journal_entries.id`
- `valuation_source`
- `base_value_amount`
- `reversal_of_movement_id` self-FK, nullable
- `reversed_by_movement_id` self-FK, nullable

Why:

- every quantity/value movement can be reconciled to accounting where required
- not every transfer needs GL impact, so nullable fields and `NOT_REQUIRED` status are important

### `grn_lines`

Add nullable fields:

- `posting_link_id` FK `operational_posting_links.id`
- `grni_posted_amount`
- `inventory_posted_amount`

Why:

- GRN line is the natural bridge between procurement receipt, stock movement, and GRNI accounting

### `purchase_invoice_lines`

Add nullable fields:

- `grn_line_id` FK `grn_lines.id`, nullable
- `posting_link_id` FK `operational_posting_links.id`, nullable
- `grni_cleared_amount`

Why:

- supplier invoice posting needs to clear GRNI against received goods where possible

### `material_consumptions`

Add nullable fields:

- `posting_link_id` FK `operational_posting_links.id`
- `wip_posted_amount`
- `inventory_credit_amount`

Why:

- material issue to production should post WIP debit and material inventory credit

### `finished_goods_receipts`

Add nullable fields:

- `posting_link_id` FK `operational_posting_links.id`
- `wip_credit_amount`
- `fg_inventory_posted_amount`

Why:

- finished goods receipt should post finished goods inventory debit and WIP credit

### `landed_cost_allocation_lines`

Add nullable fields:

- `posting_link_id` FK `operational_posting_links.id`
- `journal_entry_id` FK `journal_entries.id`, nullable

Why:

- landed cost should be traceable to inventory valuation and GL posting

## Source Event Posting Map

| Event | Source Record | Expected Journal |
|---|---|---|
| `GRN_POSTED` | `GRNLine` / `StockMovement` | Debit inventory, credit GRNI. |
| `SUPPLIER_INVOICE_POSTED` | `PurchaseInvoiceLine` | Debit GRNI/tax recoverable/expense as needed, credit AP. |
| `MATERIAL_ISSUED` | `MaterialConsumption` / `StockMovement` | Debit WIP, credit raw material inventory. |
| `FG_RECEIVED` | `FinishedGoodsReceipt` / `StockMovement` | Debit finished goods inventory, credit WIP. |
| `INVENTORY_ADJUSTED` | `StockMovement` | Debit/credit inventory and variance/write-off account based on direction. |
| `LANDED_COST_POSTED` | `LandedCostAllocationLine` | Debit inventory, credit landed cost clearing/AP. |
| `PRODUCTION_VARIANCE_POSTED` | `ProductionOrder` / cost rollup | Debit/credit production variance accounts. |

## Service Design For GAP-002F

Add a focused service layer, likely `backend/app/services/accounting_posting_service.py`, with functions such as:

- `post_grn_line_to_gl(db, grn_line, user_id)`
- `post_supplier_invoice_line_to_gl(db, invoice_line, user_id)`
- `post_material_issue_to_wip(db, consumption, user_id)`
- `post_finished_goods_receipt_to_gl(db, receipt, user_id)`
- `post_inventory_adjustment_to_gl(db, movement, user_id)`
- `post_landed_cost_allocation_to_gl(db, allocation_line, user_id)`
- `reverse_operational_posting(db, posting_link, user_id)`

Each function should:

1. derive source module/event/source ID
2. create or reuse `AccountingPostingBatch`
3. call `assert_posting_period_open`
4. resolve accounts from posting rules
5. derive valuation amount from standard/FIFO/weighted average/manual source
6. create balanced journal entry lines
7. mark journal posted through `mark_journal_posted`
8. update operational posting link fields
9. leave a clear error message if posting fails

## Migration Strategy For GAP-002C

Use additive migration steps:

1. Create enum types if using enums.
2. Create `operational_posting_links`.
3. Add nullable posting/link fields to `stock_movements`.
4. Add nullable posting/link fields to GRN, purchase invoice, material consumption, finished goods receipt, and landed cost allocation tables.
5. Add indexes and foreign keys.
6. Do not backfill accounting journals automatically.
7. Do not make nullable fields required until production posting behavior has run safely.

## Test Requirements For Later Tasks

`GAP-002J` should include tests for:

- GRN posting creates stock movement and accounting posting link
- GRN posting is idempotent
- material consumption creates WIP posting link
- finished goods receipt creates FG/WIP posting link
- posting is blocked in closed/locked accounting periods
- missing posting rules produce a safe failure and no partial journal
- reversing a source posting creates a reversal journal and marks the link reversed
- inventory movement with `NOT_REQUIRED` status does not require a journal

## Acceptance Criteria Result

`GAP-002B` is complete when this design is captured and the task queue points to `GAP-002C` for an additive migration.
